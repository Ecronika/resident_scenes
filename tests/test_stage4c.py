"""Version 0.6.0, rework 4c: "all off" and running scenes, moved devices, run_favorite, TVs (spec 4.5, 4.13, 4.14)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)
import voluptuous as vol

from custom_components.resident_scenes.const import CONF_ALL_OFF, DOMAIN, EVENT_FAVORITE, EVENT_SKIPPED, HOUSE
from custom_components.resident_scenes.logbook import async_describe_events
from custom_components.resident_scenes.model import all_off_steps
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import device_registry as dr, entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util
from tests.conftest import direct, eid, run_scene, save

LIGHT_ON = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 120}}
HALL_ON = {"entity_id": "light.hall", "mode": "set", "values": {"brightness": 90}}


def _ids(calls) -> list[str]:
    return [c.data["entity_id"] for c in calls]


async def _later(hass, seconds: float) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done(wait_background_tasks=True)


async def _move(hass, entity_id: str, area_id: str | None) -> None:
    er.async_get(hass).async_update_entity(entity_id, area_id=area_id)
    await hass.async_block_till_done()


async def _start(hass, entity_id: str) -> None:
    """Run a scene and leave it waiting in its delay."""
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()


async def _all_off(hass, area_id: str) -> None:
    await hass.services.async_call(DOMAIN, "all_off", {"area_id": area_id}, blocking=True)
    await hass.async_block_till_done()


def _groups(scene) -> list[tuple]:
    return [
        (s["type"], s.get("area_id"), [e["entity_id"] for e in s.get("entries", [])]) for s in scene["sequence"]
    ]


async def test_all_off_overtakes_a_called_room_scene(hass: HomeAssistant, setup):
    """Spec 4.13: also through a called room scene; other rooms go on; a run after "all off" is not affected."""
    store = setup.runtime_data
    call = direct(store)
    room = await save(call, name="Cook", area_id="kitchen", steps=[{**LIGHT_ON, "delay": 30}])
    house = await save(call, name="Evening", edit="e2", steps=[
        {"mode": "scene", "scene_id": room}, {**HALL_ON, "delay": 30},
    ])
    on = async_mock_service(hass, "light", "turn_on")
    async_mock_service(hass, "light", "turn_off")
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    await _start(hass, eid(hass, house))
    await _all_off(hass, "kitchen")
    await _later(hass, 31)
    assert _ids(on) == ["light.hall"]  # the hall goes on, the kitchen light stays off
    assert skipped[-1].data["entities"] == ["light.kitchen"] and skipped[-1].data["scene_id"] == room
    # a run that begins after "all off" switches the light again
    await _start(hass, eid(hass, room))
    await _later(hass, 31)
    assert _ids(on)[-1] == "light.kitchen"


async def test_moved_device_in_a_room_scene(hass: HomeAssistant, setup):
    """Spec 4.5, acceptance "Gerät zieht um": skipped and named, the entry stays, applies again when back."""
    store = setup.runtime_data
    sid = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    on = async_mock_service(hass, "light", "turn_on")
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    issues = ir.async_get(hass)
    await _move(hass, "light.kitchen", "hall")
    await _later(hass, 3)
    issue = issues.async_get_issue(DOMAIN, f"broken_{sid}")
    assert issue.translation_placeholders == {"scene": "Cook", "items": "light.kitchen"}
    await run_scene(hass, eid(hass, sid))
    assert not on and skipped[-1].data["entities"] == ["light.kitchen"]
    assert _groups(store.scenes[sid]) == [("group", "kitchen", ["light.kitchen"])]  # a room scene keeps the entry
    await _move(hass, "light.kitchen", "kitchen")
    await _later(hass, 3)
    assert issues.async_get_issue(DOMAIN, f"broken_{sid}") is None
    await run_scene(hass, eid(hass, sid))
    assert _ids(on) == ["light.kitchen"]


async def test_moved_device_in_a_house_scene(hass: HomeAssistant, setup):
    """Spec 4.5: the entry moves into a step of the new room right after the old one, a step left empty goes."""
    store = setup.runtime_data
    sid = await save(direct(store), name="Away", steps=[LIGHT_ON, {"entity_id": "cover.kitchen", "mode": "off"}])
    version = store.scenes[sid]["version"]
    await _move(hass, "light.kitchen", "hall")
    assert _groups(store.scenes[sid]) == [("group", "hall", ["light.kitchen"]), ("group", "kitchen", ["cover.kitchen"])]
    assert store.scenes[sid]["version"] > version
    on = async_mock_service(hass, "light", "turn_on")
    await run_scene(hass, eid(hass, sid))
    assert _ids(on) == ["light.kitchen"]  # the house scene switches as before
    # losing its room: into a step without a room
    await _move(hass, "light.kitchen", None)
    assert _groups(store.scenes[sid])[0] == ("group", None, ["light.kitchen"])
    await _move(hass, "light.kitchen", "kitchen")
    assert _groups(store.scenes[sid])[0] == ("group", "kitchen", ["light.kitchen"])


async def test_moved_device_joins_the_next_step_before_a_delay(hass: HomeAssistant, setup):
    """Spec 4.5: a following step of that room and domain takes the entry; one of the device there wins."""
    store = setup.runtime_data
    sid = await save(direct(store), name="Away", steps=[
        LIGHT_ON, {"entity_id": "light.kitchen", "mode": "off", "delay": 5}, HALL_ON,
    ])
    assert [s[1] for s in _groups(store.scenes[sid])] == ["kitchen", None, "kitchen", "hall"]
    await _move(hass, "light.kitchen", "hall")
    # before the delay a new step; after it the hall step that follows takes the entry
    assert _groups(store.scenes[sid]) == [
        ("group", "hall", ["light.kitchen"]), ("delay", None, []), ("group", "hall", ["light.hall", "light.kitchen"]),
    ]
    # an entry of the device in the target step stays, the moved one goes
    await _move(hass, "light.kitchen", "kitchen")
    on, off = {"state": "on", "attributes": {}}, {"state": "off", "attributes": {}}
    store.scenes[sid]["sequence"] = [
        {"id": "a", "type": "group", "domain": "light", "area_id": "kitchen",
         "entries": [{"entity_id": "light.kitchen", **on}]},
        {"id": "b", "type": "group", "domain": "light", "area_id": "hall",
         "entries": [{"entity_id": "light.kitchen", **off}]},
    ]
    await _move(hass, "light.kitchen", "hall")
    assert store.scenes[sid]["sequence"] == [
        {"id": "b", "type": "group", "domain": "light", "area_id": "hall",
         "entries": [{"entity_id": "light.kitchen", **off}]},
    ]


async def test_moved_device_follows_its_device_and_the_start(hass: HomeAssistant, setup):
    """Spec 4.10: a device moved by its device area, and one moved while Home Assistant was stopped."""
    store = setup.runtime_data
    dev = dr.async_get(hass).async_get_or_create(config_entry_id=setup.entry_id, identifiers={("test", "lamp")})
    dr.async_get(hass).async_update_device(dev.id, area_id="kitchen")
    ent = er.async_get(hass).async_get_or_create("light", "test", "lamp", suggested_object_id="lamp", device_id=dev.id)
    er.async_get(hass).async_update_entity(ent.entity_id, labels={"resident_scenes"})
    hass.states.async_set(ent.entity_id, "on", {"brightness": 50, "color_mode": "brightness"})
    sid = await save(direct(store), name="Away", steps=[{"entity_id": ent.entity_id, "mode": "off"}])
    dr.async_get(hass).async_update_device(dev.id, area_id="hall")
    await hass.async_block_till_done()
    assert _groups(store.scenes[sid]) == [("group", "hall", [ent.entity_id])]
    # stored with the old room, as if the device had moved while stopped
    store.scenes[sid]["sequence"][0]["area_id"] = "kitchen"
    await hass.config_entries.async_reload(setup.entry_id)
    await hass.async_block_till_done()
    assert _groups(setup.runtime_data.scenes[sid]) == [("group", "hall", [ent.entity_id])]


async def test_run_favorite(hass: HomeAssistant, setup, hass_read_only_user, resident_token):
    """Spec 4.14, acceptance "Favoritenplatz am Taster": the scene on the slot of this moment."""
    store = setup.runtime_data
    call = direct(store)
    first = await save(call, name="One", area_id="kitchen", steps=[LIGHT_ON])
    second = await save(call, name="Two", area_id="kitchen", steps=[{"entity_id": "light.kitchen", "mode": "off"}])
    house = await save(call, name="House", steps=[HALL_ON])
    await store.async_set_favorite("kitchen", 0, first)
    await store.async_set_favorite(HOUSE, 1, house)
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    events = async_capture_events(hass, EVENT_FAVORITE)

    async def run(data, user=None):
        context = Context(user_id=user) if user else None
        await hass.services.async_call(DOMAIN, "run_favorite", data, blocking=True, context=context)
        await hass.async_block_till_done(wait_background_tasks=True)

    await run({"area_id": "kitchen", "slot": 1})
    assert _ids(on) == ["light.kitchen"]
    assert hass.states.get(eid(hass, first)).state != "unknown"  # the scene state is that of scene.turn_on
    await store.async_set_favorite("kitchen", 0, second)  # the resident puts another scene on the slot
    await run({"area_id": "kitchen", "slot": 1})
    assert _ids(off) == ["light.kitchen"]
    await run({"house": True, "slot": 2})
    assert _ids(on) == ["light.kitchen", "light.hall"]
    # an empty slot runs nothing and is named in the logbook
    await run({"area_id": "kitchen", "slot": 4})
    assert events[-1].data == {"area_id": "kitchen", "name": "Kitchen", "slot": 4, "result": "empty"}
    assert len(on) == 2 and len(off) == 1
    # a slot that does not exist, an unknown room
    with pytest.raises(ServiceValidationError):
        await run({"area_id": "kitchen", "slot": 5})
    with pytest.raises(ServiceValidationError):
        await run({"area_id": "cellar", "slot": 1})
    # exactly one target, a slot from 1
    for data in ({"slot": 1}, {"house": True, "area_id": "kitchen", "slot": 1}, {"house": False, "slot": 1},
                 {"house": True, "slot": 0}):
        with pytest.raises(vol.Invalid):
            await run(data)
    # a user: the right of running the scene; read-only accounts are refused, a resident runs it
    hass_read_only_user.groups = []
    hass_read_only_user.invalidate_cache()
    with pytest.raises(Unauthorized):
        await run({"area_id": "kitchen", "slot": 1}, hass_read_only_user.id)
    assert events[-1].data["result"] == "refused" and len(off) == 1


async def test_run_favorite_for_a_resident(hass: HomeAssistant, setup, hass_read_only_user, resident_token):
    """Spec 4.14: a resident with the room right runs the slot under his account."""
    store = setup.runtime_data
    sid = await save(direct(store), name="One", area_id="kitchen", steps=[LIGHT_ON])
    await store.async_set_favorite("kitchen", 0, sid)
    on = async_mock_service(hass, "light", "turn_on")
    await hass.services.async_call(
        DOMAIN, "run_favorite", {"area_id": "kitchen", "slot": 1}, blocking=True,
        context=Context(user_id=hass_read_only_user.id),
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert on[0].context.user_id == hass_read_only_user.id


async def test_run_favorite_logbook(hass: HomeAssistant, setup):
    """Spec 4.14: logbook texts are English, the room or the house by name."""
    describers: dict = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))
    events = async_capture_events(hass, EVENT_FAVORITE)
    await hass.services.async_call(DOMAIN, "run_favorite", {"house": True, "slot": 1}, blocking=True)
    await hass.async_block_till_done()
    entry = describers[EVENT_FAVORITE](events[-1])
    assert entry == {"name": "House", "message": "favorite slot 1 is empty, nothing run"}
    events[-1].data["result"] = "refused"
    assert describers[EVENT_FAVORITE](events[-1])["message"] == "favorite slot 1 not run: no right for this room"


async def test_run_favorite_not_loaded(hass: HomeAssistant, setup):
    """Without a loaded entry the action says so."""
    await hass.config_entries.async_unload(setup.entry_id)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "run_favorite", {"house": True, "slot": 1}, blocking=True)


async def test_tv_from_the_state(hass: HomeAssistant, setup):
    """Review AD4: a player without a class in the registry counts as TV by the class of its state."""
    hass.config_entries.async_update_entry(setup, options={CONF_ALL_OFF: {"kitchen": ["tv"]}})
    assert all(s["entity_id"] != "media_player.kitchen" for s in all_off_steps(hass, setup, "kitchen"))
    hass.states.async_set("media_player.kitchen", "on", {"device_class": "tv"})
    step = next(s for s in all_off_steps(hass, setup, "kitchen") if s["entity_id"] == "media_player.kitchen")
    assert step["music"] == "tv_off"
