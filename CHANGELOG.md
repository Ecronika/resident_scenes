# Changelog

## 0.2.0

- Stage 2. Scenes run through the script helper (mode restart): delays per step, a transition time for lights.
- Values set directly: brightness, colour temperature, colour, position, tilt, mode and temperature.
- Live preview while editing with restore on cancel (on for room scenes, off for house scenes).
- House scenes call room scenes; a deleted one shows as "Scene missing" and is skipped.
- Installer scenes: protected, content can be released to residents; templates loaded in the options.
- Action `resident_scenes.capture` takes over the current state, e.g. on a long press of a KNX push button.
- Own scene images with crop; the server re-encodes them without metadata (limits 1600 px, 500 kB, 200 images).
- Main users manage the edit right of accounts in the card.
- Undo of the last change, including the image.
- Missing music favorites are marked; favorites only for players of the music system (Sonos).
- The card gets the scenes of its area only, steps only for the selected scene; device names via
  `hass.formatEntityName`.
- Repair issues for scenes with missing devices, scenes or favorites.
- Card rebuilt with Lit, bundled into one file. It keeps the last data when loading fails and retries with growing
  pauses, renews its subscription after a restart, reloads when visible at most every 5 minutes, buttons are 44 px.
- Image URLs are signed for the content user, one cache entry per image (review N1).
- Options keep the entered values on an error; a label name that cannot be created no longer stops the setup.
- Storage version 2 (migrated automatically).

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
