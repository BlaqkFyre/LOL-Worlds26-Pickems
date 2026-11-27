"""Push continuation after a won fight, part A: the fit (27 Nov 2026 AEST; Luke OK'd research/memory/push-continuation-plan.md part A,
"Yes to 1 and 2": a fitted step after a won fight, and the per-minute base push refitted without the fight-push minutes).
Real won fights (gol.gg timelines; kills under 20 s apart, the side with more kills wins; the winner has a T3 tower down at the fight's
start, as m16_nexus_push.py) and the winner's base structures (inhibitor, nexus tower, Nexus) that follow:
  push      the base structures from the fight's start, each within CHAIN s of the push's previous event (the fight's last kill for the
            first), before the next fight starts. CHAIN = 60 s: real base structures after a won fight stop coming then (gaps over 45 s:
            28 of 1,584, over 60 s: 25, over 90 s: 21; the 99th percentile gap is 96 s), and it matches the under-60 s base gap tables
            and the real Nexus never coming 60 s+ after the last kill. 45 / 90 s and the plan's 120 s from the last kill are reported.
  step      one row per "does the push take the next base structure?": y = 1 if it does. The push ends at the first no or at the Nexus.
            A no is dropped (censored) when the game ends inside that step's window and the fight's winner did not win the game
            (a base race: EWC 2026 semi-final game 3, T1 at 0 left 37:58-38:10, Karmine Corp's Nexus at 38:23).
  inputs    at the step's moment (the last kill, then each structure's time): structures left to the Nexus now (as m17, counting the
            push's structures already taken), enemies and own dead now (official timer, as m17), seconds since the last kill (per 10 s),
            the step (0, 1, 2+), gold lead, v1 logit, baron and elder (taken in the last 180 / 150 s), and the fight's kill margin (step 0).
Per-minute base push (m17's v2 inputs, the same choices on training halves) refitted on the team-minutes outside real fight pushes
(the winner's minutes from the fight's start to its push's last structure). Port check first: the same fit with nothing left out gives
SIM_TABLES.base.coef in js/sim-tables.js exactly (app copy).
Replay check (no sim): every real won fight's chance of the Nexus in its push from the fitted steps, walking left down one per step at
the real median step time, with the real death intervals; mean by structures left at the fight's start against the real share.
Two copies as m17: research (fit before 1 Sep; held-out log loss from 1 Sep and Worlds) and app (games before 10 Nov).
Output: research/model/memory/m19_push_continue.json with the app block; --app also writes SIM_TABLES.base_continue to js/sim-tables.js.
usage (repo root): python -I research/memory/m19_push_continue.py [--app]"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import (APP_CUT, INP, DTJ, RATES, rates, dead_intervals, dead_at, structures, left_at, add_state, extra, names_extra, ll)

OUT = config.MODEL_DIR / "memory"
CHAIN, ALT_CHAINS, CAP = 60, (45, 90), 120
WRITE_APP = "--app" in sys.argv[1:]
BASEK = ("inhib", "nxt", "nexus")
cl = lambda v, a, b: float(min(b, max(a, v)))

def won_fights(d):
    k = d[d.type == "kill"]
    if not len(k): return []
    kt, ks = k.t.values.astype(float), k.side.values
    grp = np.cumsum(np.r_[True, np.diff(kt) > 20]); F = []
    for gi in np.unique(grp):
        m = grp == gi; nb, nr = int((ks[m] == "blue").sum()), int((ks[m] == "red").sum())
        F.append((kt[m].min(), kt[m].max(), "blue" if nb > nr else "red" if nr > nb else None, abs(nb - nr)))
    return F

def step_rows(ns, ST, DEAD, chain=CHAIN, cap=None):
    """step rows, the winner's fight-push team-minutes, and one row per won fight (for the replay)"""
    ev, info, GD = ns["ev"], ns["info"], ns["GD"]
    rows, pmin, fights = [], set(), []
    for g, d in ev.sort_values(["gid", "t"]).groupby("gid"):
        if g not in info.index: continue
        gi = info.loc[g]; glen, gwin = float(gi.len), gi.win
        bar = d[d.type == "baron"]; eld = d[(d.type == "dragon") & (d.detail == "elder")]
        F = won_fights(d)
        for i, (t0, t1, w, mg) in enumerate(F):
            if w is None: continue
            o = "red" if w == "blue" else "blue"; st = ST.get((g, w), [])
            if not any(kd == "T3" and x < t0 for x, kd in st): continue      # lane closed at the fight's start
            nf = F[i + 1][0] if i + 1 < len(F) else 1e9
            base = [(x, kd) for x, kd in st if kd in BASEK and t0 <= x < nf]
            seq, anchor = [], t1
            for x, kd in base:
                if (x - t1 > cap) if cap is not None else (x - anchor > chain): break
                seq.append((x, kd)); anchor = max(anchor, x)
            sg = 1 if w == "blue" else -1; dd = DEAD.get(g, {"blue": [], "red": []})
            gd = lambda t: next((GD[(g, mm)] for mm in (int(t // 60), int(t // 60) - 1) if (g, mm) in GD and GD[(g, mm)] == GD[(g, mm)]), 0.0)
            ta, cens, L0 = t1, False, left_at(st, t0)
            for j in range(len(seq) + 1):
                y = 1 if j < len(seq) else 0
                if not y:
                    lim = min(nf, ta + chain) if cap is None else min(nf, t1 + cap)
                    if glen < lim and gwin != w: cens = True; break
                    if seq and seq[-1][1] == "nexus": break
                taken = [s for s in st if s not in seq[j:]]
                rows.append({"gid": g, "split": gi.split, "y": y, "left": left_at(taken, ta + 1e-3), "L0": L0, "step": min(j, 2),
                             "en": min(5, dead_at(dd[o], ta)), "own": min(5, dead_at(dd[w], ta)), "since": max(0.0, ta - t1),
                             "lead": cl(gd(ta) * sg / 1000, -15, 15), "z": float(gi.z) * sg,
                             "baron": int(((bar.side == w) & (bar.t > ta - 180) & (bar.t <= ta)).any()),
                             "elder": int(((eld.side == w) & (eld.t > ta - 150) & (eld.t <= ta)).any()), "margin": cl(mg, 0, 5) if j == 0 else 0.0,
                             "dt": (max(ta, seq[j][0]) - ta) if y else None})
                if y:
                    ta = max(ta, seq[j][0])
                    if seq[j][1] == "nexus": break
            last = seq[-1][0] if seq else t1
            for mm in range(int(t0 // 60), int(last // 60) + 1): pmin.add((g, mm, w))
            fights.append({"gid": g, "split": gi.split, "t1": t1, "w": w, "L0": L0, "nexus": any(kd == "nexus" for x, kd in seq), "censored": cens,
                           "lead": cl(gd(t1) * sg / 1000, -15, 15), "z": float(gi.z) * sg, "margin": cl(mg, 0, 5),
                           "baron": int(((bar.side == w) & (bar.t > t1 - 180) & (bar.t <= t1)).any()), "elder": int(((eld.side == w) & (eld.t > t1 - 150) & (eld.t <= t1)).any()),
                           "left1": left_at([s for s in st if s not in seq], t1 + 1e-3)})   # structures left at step 0, as the step rows count it
    return pd.DataFrame(rows), pmin, pd.DataFrame(fights)

GROUPS = {"step": (lambda d, f: np.c_[(d.step == 1), (d.step == 2)].astype(float), ["step 1", "step 2+"]),
          "dead": (lambda d, f: np.c_[d.en, d.own].astype(float), ["enemies_dead_now", "own_dead_now"]),
          "since": (lambda d, f: (d.since.values / 10.0)[:, None], ["per_10s_since_last_kill"]),
          "game state": (lambda d, f: np.c_[d.lead, d.z, d.baron, d.elder].astype(float), ["per_1k_lead", "per_v1_logit", "baron", "elder"]),
          "margin": (lambda d, f: d.margin.values[:, None].astype(float), ["fight_kill_margin_step0"])}
def left_cols(d, form): return d.left.values[:, None].astype(float) if form == "linear" else np.c_[tuple((d.left.values == L).astype(float) for L in (0, 1, 2))]
def left_names(form): return ["structures_left"] if form == "linear" else ["left 0", "left 1", "left 2"]
def SX(d, form, groups):
    c = [np.ones((len(d), 1)), left_cols(d, form)] + [GROUPS[k][0](d, form) for k in groups]
    return np.c_[tuple(c)]
def SN(form, groups): return ["intercept"] + left_names(form) + sum((GROUPS[k][1] for k in groups), [])

def fit_steps(ns, S):
    logit_fit = ns["logit_fit"]; tr = S[S.split == "train"]; y = lambda d: d.y.values.astype(float)
    early = (tr.gid.map(ns["info"].date) < ns["CUTD"]).values; E, Lt = tr[early], tr[~early]; ALL = list(GROUPS)
    ch = {form: ll(SX(Lt, form, ALL), logit_fit(SX(E, form, ALL), y(E)), y(Lt)) for form in ("linear", "dummies")}
    form = "linear" if ch["linear"] <= ch["dummies"] else "dummies"
    V = {"left + step": ["step"], **{f"left + step + {k}": ["step", k] for k in ALL if k != "step"}, "all": ALL}
    R = {}
    for k, gs in V.items():
        b = logit_fit(SX(tr, form, gs), y(tr))
        R[k] = {"coef": dict(zip(SN(form, gs), np.round(b, 4).tolist())),
                **{s: {"n": int((S.split == s).sum()), "logloss": ll(SX(S[S.split == s], form, gs), b, y(S[S.split == s])) if (S.split == s).any() else None} for s in ("train", "test", "worlds")}}
    b_all = logit_fit(SX(tr, form, ALL), y(tr))
    return {"choice": {"split_date": ns["CUTD"], "n_fit": int(early.sum()), "n_check": int((~early).sum()), "later-half log loss": ch, "left form": form},
            "versions": R, "form": form}, b_all

def replay(Fd, ST_, DEAD, form, b, dt_med):
    """each real won fight's chance of the Nexus in its push, from the fitted steps (left down one per step, real median step time)"""
    out = []
    for r in Fd.itertuples():
        if r.censored: continue
        o = "red" if r.w == "blue" else "blue"; dd = DEAD.get(r.gid, {"blue": [], "red": []}); p = 1.0; L = int(r.left1)
        for j in range(L + 1):
            ta = r.t1 + j * dt_med
            row = pd.DataFrame([{"left": L - j, "step": min(j, 2), "en": min(5, dead_at(dd[o], ta)), "own": min(5, dead_at(dd[r.w], ta)), "since": j * dt_med,
                                 "lead": r.lead, "z": r.z, "baron": r.baron, "elder": r.elder, "margin": r.margin if j == 0 else 0.0}])
            p *= float(1 / (1 + np.exp(-SX(row, form, list(GROUPS)) @ b))[0])
        out.append({"split": r.split, "L0": r.L0, "p": p, "real": int(r.nexus)})
    D = pd.DataFrame(out); res = {}
    for s in ("train", "test", "worlds"):
        q = D[D.split == s]
        res[s] = {str(L): {"won fights": int((q.L0 == L).sum()), "real Nexus share": round(float(q[q.L0 == L].real.mean()), 3) if (q.L0 == L).any() else None,
                           "fitted chance (mean)": round(float(q[q.L0 == L].p.mean()), 3) if (q.L0 == L).any() else None} for L in range(4)}
    return res

def minute_fit(ns, B):
    """m17's per-minute fit (today's inputs + the v2 terms, left form and interaction chosen on training halves) on rows B"""
    logit_fit, Xb, fight_terms, cB = ns["logit_fit"], ns["Xb"], ns["fight_terms"], ns["res"]["base_push_fight"]["clear_fight_cutoff"]
    names0 = [n if n != "siege_style" else "siege_style_sum" for n in ns["names_b"]] + ["net_kills_last_minute"] + (["clear_fight_win"] if cB is not None else [])
    y = lambda d: (d.y.values > 0).astype(float); X0 = lambda d: np.c_[Xb(d), fight_terms(d, cB)]
    tr = B[B.split == "train"]; early = (tr.gid.map(ns["info"].date) < ns["CUTD"]).values; E, Lt = tr[early], tr[~early]; ch = {}
    for form in ("linear", "dummies"):
        for inter in (False, True):
            X = lambda d: np.c_[X0(d), extra(d, form, inter)]
            ch[f"{form}{' + interaction' if inter else ''}"] = ll(X(Lt), logit_fit(X(E), y(E)), y(Lt))
    form = "linear" if ch["linear"] <= ch["dummies"] else "dummies"; inter = ch[f"{form} + interaction"] < ch[form]
    X = lambda d: np.c_[X0(d), extra(d, form, inter)]; b = logit_fit(X(tr), y(tr))
    return {"coef": dict(zip(names0 + names_extra(form, inter), np.round(b, 4).tolist())), "left_form": form, "interaction": bool(inter), "clear_fight_cutoff": cB,
            "choice later-half log loss": ch, "n": {s: int((B.split == s).sum()) for s in ("train", "test", "worlds")}}, X, b, y

def app_base_coef():
    js = (config.ROOT / "js" / "sim-tables.js").read_text(encoding="utf-8")
    m = re.search(r'window\.SIM_TABLES\.base = (\{.*?\});\n', js); return json.loads(m.group(1))["coef"]

def counts(S, Fd):
    tr = S[S.split == "train"]; ft = Fd[Fd.split == "train"]
    return {"step rows (train) by structures left now x step": {f"{L} left": {f"step {k}": int(((tr.left == L) & (tr.step == k)).sum()) for k in (0, 1, 2)} for L in range(4)},
            "step rows by split": {s: int((S.split == s).sum()) for s in ("train", "test", "worlds")},
            "won fights (train) by structures left at the fight's start": {str(L): int((ft.L0 == L).sum()) for L in range(4)},
            "censored (base race) won fights, all splits": int(Fd.censored.sum())}

def real_share(Fd):
    q = Fd[~Fd.censored]; return {str(L): [int((q.L0 == L).sum()), round(float(q[q.L0 == L].nexus.mean()), 3) if (q.L0 == L).any() else None] for L in range(4)}

with Run("memory_push_continue", params={"app_cut": APP_CUT, "split": config.SPLIT, "chain_s": CHAIN, "alt_chains": list(ALT_CHAINS), "cap_alt": CAP, "ridge": 1.0, "write_app": WRITE_APP},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, *[p for c in INP.values() for p in (c["v1"], c["comp"])]]) as run:
    o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
    XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
    DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
    R = {"source": "research/memory/m19_push_continue.py (27 Nov 2026 AEST)", "chain_s": CHAIN}
    for copy in ("research", "app"):
        ns = rates(copy); info, ev = ns["info"], ns["ev"]
        if copy == "app": ns["ev"] = ev = ev[ev.gid.map(info.date) < APP_CUT]; ns["info"] = info = info[info.date < APP_CUT]
        ST = structures(ev); DEAD, matched = dead_intervals(info, ev, XP, AVG, DT)
        S, pmin, Fd = step_rows(ns, ST, DEAD)
        C = {"deaths matched to the file's XP": matched, **counts(S, Fd), "real Nexus share by structures left (won fights, share), chain 60 s": real_share(Fd)}
        for ch_ in ALT_CHAINS:
            S2, pm2, F2 = step_rows(ns, ST, DEAD, chain=ch_); C[f"chain {ch_} s"] = {"step rows": len(S2), "fight-push minutes": len(pm2), "real Nexus share by structures left": real_share(F2)}
        S3, pm3, F3 = step_rows(ns, ST, DEAD, cap=CAP); C[f"window {CAP} s from the last kill (the plan's first reading)"] = {"step rows": len(S3), "fight-push minutes": len(pm3), "real Nexus share by structures left": real_share(F3)}
        fs, b_all = fit_steps(ns, S)
        dt_med = float(np.median(S[(S.split == "train") & (S.y == 1)].dt.dropna()))
        fs["replay (no sim)"] = replay(Fd, ST, DEAD, fs["form"], b_all, dt_med); fs["replay step time s (median, train)"] = dt_med
        # per-minute base push: full rows (the port check) and without the fight-push minutes
        B = add_state(ns["BASE"], ST, DEAD)
        keep = np.array([(g, m, s) not in pmin for g, m, s in zip(B.gid, B.m, B.side)])
        full, Xf, bf, yb = minute_fit(ns, B); ex, Xe, be, _ = minute_fit(ns, B[keep])
        Bk = B[keep]
        ex["held-out log loss on rows outside fight pushes (refit | v2 fit on all rows)"] = {s: [ll(Xe(Bk[Bk.split == s]), be, yb(Bk[Bk.split == s])), ll(Xf(Bk[Bk.split == s]), bf, yb(Bk[Bk.split == s]))] if (Bk.split == s).any() else None for s in ("train", "test", "worlds")}
        ex["push start share outside fight pushes by structures left (train)"] = {str(L): [round(float((q.y > 0).mean()), 3), len(q)] for L, q in Bk[Bk.split == "train"].groupby("left")}
        R[copy] = {"counts": C, "steps": fs, "per-minute, all rows (port check)": full, "per-minute, outside fight pushes": ex, "fight-push team-minutes left out": int((~keep).sum())}
    inapp = app_base_coef(); ref = R["app"]["per-minute, all rows (port check)"]["coef"]
    diff = {k: round(ref.get(k, float("nan")) - v, 4) for k, v in inapp.items()}
    R["port check"] = {"app copy, per-minute fit on all rows v SIM_TABLES.base.coef (differences)": diff, "identical": all(abs(v) < 1e-9 for v in diff.values()) and set(ref) == set(inapp)}
    A = R["app"]
    block = {"cutoff": APP_CUT, "source": f"research/memory/m19_push_continue.py, gol.gg timelines before {APP_CUT}", "chain_s": CHAIN,
             "step": {"coef": A["steps"]["versions"]["all"]["coef"], "left_form": A["steps"]["form"], "since_unit_s": 10, "margin_cap": 5},
             "minute": {k: A["per-minute, outside fight pushes"][k] for k in ("coef", "left_form", "interaction", "clear_fight_cutoff")}}
    R["app block"] = block
    if WRITE_APP:
        JS = config.ROOT / "js" / "sim-tables.js"
        START, END = "/* push continuation tables: BUILT BY research/memory/m19_push_continue.py, never edit by hand */", "/* end push continuation tables */"
        txt = f"{START}\nwindow.SIM_TABLES.base_continue = {json.dumps(block, separators=(',', ':'))};\n{END}\n"
        js = JS.read_text(encoding="utf-8"); js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + txt
        tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)
    run.result("port identical", R["port check"]["identical"])
    for s in ("test", "worlds"):
        v = R["research"]["steps"]["versions"]; run.result(f"research steps {s} log loss left+step / all", [v["left + step"][s]["logloss"], v["all"][s]["logloss"]])
    run.save_json(OUT / "m19_push_continue.json", R)
    print(json.dumps(R["port check"], indent=1))
    for c in ("research", "app"):
        print(c, json.dumps({"counts": R[c]["counts"], "choice": R[c]["steps"]["choice"], "scores": {k: {s: v[s]["logloss"] for s in ("train", "test", "worlds")} for k, v in R[c]["steps"]["versions"].items()},
                             "coef": R[c]["steps"]["versions"]["all"]["coef"], "replay": R[c]["steps"]["replay (no sim)"], "minute": R[c]["per-minute, outside fight pushes"]}, indent=1))
