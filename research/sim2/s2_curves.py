"""Sim session 2, part 2 (read-only): champion power curves.
Per champion-role, from pro major-league games:
  lane gold curve  gold lead v the lane opponent at 10/15/20/25 minutes, minus what the two players' laning skills predict
                   (slope per role and minute fitted before 1 Sep), averaged and pulled toward 0 (k = 20 games)
  scaling          the curve's 25-minute value minus its 10-minute value (positive = gets stronger later)
  length result    win left after v1 (result - v1 chance) in short (< 28 min), medium (28-34) and long (> 34) games, pulled toward 0 (k = 30)
Checks:
  (1) do curves hold? curves from games before 1 Sep v curves from games from 1 Sep, same champion-roles (10+ games in both): correlation
  (2) who-wins: team scaling (sum of its champions' scaling, earlier days only) blue minus red, alone on v1; and in long v short games
  (3) the file's raw gold lead at 15 per champion in LCK Rounds 3-4 (regular season) v gol.gg's GD@15 for the same games
usage: python -I s2_curves.py <OE csv> v1_games.csv gfeat.csv gol_lck_r34.csv <out_dir>"""
import os, sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, GF, GOL, OUT = sys.argv[1:6]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]; MINS = [10, 15, 20, 25]
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own", "sup": "e_playmaking"}
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
cols = ["gameid", "league", "split", "playoffs", "date", "side", "position", "champion", "result", "gamelength"] + [f"golddiffat{m}" for m in MINS]
raw = pd.read_csv(CSV, low_memory=False, usecols=cols)
raw = raw[raw.league.isin(MAJOR) & (raw.position.isin(ROLES)) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]; raw["mins"] = raw.gamelength / 60
pv = pd.read_csv(V1).set_index("gameid").p_v1.to_dict()
raw["p_side"] = raw.gameid.map(pv); red = raw.side == "Red"; raw.loc[red, "p_side"] = 1 - raw.loc[red, "p_side"]; raw["res"] = raw.result - raw.p_side
gf = pd.read_csv(GF)
gf["skill"] = [r[SKILL[r.position]] for _, r in gf.iterrows()]
raw = raw.merge(gf[["gameid", "side", "position", "skill"]], on=["gameid", "side", "position"], how="left")
opp = raw[["gameid", "side", "position", "skill"]].copy(); opp["side"] = np.where(opp.side == "Blue", "Red", "Blue")
raw = raw.merge(opp.rename(columns={"skill": "skill_opp"}), on=["gameid", "side", "position"], how="left")
raw["sd"] = raw.skill - raw.skill_opp
for m in MINS:
    raw[f"res{m}"] = np.nan
    for r in ROLES:
        d = raw[(raw.position == r) & (raw.day < "2026-09-01")].dropna(subset=[f"golddiffat{m}", "sd"])
        b = np.polyfit(d.sd, d[f"golddiffat{m}"], 1); msk = raw.position == r
        raw.loc[msk, f"res{m}"] = raw.loc[msk, f"golddiffat{m}"] - np.polyval(b, raw.loc[msk, "sd"].fillna(0))
raw["band"] = pd.cut(raw.mins, [0, 28, 34, 999], labels=["short", "medium", "long"])
def curves(d, k=20, kl=30):
    g = d.groupby(["champion", "position"])
    out = pd.DataFrame({"games": g.size()})
    for m in MINS:
        s = g[f"res{m}"].agg(["sum", "count"]); out[f"gd{m}"] = s["sum"] / (s["count"] + k)
    out["scaling"] = out.gd25 - out.gd10
    for b in ["short", "medium", "long"]:
        s = d[d.band == b].groupby(["champion", "position"]).res.agg(["sum", "count"])
        out[f"win_{b}"] = (s["sum"] / (s["count"] + kl)).reindex(out.index).fillna(0)
    return out
allc = curves(raw); allc.round(4).to_csv(os.path.join(OUT, "champion_curves.csv"))
meta = curves(raw[raw.date >= "2026-07-01"]); meta.round(4).to_csv(os.path.join(OUT, "champion_curves_recent.csv"))
print("games per band:", raw.drop_duplicates("gameid").band.value_counts().to_dict())
print("role averages of raw gold lead residual sd at 10/15/20/25:", {m: round(float(raw[f'res{m}'].std()), 0) for m in MINS})
# (1) stability
A, B = curves(raw[raw.day < "2026-09-01"], k=0, kl=0), curves(raw[raw.day >= "2026-09-01"], k=0, kl=0)
J = A.join(B, lsuffix="_a", rsuffix="_b", how="inner"); J = J[(J.games_a >= 10) & (J.games_b >= 10)]
print(f"\n(1) curves before v from 1 Sep, {len(J)} champion-roles with 10+ games in both:")
for c in [f"gd{m}" for m in MINS] + ["scaling", "win_short", "win_long"]:
    print(f"   {c}: correlation {np.corrcoef(J[c + '_a'], J[c + '_b'])[0, 1]:.3f}")
