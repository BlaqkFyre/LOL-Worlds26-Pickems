"""Game memory, step 1 (17 Nov 2026 AEST): choosing how to cut pauses from the feed's clock.
Feed seconds are wall-clock from the game's first gold, so pauses are inside them. Each rule turns feed seconds into game seconds:
a gap over GAP s between frames counts as 1 s, and a stretch of FROZEN s or more with no gold change for anyone (after 1:30) counts 0.
Checked two ways on the 98 Worlds games: length against the Oracle's Elixir file, and each kill's time against gol.gg's timeline
(94 games have one). The rule in lib.feed.clock (gap 5 s, frozen 30 s) was chosen from this table.
Output: research/model/memory/m0_clock.json.
usage (repo root): python -I research/memory/m0_clock.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from lib import config, data, feed
from lib.runlog import Run

RULES = {"no cutting": (1e9, 1e9), "gap 2 s, frozen 30 s": (2, 30), "gap 5 s, frozen 30 s (used)": (5, 30), "gap 10 s, frozen 30 s": (10, 30),
         "gap 5 s, frozen 60 s": (5, 60), "gap 5 s, frozen never": (5, 1e9), "gap 5 s, frozen 1 s": (5, 1)}

def clock(s, gold, gap, froz):
    step = np.diff(s, prepend=s[0]).astype(float); step[step > gap] = 1
    G = gold.sum(1); same = np.r_[False, G[1:] == G[:-1]]; i = 0
    while i < len(s):
        if same[i]:
            j = i
            while j + 1 < len(s) and same[j + 1]: j += 1
            if s[i] > 90 and s[j] - s[i - 1] >= froz: step[i:j + 1] = 0
            i = j + 1
        else: i += 1
    return np.cumsum(step)

with Run("memory_clock", params={"rules": RULES}, inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV]) as run:
    games = feed.full(); tm, ev, _ = data.timelines(); g2 = dict(zip(tm.gameid, tm.gid)); kills = ev[ev.type == "kill"]; R = {}
    for name, (gap, froz) in RULES.items():
        L, Kd, Kl = [], [], []
        for g in games:
            t = clock(g["feed_s"], g["P"][:, :, 0], gap, froz); L.append(t[-1] - g["length"])
            if g["gameid"] in g2:
                K = g["P"][:, :, 2].sum(1); gk = np.sort(kills[kills.gid == g2[g["gameid"]]].t.values)
                fk = t[np.searchsorted(K, np.arange(1, int(K[-1]) + 1))]; n = min(len(gk), len(fk)); d = fk[:n] - gk[:n]
                Kd += list(d); Kl += list(d[gk[:n] > 1500])
        L, Kd, Kl = map(np.array, (L, Kd, Kl))
        R[name] = {"length v file: median s": float(np.median(L)), "games more than 30 s off": int((abs(L) > 30).sum()), "largest s over": float(L.max()),
                   "kills within 3 s of gol.gg": round(float(np.mean(abs(Kd) <= 3)), 3), "kills after 25:00 within 3 s": round(float(np.mean(abs(Kl) <= 3)), 3),
                   "kills compared": int(len(Kd))}
    run.save_json(config.MODEL_DIR / "memory" / "m0_clock.json", R)
    for k, v in R.items(): print(k, v)
