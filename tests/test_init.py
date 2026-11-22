"""Tests for Resident Scenes: rights, editing, slots, activation, images."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events, async_mock_service

from custom_components.resident_scenes.const import (
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_USERS_WITHOUT_EDIT,
    DOMAIN,
    EVENT_CHANGED,
    EVENT_SKIPPED,
    VERSION,
)
from custom_components.resident_scenes.diagnostics import async_get_config_entry_diagnostics
from custom_components.resident_scenes.logbook import async_describe_events
from custom_components.resident_scenes.model import can_edit
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from tests.conftest import direct, eid, flat, make, run_scene, save, ws as _ws

ROOT = Path(__file__).parent.parent / "custom_components" / DOMAIN


def test_versions_match() -> None:
    """Manifest, constant and card carry the same version."""
    manifest = json.loads((ROOT / "manifest.json").read_text())
    card = (ROOT / "frontend" / "resident-scenes-card.js").read_text()
    assert manifest["version"] == VERSION
    assert f'VERSION = "{VERSION}"' in card


async def test_flows(hass: HomeAssistant) -> None:
    """Config flow creates one entry, options store numbers as int."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "settings"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "label": "resident_scenes",
            "scenes_per_area": 5.0,
            "house_scenes": 30,
            "steps_per_scene": 150,
            "name_length": 30,
            "max_delay": 600,
            "image_side": 1600,
            "image_kb": 500,
            "image_count": 200,
            "favorite_slots": 4,
            "image_dir": "resident_scenes",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["scenes_per_area"] == 5


async def test_create_capture_and_activate(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, resident_token
) -> None:
    """A non-admin creates a scene from the current state; running it restores it."""
    call = await _ws(hass, hass_ws_client, resident_token)
    changes = async_capture_events(hass, EVENT_CHANGED)

    res = await call(type=f"{DOMAIN}/devices", area_id="kitchen")
    assert {e["entity_id"] for e in res["result"]["entities"]} == {
        "light.kitchen",
        "cover.kitchen",
        "climate.kitchen",
        "media_player.kitchen",
        "media_player.sonos_kitchen",
    }  # no lock, no unlabelled light, no other area
    assert {"id": "FV:2/1", "name": "Sport"} in res["result"]["favorites"]

    scene_id = await save(
        call,
        name="Evening",
        area_id="kitchen",
        steps=[
            {"entity_id": "light.kitchen", "mode": "capture"},
            {"entity_id": "cover.kitchen", "mode": "off"},
            {"entity_id": "media_player.sonos_kitchen", "mode": "capture"},
        ],
    )
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = eid(hass, scene_id)
    assert entity_id == "scene.evening"  # follows the first rename of "New 1"
    assert ent_reg.async_get(entity_id).area_id == "kitchen"
    assert hass.states.get(entity_id).attributes["step_count"] == 3
    # the creating edit logs no change; "created" once, under the first id (spec 4.10, review Z3)
    assert [(c.data["action"], c.data["entity_id"]) for c in changes] == [("created", "scene.new_1")]
    assert changes[0].context.user_id is not None

    stored = flat(setup.runtime_data.scenes[scene_id])
    assert stored[0] == {
        "entity_id": "light.kitchen",
        "state": "on",
        "attributes": {"brightness": 128, "color_mode": "brightness"},
    }
    assert stored[2]["music"] == "favorite" and stored[2]["favorite_id"] == "FV:2/1"
    assert [s["domain"] for s in setup.runtime_data.scenes[scene_id]["sequence"]] == ["light", "cover", "media_player"]

    # change the room, then run the scene
    hass.states.async_set("light.kitchen", "off", {})
    turn_on = async_mock_service(hass, "light", "turn_on")
    close = async_mock_service(hass, "cover", "close_cover")
    volume = async_mock_service(hass, "media_player", "volume_set")
    play = async_mock_service(hass, "media_player", "play_media")
    await run_scene(hass, entity_id)
    assert turn_on[0].data["brightness"] == 128
    assert len(close) == 1
    assert volume[0].data["volume_level"] == 0.5
    assert play[0].data["media_content_id"] == "FV:2/1"
    assert play[0].data["media_content_type"] == "favorite_item_id"

    # a later rename keeps the entity id
    res = await call(type=f"{DOMAIN}/update", scene_id=scene_id, edit="e2", name="Dinner")
    assert res["success"], res
    await hass.async_block_till_done()
    assert eid(hass, scene_id) == entity_id
    assert hass.states.get(entity_id).name == "Dinner"
    assert changes[-1].data["action"] == "changed"


