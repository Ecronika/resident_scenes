"""WebSocket commands of the card. Open to all users, rights are checked here."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import area_registry as ar, entity_registry as er, floor_registry as fr
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    ALLOWED_DOMAINS,
    CONF_HOUSE_SCENES,
    CONF_MAX_DELAY,
    CONF_NAME_LENGTH,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_ROOMS,
    CONF_SCENES_PER_AREA,
    CONF_SCHEDULES,
    CONF_USERS_WITHOUT_EDIT,
    CONF_USERS_WITHOUT_HOUSE,
    DOMAIN,
    EVENT_CHANGED,
    EVENT_RIGHTS,
    HOUSE,
    KIND_INSTALLER,
    KIND_RESIDENT,
    MAX_OFFSET,
    MAX_TRANSITION,
    SIGNAL_CHANGED,
    TRIGGERS,
    VERSION,
)
from .model import (
    ValidationError,
    allowed_entities,
    can_control,
    can_edit,
    entity_area,
    is_main_user,
    is_music_player,
    light_hs,
    may_edit,
    may_see,
    music_favorites,
    opt,
    slot_count,
    step_issue,
)
from .schedules import fire_schedule_event, may_change_schedule, may_see_schedule, target
from .store import SceneStore

type Connection = websocket_api.ActiveConnection

VALUE_KEYS = ("brightness", "color_temp_kelvin", "hue", "saturation", "position", "tilt", "hvac_mode",
              "temperature", "percentage", "on", "white")
ENTRY_SCHEMA = {
    vol.Required("entity_id"): str,
    vol.Required("mode"): vol.In(["capture", "off", "set", "music"]),
    vol.Optional("music"): vol.In(["off", "on", "favorite"]),
    vol.Optional("volume"): vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
    vol.Optional("favorite_id"): str,
    vol.Optional("values"): {vol.In(VALUE_KEYS): vol.Any(bool, int, float, str)},
}
DOMAINS = vol.In(sorted(ALLOWED_DOMAINS))
# fields of the inputs of the editor; each also takes scene_id and edit (design "Edits")
INPUTS: dict[str, dict[Any, Any]] = {
    "update": {
        vol.Optional("name"): str,
        vol.Optional("image"): vol.Any(str, None),
        vol.Optional("transition"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0))),
        vol.Optional("kind"): vol.In([KIND_RESIDENT, KIND_INSTALLER]),
        vol.Optional("content_released"): bool,
    },
    "add_step": {
        vol.Required("step_type"): vol.In(["group", "scene", "delay"]),
        vol.Optional("domain"): DOMAINS,
        vol.Optional("area_id"): vol.Any(str, None),
        vol.Optional("target"): str,
        vol.Optional("index"): int,
    },
    "set_delay": {vol.Required("step_id"): str, vol.Required("seconds"): vol.Coerce(float)},
    "remove_step": {vol.Required("step_id"): str},
    "move_step": {vol.Required("step_id"): str, vol.Required("index"): int},
    "set_entry": {vol.Required("step_id"): str, **ENTRY_SCHEMA, vol.Optional("live", default=False): bool},
    "remove_entry": {vol.Required("step_id"): str, vol.Required("entity_id"): str},
    "set_all": {
        vol.Required("step_id"): str,
        vol.Required("mode"): vol.In(["capture", "off"]),
        vol.Optional("live", default=False): bool,
    },
    "house_off": {vol.Required("domain"): DOMAINS},
}


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands."""
    for command in (
        ws_list, ws_scene, ws_devices, ws_create, ws_duplicate, ws_delete, ws_undo, ws_set_favorite, ws_subscribe,
        ws_rights, ws_set_right, ws_set_rooms, ws_schedules, ws_schedule_create, ws_schedule_update,
        ws_schedule_delete, ws_schedule_move, *(_input_command(name, fields) for name, fields in INPUTS.items()),
    ):
        websocket_api.async_register_command(hass, command)


def _store(hass: HomeAssistant, connection: Connection, msg_id: int) -> SceneStore | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    connection.send_error(msg_id, "not_loaded", "Resident Scenes is not set up")
    return None


