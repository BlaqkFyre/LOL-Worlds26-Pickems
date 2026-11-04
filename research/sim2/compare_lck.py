"""Sim session 2 (read-only): champion picks/bans/wins in LCK 2026 Rounds 3-4 from gol.gg, Leaguepedia and the Oracle's Elixir file,
plus the file's learned champion strength next to each pro win rate.
usage: python -I compare_lck.py <csv> gol_lck_r34.csv lp_lck_r34.csv champion_strength_now.csv <out_csv>"""
import re, sys
import numpy as np
import pandas as pd

CSV, GOL, LP, STR, OUT = sys.argv[1:6]
key = lambda s: re.sub(r"[^a-z]", "", str(s).lower())
df = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "split", "date", "position", "side", "champion", "result",
                                                 "ban1", "ban2", "ban3", "ban4", "ban5"])
lck = df[df.league == "LCK"]
print("LCK splits in file:", lck.groupby("split").agg(games=("gameid", "nunique"), first=("date", "min"), last=("date", "max")).to_string())
gol = pd.read_csv(GOL); lp = pd.read_csv(LP)
gol["k"] = gol.champ.map(key); lp["k"] = lp.champ.map(key)
n_gol = int(gol.picks.sum() / 10); n_lp = int(lp.picks.sum() / 10)
print(f"games implied by picks: gol.gg {gol.picks.sum() / 10:.1f}, Leaguepedia {lp.picks.sum() / 10:.1f}")
def file_counts(sub):
    pl = sub[sub.position != "team"]; tm = sub[sub.position == "team"]
    f = pl.groupby("champion").agg(picks=("gameid", "size"), wins=("result", "sum")).reset_index()
    bans = pd.concat([tm[c] for c in ["ban1", "ban2", "ban3", "ban4", "ban5"]]).value_counts()
    f["bans"] = f.champion.map(bans).fillna(0).astype(int); f["k"] = f.champion.map(key)
    return f, pl.gameid.nunique()
# pick the file window whose game count best matches the sites' (by split name first)
lck = lck.merge(df[df.position == "team"].groupby("gameid").size().rename("_n"), left_on="gameid", right_index=True)
raw_po = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "playoffs"]).groupby("gameid").playoffs.max()
lck = lck[lck.split == "Rounds 3-4"].copy(); lck["playoffs"] = lck.gameid.map(raw_po)
print("file Rounds 3-4 by playoffs flag:", lck.groupby("playoffs").gameid.nunique().to_dict())
sub = lck[lck.playoffs == 0]; sp = "Rounds 3-4, playoffs = 0"
F, n_file = file_counts(sub)
print(f"file window used: split {sp!r}, {n_file} games")
M = gol[["k", "champ", "picks", "bans", "wins"]].rename(columns={"picks": "gol_picks", "bans": "gol_bans", "wins": "gol_wins"}) \
    .merge(lp[["k", "picks", "bans", "wins"]].rename(columns={"picks": "lp_picks", "bans": "lp_bans", "wins": "lp_wins"}), on="k", how="outer") \
    .merge(F[["k", "picks", "bans", "wins"]].rename(columns={"picks": "oe_picks", "bans": "oe_bans", "wins": "oe_wins"}), on="k", how="outer")
S = pd.read_csv(STR); S["k"] = S.champion.map(key)
st = S.groupby("k").apply(lambda d: np.average(d.strength, weights=d.games)).rename("file_strength")
M = M.merge(st, left_on="k", right_index=True, how="left").fillna({c: 0 for c in M.columns if c.endswith(("picks", "bans", "wins"))})
for a, b in (("gol", "lp"), ("gol", "oe"), ("lp", "oe")):
    for s in ("picks", "bans", "wins"):
        d = (M[f"{a}_{s}"] - M[f"{b}_{s}"]).abs()
        print(f"{a} v {b} {s}: exact {int((d == 0).sum())}/{len(M)}, total abs diff {int(d.sum())}")
big = M[M.lp_picks >= 10].copy()
for s in ("gol", "lp", "oe"): big[f"{s}_wr"] = big[f"{s}_wins"] / big[f"{s}_picks"].replace(0, np.nan)
print("\nchampions with 10+ games:", len(big))
print("rank agreement (Spearman) of win rate: gol v lp %.3f, lp v file %.3f" % (big.gol_wr.rank().corr(big.lp_wr.rank()), big.lp_wr.rank().corr(big.oe_wr.rank())))
print("rank agreement, LCK R3-4 win rate v file's learned season strength: %.3f" % big.lp_wr.rank().corr(big.file_strength.rank()))
M.sort_values("lp_picks", ascending=False).to_csv(OUT, index=False)
print(M.sort_values("lp_picks", ascending=False).head(12).to_string(index=False))
