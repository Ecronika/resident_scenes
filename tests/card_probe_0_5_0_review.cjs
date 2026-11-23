// Review of version 0.5.0 (commit c96d95a): the favorites grid after the row was shortened, the report of a
// failed "Alles aus", the rights view when the role goes. Lines marked FINDING show a defect, NOTE a limit,
// OK a point that holds. Every check passes against 0.5.0. Lines marked FIXED were flipped with version 0.6.0.
// Run: node card_probe_0_5_0_review.cjs <path of the repository>   (after npm run build)
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { tick, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const scene = (i) => ({ id: `s${i}`, name: `Szene ${i}`, area_id: "r1", entity_id: `scene.s${i}`, kind: "resident",
  image: null, image_url: null, editable: true, can_undo: false, version: 1, transition: null, content_released: false });

function filled(n) {
  const s = world({ lang: "de" });
  const scenes = Array.from({ length: n }, (_, i) => scene(i + 1));
  s.data = { ...s.data, access: true, scenes, favorite_slots: Math.max(4, n),
    favorites: [...scenes.map((x) => x.id), ...Array(Math.max(4, n) - n).fill(null)] };
  return s;
}

// the grid at a card width, as the ResizeObserver reports it; 34 px of it are padding and border
async function at(card, width) {
  card._width = width;
  await tick();
  const cols = /repeat\((\d+), (\d+)px\)/.exec(q(card.shadowRoot, ".fav .tiles").getAttribute("style"));
  return { perRow: +cols[1], edge: +cols[2] };
}
const room = { scope: "area", area: "r1", view: "favorites" };

(async () => {
  // ---------- 1 the edge after the row was shortened (spec 5.2 "Schmale Karte") ----------
  {
    const four = await make(filled(4), { ...room, columns: 4 });
    const auto = await make(filled(4), room);
    same(await at(auto, 360), { perRow: 2, edge: 104 }, "OK: without options two and two of 104 px");
    // FIXED (AD2): the same four tiles with columns: 4 stand two and two as well, now 104 px,
    // as two tiles of 104 px need 220 of the 326 px inside the card
    same(await at(four, 360), { perRow: 2, edge: 104 }, "columns 4 at 360 px");
    assert.ok(2 * 104 + 12 <= 360 - 34);
    // the room page below 298 px: one favorite beside the column, both 104 px, as they fit
    const s = filled(4);
    s.data.scenes.push({ ...scene(9), id: "tpl_on", name: "Alles ein", kind: "installer", entity_id: "scene.on" });
    const side = await make(s, { ...room, columns: 2, all_off: true, all_on: "tpl_on" });
    same(await at(side, 320), { perRow: 2, edge: 87 }, "OK: 320 px, three tiles in a row");
    same(await at(side, 300), { perRow: 2, edge: 80 }, "OK: 300 px, still three in a row, now 80 px");
    same(await at(side, 290), { perRow: 1, edge: 104 }, "FIXED (AD2): 290 px, two tiles of 104 px in a row");
    assert.ok(2 * 104 + 12 <= 290 - 34);
    console.log("FIXED AD2: after the row is shortened the tiles grow to what fits, at most tile_size");
  }
  // ---------- 2 rows are filled evenly, tile_size holds ----------
  {
    same(await at(await make(filled(5), room), 500), { perRow: 3, edge: 104 }, "OK: five as three and two");
    same(await at(await make(filled(6), { ...room, columns: 4 }), 500), { perRow: 3, edge: 104 }, "OK: six as three and three");
    same(await at(await make(filled(7), room), 1000), { perRow: 7, edge: 104 }, "OK: one row when all fit");
    same(await at(await make(filled(4), { ...room, tile_size: 135 }), 320), { perRow: 2, edge: 135 }, "OK: 135 px at 320 px");
    console.log("OK: rows are filled evenly and no tile is larger than tile_size");
  }
  // ---------- 3 a failed "Alles aus" is reported, the next run takes the report away ----------
  {
    const s = filled(1);
    const card = await make(s, { ...room, all_off: true });
    s.hass.callService = async () => { throw { code: "unauthorized" }; };
    await click(card.shadowRoot, '[data-action="all-off"]');
    const alert = q(card.shadowRoot, '.error[role="alert"]');
    assert.ok(alert && alert.textContent.includes("Alles aus"), "the failed run is reported by name");
    assert.ok(!q(card.shadowRoot, '[data-action="all-off"].played'), "no mark on the tile");
    s.hass.callService = async () => {};
    await click(card.shadowRoot, '[data-action="all-off"]');
    assert.ok(!q(card.shadowRoot, '.error[role="alert"]') && q(card.shadowRoot, '[data-action="all-off"].played .done'));
    console.log("OK: a refused Alles aus is reported, the next run clears the report and marks the tile");
  }
  // ---------- 4 the mark on a tile is for the eye only ----------
  {
    const card = await make(filled(1), room);
    await click(card.shadowRoot, '[data-action="play"]');
    const tile = q(card.shadowRoot, ".tile.played");
    assert.strictEqual(tile.getAttribute("aria-label"), "Szene 1");
    assert.strictEqual(q(tile, ".done").getAttribute("aria-hidden"), "true");
    // FIXED (AD3): the status field of the card names the scene that ran
    assert.strictEqual(q(card.shadowRoot, '[role="status"]').textContent.trim(), "Ausgelöst: Szene 1");
    console.log("FIXED AD3: a screen reader hears \"Ausgelöst\" with the scene after a tap on a tile");
  }
  // ---------- 5 the rights view goes when the role goes ----------
  {
    const info = { accounts: [{ user_id: "u1", name: "Kind", kind: "resident", can_edit: true }],
      room_rights: { u1: { rooms: null, house: true } }, floors: [], areas: [{ area_id: "r1", name: "Küche", floor_id: null }] };
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const callWS = s.hass.callWS;
    s.hass.callWS = async (msg) => (msg.type === "resident_scenes/rights" ? JSON.parse(JSON.stringify(info)) : callWS(msg));
    const card = await make(s, { view: "rights" });
    await tick(50);
    assert.ok(q(card.shadowRoot, '[data-field="all_rooms"][data-entity="u1"]'));
    s.data = { ...s.data, manages_rights: false };
    s.notify({ changed: true });
    await tick(50);
    assert.strictEqual(card.shadowRoot.querySelector(".card"), null);
    console.log("OK: the rights view shows nothing as soon as the account is no main user any more");
  }
  // ---------- 6 AD5: the frontend swaps in its own registry after the card module ran ----------
  {
    const fs = require("node:fs");
    const { JSDOM } = require("jsdom");
    const w = new JSDOM("<!doctype html><body></body>", { runScripts: "outside-only" }).window;
    w.eval(fs.readFileSync(path.join(repo, "custom_components", "resident_scenes", "frontend", "resident-scenes-card.js"), "utf8"));
    assert.ok(w.customElements.get("resident-scenes-card"), "registered in the registry of the moment");
    const defined = new Map();
    Object.defineProperty(w, "customElements", { configurable: true,
      value: { get: (n) => defined.get(n), define: (n, c) => defined.set(n, c) } });
    defined.set("home-assistant", class {});
    await tick(250);
    assert.ok(defined.get("resident-scenes-card"), "FIXED (AD5): registered again in the frontend's registry");
    w.close();
    console.log("FIXED AD5: the card is registered in the registry the frontend put in place");
  }
  console.log("card probe 0.5.0 review passed");
  process.exit(0);
})().catch((err) => { console.error(err); process.exit(1); });
