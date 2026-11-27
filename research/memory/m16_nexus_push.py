"""Nexus timing, step 3 groundwork (27 Nov 2026 AEST; Luke away: "work on playtest and then the Nexus timing"). In v54 the Nexus falls a
median 30 s after a won fight's last kill (real 14), so more Nexus tries miss the losers' respawn and games run long. Each part of the
push matches real on its own (m14), so this measures the push by the state of the losers' base when the fight ends:
  fights and pushes as m14 (kills under 20 s apart, winner = more kills, push = the winner's structures from the fight's start until the
  next fight starts or 120 s after its last kill).
  base state of the losers at the fight's last kill, from the timeline's structure events: inhibitors down (back after 300 s, the
  app's INHIB_BACK), nexus towers down (back after 180 s, the app's NEXUS_TURRET_BACK), lanes open (T3 tower down).
  "structures left to the Nexus" = nexus towers standing + (1 if no inhibitor is down); only for fights with a lane open.
  measured by that count (0, 1, 2, 3): won fights, share whose push takes the Nexus, Nexus from the last kill, structures the
  push takes before the Nexus, the push's first structure from the last kill, and the gaps by pair (inhib > nexus tower,
  nexus tower > nexus tower, nexus tower > Nexus, inhib > Nexus).
Games: gol.gg timelines, training (before config.SPLIT) and all 640. Nothing in the app is written.
Output: research/model/memory/m16_nexus_push.json.
usage (repo root): python -I research/memory/m16_nexus_push.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from lib import config, data
from lib.runlog import Run

OUT = config.MODEL_DIR / "memory"
STR = {"tower", "inhib", "nexus"}
QS = [.1, .25, .5, .75, .9]
INHIB_BACK, NXT_BACK = 300, 180
r3 = lambda x: round(float(x), 3)
qq = lambda a: [round(float(v), 1) for v in np.quantile(a, QS)] if len(a) else None

def kind(ty, det):
    d = str(det)
    if ty == "nexus": return "nexus"
    if ty == "inhib": return "inhib"
    if "NEXUS" in d: return "nxt"
    if d.startswith("T3"): return "T3"
    return "outer"

def pushes(ev, gids):
    E = ev[ev.gid.isin(gids)].sort_values(["gid", "t"]); P = []
    for g, d in E.groupby("gid"):
        k = d[d.type == "kill"]; s = d[d.type.isin(STR)]
        if not len(k): continue
        sk = [(float(t), sd, kind(ty, de)) for t, sd, ty, de in zip(s.t, s.side, s.type, s.detail)]
        kt, ks = k.t.values.astype(float), k.side.values
        grp = np.cumsum(np.r_[True, np.diff(kt) > 20]); F = []
        for gi in np.unique(grp):
            m = grp == gi; nb, nr = int((ks[m] == "blue").sum()), int((ks[m] == "red").sum())
            F.append((kt[m].min(), kt[m].max(), "blue" if nb > nr else "red" if nr > nb else None))
        for i, (t0, t1, w) in enumerate(F):
            if w is None: continue
            # the losers' base when the fight ends (structures the winner took before t1)
            mine = [(t, kd) for t, sd, kd in sk if sd == w and t <= t1]
            t3 = sum(1 for t, kd in mine if kd == "T3"); inh = sum(1 for t, kd in mine if kd == "inhib" and t > t1 - INHIB_BACK)
            nxd = min(2, sum(1 for t, kd in mine if kd == "nxt" and t > t1 - NXT_BACK))
            end = min(F[i + 1][0] if i + 1 < len(F) else 1e9, t1 + 120)
            x = [(t, kd) for t, sd, kd in sk if sd == w and t0 <= t < end]
            # structures that fell during the fight before t1 are part of the push: count the state from the fight's start instead
            pre = [(t, kd) for t, kd in mine if t < t0]
            t3s = sum(1 for t, kd in pre if kd == "T3"); inhs = sum(1 for t, kd in pre if kd == "inhib" and t > t0 - INHIB_BACK)
            nxs = min(2, sum(1 for t, kd in pre if kd == "nxt" and t > t0 - NXT_BACK))
            left = (2 - nxs) + (0 if inhs else 1) if t3s else None
            P.append({"t0": t0, "t1": t1, "left": left, "x": x})
    return P

def gaps(P, a, b):
    out = []
    for p in P:
        x = p["x"]
        for j in range(1, len(x)):
            if x[j - 1][1] == a and x[j][1] == b: out.append(x[j][0] - x[j - 1][0])
    return qq(out), len(out)

def summary(P):
    R = {}
    for L in (0, 1, 2, 3):
        S = [p for p in P if p["left"] == L]; nx = [p for p in S if any(kd == "nexus" for t, kd in p["x"])]
        nxk = [next(t for t, kd in p["x"] if kd == "nexus") - p["t1"] for p in nx]
        before = [sum(1 for t, kd in p["x"][:[kd for t, kd in p["x"]].index("nexus")]) for p in nx]
        first = [p["x"][0][0] - p["t1"] for p in S if p["x"]]
        R[f"{L} left"] = {"won fights": len(S), "push takes the Nexus": r3(len(nx) / len(S)) if S else None,
            "Nexus from the last kill s (10/25/50/75/90%)": qq(nxk), "structures before the Nexus (10/25/50/75/90%)": qq(before),
            "first structure from the last kill s": qq(first), "pushes with a structure": len(first)}
    R["gaps s (10/25/50/75/90%), n"] = {f"{a} > {b}": gaps(P, a, b) for a, b in
        (("T3", "inhib"), ("inhib", "nxt"), ("nxt", "nxt"), ("nxt", "nexus"), ("inhib", "nexus"), ("T3", "nxt"))}
    nx_all = [p for p in P if any(kd == "nexus" for t, kd in p["x"])]
    R["pushes ending in the Nexus, by structures left at the fight's start (0, 1, 2, 3, lane closed)"] = [sum(1 for p in nx_all if p["left"] == L) for L in (0, 1, 2, 3, None)]
    return R

with Run("memory_nexus_push", params={"fight_gap_s": 20, "push_until_s_after_last_kill": 120, "inhib_back": INHIB_BACK, "nexus_tower_back": NXT_BACK},
         inputs=[config.TL_MATCH, config.TL_EVENTS]) as run:
    tm, ev, _ = data.timelines()
    train = set(tm.gid[tm.day < config.SPLIT]); allg = set(tm.gid)
    R = {"training games (before 1 Sep)": summary(pushes(ev, train)), "all 640 timelines": summary(pushes(ev, allg))}
    run.result("training pushes ending in the Nexus", sum(R["training games (before 1 Sep)"]["pushes ending in the Nexus, by structures left at the fight's start (0, 1, 2, 3, lane closed)"]))
    run.save_json(OUT / "m16_nexus_push.json", R)
    import json; print(json.dumps(R["all 640 timelines"], indent=1))
