"""Version 0.7.0, stage 5: schedules (spec 4.15, 5.8), with a stepped clock; and the open points AD6, AE1, AE2."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events, async_fire_time_changed

from custom_components.resident_scenes.const import (
    CONF_ROOMS,
    CONF_SCHEDULES,
    CONF_USERS_WITHOUT_EDIT,
    DOMAIN,
    EVENT_ALL_OFF,
    EVENT_CHANGED,
    EVENT_SCHEDULE,
    STORAGE_KEY,
)
from custom_components.resident_scenes.diagnostics import async_get_config_entry_diagnostics
from custom_components.resident_scenes.logbook import async_describe_events
from custom_components.resident_scenes.model import ValidationError
from custom_components.resident_scenes.schedules import next_run
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import area_registry as ar, entity_registry as er, issue_registry as ir
from homeassistant.util import dt as dt_util
from tests.conftest import direct, eid, save, ws

BERLIN = ZoneInfo("Europe/Berlin")
LIGHT_ON = {"entity_id": "light.kitchen", "mode": "set", "values": {"brightness": 120}}
HALL_ON = {"entity_id": "light.hall", "mode": "set", "values": {"brightness": 90}}


async def _at(hass: HomeAssistant, freezer, when: datetime) -> None:
    """Step the clock to a moment and let the timers of that moment run."""
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _plan(store, scene_id=None, entity_id=None, active=True, **fields) -> dict:
    """A schedule made like the card does: created, then one field per input, then switched on."""
    schedule = await store.async_create_schedule(store.scene_ref(scene_id, entity_id), "Plan", "e0", None)
    for key, value in fields.items():
        await store.async_update_schedule(schedule["id"], key, value, "e0", None)
    if active:
        await store.async_update_schedule(schedule["id"], "active", True, "e0", None)
    # let the debounced recheck of registry changes run now, not at the stepped moment
    async_fire_time_changed(store.hass, dt_util.utcnow() + timedelta(seconds=30))
    await store.hass.async_block_till_done()
    return schedule


def _ran(events) -> list[str]:
    return [e.data["schedule_id"] for e in events if e.data["action"] == "ran"]


def _switch(hass: HomeAssistant, schedule_id: str) -> str:
    return er.async_get(hass).async_get_entity_id("switch", DOMAIN, schedule_id)


@pytest.fixture
async def berlin(hass: HomeAssistant, setup, freezer):
    """Europe/Berlin and Hamburg, the clock frozen on a Thursday in June."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    hass.config.latitude, hass.config.longitude, hass.config.elevation = 53.5511, 9.9937, 0
    freezer.move_to(datetime(2026, 6, 18, 12, 0, tzinfo=BERLIN))
    return setup


async def test_dst_spring_runs_once_at_three(hass: HomeAssistant, berlin, freezer):
    """Spec 4.15: 2:30 in the night summer time begins runs once, at 3:00; 7:00 at 7:00."""
    store = berlin.runtime_data
    sid = await save(direct(store), name="Night", area_id="kitchen", steps=[LIGHT_ON])
    freezer.move_to(datetime(2026, 3, 28, 12, 0, tzinfo=BERLIN))
    events = async_capture_events(hass, EVENT_SCHEDULE)
    night = await _plan(store, sid, time="02:30")
    morning = await _plan(store, sid, time="07:00")
    three = datetime(2026, 3, 29, 3, 0, tzinfo=BERLIN)
    assert store.scheduler.next[night["id"]] == three  # 1:00 UTC, the end of the skipped hour
    await _at(hass, freezer, dt_util.as_utc(three) - timedelta(minutes=1))  # 2:59 winter time
    assert _ran(events) == []
    await _at(hass, freezer, three)
    assert _ran(events) == [night["id"]]
    assert store.scheduler.next[night["id"]] == datetime(2026, 3, 30, 2, 30, tzinfo=BERLIN)
    await _at(hass, freezer, datetime(2026, 3, 29, 7, 0, tzinfo=BERLIN))
    assert _ran(events) == [night["id"], morning["id"]]
    # the scene names the schedule as its trigger: the same context
    assert hass.states.get(eid(hass, sid)).context.id == events[-1].context.id


