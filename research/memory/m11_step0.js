/* Timing fixes, step 0 (24 Nov 2026 AEST; Luke OK'd): diagnosis in a tab of the app served locally (fetch and eval; changes nothing on
   disk). Three parts:
   A. the app sim on the 72 Worlds drafts x 100 seeds with the event-order clock on (default) and off (cal.event_order "off": every
      event keeps the time it was drawn at): fights starting in minutes 0-4 (per game, start seconds), first blood times, kills per
      10 s up to 3:00, same-team gaps within 1 s (monster/structure pairs and kill then objective);
   B. a traced copy of js/sim-engine.js (its at() clock patched to remember each event's drawn time; loaded under another name, so the
      app's engine is untouched) replaying Luke's v53 Bo5 game 4 (T1 blue v BLG red, seed 539665242367511, the draft from his paste):
      every event from 23:40 to 24:40 with its drawn and placed time;
   C. where the sim's kills at 0:30-0:39 come from: the start second of each minute-0 fight and its kills.
   Results copied by hand to research/model/memory/m11_step0.json. */
(async () => {
  const T = SIM_TABLES, E = SIM_ENGINE, SEEDS = 100, MAP = {TOP: "top", JGL: "jng", MID: "mid", ADC: "bot", SUP: "sup"};
  const MON = new Set(["dragon", "elder", "baron", "herald"]), STR = new Set(["tower", "inhib", "nexus"]);
  const r3 = x => Math.round(x * 1000) / 1000, q = (a, p) => a.length ? a[Math.min(a.length - 1, Math.floor(p * a.length))] : null;
  const part = (extra) => {
    const S = new E.Sim(T.P, Object.assign({}, T.cal.default, extra)); let games = 0; const fbs = [], bins = new Array(18).fill(0), G = {}, FM = [[], [], [], [], []], m0 = [];
    for(const g of WORLDS_LIVE.games){
      const side = s => { const o = {}; g.pl[s].forEach(p => { o[MAP[p[0]]] = p[2]; }); return o; };
      const I = E.inputs(T, g.blue, g.red, side("blue"), side("red"));
      for(let seed = 1; seed <= SEEDS; seed++){
        const o = S.run(I.x, seed, true); games++;
        const ks = o.steps.filter(x => x.kind === "kill"); if(ks.length) fbs.push(Math.min(...ks.map(k => k.t)));
        ks.forEach(k => { if(k.t < 180) bins[Math.floor(k.t / 10)]++; });
        o.fights.forEach(f => { const m = Math.floor(f.t / 60); if(m < 5) FM[m].push(f.t - 60 * m); if(m === 0) m0.push([f.t, f.b + f.r]); });
        for(const sd of ["blue", "red"]){
          const ev = o.steps.filter(x => x.side === sd && (MON.has(x.kind) || STR.has(x.kind) || x.kind === "kill"));
          for(let i = 1; i < ev.length; i++){
            if(ev[i].kind === "kill") continue;
            const a = ev[i - 1].kind === "kill" ? "kill" : MON.has(ev[i - 1].kind) ? "monster" : "structure", b = MON.has(ev[i].kind) ? "monster" : "structure";
            (G[a + " then " + b] = G[a + " then " + b] || []).push(ev[i].t - ev[i - 1].t);
          }
        }
      }
    }
    fbs.sort((a, b) => a - b); FM.forEach(a => a.sort((x, y) => x - y));
    return {games, "fights starting in minutes 0-4": FM.map((a, m) => ({minute: m, "fights per game": r3(a.length / games), "start second quantiles 10, 25, 50, 75, 90%": [.1, .25, .5, .75, .9].map(p => q(a, p))})),
      "first blood before 0:30 / 1:00 / 2:00": [30, 60, 120].map(s => r3(fbs.filter(x => x < s).length / fbs.length)), "first blood median s": q(fbs, .5),
      "kills per game by 10 s, 0:00-3:00": bins.map(b => r3(b / games)),
      "same-team pairs within 1 s (and median s)": Object.fromEntries(Object.entries(G).map(([p, a]) => { a.sort((x, y) => x - y); return [p, [r3(a.filter(x => x <= 1).length / a.length), q(a, .5), a.length]]; })),
      "minute-0 fights: start second of the fight (counts by 10 s) and kills in them": (() => { const c = new Array(6).fill(0); let k = 0; m0.forEach(([t, n]) => { c[Math.min(5, Math.floor(t / 10))]++; k += n; }); return {fights: m0.length, "by 10 s": c, kills: k}; })()};
  };
  const R = {"A. clock on (default)": part({}), "A. clock off (event_order off)": part({event_order: "off"})};
  /* B: traced engine */
  let src = await (await fetch("/js/sim-engine.js?trace=" + Date.now())).text();
  const AT = "const at = d => !EO ? d : (cur = (MT && cur > 0 && d <= cur) ? cur + 1 : Math.max(cur, d));";
  if(!src.includes(AT)) return JSON.stringify({error: "at() line not found; trace not run", R});
  src = src.replace(AT, "const at = d => { const p_ = !EO ? d : (cur = (MT && cur > 0 && d <= cur) ? cur + 1 : Math.max(cur, d)); window.__RAW[Math.floor(p_)] = d; return p_; };")
           .replace("window.SIM_ENGINE = {", "window.SIM_ENGINE_TRACE = {");
  (0, eval)(src); const ET = window.SIM_ENGINE_TRACE; window.__RAW = {};
  const B = {top: "Rumble", jng: "Wukong", mid: "Anivia", bot: "Zeri", sup: "Yuumi"}, Rd = {top: "Ornn", jng: "Pantheon", mid: "Viktor", bot: "Varus", sup: "Bard"};
  const I = ET.inputs(T, "T1", "BLG", B, Rd), o = new ET.Sim(T.P, T.cal.default).run(I.x, 539665242367511, true);
  const mm = s => Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
  R["B. game 4 replay"] = {winner: o.winner, length: mm(o.sec), kills: o.kills, "matches Luke's paste (BLG win in 38:41, kills 6-21)": o.winner === "red" && mm(o.sec) === "38:41" && o.kills[0] === 6 && o.kills[1] === 21,
    "events 23:40-24:40 [placed, drawn, side, kind, text]": o.steps.filter(x => x.t >= 1420 && x.t <= 1480).map(x => [mm(x.t), window.__RAW[x.t] != null ? mm(window.__RAW[x.t]) + (window.__RAW[x.t] % 1 ? "." + String(Math.round((window.__RAW[x.t] % 1) * 10)) : "") : "?", x.side, x.kind, x.text])};
  delete window.SIM_ENGINE_TRACE; delete window.__RAW;
  return JSON.stringify(R);
})();
