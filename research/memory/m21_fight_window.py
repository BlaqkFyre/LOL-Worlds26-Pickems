"""Fight windows, part A: the fit (27 Nov 2026 AEST; Luke OK'd research/memory/fight-window-plan.md part A).
After a real won fight (kills under 20 s apart, the side with more kills wins) the winners take objectives one at a time, or reset:
  options   dragon, elder, baron (up by the spawn timers, as m20), herald and grubs (spawned, not yet taken; once a game, as the engine),
            an inhibitor (a lane whose T3 the winners took, inhibitor up), a nexus tower (an inhibitor down, a nexus tower standing),
            the Nexus (an inhibitor down, no nexus tower standing). Lane towers (outer, T3) are not options in this build: they fall plate by
            plate in the engine and keep today's per-minute segment draws; they do move the window on (below).
  window    the winners' objectives from the fight's start until the next fight starts, each within CHAIN = 60 s of the previous event
            (the fight's last kill, then any structure or monster the winners took, lane towers included); 60 s as m19 (the 45 / 60 / 90 s
            readings gave the same real shares there).
  steps     one row per "what next?": an option (the winners' next objective in the window) or reset. A reset is dropped (censored) when the
            game ends inside its 60 s and the winners lost the game (a base race, as m19).
  inputs    at the step's moment (the last kill, then each objective's time): players alive on each side, seconds until the first and
            until the last of the losers dead now are back (official timers, as m17), the step (0, 1, 2+), gold lead, v1 logit, own
            baron / elder buff, game time (from 25, from 35), and which options are up.
  model     stage 1, take something or reset (logistic, ridge 1, as the other fits); stage 2, which option among those up (conditional
            logit: per option an intercept, a slope on players alive (winners minus losers) and on seconds until all are back; ridge 1).
  times     from the step's moment to the objective, by option and players alive (winners 3+ up, 1-2 up, even or behind); 21 quantiles
            where 20+ takes, else the option pooled.
Replay check (no sim): every real won fight played through the fitted window (20 draws each, seeded by game and fight), with the real
death intervals and the real state at the last kill; the share that take the Nexus by structures left and players alive, baron and dragon
when up by players alive, against the real shares with the same definitions.
Per-minute draws refitted outside the windows (port check first: with nothing left out each reproduces the table in js/sim-tables.js):
  base push   today's inputs (`base_push_fight`, s3_rates.py), without the winners' team-minutes inside a real window
  monsters    each kind's per-minute take chance (`monsters`, s3_rates.py), without the minutes inside any real window
The monster taker model and the lane tower draws are not refitted here (reported as open).
Two copies as m17: research (fit before 1 Sep; held-out from 1 Sep and Worlds) and app (games before 10 Nov).
Output: research/model/memory/m21_fight_window.json with the app block; --app also writes SIM_TABLES.window to js/sim-tables.js.
--write-app writes the app block saved in that JSON by the last full run, without refitting.
usage (repo root): python -I research/memory/m21_fight_window.py [--app | --write-app]"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, zlib
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import APP_CUT, INP, DTJ, RATES, rates, dead_intervals, dead_at, ll

OUT = config.MODEL_DIR / "memory"
CHAIN, DRAWS = 60, 20
WRITE_APP = "--app" in sys.argv[1:]
OPT = ["dragon", "elder", "baron", "herald", "grub", "inhib", "nxt", "nexus"]
MON = {"dragon", "elder", "baron", "herald", "grub"}
LANES = ("TOP", "MID", "BOT")
cl = lambda v, a, b: float(min(b, max(a, v)))
Q21 = np.linspace(0, 1, 21); q21 = lambda a: [round(float(v), 1) for v in np.quantile(a, Q21)]
def bucket(d): return "ahead 3+" if d >= 3 else "ahead 1-2" if d >= 1 else "even or behind"
BUCKETS = ["ahead 3+", "ahead 1-2", "even or behind"]

def lane_of(det):
    d = str(det)
    for L in LANES:
        if L in d: return L
    return None

def game_objects(d):
    """objectives in time order: (t, side, kind, lane) with kind in OPT or 'outer' / 'T3'"""
    out = []
    for t, sd, ty, de in zip(d.t, d.side, d.type, d.detail):
        if ty == "dragon": k = "elder" if de == "elder" else "dragon"
        elif ty in ("baron", "herald", "grub"): k = ty
        elif ty == "nexus": k = "nexus"
        elif ty == "inhib": k = "inhib"
        elif ty == "tower": k = "nxt" if "NEXUS" in str(de) else "T3" if str(de).startswith("T3") else "outer"
        else: continue
        out.append((float(t), sd, k, lane_of(de)))
    return out

class State:
    """what is up for side w at time t, from the objectives taken before t (plus extra takes in a replay)"""
    def __init__(self, objs): self.objs = objs
    def avail(self, w, t, extra=()):
        O = [o for o in self.objs if o[0] < t] + list(extra)
        # monsters
        nd, soul, em = 300.0, {"blue": 0, "red": 0}, False
        for tt, sd, k, _ in sorted([o for o in O if o[2] in ("dragon", "elder")]):
            if k == "dragon": soul[sd] += 1
            if max(soul.values()) >= 4: em = True
            nd = tt + (360 if em else 300)
        nb = 1200.0
        for tt in sorted(o[0] for o in O if o[2] == "baron"): nb = tt + 360
        A = {"dragon": (not em) and t >= nd, "elder": em and t >= nd, "baron": t >= nb,
             "herald": t >= 900 and not any(o[2] == "herald" for o in O), "grub": t >= 480 and not any(o[2] == "grub" for o in O)}
        mine = [o for o in O if o[1] == w]
        t3 = {o[3] for o in mine if o[2] == "T3"}
        inh_down = {o[3] for o in mine if o[2] == "inhib" and t - 300 < o[0]}
        nxd = min(2, sum(1 for o in mine if o[2] == "nxt" and t - 180 < o[0]))
        A["inhib"] = any(L in t3 and L not in inh_down for L in LANES)
        A["nxt"] = bool(inh_down) and nxd < 2
        A["nexus"] = bool(inh_down) and nxd >= 2
        left = (2 - nxd) + (0 if inh_down else 1)
        return A, (left if t3 else None)

def fights_of(d):
    k = d[d.type == "kill"]
    if not len(k): return []
    kt, ks = k.t.values.astype(float), k.side.values
    grp = np.cumsum(np.r_[True, np.diff(kt) > 20]); F = []
    for gi in np.unique(grp):
        m = grp == gi; nb, nr = int((ks[m] == "blue").sum()), int((ks[m] == "red").sum())
        F.append((kt[m].min(), kt[m].max(), "blue" if nb > nr else "red" if nr > nb else None))
    return F

def feats(gi, w, t, t1, j, dd, A, GD, g, bar_t, eld_t):
    o = "red" if w == "blue" else "blue"; sg = 1 if w == "blue" else -1
    back = sorted(e for s, e in dd[o] if s <= t < e)
    gd = next((GD[(g, mm)] for mm in (int(t // 60), int(t // 60) - 1) if (g, mm) in GD and GD[(g, mm)] == GD[(g, mm)]), 0.0)
    return {"own_alive": 5 - min(5, dead_at(dd[w], t)), "enemy_alive": 5 - min(5, dead_at(dd[o], t)),
            "first_back": (back[0] - t) if back else 0.0, "all_back": (back[-1] - t) if back else 0.0, "step": min(j, 2),
            "lead": cl(gd * sg / 1000, -15, 15), "z": float(gi.z) * sg, "baron_buff": int(any(t - 180 < x <= t for x in bar_t)),
            "elder_buff": int(any(t - 150 < x <= t for x in eld_t)), "min": t / 60, **{f"up_{k}": int(A[k]) for k in OPT}}

def window_rows(ns, DEAD):
    """step rows, the window team-minutes / minutes, and one row per won fight (for the replay and the real shares)"""
    ev, info, GD = ns["ev"], ns["info"], ns["GD"]
    S, F_rows, wmin_side, wmin = [], [], set(), set()
    for g, d in ev.sort_values(["gid", "t"]).groupby("gid"):
        if g not in info.index: continue
        gi = info.loc[g]; glen, gwin = float(gi.len), gi.win
        objs = game_objects(d); ST = State(objs); dd = DEAD.get(g, {"blue": [], "red": []})
        F = fights_of(d)
        for i, (t0, t1, w) in enumerate(F):
            if w is None: continue
            bar_t = [o[0] for o in objs if o[1] == w and o[2] == "baron"]; eld_t = [o[0] for o in objs if o[1] == w and o[2] == "elder"]
            nf = F[i + 1][0] if i + 1 < len(F) else 1e9
            mine = [o for o in objs if o[1] == w and t0 <= o[0] < nf]
            seq, anchor = [], t1
            for o in mine:
                if o[0] - anchor > CHAIN: break
                seq.append(o); anchor = max(anchor, o[0])
            opts = [o for o in seq if o[2] in OPT]
            A0, left0 = ST.avail(w, t0, [])   # what was up and structures left at the fight's start (as m16 / m20)
            ta, cens, j = t1, False, 0
            for jj in range(len(opts) + 1):
                y = opts[jj][2] if jj < len(opts) else "reset"
                if y == "reset":
                    if glen < min(nf, ta + CHAIN) and gwin != w: cens = True; break
                    if opts and opts[-1][2] == "nexus": break
                A, _ = State([o for o in objs if o not in opts[jj:]]).avail(w, ta + 1e-3, [])   # the window's own takes count once they fall
                if y != "reset" and not A[y]: A[y] = True   # it fell, so it was up (the timers' edges, a lane opened in the same moment)
                f = feats(gi, w, ta, t1, jj, dd, A, GD, g, bar_t, eld_t)
                S.append({"gid": g, "split": gi.split, "y": y, "dt": (opts[jj][0] - ta) if y != "reset" else None, **f})
                if y != "reset":
                    ta = max(ta, opts[jj][0])
                    if y == "nexus": break
            last = max([t1] + [o[0] for o in seq])
            for mm in range(int(t0 // 60), int(last // 60) + 1): wmin_side.add((g, mm, w)); wmin.add((g, mm))
            fa = feats(gi, w, t1, t1, 0, dd, A0, GD, g, bar_t, eld_t)
            F_rows.append({"gid": g, "fi": i, "split": gi.split, "t1": t1, "w": w, "censored": cens, "left": left0, **fa,
                           "took": [o[2] for o in opts], "took_t": [o[0] for o in opts]})
    return pd.DataFrame(S), pd.DataFrame(F_rows), wmin_side, wmin

# stage 1: take something or reset
S1N = ["intercept", "own_alive", "enemy_alive", "per_10s_until_first_back", "per_10s_until_all_back", "step 1", "step 2+", "per_1k_lead", "per_v1_logit",
       "baron_buff", "elder_buff", "from 25", "from 35"] + [f"up_{k}" for k in OPT]
def X1(d):
    return np.c_[np.ones(len(d)), d.own_alive, d.enemy_alive, d.first_back / 10, d.all_back / 10, d.step == 1, d.step == 2, d.lead, d.z,
                 d.baron_buff, d.elder_buff, d["min"] >= 25, d["min"] >= 35, *[d[f"up_{k}"] for k in OPT]].astype(float)
# stage 2: which option among those up
S2T = ["intercept", "per_alive_diff", "per_10s_until_all_back"]
def X2(d):
    """rows x options x terms; terms placed in the option's own block"""
    base = np.c_[np.ones(len(d)), (d.own_alive - d.enemy_alive), d.all_back / 10].astype(float)
    K, P = len(OPT), len(S2T); X = np.zeros((len(d), K, K * P))
    for k in range(K): X[:, k, k * P:(k + 1) * P] = base
    M = np.c_[tuple(d[f"up_{k}"].values for k in OPT)].astype(bool)
    return X, M
