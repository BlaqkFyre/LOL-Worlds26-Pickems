/* Worlds 2026 Pick'Em: views, meta, counters, champ select and game simulation. */

const ROLES=["TOP","JGL","MID","ADC","SUP"];
const RNAME={TOP:"Top",JGL:"Jungle",MID:"Mid",ADC:"ADC",SUP:"Support"};
const ATTR={TOP:["Laning","Teamfight","Consistency"],JGL:["Early game","Objectives","Teamfight"],MID:["Laning","Roaming","Damage"],ADC:["Laning","Damage","Positioning"],SUP:["Playmaking","Map presence","Reliability"]};
/* Champion pro data (js/champions.js): blended presence bl = 0.9 × (26.20 weighted 4× + 26.16–26.20) + 0.1 × season */
function metaOf(c){const d=CHAMP_DB[c],b=d&&d.bl;if(b>=30)return["meta",`Meta: ${Math.round(b)}% pick/ban presence in recent pro play`];if(b>0)return["mix",`In the mix: ${Math.round(b)}% presence in recent pro play`];return["off","Not in the recent pro pick/ban tables"];}
/* sample-size-shrunk win rate: (wins+20)/(games+40), from the freshest table that lists the champion */
function wrOf(c){const d=CHAMP_DB[c];if(!d)return null;let n=0,wr=null,src="";
  if(d.rec){n=Math.round(d.rec[0]*4.65);wr=d.rec[2];src="26.16–26.20"}else if(d.p20&&!d.sea){n=Math.round(d.p20[0]*.25);wr=d.p20[2];src="26.20"}
  else if(d.sea){n=Math.round(d.sea[0]*27.23);wr=d.sea[2];src="2026 season"}else if(d.g&&d.w!=null){n=d.g;wr=Math.round(d.w/d.g*100);src="2026 pro, all leagues"}
  const wl=(typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.champ[c])||{p:0,w:0};
  if(wr==null||!n){if(!wl.p)return null;return {wr:Math.round(wl.w/wl.p*100),n:wl.p,src:"Worlds 2026",adj:Math.round((wl.w*2+20)/(wl.p*2+40)*1000)/10}}
  return {wr,n,src,adj:Math.round((wr/100*n+wl.w*2+20)/(n+wl.p*2+40)*1000)/10}}
function trendOf(c){const d=CHAMP_DB[c];if(!d)return"";if(d.fade)return"fading";if(d.tr>=6)return"rising";if(d.tr<=-6)return"falling";return""}
const TREND_TXT={rising:"▲ rising",falling:"▼ falling",fading:"fading"};

const avg=a=>a.reduce((s,x)=>s+x,0)/a.length;
TEAMS.forEach(t=>{t.p=t.p.map((r,i)=>({n:r[0],a:r[1],picks:r[2],kda:r[3],note:r[4],role:ROLES[i],team:t,key:t.id+"|"+i,ov:Math.round(avg(r[1]))}));t.ov=Math.round(avg(t.p.map(x=>x.ov))*10)/10;
  t.metaFit=t.p.reduce((s,p)=>s+p.picks.filter(c=>metaOf(c[0])[0]==="meta").length,0);});
const tier=v=>v>=95?"var(--gold)":v>=90?"var(--teal)":v>=85?"var(--blue)":"var(--grey)";
const pct=v=>Math.max(0,Math.min(100,(v-60)/40*100));
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const bar=(v,label)=>`<div class="bar" role="img" aria-label="${esc(label)} ${v}"><b style="width:${pct(v)}%;background:${tier(v)}"></b></div>`;
function chips(p){
  if(!p.picks.length)return `<div class="chips"><span class="chip off">No 2026 champion data found</span></div>`;
  return `<div class="chips">${p.picks.map(([c,g,w])=>{const[m,t]=metaOf(c);return `<span class="chip ${m}" data-tc="${esc(c)}" tabindex="0">${icon(c,18)}${esc(c)} <em>${g?g+"g ":""}${w}%</em></span>`}).join("")}</div>`;
}

/* Simulated games stay inside their own mode: a tournament run's numbers show only on tournament screens
   (and a draft started from the tournament). Everywhere else the app shows real data only. */
let CUR="tour";
const runCtx=()=>(typeof RUN!=="undefined"&&RUN&&(CUR==="tour"||(CUR==="draft"&&DS.tour)))?RUN:null;
/* main menu: three sections (Play, Game Details, Teams), each with its own pages as sub-tabs */
const SECTIONS=[["play","Play"],["details","Game Details"],["teams","Teams"]];
const VIEWS=[["tour","Worlds 2026","play"],["custom","Custom","play"],["draft","Champ Select","play"],
  ["meta","Meta","details"],["ctop","Top","details"],["cjungle","Jungle","details"],["cmid","Mid","details"],["cadc","ADC","details"],["csupport","Support","details"],
  ["power","Power Rankings","teams"],["rosters","Rosters","teams"],["top","Top","teams"],["jungle","Jungle","teams"],["mid","Mid","teams"],["adc","ADC","teams"],["support","Support","teams"]];
const VROLE={top:"TOP",jungle:"JGL",mid:"MID",adc:"ADC",support:"SUP"},CROLE={ctop:"TOP",cjungle:"JGL",cmid:"MID",cadc:"ADC",csupport:"SUP"};
const GAPBEFORE=new Set(["draft","ctop","top"]),LASTV={play:"tour",details:"meta",teams:"power"},OLDV={teams:"power"};
const tabs=document.getElementById("tabs"),subtabs=document.getElementById("subtabs");
function drawNav(v){const sec=(VIEWS.find(x=>x[0]===v)||VIEWS[0])[2];
  tabs.innerHTML=SECTIONS.map(([k,l])=>`<button role="tab" data-sec="${k}" aria-selected="${k===sec}">${l}</button>`).join("");
  subtabs.innerHTML=VIEWS.filter(x=>x[2]===sec).map(([k,l])=>`<button role="tab" data-v="${k}" aria-selected="${k===v}" class="${GAPBEFORE.has(k)?"gap":""}${k==="custom"?" soon":""}">${l}${k==="custom"?"<small>soon</small>":""}</button>`).join("")}
function show(v){
  v=OLDV[v]||v;if(!VIEWS.some(x=>x[0]===v))v="tour";CUR=v;LASTV[VIEWS.find(x=>x[0]===v)[2]]=v;drawNav(v);
  const lg=document.querySelector("header .legend");if(lg)lg.hidden=v==="tour"||v==="custom"; /* ratings and meta tags aren't used on these pages; the tournament reuses the tag colours for Qualified/Alive/Eliminated */
  const tv=document.getElementById("v-tour");if(tv){tv.hidden=v!=="tour";if(v==="tour"&&typeof renderTour==="function")renderTour()}
  const teamsV=v==="power"||v==="rosters";document.getElementById("v-teams").hidden=!teamsV;
  if(teamsV){document.getElementById("powerPanel").hidden=v!=="power";document.getElementById("cmpPanel").hidden=v!=="power";document.getElementById("rosterPanel").hidden=v!=="rosters";if(v==="power")drawPower()}
  document.getElementById("v-draft").hidden=v!=="draft";if(v==="draft")renderDraft();
  const rv=document.getElementById("v-role"),inRole=!teamsV&&v!=="draft"&&v!=="tour";rv.hidden=!inRole;
  if(inRole){rv.innerHTML=v==="meta"?metaView():v==="custom"?customView():CROLE[v]?champRoleView(CROLE[v]):roleView(VROLE[v]);fitTicks(rv);if(document.fonts)document.fonts.ready.then(()=>{if(!rv.hidden)fitTicks(rv)})}
  try{history.replaceState(null,"","#"+v)}catch(e){}
}
tabs.addEventListener("click",e=>{const b=e.target.closest("button[data-sec]");if(b)show(LASTV[b.dataset.sec])});
subtabs.addEventListener("click",e=>{const b=e.target.closest("button[data-v]");if(b)show(b.dataset.v)});
const ranked=[...TEAMS].sort((a,b)=>b.ov-a.ov);

/* roster cards */
document.getElementById("grid").innerHTML=ranked.map(t=>`<article class="panel team"><div class="thead"><div><h3>${regDot(t.id)}${esc(t.name)}</h3><small>${esc(t.reg)} · ${t.metaFit}/15 favourite picks meta</small></div><div class="tscore">${t.ov.toFixed(1)}</div></div>`+
  t.p.map(p=>`<div><div class="prow"><span class="role">${p.role}</span><div><div class="pn"><span class="hov" data-tp="${t.id}|${ROLES.indexOf(p.role)}" tabindex="0">${esc(p.n)}</span></div>${bar(p.ov,p.n)}</div><span class="num">${p.ov}</span></div><div style="margin-left:48px">${chips(p)}</div></div>`).join("")+`</article>`).join("");

/* compare */
const sA=document.getElementById("tA"),sB=document.getElementById("tB");
[sA,sB].forEach(s=>s.innerHTML=TEAMS.map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join(""));
sA.value="LYON";sB.value="TSW";
function side(cls,name,v,col){return `<div class="cside ${cls}"><div class="cname">${esc(name)} <span style="font-family:var(--mono)">${v}</span></div><div class="cbar"><b style="width:${pct(v)}%;background:${col}"></b></div></div>`}
function drawCmp(){
  const A=TEAMS.find(t=>t.id===sA.value),B=TEAMS.find(t=>t.id===sB.value);
  const row=(label,a,b,an,bn,total)=>{const d=Math.round((a-b)*10)/10;
    return `<div class="crow${total?" ctotal":""}">${side("l",an,a,d>=0?tier(a):"var(--grey)")}<div class="cmid">${label}<span class="edge"${d===0?' style="color:var(--muted)"':""}>${d===0?"even":(d>0?A.id:B.id)+" +"+Math.abs(d)}</span></div>${side("r",bn,b,d<=0?tier(b):"var(--grey)")}</div>`};
  document.getElementById("cmp").innerHTML=ROLES.map((r,i)=>row(RNAME[r],A.p[i].ov,B.p[i].ov,A.p[i].n,B.p[i].n)).join("")+row("Team",A.ov,B.ov,A.name,B.name,true);
}
sA.addEventListener("change",drawCmp);sB.addEventListener("change",drawCmp);drawCmp();

/* role tier lists */
const TIERS=[["S",93,"Elite","var(--gold)"],["A",89,"World class","var(--teal)"],["B",84,"Strong","var(--blue)"],["C",78,"Solid","var(--grey)"],["D",0,"Underdog","var(--grey)"]];
/* ---- card pages (same look as the hover cards) ---- */
const ovBox=v=>`<span class="ov" title="Overall rating" style="--oc:${tier(v)}"><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span><span class="n">${v}</span></span>`;
const ticker=t=>t?`<div class="tick"><b>Note</b><div class="rail"><span>${esc(t)}</span></div></div>`:"";
/* a note scrolls only when it doesn't fit its bar (checked after render and on resize), at a steady speed */
function fitTicks(root){root.querySelectorAll(".tick .rail").forEach(r=>{const s=r.firstElementChild;r.classList.remove("run");s.style.animationDuration="";
  if(r.scrollWidth>r.clientWidth+1){s.style.animationDuration=Math.max(8,(r.scrollWidth+r.clientWidth)/45).toFixed(1)+"s";r.classList.add("run")}})}
let fitT=null,fitW=0;const fitRO=typeof ResizeObserver==="function"&&new ResizeObserver(es=>{const w=Math.round(es[0].contentRect.width);if(w===fitW)return;fitW=w;clearTimeout(fitT);fitT=setTimeout(()=>{const rv=document.getElementById("v-role");if(rv&&!rv.hidden)fitTicks(rv)},150)});
if(fitRO)fitRO.observe(document.getElementById("v-role"));
function playerCard(p,rk){const idx=ROLES.indexOf(p.role),tid=p.team.id;
  const wp=(typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.pchamp[p.n])||{},seen=new Set(),tiles=[];
  Object.entries(wp).sort((a,b)=>b[1].g-a[1].g||b[1].w-a[1].w).forEach(([c,v])=>{seen.add(c);const isNew=!p.picks.some(x=>x[0]===c);
    tiles.push(`<span class="cc" data-tc="${esc(c)}" title="${esc(`${c} · ${v.g} Worlds game${v.g>1?"s":""}, ${v.w}-${v.g-v.w}${isNew?" · new at Worlds":""}`)}"><span class="pchamp${isNew?" isnew":""}">${icon(c,22)}</span><span class="cn">${esc(c)}</span><em class="${v.w*2<v.g?"b":"g"}">${v.w}-${v.g-v.w}</em></span>`)});
  p.picks.forEach(([c,g,w])=>{if(seen.has(c))return;seen.add(c);tiles.push(`<span class="cc" data-tc="${esc(c)}" title="${esc(`${c} · ${g?g+" games in 2026":"2026 pick"}${w!=null?", "+w+"% wins":""}`)}"><span class="pchamp">${icon(c,22)}</span><span class="cn">${esc(c)}</span><span class="dim">${g?g+"g":""}</span></span>`)});
  return `<article class="pcard"><div class="tiph ph" style="--tc:${teamCol(tid)}"><span class="rkn">${rk}</span>${regDot(tid)}<span class="tm">${esc(tid)}</span><b class="hov" data-tp="${tid}|${idx}" tabindex="0">${esc(p.n)}</b>${ovBox(p.ov)}</div>
  <div class="pskills skrow"><span class="prank"><b>${rk}/16</b> ${RNAME[p.role]}</span>${ATTR[p.role].map((a,j)=>skillChip(p.role,j,p.a[j])).join("")}${p.kda?`<span class="sk" title="2026 KDA"><small>KDA</small>${p.kda}</span>`:""}</div>
  ${wformBox(p)}
  <div class="ccs c3">${tiles.slice(0,6).join("")||`<span class="notes">No 2026 champion data</span>`}</div>
  ${ticker(p.note)}</article>`}
function roleView(role){
  const i=ROLES.indexOf(role),ps=TEAMS.map(t=>t.p[i]).sort((a,b)=>b.ov-a.ov||avg(b.a)-avg(a.a));
  return `<div class="panel" style="display:grid;gap:14px"><div><h2>${RNAME[role]} · all 16 Worlds teams</h2><p class="notes" style="margin:4px 0 0">Ranked by overall rating. Skills: ${ATTR[role].join(" · ")}. Worlds champions come first with their record (teal frame = new at Worlds), then 2026 picks. Hover or tap a name or champion for its full card.</p></div>
  <div class="pgrid">${ps.map((p,k)=>playerCard(p,k+1)).join("")}</div></div>`}
function champCard(c,role){const d=CHAMP_DB[c]||{},pr=presOf(c),tr=trendOf(c),W=wrOf(c),WM=worldsMeta(c),mp=mostPicked(c,6);
  const R=d.rec,RS=R?"26.16–26.20":d.sea?"2026 season":d.p20?"26.20 only":"",RT=R||d.sea||d.p20,rs=[...(ROLEMAP[c]||[])];
  return `<article class="pcard ccardp"><div class="chead">${icon(c,46)}<div><b class="hov" data-tc="${esc(c)}" tabindex="0">${esc(c)}</b><div><span class="tag">${pr?`<b class="tcol" style="color:${tierCol(tierOf(pr))}">${tierOf(pr)}-tier</b> · `:""}${rs.map(r=>RNAME[r]).join("/")||RNAME[role]}</span>${tr?`<span class="trend ${tr}">${TREND_TXT[tr]}</span>`:""}</div></div></div>
  <div class="hsec"><div class="label">Recent pro</div><div class="hbars">
  ${RT?hb("Presence",fill(RT[0]+RT[1]),`${RT[0]+RT[1]}%`,R?"465 games":RS):hb("Presence","","—","not in pro tables")}
  ${W?hb("Win rate",fill(W.wr),`${W.wr}%`,`${W.src}${W.n<15?" · small sample":""}`):hb("Win rate","","—","no data")}</div></div>
  <div class="hsec"><div class="label"><span class="hl">Worlds · ${WM.g} games</span></div><div class="hbars">
  ${hb("Pick / ban",fill(WM.pk,"pk")+fill(WM.bn,"bn"),`${WM.pk}% · ${WM.bn}%`,"picked · banned")}
  ${hb("Win rate",WM.p?fill(WM.w/WM.p*100):"",WM.p?`${WM.w}-${WM.l}`:"—",WM.p?`${Math.round(WM.w/WM.p*100)}%${WM.p<5?" · small sample":""}`:"not played")}</div></div>
  <div><div class="label">Played at Worlds by</div><div class="ccs c3">${mp.length?mp.map(e=>{const T=team(e.t),pi=T?T.p.findIndex(x=>x.n===e.n):-1;return `<span class="cc mp" style="--tc:${teamCol(e.t)}"${pi>=0?` data-tp="${e.t}|${pi}" tabindex="0"`:""} title="${esc(`${e.n} (${e.t}) · ${e.g} game${e.g>1?"s":""} on ${c} at Worlds, ${e.w}-${e.g-e.w}`)}"><span class="tm">${esc(e.t)}</span><span class="cn">${esc(e.n)}</span><em class="${e.w*2<e.g?"b":"g"}">${e.w}-${e.g-e.w}</em></span>`}).join(""):`<span class="notes">Not played at Worlds yet</span>`}</div></div>
  <div><div class="label">Counters ${infoI(BEATS_INFO)}</div><div class="ccs c3">${(bt=>bt.length?bt.map(o=>`<span class="cc" data-tc="${esc(o.x)}" tabindex="0" title="${esc(`${o.x} · ${o.note}${o.other?" · matchup from another lane":""}`)}">${icon(o.x,22)}<span class="cn">${esc(o.x)}</span><em class="g">${esc(o.em)}</em></span>`).join(""):`<span class="notes">no matchup data</span>`)(beats3(c))}</div></div></article>`}
function champRoleView(role){
  const cs=POOL.filter(c=>primaryRole(c)===role).map(c=>[c,presOf(c)]).sort((a,b)=>b[1]-a[1]).map(x=>x[0]);
  const shown=cs.filter(c=>presOf(c)>0||worldsMeta(c).p+worldsMeta(c).b>0);
  return `<div class="panel" style="display:grid;gap:14px"><div><h2>${RNAME[role]} champions</h2><p class="notes" style="margin:4px 0 0">Every ${RNAME[role].toLowerCase()} champion seen in recent pro play or at Worlds, by blended presence. Recent pro = patches 26.16–26.20; Worlds = real play-in and Swiss games. Hover or tap a champion for its full card.</p></div>
  <div class="pgrid">${shown.map(c=>champCard(c,role)).join("")}</div></div>`}
