"""Sim session 2, step 2 (read-only): champion strength and player-champion comfort, measured beyond v1's odds.
For each day, features use only earlier days (no look-ahead). Residual of a player-row = result - v1's win chance for that side.
  champ  = champion-role strength: recency-weighted residual sum / (weight + k1)          (major games with v1 odds)
  cgames = log(1 + player's earlier games on the champion, all leagues incl. minor)       (history, per decision)
  cres   = player-champion residual, shrunk: sum / (weight + k2)                          (major games with v1 odds)
  newpk  = number of players on a champion they have never played in the file
Game feature = blue sum - red sum. Model: logit = z_v1 + b . features (small ridge).
Tuning on Jul-Aug (fit Feb-Jun); test: fit Feb-Aug, predict from 1 Sep and Worlds.
usage: python -I s2_champ.py <csv> v1_games.csv <out_dir>"""
import json, os, sys
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
raw = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                  usecols=["gameid", "league", "date", "side", "position", "playerid", "playername", "champion", "result"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]
V = pd.read_csv(V1); V["day"] = V.date.str[:10]
pv = V.set_index("gameid").p_v1.to_dict()
raw["major"] = raw.league.isin(MAJOR)
raw["p_side"] = raw.gameid.map(pv)
raw.loc[raw.side == "Red", "p_side"] = 1 - raw.loc[raw.side == "Red", "p_side"]
raw["res"] = raw.result - raw.p_side
raw = raw.sort_values(["day", "gameid"])
DAYS = sorted(raw.day.unique())
t_of = {d: (pd.Timestamp(d) - pd.Timestamp("2026-01-01")).days for d in DAYS}

def run_features(hl, k1, k2):
    """returns DataFrame gameid -> features (blue - red) for major games"""
    acc_c, acc_r, cnt = {}, {}, {}
    def val(acc, key, t, k):
        if key not in acc: return 0.0, 0.0
        S, N, t0 = acc[key]; f = 1.0 if hl is None else 0.5 ** ((t - t0) / hl)
        return S * f, N * f
    def add(acc, key, t, r):
        S, N = val(acc, key, t, 0); acc[key] = (S + r, N + 1.0, t)
    feats = {}
    for d, day_rows in raw.groupby("day", sort=True):
        t = t_of[d]
        mj = day_rows[day_rows.major]
        for r in mj.itertuples(index=False):
            sg = 1.0 if r.side == "Blue" else -1.0
            S, N = val(acc_c, (r.champion, r.position), t, k1); champ = S / (N + k1)
            S2, N2 = val(acc_r, (r.playerid, r.champion), t, k2); cres = S2 / (N2 + k2)
            n = cnt.get((r.playerid, r.champion), 0)
            f = feats.setdefault(r.gameid, [0.0, 0.0, 0.0, 0.0])
            f[0] += sg * champ; f[1] += sg * np.log1p(n); f[2] += sg * cres; f[3] += sg * (n == 0)
        for r in day_rows.itertuples(index=False):
            cnt[(r.playerid, r.champion)] = cnt.get((r.playerid, r.champion), 0) + 1
            if r.major and not np.isnan(r.res):
                add(acc_c, (r.champion, r.position), t, r.res); add(acc_r, (r.playerid, r.champion), t, r.res)
    F = pd.DataFrame.from_dict(feats, orient="index", columns=["champ", "cgames", "cres", "newpk"])
    return F, acc_c, cnt

def fit(Z, X, y, lam=1.0, iters=50):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6)
    return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4), round(float(np.mean((p > .5) == (y == 1))), 3)

G = V.dropna(subset=["z_v1"]).set_index("gameid")
SETS = {"champ": ["champ"], "comfort": ["cgames", "cres", "newpk"], "cgames": ["cgames"], "cres": ["cres"], "newpk": ["newpk"],
        "champ+comfort": ["champ", "cgames", "cres", "newpk"]}
def split(D, a, z): return D[(D.day >= a) & (D.day < z)]
R = {"tuning": []}
cache = {}
for hl in (90, 180, None):
    for k1 in (10, 30, 100):
        for k2 in (3, 10, 30):
            F, _, _ = run_features(hl, k1, k2); D = G.join(F, how="inner")
            tr, va = split(D, "2026-02-01", "2026-07-01"), split(D, "2026-07-01", "2026-09-01")
            cols = SETS["champ+comfort"]; b = fit(tr.z_v1.values, tr[cols].values, tr.blue_win.values)
            R["tuning"].append([hl, k1, k2, ll(va.z_v1.values, va[cols].values, va.blue_win.values, b)[0]])
            cache[(hl, k1, k2)] = D
R["tuning"].sort(key=lambda x: x[3])
hl, k1, k2, _ = R["tuning"][0]; R["chosen"] = {"half_life": hl, "k_champ": k1, "k_comfort": k2}
D = cache[(hl, k1, k2)]
tr, va, te = split(D, "2026-02-01", "2026-09-01"), split(D, "2026-07-01", "2026-09-01"), split(D, "2026-09-01", "2027-01-01")
wo = D[D.league == "WLDs"]
zero = np.zeros((0,))
R["v1"] = {"jul_aug": ll(va.z_v1.values, np.zeros((len(va), 1)), va.blue_win.values, np.zeros(1)),
           "from_sep": ll(te.z_v1.values, np.zeros((len(te), 1)), te.blue_win.values, np.zeros(1)),
           "worlds": ll(wo.z_v1.values, np.zeros((len(wo), 1)), wo.blue_win.values, np.zeros(1)), "n_from_sep": len(te), "n_worlds": len(wo)}
R["models"] = {}
for name, cols in SETS.items():
    trv = split(D, "2026-02-01", "2026-07-01"); bv = fit(trv.z_v1.values, trv[cols].values, trv.blue_win.values)
    b = fit(tr.z_v1.values, tr[cols].values, tr.blue_win.values)
    R["models"][name] = {"weights": dict(zip(cols, np.round(b, 3).tolist())),
                         "jul_aug": ll(va.z_v1.values, va[cols].values, va.blue_win.values, bv),
                         "from_sep": ll(te.z_v1.values, te[cols].values, te.blue_win.values, b),
                         "worlds": ll(wo.z_v1.values, wo[cols].values, wo.blue_win.values, b)}
# feature spread, to read weights
R["spread_sd"] = D[SETS["champ+comfort"]].std().round(3).to_dict()
# champion-role table at the end of the data (all games), for comparison with outside sources
F, acc_c, cnt = run_features(hl, k1, k2)
tend = t_of[DAYS[-1]] + 1
mj = raw[raw.major]
base = mj.groupby(["champion", "position"]).agg(games=("gameid", "size"), wins=("result", "sum"), res_raw=("res", "mean")).reset_index()
def strength(r):
    if (r.champion, r.position) not in acc_c: return 0.0
    S, N, t0 = acc_c[(r.champion, r.position)]; f = 1.0 if hl is None else 0.5 ** ((tend - t0) / hl); return S * f / (N * f + k1)
base["wr"] = (base.wins / base.games).round(3)
base["strength"] = base.apply(strength, axis=1).round(4)
base.sort_values("games", ascending=False).to_csv(os.path.join(OUT, "champion_strength_now.csv"), index=False)
json.dump(R, open(os.path.join(OUT, "champfit_results.json"), "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if k != "tuning"}, indent=1, default=str))
print("best tuning:", R["tuning"][:5])
