/* App sim (js/sim-engine.js v50) shape check, 17 Nov 2026 AEST: paste into a tab of the app served locally (python http.server, see
   CLAUDE.md notes sessions). The real-game side of the same measures is in m5_sim_compare.py (shape()), read from gol.gg timelines.
   Draft: the Worlds final game 4 (BLG blue v GEN red), champions from the lolesports feed of that game.
   1) the play-by-play of seed 2650763346037409 (the game the fork traced), read as fights (kills 20 s apart) and objectives;
   2) 1,000 seeds (1..1000): deaths per fight, fights with 6+ deaths on one side, objectives in the same second as the one before,
      seconds from the last kill to the Nexus.
   The results were copied from the browser into research/model/memory/app_sim_check.json (no run record: the browser has no lib.Run). */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE;
  const B = {top: "Gwen", jng: "Nocturne", mid: "Twisted Fate", bot: "Yunara", sup: "Neeko"}, R = {top: "Aurora", jng: "Pantheon", mid: "Akali", bot: "Xayah", sup: "Lulu"};
  const I = E.inputs(T, "BLG", "GEN", B, R), S = new E.Sim(T.P, T.cal.default);
  const mm = s => Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  const OBJ = ["tower", "inhib", "baron", "dragon", "elder", "nexus"];
  const fightsOf = o => { const K = o.steps.filter(x => x.kind === "kill"), g = []; let c = [];
    K.forEach(k => { if(c.length && k.t - c[c.length - 1].t > 20){ g.push(c); c = []; } c.push(k); }); if(c.length) g.push(c); return g; };
  const one = S.run(I.x, 2650763346037409, true);
  const trace = {winner: one.winner, length: mm(one.sec), kills: one.kills, towers: one.towers, barons: one.ba,
    fights: fightsOf(one).map(f => { const b = f.filter(k => k.side === "blue").length; return mm(f[0].t) + "-" + mm(f[f.length - 1].t) + " BLG " + b + " GEN " + (f.length - b); }),
    objectives: one.steps.filter(s => OBJ.concat(["herald", "grubs"]).includes(s.kind)).map(s => mm(s.t) + " " + (s.side === "blue" ? "BLG" : "GEN") + " " + s.kind + (s.kind === "tower" ? " " + s.text : ""))};
  let nf = 0, six = 0, same = 0, objs = 0; const sizes = {}, gap = [];
  for(let s = 1; s <= 1000; s++){ const o = S.run(I.x, s, true), g = fightsOf(o);
    g.forEach(f => { nf++; const n = Math.min(f.length, 12); sizes[n] = (sizes[n] || 0) + 1; const b = f.filter(k => k.side === "blue").length; if(b > 5 || f.length - b > 5) six++; });
    const ob = o.steps.filter(x => OBJ.includes(x.kind)); objs += ob.length; for(let i = 1; i < ob.length; i++) if(ob[i].t === ob[i - 1].t) same++;
    const nx = o.steps.find(x => x.kind === "nexus"); if(nx && g.length){ const lf = g[g.length - 1]; gap.push(nx.t - lf[lf.length - 1].t); } }
  gap.sort((a, b) => a - b);
  return JSON.stringify({trace, seeds: 1000, fights_per_game: nf / 1000, deaths_per_fight_counts: sizes, fights_6plus_one_side: six / nf,
    same_second_objective_pairs_per_game: same / 1000, objectives_per_game: objs / 1000, nexus_s_after_last_kill_median: gap[gap.length >> 1],
    nexus_over_60s_after_last_kill: gap.filter(x => x > 60).length / gap.length});
})();
