"""Spread work (14 Nov 2026 AEST): base pushes that follow kills. Fit on gol.gg timeline games before 1 Sep; judged on games from 1 Sep and Worlds.
Why (research/sim4/spread_kills_structures.py): real inhibitor towers, inhibitors, nexus towers and nexus fall right after the taking side's
kills (nexus: 99.6% with an own kill in the 60 s before, 91% with 3+); the sim's only about half the time, and 25% of sim games end with no
kill in the last 2 minutes (real 0%). The sim's base push = a fitted chance that a push starts this minute (kills edge this and last minute
as straight lines) and a size drawn from real pushes by "enemy inhibitor already down" only, so how far a push runs (up to the Nexus)
never depends on the kills that opened it.
Rows: as research/sim3/s3_rates.py (a side-minute once that side has an open lane). New inputs: the side's own kills and the enemy's kills,
this minute and last minute, counted separately (a 3-for-3 trade is not a 0 edge for pushing: dead defenders and dead attackers both
matter). Fits (logistic, ridge 1, same as s3_rates.py):
  A  current: base_push_fight_simple inputs (timing-only)
  B  A with own / enemy kills this and last minute instead of the edges
  C  B with "own kills this minute" by "enemy inhibitor down" (a dead defending team matters more once the base is open)
Push size (structures in the push, real pushes under 30 s apart): counted on training pushes by enemy inhibitor down (no / yes) x own kills
in the push's start minute (0 / 1-2 / 3+), with the share of pushes that end the game. Printed for the held-out games too.
usage (repo root): python -I research/sim4/s4_basepush.py tl_match.csv tl_events.csv tl_gold.csv v1_games.csv comp3_games.csv <out_json>"""
import os, sys, json
import numpy as np, pandas as pd

TM, TE, TGo, V1, CO, OUT = sys.argv[1:7]
CUT = os.environ.get("S3_CUTOFF", "2026-09-01")
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
v1 = pd.read_csv(V1).set_index("gameid"); M["z"] = M.gameid.map(v1.z_v1); M = M[M.z.notna()].copy()
M["split"] = np.where(M.date < CUT, "train", "test"); M.loc[M.tournament.str.startswith("Worlds") & (M.date >= CUT), "split"] = "worlds"
comp = pd.read_csv(CO).set_index("gameid"); M["siege_s"] = M.gameid.map(comp.siege_blue + comp.siege_red).fillna(0)
info = M.set_index("gid")
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)].copy()
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold")]
go["sv"] = go.value * np.where(go.side == "blue", 1, -1); GD = go.groupby(["gid", "minute"]).sv.sum().to_dict()

def logit_fit(X, y, l2=1.0, it=60):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(b)); g = X.T @ (y - p) - l2 * b
        b += np.linalg.solve(H, g)
    return b
lg = lambda p, y: float(-np.mean(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1 - 1e-6))))

