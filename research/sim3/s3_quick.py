"""Sim session 3 (research only): quick shape check of a sim version on held-out games (single process).
Length quantiles and spread, share of games under 24 min and their Baron / kill rate, kills and their spread, kill difference
and gold lead at 15, kill rate v length; real side from the gol.gg timelines (from 1 Sep, Worlds included).
usage: python -I s3_quick.py params3.json test3_results.json(cal) lanes3_features.csv comp3_games.csv tl_match.csv tl_events.csv tl_gold.csv [games] [runs]"""
import os, sys, json, importlib.util
import numpy as np
import pandas as pd

PJ, CJ, FE, CO, TM, TE, TGo = sys.argv[1:8]; NG = int(sys.argv[8]) if len(sys.argv) > 8 else 150; NR = int(sys.argv[9]) if len(sys.argv) > 9 else 4
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; sim = m.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
rows = []
for i, g in enumerate(fe[fe.day >= "2026-09-01"].gameid.unique()[:NG]):
    d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if g in comp.index:
        c = comp.loc[g]; x.update(pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(NR):
        r = sim.run(x, seed=50000 + 10 * i + j, log=True); st = r["steps"]
        rows.append(dict(min=r["sec"] / 60, kills=sum(r["kills"]), barons=sum(r["ba"]), gd15=r["gd"].get(15, np.nan),
                         k15=sum((1 if e["side"] == "blue" else -1) for e in st if e["kind"] == "kill" and e["t"] < 900)))
S = pd.DataFrame(rows)
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.date >= "2026-09-01")]
e = pd.read_csv(TE, dtype={"gid": str}); e = e[e.gid.isin(M.gid)]; e["v"] = np.where(e.side == "blue", 1, -1)
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold") & (go.minute == 15)]; go["sv"] = go.value * np.where(go.side == "blue", 1, -1)
R = M.set_index("gid")[["len"]].copy(); R["min"] = R.len / 60; R["kills"] = e[e.type == "kill"].groupby("gid").size()
R["barons"] = e[e.type == "baron"].groupby("gid").size().reindex(R.index).fillna(0); R["gd15"] = go.groupby("gid").sv.sum()
R["k15"] = e[(e.type == "kill") & (e.t < 900)].groupby("gid").v.sum().reindex(R.index).fillna(0)
for nm, D in [("SIM ", S), ("REAL", R.dropna())]:
    sh = D[D["min"] < 24]
    print(f"{nm} length q10/50/90 {D['min'].quantile(.1):.1f}/{D['min'].median():.1f}/{D['min'].quantile(.9):.1f} sd {D['min'].std():.2f} | under 24 min {len(sh)/len(D):.3f} (no Baron {(sh.barons == 0).mean() if len(sh) else float('nan'):.2f})"
          f" | kills {D.kills.mean():.1f} sd {D.kills.std():.1f} | kill diff@15 sd {D.k15.std():.2f} | gd15 sd {D.gd15.std():.0f} | Baron games {(D.barons > 0).mean():.3f}"
          f" | corr(kill rate, length) {np.corrcoef(D.kills / D['min'], D['min'])[0, 1]:+.2f}")
