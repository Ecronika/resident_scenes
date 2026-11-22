"""Review of version 0.2.0 (findings S1 to S14), turned around after the fixes in 0.2.1.

Lines marked FIXED were FINDING lines of the review; OK lines confirmed earlier fixes.
"""

from __future__ import annotations

from datetime import timedelta
import io
import json
from pathlib import Path

from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import (
    MockUser,
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.resident_scenes.const import (
    CONF_IMAGE_COUNT,
    CONF_MAIN_USERS,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_USERS_WITHOUT_EDIT,
    DOMAIN,
    EVENT_SKIPPED,
)
from custom_components.resident_scenes.store import upload_dir
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import (
    area_registry as ar,
    entity_registry as er,
    issue_registry as ir,
    label_registry as lr,
)
from homeassistant.util import dt as dt_util
from tests.conftest import direct, eid as _eid, flat, make, run_scene, save as _save, ws as _ws

LIGHT_SET = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}
SETTINGS = {
    "label": "resident_scenes",
    "scenes_per_area": 5,
    "house_scenes": 30,
    "steps_per_scene": 150,
    "max_delay": 600,
    "name_length": 30,
    "favorite_slots": 4,
    "image_side": 1600,
    "image_kb": 500,
    "image_count": 200,
    "image_dir": "resident_scenes",
}


def _png(size=(64, 48), mode="RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, size).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
async def uploads(hass):
    """Start and end with an empty upload folder; the config folder is shared between tests."""
    folder = upload_dir(hass)

    def clear() -> None:
        if folder.is_dir():
            for path in folder.iterdir():
                path.unlink()

    await hass.async_add_executor_job(clear)
    yield folder
    await hass.async_add_executor_job(clear)


# ---------------------------------------------------------------- earlier findings, now fixed


@pytest.mark.parametrize("expected_lingering_timers", [True])  # the resident's connection is cut off
async def test_n1_fixed_image_address_survives_a_logout(
    hass, setup, hass_client_no_auth, hass_ws_client, resident_token, hass_read_only_user, hass_access_token
):
    folder = Path(hass.config.path("resident_scenes"))

    def make() -> None:
        folder.mkdir(exist_ok=True)
        (folder / "sofa.png").write_bytes(_png())

    await hass.async_add_executor_job(make)
    try:
        resident = await _ws(hass, hass_ws_client, resident_token)
        admin = await _ws(hass, hass_ws_client, hass_access_token)

        async def url(call):
            images = (await call(type=f"{DOMAIN}/devices"))["result"]["images"]
            return next(i["url"] for i in images if i["name"] == "sofa.png")

        first = await url(resident)
        assert await url(admin) == first
        for token in list(hass_read_only_user.refresh_tokens.values()):  # the resident logs out
            hass.auth.async_remove_refresh_token(token)
        await hass.async_block_till_done()
        anon = await hass_client_no_auth()
        assert (await anon.get(first)).status == 200  # OK (N1): no longer tied to the resident's login
        assert (await anon.get(first.split("?")[0])).status == 401  # and still nothing without signature
    finally:
        await hass.async_add_executor_job((folder / "sofa.png").unlink)


async def test_n4_fixed_options_error_keeps_the_inputs(hass, setup):
    flow = await hass.config_entries.options.async_init(setup.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "settings"})
    result = await hass.config_entries.options.async_configure(flow["flow_id"], {**SETTINGS, "image_dir": "/etc"})
    suggested = {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description and "suggested_value" in key.description
    }
    assert result["errors"] == {"image_dir": "outside_config"}
    assert suggested["scenes_per_area"] == 5  # OK (N4)


async def test_n5_fixed_label_name_in_use(hass, setup):
    labels = lr.async_get(hass)
    labels.async_delete("resident_scenes")
    other = labels.async_create("Bewohner")
    labels.async_update(other.label_id, name="resident_scenes")  # same name, other id
    await hass.config_entries.async_reload(setup.entry_id)
    await hass.async_block_till_done()
    assert setup.state is ConfigEntryState.LOADED  # OK (N5)


