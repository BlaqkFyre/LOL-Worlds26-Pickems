"""Diagnosis (13 Nov 2026 AEST): why does the fight-players version weaken the link between bot-lane gold at 10 and the first dragon
(test_dragon_botlane.py: real +0.68, default sim +0.66, fight players +0.36; mid +0.93 v real -0.07)? Read-only.
For the 321 held-out games (from 1 Sep), real v the default sim v the fight-players version (N sims each, seeded):
  gold at 10 by role      spread (sd), link with v1 (slope per unit of v1 log-odds), correlation between roles' leads
  gold at 10 v first dragon   first-dragon blue share when blue's bot duo / mid / jungle is ahead by 500+ at 10 v behind by 500+
  kills before 10         per game, by killer role and victim role; and each role's kills-minus-deaths sd at 10
  where the first dragon falls   minute of the first dragon
Real gold at 10 and kills at 10 from the Oracle's Elixir file (golddiffat10, killsat10, deathsat10).
usage (repo root): python -I research/sim4/diag_lanes10.py <OE csv> params_dir ll_dir lanes3_features.csv comp3_games.csv cal_default.json cal_fp.json <out_json> [n=30]"""
import os, sys, json, zlib, importlib.util
import numpy as np, pandas as pd
CSV, PD, LLD, FE, CO, CD, CF, OUT = sys.argv[1:9]; N = int(sys.argv[9]) if len(sys.argv) > 9 else 30
ROLES = ["top", "jng", "mid", "bot", "sup"]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join("research", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(os.path.join(PD, "params3.json"))); P["fight_typed"] = json.load(open(os.path.join(PD, "fighttypes.json")))
P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); P["early_kills"] = json.load(open(os.path.join(PD, "earlykills.json"))); P["fight_players"] = json.load(open(os.path.join(PD, "participants.json")))
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid"); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "side", "position", "golddiffat10", "killsat10", "deathsat10", "firstdragon"])
blue = raw[raw.side == "Blue"]; pb = blue[blue.position.isin(ROLES)]
gd10 = pb.pivot_table(index="gameid", columns="position", values="golddiffat10")
kd10 = (pb.assign(kd=pb.killsat10 - pb.deathsat10).pivot_table(index="gameid", columns="position", values="kd")
        - raw[(raw.side == "Red") & raw.position.isin(ROLES)].assign(kd=lambda t: t.killsat10 - t.deathsat10).pivot_table(index="gameid", columns="position", values="kd"))
k10b = pb.pivot_table(index="gameid", columns="position", values="killsat10"); k10r = raw[(raw.side == "Red") & raw.position.isin(ROLES)].pivot_table(index="gameid", columns="position", values="killsat10")
fd = blue[blue.position == "team"].set_index("gameid").firstdragon
X = {}
for g in sorted(fe[fe.day >= "2026-09-01"].gameid.unique()):
    if g not in m0.index or g not in comp.index or g not in gd10.index: continue
    d = fe[fe.gameid == g].set_index("position").reindex(ROLES); c = comp.loc[g]
    if d.z_v1.isna().any(): continue
    e0c = [f"e0_{r}" if f"e0_{r}" in m0.columns else f"m0_{r}" for r in ROLES]
    X[g] = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
            "siege_d": float(c.siege_blue - c.siege_red), "obj_d": float(c.objectives_blue - c.objectives_red), "skirm_d": float(c.skirmish_blue - c.skirmish_red),
            "pace_s": float(c.pace_blue + c.pace_red), "siege_s": float(c.siege_blue + c.siege_red), "obj_s": float(c.objectives_blue + c.objectives_red),
            "ll_m0": m0.loc[g, [f"m0_{r}" for r in ROLES]].tolist(), "ll_e0": m0.loc[g, e0c].tolist()}
gs = list(X)
def summary(G10, KD, KB, KR, FD, Z, MINS=None):
    G10 = G10.copy(); G10["duo"] = G10.bot + G10.sup
    out = {"sd at 10": {r: round(float(G10[r].std())) for r in ROLES + ["duo"]},
           "slope on v1 (gold per unit)": {r: round(float(np.polyfit(Z, G10[r], 1)[0])) for r in ROLES + ["duo"]},
           "corr between leads at 10": {f"{a}~{b}": round(float(G10[a].corr(G10[b])), 2) for a, b in [("jng", "mid"), ("jng", "duo"), ("mid", "duo"), ("top", "jng"), ("top", "duo"), ("bot", "sup")]},
           "kills-minus-deaths sd at 10": {r: round(float(KD[r].std()), 2) for r in ROLES},
           "kills before 10 per game, by role (both sides)": {r: round(float((KB[r] + KR[r]).mean()), 3) for r in ROLES},
           "first dragon blue share when blue is ahead / behind by 500+ at 10": {r: [round(float(FD[G10[r] > 500].mean()), 3), round(float(FD[G10[r] < -500].mean()), 3)] for r in ["jng", "mid", "duo"]},
           "first dragon blue share": round(float(FD.mean()), 3)}
    if MINS is not None: out["first dragon minute p10 / median / p90"] = [round(float(np.nanpercentile(MINS, q)), 2) for q in (10, 50, 90)]
    return out
R = {"games": len(gs), "sims_per_game": N}
R["real"] = summary(gd10.loc[gs], kd10.loc[gs], k10b.loc[gs], k10r.loc[gs], fd.loc[gs], np.array([X[g]["z"] for g in gs]))
for vn, cf, extra in [("sim: default now", CD, {}), ("sim: fight players + early counts + event order", CF, {"fight_players": "on", "early_kills": "counts", "event_order": "on"})]:
    cal = dict(json.load(open(cf))["cal"], **extra); sim = sm.Sim(P, cal); rows = []
    for g in gs:
        for j in range(N):
            o = sim.run(X[g], seed=700_000 + zlib.crc32(g.encode()) * 10_000 + j, log=True); r10 = o["roles10"]  # seeds by game ID (13 Nov fix)
            kb = [0] * 5; kr = [0] * 5; kdv = [0] * 5
            for e in o["steps"]:
                if e["kind"] != "kill" or e["t"] >= 600: continue
                k_, v_ = e["text"].replace(" (solo)", "").split(" kills "); ki, vi = ROLES.index(k_), ROLES.index(v_)
                if e["side"] == "blue": kb[ki] += 1; kdv[ki] += 1; kdv[vi] -= 1
                else: kr[ki] += 1; kdv[ki] -= 1; kdv[vi] += 1
            if o["first"].get("dragon") is None or any(np.isnan(r10)): continue
            rows.append((X[g]["z"], *r10, *kdv, *kb, *kr, 1.0 if o["first"]["dragon"] == "blue" else 0.0, o["first_t"].get("dragon", np.nan) / 60))
    S = pd.DataFrame(rows, columns=["z", *ROLES, *[f"kd_{r}" for r in ROLES], *[f"kb_{r}" for r in ROLES], *[f"kr_{r}" for r in ROLES], "fd", "fdmin"])
    R[vn] = summary(S[ROLES], S[[f"kd_{r}" for r in ROLES]].set_axis(ROLES, axis=1), S[[f"kb_{r}" for r in ROLES]].set_axis(ROLES, axis=1),
                    S[[f"kr_{r}" for r in ROLES]].set_axis(ROLES, axis=1), S.fd, S.z.values, S.fdmin.values)
json.dump(R, open(OUT, "w"), indent=1)
for k_ in [k for k in R if isinstance(R[k], dict)]:
    print("\n==", k_)
    for a, b in R[k_].items(): print("  ", a, b)
