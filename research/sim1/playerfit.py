"""Sim session 1, step 3b: do player skills add to the team ratings? Fit the overall weights; ADC Positioning v Late game.
Team pre-game logit: the step-2 team model refitted day by day (90-day half-life, ridge 2, temperature 1.125, no extra Worlds weight).
Player part: for each role and skill, (blue player's pre-game estimate - red player's), with fitted weights (ridge).
Choices (ADC skill, player ridge) on validation Jul-Aug; final weights on Feb-Aug; tests on 1 Sep onwards and on Worlds.
usage: python -I playerfit.py games.csv gfeat.csv pnow.csv data.js out_dir"""
import json, os, re, sys
import numpy as np
import pandas as pd

G = pd.read_csv(sys.argv[1]); GF = pd.read_csv(sys.argv[2]); PN = pd.read_csv(sys.argv[3]); DATAJS = sys.argv[4]; OUT = sys.argv[5]
G["t"] = pd.to_datetime(G.date); G["day"] = G.t.dt.strftime("%Y-%m-%d")
HL, LAM, TEMP = 90.0, 2.0, 1.125
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

# 1. team pre-game logit, refitted per day
tl = np.full(len(G), np.nan)
pen_t = np.r_[np.full(NT, LAM), np.full(NL, 0.1), 0.0]
for d in sorted(G.day.unique()):
    tr = np.where(G.day < d)[0]; te = np.where(G.day == d)[0]
    if len(tr) < 150: continue
    w = 0.5 ** (((np.datetime64(d) - G.t.values[tr]) / np.timedelta64(1, "D")) / HL)
    b = logit_fit(X[tr], Y[tr], w, pen_t)
    tl[te] = (X[te] @ b) / TEMP

# 2. player differences per game
SK = {"top": ["laning", "teamfight", "cons_side", "cons_dur", "cons_steady"], "jng": ["early", "objectives", "teamfight"],
      "mid": ["laning", "mapimpact", "damage"], "bot": ["lane_own", "lane_duo", "damage", "positioning", "lategame"],
      "sup": ["playmaking", "mappresence", "reliability"]}
COLS = [f"{r}_{s}" for r, ss in SK.items() for s in ss]
D = pd.DataFrame(0.0, index=G.gameid, columns=COLS)
for (gid, side, pos), grp in GF.groupby(["gameid", "side", "position"]):
    sg = 1 if side == "Blue" else -1
    for s in SK[pos]:
        D.loc[gid, f"{pos}_{s}"] += sg * float(grp["e_" + s].iloc[0])
D = D.loc[G.gameid].values
ok = ~np.isnan(tl)

def score(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4),
            "brier": round(float(np.mean((p - y) ** 2)), 4), "fav_won": round(float(np.mean((p > 0.5) == (y == 1))), 3)}

def model(cols, use_team, idx_tr, lam_p):
    ci = [COLS.index(c) for c in cols]
    A = np.c_[tl if use_team else np.ones(len(G)), D[:, ci]]
    pen = np.r_[0.0, np.full(len(ci), lam_p)]
    b = logit_fit(A[idx_tr], Y[idx_tr], np.ones(len(idx_tr)), pen)
    return b, A

def run(cols, use_team, tr, te, lam_p):
    b, A = model(cols, use_team, tr, lam_p)
    return score(1 / (1 + np.exp(-(A[te] @ b))), Y[te]), b

R = {}
idx = lambda a, z: np.where(ok & (G.t >= pd.Timestamp(a)) & (G.t < pd.Timestamp(z)))[0]
TR_V, VA = idx("2026-02-01", "2026-07-01"), idx("2026-07-01", "2026-09-01")
TR, TE = idx("2026-02-01", "2026-09-01"), idx("2026-09-01", "2027-01-01")
WO = np.where(ok & (G.league == "WLDs").values)[0]
base = [c for c in COLS if c not in ("bot_positioning", "bot_lategame")]
# choose player ridge and ADC skill on validation
choice = []
for lam_p in (1, 5, 20, 80, 160, 320, 640):
    for adc in (["bot_positioning"], ["bot_lategame"], ["bot_positioning", "bot_lategame"], []):
        s, _ = run(base + adc, True, TR_V, VA, lam_p); choice.append((s["logloss"], lam_p, "+".join(a.split("_")[1] for a in adc) or "neither", s))
