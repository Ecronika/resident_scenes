"""Review of version 0.4.1 (commit 6740918): the fixes of AB1 and AB2, with AC3 marked fixed in 0.4.2.

Every test passes against 0.4.2. Lines marked FINDING show a defect, NOTE a limit or a difference
to functional spec draft 0.16, OK a point that holds. Drop the file into tests/ to run it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import CONF_ROOMS, CONF_USERS_WITHOUT_HOUSE, DOMAIN, EVENT_RIGHTS
from custom_components.resident_scenes.model import may_see
from homeassistant.core import Context
from homeassistant.exceptions import Unauthorized
from tests.conftest import direct, eid, save, ws

LIGHT = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}
HALL_OFF = {"entity_id": "light.hall", "mode": "off"}


async def _limit(hass, setup, user, rooms, house=True):
    options = {**setup.options, CONF_ROOMS: {user.id: list(rooms)}}
    options[CONF_USERS_WITHOUT_HOUSE] = [] if house else [user.id]
    hass.config_entries.async_update_entry(setup, options=options)
    await hass.async_block_till_done()


async def _turn_on(hass, entity_id: str, user_id: str | None) -> None:
    context = Context(user_id=user_id) if user_id else None
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True, context=context)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_ab1_an_allowed_call_still_marks_the_scene_as_run(hass, setup, resident_token, hass_read_only_user):
    """AB1 and spec 4.3: with the entity on BaseScene, a call that runs still records the run, once."""
    admin = direct(setup.runtime_data)
    kitchen = await save(admin, name="Kochen", area_id="kitchen", steps=[LIGHT])
    await hass.async_block_till_done()
    await _limit(hass, setup, hass_read_only_user, ["kitchen"])
    entity_id = eid(hass, kitchen)
    on = async_mock_service(hass, "light", "turn_on")
    stamps = async_capture_events(hass, "state_changed")
    assert hass.states.get(entity_id).state == "unknown"
    await _turn_on(hass, entity_id, hass_read_only_user.id)
    first = hass.states.get(entity_id)
    assert first.state != "unknown" and first.context.user_id == hass_read_only_user.id  # OK: run by the account
    assert len(on) == 1  # OK: the scene ran
    await _turn_on(hass, entity_id, None)  # a schedule
    second = hass.states.get(entity_id)
    assert second.state > first.state and second.context.user_id is None  # OK: recorded without a user too
    assert len(on) == 2
    assert len([e for e in stamps if e.data["entity_id"] == entity_id]) == 2  # OK: one state change per run


async def test_ab1_a_refused_house_scene_leaves_its_state(hass, setup, resident_token, hass_read_only_user):
    """AB1 for the house right: without it the house scene is refused and keeps its last run."""
    admin = direct(setup.runtime_data)
    away = await save(admin, name="Abwesend", steps=[HALL_OFF])
    await hass.async_block_till_done()
    entity_id = eid(hass, away)
    await _turn_on(hass, entity_id, None)
    before = hass.states.get(entity_id)
    await _limit(hass, setup, hass_read_only_user, ["kitchen"], house=False)
    off = async_mock_service(hass, "light", "turn_off")
    stamps = async_capture_events(hass, "state_changed")
    with pytest.raises(Unauthorized):
        await _turn_on(hass, entity_id, hass_read_only_user.id)
    await hass.async_block_till_done(wait_background_tasks=True)
    after = hass.states.get(entity_id)
    assert not off and after.state == before.state  # OK: the time of the last real run stays
    assert not [e for e in stamps if e.data["entity_id"] == entity_id]  # OK: no state change, no trigger


async def test_ab2_a_template_replaces_the_room_rights_as_a_whole(hass, setup, resident_token, hass_read_only_user):
    """AB2 and spec 4.1: the template carries room rights. It sets them for all accounts at once."""
    child = hass_read_only_user  # resident_token makes it an ordinary resident account
    assert may_see(hass, setup, child, "hall") and may_see(hass, setup, child, None)
    panel = await hass.auth.async_create_user("Panel", group_ids=["system-users"])

    async def load(options: dict) -> dict:
        path = Path(hass.config.path("tpl.json"))
        await hass.async_add_executor_job(path.write_text, json.dumps({"options": options}))
        try:
            flow = await hass.config_entries.options.async_init(setup.entry_id)
            flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "template"})
            return await hass.config_entries.options.async_configure(flow["flow_id"], {"template": "tpl.json"})
        finally:
            await hass.async_add_executor_job(path.unlink)

    # a main user has limited the child to the kitchen and taken its house right, in the card
    await _limit(hass, setup, child, ["kitchen"], house=False)
    assert not may_see(hass, setup, child, "hall") and not may_see(hass, setup, child, None)
    # the installer loads a template that limits the panel
    assert (await load({"rooms": {panel.id: ["hall"]}, "users_without_house": []}))["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {panel.id: ["hall"]}
    # NOTE: the child has all rooms and the house right again. The mapping of the template replaces the
    # stored one, as it does for the other lists of accounts. README: "an account not listed has all rooms".
    assert may_see(hass, setup, child, "hall") and may_see(hass, setup, child, None)
    # OK: an account with no room at all can be set, a value that is no list is refused whole
    assert (await load({"rooms": {panel.id: []}}))["type"] == "create_entry"
    await hass.async_block_till_done()
    assert not may_see(hass, setup, panel, "hall")
    assert (await load({"rooms": {panel.id: None}}))["errors"] == {"base": "invalid_template"}
    assert (await load({"users_without_house": panel.id}))["errors"] == {"base": "invalid_template"}
    assert setup.options[CONF_ROOMS] == {panel.id: []}  # OK: a refused template changes nothing
    # NOTE: an account id the installation does not know is stored as it comes, like in the other lists
    assert (await load({"rooms": {"nobody": ["hall"]}}))["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {"nobody": ["hall"]}
    assert (await hass.config_entries.async_reload(setup.entry_id)) and DOMAIN in hass.config.components


async def test_set_rooms_without_change_writes_no_logbook_entry(
    hass, setup, hass_ws_client, hass_access_token, resident_token, hass_read_only_user
):
    """Spec 3: every change of the rights is in the logbook. A call that changes nothing logs nothing."""
    admin = await ws(hass, hass_ws_client, hass_access_token)
    events = async_capture_events(hass, EVENT_RIGHTS)
    call = {"type": f"{DOMAIN}/set_rooms", "user_id": hass_read_only_user.id, "rooms": ["kitchen"], "house": True}
    assert (await admin(**call))["success"]
    assert (await admin(**call))["success"]  # the card sends this for two taps while a call is on its way
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {hass_read_only_user.id: ["kitchen"]}
    # FIXED AC3: one entry for one change, the second call still succeeds
    assert [e.data["rooms"] for e in events] == [["Kitchen"]]
