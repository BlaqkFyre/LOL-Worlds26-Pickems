"""Example of the proposed per-game rating: the quick Player of the Game model's performance score (weights from pog_measure.json,
role terms left out), compared with every major-league player-game before 1 Sep in the same role (winners and losers).
Shows the percentile and one example 0-10 scale (6 + 1.5 x standard deviations above the role average, clipped 0-10).
usage: python -I pog_rate_example.py <OE csv> <pog_measure.json> <gameid>"""
import json, sys
import numpy as np
import pandas as pd

CSV, MJ, GID = sys.argv[1:4]
M = json.load(open(MJ))["choice_model"]; W = M["weights"]
FE = ["kills", "deaths", "assists", "damageshare", "earnedgoldshare", "kp", "golddiffat15", "vspm", "damagetakenperminute"]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
d = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "position", "playername", "teamname", "result", "teamkills"] + [f for f in FE if f != "kp"])
d = d[d.league.isin(MAJOR) & (d.position != "team") & ~((d.league == "WLDs") & (d.date < "2026-10-01"))].copy()
d["kp"] = (d.kills + d.assists) / d.teamkills.clip(lower=1)
# standardise as the model was fitted: mean / sd of winning players (pog_measure.py used the LPL/LCS/FST award games' winners;
# here the 2026 major-league winners before 1 Sep, close to that)
ref = d[(d.result == 1) & (d.date < "2026-09-01")].dropna(subset=FE)
mu, sd = ref[FE].mean(), ref[FE].std()
d = d.dropna(subset=FE)
d["score"] = sum(W[f] * (d[f] - mu[f]) / sd[f] for f in FE)
base = d[d.date < "2026-09-01"]
st = base.groupby("position").score.agg(["mean", "std"])
g = d[d.gameid == GID].copy()
g["pct"] = [float((base[base.position == r].score < s).mean()) for r, s in zip(g.position, g.score)]
g["z"] = [(s - st.loc[r, "mean"]) / st.loc[r, "std"] for r, s in zip(g.position, g.score)]
g["rating_example"] = (6 + 1.5 * g.z).clip(0, 10)
g["kda"] = g.kills.astype(int).astype(str) + "/" + g.deaths.astype(int).astype(str) + "/" + g.assists.astype(int).astype(str)
print("reference player-games before 1 Sep:", len(base))
print(g[["teamname", "position", "playername", "kda", "score", "pct", "z", "rating_example"]].round(2).to_string(index=False))
