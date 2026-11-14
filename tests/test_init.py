"""Tests for Resident Scenes: rights, saving, slots, activation, images."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

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
from custom_components.resident_scenes.model import async_activate, can_edit
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

ROOT = Path(__file__).parent.parent / "custom_components" / DOMAIN


async def _ws(hass, hass_ws_client, token):
    client = await hass_ws_client(hass, token)
    counter = iter(range(1, 1000))

    async def call(**msg):
        msg_id = next(counter)
        await client.send_json({"id": msg_id, **msg})
        while True:  # subscription events may arrive in between
            reply = await client.receive_json()
            if reply["type"] == "event":
                call.events.append(reply)
            elif reply["id"] == msg_id:
                return reply

    call.events = []
    return call


def test_versions_match() -> None:
    """Manifest, constant and card carry the same version."""
    manifest = json.loads((ROOT / "manifest.json").read_text())
    card = (ROOT / "frontend" / "resident-scenes-card.js").read_text()
    assert manifest["version"] == VERSION
    assert f'const VERSION = "{VERSION}";' in card


async def test_flows(hass: HomeAssistant) -> None:
    """Config flow creates one entry, options store numbers as int."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "label": "resident_scenes",
            "scenes_per_area": 5.0,
            "house_scenes": 30,
            "steps_per_scene": 150,
            "name_length": 30,
            "favorite_slots": 4,
            "image_dir": "resident_scenes",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["scenes_per_area"] == 5


async def test_create_capture_and_activate(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, hass_read_only_access_token
) -> None:
    """A non-admin creates a scene from the current state; running it restores it."""
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    changes = []
    hass.bus.async_listen(EVENT_CHANGED, changes.append)

    res = await call(type=f"{DOMAIN}/devices", area_id="kitchen")
    assert {e["entity_id"] for e in res["result"]["entities"]} == {
        "light.kitchen",
        "cover.kitchen",
        "media_player.kitchen",
    }  # no lock, no unlabelled light, no other area
    assert {"id": "FV:2/1", "name": "Sport"} in res["result"]["favorites"]

    res = await call(
        type=f"{DOMAIN}/save",
        name="Evening",
        area_id="kitchen",
        steps=[
            {"entity_id": "light.kitchen", "mode": "capture"},
            {"entity_id": "cover.kitchen", "mode": "off"},
            {"entity_id": "media_player.kitchen", "mode": "capture"},
        ],
    )
    assert res["success"], res
    scene_id = res["result"]["scene_id"]
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id("scene", DOMAIN, scene_id)
    assert entity_id == "scene.evening"
    assert ent_reg.async_get(entity_id).area_id == "kitchen"
    assert hass.states.get(entity_id).attributes["step_count"] == 3
    assert changes[0].data["action"] == "created"
    assert changes[0].context.user_id is not None

    stored = setup.runtime_data.scenes[scene_id]["steps"]
    assert stored[0] == {
        "entity_id": "light.kitchen",
        "state": "on",
        "attributes": {"brightness": 128, "color_mode": "brightness"},
    }
    assert stored[2]["music"] == "favorite" and stored[2]["favorite_id"] == "FV:2/1"

    # change the room, then run the scene
    hass.states.async_set("light.kitchen", "off", {})
    turn_on = async_mock_service(hass, "light", "turn_on")
    close = async_mock_service(hass, "cover", "close_cover")
    volume = async_mock_service(hass, "media_player", "volume_set")
    play = async_mock_service(hass, "media_player", "play_media")
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()
    assert turn_on[0].data["brightness"] == 128
    assert len(close) == 1
    assert volume[0].data["volume_level"] == 0.4
    assert play[0].data["media_content_id"] == "FV:2/1"
    assert play[0].data["media_content_type"] == "favorite_item_id"

    # rename keeps the entity id
    res = await call(
        type=f"{DOMAIN}/save",
        scene_id=scene_id,
        version=1,
        name="Dinner",
        area_id="kitchen",
        steps=[{"entity_id": "light.kitchen", "mode": "keep"}],
    )
    assert res["success"], res
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).name == "Dinner"


