"""Sim session 2, step 4 (read-only): lane matchups and the bot duo.
Lane result = gold lead at 15 v the lane opponent (blue minus red). Expected part from the players' pre-game laning skill
(top/mid laning, jungle early game, ADC own lane; fitted before 1 Sep); the rest is what a matchup could explain.
Matchup inputs (game's own patch; lolalytics pulled for 16.15, 16.16, 16.17, 16.20 = every pro patch from 16.15):
  solo_<role> = lolalytics d1 (percentage points), averaged over both directions: (d1(A v B) - d1(B v A)) / 2
  solo_duo    = bot duo: mean of ADC v ADC, ADC v enemy support, support v enemy ADC, support v support (each both ways)
  (pro champion-pair lane records are the next step, once this solo-queue starting point is measured)
Tests: (L) does each input explain the lane result beyond skills (correlation, slope in gold per point)?
       (W) does it add to v1's win odds? Train: games before 1 Sep on patch 16.15+; test from 1 Sep and Worlds.
usage: python -I s2_lanes.py <OE csv> v1_games.csv gfeat.csv lola_counters.csv <out_dir>"""
import json, os, sys
import numpy as np
import pandas as pd

CSV, V1, GF, LC, OUT = sys.argv[1:6]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
VS = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own", "sup": "e_lane_duo"}
def np_(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
df = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                 usecols=["gameid", "league", "date", "patch", "side", "position", "champion", "golddiffat15", "result"])
df = df[df.league.isin(MAJOR) & (df.position != "team") & ~((df.league == "WLDs") & (df.date < "2026-10-01"))].copy()
df["patch"] = df.patch.map(np_); df["day"] = df.date.str[:10]
gf = pd.read_csv(GF); gf["skill"] = [r[SKILL[r.position]] if r.position in SKILL and r.position != "sup" else np.nan for _, r in gf.iterrows()]
df = df.merge(gf[["gameid", "side", "position", "skill"]], on=["gameid", "side", "position"], how="left")
B = df[df.side == "Blue"].set_index(["gameid", "position"]); Rd = df[df.side == "Red"].set_index(["gameid", "position"])
G = B[["day", "patch", "league", "champion", "golddiffat15", "skill"]].join(Rd[["champion", "skill"]], rsuffix="_r").reset_index()
G = G.rename(columns={"champion": "cb", "champion_r": "cr", "golddiffat15": "gd"}); G["sd"] = G.skill - G.skill_r
# lolalytics d1 lookup
L = pd.read_csv(LC, dtype={"patch": str}); L["patch"] = L.patch.map(np_)
D1 = {(r.patch, r.position, r.vslane, key(r.champion), key(r.vs_champion)): r.d1 for r in L.itertuples()}
POS_OF = {"top": "top", "jungle": "jng", "middle": "mid", "bottom": "bot", "support": "sup"}
def solo(patch, pa, a, pb, b):
    x = D1.get((patch, pa, VS[pb], key(a), key(b))); y = D1.get((patch, pb, VS[pa], key(b), key(a)))
    v = [s for s in (x, None if y is None else -y) if s is not None]
    return np.mean(v) if v else np.nan
G["solo"] = [solo(r.patch, r.position, r.cb, r.position, r.cr) if r.position != "sup" else np.nan for r in G.itertuples()]
# bot duo: per game, from the bot and support rows
W = G.pivot_table(index="gameid", columns="position", values=["cb", "cr"], aggfunc="first")
pat = G.groupby("gameid").patch.first()
def duo(g):
    try: ab, sb, ar, sr = W.loc[g, ("cb", "bot")], W.loc[g, ("cb", "sup")], W.loc[g, ("cr", "bot")], W.loc[g, ("cr", "sup")]
    except KeyError: return np.nan
    p = pat[g]; v = [solo(p, "bot", ab, "bot", ar), solo(p, "bot", ab, "sup", sr), solo(p, "sup", sb, "bot", ar), solo(p, "sup", sb, "sup", sr)]
    v = [x for x in v if not np.isnan(x)]; return np.mean(v) if v else np.nan
