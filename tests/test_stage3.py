"""Tests for stage 3: sequence format, migration, inputs per edit, live adjustments, review U1 and U2."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import io

from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.resident_scenes.const import CONF_IMAGE_COUNT, DOMAIN, EVENT_BATCH, EVENT_CHANGED, STORAGE_KEY
from custom_components.resident_scenes.model import ValidationError
from custom_components.resident_scenes.store import upload_dir
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import Context
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from tests.conftest import direct, eid, flat, run_scene, save, ws

LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}


async def later(hass, seconds: float) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done(wait_background_tasks=True)


def _cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


@pytest.fixture
async def v2_data(hass, hass_storage):
    """Storage of 0.2.x: a room scene and a house scene with a delay, a call and a device without room."""
    ent = er.async_get(hass).async_get_or_create("light", "test", "loose", suggested_object_id="loose")
    er.async_get(hass).async_update_entity(ent.entity_id, labels={"resident_scenes"})
    common = {"image": None, "kind": "resident", "content_released": False, "transition": None, "version": 1,
              "changed_by": None, "changed_at": None}
    hass_storage[STORAGE_KEY] = {
        "version": 2,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {
            "scenes": {
                "r": {**common, "id": "r", "name": "Cook", "area_id": "kitchen", "previous": None,
                      "steps": [{"entity_id": "media_player.kitchen", "music": "off"}]},
                "h": {
                    **common, "id": "h", "name": "Home", "area_id": None,
                    "previous": {"name": "Old", "area_id": None, "image": None, "transition": None,
                                 "steps": [{"entity_id": "light.hall", "state": "on", "attributes": {}}]},
                    "steps": [
                        {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 10}},
                        {"entity_id": "light.hall", "state": "off", "attributes": {}},
                        {"entity_id": "cover.kitchen", "state": "closed", "attributes": {}},
                        {"scene_id": "r", "name": "Cook"},
                        {"entity_id": "climate.kitchen", "state": "off", "attributes": {}, "delay": 5},
                        {"entity_id": "light.loose", "state": "off", "attributes": {}},
                    ],
                },
            },
            "favorites": {},
        },
    }


async def test_migration_keeps_the_behaviour(hass, v2_data, setup, hass_storage):
    """2 -> 3: delay steps, groups per (area, domain) in order of first appearance, calls become scene steps."""
    store = setup.runtime_data
    house = store.scenes["h"]
    shape = [(s["type"], s.get("domain"), s.get("area_id"), s.get("seconds")) for s in house["sequence"]]
    assert shape == [
        ("group", "light", "kitchen", None),
        ("group", "light", "hall", None),
        ("group", "cover", "kitchen", None),
        ("scene", None, "kitchen", None),
        ("delay", None, None, 5),
        ("group", "climate", "kitchen", None),
        ("group", "light", None, None),  # a device without room
    ]
    assert len({s["id"] for s in house["sequence"]}) == 7
    assert house["entity_named"] is True
    assert flat(house)[0] == {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 10}}
    assert house["previous"]["sequence"][0]["entries"] == [{"entity_id": "light.hall", "state": "on", "attributes": {}}]
    assert store.scenes["r"]["sequence"][0]["area_id"] == "kitchen"
    await store.async_write()
    assert hass_storage[STORAGE_KEY]["version"] == 3

    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    close = async_mock_service(hass, "cover", "close_cover")
    stop = async_mock_service(hass, "media_player", "media_stop")
    climate = async_mock_service(hass, "climate", "set_hvac_mode")
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, "h")}, blocking=True)
    await hass.async_block_till_done()
    assert on[0].data["brightness"] == 10 and off[0].data["entity_id"] == "light.hall"
    assert close and stop  # the called room scene ran
    assert not climate
    await later(hass, 6)
    assert climate[0].data["hvac_mode"] == "off"


async def test_same_entity_in_two_steps(hass, setup, hass_ws_client, resident_token):
    """Light on, 5 s, light off runs so; inside one batch the lower entry wins."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Blink", area_id="kitchen",
                     steps=[LIGHT_SET, {"entity_id": "light.kitchen", "mode": "off", "delay": 5}])
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done()
    assert len(on) == 1 and not off
    await later(hass, 6)
    assert len(off) == 1

    both = await save(call, name="Both", area_id="kitchen")
    for mode in ("set", "off"):
        res = await call(**_cmd("add_step", both, step_type="group", domain="light"))
        step_id = res["result"]["step_id"]
        assert (await call(**_cmd("set_entry", both, step_id=step_id, **{**LIGHT_SET, "mode": mode})))["success"]
    await run_scene(hass, eid(hass, both))
    assert len(on) == 1 and len(off) == 2  # only the lower entry ran


