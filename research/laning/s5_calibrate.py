"""Calibrate the laning module's strength gain on training games (16 Nov 2026 AEST; Luke: rerun who-wins with the module's own calibration).
Same method as research/sim3/s3_test.py part B: 300 major-league games before 1 Sep (same random draw, seed 7), 24 sims each; fit
real win ~ logistic(a + b x v1 log-odds) on the simulated games' blue wins; gain <- gain / max(0.3, b)^0.8, until b is 1 (the sim's win
chance moves with strength as real results do). Module tables: research/local/laning/params/laning_train.json (fitted before 1 Sep).
Everything else as the current sim with death timers (research/local/sim4/spread/w_dt). Also reports the team gold edge at 15 and its
link to strength, real v sim, for each step.
usage (repo root): python -I research/laning/s5_calibrate.py [iterations=6]   (writes research/model/laning/calibration.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from lib import config, data, simsetup, fit
from lib.runlog import Run
IT = int(sys.argv[1]) if len(sys.argv) > 1 else 6
with Run("laning_calibrate", params={"iterations": IT}, inputs=[config.OE_CSV, config.R / "sim3" / "s3_sim.py", config.R / "local" / "laning" / "inputs_train.json"]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "result", "golddiffat15"]); data.check(o)
    B = o[(o.side == "Blue") & (o.position == "team")].set_index("gameid")
    IT_ = json.load(open(config.R / "local" / "laning" / "inputs_train.json")); XS = simsetup.inputs()
    train = sorted(g for g in IT_ if g in XS and g in B.index)
    tr = list(np.random.default_rng(7).choice(train, size=min(300, len(train)), replace=False))
    y = np.array([float(B.result[g]) for g in tr]); z = np.array([XS[g]["z"] for g in tr]); g15r = np.array([B.golddiffat15[g] for g in tr], float)
    sim = simsetup.sim_module(); P = simsetup.params({"typed", "ll", "fdt", "fpl", "dt"}); P["laning"] = json.load(open(config.R / "local" / "laning" / "params" / "laning_train.json"))
    cal = dict(simsetup.cal_default(), laning="actions"); hist = []
    okr = ~np.isnan(g15r)
    for it in range(IT):
        S = sim.Sim(P, cal); wins, zs, g15 = [], [], []
        for g in tr:
            x = dict(XS[g]); x["la"] = IT_[g]
            for j in range(24):
                r = S.run(x, 10_000_000 * (it + 1) + simsetup.seed(g, j) % 10_000_000); wins.append(r["winner"] == "blue"); zs.append(x["z"]); g15.append(r["g15"])
        b = fit.logistic(np.c_[np.ones(len(zs)), zs], np.array(wins, float)); g15 = np.array(g15); ok = ~np.isnan(g15)
        hist.append({"iter": it, "gain": cal["gain"], "win_slope_on_v1": round(float(b[1]), 3), "win_intercept": round(float(b[0]), 3),
                     "team_gd15_sd sim / real": [round(float(g15[ok].std())), round(float(g15r[okr].std()))],
                     "team_gd15 per v1 sim / real": [round(float(np.polyfit(np.array(zs)[ok], g15[ok], 1)[0])), round(float(np.polyfit(z[okr], g15r[okr], 1)[0]))]})
        print(hist[-1], flush=True)
        if abs(b[1] - 1) < 0.03 or it == IT - 1: break
        cal["gain"] = round(cal["gain"] / max(0.3, b[1]) ** 0.8, 3)
    run.result("gain", cal["gain"]); run.save_json(config.MODEL_DIR / "laning" / "calibration.json", {"cal": cal, "history": hist, "training games": len(tr), "sims each": 24})
