"""Sim session 4 pre-work (research only, 11 Nov): walk-forward test of the game-state sim (Luke, 10 Nov: two tests always).
The fixed test (fit before 1 Sep, test everything after) stays as it is: s3_test.py without any S3_* setting.
Walk-forward: for each week from <start> that has major-league games, every fit is redone on the games BEFORE that week
(Worlds games before it included), the sim is calibrated on those games, and only that week's games are predicted.
  per week   s3_lanes -> s3_comp -> s3_events -> s3_rates -> [s3_fighttypes] -> s3_targets -> s3_params   (into <out_root>/<week>/fit)
             then s3_test once per sim version                                                             (into <out_root>/<week>/<version>)
  half-life  lanes and draft styles (fitted from the file alone, history back to January) can weight recent games more
             (S3_HALFLIFE, days); the timeline-fitted parts use no fade (timelines only start in late July). Luke, 11 Nov.
  versions   base (the default sim: lane x tier pushes), nolt (the earlier sim), pfs (+ last minute's kills edge), pf (+ the
             clear-fight flag, cutoff chosen on that week's training games), typed (fight types), typed_pf (both)
Finished steps are skipped, so a stopped run can be started again. Every step's printout goes to a log file beside its output.
Scores: all weeks' per-game odds together, for games from 1 Sep, Worlds, and the Worlds knockouts (from 3 Nov), with v1 on the
same games (v1's team ratings are already refitted every day).
usage: python -I s3_walkforward.py <OE csv> v1_games.csv gfeat.csv tl_match.csv tl_games.csv tl_events.csv tl_gold.csv <out_root>
                                   [versions=base,pfs] [n_sims=200] [start=2026-09-01] [end=2026-12-31] [hl_lanes=none] [hl_comp=none] [only_week=YYYY-MM-DD] [tag]"""
import os, sys, json, time, subprocess
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV, V1, GF, TM, TG, TE, TGO, ROOT = sys.argv[1:9]
opt = lambda i, d: sys.argv[i] if len(sys.argv) > i and sys.argv[i] not in ("", "-") else d
VERSIONS = opt(9, "base,pfs").split(","); NS = int(opt(10, "200")); START, STOP = opt(11, "2026-09-01"), opt(12, "2026-12-31")
HL_LANES, HL_COMP, ONLY = opt(13, "none"), opt(14, "none"), opt(15, None)
TAG = opt(16, "")  # added to each version's folder and result file names, so a re-run (e.g. more sims) can reuse the saved weekly fits
OPTS = {"base": "none", "nolt": "nolt", "pfs": "pfs", "pf": "pf", "typed": "typed", "typed_pf": "typed,pf"}
for v in VERSIONS:
    if v not in OPTS: sys.exit(f"unknown version {v}; choose from {sorted(OPTS)}")
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
os.makedirs(ROOT, exist_ok=True)

def run(name, script, args, out_marker, env_extra):
    """Run one script unless its output is already there; returns seconds (0 if skipped)."""
    if os.path.exists(out_marker): return 0.0
    env = dict(os.environ); env.update(env_extra); t0 = time.time()
    os.makedirs(os.path.dirname(out_marker), exist_ok=True); log = out_marker + ".log.txt"
    with open(log, "w", encoding="utf-8") as fh:
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, script), *args], env=env, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        if os.path.exists(out_marker): os.remove(out_marker)  # never leave a half-written output that a later run would skip
        sys.exit(f"{name} failed (exit {r.returncode}); see {log}")
    return time.time() - t0

