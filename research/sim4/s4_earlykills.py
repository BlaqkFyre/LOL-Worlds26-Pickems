"""Sim session 4 (13 Nov 2026 AEST): lane-aware early kills, fitted on the gol.gg timelines (Luke's feedback on the example
play-by-play: early kills must follow the lanes; research/sim4/early_kill_roles.py measured the gap: before 5:00 real kills are
54% same-lane and 7% laner-v-laner across lanes, the sim's 19% and 37%).
Kills before 15:00, both roles matched through the file's rows; fights = kills 20 s+ apart start a new fight (as s3_fighttypes.py);
windows 0-4, 5-9, 10-14 (minutes).
A  pair   which killer role (killing side) and victim role (dying side) a kill is: conditional logit over the pairs still alive in
          the fight (roles already killed in this fight are out), with
            pair terms a[k,v] (25) + window terms d[w,k,v] (75), ridge (a 0.1, d 2.0)
            lean on each role's expected lead before the game (lane-level fit: e0 + z_pre * z), killer (own lead) and victim (own lead)
            follow-on kills (2nd+ in a fight): killer / victim role already in the fight on its side; killer / victim lane already in it
B  assist each alive teammate of the killer: logistic on window, role, same lane as the killer, same lane as the victim, already in
          the fight (2nd+ kills)
Fitted on games before S3_CUTOFF (default 1 Sep); held-out log loss from the cutoff and at Worlds, against what the sim does now
(killer and victim drawn separately with the lane-level fit's role choice; assists at a flat rate per role).
usage (repo root): python -I research/sim4/s4_earlykills.py <OE csv> tl_match.csv tl_events.csv v1_games.csv <ll_dir> params3.json <out_json>"""
import os, sys, json
import numpy as np, pandas as pd
CSV, TMF, TEF, V1, LLD, PJ, OUT = sys.argv[1:8]
CUT = os.environ.get("S3_CUTOFF", "2026-09-01")
ROLES = ["top", "jng", "mid", "bot", "sup"]; LANE = [0, -1, 1, 2, 2]  # lane id per role (jungle none)
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "champion"])
pl = raw[raw.position.isin(ROLES)]
role_of = {(g, s.lower(), key(c)): ROLES.index(p) for g, s, c, p in zip(pl.gameid, pl.side, pl.champion, pl.position)}
lg = pl.drop_duplicates("gameid").set_index("gameid").league
tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[tm.gameid != "AMBIGUOUS"].drop_duplicates("gameid")
ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[(ev.type == "kill") & (ev.t < 900) & ev.gid.isin(tm.gid)].merge(tm[["gid", "gameid", "date"]], on="gid")
v1 = pd.read_csv(V1).set_index("gameid"); fit = json.load(open(os.path.join(LLD, "lanelevel_fit.json")))
lf = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
zp = np.array([fit["coef_pregame"][r]["z"] for r in ROLES])
def exp_lead(g):  # blue's expected lead per role before the game, gold
    if g not in lf.index or g not in v1.index or pd.isna(v1.z_v1.get(g)): return None
    e0 = np.array([lf.at[g, f"e0_{r}"] for r in ROLES], float); return e0 + zp * float(v1.z_v1[g])
P = json.load(open(PJ)); ks_, ap_ = P["role_kill_share"], P["role_assist_per_team_kill"]
flat_ap = np.array([min(0.95, ap_[r] / max(1e-6, 1 - ks_[r])) for r in ROLES])
KR = fit["kill_role"]

