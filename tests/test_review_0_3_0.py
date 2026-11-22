"""Review of version 0.3.0 (commit 73251c4), turned into regression tests for 0.3.1.

Every test passes against 0.3.0. Lines marked FINDING show a defect, NOTE a limit that should be
known, OK a point of functional spec draft 0.8 that holds. Drop the file into tests/ to run it.
"""

from __future__ import annotations

import asyncio
import io

from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.resident_scenes import store as store_module
from custom_components.resident_scenes.const import (
    CONF_IMAGE_COUNT,
    CONF_STEPS_PER_SCENE,
    DOMAIN,
    EVENT_CHANGED,
    EVENT_SKIPPED,
    STORAGE_KEY,
)
from custom_components.resident_scenes.runner import batches
from custom_components.resident_scenes.store import upload_dir
from homeassistant.core import Context
from homeassistant.helpers import area_registry as ar, entity_registry as er
from tests.conftest import eid, flat, save, ws

LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}
BLIND = {"entity_id": "cover.kitchen", "mode": "off"}


def cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


def group(scene: dict, domain: str) -> dict:
    return next(s for s in scene["sequence"] if s["type"] == "group" and s["domain"] == domain)


# ---------- findings ----------


async def test_w1_deleted_room_freezes_its_scenes(hass, setup, hass_ws_client, resident_token):
    """Spec 7 "Raum gelöscht": the scenes stay runnable and changeable. The entries are not changeable any more."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    on = async_mock_service(hass, "light", "turn_on")
    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    store = setup.runtime_data
    scene = store.scenes[sid]
    assert scene["area_id"] is None  # OK (decision 7): now a house scene
    step = group(scene, "light")
    assert step["area_id"] is None  # fixed W1: a step without a room
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]["sequence"][0]
    assert shown["entries"][0]["issue"] is None
    res = await call(**cmd("set_entry", sid, step_id=step["id"], entity_id="light.kitchen", mode="set",
                           values={"brightness": 200}))
    assert res["success"]
    res = await call(**cmd("add_step", sid, step_type="group", domain="light", area_id=None))
    assert res["success"]
    res = await call(**cmd("set_entry", sid, step_id=step["id"], entity_id="light.kitchen", mode="set",
                           values={"brightness": 10}))
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert on[-1].data["brightness"] == 10  # OK: the scene still runs


async def test_w2_device_without_room_cannot_be_added(hass, setup, hass_ws_client, resident_token):
    """A released device without a room could be put into a house scene in 0.2.2. In 0.3.0 no step takes it."""
    reg = er.async_get(hass)
    loose = reg.async_get_or_create("light", "test", "loose", suggested_object_id="loose")
    reg.async_update_entity(loose.entity_id, labels={"resident_scenes"})
    hass.states.async_set("light.loose", "on", {"brightness": 50, "color_mode": "brightness"})
    call = await ws(hass, hass_ws_client, resident_token)
    devices = (await call(type=f"{DOMAIN}/devices"))["result"]["entities"]
    assert {"light.loose": None}.items() <= {d["entity_id"]: d["area_id"] for d in devices}.items()  # offered
    sid = await save(call, name="Home")
    res = await call(**cmd("add_step", sid, step_type="group", domain="light", area_id=None))
    step_id = res["result"]["step_id"]  # fixed W2: a step without a room
    res = await call(**cmd("set_entry", sid, step_id=step_id, entity_id="light.loose", mode="capture"))
    assert res["success"]
    room = await save(call, name="Cook", area_id="kitchen")
    res = await call(**cmd("add_step", room, step_type="group", domain="light", area_id=None))
    assert res["success"]  # in a room scene the step always gets the room
    assert group(setup.runtime_data.scenes[room], "light")["area_id"] == "kitchen"


async def test_w3_edit_id_is_not_bound_to_account_or_time(
    hass, setup, hass_ws_client, resident_token, hass_access_token, freezer
):
    """Spec 4.10: every edit is in the logbook once, with its account. An edit id is valid for anyone, for ever."""
    resident = await ws(hass, hass_ws_client, resident_token)
    admin = await ws(hass, hass_ws_client, hass_access_token)
    sid = await save(resident, name="Cook", area_id="kitchen", steps=[LIGHT_SET], edit="create")
    store = setup.runtime_data
    step = group(store.scenes[sid], "light")
    events = []
    hass.bus.async_listen(EVENT_CHANGED, events.append)
    entry = {"step_id": step["id"], "entity_id": "light.kitchen", "mode": "set"}
    assert (await resident(**cmd("set_entry", sid, "e1", **entry, values={"brightness": 20})))["success"]
    await hass.async_block_till_done()
    assert [e.data["action"] for e in events] == ["changed"]  # OK: the edit of the resident
    before = store.scenes[sid]["previous"]["sequence"][0]["entries"][0]["attributes"]["brightness"]
    assert before == 10
    # another account sends the same edit id
    assert (await admin(**cmd("set_entry", sid, "e1", **entry, values={"brightness": 99})))["success"]
    await hass.async_block_till_done()
    assert len(events) == 2  # fixed W3: the second account begins its own edit
    # an editor left open on a wall panel: the same edit id a week later
    freezer.tick(7 * 24 * 3600)
    assert (await resident(**cmd("set_entry", sid, "e1", **entry, values={"brightness": 30})))["success"]
    await hass.async_block_till_done()
    assert len(events) == 3  # a new edit
    undo = store.scenes[sid]["previous"]["sequence"][0]["entries"][0]["attributes"]["brightness"]
    assert undo == 99  # undo goes back to the state before this edit


async def test_w4_image_change_swallows_an_input_made_meanwhile(hass, setup, hass_ws_client, resident_token):
    """SECURITY.md: inputs change a scene without awaiting in between. The image check awaits before the copy."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[{**LIGHT_SET, "delay": 5}])
    store = setup.runtime_data
    delay = next(s for s in store.scenes[sid]["sequence"] if s["type"] == "delay")
    gate = asyncio.Event()

    async def slow_check(image: str) -> bool:  # the real check reads the disk in the executor
        await gate.wait()
        return True

    store._async_image_exists = slow_check
    image = "upload:" + "a" * 32 + ".jpg"
    picture = hass.async_create_task(store.async_input(cmd("update", sid, "e1", image=image), None, True))
    await asyncio.sleep(0)  # the image input waits for the disk
    await store.async_input(cmd("set_delay", sid, "e2", step_id=delay["id"], seconds=9), None, True)
    assert next(s for s in store.scenes[sid]["sequence"] if s["type"] == "delay")["seconds"] == 9
    gate.set()
    await picture
    scene = store.scenes[sid]
    assert scene["image"] == image
    assert next(s for s in scene["sequence"] if s["type"] == "delay")["seconds"] == 9  # fixed W4


