# Security

Resident Scenes gives non-admin accounts functions that Home Assistant otherwise reserves for admins.
Please report vulnerabilities privately via GitHub: *Security → Report a vulnerability* in this repository.
Do not open a public issue for them.

## Review of version 0.3.3 (2026-11-22)

| Area | Check | Result |
|---|---|---|
| Rights | Every WebSocket command and the upload check the logged-in account on the server (`can_edit`); system and deactivated accounts never edit, read-only accounts neither edit nor run | ok, tested |
| Rights | Edit right withdrawn during editing: the next input is rejected, the card leaves the editor | ok, tested |
| Rights | Installer scenes: residents change only released content; rename, move, image change and delete are refused, also through undo | ok, tested (review S4) |
| Rights | Main users change the edit right of residents and panels only; admins and main users are not listed and cannot be changed | ok, tested (review S8) |
| Rights | Room rights (0.4.0): list, scene, devices, every input, create, duplicate, delete, undo, favorite slots, `capture` and the upload check the room right of the scene's room, for house scenes the house right to see and all rooms to change; answers contain only what the account may see; no room at all also refuses the upload | ok, tested |
| Rights | `scene.turn_on` with a user needs the room right (house scenes: the house right) and is refused with `Unauthorized` and a logbook entry; the right is checked before the run is recorded, so a refused call leaves the scene state unchanged (0.4.1); a script or button started by an account carries that account; calls without a user always run; a house scene runs fully | ok, tested (review AB1, AB6) |
| Rights | `resident_scenes.all_off` (0.5.0): a call with a user needs the room right of every target room, like running a room scene, and is refused with `Unauthorized` and a logbook entry before anything switches; the edit right is not needed; calls without a user always run; it switches only released lights of the room, and released media players and switches only as the installer set for that room; shading, climate, fans and scenes never; unknown rooms are refused; the scope per room is set by the installer only (options, template), never in the card | ok, tested |
| Rights | `resident_scenes.run_favorite` (0.6.0): a room (`area_id`) or the house (`house: true`), exactly one, and a slot from 1 up to the number of slots, otherwise refused; a call with a user needs the right of running the scene (room right, house right) and is refused with `Unauthorized` and a logbook entry before anything runs; the scene then runs through `scene.turn_on` with the same checks and logbook; an empty slot runs nothing and is written to the logbook; calls without a user always run | ok, tested |
| Rights | "All off" and running scenes (0.6.0): a run that began before "All off" no longer switches the devices it took, also through a called room scene; the entries are skipped and written to the logbook | ok, tested |
| Rights | Control right per device instead of all entities: a room counts only if the account may control each released device of it; an account with control of some devices may edit there, a read-only account still not | ok, tested |
| Rights | Room right withdrawn during editing: the next input is rejected (`no_access`); a deleted room drops its right, also for a new room with the same id; room rights survive the installer's settings form; a template sets room rights with the checks of `set_rooms`, an unknown room refuses it whole (0.4.1); two quick changes in the card's room tree both apply (0.4.1) | ok, tested (review AB2, AB3) |
| Rights | `capture`: Home Assistant resolves the targets and checks control rights; the integration checks the edit right per scene; automations without a user are allowed (spec 4.9) | ok, tested |
| Input | Every input carries entity id, mode and checked values (the white mode only for lights that support it); target states are built by the server, never taken from the client; an input is checked on a copy of the scene and applied only if every check passes | ok, tested |
| Input | Only entities with the label, in the allowed domains, not disabled, no configuration or diagnostic entities; locks and alarm panels never | ok, tested |
| Input | A trade step takes devices of its room only, a step without a room devices without a room only; a stored entry of a moved device is marked "other room" and cannot be changed; from 0.6.0 a room scene skips it when running and a repair issue names it, a house scene moves it into a step of the new room | ok, tested (review X3, X10) |
| Input | "keep" keeps a stored step without checking the release again (rule B2): a device whose label was removed stays in the scene, is skipped when running and cannot be changed | by design, tested |
| Input | Called scenes: only room scenes are newly called, only by house scenes, never the scene itself, each at most once per scene; a stored call stays when its target loses its room; when running, each scene runs at most once per trigger, so a loop cannot repeat | ok, tested (review S2, T1) |
| Input | Live adjustments switch only released lights, covers, switches and fans of the step's room; nothing is restored when leaving (spec 5.4) | ok, tested |
| Input | Music only from the Sonos favorites list, volume 0–1 | ok, tested |
| Input | Name length, scenes per scope, steps per scene, delay and transition limited; favorite scopes only house or existing areas | ok, tested |
| Input | Template: only files inside the config folder, option values checked like the settings form, loaded all or nothing; `all_off` only known rooms and the values `music`, `tv`, `switch`; `house_favorite_slots` 1 to 12 (0.5.0) | ok, tested (review S6) |
| Files | Library image names without path parts or hidden files, allowed suffixes only, served from the library folder inside the config folder only | ok, tested |
| Files | Upload: JPEG, PNG and WebP only, at most 4096 pixels per side checked before decoding, request up to 4 MB, re-encoded as JPEG without metadata, count limited by the files on disk, one image decoded at a time | ok, tested (review S5, T5) |
| Files | Images only for logged-in accounts or via signed URLs (1 day, signed for the content user) | ok, tested |
| Output | Card renders every text through Lit templates (escaped); error details name devices and scenes, no ids | ok |
| Concurrency | Inputs address one step or entry by id and change it without awaiting in between; an image change reads the scene again after its file check (review W4); an input on a removed step is refused (`step_missing`); undo keeps its version check | ok, tested |
| Logbook | An edit id belongs to one account and ends after 10 minutes without input; it is stored with the scene, so a restart begins no second edit (review W3, W5); undo ends every open edit of the scene (review X9) | ok, tested |
| Privacy | Diagnostics contain counts; every option holding user ids is reduced to a count | ok, tested (review S14) |

Known limit (by design, see README): Home Assistant lets every user control every entity. This integration
controls who changes scenes, not who switches devices.
