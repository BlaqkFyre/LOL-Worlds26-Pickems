"""Sim session 3 (research only, read-only): why the sim has too many kills and too many souls. Real side from the gol.gg
timelines matched to the file (games before 1 Sep unless noted); sim side from a small single-process batch of the saved
sim (params3.json + cal from test3_results_side.json, the last finished calibration) on held-out games.
Kills:  fights per minute and kills per fight by game time x size of the gold lead (real), so we can see whether real
        fights slow down when one team is far ahead; kills per game by game length (real v sim)
Souls:  dragon by dragon, the chance the team that took the last dragon takes the next one, and the team with more dragons
        takes the next one (real v sim); share of games with a soul
usage: python -I s3_check_ks.py tl_match.csv tl_events.csv tl_gold.csv params3.json test3_results_side.json lanes3_features.csv comp3_games.csv <out_json>"""
import os, sys, json, importlib.util
import numpy as np
import pandas as pd

TM, TE, TGo, PJ, CJ, FE, CO, OUTJ = sys.argv[1:9]
HERE = os.path.dirname(os.path.abspath(__file__)); ROLES = ["top", "jng", "mid", "bot", "sup"]
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)]
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold")]
go["sv"] = go.value * np.where(go.side == "blue", 1, -1); GD = go.groupby(["gid", "minute"]).sv.sum()
res = {}

# ---------- real: fights by game time x lead ----------
K = ev[ev.type == "kill"].sort_values(["gid", "t"]).copy()
K["new"] = (K.groupby("gid").t.diff().fillna(999) > 20).astype(int); K["fight"] = K.groupby("gid").new.cumsum()
F = K.groupby(["gid", "fight"]).agg(t=("t", "min"), n=("t", "size")).reset_index(); F["m"] = F.t // 60
L = M.set_index("gid").len // 60
mins = pd.DataFrame([(g, m) for g in M.gid for m in range(int(L[g]) + 1)], columns=["gid", "m"])
mins["lead"] = [abs(GD.get((g, m), np.nan)) for g, m in zip(mins.gid, mins.m)]
mins = mins.dropna(); mins["split"] = mins.gid.map(M.set_index("gid").date).lt("2026-09-01").map({True: "train", False: "test"})
fc = F.groupby(["gid", "m"]).agg(nf=("n", "size"), nk=("n", "sum"))
mins = mins.join(fc, on=["gid", "m"]).fillna({"nf": 0, "nk": 0})
mins["phase"] = pd.cut(mins.m, [-1, 13, 24, 34, 99], labels=["0-13", "14-24", "25-34", "35+"])
mins["band"] = pd.cut(mins.lead, [-1, 2000, 5000, 9000, 1e9], labels=["<2k", "2-5k", "5-9k", "9k+"])
t = mins[mins.split == "train"].groupby(["phase", "band"], observed=True).agg(minutes=("nf", "size"), fights_per_min=("nf", "mean"), kills_per_min=("nk", "mean"))
res["real_fights_by_phase_and_lead"] = {f"{a} | {b}": {k: round(float(v), 3) for k, v in r.items()} for (a, b), r in t.iterrows()}
# kills per game by length band, real (all matched games from 1 Sep)
G = M.set_index("gid"); G["kills"] = K.groupby("gid").size(); G["mins"] = G.len / 60
te = G[G.date >= "2026-09-01"]
res["real_kills_by_length"] = {str(k): round(float(v), 1) for k, v in te.groupby(pd.cut(te.mins, [0, 28, 32, 36, 40, 99])).kills.mean().items()}
res["real_kills_sd"] = round(float(te.kills.std()), 2)

# ---------- real: dragon by dragon ----------
def dragon_runs(seqs):
    same, lead_takes, n1, n2, soul = 0, 0, 0, 0, 0
    for sq in seqs:
        cnt = {0: 0, 1: 0}
        for i, s in enumerate(sq):
            if i > 0:
                n1 += 1; same += int(s == sq[i - 1])
                if cnt[0] != cnt[1]:
                    n2 += 1; lead_takes += int(cnt[s] > cnt[1 - s])
            cnt[s] += 1
        soul += int(max(cnt.values()) >= 4)
    return {"next_to_last_taker": round(same / max(n1, 1), 3), "next_to_team_with_more": round(lead_takes / max(n2, 1), 3),
            "soul_games": round(soul / max(len(seqs), 1), 3), "dragons": n1 + len(seqs), "games": len(seqs)}
