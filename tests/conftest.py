"""Fixtures for Resident Scenes tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.resident_scenes.const import DOMAIN
from custom_components.resident_scenes.model import ValidationError, allowed_entities, entity_area, entries
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, label_registry as lr
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the custom integration."""


@pytest.fixture
async def setup(hass: HomeAssistant) -> MockConfigEntry:
    """Kitchen with a released light, cover, media player and Sonos player, a hall light; set up the integration."""
    assert await async_setup_component(hass, "http", {})
    kitchen = ar.async_get(hass).async_create("Kitchen")
    hall = ar.async_get(hass).async_create("Hall")
    lr.async_get(hass).async_create("resident_scenes")
    ent_reg = er.async_get(hass)
    for domain, platform, uid, area in (
        ("light", "test", "kitchen", kitchen.id),
        ("cover", "test", "kitchen", kitchen.id),
        ("media_player", "test", "kitchen", kitchen.id),
        ("media_player", "sonos", "sonos_kitchen", kitchen.id),
        ("climate", "test", "kitchen", kitchen.id),
        ("light", "test", "hall", hall.id),
        ("lock", "test", "door", kitchen.id),
    ):
        entry = ent_reg.async_get_or_create(domain, platform, uid, suggested_object_id=uid)
        ent_reg.async_update_entity(entry.entity_id, area_id=area, labels={"resident_scenes"})
    ent_reg.async_get_or_create("light", "test", "unreleased", suggested_object_id="unreleased")
    fav = ent_reg.async_get_or_create("sensor", "sonos", "favorites", suggested_object_id="sonos_favorites")
    hass.states.async_set(fav.entity_id, "2", {"items": {"FV:2/1": "Sport", "FV:2/2": "News"}})
    hass.states.async_set(
        "light.kitchen",
        "on",
        {"brightness": 128, "color_mode": "brightness", "supported_color_modes": ["color_temp", "hs"],
         "min_color_temp_kelvin": 2000, "max_color_temp_kelvin": 6500},
    )
    hass.states.async_set("light.hall", "on", {"brightness": 255, "color_mode": "brightness"})
    hass.states.async_set("cover.kitchen", "open", {"current_position": 70, "supported_features": 135})
    hass.states.async_set("media_player.kitchen", "playing", {"volume_level": 0.4, "media_title": "Sport"})
    hass.states.async_set("media_player.sonos_kitchen", "playing", {"volume_level": 0.5, "media_title": "Sport"})
    hass.states.async_set(
        "climate.kitchen", "heat", {"hvac_modes": ["off", "heat"], "temperature": 21, "min_temp": 7, "max_temp": 30}
    )
    hass.states.async_set("lock.door", "locked")

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def resident_token(hass: HomeAssistant, hass_read_only_user: User, hass_read_only_access_token: str) -> str:
    """Token of an ordinary resident account (group system-users, no admin)."""
    hass_read_only_user.groups = [await hass.auth.async_get_group(GROUP_ID_USER)]
    hass_read_only_user.invalidate_cache()
    return hass_read_only_access_token


async def run_scene(hass: HomeAssistant, entity_id: str) -> None:
    """Run a scene and wait for the script helper to finish all batches without delay."""
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)


async def ws(hass: HomeAssistant, hass_ws_client, token: str):
    """Return a function sending one command and returning its reply; events are collected."""
    client = await hass_ws_client(hass, token)
    counter = iter(range(1, 10000))

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


def direct(store, user_id: str | None = None, admin: bool = True):
    """Like ws(), but calls the store directly (as installer automation or admin)."""

    async def call(**msg):
        kind = msg["type"].split("/")[1]
        try:
            if kind == "create":
                scene = await store.async_create(msg.get("area_id"), msg["name"], msg["edit"], user_id)
                result = {"scene_id": scene["id"], "version": scene["version"]}
            elif kind == "devices":
                allowed = allowed_entities(store.hass, store.entry)
                areas = [{"entity_id": e, "area_id": entity_area(store.hass, r)} for e, r in allowed.items()]
                result = {"entities": areas}
            elif kind == "delete":
                await store.async_delete_scene(msg["scene_id"], admin)
                result = None
            else:
                scene, _, extra = await store.async_input(msg, user_id, admin)
                result = {"version": scene["version"], **extra}
        except ValidationError as err:
            return {"success": False, "error": {"code": err.code, "message": str(err)}}
        return {"success": True, "result": result}

    return call


async def make(call, name: str = "Scene", area_id: str | None = None, steps=(), edit: str = "e1", **fields):
    """Build a scene with the editor commands from a 0.2.x style step list.

    Delays start a delay step; device steps are grouped per (area, domain) between delays.
    Returns the reply of the first failing command (the half-made scene is deleted) or a
    success reply with the scene id.
    """
    res = await call(type=f"{DOMAIN}/create", area_id=area_id, name="New", edit=edit)
    if not res["success"]:
        return res
    sid = res["result"]["scene_id"]
    base = {"scene_id": sid, "edit": edit}
    res = await call(type=f"{DOMAIN}/update", **base, name=name, **fields)
    devices = await call(type=f"{DOMAIN}/devices")
    areas = {e["entity_id"]: e["area_id"] for e in devices["result"]["entities"]} if devices["success"] else {}
    groups: dict = {}
    for raw in steps:
        if not res["success"]:
            break
        raw = dict(raw)
        if delay := raw.pop("delay", 0):
            res = await call(type=f"{DOMAIN}/add_step", **base, step_type="delay")
            res = await call(type=f"{DOMAIN}/set_delay", **base, step_id=res["result"]["step_id"], seconds=delay)
            groups = {}
            if not res["success"]:
                break
        if raw.get("mode") == "scene":
            res = await call(type=f"{DOMAIN}/add_step", **base, step_type="scene", target=raw["scene_id"])
            continue
        key = (area_id or areas.get(raw["entity_id"]), raw["entity_id"].split(".")[0])
        if key not in groups:
            res = await call(type=f"{DOMAIN}/add_step", **base, step_type="group", domain=key[1], area_id=key[0])
            if not res["success"]:
                break
            groups[key] = res["result"]["step_id"]
        res = await call(type=f"{DOMAIN}/set_entry", **base, step_id=groups[key], **raw)
    if not res["success"]:
        await call(type=f"{DOMAIN}/delete", scene_id=sid)
        return res
    return {"success": True, "result": {"scene_id": sid, "version": res["result"]["version"]}}


async def save(call, **payload) -> str:
    """make() that must succeed; returns the scene id."""
    res = await make(call, **payload)
    assert res["success"], res
    return res["result"]["scene_id"]


def flat(scene: dict) -> list[dict]:
    """Entries and scene steps of a stored scene, in order."""
    return list(entries(scene["sequence"]))


def eid(hass: HomeAssistant, scene_id: str) -> str | None:
    """Entity id of a scene."""
    return er.async_get(hass).async_get_entity_id("scene", DOMAIN, scene_id)
