"""Sim session 4 (13 Nov 2026 AEST): a taker model for the game's first dragon on its own.
Why: real games tie the first dragon to bot-lane gold (file, held out from 1 Sep: +0.68 per 1k of bot-duo gold at 10, mid -0.07), but the
sim gives +0.28 and mid +0.41 (research/sim4/test_dragon_botlane.py, seeds by game ID). The sim's taker (research/sim3/s3_events.py) pools
every dragon in one fit and marks the first only with an on/off term, so the first dragon has no lane terms of its own.
Fit (gol.gg timelines matched to the file, the game's first dragon only, games before S3_CUTOFF, default 1 Sep): who takes it (logistic, ridge 2
as s3_events.py) on side (intercept), team gold lead, jungle, mid, bot-duo and top leads at the minute it is taken (per 1k), net kills that
minute, the draft objectives style (blue minus red) and v1. Judged on first dragons from the cutoff and at Worlds against the current pooled
taker (params3.json "taker" with its first-dragon term) and against side only.
usage (repo root): python -I research/sim4/s4_firstdragon.py tl_match.csv tl_events.csv tl_gold.csv v1_games.csv comp3_games.csv params3.json <out_json>"""
import os, sys, json
import numpy as np, pandas as pd
TMF, TEF, TGF, V1, CO, PJ, OUT = sys.argv[1:8]
CUT = os.environ.get("S3_CUTOFF", "2026-09-01"); ROLES = ["top", "jng", "mid", "bot", "sup"]
tm = pd.read_csv(TMF, dtype={"gid": str}); tm = tm[tm.gameid.notna() & (tm.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
v1 = pd.read_csv(V1).set_index("gameid"); tm = tm[tm.gameid.map(v1.z_v1).notna()].copy(); tm["z"] = tm.gameid.map(v1.z_v1)
tm["split"] = np.where(tm.date < CUT, "train", "test"); tm.loc[tm.tournament.str.startswith("Worlds") & (tm.date >= CUT), "split"] = "worlds"
comp = pd.read_csv(CO).set_index("gameid"); tm["obj_d"] = tm.gameid.map(comp.objectives_blue - comp.objectives_red).fillna(0)
info = tm.set_index("gid")
ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[ev.gid.isin(info.index)]
go = pd.read_csv(TGF, dtype={"gid": str}); go = go[go.gid.isin(info.index) & (go.kind == "gold")]
go["sv"] = go.value * np.where(go.side == "blue", 1, -1)
RD = go.pivot_table(index=["gid", "minute"], columns="role", values="sv", aggfunc="sum")
fd = ev[(ev.type == "dragon") & (ev.detail != "elder")].sort_values("t").groupby("gid").head(1).copy(); fd["m"] = fd.t // 60
kills = ev[ev.type == "kill"]
rows = []
for r in fd.itertuples():
    if (r.gid, r.m) not in RD.index: continue
    L = RD.loc[(r.gid, r.m)]; k = kills[(kills.gid == r.gid) & (kills.t <= r.t) & (kills.t > r.t - 60)]
    i = info.loc[r.gid]
    rows.append(dict(gid=r.gid, split=i.split, blue=int(r.side == "blue"), m=r.m, gd=float(L[ROLES].sum()), top=float(L.top), jng=float(L.jng), mid=float(L["mid"]),
                     bot2=float(L.bot + L.sup), net=int((k.side == "blue").sum() - (k.side == "red").sum()), obj=float(i.obj_d), z=float(i.z)))
D = pd.DataFrame(rows)
def logit_fit(X, y, l2=2.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.diag(np.r_[0, np.ones(X.shape[1] - 1)]); b += np.linalg.solve(H, X.T @ (y - p) - l2 * np.r_[0, b[1:]])
    return b
lg = lambda p, y: round(float(-np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))), 4)
FEATS = ["gd", "jng", "mid", "bot2", "top", "netk", "objk"]
D["netk"] = D.net * 1000; D["objk"] = D.obj * 1000
X = lambda q: np.c_[np.ones(len(q)), q[FEATS].values / 1000, q.z.values]
tr = D[D.split == "train"]; b = logit_fit(X(tr), tr.blue.values.astype(float))
T = json.load(open(PJ))["taker"]["dragon"]
def p_now(q):  # the sim's current pooled taker, as the sim calls it for the first dragon
    xb = T["blue_side"] + T["per_v1_logit"] * q.z + T["gd_per_1k"] * q.gd / 1000 + T["jng_per_1k"] * q.jng / 1000 + T["bot2_per_1k"] * q.bot2 / 1000 + T["mid_per_1k"] * q["mid"] / 1000 \
         + T["net60k_per_1k"] * q.net + T["objk_per_1k"] * q.obj + T["first1k_per_1k"]
    return 1 / (1 + np.exp(-xb))
R = {"cutoff": CUT, "first dragons": {s: int((D.split == s).sum()) for s in ("train", "test", "worlds")},
     "coef": dict(zip(["blue_side", "gd_per_1k", "jng_per_1k", "mid_per_1k", "bot2_per_1k", "top_per_1k", "net_kill", "objectives_style", "per_v1_logit"], np.round(b, 4).tolist())),
     "logloss": {}}
for s in ("train", "test", "worlds"):
    q = D[D.split == s]
    if len(q): R["logloss"][s] = {"n": len(q), "first-dragon model": lg(1 / (1 + np.exp(-X(q) @ b)), q.blue.values), "sim now (pooled)": lg(p_now(q), q.blue.values),
                                  "side only": lg(np.full(len(q), tr.blue.mean()), q.blue.values), "blue share": round(float(q.blue.mean()), 3)}
R["minute taken, median"] = float(D.m.median())
# the taker table the sim reads (same keys as params3.json "taker" so the sim's taker() can use it)
R["taker"] = {"blue_side": R["coef"]["blue_side"], "gd_per_1k": R["coef"]["gd_per_1k"], "jng_per_1k": R["coef"]["jng_per_1k"], "mid_per_1k": R["coef"]["mid_per_1k"],
              "bot2_per_1k": R["coef"]["bot2_per_1k"], "top_per_1k": R["coef"]["top_per_1k"], "net60k_per_1k": R["coef"]["net_kill"], "objk_per_1k": R["coef"]["objectives_style"],
              "per_v1_logit": R["coef"]["per_v1_logit"]}
# timing-only version (draft styles change when things happen, not who gets them; Luke 5 Nov): the same fit without the objectives style
FT_ = [f_ for f_ in FEATS if f_ != "objk"]; XT = lambda q: np.c_[np.ones(len(q)), q[FT_].values / 1000, q.z.values]
bt = logit_fit(XT(tr), tr.blue.values.astype(float))
R["coef_timing"] = dict(zip(["blue_side", "gd_per_1k", "jng_per_1k", "mid_per_1k", "bot2_per_1k", "top_per_1k", "net_kill", "per_v1_logit"], np.round(bt, 4).tolist()))
for s in ("train", "test", "worlds"):
    q = D[D.split == s]
    if len(q): R["logloss"][s]["first-dragon model, timing-only"] = lg(1 / (1 + np.exp(-XT(q) @ bt)), q.blue.values)
c_ = R["coef_timing"]
R["taker_timing"] = {"blue_side": c_["blue_side"], "gd_per_1k": c_["gd_per_1k"], "jng_per_1k": c_["jng_per_1k"], "mid_per_1k": c_["mid_per_1k"], "bot2_per_1k": c_["bot2_per_1k"],
                     "top_per_1k": c_["top_per_1k"], "net60k_per_1k": c_["net_kill"], "per_v1_logit": c_["per_v1_logit"]}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps({k_: R[k_] for k_ in ("logloss", "coef_timing")}, indent=1))
