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
from .model import allowed_entities, music_favorites

_LOGGER = logging.getLogger(__name__)


def batches(steps: list[dict[str, Any]]) -> list[tuple[float, list[dict[str, Any]]]]:
    """Split steps into (delay, steps) batches; a delay moves all following steps."""
    result: list[tuple[float, list[dict[str, Any]]]] = []
    for step in steps:
        if not result or step.get("delay"):
            result.append((step.get("delay", 0), []))
        result[-1][1].append(step)
    return result


class SceneRunner:
    """One script per scene version; running again restarts it."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, scenes: dict[str, dict[str, Any]]) -> None:
        """Initialize the runner."""
        self.hass = hass
        self.entry = entry
        self.scenes = scenes
        self._scripts: dict[str, tuple[int, Script]] = {}
        entry.async_on_unload(hass.bus.async_listen(EVENT_BATCH, self._batch))
        entry.async_on_unload(self._stop_all)

    @callback
    def _stop_all(self) -> None:
        for _, script in self._scripts.values():
            self.hass.async_create_task(script.async_stop())

    async def async_run(self, scene_id: str, context: Context | None) -> None:
        """Start a scene; a run of the same scene still going is cancelled."""
        scene = self.scenes[scene_id]
        version, script = self._scripts.get(scene_id, (None, None))
        if script is None or version != scene["version"]:
            if script is not None:
                await script.async_stop()
            sequence: list[dict[str, Any]] = []
            for index, (delay, _) in enumerate(batches(scene["steps"])):
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
            self._scripts[scene_id] = (scene["version"], script)
        # runs in the background: delays must not block scene.turn_on
        self.hass.async_create_background_task(
            script.async_run(context=context), f"{DOMAIN} {scene['name']}"
        )

    async def _batch(self, event: Event) -> None:
        data = event.data
        scene = self.scenes.get(data.get("scene_id", ""))
        # only our own scripts fire this event with the current version (firing events needs admin)
        if scene is None or scene["version"] != data.get("version"):
            return
        groups = batches(scene["steps"])
        if not isinstance(index := data.get("batch"), int) or not 0 <= index < len(groups):
            return
        await self.async_apply(scene, groups[index][1], event.context)

    async def async_apply(
        self, scene: dict[str, Any], steps: list[dict[str, Any]], context: Context | None
    ) -> None:
        """Apply steps together, skipping unreachable, missing or unreleased devices."""
        hass = self.hass
        favorites = music_favorites(hass)
        allowed = allowed_entities(hass, self.entry)
        ent_reg = er.async_get(hass)
        transition = scene.get("transition")
        jobs: list[tuple[str, Any]] = []
        skipped: list[str] = []
        for step in steps:
            if "scene_id" in step:
                target = ent_reg.async_get_entity_id("scene", DOMAIN, step["scene_id"])
                if step["scene_id"] not in self.scenes or target is None:
                    skipped.append(step["name"])  # scene missing
                else:
                    jobs.append((step["name"], self.async_run(step["scene_id"], context)))
                continue
            entity_id = step["entity_id"]
            current = hass.states.get(entity_id)
            if entity_id not in allowed or current is None or current.state == STATE_UNAVAILABLE:
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
