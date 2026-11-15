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
    constructor(t3, e4, o5) {
      if (this._$cssResult$ = true, o5 !== s) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
      this.cssText = t3, this.t = e4;
    }
    get styleSheet() {
      let t3 = this.o;
      const s4 = this.t;
      if (e && void 0 === t3) {
        const e4 = void 0 !== s4 && 1 === s4.length;
        e4 && (t3 = o.get(s4)), void 0 === t3 && ((this.o = t3 = new CSSStyleSheet()).replaceSync(this.cssText), e4 && o.set(s4, t3));
      }
      return t3;
    }
    toString() {
      return this.cssText;
    }
  };
  var r = (t3) => new n("string" == typeof t3 ? t3 : t3 + "", void 0, s);
  var i = (t3, ...e4) => {
    const o5 = 1 === t3.length ? t3[0] : e4.reduce((e5, s4, o6) => e5 + ((t4) => {
      if (true === t4._$cssResult$) return t4.cssText;
      if ("number" == typeof t4) return t4;
      throw Error("Value passed to 'css' function must be a 'css' function result: " + t4 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
    })(s4) + t3[o6 + 1], t3[0]);
    return new n(o5, t3, s);
  };
  var S = (s4, o5) => {
    if (e) s4.adoptedStyleSheets = o5.map((t3) => t3 instanceof CSSStyleSheet ? t3 : t3.styleSheet);
    else for (const e4 of o5) {
      const o6 = document.createElement("style"), n4 = t.litNonce;
      void 0 !== n4 && o6.setAttribute("nonce", n4), o6.textContent = e4.cssText, s4.appendChild(o6);
    }
  };
  var c = e ? (t3) => t3 : (t3) => t3 instanceof CSSStyleSheet ? ((t4) => {
    let e4 = "";
    for (const s4 of t4.cssRules) e4 += s4.cssText;
    return r(e4);
  })(t3) : t3;

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
  var d = (t3, s4) => t3;
  var u = { toAttribute(t3, s4) {
    switch (s4) {
      case Boolean:
        t3 = t3 ? l : null;
        break;
      case Object:
      case Array:
        t3 = null == t3 ? t3 : JSON.stringify(t3);
    }
    return t3;
  }, fromAttribute(t3, s4) {
    let i5 = t3;
    switch (s4) {
      case Boolean:
        i5 = null !== t3;
        break;
      case Number:
        i5 = null === t3 ? null : Number(t3);
        break;
      case Object:
      case Array:
        try {
          i5 = JSON.parse(t3);
        } catch (t4) {
          i5 = null;
        }
    }
    return i5;
  } };
  var f = (t3, s4) => !i2(t3, s4);
  var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
  Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), a.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
  var y = class extends HTMLElement {
    static addInitializer(t3) {
      this._$Ei(), (this.l ??= []).push(t3);
    }
    static get observedAttributes() {
      return this.finalize(), this._$Eh && [...this._$Eh.keys()];
    }
    static createProperty(t3, s4 = b) {
      if (s4.state && (s4.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t3) && ((s4 = Object.create(s4)).wrapped = true), this.elementProperties.set(t3, s4), !s4.noAccessor) {
        const i5 = /* @__PURE__ */ Symbol(), h3 = this.getPropertyDescriptor(t3, i5, s4);
        void 0 !== h3 && e2(this.prototype, t3, h3);
      }
    }
    static getPropertyDescriptor(t3, s4, i5) {
      const { get: e4, set: r4 } = h(this.prototype, t3) ?? { get() {
        return this[s4];
      }, set(t4) {
        this[s4] = t4;
      } };
      return { get: e4, set(s5) {
        const h3 = e4?.call(this);
        r4?.call(this, s5), this.requestUpdate(t3, h3, i5);
      }, configurable: true, enumerable: true };
    }
    static getPropertyOptions(t3) {
      return this.elementProperties.get(t3) ?? b;
    }
    static _$Ei() {
      if (this.hasOwnProperty(d("elementProperties"))) return;
      const t3 = n2(this);
      t3.finalize(), void 0 !== t3.l && (this.l = [...t3.l]), this.elementProperties = new Map(t3.elementProperties);
    }
    static finalize() {
      if (this.hasOwnProperty(d("finalized"))) return;
      if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
        const t4 = this.properties, s4 = [...r2(t4), ...o2(t4)];
        for (const i5 of s4) this.createProperty(i5, t4[i5]);
      }
      const t3 = this[Symbol.metadata];
      if (null !== t3) {
        const s4 = litPropertyMetadata.get(t3);
        if (void 0 !== s4) for (const [t4, i5] of s4) this.elementProperties.set(t4, i5);
      }
      this._$Eh = /* @__PURE__ */ new Map();
      for (const [t4, s4] of this.elementProperties) {
        const i5 = this._$Eu(t4, s4);
        void 0 !== i5 && this._$Eh.set(i5, t4);
      }
      this.elementStyles = this.finalizeStyles(this.styles);
    }
    static finalizeStyles(s4) {
      const i5 = [];
      if (Array.isArray(s4)) {
        const e4 = new Set(s4.flat(1 / 0).reverse());
        for (const s5 of e4) i5.unshift(c(s5));
      } else void 0 !== s4 && i5.push(c(s4));
      return i5;
    }
    static _$Eu(t3, s4) {
      const i5 = s4.attribute;
      return false === i5 ? void 0 : "string" == typeof i5 ? i5 : "string" == typeof t3 ? t3.toLowerCase() : void 0;
    }
    constructor() {
      super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
    }
    _$Ev() {
      this._$ES = new Promise((t3) => this.enableUpdating = t3), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t3) => t3(this));
    }
    addController(t3) {
      (this._$EO ??= /* @__PURE__ */ new Set()).add(t3), void 0 !== this.renderRoot && this.isConnected && t3.hostConnected?.();
    }
    removeController(t3) {
      this._$EO?.delete(t3);
    }
    _$E_() {
      const t3 = /* @__PURE__ */ new Map(), s4 = this.constructor.elementProperties;
      for (const i5 of s4.keys()) this.hasOwnProperty(i5) && (t3.set(i5, this[i5]), delete this[i5]);
      t3.size > 0 && (this._$Ep = t3);
    }
    createRenderRoot() {
      const t3 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
      return S(t3, this.constructor.elementStyles), t3;
    }
    connectedCallback() {
      this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach((t3) => t3.hostConnected?.());
    }
    enableUpdating(t3) {
    }
    disconnectedCallback() {
      this._$EO?.forEach((t3) => t3.hostDisconnected?.());
    }
    attributeChangedCallback(t3, s4, i5) {
      this._$AK(t3, i5);
    }
    _$ET(t3, s4) {
      const i5 = this.constructor.elementProperties.get(t3), e4 = this.constructor._$Eu(t3, i5);
      if (void 0 !== e4 && true === i5.reflect) {
        const h3 = (void 0 !== i5.converter?.toAttribute ? i5.converter : u).toAttribute(s4, i5.type);
        this._$Em = t3, null == h3 ? this.removeAttribute(e4) : this.setAttribute(e4, h3), this._$Em = null;
      }
    }
    _$AK(t3, s4) {
      const i5 = this.constructor, e4 = i5._$Eh.get(t3);
      if (void 0 !== e4 && this._$Em !== e4) {
        const t4 = i5.getPropertyOptions(e4), h3 = "function" == typeof t4.converter ? { fromAttribute: t4.converter } : void 0 !== t4.converter?.fromAttribute ? t4.converter : u;
        this._$Em = e4;
        const r4 = h3.fromAttribute(s4, t4.type);
        this[e4] = r4 ?? this._$Ej?.get(e4) ?? r4, this._$Em = null;
      }
    }
    requestUpdate(t3, s4, i5, e4 = false, h3) {
      if (void 0 !== t3) {
        const r4 = this.constructor;
        if (false === e4 && (h3 = this[t3]), i5 ??= r4.getPropertyOptions(t3), !((i5.hasChanged ?? f)(h3, s4) || i5.useDefault && i5.reflect && h3 === this._$Ej?.get(t3) && !this.hasAttribute(r4._$Eu(t3, i5)))) return;
        this.C(t3, s4, i5);
      }
      false === this.isUpdatePending && (this._$ES = this._$EP());
    }
    C(t3, s4, { useDefault: i5, reflect: e4, wrapped: h3 }, r4) {
      i5 && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t3) && (this._$Ej.set(t3, r4 ?? s4 ?? this[t3]), true !== h3 || void 0 !== r4) || (this._$AL.has(t3) || (this.hasUpdated || i5 || (s4 = void 0), this._$AL.set(t3, s4)), true === e4 && this._$Em !== t3 && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t3));
    }
    async _$EP() {
      this.isUpdatePending = true;
      try {
        await this._$ES;
      } catch (t4) {
        Promise.reject(t4);
      }
      const t3 = this.scheduleUpdate();
      return null != t3 && await t3, !this.isUpdatePending;
    }
    scheduleUpdate() {
      return this.performUpdate();
    }
    performUpdate() {
      if (!this.isUpdatePending) return;
      if (!this.hasUpdated) {
        if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
          for (const [t5, s5] of this._$Ep) this[t5] = s5;
          this._$Ep = void 0;
        }
        const t4 = this.constructor.elementProperties;
        if (t4.size > 0) for (const [s5, i5] of t4) {
          const { wrapped: t5 } = i5, e4 = this[s5];
          true !== t5 || this._$AL.has(s5) || void 0 === e4 || this.C(s5, void 0, i5, e4);
        }
      }
      let t3 = false;
      const s4 = this._$AL;
      try {
        t3 = this.shouldUpdate(s4), t3 ? (this.willUpdate(s4), this._$EO?.forEach((t4) => t4.hostUpdate?.()), this.update(s4)) : this._$EM();
      } catch (s5) {
        throw t3 = false, this._$EM(), s5;
      }
      t3 && this._$AE(s4);
    }
    willUpdate(t3) {
    }
    _$AE(t3) {
      this._$EO?.forEach((t4) => t4.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t3)), this.updated(t3);
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
    shouldUpdate(t3) {
      return true;
    }
    update(t3) {
      this._$Eq &&= this._$Eq.forEach((t4) => this._$ET(t4, this[t4])), this._$EM();
    }
    updated(t3) {
    }
    firstUpdated(t3) {
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
  var i3 = (t3) => t3;
  var s2 = t2.trustedTypes;
  var e3 = s2 ? s2.createPolicy("lit-html", { createHTML: (t3) => t3 }) : void 0;
  var h2 = "$lit$";
  var o3 = `lit$${Math.random().toFixed(9).slice(2)}$`;
  var n3 = "?" + o3;
  var r3 = `<${n3}>`;
  var l2 = document;
  var c3 = () => l2.createComment("");
  var a2 = (t3) => null === t3 || "object" != typeof t3 && "function" != typeof t3;
  var u2 = Array.isArray;
  var d2 = (t3) => u2(t3) || "function" == typeof t3?.[Symbol.iterator];
  var f2 = "[ 	\n\f\r]";
  var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
  var _ = /-->/g;
  var m = />/g;
  var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
  var g = /'/g;
  var $ = /"/g;
  var y2 = /^(?:script|style|textarea|title)$/i;
  var x = (t3) => (i5, ...s4) => ({ _$litType$: t3, strings: i5, values: s4 });
  var b2 = x(1);
  var w = x(2);
  var T = x(3);
  var E = /* @__PURE__ */ Symbol.for("lit-noChange");
  var A = /* @__PURE__ */ Symbol.for("lit-nothing");
  var C = /* @__PURE__ */ new WeakMap();
  var P = l2.createTreeWalker(l2, 129);
  function V(t3, i5) {
    if (!u2(t3) || !t3.hasOwnProperty("raw")) throw Error("invalid template strings array");
    return void 0 !== e3 ? e3.createHTML(i5) : i5;
  }
  var N = (t3, i5) => {
    const s4 = t3.length - 1, e4 = [];
    let n4, l3 = 2 === i5 ? "<svg>" : 3 === i5 ? "<math>" : "", c4 = v;
    for (let i6 = 0; i6 < s4; i6++) {
      const s5 = t3[i6];
      let a3, u3, d3 = -1, f3 = 0;
      for (; f3 < s5.length && (c4.lastIndex = f3, u3 = c4.exec(s5), null !== u3); ) f3 = c4.lastIndex, c4 === v ? "!--" === u3[1] ? c4 = _ : void 0 !== u3[1] ? c4 = m : void 0 !== u3[2] ? (y2.test(u3[2]) && (n4 = RegExp("</" + u3[2], "g")), c4 = p2) : void 0 !== u3[3] && (c4 = p2) : c4 === p2 ? ">" === u3[0] ? (c4 = n4 ?? v, d3 = -1) : void 0 === u3[1] ? d3 = -2 : (d3 = c4.lastIndex - u3[2].length, a3 = u3[1], c4 = void 0 === u3[3] ? p2 : '"' === u3[3] ? $ : g) : c4 === $ || c4 === g ? c4 = p2 : c4 === _ || c4 === m ? c4 = v : (c4 = p2, n4 = void 0);
      const x2 = c4 === p2 && t3[i6 + 1].startsWith("/>") ? " " : "";
      l3 += c4 === v ? s5 + r3 : d3 >= 0 ? (e4.push(a3), s5.slice(0, d3) + h2 + s5.slice(d3) + o3 + x2) : s5 + o3 + (-2 === d3 ? i6 : x2);
    }
    return [V(t3, l3 + (t3[s4] || "<?>") + (2 === i5 ? "</svg>" : 3 === i5 ? "</math>" : "")), e4];
  };
  var S2 = class _S {
    constructor({ strings: t3, _$litType$: i5 }, e4) {
      let r4;
      this.parts = [];
      let l3 = 0, a3 = 0;
      const u3 = t3.length - 1, d3 = this.parts, [f3, v2] = N(t3, i5);
      if (this.el = _S.createElement(f3, e4), P.currentNode = this.el.content, 2 === i5 || 3 === i5) {
        const t4 = this.el.content.firstChild;
        t4.replaceWith(...t4.childNodes);
      }
      for (; null !== (r4 = P.nextNode()) && d3.length < u3; ) {
        if (1 === r4.nodeType) {
          if (r4.hasAttributes()) for (const t4 of r4.getAttributeNames()) if (t4.endsWith(h2)) {
            const i6 = v2[a3++], s4 = r4.getAttribute(t4).split(o3), e5 = /([.?@])?(.*)/.exec(i6);
            d3.push({ type: 1, index: l3, name: e5[2], strings: s4, ctor: "." === e5[1] ? I : "?" === e5[1] ? L : "@" === e5[1] ? z : H }), r4.removeAttribute(t4);
          } else t4.startsWith(o3) && (d3.push({ type: 6, index: l3 }), r4.removeAttribute(t4));
          if (y2.test(r4.tagName)) {
            const t4 = r4.textContent.split(o3), i6 = t4.length - 1;
            if (i6 > 0) {
              r4.textContent = s2 ? s2.emptyScript : "";
              for (let s4 = 0; s4 < i6; s4++) r4.append(t4[s4], c3()), P.nextNode(), d3.push({ type: 2, index: ++l3 });
              r4.append(t4[i6], c3());
            }
          }
        } else if (8 === r4.nodeType) if (r4.data === n3) d3.push({ type: 2, index: l3 });
        else {
          let t4 = -1;
          for (; -1 !== (t4 = r4.data.indexOf(o3, t4 + 1)); ) d3.push({ type: 7, index: l3 }), t4 += o3.length - 1;
        }
        l3++;
      }
    }
    static createElement(t3, i5) {
      const s4 = l2.createElement("template");
      return s4.innerHTML = t3, s4;
    }
  };
  function M(t3, i5, s4 = t3, e4) {
    if (i5 === E) return i5;
    let h3 = void 0 !== e4 ? s4._$Co?.[e4] : s4._$Cl;
    const o5 = a2(i5) ? void 0 : i5._$litDirective$;
    return h3?.constructor !== o5 && (h3?._$AO?.(false), void 0 === o5 ? h3 = void 0 : (h3 = new o5(t3), h3._$AT(t3, s4, e4)), void 0 !== e4 ? (s4._$Co ??= [])[e4] = h3 : s4._$Cl = h3), void 0 !== h3 && (i5 = M(t3, h3._$AS(t3, i5.values), h3, e4)), i5;
  }
  var R = class {
    constructor(t3, i5) {
      this._$AV = [], this._$AN = void 0, this._$AD = t3, this._$AM = i5;
    }
    get parentNode() {
      return this._$AM.parentNode;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    u(t3) {
      const { el: { content: i5 }, parts: s4 } = this._$AD, e4 = (t3?.creationScope ?? l2).importNode(i5, true);
      P.currentNode = e4;
      let h3 = P.nextNode(), o5 = 0, n4 = 0, r4 = s4[0];
      for (; void 0 !== r4; ) {
        if (o5 === r4.index) {
          let i6;
          2 === r4.type ? i6 = new k(h3, h3.nextSibling, this, t3) : 1 === r4.type ? i6 = new r4.ctor(h3, r4.name, r4.strings, this, t3) : 6 === r4.type && (i6 = new Z(h3, this, t3)), this._$AV.push(i6), r4 = s4[++n4];
        }
        o5 !== r4?.index && (h3 = P.nextNode(), o5++);
      }
      return P.currentNode = l2, e4;
    }
    p(t3) {
      let i5 = 0;
      for (const s4 of this._$AV) void 0 !== s4 && (void 0 !== s4.strings ? (s4._$AI(t3, s4, i5), i5 += s4.strings.length - 2) : s4._$AI(t3[i5])), i5++;
    }
  };
  var k = class _k {
    get _$AU() {
      return this._$AM?._$AU ?? this._$Cv;
    }
    constructor(t3, i5, s4, e4) {
      this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t3, this._$AB = i5, this._$AM = s4, this.options = e4, this._$Cv = e4?.isConnected ?? true;
    }
    get parentNode() {
      let t3 = this._$AA.parentNode;
      const i5 = this._$AM;
      return void 0 !== i5 && 11 === t3?.nodeType && (t3 = i5.parentNode), t3;
    }
    get startNode() {
      return this._$AA;
    }
    get endNode() {
      return this._$AB;
    }
    _$AI(t3, i5 = this) {
      t3 = M(this, t3, i5), a2(t3) ? t3 === A || null == t3 || "" === t3 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t3 !== this._$AH && t3 !== E && this._(t3) : void 0 !== t3._$litType$ ? this.$(t3) : void 0 !== t3.nodeType ? this.T(t3) : d2(t3) ? this.k(t3) : this._(t3);
    }
    O(t3) {
      return this._$AA.parentNode.insertBefore(t3, this._$AB);
    }
    T(t3) {
      this._$AH !== t3 && (this._$AR(), this._$AH = this.O(t3));
    }
    _(t3) {
      this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t3 : this.T(l2.createTextNode(t3)), this._$AH = t3;
    }
    $(t3) {
      const { values: i5, _$litType$: s4 } = t3, e4 = "number" == typeof s4 ? this._$AC(t3) : (void 0 === s4.el && (s4.el = S2.createElement(V(s4.h, s4.h[0]), this.options)), s4);
      if (this._$AH?._$AD === e4) this._$AH.p(i5);
      else {
        const t4 = new R(e4, this), s5 = t4.u(this.options);
        t4.p(i5), this.T(s5), this._$AH = t4;
      }
    }
    _$AC(t3) {
      let i5 = C.get(t3.strings);
      return void 0 === i5 && C.set(t3.strings, i5 = new S2(t3)), i5;
    }
    k(t3) {
      u2(this._$AH) || (this._$AH = [], this._$AR());
      const i5 = this._$AH;
      let s4, e4 = 0;
      for (const h3 of t3) e4 === i5.length ? i5.push(s4 = new _k(this.O(c3()), this.O(c3()), this, this.options)) : s4 = i5[e4], s4._$AI(h3), e4++;
      e4 < i5.length && (this._$AR(s4 && s4._$AB.nextSibling, e4), i5.length = e4);
    }
    _$AR(t3 = this._$AA.nextSibling, s4) {
      for (this._$AP?.(false, true, s4); t3 !== this._$AB; ) {
        const s5 = i3(t3).nextSibling;
        i3(t3).remove(), t3 = s5;
      }
    }
    setConnected(t3) {
      void 0 === this._$AM && (this._$Cv = t3, this._$AP?.(t3));
    }
  };
  var H = class {
    get tagName() {
      return this.element.tagName;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    constructor(t3, i5, s4, e4, h3) {
      this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t3, this.name = i5, this._$AM = e4, this.options = h3, s4.length > 2 || "" !== s4[0] || "" !== s4[1] ? (this._$AH = Array(s4.length - 1).fill(new String()), this.strings = s4) : this._$AH = A;
    }
    _$AI(t3, i5 = this, s4, e4) {
      const h3 = this.strings;
      let o5 = false;
      if (void 0 === h3) t3 = M(this, t3, i5, 0), o5 = !a2(t3) || t3 !== this._$AH && t3 !== E, o5 && (this._$AH = t3);
      else {
        const e5 = t3;
        let n4, r4;
        for (t3 = h3[0], n4 = 0; n4 < h3.length - 1; n4++) r4 = M(this, e5[s4 + n4], i5, n4), r4 === E && (r4 = this._$AH[n4]), o5 ||= !a2(r4) || r4 !== this._$AH[n4], r4 === A ? t3 = A : t3 !== A && (t3 += (r4 ?? "") + h3[n4 + 1]), this._$AH[n4] = r4;
      }
      o5 && !e4 && this.j(t3);
    }
    j(t3) {
      t3 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t3 ?? "");
    }
  };
  var I = class extends H {
    constructor() {
      super(...arguments), this.type = 3;
    }
    j(t3) {
      this.element[this.name] = t3 === A ? void 0 : t3;
    }
  };
  var L = class extends H {
    constructor() {
      super(...arguments), this.type = 4;
    }
    j(t3) {
      this.element.toggleAttribute(this.name, !!t3 && t3 !== A);
    }
  };
  var z = class extends H {
    constructor(t3, i5, s4, e4, h3) {
      super(t3, i5, s4, e4, h3), this.type = 5;
    }
    _$AI(t3, i5 = this) {
      if ((t3 = M(this, t3, i5, 0) ?? A) === E) return;
      const s4 = this._$AH, e4 = t3 === A && s4 !== A || t3.capture !== s4.capture || t3.once !== s4.once || t3.passive !== s4.passive, h3 = t3 !== A && (s4 === A || e4);
      e4 && this.element.removeEventListener(this.name, this, s4), h3 && this.element.addEventListener(this.name, this, t3), this._$AH = t3;
    }
    handleEvent(t3) {
      "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t3) : this._$AH.handleEvent(t3);
    }
  };
  var Z = class {
    constructor(t3, i5, s4) {
      this.element = t3, this.type = 6, this._$AN = void 0, this._$AM = i5, this.options = s4;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(t3) {
      M(this, t3);
    }
  };
  var B = t2.litHtmlPolyfillSupport;
  B?.(S2, k), (t2.litHtmlVersions ??= []).push("3.3.3");
  var D = (t3, i5, s4) => {
    const e4 = s4?.renderBefore ?? i5;
    let h3 = e4._$litPart$;
    if (void 0 === h3) {
      const t4 = s4?.renderBefore ?? null;
      e4._$litPart$ = h3 = new k(i5.insertBefore(c3(), t4), t4, void 0, s4 ?? {});
    }
    return h3._$AI(t3), h3;
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
      const t3 = super.createRenderRoot();
      return this.renderOptions.renderBefore ??= t3.firstChild, t3;
    }
    update(t3) {
      const r4 = this.render();
      this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t3), this._$Do = D(r4, this.renderRoot, this.renderOptions);
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

  // src/resident-scenes-card.js
  var VERSION = "0.2.0";
  var WS = "resident_scenes";
  var HOUSE = "_house";
  var DOMAINS = ["light", "cover", "climate", "switch", "fan", "media_player", "scene"];
  var VISIBLE_RELOAD = 5 * 60 * 1e3;
  var I18N = {
    en: {
      new_scene: "New scene",
      scenes: "Scenes",
      other_scenes: "Other scenes",
      favorites: "Favorites",
      play: "Play",
      edit: "Edit",
      save: "Save",
      cancel: "Cancel",
      delete: "Delete",
      duplicate: "Duplicate",
      back: "Back",
      name: "Name",
      image: "Image",
      no_image: "No image",
      all: "All",
      none: "\u2013",
      slot: "Slot",
      keep: "Stored value",
      capture: "Current state",
      off: "Off",
      closed: "Closed",
      set: "Set value",
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
      no_devices: "No released devices.",
      confirm_delete: "Delete this scene for good?",
      used_on: "Used by:",
      outside_note: "Automations and schedules using it will stop working.",
      yes: "Delete",
      no: "Keep",
      conflict: "Someone else changed this scene meanwhile.",
      load_new: "Load new version",
      save_copy: "Save mine as copy",
      copy: "copy",
      reload: "A new version is installed. Please reload.",
      reload_btn: "Reload",
      house: "House",
      installer: "Installer",
      released: "Content released to residents",
      kind: "Kind",
      resident: "Resident scene",
      brightness: "Brightness",
      color_temp: "Colour temperature",
      hue: "Colour",
      position: "Position",
      tilt: "Tilt",
      temperature: "Temperature",
      mode: "Mode",
      delay: "Delay (s)",
      transition: "Transition (s)",
      order: "Sequence",
      up: "Move up",
      down: "Move down",
      preview: "Live preview",
      undo: "Undo last change",
      rights: "Permissions",
      may_edit: "may change scenes",
      panel: "Panel",
      own_image: "Own image",
      crop: "Section",
      crop_x: "Horizontal",
      crop_y: "Vertical",
      use_image: "Use image",
      room_scene: "Room scene",
      remove: "Remove",
      stale: "Not up to date, retrying \u2026",
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
        too_many_steps: "Too many devices.",
        entity_not_allowed: "Not released for this scene:",
        entity_unavailable: "Not reachable, its state cannot be captured:",
        unknown_favorite: "This favorite no longer exists.",
        not_found: "The scene no longer exists.",
        invalid_step: "Invalid setting.",
        invalid_value: "Value out of range:",
        invalid_delay: "Delay too long:",
        favorite_not_supported: "Favorites only work on players of the music system:",
        invalid_scene_call: "This scene cannot be called.",
        duplicate_entity: "Device used twice:",
        protected: "Installer scene: only its released content can be changed.",
        invalid_image: "Image not found.",
        invalid_image_file: "This is not an image file.",
        image_too_large: "Image too large, limit:",
        image_limit: "Image limit reached:",
        nothing_to_undo: "Nothing to undo.",
        default: "Saving failed."
      }
    },
    de: {
      new_scene: "Neue Szene",
      scenes: "Szenen",
      other_scenes: "Weitere Szenen",
      favorites: "Favoriten",
      play: "Abspielen",
      edit: "\xC4ndern",
      save: "Speichern",
      cancel: "Abbrechen",
      delete: "L\xF6schen",
      duplicate: "Duplizieren",
      back: "Zur\xFCck",
      name: "Name",
      image: "Bild",
      no_image: "Kein Bild",
      all: "Alle",
      none: "\u2013",
      slot: "Platz",
      keep: "Gespeicherter Wert",
      capture: "Aktueller Zustand",
      off: "Aus",
      closed: "Zu",
      set: "Wert setzen",
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
      no_devices: "Keine freigegebenen Ger\xE4te.",
      confirm_delete: "Diese Szene endg\xFCltig l\xF6schen?",
      used_on: "Verwendet in:",
      outside_note: "Automationen und Zeitpl\xE4ne damit wirken nicht mehr.",
      yes: "L\xF6schen",
      no: "Behalten",
      conflict: "Jemand anderes hat die Szene inzwischen ge\xE4ndert.",
      load_new: "Neuen Stand laden",
      save_copy: "Meine Fassung als Kopie sichern",
      copy: "Kopie",
      reload: "Eine neue Version ist installiert. Bitte neu laden.",
      reload_btn: "Neu laden",
      house: "Haus",
      installer: "Errichter",
      released: "Inhalt f\xFCr Bewohner freigegeben",
      kind: "Art",
      resident: "Kundenszene",
      brightness: "Helligkeit",
      color_temp: "Farbtemperatur",
      hue: "Farbe",
      position: "Position",
      tilt: "Neigung",
      temperature: "Temperatur",
      mode: "Betriebsart",
      delay: "Verz\xF6gerung (s)",
      transition: "\xDCbergang (s)",
      order: "Ablauf",
      up: "Nach oben",
      down: "Nach unten",
      preview: "Live-Vorschau",
      undo: "Letzte \xC4nderung zur\xFCcknehmen",
      rights: "Berechtigungen",
      may_edit: "darf Szenen \xE4ndern",
      panel: "Panel",
      own_image: "Eigenes Bild",
      crop: "Ausschnitt",
      crop_x: "Waagerecht",
      crop_y: "Senkrecht",
      use_image: "Bild \xFCbernehmen",
      room_scene: "Raumszene",
      remove: "Entfernen",
      stale: "Nicht aktuell, neuer Versuch l\xE4uft \u2026",
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
        too_many_steps: "Zu viele Ger\xE4te.",
        entity_not_allowed: "F\xFCr diese Szene nicht freigegeben:",
        entity_unavailable: "Nicht erreichbar, der Zustand l\xE4sst sich nicht \xFCbernehmen:",
        unknown_favorite: "Diesen Favoriten gibt es nicht mehr.",
        not_found: "Die Szene gibt es nicht mehr.",
        invalid_step: "Ung\xFCltige Einstellung.",
        invalid_value: "Wert au\xDFerhalb des Bereichs:",
        invalid_delay: "Verz\xF6gerung zu lang:",
        favorite_not_supported: "Favoriten nur f\xFCr Player des Musiksystems:",
        invalid_scene_call: "Diese Szene l\xE4sst sich nicht aufrufen.",
        duplicate_entity: "Ger\xE4t doppelt:",
        protected: "Errichterszene: nur der freigegebene Inhalt l\xE4sst sich \xE4ndern.",
        invalid_image: "Bild nicht gefunden.",
        invalid_image_file: "Das ist keine Bilddatei.",
        image_too_large: "Bild zu gro\xDF, Grenze:",
        image_limit: "H\xF6chstzahl an Bildern erreicht:",
        nothing_to_undo: "Nichts zur\xFCckzunehmen.",
        default: "Speichern fehlgeschlagen."
      }
    }
  };
  var TILE = { w: 640, h: 480 };
  var ResidentScenesCard = class extends i4 {
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
      this._ro = new ResizeObserver(([entry]) => this._narrow = entry.contentRect.width < 600);
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
      this._onReady ??= () => (this._needSub = true, this._load());
      this._onVisible ??= () => document.visibilityState === "visible" && Date.now() - (this._loadedAt ?? 0) > VISIBLE_RELOAD && this._load();
      this.hass.connection.addEventListener?.("ready", this._onReady);
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
    _t(key) {
      const lang = this.hass?.locale?.language?.startsWith("de") ? "de" : "en";
      return key.split(".").reduce((o5, k2) => o5?.[k2], I18N[lang]) ?? key;
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
        this._endPreview(true);
        this._edit = null;
        this._notice = "rights_gone";
      }
      if (this._rights && this._data.manages_rights) this._loadRights();
      if (!this._data.manages_rights) this._rights = null;
      if (fromServer && this._edit) return;
      if (this._selected) await this._loadDetail();
    }
    async _loadDetail() {
      try {
        this._detail = await this.hass.callWS({ type: `${WS}/scene`, scene_id: this._selected });
      } catch (err) {
        if (err.code === "not_found") this._selected = null, this._detail = null;
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
      return this._data?.scenes.find((s4) => s4.id === id);
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
      ${this._stale && this._data ? b2`<p class="muted" role="status">${this._t("stale")}</p>` : A}
      ${this._notice ? b2`<p class="error" role="alert">${this._t(this._notice)}</p>` : A} ${body}
    </div>`;
    }
    _renderFavorites() {
      const tiles = this._data.favorites.map((id) => this._scene(id)).filter(Boolean);
      if (!tiles.length) return A;
      return b2`<div class="tiles">
      ${tiles.map(
        (s4) => b2`<button class="tile" data-action="play" aria-label=${s4.name} @click=${() => this._play(s4.entity_id)}>
          ${s4.image_url ? b2`<img src=${s4.image_url} alt="" />` : A}<span>${s4.name}</span>
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
      return b2`<div class="columns"><div class="col-list">${list}</div><div class="col-detail">${detail}</div></div>`;
    }
    _renderList() {
      const manage = this._config.view === "manage";
      const d3 = this._data;
      const canEdit = manage && d3.can_edit;
      const full = this._scenes.length >= d3.limit;
      const play = (eid) => b2`<button class="icon" data-action="play" aria-label=${this._t("play")}
      @click=${() => this._play(eid)}>▶</button>`;
      return b2`
      ${canEdit ? b2`<button class="primary wide" data-action="new" ?disabled=${full} @click=${() => this._openEditor(null)}>
              + ${this._t("new_scene")}</button>
            ${full ? b2`<p class="muted">${this._t("err.limit_reached")} (${d3.limit})</p>` : A}` : A}
      ${manage && d3.manages_rights ? b2`<button class="wide" data-action="rights" @click=${this._openRights}>${this._t("rights")}</button>` : A}
      <h3>${this._t("scenes")}</h3>
      ${this._scenes.length ? this._scenes.map(
        (s4) => b2`<div class="row ${this._selected === s4.id ? "selected" : ""}">
              ${s4.image_url ? b2`<img class="thumb" src=${s4.image_url} alt="" />` : b2`<span class="thumb"></span>`}
              ${manage ? b2`<button class="name link" data-action="select" data-id=${s4.id} @click=${() => this._select(s4.id)}>
                    ${s4.name}</button>` : b2`<span class="name">${s4.name}</span>`}
              ${s4.kind === "installer" ? b2`<span class="badge">${this._t("installer")}</span>` : A}
              ${play(s4.entity_id)}
            </div>`
      ) : b2`<p class="muted">${this._t("empty")}</p>`}
      ${d3.foreign_scenes.length ? b2`<h3>${this._t("other_scenes")}</h3>
            ${d3.foreign_scenes.map(
        (s4) => b2`<div class="row"><span class="thumb"></span>
                <span class="name">${this._name(s4.entity_id, s4.name)}${s4.knx ? b2`<span class="badge">KNX</span>` : A}</span>
                ${play(s4.entity_id)}</div>`
      )}` : A}
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
      const s4 = this._detail;
      if (!s4) return A;
      const d3 = this._data;
      const slot = d3.favorites.indexOf(s4.id);
      return b2`${this._narrow ? b2`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : A}
      <div class="head">
        ${s4.image_url ? b2`<img class="hero" src=${s4.image_url} alt="" />` : A}
        <h2>${s4.name} ${s4.kind === "installer" ? b2`<span class="badge">${this._t("installer")}</span>` : A}</h2>
        <button class="primary" data-action="play" @click=${() => this._play(s4.entity_id)}>▶ ${this._t("play")}</button>
        ${d3.can_edit ? b2`<label class="heart">♥
              <select data-field="favorite" aria-label=${this._t("favorites")} @change=${(e4) => this._setFavorite(e4.target.value)}>
                <option value="">${this._t("none")}</option>
                ${d3.favorites.map(
        (_2, i5) => b2`<option value=${i5} ?selected=${i5 === slot}>${this._t("slot")} ${i5 + 1}</option>`
      )}
              </select></label>` : A}
        ${d3.can_edit && s4.editable ? b2`<button data-action="edit" @click=${() => this._openEditor(s4)}>${this._t("edit")}</button>` : A}
        ${d3.can_edit && s4.editable && s4.can_undo ? b2`<button data-action="undo" @click=${this._undo}>${this._t("undo")}</button>` : A}
      </div>
      ${this._detailError ? b2`<p class="error" role="alert">${this._detailError}</p>` : A}
      ${this._renderSteps(s4.steps)}`;
    }
    _groupOf(step) {
      if (step.scene_id) return this._t("scene");
      return this._house ? this._areaName(this._entityArea(step.entity_id)) : this._t(step.entity_id.split(".")[0]);
    }
    _renderSteps(steps) {
      const groups = /* @__PURE__ */ new Map();
      for (const step of steps) {
        const key = this._groupOf(step);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(step);
      }
      return [...groups].map(
        ([title, items]) => b2`<h3>${title}</h3>
        ${items.map(
          (step) => b2`<div class="row">
            <span class="name">${step.scene_id ? step.name : this._name(step.entity_id, step.name)}
              ${step.issue ? b2`<span class="badge warn">${this._t(step.issue)}</span>` : A}</span>
            <span class="muted">${this._summary(step)}${step.delay ? ` \xB7 +${step.delay} s` : ""}</span>
          </div>`
        )}`
      );
    }
    _summary(step) {
      const pct = (v2) => `${Math.round(v2 * 100)} %`;
      if (step.scene_id || step.call) return this._t("call");
      if (step.music === "off") return this._t("off");
      if (step.music === "on") return `${this._t("on")} \xB7 ${pct(step.volume)}`;
      if (step.music === "favorite") return `${step.favorite_name} \xB7 ${pct(step.volume)}`;
      const a3 = step.attributes ?? {};
      if (step.state === "off") return this._t("off");
      if (step.state === "closed") return this._t("closed");
      if (a3.brightness != null) {
        const color = a3.color_temp_kelvin ? ` \xB7 ${a3.color_temp_kelvin} K` : "";
        return `${this._t("on")} \xB7 ${Math.round(a3.brightness / 2.55)} %${color}`;
      }
      if (a3.current_position != null) return `${a3.current_position} %`;
      if (a3.temperature != null) return `${step.state} \xB7 ${a3.temperature} \xB0`;
      if (a3.percentage != null) return `${this._t("on")} \xB7 ${a3.percentage} %`;
      return step.state === "on" ? this._t("on") : step.state;
    }
    // ---------- rights (spec 3) ----------
    async _openRights() {
      this._selected = null;
      this._detail = null;
      await this._loadRights();
    }
    _renderRights() {
      return b2`${this._narrow ? b2`<button data-action="back" @click=${this._back}>‹ ${this._t("back")}</button>` : A}
      <h2>${this._t("rights")}</h2>
      ${this._rights.map(
        (a3) => b2`<label class="row">
          <span class="name">${a3.name} ${a3.kind === "panel" ? b2`<span class="badge">${this._t("panel")}</span>` : A}</span>
          <span class="muted">${this._t("may_edit")}</span>
          <input type="checkbox" class="switch" data-field="right" data-id=${a3.user_id} .checked=${a3.can_edit}
            @change=${(e4) => this._setRight(a3.user_id, e4.target.checked)} />
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
        await this._load();
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
        result = await this.hass.callWS({ type: `${WS}/devices`, ...this._house ? {} : { area_id: this._config.area } });
      } catch (err) {
        return;
      }
      const devices = result.entities;
      const steps = /* @__PURE__ */ new Map();
      for (const step of scene?.steps ?? []) {
        if (step.scene_id) {
          steps.set(`scene:${step.scene_id}`, {
            choice: "scene",
            scene_id: step.scene_id,
            name: step.name,
            area_id: result.room_scenes.find((r4) => r4.id === step.scene_id)?.area_id,
            issue: step.issue,
            delay: step.delay ?? 0
          });
          continue;
        }
        const s4 = { choice: "keep", stored: step, issue: step.issue, delay: step.delay ?? 0, values: this._valuesFromStep(step) };
        if (step.music && step.music !== "off") Object.assign(s4, { volume: step.volume, favorite_id: step.favorite_id });
        steps.set(step.entity_id, s4);
        if (!devices.some((d3) => d3.entity_id === step.entity_id)) {
          devices.push({
            entity_id: step.entity_id,
            name: this._name(step.entity_id, step.name),
            domain: step.entity_id.split(".")[0],
            area_id: this._entityArea(step.entity_id),
            available: false,
            released: false,
            capabilities: {}
          });
        }
      }
      for (const dev of devices) dev.label = this._name(dev.entity_id, dev.name);
      devices.sort((a3, b3) => a3.label.localeCompare(b3.label));
      this._edit = {
        scene_id: scene?.id,
        version: scene?.version,
        name: scene?.name ?? "",
        image: scene?.image ?? null,
        imageUrl: scene?.image_url ?? null,
        kind: scene?.kind ?? "resident",
        content_released: scene?.content_released ?? false,
        transition: scene?.transition ?? null,
        steps,
        devices,
        favorites: result.favorites,
        images: result.images,
        room_scenes: result.room_scenes,
        preview: !this._house
        // spec 5.4: on for room scenes, off for house scenes
      };
    }
    _valuesFromStep(step) {
      const a3 = step.attributes ?? {};
      const domain = step.entity_id.split(".")[0];
      if (domain === "light") {
        const v2 = { brightness: a3.brightness ?? 255 };
        if (a3.color_temp_kelvin) v2.color_temp_kelvin = a3.color_temp_kelvin;
        if (a3.hs_color) Object.assign(v2, { hue: a3.hs_color[0], saturation: a3.hs_color[1] });
        return v2;
      }
      if (domain === "cover") return { position: a3.current_position ?? (step.state === "closed" ? 0 : 100), ...a3.current_tilt_position != null ? { tilt: a3.current_tilt_position } : {} };
      if (domain === "climate") return { hvac_mode: step.state, ...a3.temperature != null ? { temperature: a3.temperature } : {} };
      if (domain === "fan") return { percentage: a3.percentage ?? 50 };
      if (domain === "switch") return { on: step.state === "on" };
      return {};
    }
    _valuesFromState(dev) {
      const st = this.hass.states[dev.entity_id];
      if (!st) return {};
      return this._valuesFromStep({ entity_id: dev.entity_id, state: st.state, attributes: st.attributes });
    }
    _canSet(dev) {
      const c4 = dev.capabilities ?? {};
      if (dev.domain === "light") return c4.brightness || c4.color_temp || c4.color;
      if (dev.domain === "cover") return c4.position || c4.tilt;
      if (dev.domain === "climate") return (c4.hvac_modes ?? []).length > 0;
      return dev.domain === "fan" || dev.domain === "switch";
    }
    _groupKey(dev) {
      return this._house ? dev.area_id ?? "" : dev.domain;
    }
    _renderEditor() {
      const e4 = this._edit;
      const d3 = this._data;
      const groups = /* @__PURE__ */ new Map();
      for (const dev of e4.devices.filter((x2) => x2.domain !== "scene")) {
        const key = this._groupKey(dev);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(dev);
      }
      const order = [...groups.keys()].sort(
        (a3, b3) => this._house ? this._areaName(a3).localeCompare(this._areaName(b3)) : DOMAINS.indexOf(a3) - DOMAINS.indexOf(b3)
      );
      const trades = this._house ? DOMAINS.filter((t3) => t3 !== "scene" && e4.devices.some((dev) => dev.domain === t3 && dev.released !== false)) : [];
      return b2`<div class="editor">
      <label>${this._t("name")}<input data-field="name" maxlength=${d3.name_length} .value=${e4.name}
        @input=${(ev) => e4.name = ev.target.value} /></label>
      ${this._renderImagePicker()}
      ${d3.is_admin ? b2`<label>${this._t("kind")}<select data-field="kind" @change=${(ev) => this._setEdit({ kind: ev.target.value })}>
              <option value="resident" ?selected=${e4.kind === "resident"}>${this._t("resident")}</option>
              <option value="installer" ?selected=${e4.kind === "installer"}>${this._t("installer")}</option></select></label>
            ${e4.kind === "installer" ? b2`<label class="inline"><input type="checkbox" data-field="released" .checked=${e4.content_released}
                  @change=${(ev) => e4.content_released = ev.target.checked} />${this._t("released")}</label>` : A}` : A}
      <label>${this._t("transition")}<input type="number" min="0" max=${d3.max_transition} step="0.5" data-field="transition"
        .value=${e4.transition ?? ""} @change=${(ev) => e4.transition = ev.target.value === "" ? null : Number(ev.target.value)} /></label>
      <label class="inline"><input type="checkbox" class="switch" data-field="preview" .checked=${e4.preview}
        @change=${(ev) => this._setEdit({ preview: ev.target.checked })} />${this._t("preview")}</label>
      ${trades.length ? b2`<h3>${this._t("all_house")}</h3>
            <div class="actions">${trades.map(
        (t3) => b2`<button class="small" data-action="trade-off" data-domain=${t3}
                @click=${() => this._allOff((dev) => dev.domain === t3)}>${this._t(t3)} · ${this._t(t3 === "cover" ? "all_closed" : "all_off")}</button>`
      )}</div>` : A}
      ${this._house ? this._renderRoomScenes() : A}
      ${order.length ? order.map((key) => {
        const devs = groups.get(key);
        const all = devs.every((dev) => e4.steps.has(dev.entity_id));
        const closeLabel = !this._house && key === "cover" ? "all_closed" : "all_off";
        return b2`<h3><label class="inline"><input type="checkbox" data-field="all" data-group=${key} .checked=${all}
                @change=${(ev) => this._pickAll(devs, ev.target.checked)} />
                ${this._house ? this._areaName(key || null) : this._t(key)} · ${this._t("all")}</label>
              <button class="small" data-action="group-off" data-group=${key}
                @click=${() => this._allOff((dev) => this._groupKey(dev) === key)}>${this._t(closeLabel)}</button></h3>
              ${devs.map((dev) => this._renderDevice(dev))}`;
      }) : b2`<p class="muted">${this._t("no_devices")}</p>`}
      ${this._renderOrder()}
      ${e4.error ? b2`<p class="error" role="alert">${this._err(e4.error, e4.errorDetail)}</p>` : A}
      ${e4.conflict ? b2`<div class="banner">${this._t("conflict")}
            <button data-action="load-new" @click=${this._loadNew}>${this._t("load_new")}</button>
            <button data-action="save-copy" @click=${() => this._save({ copy: true })}>${this._t("save_copy")}</button></div>` : A}
      ${e4.confirmDelete ? this._renderConfirmDelete() : A}
      <div class="actions">
        <button class="primary" data-action="save" ?disabled=${e4.busy} @click=${() => this._save({})}>${this._t("save")}</button>
        <button data-action="cancel" @click=${this._cancel}>${this._t("cancel")}</button>
        ${e4.scene_id ? b2`<button data-action="duplicate" @click=${() => this._save({ copy: true })}>${this._t("duplicate")}</button>` : A}
        ${e4.scene_id && (e4.kind === "resident" || d3.is_admin) ? b2`<button class="danger" data-action="ask-delete" @click=${() => this._setEdit({ confirmDelete: true })}>${this._t("delete")}</button>` : A}
      </div></div>`;
    }
    _setEdit(patch) {
      this._edit = { ...this._edit, ...patch };
    }
    _renderImagePicker() {
      const e4 = this._edit;
      const crop = e4.crop;
      return b2`<label>${this._t("image")}
        <select data-field="image" @change=${(ev) => this._pickImage(ev.target.value)}>
          <option value="">${this._t("no_image")}</option>
          ${e4.image?.startsWith("upload:") ? b2`<option value=${e4.image} selected>${this._t("own_image")}</option>` : A}
          ${e4.images.map((i5) => b2`<option value=${i5.name} ?selected=${i5.name === e4.image}>${i5.name}</option>`)}
        </select></label>
      <label class="file">${this._t("own_image")}
        <input type="file" accept="image/*" data-field="upload" @change=${(ev) => this._openCrop(ev.target.files?.[0])} /></label>
      ${crop ? b2`<div class="crop">
            <canvas width=${TILE.w / 2} height=${TILE.h / 2}></canvas>
            <label>${this._t("crop_x")}<input type="range" min="0" max="100" .value=${String(crop.x)}
              @input=${(ev) => this._moveCrop({ x: Number(ev.target.value) })} /></label>
            <label>${this._t("crop_y")}<input type="range" min="0" max="100" .value=${String(crop.y)}
              @input=${(ev) => this._moveCrop({ y: Number(ev.target.value) })} /></label>
            <button class="primary" data-action="use-image" @click=${this._upload}>${this._t("use_image")}</button>
          </div>` : e4.imageUrl ? b2`<img class="hero" src=${e4.imageUrl} alt="" />` : A}`;
    }
    _pickImage(name) {
      const image = name || null;
      const url = this._edit.images.find((i5) => i5.name === image)?.url ?? (image === this._edit.image ? this._edit.imageUrl : null);
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
        this._setEdit({ image: body.image, imageUrl: body.url, crop: null, error: null });
      } catch (err) {
        const detail = /: (.+)$/.exec(err.message ?? "")?.[1] ?? "";
        this._setEdit({ crop: null, error: err.code ?? "invalid_image_file", errorDetail: detail });
      }
    }
    _renderRoomScenes() {
      const e4 = this._edit;
      const areas = [...new Set(e4.room_scenes.map((r4) => r4.area_id))].sort((a3, b3) => this._areaName(a3).localeCompare(this._areaName(b3)));
      const missing = [...e4.steps].filter(([, s4]) => s4.choice === "scene" && s4.issue === "scene_missing");
      return b2`<h3>${this._t("scene")}</h3>
      ${areas.map((area) => {
        const current = [...e4.steps.values()].find((s4) => s4.choice === "scene" && s4.area_id === area)?.scene_id ?? "";
        return b2`<label>${this._areaName(area)} · ${this._t("room_scene")}
          <select data-field="room-scene" data-group=${area} @change=${(ev) => this._setRoomScene(area, ev.target.value)}>
            <option value="">${this._t("none")}</option>
            ${e4.room_scenes.filter((r4) => r4.area_id === area).map(
          (r4) => b2`<option value=${r4.id} ?selected=${r4.id === current}>${r4.name}</option>`
        )}
          </select></label>`;
      })}
      ${missing.map(
        ([key, s4]) => b2`<div class="row"><span class="name">${s4.name}
          <span class="badge warn">${this._t("scene_missing")}</span></span>
          <button data-action="remove" @click=${() => this._removeStep(key)}>${this._t("remove")}</button></div>`
      )}`;
    }
    _setRoomScene(area, sceneId) {
      const steps = new Map([...this._edit.steps].filter(([, s4]) => !(s4.choice === "scene" && s4.area_id === area)));
      const scene = this._edit.room_scenes.find((r4) => r4.id === sceneId);
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
      let controls = A;
      if (step) {
        const choices = [];
        if (step.stored) choices.push("keep");
        if (!locked) {
          choices.push("capture", "off");
          if (this._canSet(dev) && dev.domain !== "media_player") choices.push("set");
          if (dev.domain === "media_player") choices.push("on");
          if (dev.domain === "media_player" && dev.music_system) choices.push("favorite");
        }
        const label = (c4) => this._t(c4 === "off" && dev.domain === "cover" ? "closed" : c4);
        controls = b2`<select data-field="choice" data-entity=${dev.entity_id} aria-label=${dev.label}
          @change=${(ev) => this._choose(dev, ev.target.value)}>
          ${choices.map((c4) => b2`<option value=${c4} ?selected=${c4 === step.choice}>${label(c4)}</option>`)}
        </select>
        ${step.choice === "set" ? this._renderValues(dev, step) : A}
        ${step.choice === "favorite" ? b2`<select data-field="favorite_id" data-entity=${dev.entity_id} aria-label=${this._t("favorite")}
              @change=${(ev) => this._change(dev, { favorite_id: ev.target.value })}>
              ${step.issue === "favorite_missing" ? b2`<option value="" selected>${this._t("favorite_missing")}</option>` : A}
              ${this._edit.favorites.map((f3) => b2`<option value=${f3.id} ?selected=${f3.id === step.favorite_id}>${f3.name}</option>`)}
            </select>` : A}
        ${step.choice === "on" || step.choice === "favorite" ? b2`<input type="range" min="0" max="100" data-field="volume" data-entity=${dev.entity_id}
              .value=${String(Math.round((step.volume ?? 0.3) * 100))} aria-label=${this._t("volume")}
              @change=${(ev) => this._change(dev, { volume: Number(ev.target.value) / 100 })} />` : A}`;
      }
      const st = this.hass.states[dev.entity_id];
      const why = step?.issue ?? (dev.released === false ? "not_released" : !st ? "missing" : !dev.available ? "unavailable" : "");
      return b2`<div class="row device">
      <label class="name inline"><input type="checkbox" data-field="pick" data-entity=${dev.entity_id} .checked=${!!step}
        @change=${(ev) => this._pick(dev, ev.target.checked)} />
        ${dev.label} ${why ? b2`<span class="badge warn">${this._t(why)}</span>` : A}</label>${controls}
    </div>`;
    }
    _renderValues(dev, step) {
      const c4 = dev.capabilities ?? {};
      const v2 = step.values ?? {};
      const slider = (key, label, min, max, value, toValue = Number) => b2`<label class="value">${this._t(label)}
      <input type="range" min=${min} max=${max} data-field=${key} data-entity=${dev.entity_id} .value=${String(value)}
        @change=${(ev) => this._change(dev, { values: { ...step.values, [key]: toValue(ev.target.value) } })} /></label>`;
      if (dev.domain === "light") {
        return b2`${slider("brightness", "brightness", 1, 100, Math.round((v2.brightness ?? 255) / 2.55), (p3) => Math.max(1, Math.round(p3 * 2.55)))}
        ${c4.color_temp ? slider("color_temp_kelvin", "color_temp", c4.min_kelvin ?? 2e3, c4.max_kelvin ?? 6500, v2.color_temp_kelvin ?? c4.min_kelvin ?? 2700) : A}
        ${c4.color && !v2.color_temp_kelvin ? slider("hue", "hue", 0, 360, v2.hue ?? 30) : A}`;
      }
      if (dev.domain === "cover") {
        return b2`${c4.position ? slider("position", "position", 0, 100, v2.position ?? 100) : A}
        ${c4.tilt ? slider("tilt", "tilt", 0, 100, v2.tilt ?? 50) : A}`;
      }
      if (dev.domain === "climate") {
        return b2`<select data-field="hvac_mode" data-entity=${dev.entity_id} aria-label=${this._t("mode")}
          @change=${(ev) => this._change(dev, { values: { ...step.values, hvac_mode: ev.target.value } })}>
          ${(c4.hvac_modes ?? []).map((m2) => b2`<option value=${m2} ?selected=${m2 === v2.hvac_mode}>${m2}</option>`)}
        </select>
        <label class="value">${this._t("temperature")}<input type="number" min=${c4.min_temp ?? 5} max=${c4.max_temp ?? 35}
          step=${c4.temp_step ?? 0.5} data-field="temperature" data-entity=${dev.entity_id} .value=${String(v2.temperature ?? "")}
          @change=${(ev) => this._change(dev, { values: { ...step.values, temperature: Number(ev.target.value) } })} /></label>`;
      }
      if (dev.domain === "fan") return slider("percentage", "position", 0, 100, v2.percentage ?? 50);
      if (dev.domain === "switch") {
        return b2`<input type="checkbox" class="switch" data-field="on" data-entity=${dev.entity_id} .checked=${!!v2.on}
        aria-label=${this._t("on")} @change=${(ev) => this._change(dev, { values: { on: ev.target.checked } })} />`;
      }
      return A;
    }
    _renderOrder() {
      const steps = [...this._edit.steps];
      if (!steps.length) return A;
      const max = this._data.max_delay;
      return b2`<h3>${this._t("order")}</h3>
      ${steps.map(([key, s4], i5) => b2`<div class="row">
        <span class="name">${s4.choice === "scene" ? s4.name : this._edit.devices.find((d3) => d3.entity_id === key)?.label ?? key}</span>
        <label class="value">${this._t("delay")}<input type="number" min="0" max=${max} data-field="delay" data-entity=${key}
          .value=${String(s4.delay ?? 0)} @change=${(ev) => this._setDelay(key, Number(ev.target.value))} /></label>
        <button class="icon" data-action="up" aria-label=${this._t("up")} ?disabled=${i5 === 0} @click=${() => this._move(i5, -1)}>↑</button>
        <button class="icon" data-action="down" aria-label=${this._t("down")} ?disabled=${i5 === steps.length - 1}
          @click=${() => this._move(i5, 1)}>↓</button>
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
      if (patch.favorite_id) step.issue = null;
      this._edit.steps.set(dev.entity_id, step);
      this.requestUpdate();
      this._preview(dev.entity_id, step);
    }
    _allOff(match) {
      const steps = new Map(this._edit.steps);
      for (const dev of this._edit.devices.filter((d3) => match(d3) && d3.domain !== "scene" && d3.released !== false)) {
        const step = { delay: 0, ...steps.get(dev.entity_id), choice: "off" };
        steps.set(dev.entity_id, step);
        this._preview(dev.entity_id, step);
      }
      this._setEdit({ steps });
    }
    _stepPayload(key, s4) {
      const delay = s4.delay ? { delay: s4.delay } : {};
      if (s4.choice === "scene") return { mode: "scene", scene_id: s4.scene_id, ...delay };
      if (s4.choice === "on" || s4.choice === "favorite") {
        return {
          entity_id: key,
          mode: "music",
          music: s4.choice,
          volume: s4.volume ?? 0.3,
          ...s4.choice === "favorite" ? { favorite_id: s4.favorite_id ?? "" } : {},
          ...delay
        };
      }
      if (s4.choice === "set") return { entity_id: key, mode: "set", values: s4.values ?? {}, ...delay };
      return { entity_id: key, mode: s4.choice, ...delay };
    }
    _payloadSteps() {
      return [...this._edit.steps].map(([key, s4]) => this._stepPayload(key, s4));
    }
    // live preview (spec 5.4): every change switches the device; cancel restores the state from before
    _preview(key, s4) {
      if (!this._edit?.preview || !["off", "set", "on"].includes(s4.choice)) return;
      const { delay, ...step } = this._stepPayload(key, s4);
      this._previewed = true;
      this.hass.callWS({ type: `${WS}/preview`, step, ...this._house ? {} : { area_id: this._config.area } }).catch(() => {
      });
    }
    _endPreview(restore) {
      if (!this._previewed) return;
      this._previewed = false;
      this.hass.callWS({ type: `${WS}/preview_end`, restore }).catch(() => {
      });
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
      const slots = used.slots.map((s4) => {
        const [scope, n4] = s4.split(":");
        return `${this._areaName(scope === HOUSE ? null : scope)} ${this._t("slot")} ${n4}`;
      });
      const all = [...used.scenes, ...slots];
      return b2`<div class="banner" role="alertdialog">${this._t("confirm_delete")}
      ${all.length ? b2`<br />${this._t("used_on")} ${all.join(", ")}` : A}
      <br /><span class="muted">${this._t("outside_note")}</span><br />
      <button class="danger" data-action="delete" @click=${this._delete}>${this._t("yes")}</button>
      <button data-action="keep-scene" @click=${() => this._setEdit({ confirmDelete: false })}>${this._t("no")}</button></div>`;
    }
    async _save({ copy }) {
      const e4 = this._edit;
      const taken = this._scenes.some((s4) => s4.id !== e4.scene_id && s4.name.trim().toLowerCase() === e4.name.trim().toLowerCase());
      if (taken && !copy) return this._setEdit({ error: "name_exists", errorDetail: "" });
      const msg = { type: `${WS}/save`, name: e4.name, image: e4.image, transition: e4.transition, steps: this._payloadSteps() };
      if (!this._house) msg.area_id = this._config.area;
      if (this._data.is_admin) Object.assign(msg, { kind: e4.kind, content_released: e4.content_released });
      if (copy && e4.scene_id) {
        const suffix = ` (${this._t("copy")})`;
        msg.name = e4.name.slice(0, this._data.name_length - suffix.length) + suffix;
        msg.copy_from = e4.scene_id;
      } else if (e4.scene_id) {
        Object.assign(msg, { scene_id: e4.scene_id, version: e4.version });
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
  };
  __publicField(ResidentScenesCard, "properties", {
    hass: { attribute: false },
    _data: { state: true },
    _detail: { state: true },
    _edit: { state: true },
    _rights: { state: true },
    _selected: { state: true },
    _narrow: { state: true },
    _notice: { state: true },
    _stale: { state: true }
  });
  __publicField(ResidentScenesCard, "styles", i`
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
  `);
  customElements.define("resident-scenes-card", ResidentScenesCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "resident-scenes-card", name: "Resident Scenes", description: "Create, edit and run resident scenes" });
})();
