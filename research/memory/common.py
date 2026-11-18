"""Shared fight code for the game-memory scripts (17 Nov 2026): deaths with measured respawns, fights by death gap, the gold-swing winner.
See m1_fights.py for what each step does and why the gap is 20 s."""
import numpy as np
HP_DROP, HP_PER_SIDE = 0.05, 2; AFTER = 5
FIGHT_GAP = 20   # where the gaps between deaths stop thinning out (m1_fights.json, 17 Nov)

# official death timer (League wiki, Respawn page, read 14 Nov 2026; the same as research/sim4/deathtimer_check.py), with the feed's level
BRW = [10, 10, 12, 12, 14, 16, 20, 25, 28, 32.5, 35, 37.5, 40, 42.5, 45, 47.5, 50, 52.5]
def tif(t):
    h = t / 30.0
    return min(0.00425 * min(max(h - 30, 0), 30) + 0.0030 * min(max(h - 60, 0), 30) + 0.0145 * min(max(h - 90, 0), 20), 0.5)
def wiki_timer(level, t): return BRW[int(min(max(level, 1), 18)) - 1] * (1 + tif(t))
RESPAWN_TOL = 5   # measured respawn kept when within 5 s of the official timer; otherwise the feed's health was not read at the death

def deaths(g):
    """every death: time, player, the respawn (measured from health when it agrees with the official timer, else the timer: "src")"""
    t, P = g["t"], g["P"]; d, hp = P[:, :, 3], P[:, :, 6]; ev = []
    for p in range(10):
        for i in np.where(np.diff(d[:, p]) > 0)[0] + 1:
            for _ in range(int(d[i, p] - d[i - 1, p])):
                wt = wiki_timer(P[i, p, 1], t[i]); resp, src, over = t[i] + wt, "timer", False
                z = [j for j in range(max(i - 2, 0), min(i + 4, len(t))) if hp[j, p] <= 0]
                if z:
                    k = z[0]
                    while k < len(t) and hp[k, p] <= 0: k += 1
                    if k >= len(t): over = True
                    elif abs((t[k] - t[i]) - wt) <= RESPAWN_TOL: resp, src = t[k], "measured"
                if t[i] + wt >= t[-1] and not over: over = t[i] + wt >= t[-1]
                ev.append({"t": t[i], "i": i, "p": p, "side": g["sides"][p], "role": g["roles"][p], "level": P[i, p, 1],
                           "respawn": np.nan if over else resp, "src": "game over" if over else src, "wiki": wt, "game_over": over})
    return sorted(ev, key=lambda e: e["t"])

def contact(g):
    """seconds where >= HP_PER_SIDE players on each side lose >= HP_DROP of their max health"""
    P = g["P"]; hp, mx = P[:, :, 6], np.maximum(P[:, :, 7], 1)
    drop = np.r_[np.zeros((1, 10), bool), (hp[:-1] - hp[1:]) / mx[1:] >= HP_DROP] & (hp > 0)
    return np.where((drop[:, :5].sum(1) >= HP_PER_SIDE) & (drop[:, 5:].sum(1) >= HP_PER_SIDE))[0]

def at(t, x):
    return min(max(int(np.searchsorted(t, x)), 0), len(t) - 1)

def fights(g, ev, G):
    t, T, P = g["t"], g["T"], g["P"]; out, cur = [], []
    for e in ev:
        if cur and e["t"] - cur[-1]["t"] > G: out.append(cur); cur = []
        cur.append(e)
    if cur: out.append(cur)
    rows = []
    for n, f in enumerate(out):
        t0, t1 = f[0]["t"] - G, f[-1]["t"] + AFTER; i0, i1 = at(t, t0), at(t, t1)
        swing = (T[i1, 0, 0] - T[i1, 1, 0]) - (T[i0, 0, 0] - T[i0, 1, 0])
        db, dr = sum(e["side"] == "blue" for e in f), sum(e["side"] == "red" for e in f)
        seg = slice(i0, i1 + 1); hp, mx = P[seg, :, 6], np.maximum(P[seg, :, 7], 1)
        hurt = ((hp[:-1] - hp[1:]) / mx[1:] >= HP_DROP).any(0) | np.isin(np.arange(10), [e["p"] for e in f])  # took part: lost health or died
        alive0 = P[i0, :, 6] > 0; hp0 = P[i0, :, 6] / np.maximum(P[i0, :, 7], 1)
        rows.append({"gameid": g["gameid"], "day": g["day"], "n": n, "t_first": f[0]["t"], "t_last": f[-1]["t"], "t0": t[i0], "t1": t[i1],
                     "deaths_blue": db, "deaths_red": dr, "swing": swing,
                     "win_gold": "blue" if swing > 0 else "red" if swing < 0 else "even",
                     "win_kills": "blue" if dr > db else "red" if db > dr else "trade",
                     "in_blue": int((hurt & alive0)[:5].sum()), "in_red": int((hurt & alive0)[5:].sum()),
                     "hp_blue": float((hp0 * (hurt & alive0))[:5].sum()), "hp_red": float((hp0 * (hurt & alive0))[5:].sum()),
                     "alive_blue": int(alive0[:5].sum()), "alive_red": int(alive0[5:].sum()),
                     "lead_before": float(T[i0, 0, 0] - T[i0, 1, 0]), "winner_game": g["winner"],
                     "respawn_blue": max([e["respawn"] for e in f if e["side"] == "blue"], default=np.nan),
                     "respawn_red": max([e["respawn"] for e in f if e["side"] == "red"], default=np.nan),
                     "victims": "|".join(f'{e["side"][0]}{e["role"]}' for e in f)})
    return rows


