"""Sim session 2, part 2 (read-only): champion pool depth as part of player ratings (Luke, 5 Nov: "deep research").
2026 is Fearless everywhere in the file (0 repeat picks inside a series in every major league), so a series' later games lock out
champions already used. Player history = all leagues incl. minor, 2026, earlier days only.
Measures per player at game time:
  pool_eff90   effective number of champions, last 90 days (exp of the entropy of champion shares)
  pool_n3_180  champions with 3+ games in the last 180 days
  meta_pool    of the player's champions with 2+ games (180 days), how many are in the current pro meta for the role
               (top 10 by pro picks in that role over the previous 30 days; earlier days only)
  free_comfort champions with 3+ games (180 days) the player can still pick in this game: not already used in this series by
               either team (Fearless). In game 1 it equals pool_n3_180.
Tests:
  (A) pool v skill: correlation of each measure with the player's pre-game role skill (session 1 estimate), per role.
  (B) beyond v1, per role and team total: fit Feb-Aug, change in log loss from 1 Sep, split game 1 v games 2+ of a series, and Worlds;
      plus the Jul-Aug check (fit Feb-Jun).
  (C) direct: in games 3+ of a series, sides banded by team free comfort; won - v1 expected.
usage: python -I s2_pool.py <OE csv> v1_games.csv gfeat.csv <out_dir>"""
import os, sys
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

CSV, V1, GF, OUT = sys.argv[1:5]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own", "sup": "e_playmaking"}
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "game", "side", "position", "playerid", "teamid", "champion", "result"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]; raw["t"] = (pd.to_datetime(raw.day) - pd.Timestamp("2026-01-01")).dt.days
# series = same day, same two teams; order games by time
tm = raw[raw.teamid.notna()].groupby("gameid").agg(day=("day", "first"), date=("date", "first"),
                                                     teams=("teamid", lambda s: "|".join(sorted(set(map(str, s))))))
tm["series"] = tm.day + "|" + tm.teams; tm = tm.sort_values("date"); tm["gnum"] = tm.groupby("series").cumcount() + 1
raw = raw.join(tm[["series", "gnum"]], on="gameid")
V = pd.read_csv(V1).set_index("gameid"); pv = V.p_v1.to_dict()
gf = pd.read_csv(GF); gf["skill"] = [r[SKILL[r.position]] for _, r in gf.iterrows()]
skill = {(r.gameid, r.side, r.position): r.skill for r in gf.itertuples(index=False)}
hist = defaultdict(list)                       # player -> [(t, champion)]
proh = []                                      # (t, role, champion) pro picks, major only
used_in_series = defaultdict(set)              # series -> champions used so far
feats, prow, sides = {}, [], []
def pool(pid, t):
    h90 = Counter(ch for tt, ch in hist[pid] if t - tt <= 90); h180 = Counter(ch for tt, ch in hist[pid] if t - tt <= 180)
    if h90:
        sh = np.array(list(h90.values()), float); sh /= sh.sum(); eff = float(np.exp(-(sh * np.log(sh)).sum()))
    else: eff = 0.0
    return eff, {c for c, n in h180.items() if n >= 3}, {c for c, n in h180.items() if n >= 2}
for d, rows in raw.sort_values(["date"]).groupby("day", sort=True):
    t = rows.t.iloc[0]
    recent = Counter((r, c) for tt, r, c in proh if t - tt <= 30)
    meta = {r: {c for (rr, c), n in recent.most_common() if rr == r} for r in ROLES}
    meta = {r: set([c for (rr, c), n in sorted(recent.items(), key=lambda kv: -kv[1]) if rr == r][:10]) for r in ROLES}
    for g, gr in rows.sort_values("date").groupby("gameid", sort=False):
        lg = gr.league.iloc[0]; s = gr.series.iloc[0]; gn = gr.gnum.iloc[0]
        if lg in MAJOR:
            f = defaultdict(float)
            for sd, sg in (("Blue", 1.0), ("Red", -1.0)):
                team_free = 0
                for r in gr[gr.side == sd].itertuples(index=False):
                    if not isinstance(r.playerid, str) or r.position not in ROLES: continue
                    eff, n3, n2 = pool(r.playerid, t)
                    free = len(n3 - used_in_series[s]) if isinstance(s, str) else len(n3)
                    mp = len(n2 & meta[r.position])
                    for k, v in (("pool_eff90", eff), ("pool_n3_180", len(n3)), ("meta_pool", mp), ("free_comfort", free)):
                        f[f"{k}|{r.position}"] += sg * v; f[f"{k}|team"] += sg * v
                    team_free += free
                    sk = skill.get((g, sd, r.position), np.nan)
                    prow.append((r.position, eff, len(n3), mp, sk))
                p = pv.get(g, np.nan)
                if not np.isnan(p):
                    won = gr[gr.side == sd].result.iloc[0]
                    sides.append((g, gn, team_free, won, p if sd == "Blue" else 1 - p, lg))
            f["gnum"] = gn; feats[g] = f
        if isinstance(s, str): used_in_series[s] |= set(gr.champion)
    for r in rows.itertuples(index=False):
        if isinstance(r.playerid, str): hist[r.playerid].append((t, r.champion))
        if r.league in MAJOR and r.position in ROLES: proh.append((t, r.position, r.champion))
