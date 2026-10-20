/* Page chrome: light/dark toggle, Worlds mode themes, "how the ratings are made" popover. */
(function(){
  const root = document.documentElement;
  const get = k => { try{ return localStorage.getItem(k); }catch(e){ return null; } };
  const set = (k, v) => { try{ v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); }catch(e){} };
  const dark = () => root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;

  function syncThemeBtn(){
    const b = document.getElementById("themeBtn"); if(!b) return;
    const d = dark(), w = root.dataset.worlds;
    b.classList.toggle("is-dark", d);
    b.setAttribute("aria-label", d ? "Switch to light mode" : "Switch to dark mode");
    b.disabled = !!w;
    b.title = w ? "Worlds mode sets its own colours — turn it off to use light/dark" : "Light / dark mode";
  }
  function setWorlds(v){
    if(v && v !== "off") root.dataset.worlds = v; else delete root.dataset.worlds;
    set("lolw26-worlds", v && v !== "off" ? v : null);
    syncThemeBtn();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const tb = document.getElementById("themeBtn"), ws = document.getElementById("worldsSel");
    const ab = document.getElementById("aboutBtn"), pop = document.getElementById("aboutPop");
    if(ws) ws.value = root.dataset.worlds || "off";
    syncThemeBtn();
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncThemeBtn);
    tb && tb.addEventListener("click", () => { const next = dark() ? "light" : "dark"; root.dataset.theme = next; set("lolw26-theme", next); syncThemeBtn(); });
    ws && ws.addEventListener("change", () => setWorlds(ws.value));

    /* popover: opens on click/tap, or on hover with a pointer; closes on outside click or Esc */
    if(ab && pop){
      let pinned = false, t = null;
      const open = () => { clearTimeout(t); pop.hidden = false; ab.setAttribute("aria-expanded", "true"); };
      const close = () => { pop.hidden = true; pinned = false; ab.setAttribute("aria-expanded", "false"); };
      ab.addEventListener("click", e => { e.stopPropagation(); if(pinned){ close(); } else { pinned = true; open(); } });
      const wrap = ab.parentElement;
      wrap.addEventListener("mouseenter", () => { if(matchMedia("(hover: hover)").matches) open(); });
      wrap.addEventListener("mouseleave", () => { if(!pinned) t = setTimeout(close, 200); });
      document.addEventListener("click", e => { if(!pop.hidden && !wrap.contains(e.target)) close(); });
      document.addEventListener("keydown", e => { if(e.key === "Escape" && !pop.hidden){ close(); ab.focus(); } });
    }
  });
})();
