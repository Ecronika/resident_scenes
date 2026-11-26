"""Config and options flow for Resident Scenes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.selector import (
    AreaSelector,
    BooleanSelector,
    LabelSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)
from homeassistant.util.yaml import load_yaml_dict

from .const import (
    ALL_OFF_PARTS,
    CONF_ALL_OFF,
    CONF_FAVORITE_SLOTS,
    CONF_HOUSE_FAVORITE_SLOTS,
    CONF_HOUSE_SCENES,
    CONF_IMAGE_COUNT,
    CONF_IMAGE_DIR,
    CONF_IMAGE_KB,
    CONF_IMAGE_SIDE,
    CONF_LABEL,
    CONF_MAIN_USERS,
    CONF_MAX_DELAY,
    CONF_NAME_LENGTH,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_ROOMS,
    CONF_SCENES_PER_AREA,
    CONF_SCHEDULES,
    CONF_STEPS_PER_SCENE,
    CONF_USERS_WITHOUT_EDIT,
    CONF_USERS_WITHOUT_HOUSE,
    DEFAULTS,
    DOMAIN,
)
from .model import ValidationError
from .store import inside_config

LIMITS = {
    CONF_SCENES_PER_AREA: 200,
    CONF_HOUSE_SCENES: 200,
    CONF_STEPS_PER_SCENE: 500,
    CONF_MAX_DELAY: 3600,
    CONF_NAME_LENGTH: 100,
    CONF_FAVORITE_SLOTS: 12,
    CONF_SCHEDULES: 200,
    CONF_IMAGE_SIDE: 4000,
    CONF_IMAGE_KB: 5000,
    CONF_IMAGE_COUNT: 2000,
}
HOUSE_SLOTS_MAX = 12  # like the count per room; optional, so not in LIMITS (spec 4.1)
RIGHTS = (CONF_MAIN_USERS, CONF_USERS_WITHOUT_EDIT, CONF_PANEL_USERS, CONF_PANELS_WITH_EDIT)
CONF_TEMPLATE = "template"


class ResidentScenesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add Resident Scenes once per installation."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm the setup."""
        if user_input is not None:
            return self.async_create_entry(title="Resident Scenes", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return ResidentScenesOptionsFlow()


class ResidentScenesOptionsFlow(OptionsFlow):
    """Rights, device release, limits and the template of the installer.

    Rights are stored as deviations from the defaults, so new accounts may edit
    without anyone opening these options.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose between settings and loading a template."""
        return self.async_show_menu(step_id="init", menu_options=["settings", "all_off", "template"])

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show all options on one page."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not inside_config(self.hass, user_input[CONF_IMAGE_DIR]):
                errors[CONF_IMAGE_DIR] = "outside_config"
            else:
                # room rights are managed in the card and not part of this form (spec 3)
                options = self.config_entry.options
                # nor is "all off" per room, which has its own step
                kept = {k: options[k] for k in (CONF_ROOMS, CONF_USERS_WITHOUT_HOUSE, CONF_ALL_OFF) if k in options}
                numbers = (*LIMITS, CONF_HOUSE_FAVORITE_SLOTS)
                return self.async_create_entry(
                    data=kept | {k: int(v) if k in numbers else v for k, v in user_input.items()}
                )
        users = [
            SelectOptionDict(value=u.id, label=u.name or u.id)
            for u in await self.hass.auth.async_get_users()
            if not u.system_generated and u.is_active and not u.is_admin
        ]
        user_select = SelectSelector(SelectSelectorConfig(options=users, multiple=True))
        # removed or promoted accounts would make the form unsavable
        known = {u["value"] for u in users}
        current = {
            k: [uid for uid in v if uid in known] if k in RIGHTS else v
            for k, v in (user_input or self.config_entry.options).items()  # on error keep what was entered
        }
        schema: dict[Any, Any] = {
            vol.Required(CONF_LABEL): LabelSelector(),
            vol.Optional(CONF_MAIN_USERS): user_select,
            vol.Optional(CONF_USERS_WITHOUT_EDIT): user_select,
            vol.Optional(CONF_PANEL_USERS): user_select,
            vol.Optional(CONF_PANELS_WITH_EDIT): user_select,
        }
        for key, maximum in LIMITS.items():
            # left empty, the schedules keep their default: an update asks nothing new (spec 4.1)
            schema[vol.Optional(key) if key == CONF_SCHEDULES else vol.Required(key)] = NumberSelector(
                NumberSelectorConfig(min=1, max=maximum, step=1, mode=NumberSelectorMode.BOX)
            )
            if key == CONF_FAVORITE_SLOTS:  # left empty: the house has as many as each room
                schema[vol.Optional(CONF_HOUSE_FAVORITE_SLOTS)] = NumberSelector(
                    NumberSelectorConfig(min=1, max=HOUSE_SLOTS_MAX, step=1, mode=NumberSelectorMode.BOX)
                )
        schema[vol.Required(CONF_IMAGE_DIR)] = TextSelector()
        return self.async_show_form(
            step_id="settings",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(vol.Schema(schema), {**DEFAULTS, **current}),
        )

    async def async_step_all_off(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose the room whose "all off" to set (spec 4.1, 4.13)."""
        if user_input is not None:
            self._area = user_input["area"]
            return await self.async_step_all_off_room()
        return self.async_show_form(step_id="all_off", data_schema=vol.Schema({vol.Required("area"): AreaSelector()}))

    async def async_step_all_off_room(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Three switches: what "all off" takes in the room beside the lights."""
        current = dict(self.config_entry.options.get(CONF_ALL_OFF, {}))
        if user_input is not None:
            parts = [p for p in ALL_OFF_PARTS if user_input.get(p)]
            current.pop(self._area, None)
            return self.async_create_entry(
                data={**self.config_entry.options, CONF_ALL_OFF: current | ({self._area: parts} if parts else {})}
            )
        area = ar.async_get(self.hass).async_get_area(self._area)
        stored = current.get(self._area, [])
        return self.async_show_form(
            step_id="all_off_room",
            data_schema=vol.Schema({vol.Required(p, default=p in stored): BooleanSelector() for p in ALL_OFF_PARTS}),
            description_placeholders={"area": area.name if area else self._area},
        )

    async def async_step_template(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Load options and installer scenes from a JSON or YAML file in the config folder."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_TEMPLATE]
            if not inside_config(self.hass, name):
                errors[CONF_TEMPLATE] = "outside_config"
            elif self.config_entry.state is not ConfigEntryState.LOADED:
                errors["base"] = "not_loaded"
            else:
                try:
                    template = await self.hass.async_add_executor_job(_read_template, self.hass.config.path(name))
                    options = {**self.config_entry.options, **template.get("options", {})}
                    if not inside_config(self.hass, str(options.get(CONF_IMAGE_DIR, DEFAULTS[CONF_IMAGE_DIR]))):
                        raise ValueError("image_dir outside the config folder")
                    areas = ar.async_get(self.hass)
                    if CONF_ROOMS in options:  # unknown room: refuse the whole template, like set_rooms
                        if any(areas.async_get_area(a) is None for r in options[CONF_ROOMS].values() for a in r):
                            raise ValueError("unknown room in rooms")
                        options[CONF_ROOMS] = {u: list(dict.fromkeys(r)) for u, r in options[CONF_ROOMS].items()}
                    if CONF_ALL_OFF in template.get("options", {}):  # replaces the stored setting as a whole
                        if any(areas.async_get_area(a) is None for a in options[CONF_ALL_OFF]):
                            raise ValueError("unknown room in all_off")
                        options[CONF_ALL_OFF] = {
                            a: [p for p in ALL_OFF_PARTS if p in parts] for a, parts in options[CONF_ALL_OFF].items()
                        }
                    count = await self.config_entry.runtime_data.async_import(template)
                except (OSError, ValueError, KeyError, TypeError, ValidationError) as err:
                    errors["base"] = "invalid_template"
                    self._error = str(err)
                else:
                    return self.async_create_entry(title=str(count), data=options)
        return self.async_show_form(
            step_id="template",
            errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_TEMPLATE): TextSelector()}),
            description_placeholders={"error": getattr(self, "_error", "")},
        )


