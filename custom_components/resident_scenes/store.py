"""Persistent scenes, favorite slots, uploaded images and the image library."""

from __future__ import annotations

from datetime import timedelta
import io
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FAVORITE_SLOTS,
    CONF_HOUSE_SCENES,
    CONF_IMAGE_COUNT,
    CONF_IMAGE_DIR,
    CONF_IMAGE_KB,
    CONF_IMAGE_SIDE,
    CONF_NAME_LENGTH,
    CONF_SCENES_PER_AREA,
    CONF_STEPS_PER_SCENE,
    EVENT_CHANGED,
    HOUSE,
    IMAGE_SUFFIXES,
    IMAGE_URL,
    KIND_INSTALLER,
    KIND_RESIDENT,
    MAX_TRANSITION,
    PHOTO_URL,
    SIGNAL_CHANGED,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPLOAD_FOLDER,
    UPLOAD_PREFIX,
)
from .model import ValidationError, allowed_entities, build_steps, music_favorites, opt, step_issue

SIGN_EXPIRY = timedelta(days=1)
UPLOAD_GRACE = 3600  # an upload not yet saved in a scene is kept this long (seconds)
MAX_PIXEL_SIDE = 4096  # refused before decoding (memory); the card uploads 640 x 480
CONTENT = ("name", "area_id", "image", "steps", "transition")


def valid_image_name(name: str) -> bool:
    """Return whether a file name is a plain image name (no path parts)."""
    path = Path(name)
    return (
        path.name == name
        and not name.startswith(".")
        and not set(name) & set("#?%")  # would break the signed URL
        and path.suffix.lower() in IMAGE_SUFFIXES
    )


def valid_upload_id(upload_id: str) -> bool:
    """Return whether an id is one the integration generates (hex name + .jpg)."""
    stem, _, suffix = upload_id.partition(".")
    return suffix == "jpg" and len(stem) == 32 and all(c in "0123456789abcdef" for c in stem)


def image_dir(hass: HomeAssistant, entry: ConfigEntry) -> Path:
    """Return the folder of the installer's image library, always inside the config folder."""
    folder = str(opt(entry, CONF_IMAGE_DIR))
    return Path(hass.config.path(folder if inside_config(hass, folder) else "resident_scenes"))


def upload_dir(hass: HomeAssistant) -> Path:
    """Return the folder of uploaded scene images (in .storage, so in every backup)."""
    return Path(hass.config.path(".storage", UPLOAD_FOLDER))


def inside_config(hass: HomeAssistant, folder: str) -> bool:
    """Return whether a folder lies inside the config folder (string check, no file access)."""
    config = os.path.normpath(hass.config.path())
    return os.path.normpath(os.path.join(config, folder)).startswith(config + os.sep)


def recode_image(data: bytes, max_side: int, max_kb: int) -> bytes:
    """Check that data is an image and re-encode it as JPEG without metadata (location, time)."""
    from PIL import Image, ImageOps, UnidentifiedImageError  # noqa: PLC0415

    formats = ["JPEG", "PNG", "WEBP"]
    try:
        with Image.open(io.BytesIO(data), formats=formats) as img:
            # the header gives the size: refuse before decoding (a small PNG can hold 13000 x 13000 pixels)
            if max(img.size) > MAX_PIXEL_SIDE:
                raise ValidationError("invalid_image_file", "too many pixels")
            img.verify()
        with Image.open(io.BytesIO(data), formats=formats) as img:
            image = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as err:
        raise ValidationError("invalid_image_file") from err
    image.thumbnail((max_side, max_side))
    for quality in (85, 75, 65, 50, 35):
        out = io.BytesIO()
        image.save(out, "JPEG", quality=quality)  # saved without EXIF: no location, no time
        if out.tell() <= max_kb * 1024:
            return out.getvalue()
    raise ValidationError("image_too_large", str(max_kb))


