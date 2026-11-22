// Review of version 0.3.1 (commit e0e8fe1), adopted for 0.3.2: the card in jsdom, with the mocked server of the repository.
// Run: node card_probe_0_3_1.cjs <path to the repository>   (after npm ci && npm run build there)
// FIXED = was a FINDING or NOTE against 0.3.1, asserts the fixed behaviour; OK = point that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, tick, fire, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);
const key = (node, name, extra = {}) =>
  node.dispatchEvent(new w.KeyboardEvent("keydown", { key: name, bubbles: true, composed: true, ...extra }));

(async () => {
  // ---------- X3: the devices of a deleted room got a room again ----------
  {
    const s = world({ lang: "de" });
    s.devices.push({ entity_id: "light.loose", name: "Loose", domain: "light", area_id: null, available: true,
      music_system: false, capabilities: { brightness: true } });
    s.hass.states["light.loose"] = { entity_id: "light.loose", state: "on", attributes: { brightness: 128 } };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    // what the server of 0.3.2 sends after "room deleted, light put into room r0": a step without a room, "other_area"
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: null,
      entries: [{ entity_id: "light.r0_0", name: "Light 0.0", state: "on", attributes: { brightness: 26 }, issue: "other_area" }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const rows = [...root.querySelectorAll(".row.device")];
    same(rows.map((r) => r.querySelector('[data-field="pick"]').dataset.entity), ["light.loose", "light.r0_0"]);
    const moved = rows[1];
    assert.ok(!moved.textContent.includes("Nicht freigegeben")); // FIXED
    assert.ok(moved.textContent.includes("In anderem Raum")); // FIXED: the reason of draft 0.9 (4.5)
    assert.ok(!moved.querySelector(".controls"), "locked in the card, the server refuses a new value as well");
    await click(root, '[data-action="close-step"]');
    assert.ok(root.textContent.includes("In anderem Raum"), "the sequence shows the mark"); // FIXED
    card.remove();
  }

  // ---------- X4: an input for the delay that is not taken shows the stored value and the reason ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="add-delay"]');
    const field = () => q(root, '[data-field="delay"]');
    assert.strictEqual(field().type, "text"); // OK (V16): no number field of the browser
    assert.strictEqual(field().maxLength, 3);
    for (const typed of ["2,5", "700", "0", "abc", "2.5"]) {
      setValue(field(), typed, "input");
      fire(field(), "change");
      await tick();
      assert.strictEqual(sent(s, "set_delay").length, 0, typed); // OK: nothing is sent; FIXED: "2.5" is not rounded
      assert.strictEqual(field().value, "5"); // FIXED: the stored value again
      assert.ok(q(root, ".error").textContent.includes("Verzögerung außerhalb des Bereichs"), typed); // FIXED: the reason
      assert.strictEqual(s.scene.sequence[0].seconds, 5);
    }
    setValue(field(), "12", "input");
    fire(field(), "change");
    await tick();
    assert.strictEqual(sent(s, "set_delay").at(-1).seconds, 12); // OK
    assert.ok(!q(root, ".error"), "the message goes with the next accepted input");
    card.remove();
  }

  // ---------- X5: the question before replacing a favorite slot gets the focus ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="done"]');
    s.data = { ...s.data, scenes: [...s.data.scenes, { id: "other", name: "Abend", entity_id: "scene.abend", editable: true }],
      favorites: ["other", null, null, null] };
    s.notify({ changed: true });
    await tick();
    const heart = q(root, '[data-action="heart"]');
    heart.focus();
    heart.click();
    await tick();
    assert.strictEqual(root.activeElement?.dataset.action, "slot-close"); // OK (V15): focus on "Schließen"
    const taken = q(root, '[data-action="slot"][data-slot="0"]');
    taken.focus(); // a browser focuses the button that is pressed
    taken.click();
    await tick();
    assert.ok(q(root, '[data-action="slot-confirm"]'), "the question is open");
    assert.strictEqual(root.activeElement?.dataset.action, "slot-cancel"); // FIXED: focus on "Abbrechen"
    key(root.activeElement, "Escape"); // so Escape answers the question
    await tick();
    assert.ok(!q(root, '[data-action="slot-confirm"]') && q(root, '[data-action="slot-close"]'), "back to the list of slots");
    assert.strictEqual(root.activeElement?.dataset.action, "slot-close"); // FIXED: the list of slots has the focus again
    assert.strictEqual(sent(s, "set_favorite").length, 0); // OK: nothing replaced
    card.remove();
  }

  // ---------- questions: the card behind takes no input, Tab stays inside, the scene is named ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const opener = q(root, '[data-action="ask-delete"]');
    opener.focus();
    opener.click();
    await tick();
    const dialog = q(root, '[role="alertdialog"]');
    assert.strictEqual(root.activeElement?.dataset.action, "keep-scene"); // OK (V15)
    assert.ok(q(root, ".editor").closest("[inert]")); // FIXED (X5; draft 0.9, 5.7): the form behind is locked
    assert.ok(dialog.textContent.includes("Neue Szene 1")); // FIXED (draft 0.9, 5.3): the question names the scene
    key(root.activeElement, "Tab");
    assert.strictEqual(root.activeElement?.dataset.action, "delete"); // FIXED: Tab goes round inside the question
    key(root.activeElement, "Tab", { shiftKey: true });
    assert.strictEqual(root.activeElement?.dataset.action, "keep-scene");
    key(root.activeElement, "Tab", { shiftKey: true });
    assert.strictEqual(root.activeElement?.dataset.action, "delete");
    key(dialog, "Escape");
    await tick();
    assert.strictEqual(root.activeElement?.dataset.action, "ask-delete"); // OK: the focus goes back
    assert.ok(!q(root, ".editor").closest("[inert]"));
    card.remove();
  }

  // ---------- V6 and draft 0.9, 5.2: the row of a step ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const entry = (i, issue = null) => ({ entity_id: `light.r0_${i}`, name: `Light 0.${i}`, state: "on",
      attributes: { brightness: 26, color_temp_kelvin: 2700 }, issue });
    s.scene.sequence = [
      { id: "g2", type: "group", domain: "light", area_id: "r0", entries: [entry(0), entry(1)] },
      { id: "g3", type: "group", domain: "light", area_id: "r1", entries: [entry(0), entry(1), entry(2, "missing"), entry(3)] },
      { id: "d1", type: "delay", seconds: 3 },
    ];
    s.notify({ changed: true });
    await tick();
    const lines = (id) => [...q(root, `[data-action="open"][data-id="${id}"]`).closest(".row").querySelectorAll(".name > .line")]
      .map((l) => l.textContent.replace(/\s+/g, " ").trim());
    same(lines("g2").length, 2); // FIXED: two lines, the title over the devices
    assert.match(lines("g2")[0], /– Licht$/);
    assert.match(lines("g2")[1], /^Room · light\.r0_0 10 % · 2\.700 K, Room · light\.r0_1 10 % · 2\.700 K$/);
    assert.match(lines("g3")[1], /2\.700 K\+ 2 weitere\s*Gerät fehlt$/); // FIXED: "+ 2 weitere", and the mark of an entry
    assert.ok(q(root, ".line .clip"), "the devices are clipped to one line");
    assert.ok(root.textContent.includes("ohne Wirkung")); // FIXED (draft 0.9, 5.2): the delay at the end has the hint
    // moved up, the delay has an effect again
    q(root, '[data-action="drag"][data-id="d1"]').focus();
    key(q(root, '[data-action="drag"][data-id="d1"]'), "ArrowUp");
    await tick(50);
    assert.strictEqual(sent(s, "move_step").at(-1).index, 1);
    assert.ok(!root.textContent.includes("ohne Wirkung"));
    assert.strictEqual(q(root, '.sr[role="status"]').textContent, "An Stelle 2 von 3 verschoben."); // FIXED (5.7)
    await click(root, '[data-action="done"]');
    assert.ok(root.textContent.includes("+ 2 weitere"), "the same row in the scene view");
    card.remove();
  }

  // ---------- W7: counting on from the value sent last, and its limit ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="add-delay"]');
    const plus = () => q(root, '[data-action="delay-plus"]');
    plus().click();
    plus().click();
    plus().click();
    await tick(100);
    same(sent(s, "set_delay").map((c) => c.seconds), [6, 7, 8], "three taps"); // OK (W7)
    s.scene.sequence[0].seconds = 20; // a second editor sets the delay within two seconds of the tap
    s.notify({ changed: true });
    await tick();
    assert.strictEqual(q(root, '[data-field="delay"]').value, "20");
    plus().click();
    await tick();
    assert.strictEqual(sent(s, "set_delay").at(-1).seconds, 9); // NOTE: the field shows 20, the tap sends 9
    card.remove();
  }

  // ---------- X6, X7: the options of a music player ----------
  {
    const s = world({ lang: "de" });
    s.devices.push({ entity_id: "media_player.r0", name: "Sonos", domain: "media_player", area_id: "r0", available: true,
      music_system: true, capabilities: {} });
    s.hass.states["media_player.r0"] = { entity_id: "media_player.r0", state: "idle", attributes: { volume_level: 0.2 } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" }); // the mocked server has no music favorites
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="add-step"]');
    await click(root, '[data-action="pick-domain"][data-domain="media_player"]');
    const seg = () => [...root.querySelectorAll('[data-field="music"] button')];
    same(seg().map((b) => b.dataset.value), ["off", "on"]); // FIXED (X6): no "Favorit" without any favorite
    assert.ok(root.textContent.includes("Keine Favoriten")); // FIXED: the hint names the reason
    // X7: the player is off and not ticked, so "Aus" is shown as chosen; pressing it ticks the player
    assert.strictEqual(seg()[0].getAttribute("aria-checked"), "true");
    assert.strictEqual(q(root, '[data-field="pick"]').getAttribute("aria-checked"), "false");
    seg()[0].click();
    await tick();
    assert.strictEqual(sent(s, "set_entry").at(-1).music, "off"); // FIXED (X7): spec 4.5, an input on an unticked device ticks it
    assert.strictEqual(q(root, '[data-field="pick"]').getAttribute("aria-checked"), "true");
    s.scene.sequence[0].entries = [{ entity_id: "media_player.r0", name: "Sonos", music: "off", issue: null }]; // as the server stores it
    s.notify({ changed: true });
    await tick();
    seg()[0].click(); // ticked: the marked choice changes nothing
    await tick();
    assert.strictEqual(sent(s, "set_entry").length, 1);
    card.remove();
  }

  // ---------- music favorites: one list, not a button each (draft 0.9, 5.2) ----------
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
    await click(root, '[data-action="add-step"]');
    await click(root, '[data-action="pick-domain"][data-domain="media_player"]');
    const seg = () => [...root.querySelectorAll('[data-field="music"] button')];
    same(seg().map((b) => b.dataset.value), ["off", "on", "favorite"]); // OK: offered with favorites
    seg()[2].click();
    await tick();
    assert.strictEqual(sent(s, "set_entry").at(-1).favorite_id, "f1");
    s.scene.sequence[0].entries[0] = { entity_id: "media_player.r0", music: "favorite", favorite_id: "f1", favorite_name: "Sport",
      volume: 0.2, issue: null };
    s.notify({ changed: true });
    await tick();
    assert.strictEqual(root.querySelectorAll('[data-field="favorite_id"] button').length, 1); // only the opener (0.3.3)
    await click(root, '[data-action="favorite-open"]'); // a list of the card since 0.3.3 (Y5)
    const options = [...root.querySelectorAll('[data-field="favorite_id"] [role="option"]')];
    same(options.map((o) => o.textContent.trim()), ["Sport", "News"]); // FIXED: a list
    options[1].click();
    await tick();
    assert.strictEqual(sent(s, "set_entry").at(-1).favorite_id, "f2");
    card.remove();
  }

  // ---------- house scene: "Alle im Haus aus" for a trade that only has devices without a room ----------
  {
    const s = world({ lang: "de" });
    s.devices.push({ entity_id: "switch.loose", name: "Pump", domain: "switch", area_id: null, available: true,
      music_system: false, capabilities: {} });
    s.hass.states["switch.loose"] = { entity_id: "switch.loose", state: "on", attributes: {} };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const off = [...root.querySelectorAll('[data-action="house-off"]')].map((b) => b.dataset.domain);
    assert.ok(off.includes("switch")); // OK (X1 fixed): the server makes a step "Ohne Raum" for it (test_x1)
    await click(root, '[data-action="add-step"]');
    const rooms = [...root.querySelectorAll('[data-action="pick-room"]')].map((b) => b.textContent.trim());
    assert.strictEqual(rooms.at(-1), "Ohne Raum"); // OK (W2): after the rooms
    await click(root, '[data-action="pick-room"][data-id=""]');
    same([...root.querySelectorAll('[data-action="pick-domain"]')].map((b) => b.dataset.domain), ["switch"]); // OK
    card.remove();
  }

  // ---------- X11: a colour captured as rgb_color, xy_color …; the server adds hs_color, an input keeps the colour ----------
  {
    const s = world({ lang: "de" });
    // light.r0_0 has white and colour, light.r0_1 colour only
    s.devices.find((d) => d.entity_id === "light.r0_1").capabilities = { brightness: true, color_temp: false, color: true };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    // what the server of 0.3.2 sends for a blue light in colour mode "rgb" or "xy" (test_x11)
    const blue = (id, attributes) => ({ entity_id: id, name: id, state: "on", attributes, issue: null });
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [
      blue("light.r0_0", { brightness: 128, color_mode: "rgb", rgb_color: [0, 0, 255], hs_color: [240, 100] }),
      blue("light.r0_1", { brightness: 128, color_mode: "xy", xy_color: [0.136, 0.04], hs_color: [240, 100] })] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const field = (name, id) => q(root, `[data-field="${name}"][data-entity="${id}"]`);
    const move = async (name, id, value) => { setValue(field(name, id), String(value)); await tick(); return sent(s, "set_entry").at(-1).values; };
    const stored = (id) => s.scene.sequence[0].entries.find((e) => e.entity_id === id).attributes;

    // white and colour: the stored blue is shown as colour
    const mode = [...field("light_mode", "light.r0_0").querySelectorAll("button")].find((b) => b.getAttribute("aria-checked") === "true");
    assert.strictEqual(mode.dataset.value, "colour"); // FIXED
    assert.strictEqual(field("hue", "light.r0_0").value, "240"); // FIXED
    assert.ok(!field("color_temp_kelvin", "light.r0_0"));
    same(await move("brightness", "light.r0_0", 10), { brightness: 26 }); // FIXED: only the brightness is sent
    same(stored("light.r0_0").rgb_color, [0, 0, 255]); // FIXED: the blue stays

    // colour only: the stored blue is shown with its hue, moving the brightness keeps it
    assert.strictEqual(field("hue", "light.r0_1").value, "240"); // FIXED: blue is 240
    same(await move("brightness", "light.r0_1", 10), { brightness: 26 }); // FIXED
    same(stored("light.r0_1").xy_color, [0.136, 0.04]);
    // the change to white replaces the colour (spec 4.5)
    [...field("light_mode", "light.r0_0").querySelectorAll("button")].find((b) => b.dataset.value === "white").click();
    await tick();
    same(sent(s, "set_entry").at(-1).values, { color_temp_kelvin: 2000 });
    assert.ok(!stored("light.r0_0").rgb_color);
    card.remove();
  }

  // ---------- X11, the other way round: an entry stored as hs_color keeps its colour ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries: [
      { entity_id: "light.r0_0", name: "Light", state: "on", attributes: { brightness: 128, color_mode: "hs", hs_color: [240, 100] }, issue: null }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="g1"]');
    const field = (name) => q(root, `[data-field="${name}"][data-entity="light.r0_0"]`);
    assert.strictEqual(field("hue").value, "240"); // OK
    setValue(field("brightness"), "10");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { brightness: 26 }); // the input sends its own value (spec 4.5, draft 0.10)
    same(s.scene.sequence[0].entries[0].attributes.hs_color, [240, 100]); // OK: the colour stays
    setValue(field("hue"), "120");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { hue: 120, saturation: 100 }); // the colour is hue and saturation together
    card.remove();
  }

  // ---------- X8, X2 and the message after undo ----------
  {
    const s = world({ lang: "de" });
    s.hass.config = { unit_system: { temperature: "°C" } };
    s.hass.formatEntityState = (st, state) => ({ heat: "Heizen", off: "Aus" })[state ?? st.state];
    s.devices.push({ entity_id: "climate.r0", name: "Thermostat", domain: "climate", area_id: "r0", available: true,
      music_system: false, capabilities: { hvac_modes: ["off", "heat"], min_temp: 7, max_temp: 30 } });
    s.hass.states["climate.r0"] = { entity_id: "climate.r0", state: "heat", attributes: { temperature: 21 } };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    same(card.getGridOptions().columns, "full"); // FIXED (X2)
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="add-step"]');
    await click(root, '[data-action="pick-domain"][data-domain="climate"]');
    same([...root.querySelectorAll('[data-field="hvac_mode"] button')].map((b) => b.textContent), ["Aus", "Heizen"]); // FIXED (X8)
    const temp = q(root, '[data-field="temperature"]');
    assert.strictEqual(temp.type, "text"); // FIXED: no arrows of the browser
    assert.ok(temp.closest("label").textContent.includes("°C"));
    setValue(temp, "21,5");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { hvac_mode: "heat", temperature: 21.5 });
    s.scene.sequence[0].entries = [{ entity_id: "climate.r0", name: "T", state: "heat", attributes: { temperature: 21.5 }, issue: null }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="close-step"]');
    assert.ok(root.textContent.includes("Heizen · 21,5 °C")); // FIXED (X8): in the row of the sequence
    await click(root, '[data-action="done"]');
    s.scene.can_undo = true;
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="undo"]');
    assert.ok(q(root, '[role="status"]').textContent.includes("Der frühere Stand gilt wieder.")); // FIXED (draft 0.9, 5.3)
    const list = w.document.createElement("resident-scenes-card");
    list.setConfig({ scope: "house", view: "list" });
    same(list.getGridOptions().columns, 12); // OK: list and favorites keep their width
    card.remove();
  }

  console.log("card probe 0.3.1 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
