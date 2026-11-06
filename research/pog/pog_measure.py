"""What do Player of the Game winners look like? (research for the session 4 plan)
Per game (LPL, LCS, First Stand; Leaguepedia awards matched to the file): winner-team share, role shares, how often the award goes to
the winning side's leader in one stat, and a small choice model (one award among the winning side's five) fitted on LPL games
before 1 Aug and judged on later LPL games and on all LCS + First Stand games (other leagues, never fitted).
Per series: LPL has both kinds of award, so check how the series MVP relates to the per-game awards; then use the per-game model
to name each series' MVP in leagues with series awards only (LCK, LEC, CBLOL, LCP, internationals) and count hits.
usage: python -I pog_measure.py <pog dir> <out json>"""
import json, os, sys
import numpy as np
import pandas as pd

D, OUT = sys.argv[1:3]
G = pd.read_csv(os.path.join(D, "pog_games_matched.csv")); S = pd.read_csv(os.path.join(D, "pog_series_matched.csv"))
res = {}
for X in (G, S):
    X["kda"] = (X.kills + X.assists) / X.deaths.clip(lower=1); X["kp"] = (X.kills + X.assists) / X.teamkills.clip(lower=1)
    X["min"] = X.gamelength / 60
g = G.groupby("gameid")
win = G[G.mvp == 1]
res["games"] = {"n": int(G.gameid.nunique()), "by_league": G.groupby("lg").gameid.nunique().to_dict(),
                "award_on_winning_team": round(float(win.result.mean()), 4),
                "role_share": win.position.value_counts(normalize=True).round(3).to_dict(),
                "role_share_by_league": {lg: d.position.value_counts(normalize=True).round(3).to_dict() for lg, d in win.groupby("lg")}}
# leader in one stat on the winning side
W = G[G.result == 1].copy()
lead = {}
for st in ["kills", "kda", "damageshare", "earnedgoldshare", "kp", "golddiffat15", "dpm", "assists", "visionscore"]:
    w = W.dropna(subset=[st]); top = w.loc[w.groupby("gameid")[st].idxmax()]
    lead[st] = round(float(top.mvp.mean()), 3)
res["games"]["award_to_winning_side_leader_in"] = lead
# choice model among the winning five
FE = ["kills", "deaths", "assists", "damageshare", "earnedgoldshare", "kp", "golddiffat15", "vspm", "damagetakenperminute"]
W = W.dropna(subset=FE).copy()
W = W[W.groupby("gameid").position.transform("size") == 5]
W = W[W.groupby("gameid").mvp.transform("sum") == 1]
for r in ["jng", "mid", "bot", "sup"]: W["r_" + r] = (W.position == r).astype(float)
F = FE + ["r_jng", "r_mid", "r_bot", "r_sup"]
mu, sd = W[FE].mean(), W[FE].std()
W[FE] = (W[FE] - mu) / sd
def fit(d, l2=1.0, it=60):
    X = d[F].values; y = d.mvp.values; gid = pd.factorize(d.gameid)[0]; b = np.zeros(len(F))
    for _ in range(it):
        s = X @ b; s = s - pd.Series(s).groupby(gid).transform("max").values; e = np.exp(s)
        p = e / pd.Series(e).groupby(gid).transform("sum").values
        gr = X.T @ (y - p) - l2 * b
        Hf = np.zeros((len(F), len(F)))
        for k in np.unique(gid):
            m = gid == k; Xk = X[m]; pk = p[m]; xb = pk @ Xk
            Hf += (Xk * pk[:, None]).T @ Xk - np.outer(xb, xb)
        b += np.linalg.solve(Hf + l2 * np.eye(len(F)), gr)
    return b
def score(d, b):
    X = d[F].values; gid = pd.factorize(d.gameid)[0]; s = X @ b; e = np.exp(s - pd.Series(s).groupby(gid).transform("max").values)
    p = e / pd.Series(e).groupby(gid).transform("sum").values; d = d.assign(p=p)
    top = d.loc[d.groupby("gameid").p.idxmax()]
    return {"games": int(d.gameid.nunique()), "top_pick_right": round(float(top.mvp.mean()), 3),
            "log_loss": round(float(-np.log(d[d.mvp == 1].p).mean()), 4), "uniform_log_loss": round(float(np.log(5)), 4)}, d
