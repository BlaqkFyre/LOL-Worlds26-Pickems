"""Sim session 3 (research only, 10 Nov): fight types and what holds fights in check, fitted for the sim (report 7g).
Luke (10 Nov): kills may build up through fight types: 1v1 (or the 2v2 bot duo), skirmishes (1-3 a side) and team fights (4-5 a side).
Fights: kills 20 s+ apart start a new fight (as s3_events.py). Players involved per side = killers, assisters and victims seen in
the fight's kills (champions), so a fight's type is a lower bound (players present but without a kill, assist or death aren't seen).
Type = the larger side: 1-2 players "small" (duels, 2v2s), 3 "skirmish", 4-5 "teamfight".
Fitted on games before 1 Sep; judged on games from 1 Sep and Worlds (log loss v the current specification):
  count  fights starting in a minute (Poisson) ~ phase, gold lead size, monster up, buff up, draft pace (the current model)
         + what just happened: a fight started last minute, kills in the last 2 minutes
  type   type of each fight (multinomial) ~ phase, gold lead size, monster up, buff up, kills in the last 2 minutes
  size   kills in a fight, by type and stage (0-13, 14-24, 25-34, 35+), training games
usage: python -I s3_fighttypes.py tl_match.csv tl_events.csv tl_gold.csv v1_games.csv comp3_games.csv <out json>"""
import json, sys
import numpy as np
import pandas as pd

TM, TE, TGo, V1, CO, OUT = sys.argv[1:7]
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
v1 = pd.read_csv(V1).set_index("gameid"); M = M[M.gameid.map(v1.z_v1).notna()].copy()
M["split"] = np.where(M.date < "2026-09-01", "train", "test"); M.loc[M.tournament.str.startswith("Worlds"), "split"] = "worlds"
comp = pd.read_csv(CO).set_index("gameid"); M["pace_s"] = M.gameid.map(comp.pace_blue + comp.pace_red).fillna(0)
info = M.set_index("gid")
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)].copy()
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold")]
GD = go.assign(sv=go.value * np.where(go.side == "blue", 1, -1)).groupby(["gid", "minute"]).sv.sum().to_dict()
SP = {"dragon": 300, "grub": 480, "herald": 900, "baron": 1200}
PH = [0, 14, 20, 25, 30, 35, 999]; PHN = ["0-13", "14-19", "20-24", "25-29", "30-34", "35+"]
STG = lambda m: "0-13" if m < 14 else "14-24" if m < 25 else "25-34" if m < 35 else "35+"
TYPES = ["small", "skirmish", "teamfight"]

FT, PAN = [], []
for g, gi in info.iterrows():
    e = ev[ev.gid == g].sort_values("t"); L = int(gi.len) // 60
    k = e[e.type == "kill"]
    # fights and their types
    fights = []
    if len(k):
        grp = np.cumsum(np.r_[True, np.diff(k.t.values) > 20])
        for _, f in k.groupby(grp):
            inv = {"blue": set(), "red": set()}
            for r in f.itertuples():
                o = "red" if r.side == "blue" else "blue"
                inv[r.side].add(r.champ); inv[o].add(r.victim_champ)
                if isinstance(r.assists, str): inv[r.side].update(r.assists.split("|"))
            big = max(len(inv["blue"]), len(inv["red"]))
            typ = "small" if big <= 2 else "skirmish" if big == 3 else "teamfight"
            fights.append((int(f.t.min()), len(f), typ))
    fs = np.array([x[0] for x in fights]); kt = k.t.values
    # monster windows (as s3_rates.py)
    bar = e[e.type == "baron"]; eld = e[(e.type == "dragon") & (e.detail == "elder")]; drag = e[e.type == "dragon"]; up = []
    nxt = SP["dragon"]; soul = {"blue": 0, "red": 0}; elder_mode = False
    for r in drag.itertuples():
        up.append(("elder" if r.detail == "elder" else "dragon", nxt, r.t))
        if r.detail != "elder": soul[r.side] += 1
        if max(soul.values()) >= 4: elder_mode = True
        nxt = r.t + (360 if elder_mode else 300)
    up.append(("elder" if elder_mode else "dragon", nxt, None))
    nb = SP["baron"]
    for r in bar.itertuples(): up.append(("baron", nb, r.t)); nb = r.t + 360
    up.append(("baron", nb, None))
    for m in range(L + 1):
        t0, t1 = 60 * m, 60 * m + 60
        gd = GD.get((g, m), np.nan)
        mon_up = int(any(s_ <= t0 and (tk is None or tk >= t0) for kk, s_, tk in up if kk in ("dragon", "baron", "elder")))
        buff = int(((bar.t <= t0) & (bar.t > t0 - 180)).any() or ((eld.t <= t0) & (eld.t > t0 - 150)).any())
        f_prev = int(((fs >= t0 - 60) & (fs < t0)).any()) if len(fs) else 0
        k_prev2 = int(((kt >= t0 - 120) & (kt < t0)).sum())
        nf = int(((fs >= t0) & (fs < t1)).sum()) if len(fs) else 0
        PAN.append((g, m, gi.split, gd, nf, mon_up, buff, gi.pace_s, f_prev, k_prev2))
        for (ts, n, typ) in fights:
            if t0 <= ts < t1: FT.append((g, m, gi.split, gd, mon_up, buff, k_prev2, f_prev, n, typ))
