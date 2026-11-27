"""Shared helpers for the base push research (27 Nov 2026 AEST), copied exactly from m17_base_push_state.py (which keeps its own copies,
so its results stay reproducible as run): structure kinds, the two input copies, s3_rates.py run quietly, death intervals on the
official timer, structures left to the Nexus, the per-minute state inputs and their column builders."""
import sys, os, contextlib, io, runpy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config

APP_CUT = "2026-11-10"
L3 = config.R / "local" / "sim3"
INP = {"research": {"cut": None, "v1": config.R / "model" / "sim2" / "v1_games.csv", "comp": L3 / "out_11nov" / "comp3_games.csv"},
       "app": {"cut": APP_CUT, "v1": config.R / "local" / "sim1" / "v1_all" / "v1_games_all_fresh.csv",
               "comp": L3 / "refit_1110_v1fresh" / "fit" / "comp3_games.csv"}}
DTJ = config.R / "model" / "sim4" / "deathtimer.json"
RATES = config.R / "sim3" / "s3_rates.py"
INHIB_BACK, NXT_BACK = 300, 180
STR = {"tower", "inhib", "nexus"}

def kind(ty, det):
    d = str(det)
    if ty == "nexus": return "nexus"
    if ty == "inhib": return "inhib"
    if "NEXUS" in d: return "nxt"
    if d.startswith("T3"): return "T3"
    return "outer"

def rates(copy, tag="m19"):
    """run s3_rates.py (quietly, to a scratch folder) with one copy's inputs; returns its namespace"""
    inp = INP[copy]; tmp = config.R / "local" / "memory" / f"{tag}_rates_{copy}"; tmp.mkdir(parents=True, exist_ok=True)
    old_argv, old_env = sys.argv, os.environ.get("S3_CUTOFF")
    if inp["cut"]: os.environ["S3_CUTOFF"] = inp["cut"]
    else: os.environ.pop("S3_CUTOFF", None)
    sys.argv = ["s3_rates.py", str(config.TL_MATCH), str(config.TL_EVENTS), str(config.TL_GOLD), str(inp["v1"]), str(tmp), str(inp["comp"])]
    try:
        with contextlib.redirect_stdout(io.StringIO()): ns = runpy.run_path(str(RATES))
    finally:
        sys.argv = old_argv
        if old_env is None: os.environ.pop("S3_CUTOFF", None)
        else: os.environ["S3_CUTOFF"] = old_env
    ns["Xb"].__globals__["SC"] = "siege_s"   # the timing-only inputs (the app's); runpy hands back a copy, so set it where Xb looks
    return ns

def dead_intervals(info, ev, XP, AVG, DT):
    """each side's death intervals (victim's side): [kill time, kill time + official timer at the victim's level]"""
    def wait(c, t):
        xp = float(np.interp(t, [0, 600, 900, 1200, 1500], [0, *c])) if t <= 1500 else min(DT["xp_levels"][-1], c[3] + (c[3] - c[2]) / 300 * (t - 1500))
        lv = int(np.searchsorted(DT["xp_levels"], xp, side="right")); tf_ = DT["time_factor"]; f = 0.0; prev = tf_["start_s"]
        for end, per in tf_["per_step"]:
            if t > prev: f += per * ((min(t, end) - prev) // tf_["step_s"])
            prev = end
        return DT["base_wait"][min(17, lv - 1)] * (1 + min(tf_["cap"], f))
    D, matched = {}, [0, 0]
    K = ev[ev.type == "kill"]
    for g, k in K.groupby("gid"):
        if g not in info.index: continue
        gid = info.loc[g, "gameid"]; L = {"blue": [], "red": []}
        for t, sd, v in zip(k.t.values, k.side.values, k.victim.values):
            c = XP.get((gid, str(v).lower())); matched[1] += 1; matched[0] += c is not None
            L["red" if sd == "blue" else "blue"].append((float(t), float(t) + wait(c or AVG, float(t))))
        D[g] = L
    return D, matched

def max_dead(iv, a, b):
    """most intervals open at the same moment within [a, b) (as s4_deadpush.py)"""
    pts = sorted([(max(s, a), 1) for s, e in iv if s < b and e > a] + [(min(e, b), -1) for s, e in iv if s < b and e > a], key=lambda z: (z[0], z[1]))
    cur = best = 0
    for _, d in pts: cur += d; best = max(best, cur)
    return best

def dead_at(iv, t):
    """players dead at the moment t"""
    return sum(1 for s, e in iv if s <= t < e)

def structures(ev):
    """per game and side: (time, kind) of the structures that side took, in time order"""
    S = ev[ev.type.isin(STR)].sort_values("t")
    return {(g, sd): [(float(t), kind(ty, de)) for t, ty, de in zip(d.t, d.type, d.detail)] for (g, sd), d in S.groupby(["gid", "side"])}

def left_at(st, t):
    """structures left to the enemy Nexus at time t (strictly before t), from this side's takes"""
    inh = any(k == "inhib" and t - INHIB_BACK < x < t for x, k in st)
    nxd = min(2, sum(1 for x, k in st if k == "nxt" and t - NXT_BACK < x < t))
    return (2 - nxd) + (0 if inh else 1)

def add_state(B, ST, DEAD):
    left, en, ow, att = [], [], [], []
    for g, m, s in zip(B.gid, B.m, B.side):
        o = "red" if s == "blue" else "blue"; t0 = 60.0 * m
        left.append(left_at(ST.get((g, s), []), t0))
        dd = DEAD.get(g, {"blue": [], "red": []}); en.append(max_dead(dd[o], t0, t0 + 60)); ow.append(max_dead(dd[s], t0, t0 + 60))
        att.append(int(any(k in ("inhib", "nxt") and t0 - 60 <= x < t0 for x, k in ST.get((g, o), []))))
    return B.assign(left=left, en_dead=np.clip(en, 0, 5), own_dead=np.clip(ow, 0, 5), under_attack=att)

def extra(d, form, inter):
    c = [d.left.values.astype(float)] if form == "linear" else [(d.left.values == L).astype(float) for L in (0, 1, 2)]
    c += [d.en_dead.values, d.own_dead.values, d.under_attack.values]
    if inter: c.append((d.left.values == 0) * d.en_dead.values)
    return np.c_[tuple(np.asarray(x, float) for x in c)]

def names_extra(form, inter):
    return (["structures_left"] if form == "linear" else ["left 0", "left 1", "left 2"]) + ["enemies_dead_max", "own_dead_max", "own_base_under_attack"] + (["left 0 x enemies_dead"] if inter else [])

lgl = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
def ll(X, b, y): return round(lgl(np.clip(1 / (1 + np.exp(-X @ b)), 1e-6, 1 - 1e-6), y), 5)
