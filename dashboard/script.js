(function () {
  const D = window.PF_DATA, K = D.kpis;
  const loc = d3.formatLocale({ decimal: ",", thousands: " ", grouping: [3], currency: ["", " €"], minus: "−" });
  const eur = (v) => loc.format(",.0f")(v) + " €";
  const meur = (v) => loc.format(",.2f")(v / 1e6) + " M€";
  const keur = (v) => loc.format(",.0f")(v / 1000) + " k€";
  const pct = (v, d = 1) => loc.format("." + d + "f")(v) + " %";
  const spct = (v) => (v > 0 ? "+" : "") + pct(v);
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const state = { scen: "Réaliste", loc: "Rue commerçante 1a (médiane)" };
  const $ = (id) => document.getElementById(id);
  const set = (id, t) => { const el = $(id); if (el) el.textContent = t; };

  // --- Tuiles et verdict
  const real = K.plan["Réaliste"];
  set("v-cash", meur(real.years[real.years.length - 1].cumulative_cash_eur));
  set("v-dens", loc.format(",.0f")(K.condition.density_needed_ttc_m2) + " €");
  set("k-market", loc.format(",.1f")(K.marche.de_market_bn) + " Md€");
  set("k-market-d", spct(K.marche.de_growth_pct) + " en 2025 (France " + spct(K.marche.fr_growth_pct) + ")");
  set("k-price", loc.format(",.1f")(K.prix.relative_price_index_de_vs_fr));
  set("k-cat", loc.format(",.0f")(K.marche.skin_per_capita_de) + " €");
  set("k-cat-d", "contre " + loc.format(",.0f")(K.marche.skin_per_capita_fr) + " € en France (−27 %)");

  function tiles() {
    const p = K.pilote[state.scen];
    set("k-ebitda", meur(p.ebitda));
    set("k-ebitda-d", "pour " + meur(p.capex) + " investis · scénario " + state.scen.toLowerCase());
    set("k-payback", p.payback_years ? loc.format(",.1f")(p.payback_years) + " ans" : "jamais");
    set("k-payback-d", "investissement ÷ EBITDA annuel des 3 pilotes");
  }

  // --- Outils de dessin
  const tipIn = (el) => { const t = document.createElement("div"); t.className = "tip"; t.hidden = true; el.appendChild(t); return t; };
  const tipShow = (el, tip, ev, title, lines) => {
    tip.replaceChildren();
    const b = document.createElement("b"); b.textContent = title; tip.appendChild(b);
    lines.forEach(([l, v]) => { tip.appendChild(document.createElement("br")); const s = document.createElement("span"); s.textContent = l; tip.appendChild(s); tip.appendChild(document.createTextNode(v)); });
    const box = el.getBoundingClientRect();
    tip.hidden = false;
    let x = ev.clientX - box.left + 12;
    if (x + tip.offsetWidth > box.width) x = Math.max(0, ev.clientX - box.left - tip.offsetWidth - 12);
    tip.style.left = x + "px"; tip.style.top = (ev.clientY - box.top + 12) + "px";
  };
  const svgIn = (el, H, label) => {
    el.replaceChildren();
    const W = Math.max(280, el.clientWidth);
    const svg = d3.select(el).append("svg").attr("width", "100%").attr("viewBox", `0 0 ${W} ${H}`).attr("height", H).attr("role", "img").attr("aria-label", label);
    return { svg, W };
  };
  const tw = (svg, s, cls) => { const t = svg.append("text").attr("class", cls || null).text(s); const w = t.node().getComputedTextLength(); t.remove(); return w; };

  // Barres horizontales groupées (catégorie -> [{key, value, color}])
  function hbars(el, rows, opts) {
    const n = rows[0].vals.length, bandH = 14 * n + 18;
    const H = rows.length * bandH + (opts.ref != null ? 18 : 6);
    const { svg, W } = svgIn(el, H, opts.label);
    const nameW = d3.max(rows, (r) => tw(svg, r.name)) + 10;
    const valW = d3.max(rows.flatMap((r) => r.vals), (v) => tw(svg, opts.fmt(v.value), "strong")) + 8;
    const ext = d3.extent([0, opts.ref ?? 0, ...rows.flatMap((r) => r.vals.map((v) => v.value))]);
    const x = d3.scaleLinear().domain(ext).range([nameW, W - valW]);
    const tip = tipIn(el);
    if (opts.ref != null) {
      svg.append("line").attr("x1", x(opts.ref)).attr("x2", x(opts.ref)).attr("y1", 0).attr("y2", H - 16).style("stroke", css("--ink")).style("stroke-opacity", .35).style("stroke-dasharray", "3 3");
      svg.append("text").attr("x", x(opts.ref)).attr("y", H - 2).attr("text-anchor", "middle").text(opts.refLabel);
    }
    rows.forEach((r, i) => {
      const y0 = i * bandH + 4;
      svg.append("text").attr("x", nameW - 10).attr("y", y0 + (14 * n) / 2 + 2).attr("dy", "0.35em").attr("text-anchor", "end").attr("class", r.strong ? "strong" : null).text(r.name);
      r.vals.forEach((v, j) => {
        if (v.value == null) return;
        const y = y0 + j * 14, x0 = x(Math.min(opts.base ?? 0, v.value)), x1 = x(Math.max(opts.base ?? 0, v.value));
        svg.append("rect").attr("x", x0).attr("y", y).attr("width", Math.max(1, x1 - x0)).attr("height", 12).attr("rx", 2).style("fill", v.color).style("opacity", r.dim ? .35 : 1)
          .on("pointermove", (ev) => tipShow(el, tip, ev, r.name, r.tip || [[v.key + " : ", opts.fmt(v.value)]]))
          .on("pointerleave", () => { tip.hidden = true; });
        const neg = v.value < (opts.base ?? 0);
        svg.append("text").attr("class", "strong" + (v.bad ? " neg" : "")).attr("x", neg ? x0 - 4 : x1 + 4).attr("y", y + 6).attr("dy", "0.35em").attr("text-anchor", neg ? "end" : "start").text(opts.fmt(v.value))
          .each(function () { if (neg && x0 - 4 - this.getComputedTextLength() < nameW) d3.select(this).attr("x", x(opts.base ?? 0) + 4).attr("text-anchor", "start"); });
      });
    });
  }

  // 1. Marché DE vs FR
  function market() {
    const m = K.marche;
    hbars($("ch-market"), [
      { name: "Marché beauté (Md€)", vals: [{ key: "Allemagne", value: m.de_market_bn, color: css("--accent") }, { key: "France", value: m.fr_market_bn, color: css("--ref") }] },
      { name: "Croissance 2025 (%)", vals: [{ key: "Allemagne", value: m.de_growth_pct, color: css("--accent") }, { key: "France", value: m.fr_growth_pct, color: css("--ref") }] },
      { name: "Soin de la peau / hab. (€)", strong: true, vals: [{ key: "Allemagne", value: m.skin_per_capita_de, color: css("--accent") }, { key: "France", value: m.skin_per_capita_fr, color: css("--ref") }] },
      { name: "Croissance du soin (%)", vals: [{ key: "Allemagne", value: m.skin_growth_de_pct, color: css("--accent") }, { key: "France", value: m.skin_growth_fr_pct, color: css("--ref") }] },
    ].map((r) => ({ ...r, vals: r.vals })), { label: "Marché beauté Allemagne et France", fmt: (v) => loc.format(",.1f")(v) });
    // chaque ligne a sa propre échelle : on redessine par ligne pour que les barres soient comparables à l'intérieur d'une ligne
  }
  function marketScaled() {
    const el = $("ch-market"), m = K.marche;
    const rows = [
      ["Marché beauté 2025", m.de_market_bn, m.fr_market_bn, (v) => loc.format(",.1f")(v) + " Md€"],
      ["Croissance du marché", m.de_growth_pct, m.fr_growth_pct, (v) => spct(v)],
      ["Soin de la peau par habitant", m.skin_per_capita_de, m.skin_per_capita_fr, (v) => loc.format(",.0f")(v) + " €"],
      ["Croissance du soin", m.skin_growth_de_pct, m.skin_growth_fr_pct, (v) => spct(v)],
    ];
    const bandH = 54, H = rows.length * bandH;
    const { svg, W } = svgIn(el, H, "Marché beauté et soin de la peau, Allemagne et France");
    const valW = 70, x0 = 0;
    const tip = tipIn(el);
    rows.forEach(([name, de, fr, f], i) => {
      const y = i * bandH, x = d3.scaleLinear().domain([0, Math.max(de, fr)]).range([0, W - valW - 4]);
      svg.append("text").attr("x", 0).attr("y", y + 10).attr("class", name.startsWith("Soin de la peau") ? "strong" : null).text(name);
      [["Allemagne", de, css("--accent")], ["France", fr, css("--ref")]].forEach(([k, v, c], j) => {
        const yy = y + 18 + j * 15;
        svg.append("rect").attr("x", x0).attr("y", yy).attr("width", Math.max(1, x(v))).attr("height", 12).attr("rx", 2).style("fill", c)
          .on("pointermove", (ev) => tipShow(el, tip, ev, name, [[k + " : ", f(v)]])).on("pointerleave", () => { tip.hidden = true; });
        svg.append("text").attr("class", "strong").attr("x", x(v) + 6).attr("y", yy + 6).attr("dy", "0.35em").text(f(v));
      });
    });
  }

  // 2. Assortiment : indice de pénétration DE / FR
  function assort() {
    const rows = D.marche.filter((r) => r.country_code === "DE").sort((a, b) => a.penetration_index_vs_fr - b.penetration_index_vs_fr)
      .map((r) => ({ name: r.category, strong: r.category === "Soins de la peau", vals: [{ key: "Indice", value: r.penetration_index_vs_fr, color: r.category === "Soins de la peau" ? css("--bad") : css("--accent"), bad: r.category === "Soins de la peau" }],
        tip: [["Indice DE / FR : ", loc.format(",.2f")(r.penetration_index_vs_fr)], ["Part du marché allemand : ", pct(r.share_pct)], ["Croissance 2025 : ", spct(r.growth_pct)]] }));
    hbars($("ch-assort"), rows, { label: "Poids des catégories en Allemagne par rapport à la France", fmt: (v) => loc.format(",.2f")(v), base: 0, ref: 1, refLabel: "1 = comme en France" });
  }

  // 3. EBITDA par ville (filtres)
  function ebitda() {
    const rows = D.bc.filter((r) => r.scenario === state.scen && r.location === state.loc).sort((a, b) => b.ebitda_eur - a.ebitda_eur);
    const v = Object.fromEntries(D.villes.map((x) => [x.city, x]));
    if (!rows.length) { $("ch-ebitda").textContent = "Aucune ville pour ce filtre."; return; }
    hbars($("ch-ebitda"), rows.map((r) => ({
      name: r.city + (v[r.city].is_pilot ? " ★" : ""), strong: v[r.city].is_pilot,
      vals: [{ key: "EBITDA", value: r.ebitda_eur, color: r.ebitda_eur < 0 ? css("--bad") : css("--accent"), bad: r.ebitda_eur < 0 }],
      tip: [["CA TTC : ", eur(r.revenue_ttc_eur)], ["Marge brute : ", eur(r.gross_margin_eur)], ["Loyer : ", eur(r.rent_eur) + " (" + pct(r.rent_pct_ca_ht) + " du CA HT)"], ["EBITDA : ", eur(r.ebitda_eur)], ["Retour sur invest. : ", r.payback_years ? loc.format(",.1f")(r.payback_years) + " ans" : "jamais"]],
    })), { label: "EBITDA annuel d'une boutique par ville", fmt: keur, base: 0 });
    const pos = rows.filter((r) => r.ebitda_eur > 0);
    const t = $("t-ebitda"); t.replaceChildren();
    const b = document.createElement("b"); b.textContent = "À retenir : "; t.appendChild(b);
    t.appendChild(document.createTextNode(pos.length
      ? `${pos.length} ville${pos.length > 1 ? "s" : ""} sur ${rows.length} rentable${pos.length > 1 ? "s" : ""} (${state.scen.toLowerCase()}, ${state.loc.toLowerCase()}). La meilleure, ${rows[0].city}, dégage ${keur(rows[0].ebitda_eur)} par an. ★ = villes pilotes 2027, choisies pour leur EBITDA. Les marges restent fines : Berlin et Leipzig rapportent moins de 30 k€ par an en scénario réaliste.`
      : `Aucune ville n'est rentable dans cette configuration (${state.scen.toLowerCase()}, ${state.loc.toLowerCase()}) : le loyer dépasse la marge dégagée. ★ = villes pilotes 2027.`));
  }

  // 4. Poids du loyer dans le CA, 1a vs artère n°1
  function rent() {
    const by = d3.group(D.bc.filter((r) => r.scenario === state.scen), (r) => r.city);
    const rows = Array.from(by, ([city, rs]) => {
      const a = rs.find((r) => r.location.startsWith("Rue")), f = rs.find((r) => r.location.startsWith("Artère"));
      return { name: city, a: a.rent_pct_ca_ht, f: f ? f.rent_pct_ca_ht : null };
    }).sort((x, y) => (y.f ?? y.a) - (x.f ?? x.a));
    hbars($("ch-rent"), rows.map((r) => ({ name: r.name, vals: [{ key: "Rue 1a", value: r.a, color: css("--accent") }, { key: "Artère n°1", value: r.f, color: css("--bad"), bad: true }],
      tip: [["Rue 1a : ", pct(r.a) + " du CA HT"], ["Artère n°1 : ", r.f == null ? "pas de loyer publié" : pct(r.f) + " du CA HT"]] })),
      { label: "Loyer en pourcentage du CA hors taxe, rue 1a et artère n°1", fmt: (v) => pct(v, 0), base: 0 });
  }

  // 5. Logistique : distance aux usines pour les villes pilotes 2027 et suivantes
  function logi() {
    const rows = D.villes.slice().sort((a, b) => a.pilot_rank - b.pilot_rank).map((v) => ({ name: v.city + (v.is_pilot ? " ★" : ""), strong: v.is_pilot,
      vals: [{ key: "Karlsruhe", value: v.distance_karlsruhe_km, color: css("--accent") }, { key: "Rambouillet", value: v.distance_rambouillet_km, color: css("--ref") }] }));
    hbars($("ch-logi"), rows, { label: "Distance routière estimée depuis les usines L'Oréal", fmt: (v) => loc.format(",.0f")(v) + " km", base: 0 });
  }

  // 6. Plan de déploiement : trésorerie cumulée par scénario
  function plan() {
    const el = $("ch-plan");
    const scen = [["Pessimiste", css("--bad")], ["Réaliste", css("--accent")], ["Optimiste", css("--good")]];
    const all = D.plan;
    const { svg, W } = svgIn(el, 260, "Trésorerie cumulée du plan 3, 8 puis 15 boutiques, par scénario");
    const y = d3.scaleLinear().domain(d3.extent([0, ...all.map((r) => r.cumulative_cash_eur)])).nice();
    const ticks = y.ticks(5);
    const m = { l: d3.max(ticks, (t) => tw(svg, meur(t))) + 10, r: 70, t: 10, b: 40 };
    y.range([260 - m.b, m.t]);
    const years = [2027, 2028, 2029, 2030, 2031];
    const x = d3.scalePoint().domain(years).range([m.l, W - m.r]).padding(.3);
    svg.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).tickValues(ticks).tickFormat(meur).tickSize(-(W - m.l - m.r))).call((g) => g.select(".domain").remove());
    svg.append("g").attr("transform", `translate(0,${260 - m.b})`).call(d3.axisBottom(x).tickSize(0).tickPadding(8).tickFormat((yr) => String(yr))).call((g) => g.select(".domain").remove())
      .selectAll(".tick text").append("tspan").attr("x", 0).attr("dy", "1.2em").text((yr) => all.find((r) => r.year === yr).stores + " bout.");
    svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0)).style("stroke", css("--ink")).style("stroke-opacity", .5);
    const tip = tipIn(el);
    scen.forEach(([s, c]) => {
      const pts = all.filter((r) => r.scenario === s).sort((a, b) => a.year - b.year);
      svg.append("path").datum(pts).attr("d", d3.line().x((r) => x(r.year)).y((r) => y(r.cumulative_cash_eur))).style("fill", "none").style("stroke", c).style("stroke-width", s === state.scen ? 3 : 1.5).style("opacity", s === state.scen ? 1 : .55);
      svg.append("g").selectAll("circle").data(pts).join("circle").attr("cx", (r) => x(r.year)).attr("cy", (r) => y(r.cumulative_cash_eur)).attr("r", s === state.scen ? 4.5 : 3).style("fill", c)
        .on("pointermove", (ev, r) => tipShow(el, tip, ev, s + " · " + r.year, [["Boutiques : ", String(r.stores)], ["CA TTC : ", meur(r.revenue_ttc_eur)], ["EBITDA : ", meur(r.ebitda_eur)], ["Investissements : ", meur(r.capex_eur)], ["Trésorerie cumulée : ", meur(r.cumulative_cash_eur)]]))
        .on("pointerleave", () => { tip.hidden = true; });
      const last = pts[pts.length - 1];
      svg.append("text").attr("class", "strong").attr("x", x(last.year) + 8).attr("y", y(last.cumulative_cash_eur)).attr("dy", "0.35em").style("fill", c).text(meur(last.cumulative_cash_eur));
    });
    // étiquettes de fin : écarter si elles se chevauchent
    const labels = svg.selectAll("text.strong").nodes().filter((n) => +n.getAttribute("x") > W - m.r);
    labels.sort((a, b) => +a.getAttribute("y") - +b.getAttribute("y"));
    for (let i = 1; i < labels.length; i++) { const p = +labels[i - 1].getAttribute("y"), c = +labels[i].getAttribute("y"); if (c - p < 14) labels[i].setAttribute("y", p + 14); }
  }

  // 7. Cascade : du CA à l'EBITDA d'une boutique pilote moyenne
  function cascade() {
    const el = $("ch-cascade");
    const pil = D.villes.filter((v) => v.is_pilot).map((v) => v.city);
    const rows = D.bc.filter((r) => r.scenario === state.scen && r.location === state.loc && pil.includes(r.city));
    const t = $("t-cascade"); t.replaceChildren();
    if (!rows.length) { el.textContent = "Pas de loyer publié pour toutes les villes pilotes dans cette configuration."; return; }
    const avg = (k) => d3.mean(rows, (r) => r[k]);
    const ht = avg("revenue_ht_eur"), gm = avg("gross_margin_eur");
    const steps = [
      ["CA hors taxe", ht, "total"], ["Coût des produits", -(ht - gm), "minus"], ["Loyer", -avg("rent_eur"), "minus"],
      ["Personnel", -avg("staff_eur"), "minus"], ["Autres charges", -avg("other_costs_eur"), "minus"], ["Logistique", -avg("logistics_eur"), "minus"], ["EBITDA", avg("ebitda_eur"), "total"],
    ];
    const H = 270, { svg, W } = svgIn(el, H, "Cascade du CA hors taxe à l'EBITDA d'une boutique pilote moyenne");
    const m = { l: 10, r: 10, t: 24, b: 36 };
    let run = 0; const bars = steps.map(([n, v, k]) => { let y0, y1; if (k === "total") { y0 = 0; y1 = v; run = v; } else { y0 = run; y1 = run + v; run = y1; } return { n, v, k, y0, y1 }; });
    const y = d3.scaleLinear().domain(d3.extent([0, ...bars.flatMap((b) => [b.y0, b.y1])])).nice().range([H - m.b, m.t]);
    const x = d3.scaleBand().domain(bars.map((b) => b.n)).range([m.l, W - m.r]).padding(.25);
    svg.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickSize(0).tickPadding(8)).call((g) => g.select(".domain").remove())
      .selectAll("text").each(function () { if (x.bandwidth() < 70) { const w = this.textContent.split(" "); if (w.length > 1) { d3.select(this).text(null); w.forEach((s, i) => d3.select(this).append("tspan").attr("x", 0).attr("dy", i ? "1.1em" : 0).text(s)); } } });
    svg.append("line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0)).style("stroke", css("--line"));
    bars.forEach((b) => {
      const col = b.k === "total" ? (b.v < 0 ? css("--bad") : css("--accent")) : css("--ref");
      svg.append("rect").attr("x", x(b.n)).attr("width", x.bandwidth()).attr("y", y(Math.max(b.y0, b.y1))).attr("height", Math.max(1, Math.abs(y(b.y0) - y(b.y1)))).attr("rx", 2).style("fill", col);
      svg.append("text").attr("class", "strong" + (b.k === "total" && b.v < 0 ? " neg" : "")).attr("x", x(b.n) + x.bandwidth() / 2).attr("y", y(Math.max(b.y0, b.y1)) - 6).attr("text-anchor", "middle").text((b.v > 0 && b.k !== "total" ? "+" : "") + keur(b.v));
    });
    const e = avg("ebitda_eur"), r = avg("rent_eur");
    const bb = document.createElement("b"); bb.textContent = "À retenir : "; t.appendChild(bb);
    t.appendChild(document.createTextNode(`sur ${keur(ht)} de CA hors taxe, le coût des produits prend ${keur(ht - gm)}, le personnel ${keur(avg("staff_eur"))} et le loyer ${keur(r)}. Il reste ${keur(e)} d'EBITDA par boutique (${state.scen.toLowerCase()}, ${state.loc.toLowerCase()}). Le personnel (4 conseillers, dont 2 formés au diagnostic) pèse plus que le loyer en rue 1a : c'est le premier levier à optimiser.`));
  }

  // --- Brique IA : synthèse pré-générée + analyse à la demande via Claude
  function renderMd(md, out) {
    out.replaceChildren();
    const lines = md.replace(/^# .*\n/, "").split("\n");
    let list = null, table = null;
    const inline = (el, s) => {
      s.split(/(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/).forEach((part) => {
        if (!part) return;
        let n;
        if (/^\*\*.+\*\*$/.test(part)) { n = document.createElement("b"); n.textContent = part.slice(2, -2); }
        else if (/^_.+_$/.test(part)) { n = document.createElement("em"); n.textContent = part.slice(1, -1); }
        else if (/^`.+`$/.test(part)) { n = document.createElement("code"); n.textContent = part.slice(1, -1); }
        else n = document.createTextNode(part);
        el.appendChild(n);
      });
    };
    lines.forEach((ln) => {
      if (/^\|/.test(ln)) {
        if (/^\|[-\s|]+\|$/.test(ln)) return;
        if (!table) { const w = document.createElement("div"); w.className = "scroll"; table = document.createElement("table"); w.appendChild(table); out.appendChild(w); }
        const tr = document.createElement("tr"); ln.slice(1, -1).split("|").forEach((c) => { const td = document.createElement("td"); inline(td, c.trim()); tr.appendChild(td); }); table.appendChild(tr); return;
      }
      table = null;
      const li = ln.match(/^\s*(?:-|\d+\.)\s+(.*)/);
      if (li) { if (!list) { list = document.createElement(/^\s*\d/.test(ln) ? "ol" : "ul"); out.appendChild(list); } const e = document.createElement("li"); inline(e, li[1]); list.appendChild(e); return; }
      list = null;
      if (/^#{2,4}\s/.test(ln)) { const h = document.createElement("h4"); h.textContent = ln.replace(/^#+\s/, ""); out.appendChild(h); return; }
      if (ln.trim()) { const p = document.createElement("p"); inline(p, ln); out.appendChild(p); }
    });
  }
  renderMd(D.synthese.replace(/^_Générée.*_\n/m, ""), $("ai-out"));

  let ctl = null;
  (async () => {
    const sample = await (window.claude?.use ? window.claude.use("sample") : null);
    if (!sample) return;
    const run = $("ai-run"), stop = $("ai-stop"), status = $("ai-status"), out = $("ai-out");
    run.hidden = false;
    stop.onclick = () => ctl?.abort();
    run.onclick = async () => {
      ctl = new AbortController();
      run.disabled = true; stop.hidden = false;
      status.textContent = "Claude analyse le scénario affiché…";
      const view = {
        filtres: { scenario: state.scen, emplacement: state.loc },
        boutiques_par_ville: D.bc.filter((r) => r.scenario === state.scen && r.location === state.loc).map((r) => ({ ville: r.city, ca_ttc: r.revenue_ttc_eur, ebitda: r.ebitda_eur, loyer_pct_ca: r.rent_pct_ca_ht, retour_invest_ans: r.payback_years })),
        plan_deploiement: D.plan.filter((r) => r.scenario === state.scen),
        kpis: { marche: K.marche, prix: K.prix, logistique: K.logistique, assortiment: K.assortiment, condition: K.condition, boutiques_france_simulees: K.boutiques_fr },
      };
      const prompt = `Tu es analyste data pour le Comex de L'Oréal, qui étudie un réseau de boutiques de diagnostic de peau en Allemagne (plan 3 boutiques en 2027, 8 en 2028, 15 en 2029). Voici les données du scénario affiché dans le dashboard (JSON) :\n\n${JSON.stringify(view)}\n\nRédige en français une analyse de ce scénario pour un dirigeant : 1) un verdict en une phrase (Go, Go conditionnel ou No-Go) ; 2) trois constats chiffrés ; 3) un risque ; 4) une action prioritaire. N'utilise que des chiffres présents dans les données, arrondis lisiblement, en euros. Précise que le business case repose sur une base interne simulée. Format Markdown simple : titres ##, listes à puces, gras **. 200 mots maximum.`;
      try {
        await sample(prompt, { signal: ctl.signal, onText: ({ text }) => { renderMd(text, out); status.textContent = "Analyse générée par Claude pour : " + state.scen.toLowerCase() + ", " + state.loc.toLowerCase() + "."; } });
      } catch (e) {
        if (e.text) renderMd(e.text, out);
        if (e.code === "not_granted" || e.code === "sampling_disabled" || e.code === "capability_disabled" || e.code === "not_declared") { run.hidden = true; status.textContent = "L'analyse IA à la demande n'est pas disponible ici. La synthèse pré-générée reste valable."; renderMd(D.synthese.replace(/^_Générée.*_\n/m, ""), out); }
        else if (e.code === "cancelled") status.textContent = "Analyse arrêtée.";
        else if (e.code === "rate_limited") status.textContent = "Trop de demandes pour le moment. Réessayez dans quelques minutes.";
        else status.textContent = "L'analyse n'a pas pu aboutir. Vous pouvez relancer.";
      } finally { run.disabled = false; stop.hidden = true; }
    };
  })();

  // --- Sources
  const ul = $("src-list");
  D.sources.forEach((s) => {
    const li = document.createElement("li");
    if (s.url) { const a = document.createElement("a"); a.href = s.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = s.name; li.appendChild(a); }
    else li.appendChild(document.createTextNode(s.name));
    li.appendChild(document.createTextNode(" · " + s.publisher + (s.reliability ? " · fiabilité " + s.reliability.toLowerCase() : "")));
    ul.appendChild(li);
  });

  // --- Filtres et rendu
  const draw = () => { tiles(); marketScaled(); assort(); ebitda(); rent(); logi(); plan(); cascade(); };
  document.querySelectorAll("#f-scen button, #f-loc button").forEach((b) => b.addEventListener("click", () => {
    const grp = b.parentElement, key = grp.id === "f-scen" ? "scen" : "loc";
    state[key] = b.dataset.v;
    grp.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    draw();
  }));
  draw();
  let rw; new ResizeObserver(() => { clearTimeout(rw); rw = setTimeout(draw, 120); }).observe(document.querySelector(".wrap"));
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
})();
