"""Pull 2026 Player of the Game (per game) and Player of the Match / series MVP (per series) from Leaguepedia's Cargo export.
Per game: MatchScheduleGame.MVP joined to ScoreboardGames (date, sides, winner). Per series: MatchSchedule.MVP.
Plain requests, paged 500 at a time, a short pause between pages.
usage: python -I pog_pull.py <out_dir>"""
import json, os, subprocess, sys, time, urllib.parse

OUT = sys.argv[1]
BASE = "https://lol.fandom.com/wiki/Special:CargoExport"

def pull(params, name):
    rows, off = [], 0
    while True:
        q = dict(params, format="json", limit="500", offset=str(off))
        url = BASE + "?" + urllib.parse.urlencode(q)
        txt = subprocess.run(["curl", "-s", "-L", url], capture_output=True, text=True, encoding="utf-8").stdout
        page = json.loads(txt)
        rows += page
        if len(page) < 500: break
        off += 500; time.sleep(1.5)
    json.dump(rows, open(os.path.join(OUT, name), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(name, len(rows))

pull({"tables": "MatchScheduleGame=MSG,ScoreboardGames=SG", "join_on": "MSG.GameId=SG.GameId",
      "fields": "MSG.OverviewPage=Page,MSG.GameId=GameId,MSG.MatchId=MatchId,MSG.MVP=MVP,SG.DateTime_UTC=Date,SG.Team1=Team1,SG.Team2=Team2,SG.WinTeam=Win,SG.N_GameInMatch=N,SG.Gamelength=Len",
      "where": 'MSG.OverviewPage LIKE "%2026%" AND MSG.MVP IS NOT NULL AND MSG.MVP != ""', "order_by": "SG.DateTime_UTC"}, "pog_games_2026.json")
time.sleep(1.5)
pull({"tables": "MatchSchedule=MS",
      "fields": "MS.OverviewPage=Page,MS.MatchId=MatchId,MS.DateTime_UTC=Date,MS.Team1=Team1,MS.Team2=Team2,MS.Winner=Winner,MS.Team1Score=S1,MS.Team2Score=S2,MS.BestOf=BestOf,MS.MVP=MVP",
      "where": 'MS.OverviewPage LIKE "%2026%" AND MS.MVP IS NOT NULL AND MS.MVP != ""', "order_by": "MS.DateTime_UTC"}, "pog_series_2026.json")