def _editor(
    hass: HomeAssistant, connection: Connection, msg_id: int, scope: str | None = HOUSE
) -> SceneStore | None:
    """Return the store if the user may edit the scenes of a room (or of the house), otherwise send an error.

    ``scope`` is an area id, None or HOUSE for the house, or ``scene:<id>`` for the room of a scene.
    """
    if (store := _store(hass, connection, msg_id)) is None:
        return None
    if not can_edit(store.entry, connection.user):
        connection.send_error(msg_id, websocket_api.ERR_UNAUTHORIZED, "No permission to edit scenes")
        return None
    if scope and scope.startswith("scene:"):
        if (scene := store.scenes.get(scope[6:])) is None:
            return store  # the store says not_found
        scope = scene["area_id"]
    if not may_edit(hass, store.entry, connection.user, None if scope == HOUSE else scope):
        connection.send_error(msg_id, "no_access", "No access to this room")  # room right (spec 3, 5.6)
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
    access = may_see(hass, store.entry, user, area_id)  # without it the card shows only its hint (spec 5.5)
    foreign = []
    for eid, ent in allowed_entities(hass, store.entry).items() if access else ():
        area = entity_area(hass, ent)
        if ent.domain == "scene" and (scope == HOUSE or area == scope) and may_see(hass, store.entry, user, area):
            foreign.append({"entity_id": eid, "name": _name(hass, eid), "area_id": area, "knx": ent.platform == "knx"})
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "access": access,
            "can_edit": may_edit(hass, store.entry, user, area_id),
            "is_admin": user.is_admin,
            "manages_rights": is_main_user(store.entry, user),
            "name_length": int(opt(store.entry, CONF_NAME_LENGTH)),
            "favorite_slots": slot_count(store.entry, scope),
            "max_delay": int(opt(store.entry, CONF_MAX_DELAY)),
            "max_transition": MAX_TRANSITION,
            "limit": int(opt(store.entry, CONF_SCENES_PER_AREA if area_id else CONF_HOUSE_SCENES)),
            "scenes": [_summary(store, s, user) for s in store.scenes.values() if access and s["area_id"] == area_id],
            "favorites": store.slots(scope) if access else [None] * slot_count(store.entry, scope),
            "foreign_scenes": foreign,
        },
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/scene", vol.Required("scene_id"): str})
@callback
def ws_scene(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return one scene with its sequence, the reason an entry is marked, and where it is used."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    if (scene := store.scenes.get(msg["scene_id"])) is None:
        connection.send_error(msg["id"], "not_found", "The scene no longer exists")
        return
    if not may_see(hass, store.entry, connection.user, scene["area_id"]):
        connection.send_error(msg["id"], "no_access", "No access to this room")
        return
    allowed = allowed_entities(hass, store.entry)
    favorites = music_favorites(hass)
    sequence = []
    for step in scene["sequence"]:
        item = dict(step)
        if step["type"] == "scene":
            target = store.scenes.get(step["scene_id"])
            issue = None if target and target["area_id"] else "no_room_scene" if target else "scene_missing"
            item |= {"issue": issue, "name": target["name"] if target else step["name"]}
        elif step["type"] == "group":
            item["entries"] = []
            for entry in step["entries"]:
                issue = step_issue(hass, step["area_id"], entry, allowed, favorites)
                shown = {**entry, "issue": issue, "name": _name(hass, entry["entity_id"])}
                attrs = entry.get("attributes") or {}
                light = st.attributes if (st := hass.states.get(entry["entity_id"])) else {}
                if "hs_color" not in attrs and (hs := light_hs(attrs, light)):  # the card's controls read hue (X11)
                    shown["attributes"] = {**attrs, "hs_color": hs}
                if entry.get("music") == "favorite":  # a renamed favorite shows its new name (spec 4.6)
                    shown["favorite_name"] = favorites.get(entry["favorite_id"], entry.get("favorite_name"))
                item["entries"].append(shown)
        sequence.append(item)
    used_in = store.used_in(scene["id"])
    if not may_see(hass, store.entry, connection.user, None):  # callers are house scenes
        used_in["scenes"] = []
    connection.send_result(
        msg["id"], {**_summary(store, scene, connection.user), "sequence": sequence, "used_in": used_in}
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
            "white_mode": "white" in modes,  # a white channel of its own, no colour (review Z2)
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
    if (store := _editor(hass, connection, msg["id"], msg.get("area_id"))) is None:
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
        vol.Required("type"): f"{DOMAIN}/create",
        vol.Optional("area_id", default=None): vol.Any(str, None),
        vol.Required("name"): str,
        vol.Required("edit"): str,
    }
)
@websocket_api.async_response
async def ws_create(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Create an empty scene; the card sends the translated base name."""
    if (store := _editor(hass, connection, msg["id"], msg["area_id"])) is None:
        return
    job = store.async_create(msg["area_id"], msg["name"], msg["edit"], connection.user.id)
    if scene := await _run(connection, msg, job):
        _changed(hass, connection, msg, scene, "created")
        connection.send_result(msg["id"], {"scene_id": scene["id"], "version": scene["version"]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/duplicate",
        vol.Required("scene_id"): str,
        vol.Required("suffix"): str,
        vol.Required("edit"): str,
    }
)
@websocket_api.async_response
async def ws_duplicate(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Copy a scene; the card sends the translated suffix."""
    if (store := _editor(hass, connection, msg["id"], f"scene:{msg['scene_id']}")) is None:
        return
    job = store.async_duplicate(msg["scene_id"], msg["suffix"], msg["edit"], connection.user.id)
    if scene := await _run(connection, msg, job):
        _changed(hass, connection, msg, scene, "created")
        connection.send_result(msg["id"], {"scene_id": scene["id"], "version": scene["version"]})


def _input_command(name: str, fields: dict[Any, Any]):
    """Build the command of one input of the editor."""

    @websocket_api.websocket_command(
        {vol.Required("type"): f"{DOMAIN}/{name}", vol.Required("scene_id"): str, vol.Required("edit"): str, **fields}
    )
    @websocket_api.async_response
    async def ws_input(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
        """Apply the input at once; the first input of an edit goes to the logbook."""
        # checked with every input: a right taken away during an edit rejects the next input (spec 3)
        if (store := _editor(hass, connection, msg["id"], f"scene:{msg['scene_id']}")) is None:
            return
        user = connection.user
        if (done := await _run(connection, msg, store.async_input(msg, user.id, user.is_admin))) is None:
            return
        scene, began, result = done
        if began:
            _changed(hass, connection, msg, scene, "changed")
        if live := result.pop("live", None):
            # live adjustment: the device follows the input, the same way a run applies it
            await store.runner.async_apply(scene, live, connection.context(msg))
        connection.send_result(msg["id"], {"version": scene["version"], **result})

    return ws_input


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/delete", vol.Required("scene_id"): str})
@websocket_api.async_response
async def ws_delete(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Delete a scene."""
    if (store := _editor(hass, connection, msg["id"], f"scene:{msg['scene_id']}")) is None:
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
    if (store := _editor(hass, connection, msg["id"], f"scene:{msg['scene_id']}")) is None:
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
    if (store := _editor(hass, connection, msg["id"], msg["scope"])) is None:
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


# ---------- rights managed by main users (spec 3) ----------


async def _accounts(hass: HomeAssistant, store: SceneStore) -> list[dict[str, Any]]:
    """Resident and panel accounts: name and kind only.

    Admins and main users are left out, they always may edit (spec 3).
    """
    panels = opt(store.entry, CONF_PANEL_USERS)
    result = []
    for user in await hass.auth.async_get_users():
        if not can_control(user, store.entry) or is_main_user(store.entry, user):
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
    accounts = await _accounts(hass, store)
    entry = store.entry
    floors = sorted(fr.async_get(hass).async_list_floors(), key=lambda f: (f.level is None, f.level or 0, f.name))
    connection.send_result(
        msg["id"],
        {
            "accounts": accounts,
            # room rights (spec 3, stage 4): rooms None means all rooms
            "room_rights": {
                a["user_id"]: {
                    "rooms": opt(entry, CONF_ROOMS).get(a["user_id"]),
                    "house": a["user_id"] not in opt(entry, CONF_USERS_WITHOUT_HOUSE),
                }
                for a in accounts
            },
            "floors": [{"floor_id": f.floor_id, "name": f.name} for f in floors],
            "areas": sorted(
                (
                    {"area_id": a.id, "name": a.name, "floor_id": a.floor_id}
                    for a in ar.async_get(hass).async_list_areas()
                ),
                key=lambda a: a["name"].casefold(),
            ),
        },
    )


async def _account(
    hass: HomeAssistant, connection: Connection, msg: dict[str, Any], store: SceneStore
) -> dict[str, Any] | None:
    """Return the account the caller may change (one below it), otherwise send an error."""
    accounts = {}
    if is_main_user(store.entry, connection.user):
        accounts = {a["user_id"]: a for a in await _accounts(hass, store)}
    if (account := accounts.get(msg["user_id"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "This account cannot be changed")
    return account


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/set_right", vol.Required("user_id"): str, vol.Required("can_edit"): bool}
)
@websocket_api.async_response
async def ws_set_right(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Give or take the edit right of an account below the caller; applies at once."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    if (account := await _account(hass, connection, msg, store)) is None:
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_rooms",
        vol.Required("user_id"): str,
        vol.Required("rooms"): vol.Any(None, [str]),
        vol.Required("house"): bool,
    }
)
@websocket_api.async_response
async def ws_set_rooms(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Limit an account below the caller to rooms (None: all rooms) and give or take the house right; at once."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    if (account := await _account(hass, connection, msg, store)) is None:
        return
    areas = ar.async_get(hass)
    wanted = None if msg["rooms"] is None else list(dict.fromkeys(msg["rooms"]))
    if wanted is not None and any(areas.async_get_area(a) is None for a in wanted):
        connection.send_error(msg["id"], "invalid_area", "Unknown room")
        return
    entry, uid = store.entry, msg["user_id"]
    rooms = {k: v for k, v in opt(entry, CONF_ROOMS).items() if k != uid} | ({} if wanted is None else {uid: wanted})
    no_house = [u for u in opt(entry, CONF_USERS_WITHOUT_HOUSE) if u != uid]
    no_house = no_house if msg["house"] else [*no_house, uid]
    if rooms == opt(entry, CONF_ROOMS) and set(no_house) == set(opt(entry, CONF_USERS_WITHOUT_HOUSE)):
        connection.send_result(msg["id"])  # nothing changes: no logbook entry (review AC3)
        return
    options = {**entry.options, CONF_ROOMS: rooms, CONF_USERS_WITHOUT_HOUSE: no_house}
    hass.config_entries.async_update_entry(entry, options=options)
    names = None if wanted is None else [areas.async_get_area(a).name for a in wanted]  # type: ignore[union-attr]
    hass.bus.async_fire(
        EVENT_RIGHTS, {"user": account["name"], "rooms": names, "house": msg["house"]}, context=connection.context(msg)
    )
    connection.send_result(msg["id"])


# ---------- schedules (spec 4.15) ----------

SCHEDULE_FIELDS = ("name", "active", "trigger", "time", "offset", "weekdays", "scene_id", "entity_id")


def _schedule_summary(hass: HomeAssistant, store: SceneStore, schedule: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "name", "active", "trigger", "time", "offset", "weekdays", "scene_id", "version")
    scene = target(hass, store, schedule)
    moment = store.scheduler.next.get(schedule["id"])
    return {
        **{k: schedule[k] for k in keys},
        "entity_id": er.async_get(hass).async_get_entity_id("switch", DOMAIN, schedule["id"]),
        "scene_entity_id": scene["entity_id"],
        "scene_name": scene["name"],
        "area_id": scene["area_id"],
        "issue": scene["issue"],
        "next_run": moment.isoformat() if moment else None,  # none when off or the scene is missing
    }


def _scene_choices(hass: HomeAssistant, store: SceneStore, user) -> list[dict[str, Any]]:
    """The scenes an account may choose for a schedule: those it may run (spec 4.15)."""
    entry = store.entry
    choices = [
        {"scene_id": s["id"], "name": s["name"], "area_id": s["area_id"], "kind": s["kind"]}
        for s in store.scenes.values()
        if may_see(hass, entry, user, s["area_id"])
    ]
    for eid, ent in allowed_entities(hass, entry).items():
        if ent.domain == "scene" and may_see(hass, entry, user, area := entity_area(hass, ent)):
            kind = "knx" if ent.platform == "knx" else "other"
            choices.append({"entity_id": eid, "name": _name(hass, eid), "area_id": area, "kind": kind})
    return choices


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/schedules"})
@callback
def ws_schedules(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Return the schedules the account sees, in the order of the list, and the scenes it may choose."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    user, limit = connection.user, int(opt(store.entry, CONF_SCHEDULES))
    editor = can_edit(store.entry, user)
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "can_edit": editor,
            "name_length": int(opt(store.entry, CONF_NAME_LENGTH)),
            "max_offset": MAX_OFFSET,
            "limit": limit,
            "full": len(store.schedules) >= limit,
            "schedules": [
                _schedule_summary(hass, store, s) for s in store.schedules if may_see_schedule(hass, store, user, s)
            ],
            "scenes": _scene_choices(hass, store, user) if editor else [],
        },
    )


def _schedule_editor(
    hass: HomeAssistant, connection: Connection, msg: dict[str, Any]
) -> tuple[SceneStore, dict[str, Any]] | None:
    """Return store and schedule if the account may change it, otherwise send an error.

    A schedule the account does not see is not named to it: not_found (spec 4.15).
    """
    if (store := _store(hass, connection, msg["id"])) is None:
        return None
    if not can_edit(store.entry, connection.user):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "No permission to change schedules")
        return None
    schedule = next((s for s in store.schedules if s["id"] == msg["schedule_id"]), None)
    if schedule is None or not may_change_schedule(hass, store, connection.user, schedule):
        connection.send_error(msg["id"], "not_found", "The schedule no longer exists")
        return None
    return store, schedule


def _scene_ref(
    hass: HomeAssistant, connection: Connection, msg: dict[str, Any], store: SceneStore
) -> dict[str, Any] | None:
    """Return the reference to the chosen scene if the account may run it, otherwise send an error."""
    try:
        ref = store.scene_ref(msg.get("scene_id"), msg.get("entity_id"))
    except ValidationError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return None
    if not may_see(hass, store.entry, connection.user, ref["area_id"]):
        connection.send_error(msg["id"], "no_access", "No access to this scene")
        return None
    return ref


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/schedule_create",
        vol.Exclusive("scene_id", "scene"): str,
        vol.Exclusive("entity_id", "scene"): str,
        vol.Required("name"): str,
        vol.Required("edit"): str,
    }
)
@websocket_api.async_response
async def ws_schedule_create(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Create a schedule for a scene; the card asks for the scene first and sends the translated name."""
    if (store := _store(hass, connection, msg["id"])) is None:
        return
    if not can_edit(store.entry, connection.user):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "No permission to change schedules")
        return
    if (ref := _scene_ref(hass, connection, msg, store)) is None:
        return
    job = store.async_create_schedule(ref, msg["name"], msg["edit"], connection.user.id)
    if schedule := await _run(connection, msg, job):
        fire_schedule_event(hass, schedule, "created", connection.context(msg))
        connection.send_result(msg["id"], {"schedule_id": schedule["id"], "version": schedule["version"]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/schedule_update",
        vol.Required("schedule_id"): str,
        vol.Optional("edit", default=""): str,
        vol.Exclusive("name", "field"): str,
        vol.Exclusive("active", "field"): bool,
        vol.Exclusive("trigger", "field"): vol.In(TRIGGERS),
        vol.Exclusive("time", "field"): vol.Match(r"^([01]\d|2[0-3]):[0-5]\d$"),
        vol.Exclusive("offset", "field"): int,
        vol.Exclusive("weekdays", "field"): [vol.All(int, vol.Range(min=0, max=6))],
        vol.Exclusive("scene_id", "field"): str,
        vol.Exclusive("entity_id", "field"): str,
    }
)
@websocket_api.async_response
async def ws_schedule_update(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Change exactly one field of a schedule at once (spec 4.15); switching goes to the logbook on its own."""
    if (found := _schedule_editor(hass, connection, msg)) is None:
        return
    store, schedule = found
    if len(fields := [k for k in SCHEDULE_FIELDS if k in msg]) != 1:
        connection.send_error(msg["id"], "invalid_value", "invalid_value: one field per input")
        return
    field, value = fields[0], msg[fields[0]]
    if field in ("scene_id", "entity_id"):
        if (value := _scene_ref(hass, connection, msg, store)) is None:
            return
        field = "scene"
    version = schedule["version"]
    job = store.async_update_schedule(schedule["id"], field, value, msg["edit"], connection.user.id)
    if (done := await _run(connection, msg, job)) is None:
        return
    schedule, began = done
    if field == "active" and schedule["version"] != version:
        fire_schedule_event(hass, schedule, "switched on" if value else "switched off", connection.context(msg))
    elif began:
        fire_schedule_event(hass, schedule, "changed", connection.context(msg))
    connection.send_result(msg["id"], {"version": schedule["version"]})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/schedule_delete", vol.Required("schedule_id"): str}
)
@websocket_api.async_response
async def ws_schedule_delete(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Delete a schedule; the card has asked with its name."""
    if (found := _schedule_editor(hass, connection, msg)) is None:
        return
    store, schedule = found
    await store.async_delete_schedule(schedule["id"])
    fire_schedule_event(hass, schedule, "deleted", connection.context(msg))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/schedule_move", vol.Required("schedule_id"): str, vol.Required("index"): int}
)
@callback
def ws_schedule_move(hass: HomeAssistant, connection: Connection, msg: dict[str, Any]) -> None:
    """Move a schedule to a place among those the account sees; the order applies to every account."""
    if (found := _schedule_editor(hass, connection, msg)) is None:
        return
    store, schedule = found
    visible = {s["id"] for s in store.schedules if may_see_schedule(hass, store, connection.user, s)}
    store.move_schedule(schedule["id"], msg["index"], visible)
    connection.send_result(msg["id"])
