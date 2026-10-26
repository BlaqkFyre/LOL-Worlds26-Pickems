/* Champion icons (Riot Data Dragon square icons only) and team colour badges.
   ASSETS.icons is the single switch: set it to false and every icon becomes an
   initials tile, with no requests to Riot's CDN. No team or Riot logos are used. */
const ASSETS = {icons: true, ver: null, ids: {}, tags: {}};
const DD_KEY = "lolw26-dd";
/* Name → Data Dragon id for names that don't simply drop punctuation. Data Dragon's
   own champion list replaces this once it has loaded. */
const DD_FIX = {"Wukong":"MonkeyKing","Nunu & Willump":"Nunu","Renata Glasc":"Renata","Kai'Sa":"Kaisa","Kha'Zix":"Khazix","Cho'Gath":"Chogath",
  "Vel'Koz":"Velkoz","Bel'Veth":"Belveth","LeBlanc":"Leblanc","Kog'Maw":"KogMaw","Rek'Sai":"RekSai","K'Sante":"KSante","Dr. Mundo":"DrMundo"};
const ddId = c => ASSETS.ids[c] || DD_FIX[c] || String(c).replace(/[^A-Za-z]/g, "");
const initials = c => String(c).split(/[\s'.&]+/).filter(Boolean).map(w => w[0]).join("").slice(0, 2).toUpperCase();
function iconImg(c){
  if(!ASSETS.icons || !ASSETS.ver) return "";
  return `<img src="https://ddragon.leagueoflegends.com/cdn/${ASSETS.ver}/img/champion/${encodeURIComponent(ddId(c))}.png" alt="" loading="lazy" decoding="async" onerror="this.remove()">`;
}
/* icon(name, px): square tile with initials underneath; the image covers them when it loads */
function icon(c, s){ return `<span class="ico" data-ic="${esc(c)}"${s ? ` style="--s:${s}px"` : ""} aria-hidden="true"><b>${esc(initials(c))}</b>${iconImg(c)}</span>`; }
/* picked champions in champ select: Data Dragon's centred splash art (no version needed); same on/off switch */
const splashUrl = c => ASSETS.icons ? `https://ddragon.leagueoflegends.com/cdn/img/champion/centered/${encodeURIComponent(ddId(c))}_0.jpg` : "";
function patchIcons(){ if(!ASSETS.icons || !ASSETS.ver) return; document.querySelectorAll(".ico[data-ic]").forEach(el => { if(!el.querySelector("img")) el.insertAdjacentHTML("beforeend", iconImg(el.dataset.ic)); }); }
(function loadDD(){
  if(!ASSETS.icons) return;
  let cache = null; try{ cache = JSON.parse(localStorage.getItem(DD_KEY) || "null"); }catch(e){}
  if(cache && typeof cache.v === "string" && /^[\d.]+$/.test(cache.v)){ ASSETS.ver = cache.v; ASSETS.ids = cache.ids || {}; ASSETS.tags = cache.tags || {}; }
  if(cache && Date.now() - (cache.t || 0) < 3 * 864e5) return;
  fetch("https://ddragon.leagueoflegends.com/api/versions.json").then(r => r.json()).then(v => {
    const ver = v && v[0]; if(typeof ver !== "string" || !/^[\d.]+$/.test(ver)) return;
    ASSETS.ver = ver; patchIcons();
    return fetch(`https://ddragon.leagueoflegends.com/cdn/${ver}/data/en_US/champion.json`).then(r => r.json()).then(j => {
      const ids = {}, tags = {};
      Object.values(j.data || {}).forEach(x => { if(x && x.name && x.id){ ids[x.name] = x.id; tags[x.name] = (x.tags || []).slice(0, 2); } });
      ASSETS.ids = ids; ASSETS.tags = tags;
      try{ localStorage.setItem(DD_KEY, JSON.stringify({v: ver, t: Date.now(), ids, tags})); }catch(e){}
    });
  }).catch(() => {});
})();

/* Team colour badges (colours only, no logos) */
const TEAM_COL = {GEN:"#b8860b", HLE:"#f97316", T1:"#e2012d", DK:"#0d9488", BLG:"#ec4899", AL:"#65a30d", TES:"#c2410c", IG:"#64748b",
  G2:"#9f1239", KC:"#0ea5e9", MKOI:"#7e22ce", TL:"#1e40af", CFO:"#d97706", TSW:"#dc2626", LYON:"#1d4ed8", LOS:"#16a34a"};
const teamCol = id => TEAM_COL[id] || "#6b7280";

/* Region badges: styled like the team badge, in the region's colour, with the team's seed from its league
   (e.g. "#1" in LCK colour; the region name shows on hover). Colours are deep enough for white text and kept apart from the team badge colours. */
const REGION_COL = {LCK:"#4f46e5", LPL:"#be123c", LEC:"#0f766e", LCS:"#475569", LCP:"#b45309", CBLOL:"#15803d"};
const REGION_NAME = {LCK:"LCK (Korea)", LPL:"LPL (China)", LEC:"LEC (Europe)", LCS:"LCS (North America)", LCP:"LCP (Pacific)", CBLOL:"CBLOL (Brazil)"};
const teamOf = id => (typeof TEAMS !== "undefined") && TEAMS.find(x => x.id === id);
const regionOf = id => { const t = teamOf(id); return t ? String(t.reg).split(/[\s·]/)[0] : ""; };
const seedOf = id => { const t = teamOf(id), m = t && String(t.reg).match(/#(\d+)/); return m ? +m[1] : 0; };
function regDot(id){
  const r = regionOf(id); if(!r) return "";
  const n = seedOf(id), lbl = `${REGION_NAME[r] || r}${n ? " seed #" + n : ""}`;
  return `<span class="rtag" style="--rc:${REGION_COL[r] || "#555"}" title="${esc(lbl)}" aria-label="${esc(lbl)}">${n ? "#" + n : esc(r)}</span>`;
}
function regionKey(){ return `<span class="rkey">${Object.keys(REGION_COL).map(r => `<span class="rtag" style="--rc:${REGION_COL[r]}" title="${esc(REGION_NAME[r])}">${r}</span>`).join("")}</span>`; }
