"""Read-only: where is Fearless draft in use? For each league/event, in multi-game series, how often a team re-picks a champion it
already played earlier in the same series (Fearless forbids this, so ~0% = Fearless). Series = same day, same two teams.
usage: python -I s2_fearless_check.py <OE csv>"""
import sys
import pandas as pd
df = pd.read_csv(sys.argv[1], low_memory=False, usecols=["gameid", "league", "date", "game", "playoffs", "side", "position", "teamid", "champion"])
df = df[df.teamid.notna() & (df.position != "team") & ~((df.league == "WLDs") & (df.date < "2026-10-01"))].copy(); df["day"] = df.date.str[:10]
tm = df.groupby("gameid").agg(day=("day", "first"), league=("league", "first"), teams=("teamid", lambda s: tuple(sorted(set(s)))))
tm["series"] = tm.day + "|" + tm.teams.astype(str); tm["n"] = tm.groupby("series").day.transform("size")
df = df.join(tm[["series", "n"]], on="gameid")
multi = df[df.n >= 2].sort_values(["series", "date"])
seen, rep, tot = {}, {}, {}
for (s, team), g in multi.groupby(["series", "teamid"]):
    lg = g.league.iloc[0]; earlier = set()
    for gid, gg in g.groupby("gameid", sort=False):
        champs = set(gg.champion)
        if earlier:
            rep[lg] = rep.get(lg, 0) + len(champs & earlier); tot[lg] = tot.get(lg, 0) + len(champs)
        earlier |= champs
out = pd.DataFrame({"picks_in_later_games": tot, "repeats": rep}).fillna(0)
out["repeat_rate"] = (out.repeats / out.picks_in_later_games).round(4)
print(out.sort_values("picks_in_later_games", ascending=False).head(25).to_string())
