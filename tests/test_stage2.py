"""Tests for stage 2: script runs, set values, scene calls, installer scenes, uploads, rights."""

from __future__ import annotations

from datetime import timedelta
import io
import json
from pathlib import Path

from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockUser,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.resident_scenes.const import (
    CONF_MAIN_USERS,
    CONF_USERS_WITHOUT_EDIT,
    DOMAIN,
    EVENT_RIGHTS,
    EVENT_SKIPPED,
    STORAGE_KEY,
)
from custom_components.resident_scenes.store import recode_image, upload_dir
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import area_registry as ar, issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from tests.conftest import direct, eid as _eid, flat, make, run_scene, save as _save, ws as _ws

LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}


def _jpeg(size=(2000, 100)) -> bytes:
    out = io.BytesIO()
    exif = Image.Exif()
    exif[0x0132] = "2026:01:01 10:00:00"  # DateTime
    Image.new("RGB", size, "red").save(out, "JPEG", exif=exif)
    return out.getvalue()


async def test_delay_restart_and_transition(hass, setup, hass_ws_client, resident_token) -> None:
    """Steps after a delay run later; running again restarts; transition goes to lights only."""
    call = await _ws(hass, hass_ws_client, resident_token)
    kitchen = ar.async_get(hass).async_get_area_by_name("Kitchen").id
    sid = await _save(
        call,
        name="Late",
        area_id=kitchen,
        transition=2,
        steps=[LIGHT_SET, {"entity_id": "cover.kitchen", "mode": "set", "values": {"position": 20}, "delay": 5}],
    )
    light = async_mock_service(hass, "light", "turn_on")
    cover = async_mock_service(hass, "cover", "set_cover_position")

    async def later(seconds: float, wait: bool = False) -> None:
        # fake time does not advance by itself, so every jump counts from now
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
        await hass.async_block_till_done(wait_background_tasks=wait)

    await hass.services.async_call("scene", "turn_on", {"entity_id": _eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done()
    assert light[0].data["brightness"] == 10
    assert light[0].data["transition"] == 2
    await later(3)
    await hass.services.async_call("scene", "turn_on", {"entity_id": _eid(hass, sid)}, blocking=True)
    await later(3)
    assert not cover
    await later(10, wait=True)
    assert len(cover) == 1  # the first run was cancelled by the restart
    assert cover[0].data["position"] == 20
    assert "transition" not in cover[0].data
    assert len(light) == 2


async def test_set_values_validated(hass, setup, hass_ws_client, resident_token) -> None:
    """Set values are checked against the device; climate and cover accept their values."""
    call = await _ws(hass, hass_ws_client, resident_token)
    bad = [
        {"entity_id": "light.kitchen", "mode": "set", "values": {"color_temp_kelvin": 9000}},
        {"entity_id": "climate.kitchen", "mode": "set", "values": {"hvac_mode": "cool"}},
        {"entity_id": "cover.kitchen", "mode": "set", "values": {}},
        {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": True}},
    ]
    for step in bad:
        res = await make(call, name="Bad", steps=[step])
        assert res["error"]["code"] == "invalid_value", step
    res = await make(call, name="Bad", steps=[{**LIGHT_SET, "delay": 9999}])
    assert res["error"]["code"] == "invalid_delay"
    res = await make(
        call,
        name="Fav",
        steps=[{"entity_id": "media_player.kitchen", "mode": "music", "music": "favorite",
                "favorite_id": "FV:2/1", "volume": 0.2}],
    )
    assert res["error"]["code"] == "favorite_not_supported"  # N6: only music-system players
    sid = await _save(
        call,
        name="Warm",
        steps=[
            {"entity_id": "light.kitchen", "mode": "set", "values": {"color_temp_kelvin": 2700, "brightness": 99}},
            {"entity_id": "climate.kitchen", "mode": "set", "values": {"temperature": 22.5}},
            {"entity_id": "cover.kitchen", "mode": "set", "values": {"position": 0, "tilt": 30}},
            {"entity_id": "media_player.kitchen", "mode": "off"},
        ],
    )
    steps = flat(setup.runtime_data.scenes[sid])
    assert steps[0]["attributes"] == {"brightness": 99, "color_mode": "color_temp", "color_temp_kelvin": 2700}
    assert steps[1] == {"entity_id": "climate.kitchen", "state": "heat", "attributes": {"temperature": 22.5}}
    assert steps[2]["state"] == "closed"
    devices = (await call(type=f"{DOMAIN}/devices"))["result"]
    caps = {e["entity_id"]: e for e in devices["entities"]}
    assert caps["light.kitchen"]["capabilities"]["color_temp"] is True
    assert caps["climate.kitchen"]["capabilities"]["hvac_modes"] == ["off", "heat"]
    assert caps["media_player.sonos_kitchen"]["music_system"] is True
    assert caps["media_player.kitchen"]["music_system"] is False


async def test_house_scene_calls_room_scene(hass, setup, hass_ws_client, resident_token) -> None:
    """A house scene runs room scenes; a deleted one is shown as missing and raises a repair issue."""
    call = await _ws(hass, hass_ws_client, resident_token)
    kitchen = ar.async_get(hass).async_get_area_by_name("Kitchen").id
    room = await _save(call, name="Cook", area_id=kitchen, steps=[LIGHT_SET])
    res = await make(call, name="Bad", area_id=kitchen, steps=[{"mode": "scene", "scene_id": room}])
    assert res["error"]["code"] == "invalid_scene_call"  # room scenes call no scenes
    house = await _save(call, name="Evening", steps=[{"mode": "scene", "scene_id": room}])
    assert (await call(type=f"{DOMAIN}/devices"))["result"]["room_scenes"] == [
        {"id": room, "name": "Cook", "area_id": kitchen}
    ]
    detail = (await call(type=f"{DOMAIN}/scene", scene_id=room))["result"]
    assert detail["used_in"]["scenes"] == ["Evening"]
    light = async_mock_service(hass, "light", "turn_on")
    await run_scene(hass, _eid(hass, house))
    assert light[0].data["brightness"] == 10

    assert (await call(type=f"{DOMAIN}/delete", scene_id=room))["success"]
    await hass.async_block_till_done()
    steps = (await call(type=f"{DOMAIN}/scene", scene_id=house))["result"]["sequence"]
    assert steps[0]["issue"] == "scene_missing"
    assert steps[0]["name"] == "Cook"
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"broken_{house}")
    skipped = []
    hass.bus.async_listen(EVENT_SKIPPED, skipped.append)
    await run_scene(hass, _eid(hass, house))
    assert skipped[0].data["entities"] == ["Cook"]
    assert (await call(type=f"{DOMAIN}/delete", scene_id=house))["success"]
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"broken_{house}") is None


async def test_step_marks(hass, setup, hass_ws_client, hass_access_token) -> None:
    """N3: missing, not released, other area and unreachable are told apart."""
    store = setup.runtime_data
    kitchen = ar.async_get(hass).async_get_area_by_name("Kitchen").id
    sid = await _save(direct(store), name="Mix", area_id=kitchen, steps=[LIGHT_SET])
    store.scenes[sid]["sequence"][0]["entries"] += [
        {"entity_id": "light.gone", "state": "on", "attributes": {}},
        {"entity_id": "light.unreleased", "state": "on", "attributes": {}},
        {"entity_id": "light.hall", "state": "on", "attributes": {}},
        {"entity_id": "cover.kitchen", "state": "open", "attributes": {}},
        {"entity_id": "media_player.sonos_kitchen", "music": "favorite", "volume": 0.2,
         "favorite_id": "FV:2/9", "favorite_name": "Old radio"},
    ]
    hass.states.async_set("cover.kitchen", "unavailable")
    hass.states.async_set("light.unreleased", "on")
    call = await _ws(hass, hass_ws_client, hass_access_token)
    steps = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]["sequence"][0]["entries"]
    assert [s["issue"] for s in steps] == [
        None, "missing", "not_released", "other_area", "unavailable", "favorite_missing"
    ]
    assert steps[-1]["favorite_name"] == "Old radio"
    await store.async_set_favorite(kitchen, 0, sid)  # any commit re-checks the issues
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"broken_{sid}")
    assert issue.translation_placeholders["items"] == "light.gone, Old radio"
    assert (await call(type=f"{DOMAIN}/undo", scene_id="nope", version=1))["error"]["code"] == "not_found"
    assert (await call(type=f"{DOMAIN}/scene", scene_id="nope"))["error"]["code"] == "not_found"


