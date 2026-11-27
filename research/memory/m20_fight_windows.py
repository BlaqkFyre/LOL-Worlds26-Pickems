"""Fight windows, counts for the plan (27 Nov 2026 AEST; Luke: "start planning this model now"). Read only; nothing is fitted.
Luke's model: after a won fight the winners know who is dead on both sides and for how long (death timers), and take what fits in that
time (dragon, elder, baron, towers, inhibitors, the base, the Nexus) with the players they have alive, then reset. This counts what real
games show for that, on the 640 gol.gg timelines:
  fight     kills under 20 s apart; the side with more kills wins (ties: no winner); the fight ends at its last kill
  alive     players alive on each side at the last kill (each death lasts the official timer at the victim's level, as m17)
  window    from the last kill until the first / the last of the losers dead at that moment respawn
  takes     the winner's objectives from the fight's start until the next fight starts, split by when they fall (before the first
            loser is back, before all are back, after all are back)
  available at the last kill: dragon / elder / baron up (spawns 5:00 / 20:00, then 5 min after a dragon, 6 min after a baron or once
            elder mode starts), a lane open (the winner has a T3 down), the Nexus exposed (structures left 0, as m16)
  outside   every objective in the games, counted as inside a won-fight window (taken by that fight's winner between the fight's start
            and its losers all back, before the next fight) or outside one
Output: research/model/memory/m20_fight_windows.json and a run record.
usage (repo root): python -I research/memory/m20_fight_windows.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from push_common import DTJ, dead_intervals, dead_at, left_at, kind

OUT = config.MODEL_DIR / "memory"
QS = [10, 25, 50, 75, 90]
qq = lambda a: [round(float(v), 1) for v in np.percentile(a, QS)] if len(a) else None
OBJ = ["dragon", "elder", "baron", "herald", "grub", "outer", "T3", "inhib", "nxt", "nexus"]
def okind(ty, det):
    if ty == "dragon": return "elder" if det == "elder" else "dragon"
    if ty in ("baron", "herald", "grub"): return ty
    return kind(ty, det)
def bucket(a, d): x = a - d; return "ahead 3+" if x >= 3 else "ahead 1-2" if x >= 1 else "even or behind"

with Run("memory_fight_windows", params={"fight_gap_s": 20}, inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV, DTJ]) as run:
    tm, ev, _ = data.timelines(); info = tm.set_index("gid")
    o_ = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
    XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o_.gameid, o_.playername, o_.xpat10, o_.xpat15, o_.xpat20, o_.xpat25)}
    DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
    DEAD, matched = dead_intervals(info, ev, XP, AVG, DT)
    F_rows, O_rows, EX = [], [], []
    for g, d in ev.sort_values(["gid", "t"]).groupby("gid"):
        if g not in info.index: continue
        gi = info.loc[g]; dd = DEAD.get(g, {"blue": [], "red": []})
        ob = d[d.type.isin(["dragon", "baron", "herald", "grub", "tower", "inhib", "nexus"])]
        objs = [(float(t), sd, okind(ty, de)) for t, sd, ty, de in zip(ob.t, ob.side, ob.type, ob.detail)]
        ST = {s: [(t, k) for t, sd_, k in objs if sd_ == s and k in ("outer", "T3", "inhib", "nxt", "nexus")] for s in ("blue", "red")}
        drg = [(t, k) for t, sd_, k in objs if k in ("dragon", "elder")]; bar = [t for t, sd_, k in objs if k == "baron"]
        def up(t):
            nd, soul, elder_mode = 300.0, {"blue": 0, "red": 0}, False
            for tt, sd_, k in [(x, s, k) for x, s, k in objs if k in ("dragon", "elder")]:
                if tt > t: break
                if k == "dragon": soul[sd_] += 1
                if max(soul.values()) >= 4: elder_mode = True
                nd = tt + (360 if elder_mode else 300)
            nb = 1200.0
            for tt in bar:
                if tt > t: break
                nb = tt + 360
            return {"dragon": (not elder_mode) and t >= nd, "elder": elder_mode and t >= nd, "baron": t >= nb}
        k = d[d.type == "kill"]
        if not len(k): continue
        kt, ks = k.t.values.astype(float), k.side.values
        grp = np.cumsum(np.r_[True, np.diff(kt) > 20]); F = []
        for gq in np.unique(grp):
            m = grp == gq; nb_, nr_ = int((ks[m] == "blue").sum()), int((ks[m] == "red").sum())
            F.append((kt[m].min(), kt[m].max(), "blue" if nb_ > nr_ else "red" if nr_ > nb_ else None, nb_, nr_))
        win_spans = []
        for i, (t0, t1, w, nb_, nr_) in enumerate(F):
            if w is None: continue
            o = "red" if w == "blue" else "blue"; nf = F[i + 1][0] if i + 1 < len(F) else 1e9
            back = sorted(e for s, e in dd[o] if s <= t1 < e)
            A, D = 5 - min(5, dead_at(dd[w], t1)), 5 - min(5, dead_at(dd[o], t1))
            first_b, all_b = (back[0] - t1, back[-1] - t1) if back else (0.0, 0.0)
            av = up(t1); lane = any(k_ == "T3" and t < t0 for t, k_ in ST[w])
            left = left_at(ST[w], t0) if lane else None
            takes = [(t - t1, k_) for t, sd_, k_ in objs if sd_ == w and t0 <= t < nf]
            lose = [(t - t1, k_) for t, sd_, k_ in objs if sd_ == o and t0 <= t < min(nf, t1 + all_b)]
            win_spans.append((w, t0, min(nf, t1 + all_b)))
            F_rows.append({"gid": g, "date": gi.date, "worlds": str(gi.tournament).startswith("Worlds"), "w": w, "t1": t1, "A": A, "D": D, "dead_losers": len(back),
                           "first_back": first_b, "all_back": all_b, "kills": (nb_, nr_) if w == "blue" else (nr_, nb_), **{f"up_{x}": v for x, v in av.items()},
                           "lane_open": lane, "left": left, "takes": takes, "loser_takes": lose, "next_fight": nf - t1,
                           "label": f"{gi.tournament} {gi.date} {gi[w]} v {gi[o]}"})
        for t, sd_, k_ in objs:
            O_rows.append({"kind": k_, "inside": any(sd_ == w and a <= t < b for w, a, b in win_spans)})
    Fd, Od = pd.DataFrame(F_rows), pd.DataFrame(O_rows)
    def phase(r, t): return "before first back" if t < r.first_back else "before all back" if t < r.all_back else "after all back"
    R = {"source": "research/memory/m20_fight_windows.py (27 Nov 2026 AEST)", "games": int(Fd.gid.nunique()), "deaths matched to the file's XP": matched,
         "won fights": len(Fd), "won fights at Worlds": int(Fd.worlds.sum())}
    R["won fights by players alive at the last kill (winners v losers)"] = {f"{a}v{d_}": int(n) for (a, d_), n in Fd.groupby(["A", "D"]).size().items()}
    R["window s (10/25/50/75/90%), until the first / all of the losers dead at the last kill respawn"] = {"first back": qq(Fd.first_back), "all back": qq(Fd.all_back)}
    R["window until all back by losers dead"] = {str(n): [int((Fd.dead_losers == n).sum()), qq(Fd[Fd.dead_losers == n].all_back)] for n in range(1, 6)}
    R["next fight from the last kill s (10/25/50/75/90%; none = game over or no fight)"] = qq(Fd.next_fight.clip(upper=3600))
    # what the winners took, by when
    T = [(r.Index, x, k_, phase(r, x)) for r in Fd.itertuples() for x, k_ in r.takes]
    Td = pd.DataFrame(T, columns=["f", "t", "kind", "when"])
    R["winner's takes before the next fight, by kind and when (count)"] = {k_: Td[Td.kind == k_].when.value_counts().to_dict() for k_ in OBJ}
    R["won fights where the winners took nothing before the next fight"] = int((Fd.takes.map(len) == 0).sum())
    R["won fights where the winners took something before all losers were back"] = int(Fd.apply(lambda r: any(x < r.all_back for x, k_ in r.takes), axis=1).sum())
    R["losers' takes before all of them are back (count by kind)"] = pd.Series([k_ for r in Fd.itertuples() for x, k_ in r.loser_takes]).value_counts().to_dict()
    # choice when it is up: share of won fights where the winners took it before all losers were back
    ch = {}
    for x, cond in [("dragon", Fd.up_dragon), ("elder", Fd.up_elder), ("baron", Fd.up_baron)]:
        q = Fd[cond]
        for b in ("ahead 3+", "ahead 1-2", "even or behind"):
            qb = q[q.apply(lambda r: bucket(r.A, r.D) == b, axis=1)]
            took = qb.apply(lambda r: any(k_ == x and t < r.all_back for t, k_ in r.takes), axis=1)
            ch[f"{x} up, {b}"] = [len(qb), round(float(took.mean()), 3) if len(qb) else None]
    for L in range(4):
        q = Fd[Fd.left == L]
        for b in ("ahead 3+", "ahead 1-2", "even or behind"):
            qb = q[q.apply(lambda r: bucket(r.A, r.D) == b, axis=1)]
            took = qb.apply(lambda r: any(k_ == "nexus" for t, k_ in r.takes), axis=1)
            ch[f"lane open, {L} left, {b}: Nexus"] = [len(qb), round(float(took.mean()), 3) if len(qb) else None]
    R["taken when available, by players alive (won fights, share)"] = ch
    # time from the last kill to the first take of each kind, by players alive
    tt = {}
    for k_ in OBJ:
        for b in ("ahead 3+", "ahead 1-2", "even or behind"):
            a = [x for r in Fd.itertuples() if bucket(r.A, r.D) == b for x, kk in r.takes[:] if kk == k_][:]
            tt[f"{k_}, {b}"] = [len(a), qq(a)]
    R["time from the last kill to each take s (10/25/50/75/90%), by players alive"] = tt
    R["objectives inside a won-fight window / all (by kind)"] = {k_: [int(Od[Od.kind == k_].inside.sum()), int((Od.kind == k_).sum())] for k_ in OBJ}
    R["objectives inside a won-fight window, all kinds"] = [int(Od.inside.sum()), len(Od)]
    # worked examples: Worlds won fights with baron up that the winners took, then more
    W = Fd[Fd.worlds & Fd.up_baron & Fd.apply(lambda r: any(k_ == "baron" for t, k_ in r.takes) and len(r.takes) >= 2, axis=1)]
    mm = lambda s: f"{int(s) // 60}:{int(s) % 60:02d}"
    R["examples (Worlds)"] = [f"{r.label}: fight ends {mm(r.t1)} ({r.kills[0]}-{r.kills[1]}), alive {r.A}v{r.D}, losers back +{r.first_back:.0f} s (first) / +{r.all_back:.0f} s (all); "
                              f"winners took {[(round(x), k_) for x, k_ in r.takes]}; next fight +{min(r.next_fight, 9999):.0f} s" for r in W.head(4).itertuples()]
    run.result("won fights", len(Fd)); run.result("inside share", round(Od.inside.mean(), 3))
    run.save_json(OUT / "m20_fight_windows.json", R)
    print(json.dumps(R, indent=1, default=str))
