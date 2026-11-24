"""Game memory, next steps, step 1b-0 (24 Nov 2026 AEST; Luke OK'd): which part of the sim's fight draw makes too many solo kills.
Step 1a (m7_kill_credit.py, m7_sim_check.js) found the v51 app sim's killer roles match real games, but its solo share rises with fight
size (7+ kill fights 24% v about 5% real) and side B's kills are 27% solo (real 6%). The sim's fight draw (js/sim-engine.js, fight
players; research/sim3/s3_sim.py the same) has three parts: (1) who is in the fight, both sides' sets drawn at the start by window and
kills group (1, 2, 3+); (2) each kill's killer and victim among the living players in the sets, by role and window; (3) assists: each
living teammate in the set, a yes/no chance (window, role, same lane as killer or victim, 1- or 2-kill fight, already in a kill).
This script replays real fights through the sim's own draws, one part at a time, with the app's fitted tables
(research/local/sim4/app_params/participants.json, the same numbers as js/sim-tables.js; fitted on games to 10 Nov, so Worlds is not
held out from them: the Worlds rows here are a like-for-like check, not a test):
  (i)   real sets, real killers, victims and kill order; the sim draws the assists only
  (ii)  real sets and each kill's real side; the sim draws killer, victim and assists
  (iii) real kill sides and fight size; the sim draws the sets, killer, victim and assists
Each real fight is replayed 20 times (seeded by fight). The lean on the expected lane lead before 15:00 (killer and victim) is left out
(set to 0): it is a small term and needs the pre-game lane model. Kills the sim can't place (nobody alive on a side in the sets) are
dropped and counted, as the sim does.
Also measured on real fights: assists credited to players who died earlier in the same fight (the sim never gives these), and kills
landed or assisted by a player not yet seen in the fight (joiners), side A v side B.
Fights: kills less than 20 s apart; sizes 1, 2, 3-4, 5-6, 7+ (as m7_kill_credit.py); executions (no killer champion) left out.
Output: research/model/memory/m8_credit_diag.json.
usage (repo root): python -I research/memory/m8_credit_diag.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, itertools
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from common import FIGHT_GAP, r3

OUT = config.MODEL_DIR / "memory"
PJ = config.R / "local" / "sim4" / "app_params" / "participants.json"
ROLES = config.ROLES; LANE = [0, -1, 1, 2, 2]; REPS = 20
SIZE = lambda n: "1" if n == 1 else "2" if n == 2 else "3-4" if n <= 4 else "5-6" if n <= 6 else "7+"; SIZES = ["1", "2", "3-4", "5-6", "7+"]
WN = ["0-4", "5-9", "10-14", "15-24", "25+"]; WIN = lambda t: 0 if t < 300 else 1 if t < 600 else 2 if t < 900 else 3 if t < 1500 else 4
NBN = ["1", "2", "3+"]; NB = lambda n: 0 if n == 1 else 1 if n == 2 else 2; LWN = ["0-4", "5-9", "10-14", "15+"]
sig = lambda x: 1 / (1 + np.exp(-x))

def real_fights(tm, ev, rl):
    split = {m.gameid: ("worlds" if m.league == "WLDs" else "train" if m.day < config.SPLIT else "after 1 Sep") for m in tm.itertuples()}
    E = ev[(ev.type == "kill") & ev.champ.notna()].sort_values(["gameid", "t"]); F = []
    for g, d in E.groupby("gameid"):
        ks = []
        for e in d.itertuples():
            k, v = rl.get((g, data.key(e.champ))), rl.get((g, data.key(e.victim_champ)))
            a = [rl.get((g, data.key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
            if k is None or v is None or any(x is None for x in a): raise RuntimeError(f"{g}: kill at {e.t} not matched to roles")
            ks.append((float(e.t), e.side, ROLES.index(k[0]), ROLES.index(v[0]), sorted({ROLES.index(x[0]) for x in a} - {ROLES.index(k[0])})))
        cur = []
        for k in ks + [None]:
            if cur and (k is None or k[0] - cur[-1][0] > FIGHT_GAP):
                A = cur[0][1]; sets = {"blue": set(), "red": set()}
                for t, s, kk, v, a in cur: sets[s].update([kk, *a]); sets["red" if s == "blue" else "blue"].add(v)
                F.append({"g": g, "split": split[g], "A": A, "kills": cur, "sets": sets}); cur = []
            if k is not None: cur.append(k)
    return F

class Draw:
    """the sim's fight-player draws (js/sim-engine.js lines 226-246), lean before 15:00 left at 0"""
    def __init__(self, FP):
        self.k, self.v, self.a = FP["killer"], FP["victim"], FP["assist"]; fp = FP["players"]
        self.subs = [sorted(c) for n in range(1, 6) for c in itertools.combinations(range(5), n)]; pairs = list(itertools.combinations(range(5), 2))
        WITH = {lw: np.array([sum(fp["same_side_pair"][lw][f"{ROLES[i]}+{ROLES[j]}"] for i, j in pairs if i in s and j in s) for s in self.subs]) for lw in LWN}
        CROSS = {lw: np.array([[sum(fp["across"][lw][f"{ROLES[i]}~{ROLES[j]}"] for i in a_ for j in b_) for b_ in self.subs] for a_ in self.subs]) for lw in LWN}
        self.probs = []
        for wi, w in enumerate(WN):
            within, cross = WITH[LWN[min(wi, 3)]], CROSS[LWN[min(wi, 3)]]
            for nb in NBN:
                ra, rb = fp["role_A"][f"{w}|{nb}"], fp["role_B"][f"{w}|{nb}"]
                ua = np.array([sum(ra[ROLES[i]] for i in s) for s in self.subs]) + within; ub = np.array([sum(rb[ROLES[i]] for i in s) for s in self.subs]) + within
                u = (ua[:, None] + ub[None, :] + cross).reshape(-1); p = np.exp(u - u.max()); self.probs.append(p / p.sum())
    def sets(self, rng, w, nb):
        ci = rng.choice(len(self.probs[0]), p=self.probs[w * 3 + nb]); return set(self.subs[ci // 31]), set(self.subs[ci % 31])
    def pick(self, rng, cands, tab, w):
        u = np.array([tab["role"][WN[w]][ROLES[i]] for i in cands]); p = np.exp(u - u.max()); return cands[rng.choice(len(cands), p=p / p.sum())]
    def assists(self, rng, ck, k, v, w, nbf, inv):
        fa = self.a; out = []
        for i in ck:
            if i == k: continue
            x = fa["window " + WN[w]] + (fa["role " + ROLES[i]] if i else 0) + fa["same_lane_as_killer"] * (LANE[i] >= 0 and LANE[i] == LANE[k]) \
                + fa["same_lane_as_victim"] * (LANE[i] >= 0 and LANE[i] == LANE[v]) + fa["one_kill_fight"] * (nbf == 0) + fa["two_kill_fight"] * (nbf == 1) \
                + fa["already_in_a_kill"] * (i in inv)
            if rng.random() < sig(x): out.append(i)
        return out

def replay(f, D, rng, test):
    """one replay of a real fight; returns kill rows (or None for a dropped kill) and the sets used"""
    n = len(f["kills"]); w = WIN(f["kills"][0][0]); nbf = NB(n); A = f["A"]; B = "red" if A == "blue" else "blue"
    S = {A: set(f["sets"][A]), B: set(f["sets"][B])} if test != "iii" else dict(zip((A, B), D.sets(rng, w, nbf)))
    dead = {"blue": set(), "red": set()}; inv = {"blue": set(), "red": set()}; rows = []
    for t, s, k, v, a in f["kills"]:
        o = "red" if s == "blue" else "blue"; wk = w  # the sim uses the fight's window (its start minute) for every kill in it
        ck = sorted(i for i in S[s] if i not in dead[s]); cv = sorted(i for i in S[o] if i not in dead[o])
        if test == "i":
            if k not in ck or v not in cv: rows.append(None); continue
        else:
            if not ck or not cv: rows.append(None); continue
            k = D.pick(rng, ck, D.k, wk); v = D.pick(rng, cv, D.v, wk)
        dead[o].add(v); ast = D.assists(rng, [i for i in ck if i not in dead[s]], k, v, wk, nbf, inv)
        inv[s].add(k); inv[s].update(ast)
        rows.append({"k": k, "n_ast": len(ast), "solo": int(not ast), "sideB": int(s != A)})
    return rows, S

def summarise(rows_by_fight, sizes_by_fight):
    """solo share and assists per kill by size, side B / side A solo share, support kill share, supports with 3+ and 4+ kills in a fight"""
    R = {"by size": {}, "dropped kills (share)": None}
    K = [dict(r, size=sz) for rows, sz in zip(rows_by_fight, sizes_by_fight) for r in rows if r is not None]
    drop = sum(r is None for rows in rows_by_fight for r in rows); tot = sum(len(rows) for rows in rows_by_fight)
    K = pd.DataFrame(K); R["dropped kills (share)"] = r3(drop / tot)
    for s in SIZES:
        y = K[K["size"] == s]
        if len(y): R["by size"][s] = {"solo share": r3(y.solo.mean()), "assists per kill": r3(y.n_ast.mean()), "support kill share": r3((y.k == 4).mean()), "kills": int(len(y))}
    R["side B kills solo share"] = r3(K[K.sideB == 1].solo.mean()); R["side A kills solo share"] = r3(K[K.sideB == 0].solo.mean())
    sup3 = sup4 = 0
    for rows in rows_by_fight:
        for side in (0, 1):
            c = sum(1 for r in rows if r is not None and r["k"] == 4 and r["sideB"] == side); sup3 += c >= 3; sup4 += c >= 4
    R["fights with a support on 3+ / 4+ kills (per 1,000 fights)"] = [r3(1000 * sup3 / len(rows_by_fight)), r3(1000 * sup4 / len(rows_by_fight))]
    return R

def real_side(F):
    rows, sizes = [], []
    for f in F:
        A = f["A"]; rows.append([{"k": k, "n_ast": len(a), "solo": int(not a), "sideB": int(s != A)} for t, s, k, v, a in f["kills"]]); sizes.append(SIZE(len(f["kills"])))
    return summarise(rows, sizes)

def dead_and_joiners(F):
    """assists by players who died earlier in the fight; kills with a killer or assister not yet seen in the fight (side A after its
    first kill, side B)"""
    n_ast = dead_ast = 0; gaps = []; J = {"A": [0, 0], "B": [0, 0]}
    for f in F:
        A = f["A"]; died = {}; seen = {"blue": set(), "red": set()}; first = True
        for t, s, k, v, a in f["kills"]:
            o = "red" if s == "blue" else "blue"
            for i in a:
                n_ast += 1
                if (s, i) in died: dead_ast += 1; gaps.append(t - died[(s, i)])
            if not first:
                side = "A" if s == A else "B"; new = any(i not in seen[s] for i in [k, *a]); J[side][0] += new; J[side][1] += 1
            seen[s].update([k, *a]); seen[o].add(v); died[(o, v)] = t; first = False
    return {"assists by a player who died earlier in the same fight": [dead_ast, n_ast, r3(dead_ast / max(n_ast, 1))],
            "seconds from that player's death to the assist (median, max)": [float(np.median(gaps)) if gaps else None, float(max(gaps)) if gaps else None],
            "kills after the fight's first with a killer or assister not seen before in the fight: side A (share, kills)": [r3(J["A"][0] / max(J["A"][1], 1)), J["A"][1]],
            "same, side B (share, kills)": [r3(J["B"][0] / max(J["B"][1], 1)), J["B"][1]]}

with Run("memory_credit_diag", params={"fight_gap": FIGHT_GAP, "reps": REPS, "tables": str(PJ.relative_to(config.ROOT)), "lean_before_15": 0},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV, PJ]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "champion"]); data.check(o); rl = data.roles(o)
    tm, ev, _ = data.timelines(); FALL = real_fights(tm, ev, rl)
    FPJ = json.load(open(PJ)); D = Draw(FPJ); R = {"tables cutoff": FPJ["cutoff"]}
    for split in ("train", "worlds"):
        F = [f for f in FALL if f["split"] == split]; sizes = [SIZE(len(f["kills"])) for f in F]
        out = {"games": len({f["g"] for f in F}), "fights": len(F), "real": real_side(F), "real: dead assists and joiners": dead_and_joiners(F)}
        for test, label in (("i", "(i) real sets, killers, victims; sim assists"), ("ii", "(ii) real sets and kill sides; sim killer, victim, assists"),
                            ("iii", "(iii) real kill sides and size; sim sets, killer, victim, assists")):
            rows_all, sz_all, setB = [], [], {s: [] for s in SIZES}
            for fi, f in enumerate(F):
                rng = np.random.default_rng(fi * 1000 + {"i": 1, "ii": 2, "iii": 3}[test])
                for _ in range(REPS):
                    rows, S = replay(f, D, rng, test); rows_all.append(rows); sz_all.append(sizes[fi])
                    B = "red" if f["A"] == "blue" else "blue"; setB[sizes[fi]].append(len(S[B]))
            out[label] = summarise(rows_all, sz_all) | {"side B set size by fight size (mean)": {s: r3(np.mean(v)) for s, v in setB.items() if v}}
        out["real side B set size by fight size (mean)"] = {s: r3(np.mean([len(f["sets"]["red" if f["A"] == "blue" else "blue"]) for f, z in zip(F, sizes) if z == s])) for s in SIZES}
        R[split] = out
        run.result(f"{split}: fights", len(F))
    run.save_json(OUT / "m8_credit_diag.json", R)
    print(json.dumps(R, indent=1))
