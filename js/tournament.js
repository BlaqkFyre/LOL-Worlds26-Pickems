/* =====================================================================
   Tournament mode: Worlds 2026 Swiss stage + knockouts, with a live
   stats pool that feeds later drafts, LCK-style Player of the Game,
   and tournament awards. Loaded before core.js; only calls core
   functions at run time.
   ===================================================================== */
const SAVE_KEY = "lolw26-pickems-run-v1";
const BASE_GAMES = 22; // play-in games behind the pre-Worlds presence numbers (NerfPlz)

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
function loadRun(){ try{ const s = localStorage.getItem(SAVE_KEY); if(s){ const r = JSON.parse(s); if(r && r.v === 1) RUN = r; } }catch(e){ RUN = null; } }
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
   objective control for junglers/supports. Only the winning side is
   eligible, as with LCK POG votes; each POG earns 100 POG points. */
const ROLE_DMG = {TOP:1.0, JGL:0.8, MID:1.25, ADC:1.35, SUP:0.45};
const ROLE_SHARE = {TOP:0.22, JGL:0.15, MID:0.27, ADC:0.29, SUP:0.07};
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
        + 1.6 * Math.min(1.6, p.dmgS / ROLE_SHARE[r])
        + 0.9 * Math.max(-1, Math.min(1, p.csd / 20))
        + 0.5 * p.solo
        + (r === "SUP" ? 0.9 * (p.vis - 1.6) : 0)
        + ((r === "JGL" || r === "SUP") ? 0.18 * p.objs : 0)
        - 0.15 * p.d;
      p.rt = Math.max(0, Math.min(10, rt));
    });
  });
  const w = g.winner, T = w === "blue" ? g.B : g.R;
  const best = ROLES.map(r => ({r, p: g.ps[w][r]})).sort((x,y) => y.p.rt - x.p.rt)[0];
  const p = best.p, why = [];
  why.push(`${p.k}/${p.d}/${p.a}`);
  why.push(`${Math.round(p.kp * 100)}% KP`);
  if(p.dmgS > ROLE_SHARE[best.r] * 1.1) why.push(`${Math.round(p.dmgS * 100)}% team damage`);
  if(p.csd >= 8) why.push(`+${p.csd} CS at 15`);
  if(p.solo) why.push(`${p.solo} solo kill${p.solo > 1 ? "s" : ""}`);
  if(best.r === "SUP") why.push(`${p.vis} vision/min`);
  g.pog = {s: w, r: best.r, n: T.P[best.r].pl.n, c: T.P[best.r].c, rt: p.rt, why: why.join(" · ")};
}

