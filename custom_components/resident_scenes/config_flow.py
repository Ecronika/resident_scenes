"""Config and options flow for Resident Scenes."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    LabelSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

from .const import (
    CONF_FAVORITE_SLOTS,
    CONF_HOUSE_SCENES,
    CONF_IMAGE_DIR,
    CONF_LABEL,
    CONF_NAME_LENGTH,
    CONF_PANEL_USERS,
    CONF_PANELS_WITH_EDIT,
    CONF_SCENES_PER_AREA,
    CONF_STEPS_PER_SCENE,
    CONF_USERS_WITHOUT_EDIT,
    DEFAULTS,
    DOMAIN,
)
from .store import inside_config

LIMITS = {
    CONF_SCENES_PER_AREA: 200,
    CONF_HOUSE_SCENES: 200,
    CONF_STEPS_PER_SCENE: 500,
    CONF_NAME_LENGTH: 100,
    CONF_FAVORITE_SLOTS: 12,
}


RIGHTS = (CONF_USERS_WITHOUT_EDIT, CONF_PANEL_USERS, CONF_PANELS_WITH_EDIT)


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
    """Rights, device release and limits.

    Rights are stored as deviations from the defaults, so new accounts may edit
    without anyone opening these options.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show all options on one page."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not inside_config(self.hass, user_input[CONF_IMAGE_DIR]):
                errors[CONF_IMAGE_DIR] = "outside_config"
            else:
                return self.async_create_entry(
                    data={k: int(v) if k in LIMITS else v for k, v in user_input.items()}
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
            for k, v in self.config_entry.options.items()
        }
        schema: dict[Any, Any] = {
            vol.Required(CONF_LABEL): LabelSelector(),
            vol.Optional(CONF_USERS_WITHOUT_EDIT): user_select,
            vol.Optional(CONF_PANEL_USERS): user_select,
            vol.Optional(CONF_PANELS_WITH_EDIT): user_select,
        }
        for key, maximum in LIMITS.items():
            schema[vol.Required(key)] = NumberSelector(
                NumberSelectorConfig(min=1, max=maximum, step=1, mode=NumberSelectorMode.BOX)
            )
        schema[vol.Required(CONF_IMAGE_DIR)] = TextSelector()
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), {**DEFAULTS, **current}
            ),
        )
