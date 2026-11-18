"""Game memory, app tables (18 Nov 2026 AEST; Luke OK'd death timers, structure rules, the Nexus after a won fight and spacing in the app).
Writes one block at the end of js/sim-tables.js, between the markers below, and nothing else in that file (the rest is built by
research/sim4/s4_tables.py and can't be rebuilt exactly since the Oracle's Elixir file was replaced). Re-running replaces the block.
  SIM_TABLES.memory = {
    level_xp:   XP needed for levels 1-18 (League wiki, Experience page, as research/local/sim4/spread/params/deathtimer.json)
    role_xp:    each role's average XP at 10, 15, 20 and 25 minutes, major-league games before 1 Sep (from that file)
    nexus_gap:  seconds from the last kill to the Nexus, 21 quantiles (gol.gg timelines, games before 1 Sep)
    struct_gap: seconds between one team's consecutive structures less than 60 s apart, 21 quantiles (same games)
    kill_gap:   seconds between consecutive kills less than 20 s apart (one fight), 21 quantiles (same games)
    base_gap:   the same as struct_gap for base structures only (T3 towers, inhibitors, nexus towers, the Nexus), used inside a base push }
The official death timer itself (base wait by level, time factor) and the structure respawns are game rules, kept in js/sim-engine.js.
usage (repo root): python -I research/memory/build_memory_tables.py"""
import sys, os, json, re; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from lib import config, data
from lib.runlog import Run

JS = config.ROOT / "js" / "sim-tables.js"; DTJ = config.R / "local" / "sim4" / "spread" / "params" / "deathtimer.json"
START, END = "/* memory tables: BUILT BY research/memory/build_memory_tables.py, never edit by hand */", "/* end memory tables */"
Q = np.linspace(0, 1, 21)

with Run("memory_tables", params={"cutoff": config.SPLIT}, inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV, DTJ]) as run:
    dt = json.load(open(DTJ)); tm, ev, _ = data.timelines(); tm = tm[tm.day < config.SPLIT]; ev = ev[ev.gameid.isin(tm.gameid)]
    nx, sg, kg, bg = [], [], [], []
    for gid, e in ev.groupby("gameid"):
        e = e.sort_values("t"); k = e[e.type == "kill"].t.values; n = e[e.type == "nexus"].t.values
        if len(n) and len(k): nx.append(n.max() - k[k <= n.max()].max() if (k <= n.max()).any() else np.nan)
        kd = np.diff(k); kg += list(kd[kd <= 20])
        for s, x in e[e.type.isin(["tower", "inhib", "nexus"])].groupby("side"):
            d = np.diff(np.sort(x.t.values)); sg += list(d[d <= 60])
        base = e[(e.type.isin(["inhib", "nexus"])) | ((e.type == "tower") & (e.detail.astype(str).str.contains("NEXUS") | e.detail.astype(str).str.startswith("T3")))]
        for s, x in base.groupby("side"):
            d = np.diff(np.sort(x.t.values)); bg += list(d[d <= 60])
    nx = np.array([v for v in nx if np.isfinite(v)])
    M = {"source": f"gol.gg timelines before {config.SPLIT} ({tm.gameid.nunique()} games); levels and role XP from {DTJ.name}",
         "level_xp": dt["xp_levels"], "role_xp": dt["role_xp"],
         "nexus_gap": [round(float(v), 1) for v in np.quantile(nx, Q)], "struct_gap": [round(float(v), 1) for v in np.quantile(sg, Q)],
         "kill_gap": [round(float(v), 1) for v in np.quantile(kg, Q)], "base_gap": [round(float(v), 1) for v in np.quantile(bg, Q)]}
    block = f"{START}\nwindow.SIM_TABLES.memory = {json.dumps(M, separators=(',', ':'))};\n{END}\n"
    js = JS.read_text(encoding="utf-8")
    js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + block
    tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)
    run.result("games", int(tm.gameid.nunique())); run.result("nexus gaps", len(nx)); run.result("structure gaps", len(sg)); run.result("kill gaps", len(kg)); run.result("base gaps", len(bg))
    run.save_json(config.MODEL_DIR / "memory" / "memory_tables.json", M)
    print(json.dumps(M, indent=1)); print("written", JS)
