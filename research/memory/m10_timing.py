"""Game memory, play-test check (24 Nov 2026 AEST; Luke OK'd "measure them now" after his v53 Bo5): three things real games are
measured on here, for comparison with the app sim (m10_sim_check.js):
  1. opening kill timing: first blood time (quantiles; share of games with first blood before 0:30, 1:00, 1:30, 2:00, 3:00 and after
     10:00, 13:00) and kills per game in 10-second steps from 0:00 to 3:00 (the v53 Bo5 had first bloods at 0:03, 0:16 and 13:50);
  2. one team's consecutive objective events (dragon / Elder, Baron, Herald = monster; tower, inhibitor, Nexus = structure): the gap
     to the team's next one, by pair (monster then structure, monster then monster, structure then structure): share within 1, 2, 5
     and 10 s, median (the Bo5 had Herald -> tower, soul -> tower, Baron -> inhibitor 1 s apart). Void grubs are left out: the
     timelines log each grub, the sim one event for the set;
  3. dragons by side: blue's share of dragons (the file's "dragons" per team) and of first dragons, Worlds main event and other 2026
     major games (BLG took 15 of 18 dragons in the Bo5, red side in 3 of 4 games).
Sources: gol.gg timelines (640 matched games; Worlds = the file's WLDs games) for 1-2, the Oracle's Elixir file for 3.
Output: research/model/memory/m10_timing.json.
usage (repo root): python -I research/memory/m10_timing.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run

OUT = config.MODEL_DIR / "memory"
r3 = lambda x: round(float(x), 3)
MON = {"dragon", "baron", "herald"}; STR = {"tower", "inhib", "nexus"}

def opening(ev, games):
    K = ev[(ev.type == "kill") & ev.gameid.isin(games)]; fb = K.groupby("gameid").t.min().reindex(games)
    out = {"games": int(len(games)), "games with no kill": int(fb.isna().sum())}
    f = fb.dropna()
    out["first blood time quantiles (s): 5, 10, 25, 50, 75, 90, 95%"] = [round(float(q)) for q in f.quantile([.05, .1, .25, .5, .75, .9, .95])]
    out["share of games with first blood before (s)"] = {str(s): r3((f < s).mean()) for s in (30, 60, 90, 120, 180)}
    out["share of games with first blood after (s)"] = {str(s): r3((f >= s).mean()) for s in (600, 780)}
    k = K[K.t < 180]; out["kills per game by 10 s, 0:00-3:00"] = [r3(((k.t >= a) & (k.t < a + 10)).sum() / len(games)) for a in range(0, 180, 10)]
    return out

def gaps(ev, games):
    E = ev[ev.type.isin(MON | STR)].sort_values(["gameid", "t"]); rows = []
    for (g, s), d in E.groupby(["gameid", "side"]):
        ty, t = d.type.values, d.t.values
        for i in range(1, len(d)):
            a = "monster" if ty[i - 1] in MON else "structure"; b = "monster" if ty[i] in MON else "structure"
            rows.append((f"{a} then {b}", float(t[i] - t[i - 1])))
    D = pd.DataFrame(rows, columns=["pair", "gap"]); out = {}
    for p, x in D.groupby("pair"):
        out[p] = {"pairs": int(len(x)), **{f"within {s} s": r3((x.gap <= s).mean()) for s in (1, 2, 5, 10)}, "median s": round(float(x.gap.median()), 1)}
    return out

def gaps_with_kills(ev):
    """step 0 of the timing fixes (24 Nov): the same gaps with the team's own kills in the sequence (kill = the killing team's event),
    so kill then monster / kill then structure show how soon a team takes something after its kill"""
    E = ev[ev.type.isin(MON | STR | {"kill"})].sort_values(["gameid", "t"]); rows = []
    for (g, s), d in E.groupby(["gameid", "side"]):
        ty, t = d.type.values, d.t.values
        for i in range(1, len(d)):
            if ty[i] == "kill": continue
            a = "kill" if ty[i - 1] == "kill" else "monster" if ty[i - 1] in MON else "structure"; b = "monster" if ty[i] in MON else "structure"
            rows.append((f"{a} then {b}", float(t[i] - t[i - 1])))
    D = pd.DataFrame(rows, columns=["pair", "gap"])
    return {p: {"pairs": int(len(x)), **{f"within {s} s": r3((x.gap <= s).mean()) for s in (1, 2, 5, 10)}, "median s": round(float(x.gap.median()), 1)}
            for p, x in D.groupby("pair") if p.startswith("kill")}

def early_fights(ev, games):
    """fights (kills less than 20 s apart) starting in minutes 0-4: fights per game, and the start second within the minute"""
    K = ev[(ev.type == "kill") & ev.gameid.isin(games)].sort_values(["gameid", "t"]); st = []
    for g, d in K.groupby("gameid"):
        t = d.t.values; new = np.r_[True, np.diff(t) > 20]; st += list(t[new])
    st = np.array(st); out = {}
    for m in range(5):
        x = st[(st >= 60 * m) & (st < 60 * m + 60)] - 60 * m
        out[f"minute {m}"] = {"fights per game": r3(len(x) / len(games)), "start second quantiles 10, 25, 50, 75, 90%": [round(float(q)) for q in np.quantile(x, [.1, .25, .5, .75, .9])] if len(x) else None}
    return out

def dragons(o):
    T = o[o.position == "team"]; T = T[T.league.isin(config.MAJOR)]
    out = {}
    for name, sel in (("Worlds main event (from 23 Oct)", (T.league == "WLDs") & (T.date >= "2026-10-23")), ("other 2026 major games", T.league != "WLDs")):
        x = T[sel]; b = x[x.side == "Blue"].set_index("gameid"); r = x[x.side == "Red"].set_index("gameid"); g = b.index.intersection(r.index)
        db, dr = b.loc[g, "dragons"].astype(float), r.loc[g, "dragons"].astype(float)
        fd = b.loc[g, "firstdragon"].astype(float)
        out[name] = {"games": int(len(g)), "dragons per game": r3((db + dr).mean()), "blue share of dragons": r3(db.sum() / (db + dr).sum()),
                     "blue share of first dragons": r3(fd.mean())}
    return out

with Run("memory_timing", params={"bins_s": 10}, inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "dragons", "firstdragon"]); data.check(o)
    tm, ev, _ = data.timelines(); W = set(tm.gameid[tm.league == "WLDs"]); A = list(tm.gameid)
    R = {"opening": {"all 640 timelines": opening(ev, A), "Worlds": opening(ev, sorted(W))},
         "gaps between one team's consecutive events": {"all 640 timelines": gaps(ev, A), "Worlds": gaps(ev[ev.gameid.isin(W)], sorted(W))},
         "dragons by side": dragons(o),
         "gaps from the team's own kill to its next objective": {"all 640 timelines": gaps_with_kills(ev), "Worlds": gaps_with_kills(ev[ev.gameid.isin(W)])},
         "fights starting in minutes 0-4": {"all 640 timelines": early_fights(ev, A), "Worlds": early_fights(ev, sorted(W))}}
    run.result("games", len(A)); run.save_json(OUT / "m10_timing.json", R)
    print(json.dumps(R, indent=1))
