"""Permissions, device release, entries and sequences."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from homeassistant.auth.models import User
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import color as color_util

from .const import (
    ALLOWED_DOMAINS,
    CONF_LABEL,
    CONF_MAIN_USERS,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_ROOMS,
    CONF_USERS_WITHOUT_EDIT,
    CONF_USERS_WITHOUT_HOUSE,
    DEFAULTS,
    DOMAIN,
    MUSIC_PLATFORMS,
)

LIGHT_COLOR_ATTR = {
    "color_temp": "color_temp_kelvin",
    "hs": "hs_color",
    "rgb": "rgb_color",
    "rgbw": "rgbw_color",
    "rgbww": "rgbww_color",
    "xy": "xy_color",
}
CAPTURE_ATTRS: dict[str, tuple[str, ...]] = {
    "cover": ("current_position", "current_tilt_position"),
    "climate": ("temperature", "target_temp_low", "target_temp_high", "preset_mode"),
    "fan": ("percentage", "preset_mode"),
    "switch": (),
}
OFF_STATE = {
    "light": "off",
    "switch": "off",
    "fan": "off",
    "climate": "off",
    "cover": "closed",
}


class ValidationError(Exception):
    """A request was rejected; ``code`` is translated by the card."""

    def __init__(self, code: str, detail: str = "") -> None:
        """Store the error code and an optional detail (e.g. an entity id)."""
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def opt(entry: ConfigEntry, key: str) -> Any:
    """Return an option or its default."""
    return entry.options.get(key, DEFAULTS[key])


def can_control(user: User, entry: ConfigEntry | None = None) -> bool:
    """Return whether the account is an active person that may control devices.

    Checked per device (spec 3): an account Home Assistant limits to some areas controls their devices.
    """
    if not user.is_active or user.system_generated:
        return False
    if user.permissions.access_all_entities(POLICY_CONTROL):
        return True
    store = getattr(entry, "runtime_data", None)
    return store is not None and any(
        user.permissions.check_entity(eid, POLICY_CONTROL) for eid in allowed_entities(store.hass, entry)
    )


def is_main_user(entry: ConfigEntry, user: User) -> bool:
    """Return whether the account manages edit rights (admins and main users)."""
    return user.is_admin or (can_control(user, entry) and user.id in opt(entry, CONF_MAIN_USERS))


def can_edit(entry: ConfigEntry, user: User) -> bool:
    """Return whether the user may change scenes (default: yes, panels: no)."""
    if user.is_admin:
        return True
    if not can_control(user, entry):  # read-only accounts may neither change nor run scenes
        return False
    if user.id in opt(entry, CONF_MAIN_USERS):
        return True
    if user.id in opt(entry, CONF_PANEL_USERS):
        return user.id in opt(entry, CONF_PANELS_WITH_EDIT)
    return user.id not in opt(entry, CONF_USERS_WITHOUT_EDIT)


def room_list(entry: ConfigEntry, user: User) -> list[str] | None:
    """Return the rooms an account is limited to, None for all rooms (default; admins and main users always)."""
    return None if is_main_user(entry, user) else opt(entry, CONF_ROOMS).get(user.id)


def _controls(hass: HomeAssistant, entry: ConfigEntry, user: User, area_id: str | None = "*") -> bool:
    """Return whether the account may control each released device of a room ("*": of the whole house)."""
    perms = user.permissions
    if perms.access_all_entities(POLICY_CONTROL):
        return True
    return all(
        perms.check_entity(eid, POLICY_CONTROL)
        for eid, ent in allowed_entities(hass, entry).items()
        if area_id == "*" or entity_area(hass, ent) == area_id
    )


def may_see(hass: HomeAssistant, entry: ConfigEntry, user: User, area_id: str | None) -> bool:
    """Return whether an account sees and runs the scenes of a room, or with area None the house scenes (spec 3).

    A room counts when the account has its room right and may control the room's devices.
    """
    if area_id is None:
        return is_main_user(entry, user) or user.id not in opt(entry, CONF_USERS_WITHOUT_HOUSE)
    rooms = room_list(entry, user)
    return (rooms is None or area_id in rooms) and _controls(hass, entry, user, area_id)


def may_edit(hass: HomeAssistant, entry: ConfigEntry, user: User, area_id: str | None) -> bool:
    """Return whether an account changes the scenes and slots of a room; the house's need all rooms (spec 3)."""
    if not can_edit(entry, user):
        return False
    if area_id is None:
        return room_list(entry, user) is None and _controls(hass, entry, user)
    return may_see(hass, entry, user, area_id)


