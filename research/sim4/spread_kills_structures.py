"""Spread research (14 Nov 2026 AEST, read-only): do kills open the base in real games more than in the sim?
Outside source: Riot's win-probability model (lolesports dev diary, 9 Oct 2023) uses players alive as an input, and the League wiki's
respawn page gives death timers that grow with level (10 s at level 1, 52.5 s at 18, up to +50% late), so a won fight later in the game
leaves the base open for longer. If structures fall mostly while enemies are dead, the sim's towers and endings should follow kills too.
For held-out timeline games from 1 Sep (real) and the same games simulated N times (seeds by game ID, the given calibration):
  per structure kind (T1, T2, T3, inhibitor, nexus tower, nexus): share with 1+ / 2+ / 3+ kills by the taking side in the 30 s and 60 s
  before it, and the mean kills edge (taking side minus other side) in those 60 s
  per game: kills by the winner in the last 2 minutes; share of games whose last 2 minutes have 2+ more winner kills
  after a won fight (2+ kills edge inside 30 s) from 20:00: chance of a structure by the winners within 60 s / 120 s, and of the game ending
  within 120 s, by the number of kills edge
usage (repo root): python -I research/sim4/spread_kills_structures.py params3.json test3_results.json lanes3_features.csv comp3_games.csv
       tl_events.csv tl_match.csv ll_dir <out_json> [n=6] [opts typed,ll,fpl,ekc,fdt]"""
import os, sys, json, zlib, importlib.util
import numpy as np, pandas as pd

