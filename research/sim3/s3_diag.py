"""Sim session 3 (read-only check): structure timing in the sim v real timelines, games from 1 Sep.
Medians of first T1 / T2 / T3 / inhibitor and game end, T3 -> inhibitor and inhibitor -> end, length and kills.
usage: python -I s3_diag.py params3.json test3_results.json(cal) lanes3_features.csv tl_events.csv tl_match.csv"""
import sys, json, importlib.util, os
import numpy as np
import pandas as pd

PJ, CJ, FE, TE, TM = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; s = m.Sim(P, cal)
fe = pd.read_csv(FE); gids = fe[fe.day >= "2026-09-01"].gameid.unique()[:120]
rows = []
for i, g in enumerate(gids):
    d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    for j in range(5):
        r = s.run(x, seed=i * 10 + j, log=True); st = r["steps"]
        f = lambda pre: min([e["t"] for e in st if e["kind"] == "tower" and e["text"].startswith(pre)] or [np.nan])
        inh = [e["t"] for e in st if e["kind"] == "inhib"]
        rows.append(dict(end=r["sec"], t1=f("T1"), t2=f("T2"), t3=f("T3"), inh=min(inh) if inh else np.nan, kills=sum(r["kills"])))
d = pd.DataFrame(rows); d["inh_end"] = d.end - d.inh; d["t3_inh"] = d.inh - d.t3
e = pd.read_csv(TE, dtype={"gid": str}); mt = pd.read_csv(TM, dtype={"gid": str}); mt = mt[mt.gameid.notna() & (mt.date >= "2026-09-01")]
e = e[e.gid.isin(mt.gid)]; tw = e[e.type == "tower"]
f = lambda q: tw[tw.detail.str.startswith(q) & ~tw.detail.str.contains("NEXUS")].groupby("gid").t.min()
R = pd.DataFrame({"end": mt.set_index("gid").len, "t1": f("T1"), "t2": f("T2"), "t3": f("T3"), "inh": e[e.type == "inhib"].groupby("gid").t.min(),
                  "kills": e[e.type == "kill"].groupby("gid").size()})
R["inh_end"] = R.end - R.inh; R["t3_inh"] = R.inh - R.t3
print("SIM ", d.median().round(0).to_dict(), "length sd", round(d.end.std() / 60, 2), "kills sd", round(d.kills.std(), 1))
print("REAL", R.median().round(0).to_dict(), "length sd", round(R.end.std() / 60, 2), "kills sd", round(R.kills.std(), 1))