async def _template(hass: HomeAssistant, entry: MockConfigEntry, name: str):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "template"})
    return await hass.config_entries.options.async_configure(result["flow_id"], {"template": name})


async def test_template_and_installer_protection(hass, setup, hass_ws_client, resident_token) -> None:
    """A template loads options and installer scenes; residents change only released content."""
    kitchen = ar.async_get(hass).async_get_area_by_name("Kitchen").id
    template = {
        "options": {"favorite_slots": 3},
        "scenes": [
            {"key": "cook", "name": "Cook", "area_id": kitchen, "content_released": True, "steps": [LIGHT_SET]},
            {"key": "lock", "name": "Locked", "steps": [LIGHT_SET], "transition": 1},
        ],
    }
    path = Path(hass.config.path("tpl.json"))
    await hass.async_add_executor_job(path.write_text, json.dumps(template))
    try:
        result = await _template(hass, setup, "tpl.json")
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert setup.options["favorite_slots"] == 3
        assert (await _template(hass, setup, "../x.json"))["errors"] == {"template": "outside_config"}
        assert (await _template(hass, setup, "missing.yaml"))["errors"] == {"base": "invalid_template"}
        await hass.async_add_executor_job(path.write_text, json.dumps({"options": {"evil": 1}}))
        assert (await _template(hass, setup, "tpl.json"))["errors"] == {"base": "invalid_template"}
    finally:
        await hass.async_add_executor_job(path.unlink)

    store = setup.runtime_data
    call = await _ws(hass, hass_ws_client, resident_token)
    cook, locked = store.scenes["tpl_cook"], store.scenes["tpl_lock"]
    update = f"{DOMAIN}/update"
    assert (await call(type=update, scene_id="tpl_lock", edit="x", transition=2))["error"]["code"] == "protected"
    assert (await call(type=f"{DOMAIN}/delete", scene_id="tpl_cook"))["error"]["code"] == "protected"
    assert (await call(type=update, scene_id="tpl_cook", edit="x", name="Mine"))["error"]["code"] == "protected"
    assert (await call(type=update, scene_id="tpl_cook", edit="x", name="Cook"))["success"]  # unchanged name
    assert (await make(call, name="X", kind="installer"))["error"]["code"] == "unauthorized"
    assert (await make(call, name="X", content_released=True))["error"]["code"] == "unauthorized"
    step_id = cook["sequence"][0]["id"]
    content = {"type": f"{DOMAIN}/set_entry", "scene_id": "tpl_cook", "edit": "x", "step_id": step_id,
               "entity_id": "light.kitchen", "mode": "off"}
    assert (await call(**content))["success"]
    assert cook["kind"] == "installer" == store.scenes["tpl_cook"]["kind"]
    listing = (await call(type=f"{DOMAIN}/list", scope="_house"))["result"]
    assert [s["editable"] for s in listing["scenes"]] == [False]
    assert locked["transition"] == 1

    # undo by the resident brings back the template content
    version = store.scenes["tpl_cook"]["version"]
    res = await call(type=f"{DOMAIN}/undo", scene_id="tpl_cook", version=version)
    assert res["success"], res
    assert flat(store.scenes["tpl_cook"])[0]["attributes"]["brightness"] == 10
    res = await call(type=f"{DOMAIN}/undo", scene_id="tpl_cook", version=version + 1)
    assert res["error"]["code"] == "nothing_to_undo"
    assert (await call(type=f"{DOMAIN}/undo", scene_id="tpl_cook", version=1))["error"]["code"] == "version_conflict"


