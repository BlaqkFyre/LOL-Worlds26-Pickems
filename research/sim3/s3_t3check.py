"""Sim session 3 (research only, read-only): the inner-tower (T3, inhibitor turret) stage, real v sim.
Real (gol.gg timelines matched to the file, training games before 1 Sep and held-out from 1 Sep): per side and lane, time
from the lane's T2 falling (10th segment) to its T3 falling (15th); T3 segments per minute while the T3 stands; share of
T3 segments taken under the side's Baron buff and in minutes the side won the fighting; minutes with 0 / 1-2 / 3+ T3 segments.
Sim: the calibrated sim (params3.json + test3_results.json cal) on held-out games, tower falls from the play-by-play.
usage: python -I s3_t3check.py tl_match.csv tl_events.csv params3.json test3_results.json lanes3_features.csv comp3_games.csv <out_json>"""
import os, sys, json, importlib.util
import numpy as np
import pandas as pd

TM, TE, PJ, CJ, FE, CO, OUTJ = sys.argv[1:8]; ROLES = ["top", "jng", "mid", "bot", "sup"]
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
M["w"] = np.where(M.date < "2026-09-01", "train", "held-out")
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)]
res = {"real": {}, "sim": {}}
for w, gids in M.groupby("w").gid:
    e = ev[ev.gid.isin(gids)]; pla = e[e.type == "plate"].sort_values("t"); bar = e[e.type == "baron"]; K = e[e.type == "kill"]
    durs, segs, under_baron, won_min, permin = [], 0, 0, 0, []
    for (g, s, lane), d in pla.groupby(["gid", "side", "detail"]):
        t = d.t.values
        if len(t) < 10: continue
        t2 = t[9]; t3 = t[14] if len(t) >= 15 else None
        L = int(M.set_index("gid").len[g])
        end = t3 if t3 is not None else L
        if t3 is not None: durs.append(t3 - t2)
        ts = t[10:15]
        for x in ts:
            segs += 1
            under_baron += int(((bar.gid == g) & (bar.side == s) & (bar.t <= x) & (bar.t > x - 180)).any())
            k = K[(K.gid == g) & (K.t <= x) & (K.t > x - 60)]
            won_min += int((k.side == s).sum() > (k.side != s).sum())
        for m in range(int(t2 // 60) + 1, int(end // 60) + 1):
            permin.append(int(((ts >= 60 * m) & (ts < 60 * m + 60)).sum()))
    pm = np.array(permin)
    res["real"][w] = {"lanes_T2_to_T3": len(durs), "T2_to_T3_s": {"median": int(np.median(durs)), "p25": int(np.percentile(durs, 25)), "p75": int(np.percentile(durs, 75))},
                      "T3_segments": segs, "share_under_baron": round(under_baron / segs, 3), "share_after_won_minute": round(won_min / segs, 3),
                      "minutes_T3_standing": len(pm), "segments_per_minute": round(float(pm.mean()), 3),
                      "minutes_with_0_1to2_3plus": [round(float((pm == 0).mean()), 3), round(float(((pm >= 1) & (pm <= 2)).mean()), 3), round(float((pm >= 3).mean()), 3)]}

# sim: tower falls from the play-by-play
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; sim = sm.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
durs, under = [], []
for i, g in enumerate(fe[fe.day >= "2026-09-01"].gameid.unique()[:120]):
    d = fe[fe.gameid == g].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if g in comp.index:
        c = comp.loc[g]; x.update(siege_d=float(c.siege_blue - c.siege_red), obj_d=float(c.objectives_blue - c.objectives_red), skirm_d=float(c.skirmish_blue - c.skirmish_red),
                                   pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(5):
        r = sim.run(x, seed=70000 + 10 * i + j, log=True); st = r["steps"]
        bars = [(e["t"], e["side"]) for e in st if e["kind"] == "baron"]
        for side in ("blue", "red"):
            for lane in ("TOP", "MID", "BOT"):
                t2 = [e["t"] for e in st if e["kind"] == "tower" and e["side"] == side and e["text"] == f"T2 {lane}"]
                t3 = [e["t"] for e in st if e["kind"] == "tower" and e["side"] == side and e["text"] == f"T3 {lane}"]
                if t2 and t3:
                    durs.append(t3[0] - t2[0]); under.append(any(s == side and t3[0] - 180 < t <= t3[0] for t, s in bars))
res["sim"] = {"lanes_T2_to_T3": len(durs), "T2_to_T3_s": {"median": int(np.median(durs)), "p25": int(np.percentile(durs, 25)), "p75": int(np.percentile(durs, 75))},
              "T3_falls_under_baron": round(float(np.mean(under)), 3)}
# real share of T3 FALLS under Baron, for a like-for-like check
for w, gids in M.groupby("w").gid:
    e = ev[ev.gid.isin(gids)]; bar = e[e.type == "baron"]; t3 = e[(e.type == "tower") & e.detail.str.match(r"T3 (TOP|MID|BOT)$", na=False)]
    res["real"][w]["T3_falls_under_baron"] = round(float(np.mean([((bar.gid == r.gid) & (bar.side == r.side) & (bar.t <= r.t) & (bar.t > r.t - 180)).any() for r in t3.itertuples()])), 3)
json.dump(res, open(OUTJ, "w"), indent=1)
print(json.dumps(res, indent=1))
