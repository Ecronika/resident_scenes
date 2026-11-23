"""Running scenes through the script helper (mode restart, spec 4.4).

The script helper owns order, delays and restarts. Each batch of steps between two
delays is one event action of the script; the batch itself is applied here with the
same state restore the built-in scenes use, so every skipped or failed device can be
named in the logbook.
"""

from __future__ import annotations

import asyncio
from functools import partial
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import Context, Event, HomeAssistant, State, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.script import SCRIPT_MODE_RESTART, Script
from homeassistant.helpers.state import async_reproduce_state

from .const import DOMAIN, EVENT_BATCH, EVENT_SKIPPED
from .model import allowed_entities, entity_area, music_favorites, step_key

_LOGGER = logging.getLogger(__name__)


def batches(sequence: list[dict[str, Any]]) -> list[tuple[float, list[dict[str, Any]]]]:
    """Split a sequence at its delay steps into (delay, entries) batches.

    Scene steps become {"scene_id", "name"}. Within a batch an entity keeps only its
    lowest entry; a trailing delay has no effect.
    """
    result: list[tuple[float, list[dict[str, Any]]]] = [(0, [])]
    for step in sequence:
        if step["type"] == "delay":
            result.append((step["seconds"], []))
        elif step["type"] == "scene":
            result[-1][1].append({"scene_id": step["scene_id"], "name": step["name"]})
        else:
            result[-1][1].extend(step["entries"])
    while len(result) > 1 and not result[-1][1]:
        result.pop()
    return [(delay, list({step_key(e): e for e in items}.values())) for delay, items in result]