async def test_upload_recode_and_undo_image(hass, setup, hass_client, hass_ws_client, resident_token) -> None:
    """Uploads are re-encoded without EXIF, served signed, and come back with undo."""
    client = await hass_client()
    res = await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(_jpeg())})
    assert res.status == 200
    upload = await res.json()
    photo = await client.get(upload["url"])
    assert photo.status == 200
    with Image.open(io.BytesIO(await photo.read())) as img:
        assert img.size == (1600, 80)
        assert not img.getexif()
    bad = await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(b"no image")})
    assert bad.status == 400
    assert (await bad.json())["code"] == "invalid_image_file"
    assert (await client.post(f"/api/{DOMAIN}/upload", data={"x": "1"})).status == 400
    assert (await client.get(f"/api/{DOMAIN}/photo/notvalid.jpg")).status == 404

    call = await _ws(hass, hass_ws_client, resident_token)
    sid = await _save(call, name="Pic", image=upload["image"], steps=[LIGHT_SET])
    res = await make(call, name="P2", image="upload:" + "0" * 32 + ".jpg")
    assert res["error"]["code"] == "invalid_image"
    assert (await call(type=f"{DOMAIN}/update", scene_id=sid, edit="e2", image=None))["success"]
    file = upload_dir(hass) / upload["image"].removeprefix("upload:")
    assert await hass.async_add_executor_job(file.is_file)  # kept for undo
    version = setup.runtime_data.scenes[sid]["version"]
    assert (await call(type=f"{DOMAIN}/undo", scene_id=sid, version=version))["success"]
    assert setup.runtime_data.scenes[sid]["image"] == upload["image"]


