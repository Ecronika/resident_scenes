// Review of version 0.3.0 (commit 73251c4), turned into regression checks for 0.3.1: the card in jsdom, with the mocked server of the repository.
// Run: node card_probe_0_3_0.cjs <path to the repository>   (after npm ci && npm run build there)
// FINDING = defect, NOTE = limit, OK = point of functional spec draft 0.8 that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { w, tick, fire, setValue, same, world, make, types, last, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);

(async () => {
  // ---------- W7: plus and minus count from the value last shown ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="add-delay"]');
    assert.strictEqual(s.scene.sequence[0].seconds, 5); // OK: a new delay has 5 seconds
    const plus = q(root, '[data-action="delay-plus"]');
    plus.click(); // three quick taps, faster than the answer of the server
    plus.click();
    plus.click();
    await tick(100);
    same(sent(s, "set_delay").map((c) => c.seconds), [6, 7, 8], "three taps"); // fixed W7
    assert.strictEqual(s.scene.sequence[0].seconds, 8);
    card.remove();
  }

  // ---------- W1 in the card: after its room was deleted a step shows its entries locked ----------
  {
    const s = world({ lang: "de" });
    s.devices.push({ entity_id: "light.loose", name: "Loose", domain: "light", area_id: null, available: true,
      music_system: false, capabilities: { brightness: true } });
    s.hass.states["light.loose"] = { entity_id: "light.loose", state: "on", attributes: { brightness: 128 } };
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    // what the server sends for a scene whose room was deleted: the step has no room any more (fixed W1)
    s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: null,
      entries: [{ entity_id: "light.loose", name: "Loose", state: "on", attributes: { brightness: 26 }, issue: null }] }];
    s.notify({ changed: true });
    await tick();
    assert.ok(root.textContent.includes("Ohne Raum – Licht"));
    await click(root, '[data-action="open"][data-id="g1"]');
    const row = q(root, ".row.device");
    assert.ok(!row.textContent.includes("In anderem Raum"));
    // W2: the light has no room now; "add step" offers rooms only, so it cannot be put into a step again
    await click(root, '[data-action="close-step"]');
    await click(root, '[data-action="add-step"]');
    const rooms = [...root.querySelectorAll('[data-action="pick-room"]')].map((b) => b.dataset.id);
    assert.strictEqual(rooms.length, 31);
    assert.ok(root.querySelector(".pick").textContent.includes("Ohne Raum"), "fixed W2: devices without a room");
    await click(root, '[data-action="add-cancel"]');
    // OK (spec 4.5): a marked entry can be removed, and is not offered again
    await click(root, '[data-action="open"][data-id="g1"]');
    await click(root, '[data-field="pick"][data-entity="light.loose"]');
    same(last(s, "remove_entry"), { type: "resident_scenes/remove_entry", scene_id: "n1", edit: last(s, "create").edit,
      step_id: "g1", entity_id: "light.loose" });
    assert.ok(q(root, ".row.device"), "fixed W2: still offered, as a device without a room");
    card.remove();
  }

  // ---------- V2: the favorite slot dialog names the holder and asks before replacing ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "house", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="done"]');
    const other = { ...s.data.scenes[0], id: "x1", name: "Abend", entity_id: "scene.abend" };
    s.data = { ...s.data, scenes: [...s.data.scenes, other], favorites: ["x1", null, null, null] };
    s.notify({ changed: true });
    await tick();
    same([...root.querySelectorAll("h3")].map((h) => h.textContent).slice(0, 2), ["Favoriten", "Szenen"], "V3: group"); // OK
    await click(root, '[data-action="heart"]');
    const slots = [...root.querySelectorAll('[data-action="slot"]')].map((b) => b.textContent.trim());
    same(slots, ["Platz 1 – Abend", "Platz 2 – frei", "Platz 3 – frei", "Platz 4 – frei"]); // OK (4.7)
    await click(root, '[data-action="slot"][data-slot="0"]');
    assert.strictEqual(sent(s, "set_favorite").length, 0, "nothing set before the answer"); // OK
    assert.ok(q(root, ".dialog").textContent.includes("Abend verliert seinen Platz."));
    await click(root, '[data-action="slot-cancel"]');
    assert.strictEqual(sent(s, "set_favorite").length, 0);
    await click(root, '[data-action="slot"][data-slot="0"]');
    await click(root, '[data-action="slot-confirm"]');
    same(last(s, "set_favorite"), { type: "resident_scenes/set_favorite", scope: "_house", slot: 0, scene_id: "n1" }); // OK
    // keyboard: the slots are buttons, moving the focus sets nothing
    await click(root, '[data-action="heart"]');
    const before = sent(s, "set_favorite").length;
    for (const b of root.querySelectorAll('[data-action="slot"]')) b.focus();
    await tick();
    assert.strictEqual(sent(s, "set_favorite").length, before); // OK (V2)
    await click(root, '[data-action="slot-close"]');
    card.remove();
  }

  // ---------- leaving: nothing is sent, nothing is restored (spec 5.4) ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    await click(root, '[data-action="add-step"]');
    await click(root, '[data-action="pick-domain"][data-domain="light"]');
    q(root, '[data-field="live"]').click();
    await tick();
    const slider = q(root, '[data-field="brightness"][data-entity="light.r0_0"]');
    setValue(slider, "40", "input");
    fire(slider, "change");
    await tick();
    assert.strictEqual(last(s, "set_entry").live, true); // OK: live adjustment
    const count = s.calls.length;
    card.remove(); // the page is left without "Fertig"
    await tick(50);
    assert.strictEqual(s.calls.length, count, "leaving sends nothing"); // OK
    const names = new Set(types(s));
    assert.ok(!names.has("preview") && !names.has("preview_end") && !names.has("save")); // OK: the old commands are gone
  }

  // ---------- music: the favorites are one list (draft 0.9, 5.2) ----------
  {
    const s = world({ lang: "de" });
    s.devices.push({ entity_id: "media_player.r0", name: "Sonos", domain: "media_player", area_id: "r0", available: true,
      music_system: true, capabilities: {} });
    s.hass.states["media_player.r0"] = { entity_id: "media_player.r0", state: "paused", attributes: { volume_level: 0.2 } };
    const favorites = Array.from({ length: 40 }, (_, i) => ({ id: `FV:2/${i}`, name: `Sender ${i}` }));
    const call = s.hass.callWS;
    s.hass.callWS = async (msg) => {
      const result = await call(msg);
      return msg.type.endsWith("/devices") ? { ...result, favorites } : result;
    };
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    s.scene.sequence = [{ id: "m1", type: "group", domain: "media_player", area_id: "r0",
      entries: [{ entity_id: "media_player.r0", name: "Sonos", music: "favorite", volume: 0.2, favorite_id: "FV:2/3",
        favorite_name: "Sender 3", issue: null }] }];
    s.notify({ changed: true });
    await tick();
    await click(root, '[data-action="open"][data-id="m1"]');
    assert.strictEqual(root.querySelectorAll('[data-field="favorite_id"] button').length, 0); // FIXED (0.3.2): no button each
    assert.strictEqual(root.querySelectorAll('select[data-field="favorite_id"] option').length, 40);
    assert.ok(!q(root, '[data-field="live"]'), "no live adjustments for music"); // OK (5.4)
    assert.ok(!q(root, '.row.device [data-action="play"]'), "no play button at the favorite"); // OK
    card.remove();
  }

  // ---------- dialogs: the question does not take the focus, Escape does not answer it ----------
  {
    const s = world({ lang: "de" });
    const card = await make(s, { scope: "area", area: "r0", view: "manage" });
    const root = card.shadowRoot;
    await click(root, '[data-action="new"]');
    const opener = q(root, '[data-action="ask-delete"]');
    opener.focus(); // a browser focuses the button that is pressed
    opener.click();
    await tick();
    const dialog = q(root, '[role="alertdialog"]');
    assert.ok(dialog, "the question is an overlay of its own"); // OK (V13)
    assert.strictEqual(root.activeElement?.dataset.action, "keep-scene"); // fixed V15: focus on the safe answer
    assert.strictEqual(dialog.getAttribute("aria-modal"), "true");
    dialog.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true, composed: true }));
    await tick();
    assert.ok(!q(root, '[role="alertdialog"]'), "Escape answers with the safe answer");
    assert.strictEqual(root.activeElement?.dataset.action, "ask-delete", "the focus goes back");
    assert.strictEqual(sent(s, "delete").length, 0); // OK: "Behalten" deletes nothing
    card.remove();
  }

  // ---------- the styles: targets of 44 px, the image is not cropped in the scene view ----------
  {
    const css = w.customElements.get("resident-scenes-card").styles.cssText;
    assert.match(css, /button, input\[type=number\], input:not\(\[type\]\) \{ min-height: 44px/); // OK (5.7)
    assert.match(css, /\.hero \{[^}]*aspect-ratio: 4 \/ 3; object-fit: contain/); // OK (V7)
    assert.match(css, /\.thumb \{ width: 40px; height: 40px/); // NOTE: the list shows a 40 px square, cut from 4:3
  }

  console.log("card probe 0.3.0 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
