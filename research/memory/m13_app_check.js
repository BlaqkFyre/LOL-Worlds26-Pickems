/* Timing fixes step 1, app check (26 Nov 2026 AEST): the v54 app sim read the same way as real games in m10_timing.py, with the
   v53 settings (opening and event_gap "off") alongside. Paste into (or fetch and eval in) a tab of the app served locally.
   Drafts: every game in WORLDS_LIVE.games (teams, sides and champions as played), SEEDS large seeds each (small seeds 1-100 give
   alike early draws: m11_step0.json). Fights = kills under 20 s apart (as the real side). Same-team pairs: a team's consecutive
   objective events (grubs and the soul line left out, as m10), and from its own kill to its next objective.
   Replay check: window.M13_V53 = the v53 SIM_ENGINE (js/sim-engine.js at commit 70699d6, loaded by eval under another name); the
   fingerprint of every game record (winner, length, steps, box score) over 72 drafts x 20 seeds must match v54 with both settings
   "off", for the default and alt sims. Results copied to research/model/memory/m13_app_check.json. */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, SEEDS = window.M13_SEEDS || 100;
  const MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, MON = new Set(["dragon", "elder", "baron", "herald"]), STR = new Set(["tower", "inhib", "nexus"]);
  const r3 = x => Math.round(x * 1000) / 1000;
  const seedOf = (gi, i) => 1099511627776 + ((gi + 1) * 1000003 + i * 2654435761) % 4503599627370496;
  const drafts = WORLDS_LIVE.games.map(g => { const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    return E.inputs(T, g.blue, g.red, side("blue"), side("red")).x; });
  const read = (S, label) => {
    let games = 0, blue = 0, secs = [], kills = 0, drag = 0, tow = 0, g15 = [];
    const fb = [], fm = [0, 0, 0, 0, 0, 0], G = {}, GK = {};
    drafts.forEach((x, gi) => { for(let i = 0; i < SEEDS; i++){
      const o = S.run(x, seedOf(gi, i), true); games++; if(o.winner === "blue") blue++; secs.push(o.sec); kills += o.kills[0] + o.kills[1];
      drag += o.dr[0].length + o.dr[1].length; tow += o.towers[0] + o.towers[1]; if(!isNaN(o.g15)) g15.push(o.g15);
      const kt = o.steps.filter(s => s.kind === "kill").map(s => s.t).sort((a, b) => a - b);
      if(kt.length) fb.push(kt[0]);
      kt.forEach((t, j) => { if((j === 0 || t - kt[j - 1] > 20) && t < 360) fm[Math.floor(t / 60)]++; });
      for(const sd of ["blue", "red"]){
        const ev = o.steps.filter(s => s.side === sd && (MON.has(s.kind) || STR.has(s.kind)));
        for(let j = 1; j < ev.length; j++){ const p = (MON.has(ev[j - 1].kind) ? "monster" : "structure") + " then " + (MON.has(ev[j].kind) ? "monster" : "structure");
          (G[p] = G[p] || []).push(ev[j].t - ev[j - 1].t); }
        const ek = o.steps.filter(s => s.side === sd && (s.kind === "kill" || MON.has(s.kind) || STR.has(s.kind)));
        for(let j = 1; j < ek.length; j++){ if(ek[j].kind === "kill" || ek[j - 1].kind !== "kill") continue;
          const p = "kill then " + (MON.has(ek[j].kind) ? "monster" : "structure"); (GK[p] = GK[p] || []).push(ek[j].t - ek[j - 1].t); }
      }
    } });
    const sum = A => Object.fromEntries(Object.entries(A).map(([p, a]) => { a.sort((x, y) => x - y);
      return [p, {pairs: a.length, ...Object.fromEntries([1, 2, 5, 10].map(s => ["within " + s + " s", r3(a.filter(v => v <= s).length / a.length)])), "median s": a[a.length >> 1]}]; }));
    secs.sort((a, b) => a - b); g15.sort((a, b) => a - b); fb.sort((a, b) => a - b);
    return {label, games, "blue win": r3(blue / games), "length median min": r3(secs[secs.length >> 1] / 60), "length 45+ min": r3(secs.filter(s => s >= 2700).length / games),
      "kills per game": r3(kills / games), "dragons per game": r3(drag / games), "towers per game": r3(tow / games), "gold at 15 sd": Math.round(Math.sqrt(g15.reduce((a, v) => a + v * v, 0) / g15.length)),
      "fights starting per game, minutes 0-5": fm.map(v => r3(v / games)),
      "first blood before (s)": Object.fromEntries([30, 60, 90, 120, 180].map(s => [s, r3(fb.filter(v => v < s).length / fb.length)])),
      "first blood quantiles 10, 25, 50, 75, 90%": [.1, .25, .5, .75, .9].map(q => fb[Math.min(fb.length - 1, Math.floor(q * fb.length))]),
      "same-team objective pairs": sum(G), "own kill to next objective": sum(GK)};
  };
  const fp = (S, n) => { let h = 2166136261 >>> 0; const mix = s => { for(let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } };
    drafts.forEach((x, gi) => { for(let i = 0; i < n; i++){ const o = S.run(x, seedOf(gi, i), true); mix(JSON.stringify([o.winner, o.sec, o.kills, o.steps, o.ps])); } }); return h.toString(16); };
  const OFF = {opening: "off", event_gap: "off"}, R = {drafts: drafts.length, seeds: SEEDS, settings: T.cal.default};
  R.v54 = read(new E.Sim(T.P, T.cal.default), "v54 (default)");
  R.v54_off = read(new E.Sim(T.P, Object.assign({}, T.cal.default, OFF)), "v54 with opening and event_gap off (= v53)");
  R.v54_alt = read(new E.Sim(T.P, T.cal.alt), "v54 simpler fights (alt)");
  if(window.M13_V53){ const V = window.M13_V53; R.replay = {};
    for(const k of ["default", "alt"]){ const a = fp(new V.Sim(T.P, T.cal[k]), 20), b = fp(new E.Sim(T.P, Object.assign({}, T.cal[k], OFF)), 20);
      R.replay[k] = {v53: a, "v54 off": b, identical: a === b}; } }
  return JSON.stringify(R);
})();
