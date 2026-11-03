"""Step 5: new model v the current app on the same games. The app only rates the 16 Worlds teams, so the only shared games are
the 51 Worlds Swiss games. App odds = what the app said before each match day's data was added (recorded in
research/worlds-live-2026.md: per game for 28 games from 26 Oct; only the combined log loss 0.697 for the first 23 games).
New model = team ratings + league-adjusted player skills (base of exptest.py), refitted day by day, no draft information."""
import runpy, sys
import numpy as np
import pandas as pd

sys.argv = ["exptest.py", sys.argv[1], "games.csv", "gfeat.csv", "out/player_experience_pre2026.csv"]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path("exptest.py")
G, tl, D, Y, TR, logit_fit, LP = ns["G"], ns["tl"], ns["D"], ns["Y"], ns["TR"], ns["logit_fit"], ns["LP"]
A = np.c_[tl, D]; b = logit_fit(A[TR], Y[TR], np.r_[0.0, np.full(D.shape[1], LP)])
G["p_blue"] = 1 / (1 + np.exp(-(A @ b)))
S = G[(G.league == "WLDs") & (G.date >= "2026-10-22")].copy()
S["p_winner"] = np.where(S.blue_win == 1, S.p_blue, 1 - S.p_blue)
S["blue_app"], S["red_app"] = S.blue_app.fillna(""), S.red_app.fillna("")
# app odds for the winner, in order of play within each recorded batch (research/worlds-live-2026.md)
APP = {"2026-10-26": [("T1", "CFO", .81), ("BLG", "KC", .88), ("LOS", "TSW", .45), ("LOS", "TSW", .45), ("TL", "AL", .31), ("TL", "AL", .39)],
       "2026-10-28": [("T1", "MKOI", .75), ("T1", "MKOI", .85), ("IG", "LYON", .49), ("LYON", "IG", .51), ("IG", "LYON", .49)],
       "2026-10-29": [("KC", "CFO", .52), ("KC", "CFO", .78), ("BLG", "TES", .89), ("TES", "BLG", .10), ("TES", "BLG", .24)],
       "2026-10-30": [("LOS", "TL", .59), ("TL", "LOS", .80), ("LOS", "TL", .28), ("HLE", "G2", .65), ("HLE", "G2", .66)],
       "2026-10-31": [("KC", "MKOI", .89), ("KC", "MKOI", .62), ("LOS", "LYON", .11), ("LYON", "LOS", .86), ("LYON", "LOS", .71), ("BLG", "HLE", .66), ("BLG", "HLE", .51)]}
S["winner"] = np.where(S.blue_win == 1, S.blue_app, S.red_app); S["loser"] = np.where(S.blue_win == 1, S.red_app, S.blue_app)
S["utc_day"] = S.date.str[:10]
rows = []
used = set()
for day, lst in APP.items():
    for w, l, p in lst:
        cand = S[(S.winner == w) & (S.loser == l) & ~S.index.isin(used)]
        cand = cand[(cand.utc_day >= day) & (cand.utc_day <= (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))]
        assert len(cand) >= 1, (day, w, l)
        i = cand.index[0]; used.add(i); rows.append((i, p))
M = S.loc[[i for i, _ in rows]].copy(); M["p_app"] = [p for _, p in rows]
ll = lambda p: float(-np.mean(np.log(np.clip(p, 1e-6, 1))))
fav = lambda p: float(np.mean(p > 0.5))
first23 = S[~S.index.isin(used)]
print(f"Swiss games {len(S)}; with recorded per-game app odds {len(M)}; first 23 (app only as a total) {len(first23)}")
print(f"28 games from 26 Oct  · app log loss {ll(M.p_app):.3f}, favourite won {fav(M.p_app):.0%} · new model {ll(M.p_winner):.3f}, {fav(M.p_winner):.0%}")
print(f"first 23 games        · app log loss 0.697 (recorded total)              · new model {ll(first23.p_winner):.3f}, {fav(first23.p_winner):.0%}")
tot_app = (23 * 0.697 + len(M) * ll(M.p_app)) / 51
print(f"all 51 Swiss games    · app log loss {tot_app:.3f} (combined)                 · new model {ll(S.p_winner):.3f}, {fav(S.p_winner):.0%}")
print(f"app favourite record overall (recorded): 33 of 51; new model favourite won {int((S.p_winner > .5).sum())} of 51")
print(f"highest odds given: app {max(M.p_app.max(), 1 - M.p_app.min()):.0%} · new model {max(S.p_blue.max(), 1 - S.p_blue.min()):.0%}")
M["day"] = M.date.str[:10]
print(M[["day", "blue_app", "red_app", "winner", "p_app", "p_winner"]].round(2).to_string(index=False))
