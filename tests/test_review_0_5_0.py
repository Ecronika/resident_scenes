"""Review of version 0.5.0 (commit c96d95a): "all off" per room, and five points of an outside review.

Every test passes against 0.5.0. Lines marked FINDING show a defect, NOTE a limit or behaviour that
functional spec draft 0.22 asks for or leaves open, OK a point that holds. Drop the file into tests/ to run it.
Lines marked FIXED were flipped with version 0.6.0 (spec draft 0.24, rework 4c).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.resident_scenes.const import CONF_ALL_OFF, CONF_ROOMS, DOMAIN, EVENT_ALL_OFF, EVENT_SKIPPED
from custom_components.resident_scenes.issues import broken_steps
from custom_components.resident_scenes.logbook import async_describe_events
from custom_components.resident_scenes.model import all_off_steps, allowed_entities, step_issue
from homeassistant.core import Context
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from tests.conftest import direct, eid, flat, save

LIGHT_ON = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 120}}


async def _all_off(hass, area_id, user_id: str | None = None) -> None:
    context = Context(user_id=user_id) if user_id else None
    await hass.services.async_call(DOMAIN, "all_off", {"area_id": area_id}, blocking=True, context=context)
    await hass.async_block_till_done()


def _ids(calls) -> set[str]:
    return {c.data["entity_id"] for c in calls}


async def test_all_off_leaves_a_running_scene_alone(hass, setup):
    """Spec 4.13, draft 0.24: a scene waiting in a delay no longer switches the light on after "all off"."""
    store = setup.runtime_data
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    sid = await save(direct(store), name="Evening", area_id="kitchen", steps=[{**LIGHT_ON, "delay": 30}])
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done()
    assert not on  # the scene waits in its delay
    await _all_off(hass, "kitchen")
    assert "light.kitchen" in _ids(off)  # OK: "all off" switched the light off
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done(wait_background_tasks=True)
    # FIXED (AD1): the run that began before "all off" no longer switches the light, the logbook names it
    assert not on
    assert skipped[-1].data["entities"] == ["light.kitchen"] and skipped[-1].data["scene_id"] == sid


async def test_all_off_refuses_an_account_without_control(hass, setup, hass_read_only_user):
    """Spec 4.13: the right is that of running a room scene; a read-only account switches nothing."""
    off = async_mock_service(hass, "light", "turn_off")
    events = async_capture_events(hass, EVENT_ALL_OFF)
    with pytest.raises(Unauthorized):
        await _all_off(hass, "kitchen", hass_read_only_user.id)
    assert not off and events[-1].data["refused"] is True  # OK: refused and named in the logbook


async def test_all_off_takes_the_room_of_this_moment(hass, setup):
    """Spec 4.13: what belongs to the room and is released right now; no cover, no climate, nothing hidden away."""
    assert {s["entity_id"] for s in all_off_steps(hass, setup, "kitchen")} == {"light.kitchen"}  # OK: lights only
    registry = er.async_get(hass)
    registry.async_update_entity("light.kitchen", disabled_by=er.RegistryEntryDisabler.USER)
    assert all_off_steps(hass, setup, "kitchen") == []  # OK: a disabled light is not named as skipped every time
    registry.async_update_entity("light.kitchen", disabled_by=None)
    registry.async_update_entity("light.hall", area_id="kitchen")
    assert {s["entity_id"] for s in all_off_steps(hass, setup, "kitchen")} == {"light.kitchen", "light.hall"}  # OK
    assert all_off_steps(hass, setup, "hall") == []  # OK: the moved light left the hall at once


async def test_all_off_names_a_skipped_device_in_the_logbook(hass, setup):
    """Spec 4.13: an unreachable device is skipped and named; the entry reads like the one of a scene."""
    describers: dict = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    async_mock_service(hass, "light", "turn_off")
    hass.states.async_set("light.kitchen", "unavailable")
    await _all_off(hass, "kitchen")
    entry = describers[EVENT_SKIPPED](skipped[-1])
    assert entry["message"] == "skipped kitchen"  # OK: the device by its name
    assert entry["name"] == "All off Kitchen"  # NOTE: English in the logbook, like the other entries


async def test_all_off_setting_of_two_rooms(hass, setup):
    """Spec 4.1, draft 0.22: each room has its own setting; a room without one switches its lights only."""
    registry = er.async_get(hass)
    for uid, area in (("s_kitchen", "kitchen"), ("s_hall", "hall")):
        ent = registry.async_get_or_create("switch", "test", uid, suggested_object_id=uid)
        registry.async_update_entity(ent.entity_id, area_id=area, labels={"resident_scenes"})
        hass.states.async_set(ent.entity_id, "on")
    hass.config_entries.async_update_entry(setup, options={CONF_ALL_OFF: {"kitchen": ["switch"]}})
    assert "switch.s_kitchen" in {s["entity_id"] for s in all_off_steps(hass, setup, "kitchen")}  # OK
    assert "switch.s_hall" not in {s["entity_id"] for s in all_off_steps(hass, setup, "hall")}  # OK


async def test_outside_review_1_a_moved_device_still_runs(hass, setup, hass_read_only_user, resident_token):
    """Outside review, point 1: spec 4.5, draft 0.24. A stored entry of a moved device is skipped and named."""
    store = setup.runtime_data
    uid = hass_read_only_user.id
    sid = await save(direct(store), name="TV", area_id="kitchen", steps=[LIGHT_ON])
    er.async_get(hass).async_update_entity("light.kitchen", area_id="hall")  # the lamp moves to the hall
    await hass.async_block_till_done()
    entry = flat(store.scenes[sid])[0]
    allowed = allowed_entities(hass, setup)
    assert step_issue(hass, "kitchen", entry, allowed, {}) == "other_area"  # OK: the card marks "In anderem Raum"
    assert broken_steps(hass, store, store.scenes[sid]) == ["light.kitchen"]  # FIXED: a repair issue names it
    # an account limited to the kitchen still runs the kitchen scene, but no longer the lamp in the hall
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {uid: ["kitchen"]}})
    on = async_mock_service(hass, "light", "turn_on")
    await hass.services.async_call(
        "scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True, context=Context(user_id=uid)
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert not on  # FIXED: as spec 4.5 now says, the moved device is no longer switched
    assert flat(store.scenes[sid])[0]["entity_id"] == "light.kitchen"  # FIXED: the entry stays stored
    # "all off" goes by the room of this moment: the hall takes the lamp, the kitchen no longer
    assert {s["entity_id"] for s in all_off_steps(hass, setup, "hall")} == {"light.hall", "light.kitchen"}  # OK
    assert all_off_steps(hass, setup, "kitchen") == []  # OK


async def test_outside_review_3_capture_without_a_user(hass, setup, hass_read_only_user, resident_token):
    """Outside review, point 3: spec 4.9 asks for this. Without a user capture also takes a protected scene."""
    store = setup.runtime_data
    sid = await save(direct(store), name="Base", area_id="kitchen", steps=[LIGHT_ON], kind="installer")
    assert store.scenes[sid]["content_released"] is False
    hass.states.async_set("light.kitchen", "on", {"brightness": 33, "color_mode": "brightness"})
    target = {"entity_id": eid(hass, sid)}
    with pytest.raises(Unauthorized):  # OK: a resident may not, as in the card
        await hass.services.async_call(
            DOMAIN, "capture", target, blocking=True, context=Context(user_id=hass_read_only_user.id)
        )
    assert flat(store.scenes[sid])[0]["attributes"]["brightness"] == 120
    await hass.services.async_call(DOMAIN, "capture", target, blocking=True)
    # NOTE: an automation of the installer, e.g. a long press, overwrites the protected content
    assert flat(store.scenes[sid])[0]["attributes"]["brightness"] == 33
    assert store.scenes[sid]["previous"] is not None  # OK: the card can take this capture back


async def test_outside_review_5_a_called_scene_is_not_waited_for(hass, setup):
    """Outside review, point 5: spec 4.4. What stands between two delays goes out together; a call does not wait."""
    store = setup.runtime_data
    call = direct(store)
    room = await save(call, name="Prepare", area_id="kitchen", steps=[{**LIGHT_ON, "delay": 30}])
    house = await save(call, name="Cinema", edit="e2", steps=[
        {"mode": "scene", "scene_id": room}, {"entity_id": "light.hall", "mode": "off"},
    ])
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, house)}, blocking=True)
    await hass.async_block_till_done()
    # NOTE: the hall light goes off at once, while the called room scene still waits in its own delay
    assert _ids(off) == {"light.hall"} and not on
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert _ids(on) == {"light.kitchen"}  # OK: the room scene ends its own sequence