class _VersionedStore(Store[dict[str, Any]]):
    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Version 1 (stage 1) to 2: protection, transition and the previous state."""
        for scene in old_data.get("scenes", {}).values():
            scene.setdefault("content_released", False)
            scene.setdefault("transition", None)
            scene.setdefault("previous", None)
        return old_data


class SceneStore:
    """Scenes and favorite slots of one installation."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the store."""
        self.hass = hass
        self.entry = entry
        self._store = _VersionedStore(hass, STORAGE_VERSION, STORAGE_KEY)
        self.scenes: dict[str, dict[str, Any]] = {}
        self.favorites: dict[str, list[str | None]] = {}
        self.images: list[str] = []
        self._signed: dict[str, tuple[str, float]] = {}
        self.runner: Any = None  # SceneRunner, set up after loading
        self.previews: dict[Any, dict[str, Any]] = {}  # live preview per connection: states before editing

    async def async_load(self) -> None:
        """Load scenes and favorite slots and scan the image library."""
        data = await self._store.async_load() or {}
        self.scenes = data.get("scenes", {})
        self.favorites = data.get("favorites", {})
        await self.async_scan_images()
        # areas deleted while Home Assistant was stopped
        areas = ar.async_get(self.hass)
        if gone := {s["area_id"] for s in self.scenes.values() if s["area_id"]} - set(areas.areas):
            for area_id in gone:
                self._move_to_house(area_id)
            await self._async_commit()

    @callback
    def async_listen(self) -> None:
        """Follow deleted areas and renamed entity ids."""
        hass = self.hass
        self.entry.async_on_unload(
            hass.bus.async_listen(ar.EVENT_AREA_REGISTRY_UPDATED, self._area_updated)
        )
        self.entry.async_on_unload(
            hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._entity_updated)
        )

    async def _area_updated(self, event: Event[ar.EventAreaRegistryUpdatedData]) -> None:
        if event.data["action"] == "remove" and self._move_to_house(event.data["area_id"]):
            await self._async_commit()

    async def _entity_updated(self, event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        data = event.data
        if data["action"] != "update" or not (old := data.get("old_entity_id")):
            return
        changed = False
        for scene in self.scenes.values():
            for step in scene["steps"]:
                if step.get("entity_id") == old:
                    step["entity_id"] = data["entity_id"]
                    scene["version"] += 1  # open editors hold the old id
                    changed = True
        if changed:
            await self._async_commit()

    def _move_to_house(self, area_id: str) -> bool:
        """Scenes of a deleted area become house scenes; its favorite slots go."""
        moved = [s for s in self.scenes.values() if s["area_id"] == area_id]
        self.favorites.pop(area_id, None)
        for scene in moved:
            scene["name"] = self._free_name(scene["name"], None, scene["id"])
            scene["area_id"] = None
            scene["version"] += 1
            self.hass.bus.async_fire(
                EVENT_CHANGED, {"scene_id": scene["id"], "name": scene["name"], "action": "moved to house"}
            )
        return bool(moved)

    def _free_name(self, name: str, area_id: str | None, own_id: str) -> str:
        """Return the name, with a suffix like ' (2)' if another scene of the area has it."""
        names = {
            s["name"].casefold() for s in self.scenes.values() if s["area_id"] == area_id and s["id"] != own_id
        }
        base, result, n = name, name, 2
        while result.casefold() in names:
            suffix = f" ({n})"
            result = base[: int(opt(self.entry, CONF_NAME_LENGTH)) - len(suffix)] + suffix
            n += 1
        return result

    # ---------- images ----------

    async def async_scan_images(self) -> None:
        """Read the image library folder."""
        folder = image_dir(self.hass, self.entry)

        def scan() -> list[str]:
            if not folder.is_dir():
                return []
            return sorted(p.name for p in folder.iterdir() if p.is_file() and valid_image_name(p.name))

        self.images = await self.hass.async_add_executor_job(scan)

    def image_url(self, scene: dict[str, Any]) -> str | None:
        """Return a signed URL for the scene image or the default image of its area."""
        name = scene.get("image")
        if name is None and scene.get("area_id"):
            name = next((i for i in self.images if Path(i).stem == scene["area_id"]), None)
        return None if name is None else self.sign(name)

    def sign(self, name: str) -> str:
        """Sign the URL of an image, reused for half its lifetime so browsers can cache it.

        Signed with the content user, so the URL does not depend on the login of the
        account that asked first (it stays valid when that account logs out).
        """
        now = dt_util.utcnow().timestamp()
        if (cached := self._signed.get(name)) and cached[1] > now:
            return cached[0]
        if name.startswith(UPLOAD_PREFIX):
            path = f"{PHOTO_URL}/{name.removeprefix(UPLOAD_PREFIX)}"
        else:
            path = f"{IMAGE_URL}/{quote(name)}"
        url = async_sign_path(self.hass, path, SIGN_EXPIRY, use_content_user=True)
        self._signed[name] = (url, now + SIGN_EXPIRY.total_seconds() / 2)
        return url

    async def async_add_upload(self, data: bytes) -> str:
        """Check, shrink and re-encode an uploaded image; return its image name."""
        folder = upload_dir(self.hass)
        await self._async_clean_uploads()
        # files on disk count, also fresh uploads no scene uses yet
        count = await self.hass.async_add_executor_job(lambda: len(list(folder.glob("*.jpg"))))
        if count >= int(opt(self.entry, CONF_IMAGE_COUNT)):
            raise ValidationError("image_limit", str(opt(self.entry, CONF_IMAGE_COUNT)))
        upload_id = f"{uuid4().hex}.jpg"
        max_side, max_kb = int(opt(self.entry, CONF_IMAGE_SIDE)), int(opt(self.entry, CONF_IMAGE_KB))

        def write() -> None:
            jpeg = recode_image(data, max_side, max_kb)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / upload_id).write_bytes(jpeg)

        await self.hass.async_add_executor_job(write)
        return UPLOAD_PREFIX + upload_id

    def _uploads_in_use(self) -> set[str]:
        """Uploaded images still needed by a scene or by its previous state (for undo)."""
        names = set()
        for scene in self.scenes.values():
            for content in (scene, scene.get("previous") or {}):
                if (image := content.get("image")) and image.startswith(UPLOAD_PREFIX):
                    names.add(image.removeprefix(UPLOAD_PREFIX))
        return names

    async def _async_clean_uploads(self) -> None:
        keep = self._uploads_in_use()
        folder = upload_dir(self.hass)

        def clean() -> None:
            if not folder.is_dir():
                return
            for path in folder.iterdir():
                # fresh uploads are kept a while: the card uploads first and saves the scene after
                if path.name not in keep and path.stat().st_mtime < time.time() - UPLOAD_GRACE:
                    path.unlink(missing_ok=True)

        await self.hass.async_add_executor_job(clean)

    async def _async_image_exists(self, image: str) -> bool:
        if not image.startswith(UPLOAD_PREFIX):
            return image in self.images
        upload_id = image.removeprefix(UPLOAD_PREFIX)
        path = upload_dir(self.hass) / upload_id
        return valid_upload_id(upload_id) and await self.hass.async_add_executor_job(path.is_file)

    # ---------- scenes ----------

    def slots(self, scope: str) -> list[str | None]:
        """Return the favorite slots of a scope, padded to the configured count."""
        count = int(opt(self.entry, CONF_FAVORITE_SLOTS))
        current = self.favorites.get(scope, [])[:count]
        return current + [None] * (count - len(current))

    def editable(self, scene: dict[str, Any], is_admin: bool) -> bool:
        """Return whether an editor may change the steps of a scene."""
        return is_admin or scene["kind"] != KIND_INSTALLER or scene["content_released"]

    def used_in(self, scene_id: str) -> dict[str, list[str]]:
        """Return the house scenes calling a scene and the favorite slots it is on."""
        callers = [
            s["name"] for s in self.scenes.values() if any(st.get("scene_id") == scene_id for st in s["steps"])
        ]
        slots = [
            f"{scope}:{i + 1}" for scope, ids in self.favorites.items() for i, s in enumerate(ids) if s == scene_id
        ]
        return {"scenes": callers, "slots": slots}

    async def async_save_scene(
        self,
        payload: dict[str, Any],
        user_id: str | None,
        is_admin: bool = False,
        new_id: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        """Validate and store a new or changed scene."""
        scene_id: str | None = payload.get("scene_id")
        existing = self.scenes.get(scene_id) if scene_id else None
        if scene_id and existing is None:
            raise ValidationError("not_found")
        if existing and payload.get("version") != existing["version"]:
            raise ValidationError("version_conflict")

        name = payload["name"].strip()
        area_id: str | None = payload.get("area_id")
        image = payload.get("image")
        kind = existing["kind"] if existing else KIND_RESIDENT
        released = existing["content_released"] if existing else False
        if is_admin:
            kind = payload.get("kind", kind)
            released = payload.get("content_released", released)
        elif existing and kind == KIND_INSTALLER:
            # residents change only the content of a released installer scene (spec 2)
            if not released:
                raise ValidationError("protected")
            if (name, area_id, image) != (existing["name"], existing["area_id"], existing["image"]):
                raise ValidationError("protected")
        elif payload.get("kind", KIND_RESIDENT) != KIND_RESIDENT or "content_released" in payload:
            raise ValidationError("unauthorized")
        if not name or len(name) > int(opt(self.entry, CONF_NAME_LENGTH)):
            raise ValidationError("invalid_name")
        if area_id and ar.async_get(self.hass).async_get_area(area_id) is None:
            raise ValidationError("invalid_area")
        others = [s for s in self.scenes.values() if s["id"] != scene_id and s["area_id"] == area_id]
        if any(s["name"].casefold() == name.casefold() for s in others):
            raise ValidationError("name_exists")
        limit = int(opt(self.entry, CONF_SCENES_PER_AREA if area_id else CONF_HOUSE_SCENES))
        if len(others) >= limit and not (existing and existing["area_id"] == area_id):
            raise ValidationError("limit_reached")
        if len(payload["steps"]) > int(opt(self.entry, CONF_STEPS_PER_SCENE)):
            raise ValidationError("too_many_steps")
        if image is not None and image != (existing or {}).get("image") and not await self._async_image_exists(image):
            raise ValidationError("invalid_image")
        transition = payload.get("transition")
        if transition is not None and not 0 <= transition <= MAX_TRANSITION:
            raise ValidationError("invalid_value", "transition")
        base_id = payload.get("copy_from") or scene_id
        if base_id and base_id not in self.scenes:
            raise ValidationError("not_found")
        base_steps = self.scenes[base_id]["steps"] if base_id else []
        steps = build_steps(self.hass, self.entry, payload["steps"], base_steps, area_id, self.scenes, scene_id)

        scene = {
            "id": scene_id or new_id or uuid4().hex,
            "name": name,
            "area_id": area_id,
            "image": image,
            "kind": kind,
            "content_released": bool(released) and kind == KIND_INSTALLER,
            "transition": transition,
            "steps": steps,
            "version": existing["version"] + 1 if existing else 1,
            "changed_by": user_id,
            "changed_at": dt_util.utcnow().isoformat(),
            "previous": {k: existing[k] for k in CONTENT} if existing else None,
        }
        if existing and existing["area_id"] != area_id:
            self._clear_favorites(scene["id"])
        self.scenes[scene["id"]] = scene
        if commit:
            await self._async_commit()
        return scene

    async def async_undo(self, scene_id: str, version: int, user_id: str | None, is_admin: bool) -> dict[str, Any]:
        """Bring back the state before the last change (including its image)."""
        scene = self.scenes.get(scene_id)
        if scene is None:
            raise ValidationError("not_found")
        if scene["version"] != version:
            raise ValidationError("version_conflict")
        if not scene["previous"]:
            raise ValidationError("nothing_to_undo")
        if not self.editable(scene, is_admin):
            raise ValidationError("protected")
        previous = dict(scene["previous"])
        if not is_admin and scene["kind"] == KIND_INSTALLER:
            # residents take back only content; name, area and image stay the installer's (spec 2)
            previous = {k: v for k, v in previous.items() if k in ("steps", "transition")}
            previous |= {k: scene[k] for k in ("name", "area_id", "image")}
        if previous["area_id"] and ar.async_get(self.hass).async_get_area(previous["area_id"]) is None:
            previous["area_id"] = None
        if previous["area_id"] != scene["area_id"]:
            self._clear_favorites(scene_id)
        previous["name"] = self._free_name(previous["name"], previous["area_id"], scene_id)
        scene.update(previous)
        scene.update(
            version=scene["version"] + 1, previous=None, changed_by=user_id, changed_at=dt_util.utcnow().isoformat()
        )
        await self._async_commit()
        return scene

    async def async_capture(self, scene_id: str, user_id: str | None) -> dict[str, Any]:
        """Take over the current state of every device of a scene (action resident_scenes.capture)."""
        scene = self.scenes[scene_id]
        allowed = allowed_entities(self.hass, self.entry)
        favorites = music_favorites(self.hass)
        raw = []
        for step in scene["steps"]:
            entry = {"delay": step.get("delay", 0)}
            if "scene_id" in step:  # a stored call is kept, also when its target is gone
                raw.append({**entry, "mode": "scene", "scene_id": step["scene_id"]})
                continue
            # missing, unreachable, moved or no longer released: keep the stored value (spec 4.5)
            issue = step_issue(self.hass, scene["area_id"], step, allowed, favorites)
            mode = "capture" if issue in (None, "favorite_missing") else "keep"
            raw.append({**entry, "entity_id": step["entity_id"], "mode": mode})
        payload = {k: scene[k] for k in CONTENT if scene[k] is not None or k != "transition"}
        payload |= {"scene_id": scene_id, "version": scene["version"], "steps": raw}
        return await self.async_save_scene(payload, user_id, is_admin=True)

    async def async_delete_scene(self, scene_id: str, is_admin: bool = False) -> dict[str, Any]:
        """Delete a scene and empty its favorite slots; callers keep a 'scene missing' step."""
        scene = self.scenes.get(scene_id)
        if scene is None:
            raise ValidationError("not_found")
        if scene["kind"] == KIND_INSTALLER and not is_admin:
            raise ValidationError("protected")
        del self.scenes[scene_id]
        self._clear_favorites(scene_id)
        if self.runner is not None:
            self.runner.async_forget(scene_id)
        await self._async_commit()
        return scene

    async def async_import(self, template: dict[str, Any]) -> int:
        """Load installer scenes from a template (spec 4.1); returns the number of scenes.

        Scenes carry a ``key``; a scene of an earlier template with the same key is replaced.
        """
        backup = dict(self.scenes), {k: list(v) for k, v in self.favorites.items()}
        try:
            count = await self._async_import(template)
        except Exception:
            self.scenes.clear()  # all or nothing: the runner holds this dict
            self.scenes.update(backup[0])
            self.favorites = backup[1]
            raise
        await self._async_commit()
        return count

    async def _async_import(self, template: dict[str, Any]) -> int:
        count = 0
        for item in template.get("scenes", []):
            scene_id = f"tpl_{item['key']}"
            existing = self.scenes.get(scene_id)
            payload = {
                "name": item["name"],
                "area_id": item.get("area_id"),
                "image": item.get("image"),
                "kind": KIND_INSTALLER,
                "content_released": bool(item.get("content_released", False)),
                "steps": item.get("steps", []),
            }
            if item.get("transition") is not None:
                payload["transition"] = item["transition"]
            if existing:
                payload |= {"scene_id": scene_id, "version": existing["version"]}
            # the template key gives a stable id, so a later template replaces this scene
            await self.async_save_scene(payload, None, is_admin=True, new_id=scene_id, commit=False)
            count += 1
        return count

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
        await self._async_clean_uploads()
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)

