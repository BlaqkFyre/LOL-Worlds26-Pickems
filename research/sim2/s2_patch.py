"""Sim session 2, step 3 (read-only): patch-aware champion strength, measured beyond v1's odds.
Per champion-role, from earlier days only (no look-ahead):
  season = recency-weighted pro residual (result - v1 chance), pulled toward 0 (k = 100 games, 90-day half-life: step 2's choice)
  patch  = pro residual on the game's own patch only, pulled toward 0 with k_p games
  solo   = lolalytics Emerald+ win rate in that lane on the game's patch, minus the lane's games-weighted average (percentage points);
           solo-queue games are not pro results, so this has no look-ahead problem
  solo_prev = the same on the previous lolalytics patch (form)
Game feature = blue sum - red sum. Model: logit = z_v1 + b . features (small ridge). Tuning on Jul-Aug (fit Feb-Jun);
test: fit Feb-Aug, predict from 1 Sep and on Worlds.
usage: python -I s2_patch.py <csv> v1_games.csv lola_tiers_all.csv <out_dir>"""
import json, os, sys
import numpy as np
import pandas as pd

CSV, V1, LOLA, OUT = sys.argv[1:5]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
LANE = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}
def norm_patch(p):
    p = str(p); a, _, b = p.partition(".")
    return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
raw = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                  usecols=["gameid", "league", "date", "patch", "side", "position", "champion", "result"])
raw = raw[(raw.position != "team") & raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["patch"] = raw.patch.map(norm_patch); raw["day"] = raw.date.str[:10]
V = pd.read_csv(V1); pv = V.set_index("gameid").p_v1.to_dict()
raw["p_side"] = raw.gameid.map(pv); red = raw.side == "Red"; raw.loc[red, "p_side"] = 1 - raw.loc[red, "p_side"]
raw["res"] = raw.result - raw.p_side
raw = raw.sort_values(["day", "gameid"])
t_of = {d: (pd.Timestamp(d) - pd.Timestamp("2026-01-01")).days for d in raw.day.unique()}
print("pro patches (normalised):", raw.groupby("patch").gameid.nunique().to_dict())
# lolalytics: centred win rate per patch-lane-champion
L = pd.read_csv(LOLA, dtype={"patch": str}); L["patch"] = L.patch.map(norm_patch)
L = L[L.games >= 300].copy()
avg = L.groupby(["patch", "lane"]).apply(lambda d: np.average(d.wr, weights=d.games)).rename("lane_avg")
L = L.join(avg, on=["patch", "lane"]); L["c"] = L.wr - L.lane_avg
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
SOLO = {(r.patch, r.lane, key(r.name)): r.c for r in L.itertuples()}
LP = sorted(L.patch.unique()); PREV = {p: LP[i - 1] for i, p in enumerate(LP) if i > 0}
miss = raw[~raw.apply(lambda r: (r.patch, LANE[r.position], key(r.champion)) in SOLO, axis=1)]
print(f"pro player-rows with no lolalytics value: {len(miss)} of {len(raw)} ({len(miss) / len(raw):.1%}); top:",
      miss.groupby(["patch"]).size().sort_values(ascending=False).head(5).to_dict())

def features(k_p, hl=90.0, k1=100.0):
    acc_s, acc_p, feats = {}, {}, {}
    for d, rows in raw.groupby("day", sort=True):
        t = t_of[d]
        for r in rows.itertuples(index=False):
            sg = 1.0 if r.side == "Blue" else -1.0; kc = (r.champion, r.position)
            S, N, t0 = acc_s.get(kc, (0.0, 0.0, t)); f = 0.5 ** ((t - t0) / hl); season = S * f / (N * f + k1)
            Sp, Np = acc_p.get((r.patch,) + kc, (0.0, 0.0)); patch = Sp / (Np + k_p)
            ln, kk = LANE[r.position], key(r.champion)
            solo = SOLO.get((r.patch, ln, kk), 0.0) / 100; prev = SOLO.get((PREV.get(r.patch), ln, kk), 0.0) / 100
            x = feats.setdefault(r.gameid, np.zeros(4)); x += sg * np.array([season, patch, solo, prev])
        for r in rows.itertuples(index=False):
            if np.isnan(r.res): continue
            kc = (r.champion, r.position)
            S, N, t0 = acc_s.get(kc, (0.0, 0.0, t)); f = 0.5 ** ((t - t0) / hl); acc_s[kc] = (S * f + r.res, N * f + 1, t)
            Sp, Np = acc_p.get((r.patch,) + kc, (0.0, 0.0)); acc_p[(r.patch,) + kc] = (Sp + r.res, Np + 1)
    return pd.DataFrame.from_dict(feats, orient="index", columns=["season", "patch", "solo", "solo_prev"])

def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6)
    return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4), round(float(np.mean((p > .5) == (y == 1))), 3)