async def test_dst_autumn_runs_once_at_the_first(hass: HomeAssistant, berlin, freezer):
    """Spec 4.15: 2:30 in the night summer time ends runs once, at the first 2:30; 7:00 at 7:00."""
    store = berlin.runtime_data
    sid = await save(direct(store), name="Night", area_id="kitchen", steps=[LIGHT_ON])
    freezer.move_to(datetime(2026, 10, 24, 12, 0, tzinfo=BERLIN))
    events = async_capture_events(hass, EVENT_SCHEDULE)
    night = await _plan(store, sid, time="02:30")
    morning = await _plan(store, sid, time="07:00")
    first = datetime(2026, 10, 25, 0, 30, tzinfo=dt_util.UTC)  # 2:30 summer time
    assert store.scheduler.next[night["id"]] == first
    await _at(hass, freezer, first)
    await _at(hass, freezer, first + timedelta(hours=1))  # 2:30 winter time, the second one
    assert _ran(events) == [night["id"]]
    await _at(hass, freezer, datetime(2026, 10, 25, 7, 0, tzinfo=BERLIN))
    assert _ran(events) == [night["id"], morning["id"]]
    assert store.scheduler.next[night["id"]] == datetime(2026, 10, 26, 2, 30, tzinfo=BERLIN)


async def test_sun_offset_over_midnight(hass: HomeAssistant, berlin, freezer):
    """Spec 4.15: Hamburg in June, 180 minutes after sunset on Friday runs in the night to Saturday."""
    store = berlin.runtime_data
    sid = await save(direct(store), name="Late", area_id="kitchen", steps=[LIGHT_ON])
    events = async_capture_events(hass, EVENT_SCHEDULE)
    late = await _plan(store, sid, trigger="sunset", offset=180, weekdays=[4])
    moment = store.scheduler.next[late["id"]]
    local = dt_util.as_local(moment)
    assert (local.date().isoformat(), local.hour) == ("2026-06-20", 0)  # 0:53 on Saturday, not Friday
    assert 50 <= local.minute <= 59
    await _at(hass, freezer, datetime(2026, 6, 19, 1, 0, tzinfo=BERLIN))  # the night to Friday: nothing
    assert _ran(events) == []
    await _at(hass, freezer, moment)
    assert _ran(events) == [late["id"]]
    attrs = hass.states.get(_switch(hass, late["id"])).attributes
    assert attrs["trigger"] == "sunset" and attrs["offset"] == 180 and attrs["weekdays"] == ["fri"]
    assert attrs["next_run"].startswith("2026-06-26T")  # a week later
    # 20 minutes before sunrise, every day
    early = await _plan(store, sid, trigger="sunrise", offset=-20)
    assert dt_util.as_local(store.scheduler.next[early["id"]]).hour == 4


async def test_day_without_sunset(hass: HomeAssistant, berlin, freezer):
    """Spec 4.15: far north in summer there is no sunset; the schedule runs on the next day that has one."""
    hass.config.latitude, hass.config.longitude = 78.22, 15.65
    schedule = {"trigger": "sunset", "offset": 0, "weekdays": list(range(7))}
    moment = next_run(hass, schedule, dt_util.utcnow())
    assert moment.month == 8  # nothing in June and July
    assert next_run(hass, {**schedule, "trigger": "sunrise"}, dt_util.utcnow()).month == 8


