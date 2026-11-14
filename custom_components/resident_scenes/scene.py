"""Scene entities for resident scenes."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from . import ResidentScenesConfigEntry
from .const import DOMAIN, SIGNAL_CHANGED
from .model import async_activate
from .store import SceneStore

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
        self._store = store
        self._attr_unique_id = scene_id
        self._update_attrs()

    @property
    def _scene(self) -> dict[str, Any]:
        return self._store.scenes[self._attr_unique_id]  # type: ignore[index]

    @property
    def entity_picture(self) -> str | None:
        """Return a fresh signed URL of the scene image."""
        return self._store.image_url(self._scene, content_user=True)

    def _update_attrs(self) -> None:
        scene = self._scene
        self._attr_name = scene["name"]
        self._attr_extra_state_attributes = {
            "kind": scene["kind"],
            "area_id": scene["area_id"],
            "step_count": len(scene["steps"]),
            "changed_at": scene["changed_at"],
        }

    async def async_added_to_hass(self) -> None:
        """Assign the scene to its area once registered."""
        await super().async_added_to_hass()
        self._sync_area()

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
        """Run the scene."""
        await async_activate(self.hass, self._scene, self._context)
