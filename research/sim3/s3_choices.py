"""Sim session 3 follow-up (research only; Luke, 5 Nov): players' choice moments - jungle ganks, support and mid roams.
Data: gol.gg timeline kills (killer, assisters, victim, time) matched to the file, which gives each champion's player and role.
Only results are visible (a gank or roam that got no kill isn't), so these are kill-participation measures, not paths.
Per game and player, before 14:00 (laning):
  jungle  kills+assists by lane of the enemy who died: top / mid / bot (ADC or support) / jungle (counter-jungle); jungle CS at 14
  support roam = kill+assist where the enemy who died is top, mid or jungle and the support's own ADC isn't involved
  mid     roam = kill+assist where the enemy who died is top, bot or support
Tendency = the player's own earlier games (by date), pulled toward the role average (k = 10 games). Tests, beyond v1 and side
(logistic or linear on blue minus red tendencies), fitted before 1 Sep, judged from 1 Sep and on Worlds:
  first dragon, Herald, grubs (taker), bot / top / mid gold lead at 15.
Also the same-game links (what a gank / roam goes with), to size effects for a sim.
usage: python -I s3_choices.py <OE csv> tl_match.csv tl_events.csv tl_gold.csv v1_games.csv <out_json> <out_players_csv>"""
import sys, json
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, TM, TE, TGo, V1, OUTJ, OUTP = sys.argv[1:8]
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
ROLES = ["top", "jng", "mid", "bot", "sup"]; LANE = {"top": "top", "mid": "mid", "bot": "bot", "sup": "bot", "jng": "jng"}
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
oe = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "date", "side", "position", "champion", "playername", "playerid", "golddiffat15"])
oe = oe[oe.gameid.isin(M.gameid) & oe.position.isin(ROLES)].copy(); oe["k"] = oe.champion.map(key); oe["sd"] = oe.side.str.lower()
role = {(r.gameid, r.sd, r.k): r.position for r in oe.itertuples()}
pl = {(r.gameid, r.sd, r.position): (r.playername, r.playerid) for r in oe.itertuples()}
g2o = dict(zip(M.gid, M.gameid))
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)]
K = ev[(ev.type == "kill") & (ev.t < 840)].copy()
rows, miss = [], 0
for r in K.itertuples():
    g = g2o[r.gid]; s = r.side; o = "red" if s == "blue" else "blue"
    kr = role.get((g, s, key(r.champ))); vr = role.get((g, o, key(r.victim_champ)))
    ar = [role.get((g, s, key(a))) for a in str(r.assists).split("|") if a and a != "nan"]
    if kr is None or vr is None or None in ar: miss += 1; continue
    rows.append((r.gid, g, s, r.t, kr, set([kr] + ar), vr))
KR = pd.DataFrame(rows, columns=["gid", "gameid", "side", "t", "killer", "part", "victim"])
res = {"early_kills": len(K), "tagged": len(KR), "untagged": miss}
# per game and side: choice counts
gs = defaultdict(lambda: defaultdict(float))
for r in KR.itertuples():
    d = gs[(r.gameid, r.side)]; lane = LANE[r.victim]
    if "jng" in r.part: d[f"jng_{lane}"] += 1
    if "sup" in r.part and r.victim in ("top", "mid", "jng") and "bot" not in r.part: d["sup_roam"] += 1
    if "sup" in r.part: d["sup_all"] += 1
    if "mid" in r.part and r.victim in ("top", "bot", "sup"): d["mid_roam"] += 1
    if "mid" in r.part: d["mid_all"] += 1
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "cs") & (go.role == "jng") & (go.minute == 14)]
jcs = {(g2o[r.gid], r.side): r.value for r in go.itertuples()}
G = []
for g, gi in M.set_index("gameid").iterrows():
    for s in ("blue", "red"):
        d = gs[(g, s)]
        G.append(dict(gameid=g, side=s, date=gi.date, jng_top=d["jng_top"], jng_mid=d["jng_mid"], jng_bot=d["jng_bot"], jng_jng=d["jng_jng"],
                      sup_roam=d["sup_roam"], sup_all=d["sup_all"], mid_roam=d["mid_roam"], mid_all=d["mid_all"], jng_cs14=jcs.get((g, s), np.nan),
                      jng_player=pl.get((g, s, "jng"), ("", ""))[0], sup_player=pl.get((g, s, "sup"), ("", ""))[0], mid_player=pl.get((g, s, "mid"), ("", ""))[0]))
