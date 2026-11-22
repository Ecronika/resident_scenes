"""Review of version 0.3.2 (commit de9d64c).

Lines marked FINDING or NOTE in the review are flipped to the behaviour of 0.3.3 and marked FIXED,
OK a point that holds.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_CHANGED
from custom_components.resident_scenes.model import light_hs
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.util import color as color_util
from tests.conftest import direct, eid, flat, run_scene, save, ws

WHITE_AND_COLOUR = {
    "supported_color_modes": ["color_temp", "hs"], "min_color_temp_kelvin": 2000, "max_color_temp_kelvin": 6500,
}
COLOUR_KEYS = {"color_mode", "color_temp_kelvin", "hs_color", "rgb_color", "rgbw_color", "rgbww_color", "xy_color"}


def cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


async def light_step(call, sid: str) -> dict:
    """A step for the lights of the kitchen; returns what addresses the entry of light.kitchen."""
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light")))["result"]["step_id"]
    return {"step_id": step_id, "entity_id": "light.kitchen"}


# ---------- new with 0.3.2: the card sends only the value that was moved ----------


async def test_y1_the_colour_shown_for_a_light_that_was_off_is_stored(hass, setup, hass_ws_client, resident_token):
    """Spec 5.2: a ticked device shows its stored value.

    The way of a scene made by day with "Live-Anpassungen" off: the light is off, it is ticked,
    switched to "An" and dimmed. The card shows "Weiß" at 2000 K for it and sends it along (card probe Y1).
    """
    hass.states.async_set("light.kitchen", "off", WHITE_AND_COLOUR)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Evening", area_id="kitchen")
    entry = await light_step(call, sid)

    def stored() -> dict:
        return flat(setup.runtime_data.scenes[sid])[0]

    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    assert (stored()["state"], stored()["attributes"]) == ("off", {})
    # without a stored colour the switch "An" of the card sends the white it shows (card probe Y1)
    white = {"color_mode": "color_temp", "color_temp_kelvin": 2000}
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"color_temp_kelvin": 2000})))["success"]
    assert stored()["attributes"] == {"brightness": 255, **white}  # FIXED: the colour temperature is stored
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"brightness": 102})))["success"]
    assert stored()["attributes"] == {"brightness": 102, **white}  # FIXED
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]["sequence"][0]["entries"][0]["attributes"]
    assert shown["color_temp_kelvin"] == 2000  # the card shows what is stored
    on = async_mock_service(hass, "light", "turn_on")
    await run_scene(hass, eid(hass, sid))
    assert on[0].data["brightness"] == 102
    assert on[0].data["color_temp_kelvin"] == 2000  # FIXED: the light gets the white that was shown

    # the same for a light that is off and not ticked
    assert (await call(**cmd("remove_entry", sid, **entry)))["success"]
    values = {"brightness": 51, "color_temp_kelvin": 2000}  # the card sends the shown white along
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values=values)))["success"]
    assert stored()["attributes"] == {"brightness": 51, **white}  # FIXED
    # only the slider of the colour temperature itself stores it
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"color_temp_kelvin": 2000})))["success"]
    assert stored()["attributes"] == {"brightness": 51, "color_mode": "color_temp", "color_temp_kelvin": 2000}  # OK


async def test_stored_values_stay_when_one_is_moved(hass, setup, hass_ws_client, resident_token):
    """Spec 4.5, draft 0.10: an input changes only its own value. Holds for an entry that is on."""
    hass.states.async_set("light.kitchen", "on", {**WHITE_AND_COLOUR, "brightness": 200, "color_mode": "color_temp",
                                                  "color_temp_kelvin": 3000, "hs_color": (28.0, 65.0)})
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Evening", area_id="kitchen")
    entry = await light_step(call, sid)
    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"brightness": 26})))["success"]
    kept = {"brightness": 26, "color_mode": "color_temp", "color_temp_kelvin": 3000}
    assert flat(setup.runtime_data.scenes[sid])[0]["attributes"] == kept  # OK
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"hue": 240, "saturation": 100})))["success"]
    colour = {"brightness": 26, "color_mode": "hs", "hs_color": [240, 100]}
    assert flat(setup.runtime_data.scenes[sid])[0]["attributes"] == colour  # OK: the brightness stays


def test_hue_of_a_light_with_two_white_channels():
    """light_hs mixes the white channels of rgbww in like Home Assistant (review Y8)."""
    red_and_cold_white = (255, 0, 0, 255, 0)
    state = color_util.color_RGB_to_hs(*color_util.color_rgbww_to_rgb(*red_and_cold_white, 2000, 6500))
    assert state == (0.923, 50.98)  # what the state of the light says, shown while the light is not ticked
    assert light_hs({"rgbww_color": list(red_and_cold_white)}) == list(state)  # FIXED: shown once it is ticked
    narrow = color_util.color_RGB_to_hs(*color_util.color_rgbww_to_rgb(*red_and_cold_white, 2700, 5000))
    light = {"min_color_temp_kelvin": 2700, "max_color_temp_kelvin": 5000}
    assert light_hs({"rgbww_color": list(red_and_cold_white)}, light) == list(narrow)  # FIXED: the light's range
    rgbw = color_util.color_RGB_to_hs(*color_util.color_rgbw_to_rgb(255, 0, 0, 255))
    assert light_hs({"rgbw_color": [255, 0, 0, 255]}) == list(rgbw)  # OK: one white channel is mixed in


# ---------- entity id (draft 0.9, 4.3) ----------


async def test_entity_id_counts_on_when_the_new_name_has_the_same_slug(hass, setup, hass_ws_client, resident_token):
    call = await ws(hass, hass_ws_client, resident_token)
    await save(call, name="Abend", area_id="kitchen", edit="k")
    sid = (await call(type=f"{DOMAIN}/create", area_id="hall", name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    assert (await call(**cmd("update", sid, "c", name="Abend")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.abend_2"  # OK: scene.abend belongs to the kitchen
    assert (await call(**cmd("update", sid, "c", name="Abend!")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.abend_2"  # FIXED: its own id does not count as taken


async def test_entity_id_stops_following_when_a_second_account_edits(hass, setup, hass_ws_client, resident_token):
    """Draft 0.9, 4.3: the id follows the name as long as the creating edit runs."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    other = direct(setup.runtime_data, user_id="second-account", admin=False)
    assert (await other(**cmd("update", sid, "o", transition=2)))["success"]
    assert (await call(**cmd("update", sid, "c", name="Abend")))["success"]  # still the creating edit of the first one
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.abend"  # FIXED: only the end of the creating edit ends the following