async def test_large_scene_through_the_script_helper(hass, setup, hass_ws_client, resident_token):
    """E2 / acceptance 'GroÃŸe Szene': 60 light circuits in 30 rooms, every step is handed on."""
    ent_reg = er.async_get(hass)
    areas = ar.async_get(hass)
    steps = []
    for room in range(30):
        area = areas.async_create(f"Room {room}")
        for n in range(2):
            ent = ent_reg.async_get_or_create("light", "test", f"r{room}_{n}", suggested_object_id=f"r{room}_{n}")
            ent_reg.async_update_entity(ent.entity_id, area_id=area.id, labels={"resident_scenes"})
            hass.states.async_set(ent.entity_id, "on", {"brightness": 200, "color_mode": "brightness"})
            steps.append({"entity_id": ent.entity_id, "mode": "off"})
    call = await _ws(hass, hass_ws_client, resident_token)
    sid = await _save(call, name="Away", steps=steps)
    off = async_mock_service(hass, "light", "turn_off")
    await run_scene(hass, _eid(hass, sid))
    assert len(off) == 60  # OK


# ---------------------------------------------------------------- new findings


async def test_s1_capture_fails_when_a_device_was_moved(hass, setup, hass_ws_client, resident_token):
    """Spec 4.5: a moved device keeps its stored step and keeps running. capture refuses the whole scene."""
    call = await _ws(hass, hass_ws_client, resident_token)
    steps = [{"entity_id": "light.kitchen", "mode": "capture"}, {"entity_id": "cover.kitchen", "mode": "capture"}]
    sid = await _save(call, name="Evening", area_id="kitchen", steps=steps)
    await hass.async_block_till_done()
    bath = ar.async_get(hass).async_create("Bath")
    er.async_get(hass).async_update_entity("cover.kitchen", area_id=bath.id)  # the installer moves the blind
    hass.states.async_set("light.kitchen", "on", {"brightness": 33, "color_mode": "brightness"})
    store = setup.runtime_data
    blind = flat(store.scenes[sid])[1]
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": _eid(hass, sid)}, blocking=True)
    assert flat(store.scenes[sid])[0]["attributes"]["brightness"] == 33  # FIXED: the light is taken over
    assert flat(store.scenes[sid])[1] == blind  # FIXED: the moved blind keeps its value


