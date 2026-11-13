"""Test 2 (13 Nov 2026 AEST; Luke's note 4: first dragon goes with side, comp and bot-lane or jungle pressure): does the sim give the first
dragon to the team ahead in bot lane as often as real games do? Read-only; nothing in the sim changes.
Real: the file's held-out games (from 1 Sep) and Worlds: blue takes the first dragon ~ side + v1 + gold at 10 per 1k for jungle, mid and the
bot duo (logistic). Sim (seeds by game ID, as s3_test.py): the same games' inputs (built as s3_test.py does, tables fitted before 1 Sep), N seeded sims each, the same logistic
on the sim's own gold at 10 and first dragon; for the current default and the fight-players version.
usage (repo root): python -I research/sim4/test_dragon_botlane.py <OE csv> params_dir ll_dir lanes3_features.csv comp3_games.csv v1_games.csv
                   cal_default.json cal_fp.json <out_json> [n=100]"""
import os, sys, json, zlib, importlib.util
import numpy as np, pandas as pd
CSV, PD, LLD, FE, CO, V1, CD, CF, OUT = sys.argv[1:10]; N = int(sys.argv[10]) if len(sys.argv) > 10 else 100
ROLES = ["top", "jng", "mid", "bot", "sup"]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join("research", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(os.path.join(PD, "params3.json"))); P["fight_typed"] = json.load(open(os.path.join(PD, "fighttypes.json")))
P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); P["early_kills"] = json.load(open(os.path.join(PD, "earlykills.json"))); P["fight_players"] = json.load(open(os.path.join(PD, "participants.json")))
_fd = os.path.join(PD, "firstdragon.json")
if os.path.exists(_fd): _j = json.load(open(_fd)); P["taker_first_dragon"] = {"side": _j["taker"], "timing": _j["taker_timing"]}
ONLY = os.environ.get("ONLY_VERSION")  # run just this sim version (13 Nov: the first-dragon taker)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid"); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid"); v1 = pd.read_csv(V1).set_index("gameid")
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "side", "position", "golddiffat10", "firstdragon"])
blue = raw[raw.side == "Blue"]; gd10 = blue[blue.position.isin(ROLES)].pivot_table(index="gameid", columns="position", values="golddiffat10")
fd = blue[blue.position == "team"].set_index("gameid").firstdragon
games = sorted(g for g in fe[fe.day >= "2026-09-01"].gameid.unique() if g in m0.index and g in comp.index and g in gd10.index)
X, info = {}, {}
for g in games:
    d = fe[fe.gameid == g].set_index("position").reindex(ROLES); c = comp.loc[g]
    if d.z_v1.isna().any(): continue
    e0c = [f"e0_{r}" if f"e0_{r}" in m0.columns else f"m0_{r}" for r in ROLES]
    X[g] = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
            "siege_d": float(c.siege_blue - c.siege_red), "obj_d": float(c.objectives_blue - c.objectives_red), "skirm_d": float(c.skirmish_blue - c.skirmish_red),
            "pace_s": float(c.pace_blue + c.pace_red), "siege_s": float(c.siege_blue + c.siege_red), "obj_s": float(c.objectives_blue + c.objectives_red),
            "ll_m0": m0.loc[g, [f"m0_{r}" for r in ROLES]].tolist(), "ll_e0": m0.loc[g, e0c].tolist()}
    info[g] = d.league.iloc[0]
def logit(Xm, y):
    b = np.zeros(Xm.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-Xm @ b)); H = Xm.T @ (Xm * (p * (1 - p))[:, None]) + 1e-6 * np.eye(len(b)); b += np.linalg.solve(H, Xm.T @ (y - p))
    p = 1 / (1 + np.exp(-Xm @ b)); se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ (Xm * (p * (1 - p))[:, None]) + 1e-6 * np.eye(len(b)))))
    return {k: f"{v:+.3f} (se {s:.3f})" for k, v, s in zip(["blue side", "v1", "jungle", "mid", "bot duo"], b, se)}
R = {"games": len(X), "sims_per_game": N}
for nm, sel in {"from 1 Sep": lambda g: True, "Worlds": lambda g: info[g] == "WLDs"}.items():
    gs = [g for g in X if sel(g)]; d = gd10.loc[gs]
    R[f"real, {nm}"] = {"games": len(gs), "blue share": round(float(fd.loc[gs].mean()), 3),
                        **logit(np.c_[np.ones(len(gs)), [X[g]["z"] for g in gs], d.jng / 1000, d["mid"] / 1000, (d.bot + d.sup) / 1000], fd.loc[gs].values.astype(float))}
VERS = [("sim: default now", CD, {}), ("sim: fight players + early counts + event order", CF, {"fight_players": "on", "early_kills": "counts", "event_order": "on"}),
        ("sim: fight players + early counts + event order + first-dragon taker", CF, {"fight_players": "on", "early_kills": "counts", "event_order": "on", "first_dragon_taker": "on"})]
for vn, cf, extra in [v_ for v_ in VERS if ONLY is None or ONLY in v_[0]]:
    cal = dict(json.load(open(cf))["cal"], **extra); sim = sm.Sim(P, cal); rows = []
    for g in X:
        for j in range(N):
            o = sim.run(X[g], seed=500_000 + zlib.crc32(g.encode()) * 10_000 + j); r10 = o["roles10"]  # seeds by game ID (13 Nov fix: shared seeds gave every game the same lane draws)
            if o["first"].get("dragon") is None or any(np.isnan(r10)): continue
            rows.append((info[g], X[g]["z"], r10[1], r10[2], r10[3] + r10[4], 1.0 if o["first"]["dragon"] == "blue" else 0.0))
    S = pd.DataFrame(rows, columns=["league", "z", "jng", "mid", "bot", "y"])
    for nm, m in {"from 1 Sep": np.ones(len(S), bool), "Worlds": (S.league == "WLDs").values}.items():
        d = S[m]; R[f"{vn}, {nm}"] = {"sim games": len(d), "blue share": round(float(d.y.mean()), 3),
                                    **logit(np.c_[np.ones(len(d)), d.z, d.jng / 1000, d["mid"] / 1000, d.bot / 1000], d.y.values)}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
