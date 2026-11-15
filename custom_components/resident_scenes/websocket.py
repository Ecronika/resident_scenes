"""WebSocket commands of the card. Open to all users, rights are checked here."""

from __future__ import annotations

from functools import partial
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.state import async_reproduce_state

from .const import (
    CONF_FAVORITE_SLOTS,
    CONF_HOUSE_SCENES,
    CONF_MAIN_USERS,
    CONF_MAX_DELAY,
    CONF_NAME_LENGTH,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_SCENES_PER_AREA,
    CONF_USERS_WITHOUT_EDIT,
    DOMAIN,
    EVENT_CHANGED,
    EVENT_RIGHTS,
    HOUSE,
    KIND_INSTALLER,
    KIND_RESIDENT,
    MAX_TRANSITION,
    SIGNAL_CHANGED,
    VERSION,
)
from .model import (
    ValidationError,
    allowed_entities,
    build_step,
    can_control,
    can_edit,
    entity_area,
    is_main_user,
    is_music_player,
    music_favorites,
    opt,
)
from .store import SceneStore

type Connection = websocket_api.ActiveConnection

VALUE_KEYS = ("brightness", "color_temp_kelvin", "hue", "saturation", "position", "tilt", "hvac_mode",
              "temperature", "percentage", "on")
STEP_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): str,
        vol.Optional("scene_id"): str,
        vol.Required("mode"): vol.In(["capture", "off", "keep", "set", "music", "scene"]),
        vol.Optional("music"): vol.In(["off", "on", "favorite"]),
        vol.Optional("volume"): vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
        vol.Optional("favorite_id"): str,
        vol.Optional("values"): {vol.In(VALUE_KEYS): vol.Any(bool, int, float, str)},
        vol.Optional("delay"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands."""
    for command in (
        ws_list, ws_scene, ws_devices, ws_save, ws_delete, ws_undo, ws_set_favorite, ws_subscribe,
        ws_preview, ws_preview_end, ws_rights, ws_set_right,
    ):
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


def _name(hass: HomeAssistant, entity_id: str) -> str:
    if state := hass.states.get(entity_id):
        return state.name
    ent = er.async_get(hass).async_get(entity_id)
    return (ent.name or ent.original_name or entity_id) if ent else entity_id


def _summary(store: SceneStore, scene: dict[str, Any], user) -> dict[str, Any]:
    keys = ("id", "name", "area_id", "image", "kind", "content_released", "version", "transition", "changed_at")
    return {
        **{k: scene[k] for k in keys},
        "entity_id": er.async_get(store.hass).async_get_entity_id("scene", DOMAIN, scene["id"]),
        "image_url": store.image_url(scene),
        "editable": store.editable(scene, user.is_admin),
        "can_undo": bool(scene.get("previous")),
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list", vol.Required("scope"): str})
@callback
def ws_list(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return the scenes of one card scope (area id or _house), without steps, and the user's rights."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    scope, user = msg["scope"], connection.user
    area_id = None if scope == HOUSE else scope
    foreign = []
    for eid, ent in allowed_entities(hass, store.entry).items():
        area = entity_area(hass, ent)
        if ent.domain == "scene" and (scope == HOUSE or area == scope):
            foreign.append({"entity_id": eid, "name": _name(hass, eid), "area_id": area, "knx": ent.platform == "knx"})
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "can_edit": can_edit(store.entry, user),
            "is_admin": user.is_admin,
            "manages_rights": is_main_user(store.entry, user),
            "name_length": int(opt(store.entry, CONF_NAME_LENGTH)),
            "favorite_slots": int(opt(store.entry, CONF_FAVORITE_SLOTS)),
            "max_delay": int(opt(store.entry, CONF_MAX_DELAY)),
            "max_transition": MAX_TRANSITION,
            "limit": int(opt(store.entry, CONF_SCENES_PER_AREA if area_id else CONF_HOUSE_SCENES)),
            "scenes": [_summary(store, s, user) for s in store.scenes.values() if s["area_id"] == area_id],
            "favorites": store.slots(scope),
            "foreign_scenes": foreign,
        },
    )


def _step_issue(hass: HomeAssistant, scene: dict[str, Any], step: dict[str, Any], allowed, favorites) -> str | None:
    """Return why a stored device step is marked: missing, not released, other area, unreachable."""
    eid = step["entity_id"]
    state = hass.states.get(eid)
    if er.async_get(hass).async_get(eid) is None and state is None:
        return "missing"
    if eid not in allowed:
        return "not_released"
    if scene["area_id"] and entity_area(hass, allowed[eid]) != scene["area_id"]:
        return "other_area"
    if state is None or state.state == STATE_UNAVAILABLE:
        return "unavailable"
    if step.get("music") == "favorite" and step["favorite_id"] not in favorites:
        return "favorite_missing"
    return None


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/scene", vol.Required("scene_id"): str})
@callback
def ws_scene(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return one scene with its steps, the reason a step is marked, and where it is used."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    if (scene := store.scenes.get(msg["scene_id"])) is None:
        connection.send_error(msg["id"], "not_found", "The scene no longer exists")
        return
    allowed = allowed_entities(hass, store.entry)
    favorites = music_favorites(hass)
    steps = []
    for step in scene["steps"]:
        item = dict(step)
        if "scene_id" in step:
            target = store.scenes.get(step["scene_id"])
            item |= {"issue": None if target else "scene_missing", "name": target["name"] if target else step["name"]}
        else:
            issue = _step_issue(hass, scene, step, allowed, favorites)
            item |= {"issue": issue, "name": _name(hass, step["entity_id"])}
            if step.get("music") == "favorite":  # a renamed favorite shows its new name (spec 4.6)
                item["favorite_name"] = favorites.get(step["favorite_id"], step.get("favorite_name"))
        steps.append(item)
    connection.send_result(
        msg["id"], {**_summary(store, scene, connection.user), "steps": steps, "used_in": store.used_in(scene["id"])}
    )


def _capabilities(state: State | None) -> dict[str, Any]:
    """What can be set directly on a device, read from its state."""
    if state is None:
        return {}
    attrs = state.attributes
    if state.domain == "light":
        modes = set(attrs.get("supported_color_modes") or [])
        return {
            "brightness": bool(modes - {"onoff"}),
            "color_temp": "color_temp" in modes,
            "min_kelvin": attrs.get("min_color_temp_kelvin"),
            "max_kelvin": attrs.get("max_color_temp_kelvin"),
            "color": bool(modes & {"hs", "xy", "rgb", "rgbw", "rgbww"}),
        }
    if state.domain == "cover":
        return {"position": "current_position" in attrs, "tilt": "current_tilt_position" in attrs}
    if state.domain == "climate":
        return {
            "hvac_modes": attrs.get("hvac_modes", []),
            "min_temp": attrs.get("min_temp"),
            "max_temp": attrs.get("max_temp"),
            "temp_step": attrs.get("target_temp_step", 0.5),
        }
    return {}


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/devices", vol.Optional("area_id"): vol.Any(str, None)}
)
@websocket_api.async_response
async def ws_devices(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return the released devices (of one area, or all), music favorites, images and room scenes."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    await store.async_scan_images()  # the library folder may have changed since start
    entities = []
    for entity_id, ent in allowed_entities(hass, store.entry).items():
        area_id = entity_area(hass, ent)
        if msg.get("area_id") and area_id != msg["area_id"]:
            continue
        state = hass.states.get(entity_id)
        entities.append(
            {
                "entity_id": entity_id,
                "name": _name(hass, entity_id),
                "domain": ent.domain,
                "area_id": area_id,
                "available": state is not None and state.state != STATE_UNAVAILABLE,
                "music_system": is_music_player(hass, entity_id),
                "capabilities": _capabilities(state),
            }
        )
    room_scenes = [] if msg.get("area_id") else [
        {"id": s["id"], "name": s["name"], "area_id": s["area_id"]} for s in store.scenes.values() if s["area_id"]
    ]
    connection.send_result(
        msg["id"],
        {
            "entities": entities,
            "favorites": [{"id": k, "name": v} for k, v in music_favorites(hass).items()],
            "images": [{"name": i, "url": store.sign(i)} for i in store.images],
            "room_scenes": room_scenes,
        },
    )


async def _run(connection: Connection, msg: dict[str, Any], job) -> Any:
    """Run a store call; a validation error goes to the card as error code."""
    try:
        return await job
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save",
        vol.Optional("scene_id"): str,
        vol.Optional("version"): int,
        vol.Optional("copy_from"): str,
        vol.Required("name"): str,
        vol.Optional("area_id"): vol.Any(str, None),
        vol.Optional("image"): vol.Any(str, None),
        vol.Optional("kind"): vol.In([KIND_RESIDENT, KIND_INSTALLER]),
        vol.Optional("content_released"): bool,
        vol.Optional("transition"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
        vol.Required("steps"): [STEP_SCHEMA],
    }
)
@websocket_api.async_response
async def ws_save(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Create or change a scene."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    user = connection.user
    if scene := await _run(connection, msg, store.async_save_scene(msg, user.id, user.is_admin)):
        _changed(hass, connection, msg, scene, "changed" if "scene_id" in msg else "created")
        connection.send_result(msg["id"], {"scene_id": scene["id"], "version": scene["version"]})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/delete", vol.Required("scene_id"): str})
@websocket_api.async_response
async def ws_delete(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Delete a scene."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    if scene := await _run(connection, msg, store.async_delete_scene(msg["scene_id"], connection.user.is_admin)):
        _changed(hass, connection, msg, scene, "deleted")
        connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/undo", vol.Required("scene_id"): str, vol.Required("version"): int}
)
@websocket_api.async_response
async def ws_undo(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Take back the last change of a scene."""
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    user = connection.user
    if scene := await _run(connection, msg, store.async_undo(msg["scene_id"], msg["version"], user.id, user.is_admin)):
        _changed(hass, connection, msg, scene, "change taken back")
        connection.send_result(msg["id"], {"version": scene["version"]})


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


# ---------- live preview (spec 5.4) ----------


def _snapshots(store: SceneStore, connection: Connection) -> dict[str, State]:
    """Per account: entity id -> state before its first preview."""
    return store.previews.setdefault(connection.user.id, {})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/preview",
        vol.Required("step"): STEP_SCHEMA,
        vol.Optional("area_id"): vol.Any(str, None),
    }
)
@websocket_api.async_response
async def ws_preview(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Switch one device to the value set in the editor; the state before is kept for cancel.

    Music favorites are not started here, only on the play button (spec 5.4).
    """
    if (store := _editor(hass, connection, msg["id"])) is None:
        return
    raw = msg["step"]
    if raw["mode"] not in ("off", "set", "music") or "entity_id" not in raw or raw.get("music") == "favorite":
        connection.send_error(msg["id"], "invalid_step", "No preview for this step")
        return
    try:
        step = build_step(hass, raw, allowed_entities(hass, store.entry), {}, msg.get("area_id"))
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    snapshots = _snapshots(store, connection)
    eid = step["entity_id"]
    if eid not in snapshots and (current := hass.states.get(eid)):
        snapshots[eid] = current
    context = connection.context(msg)
    if step.get("music") == "off":
        await hass.services.async_call("media_player", "media_stop", {"entity_id": eid}, blocking=True, context=context)
    elif "music" in step:
        await hass.services.async_call(
            "media_player", "volume_set", {"entity_id": eid, "volume_level": step["volume"]},
            blocking=True, context=context,
        )
    else:
        await async_reproduce_state(hass, [State(eid, step["state"], step["attributes"])], context=context)
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/preview_end", vol.Required("restore"): bool})
@websocket_api.async_response
async def ws_preview_end(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """End the preview; on cancel the devices go back to their state from before editing."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    states = list(store.previews.pop(connection.user.id, {}).values())
    if msg["restore"] and states:
        allowed = allowed_entities(hass, store.entry)
        states = [s for s in states if s.entity_id in allowed]
        context = connection.context(msg)
        await async_reproduce_state(hass, [s for s in states if s.domain != "media_player"], context=context)
        # the preview changed only volume or stopped playback, so only that is undone
        for old in (s for s in states if s.domain == "media_player"):
            call = partial(hass.services.async_call, "media_player", blocking=True, context=context)
            if (volume := old.attributes.get("volume_level")) is not None:
                await call("volume_set", {"entity_id": old.entity_id, "volume_level": volume})
            if old.state == "playing":
                await call("media_play", {"entity_id": old.entity_id})
    connection.send_result(msg["id"])


# ---------- rights managed by main users (spec 3) ----------


def _rank(store: SceneStore, user) -> int:
    """2 admin, 1 main user, 0 other accounts."""
    return 2 if user.is_admin else 1 if user.id in opt(store.entry, CONF_MAIN_USERS) else 0


async def _accounts(hass: HomeAssistant, store: SceneStore, caller) -> list[dict[str, Any]]:
    """Resident and panel accounts below the caller: name and kind only."""
    panels = opt(store.entry, CONF_PANEL_USERS)
    result = []
    for user in await hass.auth.async_get_users():
        if not can_control(user) or user.id == caller.id or _rank(store, user) >= _rank(store, caller):
            continue
        result.append(
            {
                "user_id": user.id,
                "name": user.name or "?",
                "kind": "panel" if user.id in panels else "resident",
                "can_edit": can_edit(store.entry, user),
            }
        )
    return sorted(result, key=lambda a: a["name"].casefold())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/rights"})
@websocket_api.async_response
async def ws_rights(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """List the accounts whose edit right the caller may change."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    if not is_main_user(store.entry, connection.user):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Only main users manage rights")
        return
    connection.send_result(msg["id"], {"accounts": await _accounts(hass, store, connection.user)})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/set_right", vol.Required("user_id"): str, vol.Required("can_edit"): bool}
)
@websocket_api.async_response
async def ws_set_right(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Give or take the edit right of an account below the caller; applies at once."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    caller = connection.user
    accounts = {}
    if is_main_user(store.entry, caller):
        accounts = {a["user_id"]: a for a in await _accounts(hass, store, caller)}
    if (account := accounts.get(msg["user_id"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "This account cannot be changed")
        return
    entry, uid, allow = store.entry, msg["user_id"], msg["can_edit"]
    options = dict(entry.options)
    if account["kind"] == "panel":
        rest = [u for u in opt(entry, CONF_PANELS_WITH_EDIT) if u != uid]
        options[CONF_PANELS_WITH_EDIT] = rest + [uid] if allow else rest
    else:
        rest = [u for u in opt(entry, CONF_USERS_WITHOUT_EDIT) if u != uid]
        options[CONF_USERS_WITHOUT_EDIT] = rest if allow else rest + [uid]
    hass.config_entries.async_update_entry(entry, options=options)
    hass.bus.async_fire(EVENT_RIGHTS, {"user": account["name"], "can_edit": allow}, context=connection.context(msg))
    connection.send_result(msg["id"])
