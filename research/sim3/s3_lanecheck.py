"""Lane checks, sim v real (12 Nov, read-only): does a sim version's early game look like real lanes?
On held-out games (from 1 Sep; Worlds shown too), for each of one or more s3_test.py runs:
  lead at 15 per role        spread (sd), sim v real
  lanes moving together      correlation of the role leads at 15 (top-bot, jng-mid, bot-sup, top-mid), sim v real
  lane inputs                share of each role's real-style spread explained by the pre-game lane model (R2 of the lead at 15
                             on the fitted lane expectation): in the sim's games v in real games
  kills v gold in a lane     correlation of the role's kills minus deaths by 15 with its gold lead at 15 (needs the kd15
                             columns: runs made from 12 Nov)
  first tower lane           share top / mid / bot (real: gol.gg timelines, matched games in the window)
  first dragon               share taken by the team ahead in bot (bot + sup lead at 15)
usage: python -I s3_lanecheck.py <OE csv> lanes3_features.csv lanelevel_features.csv lanelevel_fit.json tl_match.csv tl_events.csv <out_json> name=run_dir [name=run_dir ...]"""
import os, sys, json
import numpy as np
import pandas as pd

CSV, LF, LLF, LLJ, TMF, TEF, OUT = sys.argv[1:8]; RUNS = dict(a.split("=", 1) for a in sys.argv[8:])
ROLES = ["top", "jng", "mid", "bot", "sup"]; CUT = os.environ.get("S3_CUTOFF", "2026-09-01")
lf = pd.read_csv(LF); fit = json.load(open(LLJ)); m0 = pd.read_csv(LLF).set_index("gameid")
info = lf[lf.position == "top"].set_index("gameid")[["day", "league", "z_v1"]]
real = pd.DataFrame({r: lf[lf.position == r].set_index("gameid").gd15 for r in ROLES})
PRE = "coef_pregame" in fit  # second version of the fits: the expected lead before the game is its own model
exp = pd.DataFrame({r: (m0[f"e0_{r}"] + fit["coef_pregame"][r]["z"] * info.z_v1) if PRE else (m0[f"m0_{r}"] + fit["coef"][r]["z"] * info.z_v1) for r in ROLES})
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "side", "position", "killsat15", "deathsat15", "firstdragon"])
pl = raw[raw.position.isin(ROLES)].copy(); pl["kd"] = pl.killsat15 - pl.deathsat15
kd = pl[pl.side == "Blue"].pivot_table(index="gameid", columns="position", values="kd") - pl[pl.side == "Red"].pivot_table(index="gameid", columns="position", values="kd")
fd = raw[(raw.position == "team") & (raw.side == "Blue")].set_index("gameid").firstdragon
tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); ev = pd.read_csv(TEF, dtype={"gid": str})
tw = ev[(ev.type == "tower") & ~ev.detail.str.contains("NEXUS", na=False)].sort_values("t").groupby("gid").first()
ftl = pd.Series(tw.detail.str.split().str[1].values, index=tw.index.map(tm.set_index("gid").gameid)).dropna()
PAIRS = [("top", "bot"), ("jng", "mid"), ("bot", "sup"), ("top", "mid")]

def table(lead, kdv, fdv, ftlane, e):
    """lead / kdv: frames by role; fdv: 1 = blue took first dragon; ftlane: TOP / MID / BOT; e: expected lead by role (same rows as lead)."""
    o = {"games_or_sims": int(len(lead)), "lead_sd": {r: round(float(lead[r].std())) for r in ROLES}, "team_lead_sd": round(float(lead.sum(axis=1).std())),
         "lead_corr": {f"{a}-{b}": round(float(lead[a].corr(lead[b])), 3) for a, b in PAIRS},
         "r2_on_lane_model": {r: round(float(1 - ((lead[r] - e[r]) ** 2).sum() / ((lead[r] - lead[r].mean()) ** 2).sum()), 3) for r in ROLES}}
    if kdv is not None: o["kd15_corr_with_gold"] = {r: round(float(kdv[r].corr(lead[r])), 3) for r in ROLES}; o["kd15_sd"] = {r: round(float(kdv[r].std()), 2) for r in ROLES}
    if ftlane is not None and len(ftlane): o["first_tower_lane"] = {L: round(float((ftlane == L).mean()), 3) for L in ("TOP", "MID", "BOT")}; o["first_tower_lane_n"] = int(len(ftlane))
    if fdv is not None:
        b2 = lead["bot"] + lead["sup"]; ok = fdv.notna() & (b2 != 0)
        o["first_dragon_to_bot_leader_at_15"] = round(float(((b2 > 0) == (fdv == 1))[ok].mean()), 3)
    return o

res = {}
for nm, d in RUNS.items():
    S = pd.read_csv(os.path.join(d, "sim3_heldout_games.csv.gz"))
    has_kd = "kd15_top" in S.columns
    for win, gids in [("from 1 Sep", [g for g in S.gid.unique()]), ("Worlds", [g for g in S.gid.unique() if info.league.get(g) == "WLDs"])]:
        s = S[S.gid.isin(gids)]
        lead = s[[f"r15_{r}" for r in ROLES]].set_axis(ROLES, axis=1); e = pd.DataFrame({r: s.gid.map(exp[r]).values for r in ROLES}, index=s.index)
        simt = table(lead, s[[f"kd15_{r}" for r in ROLES]].set_axis(ROLES, axis=1) if has_kd else None,
                     s.fd.map({"blue": 1.0, "red": 0.0}), s.ft_lane[s.ft_lane.isin(["TOP", "MID", "BOT"])] if "ft_lane" in s else None, e)
        if "real" not in res.setdefault(win, {}):
            rg = [g for g in gids if g in real.index]
            res[win]["real"] = table(real.loc[rg], kd.reindex(rg)[ROLES], fd.reindex(rg), ftl[ftl.index.isin(rg)], exp.loc[rg])
        res[win][nm] = simt
json.dump(res, open(OUT, "w"), indent=1)
for win, t in res.items():
    print("==", win)
    for nm, o in t.items(): print(f"{nm:14s}", json.dumps(o))
