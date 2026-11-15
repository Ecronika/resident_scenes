// Resident Scenes card. No build step, no Home Assistant internal elements: only the
// documented card API and theme variables, so frontend updates cannot break it.
const VERSION = "0.1.1"; // must match the integration (checked by tests)
const WS = "resident_scenes";
const HOUSE = "_house";
const DOMAINS = ["light", "cover", "climate", "switch", "fan", "media_player", "scene"];

const I18N = {
  en: {
    new_scene: "New scene", scenes: "Scenes", other_scenes: "Other scenes", favorites: "Favorites",
    play: "Play", edit: "Edit", save: "Save", cancel: "Cancel", delete: "Delete", duplicate: "Duplicate",
    back: "Back", name: "Name", image: "Image", no_image: "No image", all: "All", none: "–",
    slot: "Slot", keep: "Stored value", capture: "Current state", off: "Off", closed: "Closed",
    on: "On", favorite: "Favorite", volume: "Volume", call: "Run", missing: "Device missing",
    unavailable: "Not reachable", not_released: "Not released", all_off: "All off",
    all_house: "All in the house", rights_gone: "Your right to change scenes was withdrawn.", empty: "No scenes yet.", no_devices: "No released devices.",
    confirm_delete: "Delete this scene for good?", used_on: "On favorite slots:",
    outside_note: "Automations and schedules using it will stop working.", yes: "Delete", no: "Keep",
    conflict: "Someone else changed this scene meanwhile.", load_new: "Load new version",
    save_copy: "Save mine as copy", copy: "copy", reload: "A new version is installed. Please reload.",
    reload_btn: "Reload", house: "House",
    light: "Lights", cover: "Shading", climate: "Climate", switch: "Switches", fan: "Fans",
    media_player: "Music", scene: "Scenes",
    err: {
      unauthorized: "You may not change scenes.", name_exists: "This name is taken.",
      invalid_name: "Name is empty or too long.", limit_reached: "Limit of scenes reached.",
      too_many_steps: "Too many devices.", entity_not_allowed: "Not released for this scene:",
      entity_unavailable: "Not reachable, its state cannot be captured:",
      unknown_favorite: "This favorite no longer exists.", not_found: "The scene no longer exists.",
      invalid_step: "Invalid setting.", default: "Saving failed.",
    },
  },
  de: {
    new_scene: "Neue Szene", scenes: "Szenen", other_scenes: "Weitere Szenen", favorites: "Favoriten",
    play: "Abspielen", edit: "Ändern", save: "Speichern", cancel: "Abbrechen", delete: "Löschen",
    duplicate: "Duplizieren", back: "Zurück", name: "Name", image: "Bild", no_image: "Kein Bild",
    all: "Alle", none: "–", slot: "Platz", keep: "Gespeicherter Wert", capture: "Aktueller Zustand",
    off: "Aus", closed: "Zu", on: "An", favorite: "Favorit", volume: "Lautstärke", call: "Aufruf",
    missing: "Gerät fehlt", unavailable: "Nicht erreichbar", not_released: "Nicht freigegeben",
    all_off: "Alle aus", all_house: "Alle im Haus", rights_gone: "Ihr Recht, Szenen zu ändern, wurde entzogen.", empty: "Noch keine Szenen.",
    no_devices: "Keine freigegebenen Geräte.", confirm_delete: "Diese Szene endgültig löschen?",
    used_on: "Auf Favoritenplätzen:", outside_note: "Automationen und Zeitpläne damit wirken nicht mehr.",
    yes: "Löschen", no: "Behalten", conflict: "Jemand anderes hat die Szene inzwischen geändert.",
    load_new: "Neuen Stand laden", save_copy: "Meine Fassung als Kopie sichern", copy: "Kopie",
    reload: "Eine neue Version ist installiert. Bitte neu laden.", reload_btn: "Neu laden", house: "Haus",
    light: "Licht", cover: "Beschattung", climate: "Klima", switch: "Schalter", fan: "Lüfter",
    media_player: "Musik", scene: "Szenen",
    err: {
      unauthorized: "Sie dürfen Szenen nicht ändern.", name_exists: "Dieser Name ist schon vergeben.",
      invalid_name: "Name fehlt oder ist zu lang.", limit_reached: "Höchstzahl an Szenen erreicht.",
      too_many_steps: "Zu viele Geräte.", entity_not_allowed: "Für diese Szene nicht freigegeben:",
      entity_unavailable: "Nicht erreichbar, der Zustand lässt sich nicht übernehmen:",
      unknown_favorite: "Diesen Favoriten gibt es nicht mehr.", not_found: "Die Szene gibt es nicht mehr.",
      invalid_step: "Ungültige Einstellung.", default: "Speichern fehlgeschlagen.",
    },
  },
};

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class ResidentScenesCard extends HTMLElement {
  setConfig(config) {
    const cfg = { scope: "area", view: "manage", ...config };
    if (!["area", "house"].includes(cfg.scope)) throw new Error("scope must be area or house");
    if (cfg.scope === "area" && !cfg.area) throw new Error("area is required for scope: area");
    if (!["manage", "list", "favorites"].includes(cfg.view)) throw new Error("view must be manage, list or favorites");
    this._config = cfg;
    this._render();
  }

  static getStubConfig() {
    return { scope: "house", view: "manage" };
  }

  getCardSize() {
    return this._config?.view === "favorites" ? 2 : 4;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._started && this.isConnected) this._start();
  }

  connectedCallback() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
      this.shadowRoot.addEventListener("change", (e) => this._onChange(e));
      this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
    }
    this._ro = new ResizeObserver(([entry]) => {
      const narrow = entry.contentRect.width < 600;
      if (narrow !== this._narrow) {
        this._narrow = narrow;
        this._render();
      }
    });
    this._ro.observe(this);
    if (this._hass && !this._started) this._start();
  }

  disconnectedCallback() {
    this._started = false;
    clearInterval(this._timer);
    document.removeEventListener("visibilitychange", this._onVisible);
    this._hass?.connection.removeEventListener?.("ready", this._onReady);
    this._ro?.disconnect();
    this._unsub?.then((unsub) => unsub()).catch(() => {});
    this._unsub = undefined;
  }

  async _start() {
    this._started = true;
    this._unsub = this._hass.connection.subscribeMessage(() => this._load(true), { type: `${WS}/subscribe` });
    // signed image URLs die after a restart and after a day; wall panels run for weeks (spec 4.3, 5.7)
    this._onReady ??= () => this._load();
    this._onVisible ??= () => document.visibilityState === "visible" && this._load();
    this._hass.connection.addEventListener?.("ready", this._onReady);
    document.addEventListener("visibilitychange", this._onVisible);
    this._timer = setInterval(() => this._load(), 6 * 3600 * 1000);
    await this._load();
  }

  _t(key) {
    const lang = this._hass?.locale?.language?.startsWith("de") ? "de" : "en";
    return key.split(".").reduce((o, k) => o?.[k], I18N[lang]) ?? key;
  }

  async _load(fromServer = false) {
    try {
      this._data = await this._hass.callWS({ type: `${WS}/list` });
      this._loadError = null;
    } catch (err) {
      this._loadError = err.message ?? String(err);
    }
    // rights withdrawn while editing: drop the form, server would reject it anyway
    if (this._edit && this._data && !this._data.can_edit) (this._edit = null), (this._notice = "rights_gone");
    // someone else saved while this user edits: keep the form as it is, conflicts show on save
    if (fromServer && this._edit) return;
    this._render();
  }

  get _scope() {
    return this._config.scope === "house" ? HOUSE : this._config.area;
  }

  get _scenes() {
    return (this._data?.scenes ?? [])
      .filter((s) => (s.area_id ?? HOUSE) === this._scope)
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  get _foreign() {
    return (this._data?.foreign_scenes ?? []).filter((s) => this._config.scope === "house" || s.area_id === this._scope);
  }

  _scene(id) {
    return this._data?.scenes.find((s) => s.id === id);
  }

  _entityName(eid) {
    return this._hass.states[eid]?.attributes.friendly_name ?? eid;
  }

  _entityArea(eid) {
    const ent = this._hass.entities?.[eid];
    return ent?.area_id ?? this._hass.devices?.[ent?.device_id]?.area_id ?? null;
  }

  _areaName(areaId) {
    return areaId ? this._hass.areas?.[areaId]?.name ?? areaId : this._t("house");
  }

  _play(entityId) {
    if (entityId) this._hass.callService("scene", "turn_on", { entity_id: entityId });
  }

  // ---------- rendering ----------

  _render() {
    if (!this.shadowRoot || !this._config) return;
    let body;
    if (this._loadError) body = `<p class="error">${esc(this._loadError)}</p>`;
    else if (!this._data) body = "";
    else if (this._config.view === "favorites") {
      body = this._renderFavorites();
      // empty slots stay invisible (spec 4.7), so does a card without any
      if (!body && this._data.version === VERSION) {
        this.shadowRoot.innerHTML = "";
        return;
      }
    }
    else body = this._renderManage();
    const banner =
      this._data && this._data.version !== VERSION
        ? `<div class="banner">${esc(this._t("reload"))} <button data-action="reload">${esc(this._t("reload_btn"))}</button></div>`
        : "";
    const notice = this._notice ? `<p class="error" role="alert">${esc(this._t(this._notice))}</p>` : "";
    const keyOf = (n) => ["field", "action", "entity", "group", "domain", "id"].map((k) => n.dataset?.[k] ?? "").join("|");
    const focus = this.shadowRoot.activeElement;
    const key = focus && keyOf(focus);
    const scroll = this.shadowRoot.querySelector(".editor")?.scrollTop;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><div class="card">${banner}${notice}${body}</div>`;
    // the card is redrawn as a whole; give focus back so keyboards and screen readers keep their place
    if (key) [...this.shadowRoot.querySelectorAll("[data-field],[data-action]")].find((n) => keyOf(n) === key)?.focus();
    if (scroll) this.shadowRoot.querySelector(".editor").scrollTop = scroll;
  }

  _renderFavorites() {
    const slots = this._data.favorites[this._scope] ?? [];
    const tiles = slots
      .map((id) => this._scene(id))
      .filter(Boolean)
      .map(
        (s) => `<button class="tile" data-action="play" data-entity="${esc(s.entity_id)}" aria-label="${esc(s.name)}">
          ${s.image_url ? `<img src="${esc(s.image_url)}" alt="">` : ""}<span>${esc(s.name)}</span></button>`
      )
      .join("");
    return tiles && `<div class="tiles">${tiles}</div>`;
  }

  _renderManage() {
    const showDetail = this._config.view === "manage" && (this._selected || this._edit);
    const list = this._renderList();
    if (!showDetail) return list;
    const detail = this._edit ? this._renderEditor() : this._renderDetail();
    if (this._narrow) return detail;
    return `<div class="columns"><div class="col-list">${list}</div><div class="col-detail">${detail}</div></div>`;
  }

  _renderList() {
    const manage = this._config.view === "manage";
    const canEdit = manage && this._data.can_edit;
    const rows = this._scenes
      .map(
        (s) => `<div class="row ${this._selected === s.id ? "selected" : ""}">
          ${s.image_url ? `<img class="thumb" src="${esc(s.image_url)}" alt="">` : `<span class="thumb"></span>`}
          ${manage ? `<button class="name link" data-action="select" data-id="${esc(s.id)}">${esc(s.name)}</button>` : `<span class="name">${esc(s.name)}</span>`}
          <button data-action="play" data-entity="${esc(s.entity_id)}" aria-label="${esc(this._t("play"))}">▶</button></div>`
      )
      .join("");
    const foreign = this._foreign
      .map(
        (s) => `<div class="row"><span class="thumb"></span><span class="name">${esc(this._entityName(s.entity_id))}
          ${s.knx ? '<span class="badge">KNX</span>' : ""}</span>
          <button data-action="play" data-entity="${esc(s.entity_id)}" aria-label="${esc(this._t("play"))}">▶</button></div>`
      )
      .join("");
    const full = this._scenes.length >= (this._data.limits?.[this._config.scope] ?? Infinity);
    return `${canEdit ? `<button class="primary wide" data-action="new" ${full ? "disabled" : ""}>+ ${esc(this._t("new_scene"))}</button>
      ${full ? `<p class="muted">${esc(this._t("err.limit_reached"))}</p>` : ""}` : ""}
      <h3>${esc(this._t("scenes"))}</h3>${rows || `<p class="muted">${esc(this._t("empty"))}</p>`}
      ${foreign ? `<h3>${esc(this._t("other_scenes"))}</h3>${foreign}` : ""}`;
  }

  _renderDetail() {
    const s = this._scene(this._selected);
    if (!s) return "";
    const slots = this._data.favorites[this._scope] ?? [];
    const slot = slots.indexOf(s.id);
    const heart = this._data.can_edit
      ? `<label class="heart">♥ <select data-field="favorite" aria-label="${esc(this._t("favorites"))}">
          <option value="">${esc(this._t("none"))}</option>
          ${slots.map((_, i) => `<option value="${i}" ${i === slot ? "selected" : ""}>${esc(this._t("slot"))} ${i + 1}</option>`).join("")}
        </select></label>`
      : "";
    return `${this._narrow ? `<button data-action="back">‹ ${esc(this._t("back"))}</button>` : ""}
      <div class="head">${s.image_url ? `<img class="hero" src="${esc(s.image_url)}" alt="">` : ""}
        <h2>${esc(s.name)}</h2>
        <button class="primary" data-action="play" data-entity="${esc(s.entity_id)}">▶ ${esc(this._t("play"))}</button>
        ${heart}
        ${this._data.can_edit ? `<button data-action="edit">${esc(this._t("edit"))}</button>` : ""}</div>
      ${this._renderSteps(s.steps)}`;
  }

  _renderSteps(steps) {
    const groups = new Map();
    for (const step of steps) {
      const key = this._config.scope === "house" ? this._areaName(this._entityArea(step.entity_id)) : this._t(step.entity_id.split(".")[0]);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(step);
    }
    return [...groups]
      .map(
        ([title, items]) => `<h3>${esc(title)}</h3>${items
          .map((step) => {
            const st = this._hass.states[step.entity_id];
            const mark = !st ? this._t("missing") : st.state === "unavailable" ? this._t("unavailable") : "";
            return `<div class="row"><span class="name">${esc(this._entityName(step.entity_id))}
              ${mark ? `<span class="badge warn">${esc(mark)}</span>` : ""}</span>
              <span class="muted">${esc(this._summary(step))}</span></div>`;
          })
          .join("")}`
      )
      .join("");
  }

  _summary(step) {
    const pct = (v) => `${Math.round(v * 100)} %`;
    if (step.call) return this._t("call");
    if (step.music === "off") return this._t("off");
    if (step.music === "on") return `${this._t("on")} · ${pct(step.volume)}`;
    if (step.music === "favorite") return `${step.favorite_name} · ${pct(step.volume)}`;
    const a = step.attributes ?? {};
    if (step.state === "off") return this._t("off");
    if (step.state === "closed") return this._t("closed");
    if (a.brightness != null) return `${this._t("on")} · ${Math.round(a.brightness / 2.55)} %`;
    if (a.current_position != null) return `${a.current_position} %`;
    if (a.temperature != null) return `${step.state} · ${a.temperature} °`;
    if (a.percentage != null) return `${this._t("on")} · ${a.percentage} %`;
    return step.state === "on" ? this._t("on") : step.state;
  }

  _renderEditor() {
    const e = this._edit;
    const images = this._data.images
      .map((i) => `<option value="${esc(i.name)}" ${i.name === e.image ? "selected" : ""}>${esc(i.name)}</option>`)
      .join("");
    const preview = this._data.images.find((i) => i.name === e.image);
    const groups = new Map();
    for (const dev of e.devices) {
      const key = this._config.scope === "house" ? dev.area_id ?? "" : dev.domain;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(dev);
    }
    const order = [...groups.keys()].sort((a, b) =>
      this._config.scope === "house" ? this._areaName(a).localeCompare(this._areaName(b)) : DOMAINS.indexOf(a) - DOMAINS.indexOf(b)
    );
    const devices = order
      .map((key) => {
        const devs = groups.get(key);
        const title = this._config.scope === "house" ? this._areaName(key || null) : this._t(key);
        const all = devs.every((d) => e.steps.has(d.entity_id));
        return `<h3><label><input type="checkbox" data-field="all" data-group="${esc(key)}" ${all ? "checked" : ""}>
          ${esc(title)} · ${esc(this._t("all"))}</label>
          <button class="small" data-action="group-off" data-group="${esc(key)}">${esc(this._t("all_off"))}</button></h3>
          ${devs.map((d) => this._renderDevice(d)).join("")}`;
      })
      .join("");
    // house scenes: one input per trade for "everything off" (spec 4.5, 5.3)
    const trades =
      this._config.scope === "house"
        ? DOMAINS.filter((d) => d !== "scene" && e.devices.some((dev) => dev.domain === d && dev.released !== false))
            .map((d) => `<button class="small" data-action="trade-off" data-domain="${d}">${esc(this._t(d))} · ${esc(this._t("all_off"))}</button>`)
            .join("")
        : "";
    const known = this._t(`err.${e.error}`) !== `err.${e.error}`;
    const device = e.errorEntity ? ` ${this._entityName(e.errorEntity)}` : "";
    const status = e.error
      ? `<p class="error" role="alert">${esc(known ? this._t(`err.${e.error}`) + device : this._t("err.default"))}</p>`
      : "";
    const conflict = e.conflict
      ? `<div class="banner">${esc(this._t("conflict"))}
          <button data-action="load-new">${esc(this._t("load_new"))}</button>
          <button data-action="save-copy">${esc(this._t("save_copy"))}</button></div>`
      : "";
    const confirm = e.confirmDelete ? this._renderConfirmDelete() : "";
    return `<div class="editor">
      <label>${esc(this._t("name"))}<input data-field="name" maxlength="${this._data.name_length}" value="${esc(e.name)}"></label>
      <label>${esc(this._t("image"))}<select data-field="image"><option value="">${esc(this._t("no_image"))}</option>${images}</select></label>
      ${preview ? `<img class="hero" src="${esc(preview.url)}" alt="">` : ""}
      ${trades ? `<h3>${esc(this._t("all_house"))}</h3><div class="actions">${trades}</div>` : ""}
      ${devices || `<p class="muted">${esc(this._t("no_devices"))}</p>`}
      ${status}${conflict}${confirm}
      <div class="actions">
        <button class="primary" data-action="save" ${e.busy ? "disabled" : ""}>${esc(this._t("save"))}</button>
        <button data-action="cancel">${esc(this._t("cancel"))}</button>
        ${e.scene_id ? `<button data-action="duplicate">${esc(this._t("duplicate"))}</button>` : ""}
        ${e.scene_id && this._scene(e.scene_id)?.kind === "resident" ? `<button class="danger" data-action="ask-delete">${esc(this._t("delete"))}</button>` : ""}
      </div></div>`;
  }

  _renderDevice(dev) {
    const step = this._edit.steps.get(dev.entity_id);
    const id = esc(dev.entity_id);
    let controls = "";
    if (step && dev.domain !== "scene") {
      const choices = dev.released === false ? [] : ["capture", "off"];
      if (step.stored) choices.unshift("keep");
      if (dev.domain === "media_player" && dev.released !== false) choices.push("on", "favorite");
      const label = (c) => this._t(c === "off" && dev.domain === "cover" ? "closed" : c);
      controls = `<select data-field="choice" data-entity="${id}" aria-label="${esc(dev.name)}">
        ${choices.map((c) => `<option value="${c}" ${c === step.choice ? "selected" : ""}>${esc(label(c))}</option>`).join("")}</select>`;
      if (step.choice === "favorite") {
        controls += `<select data-field="favorite_id" data-entity="${id}" aria-label="${esc(this._t("favorite"))}">
          ${this._edit.favorites.map((f) => `<option value="${esc(f.id)}" ${f.id === step.favorite_id ? "selected" : ""}>${esc(f.name)}</option>`).join("")}</select>`;
      }
      if (step.choice === "on" || step.choice === "favorite") {
        controls += `<input type="range" min="0" max="100" data-field="volume" data-entity="${id}"
          value="${Math.round((step.volume ?? 0.3) * 100)}" aria-label="${esc(this._t("volume"))}">`;
      }
    }
    const st = this._hass.states[dev.entity_id];
    const why = dev.released === false ? "not_released" : !st ? "missing" : !dev.available ? "unavailable" : "";
    const mark = why ? `<span class="badge warn">${esc(this._t(why))}</span>` : "";
    return `<div class="row device"><label class="name"><input type="checkbox" data-field="pick" data-entity="${id}" ${step ? "checked" : ""}>
      ${esc(dev.name)} ${mark}</label>${controls}</div>`;
  }

  _renderConfirmDelete() {
    const id = this._edit.scene_id;
    const used = Object.entries(this._data.favorites)
      .flatMap(([scope, slots]) => slots.map((s, i) => (s === id ? `${this._areaName(scope === HOUSE ? null : scope)} ${i + 1}` : null)))
      .filter(Boolean);
    return `<div class="banner" role="alertdialog">${esc(this._t("confirm_delete"))}
      ${used.length ? `<br>${esc(this._t("used_on"))} ${esc(used.join(", "))}` : ""}
      <br><span class="muted">${esc(this._t("outside_note"))}</span><br>
      <button class="danger" data-action="delete">${esc(this._t("yes"))}</button>
      <button data-action="keep-scene">${esc(this._t("no"))}</button></div>`;
  }

  // ---------- events ----------

  async _onClick(ev) {
    const el = ev.target.closest("[data-action]");
    if (!el) return;
    const action = el.dataset.action;
    const e = this._edit;
    if (action === "play") this._play(el.dataset.entity);
    else if (action === "reload") location.reload();
    else if (action === "select") (this._selected = el.dataset.id), this._render();
    else if (action === "back") (this._selected = null), this._render();
    else if (action === "new") (this._notice = null), await this._openEditor(null);
    else if (action === "edit") await this._openEditor(this._scene(this._selected));
    else if (action === "cancel") (this._edit = null), this._render();
    else if (action === "save") await this._save({});
    else if (action === "duplicate") await this._save({ copy: true });
    else if (action === "save-copy") await this._save({ copy: true });
    else if (action === "load-new") await this._openEditor(this._scene(e.scene_id));
    else if (action === "ask-delete") (e.confirmDelete = true), this._render();
    else if (action === "keep-scene") (e.confirmDelete = false), this._render();
    else if (action === "delete") await this._delete();
    else if (action === "group-off") this._allOff((d) => (this._config.scope === "house" ? d.area_id ?? "" : d.domain) === el.dataset.group);
    else if (action === "trade-off") this._allOff((d) => d.domain === el.dataset.domain);
  }

  _onInput(ev) {
    const el = ev.target;
    if (!this._edit) return;
    if (el.dataset.field === "name") this._edit.name = el.value;
    else if (el.dataset.field === "volume") this._edit.steps.get(el.dataset.entity).volume = Number(el.value) / 100;
  }

  async _onChange(ev) {
    const el = ev.target;
    const field = el.dataset.field;
    if (field === "favorite") return this._setFavorite(el.value);
    const e = this._edit;
    if (!e) return;
    if (field === "image") e.image = el.value || null;
    else if (field === "pick") el.checked ? this._pick(el.dataset.entity) : e.steps.delete(el.dataset.entity);
    else if (field === "all") {
      const key = el.dataset.group;
      for (const dev of e.devices.filter((d) => (this._config.scope === "house" ? d.area_id ?? "" : d.domain) === key)) {
        el.checked ? this._pick(dev.entity_id) : e.steps.delete(dev.entity_id);
      }
    } else if (field === "choice") {
      const step = e.steps.get(el.dataset.entity);
      step.choice = el.value;
      if (step.choice === "favorite" && !step.favorite_id) step.favorite_id = e.favorites[0]?.id;
    } else if (field === "favorite_id") e.steps.get(el.dataset.entity).favorite_id = el.value;
    else return;
    this._render();
  }

  _allOff(match) {
    for (const dev of this._edit.devices.filter((d) => match(d) && d.domain !== "scene" && d.released !== false)) {
      this._edit.steps.set(dev.entity_id, { ...this._edit.steps.get(dev.entity_id), choice: "off" });
    }
    this._render();
  }

  _pick(entityId) {
    if (!this._edit.steps.has(entityId)) this._edit.steps.set(entityId, { choice: "capture" });
  }

  async _setFavorite(value) {
    const slots = this._data.favorites[this._scope] ?? [];
    const current = slots.indexOf(this._selected);
    try {
      if (value === "" && current >= 0) {
        await this._hass.callWS({ type: `${WS}/set_favorite`, scope: this._scope, slot: current, scene_id: null });
      } else if (value !== "") {
        await this._hass.callWS({ type: `${WS}/set_favorite`, scope: this._scope, slot: Number(value), scene_id: this._selected });
      }
    } catch (err) {
      await this._load(); // show the real state again
    }
  }

  async _openEditor(scene) {
    const area_id = this._config.scope === "house" ? null : this._config.area;
    let result;
    try {
      result = await this._hass.callWS({ type: `${WS}/devices`, ...(area_id ? { area_id } : {}) });
    } catch (err) {
      return;
    }
    const steps = new Map();
    const devices = result.entities;
    for (const step of scene?.steps ?? []) {
      const s = { choice: "keep", stored: true };
      if (step.music && step.music !== "off") Object.assign(s, { volume: step.volume, favorite_id: step.favorite_id });
      steps.set(step.entity_id, s);
      // a stored device that is no longer offered (moved, label removed) stays visible
      if (!devices.some((d) => d.entity_id === step.entity_id)) {
        const st = this._hass.states[step.entity_id];
        devices.push({ entity_id: step.entity_id, name: this._entityName(step.entity_id), domain: step.entity_id.split(".")[0],
          area_id: this._entityArea(step.entity_id), available: !!st && st.state !== "unavailable", released: false });
      }
    }
    devices.sort((a, b) => a.name.localeCompare(b.name));
    this._edit = {
      scene_id: scene?.id,
      version: scene?.version,
      name: scene?.name ?? "",
      image: scene?.image ?? null,
      steps,
      devices,
      favorites: result.favorites,
    };
    this._render();
  }

  _payloadSteps() {
    return [...this._edit.steps].map(([entity_id, s]) => {
      if (s.choice === "on" || s.choice === "favorite") {
        return { entity_id, mode: "music", music: s.choice, volume: s.volume ?? 0.3, ...(s.choice === "favorite" ? { favorite_id: s.favorite_id ?? "" } : {}) };
      }
      return { entity_id, mode: s.choice };
    });
  }

  async _save({ copy }) {
    const e = this._edit;
    const taken = this._scenes.some((s) => s.id !== e.scene_id && s.name.trim().toLowerCase() === e.name.trim().toLowerCase());
    if (taken && !copy) return (e.error = "name_exists"), (e.errorEntity = null), this._render();
    const msg = { type: `${WS}/save`, name: e.name, image: e.image, steps: this._payloadSteps() };
    if (this._config.scope === "area") msg.area_id = this._config.area;
    if (copy && e.scene_id) {
      const suffix = ` (${this._t("copy")})`;
      msg.name = e.name.slice(0, this._data.name_length - suffix.length) + suffix;
      msg.copy_from = e.scene_id;
    } else if (e.scene_id) {
      Object.assign(msg, { scene_id: e.scene_id, version: e.version });
    }
    e.busy = true;
    e.error = null;
    this._render();
    try {
      const res = await this._hass.callWS(msg);
      this._edit = null;
      this._selected = res.scene_id;
    } catch (err) {
      e.busy = false;
      e.conflict = err.code === "version_conflict";
      e.error = e.conflict ? null : err.code ?? "default";
      // the server sends "code: entity_id" for device errors
      e.errorEntity = /^\w+: ([a-z_]+\.\S+)$/.exec(err.message ?? "")?.[1] ?? null;
    }
    this._render();
  }

  async _delete() {
    const id = this._edit.scene_id;
    try {
      await this._hass.callWS({ type: `${WS}/delete`, scene_id: id });
      this._edit = null;
      this._selected = null;
    } catch (err) {
      this._edit.confirmDelete = false;
      this._edit.error = err.code ?? "default";
    }
    this._render();
  }
}

const STYLE = `
  :host { display: block; }
  .card { background: var(--ha-card-background, var(--card-background-color, #fff)); color: var(--primary-text-color);
    border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color)); padding: 16px; font-family: var(--paper-font-body1_-_font-family, inherit); }
  h2 { margin: 8px 0; font-size: 1.4em; } h3 { margin: 16px 0 4px; font-size: 1em; color: var(--secondary-text-color); }
  button, select, input[type=text], input:not([type]) { min-height: 44px; font: inherit; color: inherit; border-radius: 8px;
    border: 1px solid var(--divider-color); background: transparent; padding: 0 12px; }
  button { cursor: pointer; } button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--primary-color); }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
  button.danger { color: var(--error-color); border-color: var(--error-color); }
  button.link { border: none; text-align: left; padding: 0; } button.wide { width: 100%; }
  input[type=checkbox] { width: 24px; height: 24px; accent-color: var(--primary-color); vertical-align: middle; }
  input[type=range] { min-height: 44px; accent-color: var(--primary-color); }
  .row { display: flex; align-items: center; gap: 8px; min-height: 48px; border-bottom: 1px solid var(--divider-color); flex-wrap: wrap; }
  .row.selected { background: var(--secondary-background-color); } .row .name { flex: 1; min-width: 140px; }
  .thumb { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; background: var(--secondary-background-color); flex: none; }
  .hero { width: 100%; max-height: 180px; object-fit: cover; border-radius: 8px; }
  .head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; } .head h2 { flex: 1 1 100%; }
  .columns { display: grid; grid-template-columns: minmax(220px, 1fr) 2fr; gap: 24px; }
  .editor label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
  .editor h3 label, .device label { flex-direction: row; align-items: center; margin: 0; }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
  button.small { min-height: 32px; font-size: .85em; margin-left: 8px; } button:disabled { opacity: .5; cursor: default; }
  .badge { font-size: .75em; padding: 2px 6px; border-radius: 4px; background: var(--secondary-background-color); margin-left: 4px; }
  .badge.warn { background: var(--warning-color, #f4b400); color: #000; }
  .muted { color: var(--secondary-text-color); } .error { color: var(--error-color); }
  .banner { padding: 12px; border-radius: 8px; background: var(--secondary-background-color); margin: 8px 0; }
  .banner button { margin: 8px 8px 0 0; } .heart select { min-width: 90px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
  .tile { position: relative; height: 110px; padding: 0; overflow: hidden; display: flex; align-items: flex-end; }
  .tile img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .tile span { position: relative; width: 100%; padding: 8px; background: rgba(0,0,0,.45); color: #fff; text-align: left; }
`;

customElements.define("resident-scenes-card", ResidentScenesCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "resident-scenes-card", name: "Resident Scenes", description: "Create, edit and run resident scenes" });