def clogit_fit(X, M, yi, l2=1.0, it=60):
    b = np.zeros(X.shape[2])
    for _ in range(it):
        u = np.where(M, X @ b, -np.inf); u -= u.max(1, keepdims=True); p = np.exp(u); p /= p.sum(1, keepdims=True)
        xb = np.einsum("rk,rkp->rp", p, X); xc = X[np.arange(len(yi)), yi]
        g = (xc - xb).sum(0) - l2 * b
        H = np.einsum("rk,rkp,rkq->pq", p, X, X) - np.einsum("rp,rq->pq", xb, xb) + l2 * np.eye(len(b))
        step = np.linalg.solve(H, g); b += step
        if np.abs(step).max() < 1e-8: break
    return b
def clogit_p(X, M, b):
    u = np.where(M, X @ b, -np.inf); u -= u.max(1, keepdims=True); p = np.exp(u); return p / p.sum(1, keepdims=True)
def clogit_ll(X, M, yi, b): p = clogit_p(X, M, b); return round(float(-np.mean(np.log(np.clip(p[np.arange(len(yi)), yi], 1e-9, 1)))), 5)

def fit_window(ns, S):
    lf = ns["logit_fit"]; tr = S[S.split == "train"]
    yb = lambda d: (d.y != "reset").values.astype(float)
    b1 = lf(X1(tr), yb(tr))
    T = S[S.y != "reset"]; trT = T[T.split == "train"]
    Xt, Mt = X2(trT); yi = np.array([OPT.index(v) for v in trT.y]); b2 = clogit_fit(Xt, Mt, yi)
    R = {"stage 1 coef": dict(zip(S1N, np.round(b1, 4).tolist())), "stage 2 coef": {k: dict(zip(S2T, np.round(b2[i * 3:(i + 1) * 3], 4).tolist())) for i, k in enumerate(OPT)}}
    sc = {}
    for s in ("train", "test", "worlds"):
        q = S[S.split == s]
        if not len(q): sc[s] = None; continue
        b10 = lf(X1(tr)[:, :1], yb(tr))   # intercept only (the base share)
        qT = q[q.y != "reset"]; Xq, Mq = X2(qT); yq = np.array([OPT.index(v) for v in qT.y])
        b20 = np.zeros_like(b2)          # every option up equally likely
        sc[s] = {"steps": len(q), "takes": len(qT), "stage 1 log loss (fit | base share)": [ll(X1(q), b1, yb(q)), ll(X1(q)[:, :1], b10, yb(q))],
                 "stage 2 log loss (fit | equal among those up)": [clogit_ll(Xq, Mq, yq, b2), clogit_ll(Xq, Mq, yq, b20)]}
    R["held-out scores"] = sc
    # take times by option and players alive (train)
    TT = {}
    for k in OPT:
        a = trT[trT.y == k]; TT[k] = {}
        for bkt in BUCKETS:
            v = a[(a.own_alive - a.enemy_alive).map(bucket) == bkt].dt.values
            if len(v) >= 20: TT[k][bkt] = q21(v)
        if len(a) >= 20: TT[k]["pooled"] = q21(a.dt.values)
    TT["all"] = q21(trT.dt.values)
    R["take times s (21 quantiles; option x players alive, n >= 20)"] = TT
    R["takes (train) by option x players alive"] = {k: {bkt: int(((trT.y == k) & ((trT.own_alive - trT.enemy_alive).map(bucket) == bkt)).sum()) for bkt in BUCKETS} for k in OPT}
    return R, b1, b2, TT

