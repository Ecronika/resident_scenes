"""Review of version 0.3.4 (commit fcc87d9), turned to the fixed behaviour of 0.3.5.

Lines marked FIXED were FINDING or NOTE in the review, OK a point that holds.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_CHANGED
from tests.conftest import eid, flat, run_scene, save, ws

WHITE_MODE = {"supported_color_modes": ["hs", "white"], "color_mode": "white", "brightness": 200}


def cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


async def test_white_mode_of_a_light_that_is_not_ticked(hass, setup, hass_ws_client, resident_token):
    """Z2: a light on in its white mode, not yet in the scene. A new brightness stores the mode, the run replays it."""
    hass.states.async_set("light.kitchen", "on", WHITE_MODE)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Evening", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light")))["result"]["step_id"]
    entry = {"step_id": step_id, "entity_id": "light.kitchen"}
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"brightness": 102})))["success"]
    assert flat(setup.runtime_data.scenes[sid])[0]["attributes"] == {"brightness": 102, "color_mode": "white"}  # OK
    hass.states.async_set("light.kitchen", "off", {"supported_color_modes": ["hs", "white"]})
    on = async_mock_service(hass, "light", "turn_on")
    await run_scene(hass, eid(hass, sid))
    assert on[0].data["white"] == 102 and "hs_color" not in on[0].data  # OK: replayed as white at 40 %


async def test_entity_id_follows_for_ten_minutes_only(hass, setup, hass_ws_client, resident_token, freezer):
    """Z1, spec 4.3 and 4.5: inside the creating edit the id follows every rename, after ten idle minutes it stays."""
    changes = async_capture_events(hass, EVENT_CHANGED)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    freezer.tick(9 * 60)
    assert (await call(**cmd("update", sid, "c", name="Abend")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.abend"  # OK: nine minutes are inside the edit
    freezer.tick(11 * 60)
    assert (await call(**cmd("update", sid, "c", name="Abend im Garten")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.abend"  # OK: the editor stayed open, the edit was over
    logged = [(c.data["action"], c.data["entity_id"]) for c in changes]
    assert logged == [("created", "scene.neue_szene_1"), ("changed", "scene.abend")]
    # NOTE: "created" stays under an entity id that no longer exists (README); the logbook of scene.abend starts
    # with "scene changed". This is the state of 0.3.2 (Y7), now chosen and documented.
    assert hass.states.get("scene.neue_szene_1") is None


async def test_aa4_an_input_that_changes_nothing_begins_no_edit(hass, setup, hass_ws_client, resident_token):
    """Spec 4.5: undo restores the state before the last edit. An input with the stored value begins no edit."""
    changes = async_capture_events(hass, EVENT_CHANGED)
    hass.states.async_set("light.kitchen", "on", {"supported_color_modes": ["brightness"], "brightness": 200})
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Evening", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, "a", step_type="group", domain="light")))["result"]["step_id"]
    entry = {"step_id": step_id, "entity_id": "light.kitchen", "mode": "set"}
    assert (await call(**cmd("set_entry", sid, "a", **entry, values={"brightness": 102})))["success"]
    assert (await call(**cmd("set_entry", sid, "b", **entry, values={"brightness": 51})))["success"]  # a second edit
    store = setup.runtime_data
    version = store.scenes[sid]["version"]
    assert flat(store.scenes[sid]["previous"])[0]["attributes"]["brightness"] == 102  # undo would lead back to 40 %
    # a third visit: the stored value comes again (the card does not send it, see the card probe)
    assert (await call(**cmd("set_entry", sid, "c", **entry, values={"brightness": 51})))["success"]
    await hass.async_block_till_done()
    assert store.scenes[sid]["version"] == version  # FIXED: no new version
    # FIXED: the way back to 40 % stays
    assert flat(store.scenes[sid]["previous"])[0]["attributes"]["brightness"] == 102
    logged = len(changes)
    assert (await call(**cmd("set_entry", sid, "d", **entry, values={"brightness": 51})))["success"]
    await hass.async_block_till_done()
    assert len(changes) == logged  # FIXED: and the logbook names no change