G = pd.DataFrame(G).sort_values("date")
G["jng_all"] = G[["jng_top", "jng_mid", "jng_bot", "jng_jng"]].sum(axis=1)
MEAS = {"jng": ["jng_top", "jng_mid", "jng_bot", "jng_jng", "jng_all", "jng_cs14"], "sup": ["sup_roam", "sup_all"], "mid": ["mid_roam", "mid_all"]}
res["role_averages_per_game"] = {c: round(float(G[c].mean()), 3) for cs_ in MEAS.values() for c in cs_}
# pre-game tendency: the player's earlier games (strictly earlier dates), pulled toward the overall average of earlier games (k = 10)
KS = 10
for rl, cols in MEAS.items():
    pc = f"{rl}_player"; hist = defaultdict(list)
    tend = {c: [] for c in cols}; ngm = []
    for day, dd in G.groupby(G.date.str[:10], sort=True):
        prior = G[G.date.str[:10] < day]
        mu = {c: prior[c].mean() if len(prior) else G[c].mean() for c in cols}
        for i in dd.index:
            h = hist[G.at[i, pc]]; ngm.append(len(h))
            for c in cols:
                vals = [x[c] for x in h if x[c] == x[c]]
                tend[c].append((sum(vals) + KS * mu[c]) / (len(vals) + KS))
        for i in dd.index: hist[G.at[i, pc]].append({c: G.at[i, c] for c in cols})
    order = [i for _, dd in G.groupby(G.date.str[:10], sort=True) for i in dd.index]
    for c in cols: G.loc[order, f"t_{c}"] = tend[c]
    G.loc[order, f"n_{rl}"] = ngm
# outcomes per game
oe_t = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "side", "position", "firstdragon", "firstherald", "void_grubs", "opp_void_grubs"])
oe_t = oe_t[(oe_t.position == "team") & oe_t.gameid.isin(M.gameid)]; b = oe_t[oe_t.side == "Blue"].set_index("gameid")
gdl = oe[oe.side == "Blue"].pivot_table(index="gameid", columns="position", values="golddiffat15")
v1 = pd.read_csv(V1).set_index("gameid")
W = G.pivot_table(index="gameid", columns="side", values=[c for c in G.columns if c.startswith("t_")], aggfunc="first")
W.columns = [f"{a}_{s}" for a, s in W.columns]
W["z"] = v1.z_v1.reindex(W.index); W["date"] = G.drop_duplicates("gameid").set_index("gameid").date.reindex(W.index)
W["fd"] = b.firstdragon.reindex(W.index); W["fh"] = b.firstherald.reindex(W.index); W["grubs"] = (b.void_grubs > b.opp_void_grubs).astype(float).reindex(W.index)
for r_ in ["top", "mid", "bot", "sup", "jng"]: W[f"gd15_{r_}"] = gdl[r_].reindex(W.index)
W["gd15_botlane"] = W.gd15_bot + W.gd15_sup
W["split"] = np.where(W.index.isin(M[M.tournament.str.startswith("Worlds")].gameid), "Worlds", np.where(W.date < "2026-09-01", "train", "from 1 Sep"))
W = W.dropna(subset=["z"])
def lfit(X, y, l2=1.0):
    bb = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ bb)); bb += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(bb)), X.T @ (y - p) - l2 * bb)
    return bb
ll = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
tests = {"first dragon": ("fd", ["jng_bot", "sup_all"], "logit"), "first Herald": ("fh", ["jng_top", "jng_mid"], "logit"), "more grubs": ("grubs", ["jng_top", "jng_mid"], "logit"),
         "bot lane gold at 15": ("gd15_botlane", ["jng_bot", "sup_roam"], "lin"), "top gold at 15": ("gd15_top", ["jng_top"], "lin"),
         "mid gold at 15": ("gd15_mid", ["jng_mid", "mid_roam", "sup_roam"], "lin")}
