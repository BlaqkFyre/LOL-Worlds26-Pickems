/* Structure rules v1, app check (28 Nov 2026 AEST, v56; research/memory/structure-rules-plan.md, "Checks before reporting done").
   Paste into (or fetch and eval in) a tab of the app served locally. Before the build it reads the draft engine as a second copy:
   window.M27_V56 = the v56 SIM_ENGINE (research/local/memory/sim-engine_v56draft.js), loaded with
     const t = await (await fetch("research/local/memory/sim-engine_v56draft.js")).text();
     new Function(t.replace("window.SIM_ENGINE =", "window.M27_V56 ="))();
   After the build the app's own SIM_ENGINE is v56 and M27_V56 is not needed (window.M27_V55 = the v55 engine,
   research/local/memory/sim-engine_v55.js, loaded the same way, gives the replay check).
   72 Worlds drafts (WORLDS_LIVE.games, as played) x SEEDS large seeds (window.M27_SEEDS, default 50; seeds as m22).
   1. Replay: fingerprint of every game record (winner, length, steps, box score) over 72 drafts x 20 seeds: v56 with
      structure_rules "off" = v55; and with fight_window "off" too = v54 (cb7225e9 default, c993b12b alt, from m22).
   2. Rule breaks, read from each game's play-by-play by the side taking the structure: a nexus tower with no own-side inhibitor
      down at that second (fall <= t < fall + 300); the Nexus with no inhibitor down, or with a nexus tower standing (2 minus nexus
      towers fallen in the last 180 s); an inhibitor taken while that lane's is down; more than 2 nexus towers down at once.
      Window take order is not read separately (the play-by-play is sorted by time); its symptom is the first count.
   3. Shape, v56 v v55: blue win, length (quantiles, 45+, 50+), kills, towers (all tiers), inhibitors, nexus towers, Nexus falls inside
      a window (from the windows record).
   4. Worked examples: game 2 of Luke's v55 T1 v TES series (seed 3187772510790416; v55 must give red win, 2148 s, 11-22 first), and
      WORLDS_LIVE.games[0] at seed index 0 with fight_window off (v55: mid inhibitor 33:00, nexus towers 38:10 and 38:18): the base
      structures and the Nexus of each, v55 v v56.
   Results copied to research/model/memory/m27_app_check.json. */