def tq(TT, k, bkt, u):
    q = TT.get(k, {}).get(bkt) or TT.get(k, {}).get("pooled") or TT["all"]
    x = u * 20; i = int(x); return q[min(i, 20)] if i >= 20 else q[i] + (q[i + 1] - q[i]) * (x - i)

def replay(ns, Fd, DEAD, b1, b2, TT):
    """each real won fight through the fitted window, DRAWS times; returns per fight the share of draws taking each option"""
    ev, info, GD = ns["ev"], ns["info"], ns["GD"]; objs_by = {g: game_objects(d) for g, d in ev.sort_values(["gid", "t"]).groupby("gid")}
    out = []
    for r in Fd.itertuples():
        if r.censored: continue
        g = r.gid; gi = info.loc[g]; objs = objs_by[g]; ST = State(objs); dd = DEAD.get(g, {"blue": [], "red": []}); w = r.w; o = "red" if w == "blue" else "blue"
        bar_t = [x[0] for x in objs if x[1] == w and x[2] == "baron"]; eld_t = [x[0] for x in objs if x[1] == w and x[2] == "elder"]
        rng = np.random.default_rng(zlib.crc32(f"{g}|{int(r.fi)}".encode())); cnt = {k: 0 for k in OPT}
        tk_set = set(r.took_t)
        before = [x for x in objs if x[0] < r.t1 + 1e-3 and not (x[1] == w and x[2] in OPT and x[0] in tk_set)]
        for _ in range(DRAWS):
            ta, extra, took = r.t1, [], set()
            for j in range(8):
                A, _ = State(before).avail(w, ta + 1e-3, extra)
                if not any(A.values()): break
                f = pd.DataFrame([feats(gi, w, ta, r.t1, j, dd, A, GD, g, bar_t, eld_t)])
                if rng.random() >= 1 / (1 + np.exp(-(X1(f) @ b1)[0])): break
                X, M = X2(f); p = clogit_p(X, M, b2)[0]; k = OPT[rng.choice(len(OPT), p=p)]
                bkt = bucket(f.own_alive[0] - f.enemy_alive[0]); tk = ta + tq(TT, k, bkt, rng.random())
                if k == "nexus":
                    back = max([e for s, e in dd[o] if s <= ta < e], default=ta)
                    if tk >= back: break
                    took.add(k); break
                took.add(k); lane = None
                if k == "inhib":
                    t3 = {x[3] for x in before + extra if x[1] == w and x[2] == "T3"}; dn = {x[3] for x in before + extra if x[1] == w and x[2] == "inhib" and tk - 300 < x[0]}
                    lane = next((L for L in LANES if L in t3 and L not in dn), None)
                extra.append((max(ta, tk), w, k, lane)); ta = max(ta, tk)
            for k in took: cnt[k] += 1
        out.append({"split": r.split, "left": r.left, "bucket": bucket(r.own_alive - r.enemy_alive), **{f"up_{k}": getattr(r, f"up_{k}") for k in ("dragon", "baron")},
                    **{f"sim_{k}": cnt[k] / DRAWS for k in OPT}, **{f"real_{k}": int(k in r.took) for k in OPT}})
    D = pd.DataFrame(out); res = {}
    for s in ("train", "test", "worlds"):
        q = D[D.split == s]
        if not len(q): continue
        T_ = {}
        for L in range(4):
            for bkt in BUCKETS:
                z = q[(q.left == L) & (q.bucket == bkt)]
                if len(z): T_[f"Nexus, {L} left, {bkt}"] = [len(z), round(float(z.real_nexus.mean()), 3), round(float(z.sim_nexus.mean()), 3)]
        for k in ("baron", "dragon"):
            for bkt in BUCKETS:
                z = q[(q[f"up_{k}"] == 1) & (q.bucket == bkt)]
                if len(z): T_[f"{k} when up, {bkt}"] = [len(z), round(float(z[f"real_{k}"].mean()), 3), round(float(z[f"sim_{k}"].mean()), 3)]
        T_["any objective"] = [len(q), round(float(q[[f"real_{k}" for k in OPT]].max(1).mean()), 3), None]
        res[s] = T_
    return res