async def test_restart_makes_up_nothing(hass: HomeAssistant, berlin, freezer):
    """Spec 4.15, acceptance "Neustart": stopped at the moment, started ten minutes later; no run made up."""
    store = berlin.runtime_data
    sid = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    plan = await _plan(store, sid, time="13:00")
    events = async_capture_events(hass, EVENT_SCHEDULE)
    await hass.config_entries.async_unload(berlin.entry_id)
    await _at(hass, freezer, datetime(2026, 6, 18, 13, 10, tzinfo=BERLIN))
    assert await hass.config_entries.async_setup(berlin.entry_id)
    await hass.async_block_till_done()
    store = berlin.runtime_data
    assert _ran(events) == [] and store.schedules[0]["active"] is True
    assert store.scheduler.next[plan["id"]] == datetime(2026, 6, 19, 13, 0, tzinfo=BERLIN)


async def test_changed_time_and_same_moment(hass: HomeAssistant, berlin, freezer):
    """Spec 4.15: a time already past runs on the next day, one still to come today; same moment in list order."""
    store = berlin.runtime_data
    cook = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    hall = await save(direct(store), name="Hall", area_id="hall", steps=[HALL_ON], edit="e2")
    freezer.move_to(datetime(2026, 6, 18, 10, 0, tzinfo=BERLIN))
    events = async_capture_events(hass, EVENT_SCHEDULE)
    first = await _plan(store, cook, time="09:00")
    assert store.scheduler.next[first["id"]] == datetime(2026, 6, 19, 9, 0, tzinfo=BERLIN)
    await store.async_update_schedule(first["id"], "time", "10:05", "e1", None)
    second = await _plan(store, hall, time="10:05")
    await _at(hass, freezer, datetime(2026, 6, 18, 10, 5, tzinfo=BERLIN))
    assert _ran(events) == [first["id"], second["id"]]
    # set to a later time of the same day: it runs again today
    await store.async_update_schedule(first["id"], "time", "10:30", "e1", None)
    store.move_schedule(second["id"], 0, {first["id"], second["id"]})
    await store.async_update_schedule(second["id"], "time", "10:30", "e1", None)
    await _at(hass, freezer, datetime(2026, 6, 18, 10, 30, tzinfo=BERLIN))
    assert _ran(events)[2:] == [second["id"], first["id"]]
    # off: no run, all values kept
    await store.async_update_schedule(first["id"], "active", False, "", None)
    assert first["id"] not in store.scheduler.next and first["time"] == "10:30"
    # a new time zone applies to the next run
    await hass.config.async_update(time_zone="Europe/London")
    await hass.async_block_till_done()
    assert dt_util.as_local(store.scheduler.next[second["id"]]).hour == 10
    london = ZoneInfo("Europe/London")
    assert store.scheduler.next[second["id"]] == datetime(2026, 6, 18, 10, 30, tzinfo=london)  # still today