async def test_validation(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, hass_read_only_access_token
) -> None:
    """Unreleased devices, duplicate names, stale versions and unknown favorites are rejected."""
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)

    async def save(**kw):
        return await call(type=f"{DOMAIN}/save", **{"name": "A", "area_id": "kitchen", "steps": [], **kw})

    fav_step = {"entity_id": "media_player.kitchen", "mode": "music", "music": "favorite", "volume": 0.5}
    for steps, code in (
        ([{"entity_id": "light.unreleased", "mode": "capture"}], "entity_not_allowed"),
        ([{"entity_id": "lock.door", "mode": "capture"}], "entity_not_allowed"),
        ([{"entity_id": "light.kitchen", "mode": "keep"}], "invalid_step"),
        ([{"entity_id": "light.kitchen", "mode": "music"}], "invalid_step"),
        ([{"entity_id": "media_player.kitchen", "mode": "music", "music": "on"}], "invalid_step"),
        ([{"entity_id": "light.kitchen", "mode": "capture"}] * 2, "duplicate_entity"),
        ([{**fav_step, "favorite_id": "x"}], "unknown_favorite"),
    ):
        res = await save(steps=steps)
        assert res["error"]["code"] == code

    assert (await save(name="   "))["error"]["code"] == "invalid_name"
    assert (await save(area_id="nowhere"))["error"]["code"] == "invalid_area"
    assert (await save(image="../secret.jpg"))["error"]["code"] == "invalid_image"
    assert (await save(scene_id="nope", version=1))["error"]["code"] == "not_found"
    assert (await save(copy_from="nope"))["error"]["code"] == "not_found"
    first = await save(steps=[{"entity_id": "media_player.kitchen", "mode": "music", "music": "on", "volume": 0.2}])
    assert first["success"]
    assert (await save(name="a"))["error"]["code"] == "name_exists"
    assert (await save(name="A", area_id=None))["success"]  # same name in the house is fine

    scene_id = first["result"]["scene_id"]
    keep = [{"entity_id": "media_player.kitchen", "mode": "keep"}]
    ok = await save(scene_id=scene_id, version=1, name="B", steps=keep)
    assert ok["success"]
    assert (await save(scene_id=scene_id, version=1, name="C"))["error"]["code"] == "version_conflict"
    copy = await save(name="B (copy)", copy_from=scene_id, steps=keep)
    assert copy["success"]


async def test_limits_and_unavailable(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, hass_read_only_access_token
) -> None:
    """Scene and step limits, capturing an unreachable device."""
    hass.config_entries.async_update_entry(setup, options={"scenes_per_area": 1, "steps_per_scene": 1})
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    hass.states.async_set("light.kitchen", "unavailable")
    step = {"entity_id": "light.kitchen", "mode": "capture"}
    res = await call(type=f"{DOMAIN}/save", name="X", area_id="kitchen", steps=[step])
    assert res["error"]["code"] == "entity_unavailable"
    hall = [{"entity_id": "light.hall", "mode": "off"}, {"entity_id": "cover.kitchen", "mode": "off"}]
    assert (await call(type=f"{DOMAIN}/save", name="X", steps=hall))["error"]["code"] == "too_many_steps"
    assert (await call(type=f"{DOMAIN}/save", name="X", area_id="kitchen", steps=[]))["success"]
    res = await call(type=f"{DOMAIN}/save", name="Y", area_id="kitchen", steps=[])
    assert res["error"]["code"] == "limit_reached"


