// Review of version 0.3.5 (commit 70c15dc): the card in jsdom, with the mocked server of the repository.
// Run: node card_probe_0_3_5.cjs <path to the repository>   (after npm ci && npm run build there)
// FINDING = defect, NOTE = limit or difference to functional spec draft 0.13, OK = point that holds.
const assert = require("node:assert");
const path = require("node:path");

const repo = path.resolve(process.argv[2] ?? path.join(__dirname, ".."));
const { tick, setValue, same, world, make, q, click } = require(path.join(repo, "tests", "world.cjs"));

const sent = (s, type) => s.calls.filter((c) => c.type === `resident_scenes/${type}`);
const open = async (s, capabilities, state, entries) => {
  s.devices.find((d) => d.entity_id === "light.r0_0").capabilities = capabilities;
  s.hass.states["light.r0_0"] = state;
  const card = await make(s, { scope: "area", area: "r0", view: "manage" });
  await click(card.shadowRoot, '[data-action="new"]');
  s.scene.sequence = [{ id: "g1", type: "group", domain: "light", area_id: "r0", entries }];
  s.notify({ changed: true });
  await tick();
  await click(card.shadowRoot, '[data-action="open"][data-id="g1"]');
  return card;
};
const mode = (root) => q(root, '[data-field="light_mode"][data-entity="light.r0_0"] [aria-checked="true"]').textContent.trim();
const field = (root, name) => q(root, `[data-field="${name}"][data-entity="light.r0_0"]`);

(async () => {
  // ---------- AA2: an entry stored without a colour on a light with a white channel shows "Weiß" and stores it ----------
  {
    const s = world({ lang: "de" });
    const card = await open(s, { brightness: true, color_temp: false, color: true, white_mode: true },
      { entity_id: "light.r0_0", state: "off", attributes: {} },
      [{ entity_id: "light.r0_0", name: "light.r0_0", state: "on", attributes: { brightness: 102 }, issue: null }]);
    const root = card.shadowRoot;
    assert.strictEqual(mode(root), "Weiß"); // OK
    setValue(field(root, "brightness"), "20");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { white: true, brightness: 51 }); // OK: shown is stored
    card.remove();
  }

  // ---------- a light without a white channel keeps its default: the lowest colour temperature ----------
  {
    const s = world({ lang: "de" });
    const card = await open(s, { brightness: true, color_temp: true, color: true, min_kelvin: 2000, max_kelvin: 6500 },
      { entity_id: "light.r0_0", state: "off", attributes: {} }, []);
    const root = card.shadowRoot;
    assert.strictEqual(mode(root), "Weiß"); // the state "Weiß" of a light with colour temperature
    setValue(field(root, "brightness"), "40");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { color_temp_kelvin: 2000, brightness: 102 }); // OK: as in 0.3.3 (Y1)
    card.remove();
  }

  // ---------- white channel, colour temperature and colour, off: of the three states the card picks the white channel ----------
  {
    const s = world({ lang: "de" });
    const card = await open(s, { brightness: true, color_temp: true, color: true, white_mode: true, min_kelvin: 2000, max_kelvin: 6500 },
      { entity_id: "light.r0_0", state: "off", attributes: {} }, []);
    const root = card.shadowRoot;
    assert.strictEqual(field(root, "color_temp_kelvin"), null); // no slider: the first of "Weiß", "Farbtemperatur", "Farbe"
    setValue(field(root, "brightness"), "40");
    await tick();
    same(sent(s, "set_entry").at(-1).values, { white: true, brightness: 102 }); // OK
    card.remove();
  }

  console.log("card probe 0.3.5 passed");
  process.exit(0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
