// Card tests in jsdom against the built file. Run: npm ci && npm run build && npm test
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const dom = new JSDOM("<!doctype html><body></body>", { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.ResizeObserver = class { observe() {} disconnect() {} };
const source = fs.readFileSync(path.join(__dirname, "..", "custom_components", "resident_scenes", "frontend", "resident-scenes-card.js"), "utf8");
w.eval(source);

// A house with 30 rooms, each with two light circuits and one cover.
const devices = [];
for (let r = 0; r < 30; r++) {
  for (let i = 0; i < 2; i++) {
    devices.push({ entity_id: `light.r${r}_${i}`, name: `Light ${r}.${i}`, domain: "light", area_id: `r${r}`, available: true,
      capabilities: { brightness: true } });
  }
  devices.push({ entity_id: `cover.r${r}`, name: `Cover ${r}`, domain: "cover", area_id: `r${r}`, available: true,
    capabilities: { position: true } });
}
const listing = () => ({
  version: /VERSION = "([^"]+)"/.exec(source)[1], can_edit: true, is_admin: false, manages_rights: false, name_length: 30,
  favorite_slots: 4, max_delay: 600, max_transition: 60, limit: 30, scenes: [], favorites: [null, null, null, null], foreign_scenes: [],
});
let data = listing();
let notify;
let failList = 0;
const calls = [];
const listeners = {};
const hass = {
  locale: { language: "en" }, states: { "light.r0_0": { entity_id: "light.r0_0", state: "on", attributes: { brightness: 255 } } },
  entities: {}, devices: {}, areas: {},
  formatEntityName: (st) => `Room · ${st.entity_id}`,
  connection: {
    subscribeMessage: async (cb) => { notify = cb; return () => {}; },
    addEventListener: (type, cb) => { listeners[type] = cb; },
    removeEventListener: () => {},
  },
  callService: () => {},
  callWS: async (msg) => {
    calls.push(msg);
    if (msg.type.endsWith("/list")) {
      if (failList > 0) {
        failList--;
        throw { code: "not_loaded", message: "not loaded" };
      }
      return data;
    }
    if (msg.type.endsWith("/scene")) {
      return { id: "s1", name: "Cook", entity_id: "scene.cook", kind: "resident", editable: true, can_undo: false, version: 1,
        used_in: { scenes: [], slots: [] },
        steps: [{ entity_id: "light.r1_0", state: "on", attributes: { brightness: 255 }, issue: "other_area" }] };
    }
    if (msg.type.endsWith("/devices")) {
      const ents = msg.area_id ? devices.filter((d) => d.area_id === msg.area_id) : devices;
      return { entities: ents.map((d) => ({ ...d })), favorites: [], images: [], room_scenes: [] };
    }
    return {};
  },
};
const tick = () => new Promise((resolve) => setTimeout(resolve, 20));
const same = (a, b, msg) => assert.strictEqual(JSON.stringify(a), JSON.stringify(b), msg); // objects come from the jsdom realm
const fire = (node, type) => node.dispatchEvent(new w.Event(type, { bubbles: true }));
const make = async (config) => {
  const card = w.document.createElement("resident-scenes-card");
  card.setConfig(config);
  w.document.body.appendChild(card);
  card.hass = hass;
  await tick();
  return card;
};

