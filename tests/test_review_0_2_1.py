"""Review of version 0.2.1 (commit 52a8aa7).

Taken over from the review; the FINDING lines are turned around for 0.2.2. NOTE lines keep known limits.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_BATCH
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util
from tests.test_init import _ws

SAVE = f"{DOMAIN}/save"
LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}


def _eid(hass, scene_id):
    return er.async_get(hass).async_get_entity_id("scene", DOMAIN, scene_id)


async def _save(call, **payload):
    res = await call(type=SAVE, **payload)
    assert res["success"], res
    return res["result"]["scene_id"]


async def test_t1_a_scene_cannot_be_made_to_call_itself(hass, setup, hass_ws_client, resident_token):
    """copy_from only makes new scenes, the own id is never a call target, and every scene runs once per trigger."""
    call = await _ws(hass, hass_ws_client, resident_token)
    room = await _save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    house = await _save(call, name="Home", steps=[{"mode": "scene", "scene_id": room}])
    keep = [{"entity_id": "light.kitchen", "mode": "keep"}]
    assert (await call(type=SAVE, scene_id=room, version=1, name="Cook", area_id=None, steps=keep))["success"]
    loop = [{"mode": "scene", "scene_id": room}, LIGHT_SET]
    res = await call(type=SAVE, scene_id=room, version=2, copy_from=house, name="Cook", steps=loop)
    assert not res["success"] and res["error"]["code"] == "invalid_value"  # OK (T1): no copy_from on a change
    res = await call(type=SAVE, scene_id=house, version=1, name="Home",
                     steps=[{"mode": "scene", "scene_id": room}, {"mode": "scene", "scene_id": house}])
    assert not res["success"] and res["error"]["code"] == "invalid_scene_call"  # OK (T1): never the own id
    # a loop that got into the store anyway (older version, hand edit): one trigger runs it once
    store = setup.runtime_data
    store.scenes[house]["steps"].append({"scene_id": house, "name": "Home"})
    batches = []
    hass.bus.async_listen(EVENT_BATCH, batches.append)
    async_mock_service(hass, "light", "turn_on")
    await hass.services.async_call("scene", "turn_on", {"entity_id": _eid(hass, house)}, blocking=True)
    await asyncio.sleep(0.3)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sorted(e.data["scene_id"] for e in batches) == sorted([house, room])  # OK (T1): each once


async def test_t2_two_editors_on_one_page_keep_their_snapshots(hass, setup, hass_ws_client, resident_token):
    """Each card sends its own edit key, so two cards on one page keep their own snapshot."""
    on = async_mock_service(hass, "light", "turn_on")
    for service in ("set_cover_position", "set_cover_tilt_position"):
        async_mock_service(hass, "cover", service)
    page = await _ws(hass, hass_ws_client, resident_token)  # one browser tab, two cards in edit mode
    assert (await page(type=f"{DOMAIN}/preview", step=LIGHT_SET, edit="a"))["success"]  # editor of the first card
    blind = {"entity_id": "cover.kitchen", "mode": "set", "values": {"position": 20}}
    assert (await page(type=f"{DOMAIN}/preview", step=blind, edit="b"))["success"]  # editor of the second card
    assert (await page(type=f"{DOMAIN}/preview_end", restore=False, edit="b"))["success"]  # the second card saves
    hass.states.async_set("light.kitchen", "on", {"brightness": 10, "color_mode": "brightness"})
    calls = len(on)
    assert (await page(type=f"{DOMAIN}/preview_end", restore=True, edit="a"))["success"]  # the first card cancels
    assert len(on) > calls  # OK (T2): the light of the first card goes back


async def test_note_cancel_after_a_reload_of_the_integration(hass, setup, hass_ws_client, resident_token):
    """The snapshot lives in the store of the old setup; the cancel of the card no longer finds it."""
    on = async_mock_service(hass, "light", "turn_on")
    page = await _ws(hass, hass_ws_client, resident_token)
    assert (await page(type=f"{DOMAIN}/preview", step=LIGHT_SET))["success"]
    hass.states.async_set("light.kitchen", "on", {"brightness": 10, "color_mode": "brightness"})
    await hass.config_entries.async_reload(setup.entry_id)  # "Neu laden" in the settings while somebody edits
    await hass.async_block_till_done()
    calls = len(on)
    assert (await page(type=f"{DOMAIN}/preview_end", restore=True))["success"]  # cancel in the card
    assert len(on) == calls  # NOTE (small): nothing is restored, the light stays at the preview value


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
    assert store.scenes[first]["steps"][0]["attributes"]["brightness"] == 77
    assert store.scenes[second]["steps"][0]["state"] == "on"  # NOTE: "Dark" now switches the light on


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
