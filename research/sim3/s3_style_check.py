"""Sim session 3 (research only): do draft styles move game timing in the sim the way they do in real games?
Held-out games (from 1 Sep and Worlds, timeline-matched). Per game: both drafts' styles (pace, siege, objectives; from
games before 1 Sep, s3_comp.py). Real side: the game's kills per minute, first-tower time, towers, first-dragon wait and
first-Baron time from the timelines. Sim side: the same game simulated N times (calibrated sim, test3_results.json), the
averages. For each style and measure: correlation across games (real; sim) and the slope (change per 0.1 of style).
A style "works for timing" when the sim's link has the same sign and a similar size as the real one.
usage: python -I s3_style_check.py params3.json test3_results.json lanes3_features.csv comp3_games.csv tl_match.csv tl_events.csv <out_json> [n]"""
import os, sys, json, importlib.util
from multiprocessing import Pool
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PJ, TJ, FE, CO, TM, TE, OUTJ = sys.argv[1:8]; NS = int(sys.argv[8]) if len(sys.argv) > 8 else 40
ROLES = ["top", "jng", "mid", "bot", "sup"]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "s3_sim.py")); simmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(simmod)
P = json.load(open(PJ)); CAL = json.load(open(TJ))["cal"]
_sim = None
def init():
    global _sim; _sim = simmod.Sim(P, CAL)
def play(a):
    gid, x, seeds = a; out = []
    for s in seeds:
        g = _sim.run(x, seed=s, log=True); st = g["steps"]
        tw = [e["t"] for e in st if e["kind"] == "tower"]; dr = [e["t"] for e in st if e["kind"] == "dragon"]; ba = [e["t"] for e in st if e["kind"] == "baron"]
        out.append((sum(g["kills"]) / (g["sec"] / 60), min(tw) if tw else np.nan, sum(g["towers"]), (min(dr) - 300) if dr else np.nan,
                    min(ba) if ba else np.nan, g["sec"] / 60))
    return gid, np.nanmean(np.array(out, dtype=float), axis=0).tolist()

if __name__ == "__main__":
    fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
    mt = pd.read_csv(TM, dtype={"gid": str}); mt = mt[mt.gameid.notna() & (mt.gameid != "AMBIGUOUS") & (mt.date >= "2026-09-01")].drop_duplicates("gameid")
    ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(mt.gid)]
    rows = []
    for r in mt.itertuples():
        d = fe[fe.gameid == r.gameid].set_index("position").reindex(ROLES)
        if d.z_v1.isna().any() or r.gameid not in comp.index: continue
        c = comp.loc[r.gameid]; e = ev[ev.gid == r.gid]
        tw = e[e.type == "tower"].t; dr = e[(e.type == "dragon") & (e.detail != "elder")].t; ba = e[e.type == "baron"].t
        x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
             "siege_d": float(c.siege_blue - c.siege_red), "obj_d": float(c.objectives_blue - c.objectives_red),
             "skirm_d": float(c.skirmish_blue - c.skirmish_red), "pace_s": float(c.pace_blue + c.pace_red),
             "siege_s": float(c.siege_blue + c.siege_red), "obj_s": float(c.objectives_blue + c.objectives_red)}
        rows.append(dict(gameid=r.gameid, x=x, pace=x["pace_s"], siege=x["siege_s"], obj=x["obj_s"],
                         real=[len(e[e.type == "kill"]) / (r.len / 60), tw.min() if len(tw) else np.nan, len(tw),
                               (dr.min() - 300) if len(dr) else np.nan, ba.min() if len(ba) else np.nan, r.len / 60]))
    jobs = [(r["gameid"], r["x"], [7 + 1000 * i + j for j in range(NS)]) for i, r in enumerate(rows)]
    with Pool(3, initializer=init) as pool: sim = dict(pool.imap(play, jobs, chunksize=4))
    M = ["kills_per_min", "first_tower_s", "towers", "first_dragon_wait_s", "first_baron_s", "length_min"]
    real = pd.DataFrame([r["real"] for r in rows], columns=M); simd = pd.DataFrame([sim[r["gameid"]] for r in rows], columns=M)
    sty = pd.DataFrame([{k: r[k] for k in ["pace", "siege", "obj"]} for r in rows])
    res = {"games": len(rows), "n_sims": NS, "mode": CAL.get("style_mode", "side"), "links": {}}
    for s_ in ["pace", "siege", "obj"]:
        for m in M:
            ok = real[m].notna() & simd[m].notna()
            sl = lambda y: float(np.polyfit(sty[s_][ok], y[ok], 1)[0] * 0.1)
            res["links"][f"{s_} -> {m}"] = {"real_corr": round(float(np.corrcoef(sty[s_][ok], real[m][ok])[0, 1]), 3), "sim_corr": round(float(np.corrcoef(sty[s_][ok], simd[m][ok])[0, 1]), 3),
                                           "real_per_0.1": round(sl(real[m]), 3), "sim_per_0.1": round(sl(simd[m]), 3)}
    json.dump(res, open(OUTJ, "w"), indent=1)
    for k, v in res["links"].items(): print(f"{k:32s} real {v['real_corr']:+.3f} ({v['real_per_0.1']:+.3f})   sim {v['sim_corr']:+.3f} ({v['sim_per_0.1']:+.3f})")
