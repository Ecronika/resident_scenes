# Resident Scenes

Lets residents **without admin rights** create, edit, run and delete scenes from a dashboard card.
Scenes are stored by the integration (not in YAML), survive restarts, are part of every backup and appear as normal
`scene` entities for automations, schedules and voice.

Requires Home Assistant 2026.3 or later. The card and the settings are available in English and German.

Features (version 0.6):

- a scene editor in the card: every input is saved at once, "Done" ends editing, "New scene" creates a scene at once
- a scene is a sequence of steps: a trade (light, shading, climate, switches, fans, music, scenes) with its ticked
  devices, a call of a room scene, or a delay; the same trade and the same device may appear in several steps
  ("light on, 5 s, light off")
- devices from the current state, set to "off" or with values set directly (brightness, colour temperature, colour,
  position, tilt, mode, temperature); lights with a white channel of their own also have the state "White"; a
  setpoint is checked against the range and step of the thermostat; a transition time; running a scene again
  restarts it
- live adjustments per step for lights, shading, switches and fans: off on every opening, switching on takes over
  all devices of the step; leaving the editor restores nothing
- "All off in the house" per trade in house scenes, sorting by dragging
- house scenes calling room scenes; steps without a delay between them start together, and a called room scene
  runs beside the house scene, the house scene does not wait for it
- music steps for any released media player: off, or on with volume; with Sonos also a Sonos favorite with volume
  (favorites only, no free selection)
- favorite slots per room and for the house, each count set on its own; shown as square tiles in a grid that fits
  the card's width; a slot can be run from a push button (`resident_scenes.run_favorite`)
- "All off" per room: switches off the released lights of the room, and per room also music, TVs and switches;
  a scene that is still running does not switch them on again; "All on" is a scene of the room named in the card
- a device moved to another room drops out of the scenes of its old room (kept, named, back when the device returns)
  and moves along in house scenes
- scene images from an installer image library or uploaded and cropped in the card
- installer scenes (protected, content can be released to residents), loaded from a template
- edit right for every account that may control devices (not read-only accounts); the installer or a main user can
  withdraw it per account in the card; panel accounts have no edit right by default
- room rights per account: "All rooms" or a selection of rooms, and the right to run house scenes (default: all rooms,
  house scenes allowed); the permissions also as a card of their own for a settings page
- undo of the last edit (all inputs from opening the editor to leaving it, or until ten minutes without input); an
  input that changes nothing is no edit
- device release via a label; locks, alarm panels and configuration entities are never accepted
- logbook entries for every change, attributed to the account; repair issues for missing devices and scenes and
  for devices of a room scene that are now in another room.
  "scene created" is written once, under the first entity id (`scene.new_scene_1`); when the id then follows the name in
  the creating edit, that entry stays under the first id

## Installation

1. Home Assistant 2026.11 and later: Settings → Marketplace → custom repositories → add `Ecronika/resident_scenes`
   as *Integration*, install, restart Home Assistant. Before 2026.11: the same in HACS → Custom repositories.
2. Settings → Devices & services → Add integration → **Resident Scenes**. The label `resident_scenes` is created.
3. Give the label `resident_scenes` to the lights, covers, climate, switches, fans, media players and scenes residents
   may use (on the entity or its device).
4. For Sonos favorites enable the (disabled by default) Sonos favorites sensor.
5. Optional: put images (`.jpg`, `.png`, `.webp`) in `<config>/resident_scenes/`. An image named after an area id
   (e.g. `kitchen.jpg`) is the default image of that area. Library images: square, 640 × 640 pixels, JPEG, PNG or
   WebP, sRGB with 8 bits per channel, without location and time metadata (they are served unchanged). The card shows
   every scene image as a square and crops other formats from the middle; more pixels only cost loading time.

The card registers itself, no separate resource is needed.

## Card