async def test_edits_and_undo(hass, setup, hass_ws_client, resident_token):
    """One logbook entry per edit; undo takes back the latest edit; the creating edit has nothing to undo."""
    call = await ws(hass, hass_ws_client, resident_token)
    changes = async_capture_events(hass, EVENT_CHANGED)
    res = await call(type=f"{DOMAIN}/create", area_id="kitchen", name="New", edit="a")
    sid = res["result"]["scene_id"]
    assert (await call(**_cmd("update", sid, "a", name="Cook")))["success"]
    store = setup.runtime_data
    assert store.scenes[sid]["previous"] is None
    version = store.scenes[sid]["version"]
    assert (await call(type=f"{DOMAIN}/undo", scene_id=sid, version=version))["error"]["code"] == "nothing_to_undo"

    assert (await call(**_cmd("update", sid, "b", transition=3)))["success"]
    assert (await call(**_cmd("add_step", sid, "b", step_type="delay")))["success"]
    assert (await call(**_cmd("set_delay", sid, "b", step_id=store.scenes[sid]["sequence"][0]["id"], seconds=7)))[
        "success"
    ]
    await hass.async_block_till_done()
    assert [c.data["action"] for c in changes] == ["created", "changed"]
    listing = (await call(type=f"{DOMAIN}/list", scope="kitchen"))["result"]
    assert listing["scenes"][0]["can_undo"] is True
    version = store.scenes[sid]["version"]
    assert (await call(type=f"{DOMAIN}/undo", scene_id=sid, version=version))["success"]
    assert (store.scenes[sid]["transition"], store.scenes[sid]["sequence"], store.scenes[sid]["name"]) == (
        None, [], "Cook"
    )
    # undo ends the edit: the next input of the open editor begins a new one, logged and undoable (review X9)
    assert (await call(**_cmd("update", sid, "b", transition=1)))["success"]
    await hass.async_block_till_done()
    assert [c.data["action"] for c in changes] == ["created", "changed", "change taken back", "changed"]
    assert store.scenes[sid]["previous"]["transition"] is None


async def test_create_and_duplicate(hass, setup, hass_ws_client, resident_token):
    """New scenes are numbered; a copy gets new step ids and a free name with the suffix."""
    call = await ws(hass, hass_ws_client, resident_token)
    store = setup.runtime_data
    names = []
    for _ in range(2):
        res = await call(type=f"{DOMAIN}/create", area_id="kitchen", name="Neue Szene", edit="x")
        names.append(store.scenes[res["result"]["scene_id"]]["name"])
    assert names == ["Neue Szene 1", "Neue Szene 2"]
    res = await call(type=f"{DOMAIN}/create", area_id="kitchen", name=" ", edit="x")
    assert res["error"]["code"] == "invalid_name"
    res = await call(type=f"{DOMAIN}/create", area_id="nowhere", name="A", edit="x")
    assert res["error"]["code"] == "invalid_area"

    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET, {**LIGHT_SET, "delay": 2}])
    copies = []
    for _ in range(2):
        res = await call(type=f"{DOMAIN}/duplicate", scene_id=sid, suffix=" (copy)", edit="y")
        assert res["success"], res
        copies.append(store.scenes[res["result"]["scene_id"]])
    assert [c["name"] for c in copies] == ["Cook (copy)", "Cook (copy) (2)"]
    source = store.scenes[sid]
    assert [s["type"] for s in copies[0]["sequence"]] == [s["type"] for s in source["sequence"]]
    assert not {s["id"] for s in copies[0]["sequence"]} & {s["id"] for s in source["sequence"]}
    assert flat(copies[0]) == flat(source)
    assert copies[0]["previous"] is None and copies[0]["entity_named"] is False
    res = await call(type=f"{DOMAIN}/duplicate", scene_id="nope", suffix=" (copy)", edit="y")
    assert res["error"]["code"] == "not_found"


