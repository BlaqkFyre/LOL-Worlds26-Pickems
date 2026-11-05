"""Farming habit, every role (Luke, 5 Nov: test jungle farming; "if a piece of data feeds into the sim for one role, investigate
how other roles may get relevant inputs too"). From the Oracle's Elixir file (major leagues, all games):
  habit     a player's CS at 15 in their earlier games (strictly earlier dates), pulled toward the role average of earlier games
            (k = 10 games)
  stability first half v second half of each player's games (players with 16+ games), raw CS at 15 and CS at 15 minus the
            game's role average for that patch window (so a slow meta doesn't count as a habit)
  tests     beyond v1 and side (blue minus red habit, per sd), fitted before 1 Sep, judged from 1 Sep and on Worlds:
            who wins (log loss); the role's gold lead at 15 (rmse); jungle: first dragon, first Herald, more grubs
usage: python -I s3_farm.py <OE csv> v1_games.csv <out_json>"""
import sys, json
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, OUTJ = sys.argv[1:4]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]
c = ["gameid", "league", "date", "side", "position", "playerid", "playername", "csat15", "golddiffat15", "firstdragon", "firstherald",
     "void_grubs", "opp_void_grubs", "result"]
raw = pd.read_csv(CSV, low_memory=False, usecols=c)
raw = raw[raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
P = raw[raw.position.isin(ROLES)].dropna(subset=["csat15", "playerid"]).copy()
# relative CS: minus the role's average over the previous 30 days (meta / patch pace)
P = P.sort_values("date")
P["rel"] = np.nan
for r_ in ROLES:
    d = P[P.position == r_]
    days = sorted(d.day.unique()); mu = {}
    for dy in days:
        lo = (pd.Timestamp(dy) - pd.Timedelta(days=30)).strftime("%Y-%m-%d"); w = d[(d.day < dy) & (d.day >= lo)]
        mu[dy] = w.csat15.mean() if len(w) >= 20 else d.csat15.mean()
    P.loc[d.index, "rel"] = d.csat15 - d.day.map(mu)
res = {"games": int(P.gameid.nunique())}
# stability
st = {}
for r_ in ROLES:
    d = P[P.position == r_].groupby("playerid").filter(lambda x: len(x) >= 16)
    h = d.groupby("playerid").apply(lambda x: pd.Series({"a_raw": x.csat15.iloc[:len(x) // 2].mean(), "b_raw": x.csat15.iloc[len(x) // 2:].mean(),
                                                        "a_rel": x.rel.iloc[:len(x) // 2].mean(), "b_rel": x.rel.iloc[len(x) // 2:].mean()}))
    st[r_] = {"players": len(h), "raw": round(float(h.a_raw.corr(h.b_raw)), 3), "relative": round(float(h.a_rel.corr(h.b_rel)), 3)}
res["stability_first_v_second_half"] = st
# pre-game habit (relative CS), earlier days only, shrunk toward 0 (the role average) with k = 10
K = 10; hist = defaultdict(list); hab = {}
for dy, dd in P.groupby("day", sort=True):
    for i in dd.index:
        h = hist[dd.at[i, "playerid"]]; hab[i] = sum(h) / (len(h) + K);
    for i in dd.index: hist[dd.at[i, "playerid"]].append(dd.at[i, "rel"])
P["habit"] = pd.Series(hab)
v1 = pd.read_csv(V1).set_index("gameid")
W = P.pivot_table(index="gameid", columns=["side", "position"], values="habit", aggfunc="first")
W.columns = [f"{s.lower()}_{p}" for s, p in W.columns]
T = raw[raw.position == "team"]; b = T[T.side == "Blue"].set_index("gameid")
gd = P[P.side == "Blue"].pivot_table(index="gameid", columns="position", values="golddiffat15")
W["z"] = v1.z_v1.reindex(W.index); W["y"] = b.result.reindex(W.index); W["fd"] = b.firstdragon.reindex(W.index); W["fh"] = b.firstherald.reindex(W.index)
W["grubs"] = (b.void_grubs > b.opp_void_grubs).astype(float).reindex(W.index)
for r_ in ROLES: W[f"gd_{r_}"] = gd[r_].reindex(W.index)
W["league"] = b.league.reindex(W.index); W["date"] = b.date.reindex(W.index)
W["split"] = np.where(W.league == "WLDs", "Worlds", np.where(W.date < "2026-09-01", "train", "from 1 Sep"))
W = W.dropna(subset=["z", "y"])
def lfit(X, y, l2=1.0):
    bb = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ bb)); bb += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(bb)), X.T @ (y - p) - l2 * bb)
    return bb
ll = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
res["who_wins"] = {}; res["gold_at_15"] = {}; res["jungle_objectives"] = {}
for r_ in ROLES + ["all five"]:
    rs = ROLES if r_ == "all five" else [r_]
    d = W.dropna(subset=[f"blue_{x}" for x in rs] + [f"red_{x}" for x in rs]); tr = (d.split == "train").values
    diff = np.c_[[d[f"blue_{x}"] - d[f"red_{x}"] for x in rs]].T; sd = diff[tr].std(axis=0); sd[sd == 0] = 1; diff = diff / sd
    X0 = np.c_[np.ones(len(d)), d.z]; X1 = np.c_[X0, diff]; y = d.y.values
    b0 = lfit(X0[tr], y[tr]); b1 = lfit(X1[tr], y[tr])
    o = {"weights_per_sd": np.round(b1[2:], 4).tolist()}
    for s_ in ["train", "from 1 Sep", "Worlds"]:
        q = (d.split == s_).values; o[s_] = {"games": int(q.sum()), "v1": round(ll(1 / (1 + np.exp(-X0[q] @ b0)), y[q]), 4), "v1_plus_habit": round(ll(1 / (1 + np.exp(-X1[q] @ b1)), y[q]), 4)}
    res["who_wins"][r_] = o
    if r_ != "all five":
        dd = d.dropna(subset=[f"gd_{r_}"]); tr2 = (dd.split == "train").values; x = ((dd[f"blue_{r_}"] - dd[f"red_{r_}"]) / sd[0]).values
        X0 = np.c_[np.ones(len(dd)), dd.z]; X1 = np.c_[X0, x]; yy = dd[f"gd_{r_}"].values
        g0, *_ = np.linalg.lstsq(X0[tr2], yy[tr2], rcond=None); g1, *_ = np.linalg.lstsq(X1[tr2], yy[tr2], rcond=None)
        o2 = {"gold_per_sd": round(float(g1[2]), 1)}
        for s_ in ["train", "from 1 Sep", "Worlds"]:
            q = (dd.split == s_).values
            o2[s_] = {"rmse_v1": round(float(np.sqrt(np.mean((yy[q] - X0[q] @ g0) ** 2)))), "rmse_plus_habit": round(float(np.sqrt(np.mean((yy[q] - X1[q] @ g1) ** 2))))}
        res["gold_at_15"][r_] = o2
for nm, yc in [("first dragon", "fd"), ("first Herald", "fh"), ("more grubs", "grubs")]:
    d = W.dropna(subset=[yc, "blue_jng", "red_jng"]); tr = (d.split == "train").values
    x = (d.blue_jng - d.red_jng).values; x = x / x[tr].std()
    X0 = np.c_[np.ones(len(d)), d.z]; X1 = np.c_[X0, x]; y = d[yc].values
    b0 = lfit(X0[tr], y[tr]); b1 = lfit(X1[tr], y[tr]); o = {"weight_per_sd": round(float(b1[2]), 4)}
    for s_ in ["train", "from 1 Sep", "Worlds"]:
        q = (d.split == s_).values; o[s_] = {"v1": round(ll(1 / (1 + np.exp(-X0[q] @ b0)), y[q]), 4), "v1_plus_habit": round(ll(1 / (1 + np.exp(-X1[q] @ b1)), y[q]), 4)}
    res["jungle_objectives"][nm] = o
json.dump(res, open(OUTJ, "w"), indent=1)
print(json.dumps(res, indent=1))
