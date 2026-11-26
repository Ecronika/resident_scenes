"""One switch per schedule: on means active (spec 4.15)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ResidentScenesConfigEntry
from .const import SIGNAL_CHANGED
from .schedules import WEEKDAYS, fire_schedule_event, may_change_schedule, target
from .store import SceneStore

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResidentScenesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one switch entity per stored schedule; it goes with its schedule."""
    store = entry.runtime_data
    entities: dict[str, ScheduleSwitch] = {}

    @callback
    def sync() -> None:
        new: list[ScheduleSwitch] = []
        for schedule in store.schedules:
            if schedule["id"] in entities:
                entities[schedule["id"]].refresh()
            else:
                entities[schedule["id"]] = ScheduleSwitch(store, schedule["id"])
                new.append(entities[schedule["id"]])
        registry = er.async_get(hass)
        ids = {s["id"] for s in store.schedules}
        for schedule_id in [s for s in entities if s not in ids]:
            entity = entities.pop(schedule_id)
            if entity.registry_entry:
                registry.async_remove(entity.entity_id)
        if new:
            async_add_entities(new)

    sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_CHANGED, sync))


class ScheduleSwitch(SwitchEntity):
    """Switches a schedule on and off, e.g. from a push button; it belongs to no room and is no scene device."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "schedule"

    def __init__(self, store: SceneStore, schedule_id: str) -> None:
        """Initialize the entity."""
        self.store = store
        self._attr_unique_id = schedule_id
        self._attr_name = self._schedule["name"]

    @property
    def _schedule(self) -> dict[str, Any]:
        return self.store.schedule(self._attr_unique_id)  # type: ignore[arg-type]

    @property
    def is_on(self) -> bool:
        """Return whether the schedule is active."""
        return self._schedule["active"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Next run (empty when off or the scene is missing), trigger, weekdays and the scene."""
        schedule = self._schedule
        moment = self.store.scheduler.next.get(schedule["id"])
        return {
            "next_run": moment.isoformat() if moment else None,
            "trigger": schedule["trigger"],
            "time": schedule["time"] if schedule["trigger"] == "time" else None,
            "offset": schedule["offset"] if schedule["trigger"] != "time" else None,
            "weekdays": [WEEKDAYS[d] for d in schedule["weekdays"]],
            "scene_entity_id": target(self.hass, self.store, schedule)["entity_id"],
        }

    async def async_added_to_hass(self) -> None:
        """Remember the generated entity id; it follows the name in the creating edit (spec 4.15)."""
        await super().async_added_to_hass()
        schedule = self._schedule
        if not schedule["entity_named"] and "auto_entity_id" not in schedule:
            schedule["auto_entity_id"] = self.entity_id
            self.store.async_save_later()

    @callback
    def refresh(self) -> None:
        """Apply a changed schedule or a new next run."""
        self._attr_name = self._schedule["name"]
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the schedule on."""
        await self._async_switch(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the schedule off."""
        await self._async_switch(False)

    async def _async_switch(self, on: bool) -> None:
        """A call with a user needs the rights of the card; calls without a user always apply (spec 4.15)."""
        context, schedule = self._context, self._schedule
        user = await self.hass.auth.async_get_user(context.user_id) if context and context.user_id else None
        if user is not None and not may_change_schedule(self.hass, self.store, user, schedule):
            _LOGGER.warning("Schedule %s not switched: %s has no right for it", schedule["name"], user.name)
            fire_schedule_event(self.hass, schedule, "not switched: no right for it", context)
            raise Unauthorized(context=context, entity_id=self.entity_id, permission=POLICY_CONTROL)
        version = schedule["version"]
        schedule, _ = await self.store.async_update_schedule(
            schedule["id"], "active", on, "", user.id if user else None
        )
        if schedule["version"] != version:
            fire_schedule_event(self.hass, schedule, "switched on" if on else "switched off", context)
