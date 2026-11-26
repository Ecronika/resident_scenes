// Version 0.7.0, stage 5: the view "schedules" (spec 5.8), the schedules in the question before deleting a scene
// (spec 4.5) and the hint of "Alles aus" without a device (spec 4.13, review AD6).
// Run: node card_probe_0_7_0.cjs <path of the repository>   (after npm run build)
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, VERSION, tick, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const ALL = [0, 1, 2, 3, 4, 5, 6];
const sched = (o) => ({ id: "t1", name: "Außenlicht", active: true, trigger: "time", time: "23:00", offset: 0, weekdays: ALL,
  scene_id: "s1", version: 1, entity_id: "switch.aussenlicht", scene_entity_id: "scene.abend", scene_name: "Abend",
  area_id: "r1", issue: null, next_run: null, ...o });

// the mocked server of the schedule commands, beside the scene commands of world()
function server({ schedules = [], can_edit = true, full = false } = {}) {
  const s = world({ lang: "de" });
  s.hass.areas = { r1: { name: "Wohnzimmer" } };
  s.sched = { version: VERSION, can_edit, name_length: 30, max_offset: 180, limit: 20, full, schedules,
    scenes: [
      { scene_id: "s1", name: "Abend", area_id: "r1", kind: "resident" },
      { scene_id: "h1", name: "Abwesend", area_id: null, kind: "installer" },
      { entity_id: "scene.knx_licht", name: "KNX Licht", area_id: "r1", kind: "knx" },
    ] };
  const base = s.hass.callWS;
  s.hass.callWS = async (msg) => {
    const type = msg.type.split("/")[1];
    if (!type.startsWith("schedule")) return base(msg);
    s.calls.push(msg);
    if (s.fail[type]) { const err = s.fail[type]; delete s.fail[type]; throw err; }
    const d = s.sched;
    if (type === "schedules") return JSON.parse(JSON.stringify(d));
    const one = d.schedules.find((x) => x.id === msg.schedule_id);
    let result = {};
    if (type === "schedule_create") {
      const id = `n${d.schedules.length + 1}`;
      const choice = d.scenes.find((c) => (c.scene_id ?? c.entity_id) === (msg.scene_id ?? msg.entity_id));
      d.schedules.push(sched({ id, name: `${msg.name} 1`, active: false, time: "15:48", scene_id: msg.scene_id ?? null,
        scene_name: choice.name, area_id: choice.area_id }));
      result = { schedule_id: id, version: 1 };
    } else if (type === "schedule_update") {
      for (const k of ["name", "active", "trigger", "time", "offset", "weekdays"]) if (k in msg) one[k] = msg[k];
    } else if (type === "schedule_delete") {
      d.schedules = d.schedules.filter((x) => x !== one);
    } else if (type === "schedule_move") {
      d.schedules.splice(d.schedules.indexOf(one), 1);
      d.schedules.splice(msg.index, 0, one);
    }
    setTimeout(() => s.notify?.({ changed: true }));
    return result;
  };
  return s;
}

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);
const text = (node) => node.textContent.replace(/\s+/g, " ").trim();

