// Resident Scenes card, built with Lit and bundled into one file (npm run build).
// No Home Assistant internal elements: only the documented card API and theme variables.
import { LitElement, html, css, nothing } from "lit";
import { live } from "lit/directives/live.js";
import { repeat } from "lit/directives/repeat.js";

const VERSION = "0.3.5"; // must match the integration (checked by tests)
const WS = "resident_scenes";
const HOUSE = "_house";
const DOMAINS = ["light", "cover", "climate", "switch", "fan", "media_player", "scene"];
const LIVE = ["light", "cover", "switch", "fan"]; // spec 5.4: no live adjustments for climate and music
const FLAGS = ["missing", "not_released", "other_area"]; // stored value stays, cannot be changed (spec 4.5)
const VISIBLE_RELOAD = 5 * 60 * 1000; // wall panels turn the screen on often (review N2)
const newId = () => Math.random().toString(36).slice(2, 10);
const PLACEHOLDER = html`<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor"
  d="M19 19H5V5h14m0-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2m-5.04 9.29-2.75 3.54-1.96-2.36L6.5 17h11z"/></svg>`;

const I18N = {
  en: {
    new_scene: "New scene", scenes: "Scenes", other_scenes: "Other scenes", favorites: "Favorites",
    play: "Play", played: "Played", play_failed: "The scene could not be played.", edit: "Edit", done: "Done",
    delete: "Delete", duplicate: "Duplicate", back: "Back", name: "Name", image: "Image", no_image: "No image",
    choose_image: "Change image", all: "All", slot: "Slot", free: "free", no_slot: "No slot", close: "Close",
    loses: "loses its place.", replace: "Replace", off: "Off", closed: "Closed", on: "On", favorite: "Favorite",
    volume: "Volume", call: "Run", missing: "Device missing", unavailable: "Not reachable", not_released: "Not released",
    other_area: "In another room", favorite_missing: "Favorite missing", scene_missing: "Scene missing",
    all_off: "All off", all_closed: "All closed", all_house: "All in the house",
    rights_gone: "Your right to change scenes was withdrawn.", empty: "No scenes yet.", no_steps: "No steps yet.",
    no_devices: "No released devices.", confirm_delete: "Delete the scene “{name}” for good?", used_on: "Used by:",
    outside_note: "Automations and schedules using it will stop working.", yes: "Delete", no: "Keep", cancel: "Cancel",
    copy: "copy", reload: "A new version is installed. Please reload.", reload_btn: "Reload", house: "House", no_room: "No room", devices_n: "devices",
    installer: "Installer", protected: "Installer scene (protected)", released: "Content released to residents",
    brightness: "Brightness", color_temp: "Colour temperature", hue: "Colour", position: "Position", tilt: "Tilt",
    temperature: "Temperature", percentage: "Speed", transition: "Transition (s)", order: "Sequence",
    live: "Live adjustments", undo: "Undo last change", rights: "Permissions", may_edit: "may change scenes",
    panel: "Panel", own_image: "Own image", crop_x: "Horizontal", crop_y: "Vertical", use_image: "Use image",
    room_scene: "Room scene", remove: "Remove", open: "Open", add_step: "Add step", add_delay: "Add delay",
    pick_room: "Room", pick_domain: "Trade", stale: "Not up to date, retrying …",
    offline: "Connection lost. Editing is locked until it is back.", seconds: "Delay (s)",
    no_room_scene: "No room scene any more", white: "White", colour: "Colour", white_channel: "White", saturation: "Saturation",
    drag: "Drag to reorder, or use the arrow keys", moved: "Moved to position {n} of {m}.", more: "more",
    no_effect: "no effect", undone: "The previous state applies again.",
    no_favorites: "No favorites: none are stored in the music system, or its favorites sensor is disabled.",
    light: "Lights", cover: "Shading", climate: "Climate", switch: "Switches", fan: "Fans",
    media_player: "Music", scene: "Scenes",
    err: {
      unauthorized: "You may not change scenes.", name_exists: "This name is taken.",
      invalid_name: "Name is empty or too long.", limit_reached: "Limit of scenes reached.",
      too_many_steps: "Too many steps or devices.", entity_not_allowed: "Not released for this scene:",
      entity_unavailable: "Not reachable, its state cannot be captured:",
      unknown_favorite: "This favorite no longer exists.", not_found: "The scene no longer exists.",
      invalid_step: "Invalid setting.", invalid_value: "Value out of range:", invalid_delay: "Delay out of range:",
      invalid_temperature: "Temperature out of range:", invalid_temperature_step: "Temperature not on the step of the device:",
      favorite_not_supported: "Favorites only work on players of the music system:",
      invalid_scene_call: "This scene cannot be called.", duplicate_entity: "Device used twice:",
      protected: "Installer scene: only its released content can be changed.", invalid_image: "Image not found.",
      invalid_image_file: "This is not an image file.", image_too_large: "Image too large, limit:",
      image_limit: "Image limit reached:", nothing_to_undo: "Nothing to undo.",
      step_missing: "This step was removed meanwhile. The current state is shown.", default: "Saving failed.",
    },
  },
  de: {
    new_scene: "Neue Szene", scenes: "Szenen", other_scenes: "Weitere Szenen", favorites: "Favoriten",
    play: "Abspielen", played: "Ausgelöst", play_failed: "Die Szene ließ sich nicht auslösen.", edit: "Ändern",
    done: "Fertig", delete: "Löschen", duplicate: "Duplizieren", back: "Zurück", name: "Name", image: "Bild",
    no_image: "Kein Bild", choose_image: "Bild ändern", all: "Alle", slot: "Platz", free: "frei", no_slot: "Kein Platz",
    close: "Schließen", loses: "verliert seinen Platz.", replace: "Ersetzen", off: "Aus", closed: "Zu", on: "An",
    favorite: "Favorit", volume: "Lautstärke", call: "Aufruf", missing: "Gerät fehlt", unavailable: "Nicht erreichbar",
    not_released: "Nicht freigegeben", other_area: "In anderem Raum", favorite_missing: "Favorit fehlt",
    scene_missing: "Szene fehlt", all_off: "Alle aus", all_closed: "Alle zu", all_house: "Alle im Haus",
    rights_gone: "Ihr Recht, Szenen zu ändern, wurde entzogen.", empty: "Noch keine Szenen.",
    no_steps: "Noch keine Schritte.", no_devices: "Keine freigegebenen Geräte.",
    confirm_delete: "Die Szene „{name}“ endgültig löschen?", used_on: "Verwendet in:",
    outside_note: "Automationen und Zeitpläne damit wirken nicht mehr.", yes: "Löschen", no: "Behalten",
    cancel: "Abbrechen", copy: "Kopie", reload: "Eine neue Version ist installiert. Bitte neu laden.",
    reload_btn: "Neu laden", house: "Haus", no_room: "Ohne Raum", devices_n: "Geräte", installer: "Errichter", protected: "Errichterszene (geschützt)",
    released: "Inhalt für Bewohner freigegeben", brightness: "Helligkeit", color_temp: "Farbtemperatur",
    hue: "Farbe", position: "Position", tilt: "Neigung", temperature: "Temperatur", percentage: "Stufe",
    transition: "Übergang (s)", order: "Ablauf", live: "Live-Anpassungen", undo: "Zurücknehmen",
    rights: "Berechtigungen", may_edit: "darf Szenen ändern", panel: "Panel", own_image: "Eigenes Bild",
    crop_x: "Waagerecht", crop_y: "Senkrecht", use_image: "Bild übernehmen", room_scene: "Raumszene",
    remove: "Entfernen", open: "Öffnen", add_step: "Schritt hinzufügen", add_delay: "Verzögerung hinzufügen",
    pick_room: "Raum", pick_domain: "Gewerk", stale: "Nicht aktuell, neuer Versuch läuft …",
    offline: "Verbindung unterbrochen. Der Editor ist gesperrt, bis sie zurück ist.", seconds: "Verzögerung (s)",
    no_room_scene: "Keine Raumszene mehr", white: "Weiß", colour: "Farbe", white_channel: "Weiß", saturation: "Sättigung",
    drag: "Ziehen zum Sortieren, oder Pfeiltasten", moved: "An Stelle {n} von {m} verschoben.", more: "weitere",
    no_effect: "ohne Wirkung", undone: "Der frühere Stand gilt wieder.",
    no_favorites: "Keine Favoriten: Im Musiksystem sind keine hinterlegt, oder sein Favoriten-Sensor ist abgeschaltet.",
    light: "Licht", cover: "Beschattung", climate: "Klima", switch: "Schalter", fan: "Lüfter",
    media_player: "Musik", scene: "Szenen",
    err: {
      unauthorized: "Sie dürfen Szenen nicht ändern.", name_exists: "Dieser Name ist schon vergeben.",
      invalid_name: "Name fehlt oder ist zu lang.", limit_reached: "Höchstzahl an Szenen erreicht.",
      too_many_steps: "Zu viele Schritte oder Geräte.", entity_not_allowed: "Für diese Szene nicht freigegeben:",
      entity_unavailable: "Nicht erreichbar, der Zustand lässt sich nicht übernehmen:",
      unknown_favorite: "Diesen Favoriten gibt es nicht mehr.", not_found: "Die Szene gibt es nicht mehr.",
      invalid_step: "Ungültige Einstellung.", invalid_value: "Wert außerhalb des Bereichs:",
      invalid_delay: "Verzögerung außerhalb des Bereichs:", invalid_temperature: "Temperatur außerhalb des Bereichs:", invalid_temperature_step: "Temperatur passt nicht zur Schrittweite des Geräts:", favorite_not_supported: "Favoriten nur für Player des Musiksystems:",
      invalid_scene_call: "Diese Szene lässt sich nicht aufrufen.", duplicate_entity: "Gerät doppelt:",
      protected: "Errichterszene: nur der freigegebene Inhalt lässt sich ändern.", invalid_image: "Bild nicht gefunden.",
      invalid_image_file: "Das ist keine Bilddatei.", image_too_large: "Bild zu groß, Grenze:",
      image_limit: "Höchstzahl an Bildern erreicht:", nothing_to_undo: "Nichts zurückzunehmen.",
      step_missing: "Dieser Schritt wurde inzwischen entfernt. Der aktuelle Stand wird gezeigt.",
      default: "Speichern fehlgeschlagen.",
    },
  },
};

