"""Diagnostics without personal data (no names, no user ids)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import ResidentScenesConfigEntry
from .const import CONF_MAIN_USERS, CONF_PANEL_USERS, CONF_PANELS_WITH_EDIT, CONF_USERS_WITHOUT_EDIT, VERSION
from .model import entries

USER_KEYS = (CONF_MAIN_USERS, CONF_PANEL_USERS, CONF_PANELS_WITH_EDIT, CONF_USERS_WITHOUT_EDIT)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ResidentScenesConfigEntry
) -> dict[str, Any]:
    """Return counts and options; user lists only as counts."""
    store = entry.runtime_data
    return {
        "version": VERSION,
        "options": {k: len(v) if k in USER_KEYS else v for k, v in entry.options.items()},
        "scenes": len(store.scenes),
        "house_scenes": sum(1 for s in store.scenes.values() if s["area_id"] is None),
        "steps": sum(len(list(entries(s["sequence"]))) for s in store.scenes.values()),
        "favorite_scopes": len(store.favorites),
        "images": len(store.images),
    }
