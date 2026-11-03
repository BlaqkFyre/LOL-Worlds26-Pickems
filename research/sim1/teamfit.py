"""Sim session 1, step 2: team ratings from game results and the who-wins model, with honest tests.

Model: P(blue wins) = sigmoid(side + s_blue - s_red), s_team = L[home league] + d[team].
  - L: league strength, linked through international games (teams with no home league have L = 0).
  - d: the team's own strength within its league, pulled toward 0 (ridge, strength lam) so few games -> near league average.
  - Game weights: 0.5 ** (age_days / half_life), and x k for games of the same international event being predicted.
  - Optional temperature T: probabilities from sigmoid(z / T), fitted on validation predictions only.
Tuning uses only games before 1 Sep (rolling monthly predictions Mar-Aug, and FST/MSI/EWC day by day for k).
Tests: (a) fit at 1 Sep, predict 1 Sep onwards; (b) Worlds day by day; (c) rolling monthly, Sep-Oct reported apart.
usage: python -I teamfit.py games.csv out_dir"""
import json, os, sys
import numpy as np
import pandas as pd

G = pd.read_csv(sys.argv[1]); OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
G["t"] = pd.to_datetime(G.date)
G["day"] = G.t.dt.strftime("%Y-%m-%d")
TEAMS = sorted(set(G.blue) | set(G.red)); TI = {t: i for i, t in enumerate(TEAMS)}
LEAGUES = sorted({h for h in set(G.blue_home) | set(G.red_home) if isinstance(h, str) and h}); LI = {l: i for i, l in enumerate(LEAGUES)}
NT, NL = len(TEAMS), len(LEAGUES)
home = {}
for r in G.itertuples():
    home[r.blue] = r.blue_home if isinstance(r.blue_home, str) else ""; home[r.red] = r.red_home if isinstance(r.red_home, str) else ""
NAME = {}
for r in G.itertuples():
    NAME[r.blue] = r.blue_app or r.blue_name if isinstance(r.blue_app, str) else r.blue_name
    NAME[r.red] = r.red_app or r.red_name if isinstance(r.red_app, str) else r.red_name

def design(df):
    """rows: +1 for blue team / league, -1 for red; last column = side."""
    X = np.zeros((len(df), NT + NL + 1))
    for n, r in enumerate(df.itertuples()):
        X[n, TI[r.blue]] += 1; X[n, TI[r.red]] -= 1
        if home[r.blue]: X[n, NT + LI[home[r.blue]]] += 1
        if home[r.red]: X[n, NT + LI[home[r.red]]] -= 1
        X[n, -1] = 1
    return X

XALL = design(G); YALL = G.blue_win.values.astype(float)

def fit(idx, w, lam, lamL=0.1, iters=30):
    X, y = XALL[idx], YALL[idx]
    P = np.zeros(X.shape[1]); pen = np.r_[np.full(NT, lam), np.full(NL, lamL), 0.0]
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ b)))
        g = X.T @ (w * (p - y)) + pen * b
        H = (X * (w * p * (1 - p))[:, None]).T @ X + np.diag(pen + 1e-9)
        step = np.linalg.solve(H, g); b -= step
        if np.max(np.abs(step)) < 1e-7: break
    return b

def weights(idx, when, hl, k=1.0, event=None):
    age = (when - G.t.values[idx]) / np.timedelta64(1, "D")
    w = np.ones(len(idx)) if hl is None else 0.5 ** (age / hl)
    if event is not None: w = w * np.where(G.league.values[idx] == event, k, 1.0)
    return w

def predict(b, idx, T=1.0):
    return 1 / (1 + np.exp(-(XALL[idx] @ b) / T))

def scores(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "brier": float(np.mean((p - y) ** 2)), "fav_won": float(np.mean((p > 0.5) == (y == 1)))}

def calib(p, y):
    fav = np.where(p >= 0.5, p, 1 - p); won = np.where(p >= 0.5, y, 1 - y); rows = []
    for lo, hi in ((0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)):
        m = (fav >= lo) & (fav < hi)
        if m.any(): rows.append([f"{int(lo*100)}-{min(int(hi*100),100)}%", int(m.sum()), round(float(fav[m].mean()), 3), round(float(won[m].mean()), 3)])
    return rows

def rolling(months, hl, lam, k=1.0, T=1.0):
    ps, ys = [], []
    for m in months:
        start = pd.Timestamp(m); end = start + pd.offsets.MonthBegin(1)
        tr = np.where(G.t < start)[0]; te = np.where((G.t >= start) & (G.t < end))[0]
        if len(te) == 0 or len(tr) < 200: continue
        b = fit(tr, weights(tr, np.datetime64(start), hl), lam)
        ps.append(predict(b, te, T)); ys.append(YALL[te])
    return np.concatenate(ps), np.concatenate(ys)

def dayby(event, hl, lam, k, T=1.0, days=None):
    ev = G[G.league == event]; ps, ys, ids = [], [], []
    for d in sorted(ev.day.unique()):
        if days and d not in days: continue
        tr = np.where(G.day < d)[0]; te = np.where((G.day == d) & (G.league == event))[0]
        b = fit(tr, weights(tr, np.datetime64(d), hl, k, event), lam)
        ps.append(predict(b, te, T)); ys.append(YALL[te]); ids += list(te)
    return np.concatenate(ps), np.concatenate(ys), ids

