"""Review of version 0.3.1 (commit e0e8fe1), adopted for 0.3.2.

Lines marked FIXED were a FINDING or NOTE against 0.3.1 and assert the fixed behaviour, OK a point that holds.
"""

from __future__ import annotations

import asyncio

from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes import store as store_module
from custom_components.resident_scenes.const import DOMAIN, EVENT_CHANGED, STORAGE_KEY
from homeassistant.helpers import area_registry as ar, entity_registry as er
from tests.conftest import eid, flat, save, ws

LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}


def cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


def group(scene: dict, domain: str, area_id: str | None = "kitchen") -> dict:
    return next(
        s for s in scene["sequence"] if s["type"] == "group" and (s["domain"], s["area_id"]) == (domain, area_id)
    )


def loose_light(hass) -> str:
    """A released light without a room."""
    reg = er.async_get(hass)
    ent = reg.async_get_or_create("light", "test", "loose", suggested_object_id="loose")
    reg.async_update_entity(ent.entity_id, labels={"resident_scenes"})
    hass.states.async_set(ent.entity_id, "on", {"brightness": 50, "color_mode": "brightness"})
    return ent.entity_id


# ---------- new with the steps without a room ----------


async def test_x1_all_off_in_the_house_skips_devices_without_a_room(hass, setup, hass_ws_client, resident_token):
    """Spec 4.5 "Alle im Haus aus" and acceptance "Aus-Szene": a released light without a room goes off too."""
    loose = loose_light(hass)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Away")
    assert (await call(**cmd("house_off", sid, domain="light")))["success"]
    scene = setup.runtime_data.scenes[sid]
    assert {s["area_id"] for s in scene["sequence"]} == {"kitchen", "hall", None}  # FIXED: a step "Ohne Raum"
    entry = next(e for e in flat(scene) if e["entity_id"] == loose)
    assert entry["state"] == "off"  # FIXED
    assert len(group(scene, "light", None)["entries"]) == 1
    # again: the first step without a room is set, no second one
    assert (await call(**cmd("house_off", sid, domain="light")))["success"]
    assert len(setup.runtime_data.scenes[sid]["sequence"]) == 3
    # by hand it works as well: "Alle aus" in the step without a room takes the devices without a room only
    step_id = group(setup.runtime_data.scenes[sid], "light", None)["id"]
    assert (await call(**cmd("set_all", sid, step_id=step_id, mode="off")))["success"]
    assert len(group(setup.runtime_data.scenes[sid], "light", None)["entries"]) == 1  # OK


async def test_x10_step_without_room_takes_any_device_on_the_server(hass, setup, hass_ws_client, resident_token):
    """Draft 0.9, 4.2: a step "Ohne Raum" takes devices without a room only."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Home")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light", area_id=None)))["result"]["step_id"]
    res = await call(**cmd("set_entry", sid, step_id=step_id, **LIGHT_SET))
    assert res["error"]["code"] == "entity_not_allowed"  # FIXED: light.kitchen has a room
    assert setup.runtime_data.scenes[sid]["sequence"][0]["entries"] == []


async def test_x3_devices_of_a_deleted_room_get_a_room_again(hass, setup, hass_ws_client, resident_token):
    """The installer deletes a room and puts its devices into another one (draft 0.9, 4.5 "Gerät verschoben")."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    on = async_mock_service(hass, "light", "turn_on")
    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity("light.kitchen", area_id="hall")  # the light now belongs to the hall
    await hass.async_block_till_done()
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]["sequence"][0]
    assert shown["area_id"] is None
    assert shown["entries"][0]["issue"] == "other_area"  # FIXED: the server sees the reason
    devices = (await call(type=f"{DOMAIN}/devices"))["result"]["entities"]
    assert next(d for d in devices if d["entity_id"] == "light.kitchen")["area_id"] == "hall"
    # the card shows the entry with "In anderem Raum" (card probe); the server refuses a new value
    res = await call(**cmd("set_entry", sid, step_id=shown["id"], entity_id="light.kitchen", mode="set",
                           values={"brightness": 77}))
    assert res["error"]["code"] == "entity_not_allowed"  # FIXED
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert on[-1].data["brightness"] == 10  # OK: the scene runs with the stored value


