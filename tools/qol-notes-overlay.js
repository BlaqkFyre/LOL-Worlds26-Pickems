/* Notes overlay for display review sessions (see "Notes sessions" in CLAUDE.md). Not part of the app and never loaded by
   index.html: Claude pastes it into a browser-pane tab on the local server. Note mode outlines the element under the pointer;
   a click opens a note box. Notes are saved in localStorage "qol-review-notes" with the page, theme, Worlds mode, screen size,
   the element's text and a CSS path, so each note can be traced to code. */
(() => {
  if (window.__qolNotes) return "already on";
  const KEY = "qol-review-notes", Z = 2147483000;
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; } };
  const save = a => { try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {} };
  const css = document.createElement("style");
  css.textContent = `#qn-bar,#qn-box,#qn-list{position:fixed;z-index:${Z};font:13px/1.4 system-ui,sans-serif;color:#111;background:#fff;border:1px solid #888;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.25)}
#qn-bar{right:12px;bottom:12px;display:flex;gap:6px;padding:6px;align-items:center}
#qn-bar button,#qn-box button,#qn-list button{font:inherit;padding:4px 10px;border:1px solid #888;border-radius:6px;background:#f4f4f4;color:#111;cursor:pointer}
#qn-bar button.on{background:#ffd54a;border-color:#a77d00}
#qn-box{width:290px;padding:8px}#qn-box textarea{width:100%;box-sizing:border-box;height:80px;font:inherit;color:#111;background:#fff;border:1px solid #888;border-radius:6px;padding:4px}
#qn-box .what{color:#555;font-size:12px;margin-bottom:4px;max-height:36px;overflow:hidden}
#qn-list{right:12px;bottom:56px;width:320px;max-height:50vh;overflow:auto;padding:8px}
#qn-list .it{border-top:1px solid #ddd;padding:6px 0}#qn-list .it:first-child{border-top:0}
.qn-hover{outline:2px dashed #e0a800!important;outline-offset:1px!important}
.qn-mark{outline:2px solid #e05a00!important;outline-offset:1px!important}`;
  document.head.appendChild(css);
  const bar = document.createElement("div"); bar.id = "qn-bar";
  bar.innerHTML = `<span id="qn-w" style="color:#555;padding:0 4px"></span><button id="qn-mode">Note mode: off</button><button id="qn-show">Notes (0)</button>`;
  document.body.appendChild(bar);
  /* live width: the app's phone layout starts at 640 px and below */
  const showW = () => { bar.querySelector("#qn-w").textContent = `${innerWidth} px · ${innerWidth <= 640 ? "phone" : "desktop"}`; };
  showW(); addEventListener("resize", showW);
  let on = false, hov = null, box = null, list = null;
  const count = () => { bar.querySelector("#qn-show").textContent = `Notes (${load().length})`; };
  const ours = el => el && el.closest && el.closest("#qn-bar,#qn-box,#qn-list");
  const path = el => { const p = []; while (el && el.nodeType === 1 && el !== document.body) { let s = el.tagName.toLowerCase();
      if (el.id) { p.unshift(s + "#" + el.id); break; } const c = [...el.classList].filter(x => !x.startsWith("qn-")).slice(0, 2); if (c.length) s += "." + c.join(".");
      const sib = el.parentElement ? [...el.parentElement.children].filter(x => x.tagName === el.tagName) : []; if (sib.length > 1) s += `:nth-of-type(${sib.indexOf(el) + 1})`;
      p.unshift(s); el = el.parentElement; } return p.join(" > "); };
  const ctx = () => ({ view: location.hash || "#", theme: localStorage.getItem("lolw26-theme"), worlds: localStorage.getItem("lolw26-worlds"),
    width: innerWidth, height: innerHeight, scrollY: Math.round(scrollY) });
  const closeBox = () => { if (box) { box.remove(); box = null; } document.querySelectorAll(".qn-mark").forEach(x => x.classList.remove("qn-mark")); };
  function openBox(el, x, y) {
    closeBox(); el.classList.add("qn-mark");
    const r = el.getBoundingClientRect(), txt = (el.innerText || el.getAttribute("aria-label") || el.tagName).trim().replace(/\s+/g, " ").slice(0, 160);
    box = document.createElement("div"); box.id = "qn-box";
    box.style.left = Math.max(8, Math.min(innerWidth - 306, x + 10)) + "px"; box.style.top = Math.max(8, Math.min(innerHeight - 170, y + 10)) + "px";
    box.innerHTML = `<div class="what"></div><textarea placeholder="What should change here?"></textarea><div style="display:flex;gap:6px;justify-content:flex-end;margin-top:6px"><button data-a="x">Cancel</button><button data-a="s">Save note</button></div>`;
    box.querySelector(".what").textContent = txt || "(no text)";
    document.body.appendChild(box); const ta = box.querySelector("textarea"); ta.focus();
    const doSave = () => { const note = ta.value.trim(); if (!note) { ta.style.borderColor = "#d00"; ta.placeholder = "Type a note first"; return; }
      const a = load(); a.push({ n: a.length ? a[a.length - 1].n + 1 : 1, note, text: txt, sel: path(el), rect: [Math.round(r.left), Math.round(r.top + scrollY), Math.round(r.width), Math.round(r.height)], ...ctx(), at: new Date().toISOString() });
      save(a); count(); closeBox(); if (list) drawList(); };
    box.querySelector('[data-a="s"]').onclick = doSave; box.querySelector('[data-a="x"]').onclick = closeBox;
    ta.onkeydown = e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) doSave(); if (e.key === "Escape") closeBox(); };
  }
  function drawList() {
    if (!list) { list = document.createElement("div"); list.id = "qn-list"; document.body.appendChild(list); }
    const a = load();
    list.innerHTML = a.length ? "" : "<div>No notes yet. Turn on note mode and click part of the page.</div>";
    a.forEach(it => { const d = document.createElement("div"); d.className = "it";
      d.innerHTML = `<b>#${it.n}</b> <span style="color:#555">${it.view} · ${it.width}px</span><div class="nt"></div><div style="color:#777;font-size:12px" class="tx"></div><button style="margin-top:4px">Delete</button>`;
      d.querySelector(".nt").textContent = it.note; d.querySelector(".tx").textContent = "On: " + it.text.slice(0, 80);
      d.querySelector("button").onclick = () => { save(load().filter(x => x.n !== it.n)); count(); drawList(); }; list.appendChild(d); });
  }
  bar.querySelector("#qn-mode").onclick = e => { on = !on; e.currentTarget.textContent = "Note mode: " + (on ? "on" : "off"); e.currentTarget.classList.toggle("on", on); if (!on && hov) { hov.classList.remove("qn-hover"); hov = null; } };
  bar.querySelector("#qn-show").onclick = () => { if (list) { list.remove(); list = null; } else drawList(); };
  document.addEventListener("mouseover", e => { if (!on || ours(e.target)) return; if (hov) hov.classList.remove("qn-hover"); hov = e.target; hov.classList.add("qn-hover"); }, true);
  const block = e => { if (!on || ours(e.target)) return; e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); };
  ["mousedown", "mouseup", "pointerdown", "pointerup", "touchstart"].forEach(t => document.addEventListener(t, block, true));
  document.addEventListener("click", e => { if (!on || ours(e.target)) return; block(e); if (hov) hov.classList.remove("qn-hover"); openBox(e.target, e.clientX, e.clientY); }, true);
  count(); window.__qolNotes = true; return "notes overlay on";
})()
