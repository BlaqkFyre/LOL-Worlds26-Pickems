"""Spread of game length and kills, sim v real (12 Nov, read-only): where do the sim's quiet short games and bloody long games come from?
Held-out games from 1 Sep that have a timeline; the sim plays each N times (seeds by game ID) with the calibration of a finished test run.
Printed and saved, real v sim:
  when things happen   quantiles (2, 10, 25, 50, 75, 90, 98%) of the first T2, first T3, first inhibitor and the end; inhibitor -> end
  kills by stage       kills per minute played in 5-minute windows, and total kills before the first inhibitor
  state at 20 and 25   gold lead (absolute), towers taken by the leader, kills so far
  by game length       share of games, kills, kills per minute, gold lead at 20:00, towers at 20:00 for games under 24, 24-28, ... 45+
usage: python -I s3_spreadcheck.py params3.json test3_results.json(cal) lanes3_features.csv comp3_games.csv tl_events.csv tl_gold.csv tl_match.csv <out_json> [n=4] [opts: ll,typed,pf,ends,fpl,ekc,fdt] [ll_dir]"""
import os, sys, json, zlib, importlib.util
import numpy as np
import pandas as pd

PJ, CJ, FE, CO, TE, TGO, TM, OUT = sys.argv[1:9]; N = int(sys.argv[9]) if len(sys.argv) > 9 else 4
OPTS = set(sys.argv[10].split(",")) if len(sys.argv) > 10 else set(); LLD = sys.argv[11] if len(sys.argv) > 11 else os.path.dirname(PJ)
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; ROLES = ["top", "jng", "mid", "bot", "sup"]
if "typed" in OPTS: P["fight_typed"] = json.load(open(os.path.join(os.path.dirname(PJ), "fighttypes.json")))
if "ll" in OPTS: P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
if "sp" in OPTS: cal["seg_phase"] = "own"
if "ends" in OPTS: cal["endings"] = "on"
# session 4 options (13 Nov): the app's default sim; their switches come with the calibration file's cal
PD_ = os.path.dirname(PJ)
if "fpl" in OPTS: P["fight_players"] = json.load(open(os.path.join(PD_, "participants.json")))
if OPTS & {"ekc", "ek"}: P["early_kills"] = json.load(open(os.path.join(PD_, "earlykills.json")))
if "fdt" in OPTS: _fd = json.load(open(os.path.join(PD_, "firstdragon.json"))); P["taker_first_dragon"] = {"side": _fd["taker"], "timing": _fd["taker_timing"]}
if OPTS & {"pks", "pko"}: P["base_push_kills"] = json.load(open(os.path.join(os.path.dirname(PJ), "basepush_kills.json"))); cal["push_kills"] = "on" if "pko" in OPTS else "size"
if "dt" in OPTS: P["death_timer"] = json.load(open(os.path.join(os.path.dirname(PJ), "deathtimer.json"))); cal["death_timers"] = "on"
if "dp" in OPTS: P["dead_push"] = json.load(open(os.path.join(os.path.dirname(PJ), "deadpush_sim.json"))); cal["dead_push"] = "on"
sim = sm.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
tm = pd.read_csv(TM, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[(tm.date >= "2026-09-01") & tm.gameid.isin(fe.gameid)]
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(tm.gid)]
go = pd.read_csv(TGO, dtype={"gid": str}); go = go[go.gid.isin(tm.gid) & (go.kind == "gold")]
Q = [.02, .1, .25, .5, .75, .9, .98]

def game_row(kills_t, struct, length, lead_at, wside):
    """kills_t: kill times; struct: list of (t, side, label) with labels T1/T2/T3/INHIB/NEXUSTOWER; lead_at: {minute: blue gold lead}."""
    f = lambda lab: min([t for t, s, l in struct if l == lab], default=np.nan)
    r = {"len": length / 60, "kills": len(kills_t), "t2": f("T2") / 60, "t3": f("T3") / 60, "inh": f("INHIB") / 60}
    r["inh_to_end"] = r["len"] - r["inh"]; r["kills_pre_inh"] = sum(1 for t in kills_t if t < (f("INHIB") if f("INHIB") == f("INHIB") else length))
    for a in range(0, 45, 5): r[f"k{a}"] = sum(1 for t in kills_t if a * 60 <= t < (a + 5) * 60); r[f"min{a}"] = max(0.0, min(length, (a + 5) * 60) - a * 60) / 60
    for mm in (20, 25):
        if length >= mm * 60:
            ld = lead_at.get(mm, np.nan); s = 0 if ld >= 0 else 1
            r[f"lead{mm}"] = abs(ld); r[f"tw{mm}"] = sum(1 for t, sd, l in struct if t < mm * 60 and l in ("T1", "T2", "T3") and sd == s)
            r[f"kills{mm}"] = sum(1 for t in kills_t if t < mm * 60)
    return r

