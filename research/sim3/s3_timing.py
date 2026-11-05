"""Sim session 3 (read-only): how flexible real objective timing is, from gol.gg timelines matched to the file.
Descriptive only (nothing fitted), for Luke's realism rules: side, lane priority and jungle choices moving objectives.
  first dragon   when it goes (seconds after the 5:00 spawn): bands; by map side; by who leads bot+jungle at 5:00
  trades         grubs and first dragon to different teams; first dragon and first tower to different teams
  first blood    time; whether the first-blood team takes the next objective
  Baron          when the first Baron goes; share taken within 60 s of a fight the taker won
  Herald         taken or not; by the grubs team or the other
Windows: games before 1 Sep (summer seasons), from 1 Sep (playoffs), Worlds.
usage: python -I s3_timing.py tl_match.csv tl_events.csv tl_gold.csv <out_json>"""
import sys, json
import numpy as np
import pandas as pd

TM, TE, TGo, OUT = sys.argv[1:5]
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
M["win_"] = np.where(M.tournament.str.startswith("Worlds"), "Worlds", np.where(M.date < "2026-09-01", "before 1 Sep", "from 1 Sep"))
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)]
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold")]
go["sv"] = go.value * np.where(go.side == "blue", 1, -1)
R5 = go[go.minute == 5].pivot_table(index="gid", columns="role", values="sv", aggfunc="sum")
first = lambda typ, det=None: ev[(ev.type == typ) & ((ev.detail != "elder") if typ == "dragon" else True)].sort_values("t").groupby("gid").head(1).set_index("gid")
fd, fg, ft, fb, fbl, fh = first("dragon"), first("grub"), first("tower"), first("baron"), first("kill"), first("herald")
G = M.set_index("gid")[["win_"]].copy()
G["fd_t"] = fd.t; G["fd_side"] = fd.side; G["fg_side"] = fg.side; G["ft_side"] = ft.side; G["ft_t"] = ft.t; G["fb_t"] = fb.t; G["fb_side"] = fb.side
G["fbl_t"] = fbl.t; G["fbl_side"] = fbl.side; G["fh_side"] = fh.side
G["prio5"] = (R5.get("bot", 0) + R5.get("sup", 0) + R5.get("jng", 0)).reindex(G.index)
res = {}
for w, d in list(G.groupby("win_")) + [("all", G)]:
    wait = d.fd_t - 300
    o = {"games": len(d),
         "first_dragon_wait_s": {"within 30": round(float((wait < 30).mean()), 3), "30-90": round(float(((wait >= 30) & (wait < 90)).mean()), 3),
                                 "90-180": round(float(((wait >= 90) & (wait < 180)).mean()), 3), "180+": round(float((wait >= 180).mean()), 3),
                                 "median": int(wait.median())},
         "first_dragon_blue_share": round(float((d.fd_side == "blue").mean()), 3),
         "first_tower_s": {"median": int(d.ft_t.median()), "p10": int(d.ft_t.quantile(.1)), "p90": int(d.ft_t.quantile(.9))},
         "first_dragon_to_bot_jungle_leader_at_5": round(float(((d.prio5 > 0) == (d.fd_side == "blue"))[d.prio5.abs() > 150].mean()), 3),
         "first_dragon_median_wait_when_leader_takes_s": int((d.fd_t - 300)[((d.prio5 > 0) == (d.fd_side == "blue")) & (d.prio5.abs() > 150)].median()),
         "first_dragon_median_wait_when_other_takes_s": int((d.fd_t - 300)[((d.prio5 > 0) != (d.fd_side == "blue")) & (d.prio5.abs() > 150)].median()),
         "grubs_and_first_dragon_split": round(float((d.fg_side != d.fd_side)[d.fg_side.notna() & d.fd_side.notna()].mean()), 3),
         "first_dragon_and_first_tower_split": round(float((d.ft_side != d.fd_side)[d.ft_side.notna() & d.fd_side.notna()].mean()), 3),
         "herald_taken": round(float(d.fh_side.notna().mean()), 3),
         "herald_to_grubs_team": round(float((d.fh_side == d.fg_side)[d.fh_side.notna() & d.fg_side.notna()].mean()), 3),
         "first_blood_s": {"median": int(d.fbl_t.median()), "p10": int(d.fbl_t.quantile(.1)), "p90": int(d.fbl_t.quantile(.9))},
         "first_blood_team_takes_first_dragon": round(float((d.fbl_side == d.fd_side)[d.fd_side.notna()].mean()), 3),
         "first_baron_s": {"median": int(d.fb_t.median()), "p10": int(d.fb_t.quantile(.1)), "p90": int(d.fb_t.quantile(.9)),
                           "games_with_baron": round(float(d.fb_t.notna().mean()), 3)}}
    res[w] = o
# Barons right after a won fight: taker had more kills in the 60 s before
B = ev[ev.type == "baron"]; K = ev[ev.type == "kill"]
after = []
for r in B.itertuples():
    k = K[(K.gid == r.gid) & (K.t <= r.t) & (K.t > r.t - 60)]
    after.append((k.side == r.side).sum() - (k.side != r.side).sum())
after = np.array(after)
res["baron_after_fight"] = {"barons": len(after), "taker_won_last_minute_by_2plus": round(float((after >= 2).mean()), 3),
                            "no_kills_last_minute": round(float((after == 0).mean()), 3), "taker_behind_in_last_minute": round(float((after < 0).mean()), 3)}
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