/* ---------- run setup ---------- */
function newRun(mode, myTeams){
  RUN = {v:1, mode, myTeams, guestAI:false, day:0, matches:[], W:{}, L:{}, met:[],
    stats:{games:0, champ:{}, pchamp:{}, players:{}}, created:Date.now(), updated:Date.now()};
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
    steps: DS.steps.map(s => [s.t, s.k, s.c, s.r || ""]), ps, pog:{...g.pog, team: g.pog.s === "blue" ? blue : red}};
}
function playAIGame(m){
  const gi = m.games.length, blue = blueFor(m, gi), red = blue === m.a ? m.b : m.a;
  const rec = withDS({blue, red, fmt: m.bo > 1 ? "fearless" : "bo1", locked: lockedFor(m)}, () => { while(DS.steps.length < 20) autoStep(); return pack(simGame(false)); });
  recordGame(m, rec);
}
function recordGame(m, rec){
  m.games.push(rec);
  const S = RUN.stats; S.games++;
  rec.steps.forEach(([t, k, c]) => { const st = S.champ[c] = S.champ[c] || {p:0, b:0, w:0}; if(k === "ban") st.b++; else { st.p++; if(t === rec.winner) st.w++; } });
  ["blue","red"].forEach(s => {
    const tid = s === "blue" ? rec.blue : rec.red, won = rec.winner === tid;
    ROLES.forEach((r, i) => {
      const key = tid + "|" + i, p = rec.ps[s][r];
      const P = S.players[key] = S.players[key] || {g:0, w:0, k:0, d:0, a:0, kp:0, dmgS:0, csd:0, vis:0, solo:0, rt:0, pog:0, pts:0, swissPts:0, finRt:[]};
      P.g++; if(won) P.w++; ["k","d","a","kp","dmgS","csd","vis","solo","rt"].forEach(f => P[f] += p[f]);
      if(m.stage === "F") P.finRt.push(p.rt);
      const pc = (S.pchamp[key] = S.pchamp[key] || {}); const e = pc[p.c] = pc[p.c] || {g:0, w:0}; e.g++; if(won) e.w++;
    });
  });
  const pk = rec.pog.team + "|" + ROLES.indexOf(rec.pog.r);
  const P = S.players[pk]; P.pog++; P.pts += 100; if(m.phase === "swiss") P.swissPts += 100;
  const need = Math.ceil(m.bo / 2), wa = seriesWins(m, m.a), wb = seriesWins(m, m.b);
  if(wa >= need || wb >= need){
    m.status = "done"; m.w = wa > wb ? m.a : m.b; m.l = m.w === m.a ? m.b : m.a; m.sc = `${Math.max(wa,wb)}-${Math.min(wa,wb)}`;
    if(m.phase === "swiss"){ RUN.W[m.w]++; RUN.L[m.l]++; RUN.met.push(m.a + "|" + m.b, m.b + "|" + m.a); }
    if(RUN.mode === "guest" && RUN.myTeams.some(id => id === m.a || id === m.b)) RUN.guestAI = false;
  }
  saveRun();
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
    locked: lockedFor(m), steps:[], ai:true, showUsed:false, fresh:-1, sim:null, q:"", roleF:"ALL", game:gi + 1,
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
  recordGame(m, rec);
  DS.tour.next = m.status === "done" ? "Back to the tournament" : `Next game (${team(m.a).id} ${seriesWins(m, m.a)}–${seriesWins(m, m.b)} ${team(m.b).id})`;
  DS.sim = {g, bwin: bw / 300};
  renderDraft();
  const sEl = document.querySelector(".sim"); if(sEl) sEl.scrollIntoView({behavior:"smooth", block:"start"});
}
function tourNext(){
  const m = M(DS.tour.mid);
  if(m && m.status !== "done"){ startUserGame(m); return; }
  DS.tour = null; DS.steps = []; DS.sim = null; DS.ai = false; DS.locked = []; DS.fmt = "bo1";
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
function teamTag(id){ return `<span class="ttag">${esc(id)}</span>`; }
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
        ${RUN.mode !== "sim" ? `<button class="btn" data-ta="simnext">Sim to my next match</button>` : `<button class="btn" data-ta="simnext">Sim to end of event</button>`}
        ${dayDone(RUN.day) && RUN.day < DAYS.length - 1 ? `<button class="btn primary" data-ta="advance">Next day →</button>` : ""}
        ${RUN.mode === "guest" ? `<label class="tog"><input type="checkbox" id="tGuestAI"${RUN.guestAI ? " checked" : ""}> Play guest games as AI until my team plays</label>` : ""}
      </div></div>
    ${DS.tour ? `<div class="turn blue"><span>A draft is in progress.</span><div class="ctrls"><button class="btn primary" data-ta="resume">Resume draft</button></div></div>` : ""}
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
function matchRow(m){
  const ctrl = ctrlOf(m), wa = seriesWins(m, m.a), wb = seriesWins(m, m.b);
  const res = m.status === "done" ? `<b>${esc(m.w)}</b> wins ${m.sc}` : m.games.length ? `${wa}–${wb} in progress` : "Not started";
  const act = m.status === "done" ? "" : ctrl ? `<button class="btn primary" data-ta="draft" data-m="${m.id}">${m.games.length ? "Draft next game" : "Draft"} as ${esc(ctrl)}</button><button class="btn" data-ta="sim" data-m="${m.id}">Sim it</button>` : `<button class="btn" data-ta="sim" data-m="${m.id}">Sim</button>`;
  const pogs = m.games.map(g => `G${m.games.indexOf(g) + 1} POG ${esc(g.pog.n)}`).join(" · ");
  return `<div class="mrow ${m.status}"><div><span class="notes">${esc(stageName(m))} · Bo${m.bo}</span><div class="mteams">${teamTag(m.a)} ${esc(team(m.a).name)} <span class="vs">vs</span> ${teamTag(m.b)} ${esc(team(m.b).name)}</div><span class="notes">${res}${pogs ? " · " + pogs : ""}</span></div><div class="ctrls">${act}</div></div>`;
}
function todayView(today){
  if(!today.length) return `<p class="notes">Matches for this day are drawn once the previous round finishes.</p>`;
  const next = DAYS[RUN.day + 1];
  return `<div style="display:grid;gap:8px">${today.map(matchRow).join("")}</div>${next ? `<p class="notes">Next: ${esc(next.date)} · ${esc(next.label)}</p>` : ""}`;
}
function standingsView(){
  const rows = TEAMS.map(t => t.id).sort((a,b) => (RUN.W[b] - RUN.L[b]) - (RUN.W[a] - RUN.L[a]) || RUN.W[b] - RUN.W[a] || team(b).ov - team(a).ov);
  const st = id => RUN.W[id] >= 3 ? `<span class="chip meta">Qualified</span>` : RUN.L[id] >= 3 ? `<span class="chip off">Eliminated</span>` : `<span class="chip mix">Alive</span>`;
  const gw = id => { let w = 0, l = 0; RUN.matches.forEach(m => m.games.forEach(g => { if(g.blue === id || g.red === id){ g.winner === id ? w++ : l++; } })); return `${w}-${l}`; };
  return `<div style="overflow-x:auto"><table class="tt full"><thead><tr><th>Team</th><th>Swiss record</th><th>Games</th><th>Status</th></tr></thead><tbody>${rows.map(id => `<tr class="${RUN.myTeams.includes(id) ? "me" : ""}"><td>${teamTag(id)} ${esc(team(id).name)}</td><td class="num">${RUN.W[id]}-${RUN.L[id]}</td><td class="num">${gw(id)}</td><td>${st(id)}</td></tr>`).join("")}</tbody></table></div>`;
}
function bracketView(){
  const cell = id => { const m = M(id); if(!m) return `<div class="bcell"><span class="notes">TBD</span></div>`; return `<div class="bcell ${m.status}">${[m.a, m.b].map(t => `<div class="${m.w === t ? "bw" : ""}">${teamTag(t)} ${esc(team(t).name)} <b>${seriesWins(m, t)}</b></div>`).join("")}<span class="notes">${esc(DAYS[m.day].date)}</span></div>`; };
  return `<div class="bracket"><div><div class="eyebrow">Quarter-finals</div>${["QF1","QF2","QF3","QF4"].map(cell).join("")}</div><div><div class="eyebrow">Semi-finals</div>${["SF1","SF2"].map(cell).join("")}</div><div><div class="eyebrow">Final</div>${cell("F")}</div></div>`;
}
let statRole = "ALL", statSort = "pts";
function statsView(){
  const S = RUN.stats; if(!S.games) return `<p class="notes">No games played yet. Presence numbers still use the play-in data.</p>`;
  const ch = Object.entries(S.champ).map(([c, v]) => ({c, ...v, pres: Math.round((v.p + v.b) / S.games * 100)})).sort((a,b) => b.pres - a.pres).slice(0, 30);
  const rows = playerRows().filter(r => statRole === "ALL" || r.p.role === statRole);
  const f = {pts: r => r.s.pts, rt: r => r.avgRt, kda: r => (r.s.k + r.s.a) / Math.max(1, r.s.d), dmg: r => r.s.dmgS / r.s.g, csd: r => r.s.csd / r.s.g}[statSort];
  rows.sort((a,b) => f(b) - f(a));
  const th = (k, l) => `<th><button class="sortb" data-ss="${k}" aria-pressed="${statSort === k}">${l}</button></th>`;
  return `<div style="display:grid;gap:16px">
    <div><div class="eyebrow">Champions at this Worlds · ${S.games} games</div><p class="notes" style="margin:2px 0 6px">Presence = picked or banned in that share of games. Drafts blend this with the play-in data, weighting the tournament more as games are played.</p>
    <div style="overflow-x:auto"><table class="tt full"><thead><tr><th>Champion</th><th>Presence</th><th>Picks</th><th>Bans</th><th>W-L</th><th>Win rate</th></tr></thead><tbody>${ch.map(x => `<tr><td class="hov" data-tc="${esc(x.c)}" tabindex="0">${esc(x.c)}</td><td class="num">${x.pres}%</td><td class="num">${x.p}</td><td class="num">${x.b}</td><td class="num">${x.w}-${x.p - x.w}</td><td class="num">${x.p ? Math.round(x.w / x.p * 100) + "%" : "–"}</td></tr>`).join("")}</tbody></table></div></div>
    <div><div class="eyebrow">Players</div><div class="seg" style="margin:6px 0">${[["ALL","All"], ...ROLES.map(r => [r, r])].map(([k,l]) => `<button data-sr="${k}" aria-pressed="${statRole === k}">${l}</button>`).join("")}</div>
    <div style="overflow-x:auto"><table class="tt full"><thead><tr><th>Player</th><th>Games</th>${th("pts","POG pts")}${th("rt","Avg rating")}${th("kda","KDA")}<th>KP</th>${th("dmg","DMG%")}${th("csd","CSD@15")}</tr></thead><tbody>${rows.slice(0, 40).map(r => `<tr><td><span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span> <span class="notes">${r.tid} ${r.p.role}</span></td><td class="num">${r.s.g}</td><td class="num">${r.s.pts}</td><td class="num">${r.avgRt.toFixed(2)}</td><td class="num">${kdaOf(r.s)}</td><td class="num">${Math.round(r.s.kp / r.s.g * 100)}%</td><td class="num">${Math.round(r.s.dmgS / r.s.g * 100)}%</td><td class="num">${(r.s.csd / r.s.g).toFixed(1)}</td></tr>`).join("")}</tbody></table></div></div>
  </div>`;
}
function awardsView(aw){
  const card = (title, r, sub, pending) => `<div class="award"><span class="eyebrow">${title}</span>${r ? `<b><span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span> <span class="notes">${r.tid} ${r.p.role}</span></b><span class="notes">${sub(r)}</span>` : `<span class="notes">${pending}</span>`}${pending && r && pending.startsWith("Leading") ? `<span class="notes">${pending}</span>` : ""}</div>`;
  const lead = playerRows().filter(r => r.s.pog).sort((a,b) => b.s.pts - a.s.pts || b.avgRt - a.avgRt).slice(0, 10);
  return `<div style="display:grid;gap:14px">
    <div class="awards">
      ${card("Swiss stage MVP", aw.swissMVP, r => `${r.s.swissPts} POG points in the Swiss stage · avg rating ${r.avgRt.toFixed(2)}`, aw.swissDone ? "" : "Leading so far — awarded when the Swiss stage ends")}
      ${card("Tournament MVP", aw.tourMVP, r => `${r.s.pts} POG points · ${r.s.pog} POG · avg rating ${r.avgRt.toFixed(2)}`, aw.done ? "" : "Leading so far — awarded after the final")}
      ${card("Finals MVP", aw.finalsMVP, r => `avg rating ${avg(r.s.finRt).toFixed(2)} across ${r.s.finRt.length} final games`, "Awarded to the best-rated player on the winning team in the final")}
    </div>
    <div><div class="eyebrow">All-Tournament team ${aw.done ? "" : "(current)"}</div><p class="notes" style="margin:2px 0 6px">Best average game rating per role, minimum ${aw.minG} games.</p>
    <div class="team5">${aw.team5.map((r, i) => `<div><span class="role">${ROLES[i]}</span>${r ? `<b class="hov" data-tp="${r.tid}|${i}" tabindex="0">${esc(r.p.n)}</b><span class="notes">${r.tid} · ${r.avgRt.toFixed(2)}</span>` : `<span class="notes">—</span>`}</div>`).join("")}</div></div>
    <div><div class="eyebrow">POG points leaderboard</div>${lead.length ? `<table class="tt full"><thead><tr><th>#</th><th>Player</th><th>POG</th><th>Points</th><th>Avg rating</th></tr></thead><tbody>${lead.map((r, i) => `<tr><td>${i + 1}</td><td><span class="hov" data-tp="${r.tid}|${ROLES.indexOf(r.p.role)}" tabindex="0">${esc(r.p.n)}</span> <span class="notes">${r.tid} ${r.p.role}</span></td><td class="num">${r.s.pog}</td><td class="num">${r.s.pts}</td><td class="num">${r.avgRt.toFixed(2)}</td></tr>`).join("")}</tbody></table>` : `<p class="notes">No games yet.</p>`}</div>
    <p class="notes" style="font-size:12px">Game rating (0–10) weighs the numbers that make LCK Player of the Game winners stand out: the result, KDA and deaths, kill participation, damage share against the role's norm, CS lead at 15, solo kills, vision (supports) and objectives (junglers and supports). Metric choices follow LeagueLab's metrics guide and Team Liquid's statistical-standouts piece; points follow the LCK POG system.</p>
  </div>`;
}
function gameDetail(m, g, gi){
  const side = s => { const tid = s === "blue" ? g.blue : g.red; return `<div class="an ${s}"><h3>${esc(team(tid).name)} <small>${g.winner === tid ? "won" : "lost"} · ${g.kills[s]} kills</small></h3><table class="tt full"><thead><tr><th>Player</th><th>Champion</th><th>K/D/A</th><th>Rating</th></tr></thead><tbody>${ROLES.map((r, i) => { const p = g.ps[s][r]; return `<tr><td>${esc(team(tid).p[i].n)}</td><td class="hov" data-tc="${esc(p.c)}" tabindex="0">${esc(p.c)}</td><td class="num">${p.k}/${p.d}/${p.a}</td><td class="num">${g.pog.team === tid && g.pog.r === r ? "★ " : ""}${p.rt.toFixed(1)}</td></tr>`; }).join("")}</tbody></table><div class="notes">Bans: ${g.steps.filter(x => x[0] === tid && x[1] === "ban").map(x => esc(x[2])).join(", ")}</div></div>`; };
  return `<div class="gd"><div class="notes">Game ${gi + 1} · ${g.time}:${String(g.sec).padStart(2, "0")} · <b>${esc(team(g.winner).name)}</b> win · POG ${esc(g.pog.n)} (${esc(g.pog.c)}), ${esc(g.pog.why)}</div><div class="board">${side("blue")}${side("red")}</div></div>`;
}
function resultsView(){
  const done = RUN.matches.filter(m => m.games.length).slice().reverse();
  if(!done.length) return `<p class="notes">No results yet.</p>`;
  return `<div style="display:grid;gap:8px">${done.map(m => `<div class="mrow ${m.status}"><div style="flex:1"><span class="notes">${esc(DAYS[m.day].date)} · ${esc(stageName(m))} · Bo${m.bo}</span><div class="mteams">${teamTag(m.a)} ${seriesWins(m, m.a)}–${seriesWins(m, m.b)} ${teamTag(m.b)} ${m.status === "done" ? `<span class="notes">${esc(team(m.w).name)} win</span>` : ""}</div>${tourOpen[m.id] ? m.games.map((g, i) => gameDetail(m, g, i)).join("") : ""}</div><div class="ctrls"><button class="btn" data-ta="open" data-m="${m.id}">${tourOpen[m.id] ? "Hide" : "Games"}</button></div></div>`).join("")}</div>`;
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
  else if(a === "draft" && m) startUserGame(m);
  else if(a === "simday"){ b.textContent = "Simulating…"; setTimeout(() => { simAIToday(); renderTour(); }, 20); }
  else if(a === "simnext"){ b.textContent = "Simulating…"; setTimeout(() => { if(RUN.mode === "sim"){ for(let i = 0; i < 20; i++){ simAIToday(); if(!advanceDay()) break; } } else simToNext(); renderTour(); }, 20); }
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
    const fr = new FileReader();
    fr.onload = () => { try{ const r = JSON.parse(fr.result); if(r && r.v === 1 && r.matches){ RUN = r; saveRun(); TV = "today"; renderTour(); } else throw 0; }catch(_){ const err = document.getElementById("tErr"); if(err) err.textContent = "That file isn't a run file from this page."; } };
    fr.readAsText(t.files[0]);
  }
});
/* guest mode: 'AI until my team plays' switches off once your team's match is finished (see recordGame). */
