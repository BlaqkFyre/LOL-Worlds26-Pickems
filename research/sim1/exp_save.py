"""Join the Leaguepedia career export (exp_rows.json; read 3 Nov 2026) to the file's 442 players; players not listed have no
Worlds/MSI history before 2026. Writes out/player_experience_pre2026.csv."""
import json
import pandas as pd

rows = json.load(open("exp_rows.json", encoding="utf-8"))
pn = pd.read_csv("pnow.csv")[["playerid", "name", "team", "role", "games"]]
pn["short"] = pn.playerid.str[10:]
def full(pref):
    m = pn[pn.short.str.startswith(pref)]
    assert len(m) == 1, (pref, len(m))
    return m.playerid.iloc[0]
E = pd.DataFrame(rows, columns=["pref", "lp_link", "worlds_appearances", "worlds_games", "msi_games", "worlds_titles", "msi_titles"])
E["playerid"] = E.pref.map(full)
out = pn.merge(E.drop(columns="pref"), on="playerid", how="left")
for c in ("worlds_appearances", "worlds_games", "msi_games", "worlds_titles", "msi_titles"):
    out[c] = out[c].fillna(0).astype(int)
out["intl_games"] = out.worlds_games + out.msi_games
out.drop(columns="short").to_csv("out/player_experience_pre2026.csv", index=False)
print(len(out), "players;", int((out.intl_games > 0).sum()), "with international games;", int((out.worlds_titles > 0).sum()),
      "Worlds title holders;", int((out.msi_titles > 0).sum()), "MSI title holders")
t = out[out.worlds_titles + out.msi_titles > 0].sort_values(["worlds_titles", "msi_titles"], ascending=False)
print(t[["name", "team", "worlds_titles", "msi_titles", "worlds_appearances", "intl_games"]].to_string(index=False))