async def test_step_commands(hass, setup, hass_ws_client, resident_token, hass_access_token):
    """add_step, set_delay, move_step, remove_step, remove_entry and update with their errors."""
    call = await ws(hass, hass_ws_client, resident_token)
    store = setup.runtime_data
    sid = await save(call, name="Home")
    seq = lambda: store.scenes[sid]["sequence"]  # noqa: E731
    first = (await call(**_cmd("add_step", sid, step_type="group", domain="light", area_id="kitchen")))["result"]
    delay = (await call(**_cmd("add_step", sid, step_type="delay", index=0)))["result"]["step_id"]
    assert [s["type"] for s in seq()] == ["delay", "group"] and seq()[0]["seconds"] == 5
    for fields, code in (
        ({"step_type": "group", "domain": "light", "area_id": "nowhere"}, "invalid_area"),
        ({"step_type": "group", "area_id": "kitchen"}, "invalid_step"),
        ({"step_type": "scene", "target": "nope"}, "invalid_scene_call"),
    ):
        assert (await call(**_cmd("add_step", sid, **fields)))["error"]["code"] == code
    assert (await call(**_cmd("set_delay", sid, step_id=delay, seconds=0)))["error"]["code"] == "invalid_delay"
    assert (await call(**_cmd("set_delay", sid, step_id=delay, seconds=601)))["error"]["code"] == "invalid_delay"
    res = await call(**_cmd("set_delay", sid, step_id=first["step_id"], seconds=3))
    assert res["error"]["code"] == "invalid_step"
    assert (await call(**_cmd("set_delay", sid, step_id=delay, seconds=2.5)))["error"]["code"] == "invalid_delay"
    assert (await call(**_cmd("move_step", sid, step_id=delay, index=99)))["success"]
    assert [s["type"] for s in seq()] == ["group", "delay"]
    assert (await call(**_cmd("move_step", sid, step_id="gone", index=0)))["error"]["code"] == "step_missing"
    entry = {**LIGHT_SET, "step_id": first["step_id"]}
    assert (await call(**_cmd("set_entry", sid, **entry)))["success"]
    assert (await call(**_cmd("remove_entry", sid, step_id=first["step_id"], entity_id="light.kitchen")))["success"]
    assert seq()[0]["entries"] == []
    assert (await call(**_cmd("remove_step", sid, step_id=delay)))["success"]
    assert (await call(**_cmd("remove_step", sid, step_id=delay)))["error"]["code"] == "step_missing"
    assert (await call(**_cmd("update", sid, transition=99)))["error"]["code"] == "invalid_value"
    assert (await call(**_cmd("update", sid, kind="installer")))["error"]["code"] == "unauthorized"
    admin = await ws(hass, hass_ws_client, hass_access_token)
    res = await admin(**_cmd("update", sid, kind="installer", content_released=True))
    assert res["success"] and res["result"] == {"version": store.scenes[sid]["version"]}
    assert store.scenes[sid]["kind"] == "installer" and store.scenes[sid]["content_released"] is True


