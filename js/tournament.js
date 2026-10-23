/* =====================================================================
   Tournament mode: Worlds 2026 Swiss stage + knockouts, with a live
   stats pool that feeds later drafts, LCK-style Player of the Game,
   and tournament awards. Loaded before core.js; only calls core
   functions at run time.
   ===================================================================== */
const SAVE_KEY = "lolw26-pickems-run-v1";
const BASE_GAMES = 40; // weight of the pre-Worlds pro presence (blended 26.20 + 26.16–26.20 tables) against this run's own games

/* Real Swiss round 1 draw (Dot Esports / Insider Gaming). First team listed = higher seed. */
const R1_DRAW = [["GEN","IG"],["TL","CFO"],["AL","KC"],["G2","DK"],["HLE","TES"],["LOS","T1"],["TSW","LYON"],["BLG","MKOI"]];

/* Schedule (accountshark.net reading of Riot's dates; how multi-day rounds split is assumed). */
const DAYS = [
  {date:"Fri 23 Oct", label:"Swiss round 1", phase:"swiss", round:1},
  {date:"Sat 24 Oct", label:"Swiss round 2", phase:"swiss", round:2},
  {date:"Sun 25 Oct", label:"Swiss round 3 (day 1)", phase:"swiss", round:3},
  {date:"Mon 26 Oct", label:"Swiss round 3 (day 2)", phase:"swiss", round:3},
  {date:"Wed 28 Oct", label:"Swiss round 4 (day 1)", phase:"swiss", round:4},
  {date:"Thu 29 Oct", label:"Swiss round 4 (day 2)", phase:"swiss", round:4},
  {date:"Fri 30 Oct", label:"Swiss round 4 (day 3)", phase:"swiss", round:4},
  {date:"Sat 31 Oct", label:"Swiss round 5", phase:"swiss", round:5},
  {date:"Tue 3 Nov", label:"Quarter-final 1", phase:"ko", stage:"QF", idx:0},
  {date:"Wed 4 Nov", label:"Quarter-final 2", phase:"ko", stage:"QF", idx:1},
  {date:"Thu 5 Nov", label:"Quarter-final 3", phase:"ko", stage:"QF", idx:2},
  {date:"Fri 6 Nov", label:"Quarter-final 4", phase:"ko", stage:"QF", idx:3},
  {date:"Sat 7 Nov", label:"Semi-final 1", phase:"ko", stage:"SF", idx:0},
  {date:"Sun 8 Nov", label:"Semi-final 2", phase:"ko", stage:"SF", idx:1},
  {date:"Sat 14 Nov", label:"Grand final", phase:"ko", stage:"F", idx:0}
];
const MODES = {
  teams: {name:"My teams", desc:"Pick 1–4 teams. You draft their games (the AI drafts the other side); every other match is AI vs AI."},
  sim:   {name:"Sim run", desc:"The AI drafts and plays every match. You move through the event day by day."},
  guest: {name:"My team + guest picks", desc:"Pick one team. In every other match you draft for a randomly assigned side, or switch to AI until your team plays again."}
};

let RUN = null;
let TV = "today";        // tournament sub-view
let tourConfirmNew = false;
let tourOpen = {};       // expanded result rows

/* ---------- save / load ---------- */
function loadRun(){ try{ const s = localStorage.getItem(SAVE_KEY); if(s){ RUN = sanitizeRun(JSON.parse(s)); drawDay(); } }catch(e){ RUN = null; } }
function saveRun(){ if(!RUN) return; RUN.updated = Date.now(); try{ localStorage.setItem(SAVE_KEY, JSON.stringify(RUN)); }catch(e){} }
function clearRun(){ RUN = null; try{ localStorage.removeItem(SAVE_KEY); }catch(e){} }

/* ---------- live stats pool ---------- */
function tourPres(c, base){
  if(!RUN || !RUN.stats.games) return base;
  const st = RUN.stats.champ[c], G = RUN.stats.games;
  const tp = st ? (st.p + st.b) / G * 100 : 0;
  return Math.round((base * BASE_GAMES + tp * G) / (BASE_GAMES + G));
}
function tourPool(p){
  if(!RUN) return p.picks;
  const pc = RUN.stats.pchamp[p.key]; if(!pc) return p.picks;
  const out = p.picks.map(x => [...x]);
  Object.entries(pc).forEach(([c, v]) => {
    const e = out.find(x => x[0] === c);
    if(e){ const g0 = e[1] || 5, w0 = (e[2] || 50) / 100 * g0; e[1] = g0 + v.g; e[2] = Math.round((w0 + v.w) / (g0 + v.g) * 100); }
    else if(v.g >= 1) out.push([c, v.g, Math.round(v.w / v.g * 100)]);
  });
  return out;
}
function tourPlayerLine(p){
  if(!RUN) return "";
  const s = RUN.stats.players[p.key]; if(!s || !s.g) return "";
  const pc = RUN.stats.pchamp[p.key] || {};
  const champs = Object.entries(pc).sort((a,b) => b[1].g - a[1].g).map(([c,v]) => `${esc(c)} ${v.w}-${v.g - v.w}`).join(", ");
  return `<div class="here">At this Worlds: ${s.g} games · KDA ${kdaOf(s)} · rating ${(s.rt / s.g).toFixed(1)} · ${s.pog} POG${champs ? `<br><span class="notes">${champs}</span>` : ""}</div>`;
}
const kdaOf = s => ((s.k + s.a) / Math.max(1, s.d)).toFixed(1);

/* ---------- per-player game stats + Player of the Game ----------
   POG rating mirrors the numbers that separate LCK POG winners:
   result, KDA and deaths, kill participation, damage share (vs role
   norm), lane lead at 15 (CS), solo kills, vision for supports and
   objective control for junglers/supports. Normally only the winning side is
   eligible, as with LCK POG votes, unless a losing player out-rates the
   winners' best by LOSER_POG_GAP or more. Each POG earns 100 POG points. */
const LOSER_POG_GAP = 1.1;  // rating points a losing player must beat the winners' best by to take POG
const ROLE_DMG = {TOP:1.0, JGL:0.8, MID:1.25, ADC:1.35, SUP:0.45};
const ROLE_SHARE = {TOP:0.22, JGL:0.15, MID:0.27, ADC:0.29, SUP:0.07};
/* Role balance (tuned so POG shares by role look like the LCK, where supports rarely lead POG points):
   supports' damage share caps at their role norm, vision only scores above a normal 2.0/min, objectives
   count more for junglers than supports, kills earn a little on their own, and a small final role adjustment. */
const DMG_CAP = {TOP:1.6, JGL:1.6, MID:1.6, ADC:1.6, SUP:1.3};
const OBJ_W = {TOP:0, JGL:0.10, MID:0, ADC:0, SUP:0.10};
const ROLE_ADJ = {TOP:1.05, JGL:0.98, MID:0.98, ADC:0.98, SUP:0.97};
function gameStats(g){
  const opp = s => s === "blue" ? "red" : "blue";
  g.ps = {blue:{}, red:{}};
  ["blue","red"].forEach(s => {
    const T = s === "blue" ? g.B : g.R, won = g.winner === s, sign = s === "blue" ? 1 : -1;
    let dmgTot = 0;
    ROLES.forEach(r => {
      const [k,d,a] = g.kda[s][r], pl = T.P[r].pl;
      const dmgAttr = r === "MID" ? pl.a[2] : r === "ADC" ? pl.a[1] : r === "TOP" ? pl.a[1] : r === "JGL" ? pl.a[2] : pl.a[1];
      const dmg = ROLE_DMG[r] * (1 + 0.08 * (2 * k + a)) * (1 + (dmgAttr - 80) / 100) * (0.85 + Math.random() * 0.3) * g.time * 520;
      dmgTot += dmg;
      const laneD = r === "TOP" ? g.lanes.TOP : r === "MID" ? g.lanes.MID : r === "JGL" ? g.jd * 0.6 : g.lanes.BOT * (r === "SUP" ? 0.3 : 1);
      const csd = Math.max(-35, Math.min(35, Math.round(sign * laneD * 2.6 + gauss() * 4))) * (r === "SUP" ? 0.3 : 1);
      const vis = r === "SUP" ? 2.0 + (pl.a[1] - 80) / 40 + gauss() * 0.2 : r === "JGL" ? 1.3 + gauss() * 0.15 : 0.85 + gauss() * 0.12;
      const objs = g.dr[s] + g.gr[s] + g.ba[s];
      g.ps[s][r] = {k, d, a, dmg, csd: Math.round(csd), vis: Math.round(vis * 100) / 100, solo: g.solo[s][r] || 0, objs, won};
    });
    ROLES.forEach(r => {
      const p = g.ps[s][r], tk = Math.max(1, g.k[s]);
      p.kp = Math.min(1, (p.k + p.a) / tk);
      p.dmgS = p.dmg / dmgTot;
      const kda = (p.k + p.a) / Math.max(1, p.d);
      let rt = (p.won ? 1.5 : 0)
        + 2.0 * Math.min(kda, 10) / 10
        + 2.0 * p.kp
        + 0.12 * Math.min(p.k, 10)
        + 1.6 * Math.min(DMG_CAP[r], p.dmgS / ROLE_SHARE[r])
        + 0.9 * Math.max(-1, Math.min(1, p.csd / 20))
        + 0.5 * p.solo
        + (r === "SUP" ? 0.5 * Math.max(0, p.vis - 2.0) : 0)
        + OBJ_W[r] * p.objs
        - 0.15 * p.d;
      /* outliers (rated 90+, e.g. Keria, Chovy, Canyon) earn a little extra, as LCK POG voting rewards standout players */
      const ovp = (s === "blue" ? g.B : g.R).P[r].pl.ov;
      rt += STAR.pog * Math.max(0, ovp - 90) / 6;
      p.rt = Math.max(0, Math.min(10, rt * ROLE_ADJ[r]));
    });
  });
  /* POG normally goes to the winning side; a losing player takes it only with a rating at least LOSER_POG_GAP higher than the winners' best */
  const top = sd => ROLES.map(r => ({r, p: g.ps[sd][r]})).sort((x,y) => y.p.rt - x.p.rt)[0];
  const lw = g.winner === "blue" ? "red" : "blue", bw = top(g.winner), bl = top(lw);
  const w = bl.p.rt - bw.p.rt >= LOSER_POG_GAP ? lw : g.winner, T = w === "blue" ? g.B : g.R;
  const best = w === g.winner ? bw : bl;
  const p = best.p, why = [];
  why.push(`${p.k}/${p.d}/${p.a}`);
  why.push(`${Math.round(p.kp * 100)}% KP`);
  if(p.dmgS > ROLE_SHARE[best.r] * 1.1) why.push(`${Math.round(p.dmgS * 100)}% team damage`);
  if(p.csd >= 8) why.push(`+${p.csd} CS at 15`);
  if(p.solo) why.push(`${p.solo} solo kill${p.solo > 1 ? "s" : ""}`);
  if(best.r === "SUP") why.push(`${p.vis} vision/min`);
  if(w !== g.winner) why.push("from the losing side");
  g.pog = {s: w, r: best.r, n: T.P[best.r].pl.n, c: T.P[best.r].c, rt: p.rt, why: why.join(" · ")};
}