class SceneRunner:
    """One script per scene version; running again restarts it.

    The steps are fixed when the script is built, so a run waiting in a delay finishes
    with the steps it started with, even if the scene is changed meanwhile.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, scenes: dict[str, dict[str, Any]]) -> None:
        """Initialize the runner."""
        self.hass = hass
        self.entry = entry
        self.scenes = scenes
        self._scripts: dict[str, tuple[int, Script, list]] = {}
        # context id -> scenes already started by that trigger; each runs once per trigger (review T1)
        self._chains: dict[str, set[str]] = {}
        # "all off" overtakes runs that began before it (spec 4.13): a counter orders starts and "all off"
        self._clock = 0
        self._started: dict[str, int] = {}  # context id of a trigger -> its start
        self._all_off: dict[str, int] = {}  # entity id -> the last "all off" that took it
        entry.async_on_unload(hass.bus.async_listen(EVENT_BATCH, self._batch))
        entry.async_on_unload(self._stop_all)

    @callback
    def _stop_all(self) -> None:
        for scene_id in list(self._scripts):
            self.async_forget(scene_id)

    @callback
    def async_forget(self, scene_id: str) -> None:
        """Stop and drop the script of a deleted scene."""
        if entry := self._scripts.pop(scene_id, None):
            self.hass.async_create_task(entry[1].async_stop())

    async def async_run(self, scene_id: str, context: Context | None, called: bool = False) -> None:
        """Start a scene; a run of the same scene still going is cancelled."""
        scene = self.scenes[scene_id]
        if not called:
            # every top-level run is its own trigger, also two runs of one automation (review U1)
            context = Context(
                user_id=context.user_id if context else None, parent_id=context.id if context else None
            )
            self._chains[context.id] = {scene_id}
            self._clock += 1
            self._started[context.id] = self._clock
            # shortcut: keeps the chains of the last 100 triggers, enough for delays of running scenes
            while len(self._chains) > 100:
                del self._chains[next(iter(self._chains))]
            while len(self._started) > 100:
                del self._started[next(iter(self._started))]
        version, script, _ = self._scripts.get(scene_id, (None, None, None))
        if script is None or version != scene["version"]:
            if script is not None:
                await script.async_stop()
            groups = batches(scene["sequence"])
            sequence: list[dict[str, Any]] = []
            for index, (delay, _) in enumerate(groups):
                if delay:
                    sequence.append({"delay": {"seconds": delay}})
                data = {"scene_id": scene_id, "version": scene["version"], "batch": index}
                sequence.append({"event": EVENT_BATCH, "event_data": data})
            script = Script(
                self.hass,
                cv.SCRIPT_SCHEMA(sequence),
                scene["name"],
                DOMAIN,
                script_mode=SCRIPT_MODE_RESTART,
                logger=_LOGGER,
            )
            self._scripts[scene_id] = (scene["version"], script, groups)
        # runs in the background: delays must not block scene.turn_on
        self.hass.async_create_background_task(
            script.async_run(context=context), f"{DOMAIN} {scene['name']}"
        )

    async def _batch(self, event: Event) -> None:
        data = event.data
        scene = self.scenes.get(data.get("scene_id", ""))
        version, _, groups = self._scripts.get(data.get("scene_id", ""), (None, None, []))
        # only our own scripts fire this event with their version (firing events needs admin)
        if scene is None or version != data.get("version"):
            return
        if not isinstance(index := data.get("batch"), int) or not 0 <= index < len(groups):
            return
        await self.async_apply(scene, groups[index][1], event.context)

    async def async_all_off(self, scene: dict[str, Any], steps: list[dict[str, Any]], context: Context | None) -> None:
        """Run "all off"; runs that began before it no longer switch these devices (spec 4.13)."""
        self._clock += 1
        for step in steps:
            self._all_off[step["entity_id"]] = self._clock
        await self.async_apply(scene, steps, context)

    async def async_apply(
        self, scene: dict[str, Any], steps: list[dict[str, Any]], context: Context | None
    ) -> None:
        """Apply steps together, skipping unreachable, missing, unreleased or moved devices.

        Also skipped: devices that "all off" took after this trigger began (spec 4.13).
        """
        hass = self.hass
        started = self._started.get(context.id) if context else None
        favorites = music_favorites(hass)
        allowed = allowed_entities(hass, self.entry)
        ent_reg = er.async_get(hass)
        transition = scene.get("transition")
        jobs: list[tuple[str, Any]] = []
        skipped: list[str] = []
        for step in steps:
            if "scene_id" in step:
                target = ent_reg.async_get_entity_id("scene", DOMAIN, step["scene_id"])
                chain = self._chains.setdefault(context.id if context else "", {scene["id"]})
                if step["scene_id"] not in self.scenes or target is None:
                    skipped.append(step["name"])  # scene missing
                elif step["scene_id"] in chain:
                    _LOGGER.warning("Scene %s: %s already runs for this trigger, skipped", scene["name"], step["name"])
                    skipped.append(step["name"])
                else:
                    chain.add(step["scene_id"])
                    jobs.append((step["name"], self.async_run(step["scene_id"], context, called=True)))
                continue
            entity_id = step["entity_id"]
            current = hass.states.get(entity_id)
            if (
                entity_id not in allowed
                or current is None
                or current.state == STATE_UNAVAILABLE
                # a device moved out of a room scene's room is skipped, the entry stays (spec 4.5)
                or (scene.get("area_id") and entity_area(hass, allowed[entity_id]) != scene["area_id"])
                or (started is not None and self._all_off.get(entity_id, 0) > started)
            ):
                skipped.append(entity_id)
            elif step.get("call"):
                call = hass.services.async_call(
                    "scene", "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True, context=context
                )
                jobs.append((entity_id, call))
            elif "music" in step:
                if step["music"] == "favorite" and step["favorite_id"] not in favorites:
                    skipped.append(entity_id)
                else:
                    jobs.append((entity_id, _play_music(hass, step, context)))
            else:
                options = {"transition": transition} if transition and current.domain == "light" else None
                state = State(entity_id, step["state"], step["attributes"])
                jobs.append(
                    (entity_id, async_reproduce_state(hass, [state], context=context, reproduce_options=options))
                )
        results = await asyncio.gather(*(job for _, job in jobs), return_exceptions=True)
        failed = []
        for (name, _), result in zip(jobs, results, strict=True):
            if isinstance(result, Exception):
                _LOGGER.warning("Scene %s: %s failed: %s", scene["name"], name, result)
                failed.append(name)
        if skipped or failed:
            hass.bus.async_fire(
                EVENT_SKIPPED,
                {"scene_id": scene["id"], "name": scene["name"], "entities": skipped, "failed": failed},
                context=context,
            )


async def _play_music(hass: HomeAssistant, step: dict[str, Any], context: Context | None) -> None:
    entity_id = step["entity_id"]
    call = partial(hass.services.async_call, "media_player", blocking=True, context=context)
    if step["music"] == "off":
        await call("media_stop", {ATTR_ENTITY_ID: entity_id})
        return
    if step["music"] == "tv_off":  # only from "all off" (spec 4.13), never stored in a scene
        await call("turn_off", {ATTR_ENTITY_ID: entity_id})
        return
    # volume first, then playback (spec 4.6)
    await call("volume_set", {ATTR_ENTITY_ID: entity_id, "volume_level": step["volume"]})
    if step["music"] == "on":
        await call("media_play", {ATTR_ENTITY_ID: entity_id})
    else:
        await call(
            "play_media",
            {
                ATTR_ENTITY_ID: entity_id,
                "media_content_id": step["favorite_id"],
                "media_content_type": "favorite_item_id",
            },
        )
