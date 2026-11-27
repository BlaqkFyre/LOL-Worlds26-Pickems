/* Base push v2, app check (27 Nov 2026 AEST, v55): the app sim with base_push "v2" (the default) against "off" (= v54).
   Paste into (or fetch and eval in) a tab of the app served locally. 72 Worlds drafts (WORLDS_LIVE.games, as played) x SEEDS large
   seeds (window.M18_SEEDS, default 100; small seeds give alike early draws: m11_step0.json).
   Reads: blue win, game length (quantiles, 45+ and 50+ min), kills a game, the winner's first T3 tower to the Nexus, Player of the Game
   by role (the winner with the highest fitted chance, as m7_sim_check.js).
   Replay check: window.M18_V54 = the v54 SIM_ENGINE (js/sim-engine.js at commit d10d5d6, kept at research/local/memory/sim-engine_v54.js,
   loaded by eval under another name); the fingerprint of every game record (winner, length, steps, box score) over 72 drafts x 20 seeds
   must match v55 with base_push "off", for the default and alt sims. The m16_nexus_sim.js reading (window.M16_CAL) is run separately.
   Results copied to research/model/memory/m18_app_check.json. */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, SEEDS = window.M18_SEEDS || 100, RL = ["top", "jng", "mid", "bot", "sup"];
  const MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, r3 = x => Math.round(x * 1000) / 1000;
  const seedOf = (gi, i) => 1099511627776 + ((gi + 1) * 1000003 + i * 2654435761) % 4503599627370496;
  const QS = [.1, .25, .5, .75, .9];
  const qq = a => { if(!a.length) return null; a.sort((x, y) => x - y); return QS.map(q => { const x = q * (a.length - 1), i = Math.floor(x); return Math.round((a[i] + ((a[i + 1] ?? a[i]) - a[i]) * (x - i)) * 10) / 10; }); };
  const drafts = WORLDS_LIVE.games.map(g => { const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    return E.inputs(T, g.blue, g.red, side("blue"), side("red")).x; });
  const read = (cal, label) => {
    const S = new E.Sim(T.P, cal); let games = 0, blue = 0, kills = 0, capped = 0; const lens = [], t3nx = [], POG = {top: 0, jng: 0, mid: 0, bot: 0, sup: 0};
    drafts.forEach((x, gi) => { for(let i = 0; i < SEEDS; i++){
      const o = S.run(x, seedOf(gi, i), true); games++; if(o.winner === "blue") blue++; kills += o.kills[0] + o.kills[1]; lens.push(o.sec / 60); if(o.capped) capped++;
      const t3 = o.steps.find(s => s.side === o.winner && s.kind === "tower" && s.text.startsWith("T3")), nx = o.steps.find(s => s.kind === "nexus");
      if(t3 && nx) t3nx.push(nx.t - t3.t);
      const mins = o.sec / 60, st = {}; RL.forEach(r => { const e = o.ps[o.winner][r]; st[r] = {k: e.k, d: e.d, a: e.a, kp: e.kp, dmgS: e.dmgS, csd: e.csd, vpm: e.vis / Math.max(1, mins)}; });
      const ch = E.pogChances(T, st); POG[RL.reduce((a, r) => ch[r] > ch[a] ? r : a, RL[0])]++; } });
    return {label, games, "blue win": r3(blue / games), "length min (10/25/50/75/90%)": qq(lens.slice()), "45+ min": r3(lens.filter(v => v >= 45).length / games),
      "50+ min": r3(lens.filter(v => v >= 50).length / games), "capped at 70 min": capped, "kills per game": r3(kills / games),
      "winner's first T3 tower to the Nexus s (10/25/50/75/90%)": qq(t3nx), "Player of the Game by role": Object.fromEntries(RL.map(r => [r, r3(POG[r] / games)]))};
  };
  const fp = (S, n) => { let h = 2166136261 >>> 0; const mix = s => { for(let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } };
    drafts.forEach((x, gi) => { for(let i = 0; i < n; i++){ const o = S.run(x, seedOf(gi, i), true); mix(JSON.stringify([o.winner, o.sec, o.kills, o.steps, o.ps])); } }); return h.toString(16); };
  const OFF = {base_push: "off"}, R = {drafts: drafts.length, seeds: SEEDS, settings: T.cal.default, base_table_cutoff: (T.base || {}).cutoff || null};
  R.v55 = read(T.cal.default, "v55 (default, base_push v2)");
  R.v55_off = read(Object.assign({}, T.cal.default, OFF), "v55 with base_push off (= v54)");
  if(window.M18_V54){ const V = window.M18_V54; R.replay = {};
    for(const k of ["default", "alt"]){ const a = fp(new V.Sim(T.P, T.cal[k]), 20), b = fp(new E.Sim(T.P, Object.assign({}, T.cal[k], OFF)), 20);
      R.replay[k] = {v54: a, "v55 off": b, identical: a === b}; } }
  return JSON.stringify(R);
})();