/* ---------- run setup ---------- */
function newRun(mode, myTeams){
  RUN = {v:1, mode, myTeams, guestAI:false, day:0, matches:[], W:{}, L:{}, met:[],
    stats:{games:0, champ:{}, pchamp:{}, players:{}, crole:{}}, created:Date.now(), updated:Date.now()};
  TEAMS.forEach(t => { RUN.W[t.id] = 0; RUN.L[t.id] = 0; });
  drawDay(); saveRun();
}
const M = id => RUN.matches.find(m => m.id === id);
const dayMatches = d => RUN.matches.filter(m => m.day === d);
const roundMatches = r => RUN.matches.filter(m => m.phase === "swiss" && m.round === r);
const alive = id => RUN.W[id] < 3 && RUN.L[id] < 3;
function shuffleA(a){ for(let i = a.length - 1; i > 0; i--){ const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function pairUp(ids){
  const met = new Set(RUN.met);
  for(let t = 0; t < 300; t++){
    const s = shuffleA([...ids]), out = []; let ok = true;
    for(let i = 0; i < s.length; i += 2){ if(met.has(s[i] + "|" + s[i+1])){ ok = false; break; } out.push([s[i], s[i+1]]); }
    if(ok) return out;
  }
  const s = shuffleA([...ids]), out = []; for(let i = 0; i < s.length; i += 2) out.push([s[i], s[i+1]]); return out;
}
function mk(id, extra){ return Object.assign({id, games:[], status:"pending", ctrl:null}, extra); }
function createSwissRound(r){
  let groups;
  if(r === 1) groups = [["0-0", R1_DRAW]];
  else {
    const g = {};
    TEAMS.forEach(t => { if(alive(t.id)){ const k = RUN.W[t.id] + "-" + RUN.L[t.id]; (g[k] = g[k] || []).push(t.id); } });
    groups = Object.keys(g).sort((a,b) => (+b[0] - +a[0]) || (+a[2] - +b[2])).map(k => [k, pairUp(g[k])]);
  }
  const list = [];
  groups.forEach(([k, pairs]) => pairs.forEach(([a,b]) => {
    const [w,l] = k.split("-").map(Number);
    const hi = r === 1 ? a : (team(a).ov >= team(b).ov ? a : b), lo = hi === a ? b : a;
    list.push({a:hi, b:lo, bo:(w === 2 || l === 2) ? 3 : 1, rec:k});
  }));
  const dayOf = i => r === 1 ? 0 : r === 2 ? 1 : r === 3 ? (i < 4 ? 2 : 3) : r === 4 ? 4 + Math.floor(i / 2) : 7;
  list.forEach((x, i) => RUN.matches.push(mk(`S${r}-${i+1}`, {phase:"swiss", round:r, day:dayOf(i), a:x.a, b:x.b, bo:x.bo, rec:x.rec})));
}
function createQF(){
  const ids = TEAMS.map(t => t.id);
  const t30 = shuffleA(ids.filter(id => RUN.W[id] === 3 && RUN.L[id] === 0));
  const t31 = ids.filter(id => RUN.W[id] === 3 && RUN.L[id] === 1);
  const t32 = shuffleA(ids.filter(id => RUN.W[id] === 3 && RUN.L[id] === 2));
  const rest = shuffleA([...t31, ...t32.slice(2)]);
  const pairs = [[t30[0], t32[0]], [rest[0], rest[1]], [t30[1], t32[1]], [rest[2], rest[3]]];
  pairs.forEach(([a,b], i) => RUN.matches.push(mk(`QF${i+1}`, {phase:"ko", stage:"QF", idx:i, day:8 + i, a, b, bo:5})));
}
function koWinner(id){ const m = M(id); return m && m.status === "done" ? m.w : null; }
function drawDay(){
  const D = DAYS[RUN.day]; if(!D) return;
  if(D.phase === "swiss"){
    if(!roundMatches(D.round).length && (D.round === 1 || roundMatches(D.round - 1).every(m => m.status === "done"))) createSwissRound(D.round);
  } else if(D.stage === "QF"){
    if(!M("QF1")) createQF();
  } else if(D.stage === "SF"){
    const id = `SF${D.idx + 1}`;
    if(!M(id)){ const a = koWinner(`QF${D.idx * 2 + 1}`), b = koWinner(`QF${D.idx * 2 + 2}`); if(a && b) RUN.matches.push(mk(id, {phase:"ko", stage:"SF", idx:D.idx, day:RUN.day, a, b, bo:5})); }
  } else if(D.stage === "F"){
    if(!M("F")){ const a = koWinner("SF1"), b = koWinner("SF2"); if(a && b) RUN.matches.push(mk("F", {phase:"ko", stage:"F", idx:0, day:RUN.day, a, b, bo:5})); }
  }
}

/* ---------- who drafts ---------- */
function ctrlOf(m){
  if(!RUN || m.status === "done") return null;
  const mine = RUN.myTeams.find(id => id === m.a || id === m.b);
  if(RUN.mode === "sim") return null;
  if(mine) return mine;
  if(RUN.mode === "guest" && !RUN.guestAI){ if(!m.ctrl){ m.ctrl = Math.random() < 0.5 ? m.a : m.b; saveRun(); } return m.ctrl; }
  return null;
}
/* Game 1: higher seed (round 1) or higher-rated team has First Selection and takes blue; after that the loser of the previous game takes blue. */
function blueFor(m, gi){ if(gi === 0) return m.a; const last = m.games[gi - 1]; return last.winner === m.a ? m.b : m.a; }
function lockedFor(m){ return m.bo > 1 ? m.games.flatMap(g => g.steps.filter(s => s[1] === "pick").map(s => s[2])) : []; }
const seriesWins = (m, id) => m.games.filter(g => g.winner === id).length;
function stageName(m){ return m.phase === "swiss" ? `Swiss R${m.round} · ${m.rec} pool` : m.stage === "QF" ? `Quarter-final ${m.idx + 1}` : m.stage === "SF" ? `Semi-final ${m.idx + 1}` : "Grand final"; }

/* ---------- drafting/simulating with the shared engine ---------- */
function withDS(cfg, fn){
  const save = Object.assign({}, DS, {steps:[...DS.steps], locked:[...DS.locked]});
  Object.assign(DS, {me:cfg.blue, opp:cfg.red, side:"blue", fp:"blue", fmt:cfg.fmt, locked:cfg.locked, steps:[], ai:false, tour:null, sim:null});
  try{ return fn(); } finally { Object.assign(DS, save); }
}
function autoStep(){
  const i = DS.steps.length, [k, kind] = SEQ[i], actor = actorId(k);
  const r = recs(); let c;
  if(r.length){ const x = Math.random(); c = r[Math.min(r.length - 1, x < 0.6 ? 0 : x < 0.85 ? 1 : 2)].c; }
  else { const tk = taken(), open = openRoles(actor); c = POOL.find(ch => !tk.has(ch) && (kind === "ban" || [...ROLEMAP[ch]].some(rr => open.includes(rr)))) || POOL.find(ch => !tk.has(ch)); }
  const st = {t:actor, k:kind, c};
  if(kind === "pick"){ const open = openRoles(actor); st.r = [...(ROLEMAP[c] || [])].find(rr => open.includes(rr)) || open[0]; }
  DS.steps.push(st);
}
function pack(g){
  const blue = idOnSide("blue"), red = idOnSide("red");
  const ps = {}; ["blue","red"].forEach(s => { ps[s] = {}; ROLES.forEach(r => { const p = g.ps[s][r]; ps[s][r] = {c:(s === "blue" ? g.B : g.R).P[r].c, k:p.k, d:p.d, a:p.a, kp:+p.kp.toFixed(3), dmgS:+p.dmgS.toFixed(3), csd:p.csd, vis:p.vis, solo:p.solo, rt:+p.rt.toFixed(2)}; }); });
  return {blue, red, winner: g.winner === "blue" ? blue : red, time:g.time, sec:g.sec, kills:{...g.k},
    steps: DS.steps.map(s => [s.t, s.k, s.c, s.r || ""]), ps, pog:{...g.pog, team: g.pog.s === "blue" ? blue : red},
    dr:{...g.dr}, ba:{...g.ba}, g15:(g.gl.find(x => x[0] >= 14) || [0,0])[1]};
}
function playAIGame(m){
  const gi = m.games.length, blue = blueFor(m, gi), red = blue === m.a ? m.b : m.a;
  const rec = withDS({blue, red, fmt: m.bo > 1 ? "fearless" : "bo1", locked: lockedFor(m)}, () => { while(DS.steps.length < 20) autoStep(); return pack(simGame(false)); });
  recordGame(m, rec);
}
function addGameStats(S, m, rec){
  S.games++;
  rec.steps.forEach(([t, k, c]) => { const st = S.champ[c] = S.champ[c] || {p:0, b:0, w:0}; if(k === "ban") st.b++; else { st.p++; if(t === rec.winner) st.w++; } });
  ["blue","red"].forEach(s => {
    const tid = s === "blue" ? rec.blue : rec.red, won = rec.winner === tid;
    ROLES.forEach((r, i) => {
      const key = tid + "|" + i, p = rec.ps[s][r];
      const P = S.players[key] = S.players[key] || {g:0, w:0, k:0, d:0, a:0, kp:0, dmgS:0, csd:0, vis:0, solo:0, rt:0, pog:0, pts:0, swissPts:0, finRt:[]};
      P.g++; if(won) P.w++; ["k","d","a","kp","dmgS","csd","vis","solo","rt"].forEach(f => P[f] += p[f]);
      if(m.stage === "F") P.finRt.push(p.rt);
      const pc = (S.pchamp[key] = S.pchamp[key] || {}); const e = pc[p.c] = pc[p.c] || {g:0, w:0}; e.g++; if(won) e.w++;
      const cr = (S.crole[p.c + "|" + r] = S.crole[p.c + "|" + r] || {p:0, w:0}); cr.p++; if(won) cr.w++;
    });
  });
  const P = S.players[rec.pog.team + "|" + ROLES.indexOf(rec.pog.r)]; P.pog++; P.pts += 100; if(m.phase === "swiss") P.swissPts += 100;
}
function settleMatch(m, run){
  const need = Math.ceil(m.bo / 2), wa = seriesWins(m, m.a), wb = seriesWins(m, m.b);
  if(wa >= need || wb >= need){
    m.status = "done"; m.w = wa > wb ? m.a : m.b; m.l = m.w === m.a ? m.b : m.a; m.sc = `${Math.max(wa,wb)}-${Math.min(wa,wb)}`;
    if(m.phase === "swiss"){ run.W[m.w]++; run.L[m.l]++; run.met.push(m.a + "|" + m.b, m.b + "|" + m.a); }
    return true;
  }
  return false;
}
function recordGame(m, rec){
  m.games.push(rec);
  addGameStats(RUN.stats, m, rec);
  if(settleMatch(m, RUN) && RUN.mode === "guest" && RUN.myTeams.some(id => id === m.a || id === m.b)) RUN.guestAI = false;
  saveRun();
}

/* ---------- import / load safety ----------
   A run file (or saved run) is untrusted. Rebuild it from scratch: every
   field is type-checked against known teams, roles, champions and match
   ids, numbers are clamped, text is regenerated from the app's own data,
   and standings and stats are recomputed from the games rather than read
   from the file. Anything that doesn't fit is rejected. */
const IDS = new Set(TEAMS.map(t => t.id));
const MATCH_ID = /^(S[1-5]-[1-8]|QF[1-4]|SF[12]|F)$/;
const CHAMP_RE = /^[A-Za-z][A-Za-z' .&]{0,23}$/;
const num = (v, lo, hi, dp) => { const n = Number(v); if(!Number.isFinite(n)) throw new Error("number"); const c = Math.min(hi, Math.max(lo, n)); return dp == null ? Math.round(c) : +c.toFixed(dp); };
const tid = v => { if(typeof v !== "string" || !IDS.has(v)) throw new Error("team"); return v; };
const champ = v => { if(typeof v !== "string" || !CHAMP_RE.test(v)) throw new Error("champ"); return v; };
const arr = (v, max) => { if(!Array.isArray(v) || v.length > max) throw new Error("array"); return v; };
function cleanGame(g, m){
  const blue = tid(g.blue), red = tid(g.red), winner = tid(g.winner);
  if(new Set([blue, red, m.a, m.b]).size !== 2 || (winner !== blue && winner !== red)) throw new Error("game teams");
  const steps = arr(g.steps, 20).map(x => { arr(x, 4); const t = tid(x[0]); if(t !== blue && t !== red) throw new Error("step team"); const k = x[1] === "ban" ? "ban" : x[1] === "pick" ? "pick" : null; if(!k) throw new Error("step kind"); const r = k === "pick" ? (ROLES.includes(x[3]) ? x[3] : (() => { throw new Error("role"); })()) : ""; return [t, k, champ(x[2]), r]; });
  const ps = {};
  ["blue","red"].forEach(s => { ps[s] = {}; ROLES.forEach(r => { const p = (g.ps && g.ps[s] && g.ps[s][r]) || null; if(!p) throw new Error("player stats");
    ps[s][r] = {c:champ(p.c), k:num(p.k,0,40), d:num(p.d,0,40), a:num(p.a,0,60), kp:num(p.kp,0,1,3), dmgS:num(p.dmgS,0,1,3), csd:num(p.csd,-60,60), vis:num(p.vis,0,6,2), solo:num(p.solo,0,10), rt:num(p.rt,0,10,2)}; }); });
  const pog = g.pog || {}, ps2 = pog.s === "blue" || pog.s === "red" ? pog.s : null, pr = ROLES.includes(pog.r) ? pog.r : null;
  if(!ps2 || !pr) throw new Error("pog");
  const pteam = ps2 === "blue" ? blue : red;
  if(pteam !== winner){ const wbest = Math.max(...ROLES.map(r => ps[winner === blue ? "blue" : "red"][r].rt)); if(ps[ps2][pr].rt - wbest < LOSER_POG_GAP - 0.01) throw new Error("pog side"); }
  const ex = {};
  if(g.dr && g.ba){ ex.dr = {blue:num(g.dr.blue,0,9), red:num(g.dr.red,0,9)}; ex.ba = {blue:num(g.ba.blue,0,9), red:num(g.ba.red,0,9)}; }
  if(g.g15 != null) ex.g15 = num(g.g15,-20000,20000);
  if(g.pct != null){ ex.pct = num(g.pct,0,100); ex.up = ex.pct < 25; }
  return {...ex, blue, red, winner, time:num(g.time,10,80), sec:num(g.sec,0,59), kills:{blue:num(g.kills && g.kills.blue,0,80), red:num(g.kills && g.kills.red,0,80)}, steps, ps,
    pog:{s:ps2, r:pr, team:pteam, n:team(pteam).p[ROLES.indexOf(pr)].n, c:ps[ps2][pr].c, rt:ps[ps2][pr].rt, why:`${ps[ps2][pr].k}/${ps[ps2][pr].d}/${ps[ps2][pr].a} · ${Math.round(ps[ps2][pr].kp * 100)}% KP`}};
}
function sanitizeRun(r){
  if(!r || typeof r !== "object" || r.v !== 1) throw new Error("version");
  const mode = MODES[r.mode] ? r.mode : null; if(!mode) throw new Error("mode");
  const myTeams = [...new Set(arr(r.myTeams || [], 4).map(tid))];
  const out = {v:1, mode, myTeams, guestAI: r.guestAI === true, day:num(r.day,0,DAYS.length - 1), matches:[], W:{}, L:{}, met:[],
    stats:{games:0, champ:{}, pchamp:{}, players:{}, crole:{}}, created:num(r.created || 0,0,4e12), updated:Date.now()};
  TEAMS.forEach(t => { out.W[t.id] = 0; out.L[t.id] = 0; });
  const seen = new Set();
  arr(r.matches, 40).forEach(x => {
    if(typeof x.id !== "string" || !MATCH_ID.test(x.id) || seen.has(x.id)) throw new Error("match id"); seen.add(x.id);
    const a = tid(x.a), b = tid(x.b); if(a === b) throw new Error("same team");
    const ko = !/^S[1-5]-/.test(x.id); // SF1/SF2 also start with S
    const m = {id:x.id, games:[], status:"pending", ctrl: x.ctrl == null ? null : tid(x.ctrl), a, b, day:num(x.day,0,DAYS.length - 1),
      phase: ko ? "ko" : "swiss", bo: ko ? 5 : (x.bo === 3 ? 3 : 1)};
    if(m.ctrl && m.ctrl !== a && m.ctrl !== b) m.ctrl = null;
    if(ko){ m.stage = x.id.startsWith("QF") ? "QF" : x.id.startsWith("SF") ? "SF" : "F"; m.idx = m.stage === "F" ? 0 : num(x.id.replace(/\D/g, ""), 1, 4) - 1; }
    else { m.round = num(x.id[1], 1, 5); m.rec = /^[0-2]-[0-2]$/.test(x.rec) ? x.rec : (() => { throw new Error("rec"); })(); }
    arr(x.games, m.bo).forEach(g => { if(m.status === "done") throw new Error("extra game"); const cg = cleanGame(g, m); m.games.push(cg); addGameStats(out.stats, m, cg); settleMatch(m, out); });
    out.matches.push(m);
  });
  return out;
}
function simMatch(m){ while(m.status !== "done") playAIGame(m); }
const dayDone = d => { const ms = dayMatches(d); return ms.length > 0 && ms.every(m => m.status === "done"); };
function advanceDay(){
  if(!dayDone(RUN.day) || RUN.day >= DAYS.length - 1) return false;
  RUN.day++; drawDay(); saveRun(); return true;
}
function simAIToday(){ dayMatches(RUN.day).forEach(m => { if(m.status !== "done" && !ctrlOf(m)) simMatch(m); }); saveRun(); }
function simToNext(){
  for(let guard = 0; guard < 40; guard++){
    simAIToday();
    if(dayMatches(RUN.day).some(m => m.status !== "done" && ctrlOf(m))) break;
    if(!advanceDay()) break;
  }
  saveRun();
}

/* ---------- user-drafted game ---------- */
function startUserGame(m){
  const ctrl = ctrlOf(m); if(!ctrl) return;
  if(RUN.mode === "guest" && RUN.myTeams.includes(ctrl)) { /* your own team */ }
  const gi = m.games.length, blue = blueFor(m, gi), opp = ctrl === m.a ? m.b : m.a;
  Object.assign(DS, {me:ctrl, opp, side: ctrl === blue ? "blue" : "red", fp:"blue", fmt: m.bo > 1 ? "fearless" : "bo1",
    locked: lockedFor(m), steps:[], ai:true, showUsed:false, fresh:-1, sim:null, q:"", roleF:"ALL", game:gi + 1, series:null,
    tour:{mid:m.id, gi, next:"Continue"}});
  show("draft"); queueAI();
}
function tourDraftHeader(){
  const m = M(DS.tour.mid); if(!m) return "";
  const guest = RUN.mode === "guest" && !RUN.myTeams.includes(DS.me);
  return `<div class="tourhead"><span class="eyebrow">Worlds 2026 · ${esc(DAYS[m.day].date)} · ${esc(stageName(m))}</span>
    <b>Game ${DS.tour.gi + 1} of Bo${m.bo} · ${esc(team(m.a).id)} ${seriesWins(m, m.a)}–${seriesWins(m, m.b)} ${esc(team(m.b).id)}</b>
    <span class="notes">You draft ${esc(team(DS.me).name)}${guest ? " (guest pick)" : ""} on ${DS.side} side; the AI drafts ${esc(team(DS.opp).name)}. ${m.bo > 1 ? `Fearless: ${DS.locked.length} champions locked from earlier games.` : ""} Drafts use the tournament data pool so far (${RUN.stats.games} games).</span></div>`;
}
function tourPlay(){
  const m = M(DS.tour.mid); if(!m || DS.steps.length < 20) return;
  let bw = 0; for(let i = 0; i < 300; i++) if(simGame(true).winner === "blue") bw++;
  const g = simGame(false), rec = pack(g);
  rec.pct = Math.round((g.winner === "blue" ? bw : 300 - bw) / 3); rec.up = rec.pct < 25;
  recordGame(m, rec);
  DS.tour.next = m.status === "done" ? "Back to the tournament" : `Next game (${team(m.a).id} ${seriesWins(m, m.a)}–${seriesWins(m, m.b)} ${team(m.b).id})`;
  DS.sim = {g, bwin: bw / 300};
  renderDraft();
  const sEl = document.querySelector(".sim"); if(sEl) sEl.scrollIntoView({behavior:"smooth", block:"start"});
}
function tourNext(){
  const m = M(DS.tour.mid);
  if(m && m.status !== "done"){ startUserGame(m); return; }
  DS.tour = null; DS.steps = []; DS.sim = null; DS.ai = true; DS.locked = []; DS.fmt = "bo1";
  show("tour");
}

/* ---------- awards ---------- */
function playerRows(){
  if(!RUN) return [];
  return Object.entries(RUN.stats.players).map(([key, s]) => {
    const [tid, i] = key.split("|"), t = team(tid), p = t.p[+i];
    return {key, tid, p, s, avgRt: s.rt / s.g};
  });
}
function bestBy(rows, f, tie){ return rows.slice().sort((a,b) => (f(b) - f(a)) || (tie(b) - tie(a)))[0]; }
function awardsData(){
  const rows = playerRows().filter(r => r.s.g > 0);
  const swissDone = RUN.matches.filter(m => m.phase === "swiss").length === 33 && RUN.matches.filter(m => m.phase === "swiss").every(m => m.status === "done");
  const fin = M("F"), done = fin && fin.status === "done";
  const swissMVP = rows.length ? bestBy(rows, r => r.s.swissPts, r => r.avgRt) : null;
  const tourMVP = rows.length ? bestBy(rows, r => r.s.pts, r => r.avgRt) : null;
  const minG = Math.max(2, Math.floor(RUN.stats.games / 16 * 0.6));
  const team5 = ROLES.map(r => { const c = rows.filter(x => x.p.role === r && x.s.g >= minG); return c.length ? bestBy(c, x => x.avgRt, x => x.s.pts) : null; });
  let finalsMVP = null;
  if(fin && fin.games.length){ const c = rows.filter(r => r.tid === (done ? fin.w : fin.a) && r.s.finRt.length); if(done && c.length) finalsMVP = bestBy(c, r => avg(r.s.finRt), r => r.s.pts); }
  return {swissDone, done, swissMVP, tourMVP, team5, finalsMVP, minG, champion: done ? fin.w : null};
}

/* ---------- UI ---------- */
function teamTag(id){ return `${regDot(id)}<span class="ttag" style="--tc:${teamCol(id)}">${esc(id)}</span>`; }
function renderTour(){
  const v = document.getElementById("v-tour"); if(!v) return;
  if(!RUN){ v.innerHTML = setupView(); return; }
  const D = DAYS[RUN.day], aw = awardsData();
  const today = dayMatches(RUN.day), pendingCtrl = today.filter(m => m.status !== "done" && ctrlOf(m)), pendingAI = today.filter(m => m.status !== "done" && !ctrlOf(m));
  const sub = [["today","Today"],["standings","Standings"],["bracket","Bracket"],["stats","Stats"],["awards","Awards & MVP"],["results","Results"],["playin","Play-ins"]];
  v.innerHTML = `<div class="panel" style="display:grid;gap:14px">
    <div class="thead2"><div><span class="eyebrow">Worlds 2026 · ${esc(MODES[RUN.mode].name)}${RUN.myTeams.length ? " · " + RUN.myTeams.map(esc).join(", ") : ""}</span>
      <h2>${aw.champion ? esc(team(aw.champion).name) + " are world champions" : esc(D.date) + " · " + esc(D.label)}</h2>
      <span class="notes">Day ${RUN.day + 1} of ${DAYS.length} · ${RUN.stats.games} games played · saved in this browser</span></div>
      <div class="ctrls">
        ${pendingAI.length ? `<button class="btn" data-ta="simday">Sim ${pendingAI.length} AI match${pendingAI.length > 1 ? "es" : ""}</button>` : ""}
        ${aw.done ? `<button class="btn primary" data-ta="new">${tourConfirmNew ? "Click again to delete this run" : "Start over"}</button>` : RUN.mode === "sim" ? `<button class="btn" data-ta="simnext">Sim to end of event</button>` : pendingCtrl.length ? `<button class="btn primary" data-ta="draft" data-m="${pendingCtrl[0].id}">Draft game ${pendingCtrl[0].games.length + 1}: ${esc(pendingCtrl[0].a)} vs ${esc(pendingCtrl[0].b)}</button><button class="btn" data-ta="sim1" data-m="${pendingCtrl[0].id}">Sim next game</button>` : `<button class="btn" data-ta="simnext">Sim to my next match</button>`}
        ${dayDone(RUN.day) && RUN.day < DAYS.length - 1 ? `<button class="btn primary" data-ta="advance">Next day →</button>` : ""}
        ${RUN.mode === "guest" ? `<label class="tog"><input type="checkbox" id="tGuestAI"${RUN.guestAI ? " checked" : ""}> Play guest games as AI until my team plays</label>` : ""}
      </div></div>
    ${DS.tour ? `<div class="turn blue"><span>A draft is in progress.</span><div class="ctrls"><button class="btn primary" data-ta="resume">Resume draft</button></div></div>` : ""}
    ${aw.champion ? winnersView(aw) : ""}
    <div class="seg" role="tablist">${sub.map(([k,l]) => `<button data-tv="${k}" aria-pressed="${TV === k}">${l}</button>`).join("")}</div>
    <div>${TV === "today" ? todayView(today) : TV === "standings" ? standingsView() : TV === "bracket" ? bracketView() : TV === "stats" ? statsView() : TV === "awards" ? awardsView(aw) : TV === "results" ? resultsView() : playinView()}</div>
    <details class="notes"${tourConfirmNew ? " open" : ""}><summary style="cursor:pointer">Save, export or start over</summary>
      <div class="ctrls" style="margin-top:8px">
        <button class="btn" data-ta="export">Download run file</button>
        <button class="btn" data-ta="copy">Copy run as text</button>
        <label class="btn" style="cursor:pointer">Import run file<input type="file" id="tImport" accept=".json,application/json" hidden></label>
        <button class="btn" data-ta="new">${tourConfirmNew ? "Click again to delete this run" : "Start a new run"}</button>
      </div>
      <p>Progress saves automatically in this browser and is there next time you open the page. Use the run file to move it to another device or browser.</p>
    </details>
    <p class="notes" style="font-size:12px;margin:0">Format and dates: Wikipedia, Inven Global, accountshark.net (how multi-day rounds split is assumed). Round 1 draw: Dot Esports. Swiss: 3 wins advance, 3 losses out; advancement/elimination matches Bo3, others Bo1. Quarter-finals: the two 3-0 teams play 3-2 teams on opposite halves; knockouts Bo5 with Fearless. Game 1 blue side: the higher seed (round 1) or higher-rated team; then the loser of each game takes blue. POG follows LCK: one per game, 100 POG points (Namuwiki, LCK Awards).</p>
  </div>`;
}
function setupView(){
  const opt = TEAMS.map(t => `<label class="pickteam"><input type="checkbox" name="tTeam" value="${t.id}"> ${esc(t.name)} <small>${t.ov.toFixed(1)}</small></label>`).join("");
  return `<div class="panel" style="display:grid;gap:14px">
    <div><h2>Tournament mode</h2><p class="notes" style="margin:4px 0 0">Play Worlds 2026 from Swiss round 1 (23 October) to the Brooklyn final (14 November) on the real format and draw. Every game feeds a live data pool — champion presence, win rates and each player's Worlds champion pool — that later drafts use. LCK-style Player of the Game, MVP points and awards run all event.</p></div>
    <div class="modes">${Object.entries(MODES).map(([k, m], i) => `<label class="modecard"><input type="radio" name="tMode" value="${k}"${i === 0 ? " checked" : ""}><b>${m.name}</b><span class="notes">${m.desc}</span></label>`).join("")}</div>
    <div><div class="eyebrow">Your team(s)</div><p class="notes" style="margin:2px 0 8px">My teams: choose 1–4. Guest picks: choose 1. Sim run: none needed.</p><div class="teamgrid">${opt}</div></div>
    <div class="ctrls"><button class="btn primary" data-ta="start">Start Worlds</button><label class="btn" style="cursor:pointer">Import a run file<input type="file" id="tImport" accept=".json,application/json" hidden></label><span class="notes" id="tErr"></span></div>
  </div>`;
}
let tourFocus = null;   // match to scroll to and highlight after "Sim to my next match"
/* one match as a card: stage, both teams with score, each game's winner and POG, and its actions */
function matchCard(m){
  const ctrl = ctrlOf(m), wa = seriesWins(m, m.a), wb = seriesWins(m, m.b), st = m.status === "done" ? "done" : m.games.length ? "live" : "todo";
  const line = id => `<div class="mc-team${m.w === id ? " won" : ""}">${teamTag(id)}<span class="nm">${esc(team(id).name)}</span><b class="sc">${m.games.length ? seriesWins(m, id) : ""}</b></div>`;
  const act = m.status === "done" ? `<button class="btn" data-ta="open" data-m="${m.id}">${tourOpen[m.id] ? "Hide" : m.bo > 1 ? "Series" : "Game"}</button>`
    : ctrl ? `<button class="btn primary" data-ta="draft" data-m="${m.id}">${m.games.length ? "Draft game " + (m.games.length + 1) : "Draft"} as ${esc(ctrl)}</button><button class="btn" data-ta="sim" data-m="${m.id}">Sim</button>`
    : `<button class="btn" data-ta="sim" data-m="${m.id}">Sim</button>`;
  const gl = m.games.map((g, i) => `<li><span class="gno">G${i + 1}</span>${teamTag(g.winner)}<span class="notes">POG ${esc(g.pog.n)}</span></li>`).join("");
  return `<div class="mcard ${st}${tourFocus === m.id ? " focus" : ""}" id="mc-${m.id}"><div class="mc-head"><span class="notes">${esc(stageName(m))}</span><span class="tag dimtag">Bo${m.bo}</span></div>${line(m.a)}${line(m.b)}
    <div class="mc-res notes">${m.status === "done" ? `<b>${esc(m.w)}</b> win ${m.sc}` : m.games.length ? `${wa}–${wb} · in progress` : ctrl ? `You draft ${esc(ctrl)}` : "AI vs AI"}</div>${gl ? `<ul class="mc-games">${gl}</ul>` : ""}<div class="ctrls">${act}</div></div>`;
}
/* a day: full-width date row, then up to four match cards per row; opened series show their panel underneath */
function dayBlock(d, ms){
  const open = ms.filter(m => tourOpen[m.id] && m.games.length);
  return `<div class="dayblk"><div class="dayrow"><b>${esc(DAYS[d].date)}</b><span>${esc(DAYS[d].label)}</span><span class="notes">${ms.filter(m => m.status === "done").length}/${ms.length} played</span></div>
    <div class="mgrid">${ms.map(matchCard).join("")}</div>${open.map(m => `<div class="mopen">${m.bo > 1 ? seriesPanel({bo:m.bo, fearless:true, a:m.a, b:m.b, games:m.games, ctx:"tour", mid:m.id}) : ""}${m.games.map((g, i) => gameDetail(m, g, i)).join("")}</div>`).join("")}</div>`;
}
function todayView(today){
  if(!today.length) return `<p class="notes">Matches for this day are drawn once the previous round finishes.</p>`;
  const next = DAYS[RUN.day + 1];
  return `${dayBlock(RUN.day, today)}${next ? `<p class="notes">Next: ${esc(next.date)} · ${esc(next.label)}</p>` : ""}`;
}
function standingsView(){
  const rows = TEAMS.map(t => t.id).sort((a,b) => (RUN.W[b] - RUN.L[b]) - (RUN.W[a] - RUN.L[a]) || RUN.W[b] - RUN.W[a] || team(b).ov - team(a).ov);
  const st = id => RUN.W[id] >= 3 ? `<span class="chip meta">Qualified</span>` : RUN.L[id] >= 3 ? `<span class="chip off">Eliminated</span>` : `<span class="chip mix">Alive</span>`;
  const gw = id => { let w = 0, l = 0; RUN.matches.forEach(m => m.games.forEach(g => { if(g.blue === id || g.red === id){ g.winner === id ? w++ : l++; } })); return `${w}-${l}`; };
  return `<div class="ctrls" style="justify-content:space-between;margin-bottom:6px"><span class="eyebrow">Swiss standings</span>${regionKey()}</div><div style="overflow-x:auto"><table class="tt full"><thead><tr><th>Team</th><th>Swiss record</th><th>Games</th><th>Status</th></tr></thead><tbody>${rows.map(id => `<tr class="${RUN.myTeams.includes(id) ? "me" : ""}"><td>${teamTag(id)} ${esc(team(id).name)}</td><td class="num">${RUN.W[id]}-${RUN.L[id]}</td><td class="num">${gw(id)}</td><td>${st(id)}</td></tr>`).join("")}</tbody></table></div>`;
}
function bracketView(){
  const cell = id => { const m = M(id); if(!m) return `<div class="bcell"><span class="notes">TBD</span></div>`; return `<div class="bcell ${m.status}">${[m.a, m.b].map(t => `<div class="${m.w === t ? "bw" : ""}">${teamTag(t)} ${esc(team(t).name)} <b>${seriesWins(m, t)}</b></div>`).join("")}<span class="notes">${esc(DAYS[m.day].date)}</span></div>`; };
  return `<div class="bracket"><div><div class="eyebrow">Quarter-finals</div>${["QF1","QF2","QF3","QF4"].map(cell).join("")}</div><div><div class="eyebrow">Semi-finals</div>${["SF1","SF2"].map(cell).join("")}</div><div><div class="eyebrow">Final</div>${cell("F")}</div></div>`;
}
let statRole = "ALL", statSort = "pts", chRole = "ALL", chSort = "pres", chQ = "";
let statTab = (() => { try{ return localStorage.getItem("lolw26-stat-tab") === "players" ? "players" : "champs"; }catch(e){ return "champs"; } })();
/* the role a champion was played in most at this run (falls back to its main pro role) */
function runRole(c){ const e = ROLES.map(r => [r, (RUN.stats.crole[c + "|" + r] || {p:0}).p]).sort((a,b) => b[1] - a[1])[0]; return e[1] ? e[0] : primaryRole(c); }
function statsView(){
  const S = RUN.stats; if(!S.games) return `<p class="notes">No games played yet. Presence numbers still use the pre-Worlds pro data.</p>`;
  const all = Object.entries(S.champ).map(([c, v]) => ({c, ...v, r: runRole(c), pres: Math.round((v.p + v.b) / S.games * 100), wr: v.p ? v.w / v.p : -1}));
  const q = chQ.trim().toLowerCase();
  const cf = {pres: x => x.pres, p: x => x.p, b: x => x.b, wr: x => x.wr}[chSort];
  const ch = all.filter(x => (chRole === "ALL" || x.r === chRole) && (!q || x.c.toLowerCase().includes(q))).sort((a,b) => cf(b) - cf(a) || b.pres - a.pres);
  const rows = playerRows().filter(r => statRole === "ALL" || r.p.role === statRole);
  const f = {pts: r => r.s.pts, rt: r => r.avgRt, kda: r => (r.s.k + r.s.a) / Math.max(1, r.s.d), dmg: r => r.s.dmgS / r.s.g, csd: r => r.s.csd / r.s.g}[statSort];
  rows.sort((a,b) => f(b) - f(a));
  const th = (k, l) => `<th><button class="sortb" data-ss="${k}" aria-pressed="${statSort === k}">${l}</button></th>`;
  const tc = (k, l) => `<th><button class="sortb" data-cs="${k}" aria-pressed="${chSort === k}">${l}</button></th>`;
  const pn = playerRows().length;
  const tabs = `<div class="seg" role="group" aria-label="Stats view"><button data-st="champs" aria-pressed="${statTab === "champs"}">Champions</button><button data-st="players" aria-pressed="${statTab === "players"}">Players</button></div>`;
  return `<div style="display:grid;gap:16px">${tabs}
    ${statTab === "champs" ? `<div><div class="eyebrow">Champions · ${all.length} picked or banned · ${S.games} games</div><p class="notes" style="margin:2px 0 6px">Every champion picked or banned at least once. Presence = picked or banned in that share of games. Drafts blend this with the pre-Worlds pro data, weighting the tournament more as games are played.</p>
    <div class="ctrls" style="margin-bottom:6px"><div class="seg">${[["ALL","All"], ...ROLES.map(r => [r, r])].map(([k,l]) => `<button data-cr="${k}" aria-pressed="${chRole === k}">${l}</button>`).join("")}</div><input id="tChQ" type="search" placeholder="Search champions" value="${esc(chQ)}" aria-label="Search champions"><span class="notes">${ch.length} shown</span></div>
    <div style="overflow-x:auto"><table class="tt full ctab"><thead><tr><th>Champion</th><th>Role</th>${tc("pres","Presence")}${tc("p","Picks")}${tc("b","Bans")}<th>W-L</th>${tc("wr","Win rate")}</tr></thead><tbody>${ch.map(x => `<tr><td><span class="cname hov" data-tc="${esc(x.c)}" tabindex="0">${icon(x.c, 28)}${esc(x.c)}</span>${x.p + x.b <= 2 ? ` <span class="chip off" title="Picked or banned in 2 games or fewer">small sample</span>` : ""}</td><td>${x.r}</td><td class="num">${x.pres}%</td><td class="num">${x.p}</td><td class="num">${x.b}</td><td class="num">${x.w}-${x.p - x.w}</td><td class="num">${x.p ? Math.round(x.w / x.p * 100) + "%" : "–"}</td></tr>`).join("") || `<tr><td colspan="7" class="notes">No champions match.</td></tr>`}</tbody></table></div></div>
    </div>` : `<div><div class="eyebrow">Players · ${pn} players · ${S.games} games</div><div class="seg" style="margin:6px 0">${[["ALL","All"], ...ROLES.map(r => [r, r])].map(([k,l]) => `<button data-sr="${k}" aria-pressed="${statRole === k}">${l}</button>`).join("")}</div>
    <div style="overflow-x:auto"><table class="tt full ctab"><thead><tr><th>Player</th><th>Games</th>${th("pts","POG pts")}${th("rt","Avg rating")}${th("kda","KDA")}<th>KP</th>${th("dmg","DMG%")}${th("csd","CSD@15")}</tr></thead><tbody>${rows.map(r => `<tr><td>${teamTag(r.tid)} <span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span> <span class="notes">${r.p.role}</span></td><td class="num">${r.s.g}</td><td class="num">${r.s.pts}</td><td class="num">${r.avgRt.toFixed(2)}</td><td class="num">${kdaOf(r.s)}</td><td class="num">${Math.round(r.s.kp / r.s.g * 100)}%</td><td class="num">${Math.round(r.s.dmgS / r.s.g * 100)}%</td><td class="num">${(r.s.csd / r.s.g).toFixed(1)}</td></tr>`).join("")}</tbody></table></div></div>`}
  </div>`;
}

/* ---------- winners screen ---------- */
/* Original championship trophy (own design — not the Summoner's Cup): crowned rim with a finial gem, faceted bowl
   tapering to a fluted stem, a front jewel plus two side jewels in profile (a fourth sits at the back, hidden), stepped plinth. */
const cupSVG = k => `<svg class="cup" viewBox="0 0 120 190" aria-hidden="true">
  <defs>
    <linearGradient id="m${k}" x1="0" x2="1"><stop offset="0" stop-color="var(--cupA)"/><stop offset=".32" stop-color="var(--cupB)"/><stop offset=".5" stop-color="var(--cupC)"/><stop offset=".7" stop-color="var(--cupB)"/><stop offset="1" stop-color="var(--cupA)"/></linearGradient>
    <linearGradient id="d${k}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--cupB)"/><stop offset="1" stop-color="var(--cupA)"/></linearGradient>
    <radialGradient id="g${k}" cx=".35" cy=".35" r=".8"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="var(--teal)"/><stop offset="1" stop-color="var(--gemD)"/></radialGradient>
  </defs>
  <path d="M60 2l7 12-7 7-7-7z" fill="url(#m${k})"/><circle cx="60" cy="13" r="3" fill="url(#g${k})"/>
  <path d="M12 24l12-8 12 9 12-9 12 9 12-9 12 9 12-9 12 8-7 10H19z" fill="url(#m${k})"/>
  <path d="M19 34h82c-2 22-12 40-28 52-5 4-8 7-9 11h-8c-1-4-4-7-9-11C31 74 21 56 19 34z" fill="url(#m${k})"/>
  <path d="M38 36c2 18 8 34 18 48M82 36c-2 18-8 34-18 48M60 36v58" stroke="var(--cupA)" stroke-opacity=".4" stroke-width="1.4" fill="none"/>
  <path d="M60 46l12 12-12 14-12-14z" fill="url(#m${k})" stroke="var(--cupA)" stroke-opacity=".5"/>
  <path d="M60 50l8 8-8 10-8-10z" fill="url(#g${k})"/>
  <path d="M31.0 70.0 L23.5 52.0 L17.0 41.0 L12.0 56.0z" fill="url(#m${k})" stroke="var(--cupA)" stroke-opacity=".5"/>
  <path d="M26.7 63.6 L22.4 53.2 L18.6 46.8 L15.7 55.5z" fill="url(#g${k})"/>
  <path d="M89.0 70.0 L96.5 52.0 L103.0 41.0 L108.0 56.0z" fill="url(#m${k})" stroke="var(--cupA)" stroke-opacity=".5"/>
  <path d="M93.3 63.6 L97.6 53.2 L101.4 46.8 L104.3 55.5z" fill="url(#g${k})"/>
  <circle cx="32" cy="42" r="2.6" fill="url(#g${k})"/><circle cx="88" cy="42" r="2.6" fill="url(#g${k})"/>
  <path d="M55 96h10l-2 8 2 8-2 8 5 7H52l5-7-2-8 2-8z" fill="url(#m${k})"/>
  <ellipse cx="60" cy="128" rx="20" ry="5" fill="url(#d${k})"/>
  <path d="M40 130h40l7 16H33z" fill="url(#m${k})"/>
  <rect x="27" y="146" width="66" height="11" fill="url(#m${k})"/>
  <rect x="21" y="157" width="78" height="17" fill="url(#m${k})"/>
  <circle cx="60" cy="165.5" r="4" fill="url(#g${k})"/>
  <path d="M30 165.5h22M68 165.5h22" stroke="var(--cupB)" stroke-width="1.2"/>
  <g class="spark"><path d="M94 28l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="#fff"/></g>
</svg>`;
/* champion (LoL) team of the tournament: best win rate per role, minimum picks, one champion per slot */
function champTeam(){
  const S = RUN.stats, minP = Math.max(4, Math.round(S.games * 0.06)), used = new Set();
  return {minP, team: ROLES.map(r => {
    const c = Object.entries(S.crole).filter(([k, v]) => k.endsWith("|" + r) && v.p >= minP).map(([k, v]) => ({c: k.slice(0, k.lastIndexOf("|")), r, ...v, sc: (v.w + 1) / (v.p + 2)}))
      .filter(x => !used.has(x.c)).sort((a,b) => b.sc - a.sc || b.p - a.p)[0];
    if(c) used.add(c.c); return c || null; })};
}
function storylines(){
  const out = [], S = RUN.stats, done = RUN.matches.filter(m => m.status === "done");
  const rank = [...TEAMS].sort((a,b) => b.ov - a.ov).map(t => t.id);
  const up = done.map(m => ({m, gap: team(m.l).ov - team(m.w).ov})).sort((a,b) => b.gap - a.gap)[0];
  if(up && up.gap > 0) out.push(["Biggest upset", `${up.m.w} beat ${up.m.l} ${up.m.sc}`, `rated ${up.gap.toFixed(1)} lower · ${stageName(up.m)}`]);
  const deep = ["F","SF1","SF2"].map(M).filter(Boolean).flatMap(m => [m.a, m.b]).map(id => ({id, r: rank.indexOf(id) + 1})).sort((a,b) => b.r - a.r)[0];
  if(deep && deep.r >= 7) out.push(["Cinderella run", `${team(deep.id).name}`, `rated #${deep.r} of 16, reached the ${[M("F").a, M("F").b].includes(deep.id) ? "final" : "semi-finals"}`]);
  let long = null; RUN.matches.forEach(m => m.games.forEach(g => { const t = g.time * 60 + g.sec; if(!long || t > long.t) long = {t, g}; }));
  if(long) out.push(["Longest game", `${long.g.time}:${String(long.g.sec).padStart(2, "0")}`, `${long.g.blue} vs ${long.g.red}`]);
  const mb = Object.entries(S.champ).sort((a,b) => b[1].b - a[1].b)[0];
  if(mb) out.push(["Most banned", mb[0], `banned in ${Math.round(mb[1].b / S.games * 100)}% of games`, mb[0]]);
  const mp = Object.entries(S.champ).sort((a,b) => b[1].p - a[1].p)[0];
  if(mp) out.push(["Most picked", mp[0], `${mp[1].p} games · ${mp[1].w}-${mp[1].p - mp[1].w}`, mp[0]]);
  const perfect = TEAMS.filter(t => RUN.W[t.id] === 3 && RUN.L[t.id] === 0).map(t => t.id), sweeps = done.filter(m => m.bo === 5 && m.sc === "3-0");
  if(perfect.length || sweeps.length) out.push(["Flawless", perfect.length ? perfect.join(" & ") + " 3-0 in Swiss" : sweeps[0].w + " swept " + sweeps[0].l, sweeps.length ? `${sweeps.length} knockout sweep${sweeps.length > 1 ? "s" : ""}` : "no knockout sweeps"]);
  let best = null; RUN.matches.forEach(m => m.games.forEach(g => ["blue","red"].forEach(s => ROLES.forEach((r, i) => { const p = g.ps[s][r]; if(!best || p.rt > best.p.rt) best = {p, tid: s === "blue" ? g.blue : g.red, i, opp: s === "blue" ? g.red : g.blue}; }))));
  if(best) out.push(["Best single game", `${team(best.tid).p[best.i].n} · ${best.p.rt.toFixed(1)}`, `${best.p.c} ${best.p.k}/${best.p.d}/${best.p.a} vs ${best.opp}`, best.p.c]);
  return out;
}
function winnersView(aw){
  const fin = M("F"), w = aw.champion, t = team(w), S = RUN.stats, ct = champTeam();
  const roster = t.p.map((p, i) => { const s = S.players[w + "|" + i], pc = Object.entries(S.pchamp[w + "|" + i] || {}).sort((a,b) => b[1].g - a[1].g)[0];
    const fm = aw.finalsMVP && aw.finalsMVP.key === w + "|" + i;
    return `<div class="rcard${fm ? " mvp" : ""}"><span class="role">${p.role}</span>${pc ? icon(pc[0], 44) : ""}<b class="hov" data-tp="${w}|${i}" tabindex="0">${esc(p.n)}</b><small>${s ? `KDA ${kdaOf(s)} · ${(s.rt / s.g).toFixed(1)} avg · ${s.pog} POG` : ""}</small>${pc ? `<small class="dim">${esc(pc[0])} ${pc[1].w}-${pc[1].g - pc[1].w}</small>` : ""}${fm ? `<span class="tag">Finals MVP</span>` : ""}</div>`; }).join("");
  const award = (title, r, sub) => `<div class="award unlocked"><span class="eyebrow">★ ${title}</span>${r ? `<b>${teamTag(r.tid)} <span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span></b><span class="notes">${sub(r)}</span>` : `<span class="notes">—</span>`}</div>`;
  const confetti = Array.from({length: 26}, (_, i) => `<i style="--x:${(i * 37 + 11) % 100}%;--d:${((i * 7) % 26) / 10}s;--y:${(i * 23) % 70}%;--c:var(${["--gold","--teal","--bside","--rside"][i % 4]})"></i>`).join("");
  return `<div class="win" role="region" aria-label="World champions"><div class="confetti" aria-hidden="true">${confetti}</div>${cupSVG("w")}
    <div class="eyebrow">Brooklyn · ${esc(DAYS[fin.day].date)} · ${esc(fin.sc)}</div>
    <h3 class="wtitle">${esc(t.name)} are world champions</h3>
    <div class="notes">beat ${esc(team(fin.l).name)} ${esc(fin.sc)} in the final${aw.finalsMVP ? ` · Finals MVP ${esc(aw.finalsMVP.p.n)} (avg rating ${avg(aw.finalsMVP.s.finRt).toFixed(1)})` : ""}</div>
    <div class="eyebrow wsub">The champions</div><div class="roster">${roster}</div>
    <div class="eyebrow wsub">Champion team of the tournament</div><div class="roster">${ct.team.map((x, i) => x ? `<div class="rcard"><span class="role">${ROLES[i]}</span>${icon(x.c, 44)}<b class="hov" data-tc="${esc(x.c)}" tabindex="0">${esc(x.c)}</b><small>${x.w}-${x.p - x.w} · ${Math.round(x.w / x.p * 100)}%</small></div>` : `<div class="rcard"><span class="role">${ROLES[i]}</span><small>no champion with ${ct.minP}+ games</small></div>`).join("")}</div>
    <p class="notes" style="margin:4px auto 0;font-size:12px">Best win rate in each role with at least ${ct.minP} games (ties go to the most played).</p>
    <div class="eyebrow wsub">Storylines</div><div class="story">${storylines().map(([h, b, sub, c]) => `<div>${c ? icon(c, 32) : ""}<span><small>${esc(h)}</small><b>${esc(b)}</b><em>${esc(sub)}</em></span></div>`).join("")}</div>
    <div class="awards" style="margin-top:14px">${award("Finals MVP", aw.finalsMVP, r => `avg rating ${avg(r.s.finRt).toFixed(2)} across ${r.s.finRt.length} final games`)}${award("Tournament MVP", aw.tourMVP, r => `${r.s.pts} POG points · ${r.s.pog} POG`)}${award("Swiss stage MVP", aw.swissMVP, r => `${r.s.swissPts} POG points in the Swiss stage`)}</div>
  </div>`;
}
function awardsView(aw){
  const card = (title, r, sub, pending) => `<div class="award"><span class="eyebrow">${title}</span>${r ? `<b>${teamTag(r.tid)} <span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span> <span class="notes">${r.p.role}</span></b><span class="notes">${sub(r)}</span>` : `<span class="notes">${pending}</span>`}${pending && r && pending.startsWith("Leading") ? `<span class="notes">${pending}</span>` : ""}</div>`;
  const lead = playerRows().filter(r => r.s.pog).sort((a,b) => b.s.pts - a.s.pts || b.avgRt - a.avgRt).slice(0, 10);
  return `<div style="display:grid;gap:14px">
    <div class="awards">
      ${card("Swiss stage MVP", aw.swissMVP, r => `${r.s.swissPts} POG points in the Swiss stage · avg rating ${r.avgRt.toFixed(2)}`, aw.swissDone ? "" : "Leading so far — awarded when the Swiss stage ends")}
      ${card("Tournament MVP", aw.tourMVP, r => `${r.s.pts} POG points · ${r.s.pog} POG · avg rating ${r.avgRt.toFixed(2)}`, aw.done ? "" : "Leading so far — awarded after the final")}
      ${card("Finals MVP", aw.finalsMVP, r => `avg rating ${avg(r.s.finRt).toFixed(2)} across ${r.s.finRt.length} final games`, "Awarded to the best-rated player on the winning team in the final")}
    </div>
    <div><div class="eyebrow">All-Tournament team ${aw.done ? "" : "(current)"}</div><p class="notes" style="margin:2px 0 6px">Best average game rating per role, minimum ${aw.minG} games.</p>
    <div class="team5">${aw.team5.map((r, i) => `<div><span class="role">${ROLES[i]}</span>${r ? `<b>${teamTag(r.tid)} <span class="hov" data-tp="${r.tid}|${i}" tabindex="0">${esc(r.p.n)}</span></b><span class="notes">avg rating ${r.avgRt.toFixed(2)}</span>` : `<span class="notes">—</span>`}</div>`).join("")}</div></div>
    <div><div class="eyebrow">POG points leaderboard</div>${lead.length ? `<table class="tt full"><thead><tr><th>Player</th><th>Rank</th><th>POG</th><th>Points</th><th>Avg rating</th></tr></thead><tbody>${lead.map((r, i) => `<tr><td>${teamTag(r.tid)} <span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span> <span class="notes">${r.p.role}</span></td><td class="num">${i + 1}</td><td class="num">${r.s.pog}</td><td class="num">${r.s.pts}</td><td class="num">${r.avgRt.toFixed(2)}</td></tr>`).join("")}</tbody></table>` : `<p class="notes">No games yet.</p>`}</div>
    <p class="notes" style="font-size:12px">Game rating (0–10) weighs the numbers that make LCK Player of the Game winners stand out: the result, KDA and deaths, kill participation, damage share against the role's norm, CS lead at 15, solo kills, vision (supports) and objectives (junglers and supports). Metric choices follow LeagueLab's metrics guide and Team Liquid's statistical-standouts piece; points follow the LCK POG system. POG goes to the winning side unless a losing player's rating beats the winners' best by 1.1 or more (rare, under 1% of games). Supports are balanced so they win POG about as rarely as in the LCK (around 10% of games; Keria in 2023 was the first support to lead a split in POG points).</p>
  </div>`;
}
function gameDetail(m, g, gi){
  const side = s => { const tid = s === "blue" ? g.blue : g.red; return `<div class="an ${s}"><h3>${esc(team(tid).name)} <small>${g.winner === tid ? "won" : "lost"} · ${g.kills[s]} kills</small></h3><table class="tt full stab3"><thead><tr><th>Player</th><th>Champion</th><th>K/D/A</th><th>Rating</th></tr></thead><tbody>${ROLES.map((r, i) => { const p = g.ps[s][r]; return `<tr><td>${esc(team(tid).p[i].n)}</td><td><span class="cname hov" data-tc="${esc(p.c)}" tabindex="0">${icon(p.c,26)}${esc(p.c)}</span></td><td class="num">${p.k}/${p.d}/${p.a}</td><td class="num">${g.pog.team === tid && g.pog.r === r ? "★ " : ""}${p.rt.toFixed(1)}</td></tr>`; }).join("")}</tbody></table><div class="notes">Bans: ${g.steps.filter(x => x[0] === tid && x[1] === "ban").map(x => esc(x[2])).join(", ")}</div></div>`; };
  return `<div class="gd"><div class="notes">Game ${gi + 1} · ${g.time}:${String(g.sec).padStart(2, "0")} · <b>${esc(team(g.winner).name)}</b> win · POG ${esc(g.pog.n)} (${esc(g.pog.c)}), ${esc(g.pog.why)}</div><div class="board">${side("blue")}${side("red")}</div></div>`;
}
function resultsView(){
  const days = [...new Set(RUN.matches.filter(m => m.games.length).map(m => m.day))].sort((a,b) => b - a);
  if(!days.length) return `<p class="notes">No results yet.</p>`;
  return `<div style="display:grid;gap:18px">${days.map(d => dayBlock(d, dayMatches(d).filter(m => m.games.length))).join("")}</div>`;
}
function playinView(){
  return `<div style="display:grid;gap:8px"><p class="notes" style="margin:0">Real play-in results (15–18 October, Los Angeles): Karmine Corp beat Cloud9 3-2 and MVK 3-0 twice to take the last Swiss spot; MVK beat FURIA 3-0 and 3-1; FURIA beat Cloud9 3-1. These games, on patch 26.20, are the starting meta pool before the tournament's own games are added.</p>
    ${COMPS.map(([s, g, w, l, wn, ln]) => `<div class="mrow done"><div><span class="notes">${esc(s)} · Game ${g}</span><div><b>${esc(wn)}</b> ${w.map(esc).join(", ")}</div><div class="notes">${esc(ln)}: ${l.map(esc).join(", ")}</div></div></div>`).join("")}
    <p class="notes" style="font-size:12px">Source: eGamersWorld match reports, NerfPlz pick/ban data.</p></div>`;
}

/* ---------- events ---------- */
document.addEventListener("click", e => {
  const b = e.target.closest("button"); if(!b) return;
  if(b.dataset.act === "tplay"){ tourPlay(); return; }
  if(b.dataset.act === "tnext"){ tourNext(); return; }
  if(b.dataset.tv){ TV = b.dataset.tv; renderTour(); return; }
  if(b.dataset.sr){ statRole = b.dataset.sr; renderTour(); return; }
  if(b.dataset.ss){ statSort = b.dataset.ss; renderTour(); return; }
  if(b.dataset.cr){ chRole = b.dataset.cr; renderTour(); return; }
  if(b.dataset.cs){ chSort = b.dataset.cs; renderTour(); return; }
  if(b.dataset.st){ statTab = b.dataset.st; try{ localStorage.setItem("lolw26-stat-tab", statTab); }catch(_){} renderTour(); return; }
  const a = b.dataset.ta; if(!a) return;
  if(a !== "new") tourConfirmNew = false;
  if(a === "start"){
    const mode = (document.querySelector('input[name="tMode"]:checked') || {}).value || "teams";
    const picked = [...document.querySelectorAll('input[name="tTeam"]:checked')].map(x => x.value);
    const err = document.getElementById("tErr");
    if(mode === "teams" && (picked.length < 1 || picked.length > 4)){ err.textContent = "Choose between 1 and 4 teams."; return; }
    if(mode === "guest" && picked.length !== 1){ err.textContent = "Choose exactly 1 team for guest-pick mode."; return; }
    newRun(mode, mode === "sim" ? [] : picked); TV = "today"; renderTour(); return;
  }
  if(!RUN) return;
  const m = b.dataset.m ? M(b.dataset.m) : null;
  if(a === "sim" && m){ b.textContent = "Simulating…"; setTimeout(() => { simMatch(m); renderTour(); }, 20); }
  else if(a === "sim1" && m){ b.textContent = "Simulating…"; setTimeout(() => { if(m.status !== "done") playAIGame(m); renderTour(); }, 20); }
  else if(a === "back"){ DS.tour = null; DS.steps = []; DS.sim = null; TV = "today"; show("tour"); }
  else if(a === "draft" && m) startUserGame(m);
  else if(a === "simday"){ b.textContent = "Simulating…"; setTimeout(() => { simAIToday(); renderTour(); }, 20); }
  else if(a === "simnext"){ b.textContent = "Simulating…"; setTimeout(() => { if(RUN.mode === "sim"){ for(let i = 0; i < 20; i++){ simAIToday(); if(!advanceDay()) break; } } else simToNext();
    const nx = dayMatches(RUN.day).find(x => x.status !== "done" && ctrlOf(x)); tourFocus = nx ? nx.id : null; if(nx) TV = "today"; renderTour();
    if(nx){ const el = document.getElementById("mc-" + nx.id); if(el) el.scrollIntoView({behavior:"smooth", block:"center"}); setTimeout(() => { tourFocus = null; const e2 = document.getElementById("mc-" + nx.id); if(e2) e2.classList.remove("focus"); }, 2600); } }, 20); }
  else if(a === "advance"){ advanceDay(); renderTour(); }
  else if(a === "resume") show("draft");
  else if(a === "open" && m){ tourOpen[m.id] = !tourOpen[m.id]; renderTour(); }
  else if(a === "export"){ const blob = new Blob([JSON.stringify(RUN)], {type:"application/json"}); const u = URL.createObjectURL(blob); const l = document.createElement("a"); l.href = u; l.download = `worlds26-run-day${RUN.day + 1}.json`; document.body.appendChild(l); l.click(); l.remove(); setTimeout(() => URL.revokeObjectURL(u), 1000); }
  else if(a === "copy"){ const t = JSON.stringify(RUN); (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(() => { b.textContent = "Copied"; }).catch(() => { b.textContent = "Copy failed — use the download"; }); }
  else if(a === "new"){ if(tourConfirmNew){ clearRun(); tourConfirmNew = false; DS.tour = null; } else tourConfirmNew = true; renderTour(); }
});
document.addEventListener("change", e => {
  const t = e.target;
  if(t.id === "tGuestAI" && RUN){ RUN.guestAI = t.checked; saveRun(); renderTour(); }
  if(t.id === "tImport" && t.files && t.files[0]){
    if(t.files[0].size > 2e6){ const err = document.getElementById("tErr"); if(err) err.textContent = "That file is too large to be a run file."; t.value = ""; return; }
    const fr = new FileReader();
    fr.onload = () => { try{ if(fr.result.length > 2e6) throw 0; RUN = sanitizeRun(JSON.parse(fr.result)); drawDay(); saveRun(); TV = "today"; renderTour(); }catch(_){ const err = document.getElementById("tErr"); if(err) err.textContent = "That file isn't a run file from this page."; } };
    fr.readAsText(t.files[0]);
  }
});
/* guest mode: 'AI until my team plays' switches off once your team's match is finished (see recordGame). */
document.addEventListener("input", e => { if(e.target.id !== "tChQ") return; chQ = e.target.value; const pos = e.target.selectionStart; renderTour(); const q = document.getElementById("tChQ"); if(q){ q.focus(); try{ q.setSelectionRange(pos, pos); }catch(_){} } });
