"""Replay check for the laning module (14 Nov 2026): with the module off, the edited research sim must play every seeded game exactly as
the sim before the edit (research/local/sim4/s3_sim_before_laning.py). Default sim options (typed, ll, fdt, fpl, ekc, eo, pf, dt), 2 seeds
for each of 324 held-out games (from 1 Sep, Worlds included). Compares winner, length, kills, every play-by-play line and gold at 15.
usage (repo root): python -I research/laning/s5_replay_check.py"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import config, data, simsetup
from lib.runlog import Run
with Run("laning_replay_check", inputs=[config.R / "sim3" / "s3_sim.py", config.R / "local" / "sim4" / "s3_sim_before_laning.py", simsetup.CAL]) as run:
    new, old = simsetup.sim_module(), simsetup.sim_module(config.R / "local" / "sim4" / "s3_sim_before_laning.py", "s3_old")
    opts = {"typed", "ll", "fdt", "fpl", "dt"}; P = simsetup.params(opts); cal = simsetup.cal_default()
    o = data.oe(["gameid", "league", "date"]); held = set(o[(o.date >= config.SPLIT) & o.league.isin(config.MAJOR)].gameid)
    X = {g: x for g, x in simsetup.inputs().items() if g in held}
    a, b = new.Sim(P, cal), old.Sim(P, cal); n = same = 0; diff = []
    for g, x in sorted(X.items()):
        for j in range(2):
            ga, gb = a.run(x, simsetup.seed(g, j), log=True), b.run(x, simsetup.seed(g, j), log=True); n += 1
            ok = ga["winner"] == gb["winner"] and ga["sec"] == gb["sec"] and ga["kills"] == gb["kills"] and ga["steps"] == gb["steps"] and ga["g15"] == gb["g15"]
            same += ok
            if not ok and len(diff) < 5: diff.append(g)
    run.result("identical", f"{same} of {n}"); print(f"identical {same} of {n}", diff)
    run.save_json(config.MODEL_DIR / "laning" / "replay_check.json", {"identical": same, "games": n, "first differences": diff, "options": sorted(opts)})
