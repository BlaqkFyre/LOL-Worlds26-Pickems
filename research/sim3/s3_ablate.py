"""Sim session 3 (research only): which inputs cost the sim log loss against v1? Held-out games (from 1 Sep, Worlds),
the calibrated sim (test3_results.json) with inputs switched off one group at a time: draft styles; draft styles and
lane inputs (lane skills, champion lane values). N sims per game, seeded as in s3_test.py.
usage: python -I s3_ablate.py params3.json test3_results.json lanes3_features.csv v1_games.csv comp3_games.csv <out_json> [n_sims]"""
import os, sys, json, importlib.util
from multiprocessing import Pool
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PJ, TJ, FE, V1, CO, OUTJ = sys.argv[1:7]; NS = int(sys.argv[7]) if len(sys.argv) > 7 else 100
ROLES = ["top", "jng", "mid", "bot", "sup"]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "s3_sim.py")); simmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(simmod)
P = json.load(open(PJ)); CAL = json.load(open(TJ))["cal"]
_sim = None
def init():
    global _sim; _sim = simmod.Sim(P, CAL)
def play(a):
    gid, x, seeds = a
    return gid, float(np.mean([_sim.run(x, seed=s)["winner"] == "blue" for s in seeds]))

if __name__ == "__main__":
    fe = pd.read_csv(FE); v1 = pd.read_csv(V1).set_index("gameid"); comp = pd.read_csv(CO).set_index("gameid")
    G = {}
    for gid, d in fe[fe.day >= "2026-09-01"].groupby("gameid"):
        d = d.set_index("position").reindex(ROLES)
        if d.z_v1.isna().any() or gid not in v1.index: continue
        c = comp.loc[gid] if gid in comp.index else None
        G[gid] = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
                  "siege_d": float(c.siege_blue - c.siege_red) if c is not None else 0.0, "obj_d": float(c.objectives_blue - c.objectives_red) if c is not None else 0.0,
                  "skirm_d": float(c.skirmish_blue - c.skirmish_red) if c is not None else 0.0, "pace_s": float(c.pace_blue + c.pace_red) if c is not None else 0.0,
                     "siege_s": float(c.siege_blue + c.siege_red) if c is not None else 0.0, "obj_s": float(c.objectives_blue + c.objectives_red) if c is not None else 0.0,
                  "y": int(v1.blue_win[gid]), "p": float(v1.p_v1[gid]), "w": d.league.iloc[0] == "WLDs"}
    variants = {"full": lambda x: x,
                "no draft styles": lambda x: {**x, "siege_d": 0.0, "obj_d": 0.0, "skirm_d": 0.0, "pace_s": 0.0, "siege_s": 0.0, "obj_s": 0.0},
                "no draft styles, no lane inputs": lambda x: {**x, "siege_d": 0.0, "obj_d": 0.0, "skirm_d": 0.0, "pace_s": 0.0, "siege_s": 0.0, "obj_s": 0.0,
                                                               "skill_gap": [0.0] * 5, "cg15": [0.0] * 5}}
    keys = ("z", "skill_gap", "cg15", "siege_d", "obj_d", "skirm_d", "pace_s", "siege_s", "obj_s")
    gids = sorted(G); res = {"n_sims": NS}
    ll = lambda p, y: round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)
    for name, f in variants.items():
        jobs = [(g, f({k: G[g][k] for k in keys}), [1 + 1000 * i + j for j in range(NS)]) for i, g in enumerate(gids)]
        with Pool(3, initializer=init) as pool: ps = dict(pool.imap(play, jobs, chunksize=4))
        out = {}
        for wn, sel in [("from 1 Sep", gids), ("Worlds", [g for g in gids if G[g]["w"]])]:
            p = np.clip(np.array([ps[g] for g in sel]), 0.5 / NS, 1 - 0.5 / NS); y = np.array([G[g]["y"] for g in sel]); pv = np.array([G[g]["p"] for g in sel])
            out[wn] = {"n": len(sel), "sim": ll(p, y), "v1": ll(pv, y), "mean_gap_to_v1": round(float(np.mean(np.abs(p - pv))), 4)}
        res[name] = out; print(name, out, flush=True)
    json.dump(res, open(OUTJ, "w"), indent=1)
