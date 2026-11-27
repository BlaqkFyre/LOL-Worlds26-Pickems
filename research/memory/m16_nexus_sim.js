/* Nexus timing, sim side (27 Nov 2026 AEST): the app sim read as m16_nexus_push.py reads real games (pushes by structures left to the
   Nexus at the fight's start: nexus towers standing + 1 if no inhibitor is down, lane open only; inhibitors back after 300 s, nexus
   towers after 180 s). Paste into (or fetch and eval in) a tab of the app served locally; window.M16_CAL adds settings to the default
   sim. 72 Worlds drafts x 100 large seeds (window.M16_SEEDS). */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, S = new E.Sim(T.P, Object.assign({}, T.cal.default, window.M16_CAL || {})), SEEDS = window.M16_SEEDS || 100;
  const MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, STR = new Set(["tower", "inhib", "nexus"]);
  const seedOf = (gi, i) => 1099511627776 + ((gi + 1) * 1000003 + i * 2654435761) % 4503599627370496;
  const QS = [.1, .25, .5, .75, .9], r3 = x => Math.round(x * 1000) / 1000;
  const qq = a => { if(!a.length) return null; a.sort((x, y) => x - y); return QS.map(q => { const x = q * (a.length - 1), i = Math.floor(x); return Math.round((a[i] + ((a[i + 1] ?? a[i]) - a[i]) * (x - i)) * 10) / 10; }); };
  const kd = s => s.kind === "nexus" ? "nexus" : s.kind === "inhib" ? "inhib" : s.text === "nexus tower" ? "nxt" : s.text.startsWith("T3") ? "T3" : "outer";
  const R = {0: [], 1: [], 2: [], 3: []}, G = {}, lens = [], nxAll = [], closed = [0];
  WORLDS_LIVE.games.forEach((g, gi) => { const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    const x = E.inputs(T, g.blue, g.red, side("blue"), side("red")).x;
    for(let i = 0; i < SEEDS; i++){ const o = S.run(x, seedOf(gi, i), true); lens.push(o.sec / 60);
      const K = o.steps.filter(s => s.kind === "kill").sort((a, b) => a.t - b.t), St = o.steps.filter(s => STR.has(s.kind)).map(s => ({t: s.t, side: s.side, k: kd(s)}));
      const F = []; let cur = null;
      K.forEach(k => { if(!cur || k.t - cur.t1 > 20){ cur = {t0: k.t, t1: k.t, b: 0, r: 0}; F.push(cur); } cur.t1 = k.t; cur[k.side === "blue" ? "b" : "r"]++; });
      F.forEach((f, j) => { const w = f.b > f.r ? "blue" : f.r > f.b ? "red" : null; if(!w) return;
        const pre = St.filter(s => s.side === w && s.t < f.t0), t3 = pre.filter(s => s.k === "T3").length, inh = pre.filter(s => s.k === "inhib" && s.t > f.t0 - 300).length;
        const nxd = Math.min(2, pre.filter(s => s.k === "nxt" && s.t > f.t0 - 180).length), left = t3 ? (2 - nxd) + (inh ? 0 : 1) : null;
        const end = Math.min(j + 1 < F.length ? F[j + 1].t0 : 1e9, f.t1 + 120), xs = St.filter(s => s.side === w && s.t >= f.t0 && s.t < end);
        for(let q = 1; q < xs.length; q++){ const key = `${xs[q - 1].k} > ${xs[q].k}`; (G[key] = G[key] || []).push(xs[q].t - xs[q - 1].t); }
        const ni = xs.findIndex(s => s.k === "nexus");
        if(ni >= 0){ nxAll.push(xs[ni].t - f.t1); if(left == null) closed[0]++; }
        if(left == null || left > 3) return;
        R[left].push({nx: ni >= 0 ? xs[ni].t - f.t1 : null, before: ni >= 0 ? ni : null, first: xs.length ? xs[0].t - f.t1 : null}); }); } });
  const out = {settings: window.M16_CAL || {}, games: lens.length, "length min (10/25/50/75/90%)": qq(lens.slice()), "45+ min": r3(lens.filter(v => v >= 45).length / lens.length),
    "Nexus from the last kill s, all pushes ending in the Nexus": qq(nxAll.slice()), "pushes ending in the Nexus with the lane closed at the fight's start": closed[0]};
  [0, 1, 2, 3].forEach(L => { const A = R[L], nx = A.filter(a => a.nx != null);
    out[`${L} left`] = {"won fights": A.length, "push takes the Nexus": A.length ? r3(nx.length / A.length) : null, "Nexus from the last kill s (10/25/50/75/90%)": qq(nx.map(a => a.nx)),
      "structures before the Nexus (10/25/50/75/90%)": qq(nx.map(a => a.before)), "first structure from the last kill s": qq(A.filter(a => a.first != null).map(a => a.first))}; });
  out["gaps s (10/25/50/75/90%), n"] = {}; ["T3 > inhib", "inhib > nxt", "nxt > nxt", "nxt > nexus", "inhib > nexus", "T3 > nxt"].forEach(k => { out["gaps s (10/25/50/75/90%), n"][k] = [qq((G[k] || []).slice()), (G[k] || []).length]; });
  return JSON.stringify(out);
})();
