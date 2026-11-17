"""Pull each champion's region (faction) and Riot's related champions from Riot's Universe site (17 Nov 2026 AEST; for the Draft Clash
flavour synergies, Luke OK'd flavour). Read-only, one request per champion with a pause.
Source: https://universe-meeps.leagueoflegends.com/v1/en_us/champions/<slug>/index.json (the data behind universe.leagueoflegends.com),
fields champion.associated-faction-slug and related-champions[].slug. Slug = the Data Dragon id in lower case.
Output: research/local/champions/universe_2026-11-17.json {name: {slug, faction, related: [names]}} plus failures.
usage (repo root): python -I research/champions/pull_universe.py"""
import json, time, urllib.request, csv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research" / "local" / "champions" / "universe_2026-11-17.json"
rows = list(csv.DictReader(open(ROOT / "research" / "champions" / "champions.csv", encoding="utf-8")))
by_slug = {r["api_name"].lower(): r["name"] for r in rows}; by_slug["renataglasc"] = "Renata Glasc"  # her Universe slug differs from her Data Dragon id
res, fail = {}, {}
for r in rows:
    slug = "renataglasc" if r["name"] == "Renata Glasc" else r["api_name"].lower()
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://universe-meeps.leagueoflegends.com/v1/en_us/champions/{slug}/index.json",
                                                                     headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
        rel = [x.get("slug") for x in d.get("related-champions", [])]
        res[r["name"]] = {"slug": slug, "faction": d.get("champion", {}).get("associated-faction-slug"), "related_slugs": rel,
                          "related": [by_slug.get(s) for s in rel]}
    except Exception as e:
        fail[r["name"]] = str(e)
    time.sleep(0.3)
OUT.write_text(json.dumps({"source": "https://universe-meeps.leagueoflegends.com/v1/en_us/champions/<slug>/index.json", "pulled": "2026-11-17",
                           "champions": res, "failed": fail}, indent=1), encoding="utf-8")
print("ok", len(res), "failed", len(fail), list(fail)[:10])