for r in ROLES:
    Jr = J.xs(r, level="position") if r in J.index.get_level_values("position") else None
    if Jr is not None and len(Jr) >= 5:
        print(f"   {r}: n {len(Jr)}, gd15 {np.corrcoef(Jr.gd15_a, Jr.gd15_b)[0, 1]:.2f}, scaling {np.corrcoef(Jr.scaling_a, Jr.scaling_b)[0, 1]:.2f}")
# (2) who-wins: team scaling from earlier days
acc = defaultdict(lambda: np.zeros(4)); feats = {}
for d, rows in raw.sort_values("day").groupby("day", sort=True):
    for g, gr in rows.groupby("gameid"):
        f = 0.0
        for r in gr.itertuples(index=False):
            a = acc[(r.champion, r.position)]; sc = (a[1] / (a[0] + 20)) - (a[2] / (a[0] + 20)) if a[0] else 0.0
            f += (1 if r.side == "Blue" else -1) * sc
        feats[g] = (f, gr.mins.iloc[0])
    for r in rows.dropna(subset=["res10", "res25"]).itertuples(index=False):
        a = acc[(r.champion, r.position)]; a[0] += 1; a[1] += r.res25; a[2] += r.res10
F = pd.DataFrame.from_dict(feats, orient="index", columns=["scaling", "mins"])
V = pd.read_csv(V1).dropna(subset=["z_v1"]).set_index("gameid"); V["day"] = V.date.str[:10]
D = V.join(F, how="inner")
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); gr_ = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, gr_); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
sp = lambda a, z: D[(D.day >= a) & (D.day < z)]
trv, va, tr, te, wo = sp("2026-02-01", "2026-07-01"), sp("2026-07-01", "2026-09-01"), sp("2026-02-01", "2026-09-01"), sp("2026-09-01", "2027-01-01"), D[D.league == "WLDs"]
sd = tr.scaling.std(); X = lambda d: (d[["scaling"]] / sd).values; z0 = np.zeros(1)
bv = fit(trv.z_v1.values, X(trv), trv.blue_win.values); b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
print("\n(2) team scaling alone on v1 (change in log loss):",
      {n: round(ll(d.z_v1.values, X(d), d.blue_win.values, bb) - ll(d.z_v1.values, np.zeros((len(d), 1)), d.blue_win.values, z0), 4)
       for n, d, bb in (("jul_aug", va, bv), ("from_sep", te, b), ("worlds", wo, b))}, "weight per sd", round(float(b[0]), 3))
# does the more-scaling side win more of the long games (after v1)? (game length is not known before the game: description only)
D["res_blue"] = D.blue_win - 1 / (1 + np.exp(-D.z_v1))
for lab, sub in (("short < 28", D[D.mins < 28]), ("medium", D[(D.mins >= 28) & (D.mins <= 34)]), ("long > 34", D[D.mins > 34])):
    print(f"   {lab}: games {len(sub)}, correlation of team scaling with the win left after v1: {np.corrcoef(sub.scaling, sub.res_blue)[0, 1]:.3f}")
# (3) gol.gg GD@15 v the file, LCK Rounds 3-4 regular season
gol = pd.read_csv(GOL); gol["k"] = gol.champ.map(key)
lck = raw[(raw.league == "LCK") & (raw.split == "Rounds 3-4") & (raw.playoffs == 0)]
fl = lck.groupby("champion").agg(n=("gameid", "size"), gd15=("golddiffat15", "mean")).reset_index(); fl["k"] = fl.champion.map(key)
M = gol.merge(fl, on="k"); M = M[M.picks >= 5]
print(f"\n(3) LCK Rounds 3-4, champions with 5+ games: {len(M)}; gol.gg GD@15 v file's mean gold lead at 15: correlation {np.corrcoef(M.gd15_x, M.gd15_y)[0, 1]:.3f}; "
      f"same within 50 gold: {int(((M.gd15_x - M.gd15_y).abs() <= 50).sum())}")
print(M.assign(diff=(M.gd15_x - M.gd15_y).round(0))[["champ", "picks", "n", "gd15_x", "gd15_y", "diff"]].rename(columns={"gd15_x": "gol_gd15", "gd15_y": "file_gd15"}).head(12).round(0).to_string(index=False))