res["tests"] = {}
for nm, (yc, feats, kind) in tests.items():
    d = W.dropna(subset=[yc]); tr = d.split == "train"
    diff = np.c_[[d[f"t_{f}_blue"] - d[f"t_{f}_red"] for f in feats]].T
    sdv = diff[tr.values].std(axis=0); sdv[sdv == 0] = 1; diff = diff / sdv
    X0 = np.c_[np.ones(len(d)), d.z]; X1 = np.c_[X0, diff]; y = d[yc].values
    o = {"features (blue minus red tendency, per sd)": feats}
    if kind == "logit":
        b0 = lfit(X0[tr], y[tr]); b1 = lfit(X1[tr], y[tr]); o["weights"] = np.round(b1[2:], 4).tolist()
        for s_ in ["train", "from 1 Sep", "Worlds"]:
            q = (d.split == s_).values
            if q.sum(): o[s_] = {"games": int(q.sum()), "base": round(ll(1 / (1 + np.exp(-X0[q] @ b0)), y[q]), 4), "with_tendency": round(ll(1 / (1 + np.exp(-X1[q] @ b1)), y[q]), 4)}
    else:
        b0, *_ = np.linalg.lstsq(X0[tr], y[tr], rcond=None); b1, *_ = np.linalg.lstsq(X1[tr], y[tr], rcond=None); o["gold_per_sd"] = np.round(b1[2:], 1).tolist()
        for s_ in ["train", "from 1 Sep", "Worlds"]:
            q = (d.split == s_).values
            if q.sum(): o[s_] = {"games": int(q.sum()), "base_rmse": round(float(np.sqrt(np.mean((y[q] - X0[q] @ b0) ** 2)))), "with_tendency_rmse": round(float(np.sqrt(np.mean((y[q] - X1[q] @ b1) ** 2))))}
    res["tests"][nm] = o
# how stable are tendencies? first half v second half of each player's games (players with 16+ games)
stab = {}
for rl, cols in MEAS.items():
    pc = f"{rl}_player"; P_ = G.groupby(pc).filter(lambda d: len(d) >= 16)
    halves = P_.groupby(pc).apply(lambda d: pd.Series({c + "_a": d[c].iloc[:len(d) // 2].mean() for c in cols} | {c + "_b": d[c].iloc[len(d) // 2:].mean() for c in cols}))
    stab[rl] = {"players": len(halves), **{c: round(float(halves[c + "_a"].corr(halves[c + "_b"])), 3) for c in cols}}
res["stability_first_v_second_half"] = stab
# same-game links (association, not cause): early jungle bot involvement v first dragon; support roams v bot gold at 15
d = W.join(G[G.side == "blue"].set_index("gameid")[["jng_bot", "sup_roam"]]).join(G[G.side == "red"].set_index("gameid")[["jng_bot", "sup_roam"]], rsuffix="_r")
d = d.dropna(subset=["fd"])
res["same_game"] = {"first dragon to blue when blue jungler had more early bot kills involvement": round(float(d[d.jng_bot > d.jng_bot_r].fd.mean()), 3),
                    "... fewer": round(float(d[d.jng_bot < d.jng_bot_r].fd.mean()), 3), "... equal": round(float(d[d.jng_bot == d.jng_bot_r].fd.mean()), 3),
                    "blue bot lane gold at 15 when blue support roamed more": round(float(d[d.sup_roam > d.sup_roam_r].gd15_botlane.mean())),
                    "... less": round(float(d[d.sup_roam < d.sup_roam_r].gd15_botlane.mean()))}
# player table (players with 10+ timeline games)
out = []
for rl, cols in MEAS.items():
    pc = f"{rl}_player"
    for p_, dd in G.groupby(pc):
        if len(dd) >= 10 and p_: out.append({"role": rl, "player": p_, "games": len(dd), **{c: round(float(dd[c].mean()), 2) for c in cols}})
pd.DataFrame(out).to_csv(OUTP, index=False)
json.dump(res, open(OUTJ, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
