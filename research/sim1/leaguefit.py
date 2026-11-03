"""Sim session 1, step 3c: league shift for player skills, recheck of the weights, and the pre-set replacement candidates.
League shift per role (c_r): in international games, a player's per-game result against a stronger-league opponent falls short of
their league-relative estimate. c_r = slope of (actual - estimate) on (opponent league strength - own league strength), pooled over
the role's main skills, sign flipped. Adjusted skill = estimate + c_r * own league strength.
Weights and candidates use the adjusted skills; choices on Jul-Aug, confirmation on 1 Sep onwards and Worlds.
usage: python -I leaguefit.py games.csv prow.csv gfeat.csv pnow.csv data.js out_dir"""
import json, os, re, sys
import numpy as np
import pandas as pd

G = pd.read_csv(sys.argv[1]); PR = pd.read_csv(sys.argv[2]); GF = pd.read_csv(sys.argv[3]); PN = pd.read_csv(sys.argv[4]); DATAJS = sys.argv[5]; OUT = sys.argv[6]
G["t"] = pd.to_datetime(G.date); G["day"] = G.t.dt.strftime("%Y-%m-%d")
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

def logit_fit(A, y, w, pen, iters=40):
    b = np.zeros(A.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(A @ b))); g = A.T @ (w * (p - y)) + pen * b
        H = (A * (w * p * (1 - p))[:, None]).T @ A + np.diag(pen + 1e-9)
        s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-8: break
    return b
pen_t = np.r_[np.full(NT, LAM), np.full(NL, 0.1), 0.0]
def leagues_at(when, idx):
    w = 0.5 ** (((np.datetime64(when) - G.t.values[idx]) / np.timedelta64(1, "D")) / HL)
    b = logit_fit(X[idx], Y[idx], w, pen_t)
    return {l: float(b[NT + i]) for l, i in LI.items()}, b
L_sep, _ = leagues_at("2026-09-01", np.where(G.t < pd.Timestamp("2026-09-01"))[0])
L_now, _ = leagues_at("2026-11-01", np.arange(len(G)))
tl = np.full(len(G), np.nan)
for d in sorted(G.day.unique()):
    tr = np.where(G.day < d)[0]; te = np.where(G.day == d)[0]
    if len(tr) < 150: continue
    _, b = leagues_at(d, tr); tl[te] = (X[te] @ b) / TEMP

MAIN = {"top": ["laning", "teamfight", "cons_side", "cons_dur", "cons_steady"], "jng": ["early", "objectives", "teamfight"],
        "mid": ["laning", "mapimpact", "damage"], "bot": ["lane_own", "lane_duo", "damage", "lategame"], "sup": ["playmaking", "mappresence", "reliability"]}
ALTS = {"top_teamfight": ["teamfight", "alt_tf_kp", "alt_tf_dmg", "alt_tf_dpm", "alt_tf_kapm"], "top_cons_steady": ["cons_steady", "alt_st_d15"],
        "mid_mapimpact": ["mapimpact", "alt_mi_ka15", "alt_mi_fb", "alt_mi_vis", "alt_mi_kp"], "bot_damage": ["damage", "alt_dm_dpm", "alt_dm_share", "alt_dm_eff"]}

# 1. league slope per role from international games
side_home = {}
for r in G.itertuples(): side_home[(r.gameid, "Blue")] = r.blue_home if isinstance(r.blue_home, str) else ""; side_home[(r.gameid, "Red")] = r.red_home if isinstance(r.red_home, str) else ""
M = PR.merge(GF, on=["gameid", "playerid", "side", "position"])
M = M[M.league.isin(["FST", "MSI", "EWC", "WLDs"])]
own = np.array([side_home.get((g, s), "") for g, s in zip(M.gameid, M.side)])
opp = np.array([side_home.get((g, "Red" if s == "Blue" else "Blue"), "") for g, s in zip(M.gameid, M.side)])
Lmap = lambda a: np.array([L_now.get(x, np.nan) if x else np.nan for x in a])
dL = Lmap(opp) - Lmap(own)
C_R = {}
for role, feats in MAIN.items():
    xs, ys = [], []
    m = (M.position == role).values & ~np.isnan(dL)
    for f in feats:
        if f == "cons_steady": continue
        res = (M["f_" + f] - M["e_" + f]).values
        ok = m & ~np.isnan(res); xs.append(dL[ok]); ys.append(res[ok])
    x, y = np.concatenate(xs), np.concatenate(ys)
    slope = float((x * y).sum() / (x * x).sum()); se = float(np.sqrt(np.mean((y - slope * x) ** 2) / (x * x).sum()))
    C_R[role] = {"c": round(-slope, 3), "se": round(se, 3), "n_values": int(len(x))}
print("league strength now", {k: round(v, 2) for k, v in L_now.items()})
print("league shift per role (skill z per 1.0 of league strength):", C_R)

# 2. game differences with league-adjusted skills (adjustment uses pre-September league strengths)
allf = {r: sorted(set(MAIN[r]) | {a for k, v in ALTS.items() if k.startswith(r) for a in v}) for r in MAIN}
COLS = [f"{r}_{f}" for r in MAIN for f in allf[r]]
D = pd.DataFrame(0.0, index=G.gameid, columns=COLS)
for (gid, side, pos), grp in GF.groupby(["gameid", "side", "position"]):
    sg = 1 if side == "Blue" else -1; Lh = L_sep.get(side_home.get((gid, side), ""), 0.0)
    for f in allf[pos]:
        v = grp["e_" + f].iloc[0]
        if pd.notna(v): D.loc[gid, f"{pos}_{f}"] += sg * (float(v) + C_R[pos]["c"] * Lh)
