// Review of version 0.3.4 (commit fcc87d9), turned to the fixed behaviour of 0.3.5: the card in jsdom, with the mocked server.
// Run: node card_probe_0_3_4.cjs <path to the repository>   (after npm ci && npm run build there)
// FIXED = was FINDING or NOTE in the review, OK = point that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, tick, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);

(async () => {
  // ---------- AA2: a light with a white channel of its own that is off: the default shown and stored is "Weiß" ----------
  {
    const s = world({ lang: "de" });
    s.devices.find((d) => d.entity_id === "light.r0_0").capabilities = { brightness: true, color_temp: false, color: true, white_mode: true };
    s.hass.states["light.r0_0"] = { entity_id: "light.r0_0", state: "off", attributes: {} };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const field = (name) => q(root, `[data-field="${name}"][data-entity="light.r0_0"]`);
    const mode = () => q(root, '[data-field="light_mode"][data-entity="light.r0_0"] [aria-checked="true"]').textContent.trim();
    assert.strictEqual(mode(), "Weiß"); // FIXED: of "Weiß" and "Farbe" the card picks white
    assert.strictEqual(field("hue"), null); // FIXED: no colour sliders
    setValue(field("brightness"), "40");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { white: true, brightness: 102 }); // FIXED: shown is stored, and it is white
    card.remove();
  }

  // ---------- three states of a light with white channel, colour temperature and colour ----------
  {
    const s = world({ lang: "de" });
    s.devices.find((d) => d.entity_id === "light.r0_0").capabilities = { brightness: true, color_temp: true, color: true, white_mode: true,
      min_kelvin: 2000, max_kelvin: 6500 };
    s.hass.states["light.r0_0"] = { entity_id: "light.r0_0", state: "on", attributes: { brightness: 128, color_mode: "hs", hs_color: [200, 50] } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const seg = q(root, '[data-field="light_mode"][data-entity="light.r0_0"]');
    same([...seg.querySelectorAll("[data-value]")].map((b) => b.textContent.trim()), ["Weiß", "Farbtemperatur", "Farbe"]); // OK
    await click(root, '[data-field="light_mode"][data-entity="light.r0_0"] [data-value="white_channel"]');
    same(sent(s, "set_entry").at(-1).values, { white: true }); // OK: the state "Weiß" is a value of its own
    card.remove();
  }

  // ---------- a tap on the state that is active sends nothing (the server would take it as a new edit, AA4) ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [
      { entity_id: "light.r0_0", name: "light.r0_0", state: "on", attributes: { brightness: 128, color_mode: "color_temp", color_temp_kelvin: 2700 }, issue: null }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const active = q(root, '[data-field="light_mode"][data-entity="light.r0_0"] [aria-checked="true"]');
    assert.strictEqual(active.textContent.trim(), "Weiß");
    const calls = sent(s, "set_entry").length;
    active.click();
    await tick();
    assert.strictEqual(sent(s, "set_entry").length, calls); // OK
    card.remove();
  }

  // ---------- 0.3.5: AA3 no heading "Szenen" without rows, AA1/AA5 head and bar styles ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, favorites: ["s1", null, null, null],
      scenes: [{ id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null }] };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    same([...root.querySelectorAll("h3")].map((h) => h.textContent.trim()).filter((t) => t === "Szenen"), []); // FIXED: AA3
    const css = w.customElements.get("resident-scenes-card").styles.cssText;
    assert.match(css, /\.head \.tools \{[^}]*flex: 1 1 100%/); // FIXED: AA1, the buttons get a row of their own
    assert.doesNotMatch(css, /max-height: 200px/); // FIXED: AA1
    assert.match(css, /\.image-btn \{[^}]*display: flex/); // FIXED: AA5, no baseline gap under the image
    assert.match(css, /\.bar \.name \{[^}]*white-space: nowrap/); // FIXED: AA5, the name stays on one line
    card.remove();
  }

  console.log("card probe 0.3.4 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
