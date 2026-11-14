"""Death timers and how pushes, base races and monsters follow fights (14 Nov 2026 AEST, read-only), real v the sim.
Death timer (League wiki, Respawn page, read 14 Nov 2026): base wait by level 10/10/12/12/14/16/20/25/28/32.5/35/37.5/40/42.5/45/47.5/50/52.5 s
(levels 1-18), plus a time factor from 15:00: +0.425% every 30 s to 30:00, +0.30% to 45:00, +1.45% to 55:00, capped at +50%.
Level (wiki, Experience page: XP to reach each level): from the Oracle's Elixir file's XP at 10, 15, 20 and 25 minutes for each player,
straight lines between (0:00 = 0 XP), after 25:00 the player's own 20-25 rate, capped at 18,360 XP (level 18). Real deaths are matched to the
file by player name; sim deaths use the average XP curve of the role in real games (the sim has no XP).
Measured, real held-out timeline games from 1 Sep v the sim (seeds by game ID, given calibration):
  1 re-deaths: a player's next death after a death: share inside the estimated timer, and inside timer + 15 s (killed soon after respawn)
  2 base races: base structures (inhibitor towers, inhibitors, nexus towers, nexus) by both teams within 60 s of each other
  3 gaps inside a push: seconds between consecutive structures one team takes less than 30 s apart... and up to 60 s (both shown)
  4 monsters: dragons, souls, Elder and Barons taken within 60 s after a fight (kills 20 s+ apart start a new one), and by the fight winner
usage (repo root): python -I research/sim4/deathtimer_check.py <OE csv> params3.json test3_results.json lanes3_features.csv tl_events.csv
       tl_match.csv ll_dir <out_json> [n=4] [opts typed,ll,fpl,ekc,fdt]"""
import os, sys, json, zlib, importlib.util
import numpy as np, pandas as pd
CSV, PJ, CJ, FE, TE, TM, LLD, OUT = sys.argv[1:9]; N = int(sys.argv[9]) if len(sys.argv) > 9 else 4
OPTS = set(sys.argv[10].split(",")) if len(sys.argv) > 10 else set()
ROLES = ["top", "jng", "mid", "bot", "sup"]
BRW = [10, 10, 12, 12, 14, 16, 20, 25, 28, 32.5, 35, 37.5, 40, 42.5, 45, 47.5, 50, 52.5]
XPL = [0, 280, 660, 1140, 1720, 2400, 3180, 4060, 5040, 6120, 7300, 8580, 9960, 11440, 13020, 14700, 16480, 18360]
def tif(t):
    h = t / 30.0
    v = 0.00425 * min(max(h - 30, 0), 30) + 0.0030 * min(max(h - 60, 0), 30) + 0.0145 * min(max(h - 90, 0), 20)
    return min(v, 0.5)
def level(xp): return int(np.searchsorted(XPL, xp, side="right"))
def xp_at(c, t):  # c = (xp10, xp15, xp20, xp25)
    pts = [(0, 0), (600, c[0]), (900, c[1]), (1200, c[2]), (1500, c[3])]
    if t <= 1500: return float(np.interp(t, [p[0] for p in pts], [p[1] for p in pts]))
    return min(18360.0, c[3] + (c[3] - c[2]) / 300 * (t - 1500))
def timer(c, t): return BRW[min(17, level(xp_at(c, t)) - 1)] * (1 + tif(t))

oe = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "side", "position", "playername", "xpat10", "xpat15", "xpat20", "xpat25"])
oe = oe[oe.position.isin(ROLES)].dropna(subset=["xpat10", "xpat15", "xpat20", "xpat25"])
XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(oe.gameid, oe.playername, oe.xpat10, oe.xpat15, oe.xpat20, oe.xpat25)}
ROLE_XP = {r: tuple(oe[oe.position == r][["xpat10", "xpat15", "xpat20", "xpat25"]].mean()) for r in ROLES}
tm = pd.read_csv(TM, dtype={"gid": str}).dropna(subset=["gameid"]); fe = pd.read_csv(FE); tm = tm[(tm.date >= "2026-09-01") & tm.gameid.isin(fe.gameid)]
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(tm.gid)]

def measure(deaths, structs, monsters, kills):
    """deaths: [(t, key, xp curve)], structs: [(t, side, kind)], monsters: [(t, side, kind)], kills: [(t, side)]"""
    out = {"redeaths": [], "race": 0, "base_minutes": 0, "gaps": [], "mon": []}
    by = {}
    for t, k, c in sorted(deaths, key=lambda x: x[0]): by.setdefault(k, []).append((t, c))
    for k, L in by.items():
        for (t0, c), (t1, _) in zip(L, L[1:]):
            T = timer(c, t0); out["redeaths"].append((t1 - t0, T))
    base = sorted([s for s in structs if s[2] in ("T3", "INHIB", "NEXUSTOWER", "NEXUS")])
    for i, (t, s, k) in enumerate(base):
        out["base_minutes"] += 1; out["race"] += int(any(abs(t2 - t) <= 60 and s2 != s for t2, s2, _ in base))
    for side in (0, 1):
        ts = sorted(t for t, s, k in structs if s == side)
        out["gaps"] += [b - a for a, b in zip(ts, ts[1:]) if b - a <= 60]
    kt = sorted(kills)
    fights = []
    if kt:
        cur = [kt[0]]
        for x in kt[1:]:
            if x[0] - cur[-1][0] > 20: fights.append(cur); cur = [x]
            else: cur.append(x)
        fights.append(cur)
    for t, s, k in monsters:
        before = [f for f in fights if f[-1][0] <= t and f[-1][0] >= t - 60]
        won = any(sum(1 for x in f if x[1] == s) > sum(1 for x in f if x[1] != s) for f in before)
        out["mon"].append((k, int(bool(before)), int(won)))
    return out

