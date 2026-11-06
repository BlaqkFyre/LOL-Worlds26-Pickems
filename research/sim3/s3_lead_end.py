"""Sim session 3 research (6 Nov): how game length and kill rate depend on the gold lead at 20:00, sim v real (held-out games).
usage: python -I s3_lead_end.py params3.json cal.json lanes3_features.csv comp3_games.csv tl_match.csv tl_events.csv tl_gold.csv [games] [runs]"""
import os, sys, json, importlib.util
import numpy as np, pandas as pd
PJ, CJ, FE, CO, TM, TE, TGo = sys.argv[1:8]; NG = int(sys.argv[8]) if len(sys.argv) > 8 else 150; NR = int(sys.argv[9]) if len(sys.argv) > 9 else 4
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sim = m.Sim(json.load(open(PJ)), json.load(open(CJ))["cal"]); fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid"); rows = []
for i, g in enumerate(fe[fe.day >= "2026-09-01"].gameid.unique()[:NG]):
    d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if g in comp.index:
        c = comp.loc[g]; x.update(pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(NR):
        r = sim.run(x, seed=90000 + 10 * i + j, log=True)
        if r["sec"] >= 1260: rows.append(dict(min=r["sec"] / 60, kills=sum(r["kills"]), gd20=abs(r["gd"].get(20, np.nan))))
S = pd.DataFrame(rows)
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.date >= "2026-09-01")]
e = pd.read_csv(TE, dtype={"gid": str}); e = e[e.gid.isin(M.gid)]
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold") & (go.minute == 20)]; go["sv"] = go.value * np.where(go.side == "blue", 1, -1)
R = M.set_index("gid")[["len"]].copy(); R["min"] = R.len / 60; R["kills"] = e[e.type == "kill"].groupby("gid").size(); R["gd20"] = go.groupby("gid").sv.sum().abs()
R = R[R["min"] >= 21].dropna()
for nm, D in [("SIM ", S), ("REAL", R)]:
    D = D.dropna(); D["rate"] = D.kills / D["min"]; D["band"] = pd.cut(D.gd20, [-1, 2000, 5000, 9000, 1e9], labels=["<2k", "2-5k", "5-9k", "9k+"])
    t = D.groupby("band", observed=True).agg(n=("min", "size"), length=("min", "median"), kills_per_min=("rate", "mean"))
    print(nm, "games", len(D), "corr(|lead@20|, length)", round(D.gd20.corr(D["min"]), 2), "corr(|lead@20|, kill rate)", round(D.gd20.corr(D.rate), 2))
    print(t.round(2).to_string())