PAN = pd.DataFrame(PAN, columns=["gid", "m", "split", "gd", "y", "mon_up", "buff", "pace_s", "f_prev", "k_prev2"]).dropna()
FT = pd.DataFrame(FT, columns=["gid", "m", "split", "gd", "mon_up", "buff", "k_prev2", "f_prev", "n", "type"]).dropna()

def dummies(m): return np.c_[tuple((np.searchsorted(PH, m, side="right") - 1 == i).astype(float) for i in range(1, 6))]
def pois_fit(X, y, l2=1.0, it=60):
    b = np.zeros(X.shape[1]); b[0] = np.log(max(y.mean(), 1e-3))
    for _ in range(it):
        mu = np.exp(X @ b); H = X.T @ (X * mu[:, None]) + l2 * np.eye(len(b)); b += np.linalg.solve(H, X.T @ (y - mu) - l2 * b)
    return b
pdev = lambda mu, y: float(np.mean(mu - y * np.log(np.maximum(mu, 1e-9))))
res = {"fights": {s: int((FT.split == s).sum()) for s in ("train", "test", "worlds")}, "minutes": {s: int((PAN.split == s).sum()) for s in ("train", "test", "worlds")}}

# ---- count ----
X0 = lambda d: np.c_[np.ones(len(d)), dummies(d.m.values), (d.gd.abs() / 1000).clip(0, 15), d.mon_up, d.buff, d.pace_s]
X1 = lambda d: np.c_[X0(d), d.f_prev, np.log1p(d.k_prev2)]
tr = PAN[PAN.split == "train"]; b0 = pois_fit(X0(tr), tr.y.values); b1 = pois_fit(X1(tr), tr.y.values)
NC = ["intercept", *[f"phase {p}" for p in PHN[1:]], "per_1k_abs_lead", "monster_up", "buff_up", "pace_style", "fight_last_minute", "log1p_kills_last_2min"]
res["count"] = {"coef": dict(zip(NC, np.round(b1, 4))), "coef_current_spec": dict(zip(NC[:10], np.round(b0, 4))),
                **{s: {"current": round(pdev(np.exp(X0(PAN[PAN.split == s]) @ b0), PAN[PAN.split == s].y.values), 5),
                       "with_recent": round(pdev(np.exp(X1(PAN[PAN.split == s]) @ b1), PAN[PAN.split == s].y.values), 5)} for s in ("train", "test", "worlds")}}
# leftover dispersion with the recent terms, by phase (training)
mu = np.exp(X1(tr) @ b1); r_ = (tr.y.values - mu) ** 2 / mu
res["count"]["dispersion_by_phase"] = {p: round(float(r_[(np.searchsorted(PH, tr.m.values, side="right") - 1) == i].mean()), 3) for i, p in enumerate(PHN)}