(async () => {
  // ---------- 1 the view needs no area; an unknown view names the views ----------
  {
    const card = w.document.createElement("resident-scenes-card");
    card.setConfig({ view: "schedules" });
    assert.throws(() => card.setConfig({ view: "timers" }), /manage, list, favorites, rights or schedules/);
    same(card.getGridOptions().columns, "full", "two columns from 600 px need the full width");
    console.log("OK: view schedules without scope and area");
  }
  // ---------- 2 "Neuer Zeitplan" asks for the scene first; cancelled, no schedule ----------
  {
    const s = server();
    const card = await make(s, { view: "schedules" });
    const root = card.shadowRoot;
    assert.ok(text(root.querySelector(".card")).includes("Noch keine Zeitpläne"));
    await click(root, '[data-action="new-schedule"]');
    const dialog = q(root, ".dialog.picker");
    const heads = [...dialog.querySelectorAll("h3")].map(text);
    same(heads, ["Szene wählen", "Haus", "Wohnzimmer"], "by house and rooms");
    assert.ok(text(dialog).includes("Abwesend Errichter") && text(dialog).includes("KNX Licht KNX"), "with the mark of the kind");
    await click(root, '[data-action="picker-cancel"]');
    same(sent(s, "schedule_create").length, 0, "cancelled: no schedule");
    // chosen: created off with the scene, the editor is open
    await click(root, '[data-action="new-schedule"]');
    await click(root, '[data-action="choose-scene"][data-id="s1"]');
    await tick(40);
    same(sent(s, "schedule_create")[0].name, "Neuer Zeitplan");
    same(sent(s, "schedule_create")[0].scene_id, "s1");
    const row = q(root, ".row.sched");
    assert.ok(text(row).includes("Neuer Zeitplan 1") && text(row).includes("15:48 · täglich"));
    same(q(row, '[role="switch"]').getAttribute("aria-checked"), "false", "a new schedule is off");
    same(q(row, '[role="switch"]').getAttribute("aria-label"), "Zeitplan Neuer Zeitplan 1", "the switch names its schedule");
    assert.ok(q(root, '[data-action="schedule-done"]'), "its editor is open");
    await click(root, '[data-action="schedule-done"]');
    await tick(40);
    same(sent(s, "schedule_update").map((c) => c.active), [true], "Fertig switches it on");
    // a second one left with the back arrow stays off
    await click(root, '[data-action="new-schedule"]');
    await click(root, '[data-action="choose-scene"][data-id="scene.knx_licht"]');
    await tick(40);
    same(sent(s, "schedule_create")[1].entity_id, "scene.knx_licht", "a scene of another integration by its entity id");
    await click(root, '[data-action="schedule-back"]');
    same(sent(s, "schedule_update").length, 1, "left by the back arrow: stays off");
    // a third one whose switch was used in the edit keeps that state after Fertig
    await click(root, '[data-action="new-schedule"]');
    await click(root, '[data-action="choose-scene"][data-id="h1"]');
    await tick(40);
    await click(root, '.editor [role="switch"]');
    await click(root, '.editor [role="switch"]');
    await click(root, '[data-action="schedule-done"]');
    same(sent(s, "schedule_update").map((c) => c.active), [true, true, false], "Fertig keeps what the switch set");
    console.log("OK: new schedule asks for the scene, is off, Fertig switches it on unless its switch was used");
  }
  // ---------- 3 the short line and the detail ----------
  {
    const soon = new Date(Date.now() + 60000).toISOString();
    const s = server({ schedules: [
      sched({ weekdays: [0, 1, 2, 3, 6], next_run: soon }),
      sched({ id: "t2", name: "Rollos", trigger: "sunset", offset: -20 }),
      sched({ id: "t3", name: "Wecken", trigger: "sunrise", weekdays: [5, 6], active: false }),
      sched({ id: "t4", name: "Weg", issue: "scene_missing" }),
      sched({ id: "t5", name: "KNX", issue: "not_released", scene_id: null }),
    ] });
    const card = await make(s, { view: "schedules" });
    const root = card.shadowRoot;
    const lines = [...root.querySelectorAll(".row.sched")].map(text);
    assert.ok(lines[0].includes("23:00 · Mo Di Mi Do So"), lines[0]);
    assert.ok(lines[1].includes("Sonnenuntergang − 20 min · täglich"), lines[1]);
    assert.ok(lines[2].includes("Sonnenaufgang · Sa So"), lines[2]);
    assert.ok(lines[3].includes("Szene fehlt") && lines[4].includes("Szene nicht freigegeben"), "the marks in the list");
    await click(root, '[data-action="select-schedule"][data-id="t1"]');
    assert.match(text(q(root, '[data-field="next-run"]')), /^Nächster Lauf: (heute|morgen) \d\d:\d\d$/);
    assert.ok(text(q(root, ".col-detail")).includes("Wohnzimmer – Abend"), "the scene with room and name");
    await click(root, '[data-action="select-schedule"][data-id="t2"]');
    assert.ok(text(q(root, ".col-detail")).includes("20 min vor Sonnenuntergang"));
    await click(root, '[data-action="select-schedule"][data-id="t3"]');
    same(text(q(root, '[data-field="next-run"]')), "Ausgeschaltet, kein Lauf.", "off: the reason instead of the next run");
    await click(root, '[data-action="select-schedule"][data-id="t4"]');
    same(text(q(root, '[data-field="next-run"]')), "Szene fehlt");
    console.log("OK: short line, marks, next run and its reason");
  }
  // ---------- 4 the editor: trigger, offset, time, weekdays, scene ----------
  {
    const s = server({ schedules: [sched({ weekdays: [4] })] });
    const card = await make(s, { view: "schedules" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select-schedule"]');
    await click(root, '[data-action="edit-schedule"]');
    await click(root, '[data-action="hour-plus"]');
    same(sent(s, "schedule_update").at(-1).time, "00:00", "23 + 1 is 0");
    setValue(q(root, 'input[data-field="minute"]'), "75");
    await tick();
    assert.ok(text(q(root, ".editor .error")).includes("0–59"), "a refused input names the range");
    same(sent(s, "schedule_update").length, 1, "and is not sent");
    // the last day stays chosen
    await click(root, '[data-field="weekday"][data-day="4"]');
    same(sent(s, "schedule_update").length, 1);
    assert.ok(text(q(root, ".editor")).includes("Der letzte gewählte Tag lässt sich nicht abwählen."));
    await click(root, '[data-field="weekday"][data-day="5"]');
    same(sent(s, "schedule_update").at(-1).weekdays, [4, 5]);
    // sunset: five minutes per tap, locked at the limit, in words
    await click(root, '[data-field="trigger"] [data-value="sunset"]');
    same(sent(s, "schedule_update").at(-1).trigger, "sunset");
    await click(root, '[data-action="offset-minus"]');
    same(sent(s, "schedule_update").at(-1).offset, -5);
    same(text(q(root, '[data-field="offset-words"]')), "5 min vor Sonnenuntergang");
    setValue(q(root, 'input[data-field="offset"]'), "-180");
    await tick(40);
    assert.ok(q(root, '[data-action="offset-minus"]').disabled, "locked at −180");
    setValue(q(root, 'input[data-field="offset"]'), "0");
    await tick(40);
    same(text(q(root, '[data-field="offset-words"]')), "zum Sonnenuntergang");
    // the scene row opens the choice; the choice applies at once
    await click(root, '[data-action="change-scene"]');
    await click(root, '[data-action="choose-scene"][data-id="h1"]');
    same(sent(s, "schedule_update").at(-1).scene_id, "h1");
    // a refused input names the reason
    s.fail.schedule_update = { code: "no_access", message: "No access to this scene" };
    await click(root, '[data-field="weekday"][data-day="0"]');
    assert.ok(text(q(root, ".editor .error")).includes("Kein Zugriff"));
    console.log("OK: editor inputs are sent one field each, refusals are named, the last day stays");
  }
  // ---------- 5 order: arrow keys on the handle ----------
  {
    const s = server({ schedules: [sched(), sched({ id: "t2", name: "Rollos" })] });
    const card = await make(s, { view: "schedules" });
    const handle = q(card.shadowRoot, '.sched [data-action="drag"][data-id="t1"]');
    handle.dispatchEvent(new w.KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    await tick(60);
    same({ id: sent(s, "schedule_move")[0].schedule_id, index: sent(s, "schedule_move")[0].index }, { id: "t1", index: 1 });
    same([...card.shadowRoot.querySelectorAll(".row.sched")].map((r) => r.querySelector(".line").textContent), ["Rollos", "Außenlicht"]);
    console.log("OK: a schedule moves with the arrow keys of its handle");
  }
  // ---------- 6 without edit right: view only ----------
  {
    const s = server({ schedules: [sched()], can_edit: false });
    const card = await make(s, { view: "schedules" });
    const root = card.shadowRoot;
    assert.ok(!q(root, '[data-action="new-schedule"]') && !q(root, '[data-action="drag"]'));
    assert.ok(q(root, '[role="switch"]').disabled, "the switch shows the state only");
    await click(root, '[data-action="select-schedule"]');
    assert.ok(!q(root, '[data-action="edit-schedule"]'));
    console.log("OK: without edit right no New, no Edit, no handles, switches show the state");
  }
  // ---------- 7 limit reached ----------
  {
    const card = await make(server({ full: true }), { view: "schedules" });
    assert.ok(q(card.shadowRoot, '[data-action="new-schedule"]').disabled);
    assert.ok(text(card.shadowRoot.querySelector(".card")).includes("Höchstzahl an Zeitplänen erreicht. (20)"));
    console.log("OK: at the limit New is locked and names the limit");
  }
  // ---------- 8 deleted here and by another account ----------
  {
    const s = server({ schedules: [sched(), sched({ id: "t2", name: "Rollos" })] });
    const card = await make(s, { view: "schedules" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select-schedule"][data-id="t1"]');
    await click(root, '[data-action="edit-schedule"]');
    await click(root, '[data-action="ask-delete-schedule"]');
    assert.ok(text(q(root, ".dialog")).includes("Den Zeitplan „Außenlicht“ endgültig löschen?"));
    await click(root, '[data-action="delete-schedule"]');
    await tick(40);
    same(sent(s, "schedule_delete")[0].schedule_id, "t1");
    assert.ok(!q(root, ".error[role=alert]") && !q(root, ".col-detail h2"), "own deletion: closed without a hint");
    await click(root, '[data-action="select-schedule"][data-id="t2"]');
    s.sched.schedules = [];
    s.notify({ changed: true });
    await tick(40);
    assert.ok(text(q(root, ".error[role=alert]")).includes("Dieser Zeitplan wurde gelöscht"), "closed with a hint");
    console.log("OK: the detail closes after deleting; another account's deletion is named");
  }
  // ---------- 9 narrow card: list, detail, back ----------
  {
    const s = server({ schedules: [sched()] });
    const card = await make(s, { view: "schedules" });
    card._narrow = true;
    await click(card.shadowRoot, '[data-action="select-schedule"]');
    assert.ok(!q(card.shadowRoot, ".row.sched") && q(card.shadowRoot, '[data-field="next-run"]'), "one column: the detail");
    await click(card.shadowRoot, '[data-action="back"]');
    assert.ok(q(card.shadowRoot, ".row.sched"), "back to the list");
    console.log("OK: one column below 600 px, from the list to the detail and back");
  }
  // ---------- 10 deleting a scene names its schedules (spec 4.5) ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "house", view: "manage" });
    await click(card.shadowRoot, '[data-action="new"]');
    s.scene.used_in = { scenes: [], slots: [], schedules: ["Außenlicht"] };
    await card._loadDetail();
    await tick();
    await click(card.shadowRoot, '[data-action="ask-delete"]');
    assert.ok(text(q(card.shadowRoot, ".dialog")).includes("Verwendet in: Zeitplan Außenlicht"));
    console.log("OK: the question before deleting a scene names its schedules");
  }
  // ---------- 11 "Alles aus" without a device: the hint instead of the mark (AD6) ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true };
    const card = await make(s, { scope: "area", area: "r1", view: "favorites", all_off: true });
    s.hass.callService = async (...args) => (args[5] ? { context: {}, response: { devices: 0 } } : undefined);
    await click(card.shadowRoot, '[data-action="all-off"]');
    same(text(q(card.shadowRoot, '[role="alert"]')), "In diesem Raum ist nichts freigegeben.");
    assert.ok(!q(card.shadowRoot, ".tile.played"), "no mark");
    s.hass.callService = async () => ({ context: {}, response: { devices: 2 } });
    await click(card.shadowRoot, '[data-action="all-off"]');
    assert.ok(!q(card.shadowRoot, '[role="alert"]') && q(card.shadowRoot, ".tile.played"));
    console.log("OK: Alles aus without a released device says so instead of the mark");
  }
  console.log("card probe 0.7.0 passed");
  process.exit(0);
})().catch((err) => { console.error(err); process.exit(1); });