async def test_live_adjustment(hass, setup, hass_ws_client, resident_token):
    """A live entry applies to the device at once; climate and music are only stored."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", transition=2)
    store = setup.runtime_data
    light = (await call(**_cmd("add_step", sid, step_type="group", domain="light")))["result"]["step_id"]
    climate = (await call(**_cmd("add_step", sid, step_type="group", domain="climate")))["result"]["step_id"]
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    temperature = async_mock_service(hass, "climate", "set_temperature")
    assert (await call(**_cmd("set_entry", sid, step_id=light, live=True, **LIGHT_SET)))["success"]
    assert on[-1].data["brightness"] == 10 and on[-1].data["transition"] == 2
    values = {"temperature": 22}
    res = await call(**_cmd("set_entry", sid, step_id=climate, live=True, entity_id="climate.kitchen", mode="set",
                            values=values))
    assert res["success"] and not temperature
    assert (await call(**_cmd("set_all", sid, step_id=light, mode="off", live=True)))["success"]
    assert len(off) == 1
    assert flat(store.scenes[sid])[0]["state"] == "off"
    res = await call(**_cmd("set_entry", sid, step_id=climate, entity_id="light.kitchen", mode="off"))
    assert res["error"]["code"] == "entity_not_allowed"  # not the step's domain


async def test_set_all_keeps_flagged_and_unreachable(hass, setup, hass_ws_client, resident_token):
    """'Alle' takes the current state; unreachable devices and flagged entries keep their stored entry."""
    call = await ws(hass, hass_ws_client, resident_token)
    store = setup.runtime_data
    fav = {"entity_id": "media_player.sonos_kitchen", "mode": "music", "music": "favorite", "volume": 0.2,
           "favorite_id": "FV:2/2"}
    sid = await save(call, name="Mix", area_id="kitchen", steps=[LIGHT_SET, fav])
    light, music = (s["id"] for s in store.scenes[sid]["sequence"])
    hass.states.async_set("sensor.sonos_favorites", "1", {"items": {"FV:2/1": "Sport"}})  # News is gone
    hass.states.async_set("light.kitchen", "unavailable")
    store.scenes[sid]["sequence"][0]["entries"].append({"entity_id": "light.gone", "state": "on", "attributes": {}})
    assert (await call(**_cmd("set_all", sid, step_id=light, mode="capture")))["success"]
    assert store.scenes[sid]["sequence"][0]["entries"][0]["attributes"] == {"brightness": 10}
    assert store.scenes[sid]["sequence"][0]["entries"][1]["entity_id"] == "light.gone"
    hass.states.async_set("light.kitchen", "on", {"brightness": 77, "color_mode": "brightness"})
    assert (await call(**_cmd("set_all", sid, step_id=light, mode="capture")))["success"]
    assert store.scenes[sid]["sequence"][0]["entries"][0]["attributes"]["brightness"] == 77
    assert (await call(**_cmd("set_all", sid, step_id=music, mode="capture")))["success"]
    entries = {e["entity_id"]: e for e in store.scenes[sid]["sequence"][1]["entries"]}
    assert entries["media_player.sonos_kitchen"]["favorite_id"] == "FV:2/2"  # flagged: kept
    assert entries["media_player.kitchen"]["music"] == "on"  # added from the current state
    scenes = await call(**_cmd("add_step", sid, step_type="group", domain="scene"))
    res = await call(**_cmd("set_all", sid, step_id=scenes["result"]["step_id"], mode="off"))
    assert res["success"]  # no released scene in the kitchen: nothing to switch off


async def test_house_off(hass, setup, hass_ws_client, resident_token):
    """Per room with released devices the first step of the domain switches all off, or a new step is added."""
    call = await ws(hass, hass_ws_client, resident_token)
    store = setup.runtime_data
    sid = await save(call, name="Away", steps=[{"entity_id": "cover.kitchen", "mode": "off"}, LIGHT_SET])
    assert (await call(**_cmd("house_off", sid, domain="light")))["success"]
    shape = [(s["domain"], s["area_id"], [e["state"] for e in s["entries"]]) for s in store.scenes[sid]["sequence"]]
    assert shape == [("cover", "kitchen", ["closed"]), ("light", "kitchen", ["off"]), ("light", "hall", ["off"])]
    room = await save(call, name="Cook", area_id="kitchen")
    assert (await call(**_cmd("house_off", room, domain="light")))["error"]["code"] == "invalid_step"


async def test_u1_two_runs_of_one_automation(hass, setup, hass_ws_client, resident_token):
    """Two house scenes of one automation run call the same room scene, the first after a delay: it runs twice."""
    call = await ws(hass, hass_ws_client, resident_token)
    room = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    first = await save(call, name="Evening")
    await call(**_cmd("add_step", first, step_type="delay"))
    await call(**_cmd("add_step", first, step_type="scene", target=room, area_id="kitchen"))
    second = await save(call, name="Night", steps=[{"mode": "scene", "scene_id": room}])
    batches = async_capture_events(hass, EVENT_BATCH)
    async_mock_service(hass, "light", "turn_on")
    context = Context()  # one automation run
    for sid in (first, second):
        run = {"entity_id": eid(hass, sid)}
        await hass.services.async_call("scene", "turn_on", run, blocking=True, context=context)
    await hass.async_block_till_done()
    assert [e.data["scene_id"] for e in batches].count(room) == 1
    await later(hass, 6)
    # FIXED (U1): not skipped as "already runs for this trigger"
    assert [e.data["scene_id"] for e in batches].count(room) == 2


async def test_u2_parallel_uploads_keep_the_limit(hass, setup, hass_client):
    hass.config_entries.async_update_entry(setup, options={**setup.options, CONF_IMAGE_COUNT: 1})
    folder = upload_dir(hass)

    def clear() -> None:
        if folder.is_dir():
            for path in folder.iterdir():
                path.unlink()

    out = io.BytesIO()
    Image.new("RGB", (64, 48)).save(out, "PNG")
    await hass.async_add_executor_job(clear)
    try:
        client = await hass_client()
        replies = await asyncio.gather(
            *(client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(out.getvalue())}) for _ in range(3))
        )
        assert sorted(r.status for r in replies) == [200, 400, 400]  # FIXED (U2)
    finally:
        await hass.async_add_executor_job(clear)


async def test_entity_id_after_the_first_rename(hass, setup, hass_ws_client, resident_token):
    """'New 1' gets scene.new_1; the first rename gives the id of the new name, unless it was changed by hand."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="New", edit="x"))["result"]["scene_id"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.new_1"
    assert (await call(**_cmd("update", sid, "x", name="Brunch")))["success"]  # in the creating edit (spec 4.3)
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.brunch"
    assert hass.states.get("scene.brunch").name == "Brunch"

    other = (await call(type=f"{DOMAIN}/create", area_id=None, name="New", edit="x"))["result"]["scene_id"]
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity(eid(hass, other), new_entity_id="scene.mine")
    await hass.async_block_till_done()
    assert (await call(**_cmd("update", other, "x", name="Lunch")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, other) == "scene.mine"  # changed by hand: left alone
    assert (await call(**_cmd("update", other, "y", name="Dinner")))["success"]  # a later edit ends the creating one
    assert eid(hass, other) == "scene.mine" and setup.runtime_data.scenes[other]["entity_named"] is True


async def test_delayed_save(hass, setup, hass_ws_client, resident_token, hass_storage):
    """Inputs are written after 10 s or when Home Assistant stops; creating writes at once."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="New", edit="x"))["result"]["scene_id"]

    def stored():
        return hass_storage[STORAGE_KEY]["data"]["scenes"][sid]["transition"]

    assert stored() is None
    await later(hass, 11)  # the save of the generated entity id (scene.py)
    assert (await call(**_cmd("update", sid, transition=3)))["success"]
    await hass.async_block_till_done()
    assert stored() is None
    await later(hass, 11)
    assert stored() == 3
    assert (await call(**_cmd("update", sid, transition=4)))["success"]
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()
    assert stored() == 4


async def test_capture_keeps_the_sequence(hass, setup, hass_ws_client, resident_token):
    """capture: the first entry of an entity is taken over, later entries, delays and order stay."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Blink", area_id="kitchen",
                     steps=[LIGHT_SET, {"entity_id": "light.kitchen", "mode": "off", "delay": 5}])
    hass.states.async_set("light.kitchen", "on", {"brightness": 99, "color_mode": "brightness"})
    changes = async_capture_events(hass, EVENT_CHANGED)
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done()
    scene = setup.runtime_data.scenes[sid]
    assert [s["type"] for s in scene["sequence"]] == ["group", "delay", "group"]
    assert [e["state"] for e in flat(scene)] == ["on", "off"]
    assert flat(scene)[0]["attributes"]["brightness"] == 99
    assert [c.data["action"] for c in changes] == ["captured"]
    assert scene["previous"]["sequence"][0]["entries"][0]["attributes"]["brightness"] == 10