def test_recode_limits() -> None:
    """Too large after the lowest quality is refused."""
    with pytest.raises(Exception, match="image_too_large"):
        recode_image(_jpeg((1600, 1600)), 1600, 0)


async def test_capture_action(hass, setup, hass_admin_user, hass_read_only_user) -> None:
    """resident_scenes.capture takes over the current state; read-only accounts are refused."""
    store = setup.runtime_data
    sid = await _save(direct(store), name="Snap", steps=[LIGHT_SET])
    version = store.scenes[sid]["version"]
    entity_id = _eid(hass, sid)
    hass.states.async_set("light.kitchen", "on", {"brightness": 200, "color_mode": "brightness"})
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": entity_id}, blocking=True)
    assert flat(store.scenes[sid])[0]["attributes"]["brightness"] == 200
    await hass.services.async_call(
        DOMAIN, "capture", {"entity_id": entity_id}, blocking=True, context=Context(user_id=hass_admin_user.id)
    )
    assert store.scenes[sid]["version"] == version + 2
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "capture", {"entity_id": entity_id}, blocking=True,
            context=Context(user_id=hass_read_only_user.id),
        )
    hass.states.async_set("light.kitchen", "on", {"brightness": 90, "color_mode": "brightness"})
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": "all"}, blocking=True)  # S7: targets resolved
    assert flat(store.scenes[sid])[0]["attributes"]["brightness"] == 90


async def test_rights_by_main_user(hass, setup, hass_ws_client, resident_token, hass_read_only_user) -> None:
    """A main user lists accounts below and takes or gives the edit right."""
    other = MockUser(name="Kid", groups=[await hass.auth.async_get_group(GROUP_ID_USER)]).add_to_hass(hass)
    call = await _ws(hass, hass_ws_client, resident_token)
    assert (await call(type=f"{DOMAIN}/rights"))["error"]["code"] == "unauthorized"
    assert (await call(type=f"{DOMAIN}/set_right", user_id=other.id, can_edit=False))["error"]["code"] == (
        "unauthorized"
    )
    hass.config_entries.async_update_entry(setup, options={**setup.options, CONF_MAIN_USERS: [hass_read_only_user.id]})
    listing = (await call(type=f"{DOMAIN}/list", scope="_house"))["result"]
    assert listing["manages_rights"] is True
    accounts = (await call(type=f"{DOMAIN}/rights"))["result"]["accounts"]
    assert {"user_id": other.id, "name": "Kid", "kind": "resident", "can_edit": True} in accounts
    assert all(a["user_id"] != hass_read_only_user.id for a in accounts)
    events = []
    hass.bus.async_listen(EVENT_RIGHTS, events.append)
    assert (await call(type=f"{DOMAIN}/set_right", user_id=other.id, can_edit=False))["success"]
    await hass.async_block_till_done()
    assert setup.options[CONF_USERS_WITHOUT_EDIT] == [other.id]
    assert events[0].data == {"user": "Kid", "can_edit": False}
    assert (await call(type=f"{DOMAIN}/set_right", user_id=other.id, can_edit=True))["success"]
    assert setup.options[CONF_USERS_WITHOUT_EDIT] == []


async def test_migration_from_v1(hass: HomeAssistant, hass_storage) -> None:
    """Stage 1 data gets the new fields."""
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": {
            "scenes": {
                "a": {"id": "a", "name": "Old", "area_id": None, "image": None, "kind": "resident",
                      "steps": [], "version": 1, "changed_by": None, "changed_at": None}
            },
            "favorites": {},
        },
    }
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    scene = entry.runtime_data.scenes["a"]
    assert (scene["content_released"], scene["transition"], scene["previous"]) == (False, None, None)
    assert (scene["sequence"], scene["entity_named"]) == ([], True)
