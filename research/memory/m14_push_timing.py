"""Timing fixes step 1, push chain (26 Nov 2026 AEST; Luke: "fix the push chain now"). With real gaps on the event clock (v54) the
sim reaches the Nexus a median 24 s after a won fight's last kill (real 13 s), so more Nexus tries miss the losers' respawn and games
run long. This measures, on real games, how one team's structures follow its won fight, so the sim (m14_push_sim.js reads the
app sim the same way) can be compared part by part:
  fights: kills under 20 s apart (as everywhere); the winner takes more kills (ties left out); the push = the winner's structures
  (towers, inhibitors, Nexus; plates are not events) from the fight's start until the next fight starts or 120 s after the fight's
  last kill, whichever is first.
  measured: structures per push; first structure from the fight's start and from its last kill (negative = before it); gaps
  between the push's consecutive structures (base structures only, and all); the Nexus from the push's previous structure and
  from the last kill; share of pushes whose first structure falls before the fight's last kill.
Games: gol.gg timelines before config.SPLIT (training, as the memory tables) and all 640 (for reference).
App tables (games before 10 Nov, as the other app tables): first structure from the fight's last kill and the Nexus from the push's
previous structure, 21 quantiles each, written as one block at the end of js/sim-tables.js (SIM_TABLES.push, between markers;
nothing else in that file is touched; re-running replaces it). The sim's numbers (m14_push_sim.js) are added to the result file by hand.
Output: research/model/memory/m14_push_timing.json.
usage (repo root): python -I research/memory/m14_push_timing.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json, re
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run

OUT = config.MODEL_DIR / "memory"
STR = {"tower", "inhib", "nexus"}
QS = [.1, .25, .5, .75, .9]
r3 = lambda x: round(float(x), 3)
qq = lambda a: [round(float(v), 1) for v in np.quantile(a, QS)] if len(a) else None

def is_base(ty, det):
    d = str(det)
    return ty in ("inhib", "nexus") or (ty == "tower" and ("NEXUS" in d or d.startswith("T3")))

def pushes(ev, gids):
    E = ev[ev.gid.isin(gids)].sort_values(["gid", "t"]); P = []
    for g, d in E.groupby("gid"):
        k = d[d.type == "kill"]; s = d[d.type.isin(STR)]
        if not len(k): continue
        kt, ks = k.t.values.astype(float), k.side.values
        grp = np.cumsum(np.r_[True, np.diff(kt) > 20]); F = []
        for gi in np.unique(grp):
            m = grp == gi; nb, nr = int((ks[m] == "blue").sum()), int((ks[m] == "red").sum())
            F.append((kt[m].min(), kt[m].max(), "blue" if nb > nr else "red" if nr > nb else None, nb + nr))
        for i, (t0, t1, w, n) in enumerate(F):
            if w is None: continue
            end = min(F[i + 1][0] if i + 1 < len(F) else 1e9, t1 + 120)
            x = s[(s.side == w) & (s.t >= t0) & (s.t < end)]
            P.append({"t0": t0, "t1": t1, "kills": n, "st": x.t.values.astype(float).tolist(), "ty": x.type.tolist(),
                      "base": [is_base(a, b) for a, b in zip(x.type, x.detail)]})
    return P

def summary(P):
    with_s = [p for p in P if p["st"]]
    first0 = [p["st"][0] - p["t0"] for p in with_s]; first1 = [p["st"][0] - p["t1"] for p in with_s]
    gaps_all, gaps_base, nx_prev, nx_kill = [], [], [], []
    for p in with_s:
        st, ty, b = p["st"], p["ty"], p["base"]
        for j in range(1, len(st)):
            if ty[j] == "nexus": nx_prev.append(st[j] - st[j - 1]); continue
            gaps_all.append(st[j] - st[j - 1])
            if b[j] and b[j - 1]: gaps_base.append(st[j] - st[j - 1])
        if "nexus" in ty: nx_kill.append(st[ty.index("nexus")] - p["t1"])
    nst = np.array([len(p["st"]) for p in P])
    return {"won fights": len(P), "with a structure": len(with_s), "structures per won fight (share 0, 1, 2, 3, 4, 5+)": [r3((nst == i).mean()) for i in range(5)] + [r3((nst >= 5).mean())],
            "first structure from the fight's start s (10/25/50/75/90%)": qq(first0), "first structure from the fight's last kill s": qq(first1),
            "first structure before the fight's last kill": r3(np.mean(np.array(first1) < 0)) if first1 else None,
            "gap between the push's structures s (all, no Nexus)": qq(gaps_all), "gap between base structures s": qq(gaps_base),
            "Nexus from the push's previous structure s": qq(nx_prev), "Nexus from the fight's last kill s": qq(nx_kill), "pushes ending in the Nexus": len(nx_kill)}

def tables(P):
    """the app's push chain (Luke, 26 Nov: fix the push chain now): 21 quantiles of the first structure from the fight's last kill
    (negative = before it) and of the Nexus from the push's previous structure"""
    with_s = [p for p in P if p["st"]]
    first = [p["st"][0] - p["t1"] for p in with_s]
    # Luke, 26 Nov ("try the split"): pushes that start in the base start much sooner than pushes that start with an outer tower
    fb = [p["st"][0] - p["t1"] for p in with_s if p["base"][0]]; fo = [p["st"][0] - p["t1"] for p in with_s if not p["base"][0]]
    nxp = [p["st"][j] - p["st"][j - 1] for p in with_s for j in range(1, len(p["st"])) if p["ty"][j] == "nexus"]
    Q = np.linspace(0, 1, 21)
    qt = lambda a: [round(float(v), 1) for v in np.quantile(a, Q)]
    return {"first_q": qt(first), "first_base_q": qt(fb), "first_outer_q": qt(fo), "nexus_prev_q": qt(nxp),
            "n": {"pushes with a structure": len(first), "base first": len(fb), "outer tower first": len(fo), "Nexus after a structure of the push": len(nxp)}}

APP_CUT = "2026-11-10"
with Run("memory_push_timing", params={"fight_gap_s": 20, "push_until_s_after_last_kill": 120, "app_cut": APP_CUT}, inputs=[config.TL_MATCH, config.TL_EVENTS]) as run:
    tm, ev, _ = data.timelines()
    train = set(tm.gid[tm.day < config.SPLIT]); allg = set(tm.gid); appg = set(tm.gid[tm.day < APP_CUT])
    R = {"training games (before 1 Sep)": summary(pushes(ev, train)), "all 640 timelines": summary(pushes(ev, allg))}
    PT = tables(pushes(ev, appg)); PT = {"cutoff": APP_CUT, "source": f"research/memory/m14_push_timing.py, gol.gg timelines before {APP_CUT} ({len(appg)} games)", **PT}
    R["app tables"] = PT; R["training tables (before 1 Sep)"] = tables(pushes(ev, train))
    JS = config.ROOT / "js" / "sim-tables.js"
    START, END = "/* push chain tables: BUILT BY research/memory/m14_push_timing.py, never edit by hand */", "/* end push chain tables */"
    block = f"{START}\nwindow.SIM_TABLES.push = {json.dumps(PT, separators=(',', ':'))};\n{END}\n"
    js = JS.read_text(encoding="utf-8"); js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + block
    tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)
    run.result("training won fights", R["training games (before 1 Sep)"]["won fights"])
    run.save_json(OUT / "m14_push_timing.json", R)
    print(json.dumps({k: R[k] for k in ("app tables", "training tables (before 1 Sep)")}, indent=1))
