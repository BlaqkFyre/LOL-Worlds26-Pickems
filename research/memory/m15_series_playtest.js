/* Series play-test (27 Nov 2026 AEST, Luke away: "test 100 series b5 for yesterday's update, check logs"). Paste into (or fetch and eval
   in) a tab of the app served locally. Runs N Champ Select Bo5 Fearless series through the app's own series code (startSeries,
   autoStep for both drafts, playSeriesGame, seriesText), so the series export is exercised as a user would get it. Each played game is
   replayed from its seed through the same engine to read the step list (kill by kill, structures, monsters) and checked against the
   game record. Runs in the background: window.PT holds progress; window.PT.out the results when done. window.PT_N sets the count. */
(() => {
  const N = window.PT_N || 100, IDS = TEAMS.map(t => t.id), STR = new Set(["tower", "inhib", "nexus"]), MON = new Set(["dragon", "baron", "herald", "grubs", "elder"]);
  const PT = window.PT = {done: 0, n: N, errors: [], games: [], series: [], sample: null, t0: Date.now()};
  const errLog = e => PT.errors.push(String(e && e.stack || e).slice(0, 400));
  window.addEventListener("error", e => errLog(e.error || e.message));
  let rs = 20261127; const rnd = () => (rs = (rs * 1103515245 + 12345) % 2147483648) / 2147483648;
  const gameMetrics = (g, rec) => {
    const k = SIM_CAL[simMode()], sim = SIMS[k], o = sim.run(SIM_IN.x, g.seed, true), st = o.steps;
    const same = o.winner === g.winner && o.kills[0] === g.k.blue && o.kills[1] === g.k.red && o.sec === g.time * 60 + g.sec;
    const K = st.filter(s => s.kind === "kill"), nx = st.find(s => s.kind === "nexus");
    let sorted = true; for(let i = 1; i < st.length; i++) if(st[i].t < st[i - 1].t){ sorted = false; break; }
    const F = {}; K.forEach(s => { (F[s.f] = F[s.f] || []).push(s); });
    let big = 0, bigSolo = 0, sup4 = 0, fights7 = 0;
    Object.values(F).forEach(f => { const n = f.length; if(n >= 7){ fights7++; big += n; bigSolo += f.filter(s => !s.ast.length).length; }
      ["blue", "red"].forEach(sd => { if(f.filter(s => s.side === sd && s.k === 4).length >= 4) sup4++; }); });
    const lastK = K.length ? K[K.length - 1] : null, lastWK = [...K].reverse().find(s => s.side === o.winner);
    let pairs1 = 0, pairsN = 0, kStr1 = 0, kStrN = 0;
    const obj = st.filter(s => STR.has(s.kind) || MON.has(s.kind));
    for(let i = 1; i < obj.length; i++) if(obj[i].side && obj[i].side === obj[i - 1].side){ pairsN++; if(obj[i].t - obj[i - 1].t <= 1) pairs1++; }
    st.forEach((s, i) => { if(s.kind !== "kill") return; const nxt = st.slice(i + 1).find(x => x.side === s.side && x.kind !== "kill"); if(nxt && STR.has(nxt.kind)){ kStrN++; if(nxt.t - s.t <= 1) kStr1++; } });
    return {same, sorted, sec: o.sec, kills: o.kills[0] + o.kills[1], fb: K.length ? K[0].t : null, nxLast: nx && lastK ? nx.t - lastK.t : null, nxWin: nx && lastWK ? nx.t - lastWK.t : null,
      big, bigSolo, fights7, sup4, pairs1, pairsN, kStr1, kStrN, blueWin: o.winner === "blue", pogRole: rec.pog.r, ver: SIM_TABLES ? 1 : 0};
  };
  const oneSeries = () => {
    let a = IDS[Math.floor(rnd() * IDS.length)], b; do { b = IDS[Math.floor(rnd() * IDS.length)]; } while(b === a);
    Object.assign(DS, {me: a, opp: b, sbo: 5, sfear: "yes", side: rnd() < .5 ? "blue" : "red", ai: false});
    startSeries(); clearTimeout(aiTimer);
    const G = []; let guard = 0;
    while(!seriesDone() && guard++ < 6){
      while(DS.steps.length < 20) autoStep();
      playSeriesGame(); const g = DS.sim.g, rec = DS.series.games[DS.series.games.length - 1];
      const m = gameMetrics(g, rec); m.series = PT.done; m.gi = G.length; G.push(m); PT.games.push(m);
      if(!seriesDone()){ seriesGame(); clearTimeout(aiTimer); }
    }
    const S = seriesOf("cs"), txt = seriesText(S), games = DS.series.games;
    const picks = games.flatMap(x => x.steps.filter(s => s[1] === "pick").map(s => s[2]));
    let sideOK = true; for(let i = 1; i < games.length; i++){ const loser = games[i - 1].winner === games[i - 1].blue ? games[i - 1].red : games[i - 1].blue; if(games[i].blue !== loser) sideOK = false; }
    const blocks = txt.split("```text").length - 1, pbp = (txt.match(/Play-by-play:/g) || []).length;
    let pbpSorted = true; txt.split("```text").slice(1).forEach(bk => { const L = bk.split("Play-by-play:")[1]; if(!L) return; let prev = -1;
      L.split("\n").forEach(line => { const mt = line.match(/^(\d+):(\d\d) /); if(!mt) return; const t = +mt[1] * 60 + +mt[2]; if(t < prev) pbpSorted = false; prev = t; }); });
    const wa = games.filter(x => x.winner === a).length, wb = games.filter(x => x.winner === b).length;
    PT.series.push({a, b, score: `${Math.max(wa, wb)}-${Math.min(wa, wb)}`, n: games.length, fearlessOK: new Set(picks).size === picks.length, sideOK,
      blocks, pbp, pbpSorted, mvp: /\*\*Series MVP:\*\*/.test(txt), chars: txt.length, nan: /NaN|undefined/.test(txt)});
    if(!PT.sample) PT.sample = txt;
  };
  const summary = () => {
    const G = PT.games, q = (a, p) => { a = a.filter(x => x != null).sort((x, y) => x - y); if(!a.length) return null; const x = p * (a.length - 1), i = Math.floor(x); return Math.round((a[i] + ((a[i + 1] ?? a[i]) - a[i]) * (x - i)) * 10) / 10; };
    const Q = a => [.1, .25, .5, .75, .9].map(p => q(a, p)), sh = (f) => Math.round(1000 * G.filter(f).length / G.length) / 10, sum = f => G.reduce((t, g) => t + f(g), 0);
    const roles = {}; G.forEach(g => { roles[g.pogRole] = (roles[g.pogRole] || 0) + 1; }); Object.keys(roles).forEach(r => { roles[r] = Math.round(1000 * roles[r] / G.length) / 10; });
    const sc = {}; PT.series.forEach(s => { sc[s.score] = (sc[s.score] || 0) + 1; });
    return {version: (document.querySelector('script[src*="core.js"]').src.match(/v=(\d+)/) || [])[1], sim: simMode(), series: PT.series.length, games: G.length, seconds: Math.round((Date.now() - PT.t0) / 1000),
      errors: PT.errors, "replay matches record": G.filter(g => g.same).length, "steps in time order": G.filter(g => g.sorted).length,
      "series scores": sc, "Fearless repeats (series with a repeat pick)": PT.series.filter(s => !s.fearlessOK).length, "loser took blue (series OK)": PT.series.filter(s => s.sideOK).length,
      "export: series with a play-by-play block for every game": PT.series.filter(s => s.blocks === s.n && s.pbp === s.n).length, "export: play-by-play in time order": PT.series.filter(s => s.pbpSorted).length,
      "export: Series MVP line": PT.series.filter(s => s.mvp).length, "export: NaN/undefined in text": PT.series.filter(s => s.nan).length, "export: median size (chars)": q(PT.series.map(s => s.chars), .5),
      "length min (10/25/50/75/90%)": Q(G.map(g => g.sec / 60)), "45+ min %": sh(g => g.sec >= 2700), "50+ min %": sh(g => g.sec >= 3000), "under 25 min %": sh(g => g.sec < 1500),
      "kills per game (10/25/50/75/90%)": Q(G.map(g => g.kills)), "first blood s (10/50/90%)": [q(G.map(g => g.fb), .1), q(G.map(g => g.fb), .5), q(G.map(g => g.fb), .9)],
      "first blood before 0:30 / 1:00 / 3:00 %": [sh(g => g.fb != null && g.fb < 30), sh(g => g.fb != null && g.fb < 60), sh(g => g.fb != null && g.fb < 180)],
      "Nexus from the last kill s (10/25/50/75/90%)": Q(G.map(g => g.nxLast)), "Nexus from the winner's last kill s (10/25/50/75/90%)": Q(G.map(g => g.nxWin)), "Nexus 60 s+ after the last kill %": sh(g => g.nxLast != null && g.nxLast >= 60),
      "7+ kill fights": sum(g => g.fights7), "solo share of kills in 7+ kill fights": Math.round(1000 * sum(g => g.bigSolo) / Math.max(1, sum(g => g.big))) / 1000,
      "support 4+ kills in one fight (count)": sum(g => g.sup4), "same-team objective pairs within 1 s": Math.round(1000 * sum(g => g.pairs1) / Math.max(1, sum(g => g.pairsN))) / 1000,
      "own kill then structure within 1 s": Math.round(1000 * sum(g => g.kStr1) / Math.max(1, sum(g => g.kStrN))) / 1000, "blue win %": sh(g => g.blueWin), "Player of the Game by role %": roles};
  };
  const loop = () => { if(PT.done >= N){ PT.out = summary(); return; }
    try { oneSeries(); } catch(e){ errLog(e); } PT.done++; setTimeout(loop, 0); };
  setTimeout(loop, 0);
  return `started ${N} series`;
})();
