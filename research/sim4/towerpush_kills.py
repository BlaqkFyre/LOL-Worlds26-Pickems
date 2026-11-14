"""Spread work (14 Nov 2026 AEST, read-only): do real tower pushes (outer, inner, inhibitor towers) run further after kills?
Pushes = a side's tower segments (gol.gg plates, 5 per tower) in one lane less than 30 s apart, as research/sim3/s3_rates.py. For each push:
the tier it starts on, the side's own kills in the start minute (0 / 1-2 / 3+), from 14:00 on (after plates). The sim draws the size from
real pushes by starting tier only. Also: does the push take a whole tower, and does it run on past the tower it started on.
usage (repo root): python -I research/sim4/towerpush_kills.py tl_match.csv tl_events.csv <out_json>"""
import sys, json
import numpy as np, pandas as pd
TM, TE, OUT = sys.argv[1:4]
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
M["split"] = np.where(M.date < "2026-09-01", "train", "test"); info = M.set_index("gid")
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)]
rows = []
for g, e in ev.groupby("gid"):
    kt = e[e.type == "kill"].t.values; ks = e[e.type == "kill"].side.values
    for (sd, ln), d in e[e.type == "plate"].sort_values("t").groupby(["side", "detail"]):
        tt = d.t.values; i = 0
        while i < len(tt):
            j = i
            while j + 1 < len(tt) and tt[j + 1] - tt[j] <= 30: j += 1
            m0 = int(tt[i] // 60)
            if m0 >= 14:
                ok = int(((ks == sd) & (kt >= 60 * m0) & (kt < 60 * m0 + 60)).sum())
                rows.append((info.split.get(g, "?"), i // 5, j - i + 1, ok, int((j + 1) // 5 > i // 5 + (1 if i % 5 == 0 and False else 0)), int(j // 5 > i // 5)))
            i = j + 1
D = pd.DataFrame(rows, columns=["split", "tier0", "size", "ok", "x", "past"]); D["kg"] = np.select([D.ok == 0, D.ok <= 2], ["0", "1-2"], "3+")
R = {}
for s in ("train", "test"):
    R[s] = {f"T{t + 1}|{kg}": {"n": len(q), "mean segments": round(float(q["size"].mean()), 2), "runs past its tower": round(float(q.past.mean()), 3)}
            for (t, kg), q in D[D.split == s].groupby(["tier0", "kg"])}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
