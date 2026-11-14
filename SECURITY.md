# Security

Resident Scenes gives non-admin accounts functions that Home Assistant otherwise reserves for admins.
Please report vulnerabilities privately via GitHub: *Security → Report a vulnerability* in this repository.
Do not open a public issue for them.

## Review of version 0.1.0 (2026-11-15)

| Area | Check | Result |
|---|---|---|
| Rights | Every WebSocket command checks the logged-in account on the server (`can_edit`); system and deactivated accounts never edit | ok, tested |
| Rights | Edit right withdrawn during editing: the next save is rejected | ok, checked at save time |
| Input | Steps carry only entity id and mode; target states are read by the server, never sent by the client | ok |
| Input | Only entities with the label, in the allowed domains, not disabled, no configuration/diagnostic entities; locks and alarm panels never | ok, tested |
| Input | "keep" and "copy_from" re-check the release, so a device whose label was removed cannot stay in a re-saved scene | ok |
| Input | Music only from the Sonos favorites list, volume 0–1 | ok, tested |
| Input | Name length, scenes per scope, steps per scene limited; favorite scopes only house or existing areas | fixed in review (made-up scopes grew the storage), tested |
| Files | Image names without path parts or hidden files, allowed suffixes only, served from the library folder only | ok, tested |
| Files | Images only for logged-in accounts or via signed URLs (1 day) | ok, tested |
| Output | Card escapes every text (scene names, entity names, error codes) before rendering | ok, checked in the browser |
| Concurrency | Version check and change happen without awaiting in between, so two saves cannot both pass | ok |
| Privacy | Diagnostics contain counts, no user ids or names | ok, tested |

Known limit (by design, see README): Home Assistant lets every user control every entity. This integration
controls who changes scenes, not who switches devices.
