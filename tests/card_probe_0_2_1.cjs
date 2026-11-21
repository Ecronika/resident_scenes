// Review of the card in version 0.2.1 (commit 52a8aa7), run in jsdom against the built file.
// Put it into tests/ of the repository and run: npm ci && npm run build && node tests/card_probe_0_2_1.cjs
// Taken over from the review; the FINDING lines are turned around for 0.2.2.
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
  const editRoom = async (s) => {
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="new"]').click(); await tick();
    return { card, root };
  };
  const tickDevice = async (root, eid) => {
    const box = root.querySelector(`[data-field="pick"][data-entity="${eid}"]`);
    box.checked = true; fire(box, "change"); await tick();
  };

  // ---------- the card is moved inside the page while somebody edits ----------
  {
    const s = world();
    const { card, root } = await editRoom(s);
    await tickDevice(root, "light.r2_0");
    setValue(root.querySelector('[data-field="choice"][data-entity="light.r2_0"]'), "off"); await tick();
    assert.strictEqual(types(s).filter((t) => t === "preview").length, 1);
    // Home Assistant takes cards out of the page and puts them back, for example when a view
    // rearranges its columns after the window was resized or the tablet was turned
    const parent = card.parentNode;
    card.remove(); parent.appendChild(card); await tick();
    assert.ok(root.querySelector('[data-action="save"]'), "the form is still open");
    assert.ok(!s.calls.some((c) => c.type.endsWith("/preview_end")), "OK (T3): moved, not left");
    card.remove(); await tick();
    assert.ok(s.calls.some((c) => c.type.endsWith("/preview_end") && c.restore === true), "OK: removed counts as cancel");
    parent.appendChild(card);
    card.remove();
  }

  // ---------- dragging: a cancelled gesture still moves the row ----------
  {
    const s = world();
    const { card, root } = await editRoom(s);
    for (const eid of ["light.r2_0", "light.r2_1", "cover.r2"]) await tickDevice(root, eid);
    const order = () => card._payloadSteps().map((p) => p.entity_id);
    const rows = () => root.querySelectorAll(".row.order");
    const stub = () => rows().forEach((row, i) => { row.getBoundingClientRect = () => ({ top: i * 50, bottom: i * 50 + 50 }); });
    const pointer = (index, type, y) => root.querySelectorAll('[data-action="drag"]')[index]
      .dispatchEvent(new w.MouseEvent(type, { bubbles: true, clientY: y }));
    stub();
    pointer(2, "pointerdown", 110); pointer(2, "pointermove", 10); pointer(2, "pointerup", 10); await tick();
    assert.deepStrictEqual([...order()], ["cover.r2", "light.r2_0", "light.r2_1"], "OK: last row dragged to the top");
    stub();
    pointer(0, "pointerdown", 10); pointer(0, "pointermove", 20); pointer(0, "pointerup", 20); await tick();
    assert.deepStrictEqual([...order()], ["cover.r2", "light.r2_0", "light.r2_1"], "OK: dropped on itself, nothing moves");
    stub();
    pointer(0, "pointerdown", 10); pointer(0, "pointermove", 110); pointer(0, "pointercancel", 110); await tick();
    assert.deepStrictEqual([...order()], ["cover.r2", "light.r2_0", "light.r2_1"], "OK (T4): a cancelled gesture moves nothing");
    card.remove();
  }

  // ---------- white and colour ----------
  {
    const s = world();
    // a light in white mode reports a colour as well
    s.hass.states["light.r2_0"].attributes = { brightness: 128, color_mode: "color_temp", color_temp_kelvin: 3000, hs_color: [28, 65] };
    const { card, root } = await editRoom(s);
    await tickDevice(root, "light.r2_0");
    setValue(root.querySelector('[data-field="choice"][data-entity="light.r2_0"]'), "set"); await tick();
    const field = (name) => root.querySelector(`[data-field="${name}"][data-entity="light.r2_0"]`);
    assert.strictEqual(field("light_mode").value, "white", "OK: opens in the mode of the light");
    assert.strictEqual(card._payloadSteps()[0].values.color_temp_kelvin, 3000);
    assert.strictEqual(card._payloadSteps()[0].values.hue, undefined, "OK: only one of them is sent");
    setValue(field("light_mode"), "colour"); await tick();
    assert.ok(field("hue") && field("saturation") && !field("color_temp_kelvin"), "OK (S12 Nr. 3)");
    card.remove();
  }

  // ---------- selects follow the server ----------
  {
    const s = world();
    s.data.scenes = [{ id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null }];
    s.data.favorites = ["s1", null, null, null];
    s.scene = { id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, can_undo: false, version: 3,
      image: null, image_url: null, transition: null, content_released: false, used_in: { scenes: [], slots: [] }, steps: [] };
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    root.querySelector('[data-action="select"]').click(); await tick();
    const select = root.querySelector('[data-field="favorite"]');
    assert.strictEqual(select.value, "0");
    setValue(select, "2"); await tick(); // the user picks slot 3 ...
    s.data = { ...s.data, favorites: [null, "s1", null, null] }; // ... another panel moves the scene to slot 2
    s.notify({}); await tick();
    assert.strictEqual(select.value, "1", "OK (S12 Nr. 4): the select shows what the server holds");
    card.remove();
  }

  console.log("card probe 0.2.1 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
