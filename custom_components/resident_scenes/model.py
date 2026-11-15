"""Permissions, device release, step building and activation."""

from __future__ import annotations

import asyncio
from functools import partial
import logging
from typing import Any

from homeassistant.auth.models import User
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.state import async_reproduce_state

from .const import (
    ALLOWED_DOMAINS,
    CONF_LABEL,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_USERS_WITHOUT_EDIT,
    DEFAULTS,
    DOMAIN,
    EVENT_SKIPPED,
)

_LOGGER = logging.getLogger(__name__)

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


def can_edit(entry: ConfigEntry, user: User) -> bool:
    """Return whether the user may change scenes (default: yes, panels: no)."""
    if user.is_admin:
        return True
    if user.system_generated or not user.is_active:
        return False
    # editing needs the right to run scenes (e.g. not for read-only accounts)
    if not user.permissions.access_all_entities(POLICY_CONTROL):
        return False
    if user.id in opt(entry, CONF_PANEL_USERS):
        return user.id in opt(entry, CONF_PANELS_WITH_EDIT)
    return user.id not in opt(entry, CONF_USERS_WITHOUT_EDIT)


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
    """Return Sonos favorites (id -> name) from the Sonos favorites sensor."""
    favorites: dict[str, str] = {}
    for ent in er.async_get(hass).entities.values():
        if ent.platform != "sonos" or ent.domain != "sensor":
            continue
        state = hass.states.get(ent.entity_id)
        if state and isinstance(items := state.attributes.get("items"), dict):
            favorites.update({str(k): str(v) for k, v in items.items()})
    return favorites


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
        if fav is None:
            return {"entity_id": entity_id, "music": "on", "volume": volume}
        return {
            "entity_id": entity_id,
            "music": "favorite",
            "volume": volume,
            "favorite_id": fav,
            "favorite_name": favorites[fav],
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


def build_steps(
    hass: HomeAssistant,
    entry: ConfigEntry,
    raw_steps: list[dict[str, Any]],
    base_steps: list[dict[str, Any]],
    area_id: str | None = None,
) -> list[dict[str, Any]]:
    """Validate the requested steps and resolve them into stored steps.

    Modes: capture (current state), off (without switching), keep (stored
    value of the base scene) and music (media players only). ``keep`` also works
    for devices no longer released or moved, so the scene stays editable (spec 4.11).
    """
    allowed = allowed_entities(hass, entry)
    favorites = music_favorites(hass)
    base = {step["entity_id"]: step for step in base_steps}
    seen: set[str] = set()
    steps: list[dict[str, Any]] = []
    for raw in raw_steps:
        entity_id = raw["entity_id"]
        if entity_id in seen:
            raise ValidationError("duplicate_entity", entity_id)
        seen.add(entity_id)
        domain = entity_id.split(".", 1)[0]
        mode = raw["mode"]
        step: dict[str, Any] | None
        if mode == "keep":
            step = base.get(entity_id)
        elif entity_id not in allowed or (
            area_id and entity_area(hass, allowed[entity_id]) != area_id
        ):
            raise ValidationError("entity_not_allowed", entity_id)
        elif mode == "capture":
            step = _capture(hass, entity_id, favorites) or base.get(entity_id)
            if step is None:
                raise ValidationError("entity_unavailable", entity_id)
        elif mode == "off" and domain == "media_player":
            step = {"entity_id": entity_id, "music": "off"}
        elif mode == "off" and domain in OFF_STATE:
            step = {"entity_id": entity_id, "state": OFF_STATE[domain], "attributes": {}}
        elif mode == "music" and domain == "media_player":
            step = _music_step(entity_id, raw, favorites)
        else:
            step = None
        if step is None:
            raise ValidationError("invalid_step", entity_id)
        steps.append(step)
    return steps


def _music_step(
    entity_id: str, raw: dict[str, Any], favorites: dict[str, str]
) -> dict[str, Any] | None:
    music = raw.get("music")
    if music == "off":
        return {"entity_id": entity_id, "music": "off"}
    if "volume" not in raw:
        return None
    if music == "on":
        return {"entity_id": entity_id, "music": "on", "volume": raw["volume"]}
    if music == "favorite":
        fav = raw.get("favorite_id")
        if fav not in favorites:
            raise ValidationError("unknown_favorite", entity_id)
        return {
            "entity_id": entity_id,
            "music": "favorite",
            "volume": raw["volume"],
            "favorite_id": fav,
            "favorite_name": favorites[fav],
        }
    return None


async def _play_music(
    hass: HomeAssistant, step: dict[str, Any], context: Context | None
) -> None:
    entity_id = step["entity_id"]
    call = partial(hass.services.async_call, "media_player", blocking=True, context=context)
    if step["music"] == "off":
        await call("media_stop", {ATTR_ENTITY_ID: entity_id})
        return
    # volume first, then playback (spec 4.6)
    await call("volume_set", {ATTR_ENTITY_ID: entity_id, "volume_level": step["volume"]})
    if step["music"] == "on":
        await call("media_play", {ATTR_ENTITY_ID: entity_id})
    else:
        await call(
            "play_media",
            {
                ATTR_ENTITY_ID: entity_id,
                "media_content_id": step["favorite_id"],
                "media_content_type": "favorite_item_id",
            },
        )


async def async_activate(
    hass: HomeAssistant, entry: ConfigEntry, scene: dict[str, Any], context: Context | None
) -> None:
    """Apply all steps of a scene together, skipping unreachable or unreleased devices.

    shortcut: steps run in parallel without the script helper, switch to it with delays in stage 2.
    """
    favorites = music_favorites(hass)
    allowed = allowed_entities(hass, entry)
    jobs: list[tuple[str, Any]] = []
    skipped: list[str] = []
    for step in scene["steps"]:
        entity_id = step["entity_id"]
        current = hass.states.get(entity_id)
        if entity_id not in allowed or current is None or current.state == STATE_UNAVAILABLE:
            skipped.append(entity_id)
        elif step.get("call"):
            jobs.append((entity_id, hass.services.async_call(
                "scene", "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True, context=context
            )))
        elif "music" in step:
            if step["music"] == "favorite" and step["favorite_id"] not in favorites:
                skipped.append(entity_id)
            else:
                jobs.append((entity_id, _play_music(hass, step, context)))
        else:
            state = State(entity_id, step["state"], step["attributes"])
            jobs.append((entity_id, async_reproduce_state(hass, [state], context=context)))
    results = await asyncio.gather(*(job for _, job in jobs), return_exceptions=True)
    failed = [eid for (eid, _), res in zip(jobs, results, strict=True) if isinstance(res, Exception)]
    for (eid, _), res in zip(jobs, results, strict=True):
        if isinstance(res, Exception):
            _LOGGER.warning("Scene %s: %s failed: %s", scene["name"], eid, res)
    if skipped or failed:
        hass.bus.async_fire(
            EVENT_SKIPPED,
            {"scene_id": scene["id"], "name": scene["name"], "entities": skipped, "failed": failed},
            context=context,
        )