# weeks with major-league games (the file's UTC dates, as everywhere else in the sim work)
d = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date"])
d = d[d.league.isin(MAJOR) & ~((d.league == "WLDs") & (d.date < "2026-10-01"))].drop_duplicates("gameid"); d["day"] = d.date.str[:10]
weeks = []
w0 = pd.Timestamp(START)
while w0.strftime("%Y-%m-%d") < STOP and w0 <= pd.Timestamp(d.day.max()):
    a, b = w0.strftime("%Y-%m-%d"), (w0 + pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    n = int(((d.day >= a) & (d.day < b)).sum())
    if n: weeks.append((a, b, n))
    w0 += pd.Timedelta(days=7)
if ONLY: weeks = [w for w in weeks if w[0] == ONLY]
print("weeks:", [(a, n) for a, _, n in weeks], flush=True)

timing = {}
for a, b, n in weeks:
    fit = os.path.join(ROOT, a, "fit"); os.makedirs(fit, exist_ok=True)
    cut = {"S3_CUTOFF": a}; hl = lambda h: {} if h == "none" else {"S3_HALFLIFE": h}
    comp, feats = os.path.join(fit, "comp3_games.csv"), os.path.join(fit, "lanes3_features.csv")
    t = {}
    t["lanes"] = run("s3_lanes", "s3_lanes.py", [CSV, V1, GF, fit], feats, {**cut, **hl(HL_LANES)})
    t["comp"] = run("s3_comp", "s3_comp.py", [CSV, V1, fit], comp, {**cut, **hl(HL_COMP)})
    t["events"] = run("s3_events", "s3_events.py", [TM, TG, TE, TGO, V1, fit, comp], os.path.join(fit, "events3_results.json"), cut)
    t["rates"] = run("s3_rates", "s3_rates.py", [TM, TE, TGO, V1, fit, comp], os.path.join(fit, "rates3_results.json"), cut)
    if any("typed" in v for v in VERSIONS):
        t["fighttypes"] = run("s3_fighttypes", "s3_fighttypes.py", [TM, TE, TGO, V1, comp, os.path.join(fit, "fighttypes.json")], os.path.join(fit, "fighttypes.json"), cut)
    t["targets"] = run("s3_targets", "s3_targets.py", [CSV, fit], os.path.join(fit, "targets3.json"), cut)
    t["params"] = run("s3_params", "s3_params.py", [CSV, fit, os.path.join(fit, "params3.json")], os.path.join(fit, "params3.json"), cut)
    for v in VERSIONS:
        out = os.path.join(ROOT, a, v + TAG)
        t["test_" + v] = run("s3_test " + v, "s3_test.py", [os.path.join(fit, "params3.json"), feats, V1, os.path.join(fit, "targets3.json"),
                             os.path.join(fit, "tl_fights.csv"), comp, out, str(NS), "timing", OPTS[v]], os.path.join(out, "wf_preds.csv"), {**cut, "S3_TEST_END": b})
    timing[a] = {k: round(s, 1) for k, s in t.items()}
    print(a, "games", n, "seconds", timing[a], flush=True)

def score(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4), "brier": round(float(np.mean((p - y) ** 2)), 4),
            "fav": round(float(np.mean((p > 0.5) == (y == 1))), 3)}
res = {"settings": {"versions": VERSIONS, "n_sims": NS, "start": START, "half_life_lanes": HL_LANES, "half_life_comp": HL_COMP,
                    "weeks": [{"from": a, "to": b, "games_in_file": n} for a, b, n in weeks]}, "seconds": timing, "scores": {}}
for v in VERSIONS:
    fs = [os.path.join(ROOT, a, v + TAG, "wf_preds.csv") for a, _, _ in weeks]
    P = pd.concat([pd.read_csv(f) for f in fs if os.path.exists(f)], ignore_index=True) if any(os.path.exists(f) for f in fs) else pd.DataFrame()
    if not len(P): continue
    P.to_csv(os.path.join(ROOT, f"wf_preds_{v}{TAG}.csv"), index=False)
    sets = {"from 1 Sep": P.day >= "2026-09-01", "Worlds": P.league == "WLDs", "Worlds knockouts (from 3 Nov)": (P.league == "WLDs") & (P.day >= "2026-11-03")}
    res["scores"][v] = {k: {"sim": score(P.p_sim[m].values, P.y[m].values), "v1": score(P.p_v1[m].values, P.y[m].values)} for k, m in sets.items() if m.any()}
json.dump(res, open(os.path.join(ROOT, f"wf_results{TAG}.json"), "w"), indent=1)
print(json.dumps(res["scores"], indent=1))