async def test_validation(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, resident_token
) -> None:
    """Unreleased devices, wrong modes, duplicate names, missing steps and unknown favorites are rejected."""
    call = await _ws(hass, hass_ws_client, resident_token)

    async def bad(**kw):
        return await make(call, **{"name": "A", "area_id": "kitchen", **kw})

    fav_step = {"entity_id": "media_player.sonos_kitchen", "mode": "music", "music": "favorite", "volume": 0.5}
    for steps, code in (
        ([{"entity_id": "light.unreleased", "mode": "capture"}], "entity_not_allowed"),
        ([{"entity_id": "lock.door", "mode": "capture"}], "invalid_format"),  # no step domain "lock"
        ([{"entity_id": "light.kitchen", "mode": "music"}], "invalid_step"),
        ([{"entity_id": "media_player.kitchen", "mode": "music", "music": "on"}], "invalid_step"),
        ([{**fav_step, "favorite_id": "x"}], "unknown_favorite"),
    ):
        res = await bad(steps=steps)
        assert res["error"]["code"] == code, steps

    assert (await bad(name="   "))["error"]["code"] == "invalid_name"
    assert (await bad(area_id="nowhere"))["error"]["code"] == "invalid_area"
    assert (await bad(image="../secret.jpg"))["error"]["code"] == "invalid_image"
    assert (await call(type=f"{DOMAIN}/update", scene_id="nope", edit="x", name="B"))["error"]["code"] == "not_found"
    sid = await save(call, name="A", area_id="kitchen",
                     steps=[{"entity_id": "media_player.kitchen", "mode": "music", "music": "on", "volume": 0.2}])
    assert (await bad(name="a"))["error"]["code"] == "name_exists"
    assert (await bad(name="A", area_id=None))["success"]  # same name in the house is fine
    other = await save(call, name="B", area_id="kitchen")
    res = await call(type=f"{DOMAIN}/update", scene_id=other, edit="x", name="a ")
    assert res["error"]["code"] == "name_exists"
    assert (await call(type=f"{DOMAIN}/update", scene_id=other, edit="x", name=""))["error"]["code"] == "invalid_name"

    # the same entity twice in one step: the second input replaces the entry
    step_id = setup.runtime_data.scenes[sid]["sequence"][0]["id"]
    off = {"type": f"{DOMAIN}/set_entry", "scene_id": sid, "edit": "e1", "step_id": step_id,
           "entity_id": "media_player.kitchen", "mode": "off"}
    assert (await call(**off))["success"]
    assert flat(setup.runtime_data.scenes[sid]) == [{"entity_id": "media_player.kitchen", "music": "off"}]
    # an input on a step another editor removed: the card reloads
    assert (await call(**{**off, "step_id": "deadbeef"}))["error"]["code"] == "step_missing"
    assert (await call(**{**off, "entity_id": "light.kitchen"}))["error"]["code"] == "entity_not_allowed"


async def test_limits_and_unavailable(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, resident_token
) -> None:
    """Scene and step limits, capturing an unreachable device."""
    hass.config_entries.async_update_entry(setup, options={"scenes_per_area": 1, "steps_per_scene": 1})
    call = await _ws(hass, hass_ws_client, resident_token)
    hass.states.async_set("light.kitchen", "unavailable")
    step = {"entity_id": "light.kitchen", "mode": "capture"}
    res = await make(call, name="X", area_id="kitchen", steps=[step])
    assert res["error"]["code"] == "entity_unavailable"
    hall = [{"entity_id": "light.hall", "mode": "off"}, {"entity_id": "cover.kitchen", "mode": "off"}]
    assert (await make(call, name="X", steps=hall))["error"]["code"] == "too_many_steps"
    sid = await save(call, name="X", area_id="kitchen")
    assert (await make(call, name="Y", area_id="kitchen"))["error"]["code"] == "limit_reached"
    base = {"scene_id": sid, "edit": "e"}
    assert (await call(type=f"{DOMAIN}/add_step", **base, step_type="delay"))["success"]
    res = await call(type=f"{DOMAIN}/add_step", **base, step_type="delay")
    assert res["error"]["code"] == "too_many_steps"  # steps count too, not only entries


