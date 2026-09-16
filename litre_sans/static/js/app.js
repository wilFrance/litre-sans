/* Simulateur « Le litre sans… » — front vanilla, calcul local via engine.js. */
(function () {
  "use strict";

  const CATALOG = JSON.parse(document.getElementById("catalogData").textContent);
  const FUELS = Object.fromEntries(CATALOG.fuels.map((f) => [f.code, f]));
  const MEASURES = CATALOG.measures;
  const BY_ID = Object.fromEntries(MEASURES.map((m) => [m.id, m]));

  const $ = (s) => document.querySelector(s);
  const analytics = new Analytics();
  const fmt = (n, d = 2) =>
    n.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
  // Montant en euros, deux décimales ; en dessous du centime, on l'indique plutôt que d'afficher 0,00.
  const money = (v) => (v > 0 && v < 0.005 ? "moins de 0,01 €" : `${fmt(v, 2)} €`);
  const amountLabel = (v) => {
    const parts = [];
    if (v.budget_bn) parts.push(`${fmt(v.budget_bn, v.budget_bn < 1 ? 3 : 1)} Md€ par an`);
    if (v.direct_per_litre) parts.push(`${fmt(v.direct_per_litre, 2)} €/L`);
    return parts.join(" + ");
  };

  // ---------- État et URL ----------
  const state = { fuel: CATALOG.fuels[0].code, price: null, on: new Set(), variant: {} };
  MEASURES.forEach((m) => { state.variant[m.id] = m.variants.find((v) => v.is_default).id; });
  state.price = FUELS[state.fuel].reference_price;

  function readUrl() {
    const q = new URLSearchParams(location.search);
    const preset = document.body.dataset.preset;
    if (preset && !q.has("on") && !q.has("fuel") && BY_ID[preset]) state.on.add(preset);
    if (q.has("fuel") && FUELS[q.get("fuel")]) {
      state.fuel = q.get("fuel");
      state.price = FUELS[state.fuel].reference_price;
    }
    if (q.has("price")) {
      const p = parseFloat(q.get("price"));
      if (isValidPrice(p)) state.price = p;
    }
    if (q.has("on")) {
      q.get("on").split(",").filter((id) => BY_ID[id]).forEach((id) => state.on.add(id));
    }
    MEASURES.forEach((m) => {
      if (m.variants.length > 1 && q.has(m.id)) {
        const v = q.get(m.id);
        if (m.variants.some((x) => x.id === v)) state.variant[m.id] = v;
      }
    });
  }

  // L'URL est reconstruite à partir de l'état : les paramètres étrangers (utm_*, etc.) disparaissent.
  function writeUrl() {
    const q = new URLSearchParams();
    q.set("fuel", state.fuel);
    if (Math.abs(state.price - FUELS[state.fuel].reference_price) > 1e-9) {
      q.set("price", String(state.price));
    }
    const on = MEASURES.filter((m) => state.on.has(m.id)).map((m) => m.id);
    if (on.length) q.set("on", on.join(","));
    MEASURES.forEach((m) => {
      if (m.variants.length > 1) {
        const def = m.variants.find((v) => v.is_default).id;
        if (state.variant[m.id] !== def) q.set(m.id, state.variant[m.id]);
      }
    });
    history.replaceState(null, "", "?" + q.toString());
  }

  function isValidPrice(p) {
    return Number.isFinite(p) && p > FUELS[state.fuel].minimum_price;
  }

  function scenario() {
    return {
      fuel: state.fuel,
      start_price: state.price,
      selections: MEASURES.filter((m) => state.on.has(m.id)).map((m) => ({
        measure_id: m.id,
        variant_id: state.variant[m.id],
      })),
    };
  }

  // ---------- Calcul (engine.js, dans le navigateur) ----------
  const ENGINE = new LitreSans.Simulator(CATALOG, {
    litresBillions: CATALOG.litres_billions,
    vatRate: CATALOG.vat_rate,
    tankLitres: CATALOG.tank_litres,
  });

  let lastResult = null;

  function simulate() {
    try {
      lastResult = ENGINE.simulate(scenario());
      renderResult(lastResult);
      $("#shareText").textContent = `« ${shareText()} »`;
      showError("");
    } catch (e) {
      showError(e instanceof LitreSans.DomainError ? e.message : "Erreur de calcul.");
    }
  }

  function showError(msg) {
    let el = $("#calcError");
    if (!el) {
      el = document.createElement("p");
      el.id = "calcError";
      el.className = "error";
      el.setAttribute("role", "alert");
      $(".pump").after(el);
    }
    el.textContent = msg;
    el.hidden = !msg;
  }

  // ---------- Rendu ----------
  function renderResult(r) {
    $("#newPrice").textContent = fmt(r.breakdown_after.total);
    $("#oldPrice").textContent = `${fmt(r.price_before)} €`;
    $("#fuelLabel").textContent = `${FUELS[r.fuel].label} — prix simulé`;
    const d = r.cut_per_litre;
    const active = state.on.size > 0;
    $(".pump").classList.toggle("idle", !active);
    $("#delta").textContent = d >= 0.005 ? `–${money(d)} / litre` : "aucune baisse";
    $("#tank").textContent = d >= 0.005
      ? `–${fmt(r.tank_saving, 2)} € sur un plein de ${fmt(r.tank_litres, 0)} L`
      : "";
    const cap = $("#cap");
    cap.hidden = !r.cap_reached;
    cap.innerHTML =
      `<b>Plancher atteint.</b> Accise et TVA sont à zéro : le litre ne peut plus baisser, ` +
      `il ne reste que le coût du produit. <b>${fmt(r.unused_savings_bn, 1)} Md€</b> d'économies ` +
      `cochées n'ont donc plus d'effet.`;
    const total = r.breakdown_after.total;
    [
      ["#bHT", r.breakdown_after.ht, "#lHT"],
      ["#bAcc", r.breakdown_after.excise, "#lAcc"],
      ["#bTVA", r.breakdown_after.vat, "#lTVA"],
    ].forEach(([b, v, l]) => {
      $(b).style.flexBasis = (total ? (v / total) * 100 : 0) + "%";
      $(b).textContent = total && v / total > 0.12 ? fmt(v, 2) + " €" : "";
      $(l).textContent = fmt(v, 2) + " €";
    });
    $("#total").innerHTML =
      `Économies budgétaires cochées : <b>${fmt(r.budget_savings_bn, 1)} Md€</b> par an ` +
      `(${state.on.size} mesure${state.on.size > 1 ? "s" : ""})` +
      (r.cap_reached ? `, dont <b>${fmt(r.unused_savings_bn, 1)} Md€</b> sans effet sur le prix.` : ".");
  }

  function renderList() {
    MEASURES.forEach((m) => {
      const item = document.querySelector(`.item[data-measure="${m.id}"]`);
      const v = m.variants.find((x) => x.id === state.variant[m.id]);
      const on = state.on.has(m.id);
      item.classList.toggle("on", on);
      item.querySelector("input[type=checkbox]").checked = on;
      item.querySelector("[data-amount]").textContent = amountLabel(v);
      item.querySelector("[data-badge-label]").textContent = v.badge.label;
      const effect = v.unit_effect_per_litre;
      item.querySelector("[data-gain]").innerHTML = `–${money(effect)}<span>/ litre</span>`;
      const sel = item.querySelector("select");
      if (sel) sel.value = v.id;
    });
  }

  function renderControls() {
    document.querySelectorAll(".seg button").forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.fuel === state.fuel));
    });
    $("#priceInput").value = state.price;
  }

  function update() {
    renderList();
    writeUrl();
    simulate();
  }

  // ---------- Événements ----------
  document.querySelectorAll(".seg button").forEach((b) =>
    b.addEventListener("click", () => {
      state.fuel = b.dataset.fuel;
      state.price = FUELS[state.fuel].reference_price;
      renderControls();
      setPriceHint("");
      update();
    })
  );

  function setPriceHint(msg) {
    const hint = $("#priceHint");
    hint.textContent = msg;
    hint.hidden = !msg;
    $("#priceInput").setAttribute("aria-invalid", msg ? "true" : "false");
  }

  $("#priceInput").addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    if (isValidPrice(v)) {
      state.price = v;
      setPriceHint("");
      update();
    } else {
      setPriceHint(`Le prix doit dépasser l'accise TTC (${fmt(FUELS[state.fuel].minimum_price, 2)} €/L).`);
    }
  });

  $("#list").addEventListener("change", (e) => {
    const t = e.target;
    if (t.dataset.id) {
      if (t.checked) {
        state.on.add(t.dataset.id);
        analytics.track(`mesure-cochee-${t.dataset.id}`);
      } else {
        state.on.delete(t.dataset.id);
      }
    }
    if (t.dataset.variant) {
      state.variant[t.dataset.variant] = t.value;
      const index = BY_ID[t.dataset.variant].variants.findIndex((v) => v.id === t.value);
      analytics.track(`variante-${t.dataset.variant}-${index}`);
    }
    update();
  });

  // Infobulles : au tap/clic on bascule (mobile), au survol/focus le CSS s'en charge.
  $("#list").addEventListener("click", (e) => {
    const btn = e.target.closest(".info");
    document.querySelectorAll('.info[aria-expanded="true"]').forEach((b) => {
      if (b !== btn) b.setAttribute("aria-expanded", "false");
    });
    if (btn) btn.setAttribute("aria-expanded", String(btn.getAttribute("aria-expanded") !== "true"));
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll('.info[aria-expanded="true"]').forEach((b) => b.setAttribute("aria-expanded", "false"));
    }
  });

  $("#checkAll").addEventListener("click", () => {
    MEASURES.forEach((m) => state.on.add(m.id));
    update();
  });

  $("#reset").addEventListener("click", () => {
    state.on.clear();
    MEASURES.forEach((m) => { state.variant[m.id] = m.variants.find((v) => v.is_default).id; });
    state.price = FUELS[state.fuel].reference_price;
    renderControls();
    setPriceHint("");
    update();
  });

  // Mobile : le panneau pompe est fixé en bas ; on réserve sa hauteur sous la liste.
  const pumpPanel = $("#pumpPanel");
  $("#pumpMore").addEventListener("click", (e) => {
    const open = pumpPanel.classList.toggle("open");
    e.currentTarget.setAttribute("aria-expanded", String(open));
    e.currentTarget.textContent = open ? "Réduire ▴" : "Détails ▾";
  });
  const reserveSpace = () => {
    document.documentElement.style.setProperty("--pump-h", `${pumpPanel.offsetHeight + 16}px`);
  };
  if ("ResizeObserver" in window) new ResizeObserver(reserveSpace).observe(pumpPanel);
  window.addEventListener("resize", reserveSpace);
  reserveSpace();

  // ---------- Partage ----------
  const SITE_URL = document.body.dataset.siteUrl || "";
  const SCENARIOS = Object.fromEntries(CATALOG.scenarios.map((sc) => [sc.measure_id, sc]));
  const capitalize = (t) => t.charAt(0).toUpperCase() + t.slice(1);

  // « Sans l'AME, mon plein de 50 L coûterait 1,27 € de moins. Et vous ? »
  function shareText() {
    const chosen = MEASURES.filter((m) => state.on.has(m.id));
    if (!chosen.length || !lastResult || lastResult.tank_saving < 0.005) {
      return "Et si les économies allaient à la pompe ? Cochez des dépenses publiques à supprimer.";
    }
    const labels = chosen.map((m) => {
      const v = m.variants.find((x) => x.id === state.variant[m.id]);
      return v.share_label || m.share_label;
    });
    let clause;
    if (labels.length === 1) clause = labels[0];
    else if (labels.length === 2) clause = `${labels[0]} et ${labels[1]}`;
    else clause = `${labels[0]}, ${labels[1]} et ${labels.length - 2} autres mesures`;
    const tank = fmt(lastResult.tank_litres, 0);
    return `${capitalize(clause)}, mon plein de ${tank} L coûterait ${fmt(lastResult.tank_saving, 2)} € de moins. Et vous ?`;
  }

  // Adresse à partager : celle du scénario phare si l'état lui correspond exactement
  // (une mesure, variante par défaut, carburant et prix de référence), sinon l'URL courante.
  function shareUrl() {
    if (state.on.size === 1) {
      const id = [...state.on][0];
      const sc = SCENARIOS[id];
      const m = BY_ID[id];
      const isDefault = state.variant[id] === m.variants.find((v) => v.is_default).id;
      const refPrice = Math.abs(state.price - FUELS[state.fuel].reference_price) < 1e-9;
      if (sc && isDefault && refPrice && state.fuel === sc.fuel) {
        return SITE_URL ? `${SITE_URL}${sc.path}` : new URL(`${rootPrefix()}${sc.path}`, location.href).href;
      }
    }
    return location.href; // sans utm_* : l'URL est réécrite depuis l'état
  }

  // Préfixe relatif vers la racine du site (les pages de scénario sont dans s/<id>/).
  function rootPrefix() {
    return document.body.dataset.preset ? "../../" : "./";
  }

  const shareTargets = {
    whatsapp: (url, text) => `https://wa.me/?text=${encodeURIComponent(`${text} ${url}`)}`,
    x: (url, text) => `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
    facebook: (url, text) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${encodeURIComponent(text)}`,
    linkedin: (url) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
  };

  document.querySelectorAll("[data-share]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const channel = btn.dataset.share;
      const url = shareUrl();
      const text = shareText();
      analytics.track(`partage-${channel}`);
      if (channel === "copie-lien") {
        const msg = $("#shareMsg");
        try {
          await navigator.clipboard.writeText(`${text} ${url}`);
          msg.textContent = "Texte et lien copiés.";
        } catch (e) {
          msg.textContent = url;
        }
        setTimeout(() => { msg.textContent = ""; }, 4000);
        return;
      }
      window.open(shareTargets[channel](url, text), "_blank", "noopener");
    })
  );

  // ---------- Démarrage ----------
  readUrl();
  renderControls();
  renderList();
  writeUrl();
  simulate();
  if (state.on.size > 0) analytics.track("scenario-charge");
})();
