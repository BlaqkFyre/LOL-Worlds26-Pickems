"""Walk-forward test of the v1 who-wins model (Luke, 10 Nov: run the fixed 1 Sep test as it is, and a walk-forward test alongside).
v1 = team pre-game rating (already refitted every day on all earlier games, 90-day half-life, as in exptest.py) + league-adjusted
player skills, combined by one logistic fit.
  fixed         as now: the combination fitted on Feb-Aug games, league shift frozen at 1 Sep, applied to every later game
  walk-forward  for each match day: the combination refitted on every earlier game (recent games weighted by a half-life), and that
                day's league shift; predicts that day only. The half-life is chosen on July-August days only, from a few
                candidates; games from 1 Sep are the test, as in the fixed test.
Both are scored on the same games (from 1 Sep; Worlds; Worlds knockouts).
usage: python -I v1_walkforward.py <csv> games.csv gfeat.csv <out json>"""
import json, sys
import numpy as np
import pandas as pd

CSV, GAMES, GFEAT, OUT = sys.argv[1:5]
G = pd.read_csv(GAMES); GF = pd.read_csv(GFEAT)
G["t"] = pd.to_datetime(G.date); G["day"] = G.t.dt.strftime("%Y-%m-%d")
HL, LAM, TEMP, LP = 90.0, 2.0, 1.125, 80.0  # session 1 settings (chosen on Jul-Aug in session 1)
TEAMS = sorted(set(G.blue) | set(G.red)); TI = {t: i for i, t in enumerate(TEAMS)}
home = {}
for r in G.itertuples():
    home[r.blue] = r.blue_home if isinstance(r.blue_home, str) else ""; home[r.red] = r.red_home if isinstance(r.red_home, str) else ""
LEAGUES = sorted({h for h in home.values() if h}); LI = {l: i for i, l in enumerate(LEAGUES)}; NT, NL = len(TEAMS), len(LEAGUES)
X = np.zeros((len(G), NT + NL + 1))
for n, r in enumerate(G.itertuples()):
    X[n, TI[r.blue]] += 1; X[n, TI[r.red]] -= 1
    if home[r.blue]: X[n, NT + LI[home[r.blue]]] += 1
    if home[r.red]: X[n, NT + LI[home[r.red]]] -= 1
    X[n, -1] = 1
Y = G.blue_win.values.astype(float)
def wfit(idx, when):
    w = 0.5 ** (((np.datetime64(when) - G.t.values[idx]) / np.timedelta64(1, "D")) / HL)
    A, y = X[idx], Y[idx]; pen = np.r_[np.full(NT, LAM), np.full(NL, 0.1), 0.0]; b = np.zeros(A.shape[1])
    for _ in range(40):
        p = 1 / (1 + np.exp(-(A @ b))); g = A.T @ (w * (p - y)) + pen * b
        H = (A * (w * p * (1 - p))[:, None]).T @ A + np.diag(pen + 1e-9); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-8: break
    return b
tl = np.full(len(G), np.nan); LDAY = {}; L_sep = None
for d in sorted(G.day.unique()):
    tr = np.where(G.day < d)[0]; te = np.where(G.day == d)[0]
    if len(tr) < 150: continue
    b = wfit(tr, d); tl[te] = (X[te] @ b) / TEMP; LDAY[d] = {l: float(b[NT + i]) for l, i in LI.items()}
    if d >= "2026-09-01" and L_sep is None: L_sep = LDAY[d]
C_R = {"top": 0.138, "jng": 0.141, "mid": 0.119, "bot": 0.205, "sup": 0.082}
MAIN = {"top": ["laning", "teamfight", "cons_side", "cons_dur", "cons_steady"], "jng": ["early", "objectives", "teamfight"],
        "mid": ["laning", "mapimpact", "damage"], "bot": ["lane_own", "lane_duo", "damage", "lategame"], "sup": ["playmaking", "mappresence", "reliability"]}
