// Review of the card in version 0.2.0, run in jsdom against the built file; turned around after the fixes in 0.2.1.
// Run: npm ci && npm run build && node tests/card_probe_0_2_0.cjs
// Lines marked FIXED were FINDING lines of the review, OK lines confirmed earlier fixes.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const repo = path.join(__dirname, "..");
const file = process.argv[2] ?? path.join(repo, "custom_components", "resident_scenes", "frontend", "resident-scenes-card.js");
const sourceFile = process.argv[3] ?? path.join(repo, "src", "resident-scenes-card.js");
const source = fs.readFileSync(file, "utf8");
const dom = new JSDOM("<!doctype html><body></body>", { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.ResizeObserver = class { observe() {} disconnect() {} };
w.eval(source);

const VERSION = /VERSION = "([^"]+)"/.exec(source)[1];
const tick = (ms = 20) => new Promise((resolve) => setTimeout(resolve, ms));
const fire = (node, type) => node.dispatchEvent(new w.Event(type, { bubbles: true }));
const setValue = (node, value, type = "change") => { node.value = value; fire(node, type); };

function world() {
  const devices = [];
  for (let r = 0; r < 30; r++) {
    for (let i = 0; i < 2; i++) {
      devices.push({ entity_id: `light.r${r}_${i}`, name: `Light ${r}.${i}`, domain: "light", area_id: `r${r}`,
        available: true, music_system: false, capabilities: { brightness: true, color_temp: true, color: true, min_kelvin: 2000, max_kelvin: 6500 } });
    }
    devices.push({ entity_id: `cover.r${r}`, name: `Cover ${r}`, domain: "cover", area_id: `r${r}`, available: true,
      music_system: false, capabilities: { position: true } });
  }
  const s = {
    devices, calls: [], subs: 0, failList: 0, listeners: {}, scene: null, roomScenes: [],
    data: { version: VERSION, can_edit: true, is_admin: false, manages_rights: false, name_length: 30, favorite_slots: 4,
      max_delay: 600, max_transition: 60, limit: 30, scenes: [], favorites: [null, null, null, null], foreign_scenes: [] },
  };
  const states = {};
  for (const d of devices) {
    states[d.entity_id] = { entity_id: d.entity_id, state: d.domain === "light" ? "on" : "open",
      attributes: d.domain === "light" ? { brightness: 128, hs_color: [30, 80], friendly_name: d.name } : { current_position: 70, friendly_name: d.name } };
  }
  s.hass = {
    locale: { language: "de" }, states, entities: {}, devices: {}, areas: {},
    connection: {
      subscribeMessage: async (cb) => { s.subs++; s.notify = cb; return () => {}; },
      addEventListener: (type, cb) => { s.listeners[type] = cb; },
      removeEventListener: () => {},
    },
    callService: () => {},
    callWS: async (msg) => {
      s.calls.push(msg);
      if (msg.type.endsWith("/list")) {
        if (s.failList > 0) { s.failList--; throw { code: "unknown_command", message: "Unknown command." }; }
        return s.data;
      }
      if (msg.type.endsWith("/scene")) return s.scene;
      if (msg.type.endsWith("/devices")) {
        const ents = msg.area_id ? devices.filter((d) => d.area_id === msg.area_id) : devices;
        return { entities: ents.map((d) => ({ ...d })), favorites: [], images: [], room_scenes: s.roomScenes };
      }
      if (msg.type.endsWith("/save") && s.saveError) throw s.saveError;
      return {};
    },
  };
  return s;
}

async function make(s, config) {
  const card = w.document.createElement("resident-scenes-card");
  card.setConfig(config);
  w.document.body.appendChild(card);
  card.hass = s.hass;
  await tick();
  return card;
}
const types = (s) => s.calls.map((c) => c.type.split("/")[1]);

