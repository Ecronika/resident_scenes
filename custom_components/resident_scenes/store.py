"""Persistent scenes, favorite slots, schedules, uploaded images and the image library."""

from __future__ import annotations

import asyncio
from copy import deepcopy
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
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify

from .const import (
    ALLOWED_DOMAINS,
    CONF_ALL_OFF,
    CONF_HOUSE_SCENES,
    CONF_IMAGE_COUNT,
    CONF_IMAGE_DIR,
    CONF_IMAGE_KB,
    CONF_IMAGE_SIDE,
    CONF_MAX_DELAY,
    CONF_NAME_LENGTH,
    CONF_ROOMS,
    CONF_SCENES_PER_AREA,
    CONF_SCHEDULES,
    CONF_STEPS_PER_SCENE,
    DOMAIN,
    EVENT_CHANGED,
    HOUSE,
    IMAGE_SUFFIXES,
    IMAGE_URL,
    KIND_INSTALLER,
    KIND_RESIDENT,
    MAX_OFFSET,
    MAX_TRANSITION,
    PHOTO_URL,
    SIGNAL_CHANGED,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPLOAD_FOLDER,
    UPLOAD_PREFIX,
)
from .model import (
    ValidationError,
    allowed_entities,
    build_step,
    entity_area,
    entries,
    group_steps,
    music_favorites,
    new_step_id,
    opt,
    slot_count,
    step_issue,
)
from .schedules import target

