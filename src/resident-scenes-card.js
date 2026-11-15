// Resident Scenes card, built with Lit and bundled into one file (npm run build).
// No Home Assistant internal elements: only the documented card API and theme variables.
import { LitElement, html, css, nothing } from "lit";

const VERSION = "0.2.0"; // must match the integration (checked by tests)
const WS = "resident_scenes";
const HOUSE = "_house";
const DOMAINS = ["light", "cover", "climate", "switch", "fan", "media_player", "scene"];
const VISIBLE_RELOAD = 5 * 60 * 1000; // wall panels turn the screen on often (review N2)

const I18N = {
  en: {
    new_scene: "New scene", scenes: "Scenes", other_scenes: "Other scenes", favorites: "Favorites",
    play: "Play", edit: "Edit", save: "Save", cancel: "Cancel", delete: "Delete", duplicate: "Duplicate",
    back: "Back", name: "Name", image: "Image", no_image: "No image", all: "All", none: "–",
    slot: "Slot", keep: "Stored value", capture: "Current state", off: "Off", closed: "Closed", set: "Set value",
    on: "On", favorite: "Favorite", volume: "Volume", call: "Run", missing: "Device missing",
    unavailable: "Not reachable", not_released: "Not released", other_area: "In another room",
    favorite_missing: "Favorite missing", scene_missing: "Scene missing", all_off: "All off", all_closed: "All closed",
    all_house: "All in the house", rights_gone: "Your right to change scenes was withdrawn.", empty: "No scenes yet.",
    no_devices: "No released devices.", confirm_delete: "Delete this scene for good?", used_on: "Used by:",
    outside_note: "Automations and schedules using it will stop working.", yes: "Delete", no: "Keep",
    conflict: "Someone else changed this scene meanwhile.", load_new: "Load new version",
    save_copy: "Save mine as copy", copy: "copy", reload: "A new version is installed. Please reload.",
    reload_btn: "Reload", house: "House", installer: "Installer", released: "Content released to residents",
    kind: "Kind", resident: "Resident scene", brightness: "Brightness", color_temp: "Colour temperature",
    hue: "Colour", position: "Position", tilt: "Tilt", temperature: "Temperature", mode: "Mode",
    delay: "Delay (s)", transition: "Transition (s)", order: "Sequence", up: "Move up", down: "Move down",
    preview: "Live preview", undo: "Undo last change", rights: "Permissions", may_edit: "may change scenes",
    panel: "Panel", own_image: "Own image", crop: "Section", crop_x: "Horizontal", crop_y: "Vertical",
    use_image: "Use image", room_scene: "Room scene", remove: "Remove", stale: "Not up to date, retrying …",
    light: "Lights", cover: "Shading", climate: "Climate", switch: "Switches", fan: "Fans",
    media_player: "Music", scene: "Scenes",
    err: {
      unauthorized: "You may not change scenes.", name_exists: "This name is taken.",
      invalid_name: "Name is empty or too long.", limit_reached: "Limit of scenes reached.",
      too_many_steps: "Too many devices.", entity_not_allowed: "Not released for this scene:",
      entity_unavailable: "Not reachable, its state cannot be captured:",
      unknown_favorite: "This favorite no longer exists.", not_found: "The scene no longer exists.",
      invalid_step: "Invalid setting.", invalid_value: "Value out of range:", invalid_delay: "Delay too long:",
      favorite_not_supported: "Favorites only work on players of the music system:",
      invalid_scene_call: "This scene cannot be called.", duplicate_entity: "Device used twice:",
      protected: "Installer scene: only its released content can be changed.", invalid_image: "Image not found.",
      invalid_image_file: "This is not an image file.", image_too_large: "Image too large, limit:",
      image_limit: "Image limit reached:", nothing_to_undo: "Nothing to undo.", default: "Saving failed.",
    },
  },
  de: {
    new_scene: "Neue Szene", scenes: "Szenen", other_scenes: "Weitere Szenen", favorites: "Favoriten",
    play: "Abspielen", edit: "Ändern", save: "Speichern", cancel: "Abbrechen", delete: "Löschen",
    duplicate: "Duplizieren", back: "Zurück", name: "Name", image: "Bild", no_image: "Kein Bild",
    all: "Alle", none: "–", slot: "Platz", keep: "Gespeicherter Wert", capture: "Aktueller Zustand",
    off: "Aus", closed: "Zu", set: "Wert setzen", on: "An", favorite: "Favorit", volume: "Lautstärke", call: "Aufruf",
    missing: "Gerät fehlt", unavailable: "Nicht erreichbar", not_released: "Nicht freigegeben",
    other_area: "In anderem Raum", favorite_missing: "Favorit fehlt", scene_missing: "Szene fehlt",
    all_off: "Alle aus", all_closed: "Alle zu", all_house: "Alle im Haus",
    rights_gone: "Ihr Recht, Szenen zu ändern, wurde entzogen.", empty: "Noch keine Szenen.",
    no_devices: "Keine freigegebenen Geräte.", confirm_delete: "Diese Szene endgültig löschen?",
    used_on: "Verwendet in:", outside_note: "Automationen und Zeitpläne damit wirken nicht mehr.",
    yes: "Löschen", no: "Behalten", conflict: "Jemand anderes hat die Szene inzwischen geändert.",
    load_new: "Neuen Stand laden", save_copy: "Meine Fassung als Kopie sichern", copy: "Kopie",
    reload: "Eine neue Version ist installiert. Bitte neu laden.", reload_btn: "Neu laden", house: "Haus",
    installer: "Errichter", released: "Inhalt für Bewohner freigegeben", kind: "Art", resident: "Kundenszene",
    brightness: "Helligkeit", color_temp: "Farbtemperatur", hue: "Farbe", position: "Position", tilt: "Neigung",
    temperature: "Temperatur", mode: "Betriebsart", delay: "Verzögerung (s)", transition: "Übergang (s)",
    order: "Ablauf", up: "Nach oben", down: "Nach unten", preview: "Live-Vorschau",
    undo: "Letzte Änderung zurücknehmen", rights: "Berechtigungen", may_edit: "darf Szenen ändern",
    panel: "Panel", own_image: "Eigenes Bild", crop: "Ausschnitt", crop_x: "Waagerecht", crop_y: "Senkrecht",
    use_image: "Bild übernehmen", room_scene: "Raumszene", remove: "Entfernen",
    stale: "Nicht aktuell, neuer Versuch läuft …",
    light: "Licht", cover: "Beschattung", climate: "Klima", switch: "Schalter", fan: "Lüfter",
    media_player: "Musik", scene: "Szenen",
    err: {
      unauthorized: "Sie dürfen Szenen nicht ändern.", name_exists: "Dieser Name ist schon vergeben.",
      invalid_name: "Name fehlt oder ist zu lang.", limit_reached: "Höchstzahl an Szenen erreicht.",
      too_many_steps: "Zu viele Geräte.", entity_not_allowed: "Für diese Szene nicht freigegeben:",
      entity_unavailable: "Nicht erreichbar, der Zustand lässt sich nicht übernehmen:",
      unknown_favorite: "Diesen Favoriten gibt es nicht mehr.", not_found: "Die Szene gibt es nicht mehr.",
      invalid_step: "Ungültige Einstellung.", invalid_value: "Wert außerhalb des Bereichs:",
      invalid_delay: "Verzögerung zu lang:", favorite_not_supported: "Favoriten nur für Player des Musiksystems:",
      invalid_scene_call: "Diese Szene lässt sich nicht aufrufen.", duplicate_entity: "Gerät doppelt:",
      protected: "Errichterszene: nur der freigegebene Inhalt lässt sich ändern.", invalid_image: "Bild nicht gefunden.",
      invalid_image_file: "Das ist keine Bilddatei.", image_too_large: "Bild zu groß, Grenze:",
      image_limit: "Höchstzahl an Bildern erreicht:", nothing_to_undo: "Nichts zurückzunehmen.",
      default: "Speichern fehlgeschlagen.",
    },
  },
};