async def test_rights(
    hass: HomeAssistant,
    setup: MockConfigEntry,
    hass_ws_client,
    hass_read_only_user: User,
    resident_token: str,
) -> None:
    """Excluded accounts and panels may run but not change; a panel can be released."""
    call = await _ws(hass, hass_ws_client, resident_token)
    sid = await save(direct(setup.runtime_data), name="Any")
    uid = hass_read_only_user.id
    for options, allowed in (
        ({}, True),
        ({CONF_USERS_WITHOUT_EDIT: [uid]}, False),
        ({CONF_PANEL_USERS: [uid]}, False),
        ({CONF_PANEL_USERS: [uid], CONF_PANELS_WITH_EDIT: [uid]}, True),
    ):
        hass.config_entries.async_update_entry(setup, options=options)
        await hass.async_block_till_done()
        listing = await call(type=f"{DOMAIN}/list", scope="_house")
        assert listing["result"]["can_edit"] is allowed
        res = await make(call, name=f"S{len(options)}{allowed}")
        assert res["success"] is allowed
        if not allowed:
            assert res["error"]["code"] == "unauthorized"
            for msg in (
                {"type": f"{DOMAIN}/devices"},
                {"type": f"{DOMAIN}/delete", "scene_id": "x"},
                {"type": f"{DOMAIN}/set_favorite", "scope": "_house", "slot": 0, "scene_id": None},
                {"type": f"{DOMAIN}/duplicate", "scene_id": sid, "suffix": " (copy)", "edit": "x"},
                {"type": f"{DOMAIN}/update", "scene_id": sid, "edit": "x", "transition": 1},
                {"type": f"{DOMAIN}/house_off", "scene_id": sid, "edit": "x", "domain": "light"},
            ):
                assert (await call(**msg))["error"]["code"] == "unauthorized"


async def test_favorites_delete_and_subscribe(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, resident_token
) -> None:
    """Slots follow the scope, deleting empties them and removes the entity; cards are notified."""
    call = await _ws(hass, hass_ws_client, resident_token)
    assert (await call(type=f"{DOMAIN}/subscribe"))["success"]
    cook = await save(call, name="Cook", area_id="kitchen")
    house = await save(call, name="Away", steps=[{"entity_id": "light.hall", "mode": "off"}])
    await hass.async_block_till_done()
    await call(type=f"{DOMAIN}/list", scope="_house")
    assert call.events and call.events[0]["event"] == {"changed": True}

    fav = f"{DOMAIN}/set_favorite"
    assert (await call(type=fav, scope="kitchen", slot=0, scene_id=cook))["success"]
    assert (await call(type=fav, scope="kitchen", slot=2, scene_id=cook))["success"]  # moves, not copies
    assert (await call(type=fav, scope="kitchen", slot=0, scene_id=house))["error"]["code"] == "invalid_slot"
    assert (await call(type=fav, scope="_house", slot=9, scene_id=house))["error"]["code"] == "invalid_slot"
    assert (await call(type=fav, scope="_house", slot=0, scene_id="nope"))["error"]["code"] == "not_found"
    assert (await call(type=fav, scope="made-up", slot=0, scene_id=None))["error"]["code"] == "invalid_slot"
    assert "made-up" not in setup.runtime_data.favorites
    assert (await call(type=fav, scope="_house", slot=0, scene_id=house))["success"]
    assert (await call(type=f"{DOMAIN}/list", scope="kitchen"))["result"]["favorites"] == [None, None, cook, None]
    assert (await call(type=f"{DOMAIN}/list", scope="_house"))["result"]["favorites"][0] == house

    entity_id = eid(hass, cook)
    assert (await call(type=f"{DOMAIN}/delete", scene_id=cook))["success"]
    await hass.async_block_till_done()
    assert hass.states.get(entity_id) is None
    assert er.async_get(hass).async_get(entity_id) is None
    assert (await call(type=f"{DOMAIN}/list", scope="kitchen"))["result"]["favorites"] == [None] * 4
    assert (await call(type=f"{DOMAIN}/delete", scene_id=cook))["error"]["code"] == "not_found"


