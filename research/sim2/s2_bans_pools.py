"""Sim session 2, part 2 (read-only): denials (bans) and player champion pool depth.
All from earlier days only (no look-ahead); player history = all leagues incl. minor (2026 only).
Denials, per side (blue minus red):
  deny_top3   number of the opponents' top-3 comfort champions (each opposing player's 3 most-played champions) this side banned
  deny_weight sum over this side's bans of log(1 + the most games any opposing player has on that champion)
  denied_pick mean comfort (log 1 + earlier games) of the champions the OPPONENTS ended up playing (shows whether bans pushed them off comfort)
Pool depth, per player (blue minus red, per role and team total):
  pool_eff    effective number of champions in the player's last 90 days (exp of the entropy of their champion shares)
  pool_n3     champions with 3+ games in the last 90 days
Test: each alone on top of v1; pass = better than v1 on Jul-Aug (fit Feb-Jun) and from 1 Sep (fit Feb-Aug); Worlds reported.
Direct check: sides banded by deny_top3 (0 / 1 / 2+), won - v1 expected, big events v regular season.
usage: python -I s2_bans_pools.py <OE csv> v1_games.csv <out_dir>"""
import json, os, sys
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; DOM = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL"}
ROLES = ["top", "jng", "mid", "bot", "sup"]
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "playoffs", "side", "position", "playerid", "champion", "result",
                                                  "ban1", "ban2", "ban3", "ban4", "ban5"])
raw = raw[~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
raw["t"] = (pd.to_datetime(raw.day) - pd.Timestamp("2026-01-01")).dt.days
V = pd.read_csv(V1).set_index("gameid"); pv = V.p_v1.to_dict()
cnt = defaultdict(Counter)                 # player -> champion -> games
hist = defaultdict(list)                   # player -> [(t, champion)]
feats, sides = {}, []
for d, rows in raw.sort_values("day").groupby("day", sort=True):
    t = rows.t.iloc[0]
    for g, gr in rows.groupby("gameid"):
        lg = gr.league.iloc[0]
        if lg not in MAJOR: continue
        pl = gr[gr.position != "team"]; tm = gr[gr.position == "team"]
        P = {(r.side, r.position): r for r in pl.itertuples(index=False) if isinstance(r.playerid, str)}
        bans = {r.side: [b for b in (r.ban1, r.ban2, r.ban3, r.ban4, r.ban5) if isinstance(b, str)] for r in tm.itertuples(index=False)}
        f = defaultdict(float); dt = {}
        for sd, sg in (("Blue", 1.0), ("Red", -1.0)):
            opp = "Red" if sd == "Blue" else "Blue"
            opp_players = [P[(opp, r)].playerid for r in ROLES if (opp, r) in P]
            top3 = set(); best = Counter()
            for pid in opp_players:
                c = cnt[pid]; top3 |= {ch for ch, _ in c.most_common(3)}
                for ch, n in c.items(): best[ch] = max(best[ch], n)
            mine = bans.get(sd, [])
            d3 = sum(1 for b in mine if b in top3); f["deny_top3|team"] += sg * d3; dt[sd] = d3
            f["deny_weight|team"] += sg * sum(np.log1p(best.get(b, 0)) for b in mine)
            oc = [np.log1p(cnt[P[(opp, r)].playerid][P[(opp, r)].champion]) for r in ROLES if (opp, r) in P]
            if oc: f["denied_pick|team"] += sg * -float(np.mean(oc))      # lower opponent comfort = good for this side
            tot_eff = 0.0
            for r in ROLES:
                if (sd, r) not in P: continue
                h = [ch for (tt, ch) in hist[P[(sd, r)].playerid] if t - tt <= 90]
                if h:
                    sh = np.array(list(Counter(h).values()), float); sh /= sh.sum(); eff = float(np.exp(-(sh * np.log(sh)).sum()))
                    n3 = sum(1 for v in Counter(h).values() if v >= 3)
                else:
                    eff, n3 = 0.0, 0
                f[f"pool_eff|{r}"] += sg * eff; f[f"pool_n3|{r}"] += sg * n3; tot_eff += eff
            f["pool_eff|team"] += sg * tot_eff
        feats[g] = f
        p = pv.get(g, np.nan)
        if not np.isnan(p) and len(dt) == 2:
            grp = "Big events" if (lg in ("WLDs", "MSI", "EWC", "FST") or gr.playoffs.max() == 1) else "Domestic regular season"
            for sd in ("Blue", "Red"):
                won = pl[pl.side == sd].result.iloc[0] if len(pl[pl.side == sd]) else np.nan
                sides.append((grp, g, dt[sd], won, p if sd == "Blue" else 1 - p))
    for r in rows[rows.position != "team"].itertuples(index=False):   # update after the day
        if isinstance(r.playerid, str): cnt[r.playerid][r.champion] += 1; hist[r.playerid].append((t, r.champion))
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
    r = {"input": c.split("|")[0], "role": c.split("|")[1], "weight_per_sd": round(float(b[0]), 3),
         "d_jul_aug": round(ll(va.z_v1.values, X(va), va.blue_win.values, bv) - base["jul_aug"], 4),
         "d_from_sep": round(ll(te.z_v1.values, X(te), te.blue_win.values, b) - base["from_sep"], 4),
         "d_worlds": round(ll(wo.z_v1.values, X(wo), wo.blue_win.values, b) - base["worlds"], 4)}
    r["passes"] = bool(r["d_jul_aug"] < 0 and r["d_from_sep"] < 0); rows.append(r)
T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "bans_pools_results.csv"), index=False)
S = pd.DataFrame(sides, columns=["group", "gameid", "deny_top3", "won", "expected"]).dropna()
S["band"] = pd.cut(S.deny_top3, [-1, 0, 1, 99], labels=["0", "1", "2+"])
out = []
for grp in ["Big events", "Domestic regular season"]:
    for band, B in S[S.group == grp].groupby("band", observed=True):
        dd = B.won - B.expected
        out.append({"group": grp, "comfort_bans": band, "sides": len(B), "won_minus_expected": round(100 * dd.mean(), 1), "rough_se": round(100 * dd.std() / np.sqrt(len(B)), 1)})
B = pd.DataFrame(out); B.to_csv(os.path.join(OUT, "bans_bands.csv"), index=False)
print("mean comfort bans per side (top-3 of opponents):", round(S.deny_top3.mean(), 2))
pd.set_option("display.width", 200); print("v1:", {k: round(v, 4) for k, v in base.items()}); print(T.to_string(index=False)); print(B.to_string(index=False))
