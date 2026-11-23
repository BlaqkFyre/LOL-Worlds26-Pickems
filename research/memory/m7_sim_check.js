/* Step 1a, sim side (24 Nov 2026 AEST; Luke OK'd): the v51 app sim's kill and assist credit, read the same way as real games in
   m7_kill_credit.py (fights = kills less than 20 s apart; sizes 1, 2, 3-4, 5-6, 7+; phases by the fight's first kill 0-14, 15-24, 25+;
   side A = the side with the fight's first kill). Paste into a tab of the app served locally (see CLAUDE.md notes sessions).
   Drafts: every game in WORLDS_LIVE.games (Swiss, quarter-finals, semi-finals), teams and champions as played, 100 seeds each (1..100),
   the app's default sim settings (SIM_TABLES.cal.default, game memory on). Kills are read from the play-by-play (kind "kill": killer k,
   victim v, assisters ast, side). The result was copied from the browser into research/model/memory/m7_sim_check.json (no run record:
   the browser has no lib.Run). */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, S = new E.Sim(T.P, T.cal.default), SEEDS = 100;
  const RL = ["top", "jng", "mid", "bot", "sup"], MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"};
  const SIZE = n => n === 1 ? "1" : n === 2 ? "2" : n <= 4 ? "3-4" : n <= 6 ? "5-6" : "7+", SIZES = ["1", "2", "3-4", "5-6", "7+"];
  const PH = t => t < 900 ? "0-14" : t < 1500 ? "15-24" : "25+";
  const r3 = x => Math.round(x * 1000) / 1000, mean = a => a.length ? a.reduce((s, x) => s + x, 0) / a.length : null;
  const K = [], PF = [], F = []; let games = 0, nami = null;
  for(const g of WORLDS_LIVE.games){
    const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    const I = E.inputs(T, g.blue, g.red, side("blue"), side("red"));
    for(let seed = 1; seed <= SEEDS; seed++){
      const o = S.run(I.x, seed, true); games++;
      const ks = o.steps.filter(x => x.kind === "kill"), fs = []; let c = [];
      ks.forEach(k => { if(c.length && k.t - c[c.length - 1].t > 20){ fs.push(c); c = []; } c.push(k); }); if(c.length) fs.push(c);
      for(const f of fs){
        const n = f.length, sz = SIZE(n), ph = PH(f[0].t), A = f[0].side, B = A === "blue" ? "red" : "blue";
        const seen = {blue: new Set(), red: new Set()}, kc = {}, ac = {}, kb = {blue: 0, red: 0};
        for(const k of f){
          const o_ = k.side === "blue" ? "red" : "blue", ast = (k.ast || []).filter(i => i !== k.k);
          seen[k.side].add(k.k); ast.forEach(i => seen[k.side].add(i)); seen[o_].add(k.v); kb[k.side]++;
          kc[k.side + k.k] = (kc[k.side + k.k] || 0) + 1; ast.forEach(i => { ac[k.side + i] = (ac[k.side + i] || 0) + 1; });
          K.push({size: sz, phase: ph, killer: RL[k.k], n_ast: ast.length, solo: ast.length ? 0 : 1, sideB: k.side !== A ? 1 : 0, ast: ast.map(i => RL[i])});
        }
        for(const s of ["blue", "red"]) for(let i = 0; i < 5; i++){
          const kk = kc[s + i] || 0, aa = ac[s + i] || 0;
          if(kk + aa > 0) PF.push({size: sz, role: RL[i], side_kills: kb[s], kills: kk, assists: aa});
          if(!nami && RL[i] === "sup" && kk >= 4) nami = {blue: g.blue, red: g.red, d: g.d, seed, fight_start: f[0].t, kills: n, sup_side: s, sup_kills: kk};
        }
        F.push({size: sz, kills_A: kb[A], kills_B: kb[B], seen_A: seen[A].size, seen_B: seen[B].size, max_one: Math.max(...Object.values(kc))});
      }
    }
  }
  const by = (a, f) => { const o = {}; a.forEach(x => { const k = f(x); (o[k] = o[k] || []).push(x); }); return o; };
  const share = x => Object.assign(Object.fromEntries(RL.map(r => [r, r3(x.filter(k => k.killer === r).length / x.length)])), {kills: x.length});
  const R = {games, drafts: WORLDS_LIVE.games.length, seeds: SEEDS, kills: K.length, fights: F.length, kills_per_game: r3(K.length / games)};
  const kS = by(K, k => k.size), kPS = by(K, k => k.phase + " | " + k.size), fS = by(F, f => f.size), pS = by(PF, p => p.role + "|" + p.size);
  R["killer role share by size"] = Object.fromEntries(SIZES.filter(s => kS[s]).map(s => [s, share(kS[s])]));
  R["killer role share by phase x size"] = Object.fromEntries(Object.keys(kPS).sort().map(k => [k, share(kPS[k])]));
  R["assists by size"] = Object.fromEntries(SIZES.filter(s => kS[s]).map(s => [s, {"assists per kill": r3(mean(kS[s].map(k => k.n_ast))), "solo share": r3(mean(kS[s].map(k => k.solo))), kills: kS[s].length}]));
  R["solo share by killer role x size"] = Object.fromEntries(RL.map(r => [r, Object.fromEntries(SIZES.filter(s => kS[s]).map(s => { const x = kS[s].filter(k => k.killer === r); return [s, x.length ? r3(mean(x.map(k => k.solo))) : null]; }))]));
  R["assist chance per kill by role x size (teammate of the killer)"] = Object.fromEntries(RL.map(r => [r, Object.fromEntries(SIZES.filter(s => kS[s]).map(s => { const x = kS[s].filter(k => k.killer !== r); return [s, r3(mean(x.map(k => k.ast.includes(r) ? 1 : 0)))]; }))]));
  R["player-fights with 2+ / 3+ / 4+ kills, by role x size (share of players credited in the fight)"] = Object.fromEntries(RL.map(r => [r, Object.fromEntries(SIZES.filter(s => pS[r + "|" + s]).map(s => { const y = pS[r + "|" + s];
    return [s, [r3(mean(y.map(p => p.kills >= 2 ? 1 : 0))), r3(mean(y.map(p => p.kills >= 3 ? 1 : 0))), r3(mean(y.map(p => p.kills >= 4 ? 1 : 0))), y.length]]; }))]));
  const sup = PF.filter(p => p.role === "sup");
  R["support: fights with 3+ kills (count, of support player-fights)"] = [sup.filter(p => p.kills >= 3).length, sup.length];
  R["support: fights with 4+ kills (count)"] = sup.filter(p => p.kills >= 4).length;
  R["a support 4+ kill fight (first found)"] = nami;
  R["max kills by one player in a fight, by size (mean)"] = Object.fromEntries(SIZES.filter(s => fS[s]).map(s => [s, r3(mean(fS[s].map(f => f.max_one)))]));
  R["fights where side B gets a kill (share, by size)"] = Object.fromEntries(SIZES.filter(s => fS[s]).map(s => [s, r3(mean(fS[s].map(f => f.kills_B > 0 ? 1 : 0)))]));
  R["players seen per side by size (mean A, mean B)"] = Object.fromEntries(SIZES.filter(s => fS[s]).map(s => [s, [r3(mean(fS[s].map(f => f.seen_A))), r3(mean(fS[s].map(f => f.seen_B)))]]));
  R["side B players seen when B gets kills, by size (mean)"] = Object.fromEntries(SIZES.filter(s => fS[s] && fS[s].some(f => f.kills_B > 0)).map(s => [s, r3(mean(fS[s].filter(f => f.kills_B > 0).map(f => f.seen_B)))]));
  for(const [nm, b] of [["B", 1], ["A", 0]]){ const x = K.filter(k => k.sideB === b); R[`side ${nm}'s kills: killer role share and solo share`] = Object.assign(share(x), {"solo share": r3(mean(x.map(k => k.solo)))}); }
  const pk = PF.filter(p => p.side_kills > 0);
  R["kill participation in the fight, players credited on a side with kills, by role x size"] = Object.fromEntries(RL.map(r => [r, Object.fromEntries(SIZES.filter(s => pS[r + "|" + s]).map(s => [s, r3(mean(pk.filter(p => p.role === r && p.size === s).map(p => (p.kills + p.assists) / p.side_kills)))]))]));
  return JSON.stringify(R);
})();