async def test_rights(
    hass: HomeAssistant,
    setup: MockConfigEntry,
    hass_ws_client,
    hass_read_only_user: User,
    hass_read_only_access_token: str,
) -> None:
    """Excluded accounts and panels may run but not change; a panel can be released."""
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    uid = hass_read_only_user.id
    for options, allowed in (
        ({}, True),
        ({CONF_USERS_WITHOUT_EDIT: [uid]}, False),
        ({CONF_PANEL_USERS: [uid]}, False),
        ({CONF_PANEL_USERS: [uid], CONF_PANELS_WITH_EDIT: [uid]}, True),
    ):
        hass.config_entries.async_update_entry(setup, options=options)
        await hass.async_block_till_done()
        listing = await call(type=f"{DOMAIN}/list")
        assert listing["result"]["can_edit"] is allowed
        res = await call(type=f"{DOMAIN}/save", name=f"S{len(options)}{allowed}", steps=[])
        assert res["success"] is allowed
        if not allowed:
            assert res["error"]["code"] == "unauthorized"
            for msg in (
                {"type": f"{DOMAIN}/devices"},
                {"type": f"{DOMAIN}/delete", "scene_id": "x"},
                {"type": f"{DOMAIN}/set_favorite", "scope": "_house", "slot": 0, "scene_id": None},
            ):
                assert (await call(**msg))["error"]["code"] == "unauthorized"


async def test_favorites_delete_and_subscribe(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, hass_read_only_access_token
) -> None:
    """Slots follow the scope, deleting empties them and removes the entity; cards are notified."""
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    assert (await call(type=f"{DOMAIN}/subscribe"))["success"]
    cook = (await call(type=f"{DOMAIN}/save", name="Cook", area_id="kitchen", steps=[]))["result"]["scene_id"]
    away_steps = [{"entity_id": "light.hall", "mode": "off"}]
    house = (await call(type=f"{DOMAIN}/save", name="Away", steps=away_steps))["result"]["scene_id"]
    await hass.async_block_till_done()
    await call(type=f"{DOMAIN}/list")
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
    listing = (await call(type=f"{DOMAIN}/list"))["result"]
    assert listing["favorites"]["kitchen"] == [None, None, cook, None]
    assert listing["favorites"]["_house"][0] == house

    entity_id = er.async_get(hass).async_get_entity_id("scene", DOMAIN, cook)
    assert (await call(type=f"{DOMAIN}/delete", scene_id=cook))["success"]
    await hass.async_block_till_done()
    assert hass.states.get(entity_id) is None
    assert er.async_get(hass).async_get(entity_id) is None
    assert (await call(type=f"{DOMAIN}/list"))["result"]["favorites"]["kitchen"] == [None] * 4
    assert (await call(type=f"{DOMAIN}/delete", scene_id=cook))["error"]["code"] == "not_found"

    # moving a scene to another scope empties its slots
    res = await call(
        type=f"{DOMAIN}/save",
        scene_id=house,
        version=1,
        name="Away",
        area_id="kitchen",
        steps=[{"entity_id": "light.hall", "mode": "keep"}],
    )
    assert res["success"]
    assert (await call(type=f"{DOMAIN}/list"))["result"]["favorites"]["_house"] == [None] * 4


async def test_skipped_and_failed_steps(
    hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client, hass_read_only_access_token
) -> None:
    """Unreachable devices and missing favorites are skipped and logged, the rest runs."""
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    news = {"entity_id": "media_player.kitchen", "mode": "music", "music": "favorite", "volume": 0.3}
    res = await call(
        type=f"{DOMAIN}/save",
        name="Mix",
        area_id="kitchen",
        steps=[
            {"entity_id": "light.kitchen", "mode": "off"},
            {"entity_id": "cover.kitchen", "mode": "capture"},
            {**news, "favorite_id": "FV:2/2"},
        ],
    )
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id("scene", DOMAIN, res["result"]["scene_id"])
    skipped = []
    hass.bus.async_listen(EVENT_SKIPPED, skipped.append)
    hass.states.async_set("cover.kitchen", "unavailable")
    hass.states.async_set("sensor.sonos_favorites", "1", {"items": {"FV:2/1": "Sport"}})
    turn_off = async_mock_service(hass, "light", "turn_off")
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()
    assert len(turn_off) == 1
    assert skipped[0].data["entities"] == ["cover.kitchen", "media_player.kitchen"]