(async () => {
  const card = await make({ scope: "house", view: "manage" });
  const root = card.shadowRoot;
  assert.strictEqual(calls[0].scope, "_house", "the list is asked for the card scope only");
  root.querySelector('[data-action="new"]').click();
  await tick();

  // E1: a server notification while editing keeps the form and the focus
  const name = root.querySelector('[data-field="name"]');
  name.focus();
  name.value = "Away";
  fire(name, "input");
  notify({ changed: true });
  await tick();
  assert.strictEqual(root.activeElement, name, "name field keeps focus after a server notification");
  assert.strictEqual(root.querySelector('[data-field="name"]').value, "Away");

  // E1: ticking a device gives the focus back to that box
  const box = root.querySelector('[data-field="pick"][data-entity="light.r0_0"]');
  box.focus();
  box.checked = true;
  fire(box, "change");
  await tick();
  assert.strictEqual(root.activeElement?.dataset.entity, "light.r0_0", "focus stays on the ticked device");
  assert.ok(root.textContent.includes("Room · light.r0_0"), "device names come from formatEntityName");

  // B3: "Away" with all 60 light circuits off in one input; house scenes have no live preview by default
  root.querySelector('[data-action="trade-off"][data-domain="light"]').click();
  await tick();
  const steps = card._payloadSteps();
  assert.strictEqual(steps.length, 60);
  assert.ok(steps.every((s) => s.entity_id.startsWith("light.") && s.mode === "off"));
  assert.ok(!calls.some((c) => c.type.endsWith("/preview")), "no preview in house scenes by default");

  // B3: one room off in one input
  root.querySelector('[data-action="group-off"][data-group="r1"]').click();
  await tick();
  assert.strictEqual(card._payloadSteps().find((s) => s.entity_id === "cover.r1").mode, "off");

  // delays and order: the second step moves up and waits 5 s
  const delay = root.querySelectorAll('[data-field="delay"]')[1];
  delay.value = "5";
  fire(delay, "change");
  root.querySelectorAll('[data-action="up"]')[1].click();
  await tick();
  same(card._payloadSteps()[0], { entity_id: "light.r0_1", mode: "off", delay: 5 });

  // B4: reload after a reconnect
  const lists = () => calls.filter((c) => c.type.endsWith("/list")).length;
  let before = lists();
  listeners.ready();
  await tick();
  assert.strictEqual(lists(), before + 1, "card reloads after the connection is back");

  // N7: the withdrawn-rights notice goes once the right is back
  data = { ...listing(), can_edit: false };
  listeners.ready();
  await tick();
  assert.ok(root.textContent.includes("withdrawn"));
  data = listing();
  listeners.ready();
  await tick();
  assert.ok(!root.textContent.includes("withdrawn"), "notice cleared when can_edit is true again");

  // N2: a failed load keeps the last data and retries
  data = { ...listing(), scenes: [{ id: "s1", name: "Cook", entity_id: "scene.cook", kind: "resident", image_url: null }] };
  listeners.ready();
  await tick();
  failList = 1;
  listeners.ready();
  await tick();
  assert.ok(root.textContent.includes("Cook"), "last data stays visible");
  assert.ok(root.textContent.includes("retrying"));
  assert.strictEqual(card._backoff, 2);
  card._load();
  await tick();
  assert.ok(!root.textContent.includes("retrying"));

  // N3: the reason of a marked step is named
  root.querySelector('[data-action="select"]').click();
  await tick();
  assert.ok(root.textContent.includes("In another room"));

  // K6: limit reached disables "New scene"
  data = { ...listing(), limit: 0 };
  listeners.ready();
  await tick();
  assert.ok(root.querySelector('[data-action="new"]').disabled);

  // room card: live preview on, covers close with "All closed" (N8), cancel restores
  calls.length = 0;
  data = listing();
  const room = await make({ scope: "area", area: "r2", view: "manage" });
  const rr = room.shadowRoot;
  rr.querySelector('[data-action="new"]').click();
  await tick();
  assert.ok(rr.querySelector('[data-action="group-off"][data-group="cover"]').textContent.includes("All closed"));
  rr.querySelector('[data-action="group-off"][data-group="cover"]').click();
  await tick();
  same(calls.find((c) => c.type.endsWith("/preview")), {
    type: "resident_scenes/preview", step: { entity_id: "cover.r2", mode: "off" }, edit: room._editKey, area_id: "r2",
  });
  rr.querySelector('[data-action="cancel"]').click();
  await tick();
  same(calls.at(-1), { type: "resident_scenes/preview_end", restore: true, edit: room._editKey });

  console.log("card tests passed");
  process.exit(0); // the card keeps a refresh timer running
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