real = []
gsum = go.groupby(["gid", "minute", "side"]).value.sum().unstack("side")
for g in tm.itertuples():
    e = ev[ev.gid == g.gid]; st = []
    for x in e[e.type.isin(["tower", "inhib"])].itertuples():
        lab = "INHIB" if x.type == "inhib" else ("NEXUSTOWER" if "NEXUS" in str(x.detail) else str(x.detail).split()[0])
        st.append((x.t, 0 if x.side == "blue" else 1, lab))
    la = {mm: float(gsum.loc[(g.gid, mm), "blue"] - gsum.loc[(g.gid, mm), "red"]) for mm in (20, 25) if (g.gid, mm) in gsum.index}
    real.append(game_row(e[e.type == "kill"].t.tolist(), st, int(g.len), la, g.win))
simr = []
for g in tm.itertuples():
    d = fe[fe.gameid == g.gameid].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any(): continue
    c = comp.loc[g.gameid] if g.gameid in comp.index else None
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
         "pace_s": float(c.pace_blue + c.pace_red) if c is not None else 0.0, "siege_s": float(c.siege_blue + c.siege_red) if c is not None else 0.0,
         "obj_s": float(c.objectives_blue + c.objectives_red) if c is not None else 0.0,
         "siege_d": float(c.siege_blue - c.siege_red) if c is not None else 0.0, "obj_d": float(c.objectives_blue - c.objectives_red) if c is not None else 0.0,
         "skirm_d": float(c.skirmish_blue - c.skirmish_red) if c is not None else 0.0}
    if "ll" in OPTS: x["ll_m0"] = m0.loc[g.gameid, [f"m0_{r}" for r in ROLES]].tolist(); x["ll_e0"] = m0.loc[g.gameid, [f"e0_{r}" for r in ROLES]].tolist()
    for j in range(N):
        o = sim.run(x, seed=zlib.crc32(g.gameid.encode()) * 10_000 + 777 + j, log=True); st = []; kt = []
        for s_ in o["steps"]:
            sd = 0 if s_["side"] == "blue" else 1
            if s_["kind"] == "kill": kt.append(s_["t"])
            elif s_["kind"] == "tower": st.append((s_["t"], sd, "NEXUSTOWER" if s_["text"] == "nexus tower" else s_["text"].split()[0]))
            elif s_["kind"] == "inhib": st.append((s_["t"], sd, "INHIB"))
        simr.append(game_row(kt, st, o["sec"], {mm: o["gd"].get(mm, o["gd"].get(str(mm), np.nan)) for mm in (20, 25)}, o["winner"]))
R, S = pd.DataFrame(real), pd.DataFrame(simr)
res = {"games": {"real": len(R), "sim": len(S)}, "cal": cal, "opts": sorted(OPTS), "when": {}, "kills_per_min_by_window": {}, "state": {}, "by_length": {}}
for c in ["t2", "t3", "inh", "len", "inh_to_end", "kills", "kills_pre_inh"]:
    res["when"][c] = {"real": R[c].quantile(Q).round(1).tolist(), "sim": S[c].quantile(Q).round(1).tolist(), "real_sd": round(float(R[c].std()), 2), "sim_sd": round(float(S[c].std()), 2)}
for a in range(0, 45, 5):
    res["kills_per_min_by_window"][f"{a}-{a + 5}"] = {"real": round(float(R[f"k{a}"].sum() / max(1e-9, R[f"min{a}"].sum())), 3), "sim": round(float(S[f"k{a}"].sum() / max(1e-9, S[f"min{a}"].sum())), 3),
                                                      "games_reaching_real": round(float((R.len > a).mean()), 3), "games_reaching_sim": round(float((S.len > a).mean()), 3)}
for mm in (20, 25):
    for c in (f"lead{mm}", f"tw{mm}", f"kills{mm}"):
        res["state"][c] = {"real": [round(float(R[c].mean()), 2), round(float(R[c].std()), 2)], "sim": [round(float(S[c].mean()), 2), round(float(S[c].std()), 2)], "real_q": R[c].quantile([.1, .5, .9]).round(1).tolist(), "sim_q": S[c].quantile([.1, .5, .9]).round(1).tolist()}
bins = [0, 24, 28, 33, 38, 45, 99]
for nm, D in (("real", R), ("sim", S)):
    t = D.groupby(pd.cut(D.len, bins), observed=True).apply(lambda d: {"share": round(len(d) / len(D), 3), "kills": round(float(d.kills.mean()), 1), "kills_per_min": round(float((d.kills / d.len).mean()), 2),
                                                                      "lead20": round(float(d.lead20.mean())), "towers20": round(float(d.tw20.mean()), 2), "kills20": round(float(d.kills20.mean()), 1), "inh": round(float(d.inh.mean()), 1)})
    res["by_length"][nm] = {str(k): v for k, v in t.items()}
res["links"] = {nm: {"len_kills": round(float(D.len.corr(D.kills)), 3), "lead20_len": round(float(D.lead20.corr(D.len)), 3), "kills20_len": round(float(D.kills20.corr(D.len)), 3), "lead20_kills20": round(float(D.lead20.corr(D.kills20)), 3)} for nm, D in (("real", R), ("sim", S))}
json.dump(res, open(OUT, "w"), indent=1)
for k, v in res.items():
    if isinstance(v, dict) and k not in ("cal",):
        print("==", k)
        for a, b in v.items(): print("  ", a, json.dumps(b))