async def test_skipped_and_failed_steps(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, resident_token
) -> None:
    """Unreachable devices and missing favorites are skipped and logged, the rest runs."""
    call = await _ws(hass, hass_ws_client, resident_token)
    news = {"entity_id": "media_player.sonos_kitchen", "mode": "music", "music": "favorite", "volume": 0.3}
    sid = await save(
        call,
        name="Mix",
        area_id="kitchen",
        steps=[
            {"entity_id": "light.kitchen", "mode": "off"},
            {"entity_id": "cover.kitchen", "mode": "capture"},
            {**news, "favorite_id": "FV:2/2"},
        ],
    )
    await hass.async_block_till_done()
    skipped = async_capture_events(hass, EVENT_SKIPPED)
    hass.states.async_set("cover.kitchen", "unavailable")
    hass.states.async_set("sensor.sonos_favorites", "1", {"items": {"FV:2/1": "Sport"}})
    turn_off = async_mock_service(hass, "light", "turn_off")
    await run_scene(hass, eid(hass, sid))
    assert len(turn_off) == 1
    assert skipped[0].data["entities"] == ["cover.kitchen", "media_player.sonos_kitchen"]


async def test_music_off_on_and_scene_call(hass: HomeAssistant, setup: MockConfigEntry) -> None:
    """Music off and on, a released foreign scene (e.g. KNX), and capture of a stopped player."""
    ent_reg = er.async_get(hass)
    knx = ent_reg.async_get_or_create("scene", "knx", "s1", suggested_object_id="knx_tv")
    ent_reg.async_update_entity(knx.entity_id, labels={"resident_scenes"}, area_id="kitchen")
    hass.states.async_set(knx.entity_id, "unknown")  # scenes are unknown until first run
    stop = async_mock_service(hass, "media_player", "media_stop")
    volume = async_mock_service(hass, "media_player", "volume_set")
    media_play = async_mock_service(hass, "media_player", "media_play")
    scene_call = async_mock_service(hass, "scene", "turn_on")

    store = setup.runtime_data
    call = direct(store, "user")
    steps = [{"entity_id": "media_player.kitchen", "mode": "off"}, {"entity_id": "scene.knx_tv", "mode": "capture"}]
    off = store.scenes[await save(call, name="Quiet", area_id="kitchen", steps=steps)]
    loud = {"entity_id": "media_player.kitchen", "mode": "music", "music": "on", "volume": 0.7}
    on = store.scenes[await save(call, name="Loud", steps=[loud])]
    await store.runner.async_apply(off, flat(off), None)
    await store.runner.async_apply(on, flat(on), None)
    assert len(stop) == 1 and len(media_play) == 1
    assert volume[0].data["volume_level"] == 0.7
    assert scene_call[0].data["entity_id"] == "scene.knx_tv"

    hass.states.async_set("media_player.kitchen", "paused", {"volume_level": 0.4})
    cap = [{"entity_id": "media_player.kitchen", "mode": "capture"}]
    captured = store.scenes[await save(call, name="Cap", steps=cap)]
    assert flat(captured) == [{"entity_id": "media_player.kitchen", "music": "off"}]


async def test_images(
    hass: HomeAssistant,
    setup: MockConfigEntry,
    hass_client,
    hass_client_no_auth,
    hass_ws_client,
    resident_token,
) -> None:
    """Library images are signed, served to logged-in users only, and default per area."""
    folder = Path(hass.config.path("resident_scenes"))
    files = {"kitchen.jpg": b"\xff\xd8 kitchen", "sofa.png": b"png", "notes.txt": b"x"}

    def make_library() -> None:
        folder.mkdir(exist_ok=True)
        for name, data in files.items():
            (folder / name).write_bytes(data)

    def clean() -> None:  # the config folder is shared between tests
        for name in files:
            (folder / name).unlink(missing_ok=True)

    await hass.async_add_executor_job(make_library)
    try:
        await _check_images(hass, hass_client, hass_client_no_auth, hass_ws_client, resident_token)
    finally:
        await hass.async_add_executor_job(clean)


