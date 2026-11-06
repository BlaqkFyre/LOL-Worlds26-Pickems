"""Player of the Game model, refit for session 4 (research): only stats the new sim produces, series awards as extra training data.
Choice among the winning side's five. Inputs (standardised on training winners): kills, deaths, assists, kill participation,
damage share, CS lead at 15 (0 where the file has none, about 6-14% of rows), vision per minute, role (jungle / mid / ADC / support v top).
Fitted on games before 1 Sep; judged on games from 1 Sep (per-game awards: LPL, LCS) and series from 1 Sep (all leagues, Worlds included).
  A  today's app formula (gameStats weights on real box scores; solo kills and star bonus left out, support vision at "normal"),
     turned into chances with one fitted temperature
  B  per-game awards only
  C  per-game awards + series awards (series MVP chance = mean of the player's per-game chances over the games his team won)
Writes the weights, the scores and the role shares to <out json>.
usage: python -I pog_fit.py <OE csv> <pog dir> <out json>"""
import json, os, sys
import numpy as np
import pandas as pd

CSV, D, OUT = sys.argv[1:4]
F = ["kills", "deaths", "assists", "kp", "damageshare", "csd15", "vspm", "r_jng", "r_mid", "r_bot", "r_sup"]
CONT = F[:7]
# today's app score for every major player-game (as in pog_pct_compare.py)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
o = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "playername", "result", "kills", "deaths", "assists",
                                                 "teamkills", "damageshare", "csdiffat15", "vspm", "dragons", "void_grubs", "barons"])
o = o[o.league.isin(MAJOR)]
tm = o[o.position == "team"].set_index(["gameid", "side"])[["dragons", "void_grubs", "barons"]].fillna(0).sum(axis=1)
o = o[o.position != "team"].copy()
o["objs"] = [tm.get((g, s), 0) for g, s in zip(o.gameid, o.side)]
R = {"top": "TOP", "jng": "JGL", "mid": "MID", "bot": "ADC", "sup": "SUP"}; r = o.position.map(R)
ROLE_SHARE = {"TOP": .22, "JGL": .15, "MID": .27, "ADC": .29, "SUP": .07}; DMG_CAP = {"TOP": 1.6, "JGL": 1.6, "MID": 1.6, "ADC": 1.6, "SUP": 1.3}
OBJ_W = {"TOP": 0, "JGL": .10, "MID": 0, "ADC": 0, "SUP": .10}; ROLE_ADJ = {"TOP": 1.06, "JGL": .99, "MID": .975, "ADC": .965, "SUP": .985}
kp = ((o.kills + o.assists) / o.teamkills.clip(lower=1)).clip(upper=1); csd = o.csdiffat15.fillna(0) * np.where(r == "SUP", 0.3, 1)
app = (1.5 * o.result + 2 * ((o.kills + o.assists) / o.deaths.clip(lower=1)).clip(upper=10) / 10 + 2 * kp + 0.12 * o.kills.clip(upper=10)
       + 1.6 * np.minimum(r.map(DMG_CAP), o.damageshare / r.map(ROLE_SHARE)) + 0.9 * (csd / 20).clip(-1, 1) + r.map(OBJ_W) * o.objs - 0.15 * o.deaths)
o["app"] = (app * r.map(ROLE_ADJ)).clip(0, 10)
APP = o.set_index(["gameid", "playername"]).app

def prep(X):
    X = X.copy(); X["kp"] = ((X.kills + X.assists) / X.teamkills.clip(lower=1)).clip(upper=1); X["csd15"] = X.csdiffat15.fillna(0)
    for k in ["jng", "mid", "bot", "sup"]: X["r_" + k] = (X.position == k).astype(float)
    X["app"] = [APP.get((g, p), np.nan) for g, p in zip(X.gameid, X.playername)]
    return X.dropna(subset=["kills", "deaths", "assists", "damageshare", "vspm", "app"])
G = prep(pd.read_csv(os.path.join(D, "pog_games_matched.csv"))); S = prep(pd.read_csv(os.path.join(D, "pog_series_matched.csv")))
G = G[G.result == 1]; G = G[G.groupby("gameid").position.transform("size") == 5]; G = G[G.groupby("gameid").mvp.transform("sum") == 1]
S["won_series"] = S.groupby(["series", "teamname"]).result.transform("sum") > S.groupby("series").gameid.transform("nunique") / 2
S = S[S.won_series & (S.result == 1)]; S = S[S.groupby("gameid").position.transform("size") == 5]
S = S[S.groupby("series").mvp.transform("max") == 1]
# don't count LPL / LCS / First Stand series twice: their games already carry per-game awards
S = S[~S.lg.isin(["LPL", "LCS", "FST"])]
tr = lambda X: X[X.date < "2026-09-01"]; te = lambda X: X[X.date >= "2026-09-01"]
mu, sd = tr(G)[CONT].mean(), tr(G)[CONT].std()
for X in (G, S): X[CONT] = (X[CONT] - mu) / sd

