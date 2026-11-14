"""Laning slice: what each event really pays, from the Worlds feed second by second, against the official values (14 Nov 2026 AEST;
Luke: read the official docs as well to find gold values). Read-only.
Official values (League of Legends Wiki, read 14 Nov 2026): Gold (passive 20.4 per 10 s from 1:05; edited 3 Jul 2026), Champion gold
bounties (base 300 at levels 1-6, +10 a level to 420; first blood +100 since V26.01; bounty rises 1 per 3 gold from kills / assists and
1 per 20 from farm, shutdown above base + 100, at most base + 700 to the killer; assist pool half the bounty, at most half the base, split
among assisters, reduced early; edited 6 Jul 2026), Turret (plate 120, shared by nearby allies; first turret +300; outer turret 50 global),
Role Quests (bot lane: 300 gold on completion, then +2 a minion and +40 a takedown; jungle: +10 a camp; edited 8 Nov 2026, V26.19),
Voidgrub camp (30 gold, 3 grubs at 8:00; edited 9 Nov 2026), Infernal Drake (75 gold; edited 26 Mar 2026), Minion (melee 20, caster 14,
siege 50 to 59).
Measured (feed clocks from s5_feed_analysis.py; gold earned in a 4 s window around the event, less the passive gold of those seconds):
  kills: the killer's gain, by first blood or not, the victim's earlier kills and assists, and whether the killer had assisters
  assists: each assister's gain
  bot-lane quest: one-off jumps of 250+ gold for ADCs with no kill, assist or plate in the window (the 300 lump), and when
Then the actions-only lane test (s5_farm.py D) again, paying each real kill and assist what it really paid in that game, to see whether
the size of kills closes the gold gap.
usage (repo root): python -I research/laning/s5_event_gold.py   (writes research/model/laning/event_gold.json)"""
import sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
OUT = config.MODEL_DIR / "laning" / "event_gold.json"
ROLE_FEED = {"top": "top", "jungle": "jng", "mid": "mid", "bottom": "bot", "support": "sup"}
PASSIVE = 2.04  # gold a second from 1:05 (wiki, Gold)
with Run("event_gold", inputs=[config.OE_CSV, config.TL_MATCH, config.TL_EVENTS, config.MODEL_DIR / "laning" / "feed_analysis.json"]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "champion"]); data.check(o)
    W = o[(o.league == "WLDs") & o.position.isin(config.ROLES)]
    sig = {v: k for k, v in W.groupby("gameid").champion.apply(lambda s: "|".join(sorted(data.key(c) for c in s))).items()}
    FA = json.load(open(config.MODEL_DIR / "laning" / "feed_analysis.json")); OFF = {c["gameid"]: c["offset_s"] for c in FA["per game checks"] if c.get("aligned")}
    tm, ev, _ = data.timelines(); pl_ev = ev[ev.type == "plate"]
    K, A_, Q = [], [], []
    for f in sorted(glob.glob(str(config.FEED_DIR / "1*.json"))):
        d = json.load(open(f)); P = d["meta"]["blueTeamMetadata"]["participantMetadata"] + d["meta"]["redTeamMetadata"]["participantMetadata"]
        gid = sig.get("|".join(sorted(data.key(p["championId"]) for p in P)))
        if gid is None or gid not in OFF: continue
        role = [ROLE_FEED[p["role"]] for p in P]; side = ["blue"] * 5 + ["red"] * 5
        sec = np.array([x[0] for x in d["frames"]]) + OFF[gid]; A = np.array([x[1] for x in d["frames"]], dtype=float)
        tg = tm[tm.gameid == gid].gid; plt_ = pl_ev[pl_ev.gid == tg.iloc[0]].t.values if len(tg) else np.array([])
        def at(t):
            i = np.searchsorted(sec, t); c = [j for j in (i - 1, i) if 0 <= j < len(sec) and abs(sec[j] - t) <= 1]
            return min(c, key=lambda j: abs(sec[j] - t)) if c else None
        first = True; kills_before = np.zeros(10); assists_before = np.zeros(10)
        for i in range(1, len(sec)):
            dk = A[i, :, 2] - A[i - 1, :, 2]; da = A[i, :, 4] - A[i - 1, :, 4]; dd = A[i, :, 3] - A[i - 1, :, 3]
            if dk.sum() == 1 and dd.sum() == 1 and sec[i] - sec[i - 1] <= 2:  # one clean kill this second
                k = int(np.argmax(dk)); v = int(np.argmax(dd)); a0, a1 = at(sec[i] - 2), at(sec[i] + 2)
                if a0 is not None and a1 is not None:
                    win = sec[a1] - sec[a0]; busy = (A[a1, :, 2] - A[a0, :, 2]).sum() > 1 or any(abs(t - sec[i]) <= 3 for t in plt_)
                    gain = A[a1, k, 0] - A[a0, k, 0] - PASSIVE * win
                    K.append({"gameid": gid, "t": sec[i], "first_blood": first, "victim_kills_before": kills_before[v], "victim_assists_before": assists_before[v],
                              "assisters": int(da[[j for j in range(10) if side[j] == side[k]]].sum()), "gain": gain, "clean": not busy, "killer_role": role[k]})
                    for j in range(10):
                        if da[j] > 0 and side[j] == side[k]: A_.append({"gameid": gid, "t": sec[i], "gain": A[a1, j, 0] - A[a0, j, 0] - PASSIVE * win, "n_assist": int(da.sum()), "clean": not busy})
                first = False
            kills_before += np.maximum(dk, 0); assists_before += np.maximum(da, 0)
        for p in range(10):
            if role[p] != "bot": continue
            for i in range(1, len(sec)):
                g_ = A[i, p, 0] - A[i - 1, p, 0]; dt = sec[i] - sec[i - 1]
                if dt <= 2 and g_ - PASSIVE * dt >= 250 and A[i, p, 2] == A[i - 1, p, 2] and A[i, p, 4] == A[i - 1, p, 4] and not any(abs(t - sec[i]) <= 3 for t in plt_):
                    Q.append({"gameid": gid, "side": side[p], "t": sec[i], "jump": g_ - PASSIVE * dt})
    Kd, Ad, Qd = pd.DataFrame(K), pd.DataFrame(A_), pd.DataFrame(Q)
    Kc = Kd[Kd.clean]; R = {"kills measured (clean: no other kill or plate within 3 s)": [len(Kc), len(Kd)]}
    R["kill gold to the killer"] = {"first blood": [round(float(Kc[Kc.first_blood].gain.median())), int(Kc.first_blood.sum())],
                                    "other kills, median": round(float(Kc[~Kc.first_blood].gain.median())),
                                    "other kills, 10th / 90th percentile": [round(float(Kc[~Kc.first_blood].gain.quantile(q))) for q in (0.1, 0.9)],
                                    "official": "base 300-420 by the victim's level, first blood +100, more for a victim with kills and assists (shutdown)"}
    nf = Kc[~Kc.first_blood].copy(); nf["victim_ka"] = nf.victim_kills_before + nf.victim_assists_before
    R["kill gold by the victim's earlier kills + assists (median, n)"] = {str(b): [round(float(g.gain.median())), len(g)] for b, g in nf.groupby(pd.cut(nf.victim_ka, [-1, 0, 1, 2, 4, 99]))}
    nf["solo"] = nf.assisters == 0
    R["kill gold, solo v with assisters (median)"] = {"solo": round(float(nf[nf.solo].gain.median())), "with assisters": round(float(nf[~nf.solo].gain.median()))}
    Ac = Ad[Ad.clean]
    R["assist gold to each assister (median by number of assisters)"] = {str(n): [round(float(g.gain.median())), len(g)] for n, g in Ac.groupby(Ac.n_assist.clip(upper=4))}
    if len(Qd):
        first_q = Qd.sort_values("t").groupby(["gameid", "side"]).first()
        R["bot-lane quest lump (first 250+ jump with no kill, assist or plate)"] = {"ADCs seen": len(first_q), "median gold": round(float(first_q.jump.median())),
                                                                                   "median time": f"{int(first_q.t.median()) // 60}:{int(first_q.t.median()) % 60:02d}",
                                                                                   "10th / 90th percentile time": [f"{int(x) // 60}:{int(x) % 60:02d}" for x in first_q.t.quantile([0.1, 0.9])]}
    run.result("clean kills", len(Kc)); run.save_json(OUT, R); print(json.dumps(R, indent=1))
