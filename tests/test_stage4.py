"""Stage 4: room rights per account and the right "Haus-Szenen" (spec 3, acceptance "Raumrechte")."""

from __future__ import annotations

import io

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import (
    CONF_ROOMS,
    CONF_USERS_WITHOUT_HOUSE,
    DOMAIN,
    EVENT_CHANGED,
    EVENT_RIGHTS,
    UPLOAD_URL,
)
from custom_components.resident_scenes.logbook import async_describe_events
from custom_components.resident_scenes.model import can_edit, may_edit, may_see
from homeassistant.auth.models import Group
from homeassistant.auth.permissions.models import PermissionLookup
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)
from tests.conftest import direct, eid, run_scene, save, ws

LIGHT = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}
HALL_OFF = {"entity_id": "light.hall", "mode": "off"}


def cmd(command: str, sid: str, edit: str = "r", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


async def _world(hass, setup):
    """A kitchen scene, a hall scene and the house scene "Abwesend" with both lights off."""
    admin = direct(setup.runtime_data)
    kitchen = await save(admin, name="Kochen", area_id="kitchen", steps=[LIGHT])
    hall = await save(admin, name="Flur", area_id="hall", steps=[HALL_OFF])
    away = await save(admin, name="Abwesend", steps=[{"entity_id": "light.kitchen", "mode": "off"}, HALL_OFF])
    await hass.async_block_till_done()
    return kitchen, hall, away


async def _turn_on(hass, entity_id: str, user_id: str | None) -> None:
    context = Context(user_id=user_id) if user_id else None
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True, context=context)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_room_right(
    hass: HomeAssistant, setup, hass_ws_client, resident_token, hass_read_only_user, hass_access_token
):
    """Acceptance "Raumrecht": limited to one room, the account sees, creates and runs only there."""
    kitchen, hall, away = await _world(hass, setup)
    uid = hass_read_only_user.id
    admin = await ws(hass, hass_ws_client, hass_access_token)
    rights = (await admin(type=f"{DOMAIN}/rights"))["result"]
    assert rights["room_rights"][uid] == {"rooms": None, "house": True}  # default: all rooms, house right
    assert {a["area_id"] for a in rights["areas"]} == {"kitchen", "hall"}
    assert (await admin(type=f"{DOMAIN}/set_rooms", user_id=uid, rooms=["kitchen"], house=True))["success"]

    res = await ws(hass, hass_ws_client, resident_token)
    listing = (await res(type=f"{DOMAIN}/list", scope="kitchen"))["result"]
    assert listing["access"] and listing["can_edit"] and [s["id"] for s in listing["scenes"]] == [kitchen]
    other = (await res(type=f"{DOMAIN}/list", scope="hall"))["result"]
    assert not other["access"] and not other["can_edit"] and other["scenes"] == [] and other["favorites"] == [None] * 4

    # direct calls of the interface for the hall scene are rejected, the scene stays as it is
    version = setup.runtime_data.scenes[hall]["version"]
    for msg in (
        {"type": f"{DOMAIN}/scene", "scene_id": hall},
        cmd("update", hall, name="Mine"),
        cmd("add_step", hall, step_type="delay"),
        cmd("duplicate", hall, suffix=" x"),
        {"type": f"{DOMAIN}/delete", "scene_id": hall},
        {"type": f"{DOMAIN}/undo", "scene_id": hall, "version": version},
        {"type": f"{DOMAIN}/create", "area_id": "hall", "name": "Neu", "edit": "c"},
        {"type": f"{DOMAIN}/devices", "area_id": "hall"},
        {"type": f"{DOMAIN}/set_favorite", "scope": "hall", "slot": 0, "scene_id": hall},
    ):
        assert (await res(**msg))["error"]["code"] == "no_access", msg
    assert setup.runtime_data.scenes[hall]["version"] == version

    # in its room it creates and runs a scene
    sid = await save(res, name="Spielen", area_id="kitchen", steps=[LIGHT])
    devices = (await res(type=f"{DOMAIN}/devices", area_id="kitchen"))["result"]["entities"]
    assert {d["area_id"] for d in devices} == {"kitchen"}
    assert (await res(type=f"{DOMAIN}/set_favorite", scope="kitchen", slot=0, scene_id=sid))["success"]
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    await _turn_on(hass, eid(hass, sid), uid)
    assert on

    # scene.turn_on of the hall scene with the user: rejected and in the logbook
    refused = async_capture_events(hass, EVENT_CHANGED)
    with pytest.raises(Unauthorized):
        await _turn_on(hass, eid(hass, hall), uid)
    assert not off
    assert refused[0].data["action"] == "not run: no right for its room"
    assert refused[0].context.user_id == uid


