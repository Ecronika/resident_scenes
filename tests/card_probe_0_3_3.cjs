// Review of version 0.3.3 (commit 2a4a17e), taken over for 0.3.4: the card in jsdom, with the mocked server of the repository.
// Run: node card_probe_0_3_3.cjs <path to the repository>   (after npm ci && npm run build there)
// FIXED = a FINDING or NOTE of the review, now asserting the corrected behaviour; OK = point that holds.
// The block Z6 (added on 22.11.2026) measures the card against draft 0.12: scene image as a square.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, tick, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);
const key = (node, name) => node.dispatchEvent(new w.KeyboardEvent("keydown", { key: name, bubbles: true, composed: true }));
const light = (id, state, attributes) => ({ entity_id: id, name: id, state, attributes, issue: null });

(async () => {
  // ---------- Z2: a light that is on in its white mode gets the default colour with the first input ----------
  {
    const s = world({ lang: "de" });
    // colour channels and a white mode of its own, no colour temperature: supported_color_modes ["hs", "white"]
    s.devices.find((d) => d.entity_id === "light.r0_0").capabilities = { brightness: true, color_temp: false, color: true, white_mode: true };
    s.hass.states["light.r0_0"] = { entity_id: "light.r0_0", state: "on", attributes: { brightness: 200, color_mode: "white" } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const put = async (entries) => {
      s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries }];
      s.notify({ changed: true });
      await tick();
    };
    const field = (name) => q(root, `[data-field="${name}"][data-entity="light.r0_0"]`);
    await put([]);
    await click(root, '[data-action="open"][data-id="g1"]');
    // not ticked: the light is on in white, the card shows the state "Weiß" without sliders
    assert.strictEqual(q(root, '[data-field="pick"][data-entity="light.r0_0"]').getAttribute("aria-checked"), "false");
    assert.strictEqual(field("hue"), null); // FIXED
    assert.strictEqual(field("saturation"), null); // FIXED
    const mode = q(root, '[data-field="light_mode"][data-entity="light.r0_0"] [aria-checked="true"]');
    assert.strictEqual(mode.textContent.trim(), "Weiß"); // FIXED
    setValue(field("brightness"), "40");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { brightness: 102 }); // FIXED: dimming keeps the white mode
    // ticked while on in white: the server stores the mode (test_z2), the next input replaces it with the orange
    await put([light("light.r0_0", "on", { brightness: 200, color_mode: "white" })]);
    setValue(field("brightness"), "20");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { brightness: 51 }); // FIXED
    // the colour can still be chosen
    await click(root, '[data-field="light_mode"][data-entity="light.r0_0"] [data-value="colour"]');
    same(sent(s, "set_entry").at(-1).values, { hue: 30, saturation: 100 }); // FIXED
    card.remove();
  }

  // ---------- Y1: fixed for new inputs; an entry stored without a colour still shows one until it is touched ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    // as 0.3.2 stored it after "An" and a new brightness; also what a direct call with a brightness only stores
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [light("light.r0_0", "on", { brightness: 102 })] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const field = (name) => q(root, `[data-field="${name}"][data-entity="light.r0_0"]`);
    assert.strictEqual(field("color_temp_kelvin").value, "2000"); // NOTE: shown, not stored (draft 0.11, 4.5)
    setValue(field("brightness"), "10");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { color_temp_kelvin: 2000, brightness: 26 }); // OK: the next input stores it
    card.remove();
  }

  // ---------- music favorites: the list of the card ----------
  {
    const s = world({ lang: "de" });
    for (const id of ["media_player.r0", "media_player.r0b"]) {
      s.devices.push({ entity_id: id, name: id, domain: "media_player", area_id: "r0", available: true, music_system: true, capabilities: {} });
      s.hass.states[id] = { entity_id: id, state: "idle", attributes: { volume_level: 0.2 } };
    }
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    const original = s.hass.callWS;
    s.hass.callWS = async (m) => {
      const res = await original(m);
      return m.type === "resident_scenes/devices" ? { ...res, favorites: [{ id: "f1", name: "Sport" }, { id: "f2", name: "News" }] } : res;
    };
    await click(root, '[data-action="new"]');
    const fav = (id) => ({ entity_id: id, name: id, music: "favorite", favorite_id: "f1", favorite_name: "Sport", volume: 0.2, issue: null });
    s.scene.sequence = [{ id: "m1", type: "group", domain: "media_player", area_id: "r0", entries: [fav("media_player.r0"), fav("media_player.r0b")] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="m1"]');
    const opener = (id) => q(root, `[data-action="favorite-open"][data-entity="${id}"]`);
    opener("media_player.r0").focus();
    opener("media_player.r0").click();
    await tick();
    assert.strictEqual(opener("media_player.r0").getAttribute("aria-expanded"), "true");
    assert.strictEqual(opener("media_player.r0").getAttribute("aria-label"), "Favorit: Sport"); // OK: named for screen readers
    key(root.activeElement, "End");
    assert.strictEqual(root.activeElement.textContent.trim(), "News"); // OK
    // the list of a second player closes the first one
    opener("media_player.r0b").click();
    await tick();
    assert.strictEqual(root.querySelectorAll('[role="listbox"]').length, 1); // OK
    // a press beside the list closes it
    q(root, '[data-field="volume"][data-entity="media_player.r0"]').dispatchEvent(new w.MouseEvent("click", { bubbles: true, composed: true }));
    await tick();
    assert.ok(!q(root, '[role="listbox"]')); // FIXED
    card.remove();
  }

  // ---------- thermostat: the range the card names is the range of the device ----------
  {
    const s = world({ lang: "en" });
    s.hass.config = { unit_system: { temperature: "°C" } };
    s.devices.push({ entity_id: "climate.r0", name: "Thermostat", domain: "climate", area_id: "r0", available: true,
      music_system: false, capabilities: { hvac_modes: ["off", "heat"], min_temp: 7, max_temp: 30, temp_step: 0.5 } });
    s.hass.states["climate.r0"] = { entity_id: "climate.r0", state: "heat", attributes: { temperature: 21 } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "c1", type: "group", domain: "climate", area_id: "r0", entries: [
      { entity_id: "climate.r0", name: "Thermostat", state: "heat", attributes: { temperature: 21.5 }, issue: null }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="c1"]');
    const temp = () => q(root, '[data-field="temperature"]');
    assert.strictEqual(temp().value, "21.5"); // OK: the notation of the language
    for (const [typed, value] of [["7", 7], ["30", 30], ["21,5", 21.5]]) { // the limits count as inside
      setValue(temp(), typed);
      await tick(30);
      assert.strictEqual(sent(s, "set_entry").at(-1).values.temperature, value);
    }
    const calls = sent(s, "set_entry").length;
    setValue(temp(), "21,3");
    await tick();
    assert.strictEqual(sent(s, "set_entry").length, calls); // FIXED: the step of 0.5 is checked
    assert.strictEqual(q(root, ".error").textContent.trim(), "Temperature not on the step of the device: 0.5 °C"); // FIXED
    setValue(temp(), "30.5");
    await tick();
    assert.strictEqual(sent(s, "set_entry").length, calls);
    assert.strictEqual(q(root, ".error").textContent.trim(), "Temperature out of range: 7–30 °C"); // OK
    card.remove();
  }

  // ---------- Z6: the scene image in the list, in the scene view and on the tile (draft 0.12: 4.8, 5.2) ----------
  {
    const s = world({ lang: "de" });
    s.scene = { id: "p1", name: "Abend", area_id: null, entity_id: "scene.abend", kind: "resident", editable: true, can_undo: false,
      version: 1, image: "upload:0123.jpg", image_url: "/api/resident_scenes/photo/0123.jpg", transition: null,
      content_released: false, used_in: { scenes: [], slots: [] }, sequence: [{ id: "d1", type: "delay", seconds: 5 }] };
    s.data = { ...s.data, scenes: [{ ...s.scene }], favorites: ["p1", null, null, null] };
    const css = w.customElements.get("resident-scenes-card").styles.cssText;
    const rule = (sel) => new RegExp(`${sel.replace(".", "\\.")}\\s*\\{([^}]*)\\}`).exec(css)?.[1] ?? "";
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    // list: no image and no placeholder in the rows
    assert.strictEqual(q(root, ".row img"), null); // FIXED
    assert.strictEqual(q(root, ".row svg"), null); // FIXED
    // scene view: a square of 80 px left of the name, the buttons beside it
    await click(root, '[data-action="select"][data-id="p1"]');
    const head = q(root, ".head");
    assert.strictEqual(head.firstElementChild.className, "hero"); // the image comes first, left of ...
    assert.ok(head.firstElementChild.nextElementSibling.querySelector("h2")); // FIXED: ... the name beside it
    assert.ok(head.querySelector('.title [data-action="play"]')); // FIXED: the buttons right of the image
    assert.match(rule(".hero"), /width:\s*80px;\s*height:\s*80px/); // FIXED
    assert.match(rule(".hero"), /aspect-ratio:\s*1;[^}]*object-fit:\s*cover/); // FIXED: the image fills the square
    // AA1 (0.3.5): narrow heads put the buttons in a row of their own and need no max-height; wide heads keep 120 px
    assert.match(css, /@container \(width >= 600px\) \{\s*\.head \{ flex-wrap: nowrap; max-height: 120px; \}/); // FIXED
    // edit mode: the head image carries a pencil and opens the image choice; no field with a preview of its own
    await click(root, '[data-action="edit"]');
    assert.ok(q(root, '.bar [data-action="image"] img.hero')); // FIXED
    assert.ok(q(root, '.bar [data-action="image"] .pencil')); // FIXED
    assert.strictEqual(root.querySelectorAll('img[src="/api/resident_scenes/photo/0123.jpg"]').length, 1); // FIXED
    await click(root, '[data-action="image"]');
    assert.ok(q(root, ".tiles .tile")); // the image choice opens
    // without an image: the placeholder
    s.scene.image_url = null;
    s.scene.image = null;
    s.notify({ changed: true });
    await tick();
    assert.ok(q(root, '.bar [data-action="image"] span.hero svg')); // FIXED
    card.remove();
    // favourites view: the tile is 4:3
    const fav = await make(s, { scope: "house", view: "favorites" });
    assert.ok(q(fav.shadowRoot, ".tile img"));
    assert.match(rule(".tile"), /aspect-ratio:\s*1;/); // FIXED: square tiles, also in the image choice
    assert.match(rule(".tile span"), /linear-gradient\(transparent, rgba\(0, 0, 0, \.7\)\)[^}]*text-shadow/); // FIXED: readable name
    fav.remove();
    // upload: the card crops to the square and sends 640 x 640
    const src = fs.readFileSync(path.join(repo, "src", "resident-scenes-card.js"), "utf8");
    assert.match(src, /const TILE = \{ w: 640, h: 640 \}/); // FIXED
  }

  console.log("card probe 0.3.3 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