# ---- type (multinomial, small = base) ----
XT = lambda d: np.c_[np.ones(len(d)), dummies(d.m.values), (d.gd.abs() / 1000).clip(0, 15), d.mon_up, d.buff, np.log1p(d.k_prev2)]
XT0 = lambda d: np.c_[np.ones(len(d)), dummies(d.m.values)]
def mn_fit(X, yi, K=3, l2=1.0, it=80):
    p_ = X.shape[1]; B = np.zeros((p_, K - 1))
    for _ in range(it):
        Z = np.c_[np.zeros(len(X)), X @ B]; Pm = np.exp(Z - Z.max(1, keepdims=True)); Pm /= Pm.sum(1, keepdims=True)
        Y = np.eye(K)[yi]; G_ = X.T @ (Y - Pm)[:, 1:] - l2 * B
        H = np.zeros(((K - 1) * p_, (K - 1) * p_))
        for a in range(1, K):
            for c in range(1, K):
                w = Pm[:, a] * ((a == c) - Pm[:, c])
                H[(a - 1) * p_:a * p_, (c - 1) * p_:c * p_] = X.T @ (X * w[:, None])
        H += l2 * np.eye(len(H)); B += np.linalg.solve(H, G_.T.reshape(-1)).reshape(K - 1, p_).T
    return B
def mn_ll(X, B, yi):
    Z = np.c_[np.zeros(len(X)), X @ B]; Pm = np.exp(Z - Z.max(1, keepdims=True)); Pm /= Pm.sum(1, keepdims=True)
    return float(-np.mean(np.log(Pm[np.arange(len(yi)), yi])))
FT["yi"] = FT.type.map({t: i for i, t in enumerate(TYPES)})
ftr = FT[FT.split == "train"]; BT = mn_fit(XT(ftr), ftr.yi.values); BT0 = mn_fit(XT0(ftr), ftr.yi.values)
NT = ["intercept", *[f"phase {p}" for p in PHN[1:]], "per_1k_abs_lead", "monster_up", "buff_up", "log1p_kills_last_2min"]
res["type"] = {"coef": {t: dict(zip(NT, np.round(BT[:, i - 1], 4))) for i, t in enumerate(TYPES) if i > 0}, "base": "small",
               **{s: {"phase_only": round(mn_ll(XT0(FT[FT.split == s]), BT0, FT[FT.split == s].yi.values), 4),
                      "full": round(mn_ll(XT(FT[FT.split == s]), BT, FT[FT.split == s].yi.values), 4)} for s in ("train", "test", "worlds")}}
res["type_share"] = {s: {stg: FT[(FT.split == s) & (FT.m.map(STG) == stg)].type.value_counts(normalize=True).reindex(TYPES).fillna(0).round(3).to_dict()
                         for stg in ("0-13", "14-24", "25-34", "35+")} for s in ("train", "test")}
# ---- size by type and stage (training) ----
FT["stg"] = FT.m.map(STG)
res["size_table"] = {}
for t in TYPES:
    res["size_table"][t] = {}
    for stg in ("0-13", "14-24", "25-34", "35+"):
        d = FT[(FT.split == "train") & (FT.type == t) & (FT.stg == stg)]
        if len(d) < 20: d = FT[(FT.split == "train") & (FT.type == t)]
        res["size_table"][t][stg] = {str(int(k_)): round(float(v), 4) for k_, v in d.n.clip(upper=8).value_counts(normalize=True).sort_index().items()}
res["size_mean"] = {s: FT[FT.split == s].groupby(["type", "stg"]).n.mean().round(2).unstack().to_dict() for s in ("train", "test")}
res["kills_share_by_type"] = {s: (FT[FT.split == s].groupby("type").n.sum() / FT[FT.split == s].n.sum()).round(3).to_dict() for s in ("train", "test")}
json.dump(res, open(OUT, "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in res.items() if k not in ("size_table",)}, indent=1, default=float))
