# Parse saved gol.gg timeline pages into tables.
#   tl_games.csv  one row per game (teams by side, winner, length, patch, date, stage)
#   tl_events.csv one row per timeline event (time, side, actor, type, detail, victim, assists)
#   tl_gold.csv   per game x minute x side x role: gold and CS
import re, os, csv, sys, html as H

OUT = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(OUT, 'raw', 'tl')
ROLES = ['top', 'jng', 'mid', 'bot', 'sup']
IMG = re.compile(r"<img[^>]*_img/(?:champions_icon/)?([^'\"]+?)(?:\.png)?['\"][^>]*>")

def secs(t):
    m, s = t.split(':'); return int(m) * 60 + int(s)

def parse(gid, h):
    title = re.search(r'<title>\s*(.*?)\s*</title>', h, re.S).group(1)
    gno = re.search(r' game (\d+) Timeline', title)
    tour = re.search(r'Timeline - (.*?) - Games of Legends', title)
    teams = re.findall(r"class=\"col-12 (blue|red)-line-header\">\s*<a[^>]*>([^<]+)</a>\s*-\s*(WIN|LOSS)", h)
    if len(teams) != 2: return None
    sides = {s: (H.unescape(n), r) for s, n, r in teams}
    dt = re.search(r'(\d{4}-\d{2}-\d{2}) \(([^)]*)\)', re.sub(r'<[^>]+>', ' ', h))
    ln = re.search(r'Game Time<br/>\s*<h1>(\d+:\d+)</h1>', h)
    pt = re.search(r'>\s*v(\d+\.\d+)\s*</div>', h)
    g = dict(gid=gid, tournament=tour.group(1) if tour else '', game=int(gno.group(1)) if gno else 1,
             date=dt.group(1) if dt else '', stage=dt.group(2) if dt else '',
             patch=pt.group(1) if pt else '', len=secs(ln.group(1)) if ln else '',
             blue=sides['blue'][0], red=sides['red'][0],
             win='blue' if sides['blue'][1] == 'WIN' else 'red')
    # per-minute gold (first 10 TOP..SPT series) then CS (next 10)
    ser = re.findall(r"label: '(TOP|JGL|MID|BOT|SPT)',\s*data: \[([^\]]*)\]", h)
    gold = []
    if len(ser) >= 20:
        for i in range(20):
            vals = [int(v) for v in ser[i][1].split(',') if v.strip()]
            kind = 'gold' if i < 10 else 'cs'
            gold.append((kind, 'blue' if i % 10 < 5 else 'red', ROLES[i % 5], vals))
    ev = []
    for pid, r in re.findall(r"<tr onmouseover='ShowPoint\((\d+)\)'[^>]*>(.*?)</tr>", h, re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
        if len(tds) < 7: continue
        side = 'blue' if 'blueside' in tds[1] else 'red' if 'redside' in tds[1] else ''
        champs = IMG.findall(tds[3])
        act = IMG.findall(tds[4]); acttxt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', tds[4])).strip()
        vict = IMG.findall(tds[5]); tgt = H.unescape(re.sub(r'<[^>]+>', '', tds[6]).strip())
        if 'kill-icon' in act: typ, det = 'kill', acttxt  # bounty gold if shown
        elif 'PLATE' in acttxt: typ, det = 'plate', tgt
        elif 'tower-icon' in act: typ, det = 'tower', tgt
        elif 'inhib-icon' in act: typ, det = 'inhib', tgt
        elif 'nexus-icon' in act: typ, det = 'nexus', tgt
        elif 'nashor-icon' in act: typ, det = 'baron', ''
        elif 'herald-icon' in act: typ, det = 'herald', ''
        elif 'voidgrubs-icon' in act: typ, det = 'grub', ''
        elif any('dragon' in a or 'drake' in a for a in act):
            typ, det = 'dragon', [a for a in act if 'dragon' in a or 'drake' in a][0].replace('-dragon', '').replace('-drake', '')
        elif any('atakhan' in a for a in act): typ, det = 'atakhan', ''
        else: typ, det = 'other', '|'.join(act) + acttxt
        ev.append(dict(gid=gid, t=secs(tds[0].strip()), side=side, actor=H.unescape(re.sub(r'<[^>]+>', '', tds[2]).strip()),
                       champ=champs[0] if champs else '', assists='|'.join(champs[1:]), type=typ, detail=det,
                       victim_champ=vict[0] if vict else '', victim=tgt if typ == 'kill' else ''))
    return g, ev, gold

if __name__ == '__main__':
    files = sorted(f for f in os.listdir(TL) if f.endswith('.html') and f[:-5].isdigit())
    G, E, Gd = [], [], []
    bad = []
    for f in files:
        gid = f[:-5]
        r = parse(gid, open(os.path.join(TL, f), encoding='utf-8').read())
        if not r: bad.append(gid); continue
        g, ev, gold = r
        G.append(g); E += ev
        for kind, side, role, vals in gold:
            for m, v in enumerate(vals): Gd.append((gid, kind, side, role, m, v))
    def w(name, rows, cols):
        with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
            wr = csv.writer(fh); wr.writerow(cols)
            for x in rows: wr.writerow([x[c] for c in cols] if isinstance(x, dict) else x)
    w('tl_games.csv', G, list(G[0].keys()))
    w('tl_events.csv', E, list(E[0].keys()))
    w('tl_gold.csv', Gd, ['gid', 'kind', 'side', 'role', 'minute', 'value'])
    print('games', len(G), 'events', len(E), 'gold rows', len(Gd), 'unparsed', bad[:20], len(bad))
    from collections import Counter
    print(Counter(e['type'] for e in E))
    print(Counter(e['detail'] for e in E if e['type'] == 'dragon'))
    print([e for e in E if e['type'] == 'other'][:5])
