"""One place for every data path, date and expected size the research scripts use (14 Nov 2026; Luke: make the research system secure,
accurate, maintainable and scalable). Scripts import from here; nothing else should type a path or a split date.
Paths are relative to the repo root; scripts run from the repo root (python -I research/<folder>/<script>.py)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "research"

# data sources (the current copy of each; see STALE for copies that must not be read)
OE_CSV = R / "2026_LoL_esports_match_data_from_OraclesElixir.csv"   # Oracle's Elixir, full file to 10 Nov UTC
TL_MATCH = R / "model" / "sim3" / "tl_match.csv"                     # gol.gg timelines matched to the file (640 games, 12 Nov)
TL_EVENTS = R / "local" / "sim3" / "tl_events.csv"                   # parsed gol.gg timeline events
TL_GOLD = R / "local" / "sim3" / "tl_gold.csv"                       # gold and CS per role per minute
LANE_FEATURES = R / "local" / "sim3" / "out_11nov" / "lanes3_features.csv"  # the current sim's lane inputs (skill gap, champion gold, v1)
FEED_DIR = R / "local" / "feed"                                      # lolesports live stats frames (one JSON per esports game)
STALE = {R / "local" / "sim3" / "out" / "tl_match.csv": "older timeline match (626 games); use config.TL_MATCH"}

# where results go
RUNS_DIR = R / "runs"                    # one JSON record per script run + index.csv (committed: small)
CACHE_DIR = R / "local" / "cache"        # reusable intermediate tables (git-ignored), keyed by input fingerprints
MODEL_DIR = R / "model"

# leagues, roles, dates
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]
WORLDS_FROM = "2026-10-01"     # the file's "WLDs" rows before this are a regional qualifier, not Worlds (CLAUDE.md)
TUNE_FROM, SPLIT = "2026-08-01", "2026-09-01"   # settings are chosen fitting before TUNE_FROM, judging TUNE_FROM..SPLIT; tests from SPLIT
WORLDS_PATCH = "16.20"

# sizes the data must have; data.check() stops a script when one is off
EXPECT = {"worlds_games": 94, "major_games": 2869, "timeline_matched": 640, "worlds_timelines": 94}