G = V.dropna(subset=["z_v1"]).drop(columns=["patch"]).set_index("gameid"); G["day"] = G.date.str[:10]
sp = lambda D, a, z: D[(D.day >= a) & (D.day < z)]
SETS = {"season (step 2)": ["season"], "patch": ["patch"], "solo": ["solo"], "solo + solo_prev": ["solo", "solo_prev"],
        "season + patch": ["season", "patch"], "patch + solo": ["patch", "solo"], "season + patch + solo": ["season", "patch", "solo"],
        "all four": ["season", "patch", "solo", "solo_prev"]}
R = {"tuning": {}, "models": {}}
best = None
for k_p in (5, 15, 40):
    D = G.join(features(k_p), how="inner")
    FC = ["season", "patch", "solo", "solo_prev"]
    R.setdefault("raw_sd_pre_sep", {})[k_p] = D.loc[D.day < "2026-09-01", FC].std().round(4).to_dict()
    D[FC] = D[FC] / D.loc[D.day < "2026-09-01", FC].std()   # same scale for every feature, so the ridge pulls each equally
    trv, va = sp(D, "2026-02-01", "2026-07-01"), sp(D, "2026-07-01", "2026-09-01")
    cols = SETS["all four"]; b = fit(trv.z_v1.values, trv[cols].values, trv.blue_win.values)
    v = ll(va.z_v1.values, va[cols].values, va.blue_win.values, b)[0]; R["tuning"][k_p] = v
    if best is None or v < best[0]: best = (v, k_p, D)
_, k_p, D = best; R["chosen_k_patch"] = k_p
tr, trv, va, te = sp(D, "2026-02-01", "2026-09-01"), sp(D, "2026-02-01", "2026-07-01"), sp(D, "2026-07-01", "2026-09-01"), sp(D, "2026-09-01", "2027-01-01")
wo = D[D.league == "WLDs"]; nz = lambda d: np.zeros((len(d), 1))
R["v1"] = {"jul_aug": ll(va.z_v1.values, nz(va), va.blue_win.values, np.zeros(1)), "from_sep": ll(te.z_v1.values, nz(te), te.blue_win.values, np.zeros(1)),
           "worlds": ll(wo.z_v1.values, nz(wo), wo.blue_win.values, np.zeros(1)), "n": [len(va), len(te), len(wo)]}
for name, cols in SETS.items():
    bv = fit(trv.z_v1.values, trv[cols].values, trv.blue_win.values); b = fit(tr.z_v1.values, tr[cols].values, tr.blue_win.values)
    R["models"][name] = {"weights": dict(zip(cols, np.round(b, 3).tolist())), "jul_aug": ll(va.z_v1.values, va[cols].values, va.blue_win.values, bv),
                         "from_sep": ll(te.z_v1.values, te[cols].values, te.blue_win.values, b), "worlds": ll(wo.z_v1.values, wo[cols].values, wo.blue_win.values, b)}
R["feature_sd"] = D[SETS["all four"]].std().round(4).to_dict()
# how much of each game's draft the features cover: share of Worlds player-rows with a same-patch pro sample before that day
json.dump(R, open(os.path.join(OUT, "patchfit_results.json"), "w"), indent=1, default=str)
print("chosen k_patch", k_p, "tuning", R["tuning"]); print("v1", R["v1"])
for n, m in R["models"].items(): print(f"{n:<24} JulAug {m['jul_aug']}  from 1 Sep {m['from_sep']}  Worlds {m['worlds']}  w {m['weights']}")
