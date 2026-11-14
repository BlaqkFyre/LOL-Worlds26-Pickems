"""Laning slice, step 1d (14 Nov 2026 AEST; Luke: "who wins fights" while the feed pull runs). Read-only.
When an early fight happens (kills before 14:00, kills 20 s+ apart start a new fight), does the side whose players and champions are rated
stronger for the roles in that fight come out ahead? Fights from gol.gg timelines matched to the file; roles from the file.
Inputs, blue minus red:
  pre-game  the step 1 lane model's expected gold edge at 10 (players, champions, matchup, comfort, player x champion; research/laning/
            s5_lane_edges.py, its training-chosen settings), summed over the roles that took part in the fight (killer, assisters, victims,
            either side), per 1k. Never fitted on the game itself: games before 1 Sep get 5-fold cross-fitted values (fit on the other four
            fifths, before 1 Sep); 2026 games from 1 Sep get a fit before 1 Sep; each Worlds game gets a fit on every game before its day.
  state     the same roles' gold edge at the start of the fight's minute (timeline gold), per 1k (the lane so far).
  team      v1 team strength (z_v1).
Outcome: blue won the fight (more kills than red); even trades left out. Logistic regression, log loss (lower is better), v side only.
Tests: Worlds day by day (logistic fitted on every fight before the day), 2026 non-Worlds from 1 Sep (fitted before 1 Sep).
Data come through research/lib (14 Nov 2026): the pre-game lane predictions are lib.lane_model.pregame_preds (computed once, cached).
Every run leaves a record in research/runs/.
usage (repo root): python -I research/laning/s5_fight_winner.py   (writes research/model/laning/fight_winner.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from lib.lane_model import pregame_preds
ROLES = config.ROLES
OUT = config.MODEL_DIR / "laning" / "fight_winner.json"
with Run("fight_winner", inputs=[config.OE_CSV, config.LANE_FEATURES, config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD]) as run:
    D = pregame_preds("y10"); PE = D.set_index(["gameid", "position"]).pred.to_dict(); Z = D.drop_duplicates("gameid").set_index("gameid").z_v1.to_dict()
    print("lane predictions ready", flush=True)
    # fights
    key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    pl = data.oe(["gameid", "league", "date", "side", "position", "champion"]); data.check(pl); pl = pl[pl.position.isin(ROLES)]
    pl["ck"] = pl.champion.map(key); look = {(g, c): (r, s.lower()) for g, c, r, s in zip(pl.gameid, pl.ck, pl.position, pl.side)}
    tm, ev, gold = data.timelines(); tm = tm[tm.gameid.isin(D.gameid)].drop(columns=["day", "league"])
    ev = ev.drop(columns="gameid"); ev = ev[ev.gid.isin(tm.gid) & (ev.type == "kill") & (ev.t < 840)].sort_values(["gid", "t"])
    gold = gold[(gold.kind == "gold") & gold.gid.isin(tm.gid)]
    GW = gold.pivot_table(index=["gid", "minute"], columns=["side", "role"], values="value")
    meta = D.drop_duplicates("gameid").set_index("gameid")[["day", "league"]]
    F = []
    for g in tm.itertuples():
        e = ev[ev.gid == g.gid]; cur = []
        def close(cur):
            if not cur: return
            roles, net = set(), 0
            for x in cur:
                k = look.get((g.gameid, key(x.champ))); v = look.get((g.gameid, key(x.victim_champ)))
                if not k or not v: return
                roles |= {k[0], v[0]} | {look[(g.gameid, key(a))][0] for a in str(x.assists).split("|") if isinstance(x.assists, str) and (g.gameid, key(a)) in look}
                net += 1 if k[1] == "blue" else -1
            if net == 0: return
            m = int(cur[0].t // 60)
            try: row = GW.loc[(g.gid, m)]; st = sum(row[("blue", r)] - row[("red", r)] for r in roles) / 1000
            except KeyError: return
            pe = sum(PE.get((g.gameid, r), np.nan) for r in roles) / 1000
            if np.isnan(pe): return
            F.append({"gameid": g.gameid, "day": meta.day[g.gameid], "league": meta.league[g.gameid], "t": cur[0].t, "n": len(cur), "y": float(net > 0),
                      "pre": pe, "state": st, "team": Z.get(g.gameid, 0) or 0, "roles": len(roles)})
        for x in e.itertuples():
            if cur and x.t - cur[-1].t > 20: close(cur); cur = []
            cur.append(x)
        close(cur)
    F = pd.DataFrame(F); R = {"fights before 14:00 (not even)": len(F), "blue won": round(float(F.y.mean()), 3)}
    def lfit(X, y):
        b = np.zeros(X.shape[1])
        for _ in range(30):
            p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p); b += np.linalg.solve(X.T @ (X * W[:, None]) + 1e-6 * np.eye(len(b)), X.T @ (y - p))
        return b
    def ll(y, p): p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    VS = {"side only": [], "+ pre-game players and champions": ["pre"], "+ team strength": ["pre", "team"], "+ lane state at the time": ["pre", "team", "state"],
          "lane state only": ["state"]}
    X = lambda d, c: np.c_[np.ones(len(d)), *[d[k].values for k in c]]
    for nm, (tr, te) in {"2026 from 1 Sep (non-Worlds)": (F[F.day < config.SPLIT], F[(F.day >= config.SPLIT) & (F.league != "WLDs")])}.items():
        R[nm] = {v: round(ll(te.y.values, 1 / (1 + np.exp(-X(te, c) @ lfit(X(tr, c), tr.y.values)))), 4) for v, c in VS.items()}; R[nm]["n"] = len(te)
    acc = {v: [] for v in VS}; ys = []
    for dday in sorted(F[F.league == "WLDs"].day.unique()):
        tr, te = F[F.day < dday], F[(F.day == dday) & (F.league == "WLDs")]; ys += list(te.y)
        for v, c in VS.items(): acc[v] += list(1 / (1 + np.exp(-X(te, c) @ lfit(X(tr, c), tr.y.values))))
    R["Worlds day by day"] = {v: round(ll(np.array(ys), np.array(p)), 4) for v, p in acc.items()}; R["Worlds day by day"]["n"] = len(ys)
    b = lfit(X(F, VS["+ lane state at the time"]), F.y.values)
    R["coefficients (all fights): blue side, pre-game per 1k, team strength, state per 1k"] = [round(float(x), 3) for x in b]
    q = pd.qcut(F.pre, 5, labels=False); R["blue wins by pre-game edge fifth (weakest to strongest)"] = [round(float(F.y[q == i].mean()), 3) for i in range(5)]
    R["pre-game edge by fifth, mean per 1k"] = [round(float(F.pre[q == i].mean()), 2) for i in range(5)]
    run.save_json(OUT, R); print("queued", OUT)