async def test_house_right(
    hass: HomeAssistant, setup, hass_ws_client, resident_token, hass_read_only_user, hass_access_token
):
    """Acceptance "Haus-Szenen": with the right the house scene runs fully, without it nothing is shown."""
    kitchen, hall, away = await _world(hass, setup)
    store = setup.runtime_data
    await store.async_set_favorite("_house", 0, away)
    uid = hass_read_only_user.id
    admin = await ws(hass, hass_ws_client, hass_access_token)
    assert (await admin(type=f"{DOMAIN}/set_rooms", user_id=uid, rooms=["kitchen"], house=True))["success"]
    res = await ws(hass, hass_ws_client, resident_token)

    house = (await res(type=f"{DOMAIN}/list", scope="_house"))["result"]
    assert house["access"] and not house["can_edit"]  # run only: editing a house scene needs all rooms
    assert [s["id"] for s in house["scenes"]] == [away] and house["favorites"][0] == away
    off = async_mock_service(hass, "light", "turn_off")
    await _turn_on(hass, eid(hass, away), uid)
    assert sorted(c.data["entity_id"][0] if isinstance(c.data["entity_id"], list) else c.data["entity_id"]
                  for c in off) == ["light.hall", "light.kitchen"]  # also the hall, without its room right
    for msg in (
        cmd("update", away, name="Weg"),
        {"type": f"{DOMAIN}/create", "area_id": None, "name": "Neu", "edit": "c"},
        {"type": f"{DOMAIN}/devices"},
        {"type": f"{DOMAIN}/set_favorite", "scope": "_house", "slot": 1, "scene_id": away},
    ):
        assert (await res(**msg))["error"]["code"] == "no_access", msg
    # a kitchen scene shows no house scene calling it to an account without the house right
    detail = (await res(type=f"{DOMAIN}/scene", scene_id=kitchen))["result"]
    assert detail["used_in"]["scenes"] == []

    assert (await admin(type=f"{DOMAIN}/set_rooms", user_id=uid, rooms=["kitchen"], house=False))["success"]
    assert setup.options[CONF_USERS_WITHOUT_HOUSE] == [uid]
    house = (await res(type=f"{DOMAIN}/list", scope="_house"))["result"]
    assert not house["access"] and house["scenes"] == [] and house["favorites"] == [None] * 4
    assert (await res(type=f"{DOMAIN}/scene", scene_id=away))["error"]["code"] == "no_access"
    with pytest.raises(Unauthorized):
        await _turn_on(hass, eid(hass, away), uid)
    assert (await res(**cmd("update", away, name="Weg")))["error"]["code"] == "no_access"


