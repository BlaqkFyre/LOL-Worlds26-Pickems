"""Test 1 (13 Nov 2026 AEST; Luke's note 3: comp type helps decide mid and late game): does a draft's scaling score change who wins
fights as the game goes on? Read-only; nothing in the sim changes.
Scaling score: each champion-role's result beyond v1 in games of 35+ minutes minus games under 28 (major games before 1 Sep, pulled toward
0 with k = 30); a draft = sum of its five; the gap = blue minus red. Because the score is built from training games' results, fits on those
games flatter it, so only held-out fights (from 1 Sep, Worlds) judge it.
Fights: the timeline fights table (research/local/sim3/out/tl_fights.csv; kills 20 s+ apart start a new fight); each kill goes to blue or
red. Models for "this kill is blue's" (binomial over the fight's kills), fitted on training fights:
  base        intercept, gold lead (per 1k), v1 log-odds, Baron up (blue minus red), Elder up   (the sim's kill-side terms)
  + flat      + scaling gap
  + by time   + scaling gap x phase (0-13, 14-24, 25-34, 35+)
  + linear    + scaling gap + scaling gap x (minute - 25) / 10
Held-out log loss per kill for each.
usage (repo root): python -I research/sim4/test_scaling_time.py <OE csv> v1_games.csv tl_match.csv tl_fights.csv <out_json>"""
import sys, json
import numpy as np, pandas as pd
CSV, V1, TMF, TFF, OUT = sys.argv[1:6]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]; CUT = "2026-09-01"
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "champion", "result", "gamelength"])
raw = raw[raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01")) & (raw.date < "2026-11-10")].copy(); raw["day"] = raw.date.str[:10]
v1 = pd.read_csv(V1).set_index("gameid"); raw["z"] = raw.gameid.map(v1.z_v1); raw = raw.dropna(subset=["z"]); raw.loc[raw.side == "Red", "z"] *= -1
raw["mins"] = raw.gamelength / 60
pl = raw[raw.position.isin(ROLES)].copy(); pl["res"] = pl.result - 1 / (1 + np.exp(-pl.z))
tr = pl[pl.day < CUT]
a = tr[tr.mins >= 35].groupby(["champion", "position"]).res.agg(["sum", "count"]); b = tr[tr.mins < 28].groupby(["champion", "position"]).res.agg(["sum", "count"])
SC = (a["sum"] / (a["count"] + 30)).sub(b["sum"] / (b["count"] + 30), fill_value=0).to_dict()
pl["scal"] = [SC.get((c, r), 0.0) for c, r in zip(pl.champion, pl.position)]
dr = pl.groupby(["gameid", "side"]).scal.sum().unstack(); GAP = (dr.Blue - dr.Red).to_dict()
tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[tm.gameid != "AMBIGUOUS"].drop_duplicates("gid")
F = pd.read_csv(TFF, dtype={"gid": str}).merge(tm[["gid", "gameid"]], on="gid"); F["gap"] = F.gameid.map(GAP); F = F.dropna(subset=["gap", "gd", "z"])
F["ph"] = pd.cut(F.m, [0, 14, 25, 35, 999], labels=["0-13", "14-24", "25-34", "35+"], right=False)
def X(d, kind):
    base = [np.ones(len(d)), d.gd / 1000, d.z, d.baron, d.elder]
    if kind == "flat": base += [d.gap]
    if kind == "by time": base += [d.gap * (d.ph == p) for p in ["0-13", "14-24", "25-34", "35+"]]
    if kind == "linear": base += [d.gap, d.gap * (d.m - 25) / 10]
    return np.column_stack(base).astype(float)
def fit(Xm, k, n, l2=1e-4):
    bb = np.zeros(Xm.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-Xm @ bb)); H = Xm.T @ (Xm * (n * p * (1 - p))[:, None]) + l2 * np.eye(len(bb)); bb += np.linalg.solve(H, Xm.T @ (k - n * p) - l2 * bb)
    p = 1 / (1 + np.exp(-Xm @ bb)); se = np.sqrt(np.diag(np.linalg.inv(Xm.T @ (Xm * (n * p * (1 - p))[:, None]) + l2 * np.eye(len(bb)))))
    return bb, se
def ll(Xm, bb, k, n):
    p = np.clip(1 / (1 + np.exp(-Xm @ bb)), 1e-9, 1 - 1e-9); return float(-(k * np.log(p) + (n - k) * np.log(1 - p)).sum() / n.sum())
sets = {"train": F.split == "train", "from 1 Sep (held out)": F.split == "test", "Worlds (held out)": F.split == "worlds"}
R = {"fights": {k_: int(m.sum()) for k_, m in sets.items()}, "kills": {k_: int(F[m].n.sum()) for k_, m in sets.items()}, "logloss_per_kill": {}, "coef": {}}
t_ = F[sets["train"]]
for kind in ["base", "flat", "by time", "linear"]:
    bb, se = fit(X(t_, kind), t_.blue.values.astype(float), t_.n.values.astype(float))
    R["logloss_per_kill"][kind] = {k_: round(ll(X(F[m], kind), bb, F[m].blue.values.astype(float), F[m].n.values.astype(float)), 5) for k_, m in sets.items()}
    names = ["intercept", "gold per 1k", "v1", "baron", "elder"] + (["gap"] if kind == "flat" else [f"gap x {p}" for p in ["0-13", "14-24", "25-34", "35+"]] if kind == "by time" else ["gap", "gap x (min-25)/10"] if kind == "linear" else [])
    R["coef"][kind] = {nm: f"{v:+.3f} (se {s:.3f})" for nm, v, s in zip(names, bb, se)}
R["scaling gap sd (games in the fights table)"] = round(float(F.drop_duplicates("gid").gap.std()), 3)
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