function customView(){return `<div class="panel" style="display:grid;gap:10px;max-width:640px"><h2>Custom tournament</h2><p class="notes" style="margin:0">Coming soon: pick your own teams, format and draw, then play it out with the same draft and sim. For now, use <b>Worlds 2026</b> for the full event or <b>Champ Select</b> for a single Bo1, Bo3 or Bo5.</p><div><button class="btn primary" data-goto="tour">Go to Worlds 2026</button> <button class="btn" data-goto="draft">Go to Champ Select</button></div></div>`}
document.addEventListener("click",e=>{const b=e.target.closest("button[data-goto]");if(b)show(b.dataset.goto)});
/* power rankings with real 2026 head-to-head (never simulated games) */
let pwSel=null;
function drawPower(){const el=document.getElementById("powerPanel");if(!el)return;pwSel=pwSel||ranked[0].id;
  const H=(typeof H2H_2026!=="undefined"&&H2H_2026.g)||{},h=H[pwSel]||{},T=team(pwSel);
  const rows=ranked.filter(t=>t.id!==pwSel&&h[t.id]);
  const top8=ranked.slice(0,8).map(t=>t.id);
  el.innerHTML=`<div><h2>Power rankings</h2><p class="notes" style="margin:4px 0 12px">Team power = the five starters' average overall rating. Pick a team to see its real 2026 record against the other Worlds teams, counted in games (domestic, international and Worlds so far; data to ${typeof H2H_2026!=="undefined"?H2H_2026.asof:"—"}).</p></div>
  <div class="pwgrid"><div class="pwlist">${ranked.map((t,i)=>`<button class="pwrow${t.id===pwSel?" on":""}" data-pw="${t.id}"><span class="rkn">${i+1}</span>${regDot(t.id)}<span class="ttag" style="--tc:${teamCol(t.id)}">${esc(t.id)}</span><span class="nm">${esc(t.name)}</span>${bar(t.ov,t.name)}<span class="num">${t.ov.toFixed(1)}</span></button>`).join("")}</div>
  <div class="pwh2h"><div class="tiph"><span class="ttag" style="--tc:${teamCol(pwSel)}">${esc(pwSel)}</span><b>${esc(T.name)}</b></div><div class="notes">2026 games against other Worlds teams</div>
  <table class="tt full"><thead><tr><th>Opponent</th><th>Games</th><th>W-L</th><th>Met at</th></tr></thead><tbody>${rows.map(t=>{const [w,l,ev]=h[t.id];return `<tr><td>${teamTag(t.id)} ${esc(t.name)}</td><td class="num">${w+l}</td><td class="num"><b class="${w>l?"pos":w<l?"neg":""}">${w}-${l}</b></td><td class="notes small">${ev.map(esc).join(", ")}</td></tr>`}).join("")||`<tr><td colspan="4" class="notes">No 2026 games against other Worlds teams</td></tr>`}</tbody></table></div></div>
  <div style="margin-top:14px"><div class="label">Top eight · games won-lost, row against column</div><div style="overflow-x:auto"><table class="h2hm"><tr><th></th>${top8.map(t=>`<th>${esc(t)}</th>`).join("")}</tr>${top8.map(a=>`<tr><th>${esc(a)}</th>${top8.map(b=>{if(a===b)return'<td class="self"></td>';const x=(H[a]||{})[b];if(!x)return'<td class="none">–</td>';const [w,l]=x,sc=(w-l)/(w+l);return `<td style="--s:${Math.round(Math.abs(sc)*45)}%" class="${sc>0?"w":sc<0?"l":"e"}" title="${esc(`${a} ${w}-${l} ${b}`)}">${w}-${l}</td>`}).join("")}</tr>`).join("")}</table></div></div>`}
document.addEventListener("click",e=>{const b=e.target.closest("button[data-pw]");if(b){pwSel=b.dataset.pw;drawPower()}});
const MTIERS=[["S",55,"Must-ban / must-pick","var(--gold)"],["A",40,"Priority","var(--teal)"],["B",30,"Meta","var(--blue)"],["C",1,"Situational","var(--grey)"]];
const tierCol=T=>T==="C"?"var(--muted)":(MTIERS.find(x=>x[0]===T)||[0,0,0,"var(--muted)"])[3]; /* tier colour for text (as on the Meta page; C uses the lighter muted grey so it stays readable) */
const ALLP=TEAMS.flatMap(t=>t.p);
function comfort(c){return ALLP.filter(p=>p.picks.some(x=>x[0]===c));}
let metaRole="ALL",metaSub="tiers";
function synergyView(){
  const lift={};DUOS.forEach(([a,s,wr,l,g])=>lift[a+"|"+s]={wr,l,g});
  const adcs=[...new Set(DUOS.map(d=>d[0]))].sort(),sups=[...new Set(DUOS.map(d=>d[1]))].sort();
  const cell=(a,s)=>{const d=lift[a+"|"+s];if(!d)return `<td class="mx-na" title="Under 100 games">·</td>`;
    const c=d.l>=2?"mx-good":d.l<=-3?"mx-bad":"mx-mid";return `<td class="${c}" title="${esc(a)} + ${esc(s)}: ${d.wr}% win rate over ${d.g.toLocaleString()} games">${d.l>0?"+":""}${d.l.toFixed(1)}</td>`};
  const showBot=metaRole==="ALL"||metaRole==="ADC"||metaRole==="SUP";
  let h=`<div><h2>Synergies · patch 26.20</h2><p class="notes" style="margin:4px 0 0">Green = the pair wins more together than apart. Red = avoid. Numbers are win-rate lift in percentage points from 26.20 ranked games; pro samples are too small to measure pairs.</p></div>`;
  if(showBot)h+=`<div class="tier"><div class="eyebrow">Bot lane · ADC × support</div><div style="overflow-x:auto"><table class="mx"><thead><tr><th></th>${sups.map(s=>`<th>${esc(s)}</th>`).join("")}</tr></thead><tbody>${adcs.map(a=>`<tr><th>${esc(a)}</th>${sups.map(s=>cell(a,s)).join("")}</tr>`).join("")}</tbody></table></div><p class="notes" style="font-size:12px;margin:0">Source: <a href="https://metabot.gg/en/league/duos" target="_blank" rel="noopener">metabot.gg duos</a> (145,320 games, pairs with 100+ games). Hover a cell for win rate and games.</p></div>`;
  const parts=PARTNERS.filter(p=>metaRole==="ALL"||p[1]===metaRole||p[3][metaRole]);
  if(parts.length){
    const cols=ROLES.filter(r=>metaRole==="ALL"||r===metaRole||parts.some(p=>p[1]===metaRole));
    h+=`<div class="tier"><div class="eyebrow">Core meta picks · best partners by role</div><div style="overflow-x:auto"><table class="pt"><thead><tr><th>Pick</th>${cols.map(r=>`<th>${RNAME[r]}</th>`).join("")}</tr></thead><tbody>`+
    parts.map(([c,r,slug,by])=>`<tr><th><a href="https://www.metasrc.com/lol/champions/${slug}/synergies" target="_blank" rel="noopener">${esc(c)}</a><small>${RNAME[r]}</small></th>${cols.map(rr=>`<td>${rr===r?'<span class="notes">—</span>':(by[rr]||[]).map(([pc,ch])=>`<span class="chip ${metaOf(pc)[0]}">${esc(pc)} <em>+${ch}</em></span>`).join(" ")}</td>`).join("")}</tr>`).join("")+
    `</tbody></table></div><p class="notes" style="font-size:12px;margin:0">Source: METAsrc synergy pages, 26.20, all ranks (click a pick). Only partners seen in pro play or Swiss champion pools. Chip colour = Worlds meta status.</p></div>`;
  }
  const cl=Object.entries(CTR).filter(([c,d])=>metaRole==="ALL"||d.r===metaRole).sort((a,b)=>ROLES.indexOf(a[1].r)-ROLES.indexOf(b[1].r)||presOf(b[0])-presOf(a[0]));
  if(cl.length){const rel=l=>l.filter(([x])=>POOL.includes(x)).slice(0,4);
    h+=`<div class="tier"><div class="eyebrow">Counters · same-role matchups</div><div style="overflow-x:auto"><table class="pt"><thead><tr><th>Pick</th><th>Beats</th><th>Countered by</th></tr></thead><tbody>`+
    cl.map(([c,d])=>{const cs=countersOf(c);return `<tr><th><a href="https://www.metasrc.com/lol/champions/${d.slug.endsWith("#")?d.slug.slice(0,-1):d.slug+"/counters"}" target="_blank" rel="noopener" data-tc="${esc(c)}">${esc(c)}</a><small>${RNAME[d.r]}${d.patch?" · "+d.patch:""}</small></th><td>${rel(cs.beats).map(([x,w])=>`<span class="chip ${metaOf(x)[0]}" data-tc="${esc(x)}">${esc(x)} <em>${w}%</em></span>`).join(" ")||'<span class="notes">no pro-pool matchups</span>'}</td><td>${rel(cs.loses).map(([x,w])=>`<span class="chip ${metaOf(x)[0]}" data-tc="${esc(x)}">${esc(x)} <em>${w}%</em></span>`).join(" ")||'<span class="notes">no pro-pool matchups</span>'}</td></tr>`}).join("")+
    `</tbody></table></div><p class="notes" style="font-size:12px;margin:0">% = the pick's win rate in that matchup. Source: METAsrc counter pages (click a pick), ranked solo queue; patch shown where the page stated it. Only champions seen in pro play or Swiss champion pools are listed.</p></div>`;}
  h+=`<details class="tier"><summary class="eyebrow" style="cursor:pointer">Worlds play-in drafts on 26.20 · 14 games</summary><div style="display:grid;gap:6px;margin-top:8px">`+
    COMPS.map(([s,g,w,l,wn,ln])=>`<div style="border-top:1px solid var(--line);padding-top:6px;font-size:13px"><span class="notes" style="font-size:12px">${esc(s)} G${g}</span><div><b style="color:var(--meta)">${wn} won:</b> ${w.map(esc).join(", ")}</div><div class="notes" style="font-size:13px">${ln} lost: ${l.map(esc).join(", ")}</div></div>`).join("")+
    `<p class="notes" style="font-size:12px">Source: eGamersWorld match reports (links in Sources).</p></div></details>`;
  return h;
}
function metaView(){
  const subT=`<div class="tabs" style="position:static;border:0;padding:0" role="group" aria-label="Meta view">${[["tiers","Tier list"],["syn","Synergies & counters"]].map(([k,l])=>`<button data-ms="${k}" aria-selected="${k===metaSub}">${l}</button>`).join("")}</div>`;
  const filt0=`<div class="tabs" style="position:static;border:0;padding:0" role="group" aria-label="Filter by role">${[["ALL","All roles"],...ROLES.map(r=>[r,RNAME[r]])].map(([k,l])=>`<button data-mr="${k}" aria-selected="${k===metaRole}">${l}</button>`).join("")}</div>`;
  if(metaSub==="syn")return `<div class="panel" style="display:grid;gap:18px">${subT}${filt0}${synergyView()}</div>`;
  return metaTiers().replace('<div class="panel" style="display:grid;gap:16px">','<div class="panel" style="display:grid;gap:16px">'+subT);
}
let metaTrend="ALL";
function metaTiers(){
  const rows=Object.entries(CHAMP_DB).filter(([c,d])=>d.bl!=null).map(([c,d])=>({c,d,r:primaryRole(c),pres:Math.round(d.bl),W:wrOf(c),t:trendOf(c),who:comfort(c)}))
    .filter(x=>(metaRole==="ALL"||(ROLEMAP[x.c]&&ROLEMAP[x.c].has(metaRole)))&&(metaTrend==="ALL"||x.t===metaTrend)).sort((a,b)=>b.pres-a.pres);
  const seen=new Set(Object.keys(CHAMP_DB).filter(c=>CHAMP_DB[c].bl!=null));
  const watch={};ALLP.forEach(p=>p.picks.forEach(([c])=>{if(!seen.has(c)){(watch[c]=watch[c]||{c,r:p.role,who:[]}).who.push(p)}}));
  const wl=metaTrend!=="ALL"?[]:Object.values(watch).filter(w=>w.who.length>=2&&(metaRole==="ALL"||w.r===metaRole)).sort((a,b)=>b.who.length-a.who.length);
  const filt=`<div class="tabs" style="position:static;border:0;padding:0" role="group" aria-label="Filter by role">${[["ALL","All roles"],...ROLES.map(r=>[r,RNAME[r]])].map(([k,l])=>`<button data-mr="${k}" aria-selected="${k===metaRole}">${l}</button>`).join("")}</div>`;
  const tf=`<div class="seg" role="group" aria-label="Filter by trend">${[["ALL","All"],["rising","▲ Rising"],["falling","▼ Falling"],["fading","Fading"]].map(([k,l])=>`<button data-mt="${k}" aria-pressed="${k===metaTrend}">${l}</button>`).join("")}</div>`;
  const whoTxt=w=>w.length?`Top-3 pick for ${w.map(p=>`${esc(p.n)} (${p.team.id})`).join(", ")}`:"Not a top-3 pick for any Swiss player";
  const det=x=>{const t=x.d.rec||x.d.p20||x.d.sea,lab=x.d.rec?"26.16–20":x.d.p20?"26.20":"season";return t?`${t[0]}% picked · ${t[1]}% banned (${lab})`:""};
  let h=`<div class="panel" style="display:grid;gap:16px"><div><h2>Meta tier list · pro patches 26.16–26.20</h2><p class="notes" style="margin:4px 0 8px">Tiered by blended pick + ban presence: the Worlds patch 26.20 (25 pro games) weighted ×4 with patches 26.16–26.20 (465 games) for 90%, and the 2026 season (2,723 games) for 10% (NerfPlz). Win rate is from the freshest table that lists the champion; trend compares recent presence with the season. Champions only in the season table are marked fading.</p>${filt}<div style="margin-top:8px">${tf}</div></div>`;
  MTIERS.forEach(([T,min,label,col],k)=>{const max=k?MTIERS[k-1][1]:999;const rs=rows.filter(x=>x.pres>=min&&x.pres<max);if(!rs.length)return;
    h+=`<div class="tier"><div class="tierh"><span class="badge" style="background:${col}">${T}</span><span class="eyebrow" style="color:var(--muted)">${label} · ${T==="C"?"under 30%":min+"%+"} presence</span></div>`+
    rs.map(x=>`<div class="prole"><div class="mrowc"><span class="role">${x.r}</span>${icon(x.c,40)}<div><div class="pn"><span class="hov" data-tc="${esc(x.c)}" tabindex="0">${esc(x.c)}${x.t?` <span class="trend ${x.t}">${TREND_TXT[x.t]}</span>`:""}</span><small>${det(x)}</small></div><div class="bar" role="img" aria-label="${esc(x.c)} presence ${x.pres}%"><b style="width:${x.pres}%;background:${col}"></b></div></div><span class="num">${x.pres}%<small>${x.W?x.W.wr+"% WR":""}</small></span></div>`+
      `<div class="sub notes" style="font-size:12px">${whoTxt(x.who)}</div></div>`).join("")+`</div>`;});
  if(!rows.length)h+=`<p class="notes">No champions match this filter.</p>`;
  if(wl.length)h+=`<div class="tier"><div class="tierh"><span class="badge" style="background:var(--mix);font-size:15px">?</span><span class="eyebrow" style="color:var(--muted)">Watch list · comfort picks outside the recent pro tables</span></div>`+
    wl.map(w=>`<div class="prole"><div class="mrowc"><span class="role">${w.r}</span>${icon(w.c,40)}<div><div class="pn"><span class="hov" data-tc="${esc(w.c)}" tabindex="0">${esc(w.c)}</span><small>${w.who.length} Swiss players</small></div></div><span></span></div><div class="sub notes" style="font-size:12px">${whoTxt(w.who)}</div></div>`).join("")+`</div>`;
  return h+`</div>`;
}
document.getElementById("v-role").addEventListener("click",e=>{const b=e.target.closest("button[data-mr],button[data-ms],button[data-mt]");if(!b)return;if(b.dataset.mr)metaRole=b.dataset.mr;if(b.dataset.mt)metaTrend=b.dataset.mt;if(b.dataset.ms)metaSub=b.dataset.ms;document.getElementById("v-role").innerHTML=metaView();});
const parseL=s=>s.split(",").map(x=>{const m=x.trim().match(/^(.*) ([\d.]+)$/);return [m[1],+m[2]]});
const CTR={};Object.entries(CTR_RAW).forEach(([c,[r,patch,s,w,slug]])=>CTR[c]={r,patch,s:parseL(s),w:parseL(w),slug});
/* matchup(a,b): a's win rate vs b from either page; null if no data */
function matchup(a,b){const A=CTR[a],B=CTR[b];let x=A&&(A.s.find(y=>y[0]===b)||A.w.find(y=>y[0]===b));if(x)return x[1];let y=B&&(B.s.find(z=>z[0]===a)||B.w.find(z=>z[0]===a));if(y)return Math.round((100-y[1])*10)/10;
  const L=typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.lane[a+"|"+b];if(L&&L.g>=2)return Math.round((L.w+1)/(L.g+2)*1000)/10;return null}
function countersOf(c){/* who beats c, who c beats, merged both directions */
  const beats=new Map(),loses=new Map();const A=CTR[c];
  if(A){A.s.forEach(([x,w])=>beats.set(x,w));A.w.forEach(([x,w])=>loses.set(x,w))}
  const myR=A?[A.r]:[...(ROLEMAP[c]||[])];
  Object.entries(CTR).filter(([o,d])=>myR.includes(d.r)).forEach(([o,d])=>{d.s.forEach(([x,w])=>{if(x===c&&!loses.has(o)&&!beats.has(o))loses.set(o,Math.round((100-w)*10)/10)});d.w.forEach(([x,w])=>{if(x===c&&!beats.has(o)&&!loses.has(o))beats.set(o,Math.round((100-w)*10)/10)})});
  return {beats:[...beats].sort((a,b)=>b[1]-a[1]),loses:[...loses].sort((a,b)=>a[1]-b[1])};
}

/* ===== Champ select simulator ===== */
const ROLEMAP={};
const addRole=(c,r)=>{(ROLEMAP[c]=ROLEMAP[c]||new Set()).add(r)};
CH.forEach(([c,r])=>addRole(c,r));
TEAMS.forEach(t=>t.p.forEach(p=>p.picks.forEach(([c])=>addRole(c,p.role))));
DUOS.forEach(([a,s])=>{addRole(a,"ADC");addRole(s,"SUP")});
PARTNERS.forEach(([c,r,s,by])=>{addRole(c,r);Object.entries(by).forEach(([rr,l])=>l.forEach(([pc])=>addRole(pc,rr)))});
/* every champion played in 2026 pro play: roles with 3+ games and 10%+ of its games, else the usual pro role */
Object.entries(CHAMP_DB).forEach(([c,d])=>{if(!d.g&&d.bl==null)return;if(d.roles){const tot=Object.values(d.roles).reduce((a,b)=>a+b,0);Object.entries(d.roles).forEach(([r,n])=>{if(n>=3&&n/tot>=0.1)addRole(c,r)})}
  if(!ROLEMAP[c])(CHAMP_ROLE_FALLBACK[c]||[]).forEach(r=>addRole(c,r))});
