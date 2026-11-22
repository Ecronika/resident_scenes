"""Review of version 0.3.5 (commit 70c15dc).

Every test passes against 0.3.5. Lines marked FINDING show a defect, NOTE a limit or a difference
to functional spec draft 0.13, OK a point that holds. Drop the file into tests/ to run it.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_CHANGED
from tests.conftest import save, ws


def cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


async def test_an_input_without_change_still_switches_with_live_adjustments(
    hass, setup, hass_ws_client, resident_token
):
    """AA4 and spec 5.4: with live adjustments on, every input switches the device, also one that stores nothing new."""
    hass.states.async_set("light.kitchen", "on", {"supported_color_modes": ["brightness"], "brightness": 200})
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Evening", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, "a", step_type="group", domain="light")))["result"]["step_id"]
    entry = {"step_id": step_id, "entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 102}}
    assert (await call(**cmd("set_entry", sid, "a", **entry)))["success"]
    await hass.async_block_till_done()
    store = setup.runtime_data
    version = store.scenes[sid]["version"]
    changes = async_capture_events(hass, EVENT_CHANGED)
    on = async_mock_service(hass, "light", "turn_on")
    # a later visit with live adjustments: the stored 40 % again, while the light stands at 78 %
    assert (await call(**cmd("set_entry", sid, "b", **entry, live=True)))["success"]
    await hass.async_block_till_done()
    assert store.scenes[sid]["version"] == version and not changes  # OK: no edit, no logbook entry
    assert on[0].data["brightness"] == 102  # OK: the light follows the input


async def test_an_input_without_change_does_not_end_the_creating_edit(hass, setup, hass_ws_client, resident_token):
    """AA4 with Z1 and spec 4.3: an input that changes nothing is no edit, so it cannot end the creating edit."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    # a second editor of the same account confirms the name as it is, then the first one renames
    assert (await call(**cmd("update", sid, "d", name="Neue Szene 1")))["success"]
    assert (await call(**cmd("update", sid, "c", name="Abend")))["success"]
    await hass.async_block_till_done()
    registry_id = hass.states.async_entity_ids("scene")
    assert registry_id == ["scene.abend"]  # OK: the id still follows the name
