"""Review of version 0.3.3 (commit 2a4a17e), taken over for 0.3.4.

Lines marked FIXED were FINDING or NOTE in the review and now assert the corrected behaviour, OK a point that holds.
"""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import async_capture_events, async_mock_service

from custom_components.resident_scenes.const import DOMAIN, EVENT_CHANGED
from tests.conftest import eid, flat, run_scene, save, ws

WHITE_MODE = {"supported_color_modes": ["hs", "white"], "color_mode": "white", "brightness": 200}


def cmd(command: str, sid: str, edit: str = "e", **fields) -> dict:
    return {"type": f"{DOMAIN}/{command}", "scene_id": sid, "edit": edit, **fields}


# ---------- entity id (spec 4.3, 4.5) ----------


async def test_z1_entity_id_follows_after_the_creating_edit_ended(hass, setup, hass_ws_client, resident_token, freezer):
    """Spec 4.5: an edit ends after ten minutes without input, also with the editor left open.

    4.3: then the id stays.
    """
    changes = async_capture_events(hass, EVENT_CHANGED)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.neue_szene_1"
    freezer.tick(24 * 3600)  # the editor of the wall panel stayed open over night
    assert (await call(**cmd("update", sid, "c", name="Abend")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.neue_szene_1"  # FIXED: an automation using scene.neue_szene_1 keeps its target
    logged = [(c.data["action"], c.data["entity_id"]) for c in changes]
    # the same input is a new edit for the logbook, for undo and for the entity id
    assert logged == [("created", "scene.neue_szene_1"), ("changed", "scene.neue_szene_1")]  # FIXED
    assert setup.runtime_data.scenes[sid]["previous"]["name"] == "Neue Szene 1"


async def test_created_is_logged_once_per_new_id(hass, setup, hass_ws_client, resident_token):
    """Spec 4.10: creating a scene gives one entry; it stays under the first id (README)."""
    changes = async_capture_events(hass, EVENT_CHANGED)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    for name in ("Abend", "Abend im Garten"):  # the name is typed and then corrected
        assert (await call(**cmd("update", sid, "c", name=name)))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.abend_im_garten"  # the id still follows in the creating edit
    logged = [(c.data["action"], c.data["entity_id"]) for c in changes]
    assert logged == [("created", "scene.neue_szene_1")]  # FIXED: one entry "scene created" for one scene


# ---------- a light in the colour mode "white" ----------


async def test_z2_light_in_white_mode_gets_the_default_colour(hass, setup, hass_ws_client, resident_token):
    """A light with colour channels and a white mode of its own (no colour temperature), on in white.

    The card shows a state "Weiß" without sliders and sends the brightness only (card probe Z2).
    """
    hass.states.async_set("light.kitchen", "on", WHITE_MODE)
    call = await ws(hass, hass_ws_client, resident_token)
    sid = await save(call, name="Evening", area_id="kitchen")
    step_id = (await call(**cmd("add_step", sid, step_type="group", domain="light")))["result"]["step_id"]
    entry = {"step_id": step_id, "entity_id": "light.kitchen"}
    devices = (await call(type=f"{DOMAIN}/devices", area_id="kitchen"))["result"]["entities"]
    capabilities = next(d for d in devices if d["entity_id"] == "light.kitchen")["capabilities"]
    assert (capabilities["color"], capabilities["color_temp"]) == (True, False)
    assert capabilities["white_mode"] is True  # FIXED: the card knows the mode

    def stored() -> dict:
        return flat(setup.runtime_data.scenes[sid])[0]["attributes"]

    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    assert stored() == {"brightness": 200, "color_mode": "white"}  # OK: ticked, the white mode is stored and runs
    values = {"brightness": 102}  # the brightness slider of the card of 0.3.4
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values=values)))["success"]
    assert stored() == {"brightness": 102, "color_mode": "white"}  # FIXED: white stays white
    hass.states.async_set("light.kitchen", "off", {"supported_color_modes": ["hs", "white"]})
    on = async_mock_service(hass, "light", "turn_on")
    await run_scene(hass, eid(hass, sid))
    assert "hs_color" not in on[0].data  # FIXED: no orange
    # the state "Weiß" of the card, chosen while the light shows a colour
    hass.states.async_set("light.kitchen", "on", {**WHITE_MODE, "color_mode": "hs", "hs_color": [200, 50]})
    assert (await call(**cmd("set_entry", sid, **entry, mode="capture")))["success"]
    assert (await call(**cmd("set_entry", sid, **entry, mode="set", values={"white": True})))["success"]
    assert stored() == {"brightness": 200, "color_mode": "white"}  # FIXED
    # a light without the mode refuses it
    only_hs = {"supported_color_modes": ["hs"], "color_mode": "hs", "hs_color": [1, 2]}
    hass.states.async_set("light.kitchen", "on", only_hs)
    res = await call(**cmd("set_entry", sid, **entry, mode="set", values={"white": True}))
    assert res["error"]["code"] == "invalid_value"


# ---------- points that hold ----------


async def test_a_second_edit_of_the_creator_ends_the_following(hass, setup, hass_ws_client, resident_token):
    """Spec 4.3, Y6: only the end of the creating edit ends the following; a new edit of the creator is that end."""
    call = await ws(hass, hass_ws_client, resident_token)
    sid = (await call(type=f"{DOMAIN}/create", area_id=None, name="Neue Szene", edit="c"))["result"]["scene_id"]
    await hass.async_block_till_done()
    assert (await call(**cmd("update", sid, "d", transition=2)))["success"]  # "Fertig", then "Ändern" again
    assert (await call(**cmd("update", sid, "d", name="Abend")))["success"]
    await hass.async_block_till_done()
    assert eid(hass, sid) == "scene.neue_szene_1"  # OK
    shown = (await call(type=f"{DOMAIN}/scene", scene_id=sid))["result"]
    listed = (await call(type=f"{DOMAIN}/list", scope="_house"))["result"]["scenes"][0]
    assert "creating_edit" not in shown and "creating_edit" not in listed  # OK: the account id stays on the server
