"""Damage share at Worlds 2026 (14 Nov 2026 AEST, read-only; Luke: not every ADC should top the damage-share table).
Real: each player's average damage share over the Worlds main-event games in the Oracle's Elixir file (from 1 Oct; 3+ games); roles of the
top 16 and each role's spread of player averages. Sim: the same games played once each by the research sim (seeds by game ID, given
calibration and options); each team-role's average. The sim's damage share = role average + kill-participation effect + noise (P["box"]):
nothing for the player or champion.
usage (repo root): python -I research/sim4/dmgshare_check.py <OE csv> params3.json test3_results.json lanes3_features.csv ll_dir <out_json> [opts]"""
import os, sys, json, zlib, importlib.util
import numpy as np, pandas as pd
CSV, PJ, CJ, FE, LLD, OUT = sys.argv[1:7]; OPTS = set(sys.argv[7].split(",")) if len(sys.argv) > 7 else set()
ROLES = ["top", "jng", "mid", "bot", "sup"]
o = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "playerid", "playername", "teamname", "damageshare", "champion"])
w = o[(o.league == "WLDs") & (o.date >= "2026-10-01") & o.position.isin(ROLES)].dropna(subset=["damageshare"])
pa = w.groupby(["playername", "teamname", "position"]).agg(g=("gameid", "nunique"), dmg=("damageshare", "mean")).reset_index(); pa = pa[pa.g >= 3]
top = pa.sort_values("dmg", ascending=False).head(16)
R = {"real": {"players": len(pa), "top 16 by role": top.position.value_counts().to_dict(), "top 16": [f"{r.playername} ({r.position}) {r.dmg:.3f}" for r in top.itertuples()],
              "sd of player averages by role": pa.groupby("position").dmg.std().round(4).to_dict(), "mean by role": pa.groupby("position").dmg.mean().round(4).to_dict(),
              "sd of single games by role": w.groupby("position").damageshare.std().round(4).to_dict()}}
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join("research", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]; PD_ = os.path.dirname(PJ)
if "typed" in OPTS: P["fight_typed"] = json.load(open(os.path.join(PD_, "fighttypes.json")))
if "ll" in OPTS: P["lane_level"] = json.load(open(os.path.join(LLD, "lanelevel_fit.json"))); m0 = pd.read_csv(os.path.join(LLD, "lanelevel_features.csv")).set_index("gameid")
if "fpl" in OPTS: P["fight_players"] = json.load(open(os.path.join(PD_, "participants.json")))
if "ekc" in OPTS: P["early_kills"] = json.load(open(os.path.join(PD_, "earlykills.json")))
if "fdt" in OPTS: _fd = json.load(open(os.path.join(PD_, "firstdragon.json"))); P["taker_first_dragon"] = {"side": _fd["taker"], "timing": _fd["taker_timing"]}
DSH = None
if "dsh" in OPTS:  # damage share by player and champion, fitted before 1 Sep (research/sim4/s4_dmgshare.py --cutoff 2026-09-01)
    DSH = json.load(open(os.path.join(PD_, "dmgshare_presep.json"))); P["dmg_share"] = {"base": DSH["base"], "resid_sd_by_role": DSH["resid_sd_by_role"]}; cal["dmg_effects"] = "on"
pid_of = w.set_index(["gameid", "side", "position"])[["playerid", "champion"]].to_dict("index")
sim = sm.Sim(P, cal); fe = pd.read_csv(FE); rows = []
team_of = w.groupby(["gameid", "side"]).teamname.first().to_dict()
for g in sorted(w.gameid.unique()):
    d = fe[fe.gameid == g].set_index("position").reindex(ROLES)
    if d.z_v1.isna().any() or ("ll" in OPTS and g not in m0.index): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if "ll" in OPTS: x["ll_m0"] = m0.loc[g, [f"m0_{r}" for r in ROLES]].tolist(); x["ll_e0"] = m0.loc[g, [f"e0_{r}" for r in ROLES]].tolist()
    if DSH is not None:
        x["dmg_eff"] = [[DSH["player"].get(pid_of.get((g, S_, r), {}).get("playerid"), 0.0) + DSH["champion"].get(f'{pid_of.get((g, S_, r), {}).get("champion")}|{r}', 0.0) for r in ROLES] for S_ in ("Blue", "Red")]
    out = sim.run(x, seed=zlib.crc32(g.encode()) * 10_000 + 333)
    for side, S in (("blue", "Blue"), ("red", "Red")):
        for r in ROLES: rows.append((team_of.get((g, S)), r, out["ps"][side][r]["dmgS"]))
S_ = pd.DataFrame(rows, columns=["team", "position", "dmg"]); sa = S_.groupby(["team", "position"]).agg(g=("dmg", "size"), dmg=("dmg", "mean")).reset_index(); sa = sa[sa.g >= 3]
st = sa.sort_values("dmg", ascending=False).head(16)
R["sim"] = {"players": len(sa), "top 16 by role": st.position.value_counts().to_dict(), "sd of player averages by role": sa.groupby("position").dmg.std().round(4).to_dict(),
            "mean by role": sa.groupby("position").dmg.mean().round(4).to_dict(), "sd of single games by role": S_.groupby("position").dmg.std().round(4).to_dict()}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
