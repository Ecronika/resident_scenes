"""Persistent scenes, favorite slots and the image library."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FAVORITE_SLOTS,
    CONF_HOUSE_SCENES,
    CONF_IMAGE_DIR,
    CONF_NAME_LENGTH,
    CONF_SCENES_PER_AREA,
    CONF_STEPS_PER_SCENE,
    HOUSE,
    IMAGE_SUFFIXES,
    IMAGE_URL,
    SIGNAL_CHANGED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .model import ValidationError, build_steps, opt

SIGN_EXPIRY = timedelta(days=1)


def valid_image_name(name: str) -> bool:
    """Return whether a file name is a plain image name (no path parts)."""
    path = Path(name)
    return path.name == name and not name.startswith(".") and path.suffix.lower() in IMAGE_SUFFIXES


def image_dir(hass: HomeAssistant, entry: ConfigEntry) -> Path:
    """Return the folder of the installer's image library."""
    return Path(hass.config.path(opt(entry, CONF_IMAGE_DIR)))


class SceneStore:
    """Scenes and favorite slots of one installation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the store."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.scenes: dict[str, dict[str, Any]] = {}
        self.favorites: dict[str, list[str | None]] = {}
        self.images: list[str] = []

    async def async_load(self) -> None:
        """Load scenes and favorite slots and scan the image library."""
        data = await self._store.async_load() or {}
        self.scenes = data.get("scenes", {})
        self.favorites = data.get("favorites", {})
        await self.async_scan_images()

    async def async_scan_images(self) -> None:
        """Read the image library folder."""
        folder = image_dir(self.hass, self.entry)

        def scan() -> list[str]:
            if not folder.is_dir():
                return []
            return sorted(p.name for p in folder.iterdir() if p.is_file() and valid_image_name(p.name))

        self.images = await self.hass.async_add_executor_job(scan)

    def image_url(self, scene: dict[str, Any], *, content_user: bool = False) -> str | None:
        """Return a signed URL for the scene image or the default image of its area."""
        name = scene.get("image")
        if name is None and scene.get("area_id"):
            name = next((i for i in self.images if Path(i).stem == scene["area_id"]), None)
        if name is None:
            return None
        return self.sign(name, content_user=content_user)

    def sign(self, name: str, *, content_user: bool = False) -> str:
        """Sign the URL of a library image."""
        return async_sign_path(
            self.hass, f"{IMAGE_URL}/{quote(name)}", SIGN_EXPIRY, use_content_user=content_user
        )

    def slots(self, scope: str) -> list[str | None]:
        """Return the favorite slots of a scope, padded to the configured count."""
        count = int(opt(self.entry, CONF_FAVORITE_SLOTS))
        current = self.favorites.get(scope, [])[:count]
        return current + [None] * (count - len(current))

    async def async_save_scene(self, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Validate and store a new or changed scene."""
        scene_id: str | None = payload.get("scene_id")
        existing = self.scenes.get(scene_id) if scene_id else None
        if scene_id and existing is None:
            raise ValidationError("not_found")
        if existing and payload.get("version") != existing["version"]:
            raise ValidationError("version_conflict")

        name = payload["name"].strip()
        area_id: str | None = payload.get("area_id")
        if not name or len(name) > int(opt(self.entry, CONF_NAME_LENGTH)):
            raise ValidationError("invalid_name")
        if area_id and ar.async_get(self.hass).async_get_area(area_id) is None:
            raise ValidationError("invalid_area")
        others = [s for s in self.scenes.values() if s["id"] != scene_id and s["area_id"] == area_id]
        if any(s["name"].casefold() == name.casefold() for s in others):
            raise ValidationError("name_exists")
        limit = int(opt(self.entry, CONF_SCENES_PER_AREA if area_id else CONF_HOUSE_SCENES))
        if len(others) >= limit:
            raise ValidationError("limit_reached")
        if len(payload["steps"]) > int(opt(self.entry, CONF_STEPS_PER_SCENE)):
            raise ValidationError("too_many_steps")
        image = payload.get("image")
        if image is not None and image not in self.images:
            raise ValidationError("invalid_image")
        base_id = payload.get("copy_from") or scene_id
        if base_id and base_id not in self.scenes:
            raise ValidationError("not_found")
        base_steps = self.scenes[base_id]["steps"] if base_id else []
        steps = build_steps(self.hass, self.entry, payload["steps"], base_steps)

        scene = {
            "id": scene_id or uuid4().hex,
            "name": name,
            "area_id": area_id,
            "image": image,
            "kind": existing["kind"] if existing else "resident",
            "steps": steps,
            "version": existing["version"] + 1 if existing else 1,
            "changed_by": user_id,
            "changed_at": dt_util.utcnow().isoformat(),
        }
        if existing and existing["area_id"] != area_id:
            self._clear_favorites(scene["id"])
        self.scenes[scene["id"]] = scene
        await self._async_commit()
        return scene

    async def async_delete_scene(self, scene_id: str) -> dict[str, Any]:
        """Delete a scene and empty its favorite slots."""
        if (scene := self.scenes.pop(scene_id, None)) is None:
            raise ValidationError("not_found")
        self._clear_favorites(scene_id)
        await self._async_commit()
        return scene

    async def async_set_favorite(self, scope: str, slot: int, scene_id: str | None) -> None:
        """Put a scene on a favorite slot (or empty it); a scene uses one slot per scope."""
        # only known scopes, otherwise any editor could grow the storage with made-up keys
        if scope != HOUSE and ar.async_get(self.hass).async_get_area(scope) is None:
            raise ValidationError("invalid_slot")
        slots = self.slots(scope)
        if not 0 <= slot < len(slots):
            raise ValidationError("invalid_slot")
        if scene_id is not None:
            scene = self.scenes.get(scene_id)
            if scene is None:
                raise ValidationError("not_found")
            if (scene["area_id"] or HOUSE) != scope:
                raise ValidationError("invalid_slot")
            slots = [None if s == scene_id else s for s in slots]
        slots[slot] = scene_id
        self.favorites[scope] = slots
        await self._async_commit()

    def _clear_favorites(self, scene_id: str) -> None:
        for scope, slots in self.favorites.items():
            self.favorites[scope] = [None if s == scene_id else s for s in slots]

    async def _async_commit(self) -> None:
        await self._store.async_save({"scenes": self.scenes, "favorites": self.favorites})
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)