COLS = [f"{r}_{f}" for r in MAIN for f in MAIN[r]]
side_home = {}
for r in G.itertuples(): side_home[(r.gameid, "Blue")] = home[r.blue]; side_home[(r.gameid, "Red")] = home[r.red]
gi = {g: i for i, g in enumerate(G.gameid)}; gday = dict(zip(G.gameid, G.day))
DF, DW = np.zeros((len(G), len(COLS))), np.zeros((len(G), len(COLS)))  # fixed: 1 Sep league shift; walk-forward: that day's shift
for r in GF.itertuples():
    i = gi[r.gameid]; sg = 1 if r.side == "Blue" else -1; h_ = side_home[(r.gameid, r.side)]
    Lf = (L_sep or {}).get(h_, 0.0); Lw = LDAY.get(gday[r.gameid], {}).get(h_, 0.0)
    for f in MAIN[r.position]:
        v = getattr(r, "e_" + f)
        if pd.notna(v):
            DF[i, COLS.index(f"{r.position}_{f}")] += sg * (v + C_R[r.position] * Lf); DW[i, COLS.index(f"{r.position}_{f}")] += sg * (v + C_R[r.position] * Lw)
ok = ~np.isnan(tl)
def logit_fit(A, y, pen, w=None, iters=40):
    w = np.ones(len(y)) if w is None else w; b = np.zeros(A.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(A @ b))); g = A.T @ (w * (p - y)) + pen * b
        H = (A * (w * p * (1 - p))[:, None]).T @ A + np.diag(pen + 1e-9); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-8: break
    return b
pen = np.r_[0.0, np.full(len(COLS), LP)]
def score(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4), "brier": round(float(np.mean((p - y) ** 2)), 4),
            "fav": round(float(np.mean((p > 0.5) == (y == 1))), 3), "n": int(len(y))}
# fixed (as v1 is now)
AF = np.c_[tl, DF]; TR = np.where(ok & (G.t >= "2026-02-01") & (G.t < "2026-09-01"))[0]
bF = logit_fit(AF[TR], Y[TR], pen); pF = 1 / (1 + np.exp(-(AF @ bF)))
# walk-forward: combination refitted each match day on every earlier game, weighted by half-life h
AW = np.c_[tl, DW]
def walk(h, d0, d1):
    p = np.full(len(G), np.nan)
    for d in sorted(G.day[(G.day >= d0) & (G.day < d1)].unique()):
        tr = np.where(ok & (G.day < d) & (G.t >= "2026-02-01"))[0]; te = np.where(ok & (G.day == d))[0]
        if not len(te): continue
        w = None if h is None else 0.5 ** (((np.datetime64(d) - G.t.values[tr]) / np.timedelta64(1, "D")) / h)
        b = logit_fit(AW[tr], Y[tr], pen, w); p[te] = 1 / (1 + np.exp(-(AW[te] @ b)))
    return p
VA = np.where(ok & (G.t >= "2026-07-01") & (G.t < "2026-09-01"))[0]
res = {"settings": {"team_half_life_days": HL, "player_skill_penalty": LP}, "choose_half_life_on_jul_aug": {}}
best, bestll = None, 9
for h in [None, 60, 120, 240, 480]:
    pv = walk(h, "2026-07-01", "2026-09-01"); s = score(pv[VA], Y[VA]); res["choose_half_life_on_jul_aug"][str(h or "none")] = s
    if s["logloss"] < bestll: best, bestll = h, s["logloss"]
res["chosen_half_life_days"] = best or "none"
pW = walk(best, "2026-09-01", "2027-01-01")
sets = {"from 1 Sep": np.where(ok & (G.t >= "2026-09-01"))[0], "Worlds": np.where(ok & (G.league == "WLDs").values)[0],
        "Worlds knockouts (from 3 Nov)": np.where(ok & (G.league == "WLDs").values & (G.t >= "2026-11-03"))[0]}
res["scores"] = {k: {"fixed": score(pF[ix], Y[ix]), "walk_forward": score(pW[ix], Y[ix])} for k, ix in sets.items()}
res["weights_fixed"] = dict(zip(["team_rating"] + COLS, np.round(bF, 3)))
json.dump(res, open(OUT, "w"), indent=1, default=str); print(json.dumps(res, indent=1, default=str))
