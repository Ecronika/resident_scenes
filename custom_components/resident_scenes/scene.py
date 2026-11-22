"""Scene entities for resident scenes."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from . import ResidentScenesConfigEntry
from .const import DOMAIN, EVENT_CHANGED, SIGNAL_CHANGED
from .model import entries, may_see
from .store import SceneStore

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0
PICTURE_REFRESH = timedelta(hours=12)  # signed picture URLs live one day


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ResidentScenesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Keep one scene entity per stored scene."""
    store = entry.runtime_data
    entities: dict[str, ResidentScene] = {}

    @callback
    def sync() -> None:
        new: list[ResidentScene] = []
        for scene_id in store.scenes:
            if scene_id in entities:
                entities[scene_id].refresh()
            else:
                entities[scene_id] = ResidentScene(store, scene_id)
                new.append(entities[scene_id])
        registry = er.async_get(hass)
        for scene_id in [s for s in entities if s not in store.scenes]:
            entity = entities.pop(scene_id)
            if entity.registry_entry:
                registry.async_remove(entity.entity_id)
        if new:
            async_add_entities(new)

    @callback
    def refresh_pictures(_now: Any) -> None:
        for entity in entities.values():
            entity.async_write_ha_state()

    sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_CHANGED, sync))
    entry.async_on_unload(async_track_time_interval(hass, refresh_pictures, PICTURE_REFRESH))


class ResidentScene(Scene):
    """A scene created by residents."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, store: SceneStore, scene_id: str) -> None:
        """Initialize the entity."""
        self.store = store  # read by the capture action
        self._attr_unique_id = scene_id
        self._update_attrs()

    @property
    def _scene(self) -> dict[str, Any]:
        return self.store.scenes[self._attr_unique_id]  # type: ignore[index]

    @property
    def entity_picture(self) -> str | None:
        """Return a fresh signed URL of the scene image."""
        return self.store.image_url(self._scene)

    def _update_attrs(self) -> None:
        scene = self._scene
        self._attr_name = scene["name"]
        self._attr_extra_state_attributes = {
            "kind": scene["kind"],
            "content_released": scene["content_released"],
            "area_id": scene["area_id"],
            "step_count": len(list(entries(scene["sequence"]))),
            "changed_at": scene["changed_at"],
        }

    async def async_added_to_hass(self) -> None:
        """Assign the scene to its area once registered."""
        await super().async_added_to_hass()
        self._sync_area()
        scene = self._scene
        if not scene["entity_named"] and "auto_entity_id" not in scene:
            # the id generated from "Neue Szene N"; the first rename replaces it unless changed by hand (spec 4.3)
            scene["auto_entity_id"] = self.entity_id
            self.store.async_save_later()

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Keep the entity on an entity id change (2026.11+) instead of re-adding it."""
        if parent := getattr(super(), "async_entity_id_changed", None):
            parent(old_entity_id)

    @callback
    def refresh(self) -> None:
        """Apply a changed scene."""
        self._update_attrs()
        if self.hass is None:  # not added yet; added state picks up the new attributes
            return
        self._sync_area()
        self.async_write_ha_state()

    @callback
    def _sync_area(self) -> None:
        registry = er.async_get(self.hass)
        entry = registry.async_get(self.entity_id) if self.entity_id else None
        if entry is not None and entry.platform == DOMAIN and entry.area_id != self._scene["area_id"]:
            registry.async_update_entity(self.entity_id, area_id=self._scene["area_id"])

    async def async_activate(self, **kwargs: Any) -> None:
        """Run the scene; a call with a user needs the room right, or for a house scene the house right (spec 4.4).

        Calls without a user (automations, schedules, KNX push buttons) always run. A house scene runs
        fully, also its steps in rooms the user has no right for.
        """
        context, scene = self._context, self._scene
        user = await self.hass.auth.async_get_user(context.user_id) if context and context.user_id else None
        if user is not None and not may_see(self.hass, self.store.entry, user, scene["area_id"]):
            _LOGGER.warning("Scene %s not run: %s has no right for its room", scene["name"], user.name)
            self.hass.bus.async_fire(
                EVENT_CHANGED,
                {"scene_id": scene["id"], "name": scene["name"], "action": "not run: no right for its room",
                 "entity_id": self.entity_id},
                context=context,
            )
            raise Unauthorized(context=context, entity_id=self.entity_id, permission=POLICY_CONTROL)
        await self.store.runner.async_run(self._attr_unique_id, context)