def minute_base(ns, B):
    lf, Xb, fight_terms, cB = ns["logit_fit"], ns["Xb"], ns["fight_terms"], ns["res"]["base_push_fight"]["clear_fight_cutoff"]
    names0 = [n if n != "siege_style" else "siege_style_sum" for n in ns["names_b"]] + ["net_kills_last_minute"] + (["clear_fight_win"] if cB is not None else [])
    X = lambda d: np.c_[Xb(d), fight_terms(d, cB)]; y = lambda d: (d.y.values > 0).astype(float); tr = B[B.split == "train"]; b = lf(X(tr), y(tr))
    return {"coef": dict(zip(names0, np.round(b, 4).tolist())), "clear_fight_cutoff": cB, "n": {s: int((B.split == s).sum()) for s in ("train", "test", "worlds")},
            **{f"log loss {s}": ll(X(B[B.split == s]), b, y(B[B.split == s])) if (B.split == s).any() else None for s in ("test", "worlds")}}, X, b, y

MNAMES = ["intercept", "spawn_minute", "1_min_after", "4+_min_after", "per_1k_abs_lead", "fight_this_minute", "first_dragon", "objectives_style_sum"]
def minute_monsters(ns, Mo):
    lf = ns["logit_fit"]; out = {}
    X = lambda q: np.c_[np.ones(len(q)), (q.since == 0), (q.since == 1), (q.since >= 4), q.alead.clip(0, 15), q.fight, q["first"], q.obj_s].astype(float)
    for k in ["dragon", "grub", "herald", "baron", "elder"]:
        d = Mo[Mo.kind == k]; trd = d[d.split == "train"]
        if len(trd) < 40: continue
        b = lf(X(trd), trd.y.values, l2=2.0)
        out[k] = {"coef": dict(zip(MNAMES, np.round(b, 4).tolist())), "minutes_up": len(d), "taken": int(d.y.sum()),
                  **{f"log loss {s}": ll(X(d[d.split == s]), b, d[d.split == s].y.values.astype(float)) if (d.split == s).sum() > 5 else None for s in ("test", "worlds")}}
    return out

