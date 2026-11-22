// Review checks of the card from version 0.2.1, carried over to the step editor of 0.3.0.
// Run: npm ci && npm run build && node tests/card_probe_0_2_1.cjs
// Dropped with 0.3.0: "removed counts as cancel" (there is no restore any more, spec 5.4).
const assert = require("node:assert");
const { w, tick, fire, setValue, world, make, last, q, click } = require("./world.cjs");

const summary = { id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true, image_url: null };
const scene = (sequence, extra = {}) => ({ ...summary, area_id: "r2", can_undo: false, version: 3, image: null, transition: null,
  content_released: false, used_in: { scenes: [], slots: [] }, sequence, ...extra });
const editScene = async (s, sequence) => {
  s.data.scenes = [{ ...summary }];
  s.scene = scene(sequence);
  const card = await make(s, { scope: "area", area: "r2", view: "manage" });
  const root = card.shadowRoot;
  await click(root, '[data-action="select"]');
  await click(root, '[data-action="edit"]');
  return { card, root };
};

(async () => {
  // ---------- the card is moved inside the page while somebody edits; leaving sends nothing ----------
  {
    const s = world();
    const { card, root } = await editScene(s, []);
    const parent = card.parentNode;
    const sent = s.calls.length;
    card.remove(); parent.appendChild(card); await tick();
    assert.ok(q(root, '[data-action="done"]'), "T3: the editor is still open");
    card.remove(); await tick();
    const inputs = s.calls.slice(sent).filter((c) => !/\/(list|scene|devices)$/.test(c.type));
    assert.deepStrictEqual(inputs, [], "spec 5.4: nothing is restored or sent when the card goes away");
  }

  // ---------- dragging: cancelled gesture, drop on itself, arrow keys on the handle ----------
  {
    const s = world();
    const { card, root } = await editScene(s, [
      { id: "a", type: "group", domain: "light", area_id: "r2", entries: [] },
      { id: "b", type: "group", domain: "cover", area_id: "r2", entries: [] },
      { id: "c", type: "delay", seconds: 5 },
    ]);
    const stub = () => root.querySelectorAll(".row.order").forEach((row, i) => { row.getBoundingClientRect = () => ({ top: i * 50, bottom: i * 50 + 50 }); });
    const pointer = (index, type, y) => root.querySelectorAll('[data-action="drag"]')[index]
      .dispatchEvent(new w.MouseEvent(type, { bubbles: true, clientY: y }));
    stub();
    pointer(0, "pointerdown", 110); pointer(0, "pointermove", 120); pointer(0, "pointerup", 120); await tick();
    stub();
    pointer(0, "pointerdown", 10); pointer(0, "pointermove", 20); pointer(0, "pointerup", 20); await tick();
    stub();
    pointer(1, "pointerdown", 60); pointer(1, "pointermove", 110); pointer(1, "pointercancel", 110); await tick();
    assert.deepStrictEqual(s.scene.sequence.map((x) => x.id), ["b", "c", "a"], "only the first gesture moved a step (T4)");
    assert.strictEqual(s.calls.filter((c) => c.type.endsWith("/move_step")).length, 1);
    // keyboard: the arrow keys move the step whose handle has the focus, and the focus stays on it
    const handle = q(root, '[data-action="drag"][data-id="a"]');
    handle.focus();
    handle.dispatchEvent(new w.KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
    await tick(); await tick();
    assert.deepStrictEqual({ ...last(s, "move_step") }, { type: "resident_scenes/move_step", scene_id: "s1", edit: card._edit.id, step_id: "a", index: 1 });
    assert.deepStrictEqual(s.scene.sequence.map((x) => x.id), ["b", "a", "c"]);
    assert.strictEqual(root.activeElement?.dataset.id, "a", "focus stays on the moved handle");
    card.remove();
  }

  // ---------- white and colour: a light in white mode reports a colour as well ----------
  {
    const s = world();
    s.hass.states["light.r2_0"].attributes = { brightness: 128, color_mode: "color_temp", color_temp_kelvin: 3000, hs_color: [28, 65] };
    const { card, root } = await editScene(s, [{ id: "g", type: "group", domain: "light", area_id: "r2", entries: [] }]);
    await click(root, '[data-action="open"][data-id="g"]');
    const mode = () => q(root, '[data-field="light_mode"][data-entity="light.r2_0"] [aria-checked="true"]').dataset.value;
    assert.strictEqual(mode(), "white", "opens in the mode of the light");
    const kelvin = q(root, '[data-field="color_temp_kelvin"][data-entity="light.r2_0"]');
    assert.ok(kelvin.closest(".slider").querySelector("output").textContent.includes("3.000 K"), "V5: 3.000 K");
    await click(root, '[data-field="light_mode"][data-entity="light.r2_0"] [data-value="colour"]');
    assert.deepStrictEqual(JSON.parse(JSON.stringify(last(s, "set_entry").values)), { brightness: 128, hue: 30, saturation: 100 }, "only one of them is sent");
    assert.ok(q(root, '[data-field="hue"][data-entity="light.r2_0"]') && !q(root, '[data-field="color_temp_kelvin"][data-entity="light.r2_0"]'));
    card.remove();
  }

  // ---------- inputs follow the server while the focused field keeps its value ----------
  {
    const s = world();
    const { card, root } = await editScene(s, []);
    const name = q(root, '[data-field="name"]');
    name.focus();
    setValue(name, "Abend spät", "input");
    s.scene.transition = 2; s.scene.name = "Abend 2"; // another panel changes the scene
    s.notify({}); await tick();
    assert.strictEqual(root.activeElement, name, "focus kept");
    assert.strictEqual(q(root, '[data-field="name"]').value, "Abend spät", "typed value kept");
    assert.strictEqual(q(root, '[data-field="transition"]').value, "2", "other fields take over the change");
    card.remove();
  }

  // ---------- no friendly_name: names come from formatEntityName or the server ----------
  {
    const s = world();
    delete s.hass.formatEntityName;
    s.hass.states["light.r2_0"].attributes.friendly_name = "Friendly";
    s.devices.find((d) => d.entity_id === "light.r2_0").name = "Server name";
    const { card, root } = await editScene(s, [{ id: "g", type: "group", domain: "light", area_id: "r2", entries: [] }]);
    await click(root, '[data-action="open"][data-id="g"]');
    assert.ok(root.textContent.includes("Server name") && !root.textContent.includes("Friendly"));
    card.remove();
  }

  // ---------- favorite slots: holder named, taken slot asks first, fresh data ----------
  {
    const s = world();
    s.data.scenes = [{ ...summary }, { ...summary, id: "s2", name: "Kino", entity_id: "scene.kino" }];
    s.data.favorites = ["s1", "s2", null, null];
    s.scene = scene([]);
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    assert.deepStrictEqual([...root.querySelectorAll("h3")].map((h) => h.textContent), ["Favoriten", "Szenen"], "V3: favorites on top");
    await click(root, '[data-action="select"][data-id="s1"]');
    assert.ok(q(root, '.row.selected [data-id="s1"]'), "V10: selected row marked");
    assert.match(q(root, '[data-action="heart"]').textContent, /Platz 1/);
    await click(root, '[data-action="heart"]');
    const slots = [...root.querySelectorAll('[data-action="slot"]')].map((b) => b.textContent.trim());
    assert.deepStrictEqual(slots, ["Platz 1 – Abend", "Platz 2 – Kino", "Platz 3 – frei", "Platz 4 – frei"]);
    // a free slot acts at once
    await click(root, '[data-action="slot"][data-slot="2"]');
    assert.deepStrictEqual({ ...last(s, "set_favorite") }, { type: "resident_scenes/set_favorite", scope: "r2", slot: 2, scene_id: "s1" });
    // meanwhile another panel put Kino on slot 4: the dialog decides on fresh data
    s.data = { ...s.data, favorites: [null, null, "s1", "s2"] };
    await click(root, '[data-action="heart"]');
    const before = s.calls.filter((c) => c.type.endsWith("/set_favorite")).length;
    await click(root, '[data-action="slot"][data-slot="3"]');
    assert.match(q(root, ".dialog").textContent, /Platz 4: Kino verliert seinen Platz/, "V2: asks first, names the scene");
    assert.strictEqual(s.calls.filter((c) => c.type.endsWith("/set_favorite")).length, before, "nothing set before the answer");
    await click(root, '[data-action="slot-confirm"]');
    assert.deepStrictEqual({ ...last(s, "set_favorite") }, { type: "resident_scenes/set_favorite", scope: "r2", slot: 3, scene_id: "s1" });
    assert.ok(!q(root, ".dialog"));
    // the heart follows the server
    s.data = { ...s.data, favorites: [null, "s1", null, null] };
    s.notify({}); await tick();
    assert.match(q(root, '[data-action="heart"]').textContent, /Platz 2/);
    card.remove();
  }

  // ---------- wall panel: image URLs are signed anew after a reconnect ----------
  {
    const s = world();
    s.data.scenes = [{ ...summary, image_url: "/img?sig=old" }];
    s.scene = scene([], { image_url: "/img?sig=old" });
    s.images = [{ name: "a.jpg", url: "/lib/a.jpg?sig=old" }];
    const card = await make(s, { scope: "area", area: "r2", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select"]');
    await click(root, '[data-action="edit"]');
    s.data = { ...s.data, scenes: [{ ...summary, image_url: "/img?sig=new" }] };
    s.scene.image_url = "/img?sig=new";
    s.images = [{ name: "a.jpg", url: "/lib/a.jpg?sig=new" }];
    s.listeners.ready(); await tick();
    assert.ok(q(root, ".image-btn img").getAttribute("src").endsWith("sig=new"), "scene image renewed");
    await click(root, '[data-action="image"]');
    assert.ok(q(root, '[data-action="pick-image"][data-name="a.jpg"] img').getAttribute("src").endsWith("sig=new"), "library renewed");
    await click(root, '[data-action="pick-image"][data-name="a.jpg"]');
    assert.strictEqual(last(s, "update").image, "a.jpg", "an image counts at once");
    assert.strictEqual(q(root, 'input[type="file"]'), null, "V10: no browser file field showing");
    // V13: delete asks in a dialog over the card, with one delete button inside it
    await click(root, '[data-action="ask-delete"]');
    assert.ok(q(root, '.overlay [role="alertdialog"] [data-action="delete"]'));
    await click(root, '[data-action="delete"]');
    assert.strictEqual(last(s, "delete").scene_id, "s1");
    assert.ok(!q(root, '[data-action="done"]'));
    card.remove();
  }

  console.log("card probe 0.2.1 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
