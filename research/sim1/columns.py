"""Read-only: which per-player columns does the Oracle's Elixir file have, and how complete are they in major-league games?"""
import sys
import pandas as pd

MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
df = pd.read_csv(sys.argv[1], low_memory=False)
pl = df[(df.position != "team") & df.league.isin(MAJOR) & ~((df.league == "WLDs") & (df.date < "2026-10-01"))]
print(f"player rows {len(pl)} · games {pl.gameid.nunique()} · leagues {sorted(pl.league.unique())}")
print(f"positions {pl.position.value_counts().to_dict()}")
print("\ncolumn | non-empty % (major-league player rows) | example")
for c in df.columns:
    s = pl[c]
    full = 100 * s.notna().mean()
    ex = s.dropna().iloc[0] if s.notna().any() else ""
    print(f"{c} | {full:.0f}% | {str(ex)[:30]}")