# ---- build observations ----
A_obs, B_obs = [], []
for g, d in ev.sort_values(["gameid", "t"]).groupby("gameid"):
    E = exp_lead(g)
    if E is None: continue
    split = "train" if str(d.date.iloc[0]) < CUT else "test"; league = lg.get(g, "")
    grp = np.cumsum(np.r_[True, np.diff(d.t.values) > 20])
    for _, f in d.groupby(grp):
        dead = {"blue": set(), "red": set()}; inv = {"blue": set(), "red": set()}; lanes = set(); j = 0
        for e in f.itertuples():
            o = "red" if e.side == "blue" else "blue"
            k = role_of.get((g, e.side, key(e.champ))); v = role_of.get((g, o, key(e.victim_champ)))
            asr = [role_of.get((g, e.side, key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
            asr = [a for a in asr if a is not None]
            if k is None or v is None or k in dead[e.side] or v in dead[o]: j += 1; continue
            w = 0 if e.t < 300 else 1 if e.t < 600 else 2; sg = 1 if e.side == "blue" else -1
            alive_k = [i for i in range(5) if i not in dead[e.side]]; alive_v = [i for i in range(5) if i not in dead[o]]
            A_obs.append(dict(g=g, split=split, league=league, w=w, k=k, v=v, ak=alive_k, av=alive_v, xk=sg * E / 1000, xv=-sg * E / 1000,
                              follow=int(j > 0), invk=set(inv[e.side]), invv=set(inv[o]), lanes=set(lanes)))
            for r in alive_k:
                if r == k: continue
                B_obs.append((split, league, w, r, int(LANE[r] >= 0 and LANE[r] == LANE[k]), int(LANE[r] >= 0 and LANE[r] == LANE[v]), int(j > 0 and r in inv[e.side]), int(r in asr), flat_ap[r]))
            dead[o].add(v); inv[e.side].update([k] + asr); inv[o].add(v)
            for r in [k, v] + asr:
                if LANE[r] >= 0: lanes.add(LANE[r])
            j += 1

# ---- A: pair model ----
NP = 25; NPAR = NP + 3 * NP + 2 + 4
def feats(o):
    """rows = candidate pairs (alive), columns = parameters; returns X, index of the chosen row"""
    rows, ch = [], None
    for k in o["ak"]:
        for v in o["av"]:
            x = np.zeros(NPAR); p = k * 5 + v
            x[p] = 1; x[NP + o["w"] * NP + p] = 1
            x[4 * NP] = o["xk"][k]; x[4 * NP + 1] = o["xv"][v]
            if o["follow"]:
                x[4 * NP + 2] = k in o["invk"]; x[4 * NP + 3] = v in o["invv"]
                x[4 * NP + 4] = LANE[k] >= 0 and LANE[k] in o["lanes"]; x[4 * NP + 5] = LANE[v] >= 0 and LANE[v] in o["lanes"]
            if k == o["k"] and v == o["v"]: ch = len(rows)
            rows.append(x)
    return np.array(rows), ch
XA = [feats(o) for o in A_obs]
pen = np.r_[np.full(NP, 0.1), np.full(3 * NP, 2.0), np.full(6, 0.01)]
tr = [i for i, o in enumerate(A_obs) if o["split"] == "train"]
b = np.zeros(NPAR)
for it in range(50):
    G = -pen * b; H = np.diag(pen.copy())
    for i in tr:
        X, c = XA[i]; u = X @ b; p = np.exp(u - u.max()); p /= p.sum(); mu = p @ X
        G += X[c] - mu; H += (X * p[:, None]).T @ X - np.outer(mu, mu)
    s = np.linalg.solve(H, G); b += s
    if np.abs(s).max() < 1e-7: break
def ll_new(i):
    X, c = XA[i]; u = X @ b; p = np.exp(u - u.max()); p /= p.sum(); return -np.log(p[c])
def ll_old(i):  # the sim now: killer and victim drawn separately (lane-level role choice with lean)
    o = A_obs[i]; ak = np.array(KR["killer"]["role_intercepts"]); av = np.array(KR["victim"]["role_intercepts"])
    lk, lv = KR["killer"]["lean_per_1k_expected_lead"], KR["victim"]["lean_per_1k_expected_lead"]
    uk = np.array([ak[r] + lk * o["xk"][r] for r in o["ak"]]); pk = np.exp(uk - uk.max()); pk /= pk.sum()
    uv = np.array([av[r] + lv * o["xv"][r] for r in o["av"]]); pv = np.exp(uv - uv.max()); pv /= pv.sum()
    return -np.log(pk[o["ak"].index(o["k"])] * pv[o["av"].index(o["v"])])
sets = {"train": lambda o: o["split"] == "train", "from cutoff": lambda o: o["split"] == "test", "Worlds (from cutoff)": lambda o: o["split"] == "test" and o["league"] == "WLDs"}
res = {"cutoff": CUT, "kills": {s: int(sum(f(o) for o in A_obs)) for s, f in sets.items()}}
res["pair_logloss"] = {s: {"sim now": round(float(np.mean([ll_old(i) for i, o in enumerate(A_obs) if f(o)])), 4),
                           "new": round(float(np.mean([ll_new(i) for i, o in enumerate(A_obs) if f(o)])), 4),
                           "by window (now, new)": {w: [round(float(np.mean([ll_old(i) for i, o in enumerate(A_obs) if f(o) and o["w"] == w])), 4),
                                                        round(float(np.mean([ll_new(i) for i, o in enumerate(A_obs) if f(o) and o["w"] == w])), 4)] for w in range(3)}}
                       for s, f in sets.items()}
pair_names = [f"{ROLES[k]}>{ROLES[v]}" for k in range(5) for v in range(5)]
res["pair"] = {"pair": dict(zip(pair_names, np.round(b[:NP], 4).tolist())),
               "window": {wn: dict(zip(pair_names, np.round(b[NP + w * NP:NP + (w + 1) * NP], 4).tolist())) for w, wn in enumerate(["0-4", "5-9", "10-14"])},
               "lean_killer_per_1k": round(float(b[4 * NP]), 4), "lean_victim_per_1k": round(float(b[4 * NP + 1]), 4),
               "follow_killer_in_fight": round(float(b[4 * NP + 2]), 4), "follow_victim_in_fight": round(float(b[4 * NP + 3]), 4),
               "follow_killer_lane_in_fight": round(float(b[4 * NP + 4]), 4), "follow_victim_lane_in_fight": round(float(b[4 * NP + 5]), 4)}

# ---- B: assists ----
B = pd.DataFrame(B_obs, columns=["split", "league", "w", "r", "same_k", "same_v", "inv", "y", "flat"])
def XB(d): return np.c_[(d.w == 0), (d.w == 1), (d.w == 2), *[(d.r == i) for i in range(1, 5)], d.same_k, d.same_v, d.inv].astype(float)
bt = B[B.split == "train"]; X = XB(bt); y = bt.y.values; bb = np.zeros(X.shape[1]); l2 = 0.5
for _ in range(60):
    p = 1 / (1 + np.exp(-X @ bb)); H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(bb)); bb += np.linalg.solve(H, X.T @ (y - p) - l2 * bb)
lb = lambda p, y: float(-np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1))))
bsets = {"train": B.split == "train", "from cutoff": B.split == "test", "Worlds (from cutoff)": (B.split == "test") & (B.league == "WLDs")}
res["assist_logloss"] = {s: {"sim now": round(lb(B.flat[m].values, B.y[m].values), 4), "new": round(lb(1 / (1 + np.exp(-XB(B[m]) @ bb)), B.y[m].values), 4)} for s, m in bsets.items() if m.any()}
res["assist"] = dict(zip(["window 0-4", "window 5-9", "window 10-14", "role jng", "role mid", "role bot", "role sup", "same_lane_as_killer", "same_lane_as_victim", "already_in_fight"],
                         np.round(bb, 4).tolist()))
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("pair",)}, indent=1)); print({k: v for k, v in res["pair"].items() if k not in ("pair", "window")})
