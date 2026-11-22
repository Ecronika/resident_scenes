// Version 0.5.0: the favorites grid, the tiles "Alles ein" and "Alles aus", the feedback on a tile,
// the rights view and show_rights (spec 5.1, 5.2, acceptance "Ansichten"), in jsdom with tests/world.cjs.
// Run: node card_probe_0_5_0.cjs <path of the repository>   (after npm run build)
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, tick, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const scene = (i, area = "r1") => ({ id: `s${i}`, name: `Szene ${i}`, area_id: area, entity_id: `scene.s${i}`, kind: "resident",
  image: null, image_url: null, editable: true, can_undo: false, version: 1, transition: null, content_released: false });

function filled(n, slots = Math.max(4, n), area = "r1") {
  const s = world({ lang: "de" });
  const scenes = Array.from({ length: n }, (_, i) => scene(i + 1, area));
  s.data = { ...s.data, access: true, scenes, favorite_slots: slots,
    favorites: [...scenes.map((x) => x.id), ...Array(slots - n).fill(null)] };
  return s;
}

// the card measured at a width, as the ResizeObserver reports it
async function at(card, width) {
  card._width = width;
  await tick();
  const grid = q(card.shadowRoot, ".fav .tiles");
  const cols = grid ? /repeat\((\d+), (\d+)px\)/.exec(grid.getAttribute("style")) : null;
  return cols ? { perRow: +cols[1], edge: +cols[2] } : null;
}

