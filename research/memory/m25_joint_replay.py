"""Joint take-or-reset models compared in a replay (28 Nov 2026 AEST; Luke: "rerun both windows - compare all metrics for a realistic run,
lets see what is closer"). Three versions of the "what next?" model, all on m21's terms and m21 / m23's rows:
  window  m21's window model (fit on won-fight windows only, ridge 1): what v55 uses today
  free    m24's joint model: window terms and outside shifts fitted together (shifts' ridge by 5-fold CV by game, training games only)
  fixed   window terms held at the window model's values; only the outside shifts fitted, on outside rows (ridge chosen the same way),
          so the window steps score exactly as v55 by construction
The ridge range now runs from 0.1 (m24 chose 1, the edge of its range).
Scores (research copy, fit before 1 Sep; held out from 1 Sep and Worlds), each model on window and outside rows, both stages.
Replay (the realistic run; no sim): every held-out real chain played through each model, DRAWS draws each, the same random numbers for
every model (seeded by game and chain), with the real death intervals and the real state at the chain's start, as m21's replay:
  window chains  each real won fight from its last kill (step 0)
  outside chains each real base structure taken outside every own won-fight window (m23's anchors), from that take (step 1)
Take times use m21's fitted quantiles for every model (not refitted outside). Each draw stops at a reset, a failed Nexus (enemies back
first), the Nexus, or 8 steps. Censored chains (base races, as m21 / m23) are left out.
Metrics, real v each model, by split and chain kind: any objective taken, objectives per chain, each option's take share, the Nexus by
structures left and players alive, baron and dragon when up by players alive, an inhibitor when up by enemies alive at the start. Closeness:
the chain-weighted mean absolute gap (real v replay) over those cells. Output: research/model/memory/m25_joint_replay.json and a run record.
No app file is touched.
usage (repo root): python -I research/memory/m25_joint_replay.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, zlib
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import INP, DTJ, RATES, rates, dead_intervals, ll
import m21_fight_window as F
import m23_window_outside as O
from m24_joint_window import J1, J2, yb, yo, FOLDS

OUT = config.MODEL_DIR / "memory"
GRID = [0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000, 10000]
DRAWS = 20
N1, N2 = len(F.S1N), len(F.OPT) * len(F.S2T)
sig = lambda x: 1 / (1 + np.exp(-x))

def lfit(X, y, pen, off=0.0, it=60):
    b = np.zeros(X.shape[1]); P = np.diag(pen)
    for _ in range(it):
        p = sig(X @ b + off); s = np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]) + P, X.T @ (y - p) - pen * b); b += s
        if np.abs(s).max() < 1e-8: break
    return b
def cfit(X, M, yi, pen, off=0.0, it=60):
    b = np.zeros(X.shape[2]); P = np.diag(pen)
    for _ in range(it):
        u = np.where(M, X @ b + off, -np.inf); u -= u.max(1, keepdims=True); p = np.exp(u); p /= p.sum(1, keepdims=True)
        xb = np.einsum("rk,rkp->rp", p, X); g = (X[np.arange(len(yi)), yi] - xb).sum(0) - pen * b
        H = np.einsum("rk,rkp,rkq->pq", p, X, X) - np.einsum("rp,rq->pq", xb, xb) + P
        s = np.linalg.solve(H, g); b += s
        if np.abs(s).max() < 1e-8: break
    return b
def ll1(d, b): return ll(J1(d), b, yb(d))
def ll2(d, b): X, M = J2(d); return F.clogit_ll(X, M, yo(d), b)

def folds(tr):
    g = np.array(sorted(tr.gid.unique())); rng = np.random.default_rng(20261128); rng.shuffle(g)
    return tr.gid.map({gg: i % FOLDS for i, gg in enumerate(g)}).values

def fit_free(tr, lam1, lam2):
    T = tr[tr.y != "reset"]; X, M = J2(T)
    return lfit(J1(tr), yb(tr), np.r_[np.ones(N1), np.full(N1, lam1)]), cfit(X, M, yo(T), np.r_[np.ones(N2), np.full(N2, lam2)])
def fit_fixed(tr, bw1, bw2, lam1, lam2):
    o = tr[tr.outside]; oT = o[o.y != "reset"]; X1o = F.X1(o); X, M = F.X2(oT)
    s1 = lfit(X1o, yb(o), np.full(N1, lam1), off=X1o @ bw1); s2 = cfit(X, M, yo(oT), np.full(N2, lam2), off=X @ bw2)
    return np.r_[bw1, s1], np.r_[bw2, s2]

def choose(tr, fitter):
    f = folds(tr); cv1, cv2 = {}, {}
    for lam in GRID:
        a1 = a2 = n1 = n2 = 0.0
        for k in range(FOLDS):
            b1, b2 = fitter(tr[f != k], lam, lam); ho = tr[(f == k) & tr.outside.values]; hT = ho[ho.y != "reset"]
            a1 += ll1(ho, b1) * len(ho); n1 += len(ho); a2 += ll2(hT, b2) * len(hT); n2 += len(hT)
        cv1[lam], cv2[lam] = round(a1 / n1, 5), round(a2 / n2, 5)
    return min(cv1, key=cv1.get), min(cv2, key=cv2.get), cv1, cv2

def outside_chains(ns):
    """m23's anchors as replay starts (same reading as O.outside_rows)"""
    ev, info = ns["ev"], ns["info"]; out = []
    for g, d in ev.sort_values(["gid", "t"]).groupby("gid"):
        if g not in info.index: continue
        gi = info.loc[g]; glen, gwin = float(gi.len), gi.win
        objs = F.game_objects(d); Fl = F.fights_of(d); sp = O.window_spans(objs, Fl); fstarts = sorted(f[0] for f in Fl)
        for w in ("blue", "red"):
            used = set()
            for a in [o for o in objs if o[1] == w and o[2] in O.BASE]:
                if a in used or any(s0 <= a[0] <= s1 for s0, s1 in sp[w]): continue
                used.add(a); nf = next((t for t in fstarts if t > a[0]), 1e9); seq, anchor = [], a[0]
                for o in [o for o in objs if o[1] == w and a[0] < o[0] < nf]:
                    if o[0] - anchor > F.CHAIN: break
                    seq.append(o); anchor = max(anchor, o[0])
                used.update(o for o in seq if o[2] in O.BASE)
                opts = [o for o in seq if o[2] in F.OPT]
                last = max([a[0]] + [o[0] for o in opts])
                cens = glen < min(nf, last + F.CHAIN) and gwin != w and not (opts and opts[-1][2] == "nexus")
                out.append({"gid": g, "id": f"o{a[0]:.0f}{w}", "split": gi.split, "w": w, "t1": a[0], "j0": 1, "censored": cens,
                            "took": [o[2] for o in opts], "took_t": [o[0] for o in opts], "anchor": a})
    return out

