"""Resident Scenes: scenes that residents without admin rights create and edit."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    label_registry as lr,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, CONF_LABEL, DOMAIN, EVENT_CHANGED, SIGNAL_CHANGED, VERSION
from .http import ImageView, PhotoView, UploadView
from .issues import async_track_issues
from .model import ValidationError, can_edit, opt
from .runner import SceneRunner
from .store import SceneStore
from .websocket import async_register

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SCENE]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type ResidentScenesConfigEntry = ConfigEntry[SceneStore]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the card, the image views, the WebSocket commands and the capture action."""
    async_register(hass)
    for view in (ImageView(), PhotoView(), UploadView()):
        hass.http.register_view(view)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "frontend" / "resident-scenes-card.js"), False)]
    )
    if "frontend" in hass.config.components:
        from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

        # the version in the URL makes browsers and panels load the new card after an update
        add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    hass.services.async_register(DOMAIN, "capture", _async_capture, schema=cv.make_entity_service_schema({}))
    return True


async def _async_capture(call: ServiceCall) -> None:
    """Take over the current state into scenes, e.g. on a long press of a KNX push button."""
    hass = call.hass
    entry = next(
        (e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED), None
    )
    if entry is None:
        raise HomeAssistantError(translation_domain=DOMAIN, translation_key="not_loaded")
    store: SceneStore = entry.runtime_data
    user = await hass.auth.async_get_user(call.context.user_id) if call.context.user_id else None
    # automations of the installer run without a user and are allowed (spec 4.9)
    if user is not None and not can_edit(entry, user):
        raise Unauthorized(context=call.context)
    ent_reg = er.async_get(hass)
    for entity_id in call.data[ATTR_ENTITY_ID]:
        ent = ent_reg.async_get(entity_id)
        if ent is None or ent.platform != DOMAIN or ent.unique_id not in store.scenes:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="not_a_scene", translation_placeholders={"entity": entity_id}
            )
        scene = store.scenes[ent.unique_id]
        if user is not None and not store.editable(scene, user.is_admin):
            raise Unauthorized(context=call.context)
        try:
            scene = await store.async_capture(ent.unique_id, user.id if user else None)
        except ValidationError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="capture_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        hass.bus.async_fire(
            EVENT_CHANGED,
            {"scene_id": scene["id"], "name": scene["name"], "action": "captured", "entity_id": entity_id},
            context=call.context,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> bool:
    """Load the scenes."""
    store = SceneStore(hass, entry)
    await store.async_load()
    store.async_listen()
    store.runner = SceneRunner(hass, entry, store.scenes)
    entry.runtime_data = store
    labels = lr.async_get(hass)
    if labels.async_get_label(label := opt(entry, CONF_LABEL)) is None:
        try:
            labels.async_create(label)  # without it the device list stays empty with no hint why
        except ValueError:  # a label with this name but another id exists
            _LOGGER.warning("Label %s could not be created, a label with this name exists", label)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_track_issues(hass, entry, store)

    @callback
    def changed() -> None:
        async_track_issues(hass, entry, store, now=True)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_CHANGED, changed))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> None:
    """Rights or limits changed: rescan images and tell the cards."""
    await entry.runtime_data.async_scan_images()
    async_dispatcher_send(hass, SIGNAL_CHANGED)


async def async_unload_entry(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> bool:
    """Unload the scenes; stored data stays."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