(() => {
  const T = SIM_TABLES, A = SIM_ENGINE, B = window.M27_V56 || SIM_ENGINE, OLD = window.M27_V56 ? SIM_ENGINE : window.M27_V55;
  const SEEDS = window.M27_SEEDS || 50, MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"}, r3 = x => Math.round(x * 1000) / 1000;
  const seedOf = (gi, i) => 1099511627776 + ((gi + 1) * 1000003 + i * 2654435761) % 4503599627370496;
  const QS = [.1, .25, .5, .75, .9];
  const qq = a => { if(!a.length) return null; a.sort((x, y) => x - y); return QS.map(q => { const x = q * (a.length - 1), i = Math.floor(x); return Math.round((a[i] + ((a[i + 1] ?? a[i]) - a[i]) * (x - i)) * 10) / 10; }); };
  const side = (g, s) => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
  const drafts = WORLDS_LIVE.games.map(g => A.inputs(T, g.blue, g.red, side(g, "blue"), side(g, "red")).x);
  const lane = txt => (txt.match(/(TOP|MID|BOT)/) || [])[1];
  /* r = 0: strict on the play-by-play's whole seconds; r = 1: only breaks the rounding cannot explain (each time is floored, so the
     real second can be up to 1 s later: a boundary hit to the second is not counted) */
  const breaks = (o, r) => { const c = {nxt_no_inhib: 0, nexus_no_inhib: 0, nexus_tower_standing: 0, inhib_already_down: 0, over_2_nxt_down: 0, inhib_before_t3: 0};
    const inh = {blue: [], red: []}, nx = {blue: [], red: []}, t3 = {blue: new Set(), red: new Set()};
    for(const s of o.steps){ const sd = s.side, t = s.t; if(!sd) continue;
      const dn = inh[sd].some(([tt]) => tt <= t && t < tt + 300 + r);                         /* an inhibitor can be down at t */
      const ndMax = nx[sd].filter(x => x <= t && t < x + 180 + r).length;                      /* nexus towers that can be down at t */
      const ndMin = nx[sd].filter(x => x + r <= t && t + r < x + 180).length;                  /* nexus towers surely down at t */
      if(s.kind === "tower" && /^T3 /.test(s.text)) t3[sd].add(lane(s.text));
      if(s.kind === "inhib"){ const L = lane(s.text); if(!t3[sd].has(L)) c.inhib_before_t3++;
        if(inh[sd].some(([tt, l]) => l === L && tt + r <= t && t + r < tt + 300)) c.inhib_already_down++; inh[sd].push([t, L]); }
      else if(s.kind === "tower" && s.text === "nexus tower"){ if(!dn) c.nxt_no_inhib++; if(ndMin >= 2) c.over_2_nxt_down++; nx[sd].push(t); }
      else if(s.kind === "nexus"){ if(!dn) c.nexus_no_inhib++; if(ndMax < 2) c.nexus_tower_standing++; } }
    return c; };
  const read = (E, cal, label) => {
    const S = new E.Sim(T.P, cal); let games = 0, blue = 0, kills = 0, nexusInWindow = 0, nexusOutside = 0, chains = 0, chainTakes = 0; const lens = [], per = {tower: 0, inhib: 0, "nexus tower": 0}, BR = {}, BR0 = {}, gamesWith = {};
    drafts.forEach((x, gi) => { for(let i = 0; i < SEEDS; i++){
      const o = S.run(x, seedOf(gi, i), true); games++; if(o.winner === "blue") blue++; kills += o.kills[0] + o.kills[1]; lens.push(o.sec / 60);
      o.steps.forEach(s => { if(s.kind === "tower") per.tower++; if(s.kind === "inhib") per.inhib++; if(s.kind === "tower" && s.text === "nexus tower") per["nexus tower"]++; });
      if(o.windows && o.windows.some(w => !w.outside && w.took.includes("nexus"))) nexusInWindow++;
      if(o.windows && o.windows.some(w => w.outside && w.took.includes("nexus"))) nexusOutside++;
      if(o.windows) o.windows.filter(w => w.outside).forEach(w => { chains++; chainTakes += w.took.length; });
      const b = breaks(o, 1), b0 = breaks(o, 0); for(const k in b){ BR[k] = (BR[k] || 0) + b[k]; if(b[k]) gamesWith[k] = (gamesWith[k] || 0) + 1; BR0[k] = (BR0[k] || 0) + b0[k]; } } });
    return {label, games, "blue win": r3(blue / games), "length min (10/25/50/75/90%)": qq(lens.slice()), "45+ min": r3(lens.filter(v => v >= 45).length / games),
      "50+ min": r3(lens.filter(v => v >= 50).length / games), "kills per game": r3(kills / games),
      "per game (both sides)": Object.fromEntries(Object.entries(per).map(([k, v]) => [k, r3(v / games)])),
      "Nexus inside a window (share of games)": r3(nexusInWindow / games), "Nexus in an outside chain (share of games)": r3(nexusOutside / games),
      "outside chains per game": r3(chains / games), "takes per outside chain": chains ? r3(chainTakes / chains) : null,
      "rule breaks beyond 1 s rounding (count | games with one)": Object.fromEntries(Object.keys(BR).map(k => [k, [BR[k], gamesWith[k] || 0]])),
      "rule breaks, strict whole seconds (count)": BR0};
  };
  const fp = (S, n) => { let h = 2166136261 >>> 0; const mix = s => { for(let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } };
    drafts.forEach((x, gi) => { for(let i = 0; i < n; i++){ const o = S.run(x, seedOf(gi, i), true); mix(JSON.stringify([o.winner, o.sec, o.kills, o.steps, o.ps])); } }); return h.toString(16); };
  const OFF = {structure_rules: "off"}, OFF2 = {structure_rules: "off", fight_window: "off"}, D = T.cal.default;
  const R = {drafts: drafts.length, seeds: SEEDS, v56_engine: window.M27_V56 ? "draft copy (M27_V56)" : "app SIM_ENGINE"};
  R.replay = {};
  for(const k of ["default", "alt"]){
    const off = fp(new B.Sim(T.P, Object.assign({}, T.cal[k], OFF)), 20), off2 = fp(new B.Sim(T.P, Object.assign({}, T.cal[k], OFF2)), 20);
    R.replay[k] = {"v56 structure_rules off": off, "v56 both off": off2, "v54 (m22)": k === "default" ? "cb7225e9" : "c993b12b", "both off = v54": off2 === (k === "default" ? "cb7225e9" : "c993b12b")};
    if(OLD){ const v55 = fp(new OLD.Sim(T.P, T.cal[k]), 20); R.replay[k]["v55"] = v55; R.replay[k]["off = v55"] = off === v55; } }
  R.v56 = read(B, D, "v56 (structure_rules v1)");
  R.v56_off = read(B, Object.assign({}, D, OFF), "v56 with structure_rules off (= v55)");
  const pick = o => o.steps.filter(s => ["inhib", "nexus"].includes(s.kind) || (s.kind === "tower" && s.text === "nexus tower")).map(s => `${Math.floor(s.t / 60)}:${String(s.t % 60).padStart(2, "0")} ${s.side} ${s.text}`);
  const ex = (E, cal, x, seed) => { const o = new E.Sim(T.P, cal).run(x, seed, true); return {winner: o.winner, sec: o.sec, kills: o.kills, base: pick(o)}; };
  const g2 = A.inputs(T, "T1", "TES", {top: "Jayce", jng: "Jarvan IV", mid: "Viktor", bot: "Xayah", sup: "Poppy"},
                      {top: "K'Sante", jng: "Pantheon", mid: "Syndra", bot: "Kalista", sup: "Seraphine"}).x;
  R.examples = {"T1 v TES game 2 (seed 3187772510790416)": {v55: ex(B, Object.assign({}, D, OFF), g2, 3187772510790416), v56: ex(B, D, g2, 3187772510790416)},
                "WORLDS_LIVE.games[0], seed index 0, fight_window off": {v55: ex(B, Object.assign({}, D, OFF2), drafts[0], seedOf(0, 0)), v56: ex(B, Object.assign({}, D, {fight_window: "off"}), drafts[0], seedOf(0, 0))}};
  return JSON.stringify(R);
})();