def window_chains(Fd):
    return [{"gid": r.gid, "id": f"w{int(r.fi)}", "split": r.split, "w": r.w, "t1": r.t1, "j0": 0, "censored": r.censored,
             "took": list(r.took), "took_t": list(r.took_t), "anchor": None} for r in Fd.itertuples()]

def replay(ns, chains, DEAD, models, TT, outside):
    info, GD = ns["info"], ns["GD"]; objs_by = {g: F.game_objects(d) for g, d in ns["ev"].sort_values(["gid", "t"]).groupby("gid")}
    rows = []
    for c in chains:
        if c["censored"] or c["split"] == "train": continue
        g = c["gid"]; gi = info.loc[g]; objs = objs_by[g]; dd = DEAD.get(g, {"blue": [], "red": []}); w = c["w"]; o = "red" if w == "blue" else "blue"
        bar_t = [x[0] for x in objs if x[1] == w and x[2] == "baron"]; eld_t = [x[0] for x in objs if x[1] == w and x[2] == "elder"]
        tk_set = set(c["took_t"])
        before = [x for x in objs if x[0] < c["t1"] + 1e-3 and not (x[1] == w and x[2] in F.OPT and x[0] in tk_set)]
        A0, left = F.State(before).avail(w, c["t1"] + 1e-3, [])
        f0 = F.feats(gi, w, c["t1"], c["t1"], c["j0"], dd, A0, GD, g, bar_t, eld_t)
        row = {"split": c["split"], "left": left, "bucket": F.bucket(f0["own_alive"] - f0["enemy_alive"]), "enemy_alive": f0["enemy_alive"],
               **{f"up_{k}": f0[f"up_{k}"] for k in F.OPT}, **{f"real_{k}": int(k in c["took"]) for k in F.OPT}, "real_n": len(c["took"])}
        for name, (b1, b2) in models.items():
            rng = np.random.default_rng(zlib.crc32(f"{g}|{c['id']}".encode())); cnt = {k: 0 for k in F.OPT}; nsum = 0
            for _ in range(DRAWS):
                ta, extra, took, n = c["t1"], [], set(), 0
                for j in range(c["j0"], c["j0"] + 8):
                    A, _ = F.State(before).avail(w, ta + 1e-3, extra)
                    if not any(A.values()): break
                    f = pd.DataFrame([{**F.feats(gi, w, ta, c["t1"], j, dd, A, GD, g, bar_t, eld_t), "outside": outside}])
                    u1, u2 = rng.random(), rng.random(); u3 = rng.random()
                    if u1 >= sig((J1(f) @ b1)[0]): break
                    X, M = J2(f); p = F.clogit_p(X, M, b2)[0]; k = F.OPT[min(int(np.searchsorted(np.cumsum(p), u2 * p.sum())), len(F.OPT) - 1)]
                    tk = ta + F.tq(TT, k, F.bucket(f.own_alive[0] - f.enemy_alive[0]), u3)
                    if k == "nexus":
                        back = max([e for s, e in dd[o] if s <= ta < e], default=ta)
                        if tk < back: took.add(k); n += 1
                        break
                    took.add(k); n += 1; lane = None
                    if k == "inhib":
                        t3 = {x[3] for x in before + extra if x[1] == w and x[2] == "T3"}; dn = {x[3] for x in before + extra if x[1] == w and x[2] == "inhib" and tk - 300 < x[0]}
                        lane = next((L for L in F.LANES if L in t3 and L not in dn), None)
                    extra.append((max(ta, tk), w, k, lane)); ta = max(ta, tk)
                for k in took: cnt[k] += 1
                nsum += n
            row.update({f"{name}_{k}": cnt[k] / DRAWS for k in F.OPT}); row[f"{name}_n"] = nsum / DRAWS
        rows.append(row)
    return pd.DataFrame(rows)

