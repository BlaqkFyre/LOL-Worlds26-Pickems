"""Read-only: lolalytics lane counters (Emerald+) for every champion-role pros played on recent patches.
Each counters page embeds its matchup records (opponents with enough games): cid, vsWr (this champion's win rate v the opponent),
n (games), d1 = vsWr - allWr, d2 (lolalytics' second delta), allWr. Checked 4 Nov: Orianna mid v Ezreal mid 16.20 = 59.86 / 54.83 / +5.03.
Pairs: same lane v same lane; bot also ADC v enemy support and support v enemy ADC (for the bot duo).
usage: python -I lola_counters.py <OE csv> <out_csv> <min_pro_games> <patch> [<patch> ...]"""
import csv, html, json, re, sys, time, urllib.request
import pandas as pd

CSV, OUT, MING = sys.argv[1], sys.argv[2], int(sys.argv[3]); PATCHES = sys.argv[4:]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
LANE = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8")
def objs(h):
    o = json.loads(html.unescape(re.search(r'<script type="qwik/json">(.*?)</script>', h, re.S).group(1)))["objs"]
    return o, (lambda v: o[int(v, 36)] if isinstance(v, str) and re.fullmatch(r"[0-9a-z]+", v) else v)
# champion name <-> lolalytics key <-> id, from a tier list page
o, R = objs(get("https://lolalytics.com/lol/tierlist/?lane=top&patch=16.20"))
meta = next(x for x in o if isinstance(x, dict) and "champId" in x and "champions" in x)
cid, names = R(meta["champId"]), R(meta["champions"])
k2id = {k: R(v) for k, v in cid.items()}; id2name = {R(v): R(names[k]) for k, v in cid.items() if k in names}
norm = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
name2key = {norm(R(names[k])): k for k in names}
name2key.update({norm(k): k for k in names})
# which champion-roles pros played on recent patches
df = pd.read_csv(CSV, low_memory=False, dtype={"patch": str}, usecols=["gameid", "league", "date", "patch", "position", "champion"])
df = df[df.league.isin(MAJOR) & (df.position != "team") & ~((df.league == "WLDs") & (df.date < "2026-10-01"))]
def np_(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
df["patch"] = df.patch.map(np_)
rec = df[df.patch >= "16.15"].groupby(["champion", "position"]).size()
todo = [(c, p) for (c, p), n in rec.items() if n >= MING]
missing = sorted({c for c, _ in todo if norm(c) not in name2key})
print(f"champion-roles with {MING}+ pro games on 16.15-16.20: {len(todo)}; names not found on lolalytics: {missing}")
pairs = []
for c, p in todo:
    if norm(c) not in name2key: continue
    pairs.append((c, p, LANE[p]))
    if p == "bot": pairs.append((c, p, "support"))
    if p == "sup": pairs.append((c, p, "bottom"))
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["patch", "champion", "position", "vslane", "vs_champion", "vsWr", "n", "d1", "d2", "allWr"])
    done = 0
    for patch in PATCHES:
        for c, p, vs in pairs:
            url = f"https://lolalytics.com/lol/{name2key[norm(c)]}/counters/?lane={LANE[p]}&vslane={vs}&patch={patch}"
            try:
                h = get(url)
            except Exception as e:
                print("fail", url, e); continue
            shown = re.search(r"Patch\s*(?:<[^>]*>\s*)*(16\.\d+)", h)
            o, R = objs(h)
            for x in o:
                if isinstance(x, dict) and {"cid", "vsWr", "n", "d1"} <= set(x):
                    r = {a: R(b) for a, b in x.items()}
                    w.writerow([patch, c, p, vs, id2name.get(r["cid"], r["cid"]), r["vsWr"], r["n"], r["d1"], r["d2"], r["allWr"]])
            done += 1
            if done % 50 == 0: print(done, "pages", flush=True)
            time.sleep(0.8)
print("pages read:", done)
