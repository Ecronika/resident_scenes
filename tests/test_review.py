"""Regression tests for the findings of the stage 1 review (B1, B2, E2, E3, K1 to K4)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_SKIPPED
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar, entity_registry as er
from tests.conftest import eid, flat, make, run_scene, save, ws as _ws

LIST = f"{DOMAIN}/list"


async def _image_url(call, name):
    """Return the signed address of one library image, None if not listed."""
    images = (await call(type=f"{DOMAIN}/devices"))["result"]["images"]
    return next((i["url"] for i in images if i["name"] == name), None)


async def _scene(hass, call, **msg):
    """Build a scene and return (scene_id, entity_id)."""
    scene_id = await save(call, **msg)
    await hass.async_block_till_done()
    return scene_id, eid(hass, scene_id)


async def _settings(hass, entry):
    """Open the settings page of the options."""
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "settings"})


@pytest.fixture(autouse=True)
async def library(hass):
    """Two library images; removed again, the config folder is shared between tests."""
    folder = Path(hass.config.path("resident_scenes"))
    names = ("sofa.png", "a#b.png")

    def make() -> None:
        folder.mkdir(exist_ok=True)
        for name in names:
            (folder / name).write_bytes(b"x")

    def clean() -> None:
        for name in names:
            (folder / name).unlink(missing_ok=True)

    await hass.async_add_executor_job(make)
    yield
    await hass.async_add_executor_job(clean)


async def test_b1_deleted_area_moves_scenes_to_house(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    await _scene(hass, call, name="Cook")  # house scene with the same name
    scene_id, entity_id = await _scene(hass, call, name="Cook", area_id="kitchen")
    assert (await call(type=f"{DOMAIN}/set_favorite", scope="kitchen", slot=0, scene_id=scene_id))["success"]

    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    scene = setup.runtime_data.scenes[scene_id]
    assert scene["area_id"] is None
    assert scene["name"] == "Cook (2)"
    assert "kitchen" not in setup.runtime_data.favorites

    await _scene(hass, call, name="Other")  # any change runs sync()
    assert er.async_get(hass).async_get(entity_id).area_id is None
    res = await call(type=f"{DOMAIN}/update", scene_id=scene_id, edit="x", name="Cook 2")
    assert res["success"]


async def test_b1_area_deleted_while_stopped(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    scene_id, _ = await _scene(hass, call, name="Cook", area_id="kitchen")
    await hass.config_entries.async_unload(setup.entry_id)
    ar.async_get(hass).async_delete("kitchen")
    assert await hass.config_entries.async_setup(setup.entry_id)
    await hass.async_block_till_done()
    assert setup.runtime_data.scenes[scene_id]["area_id"] is None


async def test_b2_unreleased_or_renamed_device(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    steps = [{"entity_id": "light.kitchen", "mode": "capture"}, {"entity_id": "cover.kitchen", "mode": "off"}]
    scene_id, entity_id = await _scene(hass, call, name="Evening", area_id="kitchen", steps=steps)
    ent_reg = er.async_get(hass)

    # a) the installer removes the label from the light: skipped, scene stays editable
    ent_reg.async_update_entity("light.kitchen", labels=set())
    hass.states.async_set("light.kitchen", "off")
    turn_on = async_mock_service(hass, "light", "turn_on")
    async_mock_service(hass, "cover", "close_cover")
    skipped = []
    hass.bus.async_listen(EVENT_SKIPPED, skipped.append)
    await run_scene(hass, entity_id)
    assert turn_on == []
    assert skipped[0].data["entities"] == ["light.kitchen"]
    res = await call(type=f"{DOMAIN}/update", scene_id=scene_id, edit="x", name="Dinner")
    assert res["success"]  # other inputs keep the stored entry
    light_step = setup.runtime_data.scenes[scene_id]["sequence"][0]
    detail = (await call(type=f"{DOMAIN}/scene", scene_id=scene_id))["result"]
    assert detail["sequence"][0]["entries"][0]["issue"] == "not_released"
    res = await call(type=f"{DOMAIN}/set_entry", scene_id=scene_id, edit="x", step_id=light_step["id"],
                     entity_id="light.kitchen", mode="off")
    assert res["error"]["code"] == "entity_not_allowed"
    assert res["error"]["message"] == "entity_not_allowed: light.kitchen"  # the card names the device
    ent_reg.async_update_entity("light.kitchen", labels={"resident_scenes"})

    # b) the installer renames an entity id: the steps follow
    ent_reg.async_update_entity("cover.kitchen", new_entity_id="cover.kueche")
    await hass.async_block_till_done()
    stored = [s["entity_id"] for s in flat(setup.runtime_data.scenes[scene_id])]
    assert stored == ["light.kitchen", "cover.kueche"]
    cover_step = setup.runtime_data.scenes[scene_id]["sequence"][1]["id"]
    res = await call(type=f"{DOMAIN}/set_entry", scene_id=scene_id, edit="x", step_id=cover_step,
                     entity_id="cover.kueche", mode="off")
    assert res["success"], res


async def test_e2_failed_step_goes_to_the_logbook(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    _, entity_id = await _scene(
        hass, call, name="Evening", area_id="kitchen", steps=[{"entity_id": "light.kitchen", "mode": "off"}]
    )

    async def broken(_call):
        raise HomeAssistantError("bus down")

    hass.services.async_register("light", "turn_off", broken)
    skipped = []
    hass.bus.async_listen(EVENT_SKIPPED, skipped.append)
    await run_scene(hass, entity_id)
    assert skipped[0].data["failed"] == ["light.kitchen"]


async def test_e3_signed_urls_are_reused(hass, setup, hass_ws_client, resident_token, freezer):
    call = await _ws(hass, hass_ws_client, resident_token)
    first = await _image_url(call, "sofa.png")
    freezer.tick(2)
    assert first == await _image_url(call, "sofa.png")  # browser cache hits
    freezer.tick(timedelta(hours=13))
    assert first != await _image_url(call, "sofa.png")  # renewed after half the lifetime


async def test_k1_read_only_account_may_not_edit(
    hass, setup, hass_ws_client, hass_read_only_access_token
):
    read_only = await _ws(hass, hass_ws_client, hass_read_only_access_token)
    assert (await read_only(type=LIST, scope="_house"))["result"]["can_edit"] is False
    assert (await make(read_only, name="X"))["error"]["code"] == "unauthorized"


async def test_k1_resident_runs_with_own_account(hass, setup, hass_ws_client, resident_token, hass_read_only_user):
    resident = await _ws(hass, hass_ws_client, resident_token)
    _, entity_id = await _scene(
        hass, resident, name="Evening", area_id="kitchen", steps=[{"entity_id": "light.kitchen", "mode": "capture"}]
    )
    hass.states.async_set("light.kitchen", "off")
    turn_on = async_mock_service(hass, "light", "turn_on")
    run = {"type": "call_service", "domain": "scene", "service": "turn_on", "service_data": {"entity_id": entity_id}}
    assert (await resident(**run))["success"]
    await hass.async_block_till_done(wait_background_tasks=True)
    assert turn_on[0].context.user_id == hass_read_only_user.id


async def test_k2_removed_account_does_not_block_the_options(hass, setup):
    hass.config_entries.async_update_entry(setup, options={"users_without_edit": ["id-of-a-removed-account"]})
    await hass.async_block_till_done()
    flow = await _settings(hass, setup)
    suggested = {
        str(key): key.description["suggested_value"]
        for key in flow["data_schema"].schema
        if key.description and "suggested_value" in key.description
    }
    assert suggested["users_without_edit"] == []


async def test_k3_image_dir_and_file_names(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    assert await _image_url(call, "sofa.png")
    assert await _image_url(call, "a#b.png") is None  # '#' would break the signed address

    flow = await _settings(hass, setup)
    form = {
        "label": "resident_scenes",
        "scenes_per_area": 20,
        "house_scenes": 30,
        "steps_per_scene": 150,
        "name_length": 30,
        "max_delay": 600,
        "image_side": 1600,
        "image_kb": 500,
        "image_count": 200,
        "favorite_slots": 4,
        "image_dir": "/etc",
    }
    result = await hass.config_entries.options.async_configure(flow["flow_id"], form)
    assert result["errors"] == {"image_dir": "outside_config"}


async def test_k4_area_scene_rejects_devices_of_other_areas(hass, setup, hass_ws_client, resident_token):
    call = await _ws(hass, hass_ws_client, resident_token)
    hall = [{"entity_id": "light.hall", "mode": "capture"}]
    res = await make(call, name="Evening", area_id="kitchen", steps=hall)
    assert res["error"]["code"] == "entity_not_allowed"


async def test_k9_label_is_created(hass, setup):
    from homeassistant.helpers import label_registry as lr  # noqa: PLC0415

    lr.async_get(hass).async_delete("resident_scenes")
    await hass.config_entries.async_reload(setup.entry_id)
    await hass.async_block_till_done()
    assert lr.async_get(hass).async_get_label("resident_scenes") is not None