def tables(D, names):
    """real v each model; closeness = chain-weighted mean |gap| over cells"""
    res = {}
    for s in ("test", "worlds"):
        q = D[D.split == s]
        if not len(q): continue
        T, gaps = {}, {m: [] for m in names}
        def cell(label, z, real, sim):
            T[label] = {"chains": len(z), "real": round(float(z[real].mean()), 3), **{m: round(float(z[sim(m)].mean()), 3) for m in names}}
            for m in names: gaps[m].append((len(z), abs(float(z[real].mean()) - float(z[sim(m)].mean()))))
        T["objectives per chain"] = {"chains": len(q), "real": round(float(q.real_n.mean()), 3), **{m: round(float(q[f"{m}_n"].mean()), 3) for m in names}}
        for k in F.OPT:
            if q[f"real_{k}"].sum() or any(q[f"{m}_{k}"].sum() for m in names): cell(f"takes {k}", q, f"real_{k}", lambda m, k=k: f"{m}_{k}")
        for L in range(4):
            for bkt in F.BUCKETS:
                z = q[(q.left == L) & (q.bucket == bkt)]
                if len(z): cell(f"Nexus, {L} left, {bkt}", z, "real_nexus", lambda m: f"{m}_nexus")
        for k in ("baron", "dragon"):
            for bkt in F.BUCKETS:
                z = q[(q[f"up_{k}"] == 1) & (q.bucket == bkt)]
                if len(z): cell(f"{k} when up, {bkt}", z, f"real_{k}", lambda m, k=k: f"{m}_{k}")
        for ea in range(6):
            z = q[(q.up_inhib == 1) & (q.enemy_alive == ea)]
            if len(z): cell(f"inhibitor when up, {ea} enemies alive", z, "real_inhib", lambda m: f"{m}_inhib")
        T["closeness (chain-weighted mean abs gap; lower is closer)"] = {m: round(sum(n * g for n, g in gaps[m]) / max(1, sum(n for n, _ in gaps[m])), 4) for m in names}
        res[s] = T
    return res

