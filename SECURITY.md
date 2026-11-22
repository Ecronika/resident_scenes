# Security

Resident Scenes gives non-admin accounts functions that Home Assistant otherwise reserves for admins.
Please report vulnerabilities privately via GitHub: *Security → Report a vulnerability* in this repository.
Do not open a public issue for them.

## Review of version 0.3.1 (2026-11-22)

| Area | Check | Result |
|---|---|---|
| Rights | Every WebSocket command and the upload check the logged-in account on the server (`can_edit`); system and deactivated accounts never edit, read-only accounts neither edit nor run | ok, tested |
| Rights | Edit right withdrawn during editing: the next input is rejected, the card leaves the editor | ok, tested |
| Rights | Installer scenes: residents change only released content; rename, move, image change and delete are refused, also through undo | ok, tested (review S4) |
| Rights | Main users change the edit right of residents and panels only; admins and main users are not listed and cannot be changed | ok, tested (review S8) |
| Rights | `capture`: Home Assistant resolves the targets and checks control rights; the integration checks the edit right per scene; automations without a user are allowed (spec 4.9) | ok, tested |
| Input | Every input carries entity id, mode and checked values; target states are built by the server, never taken from the client; an input is checked on a copy of the scene and applied only if every check passes | ok, tested |
| Input | Only entities with the label, in the allowed domains, not disabled, no configuration or diagnostic entities; locks and alarm panels never | ok, tested |
| Input | "keep" keeps a stored step without checking the release again (rule B2): a device whose label was removed stays in the scene, is skipped when running and cannot be changed | by design, tested |
| Input | Called scenes: only room scenes are newly called, only by house scenes, never the scene itself, each at most once per scene; a stored call stays when its target loses its room; when running, each scene runs at most once per trigger, so a loop cannot repeat | ok, tested (review S2, T1) |
| Input | Live adjustments switch only released lights, covers, switches and fans of the step's room; nothing is restored when leaving (spec 5.4) | ok, tested |
| Input | Music only from the Sonos favorites list, volume 0–1 | ok, tested |
| Input | Name length, scenes per scope, steps per scene, delay and transition limited; favorite scopes only house or existing areas | ok, tested |
| Input | Template: only files inside the config folder, option values checked like the settings form, loaded all or nothing | ok, tested (review S6) |
| Files | Library image names without path parts or hidden files, allowed suffixes only, served from the library folder inside the config folder only | ok, tested |
| Files | Upload: JPEG, PNG and WebP only, at most 4096 pixels per side checked before decoding, request up to 4 MB, re-encoded as JPEG without metadata, count limited by the files on disk, one image decoded at a time | ok, tested (review S5, T5) |
| Files | Images only for logged-in accounts or via signed URLs (1 day, signed for the content user) | ok, tested |
| Output | Card renders every text through Lit templates (escaped); error details name devices and scenes, no ids | ok |
| Concurrency | Inputs address one step or entry by id and change it without awaiting in between; an image change reads the scene again after its file check (review W4); an input on a removed step is refused (`step_missing`); undo keeps its version check | ok, tested |
| Logbook | An edit id belongs to one account and ends after 10 minutes without input; it is stored with the scene, so a restart begins no second edit (review W3, W5) | ok, tested |
| Privacy | Diagnostics contain counts; every option holding user ids is reduced to a count | ok, tested (review S14) |

Known limit (by design, see README): Home Assistant lets every user control every entity. This integration
controls who changes scenes, not who switches devices.
