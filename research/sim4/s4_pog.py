"""Sim session 4 (13 Nov 2026 AEST): Player of the Game version C and the per-game rating for the app.
Version C (Luke, 6 Nov; research/pog/pog_fit.py): a choice among the winning side's five, fitted on per-game awards (LPL, LCS, First Stand)
plus series awards (LCK, LEC, CBLOL, LCP, MSI, EWC, Worlds; a series MVP's chance = mean of his per-game chances over the games his team won),
using only stats the new sim produces: kills, deaths, assists, kill participation, damage share, CS lead at 15, vision per minute, role.
This script:
  1. refits C on games before 1 Sep and checks the weights against research/model/pog/pog_fit.json (same data, same fit: must match)
  2. refits C on every award to date (as the sim's tables are refit on every game; Luke 12 Nov)
  3. the rating: each player-game's score (the weights on the stats, no role term) as a percentile among real major-league player-games
     in the same role before the cutoff, / 10; stored as 101 score quantiles per role (0th to 100th percentile)
  4. checks on real games from 1 Sep: average rating of winners and losers, share of losers rated 5 or more
usage (repo root): python -I research/sim4/s4_pog.py <OE csv> <pog matched dir> <pog_fit.json> <out json> [--cutoff 2026-11-10]"""
import json, os, sys
import numpy as np, pandas as pd

a = sys.argv[1:]; CSV, D, PF, OUT = a[:4]; CUTD = a[a.index("--cutoff") + 1] if "--cutoff" in a else "2026-11-10"
F = ["kills", "deaths", "assists", "kp", "damageshare", "csd15", "vspm", "r_jng", "r_mid", "r_bot", "r_sup"]; CONT = F[:7]
ROLES = ["top", "jng", "mid", "bot", "sup"]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}

def prep(X):
    X = X.copy(); X["kp"] = ((X.kills + X.assists) / X.teamkills.clip(lower=1)).clip(upper=1); X["csd15"] = X.csdiffat15.fillna(0)
    for k in ["jng", "mid", "bot", "sup"]: X["r_" + k] = (X.position == k).astype(float)
    return X.dropna(subset=["kills", "deaths", "assists", "damageshare", "vspm"])
# the same rows as pog_fit.py (it also drops rows where its app-formula score is missing; that score uses the same stats, so the rows match)
G0 = prep(pd.read_csv(os.path.join(D, "pog_games_matched.csv"))); S0 = prep(pd.read_csv(os.path.join(D, "pog_series_matched.csv")))
G0 = G0[G0.result == 1]; G0 = G0[G0.groupby("gameid").position.transform("size") == 5]; G0 = G0[G0.groupby("gameid").mvp.transform("sum") == 1]
S0["won_series"] = S0.groupby(["series", "teamname"]).result.transform("sum") > S0.groupby("series").gameid.transform("nunique") / 2
S0 = S0[S0.won_series & (S0.result == 1)]; S0 = S0[S0.groupby("gameid").position.transform("size") == 5]
S0 = S0[S0.groupby("series").mvp.transform("max") == 1]; S0 = S0[~S0.lg.isin(["LPL", "LCS", "FST"])]
G0 = G0[G0.date < CUTD]; S0 = S0[S0.date < CUTD]

class Block:  # as pog_fit.py
    def __init__(self, X, cols):
        self.X = X[cols].values.astype(float); self.y = X.mvp.values.astype(float)
        self.gid = pd.factorize(X.gameid)[0]; self.ng = self.gid.max() + 1
        self.sid = pd.factorize(X.series)[0] if "series" in X else None
        self.pkey = pd.factorize(X.series.astype(str) + "|" + X.playername)[0] if "series" in X else None
    def probs(self, b):
        s = self.X @ b; m = np.zeros(self.ng); np.maximum.at(m, self.gid, s); e = np.exp(s - m[self.gid])
        z = np.zeros(self.ng); np.add.at(z, self.gid, e); return e / z[self.gid]
    def game_ll(self, b):
        p = self.probs(b); ll = float(np.log(p[self.y == 1]).sum())
        xb = np.zeros((self.ng, self.X.shape[1])); np.add.at(xb, self.gid, self.X * p[:, None])
        return ll, (self.X[self.y == 1] - xb[self.gid[self.y == 1]]).sum(0)
    def series_ll(self, b):
        p = self.probs(b); xb = np.zeros((self.ng, self.X.shape[1])); np.add.at(xb, self.gid, self.X * p[:, None])
        npk = self.pkey.max() + 1; P = np.zeros(npk); np.add.at(P, self.pkey, p)
        num = np.zeros((npk, self.X.shape[1])); np.add.at(num, self.pkey, p[:, None] * (self.X - xb[self.gid]))
        mv = np.unique(self.pkey[self.y == 1])
        ng_s = pd.Series(self.gid).groupby(self.sid).nunique().values; spk = pd.Series(self.sid).groupby(self.pkey).first().values
        ll = float((np.log(P[mv]) - np.log(ng_s[spk[mv]])).sum())
        return ll, (num[mv] / P[mv][:, None]).sum(0)