PJ, CJ, FE, CO, TE, TM, LLD, OUT = sys.argv[1:9]; N = int(sys.argv[9]) if len(sys.argv) > 9 else 6
OPTS = set(sys.argv[10].split(",")) if len(sys.argv) > 10 else set()
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join("research", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; PD_ = os.path.dirname(PJ); ROLES = ["top", "jng", "mid", "bot", "sup"]
if "typed" in OPTS: P["fight_typed"] = json.load(open(os.path.join(PD_, "fighttypes.json")))
if "ll" in OPTS: P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
if "fpl" in OPTS: P["fight_players"] = json.load(open(os.path.join(PD_, "participants.json")))
if "ekc" in OPTS: P["early_kills"] = json.load(open(os.path.join(PD_, "earlykills.json")))
if "fdt" in OPTS: _fd = json.load(open(os.path.join(PD_, "firstdragon.json"))); P["taker_first_dragon"] = {"side": _fd["taker"], "timing": _fd["taker_timing"]}
if OPTS & {"pks", "pko"}: P["base_push_kills"] = json.load(open(os.path.join(os.path.dirname(PJ), "basepush_kills.json"))); cal["push_kills"] = "on" if "pko" in OPTS else "size"
if "dt" in OPTS: P["death_timer"] = json.load(open(os.path.join(os.path.dirname(PJ), "deathtimer.json"))); cal["death_timers"] = "on"
if "dp" in OPTS: P["dead_push"] = json.load(open(os.path.join(os.path.dirname(PJ), "deadpush_sim.json"))); cal["dead_push"] = "on"
sim = sm.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
tm = pd.read_csv(TM, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[(tm.date >= "2026-09-01") & tm.gameid.isin(fe.gameid)]
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(tm.gid)]
KINDS = ["T1", "T2", "T3", "INHIB", "NEXUSTOWER", "NEXUS"]

def game(kills, structs, length, winner):
    """kills: [(t, side)], structs: [(t, side, kind)], side 0 = blue; returns per-structure rows, per-game row, won-fight rows"""
    kt = np.array([k[0] for k in kills], float); ks = np.array([k[1] for k in kills], int)
    srows = []
    for t, s, kd in structs:
        r = {"kind": kd}
        for w in (30, 60):
            m = (kt <= t) & (kt > t - w); r[f"own{w}"] = int(((ks == s) & m).sum()); r[f"opp{w}"] = int(((ks != s) & m).sum())
        srows.append(r)
    m = kt > length - 120
    grow = {"win_last2": int(((ks == winner) & m).sum()), "lose_last2": int(((ks != winner) & m).sum()), "len": length / 60, "kills": len(kills)}
    # won fights from 20:00: kills grouped by gaps of 20 s+
    frows = []
    if len(kt):
        order = np.argsort(kt); kt, ks = kt[order], ks[order]; start = 0
        for i in range(1, len(kt) + 1):
            if i == len(kt) or kt[i] - kt[i - 1] > 20:
                t0, t1 = kt[start], kt[i - 1]; b = int((ks[start:i] == 0).sum()); rr = (i - start) - b
                if t1 >= 1200 and abs(b - rr) >= 2:
                    w = 0 if b > rr else 1
                    st = [x for x in structs if x[1] == w and t1 < x[0] <= t1 + 120 and x[2] != "NEXUS"]
                    frows.append({"edge": min(abs(b - rr), 4), "s60": int(any(x[0] <= t1 + 60 for x in st)), "s120": int(len(st) > 0),
                                  "end120": int(winner == w and length <= t1 + 120), "end120_loser": int(winner != w and length <= t1 + 120)})
                start = i
    return srows, grow, frows

def summ(S, G, F):
    S, G, F = pd.DataFrame(S), pd.DataFrame(G), pd.DataFrame(F); out = {"structures": {}, "games": {}, "won_fights_from_20": {}}
    for kd in KINDS:
        d = S[S.kind == kd]
        if not len(d): continue
        out["structures"][kd] = {"n": len(d), "own kills 30s: 1+ / 2+ / 3+": [round(float((d.own30 >= k).mean()), 3) for k in (1, 2, 3)],
                                 "own kills 60s: 1+ / 2+ / 3+": [round(float((d.own60 >= k).mean()), 3) for k in (1, 2, 3)],
                                 "kills edge 60s, mean": round(float((d.own60 - d.opp60).mean()), 2)}
    out["games"] = {"winner kills in last 2 min, mean": round(float(G.win_last2.mean()), 2), "share with winner 2+ kills ahead in last 2 min": round(float(((G.win_last2 - G.lose_last2) >= 2).mean()), 3),
                    "share with no kill in last 2 min": round(float(((G.win_last2 + G.lose_last2) == 0).mean()), 3)}
    for e, d in F.groupby("edge"):
        out["won_fights_from_20"][f"edge {e}{'+' if e == 4 else ''}"] = {"n": len(d), "structure within 60s": round(float(d.s60.mean()), 3), "structure within 120s": round(float(d.s120.mean()), 3),
                                                                     "fight winner ends within 120s": round(float(d.end120.mean()), 3)}
    return out

RS, RG, RF = [], [], []
for g in tm.itertuples():
    e = ev[ev.gid == g.gid]; sd = lambda x: 0 if x == "blue" else 1
    kills = [(x.t, sd(x.side)) for x in e[e.type == "kill"].itertuples()]
    st = []
    for x in e[e.type.isin(["tower", "inhib", "nexus"])].itertuples():
        kd = "NEXUS" if x.type == "nexus" else "INHIB" if x.type == "inhib" else "NEXUSTOWER" if "NEXUS" in str(x.detail) else str(x.detail).split()[0]
        st.append((x.t, sd(x.side), kd))
    if not any(k == "NEXUS" for _, _, k in st): st.append((int(g.len), sd(g.win), "NEXUS"))
    a, b, c = game(kills, st, int(g.len), sd(g.win)); RS += a; RG.append(b); RF += c
SS, SG, SF = [], [], []
for g in tm.itertuples():
    d = fe[fe.gameid == g.gameid].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any(): continue
    c = comp.loc[g.gameid] if g.gameid in comp.index else None
    f_ = lambda a: float(c[a + "_blue"] + c[a + "_red"]) if c is not None else 0.0; d_ = lambda a: float(c[a + "_blue"] - c[a + "_red"]) if c is not None else 0.0
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(), "pace_s": f_("pace"), "siege_s": f_("siege"),
         "obj_s": f_("objectives"), "siege_d": d_("siege"), "obj_d": d_("objectives"), "skirm_d": d_("skirmish")}
    if "ll" in OPTS: x["ll_m0"] = m0.loc[g.gameid, [f"m0_{r}" for r in ROLES]].tolist(); x["ll_e0"] = m0.loc[g.gameid, [f"e0_{r}" for r in ROLES]].tolist()
    for j in range(N):
        o = sim.run(x, seed=zlib.crc32(g.gameid.encode()) * 10_000 + 777 + j, log=True); kills, st = [], []
        for s_ in o["steps"]:
            sd = 0 if s_["side"] == "blue" else 1
            if s_["kind"] == "kill": kills.append((s_["t"], sd))
            elif s_["kind"] == "tower": st.append((s_["t"], sd, "NEXUSTOWER" if s_["text"] == "nexus tower" else s_["text"].split()[0]))
            elif s_["kind"] == "inhib": st.append((s_["t"], sd, "INHIB"))
            elif s_["kind"] == "nexus": st.append((s_["t"], sd, "NEXUS"))
        if not any(k == "NEXUS" for _, _, k in st): st.append((o["sec"], 0 if o["winner"] == "blue" else 1, "NEXUS"))
        a, b, c = game(kills, st, o["sec"], 0 if o["winner"] == "blue" else 1); SS += a; SG.append(b); SF += c
R = {"games": {"real": len(RG), "sim": len(SG)}, "opts": sorted(OPTS), "real": summ(RS, RG, RF), "sim": summ(SS, SG, SF)}
json.dump(R, open(OUT, "w"), indent=1)
for part in ("structures", "games", "won_fights_from_20"):
    print("==", part)
    for k in R["real"][part]:
        print("  ", k, "\n     real", json.dumps(R["real"][part][k]), "\n     sim ", json.dumps(R["sim"][part].get(k)))
