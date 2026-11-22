"""Version 0.5.0: favorite slots of the house and "all off" per room (spec 4.1, 4.7, 4.13, acceptance "Alles aus")."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import (
    CONF_ALL_OFF,
    CONF_HOUSE_FAVORITE_SLOTS,
    CONF_ROOMS,
    DOMAIN,
    EVENT_ALL_OFF,
    EVENT_SKIPPED,
    HOUSE,
)
from custom_components.resident_scenes.logbook import async_describe_events
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import area_registry as ar, entity_registry as er
from tests.conftest import direct, save, ws

SETTINGS = {"label": "resident_scenes", "scenes_per_area": 20, "house_scenes": 30, "steps_per_scene": 150,
            "name_length": 30, "max_delay": 600, "image_side": 1600, "image_kb": 500, "image_count": 200,
            "favorite_slots": 4, "image_dir": "resident_scenes"}


async def _flow(hass, entry, step: str, *inputs: dict) -> dict:
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": step})
    for data in inputs:
        result = await hass.config_entries.options.async_configure(result["flow_id"], data)
    await hass.async_block_till_done()
    return result


async def _template(hass, entry, options: dict) -> dict:
    path = Path(hass.config.path("tpl.json"))
    await hass.async_add_executor_job(path.write_text, json.dumps({"options": options}))
    try:
        return await _flow(hass, entry, "template", {"template": "tpl.json"})
    finally:
        await hass.async_add_executor_job(path.unlink)


async def test_house_favorite_slots(hass: HomeAssistant, setup, hass_ws_client, hass_access_token):
    """Spec 4.1, 4.7, acceptance "Startseite": eight house slots, four per room; no option, no change."""
    store = setup.runtime_data
    admin = await ws(hass, hass_ws_client, hass_access_token)
    scenes = [await save(direct(store), name=f"H{i}") for i in range(6)]
    kitchen = await save(direct(store), name="K", area_id="kitchen")
    # update: without the option the house has as many slots as each room
    assert CONF_HOUSE_FAVORITE_SLOTS not in setup.options
    assert (await admin(type=f"{DOMAIN}/list", scope=HOUSE))["result"]["favorite_slots"] == 4
    assert len(store.slots(HOUSE)) == 4

    # the settings form takes the number as int, the rooms stay at four
    result = await _flow(hass, setup, "settings", {**SETTINGS, CONF_HOUSE_FAVORITE_SLOTS: 8.0})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup.options[CONF_HOUSE_FAVORITE_SLOTS] == 8
    for slot, sid in enumerate(scenes):
        assert (await admin(type=f"{DOMAIN}/set_favorite", scope=HOUSE, slot=slot, scene_id=sid))["success"]
    house = (await admin(type=f"{DOMAIN}/list", scope=HOUSE))["result"]
    assert house["favorite_slots"] == 8 and house["favorites"] == [*scenes, None, None]
    room = (await admin(type=f"{DOMAIN}/list", scope="kitchen"))["result"]
    assert room["favorite_slots"] == 4 and len(room["favorites"]) == 4
    refused = await admin(type=f"{DOMAIN}/set_favorite", scope="kitchen", slot=5, scene_id=kitchen)
    assert not refused["success"]

    # left empty in the form: back to the count per room, the stored slots stay
    await _flow(hass, setup, "settings", SETTINGS)
    assert CONF_HOUSE_FAVORITE_SLOTS not in setup.options
    assert store.slots(HOUSE) == scenes[:4]
    assert store.favorites[HOUSE][:6] == scenes

    # the template carries it, checked like the form
    assert (await _template(hass, setup, {CONF_HOUSE_FAVORITE_SLOTS: 13}))["errors"] == {"base": "invalid_template"}
    assert (await _template(hass, setup, {CONF_HOUSE_FAVORITE_SLOTS: "8"}))["errors"] == {"base": "invalid_template"}
    assert (await _template(hass, setup, {CONF_HOUSE_FAVORITE_SLOTS: 6}))["type"] == "create_entry"
    await hass.async_block_till_done()
    assert store.slots(HOUSE) == scenes


@pytest.fixture
async def room(hass: HomeAssistant, setup):
    """The kitchen gets three lights, a socket, a TV; the hall a socket and a music player. All released and on."""
    ent_reg = er.async_get(hass)
    areas = {a.name: a.id for a in ar.async_get(hass).async_list_areas()}
    for domain, uid, area, cls in (
        ("light", "k2", "Kitchen", None), ("light", "k3", "Kitchen", None),
        ("switch", "socket", "Kitchen", "outlet"), ("media_player", "tv", "Kitchen", "tv"),
        ("switch", "hall_socket", "Hall", "outlet"), ("media_player", "hall_music", "Hall", None),
    ):
        entry = ent_reg.async_get_or_create(domain, "test", uid, suggested_object_id=uid, original_device_class=cls)
        ent_reg.async_update_entity(entry.entity_id, area_id=areas[area], labels={"resident_scenes"})
    for eid in ("light.k2", "light.k3"):
        hass.states.async_set(eid, "on", {"brightness": 200})
    for eid in ("switch.socket", "switch.hall_socket"):
        hass.states.async_set(eid, "on")
    hass.states.async_set("media_player.tv", "on", {"device_class": "tv"})
    hass.states.async_set("media_player.hall_music", "playing")
    await hass.async_block_till_done()
    return {
        "light": async_mock_service(hass, "light", "turn_off"),
        "switch": async_mock_service(hass, "switch", "turn_off"),
        "stop": async_mock_service(hass, "media_player", "media_stop"),
        "tv": async_mock_service(hass, "media_player", "turn_off"),
    }


def _ids(calls) -> set[str]:
    return {c.data["entity_id"] for c in calls}


async def _all_off(hass, area_id, user_id: str | None = None) -> None:
    context = Context(user_id=user_id) if user_id else None
    await hass.services.async_call(DOMAIN, "all_off", {"area_id": area_id}, blocking=True, context=context)
    await hass.async_block_till_done()


async def test_all_off(hass: HomeAssistant, setup, room, hass_read_only_user, resident_token):
    """Acceptance "Alles aus": the lights by default, switch and music per room, new lights at once, logbook, rights."""
    events = async_capture_events(hass, EVENT_ALL_OFF)
    describers: dict = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))

    # without a setting: the three lights of the kitchen; socket, music, TV, cover and climate stay
    await _all_off(hass, "kitchen")
    assert _ids(room["light"]) == {"light.kitchen", "light.k2", "light.k3"}
    assert not room["switch"] and not room["stop"] and not room["tv"]
    assert describers[EVENT_ALL_OFF](events[-1]) == {"name": "Kitchen", "message": "all off"}

    # switches and music for the kitchen: both Sonos and the other music player stop, the TV stays on
    hass.config_entries.async_update_entry(setup, options={CONF_ALL_OFF: {"kitchen": ["switch", "music"]}})
    room["light"].clear()
    await _all_off(hass, "kitchen")
    assert _ids(room["switch"]) == {"switch.socket"}
    assert _ids(room["stop"]) == {"media_player.kitchen", "media_player.sonos_kitchen"}
    assert not room["tv"]
    # the TV only with its own switch
    hass.config_entries.async_update_entry(setup, options={CONF_ALL_OFF: {"kitchen": ["tv"]}})
    room["stop"].clear()
    await _all_off(hass, "kitchen")
    assert _ids(room["tv"]) == {"media_player.tv"} and not room["stop"]

    # a second room without the setting: lights only, its socket and music stay on
    room["switch"].clear()
    await _all_off(hass, "hall")
    assert "light.hall" in _ids(room["light"]) and not room["switch"] and not room["stop"]

    # a fourth light released afterwards is in without any setting
    ent = er.async_get(hass).async_get_or_create("light", "test", "k4", suggested_object_id="k4")
    er.async_get(hass).async_update_entity(ent.entity_id, area_id="kitchen", labels={"resident_scenes"})
    hass.states.async_set("light.k4", "on")
    room["light"].clear()
    await _all_off(hass, "kitchen")
    assert "light.k4" in _ids(room["light"])

    # an account with the room right runs it, also without the edit right; it switches under that account
    uid = hass_read_only_user.id
    hass.config_entries.async_update_entry(setup, options={"users_without_edit": [uid], CONF_ROOMS: {uid: ["hall"]}})
    room["light"].clear()
    await _all_off(hass, "hall", uid)
    assert [c.context.user_id for c in room["light"]] == [uid]
    assert events[-1].context.user_id == uid
    # without the room right: refused, also through the action, nothing switches, the logbook names it
    room["light"].clear()
    with pytest.raises(Unauthorized):
        await _all_off(hass, "kitchen", uid)
    with pytest.raises(Unauthorized):
        await _all_off(hass, ["hall", "kitchen"], uid)
    assert not room["light"]
    assert describers[EVENT_ALL_OFF](events[-1])["message"] == "all off not run: no right for this room"
    # an automation without a user runs it in any room
    await _all_off(hass, "kitchen")
    assert "light.kitchen" in _ids(room["light"])
    assert len(events) == 9


async def test_all_off_skips_and_checks(hass: HomeAssistant, setup, room):
    """Spec 4.13: an unreachable device is skipped and named; an unknown room and a not loaded integration refuse."""
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    hass.states.async_set("light.k2", "unavailable")
    await _all_off(hass, "kitchen")
    assert "light.k2" not in _ids(room["light"])
    assert skipped[-1].data["name"] == "All off Kitchen" and skipped[-1].data["entities"] == ["light.k2"]
    with pytest.raises(ServiceValidationError):
        await _all_off(hass, "nowhere")
    await hass.config_entries.async_unload(setup.entry_id)
    with pytest.raises(ServiceValidationError):
        await _all_off(hass, "kitchen")


async def test_all_off_options(hass: HomeAssistant, setup):
    """Spec 4.1: the installer sets "all off" per room in the options and the template; a deleted room drops it."""
    result = await _flow(hass, setup, "all_off", {"area": "kitchen"})
    assert result["step_id"] == "all_off_room" and result["description_placeholders"] == {"area": "Kitchen"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"music": True, "tv": False, "switch": True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await _flow(hass, setup, "all_off", {"area": "hall"}, {"music": False, "tv": True, "switch": False})
    assert setup.options[CONF_ALL_OFF] == {"kitchen": ["music", "switch"], "hall": ["tv"]}
    # the form shows the stored switches; all off again: lights only, the room leaves the setting
    form = await _flow(hass, setup, "all_off", {"area": "kitchen"})
    defaults = {str(k): k.default() for k in form["data_schema"].schema}
    assert defaults == {"music": True, "tv": False, "switch": True}
    await hass.config_entries.options.async_configure(form["flow_id"], {"music": False, "tv": False, "switch": False})
    assert setup.options[CONF_ALL_OFF] == {"hall": ["tv"]}
    # the settings form keeps it
    await _flow(hass, setup, "settings", SETTINGS)
    assert setup.options[CONF_ALL_OFF] == {"hall": ["tv"]}

    # the template: checked, then replaces the setting as a whole
    for bad in ({"nowhere": ["tv"]}, {"kitchen": ["light"]}, {"kitchen": "tv"}, ["kitchen"]):
        assert (await _template(hass, setup, {CONF_ALL_OFF: bad}))["errors"] == {"base": "invalid_template"}
    assert setup.options[CONF_ALL_OFF] == {"hall": ["tv"]}
    loaded = await _template(hass, setup, {CONF_ALL_OFF: {"kitchen": ["switch", "music", "music"]}})
    assert loaded["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup.options[CONF_ALL_OFF] == {"kitchen": ["music", "switch"]}
    # a template without it keeps it
    assert (await _template(hass, setup, {"favorite_slots": 4}))["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup.options[CONF_ALL_OFF] == {"kitchen": ["music", "switch"]}

    # a deleted room drops its setting; a new room of the same name starts with lights only
    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    assert setup.options[CONF_ALL_OFF] == {}
    # also when the room went while Home Assistant was stopped
    hall = ar.async_get(hass).async_get_area_by_name("Hall")
    options = {**setup.options, CONF_ALL_OFF: {"gone": ["tv"], hall.id: ["tv"]}}
    hass.config_entries.async_update_entry(setup, options=options)
    await hass.config_entries.async_reload(setup.entry_id)
    await hass.async_block_till_done()
    assert setup.options[CONF_ALL_OFF] == {hall.id: ["tv"]}
