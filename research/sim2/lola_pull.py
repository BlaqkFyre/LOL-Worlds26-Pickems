"""Read-only: lolalytics tier lists (Emerald+, ranked solo/duo, global) per lane and patch, from the data each page embeds
(the page's qwik/json block holds all ~173 champions; the visible list shows only the top 20).
Checked 4 Nov 2026: decoded values match the page (Yone top 16.20: 51.67% win, 8.81% pick, 15.44% ban, 238,834 games).
usage: python -I lola_pull.py <out_csv> <patch> [<patch> ...]"""
import csv, html, json, re, sys, time, urllib.request

LANES = ["top", "jungle", "middle", "bottom", "support"]
def page(lane, patch):
    req = urllib.request.Request(f"https://lolalytics.com/lol/tierlist/?lane={lane}&patch={patch}",
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
def parse(h):
    shown = re.search(r"LEAGUE OF LEGENDS PATCH ([\d.]+)", h)
    m = re.search(r'<script type="qwik/json">(.*?)</script>', h, re.S)
    o = json.loads(html.unescape(m.group(1)))["objs"]
    R = lambda v: o[int(v, 36)] if isinstance(v, str) and re.fullmatch(r"[0-9a-z]+", v) else v
    meta = next(x for x in o if isinstance(x, dict) and "champId" in x and "champions" in x)
    cid, names = R(meta["champId"]), R(meta["champions"])
    id2key = {R(v): k for k, v in cid.items()}
    rec = {format_36(i) for i, x in enumerate(o) if isinstance(x, dict) and {"games", "wr", "pbi"} <= set(x)}
    mp = next(x for x in o if isinstance(x, dict) and len(x) > 50 and all(v in rec for v in x.values()))
    rows = []
    for k, ref in mp.items():
        r = {a: R(b) for a, b in R(ref).items()}
        key = id2key.get(int(k)); r["name"] = R(names[key]) if key in names else key; rows.append(r)
    return (shown.group(1) if shown else None), rows
def format_36(i):
    s = ""; d = "0123456789abcdefghijklmnopqrstuvwxyz"
    while True:
        s = d[i % 36] + s; i //= 36
        if i == 0: return s
out = sys.argv[1]; patches = sys.argv[2:]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["patch", "lane", "name", "wr", "pr", "br", "games", "pctLane", "tier", "pbi"])
    for p in patches:
        for lane in LANES:
            shown, rows = parse(page(lane, p))
            assert shown == p, (p, lane, shown)
            for r in rows:
                w.writerow([p, lane, r["name"], r["wr"], r["pr"], r["br"], r["games"], r["pctLane"], r["tier"], r["pbi"]])
            print(p, lane, shown, len(rows)); time.sleep(1.0)
