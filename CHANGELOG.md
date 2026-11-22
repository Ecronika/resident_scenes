# Changelog

## 0.4.1

Fixes of the 0.4.0 review (Nachbesserung 4a, draft 0.16 of the functional spec).

- `scene.turn_on` without the room right no longer marks the scene as run: the entity derives from `BaseScene` and
  checks the right before it records the run, so a refused call leaves the scene state unchanged and no state trigger
  fires (AB1, spec 4.4).
- Templates accept `rooms` (user id to a list of known area ids) and `users_without_house` (list of user ids), checked
  like `set_rooms`; an unknown room refuses the whole template. The settings form still does not show them (AB2, 4.1).
- Room tree in the card: a tap applies at once to the card's own state, and the calls go out one after the other, each
  built from the state chosen last, so two quick taps both apply (AB3).
- Favorites view without the right stays invisible, like one without a slot in use; the house card without the house
  right says "No access to the house scenes" (AB4, spec 4.7, 5.5, 5.6).
- README: a script or button started by an account runs under that account and needs its room right (AB6).
- Tests collect events with `async_capture_events`, so their order is fixed (AB7); the 0.4.0 review files
  `test_review_0_4_0.py` and `card_probe_0_4_0_review.cjs` are added with the findings marked fixed. A house scene
  still shows its whole sequence (AB5, as decided).

## 0.4.0

Stage 4 of the functional spec: room rights per account (draft 0.13, sections 3, 4.4, 4.7, 5.5, 5.6).

- Room rights: per account "All rooms" or a selection, and the right "house scenes"; default all rooms and on, so an
  update changes nothing (no storage change, missing options mean all rooms). Stored in the options like the edit right.
- Checks in every command: list, scene, devices, inputs, create, duplicate, delete, undo, favorite slots, `capture` and
  the upload; a limited account gets only what it may see. Changing house scenes and house slots needs all rooms.
- Running: `scene.turn_on` with a user needs the room right of the scene, a house scene the house right; refused calls
  raise `Unauthorized` and are written to the logbook. Calls without a user always run; a house scene runs fully.
- Control right per device: Home Assistant's control right is checked per released device instead of for all entities;
  a room counts only if the account may control each released device of it.
- A deleted room drops its right (also when deleted while Home Assistant was stopped); a new room is not granted to
  limited accounts.
- Card: "Permissions" shows per account "All rooms" or a tree of floor and room and "may run house scenes" (new command
  `set_rooms`, the rights list carries floors and rooms); a room card without right shows only "No access to this room";
  the house card of a limited account runs scenes without edit, new scene and heart; a right withdrawn while editing
  rejects the next input, shows a hint and then the no-access hint.
- Logbook: every change of room rights with the account changed and the account that made it.
- The installer's settings form keeps the room rights.
- Tests: `test_stage4.py`, card probe `card_probe_0_4_0.cjs`; the 0.3.5 review files `test_review_0_3_5.py` and
  `card_probe_0_3_5.cjs` are added.

## 0.3.5

Fixes of the 0.3.4 review.

- Scene view in narrow cards: the buttons take a full-width row of their own under image and name, so the head stays
  at 80 + 8 + 44 pixels (two button rows at most 184) and needs no height limit; from a column of 600 pixels image,
  name and buttons stay in one row of at most 120 pixels (AA1, spec 5.2).
- Light with a white channel of its own and no stored colour, off: the card shows "White" as the default and sends
  `white` with the first input instead of an orange (AA2).
- List: the heading "Scenes" is shown only when rows follow (AA3).
- Server: an input that changes nothing is accepted without beginning an edit; no new version, no logbook entry, the
  state for "Undo" stays (AA4, spec 4.5).
- Edit mode: the image button no longer has a gap under the image; the name in the head bar stays on one line and is
  shortened, the full name is in the field below (AA5).

## 0.3.4

Fixes of the 0.3.3 review and draft 0.12 of the functional spec.

- Entity id: the creating edit also ends when it went idle; an input with its edit id after ten minutes begins a new
  edit, and the id no longer follows the name (Z1, spec 4.3, 4.5).
- Light in its own white mode (`white`): the card shows a third state "White" without sliders and sends only the
  brightness; the server keeps the mode on a new brightness and stores it when "White" is chosen. The colour shown is
  sent along only when the source has no colour mode at all. Capabilities name `white_mode` (Z2).
- Logbook: "scene created" is written once, under the first entity id; it is no longer repeated when the id follows the
  name (Z3, spec 4.10). The README says so.