async def test_s1_capture_fails_when_a_called_scene_is_gone(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    room = await _save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    hall = {"entity_id": "light.hall", "mode": "capture"}
    house = await _save(call, name="Home", steps=[{"mode": "scene", "scene_id": room}, hall])
    assert (await call(type=f"{DOMAIN}/delete", scene_id=room))["success"]
    await hass.async_block_till_done()
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": _eid(hass, house)}, blocking=True)
    called = flat(setup.runtime_data.scenes[house])[0]
    assert (called["scene_id"], called["name"]) == (room, "Cook")  # FIXED: stays


async def test_s2_house_scene_stuck_after_its_room_was_deleted(hass, setup, hass_ws_client, resident_token):
    """Rule B1: scenes of a deleted room become house scenes. A house scene calling one can no longer be saved."""
    call = await _ws(hass, hass_ws_client, resident_token)
    room = await _save(call, name="Cook", area_id="kitchen", steps=[LIGHT_SET])
    hall = {"entity_id": "light.hall", "mode": "capture"}
    house = await _save(call, name="Home", steps=[{"mode": "scene", "scene_id": room}, hall])
    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    store = setup.runtime_data
    assert store.scenes[room]["area_id"] is None  # now a house scene
    detail = (await call(type=f"{DOMAIN}/scene", scene_id=house))["result"]
    assert detail["sequence"][0]["issue"] == "no_room_scene"  # FIXED: marked, the card offers "Remove"
    devices = (await call(type=f"{DOMAIN}/devices"))["result"]
    assert devices["room_scenes"] == []  # ... and no select shows it
    res = await call(type=f"{DOMAIN}/update", scene_id=house, edit="x", transition=1)
    assert res["success"], res  # FIXED: the scene stays editable
    res = await make(call, name="Other", steps=[{"mode": "scene", "scene_id": room}])
    assert res["error"] == {"code": "invalid_scene_call", "message": "invalid_scene_call: Cook"}  # FIXED: name
    light = async_mock_service(hass, "light", "turn_on")
    await run_scene(hass, _eid(hass, house))
    assert any(c.data.get("brightness") == 10 for c in light)  # running still works


async def test_s4_resident_takes_back_a_change_of_the_installer(hass, setup, hass_ws_client, resident_token):
    """Spec 2: a resident cannot rename an installer scene. Undo does it for him."""
    store = setup.runtime_data
    installer = direct(store)
    sid = await _save(installer, name="Cook", area_id="kitchen", kind="installer", content_released=True,
                      steps=[LIGHT_SET])
    assert (await installer(type=f"{DOMAIN}/update", scene_id=sid, edit="e2", name="Kochen"))["success"]  # renamed
    call = await _ws(hass, hass_ws_client, resident_token)
    back = {"type": f"{DOMAIN}/update", "scene_id": sid, "edit": "e3", "name": "Cook"}
    assert (await call(**back))["error"]["code"] == "protected"  # renaming is refused, as specified
    version = store.scenes[sid]["version"]
    assert (await call(type=f"{DOMAIN}/undo", scene_id=sid, version=version))["success"]
    assert store.scenes[sid]["name"] == "Kochen"  # FIXED: only the content is taken back


async def test_upload_needs_login_or_signature(hass, setup, hass_client, hass_client_no_auth, uploads):
    """Acceptance 'Bild': not retrievable without login."""
    client = await hass_client()
    upload = await (await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(_png())})).json()
    anon = await hass_client_no_auth()
    assert (await anon.get(upload["url"])).status == 200  # signed address
    assert (await anon.get(upload["url"].split("?")[0])).status == 401  # OK
    assert (await anon.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(_png())})).status == 401  # OK


async def test_s5_upload_limit_counts_only_images_in_use(hass, setup, hass_client, uploads):
    hass.config_entries.async_update_entry(setup, options={**setup.options, CONF_IMAGE_COUNT: 1})
    await hass.async_block_till_done()
    client = await hass_client()
    statuses = [
        (await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(_png())})).status for _ in range(3)
    ]
    assert statuses == [200, 400, 400]  # FIXED: files on disk count
    assert len(await hass.async_add_executor_job(lambda: list(uploads.iterdir()))) == 1


async def test_s5_broken_png_is_a_server_error(hass, setup, hass_client, uploads):
    data = bytearray(_png((300, 300)))
    start = data.index(b"IDAT")
    data[start + 6] ^= 0xFF  # damage the image data, the checksum no longer fits
    client = await hass_client()
    res = await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(bytes(data))})
    assert res.status == 400  # FIXED


async def test_s5_every_format_and_any_size_is_decoded(hass, setup, hass_client, uploads):
    client = await hass_client()
    out = io.BytesIO()
    Image.new("RGB", (64, 48)).save(out, "TIFF")
    res = await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(out.getvalue())})
    assert res.status == 400  # FIXED: only JPEG, PNG, WebP
    big = _png((9000, 9000), "1")  # 81 megapixels in a file of a few kB
    assert len(big) < 50_000
    res = await client.post(f"/api/{DOMAIN}/upload", data={"file": io.BytesIO(big)})
    assert res.status == 400  # FIXED: refused from the header, before decoding


