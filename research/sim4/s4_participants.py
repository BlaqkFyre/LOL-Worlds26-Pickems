"""Sim session 4 (13 Nov 2026 AEST): who takes part in each fight, fitted on the gol.gg timelines.
Luke (13 Nov): an assist only ever goes to a player who was in the fight (an assist means the player contributed; a kill means they
landed the killing blow), and solo kills should happen as often as in real games. So each fight first draws who is in it, then kills
and assists happen only among those players.
Fights: kills 20 s+ apart start a new fight (as s3_fighttypes.py), every kill's killer, victim and assisters matched to roles.
Players in a fight per side = the killers, assisters and victims seen in it (all a timeline can show). Side A = the side that gets the
fight's first kill. Windows by the fight's start: 0-4, 5-9, 10-14, 15-24, 25+ min; kills in the fight: 1, 2, 3+.
A  players   joint model of side A's set and side B's set (each a non-empty subset of the five roles; all 31 x 31 pairs enumerated):
             each role's own term per window x kills (A and B apart), a term per pair of roles on the same side, a term per role on A
             with each role on B (so a top laner's fight tends to have the enemy top laner in it). Ridge 1 (role terms 0.1).
B  kill      who lands each kill among the killing side's players still alive in the fight, and who dies among the other side's:
             role terms per window + lean on the role's own expected lead before the game (kills before 15:00 only)
C  assist    each other living player of the killing side in the fight: chance of an assist by window and role, same lane as the
             killer, same lane as the victim
Fitted on games before S3_CUTOFF (default 1 Sep); log loss on held-out games (from the cutoff, Worlds) is reported for B and C against
the sim's current draws (killer and victim from all five; assists at a flat rate from all living teammates).
usage (repo root): python -I research/sim4/s4_participants.py <OE csv> tl_match.csv tl_events.csv v1_games.csv <ll_dir> params3.json <out_json>"""
import os, sys, json, itertools
import numpy as np, pandas as pd
CSV, TMF, TEF, V1, LLD, PJ, OUT = sys.argv[1:8]
CUT = os.environ.get("S3_CUTOFF", "2026-09-01")
ROLES = ["top", "jng", "mid", "bot", "sup"]; LANE = [0, -1, 1, 2, 2]
WIN = lambda t: 0 if t < 300 else 1 if t < 600 else 2 if t < 900 else 3 if t < 1500 else 4
WN = ["0-4", "5-9", "10-14", "15-24", "25+"]; NB = lambda n: 0 if n == 1 else 1 if n == 2 else 2; NBN = ["1", "2", "3+"]
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "side", "position", "champion"]); pl = raw[raw.position.isin(ROLES)]
role_of = {(g, s.lower(), key(c)): ROLES.index(p) for g, s, c, p in zip(pl.gameid, pl.side, pl.champion, pl.position)}
lg = pl.drop_duplicates("gameid").set_index("gameid").league
tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[tm.gameid != "AMBIGUOUS"].drop_duplicates("gameid")
ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[(ev.type == "kill") & ev.gid.isin(tm.gid)].merge(tm[["gid", "gameid", "date"]], on="gid")
v1 = pd.read_csv(V1).set_index("gameid"); fit = json.load(open(os.path.join(LLD, "lanelevel_fit.json")))
lf = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid"); zp = np.array([fit["coef_pregame"][r]["z"] for r in ROLES])
P = json.load(open(PJ)); ks_, ap_ = P["role_kill_share"], P["role_assist_per_team_kill"]
flat_ap = np.array([min(0.95, ap_[r] / max(1e-6, 1 - ks_[r])) for r in ROLES]); kw = np.array([ks_[r] for r in ROLES]); kw /= kw.sum()
dw = np.array([P["role_death_share"][r] for r in ROLES]); dw /= dw.sum()
def exp_lead(g):
    if g not in lf.index or g not in v1.index or pd.isna(v1.z_v1.get(g)): return np.zeros(5)
    return np.array([lf.at[g, f"e0_{r}"] for r in ROLES], float) + zp * float(v1.z_v1[g])