D = ev[(ev.type == "dragon") & (ev.detail != "elder")].sort_values(["gid", "t"])
for w, gids in [("before 1 Sep", M[M.date < "2026-09-01"].gid), ("from 1 Sep", M[M.date >= "2026-09-01"].gid)]:
    seqs = [list((d.side == "red").astype(int)) for g, d in D[D.gid.isin(gids)].groupby("gid")]
    res.setdefault("real_dragons", {})[w] = dragon_runs(seqs)

# ---------- sim: small batch on held-out games ----------
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; sim = sm.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
gids = fe[fe.day >= "2026-09-01"].gameid.unique()[:150]
seqs, rows, fmins = [], [], []
for i, g in enumerate(gids):
    d = fe[fe.gameid == g].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any(): continue
    c = comp.loc[g] if g in comp.index else None
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if c is not None:
        x.update(siege_d=float(c.siege_blue - c.siege_red), obj_d=float(c.objectives_blue - c.objectives_red), skirm_d=float(c.skirmish_blue - c.skirmish_red),
                 pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(4):
        r = sim.run(x, seed=90000 + 10 * i + j, log=True); st = r["steps"]
        seqs.append([int(e["side"] == "red") for e in st if e["kind"] == "dragon"])
        rows.append((r["sec"] / 60, sum(r["kills"])))
        kt = np.array([e["t"] for e in st if e["kind"] == "kill"]); fs = kt[np.r_[True, np.diff(kt) > 20]] if len(kt) else kt
        for m in range(int(r["sec"] // 60) + 1):
            fmins.append((m, abs(r["gd"].get(m, np.nan)), int(((fs >= 60 * m) & (fs < 60 * m + 60)).sum()), int(((kt >= 60 * m) & (kt < 60 * m + 60)).sum())))
S = pd.DataFrame(rows, columns=["mins", "kills"])
res["sim_kills_by_length"] = {str(k): round(float(v), 1) for k, v in S.groupby(pd.cut(S.mins, [0, 28, 32, 36, 40, 99])).kills.mean().items()}
res["sim_kills_sd"] = round(float(S.kills.std()), 2)
res["sim_dragons"] = dragon_runs(seqs)
fm = pd.DataFrame(fmins, columns=["m", "lead", "nf", "nk"]).dropna()
fm["phase"] = pd.cut(fm.m, [-1, 13, 24, 34, 99], labels=["0-13", "14-24", "25-34", "35+"])
fm["band"] = pd.cut(fm.lead, [-1, 2000, 5000, 9000, 1e9], labels=["<2k", "2-5k", "5-9k", "9k+"])
ts = fm.groupby(["phase", "band"], observed=True).agg(minutes=("nf", "size"), fights_per_min=("nf", "mean"), kills_per_min=("nk", "mean"))
res["sim_fights_by_phase_and_lead"] = {f"{a} | {b}": {k: round(float(v), 3) for k, v in r.items()} for (a, b), r in ts.iterrows()}
json.dump(res, open(OUTJ, "w"), indent=1)
print("fights per minute / kills per minute by phase | lead   (real train  v  sim held-out)")
for k in res["real_fights_by_phase_and_lead"]:
    a = res["real_fights_by_phase_and_lead"][k]; b = res["sim_fights_by_phase_and_lead"].get(k, {})
    print(f"  {k:14s} real {a['fights_per_min']:.3f} / {a['kills_per_min']:.3f} (n {a['minutes']:.0f})   sim {b.get('fights_per_min', float('nan')):.3f} / {b.get('kills_per_min', float('nan')):.3f} (n {b.get('minutes', 0):.0f})")
print("kills by length  real", res["real_kills_by_length"], "sd", res["real_kills_sd"])
print("                 sim ", res["sim_kills_by_length"], "sd", res["sim_kills_sd"])
print("dragons real", res["real_dragons"]); print("dragons sim ", res["sim_dragons"])
