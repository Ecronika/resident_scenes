"""Fixtures for Resident Scenes tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.resident_scenes.const import DOMAIN
from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, label_registry as lr
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the custom integration."""


@pytest.fixture
async def setup(hass: HomeAssistant) -> MockConfigEntry:
    """Kitchen with a released light, cover, media player and Sonos player; set up the integration."""
    assert await async_setup_component(hass, "http", {})
    kitchen = ar.async_get(hass).async_create("Kitchen")
    lr.async_get(hass).async_create("resident_scenes")
    ent_reg = er.async_get(hass)
    for domain, platform, uid, area in (
        ("light", "test", "kitchen", kitchen.id),
        ("cover", "test", "kitchen", kitchen.id),
        ("media_player", "test", "kitchen", kitchen.id),
        ("media_player", "sonos", "sonos_kitchen", kitchen.id),
        ("climate", "test", "kitchen", kitchen.id),
        ("light", "test", "hall", None),
        ("lock", "test", "door", kitchen.id),
    ):
        entry = ent_reg.async_get_or_create(domain, platform, uid, suggested_object_id=uid)
        ent_reg.async_update_entity(entry.entity_id, area_id=area, labels={"resident_scenes"})
    ent_reg.async_get_or_create("light", "test", "unreleased", suggested_object_id="unreleased")
    fav = ent_reg.async_get_or_create("sensor", "sonos", "favorites", suggested_object_id="sonos_favorites")
    hass.states.async_set(fav.entity_id, "2", {"items": {"FV:2/1": "Sport", "FV:2/2": "News"}})
    hass.states.async_set(
        "light.kitchen",
        "on",
        {"brightness": 128, "color_mode": "brightness", "supported_color_modes": ["color_temp", "hs"],
         "min_color_temp_kelvin": 2000, "max_color_temp_kelvin": 6500},
    )
    hass.states.async_set("light.hall", "on", {"brightness": 255, "color_mode": "brightness"})
    hass.states.async_set("cover.kitchen", "open", {"current_position": 70, "supported_features": 135})
    hass.states.async_set("media_player.kitchen", "playing", {"volume_level": 0.4, "media_title": "Sport"})
    hass.states.async_set("media_player.sonos_kitchen", "playing", {"volume_level": 0.5, "media_title": "Sport"})
    hass.states.async_set(
        "climate.kitchen", "heat", {"hvac_modes": ["off", "heat"], "temperature": 21, "min_temp": 7, "max_temp": 30}
    )
    hass.states.async_set("lock.door", "locked")

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def resident_token(hass: HomeAssistant, hass_read_only_user: User, hass_read_only_access_token: str) -> str:
    """Token of an ordinary resident account (group system-users, no admin)."""
    hass_read_only_user.groups = [await hass.auth.async_get_group(GROUP_ID_USER)]
    hass_read_only_user.invalidate_cache()
    return hass_read_only_access_token


async def run_scene(hass: HomeAssistant, entity_id: str) -> None:
    """Run a scene and wait for the script helper to finish all batches without delay."""
    await hass.services.async_call("scene", "turn_on", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
