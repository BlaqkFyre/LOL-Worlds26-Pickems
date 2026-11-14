"""Part B of the spread work (14 Nov 2026 AEST, Luke OK'd): pushes follow dead players. Fitted on gol.gg timeline games before 1 Sep.
Real structures fall while the defenders are dead (research/sim4/spread_kills_structures.py) and a player is never killed again inside the death
timer (research/sim4/deathtimer_check.py). The sim's push models (s3_rates.py "segment_push_fight", "base_push_fight", the default sim's) see
only the kills edge. Here the same rows and inputs as those fits (timing-only draft styles), plus:
  enemies_dead_max  the most enemy players dead at the same moment during the minute (0-5)
  own_dead_max      the most of the side's own players dead at the same moment during the minute (0-5)
Dead time of each real death: the League wiki timer (research/sim4/s4_deathtimer.py table) at the victim's level, from the victim's own XP at
10/15/20/25 in the Oracle's Elixir file (matched by name), else the average curve of all roles.
Push size: drawn from real pushes (as now) but by enemies dead at the push's start (0 / 1-2 / 3+): tower pushes by starting tier, base pushes
by enemy inhibitor down. Push timing (part C): seconds between consecutive structures of one side (under 60 s), from training games, and how
long after the minute's last fight the first structure falls when enemies are dead.
usage (repo root): python -I research/sim4/s4_deadpush.py tl_match.csv tl_events.csv tl_gold.csv v1_games.csv comp3_games.csv <OE csv>
       deathtimer.json <out_dir>"""
import os, sys, json, runpy, contextlib, io
import numpy as np, pandas as pd
TM, TE, TGo, V1, CO, CSV, DTJ, OUT = sys.argv[1:9]; os.makedirs(OUT, exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):
    sys.argv = ["s3_rates.py", TM, TE, TGo, V1, os.path.join(OUT, "rates_tmp"), CO]
    ns = runpy.run_path(os.path.join("research", "sim3", "s3_rates.py"))
SEG, BASE, PUSHD, info, ev = ns["SEG"], ns["BASE"], ns["PUSHD"], ns["info"], ns["ev"]
logit_fit, lg, XgLT, Xb, fight_terms = ns["logit_fit"], ns["lg"], ns["XgLT"], ns["Xb"], ns["fight_terms"]
names_g, names_b, LTN = ns["names_g"], ns["names_b"], ns["LTN"]
cS = ns["res"]["segment_push_fight"]["clear_fight_cutoff"]; cB = ns["res"]["base_push_fight"]["clear_fight_cutoff"]
XgLT.__globals__["SC"] = "siege_s"  # timing-only versions (the default sim's); runpy hands back a copy of the globals, so set it where the functions look
DT = json.load(open(DTJ)); ROLES = ["top", "jng", "mid", "bot", "sup"]
def wait(c, t):
    xp = float(np.interp(t, [0, 600, 900, 1200, 1500], [0, *c])) if t <= 1500 else min(DT["xp_levels"][-1], c[3] + (c[3] - c[2]) / 300 * (t - 1500))
    lv = int(np.searchsorted(DT["xp_levels"], xp, side="right")); tf_ = DT["time_factor"]; f = 0.0; prev = tf_["start_s"]
    for end, per in tf_["per_step"]:
        if t > prev: f += per * ((min(t, end) - prev) // tf_["step_s"])
        prev = end
    return DT["base_wait"][min(17, lv - 1)] * (1 + min(tf_["cap"], f))
oe = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(oe.gameid, oe.playername, oe.xpat10, oe.xpat15, oe.xpat20, oe.xpat25)}
AVG = tuple(np.mean([DT["role_xp"][r] for r in ROLES], axis=0))
# death intervals per game and side (the side whose player is dead)
DEAD = {}; matched = [0, 0]
for g, gi in info.iterrows():
    k = ev[(ev.gid == g) & (ev.type == "kill")]; L = {"blue": [], "red": []}
    for x in k.itertuples():
        vs = "red" if x.side == "blue" else "blue"; c = XP.get((gi.gameid, str(x.victim).lower())); matched[1] += 1; matched[0] += c is not None
        L[vs].append((x.t, x.t + wait(c or AVG, x.t)))
    DEAD[g] = L
def max_dead(iv, a, b):
    """most intervals open at the same moment within [a, b)"""
    pts = sorted([(max(s, a), 1) for s, e in iv if s < b and e > a] + [(min(e, b), -1) for s, e in iv if s < b and e > a], key=lambda z: (z[0], z[1]))
    cur = best = 0
    for _, d in pts: cur += d; best = max(best, cur)
    return best
def add_dead(d):
    en, ow = [], []
    for g, m, s in zip(d.gid, d.m, d.side):
        o = "red" if s == "blue" else "blue"; en.append(max_dead(DEAD[g][o], 60 * m, 60 * m + 60)); ow.append(max_dead(DEAD[g][s], 60 * m, 60 * m + 60))
    return d.assign(en_dead=np.clip(en, 0, 5), own_dead=np.clip(ow, 0, 5))
