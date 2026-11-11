"""Sim session 3 (read-only): each game's draft style, for the game-state sim's timing.
Same method as session 2's comp profile (research/sim2/s2_comp.py): team stats per game as shares of both teams, minus
what v1's odds predict; each champion-role's style = average over its games, pulled toward 0 (k = 20); a draft = sum of
its five. Here the champion styles come from games BEFORE 1 Sep only, so games from 1 Sep and Worlds stay held out.
Output per game: blue and red draft siege, objectives, skirmish, pace.
usage: python -I s3_comp.py <OE csv> v1_games.csv <out_dir>"""
import os, sys
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]
c = ["gameid", "league", "date", "side", "position", "champion", "result", "gamelength", "kills", "killsat15", "firsttower", "turretplates",
     "opp_turretplates", "towers", "opp_towers", "dragons", "opp_dragons", "void_grubs", "opp_void_grubs", "heralds", "opp_heralds", "barons", "opp_barons"]
raw = pd.read_csv(CSV, low_memory=False, usecols=c)
raw = raw[raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
tm = raw[raw.position == "team"].copy(); pl = raw[raw.position.isin(ROLES)].copy()
k15 = pl.groupby(["gameid", "side"]).killsat15.sum(min_count=5).rename("k15").reset_index()
tm = tm.merge(k15, on=["gameid", "side"], how="left")
opp = tm[["gameid", "side", "k15", "kills"]].copy(); opp["side"] = np.where(opp.side == "Blue", "Red", "Blue")
tm = tm.merge(opp.rename(columns={"k15": "k15_opp", "kills": "kills_opp"}), on=["gameid", "side"], how="left")
share = lambda a, b: np.where((a + b) > 0, a / (a + b), 0.5)
tm["plates"] = share(tm.turretplates, tm.opp_turretplates); tm["towers_s"] = share(tm.towers, tm.opp_towers); tm["ftower"] = tm.firsttower
tm["drag"] = share(tm.dragons, tm.opp_dragons); tm["grubs"] = share(tm.void_grubs, tm.opp_void_grubs)
tm["herald"] = share(tm.heralds, tm.opp_heralds); tm["baron"] = share(tm.barons, tm.opp_barons)
tm["k15s"] = share(tm.k15, tm.k15_opp); tm["pace"] = (tm.kills + tm.kills_opp) / (tm.gamelength / 60)
STATS = ["plates", "towers_s", "ftower", "drag", "grubs", "herald", "baron", "k15s", "pace"]
GROUP = {"siege": ["plates", "towers_s", "ftower"], "objectives": ["drag", "grubs", "herald", "baron"], "skirmish": ["k15s"], "pace": ["pace"]}
pvb = pd.read_csv(V1).set_index("gameid").p_v1
tm["p_side"] = tm.gameid.map(pvb); tm.loc[tm.side == "Red", "p_side"] = 1 - tm.loc[tm.side == "Red", "p_side"]
tm = tm.dropna(subset=["p_side"])
# Walk-forward (11 Nov): S3_CUTOFF = champion styles from games before that date (unset: before 1 Sep, unchanged).
# S3_HALFLIFE (days, optional) = recent games count more: weight 0.5 ** (days before the cutoff / half-life).
CUT = os.environ.get("S3_CUTOFF", "2026-09-01")
HL = float(os.environ["S3_HALFLIFE"]) if os.environ.get("S3_HALFLIFE") else None
wt = lambda d: 0.5 ** ((pd.Timestamp(CUT) - pd.to_datetime(d.day)).dt.days.clip(lower=0) / HL)
for s in STATS:
    x = (tm.p_side - 0.5).abs() if s == "pace" else tm.p_side
    m = (tm.day < CUT) & tm[s].notna()
    b = np.polyfit(x[m], tm.loc[m, s], 1, w=None if HL is None else np.sqrt(wt(tm[m]))); tm[s] = tm[s] - np.polyval(b, x)
pl = pl.merge(tm[["gameid", "side"] + STATS], on=["gameid", "side"], how="inner")
tr = pl[pl.day < CUT].copy(); g = tr.groupby(["champion", "position"]); sty = pd.DataFrame({"games": g.size()})
if HL is not None: tr["w"] = wt(tr)
for s in STATS:
    if HL is None:
        a = g[s].agg(["sum", "count"]); sty[s] = a["sum"] / (a["count"] + 20)
    else:  # weighted: the 20 still pulls toward 0, in units of full-weight games
        ok = tr[s].notna(); a = tr[ok].assign(wv=tr.w[ok] * tr[s][ok]).groupby(["champion", "position"])[["wv", "w"]].sum()
        sty[s] = (a.wv / (a.w + 20)).reindex(sty.index).fillna(0.0)
for grp, ss in GROUP.items(): sty[grp] = sty[ss].mean(axis=1)
allp = raw[raw.position.isin(ROLES)][["gameid", "side", "position", "champion"]]
allp = allp.join(sty[list(GROUP)], on=["champion", "position"]).fillna({k: 0.0 for k in GROUP})
dr = allp.groupby(["gameid", "side"])[list(GROUP)].sum().unstack()
dr.columns = [f"{a}_{b.lower()}" for a, b in dr.columns]
dr.round(4).to_csv(os.path.join(OUT, "comp3_games.csv"))
sty.round(4).to_csv(os.path.join(OUT, "comp3_styles_pre_sep.csv"))
print(dr.describe().round(3).to_string())
