"""Sim session 2, part 2 (read-only): comp profile (team style) learned from what teams did with each champion.
Team stats per game and side, as shares of the two teams' total (0.5 = even):
  siege      turret plates share, towers share, first tower (0/1)
  objectives dragons share, void grubs share, Heralds share, Barons share
  skirmish   kills by 15 share (sum of player kills at 15), kills per minute of both teams (pace, not a share)
Each champion-role's style = mean of (its team's share - 0.5) over its games, pulled toward 0 (k = 20); a draft's style = sum over its 5.
Checks (styles from games before 1 Sep, applied to games from 1 Sep, so out of sample):
  (1) do champion styles hold? before v after 1 Sep, champion-roles with 10+ games in both: correlation
  (2) does a draft's style predict the game's style beyond team strength? correlation of (blue draft style - red) with the blue share,
      and the same with v1's blue chance added (partial)
  (3) who-wins: each style difference alone on v1 (Jul-Aug check; from 1 Sep; Worlds)
usage: python -I s2_comp.py <OE csv> v1_games.csv <out_dir>"""
import os, sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]
c = ["gameid", "league", "date", "side", "position", "champion", "result", "gamelength", "kills", "killsat15", "firsttower", "turretplates",
     "opp_turretplates", "towers", "opp_towers", "dragons", "opp_dragons", "void_grubs", "opp_void_grubs", "heralds", "opp_heralds", "barons", "opp_barons"]
