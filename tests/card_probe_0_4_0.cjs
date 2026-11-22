// Stage 4 (room rights, version 0.4.0): the card in jsdom, with the mocked server of world.cjs.
// Run: node tests/card_probe_0_4_0.cjs   (after npm run build)
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { tick, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);
const scene = { id: "s1", name: "Abwesend", entity_id: "scene.abwesend", kind: "resident", editable: true, image_url: null,
  can_undo: false, version: 1 };

(async () => {
  // ---------- room card without room right: only the hint, no scene (spec 5.5, 5.6) ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: false, can_edit: false };
    const card = await make(s, { scope: "area", area: "r1", view: "manage" });
    const root = card.shadowRoot;
    assert.strictEqual(q(root, '[data-hint="no_access"]').textContent.trim(), "Kein Zugriff auf diesen Raum");
    assert.strictEqual(root.querySelectorAll(".row, .tile").length, 0);
    assert.strictEqual(q(root, '[data-action="new"]'), null);
    card.remove();
    // the favorites view stays invisible without the right (spec 4.7, 5.5; 0.4.1, AB4)
    const fav = await make(s, { scope: "area", area: "r1", view: "favorites" });
    assert.strictEqual(fav.shadowRoot.textContent.trim(), "");
    fav.remove();
  }

  // ---------- house card of a limited account with the house right: run only, no edit, no new scene, no heart ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, can_edit: false, scenes: [scene] };
    s.scene = { ...scene, area_id: null, used_in: { scenes: [], slots: [] }, sequence: [] };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    assert.strictEqual(q(root, '[data-action="new"]'), null);
    await click(root, '[data-action="select"][data-id="s1"]');
    assert.ok(q(root, '[data-action="play"]'));
    for (const action of ["edit", "heart", "undo"]) assert.strictEqual(q(root, `[data-action="${action}"]`), null, action);
    card.remove();
  }

  // ---------- room right withdrawn while editing: the next input is rejected, hint, then "Kein Zugriff" ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    assert.ok(q(root, '[data-field="name"]'));
    s.data = { ...s.data, access: false, can_edit: false, scenes: [] };
    s.fail.update = { code: "no_access", message: "No access to this room" };
    setValue(q(root, '[data-field="name"]'), "Spielen");
    await tick();
    assert.strictEqual(sent(s, "update").length, 1); // the input was sent and rejected by the server
    assert.strictEqual(q(root, '[data-field="name"]'), null); // the editor is closed
    assert.ok(root.textContent.includes("Ihr Zugriff auf diesen Raum wurde entzogen."));
    assert.ok(q(root, '[data-hint="no_access"]'));
    // given back: the hint goes
    s.data = { ...s.data, access: true, can_edit: true };
    s.notify({ changed: true });
    await tick();
    assert.ok(!root.textContent.includes("entzogen"));
    assert.strictEqual(q(root, '[data-hint="no_access"]'), null);
    card.remove();
  }

  // ---------- rights: all rooms or a tree of floor and room, and the house right (spec 3) ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const info = {
      accounts: [{ user_id: "u1", name: "Kind", kind: "resident", can_edit: true }],
      room_rights: { u1: { rooms: null, house: true } },
      floors: [{ floor_id: "og", name: "Obergeschoss" }],
      areas: [{ area_id: "kind", name: "Kinderzimmer", floor_id: "og" }, { area_id: "bad", name: "Bad", floor_id: "og" },
        { area_id: "garten", name: "Garten", floor_id: null }],
    };
    const callWS = s.hass.callWS;
    s.hass.callWS = async (msg) => {
      if (msg.type === "resident_scenes/rights") return (s.calls.push(msg), JSON.parse(JSON.stringify(info)));
      if (msg.type === "resident_scenes/set_rooms") {
        s.calls.push(msg);
        info.room_rights[msg.user_id] = { rooms: msg.rooms, house: msg.house };
        return null;
      }
      return callWS(msg);
    };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="rights"]');
    const sw = (field, id) => q(root, `[data-field="${field}"][data-entity="${id}"]`);
    assert.strictEqual(sw("all_rooms", "u1").getAttribute("aria-checked"), "true");
    assert.strictEqual(sw("house_right", "u1").getAttribute("aria-checked"), "true");
    assert.strictEqual(sw("room", "u1:kind"), null); // no tree while the account has all rooms
    await click(root, '[data-field="all_rooms"][data-entity="u1"]');
    same(sent(s, "set_rooms").at(-1), { type: "resident_scenes/set_rooms", user_id: "u1", rooms: [], house: true });
    await tick();
    assert.ok(root.textContent.includes("Räume ohne Etage"));
    assert.ok(sw("room", "u1:garten"));
    // a tick at the floor sets all its rooms: two rooms of one floor (acceptance "Verwaltung")
    await click(root, '[data-field="floor"][data-entity="u1:og"]');
    same(sent(s, "set_rooms").at(-1).rooms, ["kind", "bad"]);
    await tick();
    assert.strictEqual(sw("room", "u1:bad").getAttribute("aria-checked"), "true");
    await click(root, '[data-field="room"][data-entity="u1:bad"]');
    same(sent(s, "set_rooms").at(-1).rooms, ["kind"]);
    await tick();
    assert.strictEqual(sw("floor", "u1:og").getAttribute("aria-checked"), "false");
    await click(root, '[data-field="house_right"][data-entity="u1"]');
    same(sent(s, "set_rooms").at(-1), { type: "resident_scenes/set_rooms", user_id: "u1", rooms: ["kind"], house: false });
    card.remove();
  }

  console.log("card probe 0.4.0 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