async def test_weekdays_and_new_schedule(hass: HomeAssistant, berlin, freezer, hass_ws_client, resident_token):
    """Acceptance "Uhrzeit und Wochentage", "Neuer Zeitplan": 7:00 Mon to Fri runs Friday, not Saturday."""
    store = berlin.runtime_data
    sid = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    call = await ws(hass, hass_ws_client, resident_token)
    res = await call(type=f"{DOMAIN}/schedule_create", scene_id=sid, name="Neuer Zeitplan", edit="e1")
    assert res["success"]
    pid = res["result"]["schedule_id"]
    plan = store.schedule(pid)
    assert (plan["name"], plan["active"], plan["trigger"], plan["time"], plan["weekdays"]) == (
        "Neuer Zeitplan 1", False, "time", "12:00", [0, 1, 2, 3, 4, 5, 6])
    events = async_capture_events(hass, EVENT_SCHEDULE)
    for msg in ({"time": "07:00"}, {"weekdays": [0, 1, 2, 3, 4]}, {"active": True}):
        assert (await call(type=f"{DOMAIN}/schedule_update", schedule_id=pid, edit="e1", **msg))["success"]
    assert [e.data["action"] for e in events] == ["switched on"]  # the creating edit has its entry; switching apart
    assert (await call(type=f"{DOMAIN}/schedule_update", schedule_id=pid, edit="e1", weekdays=[]))["error"]["code"] \
        == "no_weekday"
    two = await call(type=f"{DOMAIN}/schedule_update", schedule_id=pid, edit="e1", time="08:00", offset=5)
    assert not two["success"]  # one field per input
    none = await call(type=f"{DOMAIN}/schedule_update", schedule_id=pid, edit="e1")
    assert none["error"]["code"] == "invalid_value"
    listed = (await call(type=f"{DOMAIN}/schedules"))["result"]
    shown = listed["schedules"][0]
    assert shown["scene_name"] == "Cook" and shown["area_id"] == "kitchen" and shown["issue"] is None
    assert shown["next_run"] == "2026-06-19T05:00:00+00:00" and shown["entity_id"] == _switch(hass, pid)
    assert {c.get("scene_id") for c in listed["scenes"]} >= {sid}
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))  # the debounced recheck first
    await hass.async_block_till_done()
    await _at(hass, freezer, datetime(2026, 6, 19, 7, 0, tzinfo=BERLIN))  # Friday
    await _at(hass, freezer, datetime(2026, 6, 20, 7, 0, tzinfo=BERLIN))  # Saturday
    assert _ran(events) == [pid]
    assert store.scheduler.next[pid] == datetime(2026, 6, 22, 7, 0, tzinfo=BERLIN)


async def test_entity_id_follows_the_name_in_the_creating_edit(
    hass: HomeAssistant, setup, hass_ws_client, resident_token
):
    """Spec 4.15: like a scene, the entity id follows the name while the creating edit runs, then stays."""
    store = setup.runtime_data
    sid = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    call = await ws(hass, hass_ws_client, resident_token)
    pid = (await call(type=f"{DOMAIN}/schedule_create", scene_id=sid, name="New schedule", edit="e1"))["result"][
        "schedule_id"]
    await hass.async_block_till_done()
    assert _switch(hass, pid) == "switch.new_schedule_1"
    assert hass.states.get("switch.new_schedule_1").state == "off"
    await call(type=f"{DOMAIN}/schedule_update", schedule_id=pid, edit="e1", name="Garden")
    await hass.async_block_till_done()
    assert _switch(hass, pid) == "switch.garden"
    assert hass.states.get("switch.garden").name == "Garden"
    await call(type=f"{DOMAIN}/schedule_update", schedule_id=pid, edit="e2", name="Terrace")
    await hass.async_block_till_done()
    assert _switch(hass, pid) == "switch.garden"  # a later edit keeps it
    # without a user the switch always switches; the card sees it
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.garden"}, blocking=True)
    assert store.schedule(pid)["active"] is True
    assert hass.states.get("switch.garden").attributes["scene_entity_id"] == eid(hass, sid)
    # deleted: the entity goes
    assert (await call(type=f"{DOMAIN}/schedule_delete", schedule_id=pid))["success"]
    await hass.async_block_till_done()
    assert _switch(hass, pid) is None and store.schedules == []


