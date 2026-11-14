"""Champion database (14 Nov 2026 AEST; Luke: metadata for every champion for the draft work and another project). Read-only.
One row per champion (173; the wiki's two form rows, Mega Gnar and Kled & Skaarl, are left out).
Sources:
  Riot client data, read from the League wiki's Module:ChampionData/data (https://wiki.leagueoflegends.com/en-us/Module:ChampionData/data,
  read 14 Nov 2026 in the browser pane; the wiki blocks scripts). Copied line by line into
  research/local/champions/wiki_championdata_2026-11-14.txt and checked: all 175 lines match the browser's per-line fingerprints.
    class, secondary class, subclasses (Riot's class system), client tags, damage tag (Physical / Magic / Mixed), adaptive type,
    Riot's 1-3 style ratings (damage, toughness, control = crowd control, mobility, utility), style (0 = all basic attacks,
    100 = all abilities), difficulty, range type, attack range, resource, Riot's lane positions and the wiki's wider position list,
    release date, last changed patch.
  Pro play, the Oracle's Elixir file (lib.data.oe(): 2026 major leagues; the Worlds qualifier rows before 1 Oct left out):
    games and win rate in 2026, Worlds games, picks, bans and presence, role shares, average damage share by role.
Meta role (Luke: Worlds / patch 16.20 first): the role a champion is played in most at Worlds when it has 5+ Worlds games; else across
2026 major-league games when it has 5+; else Riot's first lane position (meta_role_source says which). Off-roles: every other role with
10%+ and 2+ games either at Worlds or across 2026 majors (thresholds in OFF_SHARE / OFF_GAMES; the share columns are in the file to apply others).
usage (repo root): python -I research/champions/build_champion_db.py   (writes research/champions/champions.csv and champions.json)"""
import sys, os, json, csv
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
WIKI = config.R / "local" / "champions" / "wiki_championdata_2026-11-14.txt"
OUT_CSV, OUT_JSON = config.R / "champions" / "champions.csv", config.R / "champions" / "champions.json"
MIN_GAMES, OFF_SHARE, OFF_GAMES = 5, 0.10, 2
F = ["name", "riot_id", "api_name", "title", "difficulty", "class", "class_secondary", "subclasses", "client_tags", "riot_lanes", "wiki_lanes",
     "riot_damage", "riot_toughness", "riot_cc", "riot_mobility", "riot_utility", "style", "adaptive_type", "released", "last_changed", "attack_range"]
RAW = ["name", "riot_id", "api_name", "title", "difficulty", "class", "class_secondary", "resource", "range_type", "subclasses", "client_tags",
       "riot_lanes", "wiki_lanes", "riot_damage", "riot_toughness", "riot_cc", "riot_mobility", "riot_utility", "style", "adaptive_type",
       "released", "last_changed", "attack_range"]
