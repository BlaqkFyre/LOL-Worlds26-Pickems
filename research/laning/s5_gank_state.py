"""Laning slice, step 1c (14 Nov 2026 AEST; Luke: "yes, test that"). Read-only.
Step 1b found players' early habits (which lane a jungler ganks, roams, solo kills) don't hold up as player traits. Here: do ganks and roams
follow the game state at the time, and the jungle champion?
Data: gol.gg timelines matched to the file (research/model/sim3/tl_match.csv), kills before 14:00 with roles from the file; each lane's gold
edge at the start of the kill's minute from tl_gold.csv (gold of the side's player minus the opposite player; bot lane = ADC + support).
Objective timing from the timelines themselves (no game rule typed in): dragon "up" from the earliest first dragon seen (322 s) and the
shortest gap between dragons (306 s) after the last one; grubs "up" from the earliest grub seen (484 s) until all 3 are taken.
  A. Gank lane: for each early kill a side's jungler takes part in, which lane it is in (victim's lane: top / jungle / mid / bot), as a
     choice between the 4 lanes with: lane constants; that lane's gold edge for the jungler's side (per 1k) and its size; dragon up or
     within 60 s (bot); grubs up or within 60 s (top).
  B. Gank pace: jungler-involved kills per side-minute (2:00-13:59), Poisson: minute; dragon / grubs up; the largest lane edge either
     way; the side's total gold edge; the jungle champion's own early-kill rate (shrunk toward the average, k chosen on training).
  C. Roams: for each early kill the mid (or support) takes part in, which lane: same choice model, plus the roamer's own lane edge (a
     winning mid is free to move) on the other lanes.
Each model v its constants-only version. Tests: Worlds day by day (fit on all timeline games before the day), and 2026 non-Worlds from 1 Sep
(fit before 1 Sep). A fixed tiny ridge (1e-3) only keeps the fits numerically stable.
Data come through research/lib (14 Nov 2026); every run leaves a record in research/runs/.
usage (repo root): python -I research/laning/s5_gank_state.py   (writes research/model/laning/gank_state.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
OUT = config.MODEL_DIR / "laning" / "gank_state.json"
with Run("gank_state", inputs=[config.OE_CSV, config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD]) as run:
    ROLES = ["top", "jng", "mid", "bot", "sup"]; LN = ["top", "jng", "mid", "bot"]; LANE = {"top": "top", "jng": "jng", "mid": "mid", "bot": "bot", "sup": "bot"}
    key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
    pl = data.oe(["gameid", "league", "date", "side", "position", "champion"]); data.check(pl); pl = pl[pl.position.isin(ROLES)].copy(); pl["ck"] = pl.champion.map(key); pl["sd"] = pl.side.str.lower()
    tm, ev, gold = data.timelines(); tm = tm[tm.gameid.isin(pl.gameid)].drop(columns=["day", "league"])
    meta = pl.drop_duplicates("gameid").set_index("gameid")[["league", "date"]]; tm["day"] = tm.gameid.map(meta.date).str[:10]; tm["league"] = tm.gameid.map(meta.league)
    ev = ev[ev.gid.isin(tm.gid)].drop(columns="gameid")
    gold = gold[(gold.kind == "gold") & gold.gid.isin(tm.gid)]
    GW = gold.pivot_table(index=["gid", "minute"], columns=["side", "role"], values="value")
    look = {(g, c): (r, s) for g, c, r, s in zip(pl.gameid, pl.ck, pl.position, pl.sd)}
    jchamp = pl[pl.position == "jng"].set_index(["gameid", "sd"]).champion.to_dict()
    D1, D2, KILL = 322, 306, []  # dragon first, dragon gap (from the data)
    G1 = 484
    def edges(gid, m, s):
        o = "red" if s == "blue" else "blue"
        try: row = GW.loc[(gid, m)]
        except KeyError: return None
        e = {r: row[(s, r)] - row[(o, r)] for r in ROLES}
        return {"top": e["top"], "jng": e["jng"], "mid": e["mid"], "bot": e["bot"] + e["sup"], "team": sum(e.values())}
    rows, pace = [], []
    for g in tm.itertuples():
        e = ev[ev.gid == g.gid]; dr = sorted(e[e.type == "dragon"].t); gr = sorted(e[e.type == "grub"].t)
        def drag_up(t):
            prev = [x for x in dr if x < t]; nxt = D1 if not prev else prev[-1] + D2
            return int(t >= nxt - 60)
        def grub_up(t): return int(t >= G1 - 60 and len([x for x in gr if x < t]) < 3)
        ks = e[(e.type == "kill") & (e.t < 840)]
        cnt = {}
        for x in ks.itertuples():
            kr = look.get((g.gameid, key(x.champ))); vr = look.get((g.gameid, key(x.victim_champ)))
            if not kr or not vr: continue
            inv = [kr[0]] + [look[(g.gameid, key(a))][0] for a in str(x.assists).split("|") if isinstance(x.assists, str) and (g.gameid, key(a)) in look]
            s = kr[1]; m = int(x.t // 60); E = edges(g.gid, m, s)
            if E is None: continue
            base = {"gid": g.gid, "gameid": g.gameid, "day": g.day, "league": g.league, "t": x.t, "lane": LANE[vr[0]], "E": E, "drag": drag_up(x.t), "grub": grub_up(x.t)}
            for who in ("jng", "mid", "sup"):
                if who in inv: rows.append({**base, "who": who})
            if "jng" in inv: cnt[(s, m)] = cnt.get((s, m), 0) + 1
        for s in ("blue", "red"):
            for m in range(2, 14):
                E = edges(g.gid, m, s)
                if E is None: continue
                t = 60 * m + 30
                pace.append({"gameid": g.gameid, "day": g.day, "league": g.league, "m": m, "y": cnt.get((s, m), 0), "drag": drag_up(t), "grub": grub_up(t),
                             "maxedge": max(abs(E[l]) for l in ["top", "mid", "bot"]) / 1000, "team": E["team"] / 1000, "champ": jchamp.get((g.gameid, s))})
    R = {"timeline games": int(tm.gid.nunique()), "early kills with a jungler / mid / support": {w: sum(r["who"] == w for r in rows) for w in ("jng", "mid", "sup")}}

    def X_choice(r, who, full):
        """4 x features for one kill"""
        out = []
        for l in LN:
            f = [float(l == "jng"), float(l == "mid"), float(l == "bot")]  # constants (top = 0)
            if full:
                ed = r["E"][l] / 1000; f += [ed, abs(ed), r["drag"] * (l == "bot"), r["grub"] * (l == "top")]
                if who in ("mid", "sup"):
                    own = r["E"]["mid" if who == "mid" else "bot"] / 1000; f += [own * (l != ("mid" if who == "mid" else "bot"))]
            out.append(f)
        return np.array(out)
    def fit_choice(D, who, full):
        Xs = [X_choice(r, who, full) for r in D]; y = [LN.index(r["lane"]) for r in D]; b = np.zeros(Xs[0].shape[1])
        for _ in range(30):
            gr = np.zeros_like(b); H = 1e-3 * np.eye(len(b))
            for X, yy in zip(Xs, y):
                z = X @ b; p = np.exp(z - z.max()); p /= p.sum(); xb = p @ X
                gr += X[yy] - xb; H += (X * p[:, None]).T @ X - np.outer(xb, xb)
            b += np.linalg.solve(H, gr - 1e-3 * b)
        return b
    def ll_choice(D, who, full, b):
        s = 0.0
        for r in D:
            X = X_choice(r, who, full); z = X @ b; p = np.exp(z - z.max()); p /= p.sum(); s -= np.log(p[LN.index(r["lane"])])
        return s / max(1, len(D))
    for who, label in [("jng", "A. gank lane (jungler's early kills)"), ("mid", "C. mid roams: lane of the mid's early kills"), ("sup", "C. support roams: lane of the support's early kills")]:
        D = [r for r in rows if r["who"] == who]; out = {"kills": len(D), "share by lane": pd.Series([r["lane"] for r in D]).value_counts(normalize=True).round(3).to_dict()}
        tr = [r for r in D if r["day"] < config.SPLIT]; te = [r for r in D if r["day"] >= config.SPLIT and r["league"] != "WLDs"]
        b0, b1 = fit_choice(tr, who, False), fit_choice(tr, who, True)
        out["2026 from 1 Sep (non-Worlds)"] = {"lane constants": round(ll_choice(te, who, False, b0), 4), "game state": round(ll_choice(te, who, True, b1), 4), "n": len(te)}
        s0 = s1 = n = 0
        for dday in sorted({r["day"] for r in D if r["league"] == "WLDs"}):
            tr_ = [r for r in D if r["day"] < dday]; te_ = [r for r in D if r["day"] == dday and r["league"] == "WLDs"]
            b0_, b1_ = fit_choice(tr_, who, False), fit_choice(tr_, who, True); s0 += ll_choice(te_, who, False, b0_) * len(te_); s1 += ll_choice(te_, who, True, b1_) * len(te_); n += len(te_)
        out["Worlds day by day"] = {"lane constants": round(s0 / n, 4), "game state": round(s1 / n, 4), "n": n}
        names = ["const jng", "const mid", "const bot", "lane edge per 1k", "lane edge size per 1k", "dragon up x bot", "grubs up x top"] + (["own lane edge per 1k x other lanes"] if who != "jng" else [])
        out["coefficients (all games)"] = dict(zip(names, np.round(fit_choice(D, who, True), 3).tolist()))
        R[label] = out; print(label, json.dumps(out), flush=True)

    # B. gank pace
    Pc = pd.DataFrame(pace)
    def poisson_fit(X, y):
        b = np.zeros(X.shape[1]); b[0] = np.log(max(1e-6, y.mean()))
        for _ in range(40):
            mu = np.exp(X @ b); b += np.linalg.solve((X * mu[:, None]).T @ X + 1e-3 * np.eye(len(b)), X.T @ (y - mu) - 1e-3 * b)
        return b
    def dev(y, mu): mu = np.clip(mu, 1e-9, None); return float(np.mean(2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))))
    def Xp(d, full, ce=None, cm=None):
        mins = [np.ones(len(d))] + [(d.m.values >= a) & (d.m.values < b) for a, b in [(4, 6), (6, 8), (8, 10), (10, 12), (12, 14)]]
        cols = mins + ([d.drag.values, d.grub.values, d.maxedge.values, d.team.values] if full else [])
        if ce is not None: cols += [np.log(d.champ.map(ce).fillna(cm).values / cm)]
        return np.column_stack([np.asarray(c, float) for c in cols])
    def champ_rate(tr, k):
        g = tr.groupby(["gameid", "champ"]).y.sum().reset_index(); m = g.y.mean(); a = g.groupby("champ").y.agg(["sum", "count"])
        return ((a["sum"] + k * m) / (a["count"] + k)).to_dict(), m
    tr0, va0 = Pc[Pc.day < config.TUNE_FROM], Pc[(Pc.day >= config.TUNE_FROM) & (Pc.day < config.SPLIT)]
    kbest = min([(dev(va0.y.values, np.exp(Xp(va0, True, *champ_rate(tr0, k)) @ poisson_fit(Xp(tr0, True, *champ_rate(tr0, k)), tr0.y.values))), k) for k in [2, 5, 10, 20, 40, 80, 1e9]])[1]
    out = {"side-minutes": len(Pc), "k for the jungle champion's rate (training)": kbest}
    def three(tr, te):
        ce, cm = champ_rate(tr, kbest); r = {}
        r["minute only"] = dev(te.y.values, np.exp(Xp(te, False) @ poisson_fit(Xp(tr, False), tr.y.values)))
        r["+ game state"] = dev(te.y.values, np.exp(Xp(te, True) @ poisson_fit(Xp(tr, True), tr.y.values)))
        r["+ game state + jungle champion"] = dev(te.y.values, np.exp(Xp(te, True, ce, cm) @ poisson_fit(Xp(tr, True, ce, cm), tr.y.values)))
        return r
    r26 = three(Pc[Pc.day < config.SPLIT], Pc[(Pc.day >= config.SPLIT) & (Pc.league != "WLDs")]); out["2026 from 1 Sep (non-Worlds)"] = {k: round(v, 4) for k, v in r26.items()}
    acc, n = {}, 0
    for dday in sorted(Pc[Pc.league == "WLDs"].day.unique()):
        te = Pc[(Pc.day == dday) & (Pc.league == "WLDs")]; r = three(Pc[Pc.day < dday], te); n += len(te)
        for k_, v in r.items(): acc[k_] = acc.get(k_, 0) + v * len(te)
    out["Worlds day by day"] = {k_: round(v / n, 4) for k_, v in acc.items()}
    ce, cm = champ_rate(Pc, kbest); bb = poisson_fit(Xp(Pc, True, ce, cm), Pc.y.values)
    out["coefficients (all games)"] = dict(zip(["const", "4-6", "6-8", "8-10", "10-12", "12-14", "dragon up", "grubs up", "largest lane edge per 1k", "team edge per 1k", "log champion rate"], np.round(bb, 3).tolist()))
    out["jungle champions with the highest early-kill rate (shrunk, per game before 14:00)"] = [f"{c} {v:.2f}" for c, v in sorted(ce.items(), key=lambda kv: -kv[1])[:8]]
    R["B. gank pace (jungler-involved kills per side-minute, Poisson deviance)"] = out; print("B", json.dumps(out), flush=True)
    run.save_json(OUT, R); print("queued", OUT)