async def test_rights(hass: HomeAssistant, setup, hass_ws_client, resident_token, hass_read_only_user):
    """Spec 4.15, acceptance "Rechte": an account limited to the kitchen sees, creates and switches only there."""
    store = setup.runtime_data
    admin = direct(store)
    cook = await save(admin, name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    hall = await save(admin, name="Hall", area_id="hall", steps=[HALL_ON], edit="e2")
    away = await save(admin, name="Away", steps=[HALL_ON], edit="e3")
    hall_plan = await _plan(store, hall)
    uid = hass_read_only_user.id
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {uid: ["kitchen"]}})
    await hass.async_block_till_done()
    call = await ws(hass, hass_ws_client, resident_token)
    res = await call(type=f"{DOMAIN}/schedule_create", scene_id=hall, name="New", edit="e1")
    assert res["error"]["code"] == "no_access"
    assert (await call(type=f"{DOMAIN}/schedule_create", scene_id=cook, name="New", edit="e1"))["success"]
    # a house scene: the house right and the edit right are enough, not all rooms (spec 4.15)
    assert (await call(type=f"{DOMAIN}/schedule_create", scene_id=away, name="New", edit="e1"))["success"]
    listed = (await call(type=f"{DOMAIN}/schedules"))["result"]
    assert [s["scene_name"] for s in listed["schedules"]] == ["Cook", "Away"]
    assert {c.get("scene_id") for c in listed["scenes"] if c.get("scene_id")} == {cook, away}
    for msg in (
        {"type": f"{DOMAIN}/schedule_update", "active": False},
        {"type": f"{DOMAIN}/schedule_delete"},
        {"type": f"{DOMAIN}/schedule_move", "index": 0},
    ):
        assert (await call(**msg, schedule_id=hall_plan["id"]))["error"]["code"] == "not_found"
    mine = listed["schedules"][0]["id"]
    res = await call(type=f"{DOMAIN}/schedule_update", schedule_id=mine, scene_id=hall)
    assert res["error"]["code"] == "no_access"
    # the order: the account moves what it sees, the hall schedule keeps its first place
    assert (await call(type=f"{DOMAIN}/schedule_move", schedule_id=mine, index=1))["success"]
    assert [s["scene_name"] for s in store.schedules] == ["Hall", "Away", "Cook"]
    # the switch entity: refused with the account, logged, state unchanged; without a user it applies
    await hass.async_block_till_done()
    events = async_capture_events(hass, EVENT_SCHEDULE)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": _switch(hass, hall_plan["id"])}, blocking=True,
            context=Context(user_id=uid),
        )
    assert store.schedule(hall_plan["id"])["active"] is True
    assert events[-1].data["action"] == "not switched: no right for it"
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": _switch(hass, mine)}, blocking=True, context=Context(user_id=uid)
    )
    assert store.schedule(mine)["active"] is False
    # the right taken from the creator: the schedule runs on, it is no longer shown to the account
    hass.config_entries.async_update_entry(setup, options={CONF_ROOMS: {uid: ["hall"]}})
    assert store.scheduler.next.get(hall_plan["id"])
    # without the edit right: sees, changes and switches nothing
    hass.config_entries.async_update_entry(setup, options={CONF_USERS_WITHOUT_EDIT: [uid]})
    listed = (await call(type=f"{DOMAIN}/schedules"))["result"]
    assert listed["can_edit"] is False and listed["scenes"] == [] and len(listed["schedules"]) == 3
    res = await call(type=f"{DOMAIN}/schedule_update", schedule_id=mine, active=True)
    assert res["error"]["code"] == "unauthorized"
    assert (await call(type=f"{DOMAIN}/schedule_create", scene_id=cook, name="N", edit="x"))["error"]["code"] == \
        "unauthorized"
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": _switch(hass, mine)}, blocking=True, context=Context(user_id=uid)
        )


async def test_limit(hass: HomeAssistant, setup, hass_ws_client, resident_token):
    """Spec 4.15: 20 schedules, as set; a direct call is refused."""
    store = setup.runtime_data
    sid = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    hass.config_entries.async_update_entry(setup, options={CONF_SCHEDULES: 2})
    call = await ws(hass, hass_ws_client, resident_token)
    for _ in range(2):
        assert (await call(type=f"{DOMAIN}/schedule_create", scene_id=sid, name="Plan", edit="e"))["success"]
    assert [s["name"] for s in store.schedules] == ["Plan 1", "Plan 2"]
    res = await call(type=f"{DOMAIN}/schedule_create", scene_id=sid, name="Plan", edit="e")
    assert res["error"]["code"] == "schedule_limit"
    assert (await call(type=f"{DOMAIN}/schedules"))["result"]["full"] is True
    for name, code in (("", "invalid_name"), ("x" * 31, "invalid_name")):
        res = await call(type=f"{DOMAIN}/schedule_update", schedule_id=store.schedules[0]["id"], name=name)
        assert res["error"]["code"] == code
    res = await call(type=f"{DOMAIN}/schedule_update", schedule_id=store.schedules[0]["id"], offset=181)
    assert res["error"]["code"] == "invalid_value"
    res = await call(type=f"{DOMAIN}/schedule_update", schedule_id=store.schedules[0]["id"], scene_id="nope")
    assert res["error"]["code"] == "scene_not_allowed"
    with pytest.raises(ValidationError):
        await store.async_create_schedule(store.scene_ref(sid, None), " ", "e", None)
    assert (await call(type=f"{DOMAIN}/schedule_create", entity_id="light.kitchen", name="P", edit="e"))["error"][
        "code"] == "scene_not_allowed"


