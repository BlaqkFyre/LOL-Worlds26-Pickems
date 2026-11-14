"""Early fight sizes and fights after an ace (14 Nov 2026 AEST, read-only; Luke's game: a 7-kill teamfight at 6:23).
Real held-out timeline games from 1 Sep v the sim (seeds by game ID; given calibration and options). Fights = kills 20 s+ apart start a new one.
  1 share of games with a fight of 4+ / 6+ kills before 10:00, and the largest fight before 10:00
  2 fights by size and window (0-9:59, 10-19:59, 20+): share of fights with 4+ kills
  3 what a side does in the 60 s after it kills 4+ enemies in one fight from 20:00 (real: structures, objectives, another fight)
usage (repo root): python -I research/sim4/early_fights_check.py params3.json test3_results.json lanes3_features.csv tl_events.csv tl_match.csv ll_dir <out_json> [n=4] [opts]"""
import os, sys, json, zlib, importlib.util
import numpy as np, pandas as pd
PJ, CJ, FE, TE, TM, LLD, OUT = sys.argv[1:8]; N = int(sys.argv[8]) if len(sys.argv) > 8 else 4
OPTS = set(sys.argv[9].split(",")) if len(sys.argv) > 9 else set(); ROLES = ["top", "jng", "mid", "bot", "sup"]
tm = pd.read_csv(TM, dtype={"gid": str}).dropna(subset=["gameid"]); fe = pd.read_csv(FE); tm = tm[(tm.date >= "2026-09-01") & tm.gameid.isin(fe.gameid)]
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(tm.gid)]
def fights(kills):
    kt = sorted(kills); out = []
    for x in kt:
        if out and x[0] - out[-1][-1][0] <= 20: out[-1].append(x)
        else: out.append([x])
    return out
def game(kills, other):
    F = fights(kills); r = {"early_max": max([len(f) for f in F if f[0][0] < 600], default=0), "sizes": [(f[0][0], len(f)) for f in F], "after_ace": []}
    for f in F:
        for s in (0, 1):
            if f[0][0] >= 1200 and sum(1 for x in f if x[1] == s) >= 4:
                t1 = f[-1][0]; r["after_ace"].append((int(any(t1 < t <= t1 + 60 and sd == s and k in ("struct",) for t, sd, k in other)),
                                                      int(any(t1 < t <= t1 + 60 and sd == s and k == "mon" for t, sd, k in other)),
                                                      int(any(t1 < x[0] <= t1 + 60 for x in kills))))
    return r
def summ(rows):
    em = np.array([r["early_max"] for r in rows]); sz = [s for r in rows for s in r["sizes"]]; S = pd.DataFrame(sz, columns=["t", "n"])
    S["w"] = pd.cut(S.t, [-1, 599, 1199, 1e9], labels=["0-9:59", "10-19:59", "20+"])
    aa = np.array([a for r in rows for a in r["after_ace"]]) if any(r["after_ace"] for r in rows) else np.zeros((0, 3))
    return {"games with a 4+ kill fight before 10:00": round(float((em >= 4).mean()), 3), "games with a 6+ kill fight before 10:00": round(float((em >= 6).mean()), 4),
            "share of fights with 4+ kills by window": {str(w): [round(float((d.n >= 4).mean()), 3), len(d)] for w, d in S.groupby("w", observed=True)},
            "mean fight size by window": {str(w): round(float(d.n.mean()), 2) for w, d in S.groupby("w", observed=True)},
            "after a side kills 4+ in one fight from 20:00 (within 60 s): structure / objective / another kill": [round(float(x), 3) for x in aa.mean(axis=0)] + [len(aa)]}
real = []
for g in tm.itertuples():
    e = ev[ev.gid == g.gid]; sd = lambda x: 0 if x == "blue" else 1
    other = [(x.t, sd(x.side), "struct") for x in e[e.type.isin(["tower", "inhib", "nexus"])].itertuples()] + [(x.t, sd(x.side), "mon") for x in e[e.type.isin(["dragon", "baron", "herald"])].itertuples()]
    real.append(game([(x.t, sd(x.side)) for x in e[e.type == "kill"].itertuples()], other))
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join("research", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; PD_ = os.path.dirname(PJ)
if "typed" in OPTS: P["fight_typed"] = json.load(open(os.path.join(PD_, "fighttypes.json")))
if "ll" in OPTS: P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
if "fpl" in OPTS: P["fight_players"] = json.load(open(os.path.join(PD_, "participants.json")))
if "ekc" in OPTS: P["early_kills"] = json.load(open(os.path.join(PD_, "earlykills.json")))
if "fdt" in OPTS: _fd = json.load(open(os.path.join(PD_, "firstdragon.json"))); P["taker_first_dragon"] = {"side": _fd["taker"], "timing": _fd["taker_timing"]}
if "dt" in OPTS: P["death_timer"] = json.load(open(os.path.join(PD_, "deathtimer.json"))); cal["death_timers"] = "on"
if "dp" in OPTS: P["dead_push"] = json.load(open(os.path.join(PD_, "deadpush_sim.json"))); cal["dead_push"] = "on"
sim = sm.Sim(P, cal); simr = []
for g in tm.itertuples():
    d = fe[fe.gameid == g.gameid].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if "ll" in OPTS: x["ll_m0"] = m0.loc[g.gameid, [f"m0_{r}" for r in ROLES]].tolist(); x["ll_e0"] = m0.loc[g.gameid, [f"e0_{r}" for r in ROLES]].tolist()
    for j in range(N):
        o = sim.run(x, seed=zlib.crc32(g.gameid.encode()) * 10_000 + 444 + j, log=True); kl, other = [], []
        for s_ in o["steps"]:
            sd = 0 if s_["side"] == "blue" else 1
            if s_["kind"] == "kill": kl.append((s_["t"], sd))
            elif s_["kind"] in ("tower", "inhib", "nexus"): other.append((s_["t"], sd, "struct"))
            elif s_["kind"] in ("dragon", "baron", "herald", "elder"): other.append((s_["t"], sd, "mon"))
        simr.append(game(kl, other))
R = {"games": {"real": len(real), "sim": len(simr)}, "opts": sorted(OPTS), "real": summ(real), "sim": summ(simr)}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