class Block:
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

def evaluate(b, cols):
    out = {}
    for nm, X, kd in [("games from 1 Sep (LPL, LCS)", te(G), "g"), ("series from 1 Sep (LCK, LEC, CBLOL, Worlds)", te(S), "s")]:
        if X.empty: continue
        B = Block(X, cols); p = B.probs(b); X = X.assign(p=p)
        if kd == "g":
            top = X.loc[X.groupby("gameid").p.idxmax()]
            out[nm] = {"n": int(X.gameid.nunique()), "right": round(float(top.mvp.mean()), 3), "log_loss": round(-B.game_ll(b)[0] / X.gameid.nunique(), 4)}
        else:
            a = X.groupby(["series", "playername"]).agg(p=("p", "sum"), mvp=("mvp", "max")).reset_index()
            a["p"] = a.p / a.groupby("series").p.transform("sum")
            top = a.loc[a.groupby("series").p.idxmax()]
            out[nm] = {"n": int(a.series.nunique()), "right": round(float(top.mvp.mean()), 3), "log_loss": round(float(-np.log(a[a.mvp == 1].p).mean()), 4)}
    return out

res = {"training": {"per-game award games": int(tr(G).gameid.nunique()), "series (LCK, LEC, CBLOL, LCP, internationals)": int(tr(S).series.nunique())},
       "held_out": {"games": int(te(G).gameid.nunique()), "series": int(te(S).series.nunique()), "series_by_league": te(S).groupby("lg").series.nunique().to_dict()}}
# A: app formula with one temperature
A_cols = ["app"]
bA = fit([Block(tr(G), A_cols)], ["g"], 1, l2=0.01)
res["A_app_formula"] = {"temperature_weight": round(float(bA[0]), 3), **evaluate(bA, A_cols)}
bB = fit([Block(tr(G), F)], ["g"], len(F))
res["B_per_game_awards"] = {"weights": dict(zip(F, np.round(bB, 3))), **evaluate(bB, F)}
bC = fit([Block(tr(G), F), Block(tr(S), F)], ["g", "s"], len(F))
res["C_plus_series_awards"] = {"weights": dict(zip(F, np.round(bC, 3))), **evaluate(bC, F)}
res["chance"] = {"game": "1 in 5 (log loss 1.609)", "series": "about 1 in 5"}
# role shares the model gives on held-out games v real
X = te(G).assign(p=Block(te(G), F).probs(bC))
res["role_share_held_out_games"] = {"model_C": X.groupby("position").p.sum().div(X.gameid.nunique()).round(3).to_dict(),
                                    "real": X[X.mvp == 1].position.value_counts(normalize=True).round(3).to_dict()}
json.dump({"standardise_mean": mu.round(4).to_dict(), "standardise_sd": sd.round(4).to_dict(), **res}, open(OUT, "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))

# second check, whole leagues held out (bigger samples): per-game awards fitted on LPL only, judged on all LCS + First Stand games;
# series awards fitted without LCK, judged on all 188 LCK series (the LCK never enters any fit)
def evaluate2(b, cols):
    out = {}
    X = G[G.lg != "LPL"]; B = Block(X, cols); X = X.assign(p=B.probs(b)); top = X.loc[X.groupby("gameid").p.idxmax()]
    out["LCS + First Stand games (all dates)"] = {"n": int(X.gameid.nunique()), "right": round(float(top.mvp.mean()), 3), "log_loss": round(-B.game_ll(b)[0] / X.gameid.nunique(), 4)}
    X = S[S.lg == "LCK"]; X = X.assign(p=Block(X, cols).probs(b))
    a = X.groupby(["series", "playername"]).agg(p=("p", "sum"), mvp=("mvp", "max")).reset_index(); a["p"] = a.p / a.groupby("series").p.transform("sum")
    top = a.loc[a.groupby("series").p.idxmax()]
    out["LCK series (all dates)"] = {"n": int(a.series.nunique()), "right": round(float(top.mvp.mean()), 3), "log_loss": round(float(-np.log(a[a.mvp == 1].p).mean()), 4)}
    return out
GL = G[G.lg == "LPL"]; SL = S[S.lg != "LCK"]
res2 = {"A_app_formula": evaluate2(fit([Block(GL, A_cols)], ["g"], 1, l2=0.01), A_cols),
        "B_per_game_awards": evaluate2(fit([Block(GL, F)], ["g"], len(F)), F),
        "C_plus_series_awards": evaluate2(fit([Block(GL, F), Block(SL, F)], ["g", "s"], len(F)), F)}
r0 = json.load(open(OUT)); r0["league_held_out"] = res2; json.dump(r0, open(OUT, "w"), indent=1, default=float)
print(json.dumps(res2, indent=1))
