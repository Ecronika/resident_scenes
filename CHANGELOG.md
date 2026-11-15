# Changelog

## 0.1.2

- Minimum Home Assistant version lowered to 2026.3 (first version reading the `brand/` icons). The tests also run
  against Home Assistant 2026.3.1.

## 0.1.1

- Scenes of a deleted area become house scenes (name gets a suffix if taken); the area's favorite slots go.
- Renamed entity ids are followed in all scenes. A device without the label stays in the scene, is skipped when the
  scene runs and can keep its stored value; it can no longer be captured or changed.
- Area scenes accept only devices of their area.
- Failed steps are written to the logbook with the device name.
- Read-only accounts may no longer change scenes.
- Signed image URLs are reused for 12 hours, so browsers cache the images.
- Image library folder must lie inside the config folder; image names with `#`, `?` or `%` are ignored.
- The options can be saved again after an account in a rights list was removed.
- The label is created on setup if missing.
- Card: "All off" per group and per trade in the house, reload after reconnect / when visible / every 6 hours, keeps
  focus while editing, names the device in errors, tells "not released", "device missing" and "not reachable" apart,
  disables "New scene" at the limit, checks taken names before saving, tells when the edit right was withdrawn.
- Entity id changes on Home Assistant 2026.11 update the scene entity in place.

## 0.1.0

- Stage 1: room and house scenes, music steps, favorite slots, image library, rights, logbook.