async def test_scene_missing(hass: HomeAssistant, berlin, freezer, hass_ws_client, resident_token):
    """Acceptance "Szene gelöscht": named before deleting, then "scene missing", an issue, a skipped run, back."""
    store = berlin.runtime_data
    cook = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    other = await save(direct(store), name="Other", area_id="kitchen", steps=[LIGHT_ON], edit="e2")
    plan = await _plan(store, cook, time="13:00")
    await _plan(store, cook, active=False)  # off: no issue for it
    call = await ws(hass, hass_ws_client, resident_token)
    assert (await call(type=f"{DOMAIN}/scene", scene_id=cook))["result"]["used_in"]["schedules"] == ["Plan 1", "Plan 2"]
    assert (await call(type=f"{DOMAIN}/delete", scene_id=cook))["success"]
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=30))
    await hass.async_block_till_done()
    issues = ir.async_get(hass)
    issue = issues.async_get_issue(DOMAIN, f"schedule_{plan['id']}")
    assert issue.translation_key == "schedule_scene_missing"
    assert issue.translation_placeholders == {"schedule": "Plan 1", "scene": "Cook"}
    assert len([i for (d, i) in issues.issues if d == DOMAIN and i.startswith("schedule_")]) == 1
    shown = (await call(type=f"{DOMAIN}/schedules"))["result"]["schedules"][0]
    assert (shown["issue"], shown["next_run"], shown["area_id"], shown["scene_name"]) == (
        "scene_missing", None, "kitchen", "Cook")
    assert hass.states.get(_switch(hass, plan["id"])).attributes["next_run"] is None
    events = async_capture_events(hass, EVENT_SCHEDULE)
    await _at(hass, freezer, datetime(2026, 6, 18, 13, 0, tzinfo=BERLIN))
    assert [(e.data["action"], e.data.get("reason")) for e in events] == [("not run", "scene_missing")]
    # the room deleted: it goes to the house
    ar.async_get(hass).async_delete("kitchen")
    await hass.async_block_till_done()
    assert store.schedule(plan["id"])["area_id"] is None
    # another scene: it runs again and the issue goes
    other_area = store.scenes[other]["area_id"]
    assert other_area is None  # moved to the house with its room
    res = await call(type=f"{DOMAIN}/schedule_update", schedule_id=plan["id"], edit="e9", scene_id=other)
    assert res["success"]
    assert issues.async_get_issue(DOMAIN, f"schedule_{plan['id']}") is None
    assert store.scheduler.next[plan["id"]] == datetime(2026, 6, 19, 13, 0, tzinfo=BERLIN)


