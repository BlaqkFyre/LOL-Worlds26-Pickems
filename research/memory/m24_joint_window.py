"""Joint take-or-reset model: won-fight windows and base pushes outside them (28 Nov 2026 AEST; Luke: "Fit one joint model", "go").
m23 found the fight-window model (m21) predicts too few takes in base pushes outside won-fight windows (fails its pass rule from 1 Sep).
This fits ONE model on both kinds of step and tests it before anything reaches the app.
  rows    m21's window steps (window_rows) and m23's outside steps (outside_rows), one table with an outside flag.
  stage 1 take or reset (logistic): m21's terms (ridge 1, as m21) + the outside flag x every term ("shifts"). The shifts carry a
          stronger ridge (pulled toward 0, so toward the window model) chosen by 5-fold cross-validation by game on training games
          only, scored on the outside rows of the held-out folds.
  stage 2 which option among those up (conditional logit): m21's terms (ridge 1) + outside shifts on them, ridge chosen the same way.
  scores  research copy, fit before 1 Sep; held out from 1 Sep and on Worlds:
          outside rows: joint | window model | base share (stage 1) or equal among up (stage 2) | outside-only refit;
          window rows: joint | window model (must be no worse at 3 decimals);
          inhibitor up, by enemies alive: real share taking it next v joint v window model.
Pass rule (agreed in chat, 28 Nov): on both held-out sets the joint model beats the window model and the base share / equal on the
outside rows (both stages), and is no worse than the window model on the window rows (both stages, 3 decimals). Else report to Luke.
Output: research/model/memory/m24_joint_window.json and a run record. No app file is touched.
usage (repo root): python -I research/memory/m24_joint_window.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import INP, DTJ, RATES, rates, dead_intervals, ll
import m21_fight_window as F
import m23_window_outside as O

OUT = config.MODEL_DIR / "memory"
GRID = [1, 3, 10, 30, 100, 300, 1000, 10000]
FOLDS = 5

def lfit(X, y, pen, it=60):
    """ridge logistic with one penalty per term"""
    b = np.zeros(X.shape[1]); P = np.diag(pen)
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]) + P; s = np.linalg.solve(H, X.T @ (y - p) - pen * b); b += s
        if np.abs(s).max() < 1e-8: break
    return b

def cfit(X, M, yi, pen, it=60):
    """conditional logit with one penalty per term (m21's clogit_fit, vector ridge)"""
    b = np.zeros(X.shape[2]); P = np.diag(pen)
    for _ in range(it):
        u = np.where(M, X @ b, -np.inf); u -= u.max(1, keepdims=True); p = np.exp(u); p /= p.sum(1, keepdims=True)
        xb = np.einsum("rk,rkp->rp", p, X); xc = X[np.arange(len(yi)), yi]
        g = (xc - xb).sum(0) - pen * b
        H = np.einsum("rk,rkp,rkq->pq", p, X, X) - np.einsum("rp,rq->pq", xb, xb) + P
        s = np.linalg.solve(H, g); b += s
        if np.abs(s).max() < 1e-8: break
    return b

def J1(d):
    x = F.X1(d); o = d.outside.values.astype(float)[:, None]; return np.c_[x, x * o]
def J2(d):
    X, M = F.X2(d); o = d.outside.values.astype(float)[:, None, None]; return np.concatenate([X, X * o], 2), M
yb = lambda d: (d.y != "reset").values.astype(float)
yo = lambda d: np.array([F.OPT.index(v) for v in d.y])
pen1 = lambda lam: np.r_[np.ones(len(F.S1N)), np.full(len(F.S1N), lam)]
pen2 = lambda lam: np.r_[np.ones(len(F.OPT) * len(F.S2T)), np.full(len(F.OPT) * len(F.S2T), lam)]

def choose(tr):
    """ridge on the shifts by 5-fold CV by game (training games only), scored on held-out outside rows"""
    g = np.array(sorted(tr.gid.unique())); rng = np.random.default_rng(20261128); rng.shuffle(g)
    fold = {gg: i % FOLDS for i, gg in enumerate(g)}; f = tr.gid.map(fold).values
    cv1, cv2 = {}, {}
    for lam in GRID:
        a1, a2, n1, n2 = 0.0, 0.0, 0, 0
        for k in range(FOLDS):
            fit, ho = tr[f != k], tr[(f == k) & tr.outside]
            b = lfit(J1(fit), yb(fit), pen1(lam)); a1 += ll(J1(ho), b, yb(ho)) * len(ho); n1 += len(ho)
            fT, hT = fit[fit.y != "reset"], ho[ho.y != "reset"]
            X, M = J2(fT); b2 = cfit(X, M, yo(fT), pen2(lam)); Xh, Mh = J2(hT); a2 += F.clogit_ll(Xh, Mh, yo(hT), b2) * len(hT); n2 += len(hT)
        cv1[lam], cv2[lam] = round(a1 / n1, 5), round(a2 / n2, 5)
    return min(cv1, key=cv1.get), min(cv2, key=cv2.get), cv1, cv2

def p_inhib(d, X1m, b1, X2f, b2):
    X, M = X2f(d); pc = F.clogit_p(X, M, b2)[:, F.OPT.index("inhib")]; return (1 / (1 + np.exp(-X1m(d) @ b1))) * pc

def main():
    with Run("memory_joint_window", params={"split": config.SPLIT, "chain_s": F.CHAIN, "ridge_base": 1.0, "ridge_grid": GRID, "folds": FOLDS, "copy": "research"},
             inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, INP["research"]["v1"], INP["research"]["comp"]]) as run:
        o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
        XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
        DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
        ns = rates("research", tag="m24")
        DEAD, matched = dead_intervals(ns["info"], ns["ev"], XP, AVG, DT)
        Sw, _, _, _ = F.window_rows(ns, DEAD); So, na = O.outside_rows(ns, DEAD)
        cols = [c for c in So.columns if c in Sw.columns]
        S = pd.concat([Sw[cols].assign(outside=False), So[cols].assign(outside=True)], ignore_index=True)
        tr = S[S.split == "train"]; trT = tr[tr.y != "reset"]
        lam1, lam2, cv1, cv2 = choose(tr)
        bj1 = lfit(J1(tr), yb(tr), pen1(lam1)); X, M = J2(trT); bj2 = cfit(X, M, yo(trT), pen2(lam2))
        # the window model (m21, window rows only, ridge 1), base share and outside-only refits (as m23)
        trw, tro = tr[~tr.outside], tr[tr.outside]
        bw1 = ns["logit_fit"](F.X1(trw), yb(trw)); twT = trw[trw.y != "reset"]; X, M = F.X2(twT); bw2 = F.clogit_fit(X, M, yo(twT))
        b10 = ns["logit_fit"](F.X1(tro)[:, :1], yb(tro)); bo1 = ns["logit_fit"](F.X1(tro), yb(tro))
        toT = tro[tro.y != "reset"]; X, M = F.X2(toT); bo2 = F.clogit_fit(X, M, yo(toT))
        R = {"source": "research/memory/m24_joint_window.py (28 Nov 2026 AEST)", "deaths matched": matched,
             "rows by split (window | outside)": {s: [int(((S.split == s) & ~S.outside).sum()), int(((S.split == s) & S.outside).sum())] for s in ("train", "test", "worlds")}, **na,
             "shift ridge chosen (stage 1, stage 2)": [lam1, lam2], "CV log loss on outside rows by ridge: stage 1": cv1, "stage 2": cv2}
        sc, ok = {}, True
        for s in ("test", "worlds"):
            q = S[S.split == s]; qo, qw = q[q.outside], q[~q.outside]; qoT, qwT = qo[qo.y != "reset"], qw[qw.y != "reset"]
            Xo, Mo = F.X2(qoT); Jo, JMo = J2(qoT); Xw, Mw = F.X2(qwT); Jw, JMw = J2(qwT)
            o1 = [ll(J1(qo), bj1, yb(qo)), ll(F.X1(qo), bw1, yb(qo)), ll(F.X1(qo)[:, :1], b10, yb(qo)), ll(F.X1(qo), bo1, yb(qo))]
            o2 = [F.clogit_ll(Jo, JMo, yo(qoT), bj2), F.clogit_ll(Xo, Mo, yo(qoT), bw2), F.clogit_ll(Xo, Mo, yo(qoT), np.zeros_like(bw2)), F.clogit_ll(Xo, Mo, yo(qoT), bo2)]
            w1 = [ll(J1(qw), bj1, yb(qw)), ll(F.X1(qw), bw1, yb(qw))]
            w2 = [F.clogit_ll(Jw, JMw, yo(qwT), bj2), F.clogit_ll(Xw, Mw, yo(qwT), bw2)]
            inh = qo[qo.up_inhib == 1]; tab = {}
            if len(inh):
                pj = p_inhib(inh, J1, bj1, J2, bj2); pw = p_inhib(inh, F.X1, bw1, F.X2, bw2)
                for ea in range(6):
                    m = (inh.enemy_alive == ea).values
                    if m.sum(): tab[f"{ea} enemies alive"] = [int(m.sum()), round(float((inh.y.values[m] == "inhib").mean()), 3), round(float(pj[m].mean()), 3), round(float(pw[m].mean()), 3)]
            p_j = 1 / (1 + np.exp(-J1(qo) @ bj1)); p_w = 1 / (1 + np.exp(-F.X1(qo) @ bw1))
            checks = {"outside stage 1: joint beats window model": o1[0] < o1[1], "outside stage 1: joint beats base share": o1[0] < o1[2],
                      "outside stage 2: joint beats window model": o2[0] < o2[1], "outside stage 2: joint beats equal": o2[0] < o2[2],
                      "window stage 1: joint no worse (3 dp)": round(w1[0], 3) <= round(w1[1], 3), "window stage 2: joint no worse (3 dp)": round(w2[0], 3) <= round(w2[1], 3)}
            ok = ok and all(checks.values())
            sc[s] = {"outside steps, takes": [len(qo), len(qoT)], "window steps, takes": [len(qw), len(qwT)],
                     "outside real take share | joint mean | window model mean": [round(float(yb(qo).mean()), 3), round(float(p_j.mean()), 3), round(float(p_w.mean()), 3)],
                     "outside stage 1 log loss (joint | window model | base share | outside refit)": o1,
                     "outside stage 2 log loss (joint | window model | equal among up | outside refit)": o2,
                     "window stage 1 log loss (joint | window model)": w1, "window stage 2 log loss (joint | window model)": w2,
                     "inhibitor up, outside: steps, real share taking it next, joint, window model (by enemies alive)": tab, "checks": checks}
            run.result(s, sc[s])
        R["scores"] = sc; R["pass"] = bool(ok)
        R["stage 1 coef (window terms | outside shifts)"] = {n: [round(float(bj1[i]), 4), round(float(bj1[i + len(F.S1N)]), 4)] for i, n in enumerate(F.S1N)}
        P = len(F.S2T); K = len(F.OPT)
        R["stage 2 coef (window terms | outside shifts)"] = {k: {t: [round(float(bj2[i * P + j]), 4), round(float(bj2[K * P + i * P + j]), 4)] for j, t in enumerate(F.S2T)} for i, k in enumerate(F.OPT)}
        run.result("pass", R["pass"])
        run.save_json(OUT / "m24_joint_window.json", R)
        print(json.dumps(R, indent=1))

if __name__ == "__main__": main()
