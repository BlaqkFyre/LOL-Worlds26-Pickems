"""Game memory, next steps, step 1b-1 part 1 (24 Nov 2026 AEST; Luke OK'd "credit + players alive"): fit the new kill-credit tables.
1b-0 (m8_credit_diag.py) found three causes of the v51 sim's extra solo kills, and the TL v CFO seed-24 game showed a fourth gap:
  1. players who died earlier in a fight can't assist in the sim (real: 10.7% of assists, median 4 s after their death);
  2. the assist chance has no fight-size term (real assists per kill rise 1.8 -> 2.6 with size);
  3. who is in a fight uses kills groups 1, 2, 3+ (side B too small in big fights; 5% of kills dropped);
  4. who wins each kill ignores the players alive on each side (a lone support won a fight 4-0 against four).
Fitted here (each against the v51 form of the same part, both fitted on the same training games):
  S  who is in the fight: the v51 joint model of both sides' sets with kills groups 1, 2, 3-4, 5+ (v51: 1, 2, 3+); ridge as v51
  A  assists: candidates = the killing side's players in the fight, alive or killed earlier in this fight (v51: alive only); terms:
     window, role, same lane as killer / victim, fight size (1, 2, 3-4, 5-6, 7+), side B, died earlier in this fight, already in a
     kill of this fight (v51: window, role, lanes, 1- and 2-kill fight, already in a kill); ridge 0.5 as v51
  K  who wins each kill: the v51 terms (gold lead at the fight's minute, v1 pre-game log-odds, Baron and Elder buffs) + players alive
     on each side at that kill (blue minus red; two forms: linear, or one term per difference -3..+3, ridge 1), refitted together
The killer and victim choice is not refitted: its terms (role by window, lean before 15:00) don't use the kills groups, and 1b-0 test
(ii) showed it adds almost nothing to the solo kills.
Players alive: every death in the timelines (kills and executions) lasts the sim's own respawn timer (each role's level from its XP by
minute, research/model/memory/memory_tables.json, the official timer as common.wiki_timer), so the fit and the sim count alike.
Splits: research copy fitted on games before config.SPLIT (1 Sep), judged on games from 1 Sep (not Worlds) and on Worlds. App copy
(Luke, 24 Nov: players alive as steps): the v2 forms refitted on every game before 10 Nov (as session 4's app tables), written to
research/local/sim4/app_params (participants_v2.json, killside_alive.json; the v51 participants.json is left as it is) and as one block
at the end of js/sim-tables.js (SIM_TABLES.credit, between markers; nothing else in that file is touched; re-running replaces it).
Replay check: real fights replayed 20 times through the new draws (as m8 tests i and iii), against real games.
Output: research/model/memory/m9_fit_credit.json (+ the app tables).
usage (repo root): python -I research/memory/m9_fit_credit.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, itertools, re
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from common import FIGHT_GAP, r3, wiki_timer

OUT = config.MODEL_DIR / "memory"; APD = config.R / "local" / "sim4" / "app_params"
PJ = APD / "participants.json"; MEMJ = config.MODEL_DIR / "memory" / "memory_tables.json"
APP_CUT = "2026-11-10"; REPS = 20
ROLES = config.ROLES; LANE = [0, -1, 1, 2, 2]
WN = ["0-4", "5-9", "10-14", "15-24", "25+"]; WIN = lambda t: 0 if t < 300 else 1 if t < 600 else 2 if t < 900 else 3 if t < 1500 else 4
LWN = ["0-4", "5-9", "10-14", "15+"]
GROUPS = {"v51": (["1", "2", "3+"], lambda n: 0 if n == 1 else 1 if n == 2 else 2),
          "v2": (["1", "2", "3-4", "5+"], lambda n: 0 if n == 1 else 1 if n == 2 else 2 if n <= 4 else 3)}
SIZE = lambda n: 0 if n == 1 else 1 if n == 2 else 2 if n <= 4 else 3 if n <= 6 else 4; SIZES = ["1", "2", "3-4", "5-6", "7+"]
sig = lambda x: 1 / (1 + np.exp(-x))
def ll_bin(p, y): p = np.clip(p, 1e-9, 1 - 1e-9); return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)

# ---------- data: fights with each kill's alive counts and who died earlier in the fight ----------
MEM = json.load(open(MEMJ))
def level_at(role, t):
    c = MEM["role_xp"][role]; LX = MEM["level_xp"]
    if t <= 1500: xp = c[0] * t / 600 if t <= 600 else c[0] + (c[1] - c[0]) * (t - 600) / 300 if t <= 900 else c[1] + (c[2] - c[1]) * (t - 900) / 300 if t <= 1200 else c[2] + (c[3] - c[2]) * (t - 1200) / 300
    else: xp = min(LX[17], c[3] + (c[3] - c[2]) / 300 * (t - 1500))
    return max(1, min(18, sum(xp >= x for x in LX)))

def build(tm, ev, rl, gold, z):
    day = dict(zip(tm.gameid, tm.day)); lg = dict(zip(tm.gameid, tm.league))
    G = gold[gold.kind == "gold"].groupby(["gid", "minute", "side"]).value.sum().unstack("side"); gid_of = dict(zip(tm.gameid, tm.gid))
    F = []
    for g, d in ev.sort_values(["gameid", "t"]).groupby("gameid"):
        dth = []; kills = []
        for e in d[d.type == "kill"].itertuples():
            v = rl.get((g, data.key(e.victim_champ)))
            if v is None: raise RuntimeError(f"{g} {e.t}: victim not matched")
            vside = v[1]; vr = ROLES.index(v[0]); dth.append((float(e.t), vside, vr))
            if pd.isna(e.champ): continue  # execution: a death, no kill
            k = rl.get((g, data.key(e.champ))); a = [rl.get((g, data.key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
            if k is None or any(x is None for x in a): raise RuntimeError(f"{g} {e.t}: kill not matched")
            kills.append((float(e.t), e.side, ROLES.index(k[0]), vr, sorted({ROLES.index(x[0]) for x in a} - {ROLES.index(k[0])}), len(dth) - 1))
        resp = [t + wiki_timer(level_at(ROLES[r], t), t) for t, s, r in dth]
        def alive(i_death):  # alive on each side just before death number i_death
            out = {"blue": 5, "red": 5}
            for j in range(i_death):
                if resp[j] > dth[i_death][0]: out[dth[j][1]] -= 1
            return out
        buff = d[d.type.isin(["baron", "dragon"])]
        cur = []
        for kk in kills + [None]:
            if cur and (kk is None or kk[0] - cur[-1][0] > FIGHT_GAP):
                t0 = cur[0][0]; m = int(t0 // 60); gg = gid_of[g]
                gd = float(G.loc[(gg, m), "blue"] - G.loc[(gg, m), "red"]) if (gg, m) in G.index else np.nan
                bar = buff[(buff.type == "baron") & (buff.t <= t0) & (buff.t > t0 - 180)]; eld = buff[(buff.type == "dragon") & (buff.detail.astype(str) == "elder") & (buff.t <= t0) & (buff.t > t0 - 150)]
                b_ = int((bar.side == "blue").any()) - int((bar.side == "red").any()); e_ = int((eld.side == "blue").any()) - int((eld.side == "red").any())
                A = cur[0][1]; sets = {"blue": set(), "red": set()}; rows = []; died = {"blue": set(), "red": set()}
                for t, s, k, v, a, di in cur:
                    o = "red" if s == "blue" else "blue"; sets[s].update([k, *a]); sets[o].add(v)
                for t, s, k, v, a, di in cur:
                    o = "red" if s == "blue" else "blue"; al = alive(di)
                    rows.append({"t": t, "side": s, "k": k, "v": v, "a": a, "alive": al, "died_before": {x: set(y) for x, y in died.items()}})
                    died[o].add(v)
                F.append({"g": g, "day": day[g], "league": lg[g], "A": A, "sets": sets, "kills": rows, "gd": gd, "z": z.get(g, np.nan), "baron": b_, "elder": e_})
                cur = []
            if kk is not None: cur.append(kk)
    return F

def split_of(f, cut): return "fit" if f["day"] < cut else ("worlds" if f["league"] == "WLDs" else "after")

# ---------- S: who is in the fight ----------
SUBS = [frozenset(c) for n in range(1, 6) for c in itertools.combinations(range(5), n)]; SI = {s: i for i, s in enumerate(SUBS)}; NS = len(SUBS)
PAIRS = list(itertools.combinations(range(5), 2)); NL = len(PAIRS) + 25
A_IND = np.array([[r in s for r in range(5)] for s in SUBS], float)
PAIR_IND = np.array([[(i in s and j in s) for i, j in PAIRS] for s in SUBS], float)
BASE = np.concatenate([PAIR_IND[:, None, :] + PAIR_IND[None, :, :], np.einsum("ai,bj->abij", A_IND, A_IND).reshape(NS, NS, 25)], axis=2)
class Sets:
    def __init__(self, form):
        self.names, self.nb = GROUPS[form]; self.ng = 5 * len(self.names); self.npa = 2 * self.ng * 5 + 4 * NL; self.GX = [self.gx(gi) for gi in range(self.ng)]
    def gx(self, gi):
        X = np.zeros((NS, NS, self.npa)); X[:, :, gi * 5:gi * 5 + 5] = A_IND[:, None, :]; ob = self.ng * 5 + gi * 5; X[:, :, ob:ob + 5] = A_IND[None, :, :]
        lw = min(gi // len(self.names), 3); X[:, :, 2 * self.ng * 5 + lw * NL:2 * self.ng * 5 + (lw + 1) * NL] = BASE; return X.reshape(NS * NS, self.npa)
    def gi(self, f): return WIN(f["kills"][0]["t"]) * len(self.names) + self.nb(len(f["kills"]))
    def cell(self, f): B = "red" if f["A"] == "blue" else "blue"; return SI[frozenset(f["sets"][f["A"]])] * NS + SI[frozenset(f["sets"][B])]
    def fit(self, fs, iters=60):
        cnt = np.zeros((self.ng, NS * NS))
        for f in fs: cnt[self.gi(f), self.cell(f)] += 1
        pen = np.r_[np.full(2 * self.ng * 5, 0.1), np.full(4 * NL, 1.0)]; b = np.zeros(self.npa)
        def obj(b_):
            o = -0.5 * float((pen * b_ * b_).sum())
            for gi in range(self.ng):
                n = cnt[gi].sum()
                if n: u = self.GX[gi] @ b_; o += float(cnt[gi] @ u) - n * (u.max() + np.log(np.exp(u - u.max()).sum()))
            return o
        cur = obj(b)
        for _ in range(iters):
            G_ = -pen * b; H = np.diag(pen.copy())
            for gi in range(self.ng):
                n = cnt[gi].sum()
                if not n: continue
                u = self.GX[gi] @ b; p = np.exp(u - u.max()); p /= p.sum(); mu = p @ self.GX[gi]
                G_ += cnt[gi] @ self.GX[gi] - n * mu; H += n * ((self.GX[gi] * p[:, None]).T @ self.GX[gi] - np.outer(mu, mu))
            s = np.linalg.lstsq(H, G_, rcond=None)[0]; step = 1.0
            while step > 1e-6:
                nb_ = b + step * s; new = obj(nb_)
                if new >= cur: break
                step /= 2
            if step <= 1e-6: break
            b, cur = nb_, new
            if np.abs(step * s).max() < 1e-7: break
        self.b = b; self.probs = []
        for gi in range(self.ng): u = self.GX[gi] @ b; p = np.exp(u - u.max()); self.probs.append(p / p.sum())
        return self
    def ll(self, fs): return round(float(np.mean([-np.log(self.probs[self.gi(f)][self.cell(f)]) for f in fs])), 4)
    def table(self):
        b, ng, nn = self.b, self.ng, len(self.names)
        return {"kills_groups": self.names,
                "role_A": {f"{WN[w]}|{self.names[n]}": dict(zip(ROLES, np.round(b[(w * nn + n) * 5:(w * nn + n) * 5 + 5], 4).tolist())) for w in range(5) for n in range(nn)},
                "role_B": {f"{WN[w]}|{self.names[n]}": dict(zip(ROLES, np.round(b[ng * 5 + (w * nn + n) * 5:ng * 5 + (w * nn + n) * 5 + 5], 4).tolist())) for w in range(5) for n in range(nn)},
                "same_side_pair": {lwn: {f"{ROLES[i]}+{ROLES[j]}": round(float(b[2 * ng * 5 + lw * NL + q]), 4) for q, (i, j) in enumerate(PAIRS)} for lw, lwn in enumerate(LWN)},
                "across": {lwn: {f"{ROLES[i]}~{ROLES[j]}": round(float(b[2 * ng * 5 + lw * NL + len(PAIRS) + i * 5 + j]), 4) for i in range(5) for j in range(5)} for lw, lwn in enumerate(LWN)}}

# ---------- A: assists ----------
def assist_rows(fs):
    """one row per (kill, candidate teammate): the killing side's players in the fight other than the killer, alive or killed earlier
    in this fight (players dead from before the fight are not in its sets)"""
    R = []
    for f in fs:
        n = len(f["kills"]); seen = {"blue": set(), "red": set()}; A = f["A"]; w = WIN(f["kills"][0]["t"])
        for kr in f["kills"]:
            s, k, v, a = kr["side"], kr["k"], kr["v"], kr["a"]
            for r in f["sets"][s]:
                if r == k: continue
                R.append((w, r, int(LANE[r] >= 0 and LANE[r] == LANE[k]), int(LANE[r] >= 0 and LANE[r] == LANE[v]), SIZE(n), int(s != A),
                          int(r in kr["died_before"][s]), int(r in seen[s]), int(r in a), int(len(a) == 0)))
            seen[s].update([k, *a])
    return pd.DataFrame(R, columns=["w", "r", "same_k", "same_v", "size", "sideB", "dead", "seen", "y", "solo"])
A_NAMES = {"v51": [f"window {w}" for w in WN] + [f"role {r}" for r in ROLES[1:]] + ["same_lane_as_killer", "same_lane_as_victim", "one_kill_fight", "two_kill_fight", "already_in_a_kill"],
           "v2": [f"window {w}" for w in WN] + [f"role {r}" for r in ROLES[1:]] + ["same_lane_as_killer", "same_lane_as_victim"] + [f"size {s}" for s in SIZES[1:]] + ["side_B", "died_earlier_in_fight", "already_in_a_kill"]}
def XA(d, form):
    base = [*[(d.w == i) for i in range(5)], *[(d.r == i) for i in range(1, 5)], d.same_k, d.same_v]
    if form == "v51": return np.column_stack(base + [d["size"] == 0, d["size"] == 1, d.seen]).astype(float)
    return np.column_stack(base + [*[(d["size"] == i) for i in range(1, 5)], d.sideB, d.dead, d.seen]).astype(float)
def logit_fit(X, y, ridge):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = sig(X @ b); H = X.T @ (X * (p * (1 - p))[:, None]) + ridge * np.eye(len(b)); s = np.linalg.solve(H, X.T @ (y - p) - ridge * b); b += s
        if np.abs(s).max() < 1e-8: break
    return b

# ---------- K: who wins each kill ----------
def kill_rows(fs):
    R = []
    for f in fs:
        if not np.isfinite(f["gd"]) or not np.isfinite(f["z"]): continue
        for kr in f["kills"]:
            R.append((f["gd"] / 1000, f["z"], f["baron"], f["elder"], kr["alive"]["blue"] - kr["alive"]["red"], kr["alive"]["blue"], kr["alive"]["red"], int(kr["side"] == "blue")))
    return pd.DataFrame(R, columns=["gd", "z", "baron", "elder", "adiff", "ab", "ar", "y"])
DIFFS = [-3, -2, -1, 1, 2, 3]
def XK(d, form):
    base = [np.ones(len(d)), d.gd, d.z, d.baron, d.elder]
    if form == "v51": return np.column_stack(base)
    if form == "linear": return np.column_stack(base + [d.adiff])
    return np.column_stack(base + [(d.adiff.clip(-3, 3) == x) for x in DIFFS]).astype(float)
K_NAMES = {"v51": ["intercept", "per_1k_gold_lead", "per_v1_logit", "baron", "elder"], "linear": ["intercept", "per_1k_gold_lead", "per_v1_logit", "baron", "elder", "per_alive_diff"],
           "steps": ["intercept", "per_1k_gold_lead", "per_v1_logit", "baron", "elder"] + [f"alive_diff {x:+d}" for x in DIFFS]}
K_RIDGE = {"v51": 1e-4, "linear": 1e-4, "steps": 1.0}

# ---------- replay: real fights through the new draws ----------
class Draw2:
    def __init__(self, sets, assist_b, PK):
        self.S, self.b, self.k, self.v = sets, assist_b, PK["killer"], PK["victim"]
    def pick(self, rng, cands, tab, w):
        u = np.array([tab["role"][WN[w]][ROLES[i]] for i in cands]); p = np.exp(u - u.max()); return cands[rng.choice(len(cands), p=p / p.sum())]
    def assists(self, rng, cand, k, v, w, size, sideB, died, inv):
        out = []
        for i in cand:
            if i == k: continue
            x = np.zeros(len(self.b)); x[w] = 1
            if i: x[4 + i] = 1
            x[9] = LANE[i] >= 0 and LANE[i] == LANE[k]; x[10] = LANE[i] >= 0 and LANE[i] == LANE[v]
            if size: x[10 + size] = 1
            x[15] = sideB; x[16] = i in died; x[17] = i in inv
            if rng.random() < sig(x @ self.b): out.append(i)
        return out
def replay(f, D, rng, test):
    n = len(f["kills"]); w = WIN(f["kills"][0]["t"]); A = f["A"]; B = "red" if A == "blue" else "blue"; sz = SIZE(n)
    if test == "i": S = {A: set(f["sets"][A]), B: set(f["sets"][B])}
    else: ci = rng.choice(NS * NS, p=D.S.probs[D.S.gi(f)]); S = {A: set(SUBS[ci // NS]), B: set(SUBS[ci % NS])}
    dead = {"blue": set(), "red": set()}; inv = {"blue": set(), "red": set()}; rows = []
    for kr in f["kills"]:
        s, k, v = kr["side"], kr["k"], kr["v"]; o = "red" if s == "blue" else "blue"
        ck = sorted(i for i in S[s] if i not in dead[s]); cv = sorted(i for i in S[o] if i not in dead[o])
        if test == "i":
            if k not in ck or v not in cv: rows.append(None); continue
        else:
            if not ck or not cv: rows.append(None); continue
            k = D.pick(rng, ck, D.k, w); v = D.pick(rng, cv, D.v, w)
        dead[o].add(v); ast = D.assists(rng, sorted(S[s]), k, v, w, sz, int(s != A), dead[s], inv)
        inv[s].add(k); inv[s].update(ast); rows.append({"k": k, "n_ast": len(ast), "solo": int(not ast), "sideB": int(s != A)})
    return rows, S
def summarise(rows_by_fight, sizes, setB=None):
    K = pd.DataFrame([dict(r, size=sz) for rows, sz in zip(rows_by_fight, sizes) for r in rows if r is not None])
    drop = sum(r is None for rows in rows_by_fight for r in rows); tot = sum(len(rows) for rows in rows_by_fight)
    R = {"by size": {s: {"solo share": r3(y.solo.mean()), "assists per kill": r3(y.n_ast.mean()), "support kill share": r3((y.k == 4).mean())}
                     for s in SIZES if len(y := K[K["size"] == s])},
         "side B kills solo share": r3(K[K.sideB == 1].solo.mean()), "side A kills solo share": r3(K[K.sideB == 0].solo.mean()), "dropped kills (share)": r3(drop / tot)}
    sup = [sum(1 for r in rows if r is not None and r["k"] == 4 and r["sideB"] == sd) for rows in rows_by_fight for sd in (0, 1)]
    R["fights with a support on 3+ / 4+ kills (per 1,000 fights)"] = [r3(1000 * sum(c >= 3 for c in sup) / len(rows_by_fight)), r3(1000 * sum(c >= 4 for c in sup) / len(rows_by_fight))]
    if setB: R["side B set size by fight size (mean)"] = {s: r3(np.mean(v)) for s, v in setB.items() if v}
    return R

with Run("memory_fit_credit", params={"fight_gap": FIGHT_GAP, "research_cut": config.SPLIT, "app_cut": APP_CUT, "reps": REPS, "assist_ridge": 0.5},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, config.LANE_FEATURES, PJ, MEMJ]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "champion"]); data.check(o); rl = data.roles(o)
    tm, ev, gold = data.timelines(); lf = pd.read_csv(config.LANE_FEATURES); z = lf.drop_duplicates("gameid").set_index("gameid").z_v1.to_dict()
    ALL = build(tm, ev, rl, gold, z); PK = json.load(open(PJ)); R = {"fights": len(ALL)}
    def fit_all(cut, report):
        fs = {s: [f for f in ALL if split_of(f, cut) == s] for s in ("fit", "after", "worlds")}; out = {"fights": {s: len(v) for s, v in fs.items()}}
        # S
        S = {form: Sets(form).fit(fs["fit"]) for form in ("v51", "v2")}
        if report: out["S who is in the fight: log loss (v51 kills groups, v2)"] = {s: [S["v51"].ll(v), S["v2"].ll(v)] for s, v in fs.items() if v}
        # A
        AR = {s: assist_rows(v) for s, v in fs.items()}; bA = {}
        for form in ("v51", "v2"):
            d = AR["fit"] if form == "v2" else AR["fit"][AR["fit"].dead == 0]; bA[form] = logit_fit(XA(d, form), d.y.values.astype(float), 0.5)
        if report:
            out["A assists: real assists by players killed earlier in the fight (v51 can't give them)"] = {s: r3(d[d.y == 1].dead.mean()) for s, d in AR.items() if len(d)}
            out["A assists: log loss on alive candidates (v51, v2)"] = {s: [ll_bin(sig(XA(d[d.dead == 0], "v51") @ bA["v51"]), d[d.dead == 0].y.values), ll_bin(sig(XA(d[d.dead == 0], "v2") @ bA["v2"]), d[d.dead == 0].y.values)] for s, d in AR.items() if len(d)}
            out["A assists: log loss on every candidate (v51 gives 0 to the dead, clipped at 1e-9; v2)"] = {s: [ll_bin(sig(XA(d, "v51") @ bA["v51"]) * (d.dead == 0), d.y.values), ll_bin(sig(XA(d, "v2") @ bA["v2"]), d.y.values)] for s, d in AR.items() if len(d)}
        # K
        KR = {s: kill_rows(v) for s, v in fs.items()}; bK = {form: logit_fit(XK(KR["fit"], form), KR["fit"].y.values.astype(float), K_RIDGE[form]) for form in K_NAMES}
        if report:
            out["K who wins each kill: log loss (v51, + alive linear, + alive steps)"] = {s: [ll_bin(sig(XK(d, f_) @ bK[f_]), d.y.values) for f_ in K_NAMES] for s, d in KR.items() if len(d)}
            out["K kills with each alive difference (blue minus red): count, real blue share, v51, linear, steps (mean predicted)"] = {
                s: {str(x): [int(len(y)), r3(y.y.mean())] + [r3(sig(XK(y, f_) @ bK[f_]).mean()) for f_ in K_NAMES] for x, y in d.groupby(d.adiff.clip(-4, 4))} for s, d in KR.items() if len(d)}
            out["K coefficients"] = {f_: dict(zip(K_NAMES[f_], np.round(bK[f_], 4).tolist())) for f_ in K_NAMES}
            out["A coefficients"] = {f_: dict(zip(A_NAMES[f_], np.round(bA[f_], 4).tolist())) for f_ in bA}
            # replay
            D = Draw2(S["v2"], bA["v2"], PK)
            for s, v in fs.items():
                sizes = [SIZES[SIZE(len(f["kills"]))] for f in v]
                real = [[{"k": kr["k"], "n_ast": len(kr["a"]), "solo": int(not kr["a"]), "sideB": int(kr["side"] != f["A"])} for kr in f["kills"]] for f in v]
                out[f"replay {s}: real"] = summarise(real, sizes)
                for test in ("i", "iii"):
                    rows_all, sz_all, setB = [], [], {x: [] for x in SIZES}
                    for fi, f in enumerate(v):
                        rng = np.random.default_rng(fi * 1000 + (1 if test == "i" else 3))
                        for _ in range(REPS):
                            rows, Sx = replay(f, D, rng, test); rows_all.append(rows); sz_all.append(sizes[fi]); setB[sizes[fi]].append(len(Sx["red" if f["A"] == "blue" else "blue"]))
                    out[f"replay {s}: ({test}) " + ("real sets, killers, victims; v2 assists" if test == "i" else "v2 sets, killer, victim, assists")] = summarise(rows_all, sz_all, setB)
        return S, bA, bK, out
    S1, bA1, bK1, R["research copy (fitted before 1 Sep)"] = fit_all(config.SPLIT, True)
    for k_, v in R["research copy (fitted before 1 Sep)"].items():
        if "log loss" in k_: run.result(k_, v)
    # app copy (Luke, 24 Nov: players alive as steps): every game before APP_CUT; written to app_params and as one block in js/sim-tables.js
    S2, bA2, bK2, info = fit_all(APP_CUT, False)
    CR = {"cutoff": APP_CUT, "source": f"research/memory/m9_fit_credit.py, gol.gg timelines before {APP_CUT} ({info['fights']['fit']} fights)",
          "players": S2["v2"].table(), "assist": dict(zip(A_NAMES["v2"], np.round(bA2["v2"], 4).tolist())),
          "kill_side": dict(zip(K_NAMES["steps"], np.round(bK2["steps"], 4).tolist()))}
    R["app copy (fitted before 10 Nov)"] = {"fights": info["fights"], "assist": CR["assist"], "kill_side": CR["kill_side"]}
    run.save_json(APD / "participants_v2.json", {"cutoff": APP_CUT, "players": CR["players"], "assist": CR["assist"], "killer": PK["killer"], "victim": PK["victim"]})
    run.save_json(APD / "killside_alive.json", {"cutoff": APP_CUT, "coef": CR["kill_side"]})
    JS = config.ROOT / "js" / "sim-tables.js"
    START, END = "/* kill credit tables: BUILT BY research/memory/m9_fit_credit.py, never edit by hand */", "/* end kill credit tables */"
    block = f"{START}\nwindow.SIM_TABLES.credit = {json.dumps(CR, separators=(',', ':'))};\n{END}\n"
    js = JS.read_text(encoding="utf-8"); js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + block
    tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)
    run.save_json(OUT / "m9_fit_credit.json", R)
    print(json.dumps(R, indent=1))