const TILE = { w: 640, h: 480 }; // tile format of the design system, 4:3

class ResidentScenesCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _data: { state: true },
    _detail: { state: true },
    _edit: { state: true },
    _rights: { state: true },
    _selected: { state: true },
    _narrow: { state: true },
    _notice: { state: true },
    _stale: { state: true },
  };

  setConfig(config) {
    const cfg = { scope: "area", view: "manage", ...config };
    if (!["area", "house"].includes(cfg.scope)) throw new Error("scope must be area or house");
    if (cfg.scope === "area" && !cfg.area) throw new Error("area is required for scope: area");
    if (!["manage", "list", "favorites"].includes(cfg.view)) throw new Error("view must be manage, list or favorites");
    this._config = cfg;
  }

  static getStubConfig() {
    return { scope: "house", view: "manage" };
  }

  getCardSize() {
    return this._config?.view === "favorites" ? 2 : 4;
  }

  connectedCallback() {
    super.connectedCallback();
    this._ro = new ResizeObserver(([entry]) => (this._narrow = entry.contentRect.width < 600));
    this._ro.observe(this);
    if (this.hass && !this._started) this._start();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._started = false;
    clearInterval(this._timer);
    clearTimeout(this._retry);
    document.removeEventListener("visibilitychange", this._onVisible);
    this.hass?.connection.removeEventListener?.("ready", this._onReady);
    this._ro?.disconnect();
    this._unsubscribe();
  }

  updated(changed) {
    if (changed.has("hass") && this.hass && !this._started && this.isConnected) this._start();
  }

  _start() {
    this._started = true;
    this._needSub = true;
    // signed image URLs die after a restart and after a day; wall panels run for weeks (spec 4.3, 5.7)
    this._onReady ??= () => ((this._needSub = true), this._load());
    this._onVisible ??= () =>
      document.visibilityState === "visible" && Date.now() - (this._loadedAt ?? 0) > VISIBLE_RELOAD && this._load();
    this.hass.connection.addEventListener?.("ready", this._onReady);
    document.addEventListener("visibilitychange", this._onVisible);
    this._timer = setInterval(() => this._load(), 6 * 3600 * 1000);
    this._load();
  }

  _unsubscribe() {
    this._unsub?.then((unsub) => unsub?.()).catch(() => {});
    this._unsub = undefined;
  }

  _subscribe() {
    this._unsubscribe();
    this._needSub = false;
    this._unsub = this.hass.connection.subscribeMessage(() => this._load(true), { type: `${WS}/subscribe` });
    this._unsub.catch(() => (this._needSub = true));
  }

  _t(key) {
    const lang = this.hass?.locale?.language?.startsWith("de") ? "de" : "en";
    return key.split(".").reduce((o, k) => o?.[k], I18N[lang]) ?? key;
  }

  get _scope() {
    return this._config.scope === "house" ? HOUSE : this._config.area;
  }

  get _house() {
    return this._config.scope === "house";
  }

  async _load(fromServer = false) {
    clearTimeout(this._retry);
    try {
      this._data = await this.hass.callWS({ type: `${WS}/list`, scope: this._scope });
      this._loadedAt = Date.now();
      this._stale = false;
      this._backoff = 0;
      // the subscription is renewed after the first success, e.g. once the integration is loaded again
      if (this._needSub) this._subscribe();
    } catch (err) {
      // keep showing the last data and try again with growing pauses (review N2)
      this._stale = true;
      this._backoff = Math.min((this._backoff || 1) * 2, 60);
      this._retry = setTimeout(() => this._load(), this._backoff * 1000);
      return;
    }
    if (this._data.can_edit && this._notice === "rights_gone") this._notice = null; // review N7
    // rights withdrawn while editing: drop the form, server would reject it anyway
    if (this._edit && !this._data.can_edit) {
      this._endPreview(true);
      this._edit = null;
      this._notice = "rights_gone";
    }
    if (this._rights && this._data.manages_rights) this._loadRights();
    if (!this._data.manages_rights) this._rights = null;
    // someone else saved while this user edits: keep the form as it is, conflicts show on save
    if (fromServer && this._edit) return;
    if (this._selected) await this._loadDetail();
  }

  async _loadDetail() {
    try {
      this._detail = await this.hass.callWS({ type: `${WS}/scene`, scene_id: this._selected });
    } catch (err) {
      if (err.code === "not_found") (this._selected = null), (this._detail = null);
    }
  }

  async _loadRights() {
    try {
      this._rights = (await this.hass.callWS({ type: `${WS}/rights` })).accounts;
    } catch (err) {
      this._rights = null;
    }
  }

  _scene(id) {
    return this._data?.scenes.find((s) => s.id === id);
  }

  get _scenes() {
    return [...(this._data?.scenes ?? [])].sort((a, b) => a.name.localeCompare(b.name));
  }

  _name(eid, fallback) {
    const st = this.hass.states[eid];
    if (st && typeof this.hass.formatEntityName === "function") {
      try {
        const name = this.hass.formatEntityName(st, [{ type: "device" }, { type: "entity" }], { separator: " · " });
        if (name) return name;
      } catch (err) {
        // older frontend: fall back to the friendly name
      }
    }
    return st?.attributes.friendly_name ?? fallback ?? eid;
  }

  _entityArea(eid) {
    const ent = this.hass.entities?.[eid];
    return ent?.area_id ?? this.hass.devices?.[ent?.device_id]?.area_id ?? null;
  }

  _areaName(areaId) {
    return areaId ? this.hass.areas?.[areaId]?.name ?? areaId : this._t("house");
  }

  _play(entityId) {
    if (entityId) this.hass.callService("scene", "turn_on", { entity_id: entityId });
  }

  _err(code, detail) {
    const known = this._t(`err.${code}`) !== `err.${code}`;
    return known ? `${this._t(`err.${code}`)}${detail ? ` ${detail}` : ""}` : this._t("err.default");
  }

  // ---------- rendering ----------

  render() {
    if (!this._config) return nothing;
    const outdated = this._data && this._data.version !== VERSION;
    let body = nothing;
    if (this._data && this._config.view === "favorites") {
      body = this._renderFavorites();
      // empty slots stay invisible (spec 4.7), so does a card without any
      if (body === nothing && !outdated) return nothing;
    } else if (this._data) body = this._renderManage();
    return html`<div class="card">
      ${outdated
        ? html`<div class="banner">${this._t("reload")}
            <button data-action="reload" @click=${() => location.reload()}>${this._t("reload_btn")}</button></div>`
        : nothing}
      ${this._stale && this._data ? html`<p class="muted" role="status">${this._t("stale")}</p>` : nothing}
      ${this._notice ? html`<p class="error" role="alert">${this._t(this._notice)}</p>` : nothing} ${body}
    </div>`;
  }

  _renderFavorites() {
    const tiles = this._data.favorites.map((id) => this._scene(id)).filter(Boolean);
    if (!tiles.length) return nothing;
    return html`<div class="tiles">
      ${tiles.map(
        (s) => html`<button class="tile" data-action="play" aria-label=${s.name} @click=${() => this._play(s.entity_id)}>
          ${s.image_url ? html`<img src=${s.image_url} alt="" />` : nothing}<span>${s.name}</span>
        </button>`
      )}
    </div>`;
  }

  _renderManage() {
    const showDetail = this._config.view === "manage" && (this._selected || this._edit || this._rights);
    const list = this._renderList();
    if (!showDetail) return list;
    const detail = this._edit ? this._renderEditor() : this._rights ? this._renderRights() : this._renderDetail();
    if (this._narrow) return detail;
    return html`<div class="columns"><div class="col-list">${list}</div><div class="col-detail">${detail}</div></div>`;
  }

  _renderList() {
    const manage = this._config.view === "manage";
    const d = this._data;
    const canEdit = manage && d.can_edit;
    const full = this._scenes.length >= d.limit;
    const play = (eid) => html`<button class="icon" data-action="play" aria-label=${this._t("play")}
      @click=${() => this._play(eid)}>▶</button>`;
    return html`
      ${canEdit
        ? html`<button class="primary wide" data-action="new" ?disabled=${full} @click=${() => this._openEditor(null)}>
              + ${this._t("new_scene")}</button>
            ${full ? html`<p class="muted">${this._t("err.limit_reached")} (${d.limit})</p>` : nothing}`
        : nothing}
      ${manage && d.manages_rights
        ? html`<button class="wide" data-action="rights" @click=${this._openRights}>${this._t("rights")}</button>`
        : nothing}
      <h3>${this._t("scenes")}</h3>
      ${this._scenes.length
        ? this._scenes.map(
            (s) => html`<div class="row ${this._selected === s.id ? "selected" : ""}">
              ${s.image_url ? html`<img class="thumb" src=${s.image_url} alt="" />` : html`<span class="thumb"></span>`}
              ${manage
                ? html`<button class="name link" data-action="select" data-id=${s.id} @click=${() => this._select(s.id)}>
                    ${s.name}</button>`
                : html`<span class="name">${s.name}</span>`}
              ${s.kind === "installer" ? html`<span class="badge">${this._t("installer")}</span>` : nothing}
              ${play(s.entity_id)}
            </div>`
          )
        : html`<p class="muted">${this._t("empty")}</p>`}
      ${d.foreign_scenes.length
        ? html`<h3>${this._t("other_scenes")}</h3>
            ${d.foreign_scenes.map(
              (s) => html`<div class="row"><span class="thumb"></span>
                <span class="name">${this._name(s.entity_id, s.name)}${s.knx ? html`<span class="badge">KNX</span>` : nothing}</span>
                ${play(s.entity_id)}</div>`
            )}`
        : nothing}
    `;
  }

  async _select(id) {
    this._rights = null;
    this._selected = id;
    this._detail = null;
    await this._loadDetail();
  }

  _back() {
    this._selected = null;
    this._detail = null;
    this._rights = null;
  }

  _renderDetail() {
    const s = this._detail;
    if (!s) return nothing;
    const d = this._data;
    const slot = d.favorites.indexOf(s.id);
    return html`${this._narrow ? html`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : nothing}
      <div class="head">
        ${s.image_url ? html`<img class="hero" src=${s.image_url} alt="" />` : nothing}
        <h2>${s.name} ${s.kind === "installer" ? html`<span class="badge">${this._t("installer")}</span>` : nothing}</h2>
        <button class="primary" data-action="play" @click=${() => this._play(s.entity_id)}>▶ ${this._t("play")}</button>
        ${d.can_edit
          ? html`<label class="heart">♥
              <select data-field="favorite" aria-label=${this._t("favorites")} @change=${(e) => this._setFavorite(e.target.value)}>
                <option value="">${this._t("none")}</option>
                ${d.favorites.map(
                  (_, i) => html`<option value=${i} ?selected=${i === slot}>${this._t("slot")} ${i + 1}</option>`
                )}
              </select></label>`
          : nothing}
        ${d.can_edit && s.editable
          ? html`<button data-action="edit" @click=${() => this._openEditor(s)}>${this._t("edit")}</button>`
          : nothing}
        ${d.can_edit && s.editable && s.can_undo
          ? html`<button data-action="undo" @click=${this._undo}>${this._t("undo")}</button>`
          : nothing}
      </div>
      ${this._detailError ? html`<p class="error" role="alert">${this._detailError}</p>` : nothing}
      ${this._renderSteps(s.steps)}`;
  }

  _groupOf(step) {
    if (step.scene_id) return this._t("scene");
    return this._house ? this._areaName(this._entityArea(step.entity_id)) : this._t(step.entity_id.split(".")[0]);
  }

  _renderSteps(steps) {
    const groups = new Map();
    for (const step of steps) {
      const key = this._groupOf(step);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(step);
    }
    return [...groups].map(
      ([title, items]) => html`<h3>${title}</h3>
        ${items.map(
          (step) => html`<div class="row">
            <span class="name">${step.scene_id ? step.name : this._name(step.entity_id, step.name)}
              ${step.issue ? html`<span class="badge warn">${this._t(step.issue)}</span>` : nothing}</span>
            <span class="muted">${this._summary(step)}${step.delay ? ` · +${step.delay} s` : ""}</span>
          </div>`
        )}`
    );
  }

  _summary(step) {
    const pct = (v) => `${Math.round(v * 100)} %`;
    if (step.scene_id || step.call) return this._t("call");
    if (step.music === "off") return this._t("off");
    if (step.music === "on") return `${this._t("on")} · ${pct(step.volume)}`;
    if (step.music === "favorite") return `${step.favorite_name} · ${pct(step.volume)}`;
    const a = step.attributes ?? {};
    if (step.state === "off") return this._t("off");
    if (step.state === "closed") return this._t("closed");
    if (a.brightness != null) {
      const color = a.color_temp_kelvin ? ` · ${a.color_temp_kelvin} K` : "";
      return `${this._t("on")} · ${Math.round(a.brightness / 2.55)} %${color}`;
    }
    if (a.current_position != null) return `${a.current_position} %`;
    if (a.temperature != null) return `${step.state} · ${a.temperature} °`;
    if (a.percentage != null) return `${this._t("on")} · ${a.percentage} %`;
    return step.state === "on" ? this._t("on") : step.state;
  }

  // ---------- rights (spec 3) ----------

  async _openRights() {
    this._selected = null;
    this._detail = null;
    await this._loadRights();
  }

  _renderRights() {
    return html`${this._narrow ? html`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : nothing}
      <h2>${this._t("rights")}</h2>
      ${this._rights.map(
        (a) => html`<label class="row">
          <span class="name">${a.name} ${a.kind === "panel" ? html`<span class="badge">${this._t("panel")}</span>` : nothing}</span>
          <span class="muted">${this._t("may_edit")}</span>
          <input type="checkbox" class="switch" data-field="right" data-id=${a.user_id} .checked=${a.can_edit}
            @change=${(e) => this._setRight(a.user_id, e.target.checked)} />
        </label>`
      )}`;
  }

  async _setRight(userId, canEdit) {
    try {
      await this.hass.callWS({ type: `${WS}/set_right`, user_id: userId, can_edit: canEdit });
    } finally {
      await this._loadRights();
    }
  }

  // ---------- detail actions ----------

  async _setFavorite(value) {
    const current = this._data.favorites.indexOf(this._selected);
    try {
      if (value === "" && current >= 0) {
        await this.hass.callWS({ type: `${WS}/set_favorite`, scope: this._scope, slot: current, scene_id: null });
      } else if (value !== "") {
        await this.hass.callWS({ type: `${WS}/set_favorite`, scope: this._scope, slot: Number(value), scene_id: this._selected });
      }
    } catch (err) {
      await this._load(); // show the real state again
    }
  }

  async _undo() {
    this._detailError = null;
    try {
      await this.hass.callWS({ type: `${WS}/undo`, scene_id: this._detail.id, version: this._detail.version });
    } catch (err) {
      this._detailError = this._err(err.code);
    }
    await this._load();
  }

  // ---------- editor ----------

  async _openEditor(scene) {
    this._notice = null;
    this._rights = null;
    let result;
    try {
      result = await this.hass.callWS({ type: `${WS}/devices`, ...(this._house ? {} : { area_id: this._config.area }) });
    } catch (err) {
      return;
    }
    const devices = result.entities;
    const steps = new Map();
    for (const step of scene?.steps ?? []) {
      if (step.scene_id) {
        steps.set(`scene:${step.scene_id}`, { choice: "scene", scene_id: step.scene_id, name: step.name,
          area_id: result.room_scenes.find((r) => r.id === step.scene_id)?.area_id, issue: step.issue, delay: step.delay ?? 0 });
        continue;
      }
      const s = { choice: "keep", stored: step, issue: step.issue, delay: step.delay ?? 0, values: this._valuesFromStep(step) };
      if (step.music && step.music !== "off") Object.assign(s, { volume: step.volume, favorite_id: step.favorite_id });
      steps.set(step.entity_id, s);
      // a stored device that is no longer offered (moved, label removed, deleted) stays visible
      if (!devices.some((d) => d.entity_id === step.entity_id)) {
        devices.push({ entity_id: step.entity_id, name: this._name(step.entity_id, step.name), domain: step.entity_id.split(".")[0],
          area_id: this._entityArea(step.entity_id), available: false, released: false, capabilities: {} });
      }
    }
    for (const dev of devices) dev.label = this._name(dev.entity_id, dev.name);
    devices.sort((a, b) => a.label.localeCompare(b.label));
    this._edit = {
      scene_id: scene?.id, version: scene?.version, name: scene?.name ?? "",
      image: scene?.image ?? null, imageUrl: scene?.image_url ?? null,
      kind: scene?.kind ?? "resident", content_released: scene?.content_released ?? false,
      transition: scene?.transition ?? null, steps, devices,
      favorites: result.favorites, images: result.images, room_scenes: result.room_scenes,
      preview: !this._house, // spec 5.4: on for room scenes, off for house scenes
    };
  }

  _valuesFromStep(step) {
    const a = step.attributes ?? {};
    const domain = step.entity_id.split(".")[0];
    if (domain === "light") {
      const v = { brightness: a.brightness ?? 255 };
      if (a.color_temp_kelvin) v.color_temp_kelvin = a.color_temp_kelvin;
      if (a.hs_color) Object.assign(v, { hue: a.hs_color[0], saturation: a.hs_color[1] });
      return v;
    }
    if (domain === "cover") return { position: a.current_position ?? (step.state === "closed" ? 0 : 100), ...(a.current_tilt_position != null ? { tilt: a.current_tilt_position } : {}) };
    if (domain === "climate") return { hvac_mode: step.state, ...(a.temperature != null ? { temperature: a.temperature } : {}) };
    if (domain === "fan") return { percentage: a.percentage ?? 50 };
    if (domain === "switch") return { on: step.state === "on" };
    return {};
  }

  _valuesFromState(dev) {
    const st = this.hass.states[dev.entity_id];
    if (!st) return {};
    return this._valuesFromStep({ entity_id: dev.entity_id, state: st.state, attributes: st.attributes });
  }

  _canSet(dev) {
    const c = dev.capabilities ?? {};
    if (dev.domain === "light") return c.brightness || c.color_temp || c.color;
    if (dev.domain === "cover") return c.position || c.tilt;
    if (dev.domain === "climate") return (c.hvac_modes ?? []).length > 0;
    return dev.domain === "fan" || dev.domain === "switch";
  }

  _groupKey(dev) {
    return this._house ? dev.area_id ?? "" : dev.domain;
  }

  _renderEditor() {
    const e = this._edit;
    const d = this._data;
    const groups = new Map();
    for (const dev of e.devices.filter((x) => x.domain !== "scene")) {
      const key = this._groupKey(dev);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(dev);
    }
    const order = [...groups.keys()].sort((a, b) =>
      this._house ? this._areaName(a).localeCompare(this._areaName(b)) : DOMAINS.indexOf(a) - DOMAINS.indexOf(b)
    );
    // house scenes: one input per trade for "everything off" (spec 4.5, 5.3)
    const trades = this._house
      ? DOMAINS.filter((t) => t !== "scene" && e.devices.some((dev) => dev.domain === t && dev.released !== false))
      : [];
    return html`<div class="editor">
      <label>${this._t("name")}<input data-field="name" maxlength=${d.name_length} .value=${e.name}
        @input=${(ev) => (e.name = ev.target.value)} /></label>
      ${this._renderImagePicker()}
      ${d.is_admin
        ? html`<label>${this._t("kind")}<select data-field="kind" @change=${(ev) => this._setEdit({ kind: ev.target.value })}>
              <option value="resident" ?selected=${e.kind === "resident"}>${this._t("resident")}</option>
              <option value="installer" ?selected=${e.kind === "installer"}>${this._t("installer")}</option></select></label>
            ${e.kind === "installer"
              ? html`<label class="inline"><input type="checkbox" data-field="released" .checked=${e.content_released}
                  @change=${(ev) => (e.content_released = ev.target.checked)} />${this._t("released")}</label>`
              : nothing}`
        : nothing}
      <label>${this._t("transition")}<input type="number" min="0" max=${d.max_transition} step="0.5" data-field="transition"
        .value=${e.transition ?? ""} @change=${(ev) => (e.transition = ev.target.value === "" ? null : Number(ev.target.value))} /></label>
      <label class="inline"><input type="checkbox" class="switch" data-field="preview" .checked=${e.preview}
        @change=${(ev) => this._setEdit({ preview: ev.target.checked })} />${this._t("preview")}</label>
      ${trades.length
        ? html`<h3>${this._t("all_house")}</h3>
            <div class="actions">${trades.map(
              (t) => html`<button class="small" data-action="trade-off" data-domain=${t}
                @click=${() => this._allOff((dev) => dev.domain === t)}>${this._t(t)} · ${this._t(t === "cover" ? "all_closed" : "all_off")}</button>`
            )}</div>`
        : nothing}
      ${this._house ? this._renderRoomScenes() : nothing}
      ${order.length
        ? order.map((key) => {
            const devs = groups.get(key);
            const all = devs.every((dev) => e.steps.has(dev.entity_id));
            const closeLabel = !this._house && key === "cover" ? "all_closed" : "all_off";
            return html`<h3><label class="inline"><input type="checkbox" data-field="all" data-group=${key} .checked=${all}
                @change=${(ev) => this._pickAll(devs, ev.target.checked)} />
                ${this._house ? this._areaName(key || null) : this._t(key)} · ${this._t("all")}</label>
              <button class="small" data-action="group-off" data-group=${key}
                @click=${() => this._allOff((dev) => this._groupKey(dev) === key)}>${this._t(closeLabel)}</button></h3>
              ${devs.map((dev) => this._renderDevice(dev))}`;
          })
        : html`<p class="muted">${this._t("no_devices")}</p>`}
      ${this._renderOrder()}
      ${e.error ? html`<p class="error" role="alert">${this._err(e.error, e.errorDetail)}</p>` : nothing}
      ${e.conflict
        ? html`<div class="banner">${this._t("conflict")}
            <button data-action="load-new" @click=${this._loadNew}>${this._t("load_new")}</button>
            <button data-action="save-copy" @click=${() => this._save({ copy: true })}>${this._t("save_copy")}</button></div>`
        : nothing}
      ${e.confirmDelete ? this._renderConfirmDelete() : nothing}
      <div class="actions">
        <button class="primary" data-action="save" ?disabled=${e.busy} @click=${() => this._save({})}>${this._t("save")}</button>
        <button data-action="cancel" @click=${this._cancel}>${this._t("cancel")}</button>
        ${e.scene_id ? html`<button data-action="duplicate" @click=${() => this._save({ copy: true })}>${this._t("duplicate")}</button>` : nothing}
        ${e.scene_id && (e.kind === "resident" || d.is_admin)
          ? html`<button class="danger" data-action="ask-delete" @click=${() => this._setEdit({ confirmDelete: true })}>${this._t("delete")}</button>`
          : nothing}
      </div></div>`;
  }

  _setEdit(patch) {
    this._edit = { ...this._edit, ...patch };
  }

  _renderImagePicker() {
    const e = this._edit;
    const crop = e.crop;
    return html`<label>${this._t("image")}
        <select data-field="image" @change=${(ev) => this._pickImage(ev.target.value)}>
          <option value="">${this._t("no_image")}</option>
          ${e.image?.startsWith("upload:") ? html`<option value=${e.image} selected>${this._t("own_image")}</option>` : nothing}
          ${e.images.map((i) => html`<option value=${i.name} ?selected=${i.name === e.image}>${i.name}</option>`)}
        </select></label>
      <label class="file">${this._t("own_image")}
        <input type="file" accept="image/*" data-field="upload" @change=${(ev) => this._openCrop(ev.target.files?.[0])} /></label>
      ${crop
        ? html`<div class="crop">
            <canvas width=${TILE.w / 2} height=${TILE.h / 2}></canvas>
            <label>${this._t("crop_x")}<input type="range" min="0" max="100" .value=${String(crop.x)}
              @input=${(ev) => this._moveCrop({ x: Number(ev.target.value) })} /></label>
            <label>${this._t("crop_y")}<input type="range" min="0" max="100" .value=${String(crop.y)}
              @input=${(ev) => this._moveCrop({ y: Number(ev.target.value) })} /></label>
            <button class="primary" data-action="use-image" @click=${this._upload}>${this._t("use_image")}</button>
          </div>`
        : e.imageUrl
          ? html`<img class="hero" src=${e.imageUrl} alt="" />`
          : nothing}`;
  }

  _pickImage(name) {
    const image = name || null;
    const url = this._edit.images.find((i) => i.name === image)?.url ?? (image === this._edit.image ? this._edit.imageUrl : null);
    this._setEdit({ image, imageUrl: url });
  }

  async _openCrop(file) {
    if (!file) return;
    const img = new Image();
    img.src = URL.createObjectURL(file);
    try {
      await img.decode();
    } catch (err) {
      this._setEdit({ error: "invalid_image_file", errorDetail: "" });
      return;
    }
    this._setEdit({ crop: { img, x: 50, y: 50 }, error: null });
    await this.updateComplete;
    this._drawCrop(this.renderRoot.querySelector(".crop canvas"));
  }

  _moveCrop(patch) {
    this._edit.crop = { ...this._edit.crop, ...patch };
    this._drawCrop(this.renderRoot.querySelector(".crop canvas"));
  }

  // the card shrinks the image to the tile format before upload (spec 4.8); the server checks it again
  _drawCrop(canvas) {
    const { img, x, y } = this._edit.crop;
    const ratio = TILE.w / TILE.h;
    const sw = Math.min(img.naturalWidth, img.naturalHeight * ratio);
    const sh = sw / ratio;
    const sx = ((img.naturalWidth - sw) * x) / 100;
    const sy = ((img.naturalHeight - sh) * y) / 100;
    canvas?.getContext("2d")?.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
  }

  async _upload() {
    const canvas = document.createElement("canvas");
    canvas.width = TILE.w;
    canvas.height = TILE.h;
    this._drawCrop(canvas);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    const form = new FormData();
    form.append("file", blob, "scene.jpg");
    try {
      const res = await this.hass.fetchWithAuth(`/api/${WS}/upload`, { method: "POST", body: form });
      const body = await res.json();
      if (!res.ok) throw body;
      this._setEdit({ image: body.image, imageUrl: body.url, crop: null, error: null });
    } catch (err) {
      // the old image stays (spec 5.6)
      const detail = /: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
      this._setEdit({ crop: null, error: err.code ?? "invalid_image_file", errorDetail: detail });
    }
  }

  _renderRoomScenes() {
    const e = this._edit;
    const areas = [...new Set(e.room_scenes.map((r) => r.area_id))].sort((a, b) => this._areaName(a).localeCompare(this._areaName(b)));
    const missing = [...e.steps].filter(([, s]) => s.choice === "scene" && s.issue === "scene_missing");
    return html`<h3>${this._t("scene")}</h3>
      ${areas.map((area) => {
        const current = [...e.steps.values()].find((s) => s.choice === "scene" && s.area_id === area)?.scene_id ?? "";
        return html`<label>${this._areaName(area)} · ${this._t("room_scene")}
          <select data-field="room-scene" data-group=${area} @change=${(ev) => this._setRoomScene(area, ev.target.value)}>
            <option value="">${this._t("none")}</option>
            ${e.room_scenes.filter((r) => r.area_id === area).map(
              (r) => html`<option value=${r.id} ?selected=${r.id === current}>${r.name}</option>`
            )}
          </select></label>`;
      })}
      ${missing.map(
        ([key, s]) => html`<div class="row"><span class="name">${s.name}
          <span class="badge warn">${this._t("scene_missing")}</span></span>
          <button data-action="remove" @click=${() => this._removeStep(key)}>${this._t("remove")}</button></div>`
      )}`;
  }

  _setRoomScene(area, sceneId) {
    const steps = new Map([...this._edit.steps].filter(([, s]) => !(s.choice === "scene" && s.area_id === area)));
    const scene = this._edit.room_scenes.find((r) => r.id === sceneId);
    if (scene) steps.set(`scene:${scene.id}`, { choice: "scene", scene_id: scene.id, name: scene.name, area_id: area, delay: 0 });
    this._setEdit({ steps });
  }

  _removeStep(key) {
    const steps = new Map(this._edit.steps);
    steps.delete(key);
    this._setEdit({ steps });
  }

  _renderDevice(dev) {
    const step = this._edit.steps.get(dev.entity_id);
    const locked = dev.released === false || ["missing", "not_released", "other_area"].includes(step?.issue);
    let controls = nothing;
    if (step) {
      const choices = [];
      if (step.stored) choices.push("keep");
      if (!locked) {
        choices.push("capture", "off");
        if (this._canSet(dev) && dev.domain !== "media_player") choices.push("set");
        if (dev.domain === "media_player") choices.push("on");
        if (dev.domain === "media_player" && dev.music_system) choices.push("favorite"); // review N6
      }
      const label = (c) => this._t(c === "off" && dev.domain === "cover" ? "closed" : c);
      controls = html`<select data-field="choice" data-entity=${dev.entity_id} aria-label=${dev.label}
          @change=${(ev) => this._choose(dev, ev.target.value)}>
          ${choices.map((c) => html`<option value=${c} ?selected=${c === step.choice}>${label(c)}</option>`)}
        </select>
        ${step.choice === "set" ? this._renderValues(dev, step) : nothing}
        ${step.choice === "favorite"
          ? html`<select data-field="favorite_id" data-entity=${dev.entity_id} aria-label=${this._t("favorite")}
              @change=${(ev) => this._change(dev, { favorite_id: ev.target.value })}>
              ${step.issue === "favorite_missing" ? html`<option value="" selected>${this._t("favorite_missing")}</option>` : nothing}
              ${this._edit.favorites.map((f) => html`<option value=${f.id} ?selected=${f.id === step.favorite_id}>${f.name}</option>`)}
            </select>`
          : nothing}
        ${step.choice === "on" || step.choice === "favorite"
          ? html`<input type="range" min="0" max="100" data-field="volume" data-entity=${dev.entity_id}
              .value=${String(Math.round((step.volume ?? 0.3) * 100))} aria-label=${this._t("volume")}
              @change=${(ev) => this._change(dev, { volume: Number(ev.target.value) / 100 })} />`
          : nothing}`;
    }
    const st = this.hass.states[dev.entity_id];
    const why = step?.issue ?? (dev.released === false ? "not_released" : !st ? "missing" : !dev.available ? "unavailable" : "");
    return html`<div class="row device">
      <label class="name inline"><input type="checkbox" data-field="pick" data-entity=${dev.entity_id} .checked=${!!step}
        @change=${(ev) => this._pick(dev, ev.target.checked)} />
        ${dev.label} ${why ? html`<span class="badge warn">${this._t(why)}</span>` : nothing}</label>${controls}
    </div>`;
  }

  _renderValues(dev, step) {
    const c = dev.capabilities ?? {};
    const v = step.values ?? {};
    const slider = (key, label, min, max, value, toValue = Number) => html`<label class="value">${this._t(label)}
      <input type="range" min=${min} max=${max} data-field=${key} data-entity=${dev.entity_id} .value=${String(value)}
        @change=${(ev) => this._change(dev, { values: { ...step.values, [key]: toValue(ev.target.value) } })} /></label>`;
    if (dev.domain === "light") {
      return html`${slider("brightness", "brightness", 1, 100, Math.round((v.brightness ?? 255) / 2.55), (p) => Math.max(1, Math.round(p * 2.55)))}
        ${c.color_temp ? slider("color_temp_kelvin", "color_temp", c.min_kelvin ?? 2000, c.max_kelvin ?? 6500, v.color_temp_kelvin ?? c.min_kelvin ?? 2700) : nothing}
        ${c.color && !v.color_temp_kelvin ? slider("hue", "hue", 0, 360, v.hue ?? 30) : nothing}`;
    }
    if (dev.domain === "cover") {
      return html`${c.position ? slider("position", "position", 0, 100, v.position ?? 100) : nothing}
        ${c.tilt ? slider("tilt", "tilt", 0, 100, v.tilt ?? 50) : nothing}`;
    }
    if (dev.domain === "climate") {
      return html`<select data-field="hvac_mode" data-entity=${dev.entity_id} aria-label=${this._t("mode")}
          @change=${(ev) => this._change(dev, { values: { ...step.values, hvac_mode: ev.target.value } })}>
          ${(c.hvac_modes ?? []).map((m) => html`<option value=${m} ?selected=${m === v.hvac_mode}>${m}</option>`)}
        </select>
        <label class="value">${this._t("temperature")}<input type="number" min=${c.min_temp ?? 5} max=${c.max_temp ?? 35}
          step=${c.temp_step ?? 0.5} data-field="temperature" data-entity=${dev.entity_id} .value=${String(v.temperature ?? "")}
          @change=${(ev) => this._change(dev, { values: { ...step.values, temperature: Number(ev.target.value) } })} /></label>`;
    }
    if (dev.domain === "fan") return slider("percentage", "position", 0, 100, v.percentage ?? 50);
    if (dev.domain === "switch") {
      return html`<input type="checkbox" class="switch" data-field="on" data-entity=${dev.entity_id} .checked=${!!v.on}
        aria-label=${this._t("on")} @change=${(ev) => this._change(dev, { values: { on: ev.target.checked } })} />`;
    }
    return nothing;
  }

  _renderOrder() {
    const steps = [...this._edit.steps];
    if (!steps.length) return nothing;
    const max = this._data.max_delay;
    return html`<h3>${this._t("order")}</h3>
      ${steps.map(([key, s], i) => html`<div class="row">
        <span class="name">${s.choice === "scene" ? s.name : this._edit.devices.find((d) => d.entity_id === key)?.label ?? key}</span>
        <label class="value">${this._t("delay")}<input type="number" min="0" max=${max} data-field="delay" data-entity=${key}
          .value=${String(s.delay ?? 0)} @change=${(ev) => this._setDelay(key, Number(ev.target.value))} /></label>
        <button class="icon" data-action="up" aria-label=${this._t("up")} ?disabled=${i === 0} @click=${() => this._move(i, -1)}>↑</button>
        <button class="icon" data-action="down" aria-label=${this._t("down")} ?disabled=${i === steps.length - 1}
          @click=${() => this._move(i, 1)}>↓</button>
      </div>`)}`;
  }

  _setDelay(key, delay) {
    this._edit.steps.get(key).delay = Math.max(0, delay || 0);
    this.requestUpdate();
  }

  _move(index, by) {
    const steps = [...this._edit.steps];
    [steps[index], steps[index + by]] = [steps[index + by], steps[index]];
    this._setEdit({ steps: new Map(steps) });
  }

  _pick(dev, on) {
    const steps = new Map(this._edit.steps);
    if (!on) steps.delete(dev.entity_id);
    else if (!steps.has(dev.entity_id)) steps.set(dev.entity_id, { choice: "capture", delay: 0 });
    this._setEdit({ steps });
  }

  _pickAll(devs, on) {
    const steps = new Map(this._edit.steps);
    for (const dev of devs) {
      if (!on) steps.delete(dev.entity_id);
      else if (!steps.has(dev.entity_id)) steps.set(dev.entity_id, { choice: "capture", delay: 0 });
    }
    this._setEdit({ steps });
  }

  _choose(dev, choice) {
    const step = this._edit.steps.get(dev.entity_id);
    const patch = { choice };
    if (choice === "set" && !step.values) patch.values = this._valuesFromState(dev);
    if (choice === "favorite" && !step.favorite_id) patch.favorite_id = this._edit.favorites[0]?.id;
    this._change(dev, patch);
  }

  _change(dev, patch) {
    const step = { ...this._edit.steps.get(dev.entity_id), ...patch };
    if (patch.favorite_id) step.issue = null; // another favorite chosen (spec 5.6)
    this._edit.steps.set(dev.entity_id, step);
    this.requestUpdate();
    this._preview(dev.entity_id, step);
  }

  _allOff(match) {
    const steps = new Map(this._edit.steps);
    for (const dev of this._edit.devices.filter((d) => match(d) && d.domain !== "scene" && d.released !== false)) {
      const step = { delay: 0, ...steps.get(dev.entity_id), choice: "off" };
      steps.set(dev.entity_id, step);
      this._preview(dev.entity_id, step);
    }
    this._setEdit({ steps });
  }

  _stepPayload(key, s) {
    const delay = s.delay ? { delay: s.delay } : {};
    if (s.choice === "scene") return { mode: "scene", scene_id: s.scene_id, ...delay };
    if (s.choice === "on" || s.choice === "favorite") {
      return { entity_id: key, mode: "music", music: s.choice, volume: s.volume ?? 0.3,
        ...(s.choice === "favorite" ? { favorite_id: s.favorite_id ?? "" } : {}), ...delay };
    }
    if (s.choice === "set") return { entity_id: key, mode: "set", values: s.values ?? {}, ...delay };
    return { entity_id: key, mode: s.choice, ...delay };
  }

  _payloadSteps() {
    return [...this._edit.steps].map(([key, s]) => this._stepPayload(key, s));
  }

  // live preview (spec 5.4): every change switches the device; cancel restores the state from before
  _preview(key, s) {
    if (!this._edit?.preview || !["off", "set", "on"].includes(s.choice)) return;
    const { delay, ...step } = this._stepPayload(key, s);
    this._previewed = true;
    this.hass
      .callWS({ type: `${WS}/preview`, step, ...(this._house ? {} : { area_id: this._config.area }) })
      .catch(() => {});
  }

  _endPreview(restore) {
    if (!this._previewed) return;
    this._previewed = false;
    this.hass.callWS({ type: `${WS}/preview_end`, restore }).catch(() => {});
  }

  _cancel() {
    this._endPreview(true);
    this._edit = null;
  }

  async _loadNew() {
    this._endPreview(true);
    this._selected = this._edit.scene_id;
    await this._loadDetail();
    await this._openEditor(this._detail);
  }

  _renderConfirmDelete() {
    const used = this._detail?.id === this._edit.scene_id ? this._detail.used_in : { scenes: [], slots: [] };
    const slots = used.slots.map((s) => {
      const [scope, n] = s.split(":");
      return `${this._areaName(scope === HOUSE ? null : scope)} ${this._t("slot")} ${n}`;
    });
    const all = [...used.scenes, ...slots];
    return html`<div class="banner" role="alertdialog">${this._t("confirm_delete")}
      ${all.length ? html`<br />${this._t("used_on")} ${all.join(", ")}` : nothing}
      <br /><span class="muted">${this._t("outside_note")}</span><br />
      <button class="danger" data-action="delete" @click=${this._delete}>${this._t("yes")}</button>
      <button data-action="keep-scene" @click=${() => this._setEdit({ confirmDelete: false })}>${this._t("no")}</button></div>`;
  }

  async _save({ copy }) {
    const e = this._edit;
    const taken = this._scenes.some((s) => s.id !== e.scene_id && s.name.trim().toLowerCase() === e.name.trim().toLowerCase());
    if (taken && !copy) return this._setEdit({ error: "name_exists", errorDetail: "" });
    const msg = { type: `${WS}/save`, name: e.name, image: e.image, transition: e.transition, steps: this._payloadSteps() };
    if (!this._house) msg.area_id = this._config.area;
    if (this._data.is_admin) Object.assign(msg, { kind: e.kind, content_released: e.content_released });
    if (copy && e.scene_id) {
      const suffix = ` (${this._t("copy")})`;
      msg.name = e.name.slice(0, this._data.name_length - suffix.length) + suffix;
      msg.copy_from = e.scene_id;
    } else if (e.scene_id) {
      Object.assign(msg, { scene_id: e.scene_id, version: e.version });
    }
    this._setEdit({ busy: true, error: null });
    try {
      const res = await this.hass.callWS(msg);
      this._endPreview(false);
      this._edit = null;
      this._selected = res.scene_id;
      await this._load();
    } catch (err) {
      const conflict = err.code === "version_conflict";
      // the server sends "code: detail"; a device is named by its name
      const detail = /^\w+: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
      const named = /^[a-z_]+\.\S+$/.test(detail) ? this._name(detail) : detail;
      this._setEdit({ busy: false, conflict, error: conflict ? null : err.code ?? "default", errorDetail: named });
    }
  }

  async _delete() {
    const id = this._edit.scene_id;
    try {
      await this.hass.callWS({ type: `${WS}/delete`, scene_id: id });
      this._endPreview(true);
      this._edit = null;
      this._selected = null;
      this._detail = null;
    } catch (err) {
      this._setEdit({ confirmDelete: false, error: err.code ?? "default", errorDetail: "" });
    }
  }

  static styles = css`
    :host { display: block; }
    .card { background: var(--ha-card-background, var(--card-background-color, #fff)); color: var(--primary-text-color);
      border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none);
      border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color)); padding: 16px; }
    h2 { margin: 8px 0; font-size: 1.4em; } h3 { margin: 16px 0 4px; font-size: 1em; color: var(--secondary-text-color); }
    button, select, input[type=number], input:not([type]) { min-height: 44px; font: inherit; color: inherit; border-radius: 8px;
      border: 1px solid var(--divider-color); background: transparent; padding: 0 12px; box-sizing: border-box; }
    button { cursor: pointer; min-width: 44px; }
    button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--primary-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    button.danger { color: var(--error-color); border-color: var(--error-color); }
    button.link { border: none; text-align: left; padding: 0; } button.wide { width: 100%; margin-bottom: 8px; }
    input[type=checkbox] { width: 24px; height: 24px; min-width: 24px; margin: 10px; accent-color: var(--primary-color); }
    input[type=range] { min-height: 44px; accent-color: var(--primary-color); }
    input[type=number] { width: 7em; }
    .row { display: flex; align-items: center; gap: 8px; min-height: 48px; border-bottom: 1px solid var(--divider-color); flex-wrap: wrap; }
    .row.selected { background: var(--secondary-background-color); } .row .name { flex: 1; min-width: 140px; }
    .thumb { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; background: var(--secondary-background-color); flex: none; }
    .hero { width: 100%; max-height: 180px; object-fit: cover; border-radius: 8px; }
    .head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; } .head h2 { flex: 1 1 100%; }
    .columns { display: grid; grid-template-columns: minmax(220px, 1fr) 2fr; gap: 24px; }
    .editor label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
    .editor label.inline, .editor h3 label, .device label.name { flex-direction: row; align-items: center; margin: 0; }
    .editor label.value { flex-direction: row; align-items: center; gap: 8px; margin: 0; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
    button.small { font-size: .85em; margin-left: 8px; } button:disabled { opacity: .5; cursor: default; }
    .badge { font-size: .75em; padding: 2px 6px; border-radius: 4px; background: var(--secondary-background-color); margin-left: 4px; }
    .badge.warn { background: var(--warning-color, #f4b400); color: #000; }
    .muted { color: var(--secondary-text-color); } .error { color: var(--error-color); }
    .banner { padding: 12px; border-radius: 8px; background: var(--secondary-background-color); margin: 8px 0; }
    .banner button { margin: 8px 8px 0 0; } .heart select { min-width: 90px; }
    .crop canvas { width: 100%; max-width: 320px; aspect-ratio: 4 / 3; border-radius: 8px; background: var(--secondary-background-color); }
    .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
    .tile { position: relative; height: 110px; padding: 0; overflow: hidden; display: flex; align-items: flex-end; }
    .tile img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
    .tile span { position: relative; width: 100%; padding: 8px; background: rgba(0,0,0,.45); color: #fff; text-align: left; }
  `;
}

customElements.define("resident-scenes-card", ResidentScenesCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "resident-scenes-card", name: "Resident Scenes", description: "Create, edit and run resident scenes" });
