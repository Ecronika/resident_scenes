"""Repair issues for scenes with steps that stay broken (spec 4.10)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_STATE_CHANGED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.debounce import Debouncer

from .const import DOMAIN, MUSIC_PLATFORMS
from .model import music_favorites

_LOGGER = logging.getLogger(__name__)


def broken_steps(hass: HomeAssistant, store, scene: dict) -> list[str]:
    """Return what is permanently missing in a scene: devices, called scenes, music favorites.

    Unreachable devices are not listed, they usually come back by themselves.
    """
    ent_reg = er.async_get(hass)
    favorites = music_favorites(hass)
    broken = []
    for step in scene["steps"]:
        if "scene_id" in step:
            if step["scene_id"] not in store.scenes:
                broken.append(step["name"])
        elif ent_reg.async_get(step["entity_id"]) is None and hass.states.get(step["entity_id"]) is None:
            broken.append(step["entity_id"])
        elif step.get("music") == "favorite" and favorites and step["favorite_id"] not in favorites:
            broken.append(step.get("favorite_name") or step["favorite_id"])
    return broken


@callback
def async_track_issues(hass: HomeAssistant, entry: ConfigEntry, store, now: bool = False) -> None:
    """Create or remove one repair issue per scene; waits until all integrations are loaded."""
    if not now and hass.state is not CoreState.running:

        @callback
        def started(_event: Event) -> None:
            async_track_issues(hass, entry, store, now=True)

        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started))
        return
    wanted = set()
    for scene in store.scenes.values():
        if broken := broken_steps(hass, store, scene):
            issue_id = f"broken_{scene['id']}"
            wanted.add(issue_id)
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="broken_steps",
                translation_placeholders={"scene": scene["name"], "items": ", ".join(broken)},
            )
    for (domain, issue_id) in list(ir.async_get(hass).issues):
        if domain == DOMAIN and issue_id.startswith("broken_") and issue_id not in wanted:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


@callback
def async_follow_removals(hass: HomeAssistant, entry: ConfigEntry, store) -> None:
    """Recheck the issues when an entity is removed or the music favorites change (spec 4.10)."""

    @callback
    def track() -> None:
        async_track_issues(hass, entry, store, now=True)

    debouncer = Debouncer(hass, _LOGGER, cooldown=2, immediate=False, function=track)
    entry.async_on_unload(debouncer.async_shutdown)
    ent_reg = er.async_get(hass)

    @callback
    def removed(event_data: er.EventEntityRegistryUpdatedData) -> bool:
        return event_data["action"] == "remove"

    @callback
    def favorites_changed(event_data: dict) -> bool:
        ent = ent_reg.async_get(event_data["entity_id"])
        return ent is not None and ent.domain == "sensor" and ent.platform in MUSIC_PLATFORMS

    @callback
    def recheck(_event: Event) -> None:
        debouncer.async_schedule_call()

    entry.async_on_unload(hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, recheck, event_filter=removed))
    entry.async_on_unload(hass.bus.async_listen(EVENT_STATE_CHANGED, recheck, event_filter=favorites_changed))


@callback
def async_delete_issues(hass: HomeAssistant) -> None:
    """Remove every issue of the integration (it was removed)."""
    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