const TILE = { w: 640, h: 640 }; // tile format: the square (spec 4.8)

class ResidentScenesCard extends LitElement {
  _drafts = new Map(); // what the user is typing or dragging, kept over updates from the server (spec 5.6)
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
    _slots: { state: true },
    _played: { state: true },
    _offline: { state: true },
    _undone: { state: true },
    _announce: { state: true },
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

  // sections view: the full width of the section, so the two columns appear (V1, X2)
  getGridOptions() {
    return { columns: this._config?.view === "manage" ? "full" : 12, min_columns: 6, rows: "auto" };
  }

  connectedCallback() {
    super.connectedCallback();
    this._ro = new ResizeObserver(([entry]) => {
      this._narrow = entry.contentRect.width < 600;
      this.updateComplete.then(() => this._fitLines()); // after a switch of the layout
    });
    this._ro.observe(this);
    // a press beside the open list of favorites closes it (Z5)
    this._outside ??= (ev) => {
      if (this._edit?.favOpen && !ev.composedPath().some((n) => n.classList?.contains("favorites"))) this._setEdit({ favOpen: null });
    };
    window.addEventListener("click", this._outside);
    if (this.hass && !this._started) this._start();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._started = false;
    clearInterval(this._timer);
    clearTimeout(this._retry);
    document.removeEventListener("visibilitychange", this._onVisible);
    this.hass?.connection.removeEventListener?.("ready", this._onReady);
    this.hass?.connection.removeEventListener?.("disconnected", this._onDown);
    this._ro?.disconnect();
    window.removeEventListener("click", this._outside);
    this._unsubscribe();
  }

  updated(changed) {
    if (changed.has("hass") && this.hass && !this._started && this.isConnected) this._start();
    // a step moved with the arrow keys keeps the focus on its handle
    const f = this._focusStep;
    if (f && this._detail?.sequence?.[f.index]?.id === f.id) {
      this._focusStep = null;
      this.renderRoot.querySelector(`[data-action="drag"][data-id="${f.id}"]`)?.focus();
    }
    // a question takes the focus on its safe answer, also when its content changes, and gives it back (V15, X5)
    const dialog = this.renderRoot.querySelector(".dialog");
    const safe = dialog?.querySelector("[data-safe]");
    if (dialog && !this._dialog) this._opener = this.renderRoot.activeElement;
    if (safe && safe !== this._safe) safe.focus();
    else if (!dialog && this._dialog) {
      if (this._opener?.isConnected) this._opener.focus();
      this._opener = null;
    }
    this._dialog = dialog;
    this._safe = safe;
    this._fitLines();
  }

  // the row of a step names the devices that fully fit, the rest as "+ 3 weitere"; none fits: "3 Geräte" (spec 5.2, Y3)
  _fitLines() {
    for (const clip of this.renderRoot.querySelectorAll(".clip[data-fit]")) {
      const parts = clip.parts ?? [];
      const more = clip.nextElementSibling;
      // measured once per text and width, not on every update (Z4); reading the width costs one layout per pass, not per row
      const key = JSON.stringify([clip.parentElement.clientWidth, this._lang, parts]);
      if (clip.fitted === key) continue;
      clip.fitted = key;
      const show = (k) => {
        clip.textContent = parts.slice(0, k).join(", ");
        more.textContent = k === parts.length ? "" : k ? `+ ${parts.length - k} ${this._t("more")}` : `${parts.length} ${this._t("devices_n")}`;
      };
      let k = parts.length;
      show(k);
      // no layout (hidden card, jsdom): two devices, the line clipped
      if (!clip.parentElement.clientWidth) {
        show(Math.min(2, k));
        continue;
      }
      while (k > (parts.length > 1 ? 0 : 1) && clip.scrollWidth > clip.clientWidth) show(--k);
    }
  }

  // Escape picks the safe answer, Tab stays inside the question (spec 5.7)
  _dialogKey(ev) {
    if (ev.key === "Escape") {
      ev.stopPropagation();
      this.renderRoot.querySelector(".dialog [data-safe]")?.click();
    } else if (ev.key === "Tab") {
      const items = [...this.renderRoot.querySelectorAll(".dialog button:not([disabled])")];
      const at = items.indexOf(this.renderRoot.activeElement);
      const next = at < 0 ? 0 : (at + (ev.shiftKey ? -1 : 1) + items.length) % items.length;
      ev.preventDefault();
      items[next]?.focus();
    }
  }

  _start() {
    this._started = true;
    this._needSub = true;
    // signed image URLs die after a restart and after a day; wall panels run for weeks (spec 4.3, 5.7)
    this._onReady ??= () => ((this._offline = false), (this._needSub = true), this._load());
    this._onDown ??= () => (this._offline = true);
    this._onVisible ??= () =>
      document.visibilityState === "visible" && Date.now() - (this._loadedAt ?? 0) > VISIBLE_RELOAD && this._load();
    this.hass.connection.addEventListener?.("ready", this._onReady);
    this.hass.connection.addEventListener?.("disconnected", this._onDown);
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

  get _lang() {
    return this.hass?.locale?.language?.startsWith("de") ? "de" : "en";
  }

  _t(key) {
    return key.split(".").reduce((o, k) => o?.[k], I18N[this._lang]) ?? key;
  }

  // the range the server checks a setpoint against, its defaults included
  _tempRange(c) {
    return `${this._num(c.min_temp ?? 5)}–${this._num(c.max_temp ?? 35)} ${this._unit}`;
  }

  _num(value) {
    return Number(value).toLocaleString(this._lang); // 2.700 K in German (spec 5.7)
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
    // rights withdrawn while editing: back to the scene view, the server rejects inputs anyway
    if (this._edit && !this._data.can_edit) {
      this._edit = null;
      this._notice = "rights_gone";
    }
    if (this._rights && this._data.manages_rights) this._loadRights();
    if (!this._data.manages_rights) this._rights = null;
    if (this._edit && !fromServer) this._loadDevices(); // fresh signed URLs of the image library
    if (this._selected) await this._loadDetail();
  }

  async _loadDetail() {
    try {
      const detail = await this.hass.callWS({ type: `${WS}/scene`, scene_id: this._selected });
      const focused = this.renderRoot.activeElement?.dataset?.key;
      for (const key of this._drafts.keys()) if (key !== focused) this._drafts.delete(key);
      this._detail = detail;
      if (this._edit?.open && !detail.sequence.some((s) => s.id === this._edit.open)) this._setEdit({ open: null });
    } catch (err) {
      if (err.code === "not_found") (this._selected = null), (this._detail = null), (this._edit = null);
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
        // older frontend: the server sends the name
      }
    }
    return fallback ?? eid;
  }

  _areaName(areaId) {
    return areaId ? this.hass.areas?.[areaId]?.name ?? areaId : this._t("house");
  }

  async _play(entityId) {
    if (!entityId) return;
    try {
      await this.hass.callService("scene", "turn_on", { entity_id: entityId });
      if (this._notice === "play_failed") this._notice = null;
      this._played = entityId; // short feedback (V9)
      setTimeout(() => this._played === entityId && (this._played = null), 1500);
    } catch (err) {
      this._notice = "play_failed";
    }
  }

  _err(code, detail) {
    const known = this._t(`err.${code}`) !== `err.${code}`;
    return known ? `${this._t(`err.${code}`)}${detail ? ` ${detail}` : ""}` : this._t("err.default");
  }