async def test_scene_of_another_integration(hass: HomeAssistant, berlin, freezer):
    """Acceptance "KNX-Szene": runs; without the label "not released", no run, an issue; unreachable skips."""
    store = berlin.runtime_data
    ent_reg = er.async_get(hass)
    knx = ent_reg.async_get_or_create("scene", "knx", "evening", suggested_object_id="knx_evening")
    ent_reg.async_update_entity(knx.entity_id, area_id="kitchen", labels={"resident_scenes"})
    hass.states.async_set(knx.entity_id, "unknown", {"friendly_name": "KNX Evening"})
    plan = await _plan(store, entity_id=knx.entity_id, time="13:00")
    assert (plan["scene_id"], plan["registry_id"], plan["area_id"]) == (None, knx.id, "kitchen")
    events = async_capture_events(hass, EVENT_SCHEDULE)
    calls = []
    hass.services.async_register("scene", "turn_on", lambda c: calls.append(c))  # replaces the scene action
    await _at(hass, freezer, datetime(2026, 6, 18, 13, 0, tzinfo=BERLIN))
    assert [c.data["entity_id"] for c in calls] == ["scene.knx_evening"]
    assert calls[0].context.id == events[-1].context.id and events[-1].data["scene"] == "KNX Evening"
    # a new entity id is followed
    ent_reg.async_update_entity(knx.entity_id, new_entity_id="scene.knx_abend")
    await hass.async_block_till_done()
    hass.states.async_set("scene.knx_abend", STATE_UNAVAILABLE)
    await _at(hass, freezer, datetime(2026, 6, 19, 13, 0, tzinfo=BERLIN))
    assert (events[-1].data["action"], events[-1].data["reason"]) == ("not run", "not_reachable")
    # the label taken: not released, an issue, no run
    ent_reg.async_update_entity("scene.knx_abend", labels=set())
    await _at(hass, freezer, datetime(2026, 6, 19, 13, 0, 5, tzinfo=BERLIN))
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"schedule_{plan['id']}")
    assert issue.translation_key == "schedule_not_released"
    assert plan["id"] not in store.scheduler.next
    hass.states.async_set("scene.knx_abend", "unknown")
    await _at(hass, freezer, datetime(2026, 6, 20, 13, 0, tzinfo=BERLIN))
    assert events[-1].data["reason"] == "not_released" and len(calls) == 1
    # the label back: runs again
    ent_reg.async_update_entity("scene.knx_abend", labels={"resident_scenes"})
    await _at(hass, freezer, datetime(2026, 6, 20, 13, 0, 5, tzinfo=BERLIN))
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"schedule_{plan['id']}") is None
    await _at(hass, freezer, datetime(2026, 6, 21, 13, 0, tzinfo=BERLIN))
    assert [c.data["entity_id"] for c in calls] == ["scene.knx_evening", "scene.knx_abend"]
    # the scene entity removed: missing
    ent_reg.async_remove("scene.knx_abend")
    await hass.async_block_till_done()
    assert store.scene_ref is not None and store.schedule(plan["id"])["area_id"] == "kitchen"


async def test_failing_scene_does_not_stop_the_others(hass: HomeAssistant, berlin, freezer):
    """A scene of another integration that fails is logged; the next schedule of the moment still runs."""
    store = berlin.runtime_data
    cook = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    ent_reg = er.async_get(hass)
    knx = ent_reg.async_get_or_create("scene", "knx", "evening", suggested_object_id="knx_evening")
    ent_reg.async_update_entity(knx.entity_id, area_id="kitchen", labels={"resident_scenes"})
    hass.states.async_set(knx.entity_id, "unknown")
    await _plan(store, entity_id=knx.entity_id, time="13:00")
    second = await _plan(store, cook, time="13:00")
    calls = []

    def scene_on(call):
        if call.data["entity_id"] == knx.entity_id:
            raise RuntimeError("bus down")
        calls.append(call.data["entity_id"])

    hass.services.async_register("scene", "turn_on", scene_on)  # replaces the scene action
    events = async_capture_events(hass, EVENT_SCHEDULE)
    await _at(hass, freezer, datetime(2026, 6, 18, 13, 0, tzinfo=BERLIN))
    assert _ran(events)[-1] == second["id"] and len(_ran(events)) == 2
    assert calls == [eid(hass, cook)]