R = {}
# 1. tune half-life and ridge on rolling months Mar-Aug (validation, before 1 Sep)
VAL = ["2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01"]
grid = []
for hl in (30, 60, 90, 180, None):
    for lam in (0.5, 1, 2, 4, 8):
        p, y = rolling(VAL, hl, lam); s = scores(p, y); grid.append((s["logloss"], hl, lam, s))
grid.sort(key=lambda x: x[0]); _, HL, LAM, _ = grid[0]
R["tuning_grid"] = [[g[1], g[2], round(g[0], 4)] for g in grid]
R["chosen"] = {"half_life_days": HL, "ridge": LAM}
# temperature on the same validation predictions
pv, yv = rolling(VAL, HL, LAM)
zv = np.log(np.clip(pv, 1e-6, 1 - 1e-6) / np.clip(1 - pv, 1e-6, 1))
Ts = np.linspace(0.6, 2.0, 57); llT = [scores(1 / (1 + np.exp(-zv / T)), yv)["logloss"] for T in Ts]
TT = float(Ts[int(np.argmin(llT))]); R["chosen"]["temperature"] = round(TT, 3)
R["validation"] = scores(1 / (1 + np.exp(-zv / TT)), yv)
# 2. tune the same-event weight k on FST, MSI, EWC day by day (all before 1 Sep)
kres = []
for k in (1, 1.5, 2, 3, 5):
    ps, ys = [], []
    for ev in ("FST", "MSI", "EWC"):
        p, y, _ = dayby(ev, HL, LAM, k, TT); ps.append(p); ys.append(y)
    kres.append((scores(np.concatenate(ps), np.concatenate(ys))["logloss"], k))
kres.sort(); K = kres[0][1]; R["k_grid"] = [[k, round(l, 4)] for l, k in sorted(kres, key=lambda x: x[1])]; R["chosen"]["same_event_weight"] = K
# 3. tests
SEP = pd.Timestamp("2026-09-01")
tr = np.where(G.t < SEP)[0]; te = np.where(G.t >= SEP)[0]
b = fit(tr, weights(tr, np.datetime64(SEP), HL), LAM); pa = predict(b, te, TT)
R["test_a_split"] = scores(pa, YALL[te]); R["test_a_calib"] = calib(pa, YALL[te])
R["test_a_by_league"] = {l: scores(pa[G.league.values[te] == l], YALL[te][G.league.values[te] == l]) for l in sorted(set(G.league.values[te]))}
pw, yw, wid = dayby("WLDs", HL, LAM, K, TT)
R["test_b_worlds"] = scores(pw, yw); R["test_b_calib"] = calib(pw, yw)
swiss = np.array([G.day.values[i] >= "2026-10-23" for i in wid])
R["test_b_playin"] = scores(pw[~swiss], yw[~swiss]); R["test_b_swiss"] = scores(pw[swiss], yw[swiss])
pc, yc = rolling(VAL + ["2026-09-01", "2026-10-01"], HL, LAM, K, TT)
R["test_c_rolling_all"] = scores(pc, yc)
pc2, yc2 = rolling(["2026-09-01", "2026-10-01"], HL, LAM, K, TT); R["test_c_rolling_sep_oct"] = scores(pc2, yc2)
R["baselines"] = {"coin_flip_logloss": 0.6931, "blue_rate_train": round(float(YALL[tr].mean()), 3),
                  "blue_only_test_a": scores(np.full(len(te), YALL[tr].mean()), YALL[te])}
# Worlds Swiss per-game predictions (for comparing with the app's out-of-sample odds)
R["worlds_games"] = [[G.day.values[i], NAME[G.blue.values[i]], NAME[G.red.values[i]], round(float(p), 3), int(YALL[i])] for i, p in zip(wid, pw)]
# 4. ratings now: fit on everything up to 1 Nov, Worlds games weighted k
allidx = np.arange(len(G)); now = np.datetime64("2026-11-01")
w = weights(allidx, now, HL, K, "WLDs"); bn = fit(allidx, w, LAM)
s = {t: (LI.get(home[t]) is not None and bn[NT + LI[home[t]]] or 0.0) + bn[TI[t]] for t in TEAMS}
app = {NAME[t]: t for t in TEAMS if NAME[t] in {"GEN","HLE","T1","DK","BLG","AL","TES","IG","G2","MKOI","KC","TL","LYON","TSW","CFO","LOS"}}
avg16 = np.mean([s[t] for t in app.values()])
R["side_logodds"] = round(float(bn[-1]), 3)
R["league_terms"] = {l: round(float(bn[NT + i]), 3) for l, i in LI.items()}
R["worlds16_now"] = sorted([[a, round(float(s[t]), 3), round(float(1 / (1 + np.exp(-(s[t] - avg16) / TT))), 3)] for a, t in app.items()], key=lambda x: -x[1])
json.dump(R, open(os.path.join(OUT, "teamfit_results.json"), "w"), indent=1)
pd.DataFrame([[NAME[t], home[t], round(float(s[t]), 4)] for t in TEAMS], columns=["team", "home", "rating"]).sort_values("rating", ascending=False).to_csv(os.path.join(OUT, "team_ratings_now.csv"), index=False)
for k_ in ("chosen", "validation", "test_a_split", "test_b_worlds", "test_b_playin", "test_b_swiss", "test_c_rolling_all", "test_c_rolling_sep_oct", "baselines", "side_logodds", "league_terms"):
    print(k_, json.dumps(R[k_]))
print("k_grid", R["k_grid"]); print("calib a", R["test_a_calib"]); print("calib worlds", R["test_b_calib"])
print("worlds16 now (rating, win% v average Worlds team):"); [print("  ", x) for x in R["worlds16_now"]]
