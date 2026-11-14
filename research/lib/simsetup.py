"""Load the research sim the way the tests do (14 Nov 2026), so laning checks and replay checks share one setup.
  sim_module(path)   import a copy of research/sim3/s3_sim.py (or an older backup) as its own module
  params(opts)       P for the options, as research/sim3/s3_test.py builds it (typed, ll, fdt, fpl, dt, ...) from the session 4 params folder
  cal_default()      the calibration of the default sim with death timers (research/local/sim4/spread/w_dt/test3_results.json: gain 1.604)
  inputs()           per-game x for every game with lane features: z, skill_gap, cg15, ll_m0, ll_e0 (as research/sim4/deathtimer_check.py)
  seed(gameid, j)    seeds by game ID (Luke, 12 Nov)"""
import importlib.util, json, zlib
import pandas as pd
from . import config
PD = config.R / "local" / "sim4" / "spread" / "params"; LLD = config.R / "local" / "sim3" / "ll_fit2"
CAL = config.R / "local" / "sim4" / "spread" / "w_dt" / "test3_results.json"

def sim_module(path=config.R / "sim3" / "s3_sim.py", name="s3_sim"):
    spec = importlib.util.spec_from_file_location(name, str(path)); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def params(opts):
    P = json.load(open(PD / "params3.json"))
    if "typed" in opts: P["fight_typed"] = json.load(open(PD / "fighttypes.json"))
    if "ll" in opts: P["lane_level"] = json.load(open(LLD / "lanelevel_fit.json"))
    if "fdt" in opts: fd = json.load(open(PD / "firstdragon.json")); P["taker_first_dragon"] = {"side": fd["taker"], "timing": fd["taker_timing"]}
    if "fpl" in opts: P["fight_players"] = json.load(open(PD / "participants.json"))
    if "dt" in opts or "la" in opts: P["death_timer"] = json.load(open(PD / "deathtimer.json"))
    return P

def cal_default(): return dict(json.load(open(CAL))["cal"])

def inputs():
    fe = pd.read_csv(config.LANE_FEATURES); m0 = pd.read_csv(LLD / "lanelevel_features.csv").set_index("gameid"); out = {}
    for g, d in fe.groupby("gameid"):
        d = d.set_index("position").reindex(config.ROLES)
        if d.z_v1.isna().any(): continue
        x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
        if g in m0.index: x["ll_m0"] = m0.loc[g, [f"m0_{r}" for r in config.ROLES]].tolist(); x["ll_e0"] = m0.loc[g, [f"e0_{r}" for r in config.ROLES]].tolist()
        out[g] = x
    return out

def seed(gameid, j, base=0): return zlib.crc32(gameid.encode()) * 10_000 + base + j