# event-list fights (gol.gg timelines and the research sim's event log; moved from m4_timelines.py 17 Nov): kills 20 s apart, winner by kills
import pandas as pd
OBJ = ["tower", "inhib", "baron", "dragon"]
r3 = lambda x: round(float(x), 3)
def dead_table(games):
    E = pd.DataFrame([e for g in games for e in deaths(g)]); E = E[E.respawn.notna()]
    m = (E.t // 60).astype(int); med = (E.respawn - E.t).groupby(m).median()
    full = pd.Series(np.interp(np.arange(70), med.index, med.values), index=np.arange(70))  # straight lines between measured minutes
    return full, int(len(E))

def game_rows(ev, win, length, DT):
    """ev: DataFrame or list of (t, side, type) events; fights = kills less than FIGHT_GAP s apart, winner by kills (trades left out),
    window from the last kill to the losers' respawn (DT: death seconds by minute), objectives in the window by each side"""
    if isinstance(ev, pd.DataFrame): ev = list(zip(ev.t.tolist(), ev.side.tolist(), ev.type.tolist()))
    kills = sorted((t, s) for t, s, ty in ev if ty == "kill"); out = []
    if not kills: return out
    groups, cur = [], [kills[0]]
    for e in kills[1:]:
        if e[0] - cur[-1][0] > FIGHT_GAP: groups.append(cur); cur = []
        cur.append(e)
    groups.append(cur)
    objs = [(t, s, ty) for t, s, ty in ev if ty in OBJ or ty == "nexus"]
    def kw(f):
        kb = sum(s == "blue" for _, s in f); kr = len(f) - kb
        return ("blue" if kb > kr else "red" if kr > kb else "trade"), kb, kr
    for n, f in enumerate(groups):
        w, kb, kr = kw(f)
        if w == "trade": continue
        L = "red" if w == "blue" else "blue"; t1 = max(t for t, _ in f)
        end = min(max(t + DT[min(int(t // 60), 69)] for t, s in f if s == w), length)  # the loser's deaths are the winner's kills
        inw = [(s, ty) for t, s, ty in objs if t1 < t <= end]
        r = {"t": t1, "loser_deaths": max(kb, kr), "window_s": end - t1, "nexus": int(any(s == w and ty == "nexus" for s, ty in inw))}
        for o in OBJ:
            r[o + "_w"] = sum(s == w and ty == o for s, ty in inw); r[o + "_l"] = sum(s == L and ty == o for s, ty in inw)
        nxt = groups[n + 1] if n + 1 < len(groups) else None
        r["next_t"] = float(min(t for t, _ in nxt)) if nxt is not None else np.nan
        r["next_winner"] = kw(nxt)[0] if nxt is not None else None
        r["winner"] = w; r["won_game"] = int(win == w)
        r["loser_won_fight_in_window"] = int(nxt is not None and r["next_t"] <= end and r["next_winner"] == L)
        r["loser_contested"] = int(any(r[o + "_l"] > 0 for o in OBJ) or r["loser_won_fight_in_window"])
        out.append(r)
    return out

def block(x):
    o = {"fights": int(len(x)), "window median s": round(float(x.window_s.median()))}
    for k in OBJ: o[k + " winner per fight"] = r3(x[k + "_w"].mean()); o[k + " loser per fight"] = r3(x[k + "_l"].mean())
    o["winner takes anything"] = r3((x[[k + "_w" for k in OBJ]].sum(1) > 0).mean()); o["Nexus in window"] = r3(x.nexus.mean())
    o["loser contested"] = r3(x.loser_contested.mean())
    nx = x[x.next_winner.isin(["blue", "red"])]; o["winner wins the next fight"] = r3((nx.next_winner == nx.winner).mean())
    o["fight winner wins the game"] = r3(x.won_game.mean())
    return o