ROWS, PUSH = [], []
for g, gi in info.iterrows():
    e = ev[ev.gid == g].sort_values("t"); L = int(gi.len) // 60
    kt = e[e.type == "kill"].t.values; ks = e[e.type == "kill"].side.values
    bar = e[e.type == "baron"]; eld = e[(e.type == "dragon") & (e.detail == "elder")]; inh = e[e.type == "inhib"]
    pla = e[e.type == "plate"]
    base = e[(e.type.isin(["inhib", "nexus"])) | ((e.type == "tower") & e.detail.str.contains("NEXUS", na=False))]
    kc = lambda side, a, b: int(((ks == side) & (kt >= a) & (kt < b)).sum())
    pstart = {}
    for sd_ in ("blue", "red"):
        bt = np.sort(base[base.side == sd_].t.values); nex = base[(base.side == sd_) & (base.type == "nexus")].t.values; i = 0; ps_ = []
        while i < len(bt):
            j = i
            while j + 1 < len(bt) and bt[j + 1] - bt[j] <= 30: j += 1
            dn = int(((inh.t < bt[i]) & (inh.t > bt[i] - 300) & (inh.side == sd_)).any()); m0 = int(bt[i] // 60)
            PUSH.append((gi.split, sd_, j - i + 1, dn, kc(sd_, 60 * m0, 60 * m0 + 60), int(((nex >= bt[i]) & (nex <= bt[j])).any()))); ps_.append(bt[i]); i = j + 1
        pstart[sd_] = np.array(ps_)
    for m in range(L + 1):
        t0, t1 = 60 * m, 60 * m + 60; gd = GD.get((g, m), np.nan)
        for side, sg in [("blue", 1), ("red", -1)]:
            opp = "red" if side == "blue" else "blue"
            opn = 0; just = 0
            for lane in ("TOP", "MID", "BOT"):
                lt = pla[(pla.side == side) & (pla.detail == lane)].t.values
                if len(lt) >= 15 and lt[14] < t1: opn += 1; just += int(lt[14] >= t0 - 60)
            if not opn or gd != gd: continue
            ROWS.append(dict(gid=g, m=m, split=gi.split, lead=gd * sg / 1000, z=gi.z * sg,
                             baron=int(((bar.t <= t0) & (bar.t > t0 - 180) & (bar.side == side)).any()), elder=int(((eld.t <= t0) & (eld.t > t0 - 150) & (eld.side == side)).any()),
                             idn=int(((inh.t <= t0) & (inh.t > t0 - 300) & (inh.side == side)).sum()), opn=opn, siege_s=gi.siege_s, just=int(just > 0),
                             prev=int(((base.t >= t0 - 60) & (base.t < t0) & (base.side == side)).any()),
                             ok=kc(side, t0, t1), ek=kc(opp, t0, t1), okp=kc(side, t0 - 60, t0), ekp=kc(opp, t0 - 60, t0),
                             y=int(((pstart[side] >= t0) & (pstart[side] < t1)).any())))
D = pd.DataFrame(ROWS); P_ = pd.DataFrame(PUSH, columns=["split", "side", "size", "down", "ok", "ends"])
base_cols = lambda d: [np.ones(len(d)), (d.m >= 25), (d.m >= 35), d.lead.clip(-15, 15), d.z, d.baron, d.elder, d.idn, d.opn, d.siege_s, d.just, d.prev]
NB = ["intercept", "from 25", "from 35", "per_1k_lead", "per_v1_logit", "baron", "elder", "enemy_inhibs_down", "open_lanes", "siege_style_sum", "lane_just_opened", "base_take_last_minute"]
XA = lambda d: np.c_[tuple(base_cols(d) + [(d.ok - d.ek).clip(-5, 5), (d.okp - d.ekp).clip(-5, 5)])].astype(float)
XB = lambda d: np.c_[tuple(base_cols(d) + [d.ok.clip(0, 5), d.ek.clip(0, 5), d.okp.clip(0, 5), d.ekp.clip(0, 5)])].astype(float)
XC = lambda d: np.c_[XB(d), d.ok.clip(0, 5) * (d.idn > 0)].astype(float)
NA = NB + ["net_kills_this_minute", "net_kills_last_minute"]; NBk = NB + ["own_kills_this_minute", "enemy_kills_this_minute", "own_kills_last_minute", "enemy_kills_last_minute"]
NC = NBk + ["own_kills_this_minute_x_inhib_down"]
tr = D[D.split == "train"]; R = {"cutoff": CUT, "rows": D.split.value_counts().to_dict(), "starts": {}}
fits = {}
for nm, X, names in [("A current inputs", XA, NA), ("B own and enemy kills", XB, NBk), ("C B + own kills x inhib down", XC, NC)]:
    b = logit_fit(X(tr), tr.y.values.astype(float)); fits[nm] = (X, b)
    R["starts"][nm] = {"coef": dict(zip(names, np.round(b, 4).tolist())), **{s: round(lg(1 / (1 + np.exp(-X(D[D.split == s]) @ b)), D[D.split == s].y.values), 5) for s in ("train", "test", "worlds")}}
# real push-start rate by own kills this minute (0 / 1 / 2 / 3+) x enemy inhibitor down, training games
D["okg"] = D.ok.clip(upper=3); tr = D[D.split == "train"]; R["real start rate by own kills this minute"] = {
    f"{'inhib down' if dn else 'no inhib down'}": {f"{k}{'+' if k == 3 else ''}": [round(float(q.y.mean()), 3), len(q)] for k, q in d.groupby("okg")} for dn, d in tr.groupby(tr.idn > 0)}
D["quiet"] = (D.ok + D.ek + D.okp + D.ekp) == 0
R["share of push starts with no kill either side this or last minute (train / test)"] = [round(float(D[(D.split == s) & (D.y == 1)].quiet.mean()), 3) for s in ("train", "test")]
# push size by state x own kills in the start minute
P_["kg"] = np.select([P_.ok == 0, P_.ok <= 2], ["0", "1-2"], "3+")
R["push size"] = {}
for s in ("train", "test"):
    q = P_[P_.split == s]
    R["push size"][s] = {f"{'inhib down' if dn else 'no inhib down'}|{kg}": {"n": len(d), "size": {str(k): round(float(v), 3) for k, v in d["size"].clip(upper=6).value_counts(normalize=True).sort_index().items()},
                                                                               "mean": round(float(d["size"].mean()), 2), "ends": round(float(d.ends.mean()), 3)} for (dn, kg), d in q.groupby(["down", "kg"])}
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if k != "push size"}, indent=1)); print(json.dumps(R["push size"]["train"], indent=1))
