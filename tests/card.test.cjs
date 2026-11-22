// Card tests in jsdom against the built file. Run: npm ci && npm run build && npm test
const assert = require("node:assert");
const { w, tick, fire, setValue, same, world, make, types, last, q, click } = require("./world.cjs");

(async () => {
  // ---------- house card: create, edit at once, Fertig ----------
  const s = world({ lang: "en" });
  const card = await make(s, { scope: "house", view: "manage" });
  const root = card.shadowRoot;
  assert.strictEqual(s.calls[0].scope, "_house", "the list is asked for the card scope only");
  same(card.getGridOptions(), { columns: "full", min_columns: 6, rows: "auto" }, "V1, X2: full width in sections view");

  // "New scene" creates at once and opens edit mode, no form to save
  await click(root, '[data-action="new"]');
  const create = last(s, "create");
  assert.strictEqual(create.area_id, null);
  assert.strictEqual(create.name, "New scene");
  assert.ok(create.edit, "an edit id is sent");
  assert.strictEqual(q(root, '[data-field="name"]').value, "New scene 1");
  assert.ok(!q(root, '[data-action="save"]') && !q(root, '[data-action="cancel"]'), "no save, no cancel");
  assert.ok(root.textContent.includes("No steps yet."), "V8: empty sequence named");

  // an input is sent at once with scene_id and edit; a server notification keeps focus and typed value
  const name = q(root, '[data-field="name"]');
  name.focus();
  setValue(name, "Away", "input");
  s.notify({ changed: true });
  await tick();
  assert.strictEqual(root.activeElement, name, "name field keeps focus after a server notification");
  assert.strictEqual(q(root, '[data-field="name"]').value, "Away");
  fire(name, "change");
  await tick();
  same(last(s, "update"), { type: "resident_scenes/update", scene_id: "n1", edit: create.edit, name: "Away" });

  // V12: a taken name shows its error at the field, the stored name comes back
  s.fail.update = { code: "name_exists", message: "name_exists: Away" };
  setValue(q(root, '[data-field="name"]'), "Cook");
  await tick();
  assert.ok(q(root, ".field .error").textContent.includes("taken"), "error at the name field");
  assert.strictEqual(q(root, '[data-field="name"]').value, "Away", "stored name shown again");

  // house: "All in the house off" per trade, one input each (B3: 60 light circuits, 30 blinds)
  const trades = [...root.querySelectorAll('[data-action="house-off"]')].map((b) => b.dataset.domain);
  same(trades, ["light", "cover"]);
  await click(root, '[data-action="house-off"][data-domain="light"]');
  same(last(s, "house_off"), { type: "resident_scenes/house_off", scene_id: "n1", edit: create.edit, domain: "light" });

  // add step in a house scene: room, then trade; the new step opens
  await click(root, '[data-action="add-step"]');
  await click(root, '[data-action="pick-room"][data-id="r0"]');
  await click(root, '[data-action="pick-domain"][data-domain="light"]');
  same(last(s, "add_step"), { type: "resident_scenes/add_step", scene_id: "n1", edit: create.edit, step_type: "group", domain: "light", area_id: "r0" });
  assert.ok(q(root, '[data-action="close-step"]'), "the new step is open");
  assert.ok(root.textContent.includes("Room · light.r0_0"), "device names come from formatEntityName");

  // live adjustments are off on opening; switching them on captures all devices
  const liveSwitch = () => q(root, '[data-field="live"]');
  assert.strictEqual(liveSwitch().getAttribute("aria-checked"), "false");
  await click(root, '[data-field="pick"][data-entity="light.r0_0"]');
  same(last(s, "set_entry"), { type: "resident_scenes/set_entry", scene_id: "n1", edit: create.edit, step_id: "st1",
    entity_id: "light.r0_0", mode: "capture", live: false });
  assert.strictEqual(q(root, '[data-field="pick"][data-entity="light.r0_0"]').getAttribute("aria-checked"), "true");
  liveSwitch().click();
  await tick();
  same(last(s, "set_all"), { type: "resident_scenes/set_all", scene_id: "n1", edit: create.edit, step_id: "st1", mode: "capture", live: true });

  // slider acts on release, with the live flag; dragging alone sends nothing
  const before = s.calls.length;
  const slider = q(root, '[data-field="brightness"][data-entity="light.r0_1"]');
  setValue(slider, "60", "input");
  await tick();
  assert.strictEqual(s.calls.length, before, "nothing sent while dragging");
  assert.ok(slider.closest(".slider").querySelector("output").textContent.includes("60 %"), "V5: value as number");
  fire(slider, "change");
  await tick();
  same(last(s, "set_entry"), { type: "resident_scenes/set_entry", scene_id: "n1", edit: create.edit, step_id: "st1",
    entity_id: "light.r0_1", live: true, mode: "set", values: { brightness: 153 } }); // the colour stays on the server (X11)
  await click(root, '[data-action="all-off"]');
  same(last(s, "set_all"), { type: "resident_scenes/set_all", scene_id: "n1", edit: create.edit, step_id: "st1", mode: "off", live: true });

  // back to the sequence and open again: live is off again
  await click(root, '[data-action="close-step"]');
  await click(root, '[data-action="open"][data-id="st1"]');
  assert.strictEqual(liveSwitch().getAttribute("aria-checked"), "false", "live off on every opening");
  await click(root, '[data-action="close-step"]');

  // add a room scene call in a house scene: room, then "Scenes"
  s.roomScenes = [{ id: "rs1", name: "Kochen", area_id: "r1" }];
  card._load(); // devices reload with the room scenes
  await tick();
  await click(root, '[data-action="add-step"]');
  await click(root, '[data-action="pick-room"][data-id="r1"]');
  await click(root, '[data-action="pick-domain"][data-domain="room_scene"]');
  await click(root, '[data-action="pick-scene"][data-id="rs1"]');
  same(last(s, "add_step"), { type: "resident_scenes/add_step", scene_id: "n1", edit: create.edit, step_type: "scene", target: "rs1", area_id: "r1" });
  assert.match(root.textContent, /r1 – Scenes\s+Kochen/, "scene step in short form, two lines (spec 5.2)");

  // delay: starts at 5 s, plus, minus, direct input
  await click(root, '[data-action="add-delay"]');
  same(last(s, "add_step"), { type: "resident_scenes/add_step", scene_id: "n1", edit: create.edit, step_type: "delay" });
  await click(root, '[data-action="delay-plus"]');
  assert.strictEqual(last(s, "set_delay").seconds, 6);
  await click(root, '[data-action="delay-minus"]');
  assert.strictEqual(last(s, "set_delay").seconds, 5);
  setValue(q(root, '[data-field="delay"]'), "30");
  await tick();
  same(last(s, "set_delay"), { type: "resident_scenes/set_delay", scene_id: "n1", edit: create.edit, step_id: "st3", seconds: 30 });
  assert.strictEqual(q(root, '[data-field="delay"]').value, "30");

  // step_missing: someone removed the step meanwhile; the card reloads the scene and says so
  s.scene.sequence = s.scene.sequence.filter((x) => x.id !== "st2");
  const scenes = types(s).filter((t) => t === "scene").length;
  await click(root, '[data-action="remove-step"][data-id="st2"]');
  assert.ok(types(s).filter((t) => t === "scene").length > scenes, "scene reloaded");
  assert.ok(root.textContent.includes("removed meanwhile"));
  assert.ok(!q(root, '[data-action="remove-step"][data-id="st2"]'), "the stored sequence is shown");

  // lost connection locks the editor with a note
  s.listeners.disconnected();
  await tick();
  assert.ok(q(root, ".editor").hasAttribute("inert"));
  assert.ok(root.textContent.includes("Connection lost"));
  s.listeners.ready();
  await tick();
  assert.ok(!q(root, ".editor").hasAttribute("inert"));

  // Fertig sends nothing and shows the scene
  const sent = s.calls.length;
  await click(root, '[data-action="done"]');
  assert.ok(s.calls.slice(sent).every((c) => ["resident_scenes/scene", "resident_scenes/list"].includes(c.type)), "Fertig sends no input");
  assert.ok(q(root, '[data-action="edit"]'), "back in the scene view");
  assert.ok(root.textContent.includes("+ 30 s"), "delay in short form");

  // B4: reload after a reconnect
  const lists = () => types(s).filter((t) => t === "list").length;
  const n = lists();
  s.listeners.ready();
  await tick();
  assert.strictEqual(lists(), n + 1, "card reloads after the connection is back");

  // N7: the withdrawn-rights notice goes once the right is back; rights hide edit and heart
  s.data = { ...s.data, can_edit: false };
  s.listeners.ready();
  await tick();
  assert.ok(!q(root, '[data-action="edit"]') && !q(root, '[data-action="heart"]') && !q(root, '[data-action="new"]'));
  s.data = { ...s.data, can_edit: true };
  s.listeners.ready();
  await tick();
  await click(root, '[data-action="edit"]');
  s.data = { ...s.data, can_edit: false };
  s.listeners.ready();
  await tick();
  assert.ok(root.textContent.includes("withdrawn"));
  assert.ok(!q(root, '[data-action="done"]'), "editor closed");
  s.data = { ...s.data, can_edit: true };
  s.listeners.ready();
  await tick();
  assert.ok(!root.textContent.includes("withdrawn"), "notice cleared when can_edit is true again");

  // N2: a failed load keeps the last data and retries
  s.failList = 1;
  s.listeners.ready();
  await tick();
  assert.ok(root.textContent.includes("Away"), "last data stays visible");
  assert.ok(root.textContent.includes("retrying"));
  assert.strictEqual(card._backoff, 2);
  card._load();
  await tick();
  assert.ok(!root.textContent.includes("retrying"));

  // N3: the reason of a marked entry is named in the scene view
  s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r1",
    entries: [{ entity_id: "light.r1_0", state: "on", attributes: { brightness: 255 }, issue: "other_area" }] }];
  s.notify({});
  await tick();
  assert.ok(root.textContent.includes("In another room"));

  // V9: play gives short feedback, a failure is reported
  await click(root, '.head [data-action="play"]');
  assert.ok(q(root, '.head [data-action="play"]').textContent.includes("Played"));
  s.hass.callService = async () => { throw new Error("x"); };
  await click(root, '.head [data-action="play"]');
  assert.ok(root.textContent.includes("could not be played"));

  // K6: limit reached disables "New scene"
  s.data = { ...s.data, limit: 0 };
  s.listeners.ready();
  await tick();
  assert.ok(q(root, '[data-action="new"]').disabled);
  card.remove();

  // ---------- room card: add step is a trade, no room ----------
  {
    const r = world({ lang: "en" });
    const room = await make(r, { scope: "area", area: "r2", view: "manage" });
    const rr = room.shadowRoot;
    await click(rr, '[data-action="new"]');
    assert.strictEqual(last(r, "create").area_id, "r2");
    assert.ok(!rr.querySelector('[data-action="house-off"]'), "no house-wide off in a room scene");
    await click(rr, '[data-action="add-step"]');
    assert.ok(!rr.querySelector('[data-action="pick-room"]'));
    same([...rr.querySelectorAll('[data-action="pick-domain"]')].map((b) => b.dataset.domain), ["light", "cover"]);
    await click(rr, '[data-action="pick-domain"][data-domain="cover"]');
    same(last(r, "add_step"), { type: "resident_scenes/add_step", scene_id: "n1", edit: last(r, "create").edit, step_type: "group", domain: "cover" });
    assert.ok(rr.querySelector('[data-action="all-off"]').textContent.includes("All closed"), "N8: covers close");
    room.remove();
  }

  // ---------- V6: usable at 320 px (layout is not measured in jsdom, so the styles are checked) ----------
  {
    const css = w.customElements.get("resident-scenes-card").styles.cssText;
    assert.match(css, /\.row \{[^}]*flex-wrap: wrap/, "rows wrap");
    assert.match(css, /\.controls \{[^}]*flex: 1 1 100%/, "controls take their own line");
    const widths = [...css.matchAll(/(?<![-\w])(?:min-)?width: (\d+)px/g)].map((m) => Number(m[1]));
    assert.ok(widths.every((px) => px <= 288 || px === 320), `no fixed width above the 320 px card: ${widths}`);
    assert.match(css, /grid-template-columns: minmax\(220px, 1fr\) 2fr/, "two columns only when wide");
    assert.ok(!/font-size: \.85em/.test(css), "V10: no shrunk buttons");
  }

  console.log("card tests passed");
  process.exit(0); // the card keeps a refresh timer running
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
