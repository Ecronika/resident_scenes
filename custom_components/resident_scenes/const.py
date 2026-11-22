"""Constants for Resident Scenes."""

from typing import Final

DOMAIN: Final = "resident_scenes"
VERSION: Final = "0.3.2"  # keep in sync with manifest.json and the card (checked by tests)

STORAGE_KEY: Final = f"{DOMAIN}.data"
STORAGE_VERSION: Final = 3
UPLOAD_FOLDER: Final = f"{DOMAIN}_images"  # inside .storage, so part of every backup

SIGNAL_CHANGED: Final = f"{DOMAIN}_changed"
EVENT_CHANGED: Final = f"{DOMAIN}_changed"
EVENT_SKIPPED: Final = f"{DOMAIN}_skipped"
EVENT_RIGHTS: Final = f"{DOMAIN}_rights"
EVENT_BATCH: Final = f"{DOMAIN}_batch"  # fired by the script helper, runs one batch of steps

CARD_URL: Final = f"/{DOMAIN}/resident-scenes-card.js"
IMAGE_URL: Final = f"/api/{DOMAIN}/image"
PHOTO_URL: Final = f"/api/{DOMAIN}/photo"
UPLOAD_URL: Final = f"/api/{DOMAIN}/upload"
UPLOAD_PREFIX: Final = "upload:"
HOUSE: Final = "_house"

ALLOWED_DOMAINS: Final = frozenset(
    {"light", "cover", "climate", "switch", "fan", "media_player", "scene"}
)
# platforms whose media players play the music favorites (spec 4.6)
MUSIC_PLATFORMS: Final = frozenset({"sonos"})
IMAGE_SUFFIXES: Final = frozenset({".jpg", ".jpeg", ".png", ".webp"})
KIND_RESIDENT: Final = "resident"
KIND_INSTALLER: Final = "installer"
MAX_TRANSITION: Final = 60

CONF_LABEL: Final = "label"
CONF_MAIN_USERS: Final = "main_users"
CONF_PANEL_USERS: Final = "panel_users"
CONF_USERS_WITHOUT_EDIT: Final = "users_without_edit"
CONF_PANELS_WITH_EDIT: Final = "panels_with_edit"
CONF_SCENES_PER_AREA: Final = "scenes_per_area"
CONF_HOUSE_SCENES: Final = "house_scenes"
CONF_STEPS_PER_SCENE: Final = "steps_per_scene"
CONF_MAX_DELAY: Final = "max_delay"
CONF_NAME_LENGTH: Final = "name_length"
CONF_FAVORITE_SLOTS: Final = "favorite_slots"
CONF_IMAGE_DIR: Final = "image_dir"
CONF_IMAGE_SIDE: Final = "image_side"
CONF_IMAGE_KB: Final = "image_kb"
CONF_IMAGE_COUNT: Final = "image_count"

DEFAULTS: Final[dict[str, object]] = {
    CONF_LABEL: "resident_scenes",
    CONF_MAIN_USERS: [],
    CONF_PANEL_USERS: [],
    CONF_USERS_WITHOUT_EDIT: [],
    CONF_PANELS_WITH_EDIT: [],
    CONF_SCENES_PER_AREA: 20,
    CONF_HOUSE_SCENES: 30,
    CONF_STEPS_PER_SCENE: 150,
    CONF_MAX_DELAY: 600,
    CONF_NAME_LENGTH: 30,
    CONF_FAVORITE_SLOTS: 4,
    CONF_IMAGE_DIR: "resident_scenes",
    CONF_IMAGE_SIDE: 1600,
    CONF_IMAGE_KB: 500,
    CONF_IMAGE_COUNT: 200,
}