LANE = {"Top": "top", "Jungle": "jng", "Middle": "mid", "Bottom": "bot", "Support": "sup"}
ROLE_NAME = {"top": "Top", "jng": "Jungle", "mid": "Mid", "bot": "Bot", "sup": "Support"}
with Run("champion_db", params={"min_games": MIN_GAMES, "off_share": OFF_SHARE, "off_games": OFF_GAMES}, inputs=[WIKI, config.OE_CSV]) as run:
    rows = [dict(zip(RAW, l.rstrip("\n").split("|"))) for l in open(WIKI, encoding="utf-8")]
    assert len(rows) == 175 and all(len(r) == len(RAW) for r in rows), "wiki extract changed shape"
    W = pd.DataFrame(rows); W = W[~W.riot_id.str.contains(r"\.")].copy()  # form rows (150.2 Mega Gnar, 240.1 Kled & Skaarl)
    for c in ["difficulty", "riot_damage", "riot_toughness", "riot_cc", "riot_mobility", "riot_utility", "style", "attack_range"]: W[c] = pd.to_numeric(W[c])
    W["riot_id"] = W.riot_id.astype(int)
    tags = W.client_tags.str.split("/").apply(lambda t: [x.strip() for x in t if x.strip()])
    W["damage_tag"] = tags.apply(lambda t: next((x for x in t if x in ("Physical", "Magic", "Mixed")), ""))
    W["damage_types"] = W.damage_tag.map({"Physical": "Physical", "Magic": "Magic", "Mixed": "Physical+Magic"})
    W["damage_type_source"] = np.where(W.damage_types.isna(), "Riot adaptive type (no damage tag)", "Riot damage tag")
    W["damage_types"] = W.damage_types.fillna(W.adaptive_type)
    W["playstyle_tags"] = tags.apply(lambda t: "/".join(x for x in t if x not in ("Physical", "Magic", "Mixed")))
    W["riot_lane_roles"] = W.riot_lanes.apply(lambda s: "/".join(LANE[x] for x in s.split("/") if x in LANE))
    W["wiki_lane_roles"] = W.wiki_lanes.apply(lambda s: "/".join(LANE[x] for x in s.split("/") if x in LANE))
    W["key"] = W.name.map(data.key)
    # pro play
    o = data.oe(["gameid", "league", "date", "side", "position", "champion", "result", "damageshare", "ban1", "ban2", "ban3", "ban4", "ban5"]); data.check(o)
    o = o[o.league.isin(config.MAJOR)]; P = o[o.position.isin(config.ROLES)].copy(); P["key"] = P.champion.map(data.key)
    unknown = sorted(set(P.key) - set(W.key)); assert not unknown, f"champions in the file but not in the wiki data: {unknown}"
    Wd = P[P.league == "WLDs"]; nW = Wd.gameid.nunique()
    T = o[(o.position == "team") & (o.league == "WLDs")]
    bans = pd.Series([data.key(b) for c in ["ban1", "ban2", "ban3", "ban4", "ban5"] for b in T[c].dropna()]).value_counts()
    out = []
    for r in W.to_dict("records"):
        a, w = P[P.key == r["key"]], Wd[Wd.key == r["key"]]
        sample, src = (w, "Worlds 2026") if len(w) >= MIN_GAMES else (a, "2026 major leagues") if len(a) >= MIN_GAMES else (None, "Riot lane (few pro games)")
        share = (sample.position.value_counts(normalize=True) if sample is not None else pd.Series(dtype=float))
        cnt = (sample.position.value_counts() if sample is not None else pd.Series(dtype=float))
        meta = share.idxmax() if len(share) else (r["riot_lane_roles"].split("/")[0] if r["riot_lane_roles"] else "")
        def offs(d):
            if d is None or not len(d): return set()
            sh, c = d.position.value_counts(normalize=True), d.position.value_counts()
            return {k for k in sh.index if sh[k] >= OFF_SHARE and c[k] >= OFF_GAMES}
        off = [k for k in config.ROLES if k != meta and k in (offs(w) | offs(a))]
        def rshare(d): s = d.position.value_counts(normalize=True); return {k: round(float(s.get(k, 0)), 3) for k in config.ROLES}
        dm = a[a.position == meta].damageshare.mean() if len(a[a.position == meta]) else np.nan
        role_avg = P[P.position == meta].damageshare.mean() if meta else np.nan
        row = {**{k: r[k] for k in ["name", "riot_id", "api_name", "title", "class", "class_secondary", "subclasses", "damage_types", "damage_type_source", "damage_tag",
                                              "adaptive_type", "range_type", "attack_range", "resource", "difficulty", "style",
                                              "riot_damage", "riot_toughness", "riot_cc", "riot_mobility", "riot_utility", "playstyle_tags",
                                              "riot_lane_roles", "wiki_lane_roles", "released", "last_changed"]},
               "meta_role": meta, "meta_role_name": ROLE_NAME.get(meta, ""), "off_roles": "/".join(off), "meta_role_source": src,
               "meta_role_share": round(float(share.get(meta, 0)), 3) if len(share) else None,
               "pro_games_2026": len(a), "pro_winrate_2026": round(float(a.result.mean()), 3) if len(a) else None,
               "worlds_games": len(w), "worlds_bans": int(bans.get(r["key"], 0)),
               "worlds_presence": round((len(w) + int(bans.get(r["key"], 0))) / nW, 3),
               "pro_dmg_share_meta_role": round(float(dm), 3) if pd.notna(dm) else None,
               "pro_dmg_index_meta_role": round(float(dm / role_avg), 2) if pd.notna(dm) and role_avg else None,
               **{f"share_2026_{k}": v for k, v in (rshare(a) if len(a) else {k: 0.0 for k in config.ROLES}).items()},
               **{f"share_worlds_{k}": v for k, v in (rshare(w) if len(w) else {k: 0.0 for k in config.ROLES}).items()}}
        out.append(row)
    D = pd.DataFrame(out).sort_values("name")
    run.result("champions", len(D)); run.result("with a Worlds meta role", int((D.meta_role_source == "Worlds 2026").sum()))
    run.result("with a 2026 meta role", int((D.meta_role_source == "2026 major leagues").sum())); run.result("from Riot lanes", int((D.meta_role_source == "Riot lane (few pro games)").sum()))
    meta = {"built": "research/champions/build_champion_db.py", "sources": {"riot_client_data": "League wiki Module:ChampionData/data, read 14 Nov 2026 (https://wiki.leagueoflegends.com/en-us/Module:ChampionData/data)",
            "pro_play": "Oracle's Elixir 2026 file (major leagues; Worlds = 94 games on patch 16.20)"},
            "rules": {"meta_role": f"most-played role at Worlds if {MIN_GAMES}+ Worlds games, else 2026 majors if {MIN_GAMES}+, else Riot's first lane",
                      "off_roles": f"other roles with {OFF_SHARE:.0%}+ and {OFF_GAMES}+ games at Worlds or across 2026 majors",
                      "riot ratings": "Riot client style ratings 1-3 (0 where Riot gives 0): damage, toughness, cc (control), mobility, utility",
                      "style": "0 = all basic attacks, 100 = all abilities", "damage_types": "from Riot's client damage tag; Mixed = Physical+Magic; true damage is not in the source"},
            "champions": D.replace({np.nan: None}).to_dict("records")}
    run.save_json(OUT_JSON, meta)
    tmp = OUT_CSV.with_suffix(".tmp"); D.to_csv(tmp, index=False, quoting=csv.QUOTE_MINIMAL); os.replace(tmp, OUT_CSV)
    print(D[["name", "class", "subclasses", "damage_types", "meta_role", "off_roles", "meta_role_source", "worlds_games", "riot_damage", "riot_cc", "riot_utility"]].head(12).to_string())
    print(D.meta_role_source.value_counts().to_dict())
