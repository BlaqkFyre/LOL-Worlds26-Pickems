"""Sim session 4 pre-work (research only, 11 Nov): choose how fast older games fade for the two parts of the sim that are
fitted from the Oracle's Elixir file alone: laning (s3_lanes.py) and champion draft styles (s3_comp.py).
Luke (11 Nov): recent games should count more; around 60 days (2-4 patches) if the data supports it. The number is chosen by
test, never set: each candidate half-life is scored on July-August match weeks only, so games from 1 Sep stay a clean test.
For each week from 1 Jul to 31 Aug and each candidate: both scripts are run with S3_CUTOFF = the week's first day and
S3_HALFLIFE = the candidate (so only earlier games are used, weighted 0.5 ** (age in days / half-life)); then that week's games
are scored:
  laning   the fitted lane model's prediction of each role's gold lead at 10 and 15 (v1 strength, skill gap, champion lane
           values) against the real lead: squared error as a share of the real spread, averaged over roles and minutes (lower = better)
  styles   each draft's style from earlier games (siege, objectives, skirmish as blue minus red; pace as blue plus red) against what
           the game then showed (tower and plate share and first tower; dragon / grub / Herald / Baron share; kill share at 15;
           kills per minute), after taking out what v1's odds explain: correlation, averaged over the four styles (higher = better)
The timeline-fitted parts (fights, pushes, objectives) use no fade: the timelines only start in late July.
usage: python -I s3_halflife.py <OE csv> v1_games.csv gfeat.csv <work_dir> <out json> [candidates=none,30,60,120,240]"""
import os, sys, json, subprocess
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV, V1, GF, WORK, OUTJ = sys.argv[1:6]
CANDS = (sys.argv[6] if len(sys.argv) > 6 else "none,30,60,120,240").split(",")
ROLES = ["top", "jng", "mid", "bot", "sup"]; MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
WEEKS = []; d = pd.Timestamp("2026-07-01")
while d < pd.Timestamp("2026-09-01"):
    WEEKS.append((d.strftime("%Y-%m-%d"), min(d + pd.Timedelta(days=7), pd.Timestamp("2026-09-01")).strftime("%Y-%m-%d"))); d += pd.Timedelta(days=7)

