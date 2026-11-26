"""Schedules: a scene runs by itself at a time or at sunrise or sunset (spec 4.15)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
from typing import Any

from homeassistant.auth.models import User
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE, STATE_UNAVAILABLE
from homeassistant.core import CALLBACK_TYPE, Context, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.sun import get_astral_event_next
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_SCHEDULE, SIGNAL_CHANGED
from .model import allowed_entities, can_edit, entity_area, may_see

_LOGGER = logging.getLogger(__name__)

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def target(hass: HomeAssistant, store: Any, schedule: dict[str, Any]) -> dict[str, Any]:
    """Return entity id, room, name and issue (scene_missing, not_released) of the scene of a schedule.

    Without its scene a schedule keeps the room and name it had last (spec 4.15).
    """
    ent_reg = er.async_get(hass)
    result = {"entity_id": None, "area_id": schedule["area_id"], "name": schedule["scene_name"]}
    result["issue"] = "scene_missing"
    if schedule["scene_id"]:
        scene = store.scenes.get(schedule["scene_id"])
        entity_id = ent_reg.async_get_entity_id("scene", DOMAIN, schedule["scene_id"]) if scene else None
        if scene and entity_id:
            result = {"entity_id": entity_id, "area_id": scene["area_id"], "name": scene["name"], "issue": None}
        return result
    # a scene of another integration: its entry in the registry, so a new entity id is followed
    if (ent := ent_reg.entities.get_entry(schedule["registry_id"])) is None:
        return result
    state = hass.states.get(ent.entity_id)
    return {
        "entity_id": ent.entity_id,
        "area_id": entity_area(hass, ent),
        "name": state.name if state else ent.name or ent.original_name or ent.entity_id,
        "issue": None if ent.entity_id in allowed_entities(hass, store.entry) else "not_released",
    }


def may_see_schedule(hass: HomeAssistant, store: Any, user: User, schedule: dict[str, Any]) -> bool:
    """An account sees a schedule if it may run its scene (spec 4.15)."""
    return may_see(hass, store.entry, user, target(hass, store, schedule)["area_id"])


def may_change_schedule(hass: HomeAssistant, store: Any, user: User, schedule: dict[str, Any]) -> bool:
    """Changing and switching needs the edit right and a schedule the account sees (spec 4.15)."""
    return can_edit(store.entry, user) and may_see_schedule(hass, store, user, schedule)


@callback
def fire_schedule_event(
    hass: HomeAssistant, schedule: dict[str, Any], action: str, context: Context | None, **extra: Any
) -> None:
    """Write a change, run or skipped run of a schedule to the logbook."""
    entity_id = er.async_get(hass).async_get_entity_id("switch", DOMAIN, schedule["id"])
    hass.bus.async_fire(
        EVENT_SCHEDULE,
        {"schedule_id": schedule["id"], "name": schedule["name"], "action": action, "entity_id": entity_id, **extra},
        context=context,
    )


def _moment(day: date, at: time) -> datetime:
    """Return the moment of a wall time on a day in the time zone of Home Assistant.

    A time in the hour skipped when summer time begins is moved to the end of that hour; of the hour that
    comes twice when it ends, the first is taken (spec 4.15). The time helper of the core does neither.
    """
    zone = dt_util.get_default_time_zone()
    wall = datetime.combine(day, at)
    moment = wall.replace(tzinfo=zone)  # fold 0: the first of a doubled hour
    while moment.astimezone(dt_util.UTC).astimezone(zone).replace(tzinfo=None) != wall:  # does not exist
        wall += timedelta(minutes=1)
        moment = wall.replace(tzinfo=zone)
    return moment


def next_run(hass: HomeAssistant, schedule: dict[str, Any], after: datetime) -> datetime | None:
    """Return the first run strictly after a moment, None if there is none (no sunset in the coming days)."""
    days = set(schedule["weekdays"])
    if schedule["trigger"] == "time":
        hour, minute = (int(x) for x in schedule["time"].split(":"))
        today = dt_util.as_local(after).date()
        for n in range(8):
            day = today + timedelta(days=n)
            if day.weekday() in days and (moment := _moment(day, time(hour, minute))) > after:
                return dt_util.as_utc(moment)
        return None  # pragma: no cover  (at least one weekday is always set)
    # the times of sunrise and sunset come from Home Assistant, which skips days without them
    offset = timedelta(minutes=schedule["offset"])
    point = after
    for _ in range(15):
        try:
            moment = get_astral_event_next(hass, schedule["trigger"], point, offset)
        except ValueError:  # no sunrise or sunset within a year
            return None
        # the weekday is that of the sunrise or sunset, not that of the run (spec 4.15)
        if dt_util.as_local(moment - offset).weekday() in days:
            return moment
        point = moment
    return None


class Scheduler:
    """One timer for the next moment of all active schedules, set again after each run and each change.

    Runs missed while Home Assistant was stopped are not made up (spec 4.15).
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, store: Any) -> None:
        """Initialize; connected before the entities, so they read the new times."""
        self.hass = hass
        self.store = store
        self.next: dict[str, datetime] = {}  # schedules that will run: shown as the next run
        self._due: dict[str, datetime] = {}  # also those whose scene is missing: their skip goes to the logbook
        self._unsub: CALLBACK_TYPE | None = None
        entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_CHANGED, self.async_reschedule))
        entry.async_on_unload(hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, self._config_changed))
        entry.async_on_unload(self._cancel)

    @callback
    def _cancel(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _config_changed(self, _event: Event) -> None:
        self.async_reschedule()  # time zone or location: the new values apply to the next run

    @callback
    def async_reschedule(self, after: datetime | None = None) -> None:
        """Find the next moment of every active schedule after a moment (default: now)."""
        self._cancel()
        after = after or dt_util.utcnow()
        self._due, self.next = {}, {}
        for schedule in self.store.schedules:
            if schedule["active"] and (moment := next_run(self.hass, schedule, after)):
                self._due[schedule["id"]] = moment
                if target(self.hass, self.store, schedule)["issue"] is None:
                    self.next[schedule["id"]] = moment
        if self._due:
            self._unsub = async_track_point_in_utc_time(self.hass, self._fire, min(self._due.values()))

    async def _fire(self, _now: datetime) -> None:
        """Run every schedule of this moment, in the order of the list (spec 4.15)."""
        self._unsub = None
        if not self._due:  # pragma: no cover  (the timer is cancelled when nothing is due)
            return
        moment = min(self._due.values())
        due = [s for s in self.store.schedules if self._due.get(s["id"]) == moment]
        self.async_reschedule(moment)  # strictly after this moment: each runs once
        for schedule in due:
            await self._run(schedule)
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)  # the next run of entities and cards

    async def _run(self, schedule: dict[str, Any]) -> None:
        """Run the scene without a user; the logbook names the schedule as the trigger."""
        hass = self.hass
        scene = target(hass, self.store, schedule)
        context = Context()
        issue = scene["issue"]
        state = hass.states.get(scene["entity_id"]) if scene["entity_id"] else None
        if issue is None and (state is None or state.state == STATE_UNAVAILABLE):
            issue = "not_reachable"
        if issue:
            _LOGGER.info("Schedule %s not run: %s", schedule["name"], issue)
            fire_schedule_event(hass, schedule, "not run", context, scene=scene["name"], reason=issue)
            return
        # the scene's state change carries this context, so the logbook shows the schedule as its trigger
        fire_schedule_event(hass, schedule, "ran", context, scene=scene["name"])
        try:
            await hass.services.async_call(
                "scene", "turn_on", {"entity_id": scene["entity_id"]}, blocking=True, context=context
            )
        except Exception as err:  # noqa: BLE001  a scene of another integration failed; the next schedules run
            _LOGGER.warning("Schedule %s: scene %s failed: %s", schedule["name"], scene["entity_id"], err)
