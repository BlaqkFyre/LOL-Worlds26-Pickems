"""Game memory, step 9 (18 Nov 2026 AEST): the positioning leads from the final's game 3 (final-g3-positions.md), tested on the 98 feed games.
Luke OK'd testing them. "In a fight" = credited with a kill, assist or death in it, or lost 25%+ of max health in it (from 20 s before the
first death to 5 s after the last). Pick = one death and 4 or fewer players in; big fight = 8+ players in.
 1 kind and size: by phase, by the gold gap going in, by numbers alive going in
 2 who gets picked: pick victims by role and phase, against each role's share of all deaths (positions aren't in the feed, so
   "alone" itself can't be measured)
 3 vision: per game and team (Oracle's Elixir totals: vision score, wards cleared), share of picks won and of big fights won against the
   team's share of vision; if vision matters for picks in particular, the pick slope is larger. Bootstrap over games for ranges.
 4 objectives: share of dragons and Barons with a big fight / any fight / a pick in the 90 s before, against the same share for
   random seconds (the chance a 90 s window holds such a fight anyway)
 5 late joiners: in big fights, each player's entry (first 5%+ health loss or credit) after the fight's first entry, by role; and
   the share of big fights each role is not in
 6 fights moving: not testable without positions (the towers that follow a fight are in m2_responses)
 7 towers with no fight: share of towers with no death by anyone in the 60 s before, by phase
Output: research/model/memory/m6_fight_kinds.json.
usage (repo root): python -I research/memory/m6_fight_kinds.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from lib import config, data, feed
from lib.runlog import Run
from common import deaths, fights, FIGHT_GAP

OUT = config.MODEL_DIR / "memory"; HP_IN, BOOT, WIN_OBJ, WIN_TW = 0.25, 1000, 90, 60
PHASE = [(0, 840, "before 14:00"), (840, 1500, "14:00-25:00"), (1500, 1e9, "after 25:00")]
ph = lambda s: next(n for a, b, n in PHASE if a <= s < b)
r3 = lambda x: round(float(x), 3)
def kind(n, d): return "pick" if (d == 1 and n <= 4) else "big (8+)" if n >= 8 else "other"

with Run("memory_fight_kinds", params={"hp_in": HP_IN, "fight_gap": FIGHT_GAP, "obj_window_s": WIN_OBJ, "tower_window_s": WIN_TW, "bootstrap": BOOT},
         inputs=[config.OE_CSV]) as run:
    games = feed.full(); rows, ent, objs, towers, base = [], [], [], [], {"big (8+)": [0, 0], "pick": [0, 0], "any": [0, 0]}
    rng = np.random.default_rng(20261118)
    for g in games:
        t, P, T = g["t"], g["P"], g["T"]; ev = deaths(g); F = fights(g, ev, FIGHT_GAP); fl = []
        for f in F:
            i0, i1 = int(np.searchsorted(t, f["t_first"] - FIGHT_GAP)), min(int(np.searchsorted(t, f["t_last"] + 5)), len(t) - 1)
            hp, mx = P[i0:i1 + 1, :, 6], np.maximum(P[i0 + 1:i1 + 1, :, 7], 1); step = ((hp[:-1] - hp[1:]) / mx).clip(0)
            cr = (P[i1, :, 2] - P[i0, :, 2]) + (P[i1, :, 4] - P[i0, :, 4]) + (P[i1, :, 3] - P[i0, :, 3])
            inv = (cr > 0) | (step.sum(0) >= HP_IN); n = int(inv.sum()); d = f["deaths_blue"] + f["deaths_red"]; k = kind(n, d)
            alive = P[i0, :, 6] > 0
            r = {"gameid": g["gameid"], "t": f["t_first"], "t_last": f["t_last"], "phase": ph(f["t_first"]), "n": n, "kind": k, "deaths": d,
                 "winner": f["win_gold"], "gap": abs(f["lead_before"]), "alive_diff": abs(int(alive[:5].sum()) - int(alive[5:].sum())),
                 "victims": [g["roles"][e["p"]] for e in ev if f["t_first"] <= e["t"] <= f["t_last"]],
                 "in_blue": int(inv[:5].sum()), "in_red": int(inv[5:].sum())}
            rows.append(r); fl.append(r)
            if k == "big (8+)":
                first = []
                for p in range(10):
                    if not inv[p]: ent.append({"role": g["roles"][p], "in": 0, "delay": np.nan}); continue
                    hit = np.where(step[:, p] >= 0.05)[0]
                    if not len(hit): hit = np.where(step[:, p] > 0)[0]   # lost 25%+ in small steps: first loss of any size
                    tc = [t[i0 + 1 + hit[0]]] if len(hit) else []
                    for c in (2, 3, 4):
                        ch = np.where(np.diff(P[i0:i1 + 1, p, c]) > 0)[0]
                        if len(ch): tc.append(t[i0 + 1 + ch[0]])
                    first.append((p, min(tc)))
                t0 = min(x for _, x in first)
                for p, x in first: ent.append({"role": g["roles"][p], "in": 1, "delay": x - t0})
        # objectives: dragons and Barons taken (feed team totals), and towers
        for c, name in ((5, "dragon"), (3, "baron")):
            for s in (0, 1):
                for i in np.where(np.diff(T[:, s, c]) > 0)[0] + 1:
                    tt = t[i]; near = [r for r in fl if tt - WIN_OBJ <= r["t_last"] <= tt]
                    objs.append({"obj": name, "phase": ph(tt), "big": any(r["kind"] == "big (8+)" for r in near), "pick": any(r["kind"] == "pick" for r in near), "any": bool(near)})
        dts = np.array([e["t"] for e in ev])
        for s in (0, 1):
            for i in np.where(np.diff(T[:, s, 1]) > 0)[0] + 1:
                tt = t[i]; towers.append({"phase": ph(tt), "no_death": not ((dts >= tt - WIN_TW) & (dts <= tt)).any()})
        # baseline: random seconds after 5:00 (dragons spawn at 5:00)
        for tt in rng.uniform(300, t[-1], 40):
            near = [r for r in fl if tt - WIN_OBJ <= r["t_last"] <= tt]
            for kk in ("big (8+)", "pick"): base[kk][0] += any(r["kind"] == kk for r in near); base[kk][1] += 1
            base["any"][0] += bool(near); base["any"][1] += 1
    D = pd.DataFrame(rows); R = {"fights": len(D)}
    # 1
    R["1 kind share by phase"] = {p: {k: r3((x.kind == k).mean()) for k in ("pick", "other", "big (8+)")} | {"fights": len(x)} for p, x in D.groupby("phase", sort=False)}
    D["gapbin"] = pd.cut(D.gap, [-1, 1000, 3000, 6000, 1e9], labels=["under 1k", "1-3k", "3-6k", "6k+"])
    R["1 kind share by gold gap going in"] = {str(b): {k: r3((x.kind == k).mean()) for k in ("pick", "big (8+)")} | {"fights": len(x)} for b, x in D.groupby("gapbin", observed=True)}
    R["1 kind share by numbers alive gap going in"] = {str(b): {k: r3((x.kind == k).mean()) for k in ("pick", "big (8+)")} | {"fights": len(x)} for b, x in D.groupby(D.alive_diff.clip(upper=2))}
    late = D[D.phase == "after 25:00"]; late_gap = late.groupby("gapbin", observed=True)
    R["1 after 25:00, kind share by gold gap"] = {str(b): {k: r3((x.kind == k).mean()) for k in ("pick", "big (8+)")} | {"fights": len(x)} for b, x in late_gap}
    # 2
    vict = pd.DataFrame([{"role": v, "phase": r["phase"], "pick": r["kind"] == "pick"} for r in rows for v in r["victims"]])
    R["2 deaths by role: share of pick victims v share of all deaths"] = {p: {ro: [r3((x[x.pick].role == ro).mean()), r3((x.role == ro).mean())] for ro in config.ROLES}
                                                                        | {"pick victims": int(x.pick.sum()), "deaths": len(x)} for p, x in vict.groupby("phase", sort=False)}
    # 3 vision
    o = data.oe(["gameid", "league", "date", "side", "position", "visionscore", "wardskilled"]); tm = o[(o.league == "WLDs") & (o.position == "team")]
    V = {(gid, s.lower()): (vs, wk) for gid, s, vs, wk in zip(tm.gameid, tm.side, tm.visionscore, tm.wardskilled)}
    G = []
    for gid, x in D.groupby("gameid"):
        vb, wb = V[(gid, "blue")]; vr, wr = V[(gid, "red")]
        for kk in ("pick", "big (8+)"):
            y = x[(x.kind == kk) & (x.winner != "even")]
            if len(y): G.append({"gameid": gid, "kind": kk, "won_blue": float((y.winner == "blue").mean()), "n": len(y), "vision_blue": vb / (vb + vr), "wards_killed_blue": wb / max(wb + wr, 1)})
    G = pd.DataFrame(G)
    def slope(x, col): w = x.n.values; X = np.c_[np.ones(len(x)), x[col].values - 0.5]; b = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (w * x.won_blue.values)); return b[1]
    out = {}
    for col in ("vision_blue", "wards_killed_blue"):
        for kk in ("pick", "big (8+)"):
            x = G[G.kind == kk]; ids = x.gameid.unique(); bs = []; byg = {i: y for i, y in x.groupby("gameid")}
            for _ in range(BOOT):
                pick = rng.choice(ids, len(ids)); bs.append(slope(pd.concat([byg[i] for i in pick]), col))
            out[f"{kk}: share won per +10 points of {col.replace('_blue', '')} share"] = [r3(slope(x, col) / 10), r3(np.percentile(bs, 5) / 10), r3(np.percentile(bs, 95) / 10), int(x.n.sum())]
    R["3 vision (estimate, 90% range, fights)"] = out
    # 4
    Ob = pd.DataFrame(objs)
    R["4 objectives with a fight ending in the 90 s before"] = {f"{name} ({len(x)})": {"big (8+)": r3(x.big.mean()), "pick": r3(x.pick.mean()), "any fight": r3(x["any"].mean())} for name, x in Ob.groupby("obj")}
    R["4 baseline: random seconds after 5:00"] = {k: r3(v[0] / v[1]) for k, v in base.items()}
    # 5
    E = pd.DataFrame(ent)
    R["5 big fights: share each role is not in"] = {ro: r3(1 - x["in"].mean()) for ro, x in E.groupby("role")}
    R["5 big fights: entry after the first player in, median s and share 10 s+"] = {ro: [r3(x.delay.median()), r3((x.delay >= 10).mean())] for ro, x in E[E["in"] == 1].groupby("role")}
    # 7
    Tw = pd.DataFrame(towers)
    R["7 towers with no death in the 60 s before"] = {p: [r3(x.no_death.mean()), len(x)] for p, x in Tw.groupby("phase", sort=False)}
    run.result("fights", len(D)); run.save_json(OUT / "m6_fight_kinds.json", R)
    import json; print(json.dumps(R, indent=1))