async def test_management_and_logbook(
    hass: HomeAssistant, setup, hass_ws_client, resident_token, hass_read_only_user, hass_access_token
):
    """Acceptance "Verwaltung": a main user limits a resident to two rooms of a floor; at once and in the logbook."""
    floor = fr.async_get(hass).async_create("Obergeschoss", level=1)
    areas = ar.async_get(hass)
    kid = areas.async_create("Kinderzimmer", floor_id=floor.floor_id)
    bath = areas.async_create("Bad", floor_id=floor.floor_id)
    other = await hass.auth.async_create_user("Kind", group_ids=["system-users"])
    hass.config_entries.async_update_entry(setup, options={"main_users": [hass_read_only_user.id]})
    main = await ws(hass, hass_ws_client, resident_token)
    rights = (await main(type=f"{DOMAIN}/rights"))["result"]
    assert rights["floors"] == [{"floor_id": floor.floor_id, "name": "Obergeschoss"}]
    assert {"area_id": kid.id, "name": "Kinderzimmer", "floor_id": floor.floor_id} in rights["areas"]
    events = async_capture_events(hass, EVENT_RIGHTS)
    set_rooms = {"type": f"{DOMAIN}/set_rooms", "user_id": other.id, "house": True}
    assert (await main(**set_rooms, rooms=[kid.id, bath.id, kid.id]))["success"]
    assert setup.options[CONF_ROOMS] == {other.id: [kid.id, bath.id]}
    entry = setup
    assert may_see(hass, entry, other, kid.id) and not may_see(hass, entry, other, "kitchen")  # at once
    assert events[-1].data == {"user": "Kind", "rooms": ["Kinderzimmer", "Bad"], "house": True}
    assert events[-1].context.user_id == hass_read_only_user.id  # the account that made the change
    describers = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))
    assert describers[EVENT_RIGHTS](events[-1])["message"] == "rooms: Kinderzimmer, Bad; may run house scenes"

    assert (await main(**set_rooms, rooms=["nowhere"]))["error"]["code"] == "invalid_area"
    own = {**set_rooms, "user_id": hass_read_only_user.id}
    assert (await main(**own, rooms=None))["error"]["code"] == "unauthorized"
    assert (await main(**{**set_rooms, "house": False}, rooms=None))["success"]
    assert setup.options[CONF_ROOMS] == {}
    assert describers[EVENT_RIGHTS](events[-1])["message"] == "rooms: all rooms; may not run house scenes"
    # the installer's settings form keeps the room rights
    flow = await hass.config_entries.options.async_init(setup.entry_id)
    flow = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "settings"})
    form = {"label": "resident_scenes", "scenes_per_area": 20, "house_scenes": 30, "steps_per_scene": 150,
            "name_length": 30, "max_delay": 600, "image_side": 1600, "image_kb": 500, "image_count": 200,
            "favorite_slots": 4, "image_dir": "resident_scenes"}
    result = await hass.config_entries.options.async_configure(flow["flow_id"], form)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup.options[CONF_USERS_WITHOUT_HOUSE] == [other.id]

    # an account without the main user role manages nothing
    hass.config_entries.async_update_entry(setup, options={})
    assert (await main(**set_rooms, rooms=None))["error"]["code"] == "unauthorized"


async def test_new_and_deleted_room(hass: HomeAssistant, setup, hass_read_only_user):
    """Acceptance "Neuer Raum" and spec 3: a deleted room drops its right, also for a new room of the same id."""
    user = hass_read_only_user
    other = await hass.auth.async_create_user("Alle", group_ids=["system-users"])
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {user.id: ["kitchen", "hall"]}})
    areas = ar.async_get(hass)
    garden = areas.async_create("Garden")
    assert may_see(hass, setup, other, garden.id)  # all rooms: at once
    assert not may_see(hass, setup, user, garden.id)  # limited: only once ticked
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {user.id: ["kitchen", "hall", garden.id]}})
    assert may_see(hass, setup, user, garden.id)

    store = setup.runtime_data
    hall_scene = await save(direct(store), name="Flur", area_id="hall", steps=[HALL_OFF])
    areas.async_delete("hall")
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {user.id: ["kitchen", garden.id]}
    assert store.scenes[hall_scene]["area_id"] is None  # its scenes are house scenes now, under the house right
    new_hall = areas.async_create("Hall")
    assert new_hall.id == "hall" and not may_see(hass, setup, user, "hall")
    # deleted while Home Assistant was stopped: dropped on load
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {user.id: ["kitchen", "gone"]}})
    await hass.config_entries.async_reload(setup.entry_id)
    await hass.async_block_till_done()
    assert setup.options[CONF_ROOMS] == {user.id: ["kitchen"]}


