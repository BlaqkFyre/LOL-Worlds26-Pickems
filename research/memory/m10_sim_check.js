/* Play-test check, sim side (24 Nov 2026 AEST): the app sim (default settings) read the same way as real games in m10_timing.py:
   opening kill timing, gaps between one team's consecutive objective events (grubs and the soul line left out), dragons by side.
   Paste into (or fetch and eval in) a tab of the app served locally. Drafts: every game in WORLDS_LIVE.games, teams, sides and
   champions as played, 100 seeds each. Dragons count elemental drakes and Elders (as the Oracle's Elixir "dragons" column is read in
   m10_timing.py: not checked whether that column includes Elders). Results copied to research/model/memory/m10_sim_check.json. */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, S = new E.Sim(T.P, Object.assign({}, T.cal.default, window.M10_CAL || {})), SEEDS = 100;
  const MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, MON = new Set(["dragon", "elder", "baron", "herald"]), STR = new Set(["tower", "inhib", "nexus"]);
  const r3 = x => Math.round(x * 1000) / 1000, fb = [], bins = new Array(18).fill(0), G = {};
  let games = 0, db = 0, dr = 0, fdb = 0, fdn = 0;
  for(const g of WORLDS_LIVE.games){
    const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    const I = E.inputs(T, g.blue, g.red, side("blue"), side("red"));
    for(let seed = 1; seed <= SEEDS; seed++){
      const o = S.run(I.x, seed, true); games++;
      const ks = o.steps.filter(x => x.kind === "kill");
      if(ks.length) fb.push(Math.min(...ks.map(k => k.t)));
      ks.forEach(k => { if(k.t < 180) bins[Math.floor(k.t / 10)]++; });
      const dg = o.steps.filter(x => x.kind === "dragon" || x.kind === "elder");
      dg.forEach(x => { if(x.side === "blue") db++; else dr++; });
      const fd = o.steps.find(x => x.kind === "dragon"); if(fd){ fdn++; if(fd.side === "blue") fdb++; }
      for(const sd of ["blue", "red"]){
        const ev = o.steps.filter(x => x.side === sd && (MON.has(x.kind) || STR.has(x.kind)));
        for(let i = 1; i < ev.length; i++){
          const p = (MON.has(ev[i - 1].kind) ? "monster" : "structure") + " then " + (MON.has(ev[i].kind) ? "monster" : "structure");
          (G[p] = G[p] || []).push(ev[i].t - ev[i - 1].t);
        }
      }
    }
  }
  fb.sort((a, b) => a - b); const q = p => fb[Math.min(fb.length - 1, Math.floor(p * fb.length))];
  const R = {games, drafts: WORLDS_LIVE.games.length, seeds: SEEDS, settings: Object.assign({}, T.cal.default, window.M10_CAL || {}),
    opening: {"games with no kill": games - fb.length, "first blood time quantiles (s): 5, 10, 25, 50, 75, 90, 95%": [.05, .1, .25, .5, .75, .9, .95].map(q),
      "share of games with first blood before (s)": Object.fromEntries([30, 60, 90, 120, 180].map(s => [s, r3(fb.filter(x => x < s).length / fb.length)])),
      "share of games with first blood after (s)": Object.fromEntries([600, 780].map(s => [s, r3(fb.filter(x => x >= s).length / fb.length)])),
      "kills per game by 10 s, 0:00-3:00": bins.map(b => r3(b / games))},
    "gaps between one team's consecutive events": Object.fromEntries(Object.entries(G).map(([p, a]) => { a.sort((x, y) => x - y);
      return [p, {pairs: a.length, ...Object.fromEntries([1, 2, 5, 10].map(s => ["within " + s + " s", r3(a.filter(x => x <= s).length / a.length)])), "median s": a[a.length >> 1]}]; })),
    "dragons by side": {"dragons per game": r3((db + dr) / games), "blue share of dragons": r3(db / (db + dr)), "blue share of first dragons": r3(fdb / fdn)}};
  return JSON.stringify(R);
})();