  _draft(key, stored) {
    return this._drafts.has(key) ? this._drafts.get(key) : stored;
  }

  _keep(key) {
    return (ev) => (this._drafts.set(key, ev.target.value), this.requestUpdate());
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
      ${this._stale ? html`<p class="muted" role="status">${this._t("stale")}</p>` : nothing}
      ${this._notice ? html`<p class="error" role="alert">${this._t(this._notice)}</p>` : nothing} ${body}
    </div>`;
  }

  _renderFavorites() {
    const tiles = this._data.favorites.map((id) => this._scene(id)).filter(Boolean);
    if (!tiles.length) return nothing;
    return html`<div class="tiles">
      ${tiles.map(
        (s) => html`<button class="tile" data-action="play" aria-label=${s.name} @click=${() => this._play(s.entity_id)}>
          ${s.image_url ? html`<img src=${s.image_url} alt="" />` : PLACEHOLDER}<span>${s.name}</span>
        </button>`
      )}
    </div>`;
  }

  _renderManage() {
    const showDetail = this._config.view === "manage" && (this._selected || this._edit || this._rights);
    const list = this._renderList();
    if (!showDetail) return list;
    const editing = this._edit && this._detail?.id === this._edit.scene_id;
    const detail = editing ? this._renderEditor() : this._rights ? this._renderRights() : this._renderDetail();
    // a question lies over the whole card, the card behind takes no input (spec 5.7, X5)
    const question = editing && this._edit.confirmDelete ? this._renderConfirmDelete()
      : !editing && this._slots && this._detail ? this._renderSlots() : nothing;
    const body = this._narrow ? detail : html`<div class="columns"><div class="col-list">${list}</div><div class="col-detail">${detail}</div></div>`;
    return html`<div ?inert=${question !== nothing}>${body}</div>${question}`;
  }

  _playButton(eid, label = false, name = "") {
    const done = this._played === eid;
    return html`<button class=${label ? "primary" : "icon"} data-action="play" aria-label=${name ? `${this._t("play")}: ${name}` : this._t("play")}
      @click=${() => this._play(eid)}>${done ? "✓" : "▶"}${label ? ` ${this._t(done ? "played" : "play")}` : ""}</button>`;
  }

  _renderList() {
    const manage = this._config.view === "manage";
    const d = this._data;
    const canEdit = manage && d.can_edit;
    const full = this._scenes.length >= d.limit;
    const favs = d.favorites.map((id) => this._scene(id)).filter(Boolean);
    const rest = this._scenes.filter((s) => !d.favorites.includes(s.id));
    const row = (s) => html`<div class="row ${this._selected === s.id ? "selected" : ""}">
      ${manage
        ? html`<button class="name link" data-action="select" data-id=${s.id} @click=${() => this._select(s.id)}>${s.name}</button>`
        : html`<span class="name">${s.name}</span>`}
      ${s.kind === "installer" ? html`<span class="badge">${this._t("installer")}</span>` : nothing}
      ${this._playButton(s.entity_id, false, s.name)}
    </div>`;
    return html`
      ${canEdit
        ? html`<button class="primary wide" data-action="new" ?disabled=${full} @click=${this._create}>
              + ${this._t("new_scene")}</button>
            ${full ? html`<p class="muted">${this._t("err.limit_reached")} (${d.limit})</p>` : nothing}`
        : nothing}
      ${manage && d.manages_rights
        ? html`<button class="wide" data-action="rights" @click=${this._openRights}>${this._t("rights")}</button>`
        : nothing}
      ${favs.length ? html`<h3>${this._t("favorites")}</h3>${favs.map(row)}` : nothing}
      ${rest.length ? html`<h3>${this._t("scenes")}</h3>${rest.map(row)}`
        : favs.length ? nothing : html`<h3>${this._t("scenes")}</h3><p class="muted">${this._t("empty")}</p>`}
      ${d.foreign_scenes.length
        ? html`<h3>${this._t("other_scenes")}</h3>
            ${d.foreign_scenes.map(
              (s) => html`<div class="row">
                <span class="name">${this._name(s.entity_id, s.name)}${s.knx ? html`<span class="badge">KNX</span>` : nothing}</span>
                ${this._playButton(s.entity_id, false, this._name(s.entity_id, s.name))}</div>`
            )}`
        : nothing}
    `;
  }

  async _select(id) {
    this._rights = null;
    this._edit = null;
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
        ${this._hero(s)}
        <div class="title">
        <h2>${s.name} ${s.kind === "installer" ? html`<span class="badge">${this._t("installer")}</span>` : nothing}</h2>
        <div class="tools">
        ${this._playButton(s.entity_id, true)}
        ${d.can_edit
          ? html`<button data-action="heart" aria-label=${this._t("favorites")} aria-pressed=${slot >= 0 ? "true" : "false"}
              @click=${() => (this._slots = {})}>♥${slot >= 0 ? ` ${this._t("slot")} ${slot + 1}` : ""}</button>`
          : nothing}
        ${d.can_edit && s.editable
          ? html`<button data-action="edit" @click=${() => this._openEditor(s.id)}>${this._t("edit")}</button>`
          : nothing}
        ${d.can_edit && s.editable && s.can_undo
          ? html`<button data-action="undo" @click=${this._undo}>${this._t("undo")}</button>`
          : nothing}
      </div></div></div>
      ${this._detailError ? html`<p class="error" role="alert">${this._detailError}</p>` : nothing}
      <p class="muted" role="status">${this._undone ? this._t("undone") : nothing}</p>
      ${s.sequence.length
        ? html`<h3>${this._t("order")}</h3>${s.sequence.map((step, i) => html`<div class="row">${this._stepLine(step, i === s.sequence.length - 1)}</div>`)}`
        : html`<p class="muted">${this._t("no_steps")}</p>`}`;
  }

  // the scene image: a square of 80 px beside the name, the placeholder without one (spec 5.2, Z6)
  _hero(s) {
    return s.image_url ? html`<img class="hero" src=${s.image_url} alt="" />` : html`<span class="hero">${PLACEHOLDER}</span>`;
  }

  _stepTitle(step) {
    const room = !this._house ? "" : `${step.area_id ? this._areaName(step.area_id) : this._t("no_room")} – `;
    return room + this._t(step.type === "scene" ? "scene" : step.domain);
  }

  // at most two lines per step: "Küche – Licht" over "Decke 60 %, Wand Aus + 3 weitere"; "+ 5 s" (spec 5.2)
  _stepLine(step, last = false) {
    if (step.type === "delay") {
      // a delay at the end delays nothing (spec 4.4)
      return html`<span class="name">+ ${this._num(step.seconds)} s${last ? html` <span class="muted">· ${this._t("no_effect")}</span>` : nothing}</span>`;
    }
    const issue = step.type === "scene" ? step.issue : step.entries.find((e) => e.issue)?.issue;
    // the devices are filled in by _fitLines after the layout
    const parts = step.type === "scene" ? [] : step.entries.map((e) => `${this._name(e.entity_id, e.name)} ${this._summary(e)}`);
    const values = parts.length
      ? html`<span class="clip" data-fit .parts=${parts}></span><span class="more"></span>`
      : html`<span class="clip">${step.type === "scene" ? step.name : "–"}</span>`;
    return html`<span class="name"><span class="line">${this._stepTitle(step)}</span>
      <span class="line">${values}${issue ? html`<span class="badge warn">${this._t(issue)}</span>` : nothing}</span></span>`;
  }

  _summary(entry) {
    const pct = (v) => `${Math.round(v * 100)} %`;
    if (entry.call) return this._t("call");
    if (entry.music === "off") return this._t("off");
    if (entry.music === "on") return `${this._t("on")} · ${pct(entry.volume)}`;
    if (entry.music === "favorite") return `${entry.favorite_name} · ${pct(entry.volume)}`;
    const a = entry.attributes ?? {};
    if (entry.state === "off") return this._t("off");
    if (entry.state === "closed") return this._t("closed");
    if (a.brightness != null) {
      const color = a.color_temp_kelvin ? ` · ${this._num(a.color_temp_kelvin)} K` : "";
      return `${Math.round(a.brightness / 2.55)} %${color}`;
    }
    if (a.current_position != null) return `${a.current_position} %`;
    if (a.temperature != null) return `${this._state(entry.entity_id, entry.state)} · ${this._num(a.temperature)} ${this._unit}`;
    if (a.percentage != null) return `${a.percentage} %`;
    return entry.state === "on" ? this._t("on") : this._state(entry.entity_id, entry.state);
  }

  // the name of a state in the language of the account, e.g. hvac mode "heat" (X8)
  _state(eid, state) {
    const st = this.hass.states[eid];
    try {
      const name = st && this.hass.formatEntityState?.(st, state);
      if (name) return name;
    } catch (err) {
      // older frontend: the translation key below
    }
    const domain = eid.split(".")[0];
    return this.hass.localize?.(`component.${domain}.entity_component._.state.${state}`) || state;
  }

