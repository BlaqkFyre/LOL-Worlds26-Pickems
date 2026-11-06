"""Percentile-based rating, two scores (Luke, 6 Nov: lean on real data, not hand-made numbers):
  app    today's per-game rating formula (js/tournament.js gameStats, its own weights) on real box scores; solo kills and the star
         bonus left out (not in the file / not the same for every player), support vision at "normal" (adds 0)
  quick  the quick Player of the Game model's performance score (pog_measure.json weights, role terms left out)
Each score becomes a percentile within the role among major-league player-games before 1 Sep; rating = percentile x 10.
Shows game <gameid>, and how winners and losers spread on games from 1 Sep (held out).
usage: python -I pog_pct_compare.py <OE csv> <pog_measure.json> <gameid>"""
import json, sys
import numpy as np
import pandas as pd

CSV, MJ, GID = sys.argv[1:4]
W = json.load(open(MJ))["choice_model"]["weights"]
FE = ["kills", "deaths", "assists", "damageshare", "earnedgoldshare", "kp", "golddiffat15", "vspm", "damagetakenperminute"]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
cols = ["gameid", "league", "date", "side", "position", "playername", "result", "teamkills", "csdiffat15", "dragons", "void_grubs", "barons"] + [f for f in FE if f != "kp"]
d = pd.read_csv(CSV, low_memory=False, usecols=cols)
d = d[d.league.isin(MAJOR) & ~((d.league == "WLDs") & (d.date < "2026-10-01"))].copy()
tm = d[d.position == "team"].set_index(["gameid", "side"])
d = d[d.position != "team"].copy()
d["objs"] = [tm.loc[(g, s), ["dragons", "void_grubs", "barons"]].fillna(0).sum() for g, s in zip(d.gameid, d.side)]
d["kp"] = (d.kills + d.assists) / d.teamkills.clip(lower=1)
# app formula (js/tournament.js lines 84-128)
R = {"top": "TOP", "jng": "JGL", "mid": "MID", "bot": "ADC", "sup": "SUP"}
ROLE_SHARE = {"TOP": .22, "JGL": .15, "MID": .27, "ADC": .29, "SUP": .07}; DMG_CAP = {"TOP": 1.6, "JGL": 1.6, "MID": 1.6, "ADC": 1.6, "SUP": 1.3}
OBJ_W = {"TOP": 0, "JGL": .10, "MID": 0, "ADC": 0, "SUP": .10}; ROLE_ADJ = {"TOP": 1.06, "JGL": .99, "MID": .975, "ADC": .965, "SUP": .985}
r = d.position.map(R)
csd = d.csdiffat15.fillna(0) * np.where(r == "SUP", 0.3, 1)
kda = (d.kills + d.assists) / d.deaths.clip(lower=1)
app = (1.5 * d.result + 2 * kda.clip(upper=10) / 10 + 2 * d.kp.clip(upper=1) + 0.12 * d.kills.clip(upper=10)
       + 1.6 * np.minimum(r.map(DMG_CAP), d.damageshare / r.map(ROLE_SHARE)) + 0.9 * (csd / 20).clip(-1, 1)
       + r.map(OBJ_W) * d.objs - 0.15 * d.deaths)
d["app"] = (app * r.map(ROLE_ADJ)).clip(0, 10)
ref = d[(d.result == 1) & (d.date < "2026-09-01")].dropna(subset=FE)
mu, sd = ref[FE].mean(), ref[FE].std()
d = d.dropna(subset=FE + ["app"])
d["quick"] = sum(W[f] * (d[f] - mu[f]) / sd[f] for f in FE)
base = d[d.date < "2026-09-01"]
def pct(df, col):
    out = pd.Series(index=df.index, dtype=float)
    for pos, x in df.groupby("position"):
        ref_s = np.sort(base[base.position == pos][col].values)
        out[x.index] = np.searchsorted(ref_s, x[col].values, side="right") / len(ref_s)
    return out
for c in ["app", "quick"]: d[c + "_rating"] = (10 * pct(d, c)).round(1)
g = d[d.gameid == GID].copy()
g["kda"] = g.kills.astype(int).astype(str) + "/" + g.deaths.astype(int).astype(str) + "/" + g.assists.astype(int).astype(str)
print(g[["playername", "position", "result", "kda", "app", "app_rating", "quick_rating"]].round(2).to_string(index=False))
h = d[d.date >= "2026-09-01"]
summ = {}
for c in ["app_rating", "quick_rating"]:
    summ[c] = {"winners_mean": round(float(h[h.result == 1][c].mean()), 2), "losers_mean": round(float(h[h.result == 0][c].mean()), 2),
               "losers_5_plus": round(float((h[h.result == 0][c] >= 5).mean()), 3), "winners_below_5": round(float((h[h.result == 1][c] < 5).mean()), 3)}
print("held-out player-games from 1 Sep:", len(h)); print(json.dumps(summ, indent=1))
