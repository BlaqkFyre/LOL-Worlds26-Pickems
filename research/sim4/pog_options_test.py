"""Ratings and Player of the Game options, scored on real award games (14 Nov 2026 AEST; Luke: support ratings too high v other roles,
POG should follow in-game performance; "choose the best tested one"). Read-only.
Held-out: per-game award games from 1 Sep (LPL, LCS) with version C weights fitted before 1 Sep (research/model/pog/pog_fit.json).
Also all award games with the app's weights (in-sample, shown for size only).
  now   rating = within-role percentile of the score without role terms; POG drawn from the award chances (expected hit rate, log loss)
  A     rating = percentile of the full score (with fitted role terms) among all roles; "top-rated winner" = highest full score
  B     POG = the winner with the highest award chance (same ranking as A)
Per option: share of games where the pick (top-rated winner / POG) is the real award winner, and award shares by role.
usage (repo root): python -I research/sim4/pog_options_test.py <out_json>"""
import sys, json, numpy as np, pandas as pd
ROLES = ["top", "jng", "mid", "bot", "sup"]; F = json.load(open("research/model/pog/pog_fit.json")); A = json.load(open("research/model/pog/pog_app.json"))
G = pd.read_csv("research/local/pog/pog_games_matched.csv"); G = G[G.result == 1].dropna(subset=["kills", "deaths", "assists", "damageshare", "vspm"]).copy()
G["kp"] = ((G.kills + G.assists) / G.teamkills.clip(lower=1)).clip(upper=1); G["csd15"] = G.csdiffat15.fillna(0)
G = G[(G.groupby("gameid").position.transform("size") == 5) & (G.groupby("gameid").mvp.transform("sum") == 1)]
def run(D, W, mean, sd):
    D = D.copy(); C = list(mean); D["s"] = sum(W[c] * (D[c] - mean[c]) / sd[c] for c in C); D["u"] = D.s + D.position.map(lambda r: W.get("r_" + r, 0.0))
    D["pct"] = [np.interp(v, A["pct"][r], np.linspace(0, 100, 101)) for v, r in zip(D.s, D.position)]  # today's within-role rating
    D["p"] = np.exp(D.u - D.groupby("gameid").u.transform("max")); D["p"] /= D.groupby("gameid").p.transform("sum")
    now_top = D.loc[D.groupby("gameid").pct.idxmax()]; a_top = D.loc[D.groupby("gameid").u.idxmax()]; real = D[D.mvp == 1]
    sh = lambda d: {r: round(float((d.position == r).mean()), 3) for r in ROLES}
    return {"games": int(D.gameid.nunique()),
            "now: top-rated winner is the real POG": round(float(now_top.mvp.mean()), 3),
            "now: POG draw, expected share right": round(float(real.p.mean()), 3), "now: POG draw, log loss": round(float(-np.log(real.p).mean()), 4),
            "A/B: top full-score winner is the real POG": round(float(a_top.mvp.mean()), 3),
            "award share by role": {"now (draw, expected)": {r: round(float(D[D.position == r].p.sum() / D.gameid.nunique()), 3) for r in ROLES},
                                    "now (top-rated winner)": sh(now_top), "A/B (top full score)": sh(a_top), "real": sh(real)}}
R = {"held out: games from 1 Sep, weights fitted before 1 Sep": run(G[G.date >= "2026-09-01"], F["C_plus_series_awards"]["weights"], F["standardise_mean"], F["standardise_sd"]),
     "all award games, app weights (in-sample)": run(G, A["w"], A["mean"], A["sd"])}
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
