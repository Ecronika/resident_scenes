// Built from src/resident-scenes-card.js by npm run build, do not edit.
(() => {
  var __defProp = Object.defineProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // node_modules/@lit/reactive-element/css-tag.js
  /**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var t = globalThis;
  var e = t.ShadowRoot && (void 0 === t.ShadyCSS || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
  var s = /* @__PURE__ */ Symbol();
  var o = /* @__PURE__ */ new WeakMap();
  var n = class {
    constructor(t5, e5, o5) {
      if (this._$cssResult$ = true, o5 !== s) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
      this.cssText = t5, this.t = e5;
    }
    get styleSheet() {
      let t5 = this.o;
      const s5 = this.t;
      if (e && void 0 === t5) {
        const e5 = void 0 !== s5 && 1 === s5.length;
        e5 && (t5 = o.get(s5)), void 0 === t5 && ((this.o = t5 = new CSSStyleSheet()).replaceSync(this.cssText), e5 && o.set(s5, t5));
      }
      return t5;
    }
    toString() {
      return this.cssText;
    }
  };
  var r = (t5) => new n("string" == typeof t5 ? t5 : t5 + "", void 0, s);
  var i = (t5, ...e5) => {
    const o5 = 1 === t5.length ? t5[0] : e5.reduce((e6, s5, o6) => e6 + ((t6) => {
      if (true === t6._$cssResult$) return t6.cssText;
      if ("number" == typeof t6) return t6;
      throw Error("Value passed to 'css' function must be a 'css' function result: " + t6 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
    })(s5) + t5[o6 + 1], t5[0]);
    return new n(o5, t5, s);
  };
  var S = (s5, o5) => {
    if (e) s5.adoptedStyleSheets = o5.map((t5) => t5 instanceof CSSStyleSheet ? t5 : t5.styleSheet);
    else for (const e5 of o5) {
      const o6 = document.createElement("style"), n4 = t.litNonce;
      void 0 !== n4 && o6.setAttribute("nonce", n4), o6.textContent = e5.cssText, s5.appendChild(o6);
    }
  };
  var c = e ? (t5) => t5 : (t5) => t5 instanceof CSSStyleSheet ? ((t6) => {
    let e5 = "";
    for (const s5 of t6.cssRules) e5 += s5.cssText;
    return r(e5);
  })(t5) : t5;

  // node_modules/@lit/reactive-element/reactive-element.js
  /**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
  var a = globalThis;
  var c2 = a.trustedTypes;
  var l = c2 ? c2.emptyScript : "";
  var p = a.reactiveElementPolyfillSupport;
  var d = (t5, s5) => t5;
  var u = { toAttribute(t5, s5) {
    switch (s5) {
      case Boolean:
        t5 = t5 ? l : null;
        break;
      case Object:
      case Array:
        t5 = null == t5 ? t5 : JSON.stringify(t5);
    }
    return t5;
  }, fromAttribute(t5, s5) {
    let i7 = t5;
    switch (s5) {
      case Boolean:
        i7 = null !== t5;
        break;
      case Number:
        i7 = null === t5 ? null : Number(t5);
        break;
      case Object:
      case Array:
        try {
          i7 = JSON.parse(t5);
        } catch (t6) {
          i7 = null;
        }
    }
    return i7;
  } };
  var f = (t5, s5) => !i2(t5, s5);
  var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
  Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), a.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
  var y = class extends HTMLElement {
    static addInitializer(t5) {
      this._$Ei(), (this.l ??= []).push(t5);
    }
    static get observedAttributes() {
      return this.finalize(), this._$Eh && [...this._$Eh.keys()];
    }
    static createProperty(t5, s5 = b) {
      if (s5.state && (s5.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t5) && ((s5 = Object.create(s5)).wrapped = true), this.elementProperties.set(t5, s5), !s5.noAccessor) {
        const i7 = /* @__PURE__ */ Symbol(), h4 = this.getPropertyDescriptor(t5, i7, s5);
        void 0 !== h4 && e2(this.prototype, t5, h4);
      }
    }
    static getPropertyDescriptor(t5, s5, i7) {
      const { get: e5, set: r5 } = h(this.prototype, t5) ?? { get() {
        return this[s5];
      }, set(t6) {
        this[s5] = t6;
      } };
      return { get: e5, set(s6) {
        const h4 = e5?.call(this);
        r5?.call(this, s6), this.requestUpdate(t5, h4, i7);
      }, configurable: true, enumerable: true };
    }
    static getPropertyOptions(t5) {
      return this.elementProperties.get(t5) ?? b;
    }
    static _$Ei() {
      if (this.hasOwnProperty(d("elementProperties"))) return;
      const t5 = n2(this);
      t5.finalize(), void 0 !== t5.l && (this.l = [...t5.l]), this.elementProperties = new Map(t5.elementProperties);
    }
    static finalize() {
      if (this.hasOwnProperty(d("finalized"))) return;
      if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
        const t6 = this.properties, s5 = [...r2(t6), ...o2(t6)];
        for (const i7 of s5) this.createProperty(i7, t6[i7]);
      }
      const t5 = this[Symbol.metadata];
      if (null !== t5) {
        const s5 = litPropertyMetadata.get(t5);
        if (void 0 !== s5) for (const [t6, i7] of s5) this.elementProperties.set(t6, i7);
      }
      this._$Eh = /* @__PURE__ */ new Map();
      for (const [t6, s5] of this.elementProperties) {
        const i7 = this._$Eu(t6, s5);
        void 0 !== i7 && this._$Eh.set(i7, t6);
      }
      this.elementStyles = this.finalizeStyles(this.styles);
    }
    static finalizeStyles(s5) {
      const i7 = [];
      if (Array.isArray(s5)) {
        const e5 = new Set(s5.flat(1 / 0).reverse());
        for (const s6 of e5) i7.unshift(c(s6));
      } else void 0 !== s5 && i7.push(c(s5));
      return i7;
    }
    static _$Eu(t5, s5) {
      const i7 = s5.attribute;
      return false === i7 ? void 0 : "string" == typeof i7 ? i7 : "string" == typeof t5 ? t5.toLowerCase() : void 0;
    }
    constructor() {
      super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
    }
    _$Ev() {
      this._$ES = new Promise((t5) => this.enableUpdating = t5), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t5) => t5(this));
    }
    addController(t5) {
      (this._$EO ??= /* @__PURE__ */ new Set()).add(t5), void 0 !== this.renderRoot && this.isConnected && t5.hostConnected?.();
    }
    removeController(t5) {
      this._$EO?.delete(t5);
    }
    _$E_() {
      const t5 = /* @__PURE__ */ new Map(), s5 = this.constructor.elementProperties;
      for (const i7 of s5.keys()) this.hasOwnProperty(i7) && (t5.set(i7, this[i7]), delete this[i7]);
      t5.size > 0 && (this._$Ep = t5);
    }
    createRenderRoot() {
      const t5 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
      return S(t5, this.constructor.elementStyles), t5;
    }
    connectedCallback() {
      this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach((t5) => t5.hostConnected?.());
    }
    enableUpdating(t5) {
    }
    disconnectedCallback() {
      this._$EO?.forEach((t5) => t5.hostDisconnected?.());
    }
    attributeChangedCallback(t5, s5, i7) {
      this._$AK(t5, i7);
    }
    _$ET(t5, s5) {
      const i7 = this.constructor.elementProperties.get(t5), e5 = this.constructor._$Eu(t5, i7);
      if (void 0 !== e5 && true === i7.reflect) {
        const h4 = (void 0 !== i7.converter?.toAttribute ? i7.converter : u).toAttribute(s5, i7.type);
        this._$Em = t5, null == h4 ? this.removeAttribute(e5) : this.setAttribute(e5, h4), this._$Em = null;
      }
    }
    _$AK(t5, s5) {
      const i7 = this.constructor, e5 = i7._$Eh.get(t5);
      if (void 0 !== e5 && this._$Em !== e5) {
        const t6 = i7.getPropertyOptions(e5), h4 = "function" == typeof t6.converter ? { fromAttribute: t6.converter } : void 0 !== t6.converter?.fromAttribute ? t6.converter : u;
        this._$Em = e5;
        const r5 = h4.fromAttribute(s5, t6.type);
        this[e5] = r5 ?? this._$Ej?.get(e5) ?? r5, this._$Em = null;
      }
    }
    requestUpdate(t5, s5, i7, e5 = false, h4) {
      if (void 0 !== t5) {
        const r5 = this.constructor;
        if (false === e5 && (h4 = this[t5]), i7 ??= r5.getPropertyOptions(t5), !((i7.hasChanged ?? f)(h4, s5) || i7.useDefault && i7.reflect && h4 === this._$Ej?.get(t5) && !this.hasAttribute(r5._$Eu(t5, i7)))) return;
        this.C(t5, s5, i7);
      }
      false === this.isUpdatePending && (this._$ES = this._$EP());
    }
    C(t5, s5, { useDefault: i7, reflect: e5, wrapped: h4 }, r5) {
      i7 && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t5) && (this._$Ej.set(t5, r5 ?? s5 ?? this[t5]), true !== h4 || void 0 !== r5) || (this._$AL.has(t5) || (this.hasUpdated || i7 || (s5 = void 0), this._$AL.set(t5, s5)), true === e5 && this._$Em !== t5 && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t5));
    }
    async _$EP() {
      this.isUpdatePending = true;
      try {
        await this._$ES;
      } catch (t6) {
        Promise.reject(t6);
      }
      const t5 = this.scheduleUpdate();
      return null != t5 && await t5, !this.isUpdatePending;
    }
    scheduleUpdate() {
      return this.performUpdate();
    }
    performUpdate() {
      if (!this.isUpdatePending) return;
      if (!this.hasUpdated) {
        if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
          for (const [t7, s6] of this._$Ep) this[t7] = s6;
          this._$Ep = void 0;
        }
        const t6 = this.constructor.elementProperties;
        if (t6.size > 0) for (const [s6, i7] of t6) {
          const { wrapped: t7 } = i7, e5 = this[s6];
          true !== t7 || this._$AL.has(s6) || void 0 === e5 || this.C(s6, void 0, i7, e5);
        }
      }
      let t5 = false;
      const s5 = this._$AL;
      try {
        t5 = this.shouldUpdate(s5), t5 ? (this.willUpdate(s5), this._$EO?.forEach((t6) => t6.hostUpdate?.()), this.update(s5)) : this._$EM();
      } catch (s6) {
        throw t5 = false, this._$EM(), s6;
      }
      t5 && this._$AE(s5);
    }
    willUpdate(t5) {
    }
    _$AE(t5) {
      this._$EO?.forEach((t6) => t6.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t5)), this.updated(t5);
    }
    _$EM() {
      this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
    }
    get updateComplete() {
      return this.getUpdateComplete();
    }
    getUpdateComplete() {
      return this._$ES;
    }
    shouldUpdate(t5) {
      return true;
    }
    update(t5) {
      this._$Eq &&= this._$Eq.forEach((t6) => this._$ET(t6, this[t6])), this._$EM();
    }
    updated(t5) {
    }
    firstUpdated(t5) {
    }
  };
  y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = /* @__PURE__ */ new Map(), y[d("finalized")] = /* @__PURE__ */ new Map(), p?.({ ReactiveElement: y }), (a.reactiveElementVersions ??= []).push("2.1.2");

  // node_modules/lit-html/lit-html.js
  /**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var t2 = globalThis;
  var i3 = (t5) => t5;
  var s2 = t2.trustedTypes;
  var e3 = s2 ? s2.createPolicy("lit-html", { createHTML: (t5) => t5 }) : void 0;
  var h2 = "$lit$";
  var o3 = `lit$${Math.random().toFixed(9).slice(2)}$`;
  var n3 = "?" + o3;
  var r3 = `<${n3}>`;
  var l2 = document;
  var c3 = () => l2.createComment("");
  var a2 = (t5) => null === t5 || "object" != typeof t5 && "function" != typeof t5;
  var u2 = Array.isArray;
  var d2 = (t5) => u2(t5) || "function" == typeof t5?.[Symbol.iterator];
  var f2 = "[ 	\n\f\r]";
  var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
  var _ = /-->/g;
  var m = />/g;
  var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
  var g = /'/g;
  var $ = /"/g;
  var y2 = /^(?:script|style|textarea|title)$/i;
  var x = (t5) => (i7, ...s5) => ({ _$litType$: t5, strings: i7, values: s5 });
  var b2 = x(1);
  var w = x(2);
  var T = x(3);
  var E = /* @__PURE__ */ Symbol.for("lit-noChange");
  var A = /* @__PURE__ */ Symbol.for("lit-nothing");
  var C = /* @__PURE__ */ new WeakMap();
  var P = l2.createTreeWalker(l2, 129);
  function V(t5, i7) {
    if (!u2(t5) || !t5.hasOwnProperty("raw")) throw Error("invalid template strings array");
    return void 0 !== e3 ? e3.createHTML(i7) : i7;
  }
  var N = (t5, i7) => {
    const s5 = t5.length - 1, e5 = [];
    let n4, l4 = 2 === i7 ? "<svg>" : 3 === i7 ? "<math>" : "", c5 = v;
    for (let i8 = 0; i8 < s5; i8++) {
      const s6 = t5[i8];
      let a3, u5, d3 = -1, f3 = 0;
      for (; f3 < s6.length && (c5.lastIndex = f3, u5 = c5.exec(s6), null !== u5); ) f3 = c5.lastIndex, c5 === v ? "!--" === u5[1] ? c5 = _ : void 0 !== u5[1] ? c5 = m : void 0 !== u5[2] ? (y2.test(u5[2]) && (n4 = RegExp("</" + u5[2], "g")), c5 = p2) : void 0 !== u5[3] && (c5 = p2) : c5 === p2 ? ">" === u5[0] ? (c5 = n4 ?? v, d3 = -1) : void 0 === u5[1] ? d3 = -2 : (d3 = c5.lastIndex - u5[2].length, a3 = u5[1], c5 = void 0 === u5[3] ? p2 : '"' === u5[3] ? $ : g) : c5 === $ || c5 === g ? c5 = p2 : c5 === _ || c5 === m ? c5 = v : (c5 = p2, n4 = void 0);
      const x2 = c5 === p2 && t5[i8 + 1].startsWith("/>") ? " " : "";
      l4 += c5 === v ? s6 + r3 : d3 >= 0 ? (e5.push(a3), s6.slice(0, d3) + h2 + s6.slice(d3) + o3 + x2) : s6 + o3 + (-2 === d3 ? i8 : x2);
    }
    return [V(t5, l4 + (t5[s5] || "<?>") + (2 === i7 ? "</svg>" : 3 === i7 ? "</math>" : "")), e5];
  };
  var S2 = class _S {
    constructor({ strings: t5, _$litType$: i7 }, e5) {
      let r5;
      this.parts = [];
      let l4 = 0, a3 = 0;
      const u5 = t5.length - 1, d3 = this.parts, [f3, v3] = N(t5, i7);
      if (this.el = _S.createElement(f3, e5), P.currentNode = this.el.content, 2 === i7 || 3 === i7) {
        const t6 = this.el.content.firstChild;
        t6.replaceWith(...t6.childNodes);
      }
      for (; null !== (r5 = P.nextNode()) && d3.length < u5; ) {
        if (1 === r5.nodeType) {
          if (r5.hasAttributes()) for (const t6 of r5.getAttributeNames()) if (t6.endsWith(h2)) {
            const i8 = v3[a3++], s5 = r5.getAttribute(t6).split(o3), e6 = /([.?@])?(.*)/.exec(i8);
            d3.push({ type: 1, index: l4, name: e6[2], strings: s5, ctor: "." === e6[1] ? I : "?" === e6[1] ? L : "@" === e6[1] ? z : H }), r5.removeAttribute(t6);
          } else t6.startsWith(o3) && (d3.push({ type: 6, index: l4 }), r5.removeAttribute(t6));
          if (y2.test(r5.tagName)) {
            const t6 = r5.textContent.split(o3), i8 = t6.length - 1;
            if (i8 > 0) {
              r5.textContent = s2 ? s2.emptyScript : "";
              for (let s5 = 0; s5 < i8; s5++) r5.append(t6[s5], c3()), P.nextNode(), d3.push({ type: 2, index: ++l4 });
              r5.append(t6[i8], c3());
            }
          }
        } else if (8 === r5.nodeType) if (r5.data === n3) d3.push({ type: 2, index: l4 });
        else {
          let t6 = -1;
          for (; -1 !== (t6 = r5.data.indexOf(o3, t6 + 1)); ) d3.push({ type: 7, index: l4 }), t6 += o3.length - 1;
        }
        l4++;
      }
    }
    static createElement(t5, i7) {
      const s5 = l2.createElement("template");
      return s5.innerHTML = t5, s5;
    }
  };
  function M(t5, i7, s5 = t5, e5) {
    if (i7 === E) return i7;
    let h4 = void 0 !== e5 ? s5._$Co?.[e5] : s5._$Cl;
    const o5 = a2(i7) ? void 0 : i7._$litDirective$;
    return h4?.constructor !== o5 && (h4?._$AO?.(false), void 0 === o5 ? h4 = void 0 : (h4 = new o5(t5), h4._$AT(t5, s5, e5)), void 0 !== e5 ? (s5._$Co ??= [])[e5] = h4 : s5._$Cl = h4), void 0 !== h4 && (i7 = M(t5, h4._$AS(t5, i7.values), h4, e5)), i7;
  }
  var R = class {
    constructor(t5, i7) {
      this._$AV = [], this._$AN = void 0, this._$AD = t5, this._$AM = i7;
    }
    get parentNode() {
      return this._$AM.parentNode;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    u(t5) {
      const { el: { content: i7 }, parts: s5 } = this._$AD, e5 = (t5?.creationScope ?? l2).importNode(i7, true);
      P.currentNode = e5;
      let h4 = P.nextNode(), o5 = 0, n4 = 0, r5 = s5[0];
      for (; void 0 !== r5; ) {
        if (o5 === r5.index) {
          let i8;
          2 === r5.type ? i8 = new k(h4, h4.nextSibling, this, t5) : 1 === r5.type ? i8 = new r5.ctor(h4, r5.name, r5.strings, this, t5) : 6 === r5.type && (i8 = new Z(h4, this, t5)), this._$AV.push(i8), r5 = s5[++n4];
        }
        o5 !== r5?.index && (h4 = P.nextNode(), o5++);
      }
      return P.currentNode = l2, e5;
    }
    p(t5) {
      let i7 = 0;
      for (const s5 of this._$AV) void 0 !== s5 && (void 0 !== s5.strings ? (s5._$AI(t5, s5, i7), i7 += s5.strings.length - 2) : s5._$AI(t5[i7])), i7++;
    }
  };
  var k = class _k {
    get _$AU() {
      return this._$AM?._$AU ?? this._$Cv;
    }
    constructor(t5, i7, s5, e5) {
      this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t5, this._$AB = i7, this._$AM = s5, this.options = e5, this._$Cv = e5?.isConnected ?? true;
    }
    get parentNode() {
      let t5 = this._$AA.parentNode;
      const i7 = this._$AM;
      return void 0 !== i7 && 11 === t5?.nodeType && (t5 = i7.parentNode), t5;
    }
    get startNode() {
      return this._$AA;
    }
    get endNode() {
      return this._$AB;
    }
    _$AI(t5, i7 = this) {
      t5 = M(this, t5, i7), a2(t5) ? t5 === A || null == t5 || "" === t5 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t5 !== this._$AH && t5 !== E && this._(t5) : void 0 !== t5._$litType$ ? this.$(t5) : void 0 !== t5.nodeType ? this.T(t5) : d2(t5) ? this.k(t5) : this._(t5);
    }
    O(t5) {
      return this._$AA.parentNode.insertBefore(t5, this._$AB);
    }
    T(t5) {
      this._$AH !== t5 && (this._$AR(), this._$AH = this.O(t5));
    }
    _(t5) {
      this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t5 : this.T(l2.createTextNode(t5)), this._$AH = t5;
    }
    $(t5) {
      const { values: i7, _$litType$: s5 } = t5, e5 = "number" == typeof s5 ? this._$AC(t5) : (void 0 === s5.el && (s5.el = S2.createElement(V(s5.h, s5.h[0]), this.options)), s5);
      if (this._$AH?._$AD === e5) this._$AH.p(i7);
      else {
        const t6 = new R(e5, this), s6 = t6.u(this.options);
        t6.p(i7), this.T(s6), this._$AH = t6;
      }
    }
    _$AC(t5) {
      let i7 = C.get(t5.strings);
      return void 0 === i7 && C.set(t5.strings, i7 = new S2(t5)), i7;
    }
    k(t5) {
      u2(this._$AH) || (this._$AH = [], this._$AR());
      const i7 = this._$AH;
      let s5, e5 = 0;
      for (const h4 of t5) e5 === i7.length ? i7.push(s5 = new _k(this.O(c3()), this.O(c3()), this, this.options)) : s5 = i7[e5], s5._$AI(h4), e5++;
      e5 < i7.length && (this._$AR(s5 && s5._$AB.nextSibling, e5), i7.length = e5);
    }
    _$AR(t5 = this._$AA.nextSibling, s5) {
      for (this._$AP?.(false, true, s5); t5 !== this._$AB; ) {
        const s6 = i3(t5).nextSibling;
        i3(t5).remove(), t5 = s6;
      }
    }
    setConnected(t5) {
      void 0 === this._$AM && (this._$Cv = t5, this._$AP?.(t5));
    }
  };
  var H = class {
    get tagName() {
      return this.element.tagName;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    constructor(t5, i7, s5, e5, h4) {
      this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t5, this.name = i7, this._$AM = e5, this.options = h4, s5.length > 2 || "" !== s5[0] || "" !== s5[1] ? (this._$AH = Array(s5.length - 1).fill(new String()), this.strings = s5) : this._$AH = A;
    }
    _$AI(t5, i7 = this, s5, e5) {
      const h4 = this.strings;
      let o5 = false;
      if (void 0 === h4) t5 = M(this, t5, i7, 0), o5 = !a2(t5) || t5 !== this._$AH && t5 !== E, o5 && (this._$AH = t5);
      else {
        const e6 = t5;
        let n4, r5;
        for (t5 = h4[0], n4 = 0; n4 < h4.length - 1; n4++) r5 = M(this, e6[s5 + n4], i7, n4), r5 === E && (r5 = this._$AH[n4]), o5 ||= !a2(r5) || r5 !== this._$AH[n4], r5 === A ? t5 = A : t5 !== A && (t5 += (r5 ?? "") + h4[n4 + 1]), this._$AH[n4] = r5;
      }
      o5 && !e5 && this.j(t5);
    }
    j(t5) {
      t5 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t5 ?? "");
    }
  };
  var I = class extends H {
    constructor() {
      super(...arguments), this.type = 3;
    }
    j(t5) {
      this.element[this.name] = t5 === A ? void 0 : t5;
    }
  };
  var L = class extends H {
    constructor() {
      super(...arguments), this.type = 4;
    }
    j(t5) {
      this.element.toggleAttribute(this.name, !!t5 && t5 !== A);
    }
  };
  var z = class extends H {
    constructor(t5, i7, s5, e5, h4) {
      super(t5, i7, s5, e5, h4), this.type = 5;
    }
    _$AI(t5, i7 = this) {
      if ((t5 = M(this, t5, i7, 0) ?? A) === E) return;
      const s5 = this._$AH, e5 = t5 === A && s5 !== A || t5.capture !== s5.capture || t5.once !== s5.once || t5.passive !== s5.passive, h4 = t5 !== A && (s5 === A || e5);
      e5 && this.element.removeEventListener(this.name, this, s5), h4 && this.element.addEventListener(this.name, this, t5), this._$AH = t5;
    }
    handleEvent(t5) {
      "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t5) : this._$AH.handleEvent(t5);
    }
  };
  var Z = class {
    constructor(t5, i7, s5) {
      this.element = t5, this.type = 6, this._$AN = void 0, this._$AM = i7, this.options = s5;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(t5) {
      M(this, t5);
    }
  };
  var j = { M: h2, P: o3, A: n3, C: 1, L: N, R, D: d2, V: M, I: k, H, N: L, U: z, B: I, F: Z };
  var B = t2.litHtmlPolyfillSupport;
  B?.(S2, k), (t2.litHtmlVersions ??= []).push("3.3.3");
  var D = (t5, i7, s5) => {
    const e5 = s5?.renderBefore ?? i7;
    let h4 = e5._$litPart$;
    if (void 0 === h4) {
      const t6 = s5?.renderBefore ?? null;
      e5._$litPart$ = h4 = new k(i7.insertBefore(c3(), t6), t6, void 0, s5 ?? {});
    }
    return h4._$AI(t5), h4;
  };

  // node_modules/lit-element/lit-element.js
  /**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var s3 = globalThis;
  var i4 = class extends y {
    constructor() {
      super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
    }
    createRenderRoot() {
      const t5 = super.createRenderRoot();
      return this.renderOptions.renderBefore ??= t5.firstChild, t5;
    }
    update(t5) {
      const r5 = this.render();
      this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t5), this._$Do = D(r5, this.renderRoot, this.renderOptions);
    }
    connectedCallback() {
      super.connectedCallback(), this._$Do?.setConnected(true);
    }
    disconnectedCallback() {
      super.disconnectedCallback(), this._$Do?.setConnected(false);
    }
    render() {
      return E;
    }
  };
  i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
  var o4 = s3.litElementPolyfillSupport;
  o4?.({ LitElement: i4 });
  (s3.litElementVersions ??= []).push("4.2.2");

  // node_modules/lit-html/is-server.js
  /**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */

  // node_modules/lit-html/directive.js
  /**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var t3 = { ATTRIBUTE: 1, CHILD: 2, PROPERTY: 3, BOOLEAN_ATTRIBUTE: 4, EVENT: 5, ELEMENT: 6 };
  var e4 = (t5) => (...e5) => ({ _$litDirective$: t5, values: e5 });
  var i5 = class {
    constructor(t5) {
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AT(t5, e5, i7) {
      this._$Ct = t5, this._$AM = e5, this._$Ci = i7;
    }
    _$AS(t5, e5) {
      return this.update(t5, e5);
    }
    update(t5, e5) {
      return this.render(...e5);
    }
  };

  // node_modules/lit-html/directive-helpers.js
  /**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var { I: t4 } = j;
  var i6 = (o5) => o5;
  var r4 = (o5) => void 0 === o5.strings;
  var s4 = () => document.createComment("");
  var v2 = (o5, n4, e5) => {
    const l4 = o5._$AA.parentNode, d3 = void 0 === n4 ? o5._$AB : n4._$AA;
    if (void 0 === e5) {
      const i7 = l4.insertBefore(s4(), d3), n5 = l4.insertBefore(s4(), d3);
      e5 = new t4(i7, n5, o5, o5.options);
    } else {
      const t5 = e5._$AB.nextSibling, n5 = e5._$AM, c5 = n5 !== o5;
      if (c5) {
        let t6;
        e5._$AQ?.(o5), e5._$AM = o5, void 0 !== e5._$AP && (t6 = o5._$AU) !== n5._$AU && e5._$AP(t6);
      }
      if (t5 !== d3 || c5) {
        let o6 = e5._$AA;
        for (; o6 !== t5; ) {
          const t6 = i6(o6).nextSibling;
          i6(l4).insertBefore(o6, d3), o6 = t6;
        }
      }
    }
    return e5;
  };
  var u3 = (o5, t5, i7 = o5) => (o5._$AI(t5, i7), o5);
  var m2 = {};
  var p3 = (o5, t5 = m2) => o5._$AH = t5;
  var M2 = (o5) => o5._$AH;
  var h3 = (o5) => {
    o5._$AR(), o5._$AA.remove();
  };

  // node_modules/lit-html/directives/live.js
  /**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var l3 = e4(class extends i5 {
    constructor(r5) {
      if (super(r5), r5.type !== t3.PROPERTY && r5.type !== t3.ATTRIBUTE && r5.type !== t3.BOOLEAN_ATTRIBUTE) throw Error("The `live` directive is not allowed on child or event bindings");
      if (!r4(r5)) throw Error("`live` bindings can only contain a single expression");
    }
    render(r5) {
      return r5;
    }
    update(i7, [t5]) {
      if (t5 === E || t5 === A) return t5;
      const o5 = i7.element, l4 = i7.name;
      if (i7.type === t3.PROPERTY) {
        if (t5 === o5[l4]) return E;
      } else if (i7.type === t3.BOOLEAN_ATTRIBUTE) {
        if (!!t5 === o5.hasAttribute(l4)) return E;
      } else if (i7.type === t3.ATTRIBUTE && o5.getAttribute(l4) === t5 + "") return E;
      return p3(i7), t5;
    }
  });

  // node_modules/lit-html/directives/repeat.js
  /**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   */
  var u4 = (e5, s5, t5) => {
    const r5 = /* @__PURE__ */ new Map();
    for (let l4 = s5; l4 <= t5; l4++) r5.set(e5[l4], l4);
    return r5;
  };
  var c4 = e4(class extends i5 {
    constructor(e5) {
      if (super(e5), e5.type !== t3.CHILD) throw Error("repeat() can only be used in text expressions");
    }
    dt(e5, s5, t5) {
      let r5;
      void 0 === t5 ? t5 = s5 : void 0 !== s5 && (r5 = s5);
      const l4 = [], o5 = [];
      let i7 = 0;
      for (const s6 of e5) l4[i7] = r5 ? r5(s6, i7) : i7, o5[i7] = t5(s6, i7), i7++;
      return { values: o5, keys: l4 };
    }
    render(e5, s5, t5) {
      return this.dt(e5, s5, t5).values;
    }
    update(s5, [t5, r5, c5]) {
      const d3 = M2(s5), { values: p4, keys: a3 } = this.dt(t5, r5, c5);
      if (!Array.isArray(d3)) return this.ut = a3, p4;
      const h4 = this.ut ??= [], v3 = [];
      let m3, y3, x2 = 0, j2 = d3.length - 1, k2 = 0, w2 = p4.length - 1;
      for (; x2 <= j2 && k2 <= w2; ) if (null === d3[x2]) x2++;
      else if (null === d3[j2]) j2--;
      else if (h4[x2] === a3[k2]) v3[k2] = u3(d3[x2], p4[k2]), x2++, k2++;
      else if (h4[j2] === a3[w2]) v3[w2] = u3(d3[j2], p4[w2]), j2--, w2--;
      else if (h4[x2] === a3[w2]) v3[w2] = u3(d3[x2], p4[w2]), v2(s5, v3[w2 + 1], d3[x2]), x2++, w2--;
      else if (h4[j2] === a3[k2]) v3[k2] = u3(d3[j2], p4[k2]), v2(s5, d3[x2], d3[j2]), j2--, k2++;
      else if (void 0 === m3 && (m3 = u4(a3, k2, w2), y3 = u4(h4, x2, j2)), m3.has(h4[x2])) if (m3.has(h4[j2])) {
        const e5 = y3.get(a3[k2]), t6 = void 0 !== e5 ? d3[e5] : null;
        if (null === t6) {
          const e6 = v2(s5, d3[x2]);
          u3(e6, p4[k2]), v3[k2] = e6;
        } else v3[k2] = u3(t6, p4[k2]), v2(s5, d3[x2], t6), d3[e5] = null;
        k2++;
      } else h3(d3[j2]), j2--;
      else h3(d3[x2]), x2++;
      for (; k2 <= w2; ) {
        const e5 = v2(s5, v3[w2 + 1]);
        u3(e5, p4[k2]), v3[k2++] = e5;
      }
      for (; x2 <= j2; ) {
        const e5 = d3[x2++];
        null !== e5 && h3(e5);
      }
      return this.ut = a3, p3(s5, v3), E;
    }
  });

  // src/resident-scenes-card.js
  var VERSION = "0.3.3";
  var WS = "resident_scenes";
  var HOUSE = "_house";
  var DOMAINS = ["light", "cover", "climate", "switch", "fan", "media_player", "scene"];
  var LIVE = ["light", "cover", "switch", "fan"];
  var FLAGS = ["missing", "not_released", "other_area"];
  var VISIBLE_RELOAD = 5 * 60 * 1e3;
  var newId = () => Math.random().toString(36).slice(2, 10);
  var PLACEHOLDER = b2`<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor"
  d="M19 19H5V5h14m0-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2m-5.04 9.29-2.75 3.54-1.96-2.36L6.5 17h11z"/></svg>`;
  var I18N = {
    en: {
      new_scene: "New scene",
      scenes: "Scenes",
      other_scenes: "Other scenes",
      favorites: "Favorites",
      play: "Play",
      played: "Played",
      play_failed: "The scene could not be played.",
      edit: "Edit",
      done: "Done",
      delete: "Delete",
      duplicate: "Duplicate",
      back: "Back",
      name: "Name",
      image: "Image",
      no_image: "No image",
      choose_image: "Change image",
      all: "All",
      slot: "Slot",
      free: "free",
      no_slot: "No slot",
      close: "Close",
      loses: "loses its place.",
      replace: "Replace",
      off: "Off",
      closed: "Closed",
      on: "On",
      favorite: "Favorite",
      volume: "Volume",
      call: "Run",
      missing: "Device missing",
      unavailable: "Not reachable",
      not_released: "Not released",
      other_area: "In another room",
      favorite_missing: "Favorite missing",
      scene_missing: "Scene missing",
      all_off: "All off",
      all_closed: "All closed",
      all_house: "All in the house",
      rights_gone: "Your right to change scenes was withdrawn.",
      empty: "No scenes yet.",
      no_steps: "No steps yet.",
      no_devices: "No released devices.",
      confirm_delete: "Delete the scene \u201C{name}\u201D for good?",
      used_on: "Used by:",
      outside_note: "Automations and schedules using it will stop working.",
      yes: "Delete",
      no: "Keep",
      cancel: "Cancel",
      copy: "copy",
      reload: "A new version is installed. Please reload.",
      reload_btn: "Reload",
      house: "House",
      no_room: "No room",
      devices_n: "devices",
      installer: "Installer",
      protected: "Installer scene (protected)",
      released: "Content released to residents",
      brightness: "Brightness",
      color_temp: "Colour temperature",
      hue: "Colour",
      position: "Position",
      tilt: "Tilt",
      temperature: "Temperature",
      percentage: "Speed",
      transition: "Transition (s)",
      order: "Sequence",
      live: "Live adjustments",
      undo: "Undo last change",
      rights: "Permissions",
      may_edit: "may change scenes",
      panel: "Panel",
      own_image: "Own image",
      crop_x: "Horizontal",
      crop_y: "Vertical",
      use_image: "Use image",
      room_scene: "Room scene",
      remove: "Remove",
      open: "Open",
      add_step: "Add step",
      add_delay: "Add delay",
      pick_room: "Room",
      pick_domain: "Trade",
      stale: "Not up to date, retrying \u2026",
      offline: "Connection lost. Editing is locked until it is back.",
      seconds: "Delay (s)",
      no_room_scene: "No room scene any more",
      white: "White",
      colour: "Colour",
      saturation: "Saturation",
      drag: "Drag to reorder, or use the arrow keys",
      moved: "Moved to position {n} of {m}.",
      more: "more",
      no_effect: "no effect",
      undone: "The previous state applies again.",
      no_favorites: "No favorites: none are stored in the music system, or its favorites sensor is disabled.",
      light: "Lights",
      cover: "Shading",
      climate: "Climate",
      switch: "Switches",
      fan: "Fans",
      media_player: "Music",
      scene: "Scenes",
      err: {
        unauthorized: "You may not change scenes.",
        name_exists: "This name is taken.",
        invalid_name: "Name is empty or too long.",
        limit_reached: "Limit of scenes reached.",
        too_many_steps: "Too many steps or devices.",
        entity_not_allowed: "Not released for this scene:",
        entity_unavailable: "Not reachable, its state cannot be captured:",
        unknown_favorite: "This favorite no longer exists.",
        not_found: "The scene no longer exists.",
        invalid_step: "Invalid setting.",
        invalid_value: "Value out of range:",
        invalid_delay: "Delay out of range:",
        invalid_temperature: "Temperature out of range:",
        favorite_not_supported: "Favorites only work on players of the music system:",
        invalid_scene_call: "This scene cannot be called.",
        duplicate_entity: "Device used twice:",
        protected: "Installer scene: only its released content can be changed.",
        invalid_image: "Image not found.",
        invalid_image_file: "This is not an image file.",
        image_too_large: "Image too large, limit:",
        image_limit: "Image limit reached:",
        nothing_to_undo: "Nothing to undo.",
        step_missing: "This step was removed meanwhile. The current state is shown.",
        default: "Saving failed."
      }
    },
    de: {
      new_scene: "Neue Szene",
      scenes: "Szenen",
      other_scenes: "Weitere Szenen",
      favorites: "Favoriten",
      play: "Abspielen",
      played: "Ausgel\xF6st",
      play_failed: "Die Szene lie\xDF sich nicht ausl\xF6sen.",
      edit: "\xC4ndern",
      done: "Fertig",
      delete: "L\xF6schen",
      duplicate: "Duplizieren",
      back: "Zur\xFCck",
      name: "Name",
      image: "Bild",
      no_image: "Kein Bild",
      choose_image: "Bild \xE4ndern",
      all: "Alle",
      slot: "Platz",
      free: "frei",
      no_slot: "Kein Platz",
      close: "Schlie\xDFen",
      loses: "verliert seinen Platz.",
      replace: "Ersetzen",
      off: "Aus",
      closed: "Zu",
      on: "An",
      favorite: "Favorit",
      volume: "Lautst\xE4rke",
      call: "Aufruf",
      missing: "Ger\xE4t fehlt",
      unavailable: "Nicht erreichbar",
      not_released: "Nicht freigegeben",
      other_area: "In anderem Raum",
      favorite_missing: "Favorit fehlt",
      scene_missing: "Szene fehlt",
      all_off: "Alle aus",
      all_closed: "Alle zu",
      all_house: "Alle im Haus",
      rights_gone: "Ihr Recht, Szenen zu \xE4ndern, wurde entzogen.",
      empty: "Noch keine Szenen.",
      no_steps: "Noch keine Schritte.",
      no_devices: "Keine freigegebenen Ger\xE4te.",
      confirm_delete: "Die Szene \u201E{name}\u201C endg\xFCltig l\xF6schen?",
      used_on: "Verwendet in:",
      outside_note: "Automationen und Zeitpl\xE4ne damit wirken nicht mehr.",
      yes: "L\xF6schen",
      no: "Behalten",
      cancel: "Abbrechen",
      copy: "Kopie",
      reload: "Eine neue Version ist installiert. Bitte neu laden.",
      reload_btn: "Neu laden",
      house: "Haus",
      no_room: "Ohne Raum",
      devices_n: "Ger\xE4te",
      installer: "Errichter",
      protected: "Errichterszene (gesch\xFCtzt)",
      released: "Inhalt f\xFCr Bewohner freigegeben",
      brightness: "Helligkeit",
      color_temp: "Farbtemperatur",
      hue: "Farbe",
      position: "Position",
      tilt: "Neigung",
      temperature: "Temperatur",
      percentage: "Stufe",
      transition: "\xDCbergang (s)",
      order: "Ablauf",
      live: "Live-Anpassungen",
      undo: "Zur\xFCcknehmen",
      rights: "Berechtigungen",
      may_edit: "darf Szenen \xE4ndern",
      panel: "Panel",
      own_image: "Eigenes Bild",
      crop_x: "Waagerecht",
      crop_y: "Senkrecht",
      use_image: "Bild \xFCbernehmen",
      room_scene: "Raumszene",
      remove: "Entfernen",
      open: "\xD6ffnen",
      add_step: "Schritt hinzuf\xFCgen",
      add_delay: "Verz\xF6gerung hinzuf\xFCgen",
      pick_room: "Raum",
      pick_domain: "Gewerk",
      stale: "Nicht aktuell, neuer Versuch l\xE4uft \u2026",
      offline: "Verbindung unterbrochen. Der Editor ist gesperrt, bis sie zur\xFCck ist.",
      seconds: "Verz\xF6gerung (s)",
      no_room_scene: "Keine Raumszene mehr",
      white: "Wei\xDF",
      colour: "Farbe",
      saturation: "S\xE4ttigung",
      drag: "Ziehen zum Sortieren, oder Pfeiltasten",
      moved: "An Stelle {n} von {m} verschoben.",
      more: "weitere",
      no_effect: "ohne Wirkung",
      undone: "Der fr\xFChere Stand gilt wieder.",
      no_favorites: "Keine Favoriten: Im Musiksystem sind keine hinterlegt, oder sein Favoriten-Sensor ist abgeschaltet.",
      light: "Licht",
      cover: "Beschattung",
      climate: "Klima",
      switch: "Schalter",
      fan: "L\xFCfter",
      media_player: "Musik",
      scene: "Szenen",
      err: {
        unauthorized: "Sie d\xFCrfen Szenen nicht \xE4ndern.",
        name_exists: "Dieser Name ist schon vergeben.",
        invalid_name: "Name fehlt oder ist zu lang.",
        limit_reached: "H\xF6chstzahl an Szenen erreicht.",
        too_many_steps: "Zu viele Schritte oder Ger\xE4te.",
        entity_not_allowed: "F\xFCr diese Szene nicht freigegeben:",
        entity_unavailable: "Nicht erreichbar, der Zustand l\xE4sst sich nicht \xFCbernehmen:",
        unknown_favorite: "Diesen Favoriten gibt es nicht mehr.",
        not_found: "Die Szene gibt es nicht mehr.",
        invalid_step: "Ung\xFCltige Einstellung.",
        invalid_value: "Wert au\xDFerhalb des Bereichs:",
        invalid_delay: "Verz\xF6gerung au\xDFerhalb des Bereichs:",
        invalid_temperature: "Temperatur au\xDFerhalb des Bereichs:",
        favorite_not_supported: "Favoriten nur f\xFCr Player des Musiksystems:",
        invalid_scene_call: "Diese Szene l\xE4sst sich nicht aufrufen.",
        duplicate_entity: "Ger\xE4t doppelt:",
        protected: "Errichterszene: nur der freigegebene Inhalt l\xE4sst sich \xE4ndern.",
        invalid_image: "Bild nicht gefunden.",
        invalid_image_file: "Das ist keine Bilddatei.",
        image_too_large: "Bild zu gro\xDF, Grenze:",
        image_limit: "H\xF6chstzahl an Bildern erreicht:",
        nothing_to_undo: "Nichts zur\xFCckzunehmen.",
        step_missing: "Dieser Schritt wurde inzwischen entfernt. Der aktuelle Stand wird gezeigt.",
        default: "Speichern fehlgeschlagen."
      }
    }
  };
  var TILE = { w: 640, h: 480 };
  var ResidentScenesCard = class extends i4 {
    constructor() {
      super(...arguments);
      __publicField(this, "_drafts", /* @__PURE__ */ new Map());
    }
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
        this.updateComplete.then(() => this._fitLines());
      });
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
      this.hass?.connection.removeEventListener?.("disconnected", this._onDown);
      this._ro?.disconnect();
      this._unsubscribe();
    }
    updated(changed) {
      if (changed.has("hass") && this.hass && !this._started && this.isConnected) this._start();
      const f3 = this._focusStep;
      if (f3 && this._detail?.sequence?.[f3.index]?.id === f3.id) {
        this._focusStep = null;
        this.renderRoot.querySelector(`[data-action="drag"][data-id="${f3.id}"]`)?.focus();
      }
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
        const show = (k3) => {
          clip.textContent = parts.slice(0, k3).join(", ");
          more.textContent = k3 === parts.length ? "" : k3 ? `+ ${parts.length - k3} ${this._t("more")}` : `${parts.length} ${this._t("devices_n")}`;
        };
        let k2 = parts.length;
        show(k2);
        if (!clip.parentElement.clientWidth) {
          show(Math.min(2, k2));
          continue;
        }
        while (k2 > (parts.length > 1 ? 0 : 1) && clip.scrollWidth > clip.clientWidth) show(--k2);
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
      this._onReady ??= () => (this._offline = false, this._needSub = true, this._load());
      this._onDown ??= () => this._offline = true;
      this._onVisible ??= () => document.visibilityState === "visible" && Date.now() - (this._loadedAt ?? 0) > VISIBLE_RELOAD && this._load();
      this.hass.connection.addEventListener?.("ready", this._onReady);
      this.hass.connection.addEventListener?.("disconnected", this._onDown);
      document.addEventListener("visibilitychange", this._onVisible);
      this._timer = setInterval(() => this._load(), 6 * 3600 * 1e3);
      this._load();
    }
    _unsubscribe() {
      this._unsub?.then((unsub) => unsub?.()).catch(() => {
      });
      this._unsub = void 0;
    }
    _subscribe() {
      this._unsubscribe();
      this._needSub = false;
      this._unsub = this.hass.connection.subscribeMessage(() => this._load(true), { type: `${WS}/subscribe` });
      this._unsub.catch(() => this._needSub = true);
    }
    get _lang() {
      return this.hass?.locale?.language?.startsWith("de") ? "de" : "en";
    }
    _t(key) {
      return key.split(".").reduce((o5, k2) => o5?.[k2], I18N[this._lang]) ?? key;
    }
    // the range the server checks a setpoint against, its defaults included
    _tempRange(c5) {
      return `${this._num(c5.min_temp ?? 5)}\u2013${this._num(c5.max_temp ?? 35)} ${this._unit}`;
    }
    _num(value) {
      return Number(value).toLocaleString(this._lang);
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
        if (this._needSub) this._subscribe();
      } catch (err) {
        this._stale = true;
        this._backoff = Math.min((this._backoff || 1) * 2, 60);
        this._retry = setTimeout(() => this._load(), this._backoff * 1e3);
        return;
      }
      if (this._data.can_edit && this._notice === "rights_gone") this._notice = null;
      if (this._edit && !this._data.can_edit) {
        this._edit = null;
        this._notice = "rights_gone";
      }
      if (this._rights && this._data.manages_rights) this._loadRights();
      if (!this._data.manages_rights) this._rights = null;
      if (this._edit && !fromServer) this._loadDevices();
      if (this._selected) await this._loadDetail();
    }
    async _loadDetail() {
      try {
        const detail = await this.hass.callWS({ type: `${WS}/scene`, scene_id: this._selected });
        const focused = this.renderRoot.activeElement?.dataset?.key;
        for (const key of this._drafts.keys()) if (key !== focused) this._drafts.delete(key);
        this._detail = detail;
        if (this._edit?.open && !detail.sequence.some((s5) => s5.id === this._edit.open)) this._setEdit({ open: null });
      } catch (err) {
        if (err.code === "not_found") this._selected = null, this._detail = null, this._edit = null;
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
      return this._data?.scenes.find((s5) => s5.id === id);
    }
    get _scenes() {
      return [...this._data?.scenes ?? []].sort((a3, b3) => a3.name.localeCompare(b3.name));
    }
    _name(eid, fallback) {
      const st = this.hass.states[eid];
      if (st && typeof this.hass.formatEntityName === "function") {
        try {
          const name = this.hass.formatEntityName(st, [{ type: "device" }, { type: "entity" }], { separator: " \xB7 " });
          if (name) return name;
        } catch (err) {
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
        this._played = entityId;
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
      if (!this._config) return A;
      const outdated = this._data && this._data.version !== VERSION;
      let body = A;
      if (this._data && this._config.view === "favorites") {
        body = this._renderFavorites();
        if (body === A && !outdated) return A;
      } else if (this._data) body = this._renderManage();
      return b2`<div class="card">
      ${outdated ? b2`<div class="banner">${this._t("reload")}
            <button data-action="reload" @click=${() => location.reload()}>${this._t("reload_btn")}</button></div>` : A}
      ${this._stale ? b2`<p class="muted" role="status">${this._t("stale")}</p>` : A}
      ${this._notice ? b2`<p class="error" role="alert">${this._t(this._notice)}</p>` : A} ${body}
    </div>`;
    }
    _renderFavorites() {
      const tiles = this._data.favorites.map((id) => this._scene(id)).filter(Boolean);
      if (!tiles.length) return A;
      return b2`<div class="tiles">
      ${tiles.map(
        (s5) => b2`<button class="tile" data-action="play" aria-label=${s5.name} @click=${() => this._play(s5.entity_id)}>
          ${s5.image_url ? b2`<img src=${s5.image_url} alt="" />` : PLACEHOLDER}<span>${s5.name}</span>
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
      const question = editing && this._edit.confirmDelete ? this._renderConfirmDelete() : !editing && this._slots && this._detail ? this._renderSlots() : A;
      const body = this._narrow ? detail : b2`<div class="columns"><div class="col-list">${list}</div><div class="col-detail">${detail}</div></div>`;
      return b2`<div ?inert=${question !== A}>${body}</div>${question}`;
    }
    _playButton(eid, label = false, name = "") {
      const done = this._played === eid;
      return b2`<button class=${label ? "primary" : "icon"} data-action="play" aria-label=${name ? `${this._t("play")}: ${name}` : this._t("play")}
      @click=${() => this._play(eid)}>${done ? "\u2713" : "\u25B6"}${label ? ` ${this._t(done ? "played" : "play")}` : ""}</button>`;
    }
    _renderList() {
      const manage = this._config.view === "manage";
      const d3 = this._data;
      const canEdit = manage && d3.can_edit;
      const full = this._scenes.length >= d3.limit;
      const favs = d3.favorites.map((id) => this._scene(id)).filter(Boolean);
      const rest = this._scenes.filter((s5) => !d3.favorites.includes(s5.id));
      const row = (s5) => b2`<div class="row ${this._selected === s5.id ? "selected" : ""}">
      ${s5.image_url ? b2`<img class="thumb" src=${s5.image_url} alt="" />` : b2`<span class="thumb">${PLACEHOLDER}</span>`}
      ${manage ? b2`<button class="name link" data-action="select" data-id=${s5.id} @click=${() => this._select(s5.id)}>${s5.name}</button>` : b2`<span class="name">${s5.name}</span>`}
      ${s5.kind === "installer" ? b2`<span class="badge">${this._t("installer")}</span>` : A}
      ${this._playButton(s5.entity_id, false, s5.name)}
    </div>`;
      return b2`
      ${canEdit ? b2`<button class="primary wide" data-action="new" ?disabled=${full} @click=${this._create}>
              + ${this._t("new_scene")}</button>
            ${full ? b2`<p class="muted">${this._t("err.limit_reached")} (${d3.limit})</p>` : A}` : A}
      ${manage && d3.manages_rights ? b2`<button class="wide" data-action="rights" @click=${this._openRights}>${this._t("rights")}</button>` : A}
      ${favs.length ? b2`<h3>${this._t("favorites")}</h3>${favs.map(row)}` : A}
      <h3>${this._t("scenes")}</h3>
      ${rest.length ? rest.map(row) : favs.length ? A : b2`<p class="muted">${this._t("empty")}</p>`}
      ${d3.foreign_scenes.length ? b2`<h3>${this._t("other_scenes")}</h3>
            ${d3.foreign_scenes.map(
        (s5) => b2`<div class="row"><span class="thumb">${PLACEHOLDER}</span>
                <span class="name">${this._name(s5.entity_id, s5.name)}${s5.knx ? b2`<span class="badge">KNX</span>` : A}</span>
                ${this._playButton(s5.entity_id, false, this._name(s5.entity_id, s5.name))}</div>`
      )}` : A}
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
      const s5 = this._detail;
      if (!s5) return A;
      const d3 = this._data;
      const slot = d3.favorites.indexOf(s5.id);
      return b2`${this._narrow ? b2`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : A}
      <div class="head">
        ${s5.image_url ? b2`<img class="hero" src=${s5.image_url} alt="" />` : A}
        <h2>${s5.name} ${s5.kind === "installer" ? b2`<span class="badge">${this._t("installer")}</span>` : A}</h2>
        ${this._playButton(s5.entity_id, true)}
        ${d3.can_edit ? b2`<button data-action="heart" aria-label=${this._t("favorites")} aria-pressed=${slot >= 0 ? "true" : "false"}
              @click=${() => this._slots = {}}>♥${slot >= 0 ? ` ${this._t("slot")} ${slot + 1}` : ""}</button>` : A}
        ${d3.can_edit && s5.editable ? b2`<button data-action="edit" @click=${() => this._openEditor(s5.id)}>${this._t("edit")}</button>` : A}
        ${d3.can_edit && s5.editable && s5.can_undo ? b2`<button data-action="undo" @click=${this._undo}>${this._t("undo")}</button>` : A}
      </div>
      ${this._detailError ? b2`<p class="error" role="alert">${this._detailError}</p>` : A}
      <p class="muted" role="status">${this._undone ? this._t("undone") : A}</p>
      ${s5.sequence.length ? b2`<h3>${this._t("order")}</h3>${s5.sequence.map((step, i7) => b2`<div class="row">${this._stepLine(step, i7 === s5.sequence.length - 1)}</div>`)}` : b2`<p class="muted">${this._t("no_steps")}</p>`}`;
    }
    _stepTitle(step) {
      const room = !this._house ? "" : `${step.area_id ? this._areaName(step.area_id) : this._t("no_room")} \u2013 `;
      return room + this._t(step.type === "scene" ? "scene" : step.domain);
    }
    // at most two lines per step: "Küche – Licht" over "Decke 60 %, Wand Aus + 3 weitere"; "+ 5 s" (spec 5.2)
    _stepLine(step, last = false) {
      if (step.type === "delay") {
        return b2`<span class="name">+ ${this._num(step.seconds)} s${last ? b2` <span class="muted">· ${this._t("no_effect")}</span>` : A}</span>`;
      }
      const issue = step.type === "scene" ? step.issue : step.entries.find((e5) => e5.issue)?.issue;
      const parts = step.type === "scene" ? [] : step.entries.map((e5) => `${this._name(e5.entity_id, e5.name)} ${this._summary(e5)}`);
      const values = parts.length ? b2`<span class="clip" data-fit .parts=${parts}></span><span class="more"></span>` : b2`<span class="clip">${step.type === "scene" ? step.name : "\u2013"}</span>`;
      return b2`<span class="name"><span class="line">${this._stepTitle(step)}</span>
      <span class="line">${values}${issue ? b2`<span class="badge warn">${this._t(issue)}</span>` : A}</span></span>`;
    }
    _summary(entry) {
      const pct = (v3) => `${Math.round(v3 * 100)} %`;
      if (entry.call) return this._t("call");
      if (entry.music === "off") return this._t("off");
      if (entry.music === "on") return `${this._t("on")} \xB7 ${pct(entry.volume)}`;
      if (entry.music === "favorite") return `${entry.favorite_name} \xB7 ${pct(entry.volume)}`;
      const a3 = entry.attributes ?? {};
      if (entry.state === "off") return this._t("off");
      if (entry.state === "closed") return this._t("closed");
      if (a3.brightness != null) {
        const color = a3.color_temp_kelvin ? ` \xB7 ${this._num(a3.color_temp_kelvin)} K` : "";
        return `${Math.round(a3.brightness / 2.55)} %${color}`;
      }
      if (a3.current_position != null) return `${a3.current_position} %`;
      if (a3.temperature != null) return `${this._state(entry.entity_id, entry.state)} \xB7 ${this._num(a3.temperature)} ${this._unit}`;
      if (a3.percentage != null) return `${a3.percentage} %`;
      return entry.state === "on" ? this._t("on") : this._state(entry.entity_id, entry.state);
    }
    // the name of a state in the language of the account, e.g. hvac mode "heat" (X8)
    _state(eid, state) {
      const st = this.hass.states[eid];
      try {
        const name = st && this.hass.formatEntityState?.(st, state);
        if (name) return name;
      } catch (err) {
      }
      const domain = eid.split(".")[0];
      return this.hass.localize?.(`component.${domain}.entity_component._.state.${state}`) || state;
    }
    get _unit() {
      return this.hass.config?.unit_system?.temperature ?? "\xB0C";
    }
    // ---------- favorite slots (spec 4.7, V2) ----------
    _renderSlots() {
      const d3 = this._data;
      const current = d3.favorites.indexOf(this._detail.id);
      const ask = this._slots.ask;
      return b2`<div class="overlay" @keydown=${this._dialogKey}><div class="dialog" role="dialog" aria-modal="true" aria-label=${this._t("favorites")}>
      ${ask != null ? b2`<p>${this._t("slot")} ${ask + 1}: ${this._scene(d3.favorites[ask])?.name} ${this._t("loses")}</p>
            <div class="actions">
              <button class="primary" data-action="slot-confirm" @click=${() => this._setFavorite(ask, true)}>${this._t("replace")}</button>
              <button data-action="slot-cancel" data-safe @click=${() => this._slots = {}}>${this._t("cancel")}</button></div>` : b2`<h3>${this._t("favorites")}</h3>
            ${d3.favorites.map(
        (id, i7) => b2`<button class="wide" data-action="slot" data-slot=${i7} aria-pressed=${i7 === current ? "true" : "false"}
                @click=${() => this._setFavorite(i7)}>${this._t("slot")} ${i7 + 1} – ${id ? this._scene(id)?.name ?? "" : this._t("free")}</button>`
      )}
            ${current >= 0 ? b2`<button class="wide" data-action="slot-clear" @click=${() => this._setFavorite(null)}>${this._t("no_slot")}</button>` : A}
            <button class="wide" data-action="slot-close" data-safe @click=${() => this._slots = null}>${this._t("close")}</button>`}
    </div></div>`;
    }
    async _setFavorite(slot, confirmed = false) {
      await this._load();
      const fav = this._data.favorites;
      const id = this._detail?.id;
      const current = fav.indexOf(id);
      const holder = slot == null ? null : fav[slot];
      if (holder && holder !== id && !confirmed) return this._slots = { ask: slot };
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
      return b2`${this._narrow ? b2`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : A}
      <h2>${this._t("rights")}</h2>
      ${this._rights.map(
        (a3) => b2`<div class="row">
          <span class="name">${a3.name} ${a3.kind === "panel" ? b2`<span class="badge">${this._t("panel")}</span>` : A}</span>
          ${this._switch("right", a3.can_edit, this._t("may_edit"), (on) => this._setRight(a3.user_id, on), a3.user_id)}
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
        this._undone = true;
        clearTimeout(this._undoneTimer);
        this._undoneTimer = setTimeout(() => this._undone = false, 4e3);
      } catch (err) {
        this._detailError = this._err(err.code);
      }
      await this._load();
    }
    // ---------- custom controls (spec 5.7, V10) ----------
    _switch(field, on, label, change, id) {
      return b2`<button class="switch" role="switch" aria-checked=${on ? "true" : "false"} data-field=${field}
      data-entity=${id ?? A} @click=${() => change(!on)}><span class="track"></span><span>${label}</span></button>`;
    }
    // the marked choice of an unticked device ticks it (spec 4.5, X7)
    _seg(field, eid, options, current, pick, ticked = true) {
      return b2`<div class="seg" role="radiogroup" data-field=${field} data-entity=${eid}>
      ${options.map(([value, label]) => b2`<button role="radio" aria-checked=${value === current ? "true" : "false"}
        data-value=${value} @click=${() => (value !== current || !ticked) && pick(value)}>${label}</button>`)}</div>`;
    }
    // ---------- editor: every input is stored at once (spec 4.5) ----------
    async _create() {
      const edit = newId();
      try {
        const res = await this.hass.callWS({
          type: `${WS}/create`,
          area_id: this._house ? null : this._config.area,
          name: this._t("new_scene"),
          edit
        });
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
        const r5 = await this.hass.callWS({ type: `${WS}/devices`, ...this._house ? {} : { area_id: this._config.area } });
        for (const dev of r5.entities) dev.label = this._name(dev.entity_id, dev.name);
        r5.entities.sort((a3, b3) => a3.label.localeCompare(b3.label));
        if (this._edit) this._setEdit({ devices: r5.entities, favorites: r5.favorites, images: r5.images, room_scenes: r5.room_scenes });
      } catch (err) {
      }
    }
    _setEdit(patch) {
      this._edit = { ...this._edit, ...patch };
    }
    // one input = one command; changes come back through the subscription
    async _send(type, fields = {}, at = "error") {
      const e5 = this._edit;
      this._setEdit({ error: null, nameError: null });
      try {
        return await this.hass.callWS({ type: `${WS}/${type}`, scene_id: e5.scene_id, edit: e5.id, ...fields });
      } catch (err) {
        const detail = /^\w+: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
        const named = /^[a-z_]+\.\S+$/.test(detail) ? this._name(detail) : detail;
        const caps = this._edit?.devices.find((d3) => d3.entity_id === fields.entity_id)?.capabilities ?? {};
        const range = err.code === "invalid_value" && detail === "temperature";
        if (this._edit) this._setEdit(range ? { [at]: "invalid_temperature", errorDetail: this._tempRange(caps) } : { [at]: err.code ?? "default", errorDetail: named });
        this._drafts.clear();
        await this._loadDetail();
        return void 0;
      }
    }
    async _done() {
      this._edit = null;
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
      const e5 = this._edit;
      const step = e5.open && this._detail.sequence.find((x2) => x2.id === e5.open);
      return b2`${this._offline ? b2`<p class="error" role="alert">${this._t("offline")}</p>` : A}
      <div class="editor" ?inert=${this._offline}>
        ${e5.error ? b2`<p class="error" role="alert">${this._err(e5.error, e5.errorDetail)}</p>` : A}
        ${step ? this._renderStep(step) : this._renderSequence()}
        <p class="sr" role="status">${this._announce ?? A}</p>
      </div>`;
    }
    _renderSequence() {
      const e5 = this._edit;
      const s5 = this._detail;
      const d3 = this._data;
      const own = s5.kind === "resident" || d3.is_admin;
      const trades = this._house ? DOMAINS.filter((t5) => t5 !== "scene" && e5.devices.some((dev) => dev.domain === t5 && dev.released !== false)) : [];
      return b2`<div class="bar">
        <button class="icon" data-action="done-back" aria-label=${this._t("back")} @click=${this._done}>‹</button>
        <span class="name">${s5.name}</span>
        <button class="primary" data-action="done" @click=${this._done}>${this._t("done")}</button>
      </div>
      ${own ? b2`<label class="field">${this._t("name")}
              <input data-field="name" data-key="name" maxlength=${d3.name_length} .value=${l3(this._draft("name", s5.name))}
                @input=${this._keep("name")} @keydown=${(ev) => ev.key === "Enter" && ev.target.blur()}
                @change=${(ev) => this._rename(ev.target.value)} />
              ${e5.nameError ? b2`<span class="error" role="alert">${this._err(e5.nameError)}</span>` : A}</label>
            ${this._renderImagePicker()}` : A}
      <label class="field">${this._t("transition")}
        <input type="number" min="0" max=${d3.max_transition} step="0.5" data-field="transition" data-key="transition"
          .value=${l3(String(this._draft("transition", s5.transition ?? "")))} @input=${this._keep("transition")}
          @change=${(ev) => this._send("update", { transition: ev.target.value === "" ? null : Number(ev.target.value) })} /></label>
      ${d3.is_admin ? b2`${this._switch(
        "kind",
        s5.kind === "installer",
        this._t("protected"),
        (on) => this._send("update", { kind: on ? "installer" : "resident" })
      )}
            ${s5.kind === "installer" ? this._switch("released", s5.content_released, this._t("released"), (on) => this._send("update", { content_released: on })) : A}` : A}
      ${trades.length ? b2`<h3>${this._t("all_house")}</h3>
            <div class="actions">${trades.map(
        (t5) => b2`<button data-action="house-off" data-domain=${t5} @click=${() => this._send("house_off", { domain: t5 })}>
                ${this._t(t5)} · ${this._t(t5 === "cover" ? "all_closed" : "all_off")}</button>`
      )}</div>` : A}
      <h3>${this._t("order")}</h3>
      ${s5.sequence.length ? c4(s5.sequence, (x2) => x2.id, (x2, i7) => this._renderStepRow(x2, i7, i7 === s5.sequence.length - 1)) : b2`<p class="muted">${this._t("no_steps")}</p>`}
      ${e5.adding ? this._renderAdd() : A}
      <div class="actions">
        <button data-action="add-step" @click=${() => this._setEdit({ adding: {} })}>+ ${this._t("add_step")}</button>
        <button data-action="add-delay" @click=${() => this._addStep({ step_type: "delay" })}>+ ${this._t("add_delay")}</button>
        <button data-action="duplicate" @click=${this._duplicate}>${this._t("duplicate")}</button>
        ${own ? b2`<button class="danger" data-action="ask-delete" @click=${() => this._setEdit({ confirmDelete: true })}>${this._t("delete")}</button>` : A}
      </div>`;
    }
    _renderStepRow(step, i7, last) {
      const remove = b2`<button class="icon" data-action="remove-step" data-id=${step.id} aria-label=${this._t("remove")}
      @click=${() => this._send("remove_step", { step_id: step.id })}>✕</button>`;
      const handle = b2`<span class="handle" role="button" tabindex="0" data-action="drag" data-id=${step.id}
      aria-label=${this._t("drag")} title=${this._t("drag")} @pointerdown=${(ev) => this._drag(ev, i7)}
      @keydown=${(ev) => this._dragKey(ev, step, i7)}>≡</span>`;
      const cls = `row order ${this._dragTo === i7 ? "drop" : ""}`;
      if (step.type === "delay") {
        const max = this._data.max_delay;
        const key = `delay:${step.id}`;
        const base = () => {
          const sent = this._delaySent?.[step.id];
          return sent && Date.now() - sent.at < 2e3 ? sent.seconds : step.seconds;
        };
        const set = (seconds) => {
          if (!(seconds >= 1 && seconds <= max)) return;
          (this._delaySent ??= {})[step.id] = { seconds, at: Date.now() };
          this._send("set_delay", { step_id: step.id, seconds });
        };
        return b2`<div class="${cls} delay-row">${handle}
        <div class="delay">
          <button class="icon" data-action="delay-minus" aria-label="−1 s" ?disabled=${base() <= 1}
            @click=${() => set(base() - 1)}>−</button>
          <label class="plain">+ <input class="secs" inputmode="numeric" pattern="[0-9]*" maxlength="3" data-field="delay"
            data-key=${key} aria-label=${this._t("seconds")} .value=${l3(String(this._draft(key, step.seconds)))}
            @input=${this._keep(key)} @change=${(ev) => this._typedDelay(key, ev.target.value, max, set)} /> s</label>
          <button class="icon" data-action="delay-plus" aria-label="+1 s" ?disabled=${base() >= max}
            @click=${() => set(base() + 1)}>+</button>
        </div>${remove}</div>${last ? b2`<p class="muted hint">${this._t("no_effect")}</p>` : A}`;
      }
      return b2`<div class=${cls}>${handle}${this._stepLine(step)}
      <div class="tools">
        ${step.type === "group" ? b2`<button data-action="open" data-id=${step.id} @click=${() => this._setEdit({ open: step.id, live: false })}>
              ${this._t("open")}</button>` : A}${remove}</div></div>`;
    }
    // whole seconds from 1 to the limit; anything else shows the stored value again and says why (spec 4.5, X4)
    _typedDelay(key, typed, max, set) {
      const seconds = /^\s*\d+\s*$/.test(typed) ? Number(typed) : NaN;
      if (seconds >= 1 && seconds <= max) return set(seconds);
      this._drafts.delete(key);
      this._setEdit({ error: "invalid_delay", errorDetail: `1\u2013${this._num(max)} s` });
    }
    async _dragKey(ev, step, i7) {
      const to = ev.key === "ArrowUp" ? i7 - 1 : ev.key === "ArrowDown" ? i7 + 1 : -1;
      if (to < 0 || to >= this._detail.sequence.length) return;
      ev.preventDefault();
      this._focusStep = { id: step.id, index: to };
      const count = this._detail.sequence.length;
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
      const move = (e5) => {
        const rows = [...this.renderRoot.querySelectorAll(".row.order")];
        const to = rows.findIndex((r5) => {
          const b3 = r5.getBoundingClientRect();
          return e5.clientY >= b3.top && e5.clientY < b3.bottom;
        });
        if (to >= 0 && to !== this._dragTo) this._dragTo = to, this.requestUpdate();
        const edge = e5.clientY < 48 ? -1 : e5.clientY > window.innerHeight - 48 ? 1 : 0;
        const next = Math.min(Math.max((to < 0 ? from : to) + edge, 0), rows.length - 1);
        if (edge) rows[next]?.scrollIntoView?.({ block: "nearest" });
      };
      const cancel = () => (this._dragTo = null, end());
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
      const e5 = this._edit;
      const a3 = e5.adding;
      const close = b2`<button data-action="add-cancel" @click=${() => this._setEdit({ adding: null })}>${this._t("cancel")}</button>`;
      if (this._house && a3.area === void 0) {
        const areas = [...new Set([...e5.devices.map((d3) => d3.area_id), ...e5.room_scenes.map((r5) => r5.area_id)].filter(Boolean))].sort((x2, y3) => this._areaName(x2).localeCompare(this._areaName(y3)));
        if (e5.devices.some((d3) => d3.area_id == null && d3.released !== false)) areas.push(null);
        return b2`<div class="pick"><h3>${this._t("pick_room")}</h3>
        ${areas.map((id) => b2`<button data-action="pick-room" data-id=${id ?? ""} @click=${() => this._setEdit({ adding: { area: id } })}>
          ${id ? this._areaName(id) : this._t("no_room")}</button>`)}${close}</div>`;
      }
      const area = this._house ? a3.area : this._config.area;
      const extra = this._house ? { area_id: area } : {};
      if (a3.scenes) {
        return b2`<div class="pick"><h3>${this._areaName(area)} – ${this._t("scene")}</h3>
        ${e5.room_scenes.filter((r5) => r5.area_id === area).map(
          (r5) => b2`<button data-action="pick-scene" data-id=${r5.id} @click=${() => this._addStep({ step_type: "scene", target: r5.id, ...extra })}>
            ${r5.name}</button>`
        )}${close}</div>`;
      }
      const domains = DOMAINS.filter((dm) => e5.devices.some((d3) => d3.domain === dm && d3.area_id === area && d3.released !== false));
      const roomScenes = this._house && e5.room_scenes.some((r5) => r5.area_id === area);
      return b2`<div class="pick"><h3>${this._house ? `${area ? this._areaName(area) : this._t("no_room")} \u2013 ` : ""}${this._t("pick_domain")}</h3>
      ${domains.map((dm) => b2`<button data-action="pick-domain" data-domain=${dm}
        @click=${() => this._addStep({ step_type: "group", domain: dm, ...extra })}>${this._t(dm === "scene" ? "other_scenes" : dm)}</button>`)}
      ${roomScenes ? b2`<button data-action="pick-domain" data-domain="room_scene" @click=${() => this._setEdit({ adding: { area, scenes: true } })}>
            ${this._t("scene")}</button>` : A}${close}</div>`;
    }
    // ---------- opened group step (spec 5.2, 5.4) ----------
    _renderStep(step) {
      const e5 = this._edit;
      const devs = e5.devices.filter((d3) => d3.domain === step.domain && d3.area_id === step.area_id && d3.released !== false);
      const gone = step.entries.filter((en) => !devs.some((d3) => d3.entity_id === en.entity_id)).map((en) => ({ entity_id: en.entity_id, label: this._name(en.entity_id, en.name), domain: step.domain, released: false, capabilities: {} }));
      const all = [...devs, ...gone];
      const set = (mode) => this._send("set_all", { step_id: step.id, mode, live: this._edit.live });
      return b2`<div class="bar">
        <button class="icon" data-action="close-step" aria-label=${this._t("back")} @click=${() => this._setEdit({ open: null })}>‹</button>
        <h3 class="name">${this._stepTitle(step)}</h3>
      </div>
      ${LIVE.includes(step.domain) ? this._switch("live", e5.live, this._t("live"), (on) => (this._setEdit({ live: on }), on && set("capture"))) : A}
      <div class="actions">
        <button data-action="all" @click=${() => set("capture")}>${this._t("all")}</button>
        <button data-action="all-off" @click=${() => set("off")}>${this._t(step.domain === "cover" ? "all_closed" : "all_off")}</button>
      </div>
      ${all.length ? c4(all, (d3) => d3.entity_id, (d3) => this._renderDevice(step, d3)) : b2`<p class="muted">${this._t("no_devices")}</p>`}`;
    }
    _renderDevice(step, dev) {
      const eid = dev.entity_id;
      const entry = step.entries.find((en) => en.entity_id === eid);
      const locked = dev.released === false || FLAGS.includes(entry?.issue);
      const st = this.hass.states[eid];
      const why = entry?.issue ?? (dev.released === false ? "not_released" : !st ? "missing" : !dev.available ? "unavailable" : "");
      const source = entry ?? (st && { entity_id: eid, state: st.state, attributes: st.attributes });
      const tick = () => entry ? this._send("remove_entry", { step_id: step.id, entity_id: eid }) : this._send("set_entry", { step_id: step.id, entity_id: eid, mode: "capture", live: this._edit.live });
      return b2`<div class="row device">
      <button class="check" role="checkbox" aria-checked=${entry ? "true" : "false"} data-field="pick" data-entity=${eid}
        aria-label=${dev.label} ?disabled=${locked && !entry} @click=${tick}></button>
      <span class="name">${dev.label} ${why ? b2`<span class="badge warn">${this._t(why)}</span>` : A}</span>
      ${locked || !source ? A : b2`<div class="controls">${this._renderValues(step, dev, entry, source)}</div>`}
    </div>`;
    }
    _valuesFromStep(step) {
      const a3 = step.attributes ?? {};
      const domain = step.entity_id.split(".")[0];
      if (domain === "light") {
        const v3 = { brightness: a3.brightness ?? 255 };
        if (a3.color_temp_kelvin && (a3.color_mode === "color_temp" || !a3.hs_color)) v3.color_temp_kelvin = a3.color_temp_kelvin;
        else if (a3.hs_color) Object.assign(v3, { hue: a3.hs_color[0], saturation: a3.hs_color[1] });
        return v3;
      }
      if (domain === "cover") return { position: a3.current_position ?? (step.state === "closed" ? 0 : 100), ...a3.current_tilt_position != null ? { tilt: a3.current_tilt_position } : {} };
      if (domain === "climate") return { hvac_mode: step.state, ...a3.temperature != null ? { temperature: a3.temperature } : {} };
      if (domain === "fan") return { percentage: a3.percentage ?? 50 };
      return {};
    }
    // an input on an unticked device ticks it: set_entry adds the entry (spec 4.5)
    _renderValues(step, dev, entry, source) {
      const c5 = dev.capabilities ?? {};
      const eid = dev.entity_id;
      const v3 = this._valuesFromStep(source);
      const on = !["off", "closed"].includes(source.state);
      const base = { step_id: step.id, entity_id: eid, live: this._edit.live };
      const set = (values) => this._send("set_entry", { ...base, mode: "set", values });
      const off = () => this._send("set_entry", { ...base, mode: "off" });
      const music = (m3, extra = {}) => this._send("set_entry", { ...base, mode: "music", music: m3, ...extra });
      const slider = (field, label, min, max, value, unit, apply) => {
        const key = `${field}:${step.id}:${eid}`;
        const shown = this._draft(key, value);
        return b2`<label class="slider"><span>${this._t(label)}</span><output>${this._num(shown)} ${unit}</output>
        <input type="range" min=${min} max=${max} data-field=${field} data-entity=${eid} data-key=${key}
          .value=${l3(String(shown))} @input=${this._keep(key)} @change=${(ev) => apply(Number(ev.target.value))} /></label>`;
      };
      const power = (send) => this._switch("on", on, this._t("on"), (o5) => o5 ? send() : off(), eid);
      if (dev.domain === "light") {
        const white = c5.color_temp && (!c5.color || v3.hue == null);
        const kelvin = v3.color_temp_kelvin ?? c5.min_kelvin ?? 2700;
        const colour = (patch) => set({ hue: v3.hue ?? 30, saturation: v3.saturation ?? 100, ...patch });
        const shown = !on || v3.color_temp_kelvin == null && v3.hue == null ? white ? { color_temp_kelvin: kelvin } : c5.color ? { hue: v3.hue ?? 30, saturation: v3.saturation ?? 100 } : {} : {};
        const keep = (values) => set({ ...shown, ...values });
        return b2`${power(() => keep({}))}
        ${c5.brightness ? slider(
          "brightness",
          "brightness",
          1,
          100,
          Math.round(v3.brightness / 2.55),
          "%",
          (p4) => keep({ brightness: Math.max(1, Math.round(p4 * 2.55)) })
        ) : A}
        ${c5.color_temp && c5.color ? this._seg(
          "light_mode",
          eid,
          [["white", this._t("white")], ["colour", this._t("colour")]],
          white ? "white" : "colour",
          (m3) => m3 === "white" ? set({ color_temp_kelvin: kelvin }) : colour({}),
          !!entry
        ) : A}
        ${white ? slider(
          "color_temp_kelvin",
          "color_temp",
          c5.min_kelvin ?? 2e3,
          c5.max_kelvin ?? 6500,
          kelvin,
          "K",
          (k2) => set({ color_temp_kelvin: k2 })
        ) : A}
        ${c5.color && !white ? b2`${slider("hue", "hue", 0, 360, v3.hue ?? 30, "\xB0", (h4) => colour({ hue: h4 }))}
              ${slider("saturation", "saturation", 0, 100, v3.saturation ?? 100, "%", (x2) => colour({ saturation: x2 }))}` : A}`;
      }
      if (dev.domain === "cover") {
        const send = (patch) => set({ ...c5.position ? { position: v3.position } : {}, ...c5.tilt ? { tilt: v3.tilt ?? 50 } : {}, ...patch });
        return b2`${c5.position ? slider("position", "position", 0, 100, v3.position, "%", (p4) => send({ position: p4 })) : A}
        ${c5.tilt ? slider("tilt", "tilt", 0, 100, v3.tilt ?? 50, "%", (p4) => send({ tilt: p4 })) : A}`;
      }
      if (dev.domain === "climate") {
        const key = `temperature:${step.id}:${eid}`;
        const send = (patch) => set({ hvac_mode: v3.hvac_mode, ...v3.temperature != null ? { temperature: v3.temperature } : {}, ...patch });
        const typed = (ev) => {
          const value = Number(ev.target.value.trim().replace(",", "."));
          if (ev.target.value.trim() && value >= (c5.min_temp ?? 5) && value <= (c5.max_temp ?? 35)) return send({ temperature: value });
          this._drafts.delete(key);
          this._setEdit({ error: "invalid_temperature", errorDetail: this._tempRange(c5) });
        };
        return b2`${this._seg(
          "hvac_mode",
          eid,
          (c5.hvac_modes ?? []).map((m3) => [m3, this._state(eid, m3)]),
          v3.hvac_mode,
          (m3) => send({ hvac_mode: m3 }),
          !!entry
        )}
        <label class="field">${this._t("temperature")} (${this._unit})<input inputmode="decimal" maxlength="5"
          data-field="temperature" data-entity=${eid} data-key=${key}
          .value=${l3(String(this._draft(key, v3.temperature != null ? this._num(v3.temperature) : "")))} @input=${this._keep(key)} @change=${typed} /></label>`;
      }
      if (dev.domain === "fan") {
        return b2`${power(() => set({ percentage: v3.percentage }))}
        ${slider("percentage", "percentage", 0, 100, v3.percentage, "%", (p4) => set({ percentage: p4 }))}`;
      }
      if (dev.domain === "switch") return power(() => set({ on: true }));
      if (dev.domain === "media_player") {
        const mode = entry ? entry.music : ["playing", "on"].includes(source.state) ? "on" : "off";
        const volume = entry?.volume ?? this.hass.states[eid]?.attributes.volume_level ?? 0.3;
        const favs = this._edit.favorites;
        const favorite = entry?.favorite_id ?? favs[0]?.id;
        const offer = dev.music_system && (favs.length > 0 || mode === "favorite");
        const modes = [["off", this._t("off")], ["on", this._t("on")], ...offer ? [["favorite", this._t("favorite")]] : []];
        const send = (m3, patch = {}) => music(m3, m3 === "off" ? {} : { volume, ...m3 === "favorite" ? { favorite_id: favorite } : {}, ...patch });
        const missing = entry?.issue === "favorite_missing";
        return b2`${this._seg("music", eid, modes, mode, (m3) => send(m3), !!entry)}
        ${dev.music_system && !offer ? b2`<p class="muted">${this._t("no_favorites")}</p>` : A}
        ${mode === "favorite" ? this._favoriteList(eid, favs, missing ? null : favorite, (id) => send("favorite", { favorite_id: id })) : A}
        ${mode !== "off" ? slider("volume", "volume", 0, 100, Math.round(volume * 100), "%", (p4) => send(mode, { volume: p4 / 100 })) : A}`;
      }
      return A;
    }
    // a list of the card, not the select of the browser (spec 5.7, Y5); it shows the stored favorite, so a refused choice reverts
    _favoriteList(eid, favs, current, pick) {
      const open = this._edit.favOpen === eid;
      const name = favs.find((f3) => f3.id === current)?.name ?? this._t("favorite_missing");
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
      return b2`<div class="favorites" data-field="favorite_id" data-entity=${eid} data-value=${current ?? ""}>
      <button class="choice" data-action="favorite-open" data-entity=${eid} aria-haspopup="listbox"
        aria-expanded=${open ? "true" : "false"} aria-label=${`${this._t("favorite")}: ${name}`} @click=${toggle}>${name} ▾</button>
      ${open ? b2`<div role="listbox" data-entity=${eid} aria-label=${this._t("favorite")} @keydown=${key}>
            ${favs.map((f3) => b2`<button role="option" aria-selected=${f3.id === current ? "true" : "false"} data-value=${f3.id}
              @click=${() => (close(true), f3.id !== current && pick(f3.id))}>${f3.name}</button>`)}</div>` : A}</div>`;
    }
    // ---------- image (spec 4.8, 5.6) ----------
    _renderImagePicker() {
      const e5 = this._edit;
      const s5 = this._detail;
      const crop = e5.crop;
      return b2`<div class="field"><span>${this._t("image")}</span>
      <button class="image-btn" data-action="image" @click=${() => this._setEdit({ picking: !e5.picking })}>
        ${s5.image_url ? b2`<img src=${s5.image_url} alt="" />` : b2`<span class="thumb">${PLACEHOLDER}</span>`}
        <span>${this._t("choose_image")}</span></button>
      ${e5.picking ? b2`<div class="tiles">
            <button class="tile" data-action="pick-image" data-name="" @click=${() => this._pickImage(null)}>
              <span>${this._t("no_image")}</span></button>
            ${e5.images.map((i7) => b2`<button class="tile" data-action="pick-image" data-name=${i7.name}
              aria-pressed=${i7.name === s5.image ? "true" : "false"} @click=${() => this._pickImage(i7.name)}>
              <img src=${i7.url} alt="" /><span>${i7.name}</span></button>`)}
            <button class="tile" data-action="upload" @click=${() => this.renderRoot.querySelector('[data-field="upload"]').click()}>
              <span>${this._t("own_image")}</span></button>
          </div>
          <input type="file" accept="image/*" hidden data-field="upload" @change=${(ev) => this._openCrop(ev.target.files?.[0])} />` : A}
      ${crop ? b2`<div class="crop">
            <canvas width=${TILE.w / 2} height=${TILE.h / 2}></canvas>
            <label class="slider"><span>${this._t("crop_x")}</span><input type="range" min="0" max="100" .value=${String(crop.x)}
              @input=${(ev) => this._moveCrop({ x: Number(ev.target.value) })} /></label>
            <label class="slider"><span>${this._t("crop_y")}</span><input type="range" min="0" max="100" .value=${String(crop.y)}
              @input=${(ev) => this._moveCrop({ y: Number(ev.target.value) })} /></label>
            <button class="primary" data-action="use-image" @click=${this._upload}>${this._t("use_image")}</button>
          </div>` : A}</div>`;
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
      const { img, x: x2, y: y3 } = this._edit.crop;
      const ratio = TILE.w / TILE.h;
      const sw = Math.min(img.naturalWidth, img.naturalHeight * ratio);
      const sh = sw / ratio;
      const sx = (img.naturalWidth - sw) * x2 / 100;
      const sy = (img.naturalHeight - sh) * y3 / 100;
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
        const detail = /: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
        this._setEdit({ crop: null, error: err.code ?? "invalid_image_file", errorDetail: detail });
      }
    }
    // ---------- delete (V13: a dialog over the card) ----------
    _renderConfirmDelete() {
      const used = this._detail.used_in ?? { scenes: [], slots: [] };
      const slots = used.slots.map((s5) => {
        const [scope, n4] = s5.split(":");
        return `${this._areaName(scope === HOUSE ? null : scope)} ${this._t("slot")} ${n4}`;
      });
      const all = [...used.scenes, ...slots];
      const question = this._t("confirm_delete").replace("{name}", this._detail.name);
      return b2`<div class="overlay" @keydown=${this._dialogKey}><div class="dialog" role="alertdialog" aria-modal="true" aria-label=${question}>${question}
      ${all.length ? b2`<br />${this._t("used_on")} ${all.join(", ")}` : A}
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
  };
  // what the user is typing or dragging, kept over updates from the server (spec 5.6)
  __publicField(ResidentScenesCard, "properties", {
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
    _announce: { state: true }
  });
  __publicField(ResidentScenesCard, "styles", i`
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
    .thumb { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; background: var(--secondary-background-color); flex: none;
      display: inline-flex; align-items: center; justify-content: center; color: var(--secondary-text-color); }
    .thumb svg { width: 24px; height: 24px; }
    .hero { width: 100%; aspect-ratio: 4 / 3; object-fit: contain; border-radius: 8px; }
    .head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; } .head h2 { flex: 1 1 100%; }
    .columns { display: grid; grid-template-columns: minmax(220px, 1fr) 2fr; gap: 24px; }
    .bar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; } .bar .name { flex: 1; min-width: 0; margin: 0; }
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
    .image-btn { display: flex; align-items: center; gap: 12px; padding: 4px 12px 4px 4px; align-self: flex-start; }
    .image-btn img { width: 64px; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 6px; }
    .crop canvas { width: 100%; max-width: 320px; aspect-ratio: 4 / 3; border-radius: 8px; background: var(--secondary-background-color); }
    .handle { cursor: grab; touch-action: none; user-select: none; min-width: 44px; min-height: 44px; display: flex;
      align-items: center; justify-content: center; font-size: 1.4em; color: var(--secondary-text-color); border-radius: 8px; }
    .row.drop { outline: 2px dashed var(--primary-color); }
    .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
    .tile { position: relative; aspect-ratio: 4 / 3; padding: 0; overflow: hidden; display: flex; align-items: flex-end; justify-content: center; }
    .tile img, .tile svg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
    .tile svg { padding: 25%; box-sizing: border-box; color: var(--secondary-text-color); }
    .tile span { position: relative; width: 100%; padding: 8px; background: rgba(0,0,0,.45); color: #fff; text-align: left; }
  `);
  customElements.define("resident-scenes-card", ResidentScenesCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "resident-scenes-card", name: "Resident Scenes", description: "Create, edit and run resident scenes" });
})();