async def test_room_deleted_while_stopped(hass, hass_storage, setup):
    """Spec 4.5: an area deleted while Home Assistant was stopped. Fixed W1 also for steps of other scenes."""
    common = {"image": None, "kind": "resident", "content_released": False, "transition": None, "version": 4,
              "changed_by": None, "changed_at": None, "previous": None, "entity_named": True}
    entry = {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 10}}
    await hass.config_entries.async_unload(setup.entry_id)
    hass_storage[STORAGE_KEY] = {  # written by 0.3.0: format 3, no "edits"
        "version": 3, "minor_version": 1, "key": STORAGE_KEY,
        "data": {"scenes": {
            "r": {**common, "id": "r", "name": "Gone", "area_id": "cellar",
                  "sequence": [{"id": "s1", "type": "group", "domain": "light", "area_id": "cellar", "entries": []}]},
            "h": {**common, "id": "h", "name": "Home", "area_id": None,
                  "sequence": [{"id": "s1", "type": "group", "domain": "light", "area_id": "cellar",
                                "entries": [entry]}]},
        }, "favorites": {}},
    }
    assert await hass.config_entries.async_setup(setup.entry_id)
    await hass.async_block_till_done()
    scenes = setup.runtime_data.scenes
    assert scenes["r"]["area_id"] is None and scenes["r"]["sequence"][0]["area_id"] is None  # OK
    assert scenes["h"]["sequence"][0]["area_id"] is None and scenes["h"]["version"] == 5  # OK: also in a house scene


# ---------- the edit (W3, W5) ----------


async def test_edit_of_a_scene_stored_by_0_3_0(hass, hass_storage, setup, hass_ws_client, resident_token):
    """A scene without stored edits: the first input begins an edit, the edit ids do not reach the card."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    del setup.runtime_data.scenes[sid]["edits"]  # as loaded from a store of 0.3.0
    events = async_capture_events(hass, EVENT_CHANGED)
    assert (await call(**cmd("update", sid, "e9", transition=2)))["success"]
    await hass.async_block_till_done()
    assert [e.data["action"] for e in events] == ["changed"]  # OK
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]
    listed = (await call(type=f"{DOMAIN}/list", scope="kitchen"))["result"]["scenes"][0]
    # OK: account ids stay on the server
    assert "edits" not in shown and "edits" not in listed and "previous" not in shown


async def test_idle_counts_from_the_last_input(hass, setup, hass_ws_client, resident_token, freezer):
    """Draft 0.9, 4.5: an edit ends after ten minutes without input."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET], edit="create")
    events = async_capture_events(hass, EVENT_CHANGED)
    for value in (1, 2, 3):  # an input every nine minutes
        assert (await call(**cmd("update", sid, "e1", transition=value)))["success"]
        freezer.tick(9 * 60)
    await hass.async_block_till_done()
    assert len(events) == 1 and setup.runtime_data.scenes[sid]["previous"]["transition"] is None  # OK: one edit
    freezer.tick(2 * 60)  # eleven minutes after the last input
    assert (await call(**cmd("update", sid, "e1", transition=4)))["success"]
    await hass.async_block_till_done()
    assert len(events) == 2 and setup.runtime_data.scenes[sid]["previous"]["transition"] == 3  # OK: a new edit


