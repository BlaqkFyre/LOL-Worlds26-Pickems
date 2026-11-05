# Pull gol.gg game timelines (read-only, 3 requests at a time, cached on disk).
# Game ids in a series run in order from the series' first id; the count comes from the series score.
# Each saved page is checked (title "game N", same two teams); a series that doesn't fit falls back to its summary page.
# Output: raw/series.csv and raw/tl/<id>.html
import urllib.request, urllib.parse, re, os, time, csv
from concurrent.futures import ThreadPoolExecutor

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
TOURS = ['Worlds 2026 Main Event', 'Worlds 2026 Play-In',
         'LCK 2026 Season Playoffs',
         'LEC 2026 Summer Playoffs', 'LCS 2026 Summer Playoffs', 'CBLOL 2026 Split 2 Playoffs',
         'LCK 2026 Season Play-In',
         'LCK 2026 Rounds 3-4', 'LEC 2026 Summer Season',  # LPL: gol.gg has no timelines
         'LCS 2026 Summer', 'CBLOL 2026 Split 2', 'Esports World Cup 2026']
OUT = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(OUT, 'raw', 'tl'); os.makedirs(TL, exist_ok=True)
SM = os.path.join(OUT, 'raw', 'sm'); os.makedirs(SM, exist_ok=True)

def get(u, cache=None):
    if cache and os.path.exists(cache) and os.path.getsize(cache) > 10000:
        return open(cache, encoding='utf-8').read()
    for k in range(3):
        try:
            h = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read().decode('utf-8', 'ignore')
            time.sleep(0.5)
            if cache: open(cache, 'w', encoding='utf-8').write(h)
            return h
        except Exception as e:
            print('retry', u, e, flush=True); time.sleep(10)
    return ''

def tl(g): return get(f'https://gol.gg/game/stats/{g}/page-timeline/', os.path.join(TL, f'{g}.html'))

def fits(h, k):
    t = re.search(r'<title>(.*?)</title>', h, re.S)
    return bool(t and f' game {k} Timeline' in t.group(1))

def series(item):
    t, sid, txt, n = item
    gids = [str(int(sid) + k) for k in range(n)]
    ok = n > 0
    for k, g in enumerate(gids):
        if not fits(tl(g), k + 1) and not (n == 1): ok = False; break
    if not ok:
        sh = get(f'https://gol.gg/game/stats/{sid}/page-summary/', os.path.join(SM, sid + '.html'))
        gids = sorted(set(re.findall(r'game/stats/(\d+)/page-game', sh)), key=int) or [sid]
        for g in gids: tl(g)
    return [t, sid, txt, ' '.join(gids), 'score' if ok else 'summary']

items = []
for t in TOURS:
    h = get('https://gol.gg/tournament/tournament-matchlist/' + urllib.parse.quote(t) + '/')
    for r in re.findall(r'<tr>(.*?)</tr>', h, re.S):
        m = re.search(r'game/stats/(\d+)/page-(summary|game)', r)  # Bo1 rows link straight to the game page
        if not m: continue  # preview = not played yet
        txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', r)).strip()
        sc = re.search(r' (\d) - (\d) ', ' ' + txt + ' ')
        n = 1 if m.group(2) == 'game' else (int(sc.group(1)) + int(sc.group(2)) if sc else 0)
        items.append((t, m.group(1), txt, n))
print('series', len(items), 'games by score', sum(i[3] for i in items), flush=True)

rows_out = []
with ThreadPoolExecutor(3) as ex:
    for i, r in enumerate(ex.map(series, items)):
        rows_out.append(r)
        if i % 25 == 0: print(i, r[0], r[3], r[4], flush=True)

with open(os.path.join(OUT, 'raw', 'series.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['tournament', 'series', 'row', 'games', 'ids_from']); w.writerows(rows_out)
print('done', len(rows_out), 'series', sum(len(r[3].split()) for r in rows_out), 'games')
