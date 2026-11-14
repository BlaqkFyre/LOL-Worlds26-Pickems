"""Pull the first minutes of each game from the lolesports live stats feed (14 Nov 2026 AEST; Luke OK'd pulling the 94 Worlds games).
Feed: https://feed.lolesports.com/livestats/v1/window/<esports game id>?startingTime=<RFC 3339> (no key needed; unofficial, documented
by the community at https://vickz84259.github.io/lolesports-api-docs/). Each request returns about 10 s of frames; one frame per second is
kept. Per player per second: total gold, level, kills, deaths, assists, CS, current and max health. No map positions in this feed.
Game list (esports game ids) from the lolesports schedule API: research/local/feed/worlds_games.csv.
Output, one file per game: research/local/feed/<esports game id>.json = {"meta": participant metadata, "start": first frame time,
"frames": [[second, [10 x [gold, level, k, d, a, cs, hp, maxhp]]], ...]}. Finished games are skipped, so a re-run resumes.
Three games at a time.
usage (repo root): python -I research/laning/feed_pull.py <games csv> <out dir> [minutes=15] [pause_s=0.4]"""
import sys, os, csv, json, time, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
GAMES, OUT = sys.argv[1:3]; MIN = int(sys.argv[3]) if len(sys.argv) > 3 else 15; PAUSE = float(sys.argv[4]) if len(sys.argv) > 4 else 0.4
UA = {"User-Agent": "Mozilla/5.0"}; BASE = "https://feed.lolesports.com/livestats/v1/window/"
def get(url):
    for k in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read() or b"{}")
        except Exception as e: print("  retry", url[-40:], e, flush=True); time.sleep(5 * (k + 1))
    return {}
P = lambda f: sorted(f["blueTeam"]["participants"] + f["redTeam"]["participants"], key=lambda p: p["participantId"])
rows = list(csv.DictReader(open(GAMES)))
def one(item):
    n, r = item
    g = r["esports_game"]; path = os.path.join(OUT, g + ".json")
    if os.path.exists(path): return
    w = get(BASE + g)
    if not w.get("frames"): print(n, g, "no frames", flush=True); return
    t_first = dt.datetime.strptime(w["frames"][0]["rfc460Timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
    # game start: first frame where any player has gold (frames before are the pre-game)
    start, frames, seen, probe = None, [], set(), t_first.replace(second=t_first.second - t_first.second % 10)
    end = None
    while True:
        ts = probe.strftime("%Y-%m-%dT%H:%M:%SZ"); d = get(BASE + g + "?startingTime=" + ts); F = d.get("frames", [])
        for f in F:
            s = f["rfc460Timestamp"][:19]
            if s in seen: continue
            seen.add(s); pp = P(f); t = dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
            if start is None and any(p["totalGold"] > 0 for p in pp): start = t
            # 14 Nov fix: in a few games a stray early frame set the start, then the feed went quiet for minutes. A gap over 20 s in
            # the first 400 s means the real game starts after it: restart from that frame.
            if start is not None and frames and (t - start).total_seconds() < 400 and (t - start).total_seconds() - frames[-1][0] > 20:
                start, frames = t, []
            if start is not None:
                sec = int((t - start).total_seconds())
                frames.append([sec, [[p["totalGold"], p["level"], p["kills"], p["deaths"], p["assists"], p["creepScore"], p["currentHealth"], p["maxHealth"]] for p in pp]])
        probe += dt.timedelta(seconds=10); time.sleep(PAUSE)
        if start is not None and (probe - start).total_seconds() > 60 * MIN: break
        if (probe - t_first).total_seconds() > 60 * (MIN + 20): break  # safety: game never started in the window
    json.dump({"meta": w["gameMetadata"], "start": start.isoformat() if start else None, "frames": frames}, open(path, "w"))
    print(n, g, r["team1"], r["team2"], r["game"], "frames", len(frames), flush=True)
with ThreadPoolExecutor(3) as ex: list(ex.map(one, enumerate(rows)))  # 3 games at a time
print("done")
