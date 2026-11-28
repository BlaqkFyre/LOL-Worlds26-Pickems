"""Outside-window chains for the app: the joint model's app copy and per-minute tables refitted without the chains' minutes
(prepared 28 Nov 2026 AEST, NOT RUN; Luke: "prepare the work that allows for refit the tables without outside-chain minutes (but dont do
it yet)"). Plan: research/memory/structure-rules-plan.md (decision B2: every base structure outside a won-fight window starts a chain
the outside model runs; decision C option 1: refit the per-minute tables without those minutes, as m21 did for windows).
  model     the joint "what next?" model chosen from m25 (--model free | fixed; no default, so this cannot run before Luke picks),
            refitted on each copy, the shifts' ridge by 5-fold CV by game on that copy's training games (m25's choose).
  minutes   left out of the per-minute refits, matching the app's order inside a minute (fights and windows, then monsters, then per
            side the lane-tower segments, then the base push):
              base push (that side's team-minutes): every minute a won-fight window covers (as m21); for an outside chain, the minutes
              after the anchor's minute up to its last take; for a T3 anchor (it falls in the segment draws, before that minute's base
              push) its own minute too. An inhibitor / nexus-tower anchor's minute stays in: it is the push that starts the chain.
            monsters (all minutes): every minute a window covers (as m21); for an outside chain, the minutes after the anchor's minute
              up to its last take (the anchor minute's monster draw comes before the base push in the app).
  refits    base push (`base_push_fight` inputs, m21.minute_base) and each monster's per-minute take chance (m21.minute_monsters),
            without those minutes. Port check as m21: with nothing left out each reproduces the table in js/sim-tables.js.
  scores    research copy (fit before 1 Sep): held-out log loss on the kept minutes, these refits v m21's (window minutes only left out).
Output: research/model/memory/m26_outside_tables.json with the app block (SIM_TABLES.window as m21's, plus `outside`: the shifts, and
the refitted base_push / monsters). --app also writes it into js/sim-tables.js (m21's writer); --write-app writes the saved block only.
usage (repo root): python -I research/memory/m26_outside_tables.py --model free|fixed [--app | --write-app]"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import APP_CUT, INP, DTJ, RATES, rates, dead_intervals, ll
import m21_fight_window as F
import m23_window_outside as O
import m25_joint_replay as R5

OUT = config.MODEL_DIR / "memory"
ARGS = sys.argv[1:]
MODEL = ARGS[ARGS.index("--model") + 1] if "--model" in ARGS and ARGS.index("--model") + 1 < len(ARGS) else None
WRITE_APP = "--app" in ARGS

def chain_minutes(chains):
    """(gid, minute, side) left out of the base push and (gid, minute) left out of the monsters, for outside chains"""
    base, mon = set(), set()
    for c in chains:
        a = c["anchor"]; m0 = int(a[0] // 60); last = max([a[0]] + list(c["took_t"])); m1 = int(last // 60)
        for mm in range(m0 + 1, m1 + 1): base.add((c["gid"], mm, c["w"])); mon.add((c["gid"], mm))
        if a[2] == "T3": base.add((c["gid"], m0, c["w"]))
    return base, mon

def app_layout(blk):
    """the block as written to js/sim-tables.js: the top level stays m21's (v55: base push and monsters refitted without window minutes
    only), so structure_rules "off" replays v55; the refits without outside-chain minutes go inside `outside`, read only when it is on"""
    m21 = json.load(open(OUT / "m21_fight_window.json", encoding="utf-8"))["app block"]
    for k in ("stage1", "stage2", "take_q"):
        if m21[k] != blk[k] and blk["outside"]["model"] == "fixed": raise SystemExit(f"{k} differs from m21's: not written")
    return {**{k: v for k, v in blk.items() if k not in ("outside", "base_push", "monsters")}, "base_push": m21["base_push"], "monsters": m21["monsters"],
            "outside": {**blk["outside"], "base_push": blk["base_push"], "monsters": blk["monsters"]}}

def fit_copy(ns, DEAD):
    Sw, Fd, wms, wm = F.window_rows(ns, DEAD); So, na = O.outside_rows(ns, DEAD)
    cols = [c for c in So.columns if c in Sw.columns]
    S = pd.concat([Sw[cols].assign(outside=False), So[cols].assign(outside=True)], ignore_index=True); tr = S[S.split == "train"]
    W, bw1, bw2, TT = F.fit_window(ns, Sw)
    if MODEL == "free":
        l1, l2, cv1, cv2 = R5.choose(tr, R5.fit_free); b1, b2 = R5.fit_free(tr, l1, l2)
    else:
        l1, l2, cv1, cv2 = R5.choose(tr, lambda d, a, b: R5.fit_fixed(d, bw1, bw2, a, b)); b1, b2 = R5.fit_fixed(tr, bw1, bw2, l1, l2)
    N1, N2, P = R5.N1, R5.N2, len(F.S2T)
    outside = {"model": MODEL, "ridge (stage 1, stage 2)": [l1, l2],
               "stage1": dict(zip(F.S1N, np.round(b1[N1:], 4).tolist())),
               "stage2": {k: dict(zip(F.S2T, np.round(b2[N2 + i * P:N2 + (i + 1) * P], 4).tolist())) for i, k in enumerate(F.OPT)}}
    if MODEL == "free":   # the free model also moves the window terms: the app then reads these in place of m21's
        outside["window stage1"] = dict(zip(F.S1N, np.round(b1[:N1], 4).tolist()))
        outside["window stage2"] = {k: dict(zip(F.S2T, np.round(b2[i * P:(i + 1) * P], 4).tolist())) for i, k in enumerate(F.OPT)}
    xb, xm = chain_minutes(R5.outside_chains(ns))
    B = ns["BASE"]; Mo = ns["Mo"]
    keep_w = np.array([(g, m, s) not in wms for g, m, s in zip(B.gid, B.m, B.side)])
    keep_b = keep_w & np.array([(g, m, s) not in xb for g, m, s in zip(B.gid, B.m, B.side)])
    keepM_w = np.array([(g, m) not in wm for g, m in zip(Mo.gid, Mo.m)])
    keepM = keepM_w & np.array([(g, m) not in xm for g, m in zip(Mo.gid, Mo.m)])
    fullB, _, _, yB = F.minute_base(ns, B); wB, XwB, bwB, _ = F.minute_base(ns, B[keep_w]); nB, XnB, bnB, _ = F.minute_base(ns, B[keep_b]); Bk = B[keep_b]
    nB["held-out log loss on kept minutes (this refit | m21's window-only refit)"] = {s: [ll(XnB(Bk[Bk.split == s]), bnB, yB(Bk[Bk.split == s])), ll(XwB(Bk[Bk.split == s]), bwB, yB(Bk[Bk.split == s]))] if (Bk.split == s).any() else None for s in ("test", "worlds")}
    return {"counts": {**na, "window step rows": len(Sw), "outside step rows": len(So),
                       "base team-minutes left out (windows | + outside chains)": [int((~keep_w).sum()), int((~keep_b).sum())],
                       "monster minutes left out (windows | + outside chains)": [int((~keepM_w).sum()), int((~keepM).sum())]},
            "CV log loss on outside rows by ridge": {"stage 1": cv1, "stage 2": cv2}, "window": W, "outside": outside,
            "base push, all rows (port check)": fullB, "base push, without windows (m21)": wB, "base push, without windows and outside chains": nB,
            "monsters, all rows (port check)": F.minute_monsters(ns, Mo), "monsters, without windows and outside chains": F.minute_monsters(ns, Mo[keepM])}

def main():
    with Run("memory_outside_tables", params={"app_cut": APP_CUT, "split": config.SPLIT, "chain_s": F.CHAIN, "model": MODEL, "ridge_grid": R5.GRID, "write_app": WRITE_APP},
             inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, *[p for c in INP.values() for p in (c["v1"], c["comp"])]]) as run:
        o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
        XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
        DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
        Rs = {"source": "research/memory/m26_outside_tables.py", "model": MODEL}
        for copy in ("research", "app"):
            ns = rates(copy, tag="m26"); info, ev = ns["info"], ns["ev"]
            if copy == "app": ns["ev"] = ev[ev.gid.map(info.date) < APP_CUT]; ns["info"] = info[info.date < APP_CUT]
            DEAD, matched = dead_intervals(ns["info"], ns["ev"], XP, AVG, DT)
            Rs[copy] = {"deaths matched": matched, **fit_copy(ns, DEAD)}
        bp, mo = F.app_tables(); A = Rs["app"]
        port = {"base_push_fight (differences)": F.diffs(A["base push, all rows (port check)"]["coef"], bp),
                "monsters (differences)": {k: F.diffs(A["monsters, all rows (port check)"][k]["coef"], v) for k, v in mo.items() if k in A["monsters, all rows (port check)"]}}
        port["identical"] = {"base push": all(abs(v) < 1e-9 for v in port["base_push_fight (differences)"].values()),
                             "monsters": all(abs(v) < 1e-9 for d_ in port["monsters (differences)"].values() for v in d_.values())}
        Rs["port check"] = port
        W = A["window"]
        Rs["app block"] = {"cutoff": APP_CUT, "source": f"research/memory/m26_outside_tables.py ({MODEL}), gol.gg timelines before {APP_CUT}", "chain_s": F.CHAIN, "options": F.OPT,
                           # free: the joint fit's window terms; fixed: m21's
                           "stage1": A["outside"].get("window stage1", W["stage 1 coef"]), "stage2": A["outside"].get("window stage2", W["stage 2 coef"]),
                           "take_q": W["take times s (21 quantiles; option x players alive, n >= 20)"],
                           "outside": A["outside"],
                           "base_push": {k: A["base push, without windows and outside chains"][k] for k in ("coef", "clear_fight_cutoff")},
                           "monsters": {k: v["coef"] for k, v in A["monsters, without windows and outside chains"].items()}}
        if WRITE_APP:
            if not all(port["identical"].values()): raise SystemExit("port check failed: js/sim-tables.js not written")
            F.write_app(app_layout(Rs["app block"]))
        run.result("port identical", port["identical"])
        run.result("research base push held-out", Rs["research"]["base push, without windows and outside chains"]["held-out log loss on kept minutes (this refit | m21's window-only refit)"])
        run.save_json(OUT / "m26_outside_tables.json", Rs)
        print(json.dumps({"port check": port, "research counts": Rs["research"]["counts"], "app counts": Rs["app"]["counts"],
                          "research base push held-out": Rs["research"]["base push, without windows and outside chains"]["held-out log loss on kept minutes (this refit | m21's window-only refit)"]}, indent=1))

if __name__ == "__main__":
    if "--write-app" in ARGS:
        Rs = json.load(open(OUT / "m26_outside_tables.json", encoding="utf-8")); blk = Rs["app block"]
        if not all(Rs["port check"]["identical"].values()): raise SystemExit("port check failed: js/sim-tables.js not written")
        if "take_q" not in blk:   # the 28 Nov run's block lost take_q (a comment swallowed it); the same quantiles are saved in its app fit
            blk = {**blk, "take_q": Rs["app"]["window"]["take times s (21 quantiles; option x players alive, n >= 20)"]}
        F.write_app(app_layout(blk))
    elif MODEL not in ("free", "fixed"):
        raise SystemExit("choose the model first: --model free | fixed (from m25; Luke decides)")
    else: main()
