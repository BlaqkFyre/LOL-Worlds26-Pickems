"""Death timers for the sim (14 Nov 2026 AEST). Writes the table the sim reads (cal["death_timers"] = "on"):
  base wait by level and the time factor: League wiki, Respawn page (read 14 Nov 2026); levels 1-9 also in Riot's patch 14.16 notes
  (13 Aug 2024: 10/10/12/12/14/16/20/25/28 s); XP to reach each level: League wiki, Experience page (read 14 Nov 2026)
  each role's XP curve: average XP at 10, 15, 20 and 25 minutes in major-league games before the cutoff (Oracle's Elixir file); after 25:00
  the role's own 20-25 rate, capped at level 18 (an assumption: the file has no XP after 25:00)
Checked on real games (research/sim4/deathtimer_check.py): no real player died again inside the timer (0 of 3,849).
usage (repo root): python -I research/sim4/s4_deathtimer.py <OE csv> <out json> [--cutoff 2026-09-01]"""
import sys, json
import pandas as pd
CSV, OUT = sys.argv[1:3]; CUT = sys.argv[sys.argv.index("--cutoff") + 1] if "--cutoff" in sys.argv else "2026-09-01"
ROLES = ["top", "jng", "mid", "bot", "sup"]; MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
o = pd.read_csv(CSV, low_memory=False, usecols=["league", "date", "position", "xpat10", "xpat15", "xpat20", "xpat25"])
o = o[o.league.isin(MAJOR) & o.position.isin(ROLES) & (o.date < CUT)].dropna()
T = {"source": "League wiki Respawn + Experience pages (14 Nov 2026); Riot patch 14.16 notes; role XP from the Oracle's Elixir file", "cutoff": CUT,
     "base_wait": [10, 10, 12, 12, 14, 16, 20, 25, 28, 32.5, 35, 37.5, 40, 42.5, 45, 47.5, 50, 52.5],
     "time_factor": {"start_s": 900, "step_s": 30, "per_step": [[1800, 0.00425], [2700, 0.0030], [3300, 0.0145]], "cap": 0.5},
     "xp_levels": [0, 280, 660, 1140, 1720, 2400, 3180, 4060, 5040, 6120, 7300, 8580, 9960, 11440, 13020, 14700, 16480, 18360],
     "role_xp": {r: [round(float(x), 1) for x in o[o.position == r][["xpat10", "xpat15", "xpat20", "xpat25"]].mean()] for r in ROLES},
     "player_games": int(len(o))}
json.dump(T, open(OUT, "w"), indent=1); print(json.dumps(T["role_xp"]), T["player_games"])
