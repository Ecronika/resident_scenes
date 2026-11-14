"""Constants for Resident Scenes."""

from typing import Final

DOMAIN: Final = "resident_scenes"
VERSION: Final = "0.1.0"  # keep in sync with manifest.json and the card (checked by tests)

STORAGE_KEY: Final = f"{DOMAIN}.data"
STORAGE_VERSION: Final = 1

SIGNAL_CHANGED: Final = f"{DOMAIN}_changed"
EVENT_CHANGED: Final = f"{DOMAIN}_changed"
EVENT_SKIPPED: Final = f"{DOMAIN}_skipped"

CARD_URL: Final = f"/{DOMAIN}/resident-scenes-card.js"
IMAGE_URL: Final = f"/api/{DOMAIN}/image"
HOUSE: Final = "_house"

ALLOWED_DOMAINS: Final = frozenset(
    {"light", "cover", "climate", "switch", "fan", "media_player", "scene"}
)
IMAGE_SUFFIXES: Final = frozenset({".jpg", ".jpeg", ".png", ".webp"})

CONF_LABEL: Final = "label"
CONF_PANEL_USERS: Final = "panel_users"
CONF_USERS_WITHOUT_EDIT: Final = "users_without_edit"
CONF_PANELS_WITH_EDIT: Final = "panels_with_edit"
CONF_SCENES_PER_AREA: Final = "scenes_per_area"
CONF_HOUSE_SCENES: Final = "house_scenes"
CONF_STEPS_PER_SCENE: Final = "steps_per_scene"
CONF_NAME_LENGTH: Final = "name_length"
CONF_FAVORITE_SLOTS: Final = "favorite_slots"
CONF_IMAGE_DIR: Final = "image_dir"

DEFAULTS: Final[dict[str, object]] = {
    CONF_LABEL: "resident_scenes",
    CONF_PANEL_USERS: [],
    CONF_USERS_WITHOUT_EDIT: [],
    CONF_PANELS_WITH_EDIT: [],
    CONF_SCENES_PER_AREA: 20,
    CONF_HOUSE_SCENES: 30,
    CONF_STEPS_PER_SCENE: 150,
    CONF_NAME_LENGTH: 30,
    CONF_FAVORITE_SLOTS: 4,
    CONF_IMAGE_DIR: "resident_scenes",
}
