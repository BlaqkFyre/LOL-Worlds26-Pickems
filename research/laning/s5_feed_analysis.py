"""Laning slice, feed analysis (14 Nov 2026 AEST; Luke OK'd the Worlds feed pull and asked what it adds for early fights). Read-only.
Feed: lolesports live stats, second-by-second per player: total gold earned, level, K/D/A, CS, current and max health (no positions);
first 15 minutes of each Worlds game in research/local/feed/ (research/laning/feed_pull.py).
  1 Match each feed game to its Oracle's Elixir game (the 10 champions), and set its clock from the gol.gg timeline: the offset that
    best lines the feed's kills up with the timeline's kills (by killer champion). The feed's own start time is not trusted (in a few games
    the puller's start detector caught a stray early frame). Checks: kills within 2 s of the timeline; gold, CS, kills, deaths and
    assists at 10 minutes against the file.
  2 Dead time: a dead player's health reads 0 until respawn. Measured respawn wait v the League wiki timer by level (research/sim4
    deathtimer table).
  3 Lane trades before 14:00 with no kill: both sides' laners in a lane (top, mid, bot = ADC + support) lose 10%+ of max health within the
    same 5 s, nobody in that lane dies in the next 10 s. Winner = the side that lost less (share of max health, summed over its laners).
    Jungler present = a jungler loses 10%+ in the same 5 s.
  4 Tests, Worlds day by day (fit on earlier Worlds days only; the feed covers Worlds only):
    a trade winner ~ side; + the step 1 pre-game expected lane edge (players, champions; never fitted on the game); + level and gold
      difference at the time (log loss)
    b lane gold edge at 15 (file) ~ pre-game expected edge; + the lane's trade balance before 10:00 (error)
  Also: share of trades with a jungler hit, by lane (no-kill jungle involvement the timelines can't show).
usage (repo root): python -I research/laning/s5_feed_analysis.py   (writes research/model/laning/feed_analysis.json)"""
import sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data, fit
from lib.runlog import Run
from lib.lane_model import pregame_preds
OUT = config.MODEL_DIR / "laning" / "feed_analysis.json"
ROLE_FEED = {"top": "top", "jungle": "jng", "mid": "mid", "bottom": "bot", "support": "sup"}
LANES = {"top": ["top"], "mid": ["mid"], "bot": ["bot", "sup"]}
files = sorted(glob.glob(str(config.FEED_DIR / "1*.json")))
with Run("feed_analysis", params={"feed_files": len(files)}, inputs=[config.OE_CSV, config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.FEED_DIR / "worlds_games.csv"]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "champion", "goldat10", "csat10", "killsat10", "deathsat10", "assistsat10", "golddiffat15"]); data.check(o)
    W = o[(o.league == "WLDs") & o.position.isin(config.ROLES)]
    sig = W.groupby("gameid").champion.apply(lambda s: "|".join(sorted(data.key(c) for c in s))).to_dict(); by_sig = {v: k for k, v in sig.items()}
    tm, ev, _ = data.timelines(); kills_tl = ev[(ev.type == "kill")]
    look = data.roles(o); day = W.drop_duplicates("gameid").set_index("gameid").date.str[:10].to_dict()
    PE = pregame_preds("y10").set_index(["gameid", "position"]).pred.to_dict()
    DT = json.load(open(config.R / "model" / "sim4" / "deathtimer.json"))
    R = {"feed files": len(files)}; games, checks, deadrows, trades, jlane = [], [], [], [], []
    for f in files:
        d = json.load(open(f)); F = d["frames"]
        if not F: continue
        meta = d["meta"]; P = meta["blueTeamMetadata"]["participantMetadata"] + meta["redTeamMetadata"]["participantMetadata"]
        champs = [data.key(p["championId"]) for p in P]; gid = by_sig.get("|".join(sorted(champs)))
        if gid is None: checks.append({"file": os.path.basename(f), "matched": False}); continue
        role = [ROLE_FEED[p["role"]] for p in P]; side = ["blue"] * 5 + ["red"] * 5
        sec = np.array([x[0] for x in F]); A = np.array([x[1] for x in F], dtype=float)  # frames x 10 x [gold, lvl, k, d, a, cs, hp, maxhp]
        # clock: offset that lines the feed's kills up with the timeline's (same killer champion)
        fk = [(sec[i], p) for i in range(1, len(F)) for p in range(10) for _ in range(int(A[i, p, 2] - A[i - 1, p, 2]))]
        tk = kills_tl[kills_tl.gameid == gid]
        diffs = [t - s for s, p in fk for t in tk[tk.champ.map(data.key) == champs[p]].t]
        if not diffs: checks.append({"gameid": gid, "matched": True, "aligned": False}); continue
        cand = np.round(np.array(diffs)); vals, cnts = np.unique(cand, return_counts=True); off = float(vals[np.argmax(cnts)])
        res = [min([abs(t - (s + off)) for t in tk[tk.champ.map(data.key) == champs[p]].t] or [999]) for s, p in fk]
        gt = sec + off  # game time of each frame
        c = {"gameid": gid, "matched": True, "aligned": True, "offset_s": off, "feed_kills": len(fk), "kills within 2 s": float(np.mean(np.array(res) <= 2)) if res else None,
             "covered_s": [float(gt.min()), float(gt.max())], "frames": int(len(F)), "largest gap_s": float(np.max(np.diff(gt))) if len(gt) > 1 else None}
        i10 = np.where((gt >= 600) & (gt <= 605))[0]
        if len(i10):
            x = A[i10[0]]; oe10 = W[W.gameid == gid].set_index(["side", "position"])
            err = {k: [] for k in ("gold", "cs", "kills", "deaths", "assists")}
            for p in range(10):
                r = oe10.loc[(side[p].capitalize(), role[p])]
                for k_, j, col in [("gold", 0, "goldat10"), ("cs", 5, "csat10"), ("kills", 2, "killsat10"), ("deaths", 3, "deathsat10"), ("assists", 4, "assistsat10")]:
                    if pd.notna(r[col]): err[k_].append(abs(x[p, j] - r[col]))
            c["mean abs diff at 10:00 v the file"] = {k_: round(float(np.mean(v)), 2) for k_, v in err.items() if v}
        checks.append(c); games.append(gid)
        # dead time: from a death to the first frame with health > 0
        for p in range(10):
            for i in range(1, len(F)):
                if A[i, p, 3] > A[i - 1, p, 3]:
                    after = np.where((gt > gt[i]) & (A[:, p, 6] > 0))[0]
                    if len(after) and gt[after[0]] - gt[i] < 120 and not np.any(np.diff(gt[i:after[0] + 1]) > 3):
                        lvl = int(A[i, p, 1]); t = gt[i]; f_ = DT["time_factor"]; fac, prev = 0.0, f_["start_s"]
                        for end, per in f_["per_step"]:
                            if t > prev: fac += per * ((min(t, end) - prev) // f_["step_s"])
                            prev = end
                        deadrows.append({"level": lvl, "t": t, "dead_s": gt[after[0]] - gt[i], "wiki_s": DT["base_wait"][min(17, lvl - 1)] * (1 + min(f_["cap"], fac))})
        # trades
        hpfrac = A[:, :, 6] / np.maximum(1, A[:, :, 7]); dead = A[:, :, 6] <= 0
        idx = {t: i for i, t in enumerate(gt.astype(int))}
        def drop(p, t0):  # health share lost by player p over [t0, t0+5]
            i0, i1 = idx.get(int(t0)), idx.get(int(t0) + 5)
            if i0 is None or i1 is None or dead[i0, p] or dead[i1, p]: return None
            return float(hpfrac[i0, p] - hpfrac[i0:i1 + 1, p].min())
        deaths_t = [(gt[i], p) for i in range(1, len(F)) for p in range(10) if A[i, p, 3] > A[i - 1, p, 3]]
        jng = [role.index("jng"), 5 + role[5:].index("jng")]
        for L, rl in LANES.items():
            pb = [p for p in range(5) if role[p] in rl]; pr = [p for p in range(5, 10) if role[p] in rl]
            last = -99
            for t0 in range(60, 840, 1):
                if t0 - last < 8: continue
                db = [drop(p, t0) for p in pb]; dr = [drop(p, t0) for p in pr]
                if None in db or None in dr: continue
                if max(db) < 0.10 or max(dr) < 0.10: continue
                if any(t0 <= t <= t0 + 15 and (p in pb or p in pr) for t, p in deaths_t): last = t0; continue
                jb, jr = drop(jng[0], t0), drop(jng[1], t0)
                i0 = idx[t0]; g = lambda ps: float(sum(A[i0, p, 0] for p in ps)); lv = lambda ps: float(np.mean([A[i0, p, 1] for p in ps]))
                trades.append({"gameid": gid, "day": day[gid], "lane": L, "t": t0, "y": float(sum(db) < sum(dr)), "loss_b": sum(db), "loss_r": sum(dr),
                               "pre": sum(PE.get((gid, r), np.nan) for r in rl) / 1000, "lvl": lv(pb) - lv(pr), "gold": (g(pb) - g(pr)) / 1000,
                               "jb": float((jb or 0) >= 0.10), "jr": float((jr or 0) >= 0.10)})
                last = t0
    C = pd.DataFrame([c for c in checks if c.get("aligned")])
    R["matching"] = {"files": len(files), "matched to the file": int(sum(c.get("matched", False) for c in checks)), "aligned to the timeline": len(C),
                     "kills within 2 s of the timeline (median game)": float(C["kills within 2 s"].median()) if len(C) else None,
                     "games with a gap over 20 s": int((C["largest gap_s"] > 20).sum()) if len(C) else None,
                     "mean abs diff at 10:00 v the file (average over games)": {k: round(float(np.mean([c["mean abs diff at 10:00 v the file"][k] for c in checks if "mean abs diff at 10:00 v the file" in c])), 2)
                                                                                for k in ("gold", "cs", "kills", "deaths", "assists")}}
    R["per game checks"] = checks
    Dd = pd.DataFrame(deadrows)
    if len(Dd):
        R["dead time v wiki timer"] = {"deaths": len(Dd), "median measured / wiki": round(float((Dd.dead_s / Dd.wiki_s).median()), 3),
                                       "share within 2 s of the wiki": round(float((abs(Dd.dead_s - Dd.wiki_s) <= 2).mean()), 3),
                                       "by level (median measured, wiki)": {int(l): [round(float(g.dead_s.median()), 1), round(float(g.wiki_s.median()), 1), len(g)] for l, g in Dd.groupby("level")}}
    T = pd.DataFrame(trades); R["trades"] = {"lane trades with no kill before 14:00": len(T), "per game by lane": (T.groupby("lane").size() / max(1, len(games))).round(2).to_dict(),
                                             "blue won": round(float(T.y.mean()), 3), "with a jungler hit": round(float(((T.jb + T.jr) > 0).mean()), 3),
                                             "with a jungler hit, by lane": T.assign(j=(T.jb + T.jr) > 0).groupby("lane").j.mean().round(3).to_dict()} if len(T) else {}
    # 4a trade winner
    if len(T):
        T = T.dropna(subset=["pre"]); V = {"side only": [], "+ pre-game players and champions": ["pre"], "+ level and gold at the time": ["pre", "lvl", "gold"], "level and gold only": ["lvl", "gold"]}
        X = lambda d, c: np.c_[np.ones(len(d)), *[d[k].values for k in c]]; acc = {v: [] for v in V}; ys = []
        for dday in sorted(T.day.unique())[1:]:
            tr, te = T[T.day < dday], T[T.day == dday]; ys += list(te.y)
            for v, c in V.items(): acc[v] += list(fit.sigmoid(X(te, c) @ fit.logistic(X(tr, c), tr.y.values)))
        R["4a trade winner, Worlds day by day (log loss)"] = {v: round(fit.log_loss(np.array(ys), np.array(p)), 4) for v, p in acc.items()}; R["4a trade winner, Worlds day by day (log loss)"]["n"] = len(ys)
        R["4a coefficients (all): side, pre-game per 1k, level diff, gold diff per 1k"] = [round(float(x), 3) for x in fit.logistic(X(T, V["+ level and gold at the time"]), T.y.values)]
        # 4b do trades before 10:00 add to the lane's gold edge at 15 beyond the pre-game expectation?
        bal = T[T.t < 600].assign(s=lambda d: 2 * d.y - 1).groupby(["gameid", "lane"]).s.sum()
        rows = []
        for gid in games:
            w = W[W.gameid == gid].set_index(["side", "position"]).golddiffat15
            for L, rl in LANES.items():
                y = sum(w.get(("Blue", r), np.nan) for r in rl); pe = sum(PE.get((gid, r), np.nan) for r in rl)
                rows.append({"gameid": gid, "day": day[gid], "lane": L, "y": y / 1000, "pre": pe / 1000, "bal": float(bal.get((gid, L), 0))})
        B = pd.DataFrame(rows).dropna(); e = {"pre-game only": [], "+ trade balance before 10:00": []}; yy = []
        for dday in sorted(B.day.unique())[1:]:
            tr, te = B[B.day < dday], B[B.day == dday]; yy += list(te.y)
            for v, c in [("pre-game only", ["pre"]), ("+ trade balance before 10:00", ["pre", "bal"])]:
                Xt, Xe = np.c_[np.ones(len(tr)), tr[c].values], np.c_[np.ones(len(te)), te[c].values]; b = np.linalg.lstsq(Xt, tr.y.values, rcond=None)[0]; e[v] += list(Xe @ b)
        R["4b lane gold edge at 15 (thousands), Worlds day by day, mean squared error"] = {v: round(float(np.mean((np.array(yy) - np.array(p)) ** 2)), 4) for v, p in e.items()}
        R["4b n lanes"] = len(yy)
    run.result("aligned games", R["matching"]["aligned to the timeline"]); run.result("trades", len(T) if len(T) else 0)
    run.save_json(OUT, R); print(json.dumps({k: v for k, v in R.items() if k != "per game checks"}, indent=1))
