"""Sim session 2, part 2 (read-only): draft meta model - which champions get picked or banned in a pro game.
One row per (game, champion) for every champion seen in 2026 major-league drafts. Target: picked or banned in that game (presence),
and separately picked. Features, from earlier days only:
  pres30      pro presence (picks + bans per game) over the previous 30 days
  pres_season pro presence over all earlier days, 90-day half-life
  pres_patch  pro presence on the game's patch so far (0 if none), and log(1 + games played on that patch so far)
  solo_pick, solo_ban  lolalytics Emerald+ pick rate (summed over lanes) and ban rate on the game's patch (16.11+; 0 and a flag otherwise)
  pools       how many of the 10 players have the champion with 3+ games in the last 180 days (all leagues)
  locked      already picked earlier in this series (Fearless: can't be picked again)
Model: logistic regression (few features, ridge). Train: games before 1 Sep. Test: from 1 Sep, and Worlds.
Scores: log loss per champion-row; hit rate = of the champions actually picked or banned, the share in the model's top 20 for that game
(20 = picks + bans per game); compared with simple baselines (last-30-days presence alone; season presence alone).
usage: python -I s2_draftmeta.py <OE csv> lola_tiers_all.csv <out_dir>"""
import os, sys
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

CSV, TIERS, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
def np_(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
raw = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                  usecols=["gameid", "league", "date", "patch", "side", "position", "playerid", "teamid", "champion", "ban1", "ban2", "ban3", "ban4", "ban5"])
raw = raw[~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]; raw["patch"] = raw.patch.map(np_); raw["t"] = (pd.to_datetime(raw.day) - pd.Timestamp("2026-01-01")).dt.days
tmid = raw[(raw.position != "team") & raw.teamid.notna()].groupby("gameid").agg(day=("day", "first"), date=("date", "first"),
                                                                                 teams=("teamid", lambda s: "|".join(sorted(set(map(str, s))))))
tmid["series"] = tmid.day + "|" + tmid.teams
raw = raw.join(tmid[["series"]], on="gameid")
L = pd.read_csv(TIERS, dtype={"patch": str}); L["patch"] = L.patch.map(np_); L["k"] = L.name.map(key)
solo_pick = L.groupby(["patch", "k"]).pr.sum().to_dict(); solo_ban = L.groupby(["patch", "k"]).br.max().to_dict(); lola_patches = set(L.patch)
games_major = raw[raw.league.isin(MAJOR)]
CHAMPS = sorted(set(games_major[games_major.position != "team"].champion.dropna()))
CI = {c: i for i, c in enumerate(CHAMPS)}; NC = len(CHAMPS)
hist = defaultdict(list)                     # player -> [(t, champ)]
pres_events = []                             # (t, patch, champ) one per pick or ban in a major game
games_by_t = []                              # (t, patch) per major game
season = np.zeros(NC); season_t = 0.0; season_n = 0.0
picked_in_series = defaultdict(set)
X_rows, meta_rows = [], []
for d, rows in raw.sort_values("date").groupby("day", sort=True):
    t = rows.t.iloc[0]
    ev = [(tt, p, c) for (tt, p, c) in pres_events if t - tt <= 30]; n30 = sum(1 for (tt, p) in games_by_t if t - tt <= 30)
    c30 = np.zeros(NC)
    for _, _, c in ev: c30[CI[c]] += 1
    f = 0.5 ** ((t - season_t) / 90.0); season *= f; season_n *= f; season_t = t
    for g, gr in rows.sort_values("date").groupby("gameid", sort=False):
        lg = gr.league.iloc[0]
        if lg not in MAJOR: continue
        p = gr.patch.iloc[0]; s = gr.series.iloc[0]
        pl = gr[gr.position != "team"]; tm = gr[gr.position == "team"]
        bans = [b for r in tm.itertuples(index=False) for b in (r.ban1, r.ban2, r.ban3, r.ban4, r.ban5) if isinstance(b, str)]
        picks = list(pl.champion)
        npatch = sum(1 for (tt, pp) in games_by_t if pp == p)
        cp = np.zeros(NC)
        for (tt, pp, c) in pres_events:
            if pp == p: cp[CI[c]] += 1
        pools = np.zeros(NC)
        for r in pl.itertuples(index=False):
            if not isinstance(r.playerid, str): continue
            cnt = Counter(c for tt, c in hist[r.playerid] if t - tt <= 180)
            for c, n in cnt.items():
                if n >= 3 and c in CI: pools[CI[c]] += 1
        locked = np.zeros(NC)
        for c in picked_in_series.get(s, ()):
            if c in CI: locked[CI[c]] = 1
        has_solo = p in lola_patches
        sp_ = np.array([solo_pick.get((p, key(c)), 0.0) for c in CHAMPS]) / 100; sb_ = np.array([solo_ban.get((p, key(c)), 0.0) for c in CHAMPS]) / 100
        F = np.c_[c30 / max(n30, 1), season / max(season_n, 1), cp / max(npatch, 1), np.full(NC, np.log1p(npatch)),
                  sp_, sb_, np.full(NC, float(not has_solo)), pools / 10, locked]
        y_pres = np.zeros(NC); y_pick = np.zeros(NC)
        for c in bans + picks:
            if c in CI: y_pres[CI[c]] = 1
        for c in picks:
            if c in CI: y_pick[CI[c]] = 1
        X_rows.append(F); meta_rows.append((g, d, lg, y_pres, y_pick))
        for c in bans + picks:
            if c in CI: pres_events.append((t, p, c)); season[CI[c]] += 1
        games_by_t.append((t, p)); season_n += 1
        picked_in_series[s] |= set(picks)
    for r in rows[rows.position != "team"].itertuples(index=False):
        if isinstance(r.playerid, str): hist[r.playerid].append((t, r.champion))