  get _unit() {
    return this.hass.config?.unit_system?.temperature ?? "°C";
  }

  // ---------- favorite slots (spec 4.7, V2) ----------

  _renderSlots() {
    const d = this._data;
    const current = d.favorites.indexOf(this._detail.id);
    const ask = this._slots.ask;
    return html`<div class="overlay" @keydown=${this._dialogKey}><div class="dialog" role="dialog" aria-modal="true" aria-label=${this._t("favorites")}>
      ${ask != null
        ? html`<p>${this._t("slot")} ${ask + 1}: ${this._scene(d.favorites[ask])?.name} ${this._t("loses")}</p>
            <div class="actions">
              <button class="primary" data-action="slot-confirm" @click=${() => this._setFavorite(ask, true)}>${this._t("replace")}</button>
              <button data-action="slot-cancel" data-safe @click=${() => (this._slots = {})}>${this._t("cancel")}</button></div>`
        : html`<h3>${this._t("favorites")}</h3>
            ${d.favorites.map(
              (id, i) => html`<button class="wide" data-action="slot" data-slot=${i} aria-pressed=${i === current ? "true" : "false"}
                @click=${() => this._setFavorite(i)}>${this._t("slot")} ${i + 1} – ${id ? this._scene(id)?.name ?? "" : this._t("free")}</button>`
            )}
            ${current >= 0
              ? html`<button class="wide" data-action="slot-clear" @click=${() => this._setFavorite(null)}>${this._t("no_slot")}</button>`
              : nothing}
            <button class="wide" data-action="slot-close" data-safe @click=${() => (this._slots = null)}>${this._t("close")}</button>`}
    </div></div>`;
  }

  async _setFavorite(slot, confirmed = false) {
    await this._load(); // decide on the current assignment, not on the one shown when the dialog opened (V2)
    const fav = this._data.favorites;
    const id = this._detail?.id;
    const current = fav.indexOf(id);
    const holder = slot == null ? null : fav[slot];
    if (holder && holder !== id && !confirmed) return (this._slots = { ask: slot });
    this._slots = null;
    try {
      if (slot == null && current >= 0) {
        await this.hass.callWS({ type: `${WS}/set_favorite`, scope: this._scope, slot: current, scene_id: null });
      } else if (slot != null && holder !== id) {
        await this.hass.callWS({ type: `${WS}/set_favorite`, scope: this._scope, slot, scene_id: id });
      }
    } catch (err) {
      this._detailError = this._err(err.code);
    }
    await this._load();
  }

  // ---------- rights (spec 3) ----------

  async _openRights() {
    this._selected = null;
    this._detail = null;
    this._edit = null;
    await this._loadRights();
  }

