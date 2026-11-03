"""Read-only: what in Faker's 2026 major-league games drives his card? Compare with LCK mids and the Worlds mids, by month."""
import sys
import numpy as np
import pandas as pd

MAJOR = ["LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"]
df = pd.read_csv(sys.argv[1], low_memory=False)
df = df[df.league.isin(MAJOR) & ~((df.league == "WLDs") & (df.date < "2026-10-01")) & (df.position == "mid")].copy()
mins = df.gamelength / 60
df["kp"] = (df.kills + df.assists) / df.teamkills.where(df.teamkills > 0)
df["ka15"] = df.killsat15 + df.assistsat15
df["d30"] = df.deaths / mins * 30
df["solo_early_deaths"] = df.deathsat15
df["month"] = df.date.str[:7]
S = ["golddiffat15", "xpdiffat15", "csdiffat15", "damageshare", "dpm", "kp", "ka15", "d30", "earnedgoldshare", "cspm", "result"]
lck = df[df.league == "LCK"]
fk = df[df.playername == "Faker"]
print(f"Faker games {len(fk)} ({fk.league.value_counts().to_dict()})")
cmp = pd.DataFrame({"Faker": fk[S].mean(), "LCK mid avg": lck[S].mean(),
                    "Chovy": df[df.playername == "Chovy"][S].mean(), "Zeka": df[df.playername == "Zeka"][S].mean(),
                    "ShowMaker": df[df.playername == "ShowMaker"][S].mean(), "Knight": df[df.playername == "Knight"][S].mean()})
print(cmp.round(3).to_string())
# where does Faker rank among LCK mids with 30+ games, per stat
cnt = lck.groupby("playername").size(); big = cnt[cnt >= 30].index
rk = lck[lck.playername.isin(big)].groupby("playername")[S[:-1]].mean()
print("\nFaker's rank among", len(big), "LCK mids with 30+ games (1 = best; d30 lower is better):")
print({s: int((rk[s] > rk.loc["Faker", s]).sum() + 1) if s != "d30" else int((rk[s] < rk.loc["Faker", s]).sum() + 1) for s in S[:-1]})
print("\nFaker by month (gold/xp/cs lead at 15, damage share, kp, games, win rate):")
print(fk.groupby("month").agg(g=("result", "size"), gd15=("golddiffat15", "mean"), xpd15=("xpdiffat15", "mean"), csd15=("csdiffat15", "mean"),
                              dmg=("damageshare", "mean"), kp=("kp", "mean"), win=("result", "mean")).round(2).to_string())
print("\nT1 gold share by role (who gets T1's resources):")
t1 = pd.read_csv(sys.argv[1], low_memory=False)
t1 = t1[(t1.teamname == "T1") & (t1.position != "team") & t1.league.isin(MAJOR)]
print(t1.groupby("position")[["earnedgoldshare", "damageshare"]].mean().round(3).to_string())
lckall = pd.read_csv(sys.argv[1], low_memory=False)
lckall = lckall[(lckall.league == "LCK") & (lckall.position != "team")]
print("LCK average by role:"); print(lckall.groupby("position")[["earnedgoldshare", "damageshare"]].mean().round(3).to_string())