function primaryRole(c){const d=CHAMP_DB[c];if(d&&d.roles){const e=Object.entries(d.roles).sort((a,b)=>b[1]-a[1]);if(e.length)return e[0][0]}const f=CHAMP_ROLE_FALLBACK[c];if(f)return f[0];const x=CH.find(y=>y[0]===c);if(x)return x[1];return ROLEMAP[c]?[...ROLEMAP[c]][0]:"MID"}
const POOL=Object.keys(ROLEMAP).sort();
const SYN={};
DUOS.forEach(([a,s,wr,l])=>{SYN[a+"|"+s]=SYN[s+"|"+a]=l});
PARTNERS.forEach(([c,r,s,by])=>Object.values(by).forEach(l=>l.forEach(([pc,ch])=>{SYN[c+"|"+pc]=SYN[pc+"|"+c]=Math.max(SYN[c+"|"+pc]||-99,ch)})));
const synOf=c=>Object.entries(SYN).filter(([k])=>k.startsWith(c+"|")).map(([k,l])=>[k.split("|")[1],l]).sort((a,b)=>b[1]-a[1]);
/* pre-tournament presence: blended pro presence; champions outside the pro tables get a small estimate from 2026 pro games */
const proPres=c=>{const d=CHAMP_DB[c];if(!d)return 0;if(d.bl!=null)return Math.round(d.bl);return Math.min(9,Math.round((d.g||0)/120))};
/* pre-tournament presence = pro presence blended with real Worlds presence (play-ins + Swiss so far), the Worlds share growing with games */
const basePres=c=>{const W=worldsMeta(c),k=W.g/(W.g+60);return Math.round((1-k)*proPres(c)+k*(W.pk+W.bn))};
const presOf=c=>{const b=basePres(c);return typeof tourPres==="function"?tourPres(c,b):b};
/* a player's champion pool: 2026 favourites plus champions played at this simulated Worlds */
/* a player's champion pool: 2026 favourites, plus real Worlds games (counted double for recency; new champions added), plus your run */
function worldsPool(p){const pc=typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.pchamp[p.n];if(!pc)return p.picks;const out=p.picks.map(x=>[...x]);
  Object.entries(pc).forEach(([c,v])=>{const e=out.find(x=>x[0]===c);if(e){const g0=e[1]||5,w0=(e[2]||50)/100*g0;e[1]=g0+v.g;e[2]=Math.round((w0+2*v.w)/(g0+2*v.g)*100)}else out.push([c,v.g,Math.round(v.w/v.g*100),"new"])});return out}
function poolOf(p){const base=worldsPool(p);return typeof tourPool==="function"?tourPool(p,base):base}
const tierOf=p=>p>=55?"S":p>=40?"A":p>=30?"B":p>0?"C":"–";
/* Competitive order. F = first-pick side (blue as standard), L = the other side. */
const SEQ=[["F","ban"],["L","ban"],["F","ban"],["L","ban"],["F","ban"],["L","ban"],
 ["F","pick"],["L","pick"],["L","pick"],["F","pick"],["F","pick"],["L","pick"],
 ["L","ban"],["F","ban"],["L","ban"],["F","ban"],
 ["L","pick"],["F","pick"],["F","pick"],["L","pick"]];
