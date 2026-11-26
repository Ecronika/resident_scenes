"""Logbook entries for scene changes, skipped steps and schedules."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    DOMAIN,
    EVENT_ALL_OFF,
    EVENT_CHANGED,
    EVENT_FAVORITE,
    EVENT_RIGHTS,
    EVENT_SCHEDULE,
    EVENT_SKIPPED,
)

# why a run of a schedule did not take place (spec 4.15)
REASONS = {
    "scene_missing": "scene missing",
    "not_released": "scene not released",
    "not_reachable": "scene not reachable",
}


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, Any]]], None],
) -> None:
    """Describe the events of this integration."""

    @callback
    def describe_changed(event: Event) -> dict[str, Any]:
        entry = {LOGBOOK_ENTRY_NAME: event.data["name"], LOGBOOK_ENTRY_MESSAGE: f"scene {event.data['action']}"}
        if event.data.get("entity_id"):
            entry[LOGBOOK_ENTRY_ENTITY_ID] = event.data["entity_id"]
        return entry

    def names(entity_ids: list[str]) -> str:
        return ", ".join((s.name if (s := hass.states.get(e)) else e) for e in entity_ids)

    # logbook messages are English like those of core integrations (no translation API for them)
    @callback
    def describe_skipped(event: Event) -> dict[str, Any]:
        parts = []
        if event.data["entities"]:
            parts.append("skipped " + names(event.data["entities"]))
        if event.data.get("failed"):
            parts.append("failed " + names(event.data["failed"]))
        return {LOGBOOK_ENTRY_NAME: event.data["name"], LOGBOOK_ENTRY_MESSAGE: "; ".join(parts)}

    @callback
    def describe_rights(event: Event) -> dict[str, Any]:
        data = event.data
        if "can_edit" in data:
            right = "may now edit scenes" if data["can_edit"] else "may no longer edit scenes"
        else:  # room rights (spec 3): the account that made the change is the user of the context
            rooms = "all rooms" if data["rooms"] is None else ", ".join(data["rooms"]) or "no room"
            right = f"rooms: {rooms}; " + ("may run house scenes" if data["house"] else "may not run house scenes")
        return {LOGBOOK_ENTRY_NAME: event.data["user"], LOGBOOK_ENTRY_MESSAGE: right}

    @callback
    def describe_all_off(event: Event) -> dict[str, Any]:
        # the account is the user of the context, as for every action (spec 4.13)
        message = "all off not run: no right for this room" if event.data["refused"] else "all off"
        if event.data.get("empty"):  # nothing in the room "all off" may switch (spec 4.13)
            message = "all off: nothing released in this room"
        return {LOGBOOK_ENTRY_NAME: event.data["name"], LOGBOOK_ENTRY_MESSAGE: message}

    @callback
    def describe_favorite(event: Event) -> dict[str, Any]:
        # an empty slot is no error; the installer finds an empty push button here (spec 4.14)
        slot = event.data["slot"]
        if event.data["result"] == "refused":
            message = f"favorite slot {slot} not run: no right for this room"
        else:
            message = f"favorite slot {slot} is empty, nothing run"
        return {LOGBOOK_ENTRY_NAME: event.data["name"], LOGBOOK_ENTRY_MESSAGE: message}

    @callback
    def describe_schedule(event: Event) -> dict[str, Any]:
        # the account is the user of the context; a run has none, its scene names this entry as trigger
        data = event.data
        if data["action"] == "ran":
            message = f"ran scene {data['scene']}"
        elif data["action"] == "not run":
            message = f"not run: {REASONS.get(data['reason'], data['reason'])} ({data['scene']})"
        else:
            message = f"schedule {data['action']}"
        entry = {LOGBOOK_ENTRY_NAME: data["name"], LOGBOOK_ENTRY_MESSAGE: message}
        if data.get("entity_id"):
            entry[LOGBOOK_ENTRY_ENTITY_ID] = data["entity_id"]
        return entry

    async_describe_event(DOMAIN, EVENT_SCHEDULE, describe_schedule)
    async_describe_event(DOMAIN, EVENT_ALL_OFF, describe_all_off)
    async_describe_event(DOMAIN, EVENT_FAVORITE, describe_favorite)
    async_describe_event(DOMAIN, EVENT_RIGHTS, describe_rights)
    async_describe_event(DOMAIN, EVENT_CHANGED, describe_changed)
    async_describe_event(DOMAIN, EVENT_SKIPPED, describe_skipped)
