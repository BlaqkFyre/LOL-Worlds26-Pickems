"""Sim session 2, part 2 (read-only): player time together (Luke's "player and team synergy").
For each game and side, how many earlier games each pair of teammates has played on the same team (all leagues incl. minor,
earlier days only; the file starts 1 Jan 2026, so 2025 history is not counted).
Features (blue minus red): log(1 + games together) for each of the 10 role pairs; team cohesion = mean over the 10 pairs;
newest link = the smallest pair count on the side (a new or stand-in player shows up here).
Test 1 (model): each feature alone on top of v1; pass = better than v1 on both Jul-Aug (fit Feb-Jun) and from 1 Sep (fit Feb-Aug).
Test 2 (direct): sides banded by newest link (0-9 / 10-49 / 50+ games together): won - v1 expected, by event group.
usage: python -I s2_together.py <OE csv> v1_games.csv <out_dir>"""
import itertools, json, os, sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; DOM = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL"}
ROLES = ["top", "jng", "mid", "bot", "sup"]; PAIRS = list(itertools.combinations(ROLES, 2))
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "playoffs", "side", "position", "playerid", "result"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
V = pd.read_csv(V1).set_index("gameid"); pv = V.p_v1.to_dict()
together = defaultdict(int); feats, sides = {}, []
for d, rows in raw.sort_values("day").groupby("day", sort=True):
    for g, gr in rows.groupby("gameid"):
        P = {(r.side, r.position): r.playerid for r in gr.itertuples(index=False)}
        lg = gr.league.iloc[0]; po = gr.playoffs.max()
        if lg in MAJOR:
            f = defaultdict(float)
            for sd, sg in (("Blue", 1.0), ("Red", -1.0)):
                vals = []
                for a, b in PAIRS:
                    x, y = P.get((sd, a)), P.get((sd, b)); x = x if isinstance(x, str) else None; y = y if isinstance(y, str) else None
                    if x and y:
                        n = together[tuple(sorted((x, y)))]; v = np.log1p(n); f[f"pair|{a}-{b}"] += sg * v; vals.append(n)
                if vals:
                    f["cohesion|team"] += sg * float(np.mean(np.log1p(vals))); f["newest_link|team"] += sg * float(np.log1p(min(vals)))
                    p = pv.get(g, np.nan)
                    if not np.isnan(p):
                        grp = "Worlds" if lg == "WLDs" else ("Internationals (MSI, EWC, First Stand)" if lg in ("MSI", "EWC", "FST") else
                              ("Domestic playoffs" if po == 1 else "Domestic regular season"))
                        won = gr[gr.side == sd].result.iloc[0]
                        sides.append((grp, g, min(vals), won, p if sd == "Blue" else 1 - p))
            feats[g] = f
    for g, gr in rows.groupby("gameid"):   # update after the day
        for sd in ("Blue", "Red"):
            ids = [r.playerid for r in gr[gr.side == sd].itertuples(index=False) if isinstance(r.playerid, str)]
            for x, y in itertools.combinations(sorted(set(ids)), 2): together[(x, y)] += 1
F = pd.DataFrame.from_dict(feats, orient="index").fillna(0.0)
G = V.dropna(subset=["z_v1"]).drop(columns=["patch"], errors="ignore"); G["day"] = G.date.str[:10]
D = G.join(F, how="inner").fillna(0.0)
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); gr = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, gr); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
sp = lambda a, z: D[(D.day >= a) & (D.day < z)]
trv, va, tr, te, wo = sp("2026-02-01", "2026-07-01"), sp("2026-07-01", "2026-09-01"), sp("2026-02-01", "2026-09-01"), sp("2026-09-01", "2027-01-01"), D[D.league == "WLDs"]
base = {n: ll(d.z_v1.values, np.zeros((len(d), 1)), d.blue_win.values, np.zeros(1)) for n, d in (("jul_aug", va), ("from_sep", te), ("worlds", wo))}
rows = []
for c in sorted(F.columns):
    sd = tr[c].std()
    if not sd: continue
    X = lambda d: (d[[c]] / sd).values
    bv = fit(trv.z_v1.values, X(trv), trv.blue_win.values); b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
    r = {"input": c.split("|")[0], "pair": c.split("|")[1], "weight_per_sd": round(float(b[0]), 3),
         "d_jul_aug": round(ll(va.z_v1.values, X(va), va.blue_win.values, bv) - base["jul_aug"], 4),
         "d_from_sep": round(ll(te.z_v1.values, X(te), te.blue_win.values, b) - base["from_sep"], 4),
         "d_worlds": round(ll(wo.z_v1.values, X(wo), wo.blue_win.values, b) - base["worlds"], 4)}
    r["passes"] = bool(r["d_jul_aug"] < 0 and r["d_from_sep"] < 0); rows.append(r)
T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "together_results.csv"), index=False)
S = pd.DataFrame(sides, columns=["group", "gameid", "newest", "won", "expected"])
S["band"] = pd.cut(S.newest, [-1, 9, 49, 10**6], labels=["0-9", "10-49", "50+"])
out = []
for grp in ["Worlds", "Internationals (MSI, EWC, First Stand)", "Domestic playoffs", "Domestic regular season"]:
    for band, B in S[S.group == grp].groupby("band", observed=True):
        dd = B.won - B.expected
        out.append({"group": grp, "band": band, "sides": len(B), "won_minus_expected": round(100 * dd.mean(), 1), "rough_se": round(100 * dd.std() / np.sqrt(len(B)), 1)})
B = pd.DataFrame(out); B.to_csv(os.path.join(OUT, "together_bands.csv"), index=False)
pd.set_option("display.width", 200); print("v1:", {k: round(v, 4) for k, v in base.items()}); print(T.to_string(index=False)); print(B.to_string(index=False))