(async () => {
  // ---------- N2: Home Assistant restarts, the integration is not loaded yet ----------
  {
    const s = world();
    s.failList = 1;
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    assert.match(root.textContent, /Nicht aktuell/); // FIXED (S12 Nr. 1): hint also without data
    await tick(2200); // the card tries again by itself
    assert.ok(root.querySelector('[data-action="new"]'), "OK (N2): content appears without a reload");
    assert.strictEqual(s.subs, 1, "OK (N2): subscribed after the first success");
    s.listeners.ready(); // connection is back after a restart
    await tick();
    assert.strictEqual(s.subs, 2, "OK (N2): subscription renewed after a reconnect");
    card.remove();
  }

  // ---------- N3 and N8: reasons in the editor, size of the controls ----------
  {
    const s = world();
    s.data.scenes = [{ id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null }];
    s.scene = { id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, can_undo: false, version: 3,
      image: null, image_url: null, transition: null, content_released: false, used_in: { scenes: [], slots: [] },
      steps: [
        { entity_id: "light.r2_0", state: "on", attributes: { brightness: 255 }, issue: null },
        { entity_id: "light.gone", name: "Old lamp", state: "on", attributes: {}, issue: "missing" },
        { entity_id: "light.r2_1", state: "on", attributes: {}, issue: "not_released" },
        { entity_id: "light.r5_0", state: "on", attributes: {}, issue: "other_area" },
      ] };
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="select"]').click();
    await tick();
    root.querySelector('[data-action="edit"]').click();
    await tick();
    const badge = (eid) => root.querySelector(`[data-field="pick"][data-entity="${eid}"]`).closest(".row").querySelector(".badge")?.textContent;
    assert.strictEqual(badge("light.gone"), "Gerät fehlt", "OK (N3)");
    assert.strictEqual(badge("light.r2_1"), "Nicht freigegeben", "OK (N3)");
    assert.strictEqual(badge("light.r5_0"), "In anderem Raum", "OK (N3)");
    const options = (eid) => [...root.querySelector(`[data-field="choice"][data-entity="${eid}"]`).options].map((o) => o.value);
    assert.deepStrictEqual(options("light.r5_0"), ["keep"], "OK: a moved device keeps its value and cannot be changed");
    assert.deepStrictEqual(options("light.r2_0"), ["keep", "capture", "off", "set"]);
    const css = [...root.querySelectorAll("style")].map((n) => n.textContent).join("") || source;
    assert.match(css, /button, select, input\[type=number\], input:not\(\[type\]\) \{ min-height: 44px/, "OK (N8): 44 px");

    // a locked device that is unticked by mistake cannot come back
    const box = root.querySelector('[data-field="pick"][data-entity="light.r5_0"]');
    box.checked = false; fire(box, "change"); await tick();
    box.checked = true; fire(box, "change"); await tick();
    assert.deepStrictEqual(options("light.r5_0"), ["keep"]); // FIXED (S12 Nr. 2): the stored step is back
    assert.strictEqual(card._payloadSteps().find((p) => p.entity_id === "light.r5_0").mode, "keep");
    card.remove();
  }

  // ---------- B3: "Abwesend" in five inputs, nothing switches ----------
  {
    const s = world();
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick(); // 1
    setValue(root.querySelector('[data-field="name"]'), "Abwesend", "input"); // 2
    root.querySelector('[data-action="trade-off"][data-domain="light"]').click(); await tick(); // 3
    root.querySelector('[data-action="trade-off"][data-domain="cover"]').click(); await tick(); // 4
    root.querySelector('[data-action="save"]').click(); await tick(); // 5
    const save = s.calls.find((c) => c.type.endsWith("/save"));
    assert.strictEqual(save.steps.length, 90, "OK (B3): 60 light circuits and 30 blinds in five inputs");
    assert.ok(save.steps.every((p) => p.mode === "off"));
    assert.ok(!types(s).includes("preview"), "OK: nothing switched");
    card.remove();
  }

  // ---------- S3: the live preview is not ended when the card goes away ----------
  {
    const s = world();
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick();
    const box = root.querySelector('[data-field="pick"][data-entity="light.r2_0"]');
    box.checked = true; fire(box, "change"); await tick();
    setValue(root.querySelector('[data-field="choice"][data-entity="light.r2_0"]'), "off"); await tick();
    assert.strictEqual(types(s).filter((t) => t === "preview").length, 1, "the light is switched off for the preview");
    card.remove(); // dashboard left, panel reloaded, browser closed
    await tick();
    assert.strictEqual(JSON.stringify(s.calls.at(-1)), JSON.stringify({ type: "resident_scenes/preview_end", restore: true })); // FIXED (S3)
  }
  {
    const s = world();
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick();
    const box = root.querySelector('[data-field="pick"][data-entity="light.r2_0"]');
    box.checked = true; fire(box, "change"); await tick();
    setValue(root.querySelector('[data-field="choice"][data-entity="light.r2_0"]'), "off"); await tick();
    root.querySelector('[data-action="new"]').click(); await tick(); // "Neue Szene" again while editing (two columns)
    assert.ok(types(s).includes("preview_end")); // FIXED (S3): the first form is restored before it goes
    assert.strictEqual(card._payloadSteps().length, 0);
    card.remove();
  }

  // ---------- S2: a called scene that is no room scene any more (its room was deleted) ----------
  {
    const s = world();
    s.data.scenes = [{ id: "h1", name: "Zuhause", entity_id: "scene.zuhause", kind: "resident", editable: true, image_url: null }];
    s.scene = { id: "h1", name: "Zuhause", entity_id: "scene.zuhause", kind: "resident", editable: true, can_undo: false, version: 2,
      image: null, image_url: null, transition: null, content_released: false, used_in: { scenes: [], slots: [] },
      steps: [{ scene_id: "aaaabbbbccccddddeeeeffff00001111", name: "Kochen", issue: "no_room_scene" }] };
    s.saveError = { code: "invalid_scene_call", message: "invalid_scene_call: Kochen" };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="select"]').click(); await tick();
    root.querySelector('[data-action="edit"]').click(); await tick();
    assert.strictEqual(root.querySelectorAll('[data-field="room-scene"]').length, 0);
    assert.match(root.textContent, /Keine Raumszene mehr/); // FIXED (S2): marked
    root.querySelector('[data-action="save"]').click(); await tick();
    const error = root.querySelector(".error").textContent;
    assert.strictEqual(error, "Diese Szene lässt sich nicht aufrufen. Kochen"); // FIXED (S2): the server names the scene
    root.querySelector('[data-action="remove"]').click(); await tick(); // FIXED (S2): can be removed
    assert.strictEqual(card._payloadSteps().length, 0);
    card.remove();
  }

  // ---------- direct values: colour temperature hides colour for good ----------
  {
    const s = world();
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick();
    const box = root.querySelector('[data-field="pick"][data-entity="light.r2_0"]');
    box.checked = true; fire(box, "change"); await tick();
    const choice = root.querySelector('[data-field="choice"][data-entity="light.r2_0"]');
    setValue(choice, "set"); await tick();
    const field = (name) => root.querySelector(`[data-field="${name}"][data-entity="light.r2_0"]`);
    assert.ok(field("brightness") && field("light_mode") && field("hue"), "brightness, white or colour, colour");
    assert.ok(field("saturation"), "FIXED (S12 Nr. 3): saturation can be set");
    setValue(field("light_mode"), "white"); await tick();
    assert.strictEqual(field("hue"), null);
    setValue(field("color_temp_kelvin"), "3000"); await tick();
    setValue(field("light_mode"), "colour"); await tick();
    assert.ok(field("hue") && field("saturation"), "FIXED (S12 Nr. 3): the colour comes back");
    assert.strictEqual(card._payloadSteps()[0].values.color_temp_kelvin, undefined, "only one of them is sent");
    assert.deepStrictEqual(types(s).filter((t) => t === "preview").length, 4, "OK: every input is previewed in a room scene");

    // a select keeps showing the user's last pick when the program changes the value
    root.querySelector('[data-action="group-off"][data-group="light"]').click(); await tick();
    assert.strictEqual(card._payloadSteps()[0].mode, "off");
    assert.strictEqual(choice.value, "off"); // FIXED (S12 Nr. 4): the select follows the program
    card.remove();
  }

  // ---------- every state change in the house redraws the card ----------
  {
    const s = world();
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick();
    root.querySelector('[data-action="trade-off"][data-domain="light"]').click(); await tick();
    let renders = 0;
    const render = card.render.bind(card);
    card.render = () => { renders++; return render(); };
    const start = process.hrtime.bigint();
    for (let i = 0; i < 100; i++) {
      // Home Assistant hands every card a new hass object on every state change of any entity
      card.hass = { ...s.hass, states: { ...s.hass.states, "sensor.power": { entity_id: "sensor.power", state: String(i), attributes: {} } } };
      await card.updateComplete;
    }
    const ms = Number(process.hrtime.bigint() - start) / 1e6;
    assert.strictEqual(renders, 100); // NOT CHANGED (S12 Nr. 5): left out by decision, below 1 ms in jsdom
    console.log(`house editor with 90 devices: ${renders} redraws for 100 unrelated state changes, ${(ms / 100).toFixed(1)} ms each in jsdom`);
    card.remove();
  }

  // ---------- spec 5.7: drag a row of the sequence onto another ----------
  {
    const s = world();
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick();
    root.querySelector('[data-field="all"][data-group="light"]').click(); await tick();
    root.querySelector('[data-field="all"][data-group="cover"]').click(); await tick();
    const order = () => card._payloadSteps().map((p) => p.entity_id);
    assert.deepStrictEqual([...order()], ["light.r2_0", "light.r2_1", "cover.r2"]);
    root.querySelectorAll(".row.order").forEach((row, i) => {
      row.getBoundingClientRect = () => ({ top: i * 50, bottom: i * 50 + 50 });
    });
    const handle = root.querySelectorAll('[data-action="drag"]')[0];
    const pointer = (type, y) => handle.dispatchEvent(new w.MouseEvent(type, { bubbles: true, clientY: y }));
    pointer("pointerdown", 10); pointer("pointermove", 60); pointer("pointermove", 120); await tick();
    assert.ok(root.querySelectorAll(".row.order")[2].classList.contains("drop"), "drop target marked");
    pointer("pointerup", 120); await tick();
    assert.deepStrictEqual([...order()], ["light.r2_1", "cover.r2", "light.r2_0"], "first row moved to the end");
    card.remove();
  }

  // ---------- parts of stage 2 that are not in the card ----------
  const src = fs.readFileSync(sourceFile, "utf8");
  assert.ok(/pointerdown/.test(src)); // FIXED (spec 5.7): order by dragging and by arrows
  assert.ok(!/preview_favorite|play_favorite/.test(src)); // spec 5.4: play button for a favorite struck by decision
  assert.ok(!src.includes("getConfigElement")); // note: no visual card editor, YAML only

  console.log("card probe 0.2.0 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