def fit(blocks, kinds, k, l2=1.0, it=3000, lr=0.05):
    b = np.zeros(k); m = np.zeros(k); v = np.zeros(k)
    for t in range(1, it + 1):
        g = -l2 * b
        for B, kd in zip(blocks, kinds): g += (B.game_ll if kd == "g" else B.series_ll)(b)[1]
        m = 0.9 * m + 0.1 * g; v = 0.999 * v + 0.001 * g * g
        b += lr * (m / (1 - 0.9 ** t)) / (np.sqrt(v / (1 - 0.999 ** t)) + 1e-8) / max(1, len(blocks[0].y) / 500)
    return b
def fit_c(G, S):
    mu, sd = G[CONT].mean(), G[CONT].std(); G, S = G.copy(), S.copy()
    for X in (G, S): X[CONT] = (X[CONT] - mu) / sd
    return fit([Block(G, F), Block(S, F)], ["g", "s"], len(F)), mu, sd

R = {"cutoff": CUTD}
# 1. reproduce the published fit (games before 1 Sep)
b_pre, _, _ = fit_c(G0[G0.date < "2026-09-01"], S0[S0.date < "2026-09-01"])
pub = json.load(open(PF))["C_plus_series_awards"]["weights"]
R["check: refit before 1 Sep v pog_fit.json"] = {f: [round(float(x), 3), pub[f]] for f, x in zip(F, b_pre)}
R["check: largest gap"] = round(max(abs(float(x) - pub[f]) for f, x in zip(F, b_pre)), 4)
# 2. the app's fit: every award to the cutoff
b, mu, sd = fit_c(G0, S0)
R["training"] = {"per-game award games": int(G0.gameid.nunique()), "series": int(S0.series.nunique())}
R["mean"] = mu.round(5).to_dict(); R["sd"] = sd.round(5).to_dict()
R["w"] = {f: round(float(x), 4) for f, x in zip(F, b)}
# 3. rating reference: every major-league player-game before the cutoff (Worlds qualifier rows before 1 Oct left out)
o = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "position", "result", "kills", "deaths", "assists", "teamkills",
                                                 "damageshare", "csdiffat15", "vspm"])
o = o[o.league.isin(MAJOR) & o.position.isin(ROLES) & (o.date < CUTD) & ~((o.league == "WLDs") & (o.date < "2026-10-01"))].copy()
o = prep(o)
score = lambda X: sum(R["w"][c] * (X[c] - mu[c]) / sd[c] for c in CONT)
o["s"] = score(o)
Q = np.linspace(0, 100, 101)
R["pct"] = {r: [round(float(v), 4) for v in np.percentile(o.loc[o.position == r, "s"], Q)] for r in ROLES}
R["reference player-games"] = {r: int((o.position == r).sum()) for r in ROLES}
# 4. checks on games from 1 Sep (in the reference too; the rating is a description, not a prediction)
def rate(X):
    out = np.empty(len(X))
    for r in ROLES:
        m_ = (X.position == r).values; out[m_] = np.interp(X.s.values[m_], R["pct"][r], Q) / 10
    return out
late = o[o.date >= "2026-09-01"].copy(); late["rt"] = rate(late)
R["check: real games from 1 Sep"] = {"player-games": len(late), "winners avg": round(float(late[late.result == 1].rt.mean()), 2),
                                    "losers avg": round(float(late[late.result == 0].rt.mean()), 2),
                                    "losers rated 5+": round(float((late[late.result == 0].rt >= 5).mean()), 3)}
# role shares the model gives among winning fives (all award games to date) v real
X = G0.copy(); X[CONT] = (X[CONT] - mu) / sd; X["p"] = Block(X, F).probs(b)
R["role share, per-game award games: model v real"] = {r: [round(float(X[X.position == r].p.sum() / X.gameid.nunique()), 3),
                                                          round(float(X[(X.position == r) & (X.mvp == 1)].shape[0] / X.gameid.nunique()), 3)] for r in ROLES}
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if k != "pct"}, indent=1))
