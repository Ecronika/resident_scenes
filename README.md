# Resident Scenes

Lets residents **without admin rights** create, edit, run and delete scenes from a dashboard card.
Scenes are stored by the integration (not in YAML), survive restarts, are part of every backup and appear as normal
`scene` entities for automations, schedules and voice.

Version 0.3 can:

- a scene editor where every input is saved at once, "Done" ends editing, "New scene"
  creates a scene at once
- a scene is a sequence of steps: a trade (light, shading, climate, switches, fans, music, scenes) with its ticked
  devices, a call of a room scene, or a delay; the same trade and the same device may appear in several steps
  ("light on, 5 s, light off")
- devices from the current state, set to "off" or with values set directly (brightness, colour temperature, colour,
  position, tilt, mode, temperature); a transition time; running a scene again restarts it
- live adjustments per step for lights, shading, switches and fans: off on every opening, switching on takes over
  all devices of the step; leaving the editor restores nothing
- "All off in the house" per trade in house scenes, sorting by dragging
- house scenes calling room scenes
- music steps for any released media player: off, or on with volume; with Sonos also a Sonos favorite with volume
  (favorites only, no free selection)
- favorite slots per room and for the house
- scene images from an installer image library or uploaded and cropped in the card
- installer scenes (protected, content can be released to residents), loaded from a template
- edit right for every account that may control devices (not read-only accounts); the installer or a main user can
  withdraw it per account in the card; panel accounts have no edit right by default
- undo of the last edit (all inputs from opening the editor to leaving it)
- device release via a label; locks, alarm panels and configuration entities are never accepted
- logbook entries for every change, attributed to the account; repair issues for missing devices and scenes

## Installation

1. Home Assistant 2026.11 and later: Settings → Marketplace → custom repositories → add `Ecronika/resident_scenes`
   as *Integration*, install, restart Home Assistant. Before 2026.11: the same in HACS → Custom repositories.
2. Settings → Devices & services → Add integration → **Resident Scenes**. The label `resident_scenes` is created.
3. Give the label `resident_scenes` to the lights, covers, climate, switches, fans, media players and scenes residents
   may use (on the entity or its device).
4. For Sonos favorites enable the (disabled by default) Sonos favorites sensor.
5. Optional: put images (`.jpg`, `.png`, `.webp`) in `<config>/resident_scenes/`. An image named after an area id
   (e.g. `kitchen.jpg`) is the default image of that area.

The card registers itself, no separate resource is needed.

## Card

```yaml
type: custom:resident-scenes-card
scope: area        # area or house
area: kitchen      # area id, only with scope: area
view: manage       # manage (list and editor), list (run only) or favorites (favorite slots as tiles)
```

The view `manage` shows list and scene side by side from 600 pixels card width. In a view of type "Sections" a
section is narrower: give the card's section the full width, or use a panel view. The card asks for the full width
of its section.

## Action

`resident_scenes.capture` takes over the current state of every device of the target scenes, e.g. from an
automation on a long press of a KNX push button. Targets may be scenes, areas, devices, labels or `all`. A device
that is missing, unreachable, no longer released or moved to another room keeps its stored value, and called room
scenes stay. Every scene found takes over the same state: with an area or `all` as target, a scene "Dark" in that
room afterwards switches the lights on as they are now. Automations run without a user and are allowed.

## Options

**Settings:** label, main users, accounts without edit right, panel accounts, panel accounts with edit right, limits
(scenes per area, house scenes, steps per scene, name length, favorite slots, delay, image size and count) and the
image library folder.

**Load template:** a JSON or YAML file in the config folder with `options` and installer `scenes`:

```yaml
options:
  favorite_slots: 4
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
checks as the settings form. A template is loaded completely or not at all.
For blinds with slats give `position` and `tilt`: Home Assistant opens the slats fully if only the position is set.

## Rights and security

Every command checks the logged-in account on the server. A scene only contains states of released devices and
music favorites; free actions, templates or scripts are never accepted. Note: Home Assistant itself lets every
user control every entity. This integration controls who changes scenes, not who switches devices.

Main users manage the edit right of residents and panels in the card. Admins and main users always may edit and are
not listed there.

Images are delivered only to logged-in accounts or via signed, expiring URLs. Uploaded images are re-encoded on the
server without metadata (no location, no time) and stored in `.storage/resident_scenes_images/`.

## Removal

Remove the integration under Settings → Devices & services. Stored scenes stay in `.storage/resident_scenes.data`
until you delete that file.

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
