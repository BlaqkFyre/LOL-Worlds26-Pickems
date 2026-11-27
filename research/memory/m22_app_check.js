/* Fight window v1, app check (27 Nov 2026 AEST, v55; research/memory/fight-window-plan.md part B): the app sim with fight_window "v1"
   (the default) against "off" (= v54). Paste into (or fetch and eval in) a tab of the app served locally. 72 Worlds drafts
   (WORLDS_LIVE.games, as played) x SEEDS large seeds (window.M22_SEEDS, default 100).
   Reads: blue win, game length, kills a game, objectives a game, Player of the Game by role (the winner with the highest fitted chance,
   as m18), and the window shares as m21 counts real won fights: for each won fight (the engine's own fights; players alive at the last
   kill, what was up and structures left at the fight's start, from the result's windows record), the winners' objectives from the fight's start until the next fight starts, each within 60 s of the previous one (lane towers included), and
   whether they took the Nexus, baron, dragon.
   "off" has no windows record, so its window shares are not read; its lengths, kills and objectives a game are.
   Replay check: window.M22_V54 = the v54 SIM_ENGINE (research/local/memory/sim-engine_v54.js, loaded by eval under another name); the
   fingerprint of every game record (winner, length, steps, box score) over 72 drafts x 20 seeds must match v55 with fight_window "off",
   for the default and alt sims. Results copied to research/model/memory/m22_app_check.json. */
(() => {
  const T = SIM_TABLES, E = SIM_ENGINE, SEEDS = window.M22_SEEDS || 100, RL = ["top", "jng", "mid", "bot", "sup"];
  const MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, r3 = x => Math.round(x * 1000) / 1000;
  const seedOf = (gi, i) => 1099511627776 + ((gi + 1) * 1000003 + i * 2654435761) % 4503599627370496;
  const QS = [.1, .25, .5, .75, .9];
  const qq = a => { if(!a.length) return null; a.sort((x, y) => x - y); return QS.map(q => { const x = q * (a.length - 1), i = Math.floor(x); return Math.round((a[i] + ((a[i + 1] ?? a[i]) - a[i]) * (x - i)) * 10) / 10; }); };
  const bucket = d => d >= 3 ? "ahead 3+" : d >= 1 ? "ahead 1-2" : "even or behind";
  const OBJ = {dragon: "dragon", elder: "elder", baron: "baron", herald: "herald", grubs: "grub", tower: "tower", inhib: "inhib", nexus: "nexus"};
  const drafts = WORLDS_LIVE.games.map(g => { const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
    return E.inputs(T, g.blue, g.red, side("blue"), side("red")).x; });
  const read = (cal, label) => {
    const S = new E.Sim(T.P, cal); let games = 0, blue = 0, kills = 0, capped = 0; const lens = [], POG = {top: 0, jng: 0, mid: 0, bot: 0, sup: 0}, per = {}, W = {}, wTook = {};
    const add = (key, hit) => { const c = W[key] = W[key] || [0, 0]; c[0]++; c[1] += hit ? 1 : 0; };
    drafts.forEach((x, gi) => { for(let i = 0; i < SEEDS; i++){
      const o = S.run(x, seedOf(gi, i), true); games++; if(o.winner === "blue") blue++; kills += o.kills[0] + o.kills[1]; lens.push(o.sec / 60); if(o.capped) capped++;
      o.steps.forEach(s => { const k = OBJ[s.kind]; if(k) per[k] = (per[k] || 0) + 1; });
      const mins = o.sec / 60, st = {}; RL.forEach(r => { const e = o.ps[o.winner][r]; st[r] = {k: e.k, d: e.d, a: e.a, kp: e.kp, dmgS: e.dmgS, csd: e.csd, vpm: e.vis / Math.max(1, mins)}; });
      const ch = E.pogChances(T, st); POG[RL.reduce((a, r) => ch[r] > ch[a] ? r : a, RL[0])]++;
      if(!o.windows) continue;
      const ob = o.steps.filter(s => OBJ[s.kind]);
      o.windows.forEach(w => {
        const nf = Math.min(1e9, ...o.fights.filter(f => f.f !== w.f && (f.t > w.t0 || (f.t === w.t0 && f.f > w.f))).map(f => f.t));
        let anchor = w.t1; const took = new Set();
        for(const s of ob.filter(s => s.side === w.w && s.t >= w.t0 && s.t < nf)){ if(s.t - anchor > 60) break; took.add(OBJ[s.kind]); anchor = Math.max(anchor, s.t); }
        w.took.forEach(k => { wTook[k] = (wTook[k] || 0) + 1; });
        const b = bucket(w.alive[0] - w.alive[1]);
        if(w.left != null && w.left <= 3) add(`Nexus, ${w.left} left, ${b}`, took.has("nexus"));
        if(w.up.baron) add(`baron when up, ${b}`, took.has("baron"));
        if(w.up.dragon) add(`dragon when up, ${b}`, took.has("dragon"));
        add("any objective", took.size > 0); }); } });
    const out = {label, games, "blue win": r3(blue / games), "length min (10/25/50/75/90%)": qq(lens.slice()), "45+ min": r3(lens.filter(v => v >= 45).length / games),
      "50+ min": r3(lens.filter(v => v >= 50).length / games), "capped at 70 min": capped, "kills per game": r3(kills / games),
      "objectives per game (both sides; grubs = takes, towers all tiers)": Object.fromEntries(Object.entries(per).map(([k, v]) => [k, r3(v / games)])),
      "Player of the Game by role": Object.fromEntries(RL.map(r => [r, r3(POG[r] / games)]))};
    if(Object.keys(W).length){ out["window shares (won fights, share taking it in the 60 s chain)"] = Object.fromEntries(Object.entries(W).sort().map(([k, v]) => [k, [v[0], r3(v[1] / v[0])]]));
      out["window takes per game, by option"] = Object.fromEntries(Object.entries(wTook).map(([k, v]) => [k, r3(v / games)])); }
    return out;
  };
  const fp = (S, n) => { let h = 2166136261 >>> 0; const mix = s => { for(let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } };
    drafts.forEach((x, gi) => { for(let i = 0; i < n; i++){ const o = S.run(x, seedOf(gi, i), true); mix(JSON.stringify([o.winner, o.sec, o.kills, o.steps, o.ps])); } }); return h.toString(16); };
  const OFF = {fight_window: "off"}, R = {drafts: drafts.length, seeds: SEEDS, settings: T.cal.default, window_table_cutoff: (T.window || {}).cutoff || null};
  R.v55 = read(T.cal.default, "v55 (default, fight_window v1)");
  R.v55_off = read(Object.assign({}, T.cal.default, OFF), "v55 with fight_window off (= v54)");
  if(window.M22_V54){ const V = window.M22_V54; R.replay = {};
    for(const k of ["default", "alt"]){ const a = fp(new V.Sim(T.P, T.cal[k]), 20), b = fp(new E.Sim(T.P, Object.assign({}, T.cal[k], OFF)), 20);
      R.replay[k] = {v54: a, "v55 off": b, identical: a === b}; } }
  return JSON.stringify(R);
})();