async def test_music_off_on_and_scene_call(hass: HomeAssistant, setup: MockConfigEntry, hass_ws_client) -> None:
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
    off = await store.async_save_scene(
        {
            "name": "Quiet",
            "area_id": "kitchen",
            "steps": [
                {"entity_id": "media_player.kitchen", "mode": "off"},
                {"entity_id": "scene.knx_tv", "mode": "capture"},
            ],
        },
        "user",
    )
    loud = {"entity_id": "media_player.kitchen", "mode": "music", "music": "on", "volume": 0.7}
    on = await store.async_save_scene({"name": "Loud", "steps": [loud]}, "user")
    await async_activate(hass, off, None)
    await async_activate(hass, on, None)
    assert len(stop) == 1 and len(media_play) == 1
    assert volume[0].data["volume_level"] == 0.7
    assert scene_call[0].data["entity_id"] == "scene.knx_tv"

    hass.states.async_set("media_player.kitchen", "paused", {"volume_level": 0.4})
    hass.states.async_set("light.kitchen", "unknown")
    captured = await store.async_save_scene(
        {"name": "Cap", "steps": [{"entity_id": "media_player.kitchen", "mode": "capture"}]}, "user"
    )
    assert captured["steps"] == [{"entity_id": "media_player.kitchen", "music": "off"}]


async def test_images(
    hass: HomeAssistant,
    setup: MockConfigEntry,
    hass_client,
    hass_client_no_auth,
    hass_ws_client,
    hass_read_only_access_token,
) -> None:
    """Library images are signed, served to logged-in users only, and default per area."""
    def make_library() -> None:
        folder = Path(hass.config.path("resident_scenes"))
        folder.mkdir(exist_ok=True)
        (folder / "kitchen.jpg").write_bytes(b"\xff\xd8 kitchen")
        (folder / "sofa.png").write_bytes(b"png")
        (folder / "notes.txt").write_text("x")

    await hass.async_add_executor_job(make_library)
    call = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    listing = (await call(type=f"{DOMAIN}/list"))["result"]
    assert [i["name"] for i in listing["images"]] == ["kitchen.jpg", "sofa.png"]
    assert "authSig=" in listing["images"][0]["url"]

    assert (await call(type=f"{DOMAIN}/save", name="Pic", area_id="kitchen", image="sofa.png", steps=[]))["success"]
    assert (await call(type=f"{DOMAIN}/save", name="Default", area_id="kitchen", steps=[]))["success"]
    assert (await call(type=f"{DOMAIN}/save", name="Plain", steps=[]))["success"]
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
    assert (await call(type=f"{DOMAIN}/list"))["error"]["code"] == "not_loaded"


async def test_diagnostics_and_unload(hass: HomeAssistant, setup: MockConfigEntry) -> None:
    """Diagnostics contain no user ids; unloading keeps the data."""
    hass.config_entries.async_update_entry(setup, options={CONF_USERS_WITHOUT_EDIT: ["secret-id"]})
    await setup.runtime_data.async_save_scene({"name": "D", "steps": []}, "user")
    diag = await async_get_config_entry_diagnostics(hass, setup)
    assert diag["options"][CONF_USERS_WITHOUT_EDIT] == 1
    assert "secret-id" not in json.dumps(diag)
    assert diag["scenes"] == 1 and diag["house_scenes"] == 1
    assert await hass.config_entries.async_unload(setup.entry_id)
    assert await hass.config_entries.async_setup(setup.entry_id)
    await hass.async_block_till_done()
    assert len(setup.runtime_data.scenes) == 1