raw = pd.read_csv(CSV, low_memory=False, usecols=c)
raw = raw[raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
tm = raw[raw.position == "team"].copy(); pl = raw[raw.position.isin(ROLES)].copy()
k15 = pl.groupby(["gameid", "side"]).killsat15.sum(min_count=5).rename("k15").reset_index()
tm = tm.merge(k15, on=["gameid", "side"], how="left")
opp = tm[["gameid", "side", "k15", "kills"]].copy(); opp["side"] = np.where(opp.side == "Blue", "Red", "Blue")
tm = tm.merge(opp.rename(columns={"k15": "k15_opp", "kills": "kills_opp"}), on=["gameid", "side"], how="left")
share = lambda a, b: np.where((a + b) > 0, a / (a + b), 0.5)
tm["plates"] = share(tm.turretplates, tm.opp_turretplates); tm["towers_s"] = share(tm.towers, tm.opp_towers); tm["ftower"] = tm.firsttower
tm["drag"] = share(tm.dragons, tm.opp_dragons); tm["grubs"] = share(tm.void_grubs, tm.opp_void_grubs)
tm["herald"] = share(tm.heralds, tm.opp_heralds); tm["baron"] = share(tm.barons, tm.opp_barons)
tm["k15s"] = share(tm.k15, tm.k15_opp); tm["pace"] = (tm.kills + tm.kills_opp) / (tm.gamelength / 60)
STATS = ["plates", "towers_s", "ftower", "drag", "grubs", "herald", "baron", "k15s", "pace"]
GROUP = {"siege": ["plates", "towers_s", "ftower"], "objectives": ["drag", "grubs", "herald", "baron"], "skirmish": ["k15s"], "pace": ["pace"]}
# take team strength out: each stat minus what v1's odds for that side predict (straight-line fit on games before 1 Sep);
# pace (both teams) is fitted on how lopsided the game was expected to be
pvb = pd.read_csv(V1).set_index("gameid").p_v1
tm["p_side"] = tm.gameid.map(pvb); tm.loc[tm.side == "Red", "p_side"] = 1 - tm.loc[tm.side == "Red", "p_side"]
tm = tm.dropna(subset=["p_side"])
for s in STATS:
    x = (tm.p_side - 0.5).abs() if s == "pace" else tm.p_side
    m = (tm.day < "2026-09-01") & tm[s].notna()
    b = np.polyfit(x[m], tm.loc[m, s], 1); tm[s] = tm[s] - np.polyval(b, x)
pl = pl.merge(tm[["gameid", "side"] + STATS], on=["gameid", "side"], how="inner")
def centre(df):
    return df.copy()   # stats are already team-strength residuals
def styles(df, k=20):
    d = centre(df); g = d.groupby(["champion", "position"]); out = pd.DataFrame({"games": g.size()})
    for s in STATS:
        a = g[s].agg(["sum", "count"]); out[s] = a["sum"] / (a["count"] + k)
    for grp, ss in GROUP.items():
        out[grp] = out[ss].mean(axis=1)
    return out
styles(pl).round(4).to_csv(os.path.join(OUT, "champion_styles.csv"))
# (1) stability
A, B = styles(pl[pl.day < "2026-09-01"], 0), styles(pl[pl.day >= "2026-09-01"], 0)
J = A.join(B, lsuffix="_a", rsuffix="_b", how="inner"); J = J[(J.games_a >= 10) & (J.games_b >= 10)]
print(f"(1) champion styles before v from 1 Sep ({len(J)} champion-roles, 10+ games in both):",
      {grp: round(float(np.corrcoef(J[grp + "_a"], J[grp + "_b"])[0, 1]), 3) for grp in GROUP})
# (2) draft style v game style, from 1 Sep, styles from before 1 Sep
S0 = styles(pl[pl.day < "2026-09-01"])
te_pl = pl[pl.day >= "2026-09-01"].drop(columns=STATS).join(S0[list(GROUP)], on=["champion", "position"]).fillna({g: 0 for g in GROUP})
draft = te_pl.groupby(["gameid", "side"])[list(GROUP)].sum().reset_index()
bl = draft[draft.side == "Blue"].set_index("gameid"); rd = draft[draft.side == "Red"].set_index("gameid")
diff = bl[list(GROUP)] - rd[list(GROUP)]
tb = centre(tm[(tm.side == "Blue") & (tm.day >= "2026-09-01")]).set_index("gameid")
tb["siege"] = tb[GROUP["siege"]].mean(axis=1); tb["objectives"] = tb[GROUP["objectives"]].mean(axis=1); tb["skirmish"] = tb.k15s
V = pd.read_csv(V1).set_index("gameid")
X = diff.join(tb[["siege", "objectives", "skirmish", "pace"]], rsuffix="_game").join(V[["z_v1"]]).dropna()
print(f"\n(2) games from 1 Sep: {len(X)}; draft style difference v the game's style (blue side):")
for grp in ["siege", "objectives", "skirmish"]:
    y = X[grp + "_game"]; r = np.corrcoef(X[grp], y)[0, 1]
    A2 = np.c_[np.ones(len(X)), X.z_v1]; ry = y - A2 @ np.linalg.lstsq(A2, y, rcond=None)[0]; rx = X[grp] - A2 @ np.linalg.lstsq(A2, X[grp], rcond=None)[0]
    print(f"   {grp}: correlation {r:.3f}; after taking out v1's team-strength odds {np.corrcoef(rx, ry)[0, 1]:.3f}")
dp = draft.groupby("gameid").pace.sum(); Xp = pd.DataFrame({"draft_pace": dp, "game_pace": tb.pace}).dropna()
print(f"   pace (kills per minute, both teams): correlation of both drafts' pace with the game's {np.corrcoef(Xp.draft_pace, Xp.game_pace)[0, 1]:.3f}")
# (3) who-wins, styles from earlier days only
acc = defaultdict(lambda: np.zeros(len(STATS) + 1)); feats = {}
cpl = centre(pl)
for d, rows in cpl.sort_values("day").groupby("day", sort=True):
    for g, gr in rows.groupby("gameid"):
        f = defaultdict(float)
        for r in gr.itertuples(index=False):
            a = acc[(r.champion, r.position)]; sg = 1 if r.side == "Blue" else -1
            vals = {s: a[i + 1] / (a[0] + 20) for i, s in enumerate(STATS)}
            for grp, ss in GROUP.items(): f[grp] += sg * float(np.mean([vals[s] for s in ss]))
        feats[g] = f
    for r in rows.itertuples(index=False):
        a = acc[(r.champion, r.position)]; a[0] += 1
        for i, s in enumerate(STATS):
            v = getattr(r, s); a[i + 1] += 0 if pd.isna(v) else v
F = pd.DataFrame.from_dict(feats, orient="index").fillna(0.0)
Vv = V.dropna(subset=["z_v1"]).drop(columns=["patch"], errors="ignore"); Vv["day"] = Vv.date.str[:10]; D = Vv.join(F, how="inner")
def fit(Z, Xm, y, lam=1.0):
    b = np.zeros(Xm.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + Xm @ b))); gr_ = Xm.T @ (p - y) + lam * b
        H = (Xm * (p * (1 - p))[:, None]).T @ Xm + lam * np.eye(Xm.shape[1]); s = np.linalg.solve(H, gr_); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, Xm, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + Xm @ b))), 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
sp = lambda a, z: D[(D.day >= a) & (D.day < z)]
trv, va, tr, te, wo = sp("2026-02-01", "2026-07-01"), sp("2026-07-01", "2026-09-01"), sp("2026-02-01", "2026-09-01"), sp("2026-09-01", "2027-01-01"), D[D.league == "WLDs"]
print("\n(3) each style difference alone on v1 (change in log loss; negative = better):")
for grp in GROUP:
    sd = tr[grp].std(); Xf = lambda d: (d[[grp]] / sd).values
    bv = fit(trv.z_v1.values, Xf(trv), trv.blue_win.values); b = fit(tr.z_v1.values, Xf(tr), tr.blue_win.values)
    res = {n: round(ll(d.z_v1.values, Xf(d), d.blue_win.values, bb) - ll(d.z_v1.values, np.zeros((len(d), 1)), d.blue_win.values, np.zeros(1)), 4)
           for n, d, bb in (("jul_aug", va, bv), ("from_sep", te, b), ("worlds", wo, b))}
    print(f"   {grp}: {res}, weight per sd {b[0]:.3f}")