def summ(rows):
    rd = [x for r in rows for x in r["redeaths"]]; g = np.array([a for a, _ in rd]); T = np.array([b for _, b in rd])
    mon = pd.DataFrame([m for r in rows for m in r["mon"]], columns=["kind", "fight", "won"])
    gaps = np.array([x for r in rows for x in r["gaps"]])
    return {"deaths followed by another death": len(rd), "next death inside the timer": round(float((g < T).mean()), 4),
            "next death inside timer + 15 s": round(float((g < T + 15).mean()), 4), "median gap / timer": round(float(np.median(g / T)), 2),
            "base structures with an enemy base structure within 60 s": round(sum(r["race"] for r in rows) / max(1, sum(r["base_minutes"] for r in rows)), 3),
            "gaps between a team's structures under 60 s: share 0 s / 1-9 s / 10-29 s / 30-60 s": [round(float(np.mean(f)), 3) for f in (gaps == 0, (gaps >= 1) & (gaps < 10), (gaps >= 10) & (gaps < 30), gaps >= 30)],
            "median gap (s)": float(np.median(gaps)),
            "monsters": {k: {"n": len(d), "fight in the 60 s before": round(float(d.fight.mean()), 3), "taker won a fight in the 60 s before": round(float(d.won.mean()), 3)} for k, d in mon.groupby("kind")}}

real = []; matched = [0, 0]
for g in tm.itertuples():
    e = ev[ev.gid == g.gid]; sd = lambda x: 0 if x == "blue" else 1
    dl = []
    for x in e[e.type == "kill"].itertuples():
        c = XP.get((g.gameid, str(x.victim).lower())); matched[1] += 1
        if c is None: continue
        matched[0] += 1; dl.append((x.t, str(x.victim).lower(), c))
    st = []
    for x in e[e.type.isin(["tower", "inhib", "nexus"])].itertuples():
        st.append((x.t, sd(x.side), "NEXUS" if x.type == "nexus" else "INHIB" if x.type == "inhib" else "NEXUSTOWER" if "NEXUS" in str(x.detail) else str(x.detail).split()[0]))
    mon = [(x.t, sd(x.side), "elder" if x.detail == "elder" else "dragon") for x in e[e.type == "dragon"].itertuples()] + [(x.t, sd(x.side), "baron") for x in e[e.type == "baron"].itertuples()]
    real.append(measure(dl, st, mon, [(x.t, sd(x.side)) for x in e[e.type == "kill"].itertuples()]))

spec = importlib.util.spec_from_file_location("s3_sim", os.path.join("research", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; PD_ = os.path.dirname(PJ)
if "typed" in OPTS: P["fight_typed"] = json.load(open(os.path.join(PD_, "fighttypes.json")))
if "ll" in OPTS: P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
if "fpl" in OPTS: P["fight_players"] = json.load(open(os.path.join(PD_, "participants.json")))
if "ekc" in OPTS: P["early_kills"] = json.load(open(os.path.join(PD_, "earlykills.json")))
if "fdt" in OPTS: _fd = json.load(open(os.path.join(PD_, "firstdragon.json"))); P["taker_first_dragon"] = {"side": _fd["taker"], "timing": _fd["taker_timing"]}
if "dt" in OPTS: P["death_timer"] = json.load(open(os.path.join(os.path.dirname(PJ), "deathtimer.json"))); cal["death_timers"] = "on"
if "dp" in OPTS: P["dead_push"] = json.load(open(os.path.join(os.path.dirname(PJ), "deadpush_sim.json"))); cal["dead_push"] = "on"
sim = sm.Sim(P, cal); simr = []
for g in tm.itertuples():
    d = fe[fe.gameid == g.gameid].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if "ll" in OPTS: x["ll_m0"] = m0.loc[g.gameid, [f"m0_{r}" for r in ROLES]].tolist(); x["ll_e0"] = m0.loc[g.gameid, [f"e0_{r}" for r in ROLES]].tolist()
    for j in range(N):
        o = sim.run(x, seed=zlib.crc32(g.gameid.encode()) * 10_000 + 555 + j, log=True); dl, st, mon, kl = [], [], [], []
        for s_ in o["steps"]:
            sd = 0 if s_["side"] == "blue" else 1
            if s_["kind"] == "kill":
                k_, v_ = s_["text"].replace(" (solo)", "").split(" kills "); dl.append((s_["t"], (1 - sd, v_), ROLE_XP[v_])); kl.append((s_["t"], sd))
            elif s_["kind"] == "tower": st.append((s_["t"], sd, "NEXUSTOWER" if s_["text"] == "nexus tower" else s_["text"].split()[0]))
            elif s_["kind"] == "inhib": st.append((s_["t"], sd, "INHIB"))
            elif s_["kind"] == "nexus": st.append((s_["t"], sd, "NEXUS"))
            elif s_["kind"] in ("dragon", "elder", "baron"): mon.append((s_["t"], sd, s_["kind"]))
        simr.append(measure(dl, st, mon, kl))
R = {"source": "League wiki Respawn and Experience pages (read 14 Nov 2026); Oracle's Elixir XP at 10/15/20/25", "real deaths matched to the file": matched,
     "real": summ(real), "sim": summ(simr), "games": {"real": len(real), "sim": len(simr)}}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