async def test_s6_template_values_are_not_checked(hass, setup, hass_ws_client, resident_token):
    path = Path(hass.config.path("tpl.json"))
    await hass.async_add_executor_job(path.write_text, json.dumps({"options": {"favorite_slots": "four"}}))
    try:
        flow = await hass.config_entries.options.async_init(setup.entry_id)
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "template"})
        result = await hass.config_entries.options.async_configure(flow["flow_id"], {"template": "tpl.json"})
    finally:
        await hass.async_add_executor_job(path.unlink)
    assert result["errors"] == {"base": "invalid_template"}  # FIXED
    call = await _ws(hass, hass_ws_client, resident_token)
    assert (await call(type=f"{DOMAIN}/list", scope="_house"))["success"]


async def test_s6_template_is_loaded_in_part(hass, setup):
    template = {
        "options": {"favorite_slots": 3},
        "scenes": [
            {"key": "a", "name": "First", "steps": [LIGHT_SET]},
            {"key": "b", "name": "Second", "steps": [{"entity_id": "lock.door", "mode": "off"}]},
        ],
    }
    path = Path(hass.config.path("tpl.json"))
    await hass.async_add_executor_job(path.write_text, json.dumps(template))
    try:
        flow = await hass.config_entries.options.async_init(setup.entry_id)
        flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "template"})
        result = await hass.config_entries.options.async_configure(flow["flow_id"], {"template": "tpl.json"})
    finally:
        await hass.async_add_executor_job(path.unlink)
    assert result["errors"] == {"base": "invalid_template"}
    assert "tpl_a" not in setup.runtime_data.scenes  # FIXED: all or nothing
    assert setup.options.get("favorite_slots", 4) == 4


async def test_s7_capture_with_other_targets(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    await _save(call, name="Evening", area_id="kitchen", steps=[LIGHT_SET])
    await hass.async_block_till_done()
    store = setup.runtime_data
    hass.states.async_set("light.kitchen", "on", {"brightness": 77, "color_mode": "brightness"})
    await hass.services.async_call(DOMAIN, "capture", {"area_id": "kitchen"}, blocking=True)  # FIXED
    assert flat(next(iter(store.scenes.values())))[0]["attributes"]["brightness"] == 77
    hass.states.async_set("light.kitchen", "on", {"brightness": 66, "color_mode": "brightness"})
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": "all"}, blocking=True)  # FIXED
    assert flat(next(iter(store.scenes.values())))[0]["attributes"]["brightness"] == 66


async def test_s8_rights_ranks(hass, setup, hass_ws_client, resident_token, hass_read_only_user, hass_access_token):
    """Acceptance 'Hauptnutzer' and 'Panel' hold; the installer gets a switch without effect."""
    group = [await hass.auth.async_get_group(GROUP_ID_USER)]
    kid = MockUser(name="Kid", groups=group).add_to_hass(hass)
    panel = MockUser(name="Panel", groups=group).add_to_hass(hass)
    main2 = MockUser(name="Main 2", groups=group).add_to_hass(hass)
    options = {**setup.options, CONF_MAIN_USERS: [hass_read_only_user.id, main2.id], CONF_PANEL_USERS: [panel.id]}
    hass.config_entries.async_update_entry(setup, options=options)
    await hass.async_block_till_done()
    main = await _ws(hass, hass_ws_client, resident_token)
    right = f"{DOMAIN}/set_right"
    names = {a["name"]: a for a in (await main(type=f"{DOMAIN}/rights"))["result"]["accounts"]}
    assert set(names) == {"Kid", "Panel"}  # OK: no main user, no admin, not himself
    assert names["Panel"] == {"user_id": panel.id, "name": "Panel", "kind": "panel", "can_edit": False}
    for uid in (hass_read_only_user.id, main2.id):
        assert (await main(type=right, user_id=uid, can_edit=False))["error"]["code"] == "unauthorized"  # OK
    assert (await main(type=right, user_id=panel.id, can_edit=True))["success"]  # OK: panel switched on
    assert setup.options[CONF_PANELS_WITH_EDIT] == [panel.id]
    assert (await main(type=right, user_id=kid.id, can_edit=False))["success"]
    assert setup.options[CONF_USERS_WITHOUT_EDIT] == [kid.id]

    admin = await _ws(hass, hass_ws_client, hass_access_token)
    listed = {a["name"]: a for a in (await admin(type=f"{DOMAIN}/rights"))["result"]["accounts"]}
    assert "Main 2" not in listed  # FIXED: main users always may edit, no switch
    assert (await admin(type=right, user_id=main2.id, can_edit=False))["error"]["code"] == "unauthorized"


async def test_s9_repair_issue_waits_for_the_next_change(hass, setup, hass_ws_client, resident_token):
    """Spec 4.10: the installer sees a missing device without opening the card."""
    call = await _ws(hass, hass_ws_client, resident_token)
    sid = await _save(call, name="Evening", area_id="kitchen", steps=[LIGHT_SET])
    await hass.async_block_till_done()
    er.async_get(hass).async_remove("light.kitchen")  # the device is replaced
    hass.states.async_remove("light.kitchen")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"broken_{sid}") is not None  # FIXED: without a further change
    assert await hass.config_entries.async_remove(setup.entry_id)
    assert issues.async_get_issue(DOMAIN, f"broken_{sid}") is None  # removed with the integration


