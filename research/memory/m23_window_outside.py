"""Fight-window model outside windows: a test (28 Nov 2026 AEST; Luke: "Use the window model" for the base push's untakeable Nexus tower,
"Just test first"). The fix planned for v56 (structure_rules) would ask the fight-window model (m21, fitted only on the steps after real
won fights) what a team does next in a base push OUTSIDE a won fight's window. This checks that use on real games before it is built.
  real rows  pushes outside windows: a base structure (T3 tower, inhibitor, nexus tower) that a side takes outside every one of its own
             won-fight windows (m21's window: the fight's start to its last chained objective) starts a chain; each "what next?" is a row
             (an option, as m21, or reset), chained CHAIN = 60 s from the previous event and stopped at the next fight's start, exactly
             as m21 reads windows, with the anchor's time in place of the fight's last kill. Steps count from 1 (the anchor is a take).
             A structure already in an earlier chain does not start a new one. Resets dropped (censored) as m21 (a base race).
  inputs     m21's own (feats): players alive each side, seconds until the first / last dead enemy is back (official timers), step,
             gold lead, v1, buffs, game time, what is up.
  scores     research copy (window model fit before 1 Sep, as m21), held out from 1 Sep and on Worlds; on the outside rows:
             stage 1 (take or reset): window model | base share (intercept fitted on outside train rows) | same terms refitted on
             outside train rows (the best this model form can do there);
             stage 2 (which option): window model | equal among those up | refit;
             and the real v fitted take share when an inhibitor is up, by enemies alive (the case the fix would decide).
Pass rule (agreed in chat, 28 Nov): the window model beats the base share on both held-out sets; else report to Luke.
Output: research/model/memory/m23_window_outside.json and a run record. No app file is touched.
usage (repo root): python -I research/memory/m23_window_outside.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import INP, DTJ, RATES, rates, dead_intervals, ll
import m21_fight_window as F

OUT = config.MODEL_DIR / "memory"
BASE = {"T3", "inhib", "nxt"}

def window_spans(objs, Fl):
    """each side's won-fight windows as (start, end) seconds, read as m21.window_rows does"""
    sp = {"blue": [], "red": []}
    for i, (t0, t1, w) in enumerate(Fl):
        if w is None: continue
        nf = Fl[i + 1][0] if i + 1 < len(Fl) else 1e9
        anchor, last = t1, t1
        for o in [o for o in objs if o[1] == w and t0 <= o[0] < nf]:
            if o[0] - anchor > F.CHAIN: break
            anchor = max(anchor, o[0]); last = max(last, o[0])
        sp[w].append((t0, last))
    return sp

def outside_rows(ns, DEAD):
    ev, info, GD = ns["ev"], ns["info"], ns["GD"]
    S, n_anchor = [], {"anchors": 0, "anchors inside a window (skipped)": 0}
    for g, d in ev.sort_values(["gid", "t"]).groupby("gid"):
        if g not in info.index: continue
        gi = info.loc[g]; glen, gwin = float(gi.len), gi.win
        objs = F.game_objects(d); Fl = F.fights_of(d); dd = DEAD.get(g, {"blue": [], "red": []}); sp = window_spans(objs, Fl)
        fstarts = sorted(f[0] for f in Fl)
        for w in ("blue", "red"):
            bar_t = [o[0] for o in objs if o[1] == w and o[2] == "baron"]; eld_t = [o[0] for o in objs if o[1] == w and o[2] == "elder"]
            used = set()
            for a in [o for o in objs if o[1] == w and o[2] in BASE]:
                if a in used: continue
                if any(s0 <= a[0] <= s1 for s0, s1 in sp[w]): n_anchor["anchors inside a window (skipped)"] += 1; continue
                n_anchor["anchors"] += 1; used.add(a)
                nf = next((t for t in fstarts if t > a[0]), 1e9)
                seq, anchor = [], a[0]
                for o in [o for o in objs if o[1] == w and a[0] < o[0] < nf]:
                    if o[0] - anchor > F.CHAIN: break
                    seq.append(o); anchor = max(anchor, o[0])
                used.update(o for o in seq if o[2] in BASE)
                opts = [o for o in seq if o[2] in F.OPT]
                ta = a[0]
                for jj in range(len(opts) + 1):
                    y = opts[jj][2] if jj < len(opts) else "reset"
                    if y == "reset":
                        if glen < min(nf, ta + F.CHAIN) and gwin != w: break
                        if opts and opts[-1][2] == "nexus": break
                    A, _ = F.State([o for o in objs if o not in opts[jj:]]).avail(w, ta + 1e-3, [])
                    if y != "reset" and not A[y]: A[y] = True
                    f = F.feats(gi, w, ta, a[0], jj + 1, dd, A, GD, g, bar_t, eld_t)
                    S.append({"gid": g, "split": gi.split, "y": y, **f})
                    if y != "reset":
                        ta = max(ta, opts[jj][0])
                        if y == "nexus": break
    return pd.DataFrame(S), n_anchor