D = D.loc[G.gameid].values; ok = ~np.isnan(tl)
def score(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4), "fav_won": round(float(np.mean((p > 0.5) == (y == 1))), 3)}
def run(cols, tr, te):
    ci = [COLS.index(c) for c in cols]; A = np.c_[tl, D[:, ci]]
    b = logit_fit(A[tr], Y[tr], np.ones(len(tr)), np.r_[0.0, np.full(len(ci), LP)])
    return score(1 / (1 + np.exp(-(A[te] @ b))), Y[te]), dict(zip(cols, np.round(b[1:], 3)))
idx = lambda a, z: np.where(ok & (G.t >= pd.Timestamp(a)) & (G.t < pd.Timestamp(z)))[0]
TRV, VA, TR, TE = idx("2026-02-01", "2026-07-01"), idx("2026-07-01", "2026-09-01"), idx("2026-02-01", "2026-09-01"), idx("2026-09-01", "2027-01-01")
WO = np.where(ok & (G.league == "WLDs").values)[0]
BASE = [f"{r}_{f}" for r in MAIN for f in MAIN[r]]
R = {"league_now": L_now, "league_shift": C_R}
sv, wv = run(BASE, TRV, VA); st, wt = run(BASE, TR, TE); sw, _ = run(BASE, TR, WO)
R["adjusted_base"] = {"validation": sv, "test_from_sep": st, "worlds": sw, "weights": {k: float(v) for k, v in wt.items()}}
print("adjusted base:", sv, st, sw); print("weights:", wt)
# 3. candidates per slot: swap one slot at a time; choose on validation, confirm on test
R["candidates"] = {}; chosen = list(BASE)
for slot, cands in ALTS.items():
    role = slot.split("_")[0]; rows = []
    for c in cands:
        cols = [x for x in BASE if x != slot] + [f"{role}_{c}"]
        v, wv_ = run(cols, TRV, VA); t, wt_ = run(cols, TR, TE)
        rows.append({"candidate": c, "val_logloss": v["logloss"], "test_logloss": t["logloss"], "weight_val": float(wv_[f"{role}_{c}"]), "weight_full": float(wt_[f"{role}_{c}"])})
    rows.sort(key=lambda r: r["val_logloss"]); R["candidates"][slot] = rows
    print(slot, [(r["candidate"], r["val_logloss"], r["test_logloss"], r["weight_full"]) for r in rows])
json.dump(R, open(os.path.join(OUT, "leaguefit_results.json"), "w"), indent=1, default=float)

# 4. league-adjusted cards (base skills; weights from the adjusted base fit)
W = R["adjusted_base"]["weights"]; RN = {"top": "TOP", "jng": "JGL", "mid": "MID", "bot": "ADC", "sup": "SUP"}
CARD = {"top": {"Laning": ["laning"], "Teamfight": ["teamfight"], "Consistency": ["cons_side", "cons_dur", "cons_steady"]},
        "jng": {"Early game": ["early"], "Objectives": ["objectives"], "Teamfight": ["teamfight"]},
        "mid": {"Laning": ["laning"], "Map impact": ["mapimpact"], "Damage": ["damage"]},
        "bot": {"Laning": ["lane_own", "lane_duo"], "Damage": ["damage"], "Late game": ["lategame"]},
        "sup": {"Playmaking": ["playmaking"], "Map presence": ["mappresence"], "Reliability": ["reliability"]}}
pl_home = PR.sort_values("date").groupby("playerid").teamname.last()
team_home = {}
for r in G.itertuples(): team_home[r.blue_name] = home[r.blue]; team_home[r.red_name] = home[r.red]
rows = []
for r in PN.itertuples():
    role = r.role; Lh = L_now.get(team_home.get(r.team, ""), 0.0); rec = {"name": r.name, "team": r.team, "role": RN[role], "games": r.games, "home": team_home.get(r.team, "")}
    tot = 0.0
    for sk, parts in CARD[role].items():
        vals = [getattr(r, "e_" + p) + C_R[role]["c"] * Lh for p in parts]; ws = [W.get(f"{role}_{p}", 0.0) for p in parts]
        tot += sum(w * v for w, v in zip(ws, vals)); rec[sk] = sum(vals) / len(vals)
    rec["Overall"] = tot; rows.append(rec)
C = pd.DataFrame(rows); pool = C[C.games >= 10].copy()
VAL = [c for c in C.columns if c not in ("name", "team", "role", "games", "home")]
for role in C.role.unique():
    m = C.role == role
    for col in VAL:
        if C.loc[m, col].isna().all(): continue
        ref = pool.loc[pool.role == role, col].dropna().values
        C.loc[m, col + "_card"] = C.loc[m, col].apply(lambda v: round(50 + 49 * float((ref < v).mean())) if pd.notna(v) else np.nan)
names = {n.lower() for n in re.findall(r'\["([^"]+)",\[', open(DATAJS, encoding="utf-8").read())}
C["worlds_roster"] = C.name.str.lower().isin(names)
C.to_csv(os.path.join(OUT, "player_cards_league_adjusted.csv"), index=False)
Wd = C[C.worlds_roster]
for role in ["TOP", "JGL", "MID", "ADC", "SUP"]:
    d = Wd[Wd.role == role].sort_values("Overall", ascending=False)
    cs = [c for c in d.columns if c.endswith("_card") and d[c].notna().any()]
    print("==", role, [c[:-5] for c in cs])
    for x in d.to_dict("records"): print("  %-11s %-6s g%-3d %s" % (x["name"], x["home"], x["games"], [int(x[c]) if pd.notna(x[c]) else None for c in cs]))