async def test_without_user_and_update(hass: HomeAssistant, setup):
    """Acceptance "Ohne Benutzer" and "Update": calls without a user always run; old options mean all rooms."""
    kitchen, hall, away = await _world(hass, setup)
    user = await hass.auth.async_create_user("Kind", group_ids=["system-users"])
    assert all(may_see(hass, setup, user, a) for a in ("kitchen", "hall", None))  # options of 0.3.x: no keys
    options = {CONF_ROOMS: {user.id: []}, CONF_USERS_WITHOUT_HOUSE: [user.id]}
    hass.config_entries.async_update_entry(setup, options=options)
    off = async_mock_service(hass, "light", "turn_off")
    await run_scene(hass, eid(hass, hall))  # a schedule: no user, no account has the hall
    assert off


async def test_revoked_during_edit_and_capture(
    hass: HomeAssistant, setup, hass_ws_client, resident_token, hass_read_only_user, hass_client
):
    """Spec 3 and 5.6: a right taken away during an edit rejects the next input; capture checks the room too."""
    res = await ws(hass, hass_ws_client, resident_token)
    sid = await save(res, name="Spielen", area_id="kitchen", steps=[LIGHT])
    assert (await res(**cmd("update", sid, "x", name="Spiel")))["success"]
    uid = hass_read_only_user.id
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {uid: ["hall"]}})
    await hass.async_block_till_done()
    assert (await res(**cmd("update", sid, "x", name="Mein Spiel")))["error"]["code"] == "no_access"
    assert setup.runtime_data.scenes[sid]["name"] == "Spiel"
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "capture", {"entity_id": eid(hass, sid)}, blocking=True, context=Context(user_id=uid)
        )
    # no room at all: no image upload either
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {uid: []}})
    client = await hass_client(resident_token)
    resp = await client.post(UPLOAD_URL, data={"file": io.BytesIO(b"x")})
    assert resp.status == 403


async def test_control_right_per_device(
    hass: HomeAssistant, setup, hass_ws_client, resident_token, hass_read_only_user
):
    """Spec 3: an account Home Assistant limits to the kitchen edits the scenes of the kitchen only."""
    user = hass_read_only_user
    await ws(hass, hass_ws_client, resident_token)  # puts the account in the user group
    kitchen = ["light.kitchen", "cover.kitchen", "media_player.kitchen", "media_player.sonos_kitchen"]
    kitchen.append("climate.kitchen")
    user.groups = [Group(name="Kitchen only", policy={"entities": {"entity_ids": dict.fromkeys(kitchen, True)}})]
    if user.perm_lookup is None:
        user.perm_lookup = PermissionLookup(er.async_get(hass), dr.async_get(hass))
    user.invalidate_cache()
    assert can_edit(setup, user)  # no longer needs control of all entities
    assert may_see(hass, setup, user, "kitchen") and may_edit(hass, setup, user, "kitchen")
    assert not may_see(hass, setup, user, "hall")  # room right, but not the devices of the hall
    assert not may_edit(hass, setup, user, None)  # house scenes need all rooms
    res = await ws(hass, hass_ws_client, resident_token)
    assert (await res(type=f"{DOMAIN}/create", area_id="kitchen", name="Neu", edit="c"))["success"]
    assert (await res(type=f"{DOMAIN}/create", area_id="hall", name="Neu", edit="d"))["error"]["code"] == "no_access"
    user.groups = [Group(name="Read only", policy={"entities": {"all": {"read": True}}})]
    user.invalidate_cache()
    assert not can_edit(setup, user)  # a read-only account still may not edit