async def test_y7_created_is_logged_under_the_id_that_holds(hass, setup, hass_ws_client, resident_token):
    """Added for 0.3.3 (Y7); changed on purpose in 0.3.4 (Z3): "created" is written once, under the first id."""
    changes = async_capture_events(hass, EVENT_CHANGED)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    assert (await call(**cmd("update", sid, "c", name="Abend")))["success"]
    assert (await call(**cmd("update", sid, "c", transition=2)))["success"]  # no new id, nothing logged
    await hass.async_block_till_done()
    logged = [(c.data["action"], c.data["entity_id"], c.data["name"]) for c in changes]
    assert logged == [("created", "scene.neue_szene_1", "Neue Szene 1")]  # FIXED in 0.3.4: one entry (spec 4.10, Z3)


# ---------- points that hold ----------


async def test_moved_device_in_a_step_without_a_room(hass, setup, hass_ws_client, resident_token):
    """X3, X10: the entry of a device that got a room stays, runs, is marked and survives "Alle" and capture."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Cook", area_id="kitchen",
                     steps=[{"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 10}}])
    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity("light.kitchen", area_id="hall")
    await hass.async_block_till_done()
    step = setup.runtime_data.scenes[sid]["sequence"][0]
    assert step["area_id"] is None
    assert (await call(**cmd("set_all", sid, step_id=step["id"], mode="capture")))["success"]
    await hass.services.async_call(DOMAIN, "capture", {"entity_id": eid(hass, sid)}, blocking=True)
    entry = flat(setup.runtime_data.scenes[sid])[0]
    assert (entry["entity_id"], entry["attributes"]["brightness"]) == ("light.kitchen", 10)  # OK: the value stays
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]["sequence"][0]["entries"][0]
    assert shown["issue"] == "other_area"  # OK
    assert (await call(**cmd("remove_entry", sid, step_id=step["id"], entity_id="light.kitchen")))["success"]  # OK


async def test_temperature_out_of_range(hass, setup, hass_ws_client, resident_token):
    """The setpoint is a text field now (X8); the card checks the range too and names it (card probe, Y4)."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Warm", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="climate")))["result"]["step_id"]
    values = {"hvac_mode": "heat", "temperature": 99}
    res = await call(**cmd("set_entry", sid, step_id=step_id, entity_id="climate.kitchen", mode="set", values=values))
    assert res["error"]["code"] == "invalid_value"  # OK
    assert res["error"]["message"] == "invalid_value: temperature"  # the card maps this key to the range (Y4)
