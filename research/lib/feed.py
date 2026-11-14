"""The lolesports feed (Worlds, second by second) as tables (14 Nov 2026; the same code as research/laning/s5_farm.py and s5_rule_gold.py,
moved here for the step 3 fits). Clocks come from the gol.gg timelines (offsets in research/model/laning/feed_analysis.json).
  games()           yields (gameid, roles[10], sides[10], seconds, frames array [n, 10, 8: gold, level, k, d, a, cs, hp, maxhp])
  player_minutes()  one row per player per minute 1:00-14:59: dgold, dcs, dk, da, dd, dead share, own-lane plates, side's towers, first tower
  quest_times()     each ADC's bot-lane quest completion (first 250+ gold jump with no kill, assist or plate, from 10:00: the quest needs 1,350
                    points, and passive points plus a full lane of minions can't reach that much before then): gameid, side, t"""
import json, glob
import numpy as np, pandas as pd
from . import config, data
ROLE_FEED = {"top": "top", "jungle": "jng", "mid": "mid", "bottom": "bot", "support": "sup"}; LANE_OF = {"top": "TOP", "mid": "MID", "bot": "BOT", "sup": "BOT"}
PASSIVE = 2.04  # gold a second from 1:05 (League wiki, Gold)

def games():
    o = data.oe(["gameid", "league", "date", "position", "champion"])
    W = o[(o.league == "WLDs") & o.position.isin(config.ROLES)]
    sig = {v: k for k, v in W.groupby("gameid").champion.apply(lambda s: "|".join(sorted(data.key(c) for c in s))).items()}
    FA = json.load(open(config.MODEL_DIR / "laning" / "feed_analysis.json")); OFF = {c["gameid"]: c["offset_s"] for c in FA["per game checks"] if c.get("aligned")}
    for f in sorted(glob.glob(str(config.FEED_DIR / "1*.json"))):
        d = json.load(open(f)); P = d["meta"]["blueTeamMetadata"]["participantMetadata"] + d["meta"]["redTeamMetadata"]["participantMetadata"]
        gid = sig.get("|".join(sorted(data.key(p["championId"]) for p in P)))
        if gid is None or gid not in OFF: continue
        yield gid, [ROLE_FEED[p["role"]] for p in P], ["blue"] * 5 + ["red"] * 5, np.array([x[0] for x in d["frames"]]) + OFF[gid], np.array([x[1] for x in d["frames"]], dtype=float)

def _events():
    tm, ev, _ = data.timelines(); g2 = dict(zip(tm.gameid, tm.gid))
    return g2, ev[(ev.type == "plate") & (ev.t < 900)], ev[(ev.type == "tower") & (ev.t < 900)]

def player_minutes():
    o = data.oe(["gameid", "league", "date", "position"]); day = o[o.league == "WLDs"].drop_duplicates("gameid").set_index("gameid").date.str[:10].to_dict()
    g2, plates, towers = _events(); rows = []
    for gid, role, side, sec, A in games():
        pl = plates[plates.gid == g2.get(gid)]; tw = towers[towers.gid == g2.get(gid)]; first_tw = tw.t.min() if len(tw) else 1e9
        def at(t):
            i = np.searchsorted(sec, t); cand = [j for j in (i - 1, i) if 0 <= j < len(sec) and abs(sec[j] - t) <= 3]
            return min(cand, key=lambda j: abs(sec[j] - t)) if cand else None
        for m in range(1, 15):
            i0, i1 = at(60 * m), at(60 * m + 60)
            if i0 is None or i1 is None: continue
            seg = (sec >= sec[i0]) & (sec <= sec[i1])
            for p in range(10):
                rows.append({"gameid": gid, "day": day[gid], "m": m, "side": side[p], "role": role[p], "dgold": A[i1, p, 0] - A[i0, p, 0], "dcs": A[i1, p, 5] - A[i0, p, 5],
                             "dk": A[i1, p, 2] - A[i0, p, 2], "da": A[i1, p, 4] - A[i0, p, 4], "dd": A[i1, p, 3] - A[i0, p, 3],
                             "dead": float(np.mean(A[seg, p, 6] <= 0)) if seg.any() else 0.0,
                             "plates": int(((pl.side == side[p]) & (pl.detail == LANE_OF.get(role[p], "")) & (pl.t >= 60 * m) & (pl.t < 60 * m + 60)).sum()) if role[p] != "jng" else 0,
                             "towers": int(((tw.side == side[p]) & (tw.t >= 60 * m) & (tw.t < 60 * m + 60)).sum()),
                             "first_tower": int((tw[tw.t == first_tw].side == side[p]).any() and 60 * m <= first_tw < 60 * m + 60)})
    return pd.DataFrame(rows)

def quest_times():
    o = data.oe(["gameid", "league", "date", "position"]); day = o[o.league == "WLDs"].drop_duplicates("gameid").set_index("gameid").date.str[:10].to_dict()
    g2, plates, _ = _events(); out = []
    for gid, role, side, sec, A in games():
        plt_ = plates[plates.gid == g2.get(gid)].t.values
        for p in range(10):
            if role[p] != "bot": continue
            for i in range(1, len(sec)):
                g_ = A[i, p, 0] - A[i - 1, p, 0]; dt = sec[i] - sec[i - 1]
                if sec[i] >= 600 and dt <= 2 and g_ - PASSIVE * dt >= 250 and A[i, p, 2] == A[i - 1, p, 2] and A[i, p, 4] == A[i - 1, p, 4] and not any(abs(t - sec[i]) <= 3 for t in plt_):
                    out.append({"gameid": gid, "day": day[gid], "side": side[p], "t": float(sec[i])}); break
    return pd.DataFrame(out)
