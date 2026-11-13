"""Replay check (13 Nov 2026): an edited research/sim3/s3_sim.py must replay a saved earlier copy exactly when its new options are off.
Runs both on the port_ref.json games and versions, N seeds each, and compares every output field (with the play-by-play log).
usage (repo root): python -I research/sim4/replay_check.py <old s3_sim.py copy> port_ref.json [n_seeds=54]"""
import sys, json, importlib.util
OLD, RJ = sys.argv[1:3]; NS = int(sys.argv[3]) if len(sys.argv) > 3 else 54
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
old, new = load(OLD, "sim_old"), load("research/sim3/s3_sim.py", "sim_new")
R = json.load(open(RJ)); res = {}
for v, cal in R["cal"].items():
    so, sn = old.Sim(R["P"], cal), new.Sim(R["P"], cal); same = n = 0
    for g, x in R["x"].items():
        for j in range(NS):
            a = json.dumps(so.run(x, seed=1 + j, log=True), sort_keys=True, default=str); b = json.dumps(sn.run(x, seed=1 + j, log=True), sort_keys=True, default=str)
            n += 1; same += a == b
    res[v] = f"{same} of {n} identical"
print(res)