FEAT = ["pres30", "pres_season", "pres_patch", "log_patch_games", "solo_pick", "solo_ban", "no_solo", "pools", "locked"]
X = np.vstack(X_rows); G = np.repeat(np.arange(len(meta_rows)), NC)
Yp = np.concatenate([m[3] for m in meta_rows]); Yk = np.concatenate([m[4] for m in meta_rows])
day = np.array([m[1] for m in meta_rows]); lg = np.array([m[2] for m in meta_rows])
gtr = np.where(day < "2026-09-01")[0]; gte = np.where(day >= "2026-09-01")[0]; gwo = np.where(lg == "WLDs")[0]
rows_of = lambda gs: np.isin(G, gs)
def fit(Xm, y, lam=1.0):
    Xm = np.c_[np.ones(len(Xm)), Xm]; b = np.zeros(Xm.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-(Xm @ b))); g = Xm.T @ (p - y) + lam * np.r_[0, b[1:]]
        H = (Xm * (p * (1 - p))[:, None]).T @ Xm + lam * np.diag(np.r_[0, np.ones(len(b) - 1)]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-8: break
    return b
pred = lambda b, Xm: 1 / (1 + np.exp(-(np.c_[np.ones(len(Xm)), Xm] @ b)))
def score(p, y, gs):
    m = rows_of(gs); pp = np.clip(p[m], 1e-6, 1 - 1e-6); yy = y[m]
    ll = float(-np.mean(yy * np.log(pp) + (1 - yy) * np.log(1 - pp)))
    hits, tot = 0, 0
    for k, gi in enumerate(gs):
        pg = p[G == gi]; yg = y[G == gi]; top = np.argsort(-pg)[:20]; hits += yg[top].sum(); tot += yg.sum()
    return round(ll, 4), round(hits / max(tot, 1), 3)
mu, sdv = X[rows_of(gtr)].mean(0), X[rows_of(gtr)].std(0) + 1e-9; Z = (X - mu) / sdv
out = {}
for target, Y in (("presence (pick or ban)", Yp), ("picked", Yk)):
    res = {}
    for name, cols in {"last-30-days presence only": [0], "season presence only": [1],
                       "pro presence (30 days + season + patch)": [0, 1, 2, 3], "+ lolalytics": [0, 1, 2, 3, 4, 5, 6],
                       "+ lolalytics + player pools": [0, 1, 2, 3, 4, 5, 6, 7], "full (+ Fearless lock)": list(range(9))}.items():
        b = fit(Z[rows_of(gtr)][:, cols], Y[rows_of(gtr)]); p = pred(b, Z[:, cols])
        res[name] = {"from_sep": score(p, Y, gte), "worlds": score(p, Y, gwo)}
        if name.startswith("full"): out[target] = dict(zip(["intercept"] + [FEAT[c] for c in cols], np.round(b, 3).tolist()))
    print(f"\n{target}: (log loss per champion-row, share of actual picks/bans in the model's top 20)  games from 1 Sep {len(gte)}, Worlds {len(gwo)}")
    for n, r in res.items(): print(f"   {n:<42} from 1 Sep {r['from_sep']}   Worlds {r['worlds']}")
    pd.DataFrame(res).T.to_csv(os.path.join(OUT, f"draftmeta_{'presence' if 'pres' in target else 'picked'}.csv"))
print("\nweights per standard deviation (full model):"); [print("  ", k, v) for k, v in out.items()]