def main():
    with Run("memory_joint_replay", params={"split": config.SPLIT, "chain_s": F.CHAIN, "ridge_base": 1.0, "ridge_grid": GRID, "folds": FOLDS, "draws": DRAWS, "copy": "research"},
             inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, INP["research"]["v1"], INP["research"]["comp"]]) as run:
        o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
        XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
        DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
        ns = rates("research", tag="m25")
        DEAD, matched = dead_intervals(ns["info"], ns["ev"], XP, AVG, DT)
        Sw, Fd, _, _ = F.window_rows(ns, DEAD); So, na = O.outside_rows(ns, DEAD)
        cols = [c for c in So.columns if c in Sw.columns]
        S = pd.concat([Sw[cols].assign(outside=False), So[cols].assign(outside=True)], ignore_index=True)
        tr = S[S.split == "train"]
        W, bw1, bw2, TT = F.fit_window(ns, Sw)
        fr1, fr2, cvf1, cvf2 = choose(tr, fit_free); bf1, bf2 = fit_free(tr, fr1, fr2)
        fx1, fx2, cvx1, cvx2 = choose(tr, lambda d, a, b: fit_fixed(d, bw1, bw2, a, b)); bx1, bx2 = fit_fixed(tr, bw1, bw2, fx1, fx2)
        models = {"window": (np.r_[bw1, np.zeros(N1)], np.r_[bw2, np.zeros(N2)]), "free": (bf1, bf2), "fixed": (bx1, bx2)}
        names = list(models)
        tro = tr[tr.outside]; b10 = ns["logit_fit"](F.X1(tro)[:, :1], yb(tro))
        sc = {}
        for s in ("test", "worlds"):
            q = S[S.split == s]; sc[s] = {}
            for kind, z in (("window rows", q[~q.outside]), ("outside rows", q[q.outside])):
                zT = z[z.y != "reset"]
                sc[s][kind] = {"steps, takes": [len(z), len(zT)], "real take share": round(float(yb(z).mean()), 3),
                               "mean take chance": {m: round(float(sig(J1(z) @ models[m][0]).mean()), 3) for m in names},
                               "stage 1 log loss": {**{m: ll1(z, models[m][0]) for m in names}, "base share": ll(F.X1(z)[:, :1], b10, yb(z))},
                               "stage 2 log loss": {**{m: ll2(zT, models[m][1]) for m in names}, "equal among up": ll2(zT, np.zeros(2 * N2))}}
        Dw = replay(ns, window_chains(Fd), DEAD, models, TT, False)
        Do = replay(ns, outside_chains(ns), DEAD, models, TT, True)
        R = {"source": "research/memory/m25_joint_replay.py (28 Nov 2026 AEST)", "deaths matched": matched,
             "rows by split (window | outside)": {s: [int(((S.split == s) & ~S.outside).sum()), int(((S.split == s) & S.outside).sum())] for s in ("train", "test", "worlds")}, **na,
             "ridge chosen (stage 1, stage 2)": {"free": [fr1, fr2], "fixed": [fx1, fx2]},
             "CV log loss on outside rows by ridge": {"free": {"stage 1": cvf1, "stage 2": cvf2}, "fixed": {"stage 1": cvx1, "stage 2": cvx2}},
             "scores": sc, "replay chains (window | outside)": {s: [int((Dw.split == s).sum()), int((Do.split == s).sum())] for s in ("test", "worlds")},
             "replay: window chains": tables(Dw, names), "replay: outside chains": tables(Do, names),
             "outside shifts, stage 1 (free | fixed)": {n: [round(float(bf1[N1 + i]), 4), round(float(bx1[N1 + i]), 4)] for i, n in enumerate(F.S1N)}}
        for s in ("test", "worlds"):
            run.result(f"{s} closeness", {"window chains": R["replay: window chains"][s]["closeness (chain-weighted mean abs gap; lower is closer)"],
                                          "outside chains": R["replay: outside chains"][s]["closeness (chain-weighted mean abs gap; lower is closer)"]})
        run.save_json(OUT / "m25_joint_replay.json", R)
        print(json.dumps(R, indent=1))

if __name__ == "__main__": main()
