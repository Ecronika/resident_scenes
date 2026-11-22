"""Review of version 0.4.0 (commit 01f8349), stage 4: room rights.

Lines marked FIXED show a finding of the review that 0.4.1 fixes (spec draft 0.16), NOTE a limit or a
difference to the functional spec, OK a point that holds.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import CONF_ROOMS, CONF_USERS_WITHOUT_HOUSE, DOMAIN, EVENT_CHANGED
from homeassistant.core import Context, callback
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.setup import async_setup_component
from tests.conftest import direct, eid, save, ws

LIGHT = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}
HALL_OFF = {"entity_id": "light.hall", "mode": "off"}


async def _limited(hass, setup, user, rooms=("kitchen",), house=True):
    """Limit the resident account to rooms, as set_rooms stores it."""
    options = {**setup.options, CONF_ROOMS: {user.id: list(rooms)}}
    options[CONF_USERS_WITHOUT_HOUSE] = [] if house else [user.id]
    hass.config_entries.async_update_entry(setup, options=options)
    await hass.async_block_till_done()


async def test_ab1_a_refused_call_leaves_the_scene_state(hass, setup, resident_token, hass_read_only_user):
    """Spec 4.4: a call without the room right is refused and leaves the scene entity as it is."""
    hall = await save(direct(setup.runtime_data), name="Flur", area_id="hall", steps=[HALL_OFF])
    await hass.async_block_till_done()
    await _limited(hass, setup, hass_read_only_user)
    entity_id = eid(hass, hall)
    before = hass.states.get(entity_id)
    assert before.state == "unknown"  # never run
    off = async_mock_service(hass, "light", "turn_off")
    seen = []

    @callback
    def stamp(event) -> None:
        if event.data["entity_id"] == entity_id:
            seen.append(event)

    hass.bus.async_listen("state_changed", stamp)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            "scene", "turn_on", {"entity_id": entity_id}, blocking=True, context=Context(user_id=hass_read_only_user.id)
        )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert not off  # OK: no device was switched
    after = hass.states.get(entity_id)
    # FIXED AB1: the right is checked before the run is recorded. The refused call leaves the state
    # as it is, and no state trigger on the scene fires (spec 4.4, draft 0.16).
    assert after.state == before.state
    assert after.context.user_id != hass_read_only_user.id
    assert not seen


async def test_ab2_a_template_carries_room_rights(hass, setup, hass_read_only_user):
    """Spec 4.1: room rights are options, and the template carries the options."""
    uid = hass_read_only_user.id

    async def load(options: dict) -> dict:
        path = Path(hass.config.path("tpl.json"))
        await hass.async_add_executor_job(path.write_text, json.dumps({"options": options}))
        try:
            flow = await hass.config_entries.options.async_init(setup.entry_id)
            flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "template"})
            return await hass.config_entries.options.async_configure(flow["flow_id"], {"template": "tpl.json"})
        finally:
            await hass.async_add_executor_job(path.unlink)

    # FIXED AB2: an unknown room refuses the whole template, like set_rooms
    refused = await load({"rooms": {uid: ["kitchen", "nowhere"]}, "favorite_slots": 2})
    assert refused["errors"] == {"base": "invalid_template"}
    assert (await load({"rooms": "kitchen"}))["errors"] == {"base": "invalid_template"}
    assert CONF_ROOMS not in setup.options  # OK: refused whole, nothing was stored
    # FIXED AB2: both keys are accepted, so the generator can limit a panel account to its room
    loaded = await load({"rooms": {uid: ["kitchen", "kitchen"]}, "users_without_house": [uid]})
    assert loaded["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {uid: ["kitchen"]} and setup.options[CONF_USERS_WITHOUT_HOUSE] == [uid]
    # OK: a template without them keeps the room rights set in the card
    await _limited(hass, setup, hass_read_only_user, house=False)
    assert (await load({"favorite_slots": 3}))["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {uid: ["kitchen"]} and setup.options[CONF_USERS_WITHOUT_HOUSE] == [uid]


async def test_a_house_scene_shows_its_whole_sequence(hass, setup, hass_ws_client, resident_token, hass_read_only_user):
    """Spec 3: scenes of other rooms are not named to a limited account. A house scene names them."""
    user = hass_read_only_user
    admin = direct(setup.runtime_data)
    hall = await save(admin, name="Flur", area_id="hall", steps=[HALL_OFF])
    away = await save(admin, name="Abwesend", steps=[HALL_OFF, {"mode": "scene", "scene_id": hall}])
    await hass.async_block_till_done()
    await _limited(hass, setup, hass_read_only_user)
    res = await ws(hass, hass_ws_client, resident_token)
    assert (await res(type=f"{DOMAIN}/scene", scene_id=hall))["error"]["code"] == "no_access"  # OK
    detail = (await res(type=f"{DOMAIN}/scene", scene_id=away))["result"]
    steps = {s["type"]: s for s in detail["sequence"]}
    # OK (AB5, draft 0.16 section 3): with the house right the account reads the hall's device and the
    # name of the hall scene. A house scene is shown whole, as it runs whole (spec 4.4).
    assert steps["group"]["area_id"] == "hall" and steps["group"]["entries"][0]["entity_id"] == "light.hall"
    assert steps["scene"]["name"] == "Flur" and steps["scene"]["scene_id"] == hall
    # OK: it runs whole, the scene step too, without the room right of the hall
    off = async_mock_service(hass, "light", "turn_off")
    await hass.services.async_call(
        "scene", "turn_on", {"entity_id": eid(hass, away)}, blocking=True, context=Context(user_id=user.id)
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    # once for the step of the house scene and once for the hall scene it calls
    assert len(off) == 2 and all(c.data["entity_id"] in ("light.hall", ["light.hall"]) for c in off)


async def test_the_subscription_says_only_that_something_changed(
    hass, setup, hass_ws_client, resident_token, hass_read_only_user
):
    """Spec 4.10: an account gets messages only for scenes it may see."""
    admin = direct(setup.runtime_data)
    hall = await save(admin, name="Flur", area_id="hall", steps=[HALL_OFF])
    await _limited(hass, setup, hass_read_only_user)
    res = await ws(hass, hass_ws_client, resident_token)
    assert (await res(type=f"{DOMAIN}/subscribe"))["success"]
    assert (await admin(type=f"{DOMAIN}/update", scene_id=hall, edit="z", name="Diele"))["success"]
    await hass.async_block_till_done()
    assert (await res(type=f"{DOMAIN}/list", scope="kitchen"))["success"]  # collects the events sent meanwhile
    # NOTE: the account is told that something changed, also for the hall. OK: the message names no scene.
    assert res.events and all(e["event"] == {"changed": True} for e in res.events)


async def test_missing_and_forbidden_answer_differently(
    hass, setup, hass_ws_client, resident_token, hass_read_only_user
):
    """Spec 3: the integration does not name scenes of other rooms."""
    hall = await save(direct(setup.runtime_data), name="Flur", area_id="hall", steps=[HALL_OFF])
    await _limited(hass, setup, hass_read_only_user)
    res = await ws(hass, hass_ws_client, resident_token)
    # NOTE: the answers tell an existing scene id from an unknown one. Ids are random (uuid4),
    # and Home Assistant shows every scene entity to every account anyway (spec 3, limit).
    assert (await res(type=f"{DOMAIN}/scene", scene_id=hall))["error"]["code"] == "no_access"
    assert (await res(type=f"{DOMAIN}/scene", scene_id="0" * 32))["error"]["code"] == "not_found"


async def test_a_script_started_by_the_account_needs_the_room_right(hass, setup, resident_token, hass_read_only_user):
    """Spec 3 "Ohne Benutzer": automations, schedules and KNX push buttons run every scene. A script does not."""
    hall = await save(direct(setup.runtime_data), name="Flur", area_id="hall", steps=[HALL_OFF])
    await hass.async_block_till_done()
    sequence = [{"action": "scene.turn_on", "target": {"entity_id": eid(hass, hall)}}]
    assert await async_setup_component(hass, "script", {"script": {"flur": {"sequence": sequence}}})
    await hass.async_block_till_done()
    await _limited(hass, setup, hass_read_only_user)
    off = async_mock_service(hass, "light", "turn_off")
    refused = async_capture_events(hass, EVENT_CHANGED)
    # NOTE (AB6, README): a script started from a dashboard button carries the account that pressed it
    with contextlib.suppress(HomeAssistantError):
        await hass.services.async_call("script", "flur", blocking=True, context=Context(user_id=hass_read_only_user.id))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert not off and refused[0].data["action"] == "not run: no right for its room"
    # OK: the same script without a user runs the scene
    await hass.services.async_call("script", "flur", blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert off
