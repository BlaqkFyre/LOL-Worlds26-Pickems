"""Sim session 3 research (6 Nov): second-tier towers, real v sim. Per lane and taking side: when T1 and T2 fall, the gap between
them, and the share of games with a T2 down by 18 / 20 / 22 / 24 min. Real: held-out timeline games (from 1 Sep, Worlds included);
sim: the same matchups. Optionally a second cal file to compare a variant.
usage: python -I s3_t2check.py params3.json cal.json lanes3_features.csv comp3_games.csv tl_match.csv tl_events.csv [games] [runs] [cal2.json]"""
import os, sys, json, importlib.util
import numpy as np, pandas as pd
PJ, CJ, FE, CO, TM, TE = sys.argv[1:7]; NG = int(sys.argv[7]) if len(sys.argv) > 7 else 150; NR = int(sys.argv[8]) if len(sys.argv) > 8 else 4
C2 = sys.argv[9] if len(sys.argv) > 9 else None
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
P = json.load(open(PJ)); fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
def sim_rows(cal):
    sim = m.Sim(P, cal); rows = []
    for i, g in enumerate(fe[fe.day >= "2026-09-01"].gameid.unique()[:NG]):
        d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
        if d.z_v1.isna().any(): continue
        x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
        if g in comp.index:
            c = comp.loc[g]; x.update(pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
        for j in range(NR):
            r = sim.run(x, seed=50000 + 10 * i + j, log=True); gid = f"{i}_{j}"
            for e in r["steps"]:
                if e["kind"] == "tower" and e["text"][:2] in ("T1", "T2", "T3"): rows.append((gid, e["side"], e["text"].split()[1], e["text"][:2], e["t"]))
            rows.append((gid, "", "", "END", r["sec"]))
    return pd.DataFrame(rows, columns=["gid", "side", "lane", "tier", "t"])
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.date >= "2026-09-01")]
e = pd.read_csv(TE, dtype={"gid": str}); e = e[e.gid.isin(M.gid) & (e.type == "tower")]
e = e[e.detail.str.match(r"^T[123] (TOP|MID|BOT)$")]
R = pd.DataFrame({"gid": e.gid, "side": e.side, "lane": e.detail.str[3:], "tier": e.detail.str[:2], "t": e.t})
R = pd.concat([R, pd.DataFrame({"gid": M.gid, "side": "", "lane": "", "tier": "END", "t": M.len})])
def summary(D):
    W = D[D.tier != "END"].pivot_table(index=["gid", "side", "lane"], columns="tier", values="t", aggfunc="min")
    first_t2 = D[D.tier == "T2"].groupby("gid").t.min(); n = D.gid.nunique()
    out = {"games": n, "first T2 median": f"{int(first_t2.median()) // 60}:{int(first_t2.median()) % 60:02d}",
           **{f"T2 down by {k} min": round(float((first_t2 < 60 * k).sum() / n), 3) for k in (18, 20, 22, 24)},
           "T1 to T2 gap, median s (same lane and side)": {L: int((W.T2 - W.T1)[W.index.get_level_values("lane") == L].median()) for L in ("TOP", "MID", "BOT")},
           "T2 falls per game by lane": {L: round(float(W.T2[W.index.get_level_values("lane") == L].notna().sum() / n), 2) for L in ("TOP", "MID", "BOT")},
           "share of T1s followed by the T2 within 3 min": round(float(((W.T2 - W.T1) <= 180).sum() / W.T1.notna().sum()), 3)}
    return out
cal = json.load(open(CJ))["cal"]
res = {"REAL": summary(R), "SIM": summary(sim_rows(cal))}
if C2: res["SIM variant"] = summary(sim_rows(json.load(open(C2))["cal"]))
for k, v in res.items(): print(k, json.dumps(v))
