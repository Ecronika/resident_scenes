"""Fixtures for Resident Scenes tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.resident_scenes.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, label_registry as lr
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the custom integration."""


@pytest.fixture
async def setup(hass: HomeAssistant) -> MockConfigEntry:
    """Kitchen with a released light, cover and Sonos player; set up the integration."""
    assert await async_setup_component(hass, "http", {})
    kitchen = ar.async_get(hass).async_create("Kitchen")
    lr.async_get(hass).async_create("resident_scenes")
    ent_reg = er.async_get(hass)
    for domain, uid, area in (
        ("light", "kitchen", kitchen.id),
        ("cover", "kitchen", kitchen.id),
        ("media_player", "kitchen", kitchen.id),
        ("light", "hall", None),
        ("lock", "door", kitchen.id),
    ):
        entry = ent_reg.async_get_or_create(domain, "test", uid, suggested_object_id=uid)
        ent_reg.async_update_entity(entry.entity_id, area_id=area, labels={"resident_scenes"})
    ent_reg.async_get_or_create("light", "test", "unreleased", suggested_object_id="unreleased")
    fav = ent_reg.async_get_or_create("sensor", "sonos", "favorites", suggested_object_id="sonos_favorites")
    hass.states.async_set(fav.entity_id, "2", {"items": {"FV:2/1": "Sport", "FV:2/2": "News"}})
    hass.states.async_set("light.kitchen", "on", {"brightness": 128, "color_mode": "brightness"})
    hass.states.async_set("light.hall", "on", {"brightness": 255, "color_mode": "brightness"})
    hass.states.async_set("cover.kitchen", "open", {"current_position": 70})
    hass.states.async_set("media_player.kitchen", "playing", {"volume_level": 0.4, "media_title": "Sport"})
    hass.states.async_set("lock.door", "locked")

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