async def test_template_in_format_3(hass, setup):
    """A template sequence goes through the builders of the editor; one bad step loads nothing."""
    store = setup.runtime_data
    good = {"key": "a", "name": "A", "area_id": "kitchen",
            "sequence": [{"type": "group", "domain": "light", "entries": [LIGHT_SET]}, {"type": "delay", "seconds": 3}]}
    bad = {**good, "key": "b", "name": "B", "sequence": [{"type": "bogus"}]}
    with pytest.raises(ValidationError):
        await store.async_import({"scenes": [good, bad]})
    assert "tpl_a" not in store.scenes
    assert await store.async_import({"scenes": [good]}) == 1
    scene = store.scenes["tpl_a"]
    assert [s["type"] for s in scene["sequence"]] == ["group", "delay"]
    assert flat(scene)[0]["attributes"]["brightness"] == 10
    house = {"key": "h", "name": "H", "sequence": [{"type": "scene", "scene_id": "tpl_a"}]}
    assert await store.async_import({"scenes": [house]}) == 1
    assert store.scenes["tpl_h"]["sequence"][0]["area_id"] == "kitchen"
    many = {"key": "m", "name": "M", "sequence": [{"type": "delay", "seconds": 1}] * 151}
    with pytest.raises(ValidationError, match="too_many_steps"):
        await store.async_import({"scenes": [many]})
    call = direct(store)
    assert (await call(**_cmd("update", "tpl_a", transition=1)))["success"]