const DS={me:"LYON",opp:"LOS",side:"blue",fp:"blue",fmt:"bo1",game:1,locked:[],steps:[],roleF:"ALL",q:"",ai:true,showUsed:false,fresh:-1,sim:null,series:null,sbo:"3",sfear:"yes"};
const team=id=>TEAMS.find(t=>t.id===id);
const sideOf=id=>id===DS.me?DS.side:(DS.side==="blue"?"red":"blue");
const idOnSide=sd=>sideOf(DS.me)===sd?DS.me:DS.opp;
const actorId=k=>{const F=idOnSide(DS.fp);return k==="F"?F:(F===DS.me?DS.opp:DS.me)};
const otherId=id=>id===DS.me?DS.opp:DS.me;
const taken=()=>new Set([...DS.steps.map(s=>s.c),...(DS.fmt==="fearless"?DS.locked:[])]);
const picksOf=id=>DS.steps.map((s,i)=>({...s,i})).filter(s=>s.k==="pick"&&s.t===id);
const bansOf=id=>DS.steps.map((s,i)=>({...s,i})).filter(s=>s.k==="ban"&&s.t===id);
function openRoles(id){const used=new Set(picksOf(id).map(p=>p.r));return ROLES.filter(r=>!used.has(r))}
function comfortIn(id,c){return team(id).p.filter(p=>poolOf(p).some(x=>x[0]===c)).map(p=>({p,x:poolOf(p).find(x=>x[0]===c)}))}
function scoreFor(c,actor,kind){
  const other=otherId(actor),pres=presOf(c),why=[];let s=pres*0.5;
  if(pres)why.push(`${tierOf(pres)}-tier meta (${pres}%)`);
  if(kind==="ban"){
    comfortIn(other,c).forEach(({p,x})=>{s+=25+Math.min(x[1]||10,20);why.push(`${p.n}'s comfort (${x[1]?x[1]+"g, ":""}${x[2]}%)`)});
    if(comfortIn(actor,c).length){s-=15;why.push(`your ${comfortIn(actor,c).map(o=>o.p.n).join(", ")} plays it`)}
    picksOf(actor).forEach(p=>{const m=matchup(c,p.c);if(m!=null&&m>=52&&[...(ROLEMAP[c]||[])].includes(p.r)){s+=(m-50)*3;why.push(`counters your ${p.c} (${m}%)`)}});
    const W=wrOf(c);if(W&&W.adj>52)s+=(W.adj-50)*0.8;
    if(DS.steps.length>=12){const need=[...(ROLEMAP[c]||[])].filter(r=>openRoles(other).includes(r));if(!need.length)s*=0.3;else why.push(`they still need ${need.join("/")}`)}
    if(CHAMP_DB[c]&&CHAMP_DB[c].so)s*=0.5;
    return {c,s,why};
  }
  const open=openRoles(actor),roles=[...(ROLEMAP[c]||[])].filter(r=>open.includes(r));
  if(!roles.length)return null;
  const fade=!!(CHAMP_DB[c]&&CHAMP_DB[c].fade);
  comfortIn(actor,c).filter(o=>roles.includes(o.p.role)).forEach(({p,x})=>{s+=(30+Math.min(x[1]||10,20)+((x[2]||50)-50)/2)*(fade?0.6:1);why.push(`${p.n}'s comfort (${x[1]?x[1]+"g, ":""}${x[2]}%)${fade?" — fading in pro":""}`)});
  const W=wrOf(c);if(W){s+=(W.adj-50)*1.2;if(Math.abs(W.adj-50)>=2)why.push(`${W.wr}% WR (${W.src})`)}
  if(DS.steps.length<12&&roles.length>=2){s+=5;why.push(`flex ${roles.join("/")}`)}
  const tr=trendOf(c);if(tr==="rising"){s+=3;why.push("▲ rising")}else if(tr==="falling")why.push("▼ falling");
  if(CHAMP_DB[c]&&CHAMP_DB[c].so)s*=0.5;
  picksOf(actor).forEach(p=>{const l=SYN[c+"|"+p.c];if(l!=null){s+=l*4;why.push(`${l>0?"+":""}${l} with ${p.c}`)}
    const m=typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.mates[[c,p.c].sort().join("|")];if(m&&m.g>=2){const net=m.w-(m.g-m.w);if(net){s+=Math.max(-3,Math.min(3,net))*2;why.push(`${m.w}-${m.g-m.w} with ${p.c} at Worlds`)}}});
  const deny=comfortIn(other,c);if(deny.length){s+=8;why.push(`denies ${deny.map(o=>o.p.n).join(", ")}`)}
  picksOf(other).filter(p=>roles.includes(p.r)).forEach(p=>{const m=matchup(c,p.c);if(m!=null){s+=(m-50)*3;why.push(m>=50?`beats ${p.c} (${m}%)`:`countered by ${p.c} (${m}%)`)}});
  return {c,s,why,roles};
}
/* one suggestion reason as HTML: meta tier in its tier colour (as on the Meta page), player names in gold */
function fmtWhy(w){let m;
  if((m=w.match(/^([SABC])-tier meta(.*)$/)))return `<b style="color:${tierCol(m[1])}">${m[1]}-tier meta</b>${esc(m[2])}`;
  if((m=w.match(/^(.+?)'s comfort(.*)$/)))return `<b class="wp">${esc(m[1])}</b>'s comfort${esc(m[2])}`;
  if((m=w.match(/^(your|denies) (.+?)( plays it)?$/)))return `${m[1]} <b class="wp">${esc(m[2])}</b>${m[3]||""}`;
  return esc(w)}
function recs(){
  const i=DS.steps.length;if(i>=20)return[];
  const [k,kind]=SEQ[i],actor=actorId(k),tk=taken();
  return POOL.filter(c=>!tk.has(c)).map(c=>scoreFor(c,actor,kind)).filter(x=>x&&x.s>0).sort((a,b)=>b.s-a.s).slice(0,8);
}
function stepLabel(i){const [k,kind]=SEQ[i];const sd=actorId(k)===DS.me?DS.side:sideOf(DS.opp);
  const n=SEQ.slice(0,i+1).filter(x=>x[0]===k&&x[1]===kind).length;return `${sd==="blue"?"B":"R"}${kind==="ban"?" ban ":" pick "}${n}`}
function stepTip(){
  const i=DS.steps.length;if(i>=20)return"";
  const [k,kind]=SEQ[i],actor=actorId(k),mine=actor===DS.me;
  if(i===6)return "First pick: worth most when one champion clearly stands above the rest.";
  if(i===19)return "Last pick: answer the lineup you can see — counter-pick scores are included below.";
  if(kind==="ban"&&i<6)return "Phase 1 bans: remove S-tier picks and the other side's biggest comfort champions.";
  if(kind==="ban")return "Phase 2 bans: target the roles the other side still has to fill.";
  return mine?"Pick for an open role. Comfort and synergy with your earlier picks raise the score.":"Opponent pick.";
}
function doPick(c){
  const i=DS.steps.length;if(i>=20||taken().has(c))return;
  const [k,kind]=SEQ[i],actor=actorId(k);const st={t:actor,k:kind,c};
  if(kind==="pick"){const open=openRoles(actor);const rs=[...(ROLEMAP[c]||[])];st.r=rs.find(r=>open.includes(r))||open[0]}
  DS.steps.push(st);DS.fresh=i;DS.sim=null;renderDraft();queueAI();
}
let aiTimer=null;
function queueAI(){clearTimeout(aiTimer);const i=DS.steps.length;if(!DS.ai||i>=20||(!DS.tour&&!DS.series)||DS.sim)return;if(actorId(SEQ[i][0])===DS.me)return;
  aiTimer=setTimeout(()=>{const r=recs();if(!r.length)return;const w=[0.6,0.25,0.15],x=Math.random();let j=x<w[0]?0:x<w[0]+w[1]?1:2;j=Math.min(j,r.length-1);doPick(r[j].c)},2000)}

/* ---- tooltips and hover cards ---- */
const tip=document.createElement("div");tip.id="tip";tip.setAttribute("role","tooltip");tip.hidden=true;document.body.appendChild(tip);
function takenWhy(c){const st=DS.steps.find(x=>x.c===c);if(st)return `${st.k==="ban"?"banned":"picked"} by ${st.t}`;if(DS.fmt==="fearless"&&DS.locked.includes(c))return "locked (Fearless)";return ""}
const takenSd=c=>{const st=DS.steps.find(x=>x.c===c);return st?sideOf(st.t):""};
const inDraft=id=>id===DS.me||id===DS.opp;
/* player card: pool with availability, best pick still open, and lane counter risk against the enemy laner already locked */
/* skill icons: offence in yellow-orange, utility in blue-green; hover shows the skill name */
/* Skill icons (style A): one outline icon per skill name, 24px grid. Orange = attacking, teal = utility. */
const SWORD='<path d="M20 4v4L10 18l-4-4L16 4z"/><path d="M5 13l6 6"/><path d="M7.5 16.5 4 20"/>';
const SKILL_SVG={
  laning:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M6.5 17.5 17.5 6.5"/><circle cx="12" cy="12" r="2"/>',
  teamfight:SWORD+'<g transform="matrix(-1 0 0 1 24 0)">'+SWORD+'</g>',
  consistency:'<path d="M12 3l8 3v6c0 4.5-3.5 7.5-8 9-4.5-1.5-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
  early:'<circle cx="12" cy="13" r="7"/><path d="M12 13V9.5"/><path d="M10 3h4"/><path d="M12 3v3"/><path d="M18.5 6.5 20 5"/>',
  objectives:'<circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3.5M12 18.5V22M2 12h3.5M18.5 12H22"/>',
  roaming:'<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h6a3 3 0 0 0 0-6h-4a3 3 0 0 1 0-6h6"/>',
  damage:'<path d="M12 2l2 6 5.5-3-3 5.5 6 2-6 2 3 5.5-5.5-3-2 6-2-6-5.5 3 3-5.5-6-2 6-2-3-5.5L10 8z"/>',
  positioning:'<path d="M12 3v18M3 12h18"/><path d="M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3"/>',
  playmaking:'<path d="M13 2L4 14h7l-1 8 10-13h-7z"/>',
  presence:'<path d="M2 12c3-5.5 6.5-7.5 10-7.5s7 2 10 7.5c-3 5.5-6.5 7.5-10 7.5S5 17.5 2 12z"/><circle cx="12" cy="12" r="3"/>',
  reliability:'<circle cx="12" cy="5" r="2"/><path d="M12 7v14"/><path d="M8 11h8"/><path d="M5 14c0 4 3 7 7 7s7-3 7-7"/><path d="M3 15.5l2-2 2 2M17 15.5l2-2 2 2"/>'};
const SKILL_ICON={TOP:[["laning","o"],["teamfight","o"],["consistency","u"]],JGL:[["early","o"],["objectives","u"],["teamfight","o"]],MID:[["laning","o"],["roaming","u"],["damage","o"]],ADC:[["laning","o"],["damage","o"],["positioning","u"]],SUP:[["playmaking","o"],["presence","u"],["reliability","u"]]};
function skillChip(role,j,val,mood){const [ic,kind]=SKILL_ICON[role][j];return `<span class="sk ${kind}${mood?" "+mood:""}" title="${esc(ATTR[role][j])}"><svg viewBox="0 0 24 24" aria-hidden="true">${SKILL_SVG[ic]}</svg>${val}</span>`}
function wformBox(p){const f=typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.form[p.n];if(!f)return"";const sg=v=>v>0?"+"+v:v<0?String(v):"±0";
    const st=[["KDA",f.kda],["KP",f.kp+"%"],["DMG",f.dmg+"%"],...(f.csm?[["CS/min",f.csm]]:[])];
    return `<div class="wform"><div class="wf-l"><b class="hl">Worlds form · ${f.g} game${f.g>1?"s":""} (${f.w}-${f.g-f.w})</b><span class="pskills" title="Change to skill ratings from Worlds games">${ATTR[p.role].map((a,j)=>skillChip(p.role,j,sg(f.d[j]),f.d[j]>0?"up":f.d[j]<0?"down":"")).join("")}</span>${f.tags.length?`<span class="wf-tags">${f.tags.map(t=>`<span class="tag">${t}</span>`).join("")}</span>`:""}</div><div class="wf-stats">${st.map(([l,v])=>`<span><small>${l}</small><b>${v}</b></span>`).join("")}</div></div>`}
function playerTip(tid,idx){const t=team(tid),p=t.p[idx],live=inDraft(tid)&&DS.steps.length>0;
  const enemy=inDraft(tid)?picksOf(otherId(tid)).find(x=>x.r===p.role):null;
  const pool=poolOf(p).slice().sort((a,b)=>(b[1]||0)-(a[1]||0));
  /* display: this Worlds' games first (bright), 2026 pro numbers dimmed in brackets */
  const RX=runCtx(),tp=(RX&&RX.stats.pchamp[p.key])||{},hasRun=!!RX;
  const wp=(typeof WORLDS_LIVE!=="undefined"&&WORLDS_LIVE.pchamp[p.n])||{};
  const shown=[...new Set([...Object.keys(wp).sort((a,b)=>wp[b].g-wp[a].g),...Object.keys(tp).sort((a,b)=>tp[b].g-tp[a].g),...p.picks.map(x=>x[0])])];
  const row=c=>{const sx=p.picks.find(y=>y[0]===c),tv=tp[c],wv=wp[c];const st=takenWhy(c),m=enemy&&!st?matchup(c,enemy.c):null,fd=CHAMP_DB[c]&&CHAMP_DB[c].fade;
    const risk=m!=null?(m<48?`<span class="neg">countered by ${esc(enemy.c)} (${m}%)</span>`:m>=52?`<span class="pos">beats ${esc(enemy.c)} (${m}%)</span>`:""):"";
    const isNew=wv&&!sx;
    return `<tr class="${st?"gone":""}"><td><span class="pchamp${isNew?" isnew":""}"${isNew?` title="New at Worlds — not in their 2026 top picks"`:""}>${icon(c,22)}</span> ${esc(c)}${st?` <span class="notes${takenSd(c)?" ig "+takenSd(c):""}">${st}</span>`:""}${fd&&!st?` <span class="trend fading">fading</span>`:""}${risk?" "+risk:""}</td><td>${wv?`<em class="g">${wv.g} gm</em> <span class="wl">${wv.w}-${wv.g-wv.w}</span>`:"–"}</td>${hasRun?`<td class="notes small">${tv?`${tv.g} gm ${tv.w}-${tv.g-tv.w}`:"–"}</td>`:""}<td class="dim nw">${sx?`(${sx[1]?sx[1]+"g ":""}${sx[2]}%)`:"–"}</td><td><span class="chip ${metaOf(c)[0]}">${metaOf(c)[0]==="meta"?"Meta":metaOf(c)[0]==="mix"?"In the mix":"Unseen"}</span></td></tr>`};
  const open=pool.filter(([c])=>!takenWhy(c));
  const best=open.slice().sort((a,b)=>{const ma=enemy?matchup(a[0],enemy.c):null,mb=enemy?matchup(b[0],enemy.c):null;return ((mb==null?50:mb)-(ma==null?50:ma))*2+((b[1]||0)-(a[1]||0))*0.3})[0];
  const rk=TEAMS.map(x=>x.p[idx]).sort((a,b)=>b.ov-a.ov||avg(b.a)-avg(a.a)).indexOf(p)+1;
  return `<div class="tiph ph" style="--tc:${teamCol(tid)}">${regDot(tid)}<span class="tm">${esc(tid)}</span><b>${esc(p.n)}</b><span class="ov" title="Overall rating" style="--oc:${tier(p.ov)}"><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span><span class="n">${p.ov}</span></span></div>
  <div class="pskills"><span class="prank"><b>${rk}/16</b> ${RNAME[p.role]}</span>${ATTR[p.role].map((a,j)=>skillChip(p.role,j,p.a[j])).join("")}${p.kda?`<span class="sk" title="2026 KDA"><small>KDA</small>${p.kda}</span>`:""}</div>`+
  (live?`<div class="here">${best?`Best still open: <b>${esc(best[0])}</b>`:"<b>Every comfort pick is gone</b> — off-pool pick"}${enemy?` · facing ${esc(enemy.c)}`:""}</div>`:"")+
  wformBox(p)+
  (shown.length?`<div class="pkey"><span class="pchamp isnew"><i></i></span> New at Worlds (not in their 2026 top picks)</div><table class="tt ptab"><thead><tr><th>Champion</th><th>Worlds</th>${hasRun?"<th>Your run</th>":""}<th>2026</th><th>Meta</th></tr></thead>${shown.map(row).join("")}</table>`:`<div class="notes">No 2026 champion data</div>`)+
  (typeof tourPlayerLine==="function"?tourPlayerLine(p):"")+(p.note?`<div class="notes">${esc(p.note)}</div>`:"");}
/* role pages: the player card already shows the summary, so the hover shows the real Worlds games behind it, plus ban risk */
const MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function playerLogTip(tid,idx){const t=team(tid),p=t.p[idx],L=typeof WORLDS_LIVE!=="undefined"?WORLDS_LIVE:null,rows=[];
  if(L)L.games.forEach(g=>["blue","red"].forEach(sd=>{const me=g.pl[sd].find(r=>r[1]===p.n);if(!me)return;const os=sd==="blue"?"red":"blue";rows.push({g,me,op:g.pl[os].find(r=>r[0]===me[0]),opp:g[os],won:g.w===g[sd]})}));
  const pin=L&&L.pin&&L.pin[p.n]?Object.values(L.pin[p.n]).reduce((a,[n,w])=>[a[0]+n,a[1]+w],[0,0]):null;
  const risk=poolOf(p).map(x=>[x[0],worldsMeta(x[0])]).filter(([c,W])=>W.bn>0).sort((a,b)=>b[1].bn-a[1].bn).slice(0,4);
  const day=d=>`${+d.slice(8)} ${MON[+d.slice(5,7)-1]}`,w=rows.filter(x=>x.won).length;
  return `<div class="tiph ph" style="--tc:${teamCol(tid)}">${regDot(tid)}<span class="tm">${esc(tid)}</span><b>${esc(p.n)}</b><span class="notes">${RNAME[p.role]}</span></div>
  <div class="label"><span class="hl">Worlds game log · ${rows.length} game${rows.length===1?"":"s"}${rows.length?` (${w}-${rows.length-w})`:""}</span></div>`+
  (rows.length?`<table class="tt full glog"><thead><tr><th>Game</th><th>Champion · lane opponent</th><th>K/D/A</th><th>CS@15</th><th></th></tr></thead><tbody>${rows.map(({g,me,op,opp,won})=>`<tr><td><span class="nw">${day(g.d)}</span> <span class="ttag" style="--tc:${teamCol(opp)}">${esc(opp)}</span></td><td><span class="gch">${icon(me[2],20)}<b>${esc(me[2])}</b>${op?`<span class="notes small">v ${esc(op[2])}</span>`:""}</span></td><td class="num">${me[3]}/${me[4]}/${me[5]}</td><td class="num">${me[7]==null?"–":(me[7]>0?"+":"")+me[7]}</td><td><b class="${won?"pos":"neg"}">${won?"W":"L"}</b></td></tr>`).join("")}</tbody></table>`:`<div class="notes">No Swiss games yet.</div>`)+
  (pin&&pin[0]?`<div class="notes small">Plus ${pin[0]} play-in game${pin[0]>1?"s":""} (${pin[1]}-${pin[0]-pin[1]}), counted in their champion pool.</div>`:"")+
  `<div class="here"><b>Ban risk:</b> ${risk.length?risk.map(([c,W])=>`${esc(c)} <b>${W.bn}%</b>`).join(" · "):"none of their champions banned at Worlds yet"}</div>
  <div class="notes small">Ban risk = how often each of their champions (2026 favourites plus Worlds picks) is banned in real Worlds games with published bans. CS@15 only where a source published it.</div>`}
/* team card: comp so far, damage mix, plan, synergy pairs and open roles */
const ARCH_NAME={engage:"Engage",poke:"Poke and siege",scaling:"Scaling",skirmish:"Skirmish and dive",protect:"Protect the carry"};
function compOf(cs){const ap=cs.filter(c=>CHAMP_AP.has(c)).length,cnt={};cs.forEach(c=>Object.entries(CHAMP_ARCH).forEach(([k,l])=>{if(l.includes(c))cnt[k]=(cnt[k]||0)+1}));
  return {ap,ad:cs.length-ap,arch:Object.entries(cnt).sort((a,b)=>b[1]-a[1])}}
function teamTip(id){const t=team(id),ps=picksOf(id),open=openRoles(id),C=compOf(ps.map(p=>p.c));const pairs=[];
  for(let a=0;a<ps.length;a++)for(let b=a+1;b<ps.length;b++){const l=SYN[ps[a].c+"|"+ps[b].c];if(l!=null)pairs.push([ps[a].c,ps[b].c,l])}
  const comf=ps.filter(p=>poolOf(t.p[ROLES.indexOf(p.r)]).some(x=>x[0]===p.c)).length;
  return `<div class="tiph" style="--tc:${teamCol(id)}"><span class="tm">${esc(id)}</span><b>${esc(t.name)}</b><span class="notes">${sideOf(id)} side · ${ps.length}/5 picked</span></div>`+
  (ps.length?`<div class="icons">${ROLES.map(r=>{const p=ps.find(x=>x.r===r);return p?icon(p.c,30):`<span class="ico empty" style="--s:30px"><b>${r}</b></span>`}).join("")}</div>`+
   `<div><span class="notes">Damage:</span> ${C.ap} magic · ${C.ad} physical${ps.length>=3&&(!C.ap||!C.ad)?` <span class="neg">— one damage type, easy to itemise against</span>`:""}</div>`+
   `<div><span class="notes">Plan:</span> ${C.arch.length?C.arch.slice(0,2).map(([k,n])=>`${ARCH_NAME[k]} ×${n}`).join(", "):"no clear identity yet"}</div>`+
   `<div><span class="notes">Synergy:</span> ${pairs.length?pairs.map(([a,b,l])=>`${esc(a)} + ${esc(b)} <em class="${l>0?"pos":"neg"}">${l>0?"+":""}${l}</em>`).join(", "):"no measured pairs yet"}</div>`+
   `<div><span class="notes">Comfort picks:</span> ${comf}/${ps.length}</div>`:`<div class="notes">No picks yet.</div>`)+
  `<div><span class="notes">Open roles:</span> ${open.length?open.map(r=>RNAME[r]).join(", "):"none — lineup locked"}</div>`}
/* champion card (Arena HUD): pick/ban, Worlds patch, recent patches, win rate, Worlds W/L, then who played it here, partners and counters */
const hb=(label,inner,val,sub)=>`<div class="hb"><span>${label}</span><i>${inner}</i><span class="v">${val}<small>${sub}</small></span></div>`;
const fill=(w,cls)=>`<b${cls?` class="${cls}"`:""} style="width:${Math.max(0,Math.min(100,w))}%"></b>`;
const infoI=t=>`<span class="info" tabindex="0" aria-label="${esc(t)}">!<span class="tipx">${esc(t)}</span></span>`;
function worldsWL(c){const d=CHAMP_DB[c];let w=d&&d.pin?d.pin[0]:0,l=d&&d.pin?d.pin[1]:0;const RX=runCtx(),st=RX&&RX.stats.champ[c];if(st){w+=st.w;l+=st.p-st.w}return [w,l]}
/* Worlds meta: 22 play-in games (NerfPlz top list for bans, play-in W-L for picks) plus every game of your run */
function worldsMeta(c){const d=CHAMP_DB[c]||{},ch=CH.find(y=>y[0]===c),PG=22;let g=PG,p=0,b=0,w=0;
  if(d.pin&&(d.pin[0]+d.pin[1])){p=d.pin[0]+d.pin[1];w=d.pin[0]}else if(ch&&ch[2]!=null)p=Math.round(ch[2]/100*PG);
  if(ch&&ch[3]!=null)b=Math.round(ch[3]/100*PG);
  const L=typeof WORLDS_LIVE!=="undefined"?WORLDS_LIVE:null,sw=L?L.n:0;let gb=PG+(L?(L.nb!=null?L.nb:sw):0);if(L){g+=sw;const x=L.champ[c];if(x){p+=x.p;b+=x.b;w+=x.w}}
  const RX=runCtx(),R=RX&&RX.stats,rs=R&&R.champ[c];
  /* ban rate only over games whose bans are published */
  return {g,gb,p,b,w,l:p-w,pk:Math.round(p/g*100),bn:Math.round(b/gb*100),swiss:sw,run:R?R.games:0,runP:rs?rs.p:0,runB:rs?rs.b:0,runW:rs?rs.w:0}}
/* champions seen on the same team at this Worlds (play-in drafts + your run): [name, wins together, games together] */
function worldsMates(c){const m=new Map();const add=(x,won)=>{const e=m.get(x)||[x,0,0];e[2]++;if(won)e[1]++;m.set(x,e)};
  COMPS.forEach(([s,g,wc,lc])=>{if(wc.includes(c))wc.forEach(x=>x!==c&&add(x,true));if(lc.includes(c))lc.forEach(x=>x!==c&&add(x,false))});
  if(typeof WORLDS_LIVE!=="undefined")WORLDS_LIVE.games.forEach(gm=>["blue","red"].forEach(sd=>{const cs=gm.pl[sd].map(r=>r[2]);if(cs.includes(c)){const won=gm.w===gm[sd];cs.forEach(x=>x!==c&&add(x,won))}}));
  if(runCtx())runCtx().matches.forEach(mt=>mt.games.forEach(gm=>["blue","red"].forEach(s=>{const cs=ROLES.map(r=>gm.ps[s][r].c);if(cs.includes(c)){const won=gm.winner===(s==="blue"?gm.blue:gm.red);cs.forEach(x=>x!==c&&add(x,won))}})));
  return [...m.values()].filter(e=>e[1]>0).sort((a,b)=>b[1]-a[1]||(b[1]/b[2])-(a[1]/a[2]))}
/* five partners: measured pair lift first, then winning team-mates at this Worlds */
function pairs5(c){const out=synOf(c).filter(x=>x[1]>0).map(([x,l])=>({x,em:"+"+l,cls:"g"}));const seen=new Set(out.map(o=>o.x));
  worldsMates(c).forEach(([x,w,g])=>{if(!seen.has(x)){seen.add(x);out.push({x,em:`${w}-${g-w}`,cls:"g",note:`${w}-${g-w} together at Worlds`})}});return out.slice(0,6)}
/* five counters: same-lane matchups, then matchups from other lanes, then lane opponents that beat it at this Worlds */
function counters5(c){const out=countersOf(c).loses.filter(([x])=>POOL.includes(x)).map(([x,w])=>({x,em:Math.round(w)+"%",note:w+"% win rate in the matchup",cls:"b"}));const seen=new Set(out.map(o=>o.x));seen.add(c);
  const more=[];Object.entries(CTR).forEach(([o,d])=>{d.s.forEach(([x,w])=>{if(x===c&&!seen.has(o))more.push([o,Math.round((100-w)*10)/10])})});if(CTR[c])CTR[c].w.forEach(([x,w])=>{if(!seen.has(x))more.push([x,w])});
  more.sort((a,b)=>a[1]-b[1]).forEach(([x,w])=>{if(!seen.has(x)&&POOL.includes(x)){seen.add(x);out.push({x,em:Math.round(w)+"%",note:w+"% win rate in the matchup",cls:"b",other:1})}});
  if(out.length<6&&typeof WORLDS_LIVE!=="undefined")Object.entries(WORLDS_LIVE.lane).filter(([k,v])=>k.endsWith("|"+c)&&v.w>v.g-v.w).sort((a,b)=>b[1].w-a[1].w).forEach(([k,v])=>{const x=k.split("|")[0];if(!seen.has(x)){seen.add(x);out.push({x,em:`${v.w}-${v.g-v.w}`,cls:"b",note:`won the lane ${v.w}-${v.g-v.w} at Worlds`})}});
  if(out.length<6&&runCtx()){const m=new Map();runCtx().matches.forEach(mt=>mt.games.forEach(gm=>["blue","red"].forEach(s=>ROLES.forEach(r=>{if(gm.ps[s][r].c!==c)return;const o=s==="blue"?"red":"blue",x=gm.ps[o][r].c,lost=gm.winner!==(s==="blue"?gm.blue:gm.red);const e=m.get(x)||[x,0,0];e[2]++;if(lost)e[1]++;m.set(x,e)}))));
    [...m.values()].filter(e=>e[1]>e[2]-e[1]).sort((a,b)=>b[1]-a[1]).forEach(([x,w,g])=>{if(!seen.has(x)){seen.add(x);out.push({x,em:`${w}-${g-w}`,cls:"b",note:`beat it ${w}-${g-w} in your run`})}})}
  return out.slice(0,6)}
/* three champions it counters: same-lane matchups it wins, then wins from other lanes, then lane opponents it beat at this Worlds */
const BEATS_INFO="Champions it beats, with its matchup win rate (METAsrc). Same lane first; gaps filled by its lane wins at Worlds. Pro-played champions only.";
function beats3(c){const out=countersOf(c).beats.filter(([x,w])=>w>=50.5&&POOL.includes(x)).map(([x,w])=>({x,em:Math.round(w)+"%",note:w+"% win rate in the matchup",cls:"g"}));const seen=new Set(out.map(o=>o.x));seen.add(c);
  const more=[];Object.entries(CTR).forEach(([o,d])=>{d.w.forEach(([x,w])=>{if(x===c&&!seen.has(o))more.push([o,Math.round((100-w)*10)/10])})});if(CTR[c])CTR[c].s.forEach(([x,w])=>{if(!seen.has(x))more.push([x,w])});
  more.sort((a,b)=>b[1]-a[1]).forEach(([x,w])=>{if(w>=50.5&&!seen.has(x)&&POOL.includes(x)){seen.add(x);out.push({x,em:Math.round(w)+"%",note:w+"% win rate in the matchup",cls:"g",other:1})}});
  if(out.length<3&&typeof WORLDS_LIVE!=="undefined")Object.entries(WORLDS_LIVE.lane).filter(([k,v])=>k.startsWith(c+"|")&&v.w>v.g-v.w).sort((a,b)=>b[1].w-a[1].w).forEach(([k,v])=>{const x=k.split("|")[1];if(!seen.has(x)){seen.add(x);out.push({x,em:`${v.w}-${v.g-v.w}`,cls:"g",note:`won the lane ${v.w}-${v.g-v.w} at Worlds`})}});
  return out.slice(0,3)}
function mostPicked(c,n=3){const m=new Map(),d=CHAMP_DB[c];
    if(typeof WORLDS_LIVE!=="undefined")Object.entries(WORLDS_LIVE.pchamp).forEach(([n,pc])=>{const v=pc[c];if(!v)return;const P=WORLDS_LIVE.players[n],t=P?P.team:(WORLDS_LIVE.pinTeam||{})[n]||"",e=m.get(n)||{n,t,g:0,w:0};e.g+=v.g;e.w+=v.w;if(t)e.t=t;m.set(n,e)});
  const sea=n=>{const p=ALLP.find(x=>x.n===n),x=p&&p.picks.find(y=>y[0]===c);return x&&x[1]?x[1]:null};
  return [...m.values()].sort((a,b)=>b.g-a.g||b.w-a.w).slice(0,n).map(e=>({...e,s:sea(e.n)}))}
/* your simulated run's players on this champion (shown separately from the real Worlds numbers) */
function mostPickedRun(c){const RX=runCtx();if(!RX)return[];return Object.entries(RX.stats.pchamp).map(([key,pc])=>{const v=pc[c];if(!v)return null;const [tid,i]=key.split("|");return {n:team(tid).p[+i].n,t:tid,g:v.g,w:v.w}}).filter(Boolean).sort((a,b)=>b.g-a.g).slice(0,3)}
/* pick/ban highlights use the side colour (blue / red), never the team's badge colour, so a blue-badged opponent can't look like your pick */
const sideCol=sd=>sd==="blue"?"var(--bside)":sd==="red"?"var(--rside)":"var(--muted)";
/* a champion's status in the draft on screen: picked / banned this game, or locked by Fearless (with game and team) */
function draftStatus(c){const dv=document.getElementById("v-draft");if(!dv||dv.hidden)return null;
  const st=DS.steps.find(x=>x.c===c);if(st){const sd=sideOf(st.t);return st.k==="ban"?{k:"ban",t:st.t,sd,tag:"Ban",title:`Banned by ${st.t} (${sd} side) this game`}:{k:"pick",t:st.t,sd,tag:st.t,title:`Picked by ${st.t} (${sd} side) this game`}}
  if(DS.fmt==="fearless"&&DS.locked.includes(c)){const gs=DS.series?DS.series.games:DS.tour&&typeof M==="function"&&M(DS.tour.mid)?M(DS.tour.mid).games:[];
    for(let i=0;i<gs.length;i++){const x=gs[i].steps.find(y=>y[1]==="pick"&&y[2]===c);if(x)return {k:"lock",t:x[0],tag:`Locked · G${i+1}`,title:`Locked by Fearless — ${x[0]} picked it in game ${i+1}`}}
    return {k:"lock",t:"",tag:"Locked",title:"Locked by Fearless"}}
  return null}
function champTip(c){const d=CHAMP_DB[c]||{},pr=presOf(c),tr=trendOf(c),W=wrOf(c),rs=[...(ROLEMAP[c]||[])];
  const inGame=new Map();[DS.me,DS.opp].forEach(id=>picksOf(id).forEach(p=>inGame.set(p.c,id)));
  const R=d.rec,RS=R?"26.16–26.20":d.sea?"2026 season":d.p20?"26.20 only":"",RT=R||d.sea||d.p20,WM=worldsMeta(c);
  const mp=mostPicked(c),sy=pairs5(c),ctr=counters5(c),bt=beats3(c);
  const stx=draftStatus,cc=o=>{const st=stx(o.x),tl=st?st.title:`${o.x}${o.note?" · "+o.note:""}${o.other?" · matchup from another lane":""}`;return `<span class="cc${st?" st-"+st.k:""}"${st?` style="--tc:${sideCol(st.sd)}"`:""} title="${esc(tl)}">${icon(o.x,22)}<span class="cn">${esc(o.x)}</span><em class="${o.cls}">${esc(o.em)}</em>${st?`<span class="stag">${esc(st.tag)}</span>`:""}</span>`};
  const anySt=[...sy,...ctr,...bt].some(o=>stx(o.x));
  const who=TEAMS.flatMap(t=>t.p.filter(p=>poolOf(p).some(x=>x[0]===c)).map(p=>({p,t}))).filter(o=>inDraft(o.t.id)&&DS.steps.length);
  const flags=[d.po?"Pro-only pick":"",d.so?"Solo-queue pick":""].filter(Boolean);
  return `<div class="ccard"><div class="chead">${icon(c,52)}<div><b>${esc(c)}</b><div><span class="tag">${pr?`<b class="tcol" style="color:${tierCol(tierOf(pr))}">${tierOf(pr)}-tier</b> · `:""}${rs.map(r=>RNAME[r]).join("/")||"—"}</span>${tr?`<span class="trend ${tr}">${TREND_TXT[tr]}</span>`:""}${flags.map(f=>`<span class="tag dimtag">${f}</span>`).join("")}</div></div></div>
  ${(()=>{const st=draftStatus(c);return st?`<div class="ststat st-${st.k}" style="--tc:${sideCol(st.sd)}">${esc(st.title)}</div>`:""})()}
  <div class="hgrid"><div class="hsec"><div class="label">Recent meta ${infoI(R?`465 pro games, patches 26.16–26.20 (NerfPlz). Solid = picked, striped = banned.`:`Not in the 26.16–26.20 list, so these are ${RS} numbers (NerfPlz).`)}</div><div class="hbars">
  ${RT?hb("Pick / ban",fill(RT[0],"pk")+fill(RT[1],"bn"),`${RT[0]}% · ${RT[1]}%`,"picked · banned"):hb("Pick / ban","","—","not in pro tables")}
  ${RT?hb("Presence",fill(RT[0]+RT[1]),`${RT[0]+RT[1]}%`,R?"465 games":RS):hb("Presence","","—","not in pro tables")}
  ${W?hb("Win rate",fill(W.wr),`${W.wr}%`,`${W.src}${W.n<15?" · small sample":""}`):hb("Win rate","","—","no data")}</div></div>
  <div class="hsec"><div class="label"><span class="hl">Worlds meta</span> ${infoI(`${WM.g} real Worlds games: 22 play-in + ${WM.swiss} Swiss. Play-in bans are only partly known${WM.gb<WM.g?`; the ban rate covers ${WM.gb} games`:""}. Your run is shown below.`)}</div><div class="hbars">
  ${hb("Pick / ban",fill(WM.pk,"pk")+fill(WM.bn,"bn"),`${WM.pk}% · ${WM.bn}%`,"picked · banned")}
  ${hb("Presence",fill(WM.pk+WM.bn),`${WM.pk+WM.bn}%`,`${WM.g} games`)}
  ${hb("Win rate",WM.p?fill(WM.w/WM.p*100):"",WM.p?`${Math.round(WM.w/WM.p*100)}%`:"—",`${WM.w}-${WM.l}${WM.p&&WM.p<5?" · small sample":""}`)}</div>${WM.run?`<span class="notes small">Your run: ${WM.runP} picks · ${WM.runB} bans · ${WM.runW}-${WM.runP-WM.runW} in ${WM.run} games</span>`:""}</div></div>
  <div class="key"><span><i style="background:var(--pick)"></i>Picked</span><span><i class="bnk"></i>Banned</span></div>
  <div><div class="label">Most picked at this Worlds ${infoI(`Real Worlds games on ${c}, as each player's win-loss. Hover a player for more. Your run is listed below.`)}</div><div class="ccs c3">${mp.length?mp.map(e=>`<span class="cc mp" style="--tc:${teamCol(e.t)}" title="${esc(`${e.n} (${e.t}) · ${e.g} game${e.g>1?"s":""} on ${c} at Worlds, ${e.w}-${e.g-e.w}${e.s?` · ${e.s} games on it in 2026`:""}`)}"><span class="tm">${esc(e.t)}</span><span class="cn">${esc(e.n)}</span><em class="g">${e.w}-${e.g-e.w}</em></span>`).join(""):`<span class="notes">No games on ${esc(c)} at this Worlds yet</span>`}</div>${(()=>{const r=mostPickedRun(c);return r.length?`<div class="notes small" style="margin-top:4px">Your run: ${r.map(e=>`${esc(e.n)} (${e.t}) ${e.g} gm ${e.w}-${e.g-e.w}`).join(" · ")}</div>`:""})()}</div>
  ${who.length?`<div class="here">${who.map(o=>`<span class="ig ${sideOf(o.t.id)}">${esc(o.p.n)} (${o.t.id})</span>`).join(" ")} <span class="notes">— comfort pick in this game</span></div>`:""}
  <div class="hgrid"><div><div class="label">Pairs with ${infoI("Win-rate lift as a pair (metabot.gg, METAsrc, 26.20). Gaps filled by team-mates who won with it at Worlds.")}</div><div class="ccs c3">${sy.length?sy.map(cc).join(""):`<span class="notes">no measured pairs</span>`}</div></div>
  <div><div class="label">Countered by ${infoI("Champions that beat it, with its matchup win rate (METAsrc). Same lane first; gaps filled by Worlds lane results, then your run.")}</div><div class="ccs c3">${ctr.length?ctr.map(cc).join(""):`<span class="notes">no matchup data</span>`}</div></div></div>
  <div><div class="label">Counters ${infoI(BEATS_INFO)}</div><div class="ccs c3">${bt.length?bt.map(cc).join(""):`<span class="notes">no matchup data</span>`}</div></div>
  ${anySt?`<div class="stkey"><span class="cc st-pick" style="--tc:var(--bside)"><span class="stag">TEAM</span></span><span class="cc st-pick" style="--tc:var(--rside)"><span class="stag">TEAM</span></span> picked this game <span class="cc st-ban" style="--tc:var(--bside)"><span class="stag">Ban</span></span><span class="cc st-ban" style="--tc:var(--rside)"><span class="stag">Ban</span></span> banned this game (tag colour = blue or red side) <span class="cc st-lock"><span class="stag">Locked</span></span> Fearless, picked in an earlier game</div>`:""}
  ${d.keys||d.core?`<div class="notes build">${d.keys?esc(d.keys[0])+" · ":""}${(d.core||[]).slice(0,3).map(esc).join(" → ")}</div>`:""}</div>`}
function placeInfo(el){const x=el.querySelector(".tipx");if(!x)return;const r=el.getBoundingClientRect(),w=Math.min(240,innerWidth-16);
  x.style.position="fixed";x.style.width=w+"px";let l=r.right+6;if(l+w>innerWidth-8)l=Math.max(8,r.left-6-w);x.style.left=l+"px";x.style.top=Math.max(8,r.top-6)+"px";
  requestAnimationFrame(()=>{const h=x.offsetHeight;if(r.top-6+h>innerHeight-8)x.style.top=Math.max(8,innerHeight-h-8)+"px"})}
document.addEventListener("mouseover",e=>{const el=e.target.closest&&e.target.closest(".info");if(el)placeInfo(el)});
document.addEventListener("focusin",e=>{const el=e.target.closest&&e.target.closest(".info");if(el)placeInfo(el)});
function placeTip(e){const r=e.target.getBoundingClientRect?e.target.getBoundingClientRect():{left:0,bottom:0,top:0};const wide=tip.classList.contains("wide");const fixed=wide;let w=Math.min(wide?400:400,innerWidth-24);
  const btn=e.target.dataset&&e.target.dataset.side?(e.target.closest("button")||e.target):null,bb=btn&&innerWidth>=700?btn.getBoundingClientRect():null;
  /* beside a portrait: use the wider free side so the card never covers the tile */
    tip.style.maxWidth=w+"px";tip.style.width=fixed?w+"px":"";
  /* portraits in the champion grid and suggestions: open beside the button (left or right, whichever has room) so the card never covers the row below */
  if(bb){const b=bb,right=b.right+10+w<=innerWidth-8;const x=right?b.right+10:Math.max(8,b.left-10-w);let y=Math.max(8,b.top-40);tip.style.left=x+"px";tip.style.top=y+"px";
    requestAnimationFrame(()=>{const h=tip.offsetHeight;if(y+h>innerHeight-8)tip.style.top=Math.max(8,innerHeight-h-8)+"px"});return}
  let x=Math.min(Math.max(12,r.left),innerWidth-w-12),y=r.bottom+8;tip.style.left=x+"px";tip.style.top=y+"px";
  requestAnimationFrame(()=>{const h=tip.offsetHeight;if(y+h>innerHeight-8)tip.style.top=Math.max(8,r.top-h-8)+"px"})}
/* the card stays open while the pointer moves onto it, so its ! notes can be read */
let tipT=null,tipEl=null;
let tipD=null;
function tipOn(e){if(TOUCH)return;const el=e.target.closest&&e.target.closest("[data-tp],[data-tc],[data-tt]");if(!el||tip.contains(el))return;clearTimeout(tipT);if(el===tipEl&&!tip.hidden)return;
  clearTimeout(tipD);if(el.dataset.side&&e.type==="mouseover"){if(!tip.hidden){tip.hidden=true;tipEl=null}tipD=setTimeout(()=>showTip(el),300);return}showTip(el)}
function showTip(el){tipEl=el;
  const ch=!!el.dataset.tc&&!el.dataset.tp;tip.classList.toggle("wide",ch);tip.classList.toggle("pl",!!el.dataset.tp);
  const tpA=el.dataset.tp?el.dataset.tp.split("|").map((v,i)=>i?+v:v):null,onRoleCard=!!(tpA&&VROLE[CUR]&&el.closest("#v-role .pcard"));
  tip.innerHTML=tpA?(onRoleCard?playerLogTip(...tpA):playerTip(...tpA)):el.dataset.tt?teamTip(el.dataset.tt):champTip(el.dataset.tc);tip.hidden=false;placeTip({target:el})}
function tipOff(e){if(TOUCH)return;const el=e.target.closest&&e.target.closest("[data-tp],[data-tc],[data-tt]");if(el&&!tip.contains(el)){clearTimeout(tipD);clearTimeout(tipT);tipT=setTimeout(()=>{tip.hidden=true;tipEl=null},el.dataset.side?120:220)}}
/* touch screens (phones, tablets): no hover, so a tap opens the card as a sheet from the bottom instead of picking.
   In champ select the sheet carries the Pick / Ban button. Desktop keeps hover cards and click-to-pick. */
const touchMQ=matchMedia("(hover: none) and (pointer: coarse)");let TOUCH=touchMQ.matches;
try{touchMQ.addEventListener("change",e=>{TOUCH=e.matches})}catch(e){}
const tipBg=document.createElement("div");tipBg.className="tipbg";tipBg.hidden=true;document.body.appendChild(tipBg);
function closeTip(){clearTimeout(tipD);clearTimeout(tipT);tip.hidden=true;tipEl=null;tip.classList.remove("sheet");tipBg.hidden=true}
function openSheet(el,pickC){showTip(el);tip.classList.add("sheet");tip.style.left=tip.style.top=tip.style.width=tip.style.maxWidth="";tipBg.hidden=false;
  const nx=SEQ[DS.steps.length],act=pickC?(nx&&nx[1]==="ban"?"Ban":"Pick"):"";
  /* a champion already picked on the board (data-si = its draft step): its role can be changed here, as the row's role menu does on desktop */
  const si=el.dataset.si!=null?+el.dataset.si:null,ps=si!=null?DS.steps[si]:null;
  const roleBar=ps&&ps.k==="pick"?`<div class="sheetroles"><span class="notes">Role</span>${ROLES.map(r=>`<button class="btn${r===ps.r?" pri":""}" data-sheetrole="${si}|${r}" aria-pressed="${r===ps.r}">${r}</button>`).join("")}</div>`:"";
  tip.insertAdjacentHTML("afterbegin",`<div class="sheetbar">${pickC?`<button class="btn pri" data-sheetpick="${esc(pickC)}">${act} ${esc(pickC)}</button>`:""}<button class="btn" data-sheetclose aria-label="Close">Close</button></div>${roleBar}`)}
tipBg.addEventListener("click",closeTip);
tip.addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;if(b.hasAttribute("data-sheetclose")){closeTip();return}
  if(b.dataset.sheetpick){const c=b.dataset.sheetpick;closeTip();doPick(c)}
  if(b.dataset.sheetrole){const [si,r]=b.dataset.sheetrole.split("|");closeTip();setPickRole(+si,r)}});
document.addEventListener("click",e=>{if(!TOUCH||tip.contains(e.target))return;
  const btn=e.target.closest("button[data-c]"),inDraftV=btn&&document.getElementById("v-draft").contains(btn);
  if(inDraftV&&!btn.disabled){e.preventDefault();e.stopPropagation();openSheet(btn.querySelector("[data-tc]")||btn,btn.dataset.c);return}
  const el=e.target.closest("[data-tp],[data-tc],[data-tt]");if(el){e.preventDefault();e.stopPropagation();openSheet(el,null)}},true);
/* clicking a champion (to pick or ban) always closes its card */
document.addEventListener("click",e=>{if(!TOUCH&&!tip.contains(e.target)){clearTimeout(tipD);tip.hidden=true;tipEl=null}},true);
tip.addEventListener("mouseenter",()=>clearTimeout(tipT));tip.addEventListener("mouseleave",()=>{tip.hidden=true;tipEl=null});
document.addEventListener("mouseover",tipOn);document.addEventListener("mouseout",tipOff);
document.addEventListener("focusin",tipOn);document.addEventListener("focusout",e=>{if(!tip.contains(e.relatedTarget))tipOff(e)});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!tip.hidden)closeTip()});
window.addEventListener("scroll",()=>{tip.hidden=true;tipEl=null},{passive:true});

/* ---- analysis ---- */
function draftScore(id){
  const ps=picksOf(id),t=team(id),other=otherId(id);let meta=0,comf=0,syn=0;const pairs=[],rows=[];
  ps.forEach(p=>{const pl=t.p[ROLES.indexOf(p.r)],x=pl.picks.find(y=>y[0]===p.c),pr=presOf(p.c);meta+=pr;if(x)comf++;
    rows.push({r:p.r,pl,c:p.c,x,pr})});
  for(let a=0;a<ps.length;a++)for(let b=a+1;b<ps.length;b++){const l=SYN[ps[a].c+"|"+ps[b].c];if(l!=null){syn+=l;pairs.push([ps[a].c,ps[b].c,l])}}
  const bans=bansOf(id).map(b=>{const hit=comfortIn(other,b.c);return {c:b.c,hit,pr:presOf(b.c)}});
  const denied=ps.filter(p=>comfortIn(other,p.c).length).map(p=>({c:p.c,who:comfortIn(other,p.c)}));
  const lostComf=team(id).p.filter(pl=>pl.picks.length&&!rows.some(r=>r.pl===pl&&r.x)).map(pl=>pl.n);
  const score=meta/5*0.05+comf*1.0+syn*0.25+bans.filter(b=>b.hit.length).length*0.4;
  return {id,rows,meta:Math.round(meta/Math.max(1,ps.length)),comf,syn:Math.round(syn*10)/10,pairs,bans,denied,score,lostComf};
}
const winP=(a,b)=>1/(1+Math.exp(-(a-b)/9));
function draftEdge(){const A=draftScore(DS.me),B=draftScore(DS.opp);return Math.max(-3,Math.min(3,(A.score-B.score)*0.6))}
function analysis(){
  const A=draftScore(DS.me),B=draftScore(DS.opp),edge=draftEdge();
  const base=winP(team(DS.me).ov,team(DS.opp).ov);let mw=0;const meBlue=sideOf(DS.me)==="blue";for(let q=0;q<600;q++){const r=simGame(true);if((r.winner==="blue")===meBlue)mw++}const withD=mw/600;
  const col=d=>{const t=team(d.id);return `<div class="an ${sideOf(d.id)}"><h3>${esc(t.name)} <small>${sideOf(d.id)} side</small></h3>
    <div class="kpis"><span><b>${d.comf}/5</b>comfort picks</span><span><b>${d.meta}%</b>avg meta presence</span><span><b>${d.syn>0?"+":""}${d.syn}</b>synergy lift</span><span><b>${d.bans.filter(b=>b.hit.length).length}/5</b>bans on comfort</span></div>
    <table class="tt full"><thead><tr><th>Role</th><th>Player</th><th>Champion</th><th>Fit</th></tr></thead><tbody>${d.rows.sort((a,b)=>ROLES.indexOf(a.r)-ROLES.indexOf(b.r)).map(r=>`<tr><td>${r.r}</td><td data-tp="${d.id}|${ROLES.indexOf(r.r)}" tabindex="0" class="hov">${esc(r.pl.n)}</td><td data-tc="${esc(r.c)}" tabindex="0" class="hov">${esc(r.c)}</td><td>${r.x?`<span class="chip meta">Comfort ${r.x[1]?r.x[1]+"g ":""}${r.x[2]}%</span>`:`<span class="chip off">Off-pool</span>`} <span class="notes tcol" style="color:${tierCol(tierOf(r.pr))}">${tierOf(r.pr)}</span></td></tr>`).join("")}</tbody></table>
    <div class="notes"><b>Synergies:</b> ${d.pairs.length?d.pairs.map(([a,b,l])=>`${esc(a)} + ${esc(b)} (${l>0?"+":""}${l})`).join("; "):"none in the data"}</div>
    <div class="notes"><b>Bans:</b> ${d.bans.map(b=>`${esc(b.c)} ${b.hit.length?"→ hit "+b.hit.map(o=>o.p.n).join(", "):b.pr?"(meta only)":"(no comfort or meta target)"}`).join("; ")}</div>
    <div class="notes"><b>Denied:</b> ${d.denied.length?d.denied.map(x=>`${esc(x.c)} from ${x.who.map(o=>o.p.n).join(", ")}`).join("; "):"none"}</div>
    ${d.lostComf.length?`<div class="notes"><b>Off their comfort:</b> ${d.lostComf.map(esc).join(", ")}</div>`:""}</div>`};
  return `<div class="panel" style="display:grid;gap:12px"><h3 style="font-size:20px;text-transform:uppercase">Draft review</h3>
    <div class="verdict"><div><span class="notes">Before draft</span><b>${Math.round(base*100)}%</b></div><div><span class="notes">After draft</span><b>${Math.round(withD*100)}%</b></div><div class="notes">${esc(team(DS.me).name)} win chance for this game. Before = team ratings only; after = 600 simulated games using these picks (comfort, meta strength, synergy).</div></div>
    <div class="board">${col(sideOf(DS.me)==="blue"?A:B)}${col(sideOf(DS.me)==="blue"?B:A)}</div>
    ${DS.tour?(DS.sim?"":`<div class="ctrls"><button class="btn primary" data-act="tplay">Play this game</button></div>`):DS.series&&!DS.sim?`<div class="ctrls"><button class="btn primary" data-act="splay">Play game ${DS.series.games.length+1}</button></div>`:""}
    ${DS.sim?simView():""}</div>`;
}

/* ---- single-game simulation ---- */
const gauss=()=>{let u=0,v=0;while(!u)u=Math.random();while(!v)v=Math.random();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v)};
const sig=x=>1/(1+Math.exp(-x));
function champMod(pl,c){const x=poolOf(pl).find(y=>y[0]===c),pr=presOf(c),d=CHAMP_DB[c];let m=pr>=55?2:pr>=40?1.5:pr>=30?1:pr>0?0.5:0;
  const W=wrOf(c);if(W)m+=Math.max(-1.5,Math.min(1.5,(W.adj-50)/4));
  if(x)m+=(3+((x[2]||55)-55)/10)*(d&&d.fade?0.5:1);else if(pl.picks.length)m-=3;return m}
const SIMK=0.15; /* strength scale: calibrated against 711 real 2026 pro series (research/backtest-2026.md); was 0.3, which made favourites far too sure */
function teamStr(id){
  const t=team(id),ps=picksOf(id),P={};ROLES.forEach((r,i)=>{const pk=ps.find(p=>p.r===r);P[r]={pl:t.p[i],c:pk?pk.c:"?",m:pk?champMod(t.p[i],pk.c):0}});
  const a=(r,j)=>(P[r].pl.a[j]+P[r].m)*SIMK;let syn=0;for(let i=0;i<ps.length;i++)for(let j=i+1;j<ps.length;j++){const l=SYN[ps[i].c+"|"+ps[j].c];if(l!=null)syn+=l}
  /* star factor: the best player on the team (rated 90+) can swing fights a little on their own */
  const star=Math.max(0,...ROLES.map(r=>P[r].pl.ov-90))*STAR.fight;
  return {id,P,syn,star,
    lane:{TOP:a("TOP",0),MID:a("MID",0),BOT:(a("ADC",0)+a("SUP",0))/2},jgl:a("JGL",0),
    obj:(a("JGL",1)+a("SUP",1)+a("MID",1))/3,
    tf:(a("TOP",1)+a("JGL",2)+a("MID",2)+a("ADC",1)+a("SUP",2))/5+syn*0.25,
    late:(a("TOP",2)+a("ADC",2)+a("SUP",2)+a("MID",2))/4};
}
const KW={TOP:2,JGL:2,MID:3,ADC:3.2,SUP:0.6};
/* fight randomness and how much a gold lead counts in fights (tuned so favourites win about as often as in pro play) */
const SIM_SD=5,SIM_GOLD=1000;
/* star players: k = how strongly rating shifts kill share, die = how much less stars die, assist = support Playmaking → assists,
   fight = fight bonus per rating point above 90 for a team's best player, pog = game-rating bonus for players rated 90+ (per 6 points) */
const STAR={k:12,die:0.8,assist:85,fight:0.08,pog:0.35,supElite:0.12};
/* late-game tuning: buff and soul fight bonus, push power, when the Nexus can fall, comeback bounty, how fast gold leads fade.
   Tuned to LCK 2026 (RFT.GG): average game ~32 min, team taking Baron wins ~85%, team taking Elder wins ~75%. */
const LATE={elderGold:0.3,elderSecure:0.85,baronFight:3,elderFight:5.5,soulFight:0.5,baronPush:1.2,elderPush:1.5,goldPush:5000,latePush:12,endBar:3.0,bounty:1.0,goldFade:8};
function wpick(o){const e=Object.entries(o);let s=e.reduce((x,[,w])=>x+w,0)*Math.random();for(const [k,w] of e){if((s-=w)<=0)return k}return e[0][0]}
function simGame(quiet){
  const B=teamStr(idOnSide("blue")),R=teamStr(idOnSide("red")),S={blue:B,red:R},opp=s=>s==="blue"?"red":"blue";
  const g={fights:[],el:{blue:0,red:0},inh:{blue:0,red:0},soul:null,solo:{blue:{},red:{}},jd:0,gold:0,k:{blue:0,red:0},tw:{blue:0,red:0},dr:{blue:0,red:0},ba:{blue:0,red:0},gr:{blue:0,red:0},ev:[],gl:[[0,0]],kda:{blue:{},red:{}},lanes:{}};
  ROLES.forEach(r=>{g.kda.blue[r]=[0,0,0];g.kda.red[r]=[0,0,0]});
  const nm=(s,r)=>`${S[s].P[r].pl.n} (${S[s].P[r].c})`;
  const ev=(t,s,txt)=>{if(!quiet)g.ev.push([t,s,txt])};
  /* who gets kills, deaths and assists: role first, then player quality — stars take more of the kills and die less;
     a support's assists follow their Playmaking rating */
  const qW=(sd,r)=>Math.exp((Math.min(96,S[sd].P[r].pl.ov)-85)/STAR.k);
  const KWs={},VWs={};["blue","red"].forEach(sd=>{KWs[sd]={};VWs[sd]={};ROLES.forEach(r=>{KWs[sd][r]=KW[r]*qW(sd,r);VWs[sd][r]={TOP:2,JGL:2,MID:2,ADC:2.5,SUP:2.5}[r]/Math.pow(qW(sd,r),STAR.die)})});
  const asP=(sd,r)=>{const pl=S[sd].P[r].pl,v=r==="SUP"?pl.a[0]:pl.ov;return Math.min(0.85,0.55*(1+(v-85)/STAR.assist))};
  const kill=(s,n,forced)=>{for(let i=0;i<n;i++){const kr=forced&&i===0?forced:wpick(KWs[s]),vr=wpick(VWs[opp(s)]);g.kda[s][kr][0]++;g.kda[opp(s)][vr][1]++;
    ROLES.filter(r=>r!==kr&&Math.random()<asP(s,r)).forEach(r=>g.kda[s][r][2]++);g.k[s]++}};
  const swing=(s,amt)=>{g.gold+=s==="blue"?amt:-amt};
  const lead=()=>g.gold>0?"blue":"red";
  let fb=false;
  /* laning 0-14 */
  const jd=B.jgl-R.jgl+gauss()*7;g.jd=jd;const gankLane=["TOP","MID","BOT"][Math.floor(Math.random()*3)];
  ["TOP","MID","BOT"].forEach(L=>{let d=B.lane[L]-R.lane[L]+gauss()*7;if(L===gankLane)d+=jd*0.4;
    const mu=(rb,rr)=>{const m=matchup(B.P[rb].c,R.P[rr].c);return m==null?0:(m-50)*0.5};d+=L==="BOT"?(mu("ADC","ADC")+mu("SUP","SUP"))/2:mu(L,L);g.lanes[L]=d;swing("blue",d*35);
    const w=d>0?"blue":"red",r=L==="BOT"?"ADC":L;
    if(Math.abs(d)>6){const t=3+Math.floor(Math.random()*8);kill(w,1,r);g.solo[w][r]=(g.solo[w][r]||0)+1;ev(t,w,`${L==="BOT"?"Bot lane 2v2":"Solo kill"}: ${nm(w,r)} beats ${nm(opp(w),r)}`);fb=true}
    else if(Math.abs(d)>2)ev(9+Math.floor(Math.random()*4),w,`${nm(w,r)} builds a CS lead in ${L.toLowerCase()} lane`)});
  if(Math.abs(jd)>4){const w=jd>0?"blue":"red";kill(w,1,"JGL");ev(4+Math.floor(Math.random()*4),w,`${nm(w,"JGL")} ganks ${gankLane.toLowerCase()} lane for a kill`);fb=true;swing(w,250)}
  g.gl.push([7,g.gold]);
  const objP=s=>sig(((S[s].obj-S[opp(s)].obj)+(s==="blue"?g.gold:-g.gold)/1200)/8);
  [[5,"Dragon"],[6,"Void grubs"],[10,"Dragon"],[14,"Rift Herald"]].forEach(([t,o])=>{const w=Math.random()<objP("blue")?"blue":"red";
    if(o==="Dragon")g.dr[w]++;else g.gr[w]++;swing(w,o==="Dragon"?250:350);ev(t,w,`${o} to ${team(S[w].id).name}${o==="Dragon"?` (${g.dr[w]} dragon${g.dr[w]>1?"s":""})`:""} — ${nm(w,"JGL")} controls the pit`)});
  g.gl.push([14,g.gold]);
  /* ---- mid and late game: objectives, fights, structures, Nexus ----
     Fights decide objectives and structures; a team only ends the game by winning a fight while it has an
     inhibitor down and enough push (gold lead, Baron, Elder). A gold lead counts for less as the game goes long,
     and the team that's behind gets bounty gold when it wins a fight, so late games even out. */
  const T=LATE;
  const gl2=s=>s==="blue"?g.gold:-g.gold;                         /* gold lead from s's side */
  const buff={baron:{blue:0,red:0},elder:{blue:0,red:0}};           /* minute the buff runs out */
  let soul=null,dT=15,bT=24+Math.floor(Math.random()*3),eT=99;
  const fight=(t,label,wt,bonus,gf)=>{const goldW=(gf==null?1:gf)*g.gold/(SIM_GOLD*(1+Math.max(0,t-28)/T.goldFade));
    const bf=s=>(buff.baron[s]>t?T.baronFight:0)+(buff.elder[s]>t?T.elderFight:0)+(soul===s?T.soulFight:0);
    const d=wt*(B.tf-R.tf)+(1-wt)*(B.late-R.late)+goldW+bf("blue")-bf("red")+(B.star-R.star)+(bonus||0)+gauss()*SIM_SD;const w=d>0?"blue":"red",l=opp(w);g.fights.push([t,w,label,g.gold]);
    const late=t>=35,kw=2+Math.floor(Math.random()*(late?4:3)),kl=Math.floor(Math.random()*2);kill(w,kw);kill(l,kl);
    const behind=gl2(w)<0?Math.min(1,-gl2(w)/8000):0;swing(w,(600+kw*300)*(1+behind*T.bounty));
    const star=wpick({TOP:1,JGL:1,MID:2,ADC:2,SUP:0.6});ev(t,w,`${label}: ${team(S[w].id).name} win ${kw}-for-${kl}, led by ${nm(w,star)}`);g.gl.push([t,g.gold]);return {w,kw,kl}};
  /* after a won fight: take towers, maybe an inhibitor, maybe the Nexus */
  const push=(t,w,kw,kl)=>{const pw=1+(buff.baron[w]>t?T.baronPush:0)+(buff.elder[w]>t?T.elderPush:0)+Math.max(0,gl2(w))/T.goldPush+(kw-kl)*0.2+Math.max(0,t-30)/T.latePush;
    const take=Math.min(11-g.tw[w],Math.max(1,Math.round(pw*(0.5+Math.random()*0.8))));g.tw[w]+=take;swing(w,take*300);
    if(g.tw[w]>=7&&g.inh[w]<3&&Math.random()<sig(pw-1.6)){g.inh[w]++;swing(w,500);ev(t,w,`${team(S[w].id).name} break an inhibitor (${g.tw[w]} towers down)`)}
    if(g.inh[w]>=1&&g.tw[w]>=9&&Math.random()<sig((pw-T.endBar)*1.4)){g.tw[w]=Math.min(11,g.tw[w]+2);return true}
    return false};
  let t=14,winner=null,step=0;
  while(!winner&&t<62){step++;t+=step===1?2+Math.floor(Math.random()*3):3+Math.floor(Math.random()*2);
    let res,obj=null;
    const due=[["baron",bT],["elder",eT],["dragon",soul?99:dT]].filter(x=>t>=x[1]).sort((x,y)=>x[1]-y[1])[0];   /* the objective that has been up longest */
    if(due&&due[0]==="baron"){obj="baron";res=fight(t,"Fight around Baron",0.7)}
    else if(due&&due[0]==="elder"){obj="elder";res=fight(t,"Elder Dragon fight",0.5,0,T.elderGold)}  /* a single fight at the pit: gold matters less */
    else if(due){obj="dragon";res=fight(t,"Teamfight at dragon",t<30?1:0.6)}
    else res=fight(t,t<25?"Skirmish over mid tower":t<38?"Late-game teamfight":"Teamfight at the base",t<25?1:0.5);
    const w=res.w;
    if(obj){const take=Math.random()<(obj==="dragon"?0.95:obj==="elder"?T.elderSecure:0.88)?w:opp(w);       /* small steal chance */
      if(obj==="baron"){g.ba[take]++;buff.baron[take]=t+3;bT=t+6+Math.floor(Math.random()*3);swing(take,1500);ev(t,take,`Baron Nashor to ${team(S[take].id).name}${take!==w?" — stolen!":""}`)}
      else if(obj==="elder"){g.el[take]++;buff.elder[take]=t+2.5;eT=t+6;swing(take,800);ev(t,take,`Elder Dragon to ${team(S[take].id).name} — execute buff for 2:30${take!==w?" (stolen!)":""}`)}
      else{g.dr[take]++;dT=t+5;swing(take,300);ev(t,take,`Dragon to ${team(S[take].id).name} (${g.dr[take]})`);
        if(g.dr[take]>=4){soul=take;g.soul=take;eT=t+6;ev(t,take,`${team(S[take].id).name} claim dragon soul — Elder Dragon spawns in 6 minutes`)}}}
    if(push(t,w,res.kw,res.kl)){winner=w;t+=1;ev(t,w,`${team(S[w].id).name} push through ${buff.elder[w]>t-1?"with Elder ":buff.baron[w]>t-1?"with Baron ":""}and destroy the Nexus`)}
  }
  if(!winner){winner=g.gold>=0?"blue":"red";ev(t,winner,`${team(S[winner].id).name} close it out and destroy the Nexus`)}
  g.winner=winner;g.time=t;{const fk=g.ev.slice().sort((a,b)=>a[0]-b[0]).find(e=>/Solo kill|2v2|ganks/.test(e[2]));if(fk)fk[2]+=" — first blood"}g.sec=Math.floor(Math.random()*60);g.gl.push([t,g.gold]);g.B=B;g.R=R;g.ev.sort((a,b)=>a[0]-b[0]);
  if(!quiet&&typeof gameStats==="function")gameStats(g);
  return g;
}
function runGame(){const N=1500;let bw=0;for(let i=0;i<N;i++)if(simGame(true).winner==="blue")bw++;DS.sim={g:simGame(false),bwin:bw/N};}
function goldChart(gl,time){const W=600,H=140,P=24,mx=Math.max(3000,...gl.map(x=>Math.abs(x[1])));const X=m=>P+(m/Math.max(time,30))*(W-2*P),Y=v=>H/2-(v/mx)*(H/2-12);
  const pts=gl.map(([m,v])=>`${X(m).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
  const ticks=[0,10,20,30,40].filter(m=>m<=Math.max(time,30)).map(m=>`<text x="${X(m)}" y="${H-2}" text-anchor="middle" class="ax">${m}m</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="gchart" role="img" aria-label="Gold difference over time"><rect x="${P}" y="0" width="${W-2*P}" height="${H/2}" fill="var(--bsidebg)"/><rect x="${P}" y="${H/2}" width="${W-2*P}" height="${H/2-12}" fill="var(--rsidebg)"/><line x1="${P}" x2="${W-P}" y1="${H/2}" y2="${H/2}" stroke="var(--line)"/><text x="${P+4}" y="12" class="ax">Blue +${(mx/1000).toFixed(1)}k</text><text x="${P+4}" y="${H-16}" class="ax">Red +${(mx/1000).toFixed(1)}k</text><polyline points="${pts}" fill="none" stroke="var(--gold)" stroke-width="2.5"/>${gl.map(([m,v])=>`<circle cx="${X(m)}" cy="${Y(v)}" r="3" fill="var(--gold)"/>`).join("")}${ticks}</svg>`}
function simView(){
  const {g,bwin}=DS.sim,blueId=idOnSide("blue"),redId=idOnSide("red"),w=g.winner,wid=w==="blue"?blueId:redId;
  const pct=Math.round((w==="blue"?bwin:1-bwin)*100);
  const sb=s=>{const id=s==="blue"?blueId:redId,T=s==="blue"?g.B:g.R;return `<div class="an ${s}"><h3>${esc(team(id).name)} <small>${s} · ${g.k[s]} kills · ${g.tw[s]} towers · ${g.dr[s]} dragons · ${g.ba[s]} barons</small></h3><table class="tt full stab4"><thead><tr><th>Role</th><th>Player</th><th>Champion</th><th>K/D/A</th><th>DMG%</th><th>CSD@15</th><th>Rating</th></tr></thead><tbody>${ROLES.map((r,i)=>`<tr><td>${r}</td><td class="hov" data-tp="${id}|${i}" tabindex="0">${esc(T.P[r].pl.n)}</td><td><span class="cname hov" data-tc="${esc(T.P[r].c)}" tabindex="0">${icon(T.P[r].c,26)}${esc(T.P[r].c)}</span></td><td class="num">${g.kda[s][r].join("/")}</td>${g.ps?`<td class="num">${Math.round(g.ps[s][r].dmgS*100)}%</td><td class="num">${g.ps[s][r].csd>0?"+":""}${g.ps[s][r].csd}</td><td class="num">${g.pog&&g.pog.s===s&&g.pog.r===r?"★ ":""}${g.ps[s][r].rt.toFixed(1)}</td>`:""}</tr>`).join("")}</tbody></table></div>`};
  const lane=L=>{const d=g.lanes[L];const s=d>0?"blue":"red";return `<span class="chip ${Math.abs(d)<2?"off":s==="blue"?"bl":"rd"}">${L}: ${Math.abs(d)<2?"even":team(s==="blue"?blueId:redId).id+" ahead"}</span>`};
  const fx=(lab,b,r)=>{const d=b-r;return `<span class="chip ${Math.abs(d)<1?"off":d>0?"bl":"rd"}">${lab}: ${Math.abs(d)<1?"even":(d>0?team(blueId).id:team(redId).id)+" +"+Math.abs(d).toFixed(1)}</span>`};
  /* this game's story: lanes, gold at 15, objectives, fights won and the fight that ended it */
  const tid=x=>team(x==="blue"?blueId:redId).id,sch=(lab,x)=>`<span class="chip ${x?x==="blue"?"bl":"rd":"off"}">${lab}</span>`;
  const g15=(g.gl.find(x=>x[0]>=14)||[0,0])[1],fw={blue:g.fights.filter(f=>f[1]==="blue").length,red:g.fights.filter(f=>f[1]==="red").length};
  const lead=(a,b)=>a>b?"blue":b>a?"red":null,mm=t=>`${t}:${String((t*37)%60).padStart(2,"0")}`;
  const last=g.fights[g.fights.length-1];
  const story=[sch(`Gold @15: ${Math.abs(g15)<500?"even":tid(g15>0?"blue":"red")+" +"+(Math.abs(g15)/1000).toFixed(1)+"k"}`,Math.abs(g15)<500?null:g15>0?"blue":"red"),
    sch(`Dragons ${g.dr.blue}–${g.dr.red}`,lead(g.dr.blue,g.dr.red)),sch(`Barons ${g.ba.blue}–${g.ba.red}`,lead(g.ba.blue,g.ba.red)),sch(`Towers ${g.tw.blue}–${g.tw.red}`,lead(g.tw.blue,g.tw.red)),
    sch(`Fights won ${fw.blue}–${fw.red}`,lead(fw.blue,fw.red)),last?sch(`Decided: ${last[2].toLowerCase()} at ${mm(last[0])} → ${tid(last[1])}`,last[1]):""].join("");
  /* upset: the winner was under 25% to win this draft — find where it turned */
  const upset=pct<25;let turn="";
  if(upset){const ws=w,sg=v=>ws==="blue"?v:-v;const behind=g.fights.filter(f=>f[1]===ws&&sg(f[3])<=0);
    const f=behind.length?behind[behind.length-1]:last;
    if(!behind.length&&sg(g15)>=500)turn=`${esc(team(wid).name)} won the laning phase (+${(sg(g15)/1000).toFixed(1)}k gold at 15) and never gave the lead back, despite ${esc(team(wid===blueId?redId:blueId).name)}'s edge on paper.`;else turn=`${esc(team(wid).name)} turned it at ${mm(f[0])}: won the ${esc(f[2].toLowerCase())}${sg(f[3])<0?` from ${(Math.abs(f[3])/1000).toFixed(1)}k gold down`:""}${f!==last?` and the deciding fight at ${mm(last[0])}`:""}, despite ${esc(team(wid===blueId?redId:blueId).name)}'s edge on paper.`}
  return `<div class="sim"><div class="result ${w}"><span class="eyebrow" style="color:inherit">Simulated game</span><b>${esc(team(wid).name)} win${upset?` <span class="upset">Upset</span>`:""}</b><span>${g.time}:${String(g.sec).padStart(2,"0")} · kills ${g.k.blue}–${g.k.red} · this draft wins for ${team(wid).id} in ${pct}% of simulations</span>${upset?`<span class="pogline">${turn}</span>`:""}${g.pog?`<span class="pogline">Player of the Game: <b>${esc(g.pog.n)}</b> (${esc(g.pog.c)}) · rating ${g.pog.rt.toFixed(1)} · ${esc(g.pog.why)}</span>`:""}</div>
    <div class="ctrls"><span class="notes">This game:</span>${lane("TOP")}${lane("MID")}${lane("BOT")}${story}</div>
    <div class="ctrls"><span class="notes">On paper:</span>${fx("Jungle early",g.B.jgl,g.R.jgl)}${fx("Objectives",g.B.obj,g.R.obj)}${fx("Teamfights",g.B.tf,g.R.tf)}${fx("Late game",g.B.late,g.R.late)}${sch(`Pre-game: ${tid(bwin>=.5?"blue":"red")} ${Math.round(Math.max(bwin,1-bwin)*100)}%`,bwin>=.5?"blue":"red")}</div>
    ${goldChart(g.gl,g.time)}
    <div class="board">${sb("blue")}${sb("red")}</div>
    <div><div class="eyebrow">Play-by-play</div><ol class="pbp">${g.ev.map(([t,s,x])=>`<li class="${s}"><span class="num">${t}:${String((t*37)%60).padStart(2,"0")}</span>${esc(x)}</li>`).join("")}</ol></div>
    <p class="notes" style="font-size:12px;margin:0">"This game" shows what happened in this simulation; "On paper" shows the teams' rating edges going in. Each phase uses the players' attribute ratings for that phase (laning, early jungle, objectives, teamfights, late game), adjusted by their champion and, in lane, by the champion matchup where METAsrc has data: +3 or more on a comfort pick (scaled by win rate), −3 off their pool, plus up to +2 for meta strength and the team's synergy lift in fights. Random variance is added to every phase, so run it again for a different game.</p>
    ${DS.tour?`<button class="btn primary" data-act="tnext">${DS.tour.next}</button>`:DS.series?(seriesDone()?`<button class="btn primary" data-act="sview">See the series result</button>`:`<button class="btn primary" data-act="snext">Continue to game ${DS.series.games.length+1}</button>`):""}</div>`;
}
/* ---- render ---- */
function teamPanel(id){
  const t=team(id),sd=sideOf(id),ps=picksOf(id),bs=bansOf(id),i=DS.steps.length,nxt=i<20?SEQ[i]:null,isNext=nxt&&actorId(nxt[0])===id;
  const fpTeam=idOnSide(DS.fp)===id,picking=isNext&&nxt[1]==="pick",nextRole=picking?openRoles(id)[0]:null;
  const byRole=ROLES.map((r,ri)=>{const p=ps.find(x=>x.r===r),pl=t.p[ri];
    const art=p&&splashUrl(p.c);
    return `<div class="slot ${p?"on":""}${art?" art":""} ${p&&p.i===DS.fresh?"fresh":""} ${!p&&picking&&r===nextRole?"now":""}"${art?` style="--splash:url('${art}')"`:""}>${p?`<span class="hov" data-tc="${esc(p.c)}" data-si="${p.i}" tabindex="0">${icon(p.c,44)}</span>`:`<span class="ico empty" style="--s:44px"><b>${r}</b></span>`}<div class="st"><b class="ch"${p?` data-tc="${esc(p.c)}" data-si="${p.i}"`:""}>${p?esc(p.c):picking&&r===nextRole?"Picking…":"—"}</b><small><span class="role">${r}</span> · <span class="pl hov" data-tp="${id}|${ri}" tabindex="0">${esc(pl.n)}</span></small></div>${p?`<select data-rs="${p.i}" aria-label="Role for ${esc(p.c)}">${ROLES.map(x=>`<option${x===p.r?" selected":""}>${x}</option>`).join("")}</select>`:""}</div>`}).join("");
  const banSlots=[0,1,2,3,4].map(j=>(j===3?`<span class="bdiv" aria-hidden="true"></span>`:"")+(()=>{const b=bs[j];const willBe=!b&&isNext&&nxt[1]==="ban"&&j===bs.length;return `<span class="ban ${b?"on":""} ${b&&b.i===DS.fresh?"fresh":""} ${willBe?"next":""}" ${b?`data-tc="${esc(b.c)}" tabindex="0" aria-label="Banned: ${esc(b.c)}"`:""}>${b?icon(b.c,34):willBe?"<small>ban</small>":""}</span>`})()).join(""); /* phase 1 bans (first 3) | phase 2 bans (last 2) */
  return `<div class="side ${sd} ${isNext?"active":""}"><div class="sideh hov" data-tt="${id}" tabindex="0"><span>${regDot(id)}<span class="tb" style="--tc:${teamCol(id)}">${esc(id)}</span> ${esc(t.name)}</span><small>${sd==="blue"?"Blue":"Red"} side · ${fpTeam?"first pick":"last pick"}${id===DS.me?" · you":DS.ai?" · AI":""}</small></div>
    <div class="bans">${banSlots}</div>${byRole}<div class="picking">${picking?`Picking… open: ${openRoles(id).join(", ")}`:""}</div></div>`; /* always there at a fixed height so rows below don't jump */
}
/* after each pick: the best follow-ups for the team that just locked in */
function nextBest(){const last=[...DS.steps].reverse().find(s=>s.k==="pick");if(!last||DS.steps.length>=20)return"";const id=last.t;if(!openRoles(id).length)return"";
  const tk=taken(),rs=POOL.filter(c=>!tk.has(c)).map(c=>scoreFor(c,id,"pick")).filter(x=>x&&x.s>0).sort((a,b)=>b.s-a.s).slice(0,5);if(!rs.length)return"";
  const lead=r=>r.why.find(w=>w.includes(" with "+last.c))||r.why.find(w=>/ with /.test(w))||r.why.find(w=>/beats|counters|comfort|denies/.test(w))||r.why[0]||"";
  return `<div class="nextbest"><div class="label">${icon(last.c,22)} ${esc(last.c)} locked → next best for ${esc(team(id).id)}</div><div class="ccs">${rs.map(r=>`<span class="cc hov" data-tc="${esc(r.c)}" tabindex="0">${icon(r.c,26)}${esc(r.c)} <small>${r.roles.join("/")}</small> <em class="g">${esc(lead(r))}</em></span>`).join("")}</div></div>`}
/* typed name → the closest real champion that is still available (exact, then starts-with, then contains, then near-spelling); never a made-up name */
const normN=x=>String(x).toLowerCase().replace(/[^a-z]/g,"");
function editDist(a,b){const d=Array.from({length:a.length+1},(_,i)=>[i]);for(let j=1;j<=b.length;j++)d[0][j]=j;
  for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return d[a.length][b.length]}
function allChamps(){return [...new Set([...POOL,...Object.keys(CHAMP_DB),...Object.keys(ASSETS.ids||{}),...Object.keys(DD_FIX)])]}
const NICK={j4:"Jarvan IV",mf:"Miss Fortune",tf:"Twisted Fate",ww:"Warwick",gp:"Gangplank",asol:"Aurelion Sol",tk:"Tahm Kench",yi:"Master Yi",mundo:"Dr. Mundo",kog:"Kog'Maw",reksai:"Rek'Sai",cait:"Caitlyn",noc:"Nocturne",wu:"Wukong",mao:"Maokai",naut:"Nautilus",sera:"Seraphine",ori:"Orianna",kass:"Kassadin",fiddle:"Fiddlesticks",heimer:"Heimerdinger",cass:"Cassiopeia",lb:"LeBlanc",renata:"Renata Glasc",nunu:"Nunu & Willump",vlad:"Vladimir",zil:"Zilean",trist:"Tristana",lilia:"Lillia",ez:"Ezreal",bv:"Bel'Veth",ks:"K'Sante",xin:"Xin Zhao"};
function bestMatch(q){const n=normN(q);if(!n)return null;const tk=taken(),L=allChamps().filter(c=>!tk.has(c)).map(c=>[c,normN(c)]);
  const nk=NICK[String(q).trim().toLowerCase().replace(/\s+/g,"")];if(nk&&!tk.has(nk))return nk;
  const pres=c=>presOf(c)||0;const by=f=>L.filter(f).sort((a,b)=>pres(b[0])-pres(a[0])||a[1].length-b[1].length)[0];
  let m=by(([c,k])=>k===n)||by(([c,k])=>k.startsWith(n))||by(([c,k])=>k.includes(n)||c.toLowerCase().split(/[\s'.&]+/).some(w=>w.startsWith(q.trim().toLowerCase())));
  if(!m&&n.length>=3){const sc=L.map(([c,k])=>[c,editDist(n,k.slice(0,Math.max(n.length,k.length)))]).sort((a,b)=>a[1]-b[1]);if(sc[0][1]<=Math.max(1,Math.floor(n.length/3)))m=sc[0]}
  return m?m[0]:null}
function pickTyped(){const c=bestMatch(DS.q||"");if(!c)return;if(!ROLEMAP[c]){ROLEMAP[c]=new Set(CHAMP_ROLE_FALLBACK[c]||ROLES);POOL.push(c);POOL.sort()}DS.q="";doPick(c)}
/* ===== Series mode (Champ select free play): Bo1 / Bo3 / Bo5, Fearless or standard, ends at 1 / 2 / 3 wins ===== */
const sWins=id=>DS.series?DS.series.games.filter(g=>g.winner===id).length:0;
const sNeed=()=>Math.ceil(DS.series.bo/2);
function seriesDone(){return !!DS.series&&(sWins(DS.series.me)>=sNeed()||sWins(DS.series.opp)>=sNeed())}
function seriesLocked(){const S=DS.series;return S&&S.fearless?S.games.flatMap(g=>g.steps.filter(x=>x[1]==="pick").map(x=>x[2])):[]}
function startSeries(){clearTimeout(aiTimer);const bo=+DS.sbo||1;DS.series={bo,fearless:bo>1&&DS.sfear==="yes",me:DS.me,opp:DS.opp,side0:DS.side,ai:DS.ai,games:[]};seriesGame()}
function seriesGame(){const S=DS.series,last=S.games[S.games.length-1];
  DS.side=last?(last.winner===S.me?"red":"blue"):S.side0;   /* after game 1 the loser takes blue */
  Object.assign(DS,{me:S.me,opp:S.opp,fp:"blue",fmt:S.fearless?"fearless":"bo1",locked:seriesLocked(),steps:[],sim:null,game:S.games.length+1,fresh:-1,q:"",roleF:"ALL",ai:S.ai,showUsed:false});
  renderDraft();queueAI();window.scrollTo({top:document.getElementById("v-draft").offsetTop-60,behavior:"smooth"})}
function playSeriesGame(){if(seriesDone())return;runGame();const g=DS.sim.g,rec=pack(g),pct=Math.round((g.winner==="blue"?DS.sim.bwin:1-DS.sim.bwin)*100);
  Object.assign(rec,{dr:{...g.dr},ba:{...g.ba},g15:(g.gl.find(x=>x[0]>=14)||[0,0])[1],pct,up:pct<25,odds:{blue:DS.sim.bwin}});DS.series.games.push(rec)}
/* per-player series totals from the stored games */
function seriesPlayers(id,S){S=S||{games:DS.series.games};const t=team(id);return ROLES.map((r,i)=>{const o={pl:t.p[i],r,g:0,k:0,d:0,a:0,rt:0,pts:0,champs:[]};
  S.games.forEach(gm=>{const sd=gm.blue===id?"blue":"red",p=gm.ps[sd][r];o.g++;o.k+=p.k;o.d+=p.d;o.a+=p.a;o.rt+=p.rt;o.champs.push([p.c,gm.winner===id]);if(gm.pog.team===id&&gm.pog.r===r)o.pts+=100});
  o.avg=o.g?o.rt/o.g:0;o.kda=(o.k+o.a)/Math.max(1,o.d);return o})}
function seriesSetup(){
  const opts=sel=>TEAMS.map(t=>`<option value="${t.id}"${t.id===sel?" selected":""}>${esc(t.name)}</option>`).join("");
  const seg=(name,val,pairs)=>`<div class="seg" role="group" aria-label="${name}">${pairs.map(([k,l])=>`<button data-set="${name}" data-val="${k}" aria-pressed="${val===k}">${l}</button>`).join("")}</div>`;
  const bo=+DS.sbo;
  return `<div class="panel ssetup"><div><span class="eyebrow">Start a series</span><h2>Champ select</h2><p class="notes" style="margin:4px 0 0">Draft a Bo1, Bo3 or Bo5 against any Worlds team. Competitive draft order; blue picks first. The series ends as soon as a team reaches ${bo===1?"1 win":bo===3?"2 wins":"3 wins"}.</p></div>
    <div class="sopts2"><label class="field"><span class="flabel">Your team</span><select id="dMe">${opts(DS.me)}</select></label><label class="field"><span class="flabel">Opponent</span><select id="dOpp">${opts(DS.opp)}</select></label></div>
    <div class="sopts3">
      <div class="field"><span class="flabel">Format</span>${seg("sbo",DS.sbo,[["1","Bo1"],["3","Bo3"],["5","Bo5"]])}<span class="notes small">Series ends at ${Math.ceil(bo/2)} win${bo>1?"s":""}.</span></div>
      <div class="field"><span class="flabel">Draft style</span>${bo>1?seg("sfear",DS.sfear,[["yes","Fearless"],["no","Standard"]]):`<span class="notes small" style="padding:8px 0">Single game — no Fearless locks.</span>`}${bo>1?`<span class="notes small">Fearless: picks lock for the rest of the series; bans don't.</span>`:""}</div>
      <div class="field"><span class="flabel">Game 1 side</span>${seg("side",DS.side,[["blue","You: blue"],["red","You: red"]])}<span class="notes small">After game 1 the loser picks side (takes blue).</span></div>
    </div>
    <div class="sconfirm"><b>${DS.ai?`The AI will draft for ${esc(team(DS.opp).name)}`:`You'll draft both sides`}</b>
      <label class="tog"><input type="checkbox" id="dAI"${DS.ai?" checked":""}> AI drafts the opponent (2 seconds per pick or ban) — on by default</label>
      <span class="notes small">Turn it off to draft both sides yourself. It can't be changed mid-series.</span>
      <div class="ctrls"><button class="btn primary" data-act="sstart">Start ${bo===1?"Bo1 game":"Bo"+bo+" series"}</button></div></div></div>`}
/* Series panel for any series: champ select (ctx "cs") or a tournament match (ctx "tour").
   S = {bo, fearless, a, b, games, ctx, mid} — games are stored game records (pack()). */
function seriesPanel(S){
  if(!S){if(!DS.series)return"";const D=DS.series;S={bo:D.bo,fearless:D.fearless,a:D.me,b:D.opp,games:D.games,ctx:"cs"}}
  if(!S.games.length)return"";
  const A=S.a,B=S.b,W=id=>S.games.filter(g=>g.winner===id).length,wa=W(A),wb=W(B),need=Math.ceil(S.bo/2),done=wa>=need||wb>=need;
  const locked=S.fearless?S.games.flatMap(g=>g.steps.filter(x=>x[1]==="pick").map(x=>x[2])):[];
  const pips=Array.from({length:S.bo},(_,i)=>{const gm=S.games[i];return `<i class="${gm?(gm.winner===A?"pa":"pb"):""}"></i>`}).join("");
  const mm=gm=>`${gm.time}:${String(gm.sec).padStart(2,"0")}`;
  const gamesT=`<div class="tscroll"><table class="tt full sgt"><colgroup><col style="width:6%"><col style="width:8%"><col style="width:10%"><col style="width:22%"><col style="width:22%"><col style="width:23%"><col style="width:9%"></colgroup><thead><tr><th>Game</th><th>Time</th><th>Winner</th><th>${esc(A)} picks</th><th>${esc(B)} picks</th><th>Player of the Game</th><th>Note</th></tr></thead><tbody>${S.games.map((gm,i)=>{const pk=id=>{const sd=gm.blue===id?"blue":"red";return ROLES.map(r=>`<span class="hov" data-tc="${esc(gm.ps[sd][r].c)}">${icon(gm.ps[sd][r].c,24)}</span>`).join("")};
    return `<tr style="--tc:${teamCol(gm.winner)}"><td class="gno">G${i+1}</td><td>${mm(gm)}</td><td class="res">${esc(gm.winner)}</td><td><span class="comp">${pk(A)}</span></td><td><span class="comp">${pk(B)}</span></td><td class="pogc">${esc(gm.pog.n)} (${esc(gm.pog.c)}) ${(+gm.pog.rt).toFixed(1)}</td><td>${gm.up?`<span class="upset">Upset</span>`:gm.pog.team!==gm.winner?`<span class="notes small">POG from loss</span>`:"–"}</td></tr>`}).join("")}</tbody></table></div>`;
  const ptable=id=>{const ps=seriesPlayers(id,S),w=W(id);return `<div class="sside" style="--sc:${teamCol(id)}"><h3>${teamTag(id)} ${esc(team(id).name)} <small>· ${w} win${w===1?"":"s"}</small></h3><div class="tscroll"><table class="tt full"><thead><tr><th>Player</th><th>Champions</th><th>K/D/A</th><th>KDA</th><th>Avg rating</th><th>POG pts</th></tr></thead><tbody>${ps.map((o,i)=>`<tr><td><span class="hov" data-tp="${id}|${i}" tabindex="0"><b>${esc(o.pl.n)}</b></span> <span class="notes">${o.r}</span></td><td><span class="comp">${o.champs.map(([c,won])=>`<span class="hov${won?"":" lost"}" data-tc="${esc(c)}">${icon(c,24)}</span>`).join("")}</span></td><td class="num">${o.k}/${o.d}/${o.a}</td><td class="num">${o.kda.toFixed(1)}</td><td class="num">${o.avg.toFixed(1)}</td><td class="num pts">${o.pts?o.pts:"–"}</td></tr>`).join("")}</tbody></table></div></div>`};
  const all=[...seriesPlayers(A,S).map(o=>({...o,id:A})),...seriesPlayers(B,S).map(o=>({...o,id:B}))].sort((x,y)=>y.pts-x.pts||y.avg-x.avg);
  const race=all.slice(0,3),maxP=Math.max(100,race[0].pts);
  const sum=f=>S.games.reduce((t,gm)=>t+f(gm),0),sd=(gm,id)=>gm.blue===id?"blue":"red",has=k=>S.games.every(gm=>gm[k]!=null);
  const kills=id=>sum(gm=>gm.kills[sd(gm,id)]),drs=id=>sum(gm=>gm.dr[sd(gm,id)]),bas=id=>sum(gm=>gm.ba[sd(gm,id)]);
  const longest=S.games.reduce((m,gm,i)=>(gm.time*60+gm.sec)>(m.t||0)?{t:gm.time*60+gm.sec,i,gm}:m,{});
  let best=null;S.games.forEach(gm=>["blue","red"].forEach(x=>ROLES.forEach((r,ri)=>{const p=gm.ps[x][r];if(!best||p.rt>best.p.rt)best={p,id:x==="blue"?gm.blue:gm.red,ri}})));
  const ups=S.games.map((gm,i)=>gm.up?`G${i+1} · ${gm.winner} won at ${gm.pct}%`:null).filter(Boolean);
  const facts=[["Kills",`${A} ${kills(A)} – ${kills(B)} ${B}`]];
  if(has("g15")){const g15=sum(gm=>(gm.blue===A?1:-1)*gm.g15)/S.games.length;facts.push(["Gold at 15 (avg)",Math.abs(g15)<300?"even":`${g15>0?A:B} +${(Math.abs(g15)/1000).toFixed(1)}k`])}
  if(has("dr"))facts.push(["Dragons",`${drs(A)} – ${drs(B)}`],["Barons",`${bas(A)} – ${bas(B)}`]);
  facts.push(["Longest game",`G${longest.i+1} · ${mm(longest.gm)}`],["Best single game",`${team(best.id).p[best.ri].n} ${best.p.rt.toFixed(1)} (${best.p.c})`]);
  if(S.ctx==="cs"||ups.length)facts.push(["Upsets",ups.length?ups.join(" · "):"none"]);
  const winner=done?(wa>wb?A:B):null,mvp=done?all.filter(o=>o.id===winner).sort((x,y)=>y.pts-x.pts||y.avg-x.avg)[0]:null;
  const lastW=S.games[S.games.length-1].winner,nextSide=lastW===A?B:A;
  const endBtns=S.ctx==="cs"?`<button class="btn" data-act="srematch">Rematch (same settings)</button><button class="btn primary" data-act="snew">New series</button>`:`<button class="btn primary" data-ta="back">Back to the schedule</button>`;
  let nextBtn="";
  if(!done){if(S.ctx==="cs")nextBtn=DS.sim?`<button class="btn primary" data-act="snext">Draft game ${S.games.length+1}</button>`:"";
    else{const m=typeof M==="function"?M(S.mid):null,ctrl=m&&ctrlOf(m);nextBtn=DS.tour&&DS.tour.mid===S.mid?"":ctrl?`<button class="btn primary" data-ta="draft" data-m="${S.mid}">Draft game ${S.games.length+1} as ${esc(ctrl)}</button>`:`<button class="btn" data-ta="sim" data-m="${S.mid}">Sim the rest</button>`}}
  return `<div class="panel spanel">
    ${done?`<div class="send"><span class="eyebrow">Series over</span><h3>${esc(team(winner).name)} win the series ${Math.max(wa,wb)}–${Math.min(wa,wb)}</h3><div class="notes">Series MVP: <b>${esc(mvp.pl.n)}</b> · ${mvp.pts} POG points · KDA ${mvp.kda.toFixed(1)} · ${[...new Set(mvp.champs.map(c=>c[0]))].map(esc).join(", ")}</div><div class="ctrls" style="justify-content:center">${endBtns}</div></div>`:""}
    <div class="sbug"><div class="steam">${teamTag(A)} ${esc(team(A).name)}</div><div class="sscore"><b>${wa} – ${wb}</b><small>${S.bo===1?"Bo1":`Bo${S.bo} · first to ${need}`}${S.fearless?" · Fearless":""}</small><div class="pips" style="--pa:${teamCol(A)};--pb:${teamCol(B)}">${pips}</div></div><div class="steam r">${esc(team(B).name)} ${teamTag(B)}</div></div>
    ${gamesT}
    ${done?"":`<div class="snext"><div><b>Game ${S.games.length+1} next</b> <span class="notes">· ${esc(nextSide)} lost game ${S.games.length}, so they take blue side${S.fearless?` · ${locked.length} champions locked (Fearless)`:""}</span></div>${nextBtn}</div>`}
    <div class="stwo">${ptable(A)}${ptable(B)}</div>
    <div class="stwo"><div class="srace"><span class="eyebrow">Series MVP race · POG points</span>${race.map((o,i)=>`<div class="rc"><span class="notes">#${i+1}</span><span>${teamTag(o.id)} <b>${esc(o.pl.n)}</b></span><span class="rbar"><b style="width:${o.pts/maxP*100}%"></b></span><span class="num">${o.pts} <small>· ${o.avg.toFixed(1)}</small></span></div>`).join("")}<span class="notes small">100 points per Player of the Game; ties go to the higher average rating. The Series MVP comes from the winning team.</span></div>
      <div><span class="eyebrow">Series so far</span><div class="sfacts">${facts.map(([k,v])=>`<span><b>${k}</b>${esc(v)}</span>`).join("")}</div></div></div>
  </div>`}

function renderDraft(){
  const v=document.getElementById("v-draft");if(!v)return;
  if(!DS.tour&&!DS.series){v.innerHTML=seriesSetup();tip.hidden=true;return}
  const i=DS.steps.length,done=i>=20;
  const cur=done?null:SEQ[i],actor=done?null:actorId(cur[0]);
  const tk=taken();
  const blueId=idOnSide("blue"),redId=idOnSide("red");
  const opts=sel=>TEAMS.map(t=>`<option value="${t.id}"${t.id===sel?" selected":""}>${esc(t.name)}</option>`).join("");
  const seg=(name,val,pairs)=>`<div class="seg" role="group" aria-label="${name}">${pairs.map(([k,l])=>`<button data-set="${name}" data-val="${k}" aria-pressed="${val===k}">${l}</button>`).join("")}</div>`;
  const rs=done?[]:recs();
  const usedN=POOL.filter(c=>tk.has(c)).length,typedM=DS.q.trim()?bestMatch(DS.q):null;
  const grid=POOL.filter(c=>(DS.showUsed||!tk.has(c))&&(DS.roleF==="ALL"||ROLEMAP[c].has(DS.roleF))&&(!DS.q||c.toLowerCase().includes(DS.q.toLowerCase())));
  /* order bar: 20 fixed-size tiles in draft order, side colour of who acts, B(an)/P(ick) + step number; a done step shows its champion */
  const track=SEQ.map((x,j)=>{const sd=actorId(x[0])===DS.me?DS.side:sideOf(DS.opp),s=DS.steps[j],L=x[1]==="ban"?"B":"P";return `<span class="tk ${sd} ${x[1]==="ban"?"kb":"kp"} ${j<i?"done":""} ${j===i?"now":""}" title="${stepLabel(j)}${s?": "+esc(s.c):""}"><span class="tkb">${s?icon(s.c,28):L}</span><small>${L}${j+1}</small></span>`}).join("");
  const aiWaiting=DS.ai&&!done&&actor!==DS.me;
  v.innerHTML=`<div class="panel" style="display:grid;gap:14px">
    <div><h2>Champ select</h2><p class="notes" style="margin:4px 0 0">Competitive draft order. Blue side picks first as standard; switch only if a team used First Selection to take red side with first pick.</p></div>
    ${DS.tour?tourDraftHeader():""}
    ${!DS.tour&&DS.series?`<div class="ctrls"><span class="notes"><b>Game ${DS.series.games.length+(DS.sim?0:1)}</b> of ${DS.series.bo===1?"a Bo1":"a Bo"+DS.series.bo} · ${esc(DS.me)} on ${DS.side} · ${DS.series.ai?"AI drafts "+esc(DS.opp):"you draft both sides"}${DS.series.fearless?` · ${DS.locked.length} champions locked (Fearless)`:""}</span>${DS.sim?"":`<button class="btn" data-act="undo"${i?"":" disabled"}>Undo</button><button class="btn" data-act="reset">Restart this draft</button>`}<button class="btn" data-act="snew">New series</button></div>`:""}
    ${DS.tour&&!done?`<div class="ctrls"><button class="btn" data-act="undo"${i?"":" disabled"}>Undo</button></div>`:""}
    ${!DS.tour?seriesPanel():(()=>{const m=M(DS.tour.mid);return m&&m.bo>1?seriesPanel({bo:m.bo,fearless:true,a:m.a,b:m.b,games:m.games,ctx:"tour",mid:m.id}):""})()}
    <div class="track" aria-label="Draft progress">${track}</div>
    <div class="turn ${done?"":(actor===DS.me?DS.side:sideOf(DS.opp))}" aria-live="polite">${done?`<span class="big">Draft complete</span><span class="notes">Draft review below.</span>`:`<span class="big">${stepLabel(i)} · <b>${esc(team(actor).name)}</b> ${cur[1]==="ban"?"bans":"picks"}${actor===DS.me?" (you)":aiWaiting?" (AI thinking…)":" (opponent)"}</span><span class="notes">Step ${i+1} of 20 · ${stepTip()}</span>`}</div>
    <div class="board pb">${teamPanel(blueId)}${teamPanel(redId)}</div>
    ${nextBest()}
    ${done?analysis():`<div><div class="eyebrow">${actor===DS.me?"Suggested for you":"Likely for "+esc(team(actor).id)}</div><div class="recs">${rs.map((r,j)=>`<button class="rec ${j===0?"top":""}" data-c="${esc(r.c)}"${aiWaiting?" disabled":""}><span class="cpt" data-tc="${esc(r.c)}" data-side="1">${icon(r.c,40)}</span><b>${esc(r.c)}</b>${r.roles?`<small>${r.roles.join("/")}</small>`:""}<span class="whys">${r.why.map(fmtWhy).join(`<i class="sep"> · </i>`)}</span></button>`).join("")||'<span class="notes">No scored options left. Pick from the pool.</span>'}</div></div>
    <div><div class="ctrls"><div class="seg">${[["ALL","All"],...ROLES.map(r=>[r,r])].map(([k,l])=>`<button data-set="roleF" data-val="${k}" aria-pressed="${DS.roleF===k}">${l}</button>`).join("")}</div><input id="dQ" type="search" placeholder="Search champions (Enter picks the best match)" value="${esc(DS.q)}" aria-label="Search champions"><button class="btn" data-act="custom"${typedM?"":" disabled"}>${DS.q.trim()?(typedM?"Pick "+esc(typedM):"No champion matches"):"Pick best match"}</button><label class="tog"><input type="checkbox" id="dUsed"${DS.showUsed?" checked":""}> Show banned/picked${DS.fmt==="fearless"?"/locked":""} (${usedN})</label></div>
    <div class="cgrid">${grid.map(c=>`<button class="cbtn ${metaOf(c)[0]}" data-c="${esc(c)}"${tk.has(c)||aiWaiting?" disabled":""}><span class="cpt" data-tc="${esc(c)}" data-side="1">${icon(c,40)}</span><span>${esc(c)}</span></button>`).join("")}</div></div>`}
    <p class="notes" style="font-size:12px;margin:0">Hover a player for their pool and lane risk, a team name for its comp, or a champion for its pro card. Suggestions score blended pro presence and win rate (26.20 + 26.16–26.20, NerfPlz), flex value in phase 1, comfort picks (mid.gg, Sheep Esports), pair lift (metabot.gg, METAsrc) and denying the other side's comfort picks. Draft order and First Selection: <a href="https://www.sheepesports.com/en/articles/new-draft-rules-have-been-introduced-with-first-selection-system-aimed-at-rebalancing-the-sides/en" target="_blank" rel="noopener">Sheep Esports</a>, <a href="https://esports.gg/news/league-of-legends/first-selection-explained/" target="_blank" rel="noopener">esports.gg</a>; first vs last pick: <a href="https://nerdbot.com/2026/09/16/blue-side-vs-red-side-what-the-draft-order-is-worth/" target="_blank" rel="noopener">Nerdbot</a>. Counters: <a href="https://www.metasrc.com/lol/champions/vi/counters" target="_blank" rel="noopener">METAsrc counter pages</a> (ranked solo queue, patches 26.17–26.20) for 37 meta champions.</p>
  </div>`;
  tip.hidden=true;
}
document.addEventListener("click",e=>{
  const v=document.getElementById("v-draft");if(!v||!v.contains(e.target))return;
  const b=e.target.closest("button");if(!b||b.disabled)return;
  if(b.dataset.c){doPick(b.dataset.c);return}
  if(b.dataset.set){DS[b.dataset.set]=b.dataset.val;if(b.dataset.set!=="roleF"&&!DS.series){DS.steps=[];DS.sim=null}renderDraft();if(DS.series)queueAI();return}
  const a=b.dataset.act;
  if(a==="undo"){clearTimeout(aiTimer);DS.steps.pop();if(DS.ai)while(DS.steps.length&&actorId(SEQ[DS.steps.length][0])!==DS.me)DS.steps.pop();DS.fresh=-1;DS.sim=null;renderDraft();queueAI()}
  else if(a==="reset"){clearTimeout(aiTimer);DS.steps=[];DS.sim=null;DS.fresh=-1;renderDraft();queueAI()}
  else if(a==="sstart")startSeries();
  else if(a==="splay"){b.textContent="Simulating…";setTimeout(()=>{playSeriesGame();renderDraft();const s=document.querySelector(".sim");if(s)s.scrollIntoView({behavior:"smooth",block:"start"})},30)}
  else if(a==="snext"){if(!seriesDone())seriesGame()}
  else if(a==="sview"){const p=document.querySelector(".spanel");if(p)p.scrollIntoView({behavior:"smooth",block:"start"})}
  else if(a==="snew"){clearTimeout(aiTimer);if(DS.series)DS.side=DS.series.side0;DS.series=null;DS.steps=[];DS.sim=null;DS.locked=[];DS.fmt="bo1";DS.ai=true;renderDraft()}
  else if(a==="srematch"){const S=DS.series;Object.assign(DS,{me:S.me,opp:S.opp,side:S.side0,ai:S.ai,sbo:String(S.bo),sfear:S.fearless?"yes":"no"});startSeries()}
  else if(a==="custom")pickTyped();
});
document.addEventListener("change",e=>{
  const t=e.target;
  if(t.id==="dMe"||t.id==="dOpp"){const k=t.id==="dMe"?"me":"opp";DS[k]=t.value;if(DS.me===DS.opp){const o=TEAMS.find(x=>x.id!==DS.me);DS[k==="me"?"opp":"me"]=o.id}DS.steps=[];DS.game=1;DS.locked=[];DS.sim=null;renderDraft();queueAI()}
  if(t.id==="dAI"){DS.ai=t.checked;renderDraft();queueAI()}
  if(t.id==="dUsed"){DS.showUsed=t.checked;renderDraft()}
  if(t.dataset&&t.dataset.rs!=null)setPickRole(+t.dataset.rs,t.value);
});
/* move a picked champion to another role; a team-mate already in that role swaps into the old one */
function setPickRole(si,r){const s=DS.steps[si];if(!s||s.k!=="pick"||s.r===r)return;const other=DS.steps.find(x=>x.k==="pick"&&x.t===s.t&&x.r===r);if(other)other.r=s.r;s.r=r;DS.sim=null;renderDraft()}
document.addEventListener("keydown",e=>{if(e.target.id==="dQ"&&e.key==="Enter"){e.preventDefault();const i=DS.steps.length;if(i<20&&!(DS.ai&&actorId(SEQ[i][0])!==DS.me))pickTyped()}});
document.addEventListener("input",e=>{if(e.target.id==="dQ"){DS.q=e.target.value;const pos=e.target.selectionStart;renderDraft();const q=document.getElementById("dQ");if(q){q.focus();try{q.setSelectionRange(pos,pos)}catch(_){}}}});

let start="tour";try{const hsh=(location.hash||"").slice(1);if(hsh)start=hsh}catch(e){}
if(typeof loadRun==="function")loadRun();
show(start);

