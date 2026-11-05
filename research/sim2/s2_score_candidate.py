"""Knockout test of the fixed v2 candidate (research/model/sim2/v2_candidate.json, fixed 5 Nov before any knockout game was in the file).
Features computed exactly as in s2_v2candidate.py (earlier days only); weights and SDs read from the JSON, NOT refitted.
Scores v1 and the candidate on the knockout games only (Worlds games dated from 1 Nov UTC).
Also checks that games present in the earlier file have identical v1 odds in the new run.
usage: python -I s2_score_candidate.py <OE csv> v1_games.csv <old v1_games.csv> <v2_candidate.json>"""
import itertools, json, sys
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

CSV, V1, V1OLD, CAND = sys.argv[1:5]
C = json.load(open(CAND, encoding="utf-8")); FEAT = C["features"]; W = np.array([C["weights_per_sd"][f] for f in FEAT]); SD = np.array([C["feature_sd_before_1_Sep"][f] for f in FEAT])
new, old = pd.read_csv(V1).set_index("gameid"), pd.read_csv(V1OLD).set_index("gameid")
common = old.index.intersection(new.index)
dz = (new.loc[common, "z_v1"] - old.loc[common, "z_v1"]).abs()
print(f"games in both runs: {len(common)}; largest change in v1 log-odds: {dz.max():.2e}; games only in the new run: {len(new.index.difference(old.index))}")
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "playerid", "playername", "champion"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]; raw["t"] = (pd.to_datetime(raw.day) - pd.Timestamp("2026-01-01")).dt.days
cnt = defaultdict(int); hist = defaultdict(list); together = defaultdict(int); feats, detail = {}, {}
for d, rows in raw.sort_values("date").groupby("day", sort=True):
    t = rows.t.iloc[0]
    for g, gr in rows.groupby("gameid"):
        if gr.league.iloc[0] not in MAJOR: continue
        P = {(r.side, r.position): r for r in gr.itertuples(index=False) if isinstance(r.playerid, str)}
        f = dict(jng_comfort=0.0, jng_pool=0.0, tt_jng_mid=0.0, tt_jng_bot=0.0); det = {}
        for sd, sg in (("Blue", 1.0), ("Red", -1.0)):
            j = P.get((sd, "jng"))
            if not j: continue
            n = cnt[(j.playerid, j.champion)]; f["jng_comfort"] += sg * np.log1p(n)
            c = Counter(ch for tt, ch in hist[j.playerid] if t - tt <= 180); pool = sum(1 for v in c.values() if v >= 3); f["jng_pool"] += sg * pool
            tts = {}
            for other, k in (("mid", "tt_jng_mid"), ("bot", "tt_jng_bot")):
                o = P.get((sd, other))
                if o:
                    m = together[tuple(sorted((j.playerid, o.playerid)))]; f[k] += sg * np.log1p(m); tts[other] = m
            det[sd] = f"{j.playername} on {j.champion}: {n} earlier games, pool {pool}, with mid {tts.get('mid')} games, with ADC {tts.get('bot')}"
        feats[g] = f; detail[g] = det
    for r in rows.itertuples(index=False):
        if isinstance(r.playerid, str): cnt[(r.playerid, r.champion)] += 1; hist[r.playerid].append((t, r.champion))
    for (g, sd), gr in rows.groupby(["gameid", "side"]):
        ids = sorted({p for p in gr.playerid if isinstance(p, str)})
        for a, b in itertools.combinations(ids, 2): together[(a, b)] += 1
F = pd.DataFrame.from_dict(feats, orient="index")[FEAT]
K = new[(new.league == "WLDs") & (new.date >= "2026-11-01")].join(F)
K["p_v1"] = 1 / (1 + np.exp(-K.z_v1)); K["z_c"] = K.z_v1 + (K[FEAT].values / SD) @ W; K["p_cand"] = 1 / (1 + np.exp(-K.z_c))
ll = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))); br = lambda p, y: float(np.mean((p - y) ** 2))
print(f"\nknockout games: {len(K)}")
for g, r in K.sort_values("date").iterrows():
    print(f"  {r.date[:16]} {r.blue_app or r.blue} (blue) v {r.red_app or r.red}: blue won {int(r.blue_win)} | v1 blue {r.p_v1:.3f} | candidate blue {r.p_cand:.3f}")
    for sd in ("Blue", "Red"): print(f"      {sd}: {detail[g].get(sd)}")
y = K.blue_win.values
for name, p in (("v1", K.p_v1.values), ("v2 candidate", K.p_cand.values)):
    fav = int(np.sum((p > 0.5) == (y == 1)))
    print(f"  {name:<13} log loss {ll(p, y):.4f}  Brier {br(p, y):.4f}  favourite won {fav} of {len(K)}")
