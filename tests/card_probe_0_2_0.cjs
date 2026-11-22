// Review checks of the card from version 0.2.0, carried over to the step editor of 0.3.0.
// Run: npm ci && npm run build && node tests/card_probe_0_2_0.cjs
// Dropped with 0.3.0 (behaviour removed by the design): the per-device mode select (keep/capture/off/set),
// the end of the live preview on cancel or removal (S3), the "save" of five inputs (B3 now has no save),
// the error of a save naming a scene (S2, inputs are checked one by one now), arrow buttons of the order.
const assert = require("node:assert");
const { w, src, tick, setValue, world, make, types, last, q, click } = require("./world.cjs");

const scene = (sequence, extra = {}) => ({ id: "s1", name: "Abend", area_id: "r2", entity_id: "scene.abend", kind: "resident",
  editable: true, can_undo: false, version: 3, image: null, image_url: null, transition: null, content_released: false,
  used_in: { scenes: [], slots: [] }, sequence, ...extra });

(async () => {
  // ---------- N2: Home Assistant restarts, the integration is not loaded yet ----------
  {
    const s = world();
    s.failList = 1;
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    assert.match(root.textContent, /Nicht aktuell/, "hint also without data");
    await tick(2200); // the card tries again by itself
    assert.ok(q(root, '[data-action="new"]'), "N2: content appears without a reload");
    assert.strictEqual(s.subs, 1, "N2: subscribed after the first success");
    s.listeners.ready(); // connection is back after a restart
    await tick();
    assert.strictEqual(s.subs, 2, "N2: subscription renewed after a reconnect");
    card.remove();
  }

  // ---------- N3 and N8: reasons in the opened step, size of the controls ----------
  {
    const s = world();
    s.data.scenes = [{ id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null }];
    s.scene = scene([{ id: "g1", type: "group", domain: "light", area_id: "r2", entries: [
      { entity_id: "light.r2_0", state: "on", attributes: { brightness: 255 }, issue: null },
      { entity_id: "light.gone", name: "Old lamp", state: "on", attributes: {}, issue: "missing" },
      { entity_id: "light.r2_1", state: "on", attributes: {}, issue: "not_released" },
      { entity_id: "light.r5_0", state: "on", attributes: {}, issue: "other_area" },
    ] }]);
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select"]');
    await click(root, '[data-action="edit"]');
    await click(root, '[data-action="open"][data-id="g1"]');
    const row = (eid) => q(root, `[data-field="pick"][data-entity="${eid}"]`).closest(".row");
    assert.strictEqual(row("light.gone").querySelector(".badge").textContent, "Gerät fehlt", "N3");
    assert.strictEqual(row("light.r2_1").querySelector(".badge").textContent, "Nicht freigegeben", "N3");
    assert.strictEqual(row("light.r5_0").querySelector(".badge").textContent, "In anderem Raum", "N3");
    assert.ok(row("light.gone").textContent.includes("Old lamp"), "a missing device is named by the server");
    assert.ok(!row("light.r5_0").querySelector(".controls"), "a flagged entry cannot be changed");
    assert.ok(row("light.r2_0").querySelector('[data-field="brightness"]'), "V4: a ticked device shows its stored value");
    assert.strictEqual(row("light.r2_0").querySelector("output").textContent.trim(), "100 %");
    // a flagged entry can be removed
    await click(root, '[data-field="pick"][data-entity="light.r5_0"]');
    assert.strictEqual(last(s, "remove_entry").entity_id, "light.r5_0");
    const css = w.customElements.get("resident-scenes-card").styles.cssText;
    assert.match(css, /button, input\[type=number\], input:not\(\[type\]\) \{ min-height: 44px/, "N8: 44 px");
    assert.match(css, /\.handle \{[^}]*min-height: 44px/);
    card.remove();
  }

  // ---------- B3: "Abwesend" in four inputs, nothing switches ----------
  {
    const s = world();
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]'); // 1
    setValue(q(root, '[data-field="name"]'), "Abwesend"); await tick(); // 2
    await click(root, '[data-action="house-off"][data-domain="light"]'); // 3: 60 light circuits
    await click(root, '[data-action="house-off"][data-domain="cover"]'); // 4: 30 blinds
    const inputs = s.calls.filter((c) => !["list", "scene", "devices"].includes(c.type.split("/")[1]));
    assert.deepStrictEqual(inputs.map((c) => c.type.split("/")[1]), ["create", "update", "house_off", "house_off"]);
    assert.ok(!s.calls.some((c) => c.live), "B3: nothing switched");
    card.remove();
  }

  // ---------- S2: a called scene that is no room scene any more ----------
  {
    const s = world();
    s.data.scenes = [{ id: "s1", name: "Zuhause", entity_id: "scene.zuhause", kind: "resident", editable: true, image_url: null }];
    s.scene = scene([{ id: "c1", type: "scene", scene_id: "x", name: "Kochen", area_id: null, issue: "no_room_scene" }], { area_id: null });
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select"]');
    assert.match(root.textContent, /Keine Raumszene mehr/, "S2: marked in the scene view");
    await click(root, '[data-action="edit"]');
    assert.match(root.textContent, /Keine Raumszene mehr/, "S2: marked in the editor");
    assert.ok(!q(root, '[data-action="open"][data-id="c1"]'), "a scene step has nothing to open");
    await click(root, '[data-action="remove-step"][data-id="c1"]'); // S2: can be removed
    assert.strictEqual(last(s, "remove_step").step_id, "c1");
    assert.match(root.textContent, /Noch keine Schritte/);
    card.remove();
  }

  // ---------- direct values: white and colour, the controls follow the program ----------
  {
    const s = world();
    s.data.scenes = [{ id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null }];
    s.scene = scene([{ id: "g1", type: "group", domain: "light", area_id: "r2", entries: [] }]);
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select"]');
    await click(root, '[data-action="edit"]');
    await click(root, '[data-action="open"][data-id="g1"]');
    const field = (name) => q(root, `[data-field="${name}"][data-entity="light.r2_0"]`);
    assert.ok(field("brightness") && field("light_mode") && field("hue") && field("saturation"), "unticked shows the current state");
    await click(root, '[data-field="light_mode"][data-entity="light.r2_0"] [data-value="white"]');
    const msg = last(s, "set_entry");
    assert.deepStrictEqual(JSON.parse(JSON.stringify(msg.values)), { brightness: 128, color_temp_kelvin: 2000 }, "only one of them is sent");
    assert.strictEqual(msg.mode, "set");
    assert.strictEqual(q(root, '[data-field="pick"][data-entity="light.r2_0"]').getAttribute("aria-checked"), "true", "an input ticks the device");
    assert.ok(field("color_temp_kelvin") && !field("hue"), "white mode");
    // the server sets the light off (another editor, "Alle aus"): the switch follows
    s.scene.sequence[0].entries[0].state = "off";
    s.notify({}); await tick();
    assert.strictEqual(field("on").getAttribute("aria-checked"), "false", "S12 Nr. 4: controls follow the server");
    await click(root, '[data-field="on"][data-entity="light.r2_0"]');
    assert.strictEqual(last(s, "set_entry").mode, "set", "switching on stores a value");
    card.remove();
  }

  // ---------- every state change in the house redraws the card ----------
  {
    const s = world();
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
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
    assert.strictEqual(renders, 100); // left out by decision (S12 Nr. 5)
    console.log(`house editor: ${renders} redraws for 100 unrelated state changes, ${(ms / 100).toFixed(1)} ms each in jsdom`);
    card.remove();
  }

  // ---------- spec 5.7: drag a step onto another, auto-scroll near the edge ----------
  {
    const s = world();
    s.data.scenes = [{ id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null }];
    s.scene = scene([
      { id: "a", type: "group", domain: "light", area_id: "r2", entries: [] },
      { id: "b", type: "delay", seconds: 5 },
      { id: "c", type: "group", domain: "cover", area_id: "r2", entries: [] },
    ]);
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select"]');
    await click(root, '[data-action="edit"]');
    let scrolled = 0;
    root.querySelectorAll(".row.order").forEach((row, i) => {
      row.getBoundingClientRect = () => ({ top: i * 50, bottom: i * 50 + 50 });
      row.scrollIntoView = () => scrolled++;
    });
    const handle = root.querySelectorAll('[data-action="drag"]')[0];
    const pointer = (type, y) => handle.dispatchEvent(new w.MouseEvent(type, { bubbles: true, clientY: y }));
    pointer("pointerdown", 60); pointer("pointermove", 60); pointer("pointermove", 120); await tick();
    assert.ok(root.querySelectorAll(".row.order")[2].classList.contains("drop"), "drop target marked");
    pointer("pointermove", 10); // near the top edge
    assert.ok(scrolled > 0, "the list scrolls near its edge");
    pointer("pointermove", 120);
    pointer("pointerup", 120); await tick();
    assert.deepStrictEqual({ ...last(s, "move_step") }, { type: "resident_scenes/move_step", scene_id: "s1", edit: card._edit.id, step_id: "a", index: 2 });
    assert.deepStrictEqual(s.scene.sequence.map((x) => x.id), ["b", "c", "a"]);
    card.remove();
  }

  // ---------- parts that must not come back ----------
  assert.ok(/pointerdown/.test(src), "spec 5.7: order by dragging");
  assert.ok(!/preview|\/save|save_copy|data-action="up"/.test(src), "no preview, no save, no arrow buttons");
  assert.ok(!/preview_favorite|play_favorite/.test(src), "spec 5.4: no play button for a favorite");
  assert.ok(!src.includes("getConfigElement"), "no visual card editor, YAML only");
  assert.ok(!src.includes("friendly_name"), "names come from formatEntityName or the server");

  console.log("card probe 0.2.0 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
