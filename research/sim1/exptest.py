"""Experience test (Luke, 3 Nov): does pre-2026 career experience predict wins beyond team ratings and player skills?
Experience per game = the five players who actually played (career facts before 2026, so nothing from 2026 leaks in).
Features tried (blue minus red): titles (Worlds + MSI titles summed), log of international games summed, veterans (players with 50+
Worlds/MSI games), Worlds titles only. Base model = team pre-game logit + league-adjusted player skills (the current best).
Choice on Jul-Aug; reported on 1 Sep onwards, Worlds, and big-stage games (internationals + domestic playoffs) from 1 Sep.
Also: the same test on all big-stage games before 1 Sep with a rolling refit (more games, still out of sample).
usage: python -I exptest.py <csv> games.csv gfeat.csv out/player_experience_pre2026.csv"""
import sys
import numpy as np
import pandas as pd

CSV, GAMES, GFEAT, EXP = sys.argv[1:5]
G = pd.read_csv(GAMES); GF = pd.read_csv(GFEAT); EX = pd.read_csv(EXP)
G["t"] = pd.to_datetime(G.date); G["day"] = G.t.dt.strftime("%Y-%m-%d")
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "position", "playoffs"])
po = raw[raw.position == "team"].groupby("gameid").playoffs.max()
G["playoffs"] = G.gameid.map(po).fillna(0).astype(int)
G["big"] = G.league.isin(["FST", "MSI", "EWC", "WLDs"]) | (G.playoffs == 1)
HL, LAM, TEMP, LP = 90.0, 2.0, 1.125, 80.0
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
def logit_fit(A, y, pen, iters=40):
    b = np.zeros(A.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(A @ b))); g = A.T @ (p - y) + pen * b
        H = (A * (p * (1 - p))[:, None]).T @ A + np.diag(pen + 1e-9)
        s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-8: break
    return b
def wfit(idx, when):
    w = 0.5 ** (((np.datetime64(when) - G.t.values[idx]) / np.timedelta64(1, "D")) / HL)
    A, y = X[idx], Y[idx]; pen = np.r_[np.full(NT, LAM), np.full(NL, 0.1), 0.0]; b = np.zeros(A.shape[1])
    for _ in range(40):
        p = 1 / (1 + np.exp(-(A @ b))); g = A.T @ (w * (p - y)) + pen * b
        H = (A * (w * p * (1 - p))[:, None]).T @ A + np.diag(pen + 1e-9); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-8: break
    return b
L_sep = None
tl = np.full(len(G), np.nan)
for d in sorted(G.day.unique()):
    tr = np.where(G.day < d)[0]; te = np.where(G.day == d)[0]
    if len(tr) < 150: continue
    b = wfit(tr, d); tl[te] = (X[te] @ b) / TEMP
    if d >= "2026-09-01" and L_sep is None: L_sep = {l: float(b[NT + i]) for l, i in LI.items()}
# player skill differences, league-adjusted (shift per role from step 3c)
C_R = {"top": 0.138, "jng": 0.141, "mid": 0.119, "bot": 0.205, "sup": 0.082}
MAIN = {"top": ["laning", "teamfight", "cons_side", "cons_dur", "cons_steady"], "jng": ["early", "objectives", "teamfight"],
        "mid": ["laning", "mapimpact", "damage"], "bot": ["lane_own", "lane_duo", "damage", "lategame"], "sup": ["playmaking", "mappresence", "reliability"]}
COLS = [f"{r}_{f}" for r in MAIN for f in MAIN[r]]
side_home = {}
for r in G.itertuples(): side_home[(r.gameid, "Blue")] = home[r.blue]; side_home[(r.gameid, "Red")] = home[r.red]
gi = {g: i for i, g in enumerate(G.gameid)}
D = np.zeros((len(G), len(COLS)))
ex = EX.set_index("playerid")
EXF = ["titles", "log_intl", "veterans", "worlds_titles"]
XE = np.zeros((len(G), len(EXF)))
for r in GF.itertuples():
    i = gi[r.gameid]; sg = 1 if r.side == "Blue" else -1; Lh = L_sep.get(side_home[(r.gameid, r.side)], 0.0)
    for f in MAIN[r.position]:
        v = getattr(r, "e_" + f)
        if pd.notna(v): D[i, COLS.index(f"{r.position}_{f}")] += sg * (v + C_R[r.position] * Lh)
    e = ex.loc[r.playerid] if r.playerid in ex.index else None
    if e is not None:
        XE[i, 0] += sg * (e.worlds_titles + e.msi_titles)
        XE[i, 1] += sg * np.log1p(e.intl_games)
        XE[i, 2] += sg * (e.intl_games >= 50)
        XE[i, 3] += sg * e.worlds_titles
