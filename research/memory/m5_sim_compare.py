"""Game memory, step 7 (17 Nov 2026 AEST): the real responses next to the current research sim's, on the same Worlds games.
Real: the gol.gg timelines of the Worlds games (event times), read the same way as m4_timelines.py.
Sim: research/sim3/s3_sim.py, the current default (fight types, lane level, first-dragon taker, fight players, death timers; the
calibration lib.simsetup.cal_default), 1,000 sims a game, seeds by game ID; its event log read exactly like a timeline (kills 20 s apart
= a fight, winner by kills, the losers back after the feed's median death time at that minute). Elder counts as a dragon (as gol.gg lists it).
The sim runs minute by minute, so second-level timing (how soon) is not compared; counts per fight, per game and by phase are.
Output: research/model/memory/m5_sim_compare.json.
usage (repo root): python -I research/memory/m5_sim_compare.py [sims per game = 1000]"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from lib import config, data, feed, simsetup
from lib.runlog import Run
from common import FIGHT_GAP, OBJ, r3, dead_table, game_rows, block

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000; OUT = config.MODEL_DIR / "memory"
PHASE = [(0, 840, "before 14:00"), (840, 1500, "14:00-25:00"), (1500, 1e9, "after 25:00")]
KIND = {"kill": "kill", "tower": "tower", "inhib": "inhib", "baron": "baron", "dragon": "dragon", "elder": "dragon", "nexus": "nexus"}

def shape(ev):
    """oversized fights, same-second objectives, the Nexus's gap after the last kill, from an event list"""
    k = sorted((tt, s) for tt, s, ty in ev if ty == "kill"); six = nf = 0; cur = []
    for e in k + [(1e12, "")]:
        if cur and e[0] - cur[-1][0] > FIGHT_GAP:
            nf += 1; nb = sum(s == "blue" for _, s in cur); six += int(nb > 5 or len(cur) - nb > 5); cur = []
        cur.append(e)
    ob = sorted(tt for tt, s, ty in ev if ty in ("tower", "inhib", "baron", "dragon", "nexus"))
    nx = [tt for tt, s, ty in ev if ty == "nexus"]
    return {"six": six, "nf": nf, "same": sum(1 for a, b in zip(ob, ob[1:]) if a == b), "nxgap": (max(nx) - k[-1][0]) if nx and k else np.nan}

def summarise(D, G):
    """D: fights (game_rows + gameid, sim), G: one row per game (kills, length, ...)"""
    D = D.copy(); D["phase"] = pd.cut(D.t, [p[0] for p in PHASE] + [1e9], labels=[p[2] for p in PHASE], right=False)
    D["lost"] = D.loser_deaths.clip(upper=4).astype(str).replace({"4": "4+"})
    kw, kl = G[["kb", "kr"]].max(1), G[["kb", "kr"]].min(1)
    return {"games": int(len(G)), "per game": {"kills": r3(G.kb.add(G.kr).mean()), "minutes": r3(G.sec.mean() / 60),
            "fights with a kills winner": r3(len(D) / len(G)), "45+ min": r3((G.sec >= 2700).mean()), "50+ min": r3((G.sec >= 3000).mean()),
            "loser on a third of the winner's kills or fewer": r3((kl * 3 <= kw).mean()), "kills before 14:00": r3(G.k14.mean()),
            "fights (kills 20 s apart) with 6+ deaths on one side": r3(G.six.sum() / max(G.nf.sum(), 1)),
            "objectives in the same second as the one before, per game": r3(G.same.mean()),
            "Nexus: seconds after the last kill, median": r3(G.nxgap.median()), "Nexus more than 60 s after the last kill": r3((G.nxgap > 60).mean())},
            "all": block(D), "by phase": {str(p): block(y) for p, y in D.groupby("phase", observed=True)},
            "by loser deaths": {k: block(y) for k, y in D.groupby("lost")},
            "after 25:00 by loser deaths": {k: block(y) for k, y in D[D.t >= 1500].groupby("lost")}}

with Run("memory_sim_compare", params={"sims_per_game": N, "fight_gap": FIGHT_GAP, "sim": "s3_sim default with death timers"},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.R / "sim3" / "s3_sim.py", config.LANE_FEATURES]) as run:
    DT, _ = dead_table(feed.full()); tm, ev, _ = data.timelines(); XS = simsetup.inputs()
    W = tm[(tm.league == "WLDs") & tm.gameid.isin(XS)]; E = {g: d for g, d in ev.groupby("gameid")}
    run.result("games", len(W)); print("games", len(W), flush=True)
    sim = simsetup.sim_module(); P = simsetup.params({"typed", "ll", "fdt", "fpl", "dt"}); cal = simsetup.cal_default(); S = sim.Sim(P, cal)
    real_f, real_g, sim_f, sim_g = [], [], [], []
    for n, m in enumerate(W.itertuples()):
        e = E[m.gameid]; k = e[e.type == "kill"]
        el = list(zip(e.t.tolist(), e.side.tolist(), e.type.tolist()))
        real_g.append({"kb": int((k.side == "blue").sum()), "kr": int((k.side == "red").sum()), "sec": float(m.len), "k14": int((k.t < 840).sum()), **shape(el)})
        for r in game_rows(e, m.win, m.len, DT): r["gameid"] = m.gameid; real_f.append(r)
        for j in range(N):
            o = S.run(XS[m.gameid], simsetup.seed(m.gameid, j), log=True)
            se = [(s["t"], s["side"], KIND[s["kind"]]) for s in o["steps"] if s["kind"] in KIND]
            sim_g.append({"kb": o["kills"][0], "kr": o["kills"][1], "sec": float(o["sec"]), "k14": sum(ty == "kill" and tt < 840 for tt, _, ty in se), **shape(se)})
            for r in game_rows(se, o["winner"], o["sec"], DT): r["gameid"] = m.gameid; sim_f.append(r)
        print(f"{n + 1}/{len(W)}", flush=True)
    R = {"real (gol.gg timelines)": summarise(pd.DataFrame(real_f), pd.DataFrame(real_g)), "current sim": summarise(pd.DataFrame(sim_f), pd.DataFrame(sim_g))}
    run.save_json(OUT / "m5_sim_compare.json", R)
    import json; print(json.dumps({k: {"per game": v["per game"], "all": v["all"]} for k, v in R.items()}, indent=1))
