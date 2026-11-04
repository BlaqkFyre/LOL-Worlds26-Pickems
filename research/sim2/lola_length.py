"""Read-only: lolalytics win rate by game length (Emerald+) for the champion-roles pros played on recent patches.
Each build page embeds {time: games per bucket, timeWin: wins per bucket}, 7 buckets in game-length order (the bucket edges are not
stated in the data; only their order is used). Checked 5 Nov on Jinx bottom 16.20: games 4,555 / 37,637 / 84,507 / 156,713 / 119,666 /
47,418 / 15,463.
usage: python -I lola_length.py lola_counters.csv <out_csv> <patch> [<patch> ...]"""
import csv, html, json, re, sys, time, urllib.request
import pandas as pd

CNT, OUT = sys.argv[1:3]; PATCHES = sys.argv[3:]
LANE = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8")
def objs(h):
    o = json.loads(html.unescape(re.search(r'<script type="qwik/json">(.*?)</script>', h, re.S).group(1)))["objs"]
    return o, (lambda v: o[int(v, 36)] if isinstance(v, str) and re.fullmatch(r"[0-9a-z]+", v) else v)
o, R = objs(get("https://lolalytics.com/lol/tierlist/?lane=top&patch=16.20"))
meta = next(x for x in o if isinstance(x, dict) and "champId" in x and "champions" in x)
names = R(meta["champions"]); norm = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
name2key = {norm(R(names[k])): k for k in names}
pairs = pd.read_csv(CNT)[["champion", "position"]].drop_duplicates().values.tolist()
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["patch", "champion", "position"] + [f"g{i}" for i in range(1, 8)] + [f"w{i}" for i in range(1, 8)])
    for p in PATCHES:
        for c, pos in pairs:
            k = name2key.get(norm(c))
            if not k: continue
            try:
                o, R = objs(get(f"https://lolalytics.com/lol/{k}/build/?lane={LANE[pos]}&patch={p}"))
            except Exception as e:
                print("fail", c, pos, p, e); continue
            x = next((x for x in o if isinstance(x, dict) and set(x) == {"time", "timeWin"}), None)
            if x is None: print("no length data", c, pos, p); continue
            tg, tw = R(x["time"]), R(x["timeWin"])
            w.writerow([p, c, pos] + [R(tg.get(str(i), 0)) for i in range(1, 8)] + [R(tw.get(str(i), 0)) for i in range(1, 8)])
            time.sleep(0.6)
        print("done", p, flush=True)
