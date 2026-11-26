/* Push chain, sim side (26 Nov 2026 AEST): the app sim read as m14_push_timing.py reads real games (fights = kills under 20 s apart,
   winner = more kills, the push = the winner's structures from the fight's start until the next fight starts or 120 s after its last
   kill). Paste into (or fetch and eval in) a tab of the app served locally; window.M14_CAL adds settings to the default sim.
   72 Worlds drafts x 100 large seeds. Results copied to research/model/memory/m14_push_timing.json (sim block). */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, S = new E.Sim(T.P, Object.assign({}, T.cal.default, window.M14_CAL || {})), SEEDS = window.M14_SEEDS || 100;
  const MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, STR = new Set(["tower", "inhib", "nexus"]);
  const seedOf = (gi, i) => 1099511627776 + ((gi + 1) * 1000003 + i * 2654435761) % 4503599627370496;
  const QS = [.1, .25, .5, .75, .9], r3 = x => Math.round(x * 1000) / 1000;
  const qq = a => { if(!a.length) return null; a.sort((x, y) => x - y); return QS.map(q => { const x = q * (a.length - 1), i = Math.floor(x); return Math.round((a[i] + ((a[i + 1] ?? a[i]) - a[i]) * (x - i)) * 10) / 10; }); };
  const isBase = s => s.kind === "inhib" || s.kind === "nexus" || (s.kind === "tower" && (s.text === "nexus tower" || s.text.startsWith("T3")));
  let nP = 0, nS = 0; const nst = [0, 0, 0, 0, 0, 0], f0 = [], f1 = [], ga = [], gb = [], nxp = [], nxk = []; let before = 0;
  WORLDS_LIVE.games.forEach((g, gi) => { const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    const x = E.inputs(T, g.blue, g.red, side("blue"), side("red")).x;
    for(let i = 0; i < SEEDS; i++){ const o = S.run(x, seedOf(gi, i), true);
      const K = o.steps.filter(s => s.kind === "kill").sort((a, b) => a.t - b.t), St = o.steps.filter(s => STR.has(s.kind));
      const F = []; let cur = null;
      K.forEach(k => { if(!cur || k.t - cur.t1 > 20){ cur = {t0: k.t, t1: k.t, b: 0, r: 0}; F.push(cur); } cur.t1 = k.t; cur[k.side === "blue" ? "b" : "r"]++; });
      F.forEach((f, j) => { const w = f.b > f.r ? "blue" : f.r > f.b ? "red" : null; if(!w) return; nP++;
        const end = Math.min(j + 1 < F.length ? F[j + 1].t0 : 1e9, f.t1 + 120);
        const x_ = St.filter(s => s.side === w && s.t >= f.t0 && s.t < end); nst[Math.min(5, x_.length)]++;
        if(!x_.length) return; nS++; f0.push(x_[0].t - f.t0); f1.push(x_[0].t - f.t1); if(x_[0].t < f.t1) before++;
        for(let q = 1; q < x_.length; q++){ if(x_[q].kind === "nexus"){ nxp.push(x_[q].t - x_[q - 1].t); continue; }
          ga.push(x_[q].t - x_[q - 1].t); if(isBase(x_[q]) && isBase(x_[q - 1])) gb.push(x_[q].t - x_[q - 1].t); }
        const nx = x_.find(s => s.kind === "nexus"); if(nx) nxk.push(nx.t - f.t1); }); } });
  return JSON.stringify({settings: window.M14_CAL || {}, "won fights": nP, "with a structure": nS, "structures per won fight (share 0, 1, 2, 3, 4, 5+)": nst.map(v => r3(v / nP)),
    "first structure from the fight's start s (10/25/50/75/90%)": qq(f0), "first structure from the fight's last kill s": qq(f1), "first structure before the fight's last kill": r3(before / nS),
    "gap between the push's structures s (all, no Nexus)": qq(ga), "gap between base structures s": qq(gb), "Nexus from the push's previous structure s": qq(nxp),
    "Nexus from the fight's last kill s": qq(nxk), "pushes ending in the Nexus": nxk.length});
})();
