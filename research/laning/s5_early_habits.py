"""Laning slice, step 1b (14 Nov 2026 AEST; research/laning-plan.md; Luke OK'd step 1). Read-only.
Habits in the first 14 minutes, from gol.gg timelines matched to the Oracle's Elixir file (research/model/sim3/tl_match.csv; LPL has no
timelines on gol.gg, so LPL players' habits come only from their international games), plus team early priority from the file.
Each kill before 14:00 gets roles from the file (champions are unique in a game): killer, assisters, victim.
  jungler lanes   which lane the jungler's early kills are in (victim's role: top / jng / mid / bot+sup), per jungler-game
  jungler pace    how many early kills the jungler takes part in, per game
  roams           mid's early kills in top or bot+sup; support's early kills in top, mid or jungle (per game)
  solo kills      a laner's kills before 14:00 with no assist on his lane opponent (top, mid, bot), per game
  team priority   first dragon (file: firstdragon) and grubs (2+ of the first 3) beyond side, team strength (v1) and the bot / top edge at 10
For each habit:
  stability: player (or team) values on odd v even games before 1 Sep, correlation for those with enough games in both halves;
  prediction: Worlds day by day (fit on every timeline game before the day) and 2026 from 1 Sep (fit before 1 Sep):
    league average v the player's (team's) own value shrunk toward the average by k (k chosen on training games only: fit < 1 Aug,
    judge August). Scores: log loss for lanes and yes/no outcomes, Poisson deviance for counts (lower is better).
Data come through research/lib (14 Nov 2026); every run leaves a record in research/runs/.
usage (repo root): python -I research/laning/s5_early_habits.py   (writes research/model/laning/early_habits.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
OUT = config.MODEL_DIR / "laning" / "early_habits.json"
with Run("early_habits", inputs=[config.OE_CSV, config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.LANE_FEATURES]) as run:
    ROLES = config.ROLES; MAJOR = config.MAJOR
    key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    o = data.oe(["gameid", "league", "date", "side", "position", "playerid", "playername", "teamname", "champion", "firstdragon", "void_grubs", "golddiffat10"]).copy(); data.check(o); o["day"] = o.date.str[:10]
    o["pid"] = o.playerid.fillna("name:" + o.playername.astype(str))
    pl = o[o.position.isin(ROLES)].copy(); pl["ck"] = pl.champion.map(key)
    tm, ev, _ = data.timelines(); tm = tm[tm.gameid.isin(pl.gameid)][["gid", "gameid", "date"]]; ev = ev[ev.gid.isin(tm.gid) & (ev.type == "kill") & (ev.t < 840)].drop(columns="gameid")
    g2o = dict(zip(tm.gid, tm.gameid)); ev["gameid"] = ev.gid.map(g2o)
    R = {"timeline games": int(tm.gameid.nunique()), "by league": pl[pl.gameid.isin(tm.gameid)].drop_duplicates("gameid").league.value_counts().to_dict()}
    # roles of killer, assisters and victim
    look = {(g, c): (r, s, p) for g, c, r, s, p in zip(pl.gameid, pl.ck, pl.position, pl.side, pl.pid)}
    rows = []; miss = 0
    for x in ev.itertuples():
        kr = look.get((x.gameid, key(x.champ))); vr = look.get((x.gameid, key(x.victim_champ)))
        if not kr or not vr: miss += 1; continue
        ast = [look.get((x.gameid, key(a))) for a in str(x.assists).split("|")] if isinstance(x.assists, str) else []
        ast = [a for a in ast if a]
        rows.append({"gameid": x.gameid, "t": x.t, "kside": kr[1], "krole": kr[0], "vrole": vr[0], "inv": [kr[0]] + [a[0] for a in ast], "solo": len(ast) == 0})
    K = pd.DataFrame(rows); R["early kills matched to roles"] = [len(K), len(K) + miss]
    games = pl[pl.gameid.isin(tm.gameid)].drop_duplicates(["gameid", "side"])[["gameid", "day", "league", "side"]]
    LANE = {"top": "top", "jng": "jng", "mid": "mid", "bot": "bot", "sup": "bot"}
    # per player-game records
    rec = []
    for (g, s), d in games.set_index(["gameid", "side"]).iterrows():
        k = K[(K.gameid == g) & (K.kside == s)] if len(K) else K
        who = {r: look_r for r, look_r in []}
        pidx = pl[(pl.gameid == g) & (pl.side == s)].set_index("position").pid.to_dict()
        jk = k[k.inv.map(lambda v: "jng" in v).astype(bool).values] if len(k) else k
        rec.append({"gameid": g, "day": d.day, "league": d.league, "side": s, "pid_jng": pidx.get("jng"), "pid_mid": pidx.get("mid"), "pid_sup": pidx.get("sup"),
                    "pid_top": pidx.get("top"), "pid_bot": pidx.get("bot"),
                    "jng_lanes": [LANE[v] for v in jk.vrole], "jng_n": len(jk),
                    "mid_roam": int(k.inv.map(lambda v: "mid" in v).values[(k.vrole.isin(["top", "bot", "sup"])).values].sum()) if len(k) else 0,
                    "sup_roam": int(k.inv.map(lambda v: "sup" in v).values[(k.vrole.isin(["top", "mid", "jng"])).values].sum()) if len(k) else 0,
                    **{f"solo_{r}": int(((k.krole == r) & k.solo & (k.vrole == r)).sum()) if len(k) else 0 for r in ["top", "mid", "bot"]}})
    P = pd.DataFrame(rec); P["ts"] = pd.to_datetime(P.day)
    LN = ["top", "jng", "mid", "bot"]

    def split_corr(vals, min_n):
        """vals: DataFrame with columns id, half, x (per-game value or list); returns corr of per-id means across halves"""
        g = vals.groupby(["id", "half"]).x.agg(["mean", "count"]).unstack()
        g = g[(g["count"][0] >= min_n) & (g["count"][1] >= min_n)]
        return {"ids": int(len(g)), "corr odd v even": round(float(np.corrcoef(g["mean"][0], g["mean"][1])[0, 1]), 3) if len(g) > 3 else None}

    def poisson_dev(y, mu): mu = np.clip(mu, 1e-6, None); return float(np.mean(2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))))

    def count_test(col, idcol, label):
        """count habit: league mean v player's own rate shrunk by k (k on training: fit < 1 Aug, judge Aug)"""
        D = P.dropna(subset=[idcol]).copy(); D["half"] = D.gameid.rank(method="dense").astype(int) % 2
        out = {"stability (games before 1 Sep, 8+ per half)": split_corr(D[D.day < config.SPLIT].rename(columns={idcol: "id", col: "x"}), 8)}
        def fit(tr, k): m = tr[col].mean(); g = tr.groupby(idcol)[col].agg(["sum", "count"]); return m, ((g["sum"] + k * m) / (g["count"] + k)).to_dict()
        def pred(te, m, eff): return te[idcol].map(eff).fillna(m).values
        tr, va = D[D.day < config.TUNE_FROM], D[(D.day >= config.TUNE_FROM) & (D.day < config.SPLIT)]
        best = min([(poisson_dev(va[col].values, pred(va, *fit(tr, k))), k) for k in [2, 5, 10, 20, 40, 80, 160, 1e9]]); k = best[1]
        out["k chosen (training)"] = k
        sc = {}
        for nm, tr_, te_ in [("2026 from 1 Sep (non-Worlds)", D[D.day < config.SPLIT], D[(D.day >= config.SPLIT) & (D.league != "WLDs")])]:
            m, eff = fit(tr_, k); sc[nm] = {"league mean": round(poisson_dev(te_[col].values, np.full(len(te_), m)), 4), "own habit": round(poisson_dev(te_[col].values, pred(te_, m, eff)), 4), "n": len(te_)}
        ys, a, b = [], [], []
        for dday in sorted(D[D.league == "WLDs"].day.unique()):
            tr_, te_ = D[D.day < dday], D[(D.day == dday) & (D.league == "WLDs")]; m, eff = fit(tr_, k)
            ys += list(te_[col].values); a += [m] * len(te_); b += list(pred(te_, m, eff))
        ys, a, b = map(np.array, (ys, a, b))
        sc["Worlds day by day"] = {"league mean": round(poisson_dev(ys, a), 4), "own habit": round(poisson_dev(ys, b), 4), "n": len(ys)}
        out["held-out Poisson deviance (lower is better)"] = sc; out["average per game"] = round(float(D[col].mean()), 3)
        R[label] = out; print(label, json.dumps(out), flush=True)

    # jungler lanes: multinomial over top / jng / mid / bot for each early kill the jungler takes part in
    def lane_test():
        D = P.dropna(subset=["pid_jng"]).copy(); D["half"] = D.gameid.rank(method="dense").astype(int) % 2
        E = D[["gameid", "day", "league", "pid_jng", "half", "jng_lanes"]].explode("jng_lanes").dropna(subset=["jng_lanes"])
        E["botshare"] = (E.jng_lanes == "bot").astype(float) - (E.jng_lanes == "top").astype(float)
        out = {"kills": len(E), "share by lane (all)": E.jng_lanes.value_counts(normalize=True).round(3).to_dict(),
               "stability: bot minus top share, junglers with 15+ kills per half (before 1 Sep)": split_corr(E[E.day < config.SPLIT].rename(columns={"pid_jng": "id", "botshare": "x"}), 15)}
        def fit(tr, k):
            avg = tr.jng_lanes.value_counts(normalize=True).reindex(LN).fillna(0).values
            c = tr.groupby("pid_jng").jng_lanes.value_counts().unstack().reindex(columns=LN).fillna(0)
            return avg, {p: (row.values + k * avg) / (row.values.sum() + k) for p, row in c.iterrows()}
        def ll(te, avg, eff):
            return float(-np.mean([np.log(max(1e-9, eff.get(p, avg)[LN.index(l)])) for p, l in zip(te.pid_jng, te.jng_lanes)]))
        tr, va = E[E.day < config.TUNE_FROM], E[(E.day >= config.TUNE_FROM) & (E.day < config.SPLIT)]
        k = min([(ll(va, *fit(tr, k)), k) for k in [2, 5, 10, 20, 40, 80, 160, 1e9]])[1]; out["k chosen (training)"] = k
        sc = {}
        tr_, te_ = E[E.day < config.SPLIT], E[(E.day >= config.SPLIT) & (E.league != "WLDs")]; avg, eff = fit(tr_, k)
        sc["2026 from 1 Sep (non-Worlds)"] = {"league average": round(ll(te_, avg, {}), 4), "own habit": round(ll(te_, avg, eff), 4), "n": len(te_)}
        la, lo, n = [], [], 0
        for dday in sorted(E[E.league == "WLDs"].day.unique()):
            tr_, te_ = E[E.day < dday], E[(E.day == dday) & (E.league == "WLDs")]; avg, eff = fit(tr_, k)
            la.append(ll(te_, avg, {}) * len(te_)); lo.append(ll(te_, avg, eff) * len(te_)); n += len(te_)
        sc["Worlds day by day"] = {"league average": round(sum(la) / n, 4), "own habit": round(sum(lo) / n, 4), "n": n}
        out["held-out log loss of the kill's lane (lower is better)"] = sc
        R["jungler lanes"] = out; print("jungler lanes", json.dumps(out), flush=True)
    lane_test()
    count_test("jng_n", "pid_jng", "jungler pace (early kills involved)")
    count_test("mid_roam", "pid_mid", "mid roams (kills in other lanes)")
    count_test("sup_roam", "pid_sup", "support roams (kills in top, mid, jungle)")
    for r in ["top", "mid", "bot"]: count_test(f"solo_{r}", f"pid_{r}", f"solo kills {r}")

    # team early priority (file, all major games): first dragon and grubs majority beyond side, v1 strength and lane edges at 10
    T = o[(o.position == "team") & o.league.isin(MAJOR)][["gameid", "day", "league", "side", "teamname", "firstdragon", "void_grubs"]]
    b, r_ = T[T.side == "Blue"].set_index("gameid"), T[T.side == "Red"].set_index("gameid")
    G = b.join(r_[["teamname", "void_grubs"]], rsuffix="_r").dropna(subset=["firstdragon"])
    gd = pl[pl.side == "Blue"].pivot_table(index="gameid", columns="position", values="golddiffat10")
    feat = pd.read_csv(config.LANE_FEATURES).drop_duplicates("gameid").set_index("gameid").z_v1
    G = G.join(gd[["bot", "top", "mid"]]).join(feat).dropna(subset=["bot", "top", "mid", "z_v1"]); G["day"] = G.day.astype(str)
    G["grubs2"] = (G.void_grubs >= 2).astype(float)
    def team_test(col, label, lanes):
        def X(d): return np.c_[np.ones(len(d)), d.z_v1, *[d[l] / 1000 for l in lanes]]
        def lfit(d):
            Xm, y = X(d), d[col].values; bb = np.zeros(Xm.shape[1])
            for _ in range(30):
                p = 1 / (1 + np.exp(-Xm @ bb)); W = p * (1 - p); bb += np.linalg.solve(Xm.T @ (Xm * W[:, None]) + 1e-6 * np.eye(len(bb)), Xm.T @ (y - p))
            return bb
        def tfit(d, bb, k):
            p = 1 / (1 + np.exp(-X(d) @ bb)); res = d[col].values - p; w = p * (1 - p)
            num = pd.concat([pd.Series(res, index=d.teamname.values), pd.Series(-res, index=d.teamname_r.values)]).groupby(level=0).sum()
            den = pd.concat([pd.Series(w, index=d.teamname.values), pd.Series(w, index=d.teamname_r.values)]).groupby(level=0).sum()
            return (num / (den + k)).to_dict()
        def lp(d, bb, eff): z = X(d) @ bb + d.teamname.map(eff).fillna(0).values - d.teamname_r.map(eff).fillna(0).values; return 1 / (1 + np.exp(-z))
        def ll(y, p): p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
        tr, va = G[G.day < config.TUNE_FROM], G[(G.day >= config.TUNE_FROM) & (G.day < config.SPLIT)]; bb = lfit(tr)
        k = min([(ll(va[col].values, lp(va, bb, tfit(tr, bb, k))), k) for k in [2, 5, 10, 20, 40, 80, 1e9]])[1]
        out = {"k chosen (training)": k}
        tr_, te_ = G[G.day < config.SPLIT], G[(G.day >= config.SPLIT) & (G.league != "WLDs")]; bb = lfit(tr_)
        out["2026 from 1 Sep (non-Worlds)"] = {"side + strength + lanes": round(ll(te_[col].values, lp(te_, bb, {})), 4), "+ team habit": round(ll(te_[col].values, lp(te_, bb, tfit(tr_, bb, k))), 4), "n": len(te_)}
        ys, a, c = [], [], []
        for dday in sorted(G[G.league == "WLDs"].day.unique()):
            tr_, te_ = G[G.day < dday], G[(G.day == dday) & (G.league == "WLDs")]; bb = lfit(tr_); ef = tfit(tr_, bb, k)
            ys += list(te_[col].values); a += list(lp(te_, bb, {})); c += list(lp(te_, bb, ef))
        ys, a, c = map(np.array, (ys, a, c))
        out["Worlds day by day"] = {"side + strength + lanes": round(ll(ys, a), 4), "+ team habit": round(ll(ys, c), 4), "n": len(ys)}
        H = G[G.day < config.SPLIT].copy(); H["half"] = np.arange(len(H)) % 2; bb = lfit(H)
        e0, e1 = tfit(H[H.half == 0], bb, 0), tfit(H[H.half == 1], bb, 0)
        n0 = pd.concat([H[H.half == 0].teamname, H[H.half == 0].teamname_r]).value_counts(); n1 = pd.concat([H[H.half == 1].teamname, H[H.half == 1].teamname_r]).value_counts()
        ok = [t for t in e0 if n0.get(t, 0) >= 20 and n1.get(t, 0) >= 20]
        out["stability (teams with 20+ games per half, before 1 Sep)"] = {"teams": len(ok), "corr odd v even": round(float(np.corrcoef([e0[t] for t in ok], [e1[t] for t in ok])[0, 1]), 3) if len(ok) > 3 else None}
        out["coefficients (all games before 1 Sep): intercept (blue), v1, lanes per 1k at 10"] = [round(float(x), 3) for x in lfit(G[G.day < config.SPLIT])]
        R[label] = out; print(label, json.dumps(out), flush=True)
    team_test("firstdragon", "team priority: first dragon", ["bot", "mid"])
    team_test("grubs2", "team priority: grubs (2+ of 3)", ["top", "mid"])
    run.save_json(OUT, R); print("queued", OUT)
