"""Sim session 2, step 1 (read-only): v1's pre-game log-odds for every game, the starting point every session 2 part is measured against.
v1 = team pre-game logit (refit day by day on earlier games) + league-adjusted player skills (pre-game estimates), the same base as
exptest.py / compare_app.py. Player weights fitted on Feb-Aug only, so games from 1 Sep are out of sample.
usage: python -I v1_offsets.py <csv> games.csv gfeat.csv out/player_experience_pre2026.csv <out_csv>"""
import contextlib, io, runpy, sys
import numpy as np

OUT = sys.argv[5]
sys.argv = ["exptest.py"] + sys.argv[1:5]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path("exptest.py")
G, tl, D, Y, TR, ok, logit_fit, LP, score = (ns[k] for k in ["G", "tl", "D", "Y", "TR", "ok", "logit_fit", "LP", "score"])
A = np.c_[tl, D]
b = logit_fit(A[TR], Y[TR], np.r_[0.0, np.full(D.shape[1], LP)])
G["z_v1"] = np.where(ok, A @ b, np.nan)
G["p_v1"] = 1 / (1 + np.exp(-G.z_v1))
cols = ["gameid", "date", "league", "patch", "blue", "red", "blue_app", "red_app", "blue_win", "z_v1", "p_v1"]
G[[c for c in cols if c in G.columns]].to_csv(OUT, index=False)
te = np.where(ok & (G.t >= "2026-09-01"))[0]; wo = np.where(ok & (G.league == "WLDs").values)[0]
print("games with v1 odds", int(ok.sum()), "of", len(G))
print("from 1 Sep (log loss, fav, n):", score(G.p_v1.values[te], Y[te]))
print("Worlds:", score(G.p_v1.values[wo], Y[wo]))