```yaml
type: custom:resident-scenes-card
scope: area        # area or house
area: kitchen      # area id, only with scope: area
view: manage       # manage, list, favorites or rights
show_rights: true  # only with view: manage; false hides the button "Permissions"
columns: auto      # only with view: favorites; tiles per row: auto or a number
tile_size: 104     # only with view: favorites; edge of a tile in pixels (at least 80)
all_off: false     # only with view: favorites and scope: area; true shows the tile "All off"
all_on: tpl_kitchen_all_on  # only with view: favorites and scope: area; the scene of the tile "All on"
```

What the views are for:

- `manage` is the page "Scenes" of the house and of each room: list, scene view and editor. An account without the
  edit right gets the list and can run scenes.
- `favorites` shows the favorite slots in use as square tiles with image and name, for the home page and the room
  pages, also on wall panels. A tap runs the scene, and the tile shows for a moment that it ran.
- `list` is a list to run scenes, without scene view and editor: for pages where no account should reach the editor,
  and for the KNX scenes of a room.
- `rights` shows only the area "Permissions" and belongs on a settings page. It needs no `scope` and no `area`. An
  account that is neither main user nor admin sees nothing of this card.

The button "Permissions" stands in every `manage` card for main users and admins; `show_rights: false` hides it in
that card.

**Favorites grid:** a tile is at most `tile_size` pixels (default 104) and stands left-aligned, not stretched. With
`columns: auto` (default) a row holds as many tiles as fit; with a number, that many. If they do not fit, the tiles
shrink evenly down to 80 pixels, then a row holds fewer. Several rows are filled evenly: four as two and two, five as
three and two. With the defaults a card of 500 pixels shows four tiles in a row, a card of 360 pixels two and two.

**"All on" and "All off":** in a room card, `all_off: true` shows the tile "All off" (see the action
`resident_scenes.all_off`) and `all_on` names the scene of the tile "All on": the id of a scene of the room, for an
installer scene from a template `tpl_` and its key, or the entity id of a released scene of the room (e.g. a KNX
scene). The two tiles stand in a column of their own on the left, "All on" above "All off", as large as the
favorites; free space lies between this column and the favorites. If the named scene does not exist, the tile "All
on" is left out. The column also stands without any favorite.

Home page, the house favorites in one row as far as the width allows:

```yaml
type: custom:resident-scenes-card
scope: house
view: favorites
columns: auto
tile_size: 135
```

Room page, "All on" above "All off" and four favorites as two and two:

```yaml
type: custom:resident-scenes-card
scope: area
area: kitchen
view: favorites
columns: 2
all_off: true
all_on: tpl_kitchen_all_on
```

Settings page:

```yaml
type: custom:resident-scenes-card
view: rights
```

The view `manage` shows list and scene side by side from 600 pixels card width. In a view of type "Sections" a
section is narrower: give the card's section several columns, or use a panel view. With `view: manage` the card asks
for the full width of its section (`columns: full`), with `list`, `favorites` and `rights` for 12 columns.

## Actions

`resident_scenes.capture` takes over the current state of every device of the target scenes, e.g. from an
automation on a long press of a KNX push button. Targets may be scenes, areas, devices, labels or `all`. A device
that is missing, unreachable, no longer released or moved to another room keeps its stored value, and called room
scenes stay. Every scene found takes over the same state: with an area or `all` as target, a scene "Dark" in that
room afterwards switches the lights on as they are now. Automations run without a user and are allowed.

Without a user `capture` also overwrites an installer scene whose content is protected in the card: the protection
is for residents in the card, not for the installer's own automations. Point a long press only at scenes whose content
the resident may change. The card can take a capture back with "Undo", like any edit. Two examples for push buttons:

- **KNX scene in the actuator:** the push button calls the scene in the actuator directly; a long press stores the
  current state there with `knx.save_scene` of the KNX integration. The resident sees it in the card as a scene with
  the mark "KNX" (if it carries the label) and can run it, but not edit it.
- **Resident scene on a push button:** one automation runs the same scene entity on a short press (`scene.turn_on`)
  and takes over the current state on a long press (`resident_scenes.capture`):