choice.sort(key=lambda x: x[0]); R["validation_grid"] = [[c[1], c[2], c[0]] for c in choice]
_, LP, ADC, _ = choice[0]
adc_cols = {"positioning": ["bot_positioning"], "lategame": ["bot_lategame"], "positioning+lategame": ["bot_positioning", "bot_lategame"], "neither": []}[ADC]
FINAL = base + adc_cols; R["chosen"] = {"player_ridge": LP, "adc_third_skill": ADC}
# ADC comparison at the chosen ridge, on validation and on test
R["adc_compare"] = {name: {"validation": run(base + cols_, True, TR_V, VA, LP)[0], "test_from_sep": run(base + cols_, True, TR, TE, LP)[0]}
                    for name, cols_ in (("positioning", ["bot_positioning"]), ("lategame", ["bot_lategame"]), ("both", ["bot_positioning", "bot_lategame"]), ("neither", []))}
# main comparison
for name, cols_, team in (("team_only", [], True), ("players_only", FINAL, False), ("team_plus_players", FINAL, True)):
    R[name] = {"validation": run(cols_, team, TR_V, VA, LP)[0], "test_from_sep": run(cols_, team, TR, TE, LP)[0], "worlds": run(cols_, team, TR, WO, LP)[0]}
b, _ = model(FINAL, True, TR, LP)
R["weights"] = {"team_logit_scale": round(float(b[0]), 3), **{c: round(float(v), 3) for c, v in zip(FINAL, b[1:])}}
json.dump(R, open(os.path.join(OUT, "playerfit_results.json"), "w"), indent=1)
print("chosen", R["chosen"]); print("validation grid (top 6)", R["validation_grid"][:6])
for k in ("team_only", "players_only", "team_plus_players"): print(k, json.dumps(R[k]))
print("adc", json.dumps(R["adc_compare"])); print("weights", json.dumps(R["weights"]))

# 3. cards now: skill and overall per player; percentile within role among players with 10+ games
W = R["weights"]; ROLE_NAME = {"top": "TOP", "jng": "JGL", "mid": "MID", "bot": "ADC", "sup": "SUP"}
CARD = {"top": {"Laning": ["laning"], "Teamfight": ["teamfight"], "Consistency": ["cons_side", "cons_dur", "cons_steady"]},
        "jng": {"Early game": ["early"], "Objectives": ["objectives"], "Teamfight": ["teamfight"]},
        "mid": {"Laning": ["laning"], "Map impact": ["mapimpact"], "Damage": ["damage"]},
        "bot": {"Laning": ["lane_own", "lane_duo"], "Damage": ["damage"], ADC.split("+")[0].capitalize() if ADC != "neither" else "Positioning": [a.split("_")[1] for a in adc_cols] or ["positioning"]},
        "sup": {"Playmaking": ["playmaking"], "Map presence": ["mappresence"], "Reliability": ["reliability"]}}
rows = []
for r in PN.itertuples():
    role = r.role; rec = {"name": r.name, "team": r.team, "role": ROLE_NAME[role], "games": r.games, "league": r.league}
    tot = 0.0
    for skill, parts in CARD[role].items():
        ws = [W.get(f"{role}_{p}", 0.0) for p in parts]; vals = [getattr(r, "e_" + p) for p in parts]
        contrib = sum(w * v for w, v in zip(ws, vals)); tot += contrib
        rec[skill] = sum(vals) / len(vals) if sum(abs(w) for w in ws) == 0 else contrib / sum(abs(w) for w in ws)
    rec["overall_logodds"] = tot; rows.append(rec)
C = pd.DataFrame(rows)
pool = C[C.games >= 10].copy()
VALCOLS = [c for c in C.columns if c not in ("name", "team", "role", "games", "league")]
for role in C.role.unique():
    m = C.role == role
    for col in VALCOLS:
        if C.loc[m, col].isna().all(): continue
        ref = pool.loc[pool.role == role, col].dropna().values
        C.loc[m, col + "_card"] = C.loc[m, col].apply(lambda v: round(50 + 49 * float((ref < v).mean())) if pd.notna(v) else np.nan)
names = {n.lower() for n in re.findall(r'\["([^"]+)",\[', open(DATAJS, encoding="utf-8").read())}
C["worlds_roster"] = C.name.str.lower().isin(names)
C.sort_values(["role", "overall_logodds"], ascending=[True, False]).to_csv(os.path.join(OUT, "player_cards_now.csv"), index=False)
print("worlds roster players found:", int(C.worlds_roster.sum()), "of", len(names))
