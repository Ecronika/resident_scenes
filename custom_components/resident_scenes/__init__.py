"""Resident Scenes: scenes that residents without admin rights create and edit."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, label_registry as lr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, CONF_LABEL, DOMAIN, SIGNAL_CHANGED, VERSION
from .http import ImageView
from .model import opt
from .store import SceneStore
from .websocket import async_register

PLATFORMS = [Platform.SCENE]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type ResidentScenesConfigEntry = ConfigEntry[SceneStore]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the card, the image view and the WebSocket commands."""
    async_register(hass)
    hass.http.register_view(ImageView())
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend" / "resident-scenes-card.js"), False)]
    )
    if "frontend" in hass.config.components:
        from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

        # the version in the URL makes browsers and panels load the new card after an update
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> bool:
    """Load the scenes."""
    store = SceneStore(hass, entry)
    await store.async_load()
    store.async_listen()
    entry.runtime_data = store
    labels = lr.async_get(hass)
    if labels.async_get_label(label := opt(entry, CONF_LABEL)) is None:
        labels.async_create(label)  # without it the device list stays empty with no hint why
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> None:
    """Rights or limits changed: rescan images and tell the cards."""
    await entry.runtime_data.async_scan_images()
    async_dispatcher_send(hass, SIGNAL_CHANGED)


async def async_unload_entry(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> bool:
    """Unload the scenes; stored data stays."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
