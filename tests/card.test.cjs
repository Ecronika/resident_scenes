// Card tests in jsdom, no build step. Run: npm i jsdom && node tests/card.test.cjs
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
  for (let i = 0; i < 2; i++) devices.push({ entity_id: `light.r${r}_${i}`, name: `Light ${r}.${i}`, domain: "light", area_id: `r${r}`, available: true });
  devices.push({ entity_id: `cover.r${r}`, name: `Cover ${r}`, domain: "cover", area_id: `r${r}`, available: true });
}
const listing = {
  version: /const VERSION = "([^"]+)"/.exec(source)[1], can_edit: true, name_length: 30, favorite_slots: 4, limits: { area: 20, house: 30 },
  scenes: [], favorites: { _house: [null, null, null, null] }, foreign_scenes: [], images: [],
};
let notify;
let loads = 0;
const listeners = {};
const hass = {
  locale: { language: "en" }, states: {}, entities: {}, devices: {}, areas: {},
  connection: {
    subscribeMessage: async (cb) => { notify = cb; return () => {}; },
    addEventListener: (type, cb) => { listeners[type] = cb; },
    removeEventListener: () => {},
  },
  callService: () => {},
  callWS: async (msg) => {
    if (msg.type.endsWith("/list")) return loads++, listing;
    return { entities: devices.map((d) => ({ ...d })), favorites: [] };
  },
};
const tick = () => new Promise((resolve) => setTimeout(resolve, 20));
const fire = (node, type) => node.dispatchEvent(new w.Event(type, { bubbles: true }));

(async () => {
  const card = w.document.createElement("resident-scenes-card");
  card.setConfig({ scope: "house", view: "manage" });
  w.document.body.appendChild(card);
  card.hass = hass;
  await tick();
  const root = card.shadowRoot;
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

  // E1: ticking a device gives the focus back to that box
  const box = root.querySelector('[data-field="pick"][data-entity="light.r0_0"]');
  box.focus();
  box.checked = true;
  fire(box, "change");
  await tick();
  assert.strictEqual(root.activeElement?.dataset.entity, "light.r0_0", "focus stays on the ticked device");

  // B3: "Away" with all 60 light circuits off in one input
  root.querySelector('[data-action="trade-off"][data-domain="light"]').click();
  const steps = card._payloadSteps();
  assert.strictEqual(steps.length, 60);
  assert.ok(steps.every((s) => s.entity_id.startsWith("light.") && s.mode === "off"));

  // B3: one room off in one input
  root.querySelector('[data-action="group-off"][data-group="r1"]').click();
  assert.strictEqual(card._payloadSteps().find((s) => s.entity_id === "cover.r1").mode, "off");

  // B4: reload after a reconnect
  const before = loads;
  listeners.ready();
  await tick();
  assert.strictEqual(loads, before + 1, "card reloads after the connection is back");

  // K6: limit reached disables "New scene"
  root.querySelector('[data-action="cancel"]').click();
  listing.limits.house = 0;
  listeners.ready();
  await tick();
  assert.ok(root.querySelector('[data-action="new"]').disabled);

  console.log("card tests passed");
  process.exit(0); // the card keeps a refresh timer running
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