def app_tables():
    js = (config.ROOT / "js" / "sim-tables.js").read_text(encoding="utf-8")
    bp = json.loads(re.search(r'"base_push_fight":\{"coef":(\{[^}]*\})', js).group(1))
    mo = {k: json.loads(re.search(r'"monsters":\{.*?"' + k + r'":(\{[^}]*\})', js).group(1)) for k in ["dragon", "grub", "herald", "baron", "elder"]}
    return bp, mo
def diffs(a, b): return {k: round(a.get(k, float("nan")) - v, 4) for k, v in b.items()}

def main():
    with Run("memory_fight_window", params={"app_cut": APP_CUT, "split": config.SPLIT, "chain_s": CHAIN, "replay_draws": DRAWS, "ridge": 1.0, "write_app": WRITE_APP},
             inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, *[p for c in INP.values() for p in (c["v1"], c["comp"])]]) as run:
        o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
        XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
        DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
        R = {"source": "research/memory/m21_fight_window.py (27 Nov 2026 AEST)", "chain_s": CHAIN, "options": OPT}
        for copy in ("research", "app"):
            ns = rates(copy, tag="m21"); info, ev = ns["info"], ns["ev"]
            if copy == "app": ns["ev"] = ev = ev[ev.gid.map(info.date) < APP_CUT]; ns["info"] = info = info[info.date < APP_CUT]
            DEAD, matched = dead_intervals(info, ev, XP, AVG, DT)
            S, Fd, wms, wm = window_rows(ns, DEAD)
            C = {"deaths matched to the file's XP": matched, "won fights": len(Fd), "censored (base race)": int(Fd.censored.sum()),
                 "step rows by split": {s: int((S.split == s).sum()) for s in ("train", "test", "worlds")},
                 "steps (train) by next": S[S.split == "train"].y.value_counts().to_dict()}
            W, b1, b2, TT = fit_window(ns, S)
            W["replay (no sim): fights, real share, fitted share"] = replay(ns, Fd, DEAD, b1, b2, TT)
            B = ns["BASE"]; keepB = np.array([(g, m, s) not in wms for g, m, s in zip(B.gid, B.m, B.side)])
            Mo = ns["Mo"]; keepM = np.array([(g, m) not in wm for g, m in zip(Mo.gid, Mo.m)])
            fullB, XfB, bfB, yB = minute_base(ns, B); exB, XeB, beB, _ = minute_base(ns, B[keepB]); Bk = B[keepB]
            exB["held-out log loss outside windows (refit | fit on all rows)"] = {s: [ll(XeB(Bk[Bk.split == s]), beB, yB(Bk[Bk.split == s])), ll(XfB(Bk[Bk.split == s]), bfB, yB(Bk[Bk.split == s]))] if (Bk.split == s).any() else None for s in ("test", "worlds")}
            R[copy] = {"counts": C, "window": W, "base push, all rows (port check)": fullB, "base push, outside windows": exB, "base team-minutes left out": int((~keepB).sum()),
                       "monsters, all rows (port check)": minute_monsters(ns, Mo), "monsters, outside windows": minute_monsters(ns, Mo[keepM]), "monster minutes left out": int((~keepM).sum()),
                       "monster minutes": len(Mo)}
        bp, mo = app_tables(); A = R["app"]
        R["port check"] = {"base_push_fight (differences)": diffs(A["base push, all rows (port check)"]["coef"], bp),
                           "monsters (differences)": {k: diffs(A["monsters, all rows (port check)"][k]["coef"], v) for k, v in mo.items() if k in A["monsters, all rows (port check)"]}}
        R["port check"]["identical"] = {"base push": all(abs(v) < 1e-9 for v in R["port check"]["base_push_fight (differences)"].values()),
                                        "monsters": all(abs(v) < 1e-9 for d_ in R["port check"]["monsters (differences)"].values() for v in d_.values())}
        block = {"cutoff": APP_CUT, "source": f"research/memory/m21_fight_window.py, gol.gg timelines before {APP_CUT}", "chain_s": CHAIN, "options": OPT,
                 "stage1": A["window"]["stage 1 coef"], "stage2": A["window"]["stage 2 coef"], "take_q": A["window"]["take times s (21 quantiles; option x players alive, n >= 20)"],
                 "base_push": {k: A["base push, outside windows"][k] for k in ("coef", "clear_fight_cutoff")},
                 "monsters": {k: v["coef"] for k, v in A["monsters, outside windows"].items()}}
        R["app block"] = block
        if WRITE_APP: write_app(block)
        run.result("port identical", R["port check"]["identical"])
        for s in ("test", "worlds"): run.result(f"research {s} scores", R["research"]["window"]["held-out scores"][s])
        run.save_json(OUT / "m21_fight_window.json", R)
        print(json.dumps(R["port check"], indent=1))
        for c in ("research", "app"):
            print(c, json.dumps({"counts": R[c]["counts"], "scores": R[c]["window"]["held-out scores"], "replay": R[c]["window"]["replay (no sim): fights, real share, fitted share"]}, indent=1))

def write_app(block):
    JS = config.ROOT / "js" / "sim-tables.js"
    START, END = "/* fight window tables: BUILT BY research/memory/m21_fight_window.py, never edit by hand */", "/* end fight window tables */"
    txt = f"{START}\nwindow.SIM_TABLES.window = {json.dumps(block, separators=(',', ':'))};\n{END}\n"
    js = JS.read_text(encoding="utf-8"); js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + txt
    tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)

if __name__ == "__main__":
    if "--write-app" in sys.argv[1:]:   # write the app block saved by the last full run (no refit; the run record names that run)
        write_app(json.load(open(OUT / "m21_fight_window.json", encoding="utf-8"))["app block"])
    else: main()