W["t"] = W.gameid.map(pd.read_csv(os.path.join(D, "pog_games_matched.csv"), usecols=["gameid", "page"]).drop_duplicates("gameid").set_index("gameid").page)
tr = W[(W.lg == "LPL") & ~W.t.str.contains("Split 3|Grand Finals|Regional")]
te1 = W[(W.lg == "LPL") & W.t.str.contains("Split 3|Grand Finals|Regional")]; te2 = W[W.lg != "LPL"]
b = fit(tr)
res["choice_model"] = {"fit_on": "LPL Split 1, Split 1 playoffs, Split 2, Split 2 playoffs (winning side's five)", "features_standardised": F,
                       "weights": dict(zip(F, np.round(b, 3))),
                       "train": score(tr, b)[0], "LPL later (Split 3, Regional Finals, Grand Finals)": score(te1, b)[0],
                       "LCS + First Stand (never fitted)": score(te2, b)[0]}
kb = np.zeros(len(F)); kb[F.index("kills")] = 5
res["choice_model"]["most_kills_rule_on_LCS_FST"] = score(te2, kb)[0]
# series
S["series_won"] = S.groupby(["series", "teamname"]).result.transform("sum") > S.groupby("series").gameid.transform("nunique") / 2
sm = S[S.mvp == 1].drop_duplicates(["series", "playername"])
res["series"] = {"n": int(S.series.nunique()), "by_league": S.groupby("lg").series.nunique().to_dict(),
                 "mvp_on_series_winner": round(float(sm.series_won.mean()), 3),
                 "role_share": sm.position.value_counts(normalize=True).round(3).to_dict()}
# LPL: series MVP v per-game awards in that series
lp = S[S.lg == "LPL"].copy(); pg = G[G.mvp == 1][["gameid", "playername"]]
cnt = lp.merge(pg.assign(pog=1), on=["gameid", "playername"], how="left").fillna({"pog": 0}).groupby(["series", "playername"]).agg(pog=("pog", "sum"), mvp=("mvp", "max")).reset_index()
cnt = cnt[cnt.series.isin(lp[lp.gameid.isin(pg.gameid)].series)]
top = cnt.sort_values("pog", ascending=False).groupby("series").head(1)
ties = cnt.groupby("series").pog.apply(lambda s: (s == s.max()).sum() > 1)
res["series"]["LPL_series_mvp_v_per_game"] = {"series_with_both": int(cnt.series.nunique()),
    "series_mvp_won_at_least_one_game_award": round(float(cnt[cnt.mvp == 1].pog.gt(0).mean()), 3),
    "series_mvp_is_the_unique_most_game_awards": round(float(top[~top.series.map(ties)].mvp.mean()), 3),
    "series_with_a_tie_for_most": int(ties.sum())}
# per-game model -> series MVP elsewhere (sum of per-game chances, winning side only, over the series' games)
SS = S.dropna(subset=FE).copy()
for r in ["jng", "mid", "bot", "sup"]: SS["r_" + r] = (SS.position == r).astype(float)
SS[FE] = (SS[FE] - mu) / sd
SW = SS[SS.result == 1]; SW = SW[SW.groupby("gameid").position.transform("size") == 5]
_, sc = score(SW, b)
agg = sc.groupby(["lg", "series", "playername"]).agg(p=("p", "sum"), mvp=("mvp", "max")).reset_index()
pick = agg.loc[agg.groupby("series").p.idxmax()]
res["series"]["per_game_model_names_series_mvp"] = {lg: {"series": int(len(d)), "right": round(float(d.mvp.mean()), 3)} for lg, d in pick.groupby("lg")}
res["series"]["per_game_model_names_series_mvp"]["all"] = {"series": int(len(pick)), "right": round(float(pick.mvp.mean()), 3)}
res["series"]["chance_level"] = "about 0.2 per series (five players on the winning side, before any stats)"
json.dump(res, open(OUT, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
sc[sc.lg == "WLDs"][["series", "gameid", "teamname", "playername", "position", "champion", "kills", "deaths", "assists", "p", "mvp"]].to_csv(os.path.join(D, "pog_worlds_series_scored.csv"), index=False)
