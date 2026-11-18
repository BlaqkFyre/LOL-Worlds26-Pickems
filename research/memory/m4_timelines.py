"""Game memory, step 6 (17 Nov 2026 AEST): the step 4-5 responses again on the gol.gg 2026 timelines (second check; Luke OK'd).
Timelines have each kill, tower, inhibitor, dragon, Baron and Nexus with its game second, but no health, levels or gold by second, so:
- fights: kills less than 20 s apart (as on the feed); winner = more kills (the feed's backup; trades left out). On the feed the kill and
  gold winners agree in 96.5% of fights with a kill winner (m1_fights.json).
- respawn: each death lasts the feed's median death time at that game minute (measured on the 98 Worlds games, common.deaths).
Games: the 640 timelines matched to the file, split into the 94 Worlds games (the same games as the feed: a like-for-like check of the
method) and the 546 others (major leagues, MSI, EWC: the second check).
Output: research/model/memory/m4_timelines.json.
usage (repo root): python -I research/memory/m4_timelines.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from lib import config, data, feed
from lib.runlog import Run
from common import FIGHT_GAP, OBJ, r3, dead_table, game_rows, block

OUT = config.MODEL_DIR / "memory"
PHASE = [(0, 840, "before 14:00"), (840, 1500, "14:00-25:00"), (1500, 1e9, "after 25:00")]

with Run("memory_timelines", params={"fight_gap": FIGHT_GAP, "winner": "kills", "respawn": "feed median by minute"},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV]) as run:
    DT, nd = dead_table(feed.full()); tm, ev, _ = data.timelines(); R = {"death time table (feed, median s by minute; deaths used)": nd,
        "death time at 5, 10, 15, 20, 25, 30, 35 min": [round(float(DT[m])) for m in (5, 10, 15, 20, 25, 30, 35)]}
    E = {g: d for g, d in ev.groupby("gameid")}; rows = []
    for _, m in tm.iterrows():
        if m.gameid not in E: continue
        for r in game_rows(E[m.gameid], m.win, m.len, DT): r.update(gameid=m.gameid, worlds=m.league == "WLDs", day=m.day); rows.append(r)
    D = pd.DataFrame(rows); D["phase"] = pd.cut(D.t, [p[0] for p in PHASE] + [1e9], labels=[p[2] for p in PHASE], right=False)
    D["lost"] = D.loser_deaths.clip(upper=4).astype(str).replace({"4": "4+"})
    for name, x in (("Worlds (same games as the feed)", D[D.worlds]), ("other 2026 timelines", D[~D.worlds])):
        R[name] = {"games": int(x.gameid.nunique()), "all": block(x), "by phase": {str(p): block(y) for p, y in x.groupby("phase", observed=True)},
                   "by loser deaths": {k: block(y) for k, y in x.groupby("lost")},
                   "after 25:00 by loser deaths": {k: block(y) for k, y in x[x.t >= 1500].groupby("lost")}}
    run.result("timeline fights", len(D)); run.save_json(OUT / "m4_timelines.json", R)
    import json; print(json.dumps({k: (v["all"] if isinstance(v, dict) and "all" in v else v) for k, v in R.items()}, indent=1))
