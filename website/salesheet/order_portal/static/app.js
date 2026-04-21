/* Alpine.js state for the order builder.
 * Usage in template:  <div x-data="orderBuilder()" x-init="init()">
 */
function orderBuilder() {
  const wrap = () => document.querySelector(".order-wrap");

  return {
    // --- config from data attrs ---
    orderId: null,
    role: "external_sales",
    gmFloor: 25,
    vatPct: 7,

    // --- runtime state ---
    loading: true,
    catalog: null,         // /api/order/catalog payload
    catalogEntries: [],    // Object.values(categories) flattened for x-for
    openCats: { decking: true },  // decking expanded by default
    fx: null,

    order: {
      customer: { name:"", email:"", phone:"", company:"", billing_address:"", project_type:"", notes:"" },
      line_items: [],
      totals: { subtotal_thb: 0, vat_thb: 0, grand_total_thb: 0 },
      status: "draft",
      order_number: null,
    },

    saveState: "idle",   // idle | saving | saved | error
    submitting: false,
    validationErrors: [],

    addDialog: { product: null, colour_code: null, colour_name: "", colour_hex: "", finish: "", qty: 1 },

    _saveTimer: null,
    _validateTimer: null,

    // ---- init ----
    async init() {
      const el = wrap();
      this.orderId = el.dataset.orderId;
      this.role = el.dataset.role || "external_sales";
      this.gmFloor = parseFloat(el.dataset.gmFloor) || (this.role === "admin" ? 0 : 25);
      this.vatPct = parseFloat(el.dataset.vatPct) || 7;

      // Load order + catalog in parallel
      await Promise.all([this.loadOrder(), this.loadCatalog()]);
      this.loading = false;
      this.recomputeTotals();

      // Watch for any change in line_items / customer / totals → autosave
      this.$watch("order.customer", () => this.dirty(), { deep: true });
      this.$watch("order.line_items", () => { this.recomputeTotals(); this.dirty(); }, { deep: true });

      await this.validate();
    },

    async loadOrder() {
      try {
        const res = await fetch(`/order/${this.orderId}.json`);
        if (!res.ok) throw new Error("load failed");
        const body = await res.json();
        if (body.ok && body.order) {
          this.order = Object.assign(this.order, body.order);
          this.order.customer = Object.assign(this.order.customer, body.order.customer || {});
          this.order.line_items = body.order.line_items || [];
          this.order.totals = body.order.totals || this.order.totals;
        }
      } catch (e) { console.error("loadOrder", e); }
    },

    async loadCatalog() {
      try {
        const [cat, fx] = await Promise.all([
          fetch("/api/order/catalog").then(r => r.json()),
          fetch("/api/order/fx").then(r => r.json()),
        ]);
        this.catalog = cat;
        this.fx = fx.snapshot;
        // Ordered list for rendering. Decking first, DIY last.
        const order = ["decking", "cladding", "panels", "fence", "structure", "diy-tiles"];
        this.catalogEntries = order.map(slug => cat.categories[slug]).filter(Boolean);
      } catch (e) { console.error("loadCatalog", e); }
    },

    // ---- catalog accordion ----
    toggleCat(slug) { this.openCats[slug] = !this.openCats[slug]; },

    // ---- add-to-cart dialog ----
    openAddDialog(product) {
      const defaultColour = (product.colours && product.colours[0]) || { code: null, name: "", hex: "" };
      this.addDialog = {
        product,
        colour_code: defaultColour.code,
        colour_name: defaultColour.name,
        colour_hex: defaultColour.hex,
        finish: (product.finishes && product.finishes[0]) || "",
        qty: 1,
      };
    },
    closeAddDialog() { this.addDialog.product = null; },
    canConfirmAdd() {
      const d = this.addDialog;
      if (!d.product) return false;
      if (d.product.colours && d.product.colours.length && !d.colour_code) return false;
      if (d.product.finishes && d.product.finishes.length && !d.finish) return false;
      return d.qty > 0;
    },
    confirmAdd() {
      const d = this.addDialog;
      if (!this.canConfirmAdd()) return;
      const line = this.lineFromProduct(d.product, d.qty, d.colour_code, d.colour_name, d.colour_hex, d.finish);
      this.order.line_items.push(line);
      this.closeAddDialog();
    },

    lineFromProduct(p, qty, colCode, colName, colHex, finish) {
      const qtyM = qty * (p.len || 0) / 1000;
      const landed = p.landed_cost_thb_per_m || null;
      const unitPrice = p.default_unit_price_thb || 0;
      const lineTotal = qtyM * unitPrice;
      const gm = (landed && unitPrice > 0) ? ((unitPrice - landed) / unitPrice * 100) : null;
      return {
        sku: p.sku,
        name: p.name,
        w: p.w, t: p.t, len: p.len,
        colour: colName,
        colour_code: colCode,
        colour_hex: colHex,
        finish,
        quantity_pcs: qty,
        quantity_m: parseFloat(qtyM.toFixed(2)),
        unit_price_thb: parseFloat(unitPrice.toFixed(2)),
        landed_cost_thb_per_m: landed,
        gm_percent: gm !== null ? parseFloat(gm.toFixed(2)) : null,
        line_total_thb: parseFloat(lineTotal.toFixed(2)),
      };
    },

    // ---- line mutations ----
    removeLine(i) { this.order.line_items.splice(i, 1); },
    changeQty(i, delta) {
      const ln = this.order.line_items[i];
      ln.quantity_pcs = Math.max(1, (ln.quantity_pcs || 1) + delta);
      this.recalcLine(i);
    },
    recalcLine(i) {
      const ln = this.order.line_items[i];
      ln.quantity_pcs = Math.max(1, parseInt(ln.quantity_pcs) || 1);
      ln.quantity_m = parseFloat((ln.quantity_pcs * (ln.len || 0) / 1000).toFixed(2));
      ln.unit_price_thb = parseFloat((ln.unit_price_thb || 0).toFixed(2));
      if (ln.landed_cost_thb_per_m && ln.unit_price_thb > 0) {
        ln.gm_percent = parseFloat(((ln.unit_price_thb - ln.landed_cost_thb_per_m) / ln.unit_price_thb * 100).toFixed(2));
      }
      ln.line_total_thb = parseFloat((ln.quantity_m * ln.unit_price_thb).toFixed(2));
      this.recomputeTotals();
    },
    setLineGm(i, gmPct) {
      const ln = this.order.line_items[i];
      if (!ln.landed_cost_thb_per_m) return;
      const gm = parseFloat(gmPct);
      const floor = this.role === "admin" ? 0 : this.gmFloor;
      const clamped = Math.max(floor, Math.min(95, gm));
      // unit = landed / (1 - gm/100)
      const newUnit = ln.landed_cost_thb_per_m / (1 - clamped / 100);
      ln.unit_price_thb = parseFloat(newUnit.toFixed(2));
      this.recalcLine(i);
    },

    recomputeTotals() {
      const subtotal = this.order.line_items.reduce((s, ln) => s + (ln.line_total_thb || 0), 0);
      const vat = subtotal * (this.vatPct / 100);
      this.order.totals = {
        subtotal_thb: parseFloat(subtotal.toFixed(2)),
        vat_thb: parseFloat(vat.toFixed(2)),
        grand_total_thb: parseFloat((subtotal + vat).toFixed(2)),
      };
    },

    // ---- autosave + validation ----
    dirty() {
      this.saveState = "saving";
      clearTimeout(this._saveTimer);
      this._saveTimer = setTimeout(() => this.save(), 500);
      clearTimeout(this._validateTimer);
      this._validateTimer = setTimeout(() => this.validate(), 600);
    },
    async save() {
      try {
        const res = await fetch(`/order/${this.orderId}`, {
          method: "PATCH",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            customer: this.order.customer,
            line_items: this.order.line_items,
            totals: this.order.totals,
          }),
        });
        this.saveState = res.ok ? "saved" : "error";
      } catch (e) {
        console.error("save", e);
        this.saveState = "error";
      }
    },
    async validate() {
      try {
        const res = await fetch(`/order/${this.orderId}/validate`, { method: "POST" });
        const body = await res.json();
        this.validationErrors = body.errors || [];
      } catch (e) { console.error("validate", e); }
    },

    get canSubmit() {
      return !this.submitting && this.validationErrors.length === 0 && this.order.line_items.length > 0;
    },

    saveStateLabel() {
      return {"idle":"Draft","saving":"Saving…","saved":"Saved ✓","error":"Save failed"}[this.saveState] || this.saveState;
    },

    async submitOrder() {
      if (!this.canSubmit) return;
      this.submitting = true;
      try {
        const res = await fetch(`/order/${this.orderId}/submit`, { method: "POST" });
        const body = await res.json();
        if (body.ok) {
          // Phase 4 will return {order_number, redirect_to}
          if (body.redirect_to) window.location.href = body.redirect_to;
          else alert("Submitted — " + (body.order_number || this.orderId));
        } else {
          alert("Submit failed: " + (body.error || "unknown"));
        }
      } catch (e) {
        alert("Submit failed: " + e.message);
      } finally {
        this.submitting = false;
      }
    },
  };
}
