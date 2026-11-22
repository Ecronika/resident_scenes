# Changelog

## 0.3.0

Stage 3: a new scene editor (functional spec draft 0.8).

- Every input is saved at once and is seen on every card; "Save" and "Cancel" are gone, "Done" and the back arrow
  end editing. Inputs reach the disk within 10 seconds, at once on shutdown.
- "New scene" creates "New scene 1" at once. The entity id follows the first rename once, then stays; a hand-changed
  entity id is left alone.
- A scene is a sequence of steps: a trade with its ticked devices, a call of a room scene, or a delay. The same trade
  and the same device may appear in several steps; inside one batch the lower entry wins. The delay per device is
  gone.
- Storage format 3: existing scenes and templates of 0.2 are converted without changing how they run.
- Live adjustments per step for lights, shading, switches and fans, off on every opening; switching on takes over all
  devices of the step. Nothing is restored when leaving. The preview with restore is gone.
- Undo and logbook per edit instead of per save; the edit that created a scene has nothing to undo.
- Two people editing the same scene: inputs on different entries both stay, the open editor takes over changes of
  others at once, an input on a removed step is refused and the card reloads.
- Card: list with a "Favorites" group and placeholder images, scene view with the uncropped image, short sequence,
  feedback of the play button; favorite slot dialog naming the scene on each slot and asking before replacing one;
  own switches, selects and image picker, sliders over the full row with their value, 44 px targets, usable at
  320 px; sorting by dragging only (auto-scroll, arrow keys on the handle); delay with minus, plus and direct input;
  delete dialog over the card; full width in the "Sections" view (findings V1 to V13 of the test installation).
- Fixed: two `scene.turn_on` calls of one automation run are two triggers, so a room scene called by both runs for
  each (U1); concurrent uploads can no longer pass the image count (U2).
- Removed WebSocket commands `save`, `preview` and `preview_end`; new input commands (see `websocket.py`).

## 0.2.2

Fixes from the review of 0.2.1 (T1 to T5).

- A scene can no longer call itself. `copy_from` is accepted for new scenes only, a call to the scene's own id is
  refused, and when running every scene runs at most once per trigger; a call that would repeat one is skipped and
  named in the logbook (T1).
- Live preview: each card keeps its own state before editing, also with two cards on one page (T2).
- The card no longer ends the preview when Home Assistant only moves it within the page (T3).
- A drag the browser cancels moves nothing (T4).
- Uploads are decoded one after another (T5).
- README: `capture` with an area or `all` gives every scene found the same state.

## 0.2.1

Fixes from the review of 0.2.0 (S1 to S14).

- `capture` keeps the stored value of devices that are missing, unreachable, no longer released or moved to another
  room, and keeps called room scenes. Before, one such device made the whole action fail (S1).
- A house scene whose called scene lost its room (room deleted) can be saved again. The call is marked "No room scene
  any more" and can be removed. Error messages name the scene, not its id (S2).
- Live preview: the state before editing is kept per editor, not per account. Leaving the editor, closing the app or
  reloading the panel counts as cancel; opening a new form restores the open one first (S3).
- Undo by a resident takes back only the content of an installer scene, never its name, room or image (S4).
- Uploads: only JPEG, PNG and WebP, at most 4096 pixels per side checked before decoding, requests up to 4 MB,
  damaged files refused with an error instead of a server error. The image limit counts the files on disk (S5).
- Templates: option values get the same checks as the settings form; scenes are loaded all or nothing (S6).
- `capture` accepts areas, devices, labels and `all` as target (S7).
- Main users are no longer listed under permissions; their right could not be taken anyway (S8).
- Repair issues appear as soon as a device is removed or the music favorites change, and go when the integration is
  removed (S9).
- A run waiting in a delay finishes with the steps it started with when the scene is changed meanwhile; the script of a
  deleted scene is stopped (S10).
- Card: order by dragging as well as by arrows (spec 5.7). Lights with colour and colour temperature switch between
  white and colour, saturation can be set. The hint "Not up to date" also shows before the first data arrived. A
  locked device ticked again gets its stored step back. Selects follow changes made by the card (S11, S12).
- `SECURITY.md` reviewed for 0.2.1; diagnostics count the main users instead of listing their ids (S13, S14).
- Not changed by decision: the play button for a music favorite in the preview (spec 5.4) is struck; the card still
  redraws on every state change (below 1 ms per pass measured in jsdom).

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