def allowed_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, er.RegistryEntry]:
    """Return the entities released for scenes via the label."""
    label = opt(entry, CONF_LABEL)
    dev_reg = dr.async_get(hass)
    result: dict[str, er.RegistryEntry] = {}
    for ent in er.async_get(hass).entities.values():
        if (
            ent.domain not in ALLOWED_DOMAINS
            or ent.platform == DOMAIN
            or ent.entity_category is not None
            or ent.disabled
        ):
            continue
        device = dev_reg.async_get(ent.device_id) if ent.device_id else None
        if label in ent.labels or (device is not None and label in device.labels):
            result[ent.entity_id] = ent
    return result


def entity_area(hass: HomeAssistant, ent: er.RegistryEntry) -> str | None:
    """Return the area of an entity, falling back to its device."""
    if ent.area_id:
        return ent.area_id
    if ent.device_id and (device := dr.async_get(hass).async_get(ent.device_id)):
        return device.area_id
    return None


def music_favorites(hass: HomeAssistant) -> dict[str, str]:
    """Return music favorites (id -> name) from the favorites sensor of the music system."""
    favorites: dict[str, str] = {}
    for ent in er.async_get(hass).entities.values():
        if ent.platform not in MUSIC_PLATFORMS or ent.domain != "sensor":
            continue
        state = hass.states.get(ent.entity_id)
        if state and isinstance(items := state.attributes.get("items"), dict):
            favorites.update({str(k): str(v) for k, v in items.items()})
    return favorites


def is_music_player(hass: HomeAssistant, entity_id: str) -> bool:
    """Return whether a media player belongs to the music system (favorites allowed)."""
    ent = er.async_get(hass).async_get(entity_id)
    return ent is not None and ent.domain == "media_player" and ent.platform in MUSIC_PLATFORMS


def step_issue(
    hass: HomeAssistant, area_id: str | None, step: dict[str, Any], allowed, favorites: dict[str, str]
) -> str | None:
    """Return why a stored device step can only be kept: missing, not released, other area, unreachable.

    One rule for the card, saving and capture (spec 4.5).
    """
    eid = step["entity_id"]
    state = hass.states.get(eid)
    if er.async_get(hass).async_get(eid) is None and state is None:
        return "missing"
    if eid not in allowed:
        return "not_released"
    if entity_area(hass, allowed[eid]) != area_id:  # a step without a room takes devices without a room (X3)
        return "other_area"
    if state is None or state.state == STATE_UNAVAILABLE:
        return "unavailable"
    if step.get("music") == "favorite" and step["favorite_id"] not in favorites:
        return "favorite_missing"
    return None


def light_hs(attrs: dict[str, Any], light: Mapping[str, Any] | None = None) -> list[float] | None:
    """Return hue and saturation of a stored light colour in rgb, rgbw, rgbww or xy form (review X11).

    The white channels of rgbww mix in by the light's kelvin range, as Home Assistant does (review Y8).
    """
    if rgb := attrs.get("rgb_color"):
        return list(color_util.color_RGB_to_hs(*rgb))
    if rgbw := attrs.get("rgbw_color"):
        return list(color_util.color_RGB_to_hs(*color_util.color_rgbw_to_rgb(*rgbw)))
    if rgbww := attrs.get("rgbww_color"):
        light = light or {}
        low, high = light.get("min_color_temp_kelvin") or 2000, light.get("max_color_temp_kelvin") or 6500
        return list(color_util.color_RGB_to_hs(*color_util.color_rgbww_to_rgb(*rgbww, low, high)))
    if xy := attrs.get("xy_color"):
        return list(color_util.color_xy_to_hs(*xy))
    return None


def step_key(step: dict[str, Any]) -> str:
    """Return what an entry acts on: an entity id or a called scene."""
    return step.get("entity_id") or f"scene:{step['scene_id']}"