async def test_x9_undo_from_a_second_card_leaves_the_edit_open(hass, setup, hass_ws_client, resident_token):
    """One card edits, a second card takes the edit back, the first goes on: its next input begins a new edit."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET], edit="create")
    store = setup.runtime_data
    events = async_capture_events(hass, EVENT_CHANGED)
    assert (await call(**cmd("update", sid, "e1", transition=5)))["success"]
    res = await call(type=f"{DOMAIN}/undo", scene_id=sid, version=store.scenes[sid]["version"])
    assert res["success"] and store.scenes[sid]["transition"] is None
    assert store.scenes[sid]["edits"] == []
    assert (await call(**cmd("update", sid, "e1", transition=7)))["success"]  # the open editor goes on
    await hass.async_block_till_done()
    # FIXED: the input after the undo is logged ...
    assert [e.data["action"] for e in events] == ["changed", "change taken back", "changed"]
    assert store.scenes[sid]["previous"]["transition"] is None  # ... and can be taken back
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]
    assert shown["transition"] == 7 and shown["can_undo"] is True


# ---------- draft 0.9 ----------


async def test_entity_id_still_follows_a_late_first_rename(hass, setup, hass_ws_client, resident_token, freezer):
    """Draft 0.9, 4.3: the entity id follows the name only in the edit that created the scene."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="create"))["result"]["scene_id"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.neue_szene_1"
    freezer.tick(24 * 3600)  # the next day, another edit
    assert (await call(**cmd("update", sid, "later", name="Abend")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.neue_szene_1"  # FIXED: an automation using scene.neue_szene_1 keeps its target


async def test_entity_id_follows_every_rename_in_the_creating_edit(hass, setup, hass_ws_client, resident_token):
    """Draft 0.9, 4.3: in the creating edit the entity id follows each rename, then stays."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    for name, expected in (("Abend", "scene.abend"), ("Nacht", "scene.nacht"), ("nacht", "scene.nacht")):
        assert (await call(**cmd("update", sid, "c", name=name)))["success"]
        await hass.async_block_till_done()
        assert eid(hass, sid) == expected
    assert (await call(**cmd("update", sid, "next", name="Morgen")))["success"]  # "Fertig", then a new edit
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.nacht"


# ---------- points that hold ----------


async def test_w6_every_input_is_on_disk_within_the_delay(hass, setup, hass_ws_client, resident_token, hass_storage,
                                                          monkeypatch):
    """Fixed W6, measured: no input waits longer for the disk than the delay, also while inputs go on."""
    monkeypatch.setattr(store_module, "SAVE_DELAY", 0.3)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="New", edit="x"))["result"]["scene_id"]
    await asyncio.sleep(0.5)  # the save of the generated entity id

    def on_disk() -> int:
        return hass_storage[STORAGE_KEY]["data"]["scenes"][sid]["transition"] or 0

    loop, sent, worst = hass.loop, {}, 0.0
    for value in range(1, 16):  # an input every 0.1 s for 1.5 s
        assert (await call(**cmd("update", sid, transition=value)))["success"]
        sent[value] = loop.time()
        await asyncio.sleep(0.1)
        for done in [v for v in sent if v <= on_disk()]:
            worst = max(worst, loop.time() - sent.pop(done))
    await asyncio.sleep(0.5)
    assert on_disk() == 15 and worst < 0.55  # OK: 0.3 s delay plus the 0.1 s between two looks
    # the window starts again with the next input
    assert (await call(**cmd("update", sid, transition=20)))["success"]
    await asyncio.sleep(0.2)
    assert on_disk() == 15
    await asyncio.sleep(0.3)
    assert on_disk() == 20  # OK


async def test_delay_in_whole_seconds(hass, setup, hass_ws_client, resident_token):
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, step_type="delay")))["result"]["step_id"]
    assert (await call(**cmd("set_delay", sid, step_id=step_id, seconds=3.0)))["success"]
    stored = setup.runtime_data.scenes[sid]["sequence"][0]["seconds"]
    assert stored == 3 and isinstance(stored, int)  # OK
    for bad in (2.5, 0, 0.4, 601, -1):
        assert (await call(**cmd("set_delay", sid, step_id=step_id, seconds=bad)))["error"]["code"] == "invalid_delay"


async def test_capture_with_a_step_without_a_room(hass, setup, hass_ws_client, resident_token):
    """resident_scenes.capture takes over the state of a device in a step without a room."""
    loose = loose_light(hass)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Home")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light", area_id=None)))["result"]["step_id"]
    assert (await call(**cmd("set_entry", sid, step_id=step_id, entity_id=loose, mode="off")))["success"]
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": eid(hass, sid)}, blocking=True)
    entry = flat(setup.runtime_data.scenes[sid])[0]
    assert entry["state"] == "on" and entry["attributes"]["brightness"] == 50  # OK


# ---------- the colour of a light ----------

# A light as Home Assistant reports it: every form of the colour side by side, color_mode names the one that counts.
BLUE = {
    "brightness": 128, "supported_color_modes": ["color_temp", "rgb"],
    "min_color_temp_kelvin": 2000, "max_color_temp_kelvin": 6500, "color_temp_kelvin": None,
    "hs_color": (240.0, 100.0), "rgb_color": (0, 0, 255), "xy_color": (0.136, 0.04),
    "rgbw_color": (0, 0, 255, 0), "rgbww_color": (0, 0, 255, 0, 0),
}


async def test_x11_a_captured_colour_is_lost_in_the_editor(hass, setup, hass_ws_client, resident_token):
    """Spec 4.5 draft 0.10 "Farbe bleibt": the card gets hue and saturation, an input keeps the stored colour."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Blue", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light")))["result"]["step_id"]
    entry = {"step_id": step_id, "entity_id": "light.kitchen"}

    async def sent() -> dict:
        """The entry as the card gets it."""
        return (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]["sequence"][0]["entries"][0]["attributes"]

    for mode, attr in (("rgb", "rgb_color"), ("xy", "xy_color"), ("rgbw", "rgbw_color"), ("rgbww", "rgbww_color")):
        hass.states.async_set("light.kitchen", "on", {**BLUE, "color_mode": mode})
        assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
        shown = await sent()
        assert set(shown) == {"brightness", "color_mode", attr, "hs_color"}  # FIXED: hue and saturation for the card
        assert round(shown["hs_color"][0]) in range(230, 250) and shown["hs_color"][1] > 90
        assert set(flat(setup.runtime_data.scenes[sid])[0]["attributes"]) == {"brightness", "color_mode", attr}
    hass.states.async_set("light.kitchen", "on", {**BLUE, "color_mode": "hs"})
    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    assert (await sent())["hs_color"] == [240.0, 100.0]  # OK

    # the run is right: the stored form goes to the light as it is
    hass.states.async_set("light.kitchen", "on", {**BLUE, "color_mode": "rgb"})
    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    hass.states.async_set("light.kitchen", "off", {"supported_color_modes": ["color_temp", "rgb"]})
    on = async_mock_service(hass, "light", "turn_on")
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert on[0].data["rgb_color"] == (0, 0, 255) and on[0].data["brightness"] == 128  # OK

    # what the card sends when the brightness of this entry is moved (card_probe X11): the blue stays
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"brightness": 26})))["success"]
    assert await sent() == {"brightness": 26, "color_mode": "rgb", "rgb_color": [0, 0, 255],
                            "hs_color": [240.0, 100.0]}  # FIXED
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert on[-1].data["rgb_color"] == (0, 0, 255) and on[-1].data["brightness"] == 26  # FIXED: the same blue
    # white channels stay too; only the change between white and colour replaces the colour
    hass.states.async_set("light.kitchen", "on", {**BLUE, "color_mode": "rgbww", "rgbww_color": (0, 0, 255, 40, 0)})
    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"brightness": 50})))["success"]
    assert (await sent())["rgbww_color"] == [0, 0, 255, 40, 0]
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"color_temp_kelvin": 3000})))["success"]
    assert await sent() == {"brightness": 50, "color_mode": "color_temp", "color_temp_kelvin": 3000}


async def test_x11_an_unticked_light_keeps_its_current_colour(hass, setup, hass_ws_client, resident_token):
    """An input on an unticked light ticks it with its current state and the changed value (spec 4.5)."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Blue", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light")))["result"]["step_id"]
    hass.states.async_set("light.kitchen", "on", {**BLUE, "color_mode": "xy"})
    values = {"brightness": 200}
    assert (await call(**cmd("set_entry", sid, step_id=step_id, entity_id="light.kitchen", mode="set", values=values)))[
        "success"
    ]
    stored = flat(setup.runtime_data.scenes[sid])[0]["attributes"]
    assert stored == {"brightness": 200, "color_mode": "xy", "xy_color": (0.136, 0.04)}
