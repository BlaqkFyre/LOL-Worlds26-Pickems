"""Early kills by role, real v sim (13 Nov 2026 AEST; Luke's feedback on the example play-by-play: a mid killing a jungler at 3:36,
an early fight with bot, jungle, mid and top all in it, a top laner killing a support 1v1 at 5:10).
Real: gol.gg timelines matched to the file (killer, victim and assisting champions mapped to roles through the file's rows), kills
before 15:00 in three windows. Sim: research/sim3/s3_sim.py on the port_ref.json games (default version), its play-by-play log.
Measures (killing side's role -> dying side's role):
  pair shares       killer role x victim role, by window
  same-lane share   killer and victim in the same lane (top-top, mid-mid, bot/sup-bot/sup), jungle counted apart
  laner-v-laner across lanes (e.g. top kills support), and solo kills (no assists) across lanes
  fights            kills within 30 s of each other, both sides; how many different lanes the roles in the fight come from
                    (lanes: top, mid, bot = bot + sup; jungle not a lane), killers, victims and (real only) assisters
Sets: all matched timeline games, Worlds, Worlds knockouts (from 3 Nov).
usage (repo root): python -I research/sim4/early_kill_roles.py <OE csv> tl_match.csv tl_events.csv port_ref.json <out_json> [seeds=200] [fighttypes.json earlykills.json]
  With the two extra files the sim also runs with the lane-aware early kills on (cal["early_kills"] = "on")."""
import sys, json, zlib, importlib.util, os
from collections import Counter
import numpy as np, pandas as pd
CSV, TMF, TEF, RJ, OUT = sys.argv[1:6]; NS = int(sys.argv[6]) if len(sys.argv) > 6 else 200; EKF = sys.argv[7:9] if len(sys.argv) > 8 else None  # [9] = participants.json (optional)
ROLES = ["top", "jng", "mid", "bot", "sup"]; LANE = {"top": "top", "mid": "mid", "bot": "bot", "sup": "bot", "jng": None}
WIN = [("0-5", 0, 300), ("5-10", 300, 600), ("10-15", 600, 900)]
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())

raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "champion"])
pl = raw[raw.position.isin(ROLES)]
tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"])
ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[(ev.type == "kill") & (ev.t < 900) & ev.gid.isin(tm.gid)].merge(tm[["gid", "gameid", "date"]], on="gid")
role_of = {(g, s.lower(), key(c)): p for g, s, c, p in zip(pl.gameid, pl.side, pl.champion, pl.position)}
lg = pl.drop_duplicates("gameid").set_index("gameid").league
rows = []
for e in ev.itertuples():
    o = "red" if e.side == "blue" else "blue"
    k = role_of.get((e.gameid, e.side, key(e.champ))); v = role_of.get((e.gameid, o, key(e.victim_champ)))
    a = [role_of.get((e.gameid, e.side, key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
    rows.append((e.gameid, lg.get(e.gameid, ""), str(e.date)[:10], int(e.t), e.side, k, v, [x for x in a if x], len(a)))
K = pd.DataFrame(rows, columns=["gameid", "league", "day", "t", "side", "killer", "victim", "assist", "n_assist"])
matched = K.killer.notna() & K.victim.notna()
info = {"real_kills_before_15": int(len(K)), "both_roles_matched": int(matched.sum()), "games": int(K.gameid.nunique())}
K = K[matched]

def summarise(D, with_assist):
    out = {}
    for nm, a, b in WIN:
        d = D[(D.t >= a) & (D.t < b)]
        if not len(d): continue
        pairs = Counter(zip(d.killer, d.victim)); n = len(d)
        same = sum(c for (k, v), c in pairs.items() if LANE[k] and LANE[k] == LANE[v])
        cross = sum(c for (k, v), c in pairs.items() if LANE[k] and LANE[v] and LANE[k] != LANE[v])
        jg = sum(c for (k, v), c in pairs.items() if k == "jng" or v == "jng")
        r = {"kills": n, "same_lane": round(same / n, 3), "laner_v_laner_other_lane": round(cross / n, 3), "jungle_killer_or_victim": round(jg / n, 3),
             "top_pairs": {f"{k}>{v}": round(c / n, 3) for (k, v), c in pairs.most_common(8)},
             "mid_kills_jng": round(pairs.get(("mid", "jng"), 0) / n, 3), "top_kills_sup": round(pairs.get(("top", "sup"), 0) / n, 3)}
        if with_assist:
            solo = d[d.n_assist == 0]; sc = Counter(zip(solo.killer, solo.victim))
            r["solo_share"] = round(len(solo) / n, 3)
            r["solo_laner_v_laner_other_lane"] = round(sum(c for (k, v), c in sc.items() if LANE[k] and LANE[v] and LANE[k] != LANE[v]) / n, 3)
        out[nm] = r
    # fights: kills within 30 s of the previous kill in the same game
    F = []
    for g, d in D.sort_values(["gameid", "t"]).groupby("gameid"):
        cur = []; last = -1e9
        for e in d.itertuples():
            if e.t - last > 30 and cur: F.append(cur); cur = []
            cur.append(e); last = e.t
        if cur: F.append(cur)
    fo = {}
    for nm, a, b in WIN:
        fs = [f for f in F if a <= f[0].t < b]
        if not fs: continue
        def lanes(f, assist):
            s = set()
            for e in f:
                for r_ in [e.killer, e.victim] + (list(e.assist) if assist else []):
                    if LANE.get(r_): s.add((e.side if r_ in [e.killer] + (list(e.assist) if assist else []) else "x", LANE[r_]))
            return {l for _, l in s}
        n_l = Counter(len(lanes(f, False)) for f in fs)
        r = {"fights": len(fs), "kills_per_fight": round(np.mean([len(f) for f in fs]), 2),
             "lanes_in_fight_killers_victims": {str(k): round(c / len(fs), 3) for k, c in sorted(n_l.items())},
             "multi_kill_fights_3plus_lanes": round(sum(1 for f in fs if len(f) >= 2 and len(lanes(f, False)) >= 3) / len(fs), 3)}
        if with_assist:
            n_la = Counter(len(lanes(f, True)) for f in fs)
            r["lanes_in_fight_incl_assists"] = {str(k): round(c / len(fs), 3) for k, c in sorted(n_la.items())}
        fo[nm] = r
    out["fights"] = fo
    return out

res = {"info": info, "real": {}}
sets = {"all timeline games": K, "Worlds": K[K.league == "WLDs"], "Worlds knockouts (from 3 Nov)": K[(K.league == "WLDs") & (K.day >= "2026-11-03")]}
for nm, d in sets.items(): res["real"][nm] = dict(games=int(d.gameid.nunique()), **summarise(d, True))

# sim
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim3", "s3_sim.py"))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
R = json.load(open(RJ))
versions = {"default version": (R["P"], R["cal"]["typed_pf_ll"])}
if EKF:
    P2 = dict(R["P"]); P2["fight_typed"] = json.load(open(EKF[0])); P2["early_kills"] = json.load(open(EKF[1]))
    versions["default version + early kills + event order"] = (P2, dict(R["cal"]["typed_pf_ll"], early_kills="on", event_order="on"))
    if len(sys.argv) > 9:  # 13 Nov: + fight players (participants.json), with the early fight counts and event order
        P3 = dict(P2); P3["fight_players"] = json.load(open(sys.argv[9]))
        versions["default + fight players + early counts + event order"] = (P3, dict(R["cal"]["typed_pf_ll"], early_kills="counts", event_order="on", fight_players="on"))
for vn, (PP, cal) in versions.items():
    sim = sm.Sim(PP, cal); srows = []
    for g, x in R["x"].items():
        for j in range(NS):
            o = sim.run(x, seed=1 + zlib.crc32(g.encode()) * 10_000 + j, log=True)  # seeds by game ID (13 Nov fix)
            for e in o["steps"]:
                if e["kind"] != "kill" or e["t"] >= 900: continue
                w = e["text"].replace(" (solo)", "").split(" kills ")
                srows.append((f"{g}#{j}", "sim", "", e["t"], e["side"], w[0], w[1], [], 0 if "(solo)" in e["text"] else 1))
    S = pd.DataFrame(srows, columns=K.columns)
    res["sim (%s, %d games x %d seeds)" % (vn, len(R["x"]), NS)] = summarise(S, False)
    res["sim_solo_share_by_window (%s)" % vn] = {nm: round(float((S[(S.t >= a) & (S.t < b)].n_assist == 0).mean()), 3) for nm, a, b in WIN}
    res["sim_kills_per_game_by_window (%s)" % vn] = {nm: round(float(((S.t >= a) & (S.t < b)).sum() / (len(R["x"]) * NS)), 3) for nm, a, b in WIN}
res["real_kills_per_game_by_window"] = {nm: round(float(((K.t >= a) & (K.t < b)).sum() / K.gameid.nunique()), 3) for nm, a, b in WIN}
json.dump(res, open(OUT, "w"), indent=1); print(json.dumps(res, indent=1))
