// Shared jsdom set-up for the card tests: the built card and a small mocked server of the 0.3.0 API.
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const repo = path.join(__dirname, "..");
const file = path.join(repo, "custom_components", "resident_scenes", "frontend", "resident-scenes-card.js");
const source = fs.readFileSync(file, "utf8");
const src = fs.readFileSync(path.join(repo, "src", "resident-scenes-card.js"), "utf8");
const dom = new JSDOM("<!doctype html><body></body>", { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.ResizeObserver = class { observe() {} disconnect() {} };
w.eval(source);

const VERSION = /VERSION = "([^"]+)"/.exec(source)[1];
const tick = (ms = 20) => new Promise((resolve) => setTimeout(resolve, ms));
const fire = (node, type) => node.dispatchEvent(new w.Event(type, { bubbles: true }));
const setValue = (node, value, type = "change") => { node.value = value; fire(node, type); };
const same = (a, b, msg) => {
  if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${msg ?? "not equal"}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
};

// A house with 30 rooms, each with two light circuits and one cover.
function world({ lang = "de" } = {}) {
  const devices = [];
  for (let r = 0; r < 30; r++) {
    for (let i = 0; i < 2; i++) {
      devices.push({ entity_id: `light.r${r}_${i}`, name: `Light ${r}.${i}`, domain: "light", area_id: `r${r}`, available: true,
        music_system: false, capabilities: { brightness: true, color_temp: true, color: true, min_kelvin: 2000, max_kelvin: 6500 } });
    }
    devices.push({ entity_id: `cover.r${r}`, name: `Cover ${r}`, domain: "cover", area_id: `r${r}`, available: true,
      music_system: false, capabilities: { position: true } });
  }
  const states = {};
  for (const d of devices) {
    states[d.entity_id] = { entity_id: d.entity_id, state: d.domain === "light" ? "on" : "open",
      attributes: d.domain === "light" ? { brightness: 128, hs_color: [30, 80] } : { current_position: 70 } };
  }
  const s = {
    devices, calls: [], subs: 0, failList: 0, listeners: {}, fail: {}, roomScenes: [], scene: null, steps: 0,
    data: { version: VERSION, can_edit: true, is_admin: false, manages_rights: false, name_length: 30, favorite_slots: 4,
      max_delay: 600, max_transition: 60, limit: 30, scenes: [], favorites: [null, null, null, null], foreign_scenes: [] },
  };
  const step = (id) => {
    const found = s.scene.sequence.find((x) => x.id === id);
    if (!found) throw { code: "step_missing", message: "step_missing: gone" };
    return found;
  };
  // stored like a state, as the server's build_step does
  const stored = ({ hue, saturation, position, ...rest }) => ({ ...rest,
    ...(hue != null ? { hs_color: [hue, saturation] } : {}), ...(position != null ? { current_position: position } : {}) });
  const changed = () => setTimeout(() => s.notify?.({ changed: true }));
  const handlers = {
    list: () => s.data,
    scene: () => {
      if (!s.scene) throw { code: "not_found", message: "not found" };
      return JSON.parse(JSON.stringify(s.scene));
    },
    devices: (m) => ({ entities: (m.area_id ? devices.filter((d) => d.area_id === m.area_id) : devices).map((d) => ({ ...d })),
      favorites: [], images: s.images ?? [], room_scenes: m.area_id ? [] : s.roomScenes }),
    create: (m) => {
      s.scene = { id: "n1", name: `${m.name} 1`, area_id: m.area_id, entity_id: "scene.neue_szene_1", kind: "resident", editable: true,
        can_undo: false, version: 1, image: null, image_url: null, transition: null, content_released: false,
        used_in: { scenes: [], slots: [] }, sequence: [] };
      s.data = { ...s.data, scenes: [...s.data.scenes, { ...s.scene }] };
      return { scene_id: "n1", version: 1 };
    },
    duplicate: () => ({ scene_id: s.scene.id, version: 1 }),
    update: (m) => { for (const k of ["name", "image", "transition", "kind", "content_released"]) if (k in m) s.scene[k] = m[k]; },
    add_step: (m) => {
      const id = `st${++s.steps}`;
      const area = m.area_id ?? s.scene.area_id;
      s.scene.sequence.push(m.step_type === "delay" ? { id, type: "delay", seconds: 5 }
        : m.step_type === "scene" ? { id, type: "scene", scene_id: m.target, name: "Kochen", area_id: area, issue: null }
        : { id, type: "group", domain: m.domain, area_id: area, entries: [] });
      return { version: 1, step_id: id };
    },
    set_delay: (m) => { step(m.step_id).seconds = m.seconds; },
    remove_step: (m) => { step(m.step_id); s.scene.sequence = s.scene.sequence.filter((x) => x.id !== m.step_id); },
    move_step: (m) => {
      const seq = s.scene.sequence;
      seq.splice(m.index, 0, ...seq.splice(seq.indexOf(step(m.step_id)), 1));
    },
    set_entry: (m) => {
      const g = step(m.step_id);
      // like the server: an input keeps the other stored values; a new colour or white replaces the old one (X11)
      const prev = g.entries.find((e) => e.entity_id === m.entity_id);
      const kept = { ...(prev?.state === "on" ? prev.attributes : {}) };
      if (m.mode === "set" && ("hue" in m.values || "color_temp_kelvin" in m.values)) {
        for (const k of ["color_mode", "hs_color", "rgb_color", "rgbw_color", "rgbww_color", "xy_color", "color_temp_kelvin"]) delete kept[k];
      }
      const entry = { entity_id: m.entity_id, state: m.mode === "off" ? "off" : "on",
        attributes: m.mode === "set" ? { ...kept, ...stored(m.values) } : { brightness: 128 }, issue: null, name: m.entity_id };
      g.entries = [...g.entries.filter((e) => e.entity_id !== m.entity_id), entry];
    },
    remove_entry: (m) => { const g = step(m.step_id); g.entries = g.entries.filter((e) => e.entity_id !== m.entity_id); },
    set_all: (m) => { step(m.step_id); },
    house_off: () => {},
    delete: () => { s.scene = null; s.data = { ...s.data, scenes: [] }; },
  };
  s.hass = {
    locale: { language: lang }, states, entities: {}, devices: {}, areas: {},
    formatEntityName: (st) => `Room · ${st.entity_id}`,
    connection: {
      subscribeMessage: async (cb) => { s.subs++; s.notify = cb; return () => {}; },
      addEventListener: (type, cb) => { s.listeners[type] = cb; },
      removeEventListener: () => {},
    },
    callService: async () => {},
    callWS: async (msg) => {
      s.calls.push(msg);
      const type = msg.type.split("/")[1];
      if (type === "list" && s.failList > 0) { s.failList--; throw { code: "unknown_command", message: "Unknown command." }; }
      if (s.fail[type]) { const err = s.fail[type]; delete s.fail[type]; throw err; }
      const result = handlers[type] ? handlers[type](msg) : undefined;
      if (!["list", "scene", "devices", "subscribe", "rights"].includes(type)) changed();
      return result ?? { version: 1 };
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
const last = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`).at(-1);
const q = (root, sel) => root.querySelector(sel);
const click = async (root, sel) => {
  const node = root.querySelector(sel);
  if (!node) throw new Error(`missing ${sel}`);
  node.click();
  await tick();
};

module.exports = { w, source, src, VERSION, tick, fire, setValue, same, world, make, types, last, q, click };
