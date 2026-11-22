// Review of version 0.3.2 (commit de9d64c): the card in jsdom, with the mocked server of the repository.
// Run: node card_probe_0_3_2.cjs <path to the repository>   (after npm ci && npm run build there)
// FINDING and NOTE lines of the review are flipped to the behaviour of 0.3.3 and marked FIXED, OK = point that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, tick, fire, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);
const key = (node, name, extra = {}) =>
  node.dispatchEvent(new w.KeyboardEvent("keydown", { key: name, bubbles: true, composed: true, ...extra }));
const light = (id, state, attributes) => ({ entity_id: id, name: id, state, attributes, issue: null });

(async () => {
  // ---------- Y1: the colour shown for an entry that has none is sent along ----------
  {
    const s = world({ lang: "de" });
    // light.r0_0 has white and colour, light.r0_1 colour only
    s.devices.find((d) => d.entity_id === "light.r0_1").capabilities = { brightness: true, color_temp: false, color: true };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const put = async (entries) => {
      s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries }];
      s.notify({ changed: true });
      await tick();
    };
    const field = (name, id) => q(root, `[data-field="${name}"][data-entity="${id}"]`);
    const marked = (id) => [...field("light_mode", id).querySelectorAll("button")].find((b) => b.getAttribute("aria-checked") === "true");

    // both lights were off when they were ticked
    await put([light("light.r0_0", "off", {}), light("light.r0_1", "off", {})]);
    await click(root, '[data-action="open"][data-id="g1"]');
    field("on", "light.r0_0").click();
    await tick();
    same(sent(s, "set_entry").at(-1).values, { color_temp_kelvin: 2000 }); // FIXED: "An" sends the white it shows
    // an entry stored with a brightness and no colour (as 0.3.2 stored it)
    await put([light("light.r0_0", "on", { brightness: 102 }), light("light.r0_1", "on", { brightness: 102 })]);
    assert.strictEqual(marked("light.r0_0").dataset.value, "white"); // "Weiß" is marked,
    assert.strictEqual(field("color_temp_kelvin", "light.r0_0").value, "2000"); // and 2000 K is shown
    const calls = sent(s, "set_entry").length;
    marked("light.r0_0").click(); // pressing the marked "Weiß" does not store it either: the entry is ticked
    await tick();
    assert.strictEqual(sent(s, "set_entry").length, calls);
    setValue(field("brightness", "light.r0_0"), "10");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { color_temp_kelvin: 2000, brightness: 26 }); // FIXED: the white shown is sent along
    // colour only: hue 30° and saturation 100 % are shown and sent along
    assert.strictEqual(field("hue", "light.r0_1").value, "30");
    assert.strictEqual(field("saturation", "light.r0_1").value, "100");
    setValue(field("brightness", "light.r0_1"), "10");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { hue: 30, saturation: 100, brightness: 26 }); // FIXED
    // with a stored colour only the moved value is sent (X11)
    await put([light("light.r0_0", "on", { brightness: 102, color_mode: "color_temp", color_temp_kelvin: 3000 })]);
    setValue(field("brightness", "light.r0_0"), "20");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { brightness: 51 }); // OK
    // the row of the sequence is right: it names the brightness only
    await put([light("light.r0_0", "on", { brightness: 102 })]);
    await click(root, '[data-action="close-step"]');
    const line = [...q(root, '[data-action="open"][data-id="g1"]').closest(".row").querySelectorAll(".name > .line")].at(-1);
    assert.match(line.textContent.replace(/\s+/g, " ").trim(), /40 %$/); // OK
    card.remove();
  }

  // ---------- music favorites: a list of the card, bound to the stored favorite ----------
  {
    const s = world({ lang: "de" });
    s.devices.push({ entity_id: "media_player.r0", name: "Sonos", domain: "media_player", area_id: "r0", available: true,
      music_system: true, capabilities: {} });
    s.hass.states["media_player.r0"] = { entity_id: "media_player.r0", state: "idle", attributes: { volume_level: 0.2 } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    const original = s.hass.callWS;
    s.hass.callWS = async (m) => {
      const res = await original(m);
      return m.type === "resident_scenes/devices" ? { ...res, favorites: [{ id: "f1", name: "Sport" }, { id: "f2", name: "News" }] } : res;
    };
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "m1", type: "group", domain: "media_player", area_id: "r0", entries: [
      { entity_id: "media_player.r0", name: "Sonos", music: "favorite", favorite_id: "f1", favorite_name: "Sport", volume: 0.2, issue: null }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="m1"]');
    const list = () => q(root, '[data-field="favorite_id"]');
    assert.ok(!root.querySelector("select")); // FIXED (spec 5.7): a choice is an element of the card, not of the browser
    const opener = () => q(root, '[data-action="favorite-open"]');
    assert.strictEqual(opener().getAttribute("aria-expanded"), "false");
    assert.ok(!q(root, '[role="listbox"]')); // opens on demand
    opener().focus();
    opener().click();
    await tick();
    const options = [...root.querySelectorAll('[role="listbox"] [role="option"]')];
    same(options.map((o) => o.textContent.trim()), ["Sport", "News"]);
    assert.strictEqual(root.activeElement, options[0]); // the stored one has the focus
    key(root.activeElement, "ArrowDown");
    assert.strictEqual(root.activeElement, options[1]); // arrow keys move in the list
    key(root.activeElement, "Escape");
    await tick();
    assert.ok(!q(root, '[role="listbox"]'));
    assert.strictEqual(root.activeElement, opener()); // the focus is back
    // a refused choice: the list shows the stored favorite again
    s.fail.set_entry = { code: "unknown_favorite", message: "unknown_favorite: media_player.r0" };
    opener().click();
    await tick();
    q(root, '[role="option"][data-value="f2"]').click();
    await tick(50);
    assert.ok(q(root, ".error")); // OK: the reason is given
    assert.strictEqual(sent(s, "set_entry").at(-1).favorite_id, "f2");
    assert.strictEqual(list().dataset.value, "f1"); // FIXED: bound to the stored "Sport" (f1)
    assert.match(opener().textContent, /Sport/);
    assert.strictEqual(s.scene.sequence[0].entries[0].favorite_id, "f1");
    card.remove();
  }

  // ---------- thermostat: a setpoint out of range ----------
  {
    const s = world({ lang: "de" });
    s.hass.config = { unit_system: { temperature: "°C" } };
    s.devices.push({ entity_id: "climate.r0", name: "Thermostat", domain: "climate", area_id: "r0", available: true,
      music_system: false, capabilities: { hvac_modes: ["off", "heat"], min_temp: 7, max_temp: 30 } });
    s.hass.states["climate.r0"] = { entity_id: "climate.r0", state: "heat", attributes: { temperature: 21 } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "c1", type: "group", domain: "climate", area_id: "r0", entries: [
      { entity_id: "climate.r0", name: "Thermostat", state: "heat", attributes: { temperature: 21 }, issue: null }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="c1"]');
    const temp = () => q(root, '[data-field="temperature"]');
    assert.ok(!temp().hasAttribute("min") && !temp().hasAttribute("max")); // the field no longer knows the range (X8)
    const calls = sent(s, "set_entry").length;
    setValue(temp(), "99");
    await tick(50);
    assert.strictEqual(temp().value, "21"); // OK: the stored value again
    const range = "Temperatur außerhalb des Bereichs: 7–30 °C";
    assert.strictEqual(q(root, ".error").textContent.trim(), range); // FIXED: the card checks and names the range
    assert.strictEqual(sent(s, "set_entry").length, calls);
    s.fail.set_entry = { code: "invalid_value", message: "invalid_value: temperature" }; // the answer of the server (test_temperature_out_of_range)
    setValue(temp(), "29");
    await tick(50);
    assert.strictEqual(q(root, ".error").textContent.trim(), range); // FIXED: the server's refusal names the range too
    setValue(temp(), "abc");
    await tick();
    assert.strictEqual(q(root, ".error").textContent.trim(), range); // FIXED
    assert.strictEqual(temp().value, "21"); // OK
    s.scene.sequence[0].entries[0].attributes = { temperature: 21.5 };
    s.notify({ changed: true });
    await tick();
    assert.strictEqual(temp().value, "21,5"); // FIXED: the notation of the language, like the row of the sequence
    card.remove();
  }

  // ---------- questions: the card behind is locked for both questions, Tab stays inside the list of slots ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="done"]');
    const heart = q(root, '[data-action="heart"]');
    heart.focus();
    heart.click();
    await tick();
    assert.ok(q(root, '[data-action="heart"]').closest("[inert]")); // OK (X5): the scene view behind takes no input
    assert.ok(!q(root, ".dialog").closest("[inert]"));
    assert.strictEqual(root.activeElement?.dataset.action, "slot-close"); // OK
    const buttons = [...root.querySelectorAll(".dialog button")];
    key(root.activeElement, "Tab");
    assert.strictEqual(root.activeElement, buttons[(buttons.indexOf(q(root, '[data-action="slot-close"]')) + 1) % buttons.length]); // OK
    key(root.activeElement, "Escape");
    await tick();
    assert.ok(!q(root, ".dialog") && !q(root, '[data-action="heart"]').closest("[inert]")); // OK
    assert.strictEqual(root.activeElement?.dataset.action, "heart"); // OK: the focus is back
    card.remove();
  }

  // ---------- the row of a step: as many devices as fully fit ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const entry = (i) => light(`light.r0_${i}`, "on", { brightness: 26 });
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [entry(0), entry(1), entry(2)] }];
    s.notify({ changed: true });
    await tick();
    const second = [...q(root, '[data-action="open"][data-id="g1"]').closest(".row").querySelectorAll(".name > .line")].at(-1);
    // jsdom has no layout: two devices, as before
    assert.match(second.textContent.replace(/\s+/g, " ").trim(), /10 %, .* 10 %\+ 1 weitere$/);
    assert.ok(second.querySelector(".clip"));
    // with a layout: a line of `width` pixels, 8 pixels a character
    let width = 0;
    const box = (name, value) => Object.defineProperty(w.HTMLElement.prototype, name, { configurable: true, get: value });
    box("clientWidth", function () { return this.classList.contains("line") || this.classList.contains("clip") ? width : 0; });
    box("scrollWidth", function () { return this.textContent.length * 8; });
    const line = () => [...q(root, '[data-action="open"][data-id="g1"]').closest(".row").querySelectorAll(".name > .line")].at(-1)
      .textContent.replace(/\s+/g, " ").trim();
    const fit = async (px) => {
      width = px;
      card.requestUpdate();
      await tick();
      return line();
    };
    assert.match(await fit(1000), /^[^+]*light\.r0_1 10 %, [^+]*light\.r0_2 10 %$/); // FIXED: all three fit, nothing more
    assert.match(await fit(200), /^[^,]*light\.r0_0 10 %\+ 2 weitere$/); // FIXED: one fits fully, the rest counted
    assert.strictEqual(await fit(50), "3 Geräte"); // FIXED: not even the first fits
    delete w.HTMLElement.prototype.clientWidth;
    delete w.HTMLElement.prototype.scrollWidth;
    card.remove();
  }

  console.log("card probe 0.3.2 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
