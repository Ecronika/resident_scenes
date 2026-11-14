# Resident Scenes

Lets residents **without admin rights** create, edit, run and delete scenes from a dashboard card.
Scenes are stored by the integration (not in YAML), survive restarts, are part of every backup and appear as normal
`scene` entities for automations, schedules and voice.

Version 0.1 (stage 1) can:

- room scenes and house scenes, created from the current state or with devices set to "off" without switching them
- music steps for Sonos: off, on with volume, or a Sonos favorite with volume (favorites only, no free selection)
- favorite slots per room and for the house
- scene images from an installer image library
- edit right for every account by default; the installer can withdraw it per account; panel accounts have no edit right by default
- device release via a label; locks, alarm panels and configuration entities are never accepted
- logbook entries for every change, attributed to the account

Not yet: values set directly (brightness, colour, position), delays, live preview, house scenes calling room scenes,
installer scenes, own image upload, rights managed by main users in the card, undo, repairs. Music only with Sonos.

## Installation

1. Home Assistant 2026.11 and later: Settings → Marketplace → custom repositories → add `Ecronika/resident_scenes`
   as *Integration*, install, restart Home Assistant. Before 2026.11: the same in HACS → Custom repositories.
2. Settings → Devices & services → Add integration → **Resident Scenes**.
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

## Options

Label, accounts without edit right, panel accounts, panel accounts with edit right, limits (scenes per area,
house scenes, steps per scene, name length, favorite slots) and the image library folder.

## Rights and security

Every command checks the logged-in account on the server. A scene only contains states of released devices and
music favorites; free actions, templates or scripts are never accepted. Note: Home Assistant itself lets every
user control every entity. This integration controls who changes scenes, not who switches devices.

Images are delivered only to logged-in accounts or via signed, expiring URLs.

## Removal

Remove the integration under Settings → Devices & services. Stored scenes stay in `.storage/resident_scenes.data`
until you delete that file.

## Development

Tests need Linux (Home Assistant does not run on Windows):

```bash
pip install pytest-homeassistant-custom-component
pytest --cov=custom_components.resident_scenes
```