def _capture(
    hass: HomeAssistant, entity_id: str, favorites: dict[str, str]
) -> dict[str, Any] | None:
    """Turn the current state of an entity into a step, None if unreachable."""
    state = hass.states.get(entity_id)
    if state is None or state.state == STATE_UNAVAILABLE:
        return None
    if state.domain == "scene":  # scenes are "unknown" until first run
        return {"entity_id": entity_id, "call": True}
    if state.state == STATE_UNKNOWN:
        return None
    if state.domain == "media_player":
        if state.state != "playing":
            return {"entity_id": entity_id, "music": "off"}
        volume = float(state.attributes.get("volume_level") or 0)
        # shortcut: matches the current title by name only, upgrade if a music system exposes the favorite id
        names = {state.attributes.get(a) for a in ("media_title", "media_channel", "media_playlist")}
        fav = next((fid for fid, name in favorites.items() if name in names), None)
        if fav is None or not is_music_player(hass, entity_id):
            return {"entity_id": entity_id, "music": "on", "volume": volume}
        return {
            "entity_id": entity_id, "music": "favorite", "volume": volume,
            "favorite_id": fav, "favorite_name": favorites[fav],
        }
    attrs: dict[str, Any] = {}
    if state.domain == "light":
        if state.state == "on":
            mode = state.attributes.get("color_mode")
            keys = ["brightness", "color_mode"]
            if mode in LIGHT_COLOR_ATTR:
                keys.append(LIGHT_COLOR_ATTR[mode])
            attrs = {k: state.attributes[k] for k in keys if state.attributes.get(k) is not None}
    else:
        attrs = {
            k: state.attributes[k]
            for k in CAPTURE_ATTRS[state.domain]
            if state.attributes.get(k) is not None
        }
    return {"entity_id": entity_id, "state": state.state, "attributes": attrs}


def _number(values: dict[str, Any], key: str, low: float, high: float) -> float | None:
    """Return a value within range, None if not given; reject anything else."""
    if key not in values:
        return None
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValidationError("invalid_value", key)
    return value


def _set_step(
    hass: HomeAssistant, entity_id: str, values: dict[str, Any], stored: dict[str, Any] | None
) -> dict[str, Any]:
    """Build a step from values set directly in the editor, checked against the device."""
    domain = entity_id.split(".", 1)[0]
    current = hass.states.get(entity_id)
    attrs = current.attributes if current else {}
    if domain == "light":
        # an input changes only its own value: the rest comes from the stored entry, else the current state (X11)
        base = stored or _capture(hass, entity_id, {}) or {}
        kept = base.get("attributes", {}) if base.get("state") == "on" else {}
        brightness = _number(values, "brightness", 1, 255)
        kelvin = _number(
            values,
            "color_temp_kelvin",
            attrs.get("min_color_temp_kelvin", 1000),
            attrs.get("max_color_temp_kelvin", 12000),
        )
        hue = _number(values, "hue", 0, 360)
        saturation = _number(values, "saturation", 0, 100)
        result: dict[str, Any] = {"brightness": int(brightness or kept.get("brightness") or 255)}
        if kelvin is not None:
            result |= {"color_mode": "color_temp", "color_temp_kelvin": int(kelvin)}
        elif hue is not None:
            result |= {"color_mode": "hs", "hs_color": [hue, 100 if saturation is None else saturation]}
        elif values.get("white") is True:
            if "white" not in (attrs.get("supported_color_modes") or []):
                raise ValidationError("invalid_value", "white")
            result["color_mode"] = "white"
        elif (attr := LIGHT_COLOR_ATTR.get(kept.get("color_mode"))) in kept:
            result |= {"color_mode": kept["color_mode"], attr: kept[attr]}
        elif kept.get("color_mode") == "white":  # a new brightness keeps the white mode (review Z2)
            result["color_mode"] = "white"
        return {"entity_id": entity_id, "state": "on", "attributes": result}
    if domain == "cover":
        position = _number(values, "position", 0, 100)
        tilt = _number(values, "tilt", 0, 100)
        if position is None and tilt is None:
            raise ValidationError("invalid_value", entity_id)
        result = {}
        if position is not None:
            result["current_position"] = int(position)
        if tilt is not None:
            result["current_tilt_position"] = int(tilt)
        state = "closed" if position == 0 else "open"
        return {"entity_id": entity_id, "state": state, "attributes": result}
    if domain == "climate":
        mode = values.get("hvac_mode", current.state if current else None)
        if mode not in attrs.get("hvac_modes", []):
            raise ValidationError("invalid_value", "hvac_mode")
        temperature = _number(values, "temperature", attrs.get("min_temp", 5), attrs.get("max_temp", 35))
        result = {} if temperature is None else {"temperature": temperature}
        return {"entity_id": entity_id, "state": mode, "attributes": result}
    if domain == "fan":
        percentage = _number(values, "percentage", 0, 100)
        if percentage is None:
            raise ValidationError("invalid_value", entity_id)
        state = "on" if percentage else "off"
        return {"entity_id": entity_id, "state": state, "attributes": {"percentage": int(percentage)}}
    if domain == "switch" and isinstance(values.get("on"), bool):
        return {"entity_id": entity_id, "state": "on" if values["on"] else "off", "attributes": {}}
    raise ValidationError("invalid_step", entity_id)


