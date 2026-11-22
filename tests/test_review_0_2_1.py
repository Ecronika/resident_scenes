"""Review of version 0.2.1 (commit 52a8aa7).

Taken over from the review; the FINDING lines are turned around for 0.2.2. NOTE lines keep known limits.
The preview tests (T2, cancel after a reload) went with the preview in 0.3.0.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_BATCH
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from tests.conftest import eid as _eid, flat, save as _save, ws as _ws

LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}


async def test_t1_a_scene_cannot_be_made_to_call_itself(hass, setup, hass_ws_client, resident_token):
    """The own id is never a call target, a room scene is called once, and every scene runs once per trigger."""
    call = await _ws(hass, hass_ws_client, resident_token)
    room = await _save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    house = await _save(call, name="Home", steps=[{"mode": "scene", "scene_id": room}])
    add = {"type": f"{DOMAIN}/add_step", "edit": "x", "step_type": "scene"}
    assert (await call(**add, scene_id=house, target=house))["error"]["code"] == "invalid_scene_call"  # OK (T1)
    assert (await call(**add, scene_id=house, target=room))["error"]["code"] == "invalid_scene_call"  # once
    assert (await call(**add, scene_id=room, target=room))["error"]["code"] == "invalid_scene_call"  # room: none
    res = await call(**add, scene_id=house, target=room, area_id="other")
    assert res["error"]["code"] == "invalid_scene_call"  # a room scene of the chosen room only
    # a loop that got into the store anyway (hand edit): one trigger runs it once
    store = setup.runtime_data
    store.scenes[house]["sequence"].append(
        {"id": "00000001", "type": "scene", "scene_id": house, "name": "Home", "area_id": None}
    )
    batches = []
    hass.bus.async_listen(EVENT_BATCH, batches.append)
    async_mock_service(hass, "light", "turn_on")
    await hass.services.async_call("scene", "turn_on", {"entity_id": _eid(hass, house)}, blocking=True)
    await asyncio.sleep(0.3)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sorted(e.data["scene_id"] for e in batches) == sorted([house, room])  # OK (T1): each once


async def test_capture_all_takes_over_every_scene(hass, setup, hass_ws_client, resident_token):
    """Note for README and automations: an area or "all" as target overwrites every scene found with one state."""
    call = await _ws(hass, hass_ws_client, resident_token)
    first = await _save(call, name="Bright", area_id="kitchen", steps=[LIGHT_SET])
    dark = {"entity_id": "light.kitchen", "mode": "off"}
    second = await _save(call, name="Dark", area_id="kitchen", steps=[dark])
    await hass.async_block_till_done()
    hass.states.async_set("light.kitchen", "on", {"brightness": 77, "color_mode": "brightness"})
    await hass.services.async_call(DOMAIN, "capture", {"area_id": "kitchen"}, blocking=True)
    store = setup.runtime_data
    assert flat(store.scenes[first])[0]["attributes"]["brightness"] == 77
    assert flat(store.scenes[second])[0]["state"] == "on"  # NOTE: "Dark" now switches the light on


async def test_s9_fixed_repair_issue_when_a_favorite_is_deleted(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    radio = {"entity_id": "media_player.sonos_kitchen", "mode": "music", "music": "favorite",
             "favorite_id": "FV:2/1", "volume": 0.2}
    sid = await _save(call, name="Radio", area_id="kitchen", steps=[radio])
    await hass.async_block_till_done()
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"broken_{sid}") is None
    hass.states.async_set("sensor.sonos_favorites", "1", {"items": {"FV:2/2": "News"}})  # deleted in the Sonos app
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, f"broken_{sid}") is not None  # OK (S9): without any change of a scene
