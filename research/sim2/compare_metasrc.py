"""Read-only: the app's METAsrc counters (CTR_RAW in js/data.js: per champion, 8 best and 8 worst lane matchups, win rate, patch 26.20)
against lolalytics (Emerald+, 16.20, same lane): do the two solo-queue sources agree on the same matchups?
usage: python -I compare_metasrc.py <data.js> lola_counters.csv"""
import re, sys
import numpy as np
import pandas as pd

js, LC = sys.argv[1:3]
txt = open(js, encoding="utf-8").read()
block = txt[txt.index("const CTR_RAW={"):]; block = block[:block.index("\n};")]
POS = {"TOP": "top", "JGL": "jng", "MID": "mid", "ADC": "bot", "SUP": "sup"}
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
rows = []
for m in re.finditer(r'"([^"]+)":\["(\w+)","([\d.]+)","([^"]*)","([^"]*)"', block):
    champ, role, patch, s, w = m.groups()
    for part, kind in ((s, "wins"), (w, "loses")):
        for item in filter(None, part.split(",")):
            mm = re.match(r"^(.*) ([\d.]+)$", item.strip())
            if mm: rows.append((champ, POS.get(role, role), patch, mm.group(1), float(mm.group(2)), kind))
M = pd.DataFrame(rows, columns=["champion", "position", "patch", "vs", "metasrc_wr", "list"])
print(f"METAsrc pairs in the app: {len(M)} ({M.champion.nunique()} champions), patches {M.patch.unique().tolist()}")
L = pd.read_csv(LC, dtype={"patch": str}); L = L[(L.patch == "16.20")]
VS = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}
L = L[L.vslane == L.position.map(VS)]
lk = {(key(r.champion), r.position, key(r.vs_champion)): (r.vsWr, r.n, r.d1) for r in L.itertuples()}
M["lola"] = [lk.get((key(r.champion), r.position, key(r.vs))) for r in M.itertuples()]
J = M.dropna(subset=["lola"]).copy(); J["lola_wr"] = J.lola.map(lambda t: t[0]); J["lola_n"] = J.lola.map(lambda t: t[1]); J["lola_d1"] = J.lola.map(lambda t: t[2])
print(f"pairs found on lolalytics 16.20 (100+ games there): {len(J)} of {len(M)}")
rc = lambda a, b: float(pd.Series(a).rank().corr(pd.Series(b).rank()))
print(f"win rate agreement (rank): {rc(J.metasrc_wr, J.lola_wr):.3f}; mean METAsrc {J.metasrc_wr.mean():.1f} v lolalytics {J.lola_wr.mean():.1f}")
for kind in ("wins", "loses"):
    s = J[J.list == kind]
    print(f"  METAsrc '{kind}' list: {len(s)} pairs; lolalytics has the same direction (win rate {'>' if kind == 'wins' else '<'} 50) in "
          f"{int(((s.lola_wr > 50) if kind == 'wins' else (s.lola_wr < 50)).sum())}")
J.drop(columns=["lola"]).to_csv("metasrc_v_lola.csv", index=False)
