"""WebSocket commands of the card. Open to all users, rights are checked here."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    CONF_FAVORITE_SLOTS,
    CONF_NAME_LENGTH,
    DOMAIN,
    EVENT_CHANGED,
    HOUSE,
    SIGNAL_CHANGED,
    VERSION,
)
from .model import ValidationError, allowed_entities, can_edit, entity_area, music_favorites, opt
from .store import SceneStore

type Connection = websocket_api.ActiveConnection

STEP_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): str,
        vol.Required("mode"): vol.In(["capture", "off", "keep", "music"]),
        vol.Optional("music"): vol.In(["off", "on", "favorite"]),
        vol.Optional("volume"): vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
        vol.Optional("favorite_id"): str,
    }
)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands."""
    for command in (ws_list, ws_devices, ws_save, ws_delete, ws_set_favorite, ws_subscribe):
        websocket_api.async_register_command(hass, command)


def _store(hass: HomeAssistant, connection: Connection, msg_id: int) -> SceneStore | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    connection.send_error(msg_id, "not_loaded", "Resident Scenes is not set up")
    return None


def _editor(hass: HomeAssistant, connection: Connection, msg_id: int) -> SceneStore | None:
    """Return the store if the user may edit, otherwise send an error."""
    if (store := _store(hass, connection, msg_id)) is None:
        return None
    if not can_edit(store.entry, connection.user):
        connection.send_error(msg_id, websocket_api.ERR_UNAUTHORIZED, "No permission to edit scenes")
        return None
    return store


def _changed(
    hass: HomeAssistant, connection: Connection, msg: dict[str, Any], scene: dict[str, Any], action: str
) -> None:
    """Write the change to the logbook, attributed to the user."""
    hass.bus.async_fire(
        EVENT_CHANGED,
        {
            "scene_id": scene["id"],
            "name": scene["name"],
            "action": action,
            "entity_id": er.async_get(hass).async_get_entity_id("scene", DOMAIN, scene["id"]),
        },
        context=connection.context(msg),
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list"})
@websocket_api.async_response
async def ws_list(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return scenes, favorite slots, foreign scenes, images and the user's rights."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    await store.async_scan_images()
    ent_reg = er.async_get(hass)
    scenes = [
        {
            **{k: s[k] for k in ("id", "name", "area_id", "image", "kind", "version", "steps", "changed_at")},
            "entity_id": ent_reg.async_get_entity_id("scene", DOMAIN, s["id"]),
            "image_url": store.image_url(s),
        }
        for s in store.scenes.values()
    ]
    foreign = [
        {"entity_id": eid, "area_id": entity_area(hass, ent), "knx": ent.platform == "knx"}
        for eid, ent in allowed_entities(hass, store.entry).items()
        if ent.domain == "scene"
    ]
    scopes = {HOUSE, *(a.id for a in ar.async_get(hass).async_list_areas())}
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "can_edit": can_edit(store.entry, connection.user),
            "name_length": int(opt(store.entry, CONF_NAME_LENGTH)),
            "favorite_slots": int(opt(store.entry, CONF_FAVORITE_SLOTS)),
            "scenes": scenes,
            "favorites": {scope: store.slots(scope) for scope in scopes},
            "foreign_scenes": foreign,
            "images": [{"name": i, "url": store.sign(i)} for i in store.images],
        },
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/devices", vol.Optional("area_id"): vol.Any(str, None)}
)
@callback
def ws_devices(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return the released devices (of one area, or all) and the music favorites."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    entities = []
    for entity_id, ent in allowed_entities(hass, store.entry).items():
        area_id = entity_area(hass, ent)
        if msg.get("area_id") and area_id != msg["area_id"]:
            continue
        state = hass.states.get(entity_id)
        entities.append(
            {
                "entity_id": entity_id,
                "name": state.name if state else (ent.name or ent.original_name or entity_id),
                "domain": ent.domain,
                "area_id": area_id,
                "available": state is not None and state.state != "unavailable",
            }
        )
    favorites = [{"id": k, "name": v} for k, v in music_favorites(hass).items()]
    connection.send_result(msg["id"], {"entities": entities, "favorites": favorites})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save",
        vol.Optional("scene_id"): str,
        vol.Optional("version"): int,
        vol.Optional("copy_from"): str,
        vol.Required("name"): str,
        vol.Optional("area_id"): vol.Any(str, None),
        vol.Optional("image"): vol.Any(str, None),
        vol.Required("steps"): [STEP_SCHEMA],
    }
)
@websocket_api.async_response
async def ws_save(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Create or change a scene."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    created = "scene_id" not in msg
    try:
        scene = await store.async_save_scene(msg, connection.user.id)
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    _changed(hass, connection, msg, scene, "created" if created else "changed")
    connection.send_result(msg["id"], {"scene_id": scene["id"], "version": scene["version"]})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/delete", vol.Required("scene_id"): str})
@websocket_api.async_response
async def ws_delete(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Delete a scene."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    try:
        scene = await store.async_delete_scene(msg["scene_id"])
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    _changed(hass, connection, msg, scene, "deleted")
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_favorite",
        vol.Required("scope"): str,
        vol.Required("slot"): int,
        vol.Required("scene_id"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_set_favorite(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Put a scene on a favorite slot."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    try:
        await store.async_set_favorite(msg["scope"], msg["slot"], msg["scene_id"])
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Notify the card about every change of scenes, slots or rights."""

    @callback
    def forward() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"changed": True}))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_CHANGED, forward)
    connection.send_result(msg["id"])