ok = ~np.isnan(tl)
def score(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4), round(float(np.mean((p > 0.5) == (y == 1))), 3), int(len(y))
def run(extra, tr, te):
    A = np.c_[tl, D] if extra is None else np.c_[tl, D, XE[:, EXF.index(extra)]]
    pen = np.r_[0.0, np.full(D.shape[1], LP)] if extra is None else np.r_[0.0, np.full(D.shape[1], LP), 0.0]
    b = logit_fit(A[tr], Y[tr], pen)
    return score(1 / (1 + np.exp(-(A[te] @ b))), Y[te]), (float(b[-1]) if extra else None)
idx = lambda a, z, extra=True: np.where(ok & (G.t >= pd.Timestamp(a)) & (G.t < pd.Timestamp(z)) & extra)[0]
TRV, VA, TR = idx("2026-02-01", "2026-07-01"), idx("2026-07-01", "2026-09-01"), idx("2026-02-01", "2026-09-01")
TE = idx("2026-09-01", "2027-01-01"); WO = np.where(ok & (G.league == "WLDs").values)[0]; BIG = idx("2026-09-01", "2027-01-01", G.big.values)
print(f"games: train {len(TR)}, Jul-Aug {len(VA)}, from 1 Sep {len(TE)} (big-stage {len(BIG)}), Worlds {len(WO)}")
print("feature spread (blue - red), Worlds games:", {f: round(float(np.abs(XE[WO, k]).mean()), 2) for k, f in enumerate(EXF)})
print("\nlog loss / favourite won / games   (lower log loss = better)")
print(f"{'model':<22}{'Jul-Aug':<24}{'from 1 Sep':<24}{'Worlds':<24}{'big stage from 1 Sep':<24}weight")
for extra in [None] + EXF:
    v, _ = run(extra, TRV, VA); t, w = run(extra, TR, TE); wo, _ = run(extra, TR, WO); bg, _ = run(extra, TR, BIG)
    print(f"{('base' if extra is None else '+ ' + extra):<22}{str(v):<24}{str(t):<24}{str(wo):<24}{str(bg):<24}{'' if w is None else round(w, 3)}")
# rolling: every big-stage game, predicted with a model fitted on games before its month
print("\nRolling month by month, big-stage games only (Mar-Oct):")
for extra in [None] + EXF:
    ps, ys = [], []
    for m in pd.date_range("2026-03-01", "2026-10-01", freq="MS"):
        tr = idx("2026-02-01", m); te = idx(m, m + pd.offsets.MonthBegin(1), G.big.values)
        if len(te) == 0: continue
        A = np.c_[tl, D] if extra is None else np.c_[tl, D, XE[:, EXF.index(extra)]]
        pen = np.r_[0.0, np.full(D.shape[1], LP)] + (0 if extra is None else 0) if extra is None else np.r_[0.0, np.full(D.shape[1], LP), 0.0]
        b = logit_fit(A[tr], Y[tr], pen); ps.append(1 / (1 + np.exp(-(A[te] @ b)))); ys.append(Y[te])
    print(f"  {('base' if extra is None else '+ ' + extra):<20} {score(np.concatenate(ps), np.concatenate(ys))}")
# size of the effect, fitted on all games up to 1 Nov
for extra in EXF:
    A = np.c_[tl, D, XE[:, EXF.index(extra)]]; allok = np.where(ok)[0]
    b = logit_fit(A[allok], Y[allok], np.r_[0.0, np.full(D.shape[1], LP), 0.0])
    print(f"fitted on all games, {extra}: weight {b[-1]:+.3f} (one unit more than the opponent = {100 * (1 / (1 + np.exp(-b[-1])) - 0.5):+.1f} win-% points in an even game)")
