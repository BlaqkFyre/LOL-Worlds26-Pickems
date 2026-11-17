"""Draft Clash cards from the champion database (17 Nov 2026 AEST; Luke: all 173 champions in the game as class-letter codes, 100 on offer
per draft, stats shown as grades S+ S A+ A B+ B C D F, synergies that match League, plus flavour; "accurate enough and quick so it can
be playtested"). Read-only on the data; writes Draft Game/clash-cards.js (window.CLASH_CARDS) and research/champions/clash_cards.json.
Codes: Riot class letter + number by release date within the class (new champions append, so codes stay stable):
  F Fighter, M Mage, R Marksman, T Tank, S Support, A Assassin.
Card roles: main = the database's meta role (Worlds 2026 first, then 2026 majors, then Riot's lane); flex = its first off-role, else
Riot's next lane.
Stats (2026 major-league games, Oracle's Elixir; each pulled toward average for champions with few games, so rarely played champions sit
near B):
  lane  average gold edge at 15 over the opposing laner in its meta role (shrink k 5 games, the champion shrink the lane model chose)
  tf    teamfight: average of three z-scores, kill participation and damage share against its role's average (k 20 each), and
        Riot's crowd-control rating
  late  win rate in games of 33+ minutes minus win rate in games under 28 minutes (k 15 each)
  obj   share of dragons and Barons the champion's team took (k 15)
  Each stat is ranked across the 173 champions; rank p (0..1) becomes the game's number 62 + 30 p (the placeholder cards' spread, so the
  game's calibrated balance holds; 55-95 made 18% of random drafts 80%+ favourites) and a grade:
  S+ top 3%, S next 5%, A+ 7%, A 10%, B+ 15%, B 20%, C 18%, D 14%, F bottom 8%.
Synergy (the game adds these up for a team; the game's design scale, not fitted):
  pair    two champions on the same team in 2026 majors, 8+ games together: win rate together (pulled toward what each champion's own
          win rate predicts, k 10) minus that prediction; +0.12 -> +4, +0.08 -> +3, +0.05 -> +2, +0.03 -> +1, -0.03 -> -1, -0.06 -> -2
  style   pairs of subclasses / playstyle tags on the same team: win rate with both (k 50) minus 50%; kept when 150+ team-games and
          the sign is the same before and after 1 Sep (a quick held-out check); +/-1 per combo the team holds, the team total capped at
          +/-2 (measured per team, so applied per team, not per champion pair)
  flavour Riot's related champions (Universe site) +1 "bond"; 3+ champions from one region on a team +2 (the game applies the region set)
Each card carries its Data Dragon id (dd), used only for the optional portrait art in the game.
Matchups (3+ games, same role): only the part specific to the pair. Each champion's usual share of games ahead in gold at 15 is already
in its lane grade, so the matchup is the pair's share pulled toward what the two usual shares predict (k 20), minus that prediction, as
50 +/- points. (A plain ahead-share ran 22-78% and, with the game's lane duel adding (matchup - 50) x 0.5, counted lane strength twice.)
usage (repo root): python -I research/champions/build_clash_cards.py"""
import sys, os, json, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run, atomic_write
DB = config.R / "champions" / "champions.csv"; UNI = config.R / "local" / "champions" / "universe_2026-11-17.json"
OUT_JS, OUT_JSON = config.ROOT / "Draft Game" / "clash-cards.js", config.R / "champions" / "clash_cards.json"
LETTER = {"Fighter": "F", "Mage": "M", "Marksman": "R", "Tank": "T", "Support": "S", "Assassin": "A"}
GR = {"top": "TOP", "jng": "JGL", "mid": "MID", "bot": "BOT", "sup": "SUP"}
GRADES = [(0.97, "S+"), (0.92, "S"), (0.85, "A+"), (0.75, "A"), (0.60, "B+"), (0.40, "B"), (0.22, "C"), (0.08, "D"), (0.0, "F")]
grade = lambda p: next(g for t, g in GRADES if p >= t)
shr = lambda s, n, k, prior=0.0: (s + k * prior) / (n + k)
with Run("clash_cards", inputs=[DB, UNI, config.OE_CSV]) as run:
    D = pd.read_csv(DB).sort_values(["class", "released", "name"]).reset_index(drop=True)
    D["code"] = D["class"].map(LETTER) + (D.groupby("class").cumcount() + 1).astype(str)
    D = D.sort_values("name").reset_index(drop=True); D["key"] = D.name.map(data.key); idx = dict(zip(D.key, D.index))
    U = json.loads(UNI.read_text(encoding="utf-8"))
    assert not U["failed"] and len(U["champions"]) == len(D), f"Universe pull incomplete: {len(U['champions'])} of {len(D)}, failed {list(U['failed'])}"
    o = data.oe(["gameid", "league", "date", "side", "position", "champion", "result", "gamelength", "golddiffat15", "kills", "assists", "teamkills",
                 "damageshare", "dragons", "opp_dragons", "barons", "opp_barons"]); data.check(o)
    o = o[o.league.isin(config.MAJOR)].copy(); P = o[o.position.isin(config.ROLES)].copy(); P["key"] = P.champion.map(data.key); P["i"] = P.key.map(idx)
    assert P.i.notna().all()
    T = o[o.position == "team"].set_index(["gameid", "side"])
    P["kp"] = ((P.kills + P.assists) / P.teamkills.clip(lower=1)).clip(upper=1)
    P["objshare"] = [(lambda t: np.nanmean([t.dragons / max(1, t.dragons + t.opp_dragons), t.barons / max(1, t.barons + t.opp_barons) if t.barons + t.opp_barons else np.nan]))(T.loc[(g, s)])
                     for g, s in zip(P.gameid, P.side)]
    rm = P.groupby("position")[["kp", "damageshare"]].agg(["mean", "std"])
    raw = {k: np.zeros(len(D)) for k in ("lane", "tf", "late", "obj")}; games = np.zeros(len(D), int)
    for i, r in D.iterrows():
        a = P[P.i == i]; m = a[a.position == r.meta_role]; games[i] = len(a)
        raw["lane"][i] = shr(m.golddiffat15.dropna().sum(), m.golddiffat15.notna().sum(), 5)
        z = lambda col: shr(((m[col] - rm.loc[r.meta_role, (col, "mean")]) / rm.loc[r.meta_role, (col, "std")]).dropna().sum(), m[col].notna().sum(), 20) if r.meta_role in rm.index else 0.0
        raw["tf"][i] = np.mean([z("kp"), z("damageshare"), (r.riot_cc - 2) / 0.8])
        lo, hi = a[a.gamelength < 28 * 60], a[a.gamelength >= 33 * 60]
        raw["late"][i] = shr(hi.result.sum(), len(hi), 15, 0.5) - shr(lo.result.sum(), len(lo), 15, 0.5)
        raw["obj"][i] = shr((a.objshare.dropna() - 0.5).sum(), a.objshare.notna().sum(), 15)
    stats, grades = {}, {}
    for k, v in raw.items():
        p = pd.Series(v).rank(pct=True, method="average").values; p = (p - p.min()) / (p.max() - p.min())
        stats[k] = np.round(62 + 30 * p).astype(int); grades[k] = [grade(x) for x in p]
    # pair synergy
    own = {i: shr(a.result.sum(), len(a), 20, 0.5) for i, a in P.groupby("i")}
    team = P.groupby(["gameid", "side"]).agg(ids=("i", lambda s: sorted(int(x) for x in s)), res=("result", "first"), day=("date", "first")).reset_index()
    pc = {}
    for ids, res in zip(team.ids, team.res):
        for a, b in itertools.combinations(ids, 2): n, w = pc.get((a, b), (0, 0)); pc[(a, b)] = (n + 1, w + res)
    pairs = []
    for (a, b), (n, w) in pc.items():
        if n < 8: continue
        exp = (own.get(a, .5) + own.get(b, .5)) / 2; eff = shr(w, n, 10, exp) - exp
        v = 4 if eff >= .12 else 3 if eff >= .08 else 2 if eff >= .05 else 1 if eff >= .03 else -2 if eff <= -.06 else -1 if eff <= -.03 else 0
        if v: pairs.append([a, b, v, n, round(float(eff), 3)])
    # style synergy (subclasses + playstyle tags), quick held-out sign check
    def tags_of(r): return {"sub:" + t for t in str(r.subclasses).split("/") if t and t != "nan"} | {"tag:" + ("AoE" if t.strip().lower() == "aoe" else t.strip()) for t in str(r.playstyle_tags).split("/") if t.strip() and t != "nan"}
    TG = [tags_of(r) for r in D.itertuples()]
    acc = {}
    for ids, res, day in zip(team.ids, team.res, team.day):
        have = sorted(set().union(*[TG[i] for i in ids])); half = 0 if day < config.SPLIT else 1
        for a, b in itertools.combinations(have, 2):
            s = acc.setdefault((a, b), [0, 0, 0, 0]); s[2 * half] += 1; s[2 * half + 1] += res
    style = {}
    for (a, b), (n0, w0, n1, w1) in acc.items():
        n, w = n0 + n1, w0 + w1
        if n < 150 or min(n0, n1) < 40: continue
        e, e0, e1 = shr(w, n, 50, .5) - .5, shr(w0, n0, 50, .5) - .5, shr(w1, n1, 50, .5) - .5
        if abs(e) >= .02 and np.sign(e0) == np.sign(e1) == np.sign(e): style[f"{a}|{b}"] = 1 if e > 0 else -1
    # matchups (lane: ahead at 15 against that opponent, same role)
    opp = P.merge(P[["gameid", "position", "side", "i", "golddiffat15"]], on=["gameid", "position"], suffixes=("", "_o"))
    opp = opp[(opp.side != opp.side_o) & opp.golddiffat15.notna()]
    # only the part specific to the pair: each champion's usual share of games ahead at 15 (in that role) already sits in its lane
    # grade, so the matchup is the pair's share pulled toward what the two usual shares predict, minus that prediction
    opp["ahead"] = (opp.golddiffat15 > 0).astype(float)
    usual = {(i, r): shr(g.ahead.sum(), len(g), 20, .5) for (i, r), g in opp.groupby(["i", "position"])}
    mu = {}
    for (a, b, r), g in opp.groupby(["i", "i_o", "position"]):
        if len(g) < 3 or a >= b: continue
        exp = min(.95, max(.05, .5 + usual[(a, r)] - usual[(b, r)]))
        k_ = f"{int(a)}|{int(b)}"; v = 50 + 100 * (shr(g.ahead.sum(), len(g), 20, exp) - exp)
        if k_ not in mu or len(g) > mu[k_][1]: mu[k_] = (v, len(g))
    mu = {k_: int(round(v)) for k_, (v, n) in mu.items()}
    # flavour
    UC = U["champions"]; pretty = lambda s: (s or "").replace("-", " ").title().replace("Bandle City", "Bandle City")
    bonds = sorted({tuple(sorted((idx[data.key(n)], idx[data.key(m)]))) for n, v in UC.items() for m in v["related"] if m and data.key(m) in idx and m != n})
    cards = []
    for i, r in D.iterrows():
        offs = [x for x in str(r.off_roles).split("/") if x in GR]; riot = [x for x in str(r.riot_lane_roles).split("/") if x in GR and x != r.meta_role]
        flex = (offs + riot + [None])[0]
        cards.append({"code": r.code, "dd": r.api_name, "cls": r["class"], "cls2": r.class_secondary if isinstance(r.class_secondary, str) else "", "sub": r.subclasses,
                      "dmg": r.damage_types, "range": r.range_type, "tags": sorted(t.split(":", 1)[1] for t in TG[i] if t.startswith("tag:")),
                      "role": GR[r.meta_role], "flex": GR[flex] if flex else None, "s": {k: int(stats[k][i]) for k in stats},
                      "g": {k: grades[k][i] for k in grades}, "region": pretty(UC[r["name"]]["faction"]), "games": int(games[i])})
    out = {"version": 1, "built": "research/champions/build_clash_cards.py", "cards": cards, "pairs": pairs, "style": style, "bonds": [list(b) for b in bonds],
           "mu": mu, "region_set": {"size": 3, "bonus": 2}, "pool": 100}
    names = {i: r["name"] for i, r in D.iterrows()}
    key_out = {"code_to_name": {c["code"]: names[i] for i, c in enumerate(cards)}, **out}
    run.result("cards", len(cards)); run.result("pair synergies", len(pairs)); run.result("style synergies", len(style)); run.result("bonds", len(bonds)); run.result("matchups", len(mu))
    run.save_json(OUT_JSON, key_out)
    atomic_write(OUT_JS, "/* Draft Clash cards, built by research/champions/build_clash_cards.py from the champion database (do not hand-edit). */\nwindow.CLASH_CARDS=" + json.dumps(out, separators=(",", ":")) + ";\n")
    jl = [p for p in pairs if {names[p[0]], names[p[1]]} == {"Jinx", "Lulu"}]
    print("matchup range", min(mu.values()), max(mu.values()), "| cards", len(cards), "| pairs", len(pairs), "| style", len(style), "| bonds", len(bonds), "| matchups", len(mu), "| Jinx+Lulu:", jl or "no 8-game record")
    for k in stats: print(k, pd.Series(grades[k]).value_counts().reindex([g for _, g in GRADES]).to_dict())
    for n in ["Jinx", "Lulu", "Ambessa", "Rumble", "Azir", "Aatrox"]:
        i = int(D.index[D.name == n][0]); c = cards[i]; print(n, c["code"], c["role"], c["flex"], c["g"], c["region"], c["games"])
    print("style kept:", sorted(style.items(), key=lambda kv: -kv[1])[:12])
