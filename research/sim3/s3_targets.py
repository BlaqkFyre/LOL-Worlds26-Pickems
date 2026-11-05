"""Sim session 3, step 7 targets (read-only): what real games look like, for judging the game-state sim.
From the Oracle's Elixir file, major leagues, four windows: before 1 Sep (what the sim may be fitted on), 16.15+ patches (the current meta's run-up), from 1 Sep, Worlds.
Per window: game length, total kills, kills per team, towers, dragons, Barons, grubs, heralds, the Baron team's and
first-dragon team's win rate, each role's share of its team's kills, and the spread of the gold lead at 10/15/20/25.
usage: python -I s3_targets.py <OE csv> <out_dir>"""
import os, sys, json
import numpy as np
import pandas as pd

CSV, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]
raw = pd.read_csv(CSV, low_memory=False, dtype={"patch": str})
raw = raw[raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))]
raw["minor"] = raw.patch.str.split(".").str[1].astype(int)
T = raw[raw.position == "team"].copy(); Pl = raw[raw.position.isin(ROLES)].copy()
W = {"before 1 Sep": T.date < "2026-09-01", "16.15+": T.minor >= 15, "from 1 Sep": T.date >= "2026-09-01", "Worlds": T.league == "WLDs"}
q = lambda s: {"mean": round(float(s.mean()), 2), "sd": round(float(s.std()), 2), "p10": round(float(s.quantile(.1)), 2),
               "median": round(float(s.median()), 2), "p90": round(float(s.quantile(.9)), 2)}
res = {}
for nm, msk in W.items():
    t = T[msk]; g = t.groupby("gameid")
    blue = t[t.side == "Blue"].set_index("gameid")
    out = {"games": int(g.ngroups),
           "length_min": q(g.gamelength.first() / 60), "kills_total": q(g.teamkills.sum()),
           "kills_per_team": q(t.teamkills), "towers_total": q(g.towers.sum()), "dragons_total": q(g.dragons.sum()),
           "barons_total": q(g.barons.sum()), "grubs_total": q(g.void_grubs.sum()), "heralds_total": q(g.heralds.sum()),
           "elders_total": q(g.elders.sum()),
           "blue_win": round(float(blue.result.mean()), 3),
           "first_dragon_team_wins": round(float(t[t.firstdragon == 1].result.mean()), 3),
           "first_baron_team_wins": round(float(t[t.firstbaron == 1].result.mean()), 3),
           "first_tower_team_wins": round(float(t[t.firsttower == 1].result.mean()), 3),
           "more_grubs_team_wins": round(float(t[t.void_grubs > t.opp_void_grubs].result.mean()), 3),
           "soul_games": round(float((g.dragons.max() >= 4).mean()), 3)}
    for m in [10, 15, 20, 25]:
        x = blue[f"golddiffat{m}"].dropna(); out[f"gold_lead_{m}"] = q(x.abs())
        out[f"lead_{m}_team_wins"] = round(float(((x > 0) == (blue.loc[x.index].result == 1)).mean()), 3)
    p = Pl[Pl.gameid.isin(t.gameid)]
    share = p.groupby("position").kills.sum() / p.kills.sum()
    out["role_kill_share"] = share.reindex(ROLES).round(4).to_dict()
    out["role_death_share"] = (p.groupby("position").deaths.sum() / p.deaths.sum()).reindex(ROLES).round(4).to_dict()
    out["role_assist_per_team_kill"] = (p.groupby("position").assists.sum() / p.kills.sum()).reindex(ROLES).round(4).to_dict()
    res[nm] = out
json.dump(res, open(os.path.join(OUT, "targets3.json"), "w"), indent=1)
for nm, o in res.items():
    print(nm, o["games"], "len", o["length_min"]["median"], "kills", o["kills_total"]["mean"], "towers", o["towers_total"]["mean"],
          "drag", o["dragons_total"]["mean"], "baron", o["barons_total"]["mean"], "grubs", o["grubs_total"]["mean"],
          "blue", o["blue_win"], "FB", o["first_baron_team_wins"], "FD", o["first_dragon_team_wins"])
    print("   kill share", o["role_kill_share"], "lead15", o["gold_lead_15"]["median"], "lead15 wins", o["lead_15_team_wins"])
