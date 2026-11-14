"""Tables the laning fits read, built once from the timelines (14 Nov 2026; moved here for step 3 so the fit script and the step 1 scripts
share one copy; the code is the same as in research/laning/s5_fight_winner.py and s5_lane_actions.py).
  build(PE, Z) -> {"fights", "plates", "dragon", "grubs"}:
    fights  early fights (kills 20 s+ apart start a new one) before 14:00 that weren't even: y (blue won), pre (pre-game expected gold edge at
            10 of the roles in the fight, per 1k), state (those roles' gold edge at the fight's minute, per 1k), team (v1), day, league
    plates  side x lane x minute (3:00-13:59, outer tower standing): y plates, edge, en_dead, own_dead, taken, grubs, m, lane
    dragon  each game's first dragon: y (blue took it), z, top / jng / mid / bot edges at the time, net60, w (Worlds), tb / tr teams
    grubs   each of the first 3 grubs: the same
  PE: (gameid, role) -> pre-game expected gold edge at 10 (lane_model.pregame_preds); Z: gameid -> v1 strength."""
import numpy as np, pandas as pd
from . import config, data

def build(PE, Z, games=None):
    pl = data.oe(["gameid", "league", "date", "side", "position", "champion", "teamname"])
    team = pl[pl.position == "team"].assign(sd=lambda d: d.side.str.lower()).set_index(["gameid", "sd"]).teamname.to_dict()
    pl = pl[pl.position.isin(config.ROLES)].copy(); look = {(g, data.key(c)): (r, s.lower()) for g, c, r, s in zip(pl.gameid, pl.champion, pl.position, pl.side)}
    tm, ev, gold = data.timelines()
    if games is not None: tm = tm[tm.gameid.isin(games)]
    ev = ev[ev.gid.isin(tm.gid)].sort_values(["gid", "t"]); gold = gold[(gold.kind == "gold") & gold.gid.isin(tm.gid)]
    GW = gold.pivot_table(index=["gid", "minute"], columns=["side", "role"], values="value")
    LR = {"top": ["top"], "jng": ["jng"], "mid": ["mid"], "bot": ["bot", "sup"]}; LANES = ["top", "jng", "mid", "bot"]; PL = {"TOP": "top", "MID": "mid", "BOT": "bot"}
    OTH = {"blue": "red", "red": "blue"}; F, plates, drag, grub = [], [], [], []
    for g in tm.itertuples():
        e = ev[ev.gid == g.gid]; isw = float(g.league == "WLDs")
        def edge(m, s, roles):
            try: row = GW.loc[(g.gid, m)]
            except KeyError: return None
            return sum(row[(s, r)] - row[(OTH[s], r)] for r in roles) / 1000
        K = []
        for x in e[e.type == "kill"].itertuples():
            k = look.get((g.gameid, data.key(x.champ))); v = look.get((g.gameid, data.key(x.victim_champ)))
            if k and v: K.append((x.t, k[1], k[0], v[0], not isinstance(x.assists, str), x))
        # fights before 14:00
        cur = []
        def close(cur):
            if not cur: return
            roles, net = set(), 0
            for (t, ks, kr, vr, so, x) in cur:
                roles |= {kr, vr} | {look[(g.gameid, data.key(a))][0] for a in str(x.assists).split("|") if isinstance(x.assists, str) and (g.gameid, data.key(a)) in look}
                net += 1 if ks == "blue" else -1
            if net == 0: return
            m = int(cur[0][0] // 60)
            try: row = GW.loc[(g.gid, m)]; st = sum(row[("blue", r)] - row[("red", r)] for r in roles) / 1000
            except KeyError: return
            pe = sum(PE.get((g.gameid, r), np.nan) for r in roles) / 1000
            if np.isnan(pe): return
            F.append({"gameid": g.gameid, "day": g.day, "league": g.league, "t": cur[0][0], "y": float(net > 0), "pre": pe, "state": st, "team": Z.get(g.gameid, 0) or 0})
        for k_ in [k_ for k_ in K if k_[0] < 840]:
            if cur and k_[0] - cur[-1][0] > 20: close(cur); cur = []
            cur.append(k_)
        close(cur)
        pls = [(x.t, x.side, PL.get(str(x.detail))) for x in e[(e.type == "plate") & (e.t < 840)].itertuples()]
        t1 = {(x.side, PL.get(str(x.detail).split()[1])): x.t for x in e[(e.type == "tower") & e.detail.astype(str).str.match(r"T1 (TOP|MID|BOT)$")].itertuples()}
        grubs_t = [(x.t, x.side) for x in e[e.type == "grub"].itertuples()]
        for s in ("blue", "red"):
            for m in range(3, 14):
                t0 = 60 * m
                for L in ("top", "mid", "bot"):
                    ed = edge(m, s, LR[L])
                    if ed is None or t1.get((s, L), 1e9) < t0: continue
                    plates.append({"day": g.day, "league": g.league, "m": m, "lane": L, "edge": ed,
                                   "y": sum(1 for t, ps, pL in pls if ps == s and pL == L and t0 <= t < t0 + 60),
                                   "en_dead": sum(1 for t, ks, kr, vr, so, _ in K if ks == s and vr in LR[L] and t0 - 60 <= t < t0 + 30),
                                   "own_dead": sum(1 for t, ks, kr, vr, so, _ in K if ks == OTH[s] and vr in LR[L] and t0 - 60 <= t < t0 + 30),
                                   "taken": sum(1 for t, ps, pL in pls if ps == s and pL == L and t < t0), "grubs": sum(1 for t, gs in grubs_t if gs == s and t < t0)})
        def at(t):
            m = int(t // 60); out = {}
            for L in LANES:
                v = edge(m, "blue", LR[L]); out[L] = 0.0 if v is None else v
            out["net60"] = sum((1 if ks == "blue" else -1) for tk, ks, kr, vr, so, _ in K if t - 60 <= tk < t)
            return out
        dd = e[e.type == "dragon"]
        if len(dd):
            x = dd.iloc[0]; drag.append({"gameid": g.gameid, "day": g.day, "league": g.league, "y": float(x.side == "blue"), "z": Z.get(g.gameid, 0) or 0, "w": isw, **at(x.t),
                                         "tb": team.get((g.gameid, "blue")), "tr": team.get((g.gameid, "red"))})
        for t, s in grubs_t[:3]:
            grub.append({"gameid": g.gameid, "day": g.day, "league": g.league, "y": float(s == "blue"), "z": Z.get(g.gameid, 0) or 0, "w": isw, **at(t),
                         "tb": team.get((g.gameid, "blue")), "tr": team.get((g.gameid, "red"))})
    return {"fights": pd.DataFrame(F), "plates": pd.DataFrame(plates), "dragon": pd.DataFrame(drag), "grubs": pd.DataFrame(grub)}
