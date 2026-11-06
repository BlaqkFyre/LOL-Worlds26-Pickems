"""Sim session 3 research (6 Nov): how strongly pre-game strength (v1 log-odds) decides who gets kills, dragons, towers and Barons in
each phase of simulated games, to compare with the same measure on real timeline games.
usage: python -I s3_zphase.py params3.json cal.json lanes3_features.csv comp3_games.csv [games] [runs]"""
import os, sys, json, importlib.util
import numpy as np, pandas as pd
PJ, CJ, FE, CO = sys.argv[1:5]; NG = int(sys.argv[5]) if len(sys.argv) > 5 else 200; NR = int(sys.argv[6]) if len(sys.argv) > 6 else 3
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sim = m.Sim(json.load(open(PJ)), json.load(open(CJ))["cal"])
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid"); rows = []
for i, g in enumerate(fe[fe.day >= "2026-09-01"].gameid.unique()[:NG]):
    d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if g in comp.index:
        c = comp.loc[g]; x.update(pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(NR):
        r = sim.run(x, seed=70000 + 10 * i + j, log=True)
        for e in r["steps"]:
            if e["kind"] in ("kill", "dragon", "tower", "baron"): rows.append((e["kind"], e["t"], e["side"] == "blue", x["z"]))
E = pd.DataFrame(rows, columns=["type", "t", "blue", "z"])
def lfit(x, y, it=50):
    X = np.c_[np.ones(len(x)), x]; b = np.zeros(2)
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); b += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]) + 1e-3 * np.eye(2), X.T @ (y - p))
    return round(float(b[1]), 3), len(y)
for typ in ["kill", "dragon", "tower", "baron"]:
    q = E[E.type == typ]
    print(typ, {ph: lfit(q[(q.t >= lo) & (q.t < hi)].z.values, q[(q.t >= lo) & (q.t < hi)].blue.values.astype(float))
                for ph, lo, hi in [("0-14", 0, 840), ("14-25", 840, 1500), ("25+", 1500, 99999)] if ((q.t >= lo) & (q.t < hi)).sum() > 40})
