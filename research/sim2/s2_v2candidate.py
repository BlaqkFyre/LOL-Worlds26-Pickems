"""Sim session 2: the fixed who-wins candidate ("v2 candidate"), decided 5 Nov 2026 (AEST) before any knockout game is in the file.
logit(blue wins) = z_v1 + sum_i w_i * (x_i / s_i), with four features (blue minus red), all from earlier days only:
  jng_comfort  log(1 + the jungler's earlier games on the champion picked; all leagues, 2026)
  jng_pool     the jungler's champions with 3+ games in the last 180 days (all leagues)
  tt_jng_mid   log(1 + earlier games the jungler and mid laner have played on the same team; all leagues, 2026)
  tt_jng_bot   the same for jungler and ADC
s_i = the feature's standard deviation on games before 1 Sep; w_i fitted (ridge 1.0) on all games with v1 odds up to the end of the
file (1 Nov 11:42 UTC). Saved to model/sim2/v2_candidate.json and NOT changed afterwards: the knockouts score it as it stands.
For reference only (these games were used to choose the features, so they are not a fair test): the same recipe fitted on games
before 1 Sep and scored from 1 Sep and on Worlds.
usage: python -I s2_v2candidate.py <OE csv> v1_games.csv <out_json>"""
import itertools, json, sys
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "playerid", "champion"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]; raw["t"] = (pd.to_datetime(raw.day) - pd.Timestamp("2026-01-01")).dt.days
cnt = defaultdict(int); hist = defaultdict(list); together = defaultdict(int); feats = {}
def features(gr, t):
    P = {(r.side, r.position): r for r in gr.itertuples(index=False) if isinstance(r.playerid, str)}
    f = dict(jng_comfort=0.0, jng_pool=0.0, tt_jng_mid=0.0, tt_jng_bot=0.0)
    for sd, sg in (("Blue", 1.0), ("Red", -1.0)):
        j = P.get((sd, "jng"))
        if j:
            f["jng_comfort"] += sg * np.log1p(cnt[(j.playerid, j.champion)])
            c = Counter(ch for tt, ch in hist[j.playerid] if t - tt <= 180); f["jng_pool"] += sg * sum(1 for v in c.values() if v >= 3)
            for other, k in (("mid", "tt_jng_mid"), ("bot", "tt_jng_bot")):
                o = P.get((sd, other))
                if o: f[k] += sg * np.log1p(together[tuple(sorted((j.playerid, o.playerid)))])
    return f
for d, rows in raw.sort_values("date").groupby("day", sort=True):
    t = rows.t.iloc[0]
    for g, gr in rows.groupby("gameid"):
        if gr.league.iloc[0] in MAJOR: feats[g] = features(gr, t)
    for r in rows.itertuples(index=False):
        if isinstance(r.playerid, str): cnt[(r.playerid, r.champion)] += 1; hist[r.playerid].append((t, r.champion))
    for (g, sd), gr in rows.groupby(["gameid", "side"]):
        ids = sorted({p for p in gr.playerid if isinstance(p, str)})
        for a, b in itertools.combinations(ids, 2): together[(a, b)] += 1
FEAT = ["jng_comfort", "jng_pool", "tt_jng_mid", "tt_jng_bot"]
F = pd.DataFrame.from_dict(feats, orient="index")
V = pd.read_csv(V1).dropna(subset=["z_v1"]).set_index("gameid"); V["day"] = V.date.str[:10]
D = V.join(F, how="inner")
sd = D.loc[D.day < "2026-09-01", FEAT].std()
X = lambda d: (d[FEAT] / sd).values
def fit(Z, Xm, y, lam=1.0):
    b = np.zeros(Xm.shape[1])
    for _ in range(80):
        p = 1 / (1 + np.exp(-(Z + Xm @ b))); g = Xm.T @ (p - y) + lam * b
        H = (Xm * (p * (1 - p))[:, None]).T @ Xm + lam * np.eye(Xm.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-10: break
    return b
def ll(Z, Xm, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + Xm @ b))), 1e-6, 1 - 1e-6); return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)
fav = lambda Z, Xm, y, b: round(float(np.mean(((Z + Xm @ b) > 0) == (y == 1))), 3)
b_all = fit(D.z_v1.values, X(D), D.blue_win.values)
tr = D[(D.day >= "2026-02-01") & (D.day < "2026-09-01")]; te = D[D.day >= "2026-09-01"]; wo = D[D.league == "WLDs"]
b_ref = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
z = lambda d: np.zeros((len(d), len(FEAT)))
R = {"decided": "2026-11-05 AEST, Luke ('Yes, fix it')", "data_to": str(pd.read_csv(V1).date.max()), "games_fitted": len(D),
     "features": FEAT, "feature_sd_before_1_Sep": sd.round(4).to_dict(), "weights_per_sd": dict(zip(FEAT, np.round(b_all, 4).tolist())),
     "rule": "logit = z_v1 + sum(w * x / sd); x = blue minus red; each feature from earlier days only; ridge 1.0",
     "reference_not_fair_test": {"weights_fit_before_1_Sep": dict(zip(FEAT, np.round(b_ref, 4).tolist())),
                                 "from_1_Sep": {"games": len(te), "v1": ll(te.z_v1.values, z(te), te.blue_win.values, np.zeros(4)),
                                                "candidate": ll(te.z_v1.values, X(te), te.blue_win.values, b_ref),
                                                "fav_v1": fav(te.z_v1.values, z(te), te.blue_win.values, np.zeros(4)), "fav_candidate": fav(te.z_v1.values, X(te), te.blue_win.values, b_ref)},
                                 "worlds": {"games": len(wo), "v1": ll(wo.z_v1.values, z(wo), wo.blue_win.values, np.zeros(4)),
                                            "candidate": ll(wo.z_v1.values, X(wo), wo.blue_win.values, b_ref)}},
     "knockout_test": "when a newer Oracle's Elixir file has the knockout games: compute the four features as above (earlier days only, history up to each game), apply these weights unchanged, and compare log loss and favourite record with v1 on the knockout games only"}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
