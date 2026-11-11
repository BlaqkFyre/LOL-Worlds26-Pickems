"""Sim session 3 (read-only): gather every fitted table the game-state sim reads into one params3.json.
Fitted elsewhere (this script only copies): lanes3_coef.csv + lanes3_resid_cov15.csv (laning), rates3_results.json
(structures, fights, monsters, plates, tower lanes), events3_results.json (who wins kills, fight sizes, objective takers,
gold per event, dragon types, grubs), targets3.json (role kill / death / assist shares).
Added here from the Oracle's Elixir file (major leagues, games before 1 Sep, so held-out games stay out):
  role gold share       each role's share of its team's earned gold (splits the team's gold after laning)
  cs per gold at 15     CS lead at 15 per 1,000 gold lead at 15, per role (box score CS diff)
  damage share          role average and how it moves with the player's share of the team's kills + assists
  vision per minute     role average and spread
usage: python -I s3_params.py <OE csv> <fit_dir> <out_json>"""
import os, sys, json
import numpy as np
import pandas as pd

CSV, D, OUTJ = sys.argv[1:4]
ROLES = ["top", "jng", "mid", "bot", "sup"]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
J = lambda f: json.load(open(os.path.join(D, f)))
co = pd.read_csv(os.path.join(D, "lanes3_coef.csv"))
cov15 = pd.read_csv(os.path.join(D, "lanes3_resid_cov15.csv"), index_col=0).loc[ROLES, ROLES].values.tolist()
cov10 = pd.read_csv(os.path.join(D, "lanes3_resid_cov10.csv"), index_col=0).loc[ROLES, ROLES].values.tolist()
lanes = {r: {str(m): co[(co.role == r) & (co.minute == m)].iloc[0][["intercept", "per_z", "per_skill_sd", "per_champ_gold"]].tolist()
             for m in [10, 15]} for r in ROLES}
R, E, T = J("rates3_results.json"), J("events3_results.json"), J("targets3.json")
cols = ["gameid", "league", "date", "position", "kills", "assists", "teamkills", "earnedgoldshare", "damageshare", "vspm",
        "csdiffat15", "golddiffat15"]
raw = pd.read_csv(CSV, low_memory=False, usecols=cols)
raw = raw[raw.league.isin(MAJOR) & raw.position.isin(ROLES) & (raw.date < "2026-09-01")].copy()
raw["kp_share"] = np.where(raw.teamkills > 0, (raw.kills + raw.assists) / raw.teamkills.clip(lower=1), np.nan)
box = {}
for r in ROLES:
    d = raw[raw.position == r]
    x = d.dropna(subset=["csdiffat15", "golddiffat15"])
    cs = float(np.polyfit(x.golddiffat15 / 1000, x.csdiffat15, 1)[0])
    y = d.dropna(subset=["damageshare", "kp_share"])
    b = np.polyfit(y.kp_share - y.kp_share.mean(), y.damageshare, 1)
    box[r] = {"gold_share": round(float(d.earnedgoldshare.mean()), 4), "cs_per_1k_gold_15": round(cs, 3),
              "dmg_mean": round(float(b[1]), 4), "dmg_per_kp": round(float(b[0]), 4), "kp_mean": round(float(y.kp_share.mean()), 4),
              "dmg_sd_resid": round(float(np.std(y.damageshare - np.polyval(b, y.kp_share - y.kp_share.mean()))), 4),
              "vspm_mean": round(float(d.vspm.mean()), 3), "vspm_sd": round(float(d.vspm.std()), 3)}
P = {"roles": ROLES, "lanes": lanes, "lane_cov15": cov15, "lane_cov10": cov10,
     "segments": R["segments"]["coef"], "base_structures": R["base_structures"]["coef"], "base_push": R["base_push"],
     "segments_timing": R["segments_timing"]["coef"], "segment_push": R.get("segment_push"), "base_push_timing": R["base_push_timing"]["coef"],
     "kill_side_timing": E["kill_side_timing"]["coef"], "kill_side_within": E.get("kill_side_within"), "taker_timing": {k: v["coef"] for k, v in E["taker_timing"].items()}, "fights": R["fights"]["coef"],
     "dispersion": {k: R[k].get("dispersion_by_phase", {}) for k in ["segments", "base_structures", "fights"]}, "monsters": {k: v["coef"] for k, v in R["monsters"].items()},
     "first_tower_lane_share": R["first_tower_lane_share"], "nexus_tier_share": R["nexus_tier_share_when_inhib_down"]["share_nexus_tier"],
     "kill_side": E["kill_side"]["coef"], "fight_size_table": E["fight_size_table"], "two_sided_share_by_size": E["two_sided_share_by_size"],
     "taker": {k: v["coef"] for k, v in E["taker"].items()}, "gold": E["gold_per_event"], "gold_noise_sd": E["gold_noise_sd_per_min"],
     "gold_feedback": E["gold_lead_feedback"], "gold_feedback_within": E.get("gold_lead_feedback_within"), "taker_within": {k: v["coef"] for k, v in E.get("taker_within", {}).items()}, "segment_push_within": R.get("segment_push_within"), "segment_push_lane_tier": R.get("segment_push_lane_tier"), "base_push_within": R.get("base_push_within"),
     "segment_push_fight": R.get("segment_push_fight"), "base_push_fight": R.get("base_push_fight"),
     "segment_push_fight_simple": R.get("segment_push_fight_simple"), "base_push_fight_simple": R.get("base_push_fight_simple"), "gold_swing_share": E["gold_swing_share"], "dragon_types": E["dragon_types"], "grubs_split": E["grubs_split"],
     "role_kill_share": T["before 1 Sep"]["role_kill_share"], "role_death_share": T["before 1 Sep"]["role_death_share"],
     "role_assist_per_team_kill": T["before 1 Sep"]["role_assist_per_team_kill"], "box": box}
json.dump(P, open(OUTJ, "w"), indent=1)
print(json.dumps(box, indent=1))
