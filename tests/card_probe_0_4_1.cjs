// Review of version 0.4.1 (commit 6740918): the fixes of AB3 and AB4 (AC1, AC2 marked fixed in 0.4.2), the card in jsdom with tests/world.cjs.
// Run: node card_probe_0_4_1.cjs <path of the repository>   (after npm run build)
// Lines marked FINDING show a defect, NOTE a limit or a difference to spec draft 0.16, OK a point that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { tick, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);

// the rights of one account "Kind"; the server answers after `delay` ms and refuses the calls listed in `fail`
function rights(s, rooms, delay = 0, fail = []) {
  const info = {
    accounts: [{ user_id: "u1", name: "Kind", kind: "resident", can_edit: true }],
    room_rights: { u1: { rooms, house: true } },
    floors: [{ floor_id: "eg", name: "Erdgeschoss" }, { floor_id: "og", name: "Obergeschoss" }],
    areas: [{ area_id: "kueche", name: "Küche", floor_id: "eg" }, { area_id: "wohnen", name: "Wohnen", floor_id: "eg" },
      { area_id: "kind", name: "Kinderzimmer", floor_id: "og" }, { area_id: "bad", name: "Bad", floor_id: "og" }],
  };
  const callWS = s.hass.callWS;
  let n = 0;
  s.hass.callWS = async (msg) => {
    if (msg.type === "resident_scenes/rights") {
      await tick(delay);
      return JSON.parse(JSON.stringify(info));
    }
    if (msg.type === "resident_scenes/set_rooms") {
      s.calls.push(msg);
      await tick(delay);
      if (fail.includes(++n)) throw { code: "invalid_area", message: "Unknown room" };
      info.room_rights[msg.user_id] = { rooms: msg.rooms, house: msg.house };
      return null;
    }
    return callWS(msg);
  };
  return info;
}

async function open(s) {
  const card = await make(s, { scope: "house", view: "manage" });
  await click(card.shadowRoot, '[data-action="rights"]');
  await tick(500);
  return card;
}

(async () => {
  // ---------- AB3: three taps in a row, rooms and the house right, all apply ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const info = rights(s, ["kueche", "wohnen", "kind"], 200);
    const card = await open(s);
    const root = card.shadowRoot;
    const sw = (field, id) => q(root, `[data-field="${field}"][data-entity="${id}"]`);
    sw("room", "u1:kueche").click();
    await tick(100);
    sw("house_right", "u1").click();
    await tick(100);
    sw("floor", "u1:og").click(); // the floor adds the bathroom
    await tick(1500);
    // OK: the calls go out one after the other, each with everything chosen so far
    same(sent(s, "set_rooms").map((m) => [m.rooms, m.house]),
      [[["wohnen", "kind"], true], [["wohnen", "kind"], false], [["wohnen", "kind", "bad"], false]]);
    same(info.room_rights.u1, { rooms: ["wohnen", "kind", "bad"], house: false });
    assert.strictEqual(sw("room", "u1:bad").getAttribute("aria-checked"), "true");
    assert.strictEqual(sw("house_right", "u1").getAttribute("aria-checked"), "false");
    card.remove();
  }

  // ---------- AB3: the switch itself moves at once, before the server has answered ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const info = rights(s, ["kueche", "wohnen", "kind"], 200);
    const card = await open(s);
    const root = card.shadowRoot;
    const room = (id) => q(root, `[data-field="room"][data-entity="u1:${id}"]`);
    room("kueche").click();
    await tick(150);
    // FIXED AC1: the card draws the tap at once, while both answers are still on their way
    assert.strictEqual(room("kueche").getAttribute("aria-checked"), "false");
    // a second tap on the same switch now undoes the first one and gives the kitchen back
    room("kueche").click();
    await tick(20);
    assert.strictEqual(room("kueche").getAttribute("aria-checked"), "true");
    await tick(1200);
    same(sent(s, "set_rooms").map((m) => m.rooms), [["wohnen", "kind"], ["wohnen", "kind", "kueche"]]);
    same(info.room_rights.u1.rooms, ["wohnen", "kind", "kueche"]); // OK: the stored right is the last tap
    assert.strictEqual(room("kueche").getAttribute("aria-checked"), "true");
    card.remove();
  }

  // ---------- AB3: a refused call does not stop the ones after it ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const info = rights(s, ["kueche", "wohnen", "kind"], 100, [1]); // the server refuses the first call
    const card = await open(s);
    const root = card.shadowRoot;
    const room = (id) => q(root, `[data-field="room"][data-entity="u1:${id}"]`);
    room("kueche").click();
    await tick(50);
    room("wohnen").click();
    await tick(900);
    // OK: the second call carries both changes and is stored; the card shows what is stored
    same(info.room_rights.u1.rooms, ["kind"]);
    assert.strictEqual(room("kueche").getAttribute("aria-checked"), "false");
    assert.strictEqual(room("wohnen").getAttribute("aria-checked"), "false");
    card.remove();
  }

  // ---------- AB4: the house right is taken away while a house scene is open ----------
  {
    const s = world({ lang: "de" });
    const scene = { id: "s1", name: "Abwesend", entity_id: "scene.abwesend", kind: "resident", editable: true,
      image_url: null, can_undo: false, version: 1 };
    s.data = { ...s.data, access: true, can_edit: false, scenes: [scene] };
    s.scene = { ...scene, area_id: null, used_in: { scenes: [], slots: [] }, sequence: [] };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="select"][data-id="s1"]');
    assert.ok(q(root, '[data-action="play"]'));
    s.data = { ...s.data, access: false, scenes: [] };
    s.notify({ changed: true });
    await tick(100);
    // OK: the scene view closes and the card names the house scenes
    assert.strictEqual(q(root, '[data-action="play"]'), null);
    assert.strictEqual(q(root, '[data-hint="no_access"]').textContent.trim(), "Kein Zugriff auf die Haus-Szenen");
    // FIXED AC2: the line above it names the house scenes too
    assert.strictEqual(q(root, ".error").textContent.trim(), "Ihr Zugriff auf die Haus-Szenen wurde entzogen.");
    card.remove();
  }

  // ---------- AB4: a favorites view that loses the right disappears, and comes back with the right ----------
  {
    const s = world({ lang: "de" });
    const scene = { id: "s1", name: "Abend", entity_id: "scene.abend", kind: "resident", editable: true,
      image_url: null, can_undo: false, version: 1 };
    s.data = { ...s.data, access: true, scenes: [scene], favorites: ["s1", null, null, null] };
    const card = await make(s, { scope: "area", area: "r1", view: "favorites" });
    const root = card.shadowRoot;
    assert.strictEqual(root.querySelectorAll(".tile").length, 1);
    const shown = s.data;
    s.data = { ...s.data, access: false, scenes: [], favorites: [null, null, null, null] };
    s.notify({ changed: true });
    await tick(100);
    assert.strictEqual(root.textContent.trim(), ""); // OK: nothing is left, no hint
    s.data = shown;
    s.notify({ changed: true });
    await tick(100);
    assert.strictEqual(root.querySelectorAll(".tile").length, 1); // OK: back without a reload
    card.remove();
  }

  console.log("card probe 0.4.1 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