def scores(ns, Sw, So):
    lf = ns["logit_fit"]; yb = lambda d: (d.y != "reset").values.astype(float)
    trw = Sw[Sw.split == "train"]; b1 = lf(F.X1(trw), yb(trw))
    Tw = Sw[(Sw.y != "reset") & (Sw.split == "train")]; Xt, Mt = F.X2(Tw); b2 = F.clogit_fit(Xt, Mt, np.array([F.OPT.index(v) for v in Tw.y]))
    tro = So[So.split == "train"]; b1o = lf(F.X1(tro), yb(tro)); b10 = lf(F.X1(tro)[:, :1], yb(tro))
    To = So[(So.y != "reset") & (So.split == "train")]; Xo, Mo = F.X2(To); b2o = F.clogit_fit(Xo, Mo, np.array([F.OPT.index(v) for v in To.y]))
    R = {}
    for s in ("test", "worlds"):
        q = So[So.split == s]
        if not len(q): R[s] = None; continue
        qT = q[q.y != "reset"]; Xq, Mq = F.X2(qT); yq = np.array([F.OPT.index(v) for v in qT.y])
        p1 = 1 / (1 + np.exp(-F.X1(q) @ b1))
        inh = q[q.up_inhib == 1]; p_in = []
        if len(inh):   # chance the next step takes an inhibitor: stage 1 x stage 2 share of "inhib"
            X2i, M2i = F.X2(inh); pc = F.clogit_p(X2i, M2i, b2)[:, F.OPT.index("inhib")]; ps = 1 / (1 + np.exp(-F.X1(inh) @ b1)); p_in = ps * pc
        tab = {}
        for ea in range(6):
            m = (inh.enemy_alive == ea).values if len(inh) else np.array([], bool)
            if m.sum(): tab[f"{ea} enemies alive"] = [int(m.sum()), round(float((inh.y.values[m] == "inhib").mean()), 3), round(float(p_in[m].mean()), 3)]
        R[s] = {"steps": len(q), "takes": len(qT), "real take share": round(float(yb(q).mean()), 3), "window model's mean take chance": round(float(p1.mean()), 3),
                "stage 1 log loss (window model | base share | refit outside)": [ll(F.X1(q), b1, yb(q)), ll(F.X1(q)[:, :1], b10, yb(q)), ll(F.X1(q), b1o, yb(q))],
                "stage 2 log loss (window model | equal among up | refit outside)": [F.clogit_ll(Xq, Mq, yq, b2), F.clogit_ll(Xq, Mq, yq, np.zeros_like(b2)), F.clogit_ll(Xq, Mq, yq, b2o)] if len(qT) else None,
                "inhibitor up: steps, real share taking it next, window model's chance (by enemies alive)": tab}
        R[s]["pass (window model beats base share, stage 1)"] = R[s]["stage 1 log loss (window model | base share | refit outside)"][0] < R[s]["stage 1 log loss (window model | base share | refit outside)"][1]
    R["stage 1 coef: window model | refit outside"] = {"window": dict(zip(F.S1N, np.round(b1, 4).tolist())), "outside": dict(zip(F.S1N, np.round(b1o, 4).tolist()))}
    return R

def main():
    with Run("memory_window_outside", params={"split": config.SPLIT, "chain_s": F.CHAIN, "ridge": 1.0, "copy": "research"},
             inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, INP["research"]["v1"], INP["research"]["comp"]]) as run:
        o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
        XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
        DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
        ns = rates("research", tag="m23")
        DEAD, matched = dead_intervals(ns["info"], ns["ev"], XP, AVG, DT)
        Sw, _, _, _ = F.window_rows(ns, DEAD)
        So, na = outside_rows(ns, DEAD)
        R = {"source": "research/memory/m23_window_outside.py (28 Nov 2026 AEST)", "deaths matched": matched,
             "window step rows by split": {s: int((Sw.split == s).sum()) for s in ("train", "test", "worlds")},
             "outside rows by split": {s: int((So.split == s).sum()) for s in ("train", "test", "worlds")}, **na,
             "outside steps (all) by next": So.y.value_counts().to_dict(), "scores": scores(ns, Sw, So)}
        for s in ("test", "worlds"): run.result(f"{s}", R["scores"][s])
        run.save_json(OUT / "m23_window_outside.json", R)
        print(json.dumps(R, indent=1))

if __name__ == "__main__": main()
