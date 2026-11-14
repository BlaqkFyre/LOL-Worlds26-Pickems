"""Laning slice, step 1e (14 Nov 2026 AEST; Luke chose "2": fit the other laning actions while the feed pull runs). Read-only.
The actions the laning module needs besides lane fights (step 1d), each fitted on game state at the time and tested against a simpler
version: Worlds day by day (fit on every timeline game before the day), then 2026 non-Worlds games from 1 Sep (fit before 1 Sep).
Data: gol.gg timelines matched to the file (research/model/sim3/tl_match.csv), roles from the file, timeline gold per role per minute.
  A. Plates (side x lane x minute, 3:00-13:59, while that lane's outer tower stands; gol.gg "plate" events before 14:00), Poisson:
     minute and lane; + the lane's gold edge (per 1k); + enemy laner(s) killed in the last 60 s, own laner killed in the last 60 s;
     + plates already off that tower; + own grubs.
  B. First dragon taker (blue = 1), logistic: side; + team strength (v1), bot / mid / jungle gold edge at the time (per 1k);
     + net kills in the 60 s before; + a Worlds term (Worlds games only), since step 1b found the 2026 side effect didn't hold at Worlds.
  C. Grubs (each of the 3), same as B with top / mid / jungle edges and the team grubs priority (blue minus red team effect, from
     training games only, shrink 10 as chosen in step 1b).
  D. Lane kills (side x lane x minute, 2:00-13:59; victim in that lane: top, jungle, mid, bot = ADC + support), Poisson: minute and lane;
     + the lane's gold edge now; + the step 1 pre-game expected lane edge at 10 (cross-fitted, never fitted on the game itself).
     Also solo kills (no assist, killer and victim in the same lane).
Lower is better (Poisson deviance or log loss).
Data come through research/lib (14 Nov 2026): the pre-game lane predictions are lib.lane_model.pregame_preds (computed once, cached).
Every run leaves a record in research/runs/.
usage (repo root): python -I research/laning/s5_lane_actions.py   (writes research/model/laning/lane_actions.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from lib.lane_model import pregame_preds
ROLES = config.ROLES
OUT = config.MODEL_DIR / "laning" / "lane_actions.json"
with Run("lane_actions", inputs=[config.OE_CSV, config.LANE_FEATURES, config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD]) as run:
    D = pregame_preds("y10"); PE = D.set_index(["gameid", "position"]).pred.to_dict(); Z = D.drop_duplicates("gameid").set_index("gameid").z_v1.fillna(0).to_dict()
    print("lane predictions ready", flush=True)
    key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    pl = data.oe(["gameid", "league", "date", "side", "position", "champion", "teamname"]); data.check(pl)
    team = pl[pl.position == "team"].assign(sd=lambda d: d.side.str.lower()).set_index(["gameid", "sd"]).teamname.to_dict()
    pl = pl[pl.position.isin(ROLES)].copy(); pl["ck"] = pl.champion.map(key); look = {(g, c): (r, s.lower()) for g, c, r, s in zip(pl.gameid, pl.ck, pl.position, pl.side)}
    tm, ev, gold = data.timelines(); tm = tm[tm.gameid.isin(D.gameid)].drop(columns=["day", "league"])
    ev = ev.drop(columns="gameid"); ev = ev[ev.gid.isin(tm.gid)].sort_values(["gid", "t"])
    gold = gold[(gold.kind == "gold") & gold.gid.isin(tm.gid)]
    GW = gold.pivot_table(index=["gid", "minute"], columns=["side", "role"], values="value")
    meta = D.drop_duplicates("gameid").set_index("gameid")[["day", "league"]]
    LR = {"top": ["top"], "jng": ["jng"], "mid": ["mid"], "bot": ["bot", "sup"]}; LANES = ["top", "jng", "mid", "bot"]; PL = {"TOP": "top", "MID": "mid", "BOT": "bot"}
    OTH = {"blue": "red", "red": "blue"}
    plates, drag, grub, lk = [], [], [], []
    for g in tm.itertuples():
        e = ev[ev.gid == g.gid]; gm = meta.loc[g.gameid]; isw = float(gm.league == "WLDs")
        def edge(m, s, roles):
            try: row = GW.loc[(g.gid, m)]
            except KeyError: return None
            return sum(row[(s, r)] - row[(OTH[s], r)] for r in roles) / 1000
        K = []
        for x in e[e.type == "kill"].itertuples():
            k = look.get((g.gameid, key(x.champ))); v = look.get((g.gameid, key(x.victim_champ)))
            if k and v: K.append((x.t, k[1], k[0], v[0], not isinstance(x.assists, str)))
        pls = [(x.t, x.side, PL.get(str(x.detail))) for x in e[(e.type == "plate") & (e.t < 840)].itertuples()]
        t1 = {(x.side, PL.get(str(x.detail).split()[1])): x.t for x in e[(e.type == "tower") & e.detail.astype(str).str.match(r"T1 (TOP|MID|BOT)$")].itertuples()}
        grubs_t = [(x.t, x.side) for x in e[e.type == "grub"].itertuples()]
        for s in ("blue", "red"):
            for m in range(2, 14):
                t0 = 60 * m
                for L in LANES:
                    ed = edge(m, s, LR[L])
                    if ed is None: continue
                    kills = sum(1 for t, ks, kr, vr, solo in K if t0 <= t < t0 + 60 and ks == s and vr in LR[L])
                    solo = sum(1 for t, ks, kr, vr, so in K if t0 <= t < t0 + 60 and ks == s and so and vr in LR[L] and kr in LR[L])
                    pe = sum(PE.get((g.gameid, r), np.nan) for r in LR[L]) / 1000 * (1 if s == "blue" else -1)
                    lk.append({"day": gm.day, "league": gm.league, "m": m, "lane": L, "y": kills, "solo": solo, "edge": ed, "pre": pe})
                    if L == "jng" or m < 3: continue
                    if t1.get((s, L), 1e9) < t0: continue  # this side already took that outer tower
                    n_before = sum(1 for t, ps, pL in pls if ps == s and pL == L and t < t0)
                    y = sum(1 for t, ps, pL in pls if ps == s and pL == L and t0 <= t < t0 + 60)
                    en_dead = sum(1 for t, ks, kr, vr, so in K if ks == s and vr in LR[L] and t0 - 60 <= t < t0 + 30)
                    own_dead = sum(1 for t, ks, kr, vr, so in K if ks == OTH[s] and vr in LR[L] and t0 - 60 <= t < t0 + 30)
                    plates.append({"day": gm.day, "league": gm.league, "m": m, "lane": L, "y": y, "edge": ed, "en_dead": en_dead, "own_dead": own_dead,
                                   "taken": n_before, "grubs": sum(1 for t, gs in grubs_t if gs == s and t < t0)})
        def at(t, side_):
            m = int(t // 60); out = {}
            for L in ["top", "jng", "mid", "bot"]:
                v = edge(m, "blue", LR[L]); out[L] = 0.0 if v is None else v
            out["net60"] = sum((1 if ks == "blue" else -1) for tk, ks, kr, vr, so in K if t - 60 <= tk < t)
            return out
        dd = e[e.type == "dragon"]
        if len(dd):
            x = dd.iloc[0]; drag.append({"day": gm.day, "league": gm.league, "y": float(x.side == "blue"), "z": Z.get(g.gameid, 0), "w": isw, **at(x.t, x.side),
                                         "tb": team.get((g.gameid, "blue")), "tr": team.get((g.gameid, "red"))})
        for t, s in grubs_t[:3]:
            grub.append({"day": gm.day, "league": gm.league, "y": float(s == "blue"), "z": Z.get(g.gameid, 0), "w": isw, **at(t, s),
                         "tb": team.get((g.gameid, "blue")), "tr": team.get((g.gameid, "red"))})
    P_, DR, GR, LK = map(pd.DataFrame, (plates, drag, grub, lk))
    R = {"rows": {"plate side-lane-minutes": len(P_), "first dragons": len(DR), "grubs": len(GR), "lane kill side-lane-minutes": len(LK)},
         "averages": {"plates per side-lane-minute": round(float(P_.y.mean()), 3), "blue takes first dragon": round(float(DR.y.mean()), 3),
                      "blue first dragon at Worlds": round(float(DR[DR.w == 1].y.mean()), 3), "blue takes a grub": round(float(GR.y.mean()), 3)}}
    def poisson_fit(X, y):
        b = np.zeros(X.shape[1]); b[0] = np.log(max(1e-6, y.mean()))
        for _ in range(40): mu = np.exp(np.clip(X @ b, -20, 20)); b += np.linalg.solve((X * mu[:, None]).T @ X + 1e-3 * np.eye(len(b)), X.T @ (y - mu) - 1e-3 * b)
        return b
    def dev(y, mu): mu = np.clip(mu, 1e-9, None); return float(np.mean(2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))))
    def lfit(X, y):
        b = np.zeros(X.shape[1])
        for _ in range(30): p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p); b += np.linalg.solve(X.T @ (X * W[:, None]) + 1e-3 * np.eye(len(b)), X.T @ (y - p) - 1e-3 * b)
        return b
    def ll(y, p): p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    def test(Df, Xf, versions, kind, prep=None):
        """Xf(d, cols, ctx) -> X; prep(train) -> ctx (e.g. team effects from training only)"""
        fit, sc = (poisson_fit, lambda y, X, b: dev(y, np.exp(np.clip(X @ b, -20, 20)))) if kind == "poisson" else (lfit, lambda y, X, b: ll(y, 1 / (1 + np.exp(-X @ b))))
        out = {}
        tr, te = Df[Df.day < config.SPLIT], Df[(Df.day >= config.SPLIT) & (Df.league != "WLDs")]; ctx = prep(tr) if prep else None
        out["2026 from 1 Sep (non-Worlds)"] = {v: round(sc(te.y.values, Xf(te, c, ctx), fit(Xf(tr, c, ctx), tr.y.values)), 4) for v, c in versions.items()}
        out["2026 from 1 Sep (non-Worlds)"]["n"] = len(te)
        acc = {v: 0.0 for v in versions}; n = 0
        for dday in sorted(Df[Df.league == "WLDs"].day.unique()):
            tr, te = Df[Df.day < dday], Df[(Df.day == dday) & (Df.league == "WLDs")]; ctx = prep(tr) if prep else None; n += len(te)
            for v, c in versions.items(): acc[v] += sc(te.y.values, Xf(te, c, ctx), fit(Xf(tr, c, ctx), tr.y.values)) * len(te)
        out["Worlds day by day"] = {v: round(a / n, 4) for v, a in acc.items()}; out["Worlds day by day"]["n"] = n
        return out
    # A plates
    def XA(d, c, ctx):
        cols = [np.ones(len(d))] + [(d.m.values == m) for m in range(4, 14)] + [(d.lane.values == "mid"), (d.lane.values == "bot")]
        return np.column_stack([np.asarray(x, float) for x in cols] + [d[k].values.astype(float) for k in c])
    VA = {"minute and lane": [], "+ lane gold edge": ["edge"], "+ laners dead": ["edge", "en_dead", "own_dead"], "+ plates already off": ["edge", "en_dead", "own_dead", "taken"],
          "+ own grubs": ["edge", "en_dead", "own_dead", "taken", "grubs"]}
    R["A. plates (Poisson deviance)"] = test(P_, XA, VA, "poisson")
    b = poisson_fit(XA(P_, VA["+ own grubs"], None), P_.y.values); R["A. plates (Poisson deviance)"]["coefficients (all): edge per 1k, enemy laners dead, own dead, plates off, own grubs"] = [round(float(x), 3) for x in b[-5:]]
    print("A", json.dumps(R["A. plates (Poisson deviance)"]), flush=True)
    # B / C objectives
    def team_eff(tr, k=10.0):
        if tr is None or not len(tr): return {}
        X = np.c_[np.ones(len(tr)), tr.z]; b = lfit(X, tr.y.values); p = 1 / (1 + np.exp(-X @ b)); res = tr.y.values - p; w = p * (1 - p)
        num = pd.concat([pd.Series(res, index=tr.tb.values), pd.Series(-res, index=tr.tr.values)]).groupby(level=0).sum()
        den = pd.concat([pd.Series(w, index=tr.tb.values), pd.Series(w, index=tr.tr.values)]).groupby(level=0).sum()
        return (num / (den + k)).to_dict()
    def XO(d, c, ctx):
        cols = [np.ones(len(d))] + [d[k].values.astype(float) for k in c if k != "team"]
        if "team" in c: cols.append(d.tb.map(ctx).fillna(0).values - d.tr.map(ctx).fillna(0).values)
        return np.column_stack(cols)
    VB = {"side only": [], "+ strength and lanes at the time": ["z", "bot", "mid", "jng"], "+ kills in the 60 s before": ["z", "bot", "mid", "jng", "net60"],
          "+ Worlds term": ["z", "bot", "mid", "jng", "net60", "w"]}
    R["B. first dragon taker (log loss)"] = test(DR, XO, VB, "logistic")
    R["B. first dragon taker (log loss)"]["coefficients (all): side, strength, bot, mid, jng per 1k, net kills 60 s, Worlds"] = [round(float(x), 3) for x in lfit(XO(DR, VB["+ Worlds term"], None), DR.y.values)]
    print("B", json.dumps(R["B. first dragon taker (log loss)"]), flush=True)
    VC = {"side only": [], "+ strength and lanes at the time": ["z", "top", "mid", "jng"], "+ kills in the 60 s before": ["z", "top", "mid", "jng", "net60"],
          "+ team grubs priority": ["z", "top", "mid", "jng", "net60", "team"], "+ Worlds term": ["z", "top", "mid", "jng", "net60", "team", "w"]}
    R["C. grub taker (log loss)"] = test(GR, XO, VC, "logistic", prep=team_eff)
    R["C. grub taker (log loss)"]["coefficients (all): side, strength, top, mid, jng per 1k, net kills 60 s, team priority, Worlds"] = [round(float(x), 3) for x in lfit(XO(GR, VC["+ Worlds term"], team_eff(GR)), GR.y.values)]
    print("C", json.dumps(R["C. grub taker (log loss)"]), flush=True)
    # D lane kills
    LK = LK.dropna(subset=["pre"])
    def XD(d, c, ctx):
        cols = [np.ones(len(d))] + [(d.m.values >= a) & (d.m.values < b) for a, b in [(4, 6), (6, 8), (8, 10), (10, 12), (12, 14)]] + [(d.lane.values == l) for l in ["jng", "mid", "bot"]]
        return np.column_stack([np.asarray(x, float) for x in cols] + [d[k].values.astype(float) for k in c])
    VD = {"minute and lane": [], "+ lane gold edge now": ["edge"], "+ pre-game players and champions": ["edge", "pre"], "pre-game only": ["pre"]}
    R["D. lane kills (Poisson deviance)"] = test(LK, XD, VD, "poisson")
    R["D. solo kills (Poisson deviance)"] = test(LK.assign(y=LK.solo), XD, VD, "poisson")
    R["D. lane kills (Poisson deviance)"]["coefficients (all): edge now per 1k, pre-game per 1k"] = [round(float(x), 3) for x in poisson_fit(XD(LK, ["edge", "pre"], None), LK.y.values)[-2:]]
    R["D. solo kills (Poisson deviance)"]["coefficients (all): edge now per 1k, pre-game per 1k"] = [round(float(x), 3) for x in poisson_fit(XD(LK, ["edge", "pre"], None), LK.solo.values)[-2:]]
    print("D", json.dumps(R["D. lane kills (Poisson deviance)"]), json.dumps(R["D. solo kills (Poisson deviance)"]), flush=True)
    run.save_json(OUT, R); print("queued", OUT)