async def test_w5_reload_while_editing_moves_the_undo_point(hass, setup, hass_ws_client, resident_token):
    """Edit ids live in memory. After a restart or reload the open editor begins a second edit."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET], edit="create")
    step = group(setup.runtime_data.scenes[sid], "light")
    entry = {"step_id": step["id"], "entity_id": "light.kitchen", "mode": "set"}
    events = []
    hass.bus.async_listen(EVENT_CHANGED, events.append)
    assert (await call(**cmd("set_entry", sid, "e1", **entry, values={"brightness": 20})))["success"]
    assert await hass.config_entries.async_reload(setup.entry_id)
    await hass.async_block_till_done()
    assert (await call(**cmd("set_entry", sid, "e1", **entry, values={"brightness": 30})))["success"]
    await hass.async_block_till_done()
    previous = setup.runtime_data.scenes[sid]["previous"]["sequence"][0]["entries"][0]["attributes"]["brightness"]
    assert previous == 10  # fixed W5: still the state before the edit
    assert [e.data["action"] for e in events] == ["changed"]


# ---------- points of draft 0.8 that hold ----------


async def test_two_editors(hass, setup, hass_ws_client, resident_token, hass_access_token):
    """Spec 7 "Zwei Bearbeiter": inputs on different entries both stay; a removed step is refused."""
    first = await ws(hass, hass_ws_client, resident_token)
    second = await ws(hass, hass_ws_client, hass_access_token)
    sid = await save(first, name="Cook", area_id="kitchen", steps=[LIGHT_SET, BLIND])
    store = setup.runtime_data
    light, cover = group(store.scenes[sid], "light"), group(store.scenes[sid], "cover")
    one = first(**cmd("set_entry", sid, "a", step_id=light["id"], entity_id="light.kitchen", mode="off"))
    two = second(**cmd("set_entry", sid, "b", step_id=cover["id"], entity_id="cover.kitchen", mode="set",
                       values={"position": 40}))
    replies = await asyncio.gather(one, two)
    assert all(r["success"] for r in replies)
    states = {e["entity_id"]: e for e in flat(store.scenes[sid])}
    assert states["light.kitchen"]["state"] == "off"  # OK: both inputs are stored
    assert states["cover.kitchen"]["attributes"]["current_position"] == 40
    # the same entry: the later input wins without a notice; the other card shows it through its subscription
    await first(**cmd("set_entry", sid, "a", step_id=light["id"], entity_id="light.kitchen", mode="set",
                      values={"brightness": 50}))
    await second(**cmd("set_entry", sid, "b", step_id=light["id"], entity_id="light.kitchen", mode="set",
                       values={"brightness": 60}))
    assert flat(store.scenes[sid])[0]["attributes"]["brightness"] == 60  # NOTE: no version check for inputs
    assert (await first(**cmd("remove_step", sid, "a", step_id=cover["id"])))["success"]
    res = await second(**cmd("set_entry", sid, "b", step_id=cover["id"], entity_id="cover.kitchen", mode="off"))
    assert res["error"]["code"] == "step_missing"  # OK: refused, the card reloads


async def test_rights_of_inputs(hass, setup, hass_ws_client, resident_token, hass_access_token):
    """Protection, release, room boundary and live adjustments are checked for every input."""
    admin = await ws(hass, hass_ws_client, hass_access_token)
    resident = await ws(hass, hass_ws_client, resident_token)
    sid = await save(admin, name="Guard", area_id="kitchen", steps=[LIGHT_SET], kind="installer")
    store = setup.runtime_data
    step = group(store.scenes[sid], "light")
    entry = {"step_id": step["id"], "entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 77}}
    for command, fields in (("set_entry", entry), ("remove_step", {"step_id": step["id"]}),
                            ("add_step", {"step_type": "delay"}), ("update", {"transition": 2})):
        assert (await resident(**cmd(command, sid, "r", **fields)))["error"]["code"] == "protected"  # OK
    assert (await resident(type=f"{DOMAIN}/delete", scene_id=sid))["error"]["code"] == "protected"
    assert (await admin(**cmd("update", sid, "a", content_released=True)))["success"]
    assert (await resident(**cmd("set_entry", sid, "r", **entry)))["success"]  # OK: content is released
    assert (await resident(**cmd("update", sid, "r", name="Mine")))["error"]["code"] == "protected"
    assert (await resident(**cmd("update", sid, "r", kind="resident")))["error"]["code"] == "unauthorized"
    # room boundary: a light of the hall is no entry of a kitchen step, also not in a house scene
    hall = {"step_id": step["id"], "entity_id": "light.hall", "mode": "capture"}
    assert (await admin(**cmd("set_entry", sid, "a", **hall)))["error"]["code"] == "entity_not_allowed"  # OK
    house = await save(admin, name="Home")
    res = await admin(**cmd("add_step", house, step_type="group", domain="light", area_id="kitchen"))
    hall["step_id"] = res["result"]["step_id"]
    assert (await admin(**cmd("set_entry", house, "a", **hall)))["error"]["code"] == "entity_not_allowed"  # OK
    # live adjustments: lights follow, climate and music never do (spec 5.4)
    on = async_mock_service(hass, "light", "turn_on")
    heat = async_mock_service(hass, "climate", "set_hvac_mode")
    stop = async_mock_service(hass, "media_player", "media_stop")
    room = await save(admin, name="Live", area_id="kitchen")
    ids = {}
    for domain in ("light", "climate", "media_player"):
        ids[domain] = (await admin(**cmd("add_step", room, step_type="group", domain=domain)))["result"]["step_id"]
    await admin(**cmd("set_entry", room, step_id=ids["light"], entity_id="light.kitchen", mode="set",
                      values={"brightness": 33}, live=True))
    await admin(**cmd("set_entry", room, step_id=ids["climate"], entity_id="climate.kitchen", mode="off", live=True))
    await admin(**cmd("set_entry", room, step_id=ids["media_player"], entity_id="media_player.kitchen", mode="off",
                      live=True))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert [c.data["brightness"] for c in on] == [33]  # OK
    assert not heat and not stop  # OK
    before = len(on)
    await admin(**cmd("set_all", room, step_id=ids["light"], mode="capture", live=True))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(on) == before  # OK: switching live on takes over, it switches nothing


async def test_limits_and_delays(hass, setup, hass_ws_client, resident_token):
    hass.config_entries.async_update_entry(setup, options={**setup.options, CONF_STEPS_PER_SCENE: 3})
    await hass.async_block_till_done()
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen")
    ids = [(await call(**cmd("add_step", sid, step_type="delay")))["result"]["step_id"] for _ in range(3)]
    assert (await call(**cmd("add_step", sid, step_type="delay")))["error"]["code"] == "too_many_steps"  # OK
    store = setup.runtime_data
    assert store.scenes[sid]["sequence"][0]["seconds"] == 5  # OK: a new delay has 5 seconds
    for seconds in (0, -1, 601):
        res = await call(**cmd("set_delay", sid, step_id=ids[0], seconds=seconds))
        assert res["error"]["code"] == "invalid_delay"  # OK
    assert (await call(**cmd("set_delay", sid, step_id=ids[0], seconds=2.5)))["error"]["code"] == "invalid_delay"  # V16
    assert batches(store.scenes[sid]["sequence"]) == [(0, [])]  # OK: delays without anything after them do nothing


async def test_migration_runs_the_same(hass, hass_storage, setup):
    """Format 2 to 3: what went out together still goes out together, after the same delays."""
    steps = [
        {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 10}},
        {"entity_id": "light.hall", "state": "off", "attributes": {}},
        {"entity_id": "cover.kitchen", "state": "closed", "attributes": {}, "delay": 3},
        {"entity_id": "media_player.kitchen", "music": "off"},
        {"entity_id": "climate.kitchen", "state": "off", "attributes": {}, "delay": 2},
        {"entity_id": "light.gone", "state": "on", "attributes": {}},
    ]
    common = {"image": None, "kind": "resident", "content_released": False, "transition": None, "version": 4,
              "changed_by": None, "changed_at": None, "previous": None}
    await hass.config_entries.async_unload(setup.entry_id)
    hass_storage[STORAGE_KEY] = {
        "version": 2, "minor_version": 1, "key": STORAGE_KEY,
        "data": {"scenes": {"h": {**common, "id": "h", "name": "Home", "area_id": None, "steps": steps}},
                 "favorites": {"_house": ["h", None, None, None]}},
    }
    assert await hass.config_entries.async_setup(setup.entry_id)
    await hass.async_block_till_done()
    store = setup.runtime_data
    scene = store.scenes["h"]
    expected, current = [], (0, [])
    for step in steps:  # the batches of 0.2.2: a step with a delay starts a new one
        if step.get("delay"):
            expected.append(current)
            current = (step["delay"], [])
        current[1].append(step["entity_id"])
    expected.append(current)
    got = [(delay, sorted(e["entity_id"] for e in items)) for delay, items in batches(scene["sequence"])]
    assert got == [(delay, sorted(ids)) for delay, ids in expected]  # OK
    assert store.favorites["_house"][0] == "h" and scene["entity_named"]  # OK: slots and entity ids stay
    assert group(scene, "light")["area_id"] == "kitchen"
    loose = [s for s in scene["sequence"] if s["type"] == "group" and s["area_id"] is None]
    assert [e["entity_id"] for s in loose for e in s["entries"]] == ["light.gone"]  # NOTE: a step without a room


async def test_u1_two_scenes_of_one_automation_run(hass, setup, hass_ws_client, resident_token):
    """Review 0.2.2, U1: the delayed call of the first house scene was dropped. Now each trigger has its chain."""
    call = await ws(hass, hass_ws_client, resident_token)
    room = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    slow = await save(call, name="Slow", steps=[{"mode": "scene", "scene_id": room, "delay": 1}])
    fast = await save(call, name="Fast", steps=[{"mode": "scene", "scene_id": room}])
    await hass.async_block_till_done()
    on = async_mock_service(hass, "light", "turn_on")
    skipped = []
    hass.bus.async_listen(EVENT_SKIPPED, skipped.append)
    run = Context()  # one automation or script run
    for scene_id in (slow, fast):
        target = {"entity_id": eid(hass, scene_id)}
        await hass.services.async_call("scene", "turn_on", target, blocking=True, context=run)
    await asyncio.sleep(0.3)
    assert len(on) == 1  # "Fast" has called "Cook"
    await hass.async_block_till_done(wait_background_tasks=True)  # waits for the delay of "Slow" (real time)
    assert len(on) == 2 and not skipped  # OK (U1): "Cook" runs for each of the two
    assert on[0].context.id != on[1].context.id  # each trigger has its own context ...
    assert on[0].context.parent_id == on[1].context.parent_id == run.id  # ... linked to the automation run


@pytest.fixture
async def uploads(hass):
    folder = upload_dir(hass)

    def clear() -> None:
        if folder.is_dir():
            for path in folder.iterdir():
                path.unlink()

    await hass.async_add_executor_job(clear)
    yield folder
    await hass.async_add_executor_job(clear)


async def test_u2_parallel_uploads_keep_the_limit(hass, setup, hass_client, uploads):
    """Review 0.2.2, U2: between one and six uploads passed a limit of one."""
    hass.config_entries.async_update_entry(setup, options={**setup.options, CONF_IMAGE_COUNT: 1})
    await hass.async_block_till_done()
    out = io.BytesIO()
    Image.new("RGB", (64, 48)).save(out, "PNG")
    client = await hass_client()

    async def post():
        return (await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(out.getvalue())})).status

    statuses = await asyncio.gather(*(post() for _ in range(6)))
    files = await hass.async_add_executor_job(lambda: len(list(uploads.iterdir())))
    assert (statuses.count(200), files) == (1, 1)  # OK (U2)


async def test_saved_at_once(hass, setup, hass_ws_client, resident_token):
    """Spec 7 "Sofort gespeichert": a run right after the input uses it."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    on = async_mock_service(hass, "light", "turn_on")
    step = group(setup.runtime_data.scenes[sid], "light")
    await call(**cmd("set_entry", sid, "e1", step_id=step["id"], entity_id="light.kitchen", mode="set",
                     values={"brightness": 200}))
    await hass.services.async_call("scene", "turn_on", {"entity_id": eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert on[-1].data["brightness"] == 200  # OK


async def test_w6_the_disk_waits_for_a_pause(hass, setup, hass_ws_client, resident_token, hass_storage, monkeypatch):
    """Spec 4.5: an input is on disk after ten seconds at most. Every further input moves the write.

    Home Assistant's delayed save writes ``delay`` seconds after the latest call, not after the first.
    The delay is shortened here from 10 s to 0.3 s to run in real time.
    """
    monkeypatch.setattr(store_module, "SAVE_DELAY", 0.3)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="New", edit="x"))["result"]["scene_id"]
    await asyncio.sleep(0.5)  # the save of the generated entity id

    def on_disk():
        return hass_storage[STORAGE_KEY]["data"]["scenes"][sid]["transition"]

    seen = []
    for value in range(1, 8):  # someone editing: an input every 0.2 s for 1.4 s
        assert (await call(**cmd("update", sid, transition=value)))["success"]
        await asyncio.sleep(0.2)
        seen.append(on_disk())
    assert seen[-1] is not None  # fixed W6: written within the delay of the first input
    await asyncio.sleep(0.5)
    assert on_disk() == 7
