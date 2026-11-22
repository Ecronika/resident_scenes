// Review of version 0.4.0 (commit 01f8349), stage 4: the card in jsdom, with the mocked server of tests/world.cjs.
// Run: node tests/card_probe_0_4_0_review.cjs   (after npm run build)
// Lines marked FIXED show a finding fixed in 0.4.1 (spec draft 0.16), NOTE a limit or a difference to the spec,
// OK a point that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { tick, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);

// the rights of one account "Kind" in a house with two floors; the server answers after `delay` ms
function rights(s, rooms, delay = 0) {
  const info = {
    accounts: [{ user_id: "u1", name: "Kind", kind: "resident", can_edit: true }],
    room_rights: { u1: { rooms, house: true } },
    floors: [{ floor_id: "eg", name: "Erdgeschoss" }, { floor_id: "og", name: "Obergeschoss" }],
    areas: [{ area_id: "kueche", name: "Küche", floor_id: "eg" }, { area_id: "wohnen", name: "Wohnen", floor_id: "eg" },
      { area_id: "kind", name: "Kinderzimmer", floor_id: "og" }, { area_id: "bad", name: "Bad", floor_id: "og" }],
  };
  const callWS = s.hass.callWS;
  s.hass.callWS = async (msg) => {
    if (msg.type === "resident_scenes/rights") {
      await tick(delay);
      return JSON.parse(JSON.stringify(info));
    }
    if (msg.type === "resident_scenes/set_rooms") {
      s.calls.push(msg);
      await tick(delay);
      info.room_rights[msg.user_id] = { rooms: msg.rooms, house: msg.house };
      return null;
    }
    return callWS(msg);
  };
  return info;
}

(async () => {
  // ---------- AB3: two switches set shortly after each other, both apply ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    const info = rights(s, ["kueche", "wohnen", "kind"], 200); // 200 ms per answer, as over a remote connection
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="rights"]');
    await tick(300);
    const room = (id) => q(root, `[data-field="room"][data-entity="u1:${id}"]`);
    assert.strictEqual(room("kueche").getAttribute("aria-checked"), "true");
    // the main user takes away kitchen and living room, one tap after the other
    room("kueche").click();
    await tick(250); // a quarter of a second between two taps
    room("wohnen").click();
    await tick(1000);
    // FIXED AB3: the card applies each tap at once and sends the calls one after the other, each built
    // from the state chosen last. Both changes apply.
    same(sent(s, "set_rooms").map((m) => m.rooms), [["wohnen", "kind"], ["kind"]]);
    same(info.room_rights.u1.rooms, ["kind"]);
    assert.strictEqual(room("kueche").getAttribute("aria-checked"), "false"); // the card shows what is stored
    assert.strictEqual(room("wohnen").getAttribute("aria-checked"), "false");
    card.remove();
  }

  // ---------- "Alle Räume" off: the account has no room at once ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: true, manages_rights: true };
    rights(s, null);
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="rights"]');
    await click(root, '[data-field="all_rooms"][data-entity="u1"]');
    // NOTE: the first tap takes every room away, before a room is ticked (spec 3: a change applies at once)
    same(sent(s, "set_rooms").at(-1).rooms, []);
    await tick();
    // NOTE: a floor with some of its rooms ticked shows "off", there is no state in between
    await click(root, '[data-field="room"][data-entity="u1:kind"]');
    await tick();
    assert.strictEqual(q(root, '[data-field="floor"][data-entity="u1:og"]').getAttribute("aria-checked"), "false");
    card.remove();
  }

  // ---------- favorites view without the right stays invisible, the house card names the house scenes ----------
  {
    const s = world({ lang: "de" });
    s.data = { ...s.data, access: false, can_edit: false };
    // FIXED AB4: the favorites view of an account without the right stays invisible, like an empty one (spec 4.7, 5.5)
    const room = await make(s, { scope: "area", area: "r1", view: "favorites" });
    assert.strictEqual(room.shadowRoot.textContent.trim(), "");
    const houseFav = await make(s, { scope: "house", view: "favorites" });
    assert.strictEqual(houseFav.shadowRoot.textContent.trim(), "");
    // FIXED AB4: the house card without the house right says "die Haus-Szenen", not "diesen Raum" (spec 5.5, 5.6)
    const house = await make(s, { scope: "house", view: "manage" });
    assert.strictEqual(q(house.shadowRoot, '[data-hint="no_access"]').textContent.trim(), "Kein Zugriff auf die Haus-Szenen");
    // OK: a room card without the right keeps the room hint
    const manage = await make(s, { scope: "area", area: "r1", view: "manage" });
    assert.strictEqual(q(manage.shadowRoot, '[data-hint="no_access"]').textContent.trim(), "Kein Zugriff auf diesen Raum");
    // OK: with the right and no slot in use the favorites view stays invisible, as before
    s.data = { ...s.data, access: true };
    const empty = await make(s, { scope: "area", area: "r2", view: "favorites" });
    assert.strictEqual(empty.shadowRoot.textContent.trim(), "");
    for (const card of [room, houseFav, house, manage, empty]) card.remove();
  }

  // ---------- English wording of the house hint ----------
  {
    const s = world({ lang: "en" });
    s.data = { ...s.data, access: false, can_edit: false };
    const house = await make(s, { scope: "house", view: "manage" });
    assert.strictEqual(q(house.shadowRoot, '[data-hint="no_access"]').textContent.trim(), "No access to the house scenes");
    house.remove();
  }

  console.log("card probe 0.4.0 (review, fixed in 0.4.1) passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
