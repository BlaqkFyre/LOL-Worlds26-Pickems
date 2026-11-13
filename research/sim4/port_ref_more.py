"""More Python sims for the port check (13 Nov): one version, seeds from an offset, pooled means over the port_ref.json games.
usage: python -I research/sim4/port_ref_more.py port_ref.json <version> <n> <seed_offset> <out_json>"""
import os, sys, json, importlib.util
import numpy as np
RJ, V, N, OFF, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "..", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
R = json.load(open(RJ)); sim = sm.Sim(R["P"], R["cal"][V]); rows = []
for g, x in R["x"].items():
    for j in range(N):
        o = sim.run(x, seed=OFF + j)
        rows.append((o["winner"] == "blue", o["sec"] / 60, sum(o["kills"]), sum(o["towers"]), len(o["dr"][0]) + len(o["dr"][1]), sum(o["ba"]), o["g15"]))
a = np.array(rows, float); ks = ["blue_win", "len_min", "kills", "towers", "dragons", "barons", "g15"]
res = {k: [float(np.nanmean(a[:, i])), float(np.nanstd(a[:, i])), int((~np.isnan(a[:, i])).sum())] for i, k in enumerate(ks)}
json.dump({"version": V, "n_per_game": N, "offset": OFF, "pooled": res}, open(OUT, "w"), indent=1); print(res)
