"""Laning slice, the farm contest (14 Nov 2026 AEST; Luke: lane gold should come from actions, not a fitted lead plus leftover noise).
From the lolesports feed (Worlds, second by second, research/local/feed; clocks set from the gol.gg timelines by s5_feed_analysis.py):
  A Where a player's gold comes from, per player-minute (1:00-14:59): gold earned ~ role x minute baseline (passive income and anything not
    listed) + CS + kills + assists + own-lane plates + the side's towers and the first tower (timeline) + share of the minute dead. Least squares on all Worlds player-minutes.
  B The CS contest per minute between lane opponents (top, jungle, mid, ADC, support; both alive the whole minute): blue's CS gained minus
    red's. Mean and spread by role and minute; how much of it is the same lane-game all game long (between-game share: a persistent edge
    on the day) v minute to minute.
  C Does the pre-game CS expectation (the step 1 lane model fitted on CS at 10 instead of gold: players, champions, matchup, comfort,
    player x champion, team strength; settings chosen on training games only) explain the per-minute contest? Worlds day by day.
  D Emergence test (the point of this): build each Worlds lane's CS and gold edge at 10 and 15 from actions only (the CS contest each
    alive minute from C, nothing while dead, the real kills, assists, plates and deaths of that game paid at A's values, no noise term
    for the lead itself) and compare the spread and fit with the real edges. If the simulated spread is too small, an action is missing.
usage (repo root): python -I research/laning/s5_farm.py   (writes research/model/laning/farm.json)"""
import sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from lib.lane_model import lane_rows, Model, day0, FULL
OUT = config.MODEL_DIR / "laning" / "farm.json"
ROLE_FEED = {"top": "top", "jungle": "jng", "mid": "mid", "bottom": "bot", "support": "sup"}; LANE_OF = {"top": "TOP", "mid": "MID", "bot": "BOT", "sup": "BOT"}
with Run("farm", inputs=[config.OE_CSV, config.LANE_FEATURES, config.TL_MATCH, config.TL_EVENTS, config.MODEL_DIR / "laning" / "feed_analysis.json"]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "champion", "csdiffat10", "csdiffat15", "golddiffat10", "golddiffat15"]); data.check(o)
    W = o[(o.league == "WLDs") & o.position.isin(config.ROLES)]
    sig = {v: k for k, v in W.groupby("gameid").champion.apply(lambda s: "|".join(sorted(data.key(c) for c in s))).items()}
    day = W.drop_duplicates("gameid").set_index("gameid").date.str[:10].to_dict()
    FA = json.load(open(config.MODEL_DIR / "laning" / "feed_analysis.json")); OFF = {c["gameid"]: c["offset_s"] for c in FA["per game checks"] if c.get("aligned")}
    tm, ev, _ = data.timelines(); plates = ev[(ev.type == "plate") & (ev.t < 900)]; towers = ev[(ev.type == "tower") & (ev.t < 900)]
    rows = []
    for f in sorted(glob.glob(str(config.FEED_DIR / "1*.json"))):
        d = json.load(open(f)); P = d["meta"]["blueTeamMetadata"]["participantMetadata"] + d["meta"]["redTeamMetadata"]["participantMetadata"]
        gid = sig.get("|".join(sorted(data.key(p["championId"]) for p in P)))
        if gid is None or gid not in OFF: continue
        role = [ROLE_FEED[p["role"]] for p in P]; side = ["blue"] * 5 + ["red"] * 5
        sec = np.array([x[0] for x in d["frames"]]) + OFF[gid]; A = np.array([x[1] for x in d["frames"]], dtype=float)
        tg = tm[tm.gameid == gid].gid; pl = plates[plates.gid == tg.iloc[0]] if len(tg) else plates.iloc[:0]; tw = towers[towers.gid == tg.iloc[0]] if len(tg) else towers.iloc[:0]
        first_tw = tw.t.min() if len(tw) else 1e9
        def at(t):
            i = np.searchsorted(sec, t); cand = [j for j in (i - 1, i) if 0 <= j < len(sec) and abs(sec[j] - t) <= 3]
            return min(cand, key=lambda j: abs(sec[j] - t)) if cand else None
        for m in range(1, 15):  # 1:00-14:59 (the file's edges are at 15:00)
            i0, i1 = at(60 * m), at(60 * m + 60)
            if i0 is None or i1 is None: continue
            seg = (sec >= sec[i0]) & (sec <= sec[i1])
            for p in range(10):
                deadshare = float(np.mean(A[seg, p, 6] <= 0)) if seg.any() else 0.0
                pls = int(((pl.side == side[p]) & (pl.detail == LANE_OF.get(role[p], "")) & (pl.t >= 60 * m) & (pl.t < 60 * m + 60)).sum()) if role[p] != "jng" else 0
                rows.append({"gameid": gid, "day": day[gid], "m": m, "side": side[p], "role": role[p], "dgold": A[i1, p, 0] - A[i0, p, 0], "dcs": A[i1, p, 5] - A[i0, p, 5],
                             "dk": A[i1, p, 2] - A[i0, p, 2], "da": A[i1, p, 4] - A[i0, p, 4], "dd": A[i1, p, 3] - A[i0, p, 3], "dead": deadshare, "plates": pls,
                             "towers": int(((tw.side == side[p]) & (tw.t >= 60 * m) & (tw.t < 60 * m + 60)).sum()), "first_tower": int((tw[tw.t == first_tw].side == side[p]).any() and 60 * m <= first_tw < 60 * m + 60)})
    M = pd.DataFrame(rows); R = {"player-minutes": len(M), "games": int(M.gameid.nunique())}
    # A gold sources
    X = pd.get_dummies(M.role + "_" + M.m.astype(str), dtype=float); cols = ["dcs", "dk", "da", "plates", "dead", "towers", "first_tower"]
    Xa = np.c_[X.values, M[cols].values]; b = np.linalg.lstsq(Xa, M.dgold.values, rcond=None)[0]
    R["A gold per minute: per CS, kill, assist, own-lane plate, whole minute dead"] = {c: round(float(v), 1) for c, v in zip(cols, b[-len(cols):])}
    R["A share of gold variance explained"] = round(float(1 - np.var(M.dgold.values - Xa @ b) / np.var(M.dgold.values)), 3)
    # B per-minute CS contest between lane opponents, both alive the whole minute
    piv = M.pivot_table(index=["gameid", "day", "m", "role"], columns="side", values=["dcs", "dead"]).dropna()
    C = piv[(piv[("dead", "blue")] == 0) & (piv[("dead", "red")] == 0)].copy(); C["y"] = C[("dcs", "blue")] - C[("dcs", "red")]
    C = C[["y"]].reset_index(); C.columns = ["gameid", "day", "m", "role", "y"]
    R["B CS contest per minute (blue minus red), mean / sd by role"] = {r: [round(float(g.y.mean()), 2), round(float(g.y.std()), 2), len(g)] for r, g in C.groupby("role")}
    gm = C.groupby(["gameid", "role"]).y.agg(["mean", "count", "var"]).reset_index()
    def between_share(g):
        g = g[g["count"] >= 6]; within = g["var"].mean(); between = max(0.0, g["mean"].var() - within / g["count"].mean())
        return round(float(between / (between + within)), 3)
    R["B share of minute-to-minute CS contest variance that is the same lane-game all game (persistent on the day)"] = {r: between_share(g) for r, g in gm.groupby("role")}
    # C pre-game CS expectation (lane model on CS at 10), settings chosen on training games only
    J, _, _ = lane_rows(); J["y"] = J.c10; D = J.dropna(subset=["y"]).copy(); BL = FULL + ["team"]
    tr, va = D[D.day < config.TUNE_FROM], D[(D.day >= config.TUNE_FROM) & (D.day < config.SPLIT) & D.major]
    K, HL = {"player": 40, "champ": 40, "pair": 80, "pc": 40}, {"p": None, "c": None}
    for nm, grid in [("player", [5, 10, 20, 40, 80, 160]), ("champ", [5, 10, 20, 40, 80, 160]), ("pair", [20, 80, 320, 1280]), ("pc", [20, 80, 320, 1280])]:
        best = min((float(np.mean((va.y.values - Model(BL, {**K, nm: v}, HL).fit(tr, day0(config.TUNE_FROM)).predict(va)) ** 2)), v) for v in grid); K[nm] = best[1]
    R["C settings chosen on training games"] = K
    pre = {}
    for dd in sorted(D[D.league == "WLDs"].day.unique()):
        te = D[(D.day == dd) & (D.league == "WLDs")]; trn = D[D.day < dd]; assert trn.day.max() < dd
        for (g, r), v in zip(zip(te.gameid, te.position), Model(BL, K, HL).fit(trn, day0(dd)).predict(te)): pre[(g, r)] = v
    C["pre"] = [pre.get((g, r), np.nan) / 10 for g, r in zip(C.gameid, C.role)]  # expected CS edge per minute (the model's edge at 10 / 10)
    C = C.dropna(subset=["pre"]); ys, p0, p1 = [], [], []
    for dd in sorted(C.day.unique())[1:]:
        trn, te = C[C.day < dd], C[C.day == dd]; ys += list(te.y)
        mu = trn.groupby("role").y.mean(); p0 += list(te.role.map(mu).fillna(0))
        bb = {r: np.linalg.lstsq(np.c_[np.ones(len(g)), g.pre], g.y.values, rcond=None)[0] for r, g in trn.groupby("role")}
        p1 += [bb[r][0] + bb[r][1] * x if r in bb else 0 for r, x in zip(te.role, te.pre)]
    ys = np.array(ys); R["C per-minute CS contest, Worlds day by day, mean squared error"] = {"role mean only": round(float(np.mean((ys - np.array(p0)) ** 2)), 3),
                                                                                          "+ pre-game players and champions": round(float(np.mean((ys - np.array(p1)) ** 2)), 3), "n": len(ys)}
    # C2 the same at lane level: does the pre-game CS expectation line up with the real CS edge at 10 and 15 on Worlds lanes?
    WL = W.set_index(["gameid", "position"]); c2 = {}
    for r in config.ROLES:
        ks = [(g, rr) for (g, rr) in pre if rr == r and (g, "Blue") in set(zip(W.gameid, W.side))]
        x = np.array([pre[k] for k in ks]); b10 = np.array([W[(W.gameid == g) & (W.position == r) & (W.side == "Blue")].csdiffat10.iloc[0] for g, _ in ks])
        ok = ~np.isnan(b10); c2[r] = {"lanes": int(ok.sum()), "corr(pre-game expected, real CS edge at 10)": round(float(np.corrcoef(x[ok], b10[ok])[0, 1]), 3),
                                      "error: zero / pre-game": [round(float(np.mean(b10[ok] ** 2)), 1), round(float(np.mean((b10[ok] - x[ok]) ** 2)), 1)]}
    R["C2 lane level, Worlds day by day: pre-game expected CS edge at 10 v real"] = c2
    bb_all = {r: np.linalg.lstsq(np.c_[np.ones(len(g)), g.pre], g.y.values, rcond=None)[0] for r, g in C.groupby("role")}
    R["C slope per role (1 = the model's expected CS edge arrives in full)"] = {r: round(float(v[1]), 3) for r, v in bb_all.items()}
    # D emergence: CS and gold edges at 10 and 15 from actions only, 2,000 draws per lane-game
    rng = np.random.default_rng(14112026); sd = C.groupby("role").y.std().to_dict(); gA = R["A gold per minute: per CS, kill, assist, own-lane plate, whole minute dead"]
    real = W.set_index(["gameid", "side", "position"]); out = {}
    for r in config.ROLES:
        sim_c15, real_c15, sim_g15, real_g15 = [], [], [], []; rest_real, rest_ev = [], []
        for g in M.gameid.unique():
            mm = M[(M.gameid == g) & (M.role == r)]
            if mm.m.nunique() < 14 or (g, r) not in pre: continue
            mu = bb_all[r][0] + bb_all[r][1] * pre[(g, r)] / 10
            alive = mm.pivot_table(index="m", columns="side", values="dead").reindex(range(1, 15)).fillna(1)
            both = ((alive["blue"] == 0) & (alive["red"] == 0)).values
            ev_ = mm.pivot_table(index="m", columns="side", values=["dk", "da", "plates", "dead", "towers", "first_tower"], aggfunc="sum").fillna(0)
            evg = sum((ev_[(c, "blue")] - ev_[(c, "red")]).sum() * gA[c] for c in ["dk", "da", "plates", "dead", "towers", "first_tower"])
            # CS when one side is dead that minute: the alive one's real CS (no contest), so dead time costs the dead laner its farm
            onesided = sum(mm[(mm.m == m_) & (mm.side == "blue")].dcs.sum() - mm[(mm.m == m_) & (mm.side == "red")].dcs.sum() for m_ in range(1, 15) if not both[m_ - 1])
            draws = (mu * both.sum() + sd[r] * np.sqrt(both.sum()) * rng.standard_normal(2000)) + onesided
            rc = real.loc[(g, "Blue", r)]
            sim_c15.append(draws); real_c15.append(rc.csdiffat15 if pd.notna(rc.csdiffat15) else np.nan)  # 1:00-14:59 covers the farm to 15:00 (CS starts ~1:05)
            sim_g15.append(draws * gA["dcs"] + evg); real_g15.append(rc.golddiffat15)
            rest_real.append(rc.golddiffat15 - gA["dcs"] * rc.csdiffat15 if pd.notna(rc.csdiffat15) else np.nan); rest_ev.append(evg)
        sc, rcs, sg, rg = np.array(sim_c15), np.array(real_c15), np.array(sim_g15), np.array(real_g15)
        ok = ~np.isnan(rcs) & ~np.isnan(rg)
        out[r] = {"lanes": int(ok.sum()), "CS edge: real sd": round(float(np.std(rcs[ok])), 1), "CS edge: actions-only sd": round(float(np.std(sc[ok], axis=None)), 1),
                  "gold edge at 15: real sd": round(float(np.std(rg[ok]))), "gold edge at 15: actions-only sd": round(float(np.std(sg[ok], axis=None))),
                  "gold not from CS (real gold edge - CS edge x gold per CS): real sd": round(float(np.nanstd(np.array(rest_real)))),
                  "... from the game's kills, assists, plates and dead time at A's values: sd": round(float(np.std(np.array(rest_ev)))),
                  "... correlation of the two": round(float(pd.Series(rest_real).corr(pd.Series(rest_ev))), 3),
                  "gold: real edge inside the actions-only 80% range": round(float(np.mean([(np.percentile(s, 10) <= x <= np.percentile(s, 90)) for s, x in zip(sg[ok], rg[ok])])), 3)}
    R["D actions-only lanes v real (Worlds; real events, simulated farm contest, no lead noise)"] = out
    run.result("games", R["games"]); run.save_json(OUT, R); print(json.dumps(R, indent=1))
