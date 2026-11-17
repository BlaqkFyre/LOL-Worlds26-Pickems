"""Check a full-game feed pull against the Oracle's Elixir file (17 Nov 2026 AEST).
Each feed game is matched to the file by both sides' champions, then its final team counts (kills, towers, inhibitors, Barons, dragons)
and length are compared. Feed seconds are wall-clock seconds from the game's first gold, so pauses make a feed game longer than the
file's game length; the largest gap between frames shows where a pause was.
usage (repo root): python -I research/laning/feed_check.py [feed dir = research/local/feed_full]"""
import sys, json, glob, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import data, config
import pandas as pd
D = Path(sys.argv[1]) if len(sys.argv) > 1 else config.R / "local" / "feed_full"
o = data.oe(["gameid", "league", "date", "side", "position", "champion", "teamkills", "towers", "inhibitors", "barons", "dragons", "gamelength"])
print("file check", data.check(o)); o = o[o.league == "WLDs"]
ALIAS = {"renata": "renataglasc", "monkeyking": "wukong"}  # feed champion ids that differ from the file's names
k = lambda c: (lambda s: ALIAS.get(s, s))("".join(ch for ch in str(c).lower() if ch.isalnum()))
p, t = o[o.position != "team"], o[o.position == "team"].set_index(["gameid", "side"])
idx = {}
for g, grp in p.groupby("gameid"): idx[tuple(frozenset(map(k, grp[grp.side == s].champion)) for s in ("Blue", "Red"))] = g
rows, miss = [], []
for f in sorted(glob.glob(str(D / "1*.json"))):
    j = json.load(open(f)); m = j["meta"]; gid = os.path.basename(f)[:-5]
    key = tuple(frozenset(k(x["championId"]) for x in m[s]["participantMetadata"]) for s in ("blueTeamMetadata", "redTeamMetadata"))
    g = idx.get(key)
    if g is None: miss.append(gid); continue
    B, R = t.loc[(g, "Blue")], t.loc[(g, "Red")]; (lb, lr) = j["team"][-1][1]; secs = [x[0] for x in j["team"]]
    feed = [lb[4], lr[4], lb[1], lr[1], lb[2], lr[2], lb[3], lr[3], lb[5], lr[5]]
    oe_ = [int(x) for x in (B.teamkills, R.teamkills, B.towers, R.towers, B.inhibitors, R.inhibitors, B.barons, R.barons, B.dragons, R.dragons)]
    rows.append(dict(game=gid, oe=g, finished=j["finished"], gap=max(b - a for a, b in zip(secs, secs[1:])), dlen=secs[-1] - int(B.gamelength),
                     diff=[a - b for a, b in zip(feed, oe_)]))
r = pd.DataFrame(rows)
print(f"feed games {len(r) + len(miss)}, matched {len(r)}, not matched {miss}; file Worlds games without a feed game {o.gameid.nunique() - len(r)}")
ex = r[r["diff"].map(any)]
print(f"exact on all 10 counts: {len(r) - len(ex)}; feed 'finished' flag set: {int(r.finished.sum())}")
for _, x in ex.iterrows(): print("  off:", x.game, x.oe, "feed - file [kills B R, towers B R, inhib B R, barons B R, dragons B R]", x["diff"])
print(f"length, last feed second - file length (s): median {r.dlen.median():.0f}, min {r.dlen.min()}, max {r.dlen.max()}")
for _, x in r[r.dlen.abs() > 30].iterrows(): print(f"  {x.game} {x.oe}: {x.dlen:+d} s, largest frame gap {x.gap} s")
