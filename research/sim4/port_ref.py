"""Sim session 4 (13 Nov 2026): reference runs for checking the JS port (js/sim-engine.js) against research/sim3/s3_sim.py.
Builds each game's inputs exactly as s3_test.py does, runs N seeded Python sims per game for each version, and writes one JSON with
the tables (P), each version's calibration, the inputs and the Python summary. research/sim4/port_check.html runs the same games in JS.
usage (repo root): python -I research/sim4/port_ref.py params3.json fighttypes.json ll_dir lanes3_features.csv comp3_games.csv v1_games.csv
                   cal_dir_base cal_dir_typed_pf_ll <out_json> [n=1000] [games=12]"""
import os, sys, json, importlib.util
import numpy as np, pandas as pd
PJ, FTJ, LLD, FE, CO, V1, CB, CT, OUT = sys.argv[1:10]; N = int(sys.argv[10]) if len(sys.argv) > 10 else 1000; NG = int(sys.argv[11]) if len(sys.argv) > 11 else 12
HERE = os.path.dirname(os.path.abspath(__file__)); ROLES = ["top", "jng", "mid", "bot", "sup"]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "..", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); P["fight_typed"] = json.load(open(FTJ)); P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json")))
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid"); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
v1 = pd.read_csv(V1).set_index("gameid")
wl = sorted(g for g in fe[fe.league == "WLDs"].gameid.unique() if g in m0.index and g in comp.index)
pick = ["LOLTMNT02_487213"] + [g for g in np.random.default_rng(3).choice(wl, size=NG * 2, replace=False) if g != "LOLTMNT02_487213"][:NG - 1]
X = {}
for g in pick:
    d = fe[fe.gameid == g].set_index("position").reindex(ROLES); c = comp.loc[g]
    e0c = [f"e0_{r}" if f"e0_{r}" in m0.columns else f"m0_{r}" for r in ROLES]
    X[g] = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
            "siege_d": float(c.siege_blue - c.siege_red), "obj_d": float(c.objectives_blue - c.objectives_red), "skirm_d": float(c.skirmish_blue - c.skirmish_red),
            "pace_s": float(c.pace_blue + c.pace_red), "siege_s": float(c.siege_blue + c.siege_red), "obj_s": float(c.objectives_blue + c.objectives_red),
            "ll_m0": m0.loc[g, [f"m0_{r}" for r in ROLES]].tolist(), "ll_e0": m0.loc[g, e0c].tolist(), "real_blue_win": int(v1.blue_win.get(g, -1))}
cals = {"base": json.load(open(os.path.join(CB, "test3_results.json")))["cal"], "typed_pf_ll": json.load(open(os.path.join(CT, "test3_results.json")))["cal"]}
def summ(rows):
    a = np.array(rows, float)
    return {"n": len(a), "blue_win": a[:, 0].mean(), "len_min": a[:, 1].mean(), "len_sd": a[:, 1].std(), "kills": a[:, 2].mean(), "kills_sd": a[:, 2].std(),
            "towers": a[:, 3].mean(), "dragons": a[:, 4].mean(), "barons": a[:, 5].mean(), "g15": float(np.nanmean(a[:, 6])), "g15_sd": float(np.nanstd(a[:, 6])), "under15": float(np.isnan(a[:, 6]).mean()), "capped": a[:, 7].mean()}
res = {}
for v, cal in cals.items():
    sim = sm.Sim(P, cal); res[v] = {}
    for g in pick:
        rows = []
        for j in range(N):
            o = sim.run(X[g], seed=1 + j)
            rows.append((o["winner"] == "blue", o["sec"] / 60, sum(o["kills"]), sum(o["towers"]), len(o["dr"][0]) + len(o["dr"][1]), sum(o["ba"]), o["g15"], o["capped"]))
        res[v][g] = summ(rows); print(v, g, {k: round(x, 3) for k, x in res[v][g].items()}, flush=True)
json.dump({"P": P, "cal": cals, "x": X, "py": res, "n": N}, open(OUT, "w"))