SIGN_EXPIRY = timedelta(days=1)
UPLOAD_GRACE = 3600  # an upload not yet saved in a scene is kept this long (seconds)
MAX_PIXEL_SIDE = 4096  # refused before decoding (memory); the card uploads 640 x 480
CONTENT = ("name", "area_id", "image", "sequence", "transition")
SAVE_DELAY = 10  # seconds; inputs come in bursts while editing, Home Assistant writes pending data on stop
EDITS_KEPT = 20  # edit ids remembered per scene
EDIT_IDLE = 600  # seconds; an edit ends after this long without input (review W3)
LIVE_DOMAINS = frozenset({"light", "cover", "switch", "fan"})


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
        """Version 1 to 2: protection, transition, previous state. 2 to 3: steps become a sequence.

        3 to 4: an empty list of schedules; scenes, images and slots stay as they are (spec 4.11).
        """
        old_data.setdefault("schedules", [])
        scenes = old_data.get("scenes", {})
        for scene in scenes.values():
            scene.setdefault("content_released", False)
            scene.setdefault("transition", None)
            scene.setdefault("previous", None)
            if old_major_version < 3:
                for content in (scene, scene["previous"]):
                    if content and "steps" in content:
                        content["sequence"] = group_steps(self.hass, content["area_id"], content.pop("steps"), scenes)
                scene["entity_named"] = True
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
        self.schedules: list[dict[str, Any]] = []  # in the order of the list (spec 4.15)
        self.images: list[str] = []
        self._signed: dict[str, tuple[str, float]] = {}
        self.runner: Any = None  # SceneRunner, set up after loading
        self.scheduler: Any = None  # Scheduler, set up after loading
        self._upload_lock = asyncio.Lock()  # one image decoded at a time, about 130 MB each (review T5)
        self._save_since: float | None = None  # first input not yet on disk (review W6)

    async def async_load(self) -> None:
        """Load scenes and favorite slots and scan the image library."""
        data = await self._store.async_load() or {}
        self.scenes = data.get("scenes", {})
        self.favorites = data.get("favorites", {})
        self.schedules = data.get("schedules", [])
        await self.async_scan_images()
        # areas deleted while Home Assistant was stopped
        areas = ar.async_get(self.hass)
        used = {s["area_id"] for s in self.scenes.values()} | {
            g["area_id"] for s in self.scenes.values() for g in s["sequence"] if g["type"] == "group"
        }
        if gone := used - {None} - set(areas.areas):
            for area_id in gone:
                self._move_to_house(area_id)
            await self._async_commit()
        if self._follow_moves():  # devices moved while Home Assistant was stopped
            await self._async_commit()
        self._drop_room_rights(set(areas.areas))

    @callback
    def async_listen(self) -> None:
        """Follow deleted areas, renamed entity ids and devices that move to another room."""
        hass = self.hass
        self.entry.async_on_unload(
            hass.bus.async_listen(ar.EVENT_AREA_REGISTRY_UPDATED, self._area_updated)
        )
        self.entry.async_on_unload(
            hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._entity_updated)
        )
        self.entry.async_on_unload(
            hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._device_updated)
        )

    async def _device_updated(self, event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        if "area_id" in event.data.get("changes", {}) and (self._follow_moves() | self._sync_schedules()):
            await self._async_commit()

    async def _area_updated(self, event: Event[ar.EventAreaRegistryUpdatedData]) -> None:
        if event.data["action"] != "remove":
            return
        self._drop_room_rights(set(ar.async_get(self.hass).areas))
        if self._move_to_house(event.data["area_id"]):
            await self._async_commit()

    @callback
    def _drop_room_rights(self, areas: set[str]) -> None:
        """The room right and the "all off" setting of a deleted room go (spec 3, 4.1).

        A new room of the same id is not granted by them.
        """
        rooms, all_off = opt(self.entry, CONF_ROOMS), opt(self.entry, CONF_ALL_OFF)
        kept = {uid: [a for a in ids if a in areas] for uid, ids in rooms.items()}
        kept_off = {a: parts for a, parts in all_off.items() if a in areas}
        if kept != rooms or kept_off != all_off:
            options = {**self.entry.options, CONF_ROOMS: kept, CONF_ALL_OFF: kept_off}
            self.hass.config_entries.async_update_entry(self.entry, options=options)

    async def _entity_updated(self, event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        data = event.data
        if data["action"] != "update":
            return
        changed = "area_id" in data.get("changes", {}) and (self._follow_moves() | self._sync_schedules())
        if not (old := data.get("old_entity_id")):
            if changed:
                await self._async_commit()
            return
        for scene in self.scenes.values():
            for step in entries(scene["sequence"]):
                if step.get("entity_id") == old:
                    step["entity_id"] = data["entity_id"]
                    scene["version"] += 1  # open editors hold the old id
                    changed = True
        if changed:
            await self._async_commit()

    def _move_to_house(self, area_id: str) -> bool:
        """Scenes of a deleted area become house scenes; its favorite slots go.

        Group steps of the area become steps without a room, which stay changeable (review W1).
        """
        moved = [s for s in self.scenes.values() if s["area_id"] == area_id]
        self.favorites.pop(area_id, None)
        loose = False
        for scene in self.scenes.values():
            for step in scene["sequence"]:
                if step["type"] == "group" and step["area_id"] == area_id:
                    step["area_id"] = None
                    loose = True
                    if scene not in moved:
                        scene["version"] += 1
        for scene in moved:
            scene["name"] = self._free_name(scene["name"], None, scene["id"])
            scene["area_id"] = None
            scene["version"] += 1
            self.hass.bus.async_fire(
                EVENT_CHANGED, {"scene_id": scene["id"], "name": scene["name"], "action": "moved to house"}
            )
        for schedule in self.schedules:  # also one whose scene is missing goes to the house (spec 4.15)
            if schedule["area_id"] == area_id:
                schedule["area_id"] = None
                loose = True
        return bool(moved) or loose

    def _follow_moves(self) -> bool:
        """Entries of a house scene follow their device into its new room (spec 4.5).

        The entry goes into the next step of that room and domain before the next delay, else into a new
        step right after its old one; an entry of the device already there wins; a step left empty goes.
        Steps of a deleted room are left to _move_to_house.
        """
        ent_reg, areas = er.async_get(self.hass), ar.async_get(self.hass).areas
        changed = False
        for scene in self.scenes.values():
            if scene["area_id"]:
                continue  # in a room scene a moved device is skipped, the entry stays (spec 4.5)
            sequence, index, moved = scene["sequence"], 0, False
            while index < len(sequence):
                step = sequence[index]
                index += 1
                if step["type"] != "group" or (step["area_id"] and step["area_id"] not in areas):
                    continue
                left = False
                for entry in list(step["entries"]):
                    ent = ent_reg.async_get(entry["entity_id"])
                    if ent is None or (area := entity_area(self.hass, ent)) == step["area_id"]:
                        continue
                    target = None
                    for later in sequence[index:]:
                        if later["type"] == "delay":
                            break
                        if later["type"] == "group" and (later["domain"], later["area_id"]) == (step["domain"], area):
                            target = later
                            break
                    if target is None:
                        target = {"id": new_step_id(sequence), "type": "group", "domain": step["domain"],
                                  "area_id": area, "entries": []}
                        sequence.insert(index, target)
                    if all(e["entity_id"] != entry["entity_id"] for e in target["entries"]):
                        target["entries"].append(entry)
                    step["entries"].remove(entry)
                    left = moved = True
                if left and not step["entries"]:
                    index -= 1
                    del sequence[index]
            if moved:
                scene["version"] += 1  # open editors hold the old steps
                changed = True
                # not an edit; named once per scene (spec 4.5, review AE2)
                self.hass.bus.async_fire(
                    EVENT_CHANGED,
                    {
                        "scene_id": scene["id"],
                        "name": scene["name"],
                        "action": "follows moved devices",
                        "entity_id": ent_reg.async_get_entity_id("scene", DOMAIN, scene["id"]),
                    },
                )
        return changed

    def _sync_schedules(self) -> bool:
        """A schedule keeps room and name of its scene, also once the scene is gone (spec 4.15)."""
        changed = False
        for schedule in self.schedules:
            scene = target(self.hass, self, schedule)
            if (scene["area_id"], scene["name"]) != (schedule["area_id"], schedule["scene_name"]):
                schedule["area_id"], schedule["scene_name"] = scene["area_id"], scene["name"]
                changed = True
        return changed

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
        upload_id = f"{uuid4().hex}.jpg"
        max_side, max_kb = int(opt(self.entry, CONF_IMAGE_SIDE)), int(opt(self.entry, CONF_IMAGE_KB))

        def write() -> None:
            jpeg = recode_image(data, max_side, max_kb)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / upload_id).write_bytes(jpeg)

        async with self._upload_lock:  # counted inside, so parallel uploads cannot pass the limit (review U2)
            await self._async_clean_uploads()
            # files on disk count, also fresh uploads no scene uses yet
            count = await self.hass.async_add_executor_job(lambda: len(list(folder.glob("*.jpg"))))
            if count >= int(opt(self.entry, CONF_IMAGE_COUNT)):
                raise ValidationError("image_limit", str(opt(self.entry, CONF_IMAGE_COUNT)))
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
        count = slot_count(self.entry, scope)
        current = self.favorites.get(scope, [])[:count]
        return current + [None] * (count - len(current))

    def editable(self, scene: dict[str, Any], is_admin: bool) -> bool:
        """Return whether an editor may change the steps of a scene."""
        return is_admin or scene["kind"] != KIND_INSTALLER or scene["content_released"]

    def used_in(self, scene_id: str) -> dict[str, list[str]]:
        """Return the house scenes calling a scene, the favorite slots it is on and its schedules (spec 4.5)."""
        callers = [
            s["name"]
            for s in self.scenes.values()
            if any(st.get("scene_id") == scene_id for st in entries(s["sequence"]))
        ]
        slots = [
            f"{scope}:{i + 1}" for scope, ids in self.favorites.items() for i, s in enumerate(ids) if s == scene_id
        ]
        schedules = [s["name"] for s in self.schedules if s["scene_id"] == scene_id]
        return {"scenes": callers, "slots": slots, "schedules": schedules}

    def _check_name(self, name: str, area_id: str | None, own_id: str | None) -> str:
        """Return the stripped name; empty, too long or taken in the area is refused."""
        name = name.strip()
        if not name or len(name) > int(opt(self.entry, CONF_NAME_LENGTH)):
            raise ValidationError("invalid_name")
        others = (s for s in self.scenes.values() if s["area_id"] == area_id and s["id"] != own_id)
        if any(s["name"].casefold() == name.casefold() for s in others):
            raise ValidationError("name_exists")
        return name

    def _new_scene(self, scene_id: str, area_id: str | None, user_id: str | None) -> dict[str, Any]:
        """Return an empty scene (name still to set) after the checks for area and limit."""
        if area_id and ar.async_get(self.hass).async_get_area(area_id) is None:
            raise ValidationError("invalid_area")
        existing = self.scenes.get(scene_id)
        others = [s for s in self.scenes.values() if s["area_id"] == area_id and s["id"] != scene_id]
        limit = int(opt(self.entry, CONF_SCENES_PER_AREA if area_id else CONF_HOUSE_SCENES))
        if len(others) >= limit and not (existing and existing["area_id"] == area_id):
            raise ValidationError("limit_reached")
        return {
            "id": scene_id,
            "name": "",
            "area_id": area_id,
            "image": None,
            "kind": KIND_RESIDENT,
            "content_released": False,
            "transition": None,
            "sequence": [],
            "version": existing["version"] + 1 if existing else 1,
            "changed_by": user_id,
            "changed_at": dt_util.utcnow().isoformat(),
            "previous": None,
            "entity_named": False,
            "edits": [],
        }

    async def _async_add(self, scene: dict[str, Any], edit: str) -> dict[str, Any]:
        """Store a created scene; its creating edit has nothing to undo."""
        scene["edits"] = [[edit, scene["changed_by"], dt_util.utcnow().timestamp()]]
        scene["creating_edit"] = [edit, scene["changed_by"]]
        self.scenes[scene["id"]] = scene
        await self._async_commit()
        return scene

    async def async_create(self, area_id: str | None, name: str, edit: str, user_id: str | None) -> dict[str, Any]:
        """Create an empty scene named '<name> N' with the smallest free N."""
        scene = self._new_scene(uuid4().hex, area_id, user_id)
        base, length = name.strip(), int(opt(self.entry, CONF_NAME_LENGTH))
        if not base:
            raise ValidationError("invalid_name")
        taken = {s["name"].casefold() for s in self.scenes.values() if s["area_id"] == area_id}
        n = 1
        while (candidate := f"{base[: length - len(str(n)) - 1]} {n}").casefold() in taken:
            n += 1
        scene["name"] = self._check_name(candidate, area_id, None)
        return await self._async_add(scene, edit)

    async def async_duplicate(self, scene_id: str, suffix: str, edit: str, user_id: str | None) -> dict[str, Any]:
        """Copy a scene with new step ids under a free name with the suffix."""
        if (source := self.scenes.get(scene_id)) is None:
            raise ValidationError("not_found")
        scene = self._new_scene(uuid4().hex, source["area_id"], user_id)
        length = int(opt(self.entry, CONF_NAME_LENGTH))
        name = (source["name"][: max(0, length - len(suffix))] + suffix)[:length]
        scene["name"] = self._check_name(self._free_name(name, source["area_id"], scene["id"]), source["area_id"], None)
        sequence: list[dict[str, Any]] = []
        for step in deepcopy(source["sequence"]):
            step["id"] = new_step_id(sequence)
            sequence.append(step)
        scene |= {"image": source["image"], "transition": source["transition"], "sequence": sequence}
        return await self._async_add(scene, edit)

    # ---------- inputs of the editor ----------

    async def async_input(
        self, msg: dict[str, Any], user_id: str | None, is_admin: bool
    ) -> tuple[dict[str, Any], bool, dict[str, Any]]:
        """Apply one input (WebSocket command) to a scene.

        Returns the changed scene, whether the input began an edit, and the command's result.
        """
        command = msg["type"].rsplit("/", 1)[1]
        if command == "update":
            await self._async_check_update(self._editable(msg["scene_id"], is_admin), msg, is_admin)
        scene = self._editable(msg["scene_id"], is_admin)  # again: inputs may have come during the check (W4)
        work = deepcopy(scene)
        result = getattr(self, f"_{command}")(work, msg, is_admin) or {}
        if work == scene:  # an input that changes nothing begins no edit and keeps the undo state (review AA4)
            return scene, False, result
        began = self._apply(scene, work, msg["edit"], user_id)
        # the entity id stays from now on once the edit that created the scene is over: a new edit of its creator,
        # any edit after it went idle, or its own id after it went idle (that input begins a new edit, review Z1);
        # another account's edit meanwhile does not end it (spec 4.3, review Y6)
        creating = work.get("creating_edit")
        if (
            began
            if [msg["edit"], user_id] == creating
            else creating not in [e[:2] for e in work["edits"]] or user_id == creating[1]
        ):
            work["entity_named"] = True
        if command == "update" and work["name"] != scene["name"]:
            self._rename_entity(work, "scene")
        if command == "update" and "image" in msg:
            await self._async_commit()  # also cleans the uploads
        else:
            self._changed()
        return work, began, result

    def _editable(self, scene_id: str, is_admin: bool) -> dict[str, Any]:
        scene = self.scenes.get(scene_id)
        if scene is None:
            raise ValidationError("not_found")
        if not self.editable(scene, is_admin):
            raise ValidationError("protected")
        return scene

    def _check_size(self, before: list[dict[str, Any]], after: list[dict[str, Any]]) -> None:
        """Entries plus scene steps, and steps, stay within the limit (a lowered limit still allows shrinking)."""
        limit = int(opt(self.entry, CONF_STEPS_PER_SCENE))

        def size(sequence: list[dict[str, Any]]) -> int:
            return max(len(list(entries(sequence))), len(sequence))

        if size(after) > limit and size(after) > size(before):
            raise ValidationError("too_many_steps")

    def _apply(self, scene: dict[str, Any], work: dict[str, Any], edit: str, user_id: str | None) -> bool:
        """Put the changed copy in place; an unknown edit id begins an edit (the state before can be undone).

        An edit id belongs to one account and ends after EDIT_IDLE seconds without input (review W3).
        It is stored with the scene, so a restart does not begin a second edit (review W5).
        """
        self._check_size(scene["sequence"], work["sequence"])
        now = dt_util.utcnow().timestamp()
        edits = [e for e in scene.get("edits", []) if now - e[2] <= EDIT_IDLE and e[:2] != [edit, user_id]]
        began = len(edits) == len([e for e in scene.get("edits", []) if now - e[2] <= EDIT_IDLE])
        work["edits"] = [*edits, [edit, user_id, now]][-EDITS_KEPT:]
        if began:
            work["previous"] = {k: scene[k] for k in CONTENT}
        work.update(version=scene["version"] + 1, changed_by=user_id, changed_at=dt_util.utcnow().isoformat())
        self.scenes[scene["id"]] = work
        return began

    def _changed(self) -> None:
        self._sync_schedules()
        self.async_save_later()
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)

    @staticmethod
    def _find(work: dict[str, Any], step_id: str) -> dict[str, Any]:
        step = next((s for s in work["sequence"] if s["id"] == step_id), None)
        if step is None:
            raise ValidationError("step_missing")  # removed by another editor: the card reloads
        return step

    def _step(self, work: dict[str, Any], step_id: str, kind: str) -> dict[str, Any]:
        step = self._find(work, step_id)
        if step["type"] != kind:
            raise ValidationError("invalid_step")
        return step

    async def _async_check_update(self, scene: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> None:
        if not is_admin and ("kind" in msg or "content_released" in msg):
            raise ValidationError("unauthorized")
        name, image = msg.get("name", scene["name"]).strip(), msg.get("image", scene["image"])
        # residents change only the content of a released installer scene (spec 2)
        if not is_admin and scene["kind"] == KIND_INSTALLER and (name, image) != (scene["name"], scene["image"]):
            raise ValidationError("protected")
        if image is not None and image != scene["image"] and not await self._async_image_exists(image):
            raise ValidationError("invalid_image")

    def _update(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> None:
        if "name" in msg:
            work["name"] = self._check_name(msg["name"], work["area_id"], work["id"])
        if "image" in msg:
            work["image"] = msg["image"]
        if "transition" in msg:
            if msg["transition"] is not None and not 0 <= msg["transition"] <= MAX_TRANSITION:
                raise ValidationError("invalid_value", "transition")
            work["transition"] = msg["transition"]
        if is_admin:
            work["kind"] = msg.get("kind", work["kind"])
            work["content_released"] = msg.get("content_released", work["content_released"])
        work["content_released"] = bool(work["content_released"]) and work["kind"] == KIND_INSTALLER

    def _rename_entity(self, scene: dict[str, Any], domain: str) -> None:
        """In the edit that created a scene or schedule its entity id follows the name, unless changed by hand.

        Spec 4.3 and 4.15.
        """
        if scene["entity_named"]:
            return
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id(domain, DOMAIN, scene["id"])
        if entity_id is None or entity_id != scene.get("auto_entity_id"):
            return
        if entity_id != (new_id := f"{domain}.{slugify(scene['name'])}"):
            # its own id is not taken: "Abend!" keeps scene.abend_2 (review Y6)
            new_id = registry.async_get_available_entity_id(
                domain, slugify(scene["name"]), current_entity_id=entity_id
            )
            if new_id != entity_id:
                registry.async_update_entity(entity_id, new_entity_id=new_id)
                scene["auto_entity_id"] = new_id

    def _add_step(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool = False) -> dict[str, Any]:
        sequence = work["sequence"]
        kind = msg.get("step_type")
        step: dict[str, Any] = {"id": new_step_id(sequence), "type": kind}
        if kind == "group":
            area_id = work["area_id"] or msg.get("area_id")  # in a room scene always the room
            if msg.get("domain") not in ALLOWED_DOMAINS:
                raise ValidationError("invalid_step")
            if area_id is not None and ar.async_get(self.hass).async_get_area(area_id) is None:  # None: no room (W2)
                raise ValidationError("invalid_area")
            step |= {"domain": msg["domain"], "area_id": area_id, "entries": []}
        elif kind == "scene":
            target = self.scenes.get(msg.get("target") or "")
            # only house scenes call room scenes, each once: no cycles possible
            if (
                work["area_id"]
                or target is None
                or not target["area_id"]
                or msg.get("area_id", target["area_id"]) != target["area_id"]
                or any(s.get("scene_id") == target["id"] for s in sequence)
            ):
                raise ValidationError("invalid_scene_call", target["name"] if target else "")
            step |= {"scene_id": target["id"], "name": target["name"], "area_id": target["area_id"]}
        elif kind == "delay":
            step["seconds"] = min(5, int(opt(self.entry, CONF_MAX_DELAY)))
        else:
            raise ValidationError("invalid_step")
        sequence.insert(max(0, min(msg.get("index", len(sequence)), len(sequence))), step)
        return {"step_id": step["id"]}

    def _set_delay(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool = False) -> None:
        step = self._step(work, msg["step_id"], "delay")
        seconds = msg["seconds"]
        if seconds != int(seconds) or not 0 < seconds <= int(opt(self.entry, CONF_MAX_DELAY)):
            raise ValidationError("invalid_delay")  # whole seconds, like plus and minus (V16)
        step["seconds"] = int(seconds)

    def _remove_step(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> None:
        work["sequence"].remove(self._find(work, msg["step_id"]))

    def _move_step(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> None:
        sequence = work["sequence"]
        step = self._find(work, msg["step_id"])
        sequence.remove(step)
        sequence.insert(max(0, min(msg["index"], len(sequence))), step)

    @staticmethod
    def _put(step: dict[str, Any], entry: dict[str, Any]) -> None:
        """Add the entry to a group step or replace the entry of the same entity."""
        for index, old in enumerate(step["entries"]):
            if old["entity_id"] == entry["entity_id"]:
                step["entries"][index] = entry
                return
        step["entries"].append(entry)

    def _set_entry(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool = False) -> dict[str, Any]:
        step = self._step(work, msg["step_id"], "group")
        if msg["entity_id"].split(".", 1)[0] != step["domain"]:
            raise ValidationError("entity_not_allowed", msg["entity_id"])
        stored = next((e for e in step["entries"] if e["entity_id"] == msg["entity_id"]), None)
        entry = build_step(
            self.hass, msg, allowed_entities(self.hass, self.entry), music_favorites(self.hass), step["area_id"], stored
        )
        self._put(step, entry)
        return {"live": [entry]} if msg.get("live") and step["domain"] in LIVE_DOMAINS else {}

    def _remove_entry(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> None:
        step = self._step(work, msg["step_id"], "group")
        step["entries"] = [e for e in step["entries"] if e["entity_id"] != msg["entity_id"]]

    def _fill(self, step: dict[str, Any], mode: str) -> list[dict[str, Any]]:
        """Set every released device of the step's domain and area to its current state or off.

        Unreachable devices and flagged entries keep their stored entry (spec 4.5).
        """
        allowed = allowed_entities(self.hass, self.entry)
        favorites = music_favorites(self.hass)
        stored = {e["entity_id"]: e for e in step["entries"]}
        changed = []
        for entity_id, ent in allowed.items():
            if ent.domain != step["domain"] or entity_area(self.hass, ent) != step["area_id"]:
                continue
            if entity_id in stored and step_issue(self.hass, step["area_id"], stored[entity_id], allowed, favorites):
                continue
            try:
                raw = {"entity_id": entity_id, "mode": mode}
                entry = build_step(self.hass, raw, allowed, favorites, step["area_id"])
            except ValidationError as err:
                if err.code != "entity_unavailable":
                    raise
                continue
            self._put(step, entry)
            changed.append(entry)
        return changed

    def _set_all(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> dict[str, Any]:
        step = self._step(work, msg["step_id"], "group")
        changed = self._fill(step, msg["mode"])
        live = msg.get("live") and msg["mode"] == "off" and step["domain"] in LIVE_DOMAINS
        return {"live": changed} if live else {}

    def _house_off(self, work: dict[str, Any], msg: dict[str, Any], is_admin: bool) -> None:
        """Every room with released devices of the domain, and "no room" (X1): its first step of that domain all off."""
        if work["area_id"]:
            raise ValidationError("invalid_step")
        domain, sequence = msg["domain"], work["sequence"]
        areas: dict[str | None, None] = {}  # in order of the device list
        for ent in allowed_entities(self.hass, self.entry).values():
            if ent.domain == domain:
                areas.setdefault(entity_area(self.hass, ent))
        for area_id in areas:
            step = next(
                (s for s in sequence if s["type"] == "group" and (s["domain"], s["area_id"]) == (domain, area_id)),
                None,
            )
            if step is None:
                step = {"id": new_step_id(sequence), "type": "group", "domain": domain, "area_id": area_id,
                        "entries": []}
                sequence.append(step)
            self._fill(step, "off")

    async def async_undo(self, scene_id: str, version: int, user_id: str | None, is_admin: bool) -> dict[str, Any]:
        """Bring back the state before the latest edit (including its image)."""
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
            previous = {k: v for k, v in previous.items() if k in ("sequence", "transition")}
            previous |= {k: scene[k] for k in ("name", "area_id", "image")}
        areas = ar.async_get(self.hass)
        if previous["area_id"] and areas.async_get_area(previous["area_id"]) is None:
            previous["area_id"] = None
        if "sequence" in previous:
            previous["sequence"] = deepcopy(previous["sequence"])
            for step in previous["sequence"]:  # rooms deleted since: steps without a room (W1)
                if step["type"] == "group" and step["area_id"] and areas.async_get_area(step["area_id"]) is None:
                    step["area_id"] = None
        if previous["area_id"] != scene["area_id"]:
            self._clear_favorites(scene_id)
        previous["name"] = self._free_name(previous["name"], previous["area_id"], scene_id)
        scene.update(previous)
        scene.update(
            version=scene["version"] + 1, previous=None, changed_by=user_id, changed_at=dt_util.utcnow().isoformat(),
            edits=[],  # an editor still open begins a new edit with its next input (X9)
        )
        self._follow_moves()  # the state taken back follows devices moved since (spec 4.5, review AE1)
        await self._async_commit()
        return scene

    async def async_capture(self, scene_id: str, user_id: str | None) -> dict[str, Any]:
        """Take over the current state into a scene (action resident_scenes.capture); one edit.

        The first entry of each entity is recaptured; missing, unreachable, moved or no longer
        released devices keep their stored value (spec 4.5); scene steps, delays and order stay.
        """
        scene = self.scenes[scene_id]
        work = deepcopy(scene)
        allowed = allowed_entities(self.hass, self.entry)
        favorites = music_favorites(self.hass)
        seen: set[str] = set()
        for step in work["sequence"]:
            for index, entry in enumerate(step.get("entries", [])):
                if entry["entity_id"] in seen:
                    continue
                seen.add(entry["entity_id"])
                raw = {"entity_id": entry["entity_id"], "mode": "capture"}
                try:
                    step["entries"][index] = build_step(self.hass, raw, allowed, favorites, step["area_id"])
                except ValidationError:
                    continue
        self._apply(scene, work, uuid4().hex, user_id)
        self._changed()
        return work

    async def async_delete_scene(self, scene_id: str, is_admin: bool = False) -> dict[str, Any]:
        """Delete a scene and empty its favorite slots; callers keep a 'scene missing' step."""
        scene = self.scenes.get(scene_id)
        if scene is None:
            raise ValidationError("not_found")
        if scene["kind"] == KIND_INSTALLER and not is_admin:
            raise ValidationError("protected")
        self._sync_schedules()  # its schedules keep the room they have now (spec 4.15)
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
            # the template key gives a stable id, so a later template replaces this scene
            scene_id = f"tpl_{item['key']}"
            existing = self.scenes.get(scene_id)
            area_id = item.get("area_id")
            work = self._new_scene(scene_id, area_id, None)
            image, transition = item.get("image"), item.get("transition")
            changed = image is not None and image != (existing or {}).get("image")
            if changed and not await self._async_image_exists(image):
                raise ValidationError("invalid_image")
            if transition is not None and not 0 <= transition <= MAX_TRANSITION:
                raise ValidationError("invalid_value", "transition")
            work |= {
                "name": self._check_name(item["name"], area_id, scene_id),
                "image": image,
                "kind": KIND_INSTALLER,
                "content_released": bool(item.get("content_released", False)),
                "transition": transition,
                "entity_named": True,
                "previous": {k: existing[k] for k in CONTENT} if existing else None,
            }
            # steps of a 0.2.x template are converted; both go through the builders of the editor
            sequence = item.get("sequence") or group_steps(self.hass, area_id, item.get("steps", []), self.scenes)
            for step in sequence:
                msg = {k: step[k] for k in ("domain", "area_id") if k in step}
                step_id = self._add_step(work, {**msg, "step_type": step.get("type"), "target": step.get("scene_id")})
                if step["type"] == "delay":
                    self._set_delay(work, {"step_id": step_id["step_id"], "seconds": step["seconds"]})
                for raw in step.get("entries", []):
                    self._set_entry(work, {**raw, "step_id": step_id["step_id"]})
            self._check_size([], work["sequence"])
            if existing and existing["area_id"] != area_id:
                self._clear_favorites(scene_id)
            self.scenes[scene_id] = work
            count += 1
        return count

    # ---------- schedules (spec 4.15) ----------

    def schedule(self, schedule_id: str) -> dict[str, Any]:
        """Return a schedule; an unknown id is refused."""
        if (found := next((s for s in self.schedules if s["id"] == schedule_id), None)) is None:
            raise ValidationError("not_found")
        return found

    def scene_ref(self, scene_id: str | None, entity_id: str | None) -> dict[str, Any]:
        """Return how a schedule refers to a scene, with the scene's room and name.

        A scene of the integration by its fixed id, a released scene of another integration by its entry in
        the registry, so renaming and a new entity id are followed (spec 4.15).
        """
        if scene_id:
            if scene_id not in self.scenes:
                raise ValidationError("scene_not_allowed")
            ref: dict[str, Any] = {"scene_id": scene_id, "registry_id": None}
        else:
            ent = er.async_get(self.hass).async_get(entity_id or "")
            if ent is None or ent.domain != "scene" or ent.entity_id not in allowed_entities(self.hass, self.entry):
                raise ValidationError("scene_not_allowed")
            ref = {"scene_id": None, "registry_id": ent.id}
        scene = target(self.hass, self, {**ref, "area_id": None, "scene_name": ""})
        return {**ref, "area_id": scene["area_id"], "scene_name": scene["name"]}

    async def async_create_schedule(
        self, ref: dict[str, Any], name: str, edit: str, user_id: str | None
    ) -> dict[str, Any]:
        """Create '<name> N': off, at the time of this moment, every day, at the end of the list (spec 4.15)."""
        limit = int(opt(self.entry, CONF_SCHEDULES))
        if len(self.schedules) >= limit:
            raise ValidationError("schedule_limit", str(limit))
        base, length = name.strip(), int(opt(self.entry, CONF_NAME_LENGTH))
        if not base:
            raise ValidationError("invalid_name")
        taken = {s["name"].casefold() for s in self.schedules}
        n = 1
        while (candidate := f"{base[: length - len(str(n)) - 1]} {n}").casefold() in taken:
            n += 1
        now = dt_util.now()
        schedule = {
            "id": uuid4().hex,
            "name": candidate,
            "active": False,  # a half-set schedule runs nothing; "Done" in the card switches it on
            "trigger": "time",
            "time": f"{now.hour:02}:{now.minute:02}",
            "offset": 0,
            "weekdays": list(range(7)),
            **ref,
            "version": 1,
            "changed_by": user_id,
            "changed_at": now.isoformat(),
            "entity_named": False,
            "edits": [[edit, user_id, now.timestamp()]],
            "creating_edit": [edit, user_id],
        }
        self.schedules.append(schedule)
        await self._async_commit()
        return schedule

    async def async_update_schedule(
        self, schedule_id: str, field: str, value: Any, edit: str, user_id: str | None
    ) -> tuple[dict[str, Any], bool]:
        """Change one field of a schedule at once; return it and whether the input began an edit.

        Switching on and off is no edit, it goes to the logbook on its own (spec 4.15). Time and offset are
        kept both, so a change of the trigger finds the other again.
        """
        schedule = self.schedule(schedule_id)
        if field == "name":
            value = value.strip()
            if not value or len(value) > int(opt(self.entry, CONF_NAME_LENGTH)):
                raise ValidationError("invalid_name")
        elif field == "offset" and not -MAX_OFFSET <= value <= MAX_OFFSET:
            raise ValidationError("invalid_value", "offset")
        elif field == "weekdays" and not (value := sorted(set(value))):
            raise ValidationError("no_weekday")  # the last day cannot be taken away
        updates = value if field == "scene" else {field: value}
        if all(schedule.get(k) == v for k, v in updates.items()):
            return schedule, False  # changes nothing: no edit, no logbook entry
        began = False
        if field != "active":
            now = dt_util.utcnow().timestamp()
            alive = [e for e in schedule["edits"] if now - e[2] <= EDIT_IDLE]
            others = [e for e in alive if e[:2] != [edit, user_id]]
            began = len(others) == len(alive)
            creating = schedule["creating_edit"]
            # the entity id follows the name until the edit that created the schedule is over, as for scenes
            ended = creating not in [e[:2] for e in others] or user_id == creating[1]
            if began if [edit, user_id] == creating else ended:
                schedule["entity_named"] = True
            schedule["edits"] = [*others, [edit, user_id, now]][-EDITS_KEPT:]
        schedule.update(updates)
        schedule.update(version=schedule["version"] + 1, changed_by=user_id, changed_at=dt_util.utcnow().isoformat())
        if field == "name":
            self._rename_entity(schedule, "switch")
        self._changed()
        return schedule, began

    async def async_delete_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Delete a schedule; its switch entity goes with it."""
        schedule = self.schedule(schedule_id)
        self.schedules.remove(schedule)
        await self._async_commit()
        return schedule

    def move_schedule(self, schedule_id: str, index: int, visible: set[str]) -> None:
        """Move a schedule among those an account sees; the others keep their places (spec 4.15)."""
        places = [i for i, s in enumerate(self.schedules) if s["id"] in visible]
        order = [self.schedules[i] for i in places]
        moving = self.schedule(schedule_id)
        if moving not in order:
            raise ValidationError("not_found")
        order.remove(moving)
        order.insert(max(0, min(index, len(order))), moving)
        for place, schedule in zip(places, order, strict=True):
            self.schedules[place] = schedule
        self._changed()

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

    def _data(self) -> dict[str, Any]:
        return {"scenes": self.scenes, "favorites": self.favorites, "schedules": self.schedules}

    @callback
    def async_save_later(self) -> None:
        """Write within SAVE_DELAY seconds of the first unwritten input (or on stop).

        Home Assistant moves a delayed save with every call; the delay counts from the first one (review W6).
        """
        now = self.hass.loop.time()
        if self._save_since is None:
            self._save_since = now
        self._store.async_delay_save(self._written, max(0, SAVE_DELAY - (now - self._save_since)))

    def _written(self) -> dict[str, Any]:
        self._save_since = None
        return self._data()

    async def async_write(self) -> None:
        """Write now, also what waits for the delayed save (on unload)."""
        await self._store.async_save(self._written())

    async def _async_commit(self) -> None:
        self._sync_schedules()
        await self.async_write()
        await self._async_clean_uploads()
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)