- The row of a step is measured again only when its devices, the language or the width change (Z4).
- The list of music favorites closes on a press beside it; the setpoint is checked against the step of the thermostat,
  "Temperature not on the step of the device: 0.5 °C" (Z5).
- Scene image after draft 0.12: no image or placeholder in the rows of the list; in the scene view a square of 80
  pixels left of the name, the buttons beside it or in the line below, the head at most 200 pixels high (120 from a
  column of 600 pixels); in edit mode the head image carries a pencil and opens the image choice, the field "Image"
  with its own preview is gone; square tiles in the view "Favorites" and in the image choice, the name on a gradient;
  crop and upload at 640 × 640. Stored images stay unchanged. The README names format and size for library images
  (Z6, spec 4.8, 5.2).

## 0.3.3

Fixes of the 0.3.2 review.

- Light without a stored colour (off, or not ticked while off): "On" and the first input store the colour
  temperature or colour the editor shows; with a stored colour an input still changes only its own value (Y1, spec
  4.5, 5.2).
- Delay at 320 pixels card width: handle, minus, field, plus and remove stay in one line; "no effect" is shown below
  the row (Y2).
- The row of a step names as many devices as fully fit, the rest as "+ 3 more"; if not even the first fits, only
  "3 devices". Without a layout (hidden card) it falls back to two devices (Y3, spec 5.2).
- Thermostat: the card checks the setpoint against the range of the device and names it, "Temperature out of range:
  7–30 °C", also when the server refuses it; the field shows the value in the notation of the language (Y4).
- Music favorites: a list of the card instead of the select of the browser, opened on demand, with arrow keys and
  Escape; it shows the stored favorite, so a refused choice reverts (Y5, spec 5.7).
- Entity id in the creating edit: a rename whose slug gives the own id keeps it, and an edit of another account no
  longer ends the following; only the end of the creator's edit does (Y6, spec 4.3).
- Logbook: when the entity id follows the name, "scene created" is written again under the new id, so it appears in
  the logbook of the named scene (Y7).
- Hue of a light colour stored as RGBWW mixes the white channels in like Home Assistant, with the kelvin range of the
  light (Y8).

## 0.3.2

Fixes of the 0.3.1 review and draft 0.9 of the functional spec.

- "All in the house off" also switches off released devices without a room, in a step "Without room" (X1).
- The card asks for the full width of its section in the view `manage` (X2).
- A step without a room takes devices without a room only; an entry whose device got a room is marked "In another
  room" on the server and in the card, also in the sequence, and cannot be changed (X3, X10).
- Delay field: an input that is not a whole number from 1 to the limit shows the stored value again with the reason;
  "2.5" is no longer rounded (X4).
- Questions take the focus on the safe answer whenever their content changes, Tab stays inside, and the card behind
  takes no input; the delete question names the scene (X5, spec 5.3, 5.7).
- Music: "Favorite" is offered only when favorites exist, otherwise a hint names the reason (X6); the favorites are
  one list instead of a button each (spec 5.2).
- Pressing the marked choice of an unticked device ticks it (X7).
- Thermostat: operation modes in the language of the account, the setpoint with the unit of the installation and in
  a field without arrows of the browser (X8).
- Undo ends the open edits of the scene, so the next input begins a new edit (X9).
- Light colour: the card gets hue and saturation for a colour stored as RGB, RGBW, RGBWW or xy, and an input changes
  only its own value; changing the brightness keeps the stored colour, white channels included (X11, acceptance
  "Farbe bleibt").
- The entity id follows the name only in the edit that created the scene, there at every rename (spec 4.3).
- Card: a step takes at most two lines, the devices as "+ 3 more" beyond two; a delay at the end says "no effect";
  after undo the card says that the previous state applies again; moving a step with the arrow keys is announced to
  screen readers (spec 5.2, 5.3, 5.7).

## 0.3.1

Fixes of the 0.3.0 review.

- A deleted room no longer locks its scenes: its trade steps become steps without a room and stay changeable, also
  after undo (W1).
- House scenes take steps "Without room" for released devices that have no room (W2).
- An edit belongs to one account and ends after 10 minutes without input, so every edit is in the logbook with its
  account and undo never reaches back days (W3). The edit is stored with the scene and survives a restart (W5).
- An input made while an image change checks its file is no longer lost (W4).
- Inputs reach the disk within 10 seconds of the first unsaved input, also while editing goes on (W6).
- Delays take whole seconds only; plus and minus count on from the value sent last (W7, V16).
- Card: a step with more than two devices shows their count (V6); the mark of the selected scene is visible (V14);
  questions take the focus on the safe answer, Escape gives that answer and the focus goes back (V15); every play
  button names its scene (V17).

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