  _renderRights() {
    return html`${this._narrow ? html`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : nothing}
      <h2>${this._t("rights")}</h2>
      ${this._rights.map(
        (a) => html`<div class="row">
          <span class="name">${a.name} ${a.kind === "panel" ? html`<span class="badge">${this._t("panel")}</span>` : nothing}</span>
          ${this._switch("right", a.can_edit, this._t("may_edit"), (on) => this._setRight(a.user_id, on), a.user_id)}
        </div>`
      )}`;
  }

  async _setRight(userId, canEdit) {
    try {
      await this.hass.callWS({ type: `${WS}/set_right`, user_id: userId, can_edit: canEdit });
    } finally {
      await this._loadRights();
    }
  }

  async _undo() {
    this._detailError = null;
    try {
      await this.hass.callWS({ type: `${WS}/undo`, scene_id: this._detail.id, version: this._detail.version });
      this._undone = true; // spec 5.3: the card says briefly that the previous state applies again
      clearTimeout(this._undoneTimer);
      this._undoneTimer = setTimeout(() => (this._undone = false), 4000);
    } catch (err) {
      this._detailError = this._err(err.code);
    }
    await this._load();
  }

  // ---------- custom controls (spec 5.7, V10) ----------

  _switch(field, on, label, change, id) {
    return html`<button class="switch" role="switch" aria-checked=${on ? "true" : "false"} data-field=${field}
      data-entity=${id ?? nothing} @click=${() => change(!on)}><span class="track"></span><span>${label}</span></button>`;
  }

  // the marked choice of an unticked device ticks it (spec 4.5, X7)
  _seg(field, eid, options, current, pick, ticked = true) {
    return html`<div class="seg" role="radiogroup" data-field=${field} data-entity=${eid}>
      ${options.map(([value, label]) => html`<button role="radio" aria-checked=${value === current ? "true" : "false"}
        data-value=${value} @click=${() => (value !== current || !ticked) && pick(value)}>${label}</button>`)}</div>`;
  }

  // ---------- editor: every input is stored at once (spec 4.5) ----------

  async _create() {
    const edit = newId();
    try {
      const res = await this.hass.callWS({ type: `${WS}/create`, area_id: this._house ? null : this._config.area,
        name: this._t("new_scene"), edit });
      await this._openScene(res.scene_id, edit);
    } catch (err) {
      this._notice = this._err(err.code);
    }
  }

  async _openScene(id, edit) {
    this._rights = null;
    this._selected = id;
    this._detail = null;
    await this._openEditor(id, edit);
    await this._loadDetail();
  }

  async _openEditor(sceneId, edit = newId()) {
    this._notice = null;
    this._rights = null;
    this._edit = { id: edit, scene_id: sceneId, open: null, live: false, devices: [], favorites: [], images: [], room_scenes: [] };
    await this._loadDevices();
  }

  async _loadDevices() {
    try {
      const r = await this.hass.callWS({ type: `${WS}/devices`, ...(this._house ? {} : { area_id: this._config.area }) });
      for (const dev of r.entities) dev.label = this._name(dev.entity_id, dev.name);
      r.entities.sort((a, b) => a.label.localeCompare(b.label));
      if (this._edit) this._setEdit({ devices: r.entities, favorites: r.favorites, images: r.images, room_scenes: r.room_scenes });
    } catch (err) {
      // the editor keeps its last lists; stored entries still show
    }
  }

  _setEdit(patch) {
    this._edit = { ...this._edit, ...patch };
  }

  // one input = one command; changes come back through the subscription
  async _send(type, fields = {}, at = "error") {
    const e = this._edit;
    this._setEdit({ error: null, nameError: null });
    try {
      return await this.hass.callWS({ type: `${WS}/${type}`, scene_id: e.scene_id, edit: e.id, ...fields });
    } catch (err) {
      const detail = /^\w+: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
      const named = /^[a-z_]+\.\S+$/.test(detail) ? this._name(detail) : detail;
      const caps = this._edit?.devices.find((d) => d.entity_id === fields.entity_id)?.capabilities ?? {};
      // a refused setpoint names the range, not the key of the interface (Y4)
      const range = err.code === "invalid_value" && detail === "temperature";
      if (this._edit) this._setEdit(range ? { [at]: "invalid_temperature", errorDetail: this._tempRange(caps) }
        : { [at]: err.code ?? "default", errorDetail: named });
      this._drafts.clear(); // a rejected input shows the stored value again (spec 4.5)
      await this._loadDetail(); // also after step_missing: the step is gone, show the sequence as stored
      return undefined;
    }
  }

  async _done() {
    this._edit = null; // nothing to save and nothing to restore (spec 5.4)
    await this._loadDetail();
  }

  async _rename(name) {
    if (name.trim() === this._detail.name) return;
    await this._send("update", { name: name.trim() }, "nameError");
  }

  async _duplicate() {
    const edit = newId();
    const res = await this._send("duplicate", { suffix: ` (${this._t("copy")})`, edit });
    if (res) await this._openScene(res.scene_id, edit);
  }

  async _addStep(fields) {
    const res = await this._send("add_step", fields);
    this._setEdit({ adding: null });
    if (!res) return;
    await this._loadDetail();
    if (fields.step_type === "group") this._setEdit({ open: res.step_id, live: false });
  }

  _renderEditor() {
    const e = this._edit;
    const step = e.open && this._detail.sequence.find((x) => x.id === e.open);
    return html`${this._offline ? html`<p class="error" role="alert">${this._t("offline")}</p>` : nothing}
      <div class="editor" ?inert=${this._offline}>
        ${e.error ? html`<p class="error" role="alert">${this._err(e.error, e.errorDetail)}</p>` : nothing}
        ${step ? this._renderStep(step) : this._renderSequence()}
        <p class="sr" role="status">${this._announce ?? nothing}</p>
      </div>`;
  }

  _renderSequence() {
    const e = this._edit;
    const s = this._detail;
    const d = this._data;
    const own = s.kind === "resident" || d.is_admin; // residents never change name or image of an installer scene
    const trades = this._house
      ? DOMAINS.filter((t) => t !== "scene" && e.devices.some((dev) => dev.domain === t && dev.released !== false))
      : [];
    return html`<div class="bar">
        <button class="icon" data-action="done-back" aria-label=${this._t("back")} @click=${this._done}>‹</button>
        ${own // the head image opens the image choice, no second thumbnail (spec 5.2, Z6)
          ? html`<button class="image-btn" data-action="image" aria-label=${this._t("choose_image")} aria-expanded=${e.picking ? "true" : "false"}
              @click=${() => this._setEdit({ picking: !e.picking })}>${this._hero(s)}<span class="pencil" aria-hidden="true">✎</span></button>`
          : nothing}
        <span class="name">${s.name}</span>
        <button class="primary" data-action="done" @click=${this._done}>${this._t("done")}</button>
      </div>
      ${own
        ? html`<label class="field">${this._t("name")}
              <input data-field="name" data-key="name" maxlength=${d.name_length} .value=${live(this._draft("name", s.name))}
                @input=${this._keep("name")} @keydown=${(ev) => ev.key === "Enter" && ev.target.blur()}
                @change=${(ev) => this._rename(ev.target.value)} />
              ${e.nameError ? html`<span class="error" role="alert">${this._err(e.nameError)}</span>` : nothing}</label>
            ${this._renderImagePicker()}`
        : nothing}
      <label class="field">${this._t("transition")}
        <input type="number" min="0" max=${d.max_transition} step="0.5" data-field="transition" data-key="transition"
          .value=${live(String(this._draft("transition", s.transition ?? "")))} @input=${this._keep("transition")}
          @change=${(ev) => this._send("update", { transition: ev.target.value === "" ? null : Number(ev.target.value) })} /></label>
      ${d.is_admin
        ? html`${this._switch("kind", s.kind === "installer", this._t("protected"),
              (on) => this._send("update", { kind: on ? "installer" : "resident" }))}
            ${s.kind === "installer"
              ? this._switch("released", s.content_released, this._t("released"), (on) => this._send("update", { content_released: on }))
              : nothing}`
        : nothing}
      ${trades.length
        ? html`<h3>${this._t("all_house")}</h3>
            <div class="actions">${trades.map(
              (t) => html`<button data-action="house-off" data-domain=${t} @click=${() => this._send("house_off", { domain: t })}>
                ${this._t(t)} · ${this._t(t === "cover" ? "all_closed" : "all_off")}</button>`
            )}</div>`
        : nothing}
      <h3>${this._t("order")}</h3>
      ${s.sequence.length
        ? repeat(s.sequence, (x) => x.id, (x, i) => this._renderStepRow(x, i, i === s.sequence.length - 1))
        : html`<p class="muted">${this._t("no_steps")}</p>`}
      ${e.adding ? this._renderAdd() : nothing}
      <div class="actions">
        <button data-action="add-step" @click=${() => this._setEdit({ adding: {} })}>+ ${this._t("add_step")}</button>
        <button data-action="add-delay" @click=${() => this._addStep({ step_type: "delay" })}>+ ${this._t("add_delay")}</button>
        <button data-action="duplicate" @click=${this._duplicate}>${this._t("duplicate")}</button>
        ${own
          ? html`<button class="danger" data-action="ask-delete" @click=${() => this._setEdit({ confirmDelete: true })}>${this._t("delete")}</button>`
          : nothing}
      </div>`;
  }

  _renderStepRow(step, i, last) {
    const remove = html`<button class="icon" data-action="remove-step" data-id=${step.id} aria-label=${this._t("remove")}
      @click=${() => this._send("remove_step", { step_id: step.id })}>✕</button>`;
    const handle = html`<span class="handle" role="button" tabindex="0" data-action="drag" data-id=${step.id}
      aria-label=${this._t("drag")} title=${this._t("drag")} @pointerdown=${(ev) => this._drag(ev, i)}
      @keydown=${(ev) => this._dragKey(ev, step, i)}>≡</span>`;
    const cls = `row order ${this._dragTo === i ? "drop" : ""}`;
    if (step.type === "delay") {
      const max = this._data.max_delay;
      const key = `delay:${step.id}`;
      // taps faster than the answer count on from the value sent last (W7)
      const base = () => {
        const sent = this._delaySent?.[step.id];
        return sent && Date.now() - sent.at < 2000 ? sent.seconds : step.seconds;
      };
      const set = (seconds) => {
        if (!(seconds >= 1 && seconds <= max)) return;
        (this._delaySent ??= {})[step.id] = { seconds, at: Date.now() };
        this._send("set_delay", { step_id: step.id, seconds });
      };
      return html`<div class="${cls} delay-row">${handle}
        <div class="delay">
          <button class="icon" data-action="delay-minus" aria-label="−1 s" ?disabled=${base() <= 1}
            @click=${() => set(base() - 1)}>−</button>
          <label class="plain">+ <input class="secs" inputmode="numeric" pattern="[0-9]*" maxlength="3" data-field="delay"
            data-key=${key} aria-label=${this._t("seconds")} .value=${live(String(this._draft(key, step.seconds)))}
            @input=${this._keep(key)} @change=${(ev) => this._typedDelay(key, ev.target.value, max, set)} /> s</label>
          <button class="icon" data-action="delay-plus" aria-label="+1 s" ?disabled=${base() >= max}
            @click=${() => set(base() + 1)}>+</button>
        </div>${remove}</div>${last ? html`<p class="muted hint">${this._t("no_effect")}</p>` : nothing}`;
    }
    return html`<div class=${cls}>${handle}${this._stepLine(step)}
      <div class="tools">
        ${step.type === "group"
          ? html`<button data-action="open" data-id=${step.id} @click=${() => this._setEdit({ open: step.id, live: false })}>
              ${this._t("open")}</button>`
          : nothing}${remove}</div></div>`;
  }

  // whole seconds from 1 to the limit; anything else shows the stored value again and says why (spec 4.5, X4)
  _typedDelay(key, typed, max, set) {
    const seconds = /^\s*\d+\s*$/.test(typed) ? Number(typed) : NaN;
    if (seconds >= 1 && seconds <= max) return set(seconds);
    this._drafts.delete(key);
    this._setEdit({ error: "invalid_delay", errorDetail: `1–${this._num(max)} s` });
  }

  async _dragKey(ev, step, i) {
    const to = ev.key === "ArrowUp" ? i - 1 : ev.key === "ArrowDown" ? i + 1 : -1;
    if (to < 0 || to >= this._detail.sequence.length) return;
    ev.preventDefault();
    this._focusStep = { id: step.id, index: to };
    const count = this._detail.sequence.length;
    // the new place for screen readers (spec 5.7)
    if (await this._send("move_step", { step_id: step.id, index: to })) {
      this._announce = this._t("moved").replace("{n}", to + 1).replace("{m}", count);
    }
  }

  // drag the handle of a row onto another row (spec 5.7); pointer events cover mouse, touch and pen
  _drag(ev, from) {
    ev.preventDefault();
    const handle = ev.currentTarget;
    handle.setPointerCapture?.(ev.pointerId);
    const id = this._detail.sequence[from].id;
    const move = (e) => {
      const rows = [...this.renderRoot.querySelectorAll(".row.order")];
      const to = rows.findIndex((r) => {
        const b = r.getBoundingClientRect();
        return e.clientY >= b.top && e.clientY < b.bottom;
      });
      if (to >= 0 && to !== this._dragTo) (this._dragTo = to), this.requestUpdate();
      // shortcut: scrolls only while the finger moves near the edge; add a timer if a resting finger must keep scrolling
      const edge = e.clientY < 48 ? -1 : e.clientY > window.innerHeight - 48 ? 1 : 0;
      const next = Math.min(Math.max((to < 0 ? from : to) + edge, 0), rows.length - 1);
      if (edge) rows[next]?.scrollIntoView?.({ block: "nearest" });
    };
    const cancel = () => ((this._dragTo = null), end()); // the browser took the gesture: nothing moves (review T4)
    const end = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", end);
      handle.removeEventListener("pointercancel", cancel);
      const to = this._dragTo;
      this._dragTo = null;
      this.requestUpdate();
      if (to != null && to !== from) this._send("move_step", { step_id: id, index: to });
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", cancel);
  }

  _renderAdd() {
    const e = this._edit;
    const a = e.adding;
    const close = html`<button data-action="add-cancel" @click=${() => this._setEdit({ adding: null })}>${this._t("cancel")}</button>`;
    if (this._house && a.area === undefined) {
      const areas = [...new Set([...e.devices.map((d) => d.area_id), ...e.room_scenes.map((r) => r.area_id)].filter(Boolean))]
        .sort((x, y) => this._areaName(x).localeCompare(this._areaName(y)));
      // released devices without a room get a step without a room (W2)
      if (e.devices.some((d) => d.area_id == null && d.released !== false)) areas.push(null);
      return html`<div class="pick"><h3>${this._t("pick_room")}</h3>
        ${areas.map((id) => html`<button data-action="pick-room" data-id=${id ?? ""} @click=${() => this._setEdit({ adding: { area: id } })}>
          ${id ? this._areaName(id) : this._t("no_room")}</button>`)}${close}</div>`;
    }
    const area = this._house ? a.area : this._config.area;
    const extra = this._house ? { area_id: area } : {};
    if (a.scenes) {
      return html`<div class="pick"><h3>${this._areaName(area)} – ${this._t("scene")}</h3>
        ${e.room_scenes.filter((r) => r.area_id === area).map(
          (r) => html`<button data-action="pick-scene" data-id=${r.id} @click=${() => this._addStep({ step_type: "scene", target: r.id, ...extra })}>
            ${r.name}</button>`
        )}${close}</div>`;
    }
    const domains = DOMAINS.filter((dm) => e.devices.some((d) => d.domain === dm && d.area_id === area && d.released !== false));
    const roomScenes = this._house && e.room_scenes.some((r) => r.area_id === area);
    return html`<div class="pick"><h3>${this._house ? `${area ? this._areaName(area) : this._t("no_room")} – ` : ""}${this._t("pick_domain")}</h3>
      ${domains.map((dm) => html`<button data-action="pick-domain" data-domain=${dm}
        @click=${() => this._addStep({ step_type: "group", domain: dm, ...extra })}>${this._t(dm === "scene" ? "other_scenes" : dm)}</button>`)}
      ${roomScenes
        ? html`<button data-action="pick-domain" data-domain="room_scene" @click=${() => this._setEdit({ adding: { area, scenes: true } })}>
            ${this._t("scene")}</button>`
        : nothing}${close}</div>`;
  }

  // ---------- opened group step (spec 5.2, 5.4) ----------

  _renderStep(step) {
    const e = this._edit;
    const devs = e.devices.filter((d) => d.domain === step.domain && d.area_id === step.area_id && d.released !== false);
    // a stored entry whose device is not offered any more stays visible with its reason
    const gone = step.entries
      .filter((en) => !devs.some((d) => d.entity_id === en.entity_id))
      .map((en) => ({ entity_id: en.entity_id, label: this._name(en.entity_id, en.name), domain: step.domain, released: false, capabilities: {} }));
    const all = [...devs, ...gone];
    const set = (mode) => this._send("set_all", { step_id: step.id, mode, live: this._edit.live });
    return html`<div class="bar">
        <button class="icon" data-action="close-step" aria-label=${this._t("back")} @click=${() => this._setEdit({ open: null })}>‹</button>
        <h3 class="name">${this._stepTitle(step)}</h3>
      </div>
      ${LIVE.includes(step.domain)
        ? this._switch("live", e.live, this._t("live"), (on) => (this._setEdit({ live: on }), on && set("capture")))
        : nothing}
      <div class="actions">
        <button data-action="all" @click=${() => set("capture")}>${this._t("all")}</button>
        <button data-action="all-off" @click=${() => set("off")}>${this._t(step.domain === "cover" ? "all_closed" : "all_off")}</button>
      </div>
      ${all.length ? repeat(all, (d) => d.entity_id, (d) => this._renderDevice(step, d)) : html`<p class="muted">${this._t("no_devices")}</p>`}`;
  }

  _renderDevice(step, dev) {
    const eid = dev.entity_id;
    const entry = step.entries.find((en) => en.entity_id === eid);
    const locked = dev.released === false || FLAGS.includes(entry?.issue);
    const st = this.hass.states[eid];
    const why = entry?.issue ?? (dev.released === false ? "not_released" : !st ? "missing" : !dev.available ? "unavailable" : "");
    // ticked shows the stored value, unticked the current state (V4)
    const source = entry ?? (st && { entity_id: eid, state: st.state, attributes: st.attributes });
    const tick = () => entry
      ? this._send("remove_entry", { step_id: step.id, entity_id: eid })
      : this._send("set_entry", { step_id: step.id, entity_id: eid, mode: "capture", live: this._edit.live });
    return html`<div class="row device">
      <button class="check" role="checkbox" aria-checked=${entry ? "true" : "false"} data-field="pick" data-entity=${eid}
        aria-label=${dev.label} ?disabled=${locked && !entry} @click=${tick}></button>
      <span class="name">${dev.label} ${why ? html`<span class="badge warn">${this._t(why)}</span>` : nothing}</span>
      ${locked || !source ? nothing : html`<div class="controls">${this._renderValues(step, dev, entry, source)}</div>`}
    </div>`;
  }

  _valuesFromStep(step) {
    const a = step.attributes ?? {};
    const domain = step.entity_id.split(".")[0];
    if (domain === "light") {
      const v = { brightness: a.brightness ?? 255 };
      if (a.color_mode === "white") return { ...v, white: true }; // its own white channel, no colour (Z2)
      // a light in white mode reports a colour too: take the one of its colour mode
      if (a.color_temp_kelvin && (a.color_mode === "color_temp" || !a.hs_color)) v.color_temp_kelvin = a.color_temp_kelvin;
      else if (a.hs_color) Object.assign(v, { hue: a.hs_color[0], saturation: a.hs_color[1] });
      return v;
    }
    if (domain === "cover") return { position: a.current_position ?? (step.state === "closed" ? 0 : 100), ...(a.current_tilt_position != null ? { tilt: a.current_tilt_position } : {}) };
    if (domain === "climate") return { hvac_mode: step.state, ...(a.temperature != null ? { temperature: a.temperature } : {}) };
    if (domain === "fan") return { percentage: a.percentage ?? 50 };
    return {};
  }

  // an input on an unticked device ticks it: set_entry adds the entry (spec 4.5)
  _renderValues(step, dev, entry, source) {
    const c = dev.capabilities ?? {};
    const eid = dev.entity_id;
    const v = this._valuesFromStep(source);
    const on = !["off", "closed"].includes(source.state);
    const base = { step_id: step.id, entity_id: eid, live: this._edit.live };
    const set = (values) => this._send("set_entry", { ...base, mode: "set", values });
    const off = () => this._send("set_entry", { ...base, mode: "off" });
    const music = (m, extra = {}) => this._send("set_entry", { ...base, mode: "music", music: m, ...extra });
    // full row width, value as number, acts on release (V5)
    const slider = (field, label, min, max, value, unit, apply) => {
      const key = `${field}:${step.id}:${eid}`;
      const shown = this._draft(key, value);
      return html`<label class="slider"><span>${this._t(label)}</span><output>${this._num(shown)} ${unit}</output>
        <input type="range" min=${min} max=${max} data-field=${field} data-entity=${eid} data-key=${key}
          .value=${live(String(shown))} @input=${this._keep(key)} @change=${(ev) => apply(Number(ev.target.value))} /></label>`;
    };
    const power = (send) => this._switch("on", on, this._t("on"), (o) => (o ? send() : off()), eid);
    if (dev.domain === "light") {
      // an input sends only its own value, the server keeps the stored rest, e.g. an xy colour (spec 4.5, X11)
      // the white mode of its own: a third state "Weiß" without sliders, kept by the server (Z2)
      // no colour mode at all (the light is off): "An" and the first input store the colour shown as well (spec 4.5, Y1)
      const unset = !on || (!source.attributes?.color_mode && v.color_temp_kelvin == null && v.hue == null);
      // with a white channel of its own and no stored colour the default is "Weiß" (review AA2)
      const plain = !!c.white_mode && (on && !!v.white || unset && v.hue == null && v.color_temp_kelvin == null);
      const white = !plain && c.color_temp && (!c.color || v.hue == null);
      const kelvin = v.color_temp_kelvin ?? c.min_kelvin ?? 2700;
      const colour = (patch) => set({ hue: v.hue ?? 30, saturation: v.saturation ?? 100, ...patch });
      const shown = unset
        ? (plain ? { white: true } : white ? { color_temp_kelvin: kelvin } : c.color ? { hue: v.hue ?? 30, saturation: v.saturation ?? 100 } : {})
        : {};
      const keep = (values) => set({ ...shown, ...values });
      const modes = [
        ...(c.white_mode ? [["white_channel", this._t("white_channel")]] : []),
        ...(c.color_temp ? [["white", this._t(c.white_mode ? "color_temp" : "white")]] : []),
        ...(c.color ? [["colour", this._t("colour")]] : []),
      ];
      const pick = { white_channel: () => set({ white: true }), white: () => set({ color_temp_kelvin: kelvin }), colour: () => colour({}) };
      return html`${power(() => keep({}))}
        ${c.brightness ? slider("brightness", "brightness", 1, 100, Math.round(v.brightness / 2.55), "%",
          (p) => keep({ brightness: Math.max(1, Math.round(p * 2.55)) })) : nothing}
        ${modes.length > 1
          ? this._seg("light_mode", eid, modes, plain ? "white_channel" : white ? "white" : "colour", (m) => pick[m](), !!entry)
          : nothing}
        ${white ? slider("color_temp_kelvin", "color_temp", c.min_kelvin ?? 2000, c.max_kelvin ?? 6500, kelvin, "K",
          (k) => set({ color_temp_kelvin: k })) : nothing}
        ${c.color && !white && !plain
          ? html`${slider("hue", "hue", 0, 360, v.hue ?? 30, "°", (h) => colour({ hue: h }))}
              ${slider("saturation", "saturation", 0, 100, v.saturation ?? 100, "%", (x) => colour({ saturation: x }))}`
          : nothing}`;
    }
    if (dev.domain === "cover") {
      // position and tilt are stored together (spec 4.5)
      const send = (patch) => set({ ...(c.position ? { position: v.position } : {}), ...(c.tilt ? { tilt: v.tilt ?? 50 } : {}), ...patch });
      return html`${c.position ? slider("position", "position", 0, 100, v.position, "%", (p) => send({ position: p })) : nothing}
        ${c.tilt ? slider("tilt", "tilt", 0, 100, v.tilt ?? 50, "%", (p) => send({ tilt: p })) : nothing}`;
    }
    if (dev.domain === "climate") {
      const key = `temperature:${step.id}:${eid}`;
      const send = (patch) => set({ hvac_mode: v.hvac_mode, ...(v.temperature != null ? { temperature: v.temperature } : {}), ...patch });
      // a text field: no arrows of the browser (X8); "21,5" is read like "21.5", the range is named like the delay's (Y4)
      const typed = (ev) => {
        const value = Number(ev.target.value.trim().replace(",", "."));
        const min = c.min_temp ?? 5;
        const step = c.temp_step ?? 0.5;
        const inside = ev.target.value.trim() && value >= min && value <= (c.max_temp ?? 35);
        // on the step of the device, counted from its minimum (Z5)
        const onStep = Math.abs((value - min) / step - Math.round((value - min) / step)) < 1e-6;
        if (inside && onStep) return send({ temperature: value });
        this._drafts.delete(key);
        this._setEdit(inside ? { error: "invalid_temperature_step", errorDetail: `${this._num(step)} ${this._unit}` }
          : { error: "invalid_temperature", errorDetail: this._tempRange(c) });
      };
      return html`${this._seg("hvac_mode", eid, (c.hvac_modes ?? []).map((m) => [m, this._state(eid, m)]), v.hvac_mode,
          (m) => send({ hvac_mode: m }), !!entry)}
        <label class="field">${this._t("temperature")} (${this._unit})<input inputmode="decimal" maxlength="5"
          data-field="temperature" data-entity=${eid} data-key=${key}
          .value=${live(String(this._draft(key, v.temperature != null ? this._num(v.temperature) : "")))} @input=${this._keep(key)} @change=${typed} /></label>`;
    }
    if (dev.domain === "fan") {
      return html`${power(() => set({ percentage: v.percentage }))}
        ${slider("percentage", "percentage", 0, 100, v.percentage, "%", (p) => set({ percentage: p }))}`;
    }
    if (dev.domain === "switch") return power(() => set({ on: true }));
    if (dev.domain === "media_player") {
      const mode = entry ? entry.music : ["playing", "on"].includes(source.state) ? "on" : "off";
      const volume = entry?.volume ?? this.hass.states[eid]?.attributes.volume_level ?? 0.3;
      const favs = this._edit.favorites;
      const favorite = entry?.favorite_id ?? favs[0]?.id;
      // "Favorit" only with favorites to choose from (X6); a stored favorite stays visible
      const offer = dev.music_system && (favs.length > 0 || mode === "favorite");
      const modes = [["off", this._t("off")], ["on", this._t("on")], ...(offer ? [["favorite", this._t("favorite")]] : [])];
      const send = (m, patch = {}) => music(m, m === "off" ? {} : { volume, ...(m === "favorite" ? { favorite_id: favorite } : {}), ...patch });
      const missing = entry?.issue === "favorite_missing";
      return html`${this._seg("music", eid, modes, mode, (m) => send(m), !!entry)}
        ${dev.music_system && !offer ? html`<p class="muted">${this._t("no_favorites")}</p>` : nothing}
        ${mode === "favorite" // one list, not a button per favorite (spec 5.2)
          ? this._favoriteList(eid, favs, missing ? null : favorite, (id) => send("favorite", { favorite_id: id }))
          : nothing}
        ${mode !== "off"
          ? slider("volume", "volume", 0, 100, Math.round(volume * 100), "%", (p) => send(mode, { volume: p / 100 }))
          : nothing}`;
    }
    return nothing;
  }

  // a list of the card, not the select of the browser (spec 5.7, Y5); it shows the stored favorite, so a refused choice reverts
  _favoriteList(eid, favs, current, pick) {
    const open = this._edit.favOpen === eid;
    const name = favs.find((f) => f.id === current)?.name ?? this._t("favorite_missing");
    const close = (focus) => {
      this._setEdit({ favOpen: null });
      if (focus) this.updateComplete.then(() => this.renderRoot.querySelector(`[data-action="favorite-open"][data-entity="${eid}"]`)?.focus());
    };
    const toggle = () => {
      if (open) return close(false);
      this._setEdit({ favOpen: eid });
      this.updateComplete.then(() => {
        const list = this.renderRoot.querySelector(`[role="listbox"][data-entity="${eid}"]`);
        (list?.querySelector('[aria-selected="true"]') ?? list?.querySelector("button"))?.focus();
      });
    };
    const key = (ev) => {
      const items = [...ev.currentTarget.querySelectorAll("button")];
      const at = items.indexOf(this.renderRoot.activeElement);
      const to = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: items.length - 1 }[ev.key];
      if (ev.key === "Escape") {
        ev.stopPropagation();
        close(true);
      } else if (to != null) {
        ev.preventDefault();
        items[Math.max(0, Math.min(items.length - 1, to))]?.focus();
      }
    };
    return html`<div class="favorites" data-field="favorite_id" data-entity=${eid} data-value=${current ?? ""}>
      <button class="choice" data-action="favorite-open" data-entity=${eid} aria-haspopup="listbox"
        aria-expanded=${open ? "true" : "false"} aria-label=${`${this._t("favorite")}: ${name}`} @click=${toggle}>${name} ▾</button>
      ${open
        ? html`<div role="listbox" data-entity=${eid} aria-label=${this._t("favorite")} @keydown=${key}>
            ${favs.map((f) => html`<button role="option" aria-selected=${f.id === current ? "true" : "false"} data-value=${f.id}
              @click=${() => (close(true), f.id !== current && pick(f.id))}>${f.name}</button>`)}</div>`
        : nothing}</div>`;
  }

  // ---------- image (spec 4.8, 5.6) ----------

  _renderImagePicker() {
    const e = this._edit;
    const s = this._detail;
    const crop = e.crop;
    if (!e.picking && !crop) return nothing;
    return html`<div class="field">
      ${e.picking
        ? html`<div class="tiles">
            <button class="tile" data-action="pick-image" data-name="" @click=${() => this._pickImage(null)}>
              <span>${this._t("no_image")}</span></button>
            ${e.images.map((i) => html`<button class="tile" data-action="pick-image" data-name=${i.name}
              aria-pressed=${i.name === s.image ? "true" : "false"} @click=${() => this._pickImage(i.name)}>
              <img src=${i.url} alt="" /><span>${i.name}</span></button>`)}
            <button class="tile" data-action="upload" @click=${() => this.renderRoot.querySelector('[data-field="upload"]').click()}>
              <span>${this._t("own_image")}</span></button>
          </div>
          <input type="file" accept="image/*" hidden data-field="upload" @change=${(ev) => this._openCrop(ev.target.files?.[0])} />`
        : nothing}
      ${crop
        ? html`<div class="crop">
            <canvas width=${TILE.w / 2} height=${TILE.h / 2}></canvas>
            <label class="slider"><span>${this._t("crop_x")}</span><input type="range" min="0" max="100" .value=${String(crop.x)}
              @input=${(ev) => this._moveCrop({ x: Number(ev.target.value) })} /></label>
            <label class="slider"><span>${this._t("crop_y")}</span><input type="range" min="0" max="100" .value=${String(crop.y)}
              @input=${(ev) => this._moveCrop({ y: Number(ev.target.value) })} /></label>
            <button class="primary" data-action="use-image" @click=${this._upload}>${this._t("use_image")}</button>
          </div>`
        : nothing}</div>`;
  }

  _pickImage(name) {
    this._setEdit({ picking: false });
    this._send("update", { image: name });
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
    this._setEdit({ crop: { img, x: 50, y: 50 }, picking: false, error: null });
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
      this._setEdit({ crop: null });
      await this._send("update", { image: body.image });
    } catch (err) {
      // the old image stays (spec 5.6)
      const detail = /: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
      this._setEdit({ crop: null, error: err.code ?? "invalid_image_file", errorDetail: detail });
    }
  }

  // ---------- delete (V13: a dialog over the card) ----------

  _renderConfirmDelete() {
    const used = this._detail.used_in ?? { scenes: [], slots: [] };
    const slots = used.slots.map((s) => {
      const [scope, n] = s.split(":");
      return `${this._areaName(scope === HOUSE ? null : scope)} ${this._t("slot")} ${n}`;
    });
    const all = [...used.scenes, ...slots];
    const question = this._t("confirm_delete").replace("{name}", this._detail.name);
    return html`<div class="overlay" @keydown=${this._dialogKey}><div class="dialog" role="alertdialog" aria-modal="true" aria-label=${question}>${question}
      ${all.length ? html`<br />${this._t("used_on")} ${all.join(", ")}` : nothing}
      <br /><span class="muted">${this._t("outside_note")}</span>
      <div class="actions">
        <button class="danger" data-action="delete" @click=${this._delete}>${this._t("yes")}</button>
        <button data-action="keep-scene" data-safe @click=${() => this._setEdit({ confirmDelete: false })}>${this._t("no")}</button>
      </div></div></div>`;
  }

  async _delete() {
    try {
      await this.hass.callWS({ type: `${WS}/delete`, scene_id: this._edit.scene_id });
      this._edit = null;
      this._selected = null;
      this._detail = null;
    } catch (err) {
      this._setEdit({ confirmDelete: false, error: err.code ?? "default", errorDetail: "" });
    }
  }

  static styles = css`
    :host { display: block; }
    .card { position: relative; background: var(--ha-card-background, var(--card-background-color, #fff)); color: var(--primary-text-color);
      border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none);
      border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color)); padding: 16px; }
    h2 { margin: 8px 0; font-size: 1.4em; } h3 { margin: 16px 0 4px; font-size: 1em; color: var(--secondary-text-color); }
    button, input[type=number], input:not([type]) { min-height: 44px; font: inherit; color: inherit; border-radius: 8px;
      border: 1px solid var(--divider-color); background: transparent; padding: 0 12px; box-sizing: border-box; max-width: 100%; }
    button { cursor: pointer; min-width: 44px; }
    button:focus-visible, input:focus-visible, .handle:focus-visible { outline: 2px solid var(--primary-color); }
    button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    button.danger { color: var(--error-color); border-color: var(--error-color); }
    button.link { border: none; text-align: left; padding: 0; } button.wide { width: 100%; margin-bottom: 8px; }
    button[aria-pressed=true] { border-color: var(--primary-color); color: var(--primary-color); }
    input[type=number] { width: 7em; }
    input[type=range] { width: 100%; min-height: 44px; margin: 0; accent-color: var(--primary-color); }
    .row { display: flex; align-items: center; gap: 8px; min-height: 48px; border-bottom: 1px solid var(--divider-color); flex-wrap: wrap; }
    .row.selected { background: var(--secondary-background-color); border-left: 4px solid var(--primary-color); padding-left: 4px; }
    .row.selected .name { color: var(--primary-color); font-weight: 500; }
    .row .name { flex: 1; min-width: 0; overflow-wrap: anywhere; }
    .name .line { display: flex; gap: 4px; align-items: center; min-width: 0; overflow: hidden; white-space: nowrap; }
    .line .clip { min-width: 0; overflow: hidden; text-overflow: ellipsis; } .line .more, .line .badge { flex: none; }
    .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); margin: 0; }
    .hero { width: 80px; height: 80px; aspect-ratio: 1; object-fit: cover; border-radius: 8px; flex: none; box-sizing: border-box;
      background: var(--secondary-background-color); display: inline-flex; align-items: center; justify-content: center;
      color: var(--secondary-text-color); }
    .hero svg { width: 40px; height: 40px; }
    .head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
    .head .title { display: contents; }
    .head h2 { flex: 1 1 0; min-width: 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .head .tools { display: flex; flex-wrap: wrap; gap: 8px; flex: 1 1 100%; }
    .col-detail { container-type: inline-size; }
    /* narrow: the buttons take a full-width row under image and name, 80 + 8 + 44 (+ 8 + 44) px (review AA1) */
    @container (width >= 600px) {
      .head { flex-wrap: nowrap; max-height: 120px; }
      .head .title { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 0 8px; }
      .head h2 { flex: 1 1 12em; } .head .tools { flex: initial; }
    }
    .columns { display: grid; grid-template-columns: minmax(220px, 1fr) 2fr; gap: 24px; }
    .bar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .bar .name { flex: 1; min-width: 0; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .field { display: flex; flex-direction: column; gap: 4px; margin: 8px 0; }
    .actions, .pick, .tools, .delay, .controls, .seg { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .delay-row { flex-wrap: nowrap; } .delay-row .delay { flex: 1; min-width: 0; flex-wrap: nowrap; gap: 4px; }
    .delay-row .plain { gap: 2px; } .delay-row .plain input.secs { width: 3.5em; padding: 0 4px; }
    .hint { margin: 4px 0 8px 52px; }
    .favorites { flex: 1 1 100%; } .favorites [role=listbox] { display: flex; flex-direction: column; gap: 4px; margin-top: 4px;
      max-height: 50vh; overflow: auto; }
    .favorites [role=option] { text-align: left; }
    .favorites [role=option][aria-selected=true] { background: var(--primary-color); color: var(--text-primary-color, #fff);
      border-color: var(--primary-color); }
    .actions { margin-top: 16px; } .pick { margin: 8px 0; }
    .controls { flex: 1 1 100%; padding-bottom: 8px; }
    .seg button[aria-checked=true] { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .slider { flex: 1 1 100%; display: grid; grid-template-columns: 1fr auto; align-items: center; }
    .slider input { grid-column: 1 / -1; }
    .plain { display: flex; align-items: center; gap: 4px; } .plain input { width: 5em; text-align: center; }
    button.switch { display: inline-flex; align-items: center; gap: 12px; border: none; padding: 0 4px; text-align: left; }
    .switch .track { position: relative; width: 40px; height: 22px; border-radius: 11px; flex: none;
      background: var(--disabled-color, #bdbdbd); transition: background .2s; }
    .switch .track::after { content: ""; position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%;
      background: #fff; transition: transform .2s; }
    .switch[aria-checked=true] .track { background: var(--primary-color); }
    .switch[aria-checked=true] .track::after { transform: translateX(18px); }
    button.check { width: 44px; padding: 0; position: relative; flex: none; }
    button.check::after { content: ""; position: absolute; inset: 11px; border: 2px solid var(--secondary-text-color); border-radius: 4px; }
    button.check[aria-checked=true]::after { background: var(--primary-color); border-color: var(--primary-color); }
    button.check[aria-checked=true]::before { content: "✓"; position: relative; z-index: 1; color: var(--text-primary-color, #fff); }
    button:disabled { opacity: .5; cursor: default; }
    .badge { font-size: .75em; padding: 2px 6px; border-radius: 4px; background: var(--secondary-background-color); margin-left: 4px; }
    .badge.warn { background: var(--warning-color, #f4b400); color: #000; }
    .muted { color: var(--secondary-text-color); } .error { color: var(--error-color); }
    .banner { padding: 12px; border-radius: 8px; background: var(--secondary-background-color); margin: 8px 0; }
    .banner button { margin: 8px 8px 0 0; }
    .overlay { position: absolute; inset: 0; z-index: 2; display: flex; align-items: flex-start; justify-content: center;
      background: rgba(0, 0, 0, .4); border-radius: inherit; padding: 16px; box-sizing: border-box; }
    .dialog { background: var(--ha-card-background, var(--card-background-color, #fff)); border-radius: 12px; padding: 16px;
      width: 100%; max-width: 400px; box-sizing: border-box; position: sticky; top: 16px; }
    .image-btn { position: relative; padding: 0; border: none; flex: none; display: flex; }
    .image-btn .pencil { position: absolute; right: 4px; bottom: 4px; width: 28px; height: 28px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center; background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .crop canvas { width: 100%; max-width: 320px; aspect-ratio: 1; border-radius: 8px; background: var(--secondary-background-color); }
    .handle { cursor: grab; touch-action: none; user-select: none; min-width: 44px; min-height: 44px; display: flex;
      align-items: center; justify-content: center; font-size: 1.4em; color: var(--secondary-text-color); border-radius: 8px; }
    .row.drop { outline: 2px dashed var(--primary-color); }
    .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
    .tile { position: relative; aspect-ratio: 1; padding: 0; overflow: hidden; display: flex; align-items: flex-end; justify-content: center; }
    .tile img, .tile svg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
    .tile svg { padding: 25%; box-sizing: border-box; color: var(--secondary-text-color); }
    .tile span { position: relative; width: 100%; padding: 24px 8px 8px; color: #fff; text-align: left; box-sizing: border-box;
      background: linear-gradient(transparent, rgba(0, 0, 0, .7)); text-shadow: 0 1px 2px rgba(0, 0, 0, .8); }
  `;
}

customElements.define("resident-scenes-card", ResidentScenesCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "resident-scenes-card", name: "Resident Scenes", description: "Create, edit and run resident scenes" });
