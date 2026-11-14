"""Data loaders with checks (14 Nov 2026). Every script reads the data through here, so a stale, missing or wrong-sized file stops the
run with a clear message instead of giving quiet wrong numbers.
  oe()          the Oracle's Elixir file (all rows; Worlds qualifier rows before 1 Oct removed), read once from the 78 MB CSV and then
                from a fast copy in research/local/cache (named by the CSV's SHA-256, so a new file makes a new copy)
  check(o)      the sizes in config.EXPECT (Worlds 94 games, 2,869 major-league games)
  timelines()   matched gol.gg games, their events (with the file's game id) and gold per role per minute; checks 640 matched and every
                Worlds game present
  roles(o)      (gameid, champion key) -> (role, side) for players
  worlds_days(df), key(champion)"""
import pandas as pd
from . import config
from .runlog import sha256, fingerprint  # noqa: F401 (fingerprint re-exported)

def key(s): return "".join(ch for ch in str(s).lower() if ch.isalnum())

def oe(columns=None, raw=False):
    """raw=True keeps the Worlds qualifier rows (only for counting a player's games, as the comfort input always did)"""
    fingerprint(config.OE_CSV)
    cache = config.CACHE_DIR / f"oe_{sha256(config.OE_CSV)[:16]}.parquet"
    if cache.exists(): o = pd.read_parquet(cache, columns=columns)
    else:
        full = pd.read_csv(config.OE_CSV, low_memory=False, dtype={"patch": str})
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True); tmp = cache.with_suffix(".tmp"); full.to_parquet(tmp, index=False); tmp.replace(cache)
        o = full[columns] if columns else full
    if not raw:
        if "league" not in o or "date" not in o: raise ValueError("oe(): include league and date so the qualifier rows can be removed, or pass raw=True")
        o = o[~((o.league == "WLDs") & (o.date < config.WORLDS_FROM))]
    return o.reset_index(drop=True)

def check(o):
    """stop if the file's sizes are not what the research assumes"""
    g = o.drop_duplicates("gameid")
    got = {"worlds_games": int((g.league == "WLDs").sum()), "major_games": int(g.league.isin(config.MAJOR).sum())}
    bad = {k: (v, config.EXPECT[k]) for k, v in got.items() if v != config.EXPECT[k]}
    if bad: raise RuntimeError(f"data check failed (found, expected): {bad}; if the file was updated on purpose, update config.EXPECT")
    return got

def timelines():
    for p in (config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD): fingerprint(p)
    tm = pd.read_csv(config.TL_MATCH, dtype={"gid": str}).dropna(subset=["gameid"])
    meta = oe(["gameid", "league", "date"]).drop_duplicates("gameid").set_index("gameid")
    tm = tm[tm.gameid.isin(meta.index)].copy(); tm["day"] = tm.gameid.map(meta.date).str[:10]; tm["league"] = tm.gameid.map(meta.league)
    nw = int((tm.league == "WLDs").sum())
    if len(tm) != config.EXPECT["timeline_matched"] or nw != config.EXPECT["worlds_timelines"]:
        raise RuntimeError(f"timeline check failed: {len(tm)} matched (expected {config.EXPECT['timeline_matched']}), Worlds {nw} (expected {config.EXPECT['worlds_timelines']})")
    ev = pd.read_csv(config.TL_EVENTS, dtype={"gid": str}); ev = ev[ev.gid.isin(tm.gid)].copy(); ev["gameid"] = ev.gid.map(dict(zip(tm.gid, tm.gameid)))
    gold = pd.read_csv(config.TL_GOLD, dtype={"gid": str}); gold = gold[gold.gid.isin(tm.gid)]
    return tm, ev, gold

def roles(o):
    p = o[o.position.isin(config.ROLES)]
    return {(g, key(c)): (r, s.lower()) for g, c, r, s in zip(p.gameid, p.champion, p.position, p.side)}

def worlds_days(df, day="day", league="league"): return sorted(df.loc[df[league] == "WLDs", day].unique())