(async () => {
  // ---------- Startseite: six of eight house slots, columns auto, tile_size 135 ----------
  {
    const s = filled(6, 8, null);
    const card = await make(s, { scope: "house", view: "favorites", columns: "auto", tile_size: 135 });
    same(await at(card, 1200), { perRow: 6, edge: 135 }, "1200 px: six in one row of 135 px");
    same(await at(card, 500), { perRow: 3, edge: 135 }, "500 px: three and three");
    assert.strictEqual(card.shadowRoot.querySelectorAll(".tile").length, 6);
    assert.ok(!q(card.shadowRoot, ".fav.with-side"), "left-aligned, no side column");
  }
  // ---------- Vier in einer Zeile: columns 4, and the same without any grid option ----------
  for (const extra of [{ columns: 4 }, {}]) {
    const card = await make(filled(4), { scope: "area", area: "r1", view: "favorites", ...extra });
    same(await at(card, 500), { perRow: 4, edge: 104 }, `500 px ${JSON.stringify(extra)}: four in a row`);
    same(await at(card, 360), { perRow: 2, edge: extra.columns ? 80 : 104 }, `360 px ${JSON.stringify(extra)}: two and two`);
  }
  // even rows: five as three and two, six as three and three
  {
    const card = await make(filled(5), { scope: "area", area: "r1", view: "favorites", columns: 4 });
    same((await at(card, 500)).perRow, 3, "five tiles: three and two");
  }
  // ---------- Raumseite: columns 2, all_off, all_on ----------
  {
    const s = filled(4);
    s.data.scenes.push({ ...scene(9), id: "tpl_r1_on", name: "Alles ein", kind: "installer", entity_id: "scene.alles_ein" });
    const services = [];
    s.hass.callService = async (domain, service, data) => { services.push([domain, service, data]); };
    const card = await make(s, { scope: "area", area: "r1", view: "favorites", columns: 2, all_off: true, all_on: "tpl_r1_on" });
    const root = card.shadowRoot;
    same(await at(card, 500), { perRow: 2, edge: 104 }, "500 px: two and two beside the column");
    assert.ok(q(root, ".fav.with-side"), "free space between column and favorites");
    const side = [...root.querySelectorAll(".side .tile")].map((t) => t.getAttribute("aria-label"));
    same(side, ["Alles ein", "Alles aus"], "Alles ein over Alles aus");
    same(await at(card, 320), { perRow: 2, edge: 87 }, "320 px: three tiles in a row, none below 80 px");
    assert.strictEqual(root.querySelectorAll(".tile").length, 6);
    await click(root, '[data-action="all-on"]');
    same(services.at(-1), ["scene", "turn_on", { entity_id: "scene.alles_ein" }], "Alles ein runs its scene");
    assert.ok(q(root, '[data-action="all-on"].played .done'), "the tile shows the run");
    await click(root, '[data-action="all-off"]');
    same(services.at(-1), ["resident_scenes", "all_off", { area_id: "r1" }], "Alles aus runs the function");
    assert.ok(q(root, '[data-action="all-off"].played'));
    // a scene that does not exist: no tile "Alles ein"; the column stands without favorites
    const none = filled(0);
    const lone = await make(none, { scope: "area", area: "r1", view: "favorites", all_on: "nowhere", all_off: true });
    same([...lone.shadowRoot.querySelectorAll(".tile")].map((t) => t.dataset.action), ["all-off"]);
    // a released scene of the room by its entity id, e.g. a KNX scene
    const knx = filled(0);
    knx.data.foreign_scenes = [{ entity_id: "scene.knx_on", name: "KNX ein", area_id: "r1", knx: true }];
    const k = await make(knx, { scope: "area", area: "r1", view: "favorites", all_on: "scene.knx_on" });
    assert.strictEqual(q(k.shadowRoot, '[data-action="all-on"]').getAttribute("aria-label"), "KNX ein");
    // the house has no such column
    const house = await make(filled(0, 4, null), { scope: "house", view: "favorites", all_off: true });
    assert.strictEqual(house.shadowRoot.querySelector(".card"), null);
  }
  // ---------- Rückmeldung an der Kachel, and a failed run is reported ----------
  {
    const s = filled(1);
    const card = await make(s, { scope: "area", area: "r1", view: "favorites" });
    await click(card.shadowRoot, '[data-action="play"]');
    assert.ok(q(card.shadowRoot, ".tile.played .done"), "the tile shows the run");
    assert.ok(q(card.shadowRoot, ".tile.played span"), "the name stays");
    s.hass.callService = async () => { throw { code: "unauthorized" }; };
    await click(card.shadowRoot, '[data-action="play"]');
    assert.ok(q(card.shadowRoot, '.error[role="alert"]'), "a failed run is reported");
  }
  // ---------- Berechtigungen als eigene Ansicht, show_rights ----------
  {
    const info = { accounts: [{ user_id: "u1", name: "Kind", kind: "resident", can_edit: true }],
      room_rights: { u1: { rooms: null, house: true } }, floors: [], areas: [{ area_id: "r1", name: "Küche", floor_id: null }] };
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const callWS = s.hass.callWS;
    s.hass.callWS = async (msg) => (msg.type === "resident_scenes/rights" ? JSON.parse(JSON.stringify(info)) : callWS(msg));
    const card = await make(s, { view: "rights" }); // no scope, no area
    await tick(50);
    const root = card.shadowRoot;
    assert.ok(q(root, '[data-field="right"][data-entity="u1"]'), "edit right");
    assert.ok(q(root, '[data-field="all_rooms"][data-entity="u1"]'), "rooms");
    assert.ok(q(root, '[data-field="house_right"][data-entity="u1"]'), "house right");
    assert.ok(!q(root, '[data-action="back"]'));
    // an account without the role sees nothing
    const plain = world({ lang: "de" });
    plain.data = { ...plain.data, access: true, manages_rights: false };
    const none = await make(plain, { view: "rights" });
    assert.strictEqual(none.shadowRoot.querySelector(".card"), null);
    // manage with show_rights: false has no button, by default it has
    const hidden = await make(s, { scope: "house", view: "manage", show_rights: false });
    assert.ok(!q(hidden.shadowRoot, '[data-action="rights"]'));
    const shown = await make(s, { scope: "house", view: "manage" });
    assert.ok(q(shown.shadowRoot, '[data-action="rights"]'));
  }
  // ---------- options are checked ----------
  {
    const card = w.document.createElement("resident-scenes-card");
    for (const bad of [{ columns: 0 }, { columns: "2" }, { tile_size: 60 }, { view: "tiles" }]) {
      assert.throws(() => card.setConfig({ scope: "house", view: "favorites", ...bad }), undefined, JSON.stringify(bad));
    }
  }
  console.log("card probe 0.5.0 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