def run(script, args, env_extra, marker):
    if os.path.exists(marker): return
    env = dict(os.environ); env.update(env_extra)
    r = subprocess.run([sys.executable, "-I", os.path.join(HERE, script), *args], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0: sys.exit(f"{script} failed: {r.stderr[-800:]}")

# what each game showed (for the style check), from the file's team rows
c = ["gameid", "league", "date", "side", "position", "gamelength", "kills", "killsat15", "firsttower", "turretplates", "opp_turretplates", "towers", "opp_towers",
     "dragons", "opp_dragons", "void_grubs", "opp_void_grubs", "heralds", "opp_heralds", "barons", "opp_barons"]
raw = pd.read_csv(CSV, low_memory=False, usecols=c); raw = raw[raw.league.isin(MAJOR)]
k15 = raw[raw.position.isin(ROLES)].groupby(["gameid", "side"]).killsat15.sum(min_count=5).unstack()
tm = raw[raw.position == "team"]; b = tm[tm.side == "Blue"].set_index("gameid"); r = tm[tm.side == "Red"].set_index("gameid").reindex(b.index)
sh = lambda x, y: np.where((x + y) > 0, x / (x + y), 0.5)
REAL = pd.DataFrame({"siege": (sh(b.turretplates, b.opp_turretplates) + sh(b.towers, b.opp_towers) + b.firsttower) / 3,
                     "objectives": (sh(b.dragons, b.opp_dragons) + sh(b.void_grubs, b.opp_void_grubs) + sh(b.heralds, b.opp_heralds) + sh(b.barons, b.opp_barons)) / 4,
                     "skirmish": sh(k15.Blue.reindex(b.index), k15.Red.reindex(b.index)), "pace": (b.kills + r.kills) / (b.gamelength / 60)}, index=b.index)
REAL["p"] = pd.read_csv(V1).set_index("gameid").p_v1.reindex(REAL.index)

res = {"weeks": WEEKS, "candidates": {}, "method": "July-August match weeks only; each week fitted on earlier games"}
for h in CANDS:
    env_h = {} if h == "none" else {"S3_HALFLIFE": h}
    L, C = [], []
    for a, z in WEEKS:
        out = os.path.join(WORK, h, a); os.makedirs(out, exist_ok=True)
        run("s3_lanes.py", [CSV, V1, GF, out], {"S3_CUTOFF": a, **env_h}, os.path.join(out, "lanes3_features.csv"))
        run("s3_comp.py", [CSV, V1, out], {"S3_CUTOFF": a, **env_h}, os.path.join(out, "comp3_games.csv"))
        f = pd.read_csv(os.path.join(out, "lanes3_features.csv")); f = f[(f.day >= a) & (f.day < z)]
        co = pd.read_csv(os.path.join(out, "lanes3_coef.csv")).set_index(["role", "minute"])
        for ro in ROLES:
            q = f[f.position == ro]
            for m in (10, 15):
                k = co.loc[(ro, m)]; pred = k.intercept + k.per_z * q.z_v1 + k.per_skill_sd * q.skill_gap + k.per_champ_gold * q[f"cg{m}"]
                L.append(pd.DataFrame({"week": a, "role": ro, "minute": m, "err2": (q[f"gd{m}"] - pred) ** 2, "y": q[f"gd{m}"]}))
        g = pd.read_csv(os.path.join(out, "comp3_games.csv")).set_index("gameid"); g = g[g.index.isin(f.gameid)]
        C.append(pd.DataFrame({"week": a, "siege": g.siege_blue - g.siege_red, "objectives": g.objectives_blue - g.objectives_red,
                               "skirmish": g.skirmish_blue - g.skirmish_red, "pace": g.pace_blue + g.pace_red}, index=g.index))
    L = pd.concat(L); C = pd.concat(C)
    # laning: squared error as a share of the real spread, per role and minute, then averaged
    lane = L.groupby(["role", "minute"]).apply(lambda q: float(q.err2.mean() / q.y.var())).unstack()
    lane_week = L.groupby("week").apply(lambda q: float(np.mean([v.err2.mean() / v.y.var() for _, v in q.groupby(["role", "minute"])])))
    # styles: correlation with what the game showed, after taking out v1's odds (straight line fitted on these games, the same for every candidate)
    J = C.join(REAL, rsuffix="_real").dropna(subset=["p"]); sty = {}
    for s in ("siege", "objectives", "skirmish", "pace"):
        q = J.dropna(subset=[s + "_real"]); x = (q.p - 0.5).abs() if s == "pace" else q.p
        resid = q[s + "_real"] - np.polyval(np.polyfit(x, q[s + "_real"], 1), x)
        sty[s] = round(float(np.corrcoef(q[s], resid)[0, 1]), 4)
    res["candidates"][h] = {"laning": {"score": round(float(lane.values.mean()), 5), "games": int(L[(L.role == "top") & (L.minute == 15)].shape[0]),
                                       "by_role_at_15": {ro: round(float(lane.loc[ro, 15]), 4) for ro in ROLES}, "by_role_at_10": {ro: round(float(lane.loc[ro, 10]), 4) for ro in ROLES},
                                       "by_week": {w: round(v, 4) for w, v in lane_week.items()}},
                            "styles": {"score": round(float(np.mean(list(sty.values()))), 4), "games": int(len(J)), **sty}}
    print(h, "laning", res["candidates"][h]["laning"]["score"], "styles", res["candidates"][h]["styles"]["score"], sty, flush=True)
res["chosen"] = {"laning": min(CANDS, key=lambda h: res["candidates"][h]["laning"]["score"]), "styles": max(CANDS, key=lambda h: res["candidates"][h]["styles"]["score"])}
# how many weeks each candidate beats "none" in, so a choice that is within the noise is visible as such
if "none" in CANDS:
    base = res["candidates"]["none"]["laning"]["by_week"]
    res["laning_weeks_better_than_none"] = {h: int(sum(res["candidates"][h]["laning"]["by_week"][w] < base[w] for w in base)) for h in CANDS if h != "none"}
json.dump(res, open(OUTJ, "w"), indent=1); print(json.dumps({k: res[k] for k in res if k != "candidates"}, indent=1))