def build_step(
    hass: HomeAssistant,
    raw: dict[str, Any],
    allowed: dict[str, er.RegistryEntry],
    favorites: dict[str, str],
    area_id: str | None,
    stored: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one requested device step (modes capture, off, set, music); ``stored`` is the entry it replaces."""
    entity_id = raw["entity_id"]
    domain = entity_id.split(".", 1)[0]
    mode = raw["mode"]
    if entity_id not in allowed or entity_area(hass, allowed[entity_id]) != area_id:
        raise ValidationError("entity_not_allowed", entity_id)
    if mode == "capture":
        if (step := _capture(hass, entity_id, favorites)) is None:
            raise ValidationError("entity_unavailable", entity_id)
        return step
    if mode == "off" and domain == "media_player":
        return {"entity_id": entity_id, "music": "off"}
    if mode == "off" and domain in OFF_STATE:
        return {"entity_id": entity_id, "state": OFF_STATE[domain], "attributes": {}}
    if mode == "set" and domain in OFF_STATE:
        return _set_step(hass, entity_id, raw.get("values") or {}, stored)
    if mode == "music" and domain == "media_player" and (step := _music_step(hass, entity_id, raw, favorites)):
        return step
    raise ValidationError("invalid_step", entity_id)


def entries(sequence: list[dict[str, Any]]):
    """Yield what a sequence acts on: the entries of its group steps and its scene steps."""
    for step in sequence:
        if step["type"] == "group":
            yield from step["entries"]
        elif step["type"] == "scene":
            yield step


def new_step_id(sequence: list[dict[str, Any]]) -> str:
    """Return a step id not used in the sequence."""
    used = {step["id"] for step in sequence}
    # shortcut: random 32 bits, a removed id could come back in about one of 4e9 additions
    step_id = uuid4().hex[:8]
    while step_id in used:  # pragma: no cover
        step_id = uuid4().hex[:8]
    return step_id


def group_steps(
    hass: HomeAssistant, area_id: str | None, steps: list[dict[str, Any]], scenes: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Turn 0.2.x steps into a sequence (storage format 3) that runs the same.

    A step with a delay starts with a delay step; between two delays device entries are
    grouped per (area, domain) in order of first appearance; a call becomes a scene step.
    Works for stored steps and for template steps (which carry a mode).
    """
    ent_reg = er.async_get(hass)
    sequence: list[dict[str, Any]] = []
    groups: dict[tuple[str | None, str], dict[str, Any]] = {}
    for step in steps:
        if step.get("delay"):
            sequence.append({"id": new_step_id(sequence), "type": "delay", "seconds": step["delay"]})
            groups = {}
        entry = {k: v for k, v in step.items() if k != "delay"}
        if "scene_id" in entry:
            target = scenes.get(entry["scene_id"]) or {}
            sequence.append(
                {
                    "id": new_step_id(sequence), "type": "scene", "scene_id": entry["scene_id"],
                    "name": entry.get("name") or target.get("name", ""), "area_id": target.get("area_id"),
                }
            )
            continue
        area = area_id
        if area is None and (ent := ent_reg.async_get(entry["entity_id"])):
            area = entity_area(hass, ent)
        key = (area, entry["entity_id"].split(".", 1)[0])
        if key not in groups:
            groups[key] = {"id": new_step_id(sequence), "type": "group", "domain": key[1], "area_id": area,
                           "entries": []}
            sequence.append(groups[key])
        groups[key]["entries"].append(entry)
    return sequence


def _music_step(
    hass: HomeAssistant, entity_id: str, raw: dict[str, Any], favorites: dict[str, str]
) -> dict[str, Any] | None:
    music = raw.get("music")
    if music == "off":
        return {"entity_id": entity_id, "music": "off"}
    if "volume" not in raw:
        return None
    if music == "on":
        return {"entity_id": entity_id, "music": "on", "volume": raw["volume"]}
    if music == "favorite":
        if not is_music_player(hass, entity_id):
            raise ValidationError("favorite_not_supported", entity_id)
        if (fav := raw.get("favorite_id")) not in favorites:
            raise ValidationError("unknown_favorite", entity_id)
        return {
            "entity_id": entity_id, "music": "favorite", "volume": raw["volume"],
            "favorite_id": fav, "favorite_name": favorites[fav],
        }
    return None