def _read_template(path: str) -> dict[str, Any]:
    """Read a template; JSON or YAML (no secrets, no includes beyond what YAML of HA allows)."""
    if Path(path).suffix.lower() == ".json":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        data = load_yaml_dict(path)
    if not isinstance(data, dict):
        raise ValueError("template must be a mapping")
    for key, value in data.get("options", {}).items():
        # the same values the settings form allows; a wrong one would break every card
        if key in LIMITS:
            valid = type(value) is int and 1 <= value <= LIMITS[key]
        elif key == CONF_HOUSE_FAVORITE_SLOTS:
            valid = type(value) is int and 1 <= value <= HOUSE_SLOTS_MAX
        elif key == CONF_ALL_OFF:  # area id -> list of music, tv, switch (spec 4.1)
            valid = isinstance(value, dict) and all(
                isinstance(a, str) and isinstance(p, list) and all(x in ALL_OFF_PARTS for x in p)
                for a, p in value.items()
            )
        elif key == CONF_ROOMS:  # account -> list of area ids, as set_rooms stores it (spec 4.1)
            valid = isinstance(value, dict) and all(
                isinstance(u, str) and isinstance(a, list) and all(isinstance(r, str) for r in a)
                for u, a in value.items()
            )
        elif key in RIGHTS or key == CONF_USERS_WITHOUT_HOUSE:
            valid = isinstance(value, list) and all(isinstance(u, str) for u in value)
        else:
            valid = key in DEFAULTS and isinstance(value, str) and bool(value)
        if not valid:
            raise ValueError(f"invalid option {key}")
    return data