async def test_logbook_diagnostics_and_migration(hass: HomeAssistant, setup, hass_storage):
    """Logbook texts, counts without names, and an update from format 3 that changes nothing (spec 4.11)."""
    describers: dict = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))
    describe = describers[EVENT_SCHEDULE]

    def message(**data):
        event = type("E", (), {"data": {"name": "Plan", "entity_id": "switch.plan", **data}})()
        return describe(event)

    ran = {"name": "Plan", "message": "ran scene Cook", "entity_id": "switch.plan"}
    assert message(action="ran", scene="Cook") == ran
    assert message(action="not run", reason="scene_missing", scene="Cook")["message"] == "not run: scene missing (Cook)"
    assert message(action="switched on", entity_id=None) == {"name": "Plan", "message": "schedule switched on"}
    store = setup.runtime_data
    sid = await save(direct(store), name="Cook", area_id="kitchen", steps=[LIGHT_ON])
    await _plan(store, sid)
    diag = await async_get_config_entry_diagnostics(hass, setup)
    assert (diag["schedules"], diag["active_schedules"]) == (1, 1)
    assert "Plan" not in str(diag)
    # format 3 written by 0.6.0: an empty list of schedules, scenes and slots as they were
    await hass.config_entries.async_unload(setup.entry_id)
    scenes = hass_storage[STORAGE_KEY]["data"]["scenes"]
    hass_storage[STORAGE_KEY] = {"version": 3, "minor_version": 1, "key": STORAGE_KEY,
                                 "data": {"scenes": scenes, "favorites": {"kitchen": [sid]}}}
    assert await hass.config_entries.async_setup(setup.entry_id)
    await hass.async_block_till_done()
    store = setup.runtime_data
    assert store.schedules == [] and store.favorites == {"kitchen": [sid]} and store.scenes[sid]["name"] == "Cook"


async def test_all_off_without_a_device(hass: HomeAssistant, setup):
    """Spec 4.13, review AD6: nothing released in the room; the response says so, the logbook names it."""
    empty = ar.async_get(hass).async_create("Cellar")
    events = async_capture_events(hass, EVENT_ALL_OFF)
    res = await hass.services.async_call(
        DOMAIN, "all_off", {"area_id": empty.id}, blocking=True, return_response=True
    )
    assert res == {"devices": 0} and events[-1].data["empty"] is True
    describers: dict = {}
    async_describe_events(hass, lambda domain, event, fn: describers.__setitem__(event, fn))
    assert describers[EVENT_ALL_OFF](events[-1])["message"] == "all off: nothing released in this room"
    res = await hass.services.async_call(DOMAIN, "all_off", {"area_id": "kitchen"}, blocking=True, return_response=True)
    assert res == {"devices": 1} and events[-1].data["empty"] is False


async def test_moved_device_logbook_and_undo(hass: HomeAssistant, setup):
    """Spec 4.5, reviews AE1 and AE2: the move is named once per scene; undo brings back a state that follows it."""
    store = setup.runtime_data
    call = direct(store)
    sid = await save(call, name="Away", steps=[LIGHT_ON])
    # a second edit: its undo state holds the light in the kitchen step
    res = await call(type=f"{DOMAIN}/update", scene_id=sid, edit="e2", transition=2)
    assert res["success"]
    events = async_capture_events(hass, EVENT_CHANGED)
    er.async_get(hass).async_update_entity("light.kitchen", area_id="hall")
    await hass.async_block_till_done()
    moved = [e for e in events if e.data["action"] == "follows moved devices"]
    assert len(moved) == 1 and moved[0].data["scene_id"] == sid and moved[0].data["entity_id"] == eid(hass, sid)
    scene = store.scenes[sid]
    await store.async_undo(sid, scene["version"], None, True)
    groups = [(s["area_id"], [e["entity_id"] for e in s["entries"]]) for s in store.scenes[sid]["sequence"]]
    assert groups == [("hall", ["light.kitchen"])]
    assert store.scenes[sid]["transition"] is None