SEG = add_dead(SEG); BASE = add_dead(BASE)
R = {"source": "research/sim4/s4_deadpush.py", "deaths matched to the file's XP": matched, "cutoffs": {"segment": cS, "base": cB}}
ypt = lambda d: (d.push.values > 0).astype(float); ybb = lambda d: (d.y.values > 0).astype(float)
XgF = lambda d: np.c_[XgLT(d), fight_terms(d, cS)]; XgD = lambda d: np.c_[XgF(d), d.en_dead, d.own_dead]
XbF = lambda d: np.c_[Xb(d), fight_terms(d, cB)]; XbD = lambda d: np.c_[XbF(d), d.en_dead, d.own_dead]
fn = lambda c: ["net_kills_last_minute"] + (["clear_fight_win"] if c is not None else [])
for nm, D, X0, X1, y, names in [("segment", SEG, XgF, XgD, ypt, names_g[:-1] + ["siege_style_sum"] + LTN + fn(cS)),
                                ("base", BASE, XbF, XbD, ybb, [n if n != "siege_style" else "siege_style_sum" for n in names_b] + fn(cB))]:
    tr = D[D.split == "train"]; b0 = logit_fit(X0(tr), y(tr)); b1 = logit_fit(X1(tr), y(tr))
    sc = lambda X, b, q: round(lg(1 / (1 + np.exp(-X(q) @ b)), y(q)), 5)
    R[nm + "_push_dead"] = {"coef": dict(zip(names + ["enemies_dead_max", "own_dead_max"], np.round(b1, 4).tolist())),
                            **{s: {"n": int((D.split == s).sum()), "with dead": sc(X1, b1, D[D.split == s]), "current": sc(X0, b0, D[D.split == s])} for s in ("train", "test", "worlds")}}
    R[nm + "_start_rate_by_enemies_dead (train)"] = {str(k): [round(float(q.pipe(y).mean()), 3), len(q)] for k, q in tr.groupby(tr.en_dead.clip(upper=4))}
# push sizes by enemies dead at the start minute
grp = lambda n: "0" if n == 0 else "1-2" if n <= 2 else "3+"
SP = ns["SPUSH"].copy(); SP = SP[SP.split == "train"]
SP["en"] = [max_dead(DEAD[g][("red" if s == "blue" else "blue")], 60 * m, 60 * m + 60) for g, s, m in zip(SP.gid, SP.side, SP.m)]
SP["key"] = np.where((SP.tier0 == 0) & (SP.m < 14), "0_early", SP.tier0.astype(str))
R["segment_size_by_dead"] = {f"{k}|{grp_}": {str(z): round(float(v), 4) for z, v in d["size"].clip(upper=15).value_counts(normalize=True).sort_index().items()}
                             for (k, grp_), d in SP.assign(g_=SP.en.map(grp)).groupby(["key", "g_"])}
R["segment_size_mean_by_dead"] = {f"{k}|{grp_}": [round(float(d["size"].mean()), 2), len(d)] for (k, grp_), d in SP.assign(g_=SP.en.map(grp)).groupby(["key", "g_"])}
PD = PUSHD[PUSHD.split == "train"].copy()
PD["en"] = [max_dead(DEAD[g][("red" if s == "blue" else "blue")], 60 * m, 60 * m + 60) for g, s, m in zip(PD.gid, PD.side, PD.m)]
R["base_size_by_dead"] = {f"{'inhib_down' if dn else 'no_inhib_down'}|{grp_}": {str(z): round(float(v), 4) for z, v in d["size"].clip(upper=6).value_counts(normalize=True).sort_index().items()}
                          for (dn, grp_), d in PD.assign(g_=PD.en.map(grp)).groupby(["down", "g_"])}
R["base_size_mean_by_dead"] = {f"{'inhib_down' if dn else 'no_inhib_down'}|{grp_}": [round(float(d["size"].mean()), 2), round(float(d.ends.mean()), 3), len(d)]
                               for (dn, grp_), d in PD.assign(g_=PD.en.map(grp)).groupby(["down", "g_"])}
# timing (part C): gaps between a side's consecutive structures (towers, inhibitors, nexus towers, nexus) under 60 s; delay of the first
# structure after the last kill of the side's winning fight, when the structure falls while enemies are dead
gaps, delay = [], []
for g, gi in info[info.split == "train"].iterrows():
    e = ev[ev.gid == g]
    for sd in ("blue", "red"):
        st = np.sort(e[e.type.isin(["tower", "inhib", "nexus"]) & (e.side == sd)].t.values)
        gaps += [int(b - a) for a, b in zip(st, st[1:]) if b - a < 60]
        kt = np.sort(e[(e.type == "kill") & (e.side == sd)].t.values); o = "red" if sd == "blue" else "blue"
        for t in st:
            if any(s <= t < en_ for s, en_ in DEAD[g][o]):
                prev = kt[kt <= t]
                if len(prev) and t - prev[-1] <= 90: delay.append(int(t - prev[-1]))
gaps = np.array(gaps); delay = np.array(delay)
R["gap_between_structures_s"] = {str(k): round(float(v), 4) for k, v in pd.Series(np.clip(gaps, 0, 59)).value_counts(normalize=True).sort_index().items()}
R["gap_summary"] = {"n": len(gaps), "median": float(np.median(gaps)), "share_0s": round(float((gaps == 0).mean()), 3)}
R["delay_after_last_kill_s"] = {str(k): round(float(v), 4) for k, v in pd.Series(np.clip(delay, 0, 90)).value_counts(normalize=True).sort_index().items()}
R["delay_summary"] = {"n": len(delay), "median": float(np.median(delay)), "p10": float(np.percentile(delay, 10)), "p90": float(np.percentile(delay, 90))}
json.dump(R, open(os.path.join(OUT, "deadpush.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if not k.endswith("_s") and "size_by" not in k}, indent=1))
