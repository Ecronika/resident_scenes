"""Resident Scenes: scenes that residents without admin rights create and edit."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv, label_registry as lr, service
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import CARD_URL, CONF_LABEL, DOMAIN, EVENT_CHANGED, SIGNAL_CHANGED, VERSION
from .http import ImageView, PhotoView, UploadView
from .issues import async_delete_issues, async_follow_removals, async_track_issues
from .model import ValidationError, can_edit, may_edit, opt
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
    service.async_register_platform_entity_service(
        hass, DOMAIN, "capture", entity_domain=Platform.SCENE, schema=None, func=_async_capture
    )
    return True


async def _async_capture(entity: Any, call: ServiceCall) -> None:
    """Take over the current state into a scene, e.g. on a long press of a KNX push button.

    Home Assistant resolves the targets (entities, areas, devices, labels, all) to our scene entities.
    """
    hass = call.hass
    store: SceneStore = entity.store
    scene = store.scenes[entity.unique_id]
    user = await hass.auth.async_get_user(call.context.user_id) if call.context.user_id else None
    # automations of the installer run without a user and are allowed (spec 4.9)
    if user is not None and not (
        can_edit(store.entry, user)
        and store.editable(scene, user.is_admin)
        and may_edit(hass, store.entry, user, scene["area_id"])  # room right (spec 3)
    ):
        raise Unauthorized(context=call.context)
    try:
        scene = await store.async_capture(scene["id"], user.id if user else None)
    except ValidationError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="capture_failed",
            translation_placeholders={"error": str(err)},
        ) from err
    hass.bus.async_fire(
        EVENT_CHANGED,
        {"scene_id": scene["id"], "name": scene["name"], "action": "captured", "entity_id": entity.entity_id},
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
    async_follow_removals(hass, entry, store)

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
    await entry.runtime_data.async_write()  # the next setup reads the file, not this store's pending data
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ResidentScenesConfigEntry) -> None:
    """The integration was removed: its repair issues go too."""
    async_delete_issues(hass)