async def test_s10_change_during_a_delay_drops_the_rest(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    late = {"entity_id": "cover.kitchen", "mode": "set", "values": {"position": 20}, "delay": 5}
    sid = await _save(call, name="Late", area_id="kitchen", steps=[LIGHT_SET, late])
    async_mock_service(hass, "light", "turn_on")
    cover = async_mock_service(hass, "cover", "set_cover_position")
    async_mock_service(hass, "cover", "set_cover_tilt_position")  # "open" also opens the slats
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    await hass.services.async_call("scene", "turn_on", {"entity_id": _eid(hass, sid)}, blocking=True)
    await hass.async_block_till_done()
    assert (await call(type=f"{DOMAIN}/update", scene_id=sid, edit="x", name="Later"))["success"]  # only renamed
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=10))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert cover  # FIXED: the run finishes with the steps it started with
    assert not skipped


async def test_note_position_without_tilt_opens_the_slats(hass, setup, hass_ws_client, resident_token):
    """Not a fault of the integration: Home Assistant opens what a target state "open" leaves unset.

    Templates (and the README example) should give position AND tilt for blinds with slats.
    """
    call = await _ws(hass, hass_ws_client, resident_token)
    blind = {"entity_id": "cover.kitchen", "mode": "set", "values": {"position": 20}}
    sid = await _save(call, name="Shade", area_id="kitchen", steps=[blind])
    position = async_mock_service(hass, "cover", "set_cover_position")
    tilt = async_mock_service(hass, "cover", "set_cover_tilt_position")
    await run_scene(hass, _eid(hass, sid))
    assert position[0].data["position"] == 20
    assert tilt[0].data["tilt_position"] == 100  # NOTE: slats fully open


async def test_s14_diagnostics_list_the_main_users(hass, setup, hass_read_only_user):
    """Spec 6: the diagnostics carry nothing personal. The option added in 0.2.0 is not reduced to a count."""
    from custom_components.resident_scenes.diagnostics import async_get_config_entry_diagnostics  # noqa: PLC0415

    options = {**setup.options, CONF_MAIN_USERS: [hass_read_only_user.id], CONF_USERS_WITHOUT_EDIT: ["x", "y"]}
    hass.config_entries.async_update_entry(setup, options=options)
    await hass.async_block_till_done()
    report = await async_get_config_entry_diagnostics(hass, setup)
    assert report["options"][CONF_USERS_WITHOUT_EDIT] == 2  # a count, as intended
    assert report["options"][CONF_MAIN_USERS] == 1  # FIXED: a count
