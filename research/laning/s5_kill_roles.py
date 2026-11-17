"""Who gets each early kill and who dies, by lane matchup (15 Nov 2026 AEST; Luke: fix jungle and support lanes).
s5_lane_parts.py found that in real Worlds games each role's gold from kills, assists and plates follows that role's own pre-game
expected edge (top, jungle, support about 1,200-1,300 gold per 1k; the module about 100-230). The sim picks the killer among the killing
side's players in the fight, and the victim among the other side's, from role tables (research/sim4/s4_participants.py), the killer
leaning toward roles ahead by an older lane fit, the victim not at all.
Tested here on real kills before 14:00 (gol.gg timelines, roles from the file):
  killer: among the killing side's players in that kill (killer + assisters), role and 5-minute window + own pre-game expected gold edge
          at 10 (step 1 lane model, never fitted on the game; side-signed, per 1k)
  victim: among the 5 players of the side that died (alive at the time isn't known, so all 5), role and window + own pre-game edge
Each v role and window only; log loss, Worlds day by day (fit on all timeline kills before each day) and 2026 from 1 Sep.
usage (repo root): python -I research/laning/s5_kill_roles.py   (writes research/model/laning/kill_roles.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data, splits
from lib.runlog import Run
from lib.lane_model import pregame_preds
R5 = config.ROLES
with Run("kill_roles", inputs=[config.OE_CSV, config.LANE_FEATURES, config.TL_MATCH, config.TL_EVENTS]) as run:
    G = pregame_preds("y10"); PE = G.set_index(["gameid", "position"]).pred.to_dict(); games = set(G.gameid)
    look = data.roles(data.oe(["gameid", "league", "date", "side", "position", "champion"]))
    tm, ev, _ = data.timelines(); tm = tm[tm.gameid.isin(games)]; ev = ev[ev.gid.isin(tm.gid) & (ev.type == "kill") & (ev.t < 840)]
    meta = tm.set_index("gid")[["gameid", "day", "league"]]; rows = []
    for x in ev.itertuples():
        g = meta.loc[x.gid].gameid; k = look.get((g, data.key(x.champ))); v = look.get((g, data.key(x.victim_champ)))
        if not k or not v: continue
        ast = [look[(g, data.key(a))][0] for a in str(x.assists).split("|") if isinstance(x.assists, str) and (g, data.key(a)) in look]
        sg = 1 if k[1] == "blue" else -1; pe = {r: sg * PE.get((g, r), np.nan) / 1000 for r in R5}
        if any(np.isnan(pe[r]) for r in R5): continue
        rows.append({"day": meta.loc[x.gid].day, "league": meta.loc[x.gid].league, "w": 0 if x.t < 300 else 1 if x.t < 600 else 2,
                     "killer": k[0], "cands": sorted(set([k[0]] + ast)), "victim": v[0], "pe": pe})
    K = pd.DataFrame(rows); R = {"kills": len(K)}
    def fit_choice(D, who, use_pre):
        # features per candidate: role x window dummies (top = base) + own edge (+ for the killer's side; the victim's own edge is -pe)
        def X(r, w, pe_r): return np.array([float(r == rr and w == ww) for ww in range(3) for rr in R5[1:]] + ([pe_r] if use_pre else []))
        sets = []
        for d in D.itertuples():
            cands = d.cands if who == "killer" else R5
            sgn = 1 if who == "killer" else -1
            sets.append((np.array([X(r, d.w, sgn * d.pe[r]) for r in cands]), cands.index(d.killer if who == "killer" else d.victim)))
        b = np.zeros(len(sets[0][0][0]))
        for _ in range(25):
            gr = np.zeros_like(b); H = 1e-3 * np.eye(len(b))
            for Xs, y in sets:
                if len(Xs) == 1: continue
                z = Xs @ b; p = np.exp(z - z.max()); p /= p.sum(); xb = p @ Xs; gr += Xs[y] - xb; H += (Xs * p[:, None]).T @ Xs - np.outer(xb, xb)
            b += np.linalg.solve(H, gr - 1e-3 * b)
        return b, X
    def ll(D, who, use_pre, b, X):
        s, n = 0.0, 0
        for d in D.itertuples():
            cands = d.cands if who == "killer" else R5; sgn = 1 if who == "killer" else -1
            if len(cands) == 1: continue
            Xs = np.array([X(r, d.w, sgn * d.pe[r]) for r in cands]); z = Xs @ b; p = np.exp(z - z.max()); p /= p.sum()
            s -= np.log(p[cands.index(d.killer if who == "killer" else d.victim)]); n += 1
        return s, n
    for who in ("killer", "victim"):
        out = {}
        tr, te = splits.fixed_2026(K)
        sc = {}
        for up in (False, True): b, X = fit_choice(tr, who, up); s, n = ll(te, who, up, b, X); sc[up] = round(s / n, 4)
        out["2026 from 1 Sep (non-Worlds)"] = {"role and window": sc[False], "+ own pre-game edge": sc[True], "n": n}
        acc = {False: [0.0, 0], True: [0.0, 0]}
        for day, tr, te in splits.worlds_by_day(K):
            for up in (False, True): b, X = fit_choice(tr, who, up); s, n = ll(te, who, up, b, X); acc[up][0] += s; acc[up][1] += n
        out["Worlds day by day"] = {"role and window": round(acc[False][0] / acc[False][1], 4), "+ own pre-game edge": round(acc[True][0] / acc[True][1], 4), "n": acc[True][1]}
        b, _ = fit_choice(K, who, True); out["own pre-game edge coefficient (all kills; per 1k)"] = round(float(b[-1]), 3)
        R[who] = out; print(who, json.dumps(out), flush=True)
    run.save_json(config.MODEL_DIR / "laning" / "kill_roles.json", R)