F = pd.DataFrame.from_dict(feats, orient="index").fillna(0.0)
# (A) pool v skill
P = pd.DataFrame(prow, columns=["role", "pool_eff90", "pool_n3_180", "meta_pool", "skill"]).dropna()
A = {r: {k: round(float(P[P.role == r][[k, "skill"]].corr().iloc[0, 1]), 3) for k in ["pool_eff90", "pool_n3_180", "meta_pool"]} for r in ROLES}
print("(A) correlation with the player's pre-game role skill:"); print(pd.DataFrame(A).T.to_string())
print("typical values (median per role):"); print(P.groupby("role")[["pool_eff90", "pool_n3_180", "meta_pool"]].median().round(1).to_string())
# (B) beyond v1
G = V.dropna(subset=["z_v1"]).drop(columns=["patch"], errors="ignore"); G["day"] = G.date.str[:10]
D = G.join(F, how="inner").fillna(0.0)
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
sp = lambda a, z: D[(D.day >= a) & (D.day < z)]
trv, va, tr, te, wo = sp("2026-02-01", "2026-07-01"), sp("2026-07-01", "2026-09-01"), sp("2026-02-01", "2026-09-01"), sp("2026-09-01", "2027-01-01"), D[D.league == "WLDs"]
sets = {"jul_aug": va, "from_sep": te, "from_sep_game1": te[te.gnum == 1], "from_sep_game2plus": te[te.gnum >= 2], "worlds": wo}
base = {n: ll(d.z_v1.values, np.zeros((len(d), 1)), d.blue_win.values, np.zeros(1)) for n, d in sets.items()}
rows = []
for c in sorted(x for x in F.columns if "|" in x):
    sd = tr[c].std()
    if not sd: continue
    X = lambda d: (d[[c]] / sd).values
    bv = fit(trv.z_v1.values, X(trv), trv.blue_win.values); b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
    r = {"measure": c.split("|")[0], "role": c.split("|")[1], "weight_per_sd": round(float(b[0]), 3)}
    for n, d in sets.items():
        bb = bv if n == "jul_aug" else b
        r["d_" + n] = round(ll(d.z_v1.values, X(d), d.blue_win.values, bb) - base[n], 4)
    r["passes"] = bool(r["d_jul_aug"] < 0 and r["d_from_sep"] < 0); rows.append(r)
T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "pool_results.csv"), index=False)
pd.set_option("display.width", 220); print("\n(B) v1:", {k: round(v, 4) for k, v in base.items()}, "games:", {k: len(v) for k, v in sets.items()})
print(T.to_string(index=False))
# (C) direct, later series games
S = pd.DataFrame(sides, columns=["gameid", "gnum", "team_free", "won", "expected", "league"])
for lab, sub in (("games 3+ of a series", S[S.gnum >= 3]), ("game 1", S[S.gnum == 1])):
    q = sub.team_free.quantile([0.25, 0.75]).values
    sub = sub.assign(band=pd.cut(sub.team_free, [-1, q[0], q[1], 10**6], labels=["lowest quarter", "middle half", "highest quarter"]))
    o = sub.groupby("band", observed=True).apply(lambda B: pd.Series({"sides": len(B), "free_comfort_median": B.team_free.median(),
                                                                      "won_minus_expected": round(100 * (B.won - B.expected).mean(), 1),
                                                                      "rough_se": round(100 * (B.won - B.expected).std() / np.sqrt(len(B)), 1)}))
    print(f"\n(C) {lab}:"); print(o.to_string()); o.to_csv(os.path.join(OUT, f"pool_direct_{'g3plus' if 'games' in lab else 'g1'}.csv"))