duo_s = {g: duo(g) for g in W.index}
gd_duo = G[G.position.isin(["bot", "sup"])].groupby("gameid").gd.sum(min_count=2)
R = {"coverage": {}, "lane_test": {}, "win_test": {}}
# (L) lane result beyond skills
for pos in ["top", "jng", "mid", "bot"]:
    S = G[(G.position == pos)].dropna(subset=["gd", "sd"]).copy()
    trn = S[S.day < "2026-09-01"]; b = np.polyfit(trn.sd, trn.gd, 1); S["res"] = S.gd - np.polyval(b, S.sd)
    T = S.dropna(subset=["solo"]); R["coverage"][pos] = {"games": len(S), "with_solo": len(T)}
    for name, part in (("all 16.15+", T), ("from 1 Sep", T[T.day >= "2026-09-01"]), ("Worlds", T[T.league == "WLDs"])):
        if len(part) < 20: continue
        c = float(np.corrcoef(part.solo, part.res)[0, 1]); sl = float(np.polyfit(part.solo, part.res, 1)[0])
        R["lane_test"][f"{pos} | {name}"] = {"n": len(part), "corr": round(c, 3), "gold_per_point": round(sl, 1),
                                            "skill_gold_per_sd": round(float(b[0]), 1)}
dd = pd.DataFrame({"gd": gd_duo, "s": pd.Series(duo_s)}).dropna()
dd = dd.join(G[G.position == "bot"].set_index("gameid")[["day", "league"]])
for name, part in (("all 16.15+", dd), ("from 1 Sep", dd[dd.day >= "2026-09-01"]), ("Worlds", dd[dd.league == "WLDs"])):
    if len(part) >= 20:
        R["lane_test"][f"bot duo | {name}"] = {"n": len(part), "corr": round(float(np.corrcoef(part.s, part.gd)[0, 1]), 3),
                                              "gold_per_point": round(float(np.polyfit(part.s, part.gd, 1)[0]), 1)}
# (W) win odds
V = pd.read_csv(V1).dropna(subset=["z_v1"]).set_index("gameid"); V["day"] = V.date.str[:10]
F = G[G.position.isin(["top", "jng", "mid"])].pivot_table(index="gameid", columns="position", values="solo")
F["duo"] = pd.Series(duo_s); F = F.fillna(0.0)
F["lanes_sum"] = F[["top", "jng", "mid", "duo"]].sum(axis=1)
M = V.join(F, how="inner"); M["pn"] = M.patch.map(np_); M = M[M.pn >= "16.15"]
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)
tr, te, wo = M[M.day < "2026-09-01"], M[M.day >= "2026-09-01"], M[M.league == "WLDs"]
R["win_test"]["games"] = {"train_16.15_to_Aug": len(tr), "from_sep": len(te), "worlds": len(wo)}
z0 = lambda d: np.zeros((len(d), 1))
R["win_test"]["v1"] = {"train": ll(tr.z_v1.values, z0(tr), tr.blue_win.values, np.zeros(1)), "from_sep": ll(te.z_v1.values, z0(te), te.blue_win.values, np.zeros(1)),
                       "worlds": ll(wo.z_v1.values, z0(wo), wo.blue_win.values, np.zeros(1))}
for name, cols in {"lanes (one weight)": ["lanes_sum"], "four lanes": ["top", "jng", "mid", "duo"], "bot duo only": ["duo"], "mid only": ["mid"]}.items():
    sd = tr[cols].std().replace(0, 1); X = lambda d: (d[cols] / sd).values
    b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
    R["win_test"][name] = {"weights_per_sd": dict(zip(cols, np.round(b, 3).tolist())), "points_per_sd": dict(zip(cols, sd.round(2).tolist())),
                           "train": ll(tr.z_v1.values, X(tr), tr.blue_win.values, b), "from_sep": ll(te.z_v1.values, X(te), te.blue_win.values, b),
                           "worlds": ll(wo.z_v1.values, X(wo), wo.blue_win.values, b)}
json.dump(R, open(os.path.join(OUT, "lanefit_results.json"), "w"), indent=1)
print(json.dumps(R, indent=1))
