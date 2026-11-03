"""Four ways to put the overall on a card (Luke, 3 Nov: try all, compare, then choose). Reads league-adjusted cards and team ratings.
 S0 current: percentile among all major-league players with 10+ games (50-99)
 S1 Worlds field: percentile among the 16 Worlds players in that role (50 = weakest, 99 = best)
 S2 impact: 70 + 10 x win-chance swing (percentage points) v the average major-league player in that role
 S3 team share: stats overall (in team-rating units) + 1/5 of the team's unexplained strength, percentile among all major players
 S4 Worlds + team share: S3's value ranked within the Worlds field"""
import sys
import numpy as np
import pandas as pd

L = {"CBLOL": -0.79, "LCK": 1.49, "LCP": -0.72, "LCS": -0.12, "LEC": 0.14, "LPL": 0.95}
G = pd.read_csv("games.csv"); TR = pd.read_csv("out/team_ratings_now.csv"); PC = pd.read_csv("out/player_cards_league_adjusted.csv"); PR = pd.read_csv("prow.csv")
lab2oe = {}
for r in G.itertuples():
    for app, nm in ((r.blue_app, r.blue_name), (r.red_app, r.red_name)):
        lab2oe[app if isinstance(app, str) and app else nm] = nm
TR["oe"] = TR.team.map(lab2oe)
pos = {"TOP": "top", "JGL": "jng", "MID": "mid", "ADC": "bot", "SUP": "sup"}
lastp = PR.sort_values("date").groupby(["teamname", "position"]).playername.last().reset_index()
pcm = PC.assign(position=PC.role.map(pos))[["name", "position", "Overall"]]
agg = lastp.merge(pcm, left_on=["playername", "position"], right_on=["name", "position"], how="left").groupby("teamname").Overall.sum(min_count=5)
T = TR.merge(agg.rename("ps"), left_on="oe", right_index=True).dropna(subset=["ps"])
T["L"] = T.home.map(L).fillna(0)
A = np.c_[np.ones(len(T)), T.ps, T.L]; c, *_ = np.linalg.lstsq(A, T.rating, rcond=None)
T["unexp"] = T.rating - A @ c; SCALE = c[1]
unexp = T.set_index("oe").unexp.to_dict()
C = PC.copy()
C["tp"] = SCALE * C.Overall + C.team.map(unexp).fillna(0) / 5
pool = C[C.games >= 10]
pct = lambda v, ref: round(50 + 49 * float((ref < v).mean()))
for role in C.role.unique():
    m = C.role == role; ref = pool[pool.role == role]
    mu = ref.Overall.mean()
    C.loc[m, "S0"] = C.loc[m, "Overall"].apply(lambda v: pct(v, ref.Overall.values))
    C.loc[m, "S2"] = C.loc[m, "Overall"].apply(lambda v: round(70 + 10 * 100 * (1 / (1 + np.exp(-(v - mu))) - 0.5)))
    C.loc[m, "S3"] = C.loc[m, "tp"].apply(lambda v: pct(v, ref.tp.values))
W = C[C.worlds_roster].copy()
for role in W.role.unique():
    m = W.role == role; n = m.sum()
    for src, dst in (("Overall", "S1"), ("tp", "S4")):
        vals = W.loc[m, src].values
        W.loc[m, dst] = W.loc[m, src].apply(lambda v: round(50 + 49 * float((vals < v).sum()) / (n - 1)))
W = W.sort_values(["role", "S4"], ascending=[True, False])
W[["role", "name", "team", "home", "games", "S0", "S1", "S2", "S3", "S4"]].to_csv("out/card_scales.csv", index=False)
print(f"team-play scale {SCALE:.2f}; unexplained by Worlds team:", {k: round(v, 2) for k, v in T[T.team.isin(W.team.map(lambda x: x))].set_index('team').unexp.items()} if False else "")
for s in ("S0", "S1", "S2", "S3", "S4"):
    print(s, "bands:", pd.cut(W[s], [0, 60, 70, 80, 85, 90, 95, 100]).value_counts().sort_index().values.tolist(), "mean", round(W[s].mean(), 1))
print(W[["role", "name", "home", "S0", "S1", "S2", "S3", "S4"]].to_string(index=False))