```yaml
triggers:
  - {trigger: event, event_type: knx_event, event_data: {destination: "1/0/10"}, id: short}
  - {trigger: event, event_type: knx_event, event_data: {destination: "1/0/11"}, id: long}
actions:
  - if: [{condition: trigger, id: short}]
    then: [{action: scene.turn_on, target: {entity_id: scene.cooking}}]
    else: [{action: resident_scenes.capture, target: {entity_id: scene.cooking}}]
```

At hand-over, test it: dim a light to a brightness you can tell apart, press long, change the light, press short;
the light must come back to the brightness of the long press, and the card shows the new value.

`resident_scenes.all_off` with one or more areas (`area_id`) switches off all released lights of each room, e.g. from a
KNX push button. What else it takes is set per room by the installer (options, "All off" per room, or the template):
music (media players that are not TVs; playback stops), TVs (media players of device class `tv`; switched off) and
switches and sockets. A room without a setting switches only its lights, also a new room. Shading, climate, fans and
scenes are never taken. What counts is what belongs to the room and is released at the moment of the call, so a new
light is in without any setting. A call with a user needs the room right of every target room (not the edit right)
and switches under that account; calls without a user always run. Every run and every refused call is written to the
logbook with the room; an unreachable device is skipped and named there. There is no such action for the house: create
a house scene with "All in the house" off instead.

"All off" also wins over scenes that are still running: a run that began before it no longer switches the devices
"All off" took, also through a called room scene, e.g. a scene that waits 30 seconds and then switches a light on. These
entries are skipped and named in the logbook; the other steps of the scene go on, also in other rooms. A run that
begins after "All off" is not affected.

A media player counts as a TV when Home Assistant gives it the device class `tv`: from the entity registry, or from
its state, where the installer can set it with `customize` (`device_class: tv`). Every other media player counts as
music. To check at commissioning, open Developer tools → States, pick the player and look for `device_class: tv`
in its attributes.

`resident_scenes.run_favorite` runs the scene that lies on a favorite slot at the moment of the call, e.g. from a KNX
push button. Give either a room (`area_id`) or the house (`house: true`), and the slot (`slot`, counted from 1 as in
the card). An empty slot runs nothing and is written to the logbook with room and slot, so an empty button is found at
commissioning; a slot beyond the number of slots is refused. The rights are those of running the scene: a call with a
user needs the room right, for the house the house right; calls without a user always run. **Moving a favorite
re-binds the button:** when the resident puts another scene on the slot in the card, the next press runs that scene,
without a change to the automation or in the ETS. Tell the resident at hand-over. A long press cannot learn into a slot,
`capture` takes scenes only; for that put the button on a fixed scene.

```yaml
triggers:
  - {trigger: event, event_type: knx_event, event_data: {destination: "1/0/20"}}
actions:
  - action: resident_scenes.run_favorite
    data: {area_id: living_room, slot: 1}
```

**A device moved to another room:** in a room scene the entry stays stored, but it is skipped when the scene runs and
named in the logbook; the card marks it "In another room" and a repair issue names scene and device. When the device
returns to the room, the entry applies again and the issue goes. In a house scene the entry moves with its stored value
into a step of the new room right after its old step, so between the same delays, and the scene switches as before; a
following step of that room and trade before the next delay takes it, an entry of the device already there wins, and
a step left empty goes. A device that loses its room moves into a step "No room".

## Options

**Settings:** label, main users, accounts without edit right, panel accounts, panel accounts with edit right, limits
(scenes per area, house scenes, steps per scene, name length, favorite slots per area, delay, image size and count),
favorite slots for the house (empty: as many as per area, the default, so an update changes nothing) and the image
library folder.

**"All off" per room:** choose a room, then switch on what "All off" takes there besides the lights: music, TVs,
switches. Each room has its own setting; switching all three off returns the room to lights only. A deleted room
drops its setting.

**Load template:** a JSON or YAML file in the config folder with `options` and installer `scenes`:

```yaml
options:
  favorite_slots: 4
  house_favorite_slots: 8      # optional, up to 12
  all_off:                     # per area id: what "All off" takes besides the lights
    living_room: [music, tv, switch]
    kitchen: [switch]
scenes:
  - key: kitchen_cook          # stable key, a later template replaces the scene
    name: Cooking
    area_id: kitchen
    content_released: true     # residents may change the devices
    transition: 2
    sequence:
      - type: group
        domain: light
        entries:
          - {entity_id: light.kitchen, mode: set, values: {brightness: 200, color_temp_kelvin: 3000}}
      - {type: delay, seconds: 5}
      - type: group
        domain: cover
        entries:
          - {entity_id: cover.kitchen, mode: "off"}  # quoted, YAML reads off as false
          - {entity_id: cover.living, mode: set, values: {position: 20, tilt: 50}}
```

In house scenes a group step names its room with `area_id`, and `{type: scene, area_id: kitchen, scene_id: ...}`
calls a room scene. Templates of version 0.2 with `steps` are still accepted and converted. Options get the same
checks as the settings form. Room rights can be set too: `rooms` maps a user id to a list of area ids (an account not
listed has all rooms), `users_without_house` lists the user ids without the house right; an unknown room refuses the
template. The settings form does not show room rights, they are kept in the card. `all_off` maps an area id to a list
of `music`, `tv` and `switch`; an unknown room or another value refuses the template. A template that names `rooms`
or `all_off` replaces the stored value as a whole (a room not listed then switches only its lights); a template
without them keeps it. A template is loaded completely or not at all.
A template scene with the same `key` as a scene loaded before replaces it; the state before stays, so the card can
take the change back with "Undo".
For blinds with slats give `position` and `tilt`: Home Assistant opens the slats fully if only the position is set.

## Rights and security

Every command checks the logged-in account on the server. A scene only contains states of released devices and
music favorites; free actions, templates or scripts are never accepted. Note: Home Assistant itself lets every
user control every entity. This integration controls who changes scenes, not who switches devices.

Main users manage the edit right of residents and panels in the card. Admins and main users always may edit and are
not listed there.

**Room rights** (from 0.4.0): in "Permissions" the installer or a main user limits a resident or panel account to rooms,
as "All rooms" or a tree of floor and room (a tick at the floor sets all its rooms), and switches "may run house scenes".
A limited account sees, runs and (with edit right) changes only the scenes and favorite slots of its rooms; the card of
another room shows "No access to this room", the house card without the house right "No access to the house scenes",
and a card in the favorites view without the right stays invisible. With the house right it sees and runs the house
scenes and the house slots; a house scene runs fully, also in rooms the account has no right for, and shows its whole
sequence. Changing house scenes and house slots needs all
rooms. A new room is there at once for accounts with all rooms, for limited accounts only once ticked; a deleted room
drops its right. Calls without a user (automations, schedules, KNX push buttons) run every scene. A script or a
dashboard button that an account starts runs under that account and needs its room right for the scene. A refused call
leaves the scene entity unchanged. Changes apply at once,
also to an open editor (its next input is rejected), and are written to the logbook with both accounts. If Home
Assistant itself limits an account to some devices, a room counts only if the account may control each released device
of it. Room rights order scenes; they do not lock devices: Home Assistant still lets a user switch any entity it allows.

Images are delivered only to logged-in accounts or via signed, expiring URLs. Uploaded images are re-encoded on the
server without metadata (no location, no time) and stored in `.storage/resident_scenes_images/`.

## Removal

Remove the integration under Settings → Devices & services. Stored scenes stay in `.storage/resident_scenes.data`
and uploaded images in `.storage/resident_scenes_images/` until you delete them. The label `resident_scenes` and the
image library folder stay as well.

## Development

Tests need Linux (Home Assistant does not run on Windows):

```bash
pip install pytest-homeassistant-custom-component
pytest --cov=custom_components.resident_scenes
```

The card is written in `src/` and bundled with Lit into `custom_components/resident_scenes/frontend/`. The built file
is committed, so installing needs no build tools:

```bash
npm ci
npm run build
npm test
```
