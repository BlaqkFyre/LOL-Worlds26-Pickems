"""Laning module diagnosis (15 Nov 2026 AEST; Luke: fix jungle and support lanes and the mid / ADC spread, then the team gold link).
Splits each role's gold edge at 15 into its farm part (CS edge x gold per CS) and everything else (kills, assists, plates, turrets,
quest, objectives), real (Oracle's Elixir: csdiffat15, golddiffat15) v the laning module (research sim, Worlds day-by-day tables, seeds by
game ID). For each part and role: spread, and how well the module's average per game lines up with the real one (correlation).
Also, real and module: how each part depends on that role's pre-game expected edges (CS and gold, the lane model) and on team strength.
usage (repo root): python -I research/laning/s5_lane_parts.py [sims per game=100]   (writes research/model/laning/lane_parts.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data, simsetup
from lib.runlog import Run
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
with Run("lane_parts", params={"sims_per_game": N}, inputs=[config.OE_CSV, config.R / "sim3" / "s3_sim.py", config.R / "local" / "laning" / "inputs.json"]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "csdiffat15", "golddiffat15", "killsat15", "deathsat15", "opp_killsat15", "opp_deathsat15"]); data.check(o)
    W = o[(o.league == "WLDs") & (o.side == "Blue") & o.position.isin(config.ROLES)]
    IN = json.load(open(config.R / "local" / "laning" / "inputs.json")); XS = simsetup.inputs(); games = [g for g in IN if g in XS]
    sim = simsetup.sim_module(); P0 = simsetup.params({"typed", "ll", "fdt", "fpl", "dt"}); cal = dict(simsetup.cal_default(), laning="actions")
    rows = []
    for g in games:
        P = dict(P0); P["laning"] = json.load(open(config.R / "local" / "laning" / "params" / f"laning_{IN[g]['day']}.json")); gpc = P["laning"]["gold_per_cs"]
        x = dict(XS[g]); x["la"] = IN[g]; S = sim.Sim(P, cal); rr = [S.run(x, simsetup.seed(g, j)) for j in range(N)]
        real = W[W.gameid == g].set_index("position")
        for i, r in enumerate(config.ROLES):
            cs = np.array([q["la_cs15"][i] for q in rr]); gd = np.array([q["roles15"][i] for q in rr]); ok = ~np.isnan(cs) & ~np.isnan(gd)
            rows.append({"gameid": g, "role": r, "z": XS[g]["z"], "pre_cs": IN[g]["pre_cs"][i], "pre_gold": IN[g]["pre_gold"][i],
                         "real_farm": real.loc[r].csdiffat15 * gpc, "real_rest": real.loc[r].golddiffat15 - real.loc[r].csdiffat15 * gpc,
                         "sim_farm_mean": float(np.mean(cs[ok] * gpc)), "sim_rest_mean": float(np.mean(gd[ok] - cs[ok] * gpc)),
                         "real_kd": real.loc[r].killsat15 - real.loc[r].deathsat15, "sim_kd": float(np.mean([q["kd15"][i] for q in rr])),
                         "sim_farm_sd": float(np.std(cs[ok] * gpc)), "sim_rest_sd": float(np.std(gd[ok] - cs[ok] * gpc)), "sim_farm_all": (cs[ok] * gpc).tolist(), "sim_rest_all": (gd[ok] - cs[ok] * gpc).tolist()})
        print(".", end="", flush=True)
    D = pd.DataFrame(rows); R = {"games": len(games), "sims per game": N}
    D.drop(columns=["sim_farm_all", "sim_rest_all"]).to_csv(config.R / "local" / "laning" / "lane_parts_rows.csv", index=False)
    def joint(d, y):  # y on pre-game expected gold edge (per 1k) and team strength together
        X = np.c_[np.ones(len(d)), d.pre_gold / 1000, d.z]; b = np.linalg.lstsq(X, d[y].values, rcond=None)[0]; return [round(float(b[1]), 2), round(float(b[2]), 2)]
    for r, d in D.groupby("role"):
        sf = np.concatenate(d.sim_farm_all.values); sr = np.concatenate(d.sim_rest_all.values)
        slope = lambda y, xcol: round(float(np.polyfit(d[xcol], y, 1)[0]), 2)
        R[r] = {"farm part: spread real / module": [round(float(d.real_farm.std())), round(float(np.std(sf)))],
                "other part: spread real / module": [round(float(d.real_rest.std())), round(float(np.std(sr)))],
                "farm part: correlation of the module's game average with real": round(float(d.sim_farm_mean.corr(d.real_farm)), 3),
                "other part: correlation of the module's game average with real": round(float(d.sim_rest_mean.corr(d.real_rest)), 3),
                "other part per 1k of pre-game expected gold edge: real / module": [slope(d.real_rest, "pre_gold") * 1000, slope(d.sim_rest_mean, "pre_gold") * 1000],
                "other part per unit of team strength: real / module": [slope(d.real_rest, "z"), slope(d.sim_rest_mean, "z")],
                "farm part per unit of team strength: real / module": [slope(d.real_farm, "z"), slope(d.sim_farm_mean, "z")],
                "kills minus deaths by 15, per 1k of pre-game expected gold edge: real / module": [round(float(np.polyfit(d.pre_gold / 1000, d.real_kd, 1)[0]), 2), round(float(np.polyfit(d.pre_gold / 1000, d.sim_kd, 1)[0]), 2)],
                "kills minus deaths by 15, per unit of team strength: real / module": [slope(d.real_kd, "z"), slope(d.sim_kd, "z")],
                "kills minus deaths by 15, together [per 1k pre-game, per unit strength]: real / module": [joint(d, "real_kd"), joint(d, "sim_kd")],
                "other gold, together [per 1k pre-game, per unit strength]: real / module": [joint(d, "real_rest"), joint(d, "sim_rest_mean")]}
    print(); print(json.dumps(R, indent=1))
    run.save_json(config.MODEL_DIR / "laning" / "lane_parts.json", R)