async def _check_images(hass, hass_client, hass_client_no_auth, hass_ws_client, resident_token) -> None:
    call = await _ws(hass, hass_ws_client, resident_token)
    listing = (await call(type=f"{DOMAIN}/devices"))["result"]
    assert [i["name"] for i in listing["images"]] == ["kitchen.jpg", "sofa.png"]
    assert "authSig=" in listing["images"][0]["url"]

    await save(call, name="Pic", area_id="kitchen", image="sofa.png")
    await save(call, name="Default", area_id="kitchen")
    await save(call, name="Plain")
    await hass.async_block_till_done()
    picture = hass.states.get("scene.default").attributes["entity_picture"]
    assert picture.startswith("/api/resident_scenes/image/kitchen.jpg?authSig=")
    assert "entity_picture" not in hass.states.get("scene.plain").attributes

    anonymous = await hass_client_no_auth()
    assert (await anonymous.get(picture)).status == 200  # signed URL works without login
    assert (await anonymous.get("/api/resident_scenes/image/kitchen.jpg")).status == 401
    client = await hass_client()
    assert (await client.get("/api/resident_scenes/image/kitchen.jpg")).status == 200
    assert (await client.get("/api/resident_scenes/image/notes.txt")).status == 404
    assert (await client.get("/api/resident_scenes/image/missing.jpg")).status == 404
    assert (await client.get("/api/resident_scenes/image/.hidden.jpg")).status == 404
    assert (await client.get("/api/resident_scenes/image/..%2Fsecrets.yaml")).status in (400, 404)


async def test_logbook(hass: HomeAssistant) -> None:
    """Changes and skipped steps get readable logbook entries."""
    describers = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))
    event = type("E", (), {"data": {"name": "Eve", "action": "created", "entity_id": "scene.eve"}})
    assert describers[EVENT_CHANGED](event) == {"name": "Eve", "message": "scene created", "entity_id": "scene.eve"}
    event = type("E", (), {"data": {"name": "Eve", "entities": ["light.a", "light.b"]}})
    assert describers[EVENT_SKIPPED](event)["message"] == "skipped light.a, light.b"
    hass.states.async_set("light.a", "on", {"friendly_name": "Sofa"})
    event = type("E", (), {"data": {"name": "Eve", "entities": [], "failed": ["light.a"]}})
    assert describers[EVENT_SKIPPED](event)["message"] == "failed Sofa"


async def test_card_registration(hass: HomeAssistant) -> None:
    """With the frontend loaded the card is added with its version in the URL."""
    assert await async_setup_component(hass, "http", {})
    hass.config.components.add("frontend")
    with patch("homeassistant.components.frontend.add_extra_js_url") as add:
        assert await async_setup_component(hass, DOMAIN, {})
    add.assert_called_once_with(hass, f"/resident_scenes/resident-scenes-card.js?v={VERSION}")


async def test_special_accounts(hass: HomeAssistant, setup: MockConfigEntry) -> None:
    """Admins always edit; system and deactivated accounts never."""
    admin = await hass.auth.async_create_user("Admin", group_ids=["system-admin"])
    system = await hass.auth.async_create_system_user("Bot")
    inactive = await hass.auth.async_create_user("Old")
    await hass.auth.async_deactivate_user(inactive)
    hass.config_entries.async_update_entry(setup, options={CONF_USERS_WITHOUT_EDIT: [admin.id]})
    assert can_edit(setup, admin)
    assert not can_edit(setup, system)
    assert not can_edit(setup, inactive)


async def test_not_loaded(hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, hass_access_token) -> None:
    """Commands answer cleanly while the integration is unloaded."""
    await hass.config_entries.async_unload(setup.entry_id)
    call = await _ws(hass, hass_ws_client, hass_access_token)
    assert (await call(type=f"{DOMAIN}/list", scope="_house"))["error"]["code"] == "not_loaded"


async def test_diagnostics_and_unload(hass: HomeAssistant, setup: MockConfigEntry) -> None:
    """Diagnostics contain no user ids; unloading keeps the data."""
    hass.config_entries.async_update_entry(setup, options={CONF_USERS_WITHOUT_EDIT: ["secret-id"]})
    await save(direct(setup.runtime_data), name="D", steps=[{"entity_id": "light.hall", "mode": "off"}])
    diag = await async_get_config_entry_diagnostics(hass, setup)
    assert diag["options"][CONF_USERS_WITHOUT_EDIT] == 1
    assert "secret-id" not in json.dumps(diag)
    assert diag["scenes"] == 1 and diag["house_scenes"] == 1 and diag["steps"] == 1
    assert await hass.config_entries.async_unload(setup.entry_id)
    assert await hass.config_entries.async_setup(setup.entry_id)
    await hass.async_block_till_done()
    assert len(setup.runtime_data.scenes) == 1