# ---------- fights ----------
F = []
for g, d in ev.sort_values(["gameid", "t"]).groupby("gameid"):
    split = "train" if str(d.date.iloc[0]) < CUT else "test"; league = lg.get(g, ""); E = exp_lead(g)
    grp = np.cumsum(np.r_[True, np.diff(d.t.values) > 20])
    for _, f in d.groupby(grp):
        kills, ok = [], True
        for e in f.itertuples():
            o = "red" if e.side == "blue" else "blue"
            k = role_of.get((g, e.side, key(e.champ))); v = role_of.get((g, o, key(e.victim_champ)))
            a = [role_of.get((g, e.side, key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
            if k is None or v is None or any(x is None for x in a): ok = False; break
            kills.append((int(e.t), e.side, k, v, sorted(set(a) - {k})))
        if not ok: continue
        A = kills[0][1]; sets = {"blue": set(), "red": set()}
        for t, s, k, v, a in kills:
            o = "red" if s == "blue" else "blue"; sets[s].update([k, *a]); sets[o].add(v)
        B = "red" if A == "blue" else "blue"
        F.append(dict(g=g, split=split, league=league, w=WIN(kills[0][0]), nb=NB(len(kills)), A=A, SA=frozenset(sets[A]), SB=frozenset(sets[B]), kills=kills, E=E))
res = {"cutoff": CUT, "fights": {s: sum(f["split"] == s for f in F) for s in ("train", "test")}}

# ---------- A: joint players model ----------
SUBS = [frozenset(c) for n in range(1, 6) for c in itertools.combinations(range(5), n)]; SI = {s: i for i, s in enumerate(SUBS)}; NS = len(SUBS)
NG = 5 * 3; PAIRS = list(itertools.combinations(range(5), 2))
NL = len(PAIRS) + 25; LWN = ["0-4", "5-9", "10-14", "15+"]  # links between players vary by window (0-4, 5-9, 10-14, 15+)
NPA = 2 * NG * 5 + 4 * NL
def cfg_feats():
    """features of every (A set, B set) pair, per group block offset applied later: returns base part (pairs, cross) and role indicators"""
    a_ind = np.array([[r in s for r in range(5)] for s in SUBS], float)
    pair_ind = np.array([[(i in s and j in s) for i, j in PAIRS] for s in SUBS], float)
    cross = np.einsum("ai,bj->abij", a_ind, a_ind).reshape(NS, NS, 25)
    within = pair_ind[:, None, :] + pair_ind[None, :, :]
    return a_ind, np.concatenate([within, cross], axis=2)  # (NS, NS, 10 + 25)
A_IND, BASE = cfg_feats()
def group_X(gi):
    """full feature tensor (NS*NS, NPA) for group gi"""
    X = np.zeros((NS, NS, NPA)); off_a = gi * 5; off_b = NG * 5 + gi * 5
    X[:, :, off_a:off_a + 5] = A_IND[:, None, :]; X[:, :, off_b:off_b + 5] = A_IND[None, :, :]; lw = min(gi // 3, 3); X[:, :, 2 * NG * 5 + lw * NL:2 * NG * 5 + (lw + 1) * NL] = BASE
    return X.reshape(NS * NS, NPA)
GX = [group_X(gi) for gi in range(NG)]
def fitA(fs, iters=60):
    cnt = np.zeros((NG, NS * NS))
    for f in fs: cnt[f["w"] * 3 + f["nb"], SI[f["SA"]] * NS + SI[f["SB"]]] += 1
    pen = np.r_[np.full(2 * NG * 5, 0.1), np.full(4 * NL, 1.0)]; b = np.zeros(NPA)
    def obj(b_):  # penalised log likelihood
        o = -0.5 * float((pen * b_ * b_).sum())
        for gi in range(NG):
            n = cnt[gi].sum()
            if n: u = GX[gi] @ b_; o += float(cnt[gi] @ u) - n * (u.max() + np.log(np.exp(u - u.max()).sum()))
        return o
    cur = obj(b)
    for _ in range(iters):
        G = -pen * b; H = np.diag(pen.copy())
        for gi in range(NG):
            n = cnt[gi].sum()
            if not n: continue
            u = GX[gi] @ b; p = np.exp(u - u.max()); p /= p.sum(); mu = p @ GX[gi]
            G += cnt[gi] @ GX[gi] - n * mu; H += n * ((GX[gi] * p[:, None]).T @ GX[gi] - np.outer(mu, mu))
        s = np.linalg.lstsq(H, G, rcond=None)[0]; step = 1.0
        while step > 1e-6:  # damped Newton: take the largest step (1, 1/2, ...) that improves the fit
            nb_ = b + step * s; new = obj(nb_)
            if new >= cur: break
            step /= 2
        if step <= 1e-6: break
        b, cur = nb_, new
        if np.abs(step * s).max() < 1e-7: break
    return b
def llA(b, fs):
    out = []
    for f in fs:
        gi = f["w"] * 3 + f["nb"]; u = GX[gi] @ b; lse = u.max() + np.log(np.exp(u - u.max()).sum())
        out.append(lse - u[SI[f["SA"]] * NS + SI[f["SB"]]])
    return float(np.mean(out))
tr = [f for f in F if f["split"] == "train"]; te = [f for f in F if f["split"] == "test"]; wo = [f for f in te if f["league"] == "WLDs"]
bA = fitA(tr)
# reference: the same model with role terms only (no pair or cross terms), to show what the links between players add
res["players_logloss"] = {"train": round(llA(bA, tr), 4), "from cutoff": round(llA(bA, te), 4) if te else None, "Worlds": round(llA(bA, wo), 4) if wo else None,
                          "note": "joint log loss of the two sets (31 x 31 choices; uniform would be 6.87)"}
res["players"] = {"role_A": {f"{WN[w]}|{NBN[n]}": dict(zip(ROLES, np.round(bA[(w * 3 + n) * 5:(w * 3 + n) * 5 + 5], 4).tolist())) for w in range(5) for n in range(3)},
                  "role_B": {f"{WN[w]}|{NBN[n]}": dict(zip(ROLES, np.round(bA[NG * 5 + (w * 3 + n) * 5:NG * 5 + (w * 3 + n) * 5 + 5], 4).tolist())) for w in range(5) for n in range(3)},
                  "same_side_pair": {lwn: {f"{ROLES[i]}+{ROLES[j]}": round(float(bA[2 * NG * 5 + lw * NL + q]), 4) for q, (i, j) in enumerate(PAIRS)} for lw, lwn in enumerate(LWN)},
                  "across": {lwn: {f"{ROLES[i]}~{ROLES[j]}": round(float(bA[2 * NG * 5 + lw * NL + len(PAIRS) + i * 5 + j]), 4) for i in range(5) for j in range(5)} for lw, lwn in enumerate(LWN)}}

# ---------- B: killer and victim among the players in the fight; C: assists ----------
KB, CB = [], []
for f in F:
    dead = {"blue": set(), "red": set()}; inn = {f["A"]: set(f["SA"]), ("red" if f["A"] == "blue" else "blue"): set(f["SB"])}; seen = {"blue": set(), "red": set()}
    for t, s, k, v, a in f["kills"]:
        o = "red" if s == "blue" else "blue"; sg = 1 if s == "blue" else -1
        ck = [r for r in inn[s] if r not in dead[s]]; cv = [r for r in inn[o] if r not in dead[o]]
        if k in ck and v in cv:
            KB.append((f["split"], f["league"], WIN(t), t < 900, ck, k, sg * f["E"] / 1000, cv, v, -sg * f["E"] / 1000))
        for r in ck:
            if r == k: continue
            CB.append((f["split"], f["league"], WIN(t), r, int(LANE[r] >= 0 and LANE[r] == LANE[k]), int(LANE[r] >= 0 and LANE[r] == LANE[v]), int(r in a), flat_ap[r],
                       f["nb"], int(r in seen[s])))
        dead[o].add(v); seen[s].update([k, *a])
def choice_fit(rows, who):
    """role terms per window (top = 0) + lean on own expected lead before 15:00"""
    npar = 5 * 4 + 1; b = np.zeros(npar); pen = np.full(npar, 0.5); pen[-1] = 0.01
    def X(r):
        cands = r[4] if who == "k" else r[7]; lead = r[6] if who == "k" else r[9]
        M = np.zeros((len(cands), npar))
        for i, c in enumerate(cands):
            if c: M[i, r[2] * 4 + c - 1] = 1
            M[i, -1] = lead[c] * r[3]
        return M, cands.index(r[5] if who == "k" else r[8])
    Xs = [X(r) for r in rows if r[0] == "train"]
    for _ in range(50):
        G = -pen * b; H = np.diag(pen.copy())
        for M, c in Xs:
            u = M @ b; p = np.exp(u - u.max()); p /= p.sum(); mu = p @ M; G += M[c] - mu; H += (M * p[:, None]).T @ M - np.outer(mu, mu)
        s = np.linalg.solve(H, G); b += s
        if np.abs(s).max() < 1e-7: break
    def ll(sel):
        out_n, out_o = [], []
        for r in rows:
            if not sel(r): continue
            M, c = X(r); u = M @ b; p = np.exp(u - u.max()); p /= p.sum(); out_n.append(-np.log(p[c]))
            base = kw if who == "k" else dw; out_o.append(-np.log(base[r[5] if who == "k" else r[8]]))  # the sim now: any of the five by role share
        return round(float(np.mean(out_n)), 4), round(float(np.mean(out_o)), 4)
    sets = {"train": lambda r: r[0] == "train", "from cutoff": lambda r: r[0] == "test", "Worlds": lambda r: r[0] == "test" and r[1] == "WLDs"}
    return b, {nm: dict(zip(["players model", "sim now (all five)"], ll(f_))) for nm, f_ in sets.items() if any(f_(r) for r in rows)}
bK, llK = choice_fit(KB, "k"); bV, llV = choice_fit(KB, "v")
res["killer_logloss"], res["victim_logloss"] = llK, llV
res["killer"] = {"role": {WN[w]: dict(zip(ROLES, [0.0] + np.round(bK[w * 4:w * 4 + 4], 4).tolist())) for w in range(5)}, "lean_per_1k_before_15": round(float(bK[-1]), 4)}
res["victim"] = {"role": {WN[w]: dict(zip(ROLES, [0.0] + np.round(bV[w * 4:w * 4 + 4], 4).tolist())) for w in range(5)}, "lean_per_1k_before_15": round(float(bV[-1]), 4)}
# kills in the fight and whether the player was already in a kill of it matter: in a one-kill fight every other player seen on the winning
# side assisted by definition (players are only seen through kills), so the sim must give them the assist to keep its fights' players real
C = pd.DataFrame(CB, columns=["split", "league", "w", "r", "same_k", "same_v", "y", "flat", "nb", "seen"])
XC = lambda d: np.column_stack([*[(d.w == i) for i in range(5)], *[(d.r == i) for i in range(1, 5)], d.same_k, d.same_v, d.nb == 0, d.nb == 1, d.seen]).astype(float)
ct = C[C.split == "train"]; X = XC(ct); y = ct.y.values; bc = np.zeros(X.shape[1])
for _ in range(60):
    p = 1 / (1 + np.exp(-X @ bc)); H = X.T @ (X * (p * (1 - p))[:, None]) + 0.5 * np.eye(len(bc)); bc += np.linalg.solve(H, X.T @ (y - p) - 0.5 * bc)
lb = lambda p, y: round(float(-np.mean(y * np.log(np.clip(p, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-9, 1)))), 4)
res["assist_logloss_players_in_fight_only"] = {nm: {"players model": lb(1 / (1 + np.exp(-XC(C[m]) @ bc)), C.y[m].values), "flat rate": lb(C.flat[m].values, C.y[m].values)}
                                              for nm, m in {"train": C.split == "train", "from cutoff": C.split == "test", "Worlds": (C.split == "test") & (C.league == "WLDs")}.items() if m.any()}
res["assist"] = dict(zip([f"window {w}" for w in WN] + [f"role {r}" for r in ROLES[1:]] + ["same_lane_as_killer", "same_lane_as_victim", "one_kill_fight", "two_kill_fight", "already_in_a_kill"], np.round(bc, 4).tolist()))
res["real_shape"] = {"players per side (A, B), mean by window": {WN[w]: [round(float(np.mean([len(f["SA"]) for f in F if f["w"] == w])), 2), round(float(np.mean([len(f["SB"]) for f in F if f["w"] == w])), 2)] for w in range(5)},
                     "solo kill share by window": {WN[w]: round(float(np.mean([len(a) == 0 for f in F for (t, s, k, v, a) in f["kills"] if WIN(t) == w])), 3) for w in range(5)}}
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k_: v_ for k_, v_ in res.items() if k_ not in ("players", "killer", "victim", "assist")}, indent=1))
print("same-side pairs 0-4", res["players"]["same_side_pair"]["0-4"]); print("across 0-4", res["players"]["across"]["0-4"]); print("assist", res["assist"])
