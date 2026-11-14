"""Laning slice: lane gold paid by the official rules, then the actions-only lane test again (14 Nov 2026 AEST; Luke: rerun it).
Rules (League of Legends Wiki, opened 14 Nov 2026; see research/laning/s5_event_gold.py for pages and dates):
  kill: the victim's bounty = base (300 at levels 1-6, +10 a level to 420) + accrued bounty above a 100 buffer; accrued rises by 1 per 3
        gold the victim earned from kills and assists and 1 per 20 gold of farm (CS here x 20.2 gold, the measured value); each death
        removes 1 per 3.5 gold paid out; minimum 50; the killer gets at most base + 700; first blood +100
  assist: a pool of half the bounty, at most half the base, split equally among the assisters
  plate: 120, split among the side's laners in that lane (who else was nearby isn't in the data)
  turrets: first turret +300 split like a plate; each turret 50 to every player of the side
  ADC role quest: 300 when it completes (taken from the feed: the ADC's first 250+ jump with no kill, assist or plate), then +2 a minion
        and +40 a takedown
  Not applied (no numbers or no data): the early-game assist reduction (breakpoints not published), shut-down suppression after 6:00
  (thresholds not published), negative-state accrual, jungle quest +10 a camp, grubs and drakes (team gold, not lane).
Then:
  1 the rule gold of each real kill v what the killer really gained (clean kills, feed)
  2 the lane test again: each Worlds lane's CS contest drawn as before (s5_farm.py), plus that game's real events paid by these rules;
    spread and calibration of the gold edge at 15 v real. No noise term.
usage (repo root): python -I research/laning/s5_rule_gold.py   (writes research/model/laning/rule_gold.json)"""
import sys, os, json, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
OUT = config.MODEL_DIR / "laning" / "rule_gold.json"
ROLE_FEED = {"top": "top", "jungle": "jng", "mid": "mid", "bottom": "bot", "support": "sup"}; LANE = {"top": "TOP", "mid": "MID", "bot": "BOT", "sup": "BOT"}
PASSIVE, GPC = 2.04, None
base = lambda lvl: 300 + 10 * max(0, min(18, int(lvl)) - 6)
with Run("rule_gold", inputs=[config.OE_CSV, config.TL_MATCH, config.TL_EVENTS, config.MODEL_DIR / "laning" / "feed_analysis.json", config.MODEL_DIR / "laning" / "farm.json"]) as run:
    FARM = json.load(open(config.MODEL_DIR / "laning" / "farm.json")); GPC = FARM["A gold per minute: per CS, kill, assist, own-lane plate, whole minute dead"]["dcs"]
    o = data.oe(["gameid", "league", "date", "side", "position", "champion", "csdiffat15", "golddiffat15"]); data.check(o)
    W = o[(o.league == "WLDs") & o.position.isin(config.ROLES)]
    sig = {v: k for k, v in W.groupby("gameid").champion.apply(lambda s: "|".join(sorted(data.key(c) for c in s))).items()}
    FA = json.load(open(config.MODEL_DIR / "laning" / "feed_analysis.json")); OFF = {c["gameid"]: c["offset_s"] for c in FA["per game checks"] if c.get("aligned")}
    tm, ev, _ = data.timelines()
    kills_cmp, lane_rule = [], []
    for f in sorted(glob.glob(str(config.FEED_DIR / "1*.json"))):
        d = json.load(open(f)); P = d["meta"]["blueTeamMetadata"]["participantMetadata"] + d["meta"]["redTeamMetadata"]["participantMetadata"]
        gid = sig.get("|".join(sorted(data.key(p["championId"]) for p in P)))
        if gid is None or gid not in OFF: continue
        role = [ROLE_FEED[p["role"]] for p in P]; side = ["blue"] * 5 + ["red"] * 5
        sec = np.array([x[0] for x in d["frames"]]) + OFF[gid]; A = np.array([x[1] for x in d["frames"]], dtype=float)
        tg = tm[tm.gameid == gid].gid; e = ev[ev.gid == tg.iloc[0]] if len(tg) else ev.iloc[:0]
        pl = e[(e.type == "plate") & (e.t < 900)]; tw = e[(e.type == "tower") & (e.t < 900)].sort_values("t")
        gold = np.zeros(10); ka_gold = np.zeros(10); paid_out = np.zeros(10); first = True; quest_t = {}
        for p in range(10):  # ADC quest completion time from the feed
            if role[p] != "bot": continue
            for i in range(1, len(sec)):
                g_ = A[i, p, 0] - A[i - 1, p, 0]; dt = sec[i] - sec[i - 1]
                if dt <= 2 and g_ - PASSIVE * dt >= 250 and A[i, p, 2] == A[i - 1, p, 2] and A[i, p, 4] == A[i - 1, p, 4] and not any(abs(t - sec[i]) <= 3 for t in pl.t): quest_t[p] = sec[i]; break
        def accrued(p, i):
            farm = A[i, p, 5] * GPC
            return ka_gold[p] / 3 + farm / 20 - paid_out[p] / 3.5
        for i in range(1, len(sec)):
            if sec[i] > 900: break
            dk = A[i, :, 2] - A[i - 1, :, 2]; da = A[i, :, 4] - A[i - 1, :, 4]; dd = A[i, :, 3] - A[i - 1, :, 3]
            if dd.sum() >= 1 and dk.sum() >= 1:
                victims = [v for v in range(10) for _ in range(int(dd[v]))]; killers = [k for k in range(10) for _ in range(int(dk[k]))]
                for v, k in zip(victims, killers):
                    b0 = base(A[i - 1, v, 1]); bounty = max(50.0, b0 + max(0.0, accrued(v, i - 1) - 100)); bounty = min(bounty, b0 + 700)
                    kg = bounty + (100 if first else 0); first = False
                    asts = [j for j in range(10) if da[j] > 0 and side[j] == side[k]]
                    pool = min(0.5 * bounty, 0.5 * b0); ag = pool / len(asts) if asts else 0.0
                    gold[k] += kg; ka_gold[k] += kg
                    for j in asts: gold[j] += ag; ka_gold[j] += ag
                    if k in quest_t and sec[i] >= quest_t[k]: gold[k] += 40
                    for j in asts:
                        if j in quest_t and sec[i] >= quest_t[j]: gold[j] += 40
                    paid_out[v] += kg + ag * len(asts)
                    if dk.sum() == 1 and dd.sum() == 1:
                        a0 = np.searchsorted(sec, sec[i] - 2); a1 = min(len(sec) - 1, np.searchsorted(sec, sec[i] + 2))
                        busy = any(abs(t - sec[i]) <= 3 for t in pl.t)
                        if not busy and sec[a1] - sec[a0] <= 6:
                            kills_cmp.append({"rule": kg, "real": A[a1, k, 0] - A[a0, k, 0] - PASSIVE * (sec[a1] - sec[a0]), "accrued": accrued(v, i - 1)})
        # plates, turrets, quest lump and minion bonus, per player
        for x in pl.itertuples():
            ps = [p for p in range(10) if side[p] == x.side and LANE.get(role[p]) == x.detail]
            for p in ps: gold[p] += 120 / len(ps)
        if len(tw):
            ft = tw.iloc[0]; L = str(ft.detail).split()[-1] if isinstance(ft.detail, str) else ""
            ps = [p for p in range(10) if side[p] == ft.side and LANE.get(role[p]) == L] or [p for p in range(10) if side[p] == ft.side]
            for p in ps: gold[p] += 300 / len(ps)
            for x in tw.itertuples():
                for p in range(10):
                    if side[p] == x.side: gold[p] += 50
        i15 = min(len(sec) - 1, np.searchsorted(sec, 900))
        for p, t in quest_t.items():
            if t <= 900:
                iq = np.searchsorted(sec, t); gold[p] += 300 + 2 * (A[i15, p, 5] - A[iq, p, 5])
        for r in config.ROLES:
            b = [p for p in range(5) if role[p] == r]; rr = [p for p in range(5, 10) if role[p] == r]
            if b and rr: lane_rule.append({"gameid": gid, "role": r, "rule_events": gold[b[0]] - gold[rr[0]]})
    KC = pd.DataFrame(kills_cmp); R = {"kills compared": len(KC)}
    R["1 kill gold: rule v real"] = {"mean abs difference": round(float((KC.rule - KC.real).abs().mean()), 1), "median rule / real": [round(float(KC.rule.median())), round(float(KC.real.median()))],
                                     "correlation": round(float(KC.rule.corr(KC.real)), 3), "share within 30 gold": round(float(((KC.rule - KC.real).abs() <= 30).mean()), 3)}
    # 2 the lane test with rule gold (CS contest as in s5_farm.py D)
    LR = pd.DataFrame(lane_rule).set_index(["gameid", "role"]).rule_events
    FD = FARM["D actions-only lanes v real (Worlds; real events, simulated farm contest, no lead noise)"]
    real = W.set_index(["gameid", "side", "position"]); out = {}; rng = np.random.default_rng(14112026)
    for r in config.ROLES:
        sd_cs = FD[r]["CS edge: actions-only sd"]; rows = []
        for (g, rr), evg in LR.items():
            if rr != r: continue
            rc = real.loc[(g, "Blue", r)]
            if pd.isna(rc.golddiffat15) or pd.isna(rc.csdiffat15): continue
            rows.append((rc.golddiffat15, rc.csdiffat15, evg))
        Rr = np.array(rows); real_g, real_cs, evg = Rr[:, 0], Rr[:, 1], Rr[:, 2]
        # simulated CS edge: same spread as the actions-only CS contest, centred where the real CS edge's mean is (the contest's centre comes from the lane model)
        sim_cs = real_cs.mean() + sd_cs * rng.standard_normal((len(Rr), 2000))
        sim_g = sim_cs * GPC + evg[:, None]
        out[r] = {"lanes": len(Rr), "gold not from CS: real sd": round(float(np.std(real_g - GPC * real_cs))), "... rule events sd": round(float(np.std(evg))),
                  "... correlation": round(float(np.corrcoef(real_g - GPC * real_cs, evg)[0, 1]), 3),
                  "gold edge at 15: real sd": round(float(np.std(real_g))), "gold edge at 15: actions-only sd": round(float(np.std(sim_g))),
                  "real inside the actions-only 80% range": round(float(np.mean([(np.percentile(s, 10) <= x <= np.percentile(s, 90)) for s, x in zip(sim_g, real_g)])), 3)}
    R["2 lane test with rule gold (Worlds)"] = out
    run.result("kills compared", len(KC)); run.save_json(OUT, R); print(json.dumps(R, indent=1))
