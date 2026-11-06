"""Sim session 3, step 6 (research only; the app is not changed): the minute-by-minute game-state simulator.

Every event is a random draw from chances fitted to real games (params3.json); nothing is scripted to a result.
The same draft and seed replay the same game; a different seed plays it out differently.

Each minute:
  laning (to 15:00)  each lane's farm lead moves toward a drawn lane result: the fitted expectation for that matchup
                     (v1 strength, lane skills, champion lane values) plus noise drawn jointly for the five lanes
                     (jungle-mid and bot-support move together, as in real games)
  fights             how many start: fitted rate by phase, size of the lead, a dragon/Baron up, a buff up.
                     Size: drawn from real fight sizes by phase. Who gets each kill: fitted on gold lead, v1 strength,
                     Baron and Elder buff, plus a per-fight swing (fights go one way more often than coin flips would)
                     Killer / victim role and assists: drawn from real role shares
  monsters           dragon (5:00, then 5:00 after each take; Elder 6:00 after a soul), grubs 8:00, Herald 15:00,
                     Baron 20:00 (6:00 respawn). Once up, the chance it's taken this minute is fitted on minutes since
                     spawn, size of the lead and a fight this minute; who takes it on side, gold lead, jungle and lane
                     leads (lane priority), kills in the last minute and v1 strength. So timing varies game to game:
                     a team ahead in bot and jungle tends to take dragon early; a won fight can turn into a Baron
  towers             tower segments (5 per tower; the tower falls with its 5th) per lane: fitted on lane lead, team lead,
                     v1, Baron / Elder, Herald, grubs, tier and phase. Then inhibitors, nexus towers and nexus once a
                     lane is open (inhibitors back after 5:00); the game ends when the nexus falls
  gold               each event moves the gold lead by its fitted worth; after laning, a fitted drift, v1 term,
                     catch-up term and noise
Calibration (cal): gain (how strongly v1 strength turns into every event chance, one number), lane_mu / lane_k (lane
farm part, since kills and plates also move gold), fight_eps (per-fight swing). None of these sets a result."""
import json, math
import numpy as np

ROLES = ["top", "jng", "mid", "bot", "sup"]
LANES = ["TOP", "MID", "BOT"]; LANE_ROLES = {"TOP": [0], "MID": [2], "BOT": [3, 4]}
PH = [0, 14, 20, 25, 30, 35]; PHN = ["0-13", "14-19", "20-24", "25-29", "30-34", "35+"]
FPH = lambda m: "0-13" if m < 14 else "14-24" if m < 25 else "25-34" if m < 35 else "35+"
SPAWN = {"dragon": 300, "grub": 480, "herald": 900, "baron": 1200}
BARON_BUFF, ELDER_BUFF, INHIB_BACK = 180, 150, 300
sig = lambda x: 1.0 / (1.0 + math.exp(-x))
DEFAULT_CAL = {"gain": 1.0, "lane_mu": 1.0, "lane_k": 1.0, "fight_eps": 0.0, "max_min": 70, "style_mode": "side"}
# style_mode "side": draft styles as own-minus-enemy (they shift who gets kills, monsters and towers);
#            "timing": both drafts together, so a draft changes when things happen, not who gets them (Luke, 5 Nov)


class Sim:
    def __init__(self, P, cal=None):
        self.P = P; self.cal = dict(DEFAULT_CAL, **(cal or {}))
        self.L15 = np.linalg.cholesky(np.array(P["lane_cov15"]) + np.eye(5))
        d10, d15 = np.diag(P["lane_cov10"]), np.diag(P["lane_cov15"])
        self.A = math.log(float(np.mean(np.sqrt(d10 / d15)))) / math.log(10 / 15)  # lane path shape (t/15)^A
        self.ph = {p: P["fights"].get(f"phase {p}", 0.0) for p in PHN}
        self.seg_ph = {p: P["segments"].get(f"phase {p}", 0.0) for p in PHN}
        self.fsize = {ph: (np.array([int(k) for k in t]), np.array(list(t.values())) / sum(t.values())) for ph, t in P["fight_size_table"].items()}
        ks, ds, ap = P["role_kill_share"], P["role_death_share"], P["role_assist_per_team_kill"]
        self.kw = np.array([ks[r] for r in ROLES]); self.kw /= self.kw.sum()
        self.dw = np.array([ds[r] for r in ROLES]); self.dw /= self.dw.sum()
        self.ap = np.array([min(0.95, ap[r] / max(1e-6, 1 - ks[r])) for r in ROLES])
        self.gs = np.array([P["box"][r]["gold_share"] for r in ROLES]); self.gs /= self.gs.sum()
        sw = P.get("gold_swing_share", {}); self.sw_lane = np.array([sw.get("laning", {}).get(r, self.gs[i]) for i, r in enumerate(ROLES)])
        self.sw_late = np.array([sw.get("after", {}).get(r, self.gs[i]) for i, r in enumerate(ROLES)])
        self.sw_lane /= self.sw_lane.sum(); self.sw_late /= self.sw_late.sum()
        self.spush = {}
        if P.get("segment_push"):
            for k_, d_ in P["segment_push"]["size_dist"].items():
                self.spush[k_] = (np.array([int(z) for z in d_]), np.array(list(d_.values())) / sum(d_.values()))
            for k_ in ("0_early", "0", "1", "2"): self.spush.setdefault(k_, self.spush.get("0", (np.array([1]), np.array([1.0]))))
        # push sizes (real, training), by whether an enemy inhibitor is already down when the push starts
        self.push = {}
        for st, ps_ in P["base_push"].get("size_dist_by_state", {"no_inhib_down": P["base_push"]["size_dist"], "inhib_down": P["base_push"]["size_dist"]}).items():
            self.push[st] = (np.array([int(k) for k in ps_]), np.array(list(ps_.values())) / sum(ps_.values()))
        dt = P["dragon_types"]["first_two_share"]; self.dtypes = list(dt.keys()); self.dprob = np.array(list(dt.values())); self.dprob /= self.dprob.sum()

    def count(self, rng, mu, kind, m):
        """Draw a count with mean mu and the fitted leftover burstiness for this phase (negative binomial; Poisson if none)."""
        phi = self.P.get("dispersion", {}).get(kind, {}).get(PHN[sum(m >= p for p in PH) - 1], 1.0)
        if phi <= 1.01 or mu <= 0: return int(rng.poisson(mu))
        r = mu / (phi - 1); return int(rng.negative_binomial(r, 1 / phi))

    def lane_mean(self, x, z, m):
        out = np.zeros(5)
        for i, r in enumerate(ROLES):
            a, bz, bs, bc = self.P["lanes"][r][str(m)]
            out[i] = a + bz * z + bs * x.get("skill_gap", [0] * 5)[i] + bc * x.get(f"cg{m}", [0] * 5)[i]
        return out

    def run(self, x, seed, log=False):
        """x: {"z": v1 blue log-odds, "skill_gap": [5], "cg15": [5] champion lane gaps (blue - red),
        draft styles: "siege_d", "obj_d", "skirm_d" (blue minus red), "pace_s" (blue plus red)}."""
        P, cal, rng = self.P, self.cal, np.random.default_rng(seed)
        z = x["z"] * cal["gain"]
        siege_d, obj_d, skirm_d, pace_s = x.get("siege_d", 0.0), x.get("obj_d", 0.0), x.get("skirm_d", 0.0), x.get("pace_s", 0.0)
        siege_s, obj_s = x.get("siege_s", 0.0), x.get("obj_s", 0.0)
        TIM = cal["style_mode"] == "timing"
        SPC = P["segment_push"]["coef"] if (P.get("segment_push") and cal.get("seg_mode", "push") == "push") else None
        SEGC = SPC if SPC is not None else (P["segments_timing"] if TIM else P["segments"]); PUSHC = P["base_push_timing"] if TIM else P["base_push"]["coef"]
        KSC = P["kill_side_timing"] if TIM else P["kill_side"]; TAKC = P["taker_timing"] if TIM else P["taker"]
        FB = P["gold_feedback"]
        if cal.get("seg_lane_tier", "off") == "on" and P.get("segment_push_lane_tier"):  # opt-in (6 Nov test): lane x tier push terms
            SPC = dict(P["segment_push_lane_tier"]["coef"]); SEGC = SPC
        if cal.get("within", "off") == "on" and P.get("segment_push_within"):  # opt-in (6 Nov test): lead effects fitted within games
            SPC = P["segment_push_within"]["coef"]; SEGC = SPC; PUSHC = P["base_push_within"]["coef"]; TAKC = P["taker_within"]; FB = P["gold_feedback_within"]
        # game form: the pooled gold-lead effect on who wins fights partly reflects "this team is stronger in this game";
        # fitted within games instead (0.048 v 0.125 per 1k), with a once-per-game form draw (spread measured on training games)
        form = 0.0
        if P.get("kill_side_within") and cal.get("form", "off") == "within":  # opt-in; tested 5 Nov and not kept (report 7d)
            KSC = dict(P["kill_side_within"]["coef"], per_v1_logit=KSC["per_v1_logit"]); form = rng.normal(0, P["kill_side_within"]["game_form_sd"])
        lane_end = cal["lane_mu"] * self.lane_mean(x, z, 15) + math.sqrt(cal["lane_k"]) * (self.L15 @ rng.standard_normal(5))
        farm = np.zeros(5); gold = np.zeros(5)                 # per role, blue minus red: farm part and everything else
        K = np.zeros((2, 5), int); D = np.zeros((2, 5), int); A = np.zeros((2, 5), int); SOLO = np.zeros((2, 5), int)
        seg = [[0, 0, 0], [0, 0, 0]]                           # segments side s has taken in each enemy lane (15 = lane open)
        prevseg = [[0, 0, 0], [0, 0, 0]]                       # segments taken in that lane last minute (a push already rolling)
        inhib_back = [[-1, -1, -1], [-1, -1, -1]]             # when side s's enemy inhibitor in each lane comes back (-1 = up)
        open_t = [[None] * 3, [None] * 3]; last_base = [-1e9, -1e9]                      # minute each enemy lane opened (inhibitor turret down)
        nx_towers = [2, 2]; drag = [[], []]; soul = [None, None]; elder_n = [0, 0]; barons = [0, 0]; grubs = [0, 0]; heralds = [0, 0]
        towers = [0, 0]; inhibs = [0, 0]; first = {}; ftime = {}
        baron_until = [-1, -1]; elder_until = [-1, -1]; herald_t = [-1e9, -1e9]
        nxt = {"dragon": SPAWN["dragon"], "grub": SPAWN["grub"], "herald": SPAWN["herald"], "baron": SPAWN["baron"]}
        taken_once = {"grub": False, "herald": False}
        elder_mode = False; soul_type = None; drag_seq = []
        steps = []; gd_at = {}; kill_log = []; winner = None; t_end = None
        val = P["gold"]
        def add_gold(side, amount, roles=None):
            # every event's gold lands on the roles the way real team gold swings do (fitted shares, laning v after 15:00);
            # `roles` is kept for the play-by-play only
            sgn = 1 if side == 0 else -1
            gold[:] += sgn * amount * (self.sw_lane if m < 15 else self.sw_late)
        def note(t, side, kind, text):
            if log: steps.append({"t": int(t), "side": ["blue", "red"][side] if side is not None else "", "kind": kind, "text": text})

        for m in range(0, cal["max_min"] + 1):
            t0 = 60 * m
            # state at the start of the minute (what the fits used: gold lead at minute m), then this minute's gold drift
            lane_lead = lambda s, L: (1 if s == 0 else -1) * (farm[LANE_ROLES[L]].sum() + gold[LANE_ROLES[L]].sum())
            gd = farm.sum() + gold.sum(); gd_at[m] = gd
            if m in (5, 10, 15): gd_at[f"roles{m}"] = (farm + gold).copy()
            role_lead = farm + gold
            # --- laning / gold drift ---
            if m < 15:
                f0, f1 = (m / 15) ** self.A, ((m + 1) / 15) ** self.A
                farm += lane_end * (f1 - f0)
            else:
                fb = FB
                d = val["drift"] + val["per_v1_logit_per_min"] * z + fb["per_1k_lead"] * gd / 1000 + (fb["extra_per_1k_after_20"] * gd / 1000 if m >= 20 else 0)
                d += rng.normal(0, P["gold_noise_sd"]) * cal.get("gold_noise_k", 1.0)
                gold += d * self.sw_late
            bdir = (1 if baron_until[0] > t0 else 0) - (1 if baron_until[1] > t0 else 0)
            edir = (1 if elder_until[0] > t0 else 0) - (1 if elder_until[1] > t0 else 0)
            mon_up = any(nxt[k] is not None and nxt[k] <= t0 for k in ("dragon", "baron"))
            # --- fights ---
            fc = P["fights"]
            lam = math.exp(fc["intercept"] + self.ph[PHN[sum(m >= p for p in PH) - 1]] + fc["per_1k_abs_lead"] * min(abs(gd) / 1000, 15)
                           + fc["monster_up"] * mon_up + fc["buff_up"] * (bdir != 0 or edir != 0) + fc.get("pace_style", 0.0) * pace_s)
            nf = self.count(rng, lam, "fights", m); net = 0; fought = nf > 0
            for _ in range(nf):
                sizes, pr = self.fsize[FPH(m)]; n = int(rng.choice(sizes, p=pr))
                ks = KSC
                zk = cal.get("kill_z_phase", {}).get("0-13" if m < 14 else "14-24" if m < 25 else "25+", 1.0)  # opt-in (6 Nov test): strength in kills by phase
                p = sig(ks["intercept"] + ks["per_1k_gold_lead"] * gd / 1000 + ks["per_v1_logit"] * z * zk + ks["baron"] * bdir + ks["elder"] * edir + form
                        + ks.get("skirmish_style_early", 0.0) * skirm_d * (m < 15)
                        + rng.normal(0, cal.get("fight_eps_phase", {}).get("0-13" if m < 14 else "14-24" if m < 25 else "25+", cal["fight_eps"])))
                tf = t0 + rng.uniform(0, 55); dead = [set(), set()]
                for j in range(n):
                    s = 0 if rng.random() < p else 1; o = 1 - s
                    alive_v = [i for i in range(5) if i not in dead[o]]
                    if not alive_v: continue
                    wv = self.dw[alive_v] / self.dw[alive_v].sum(); v = int(rng.choice(alive_v, p=wv)); dead[o].add(v)
                    alive_k = [i for i in range(5) if i not in dead[s]] or list(range(5))
                    wk = self.kw[alive_k] / self.kw[alive_k].sum(); k = int(rng.choice(alive_k, p=wk))
                    ast = [i for i in range(5) if i != k and i not in dead[s] and rng.random() < self.ap[i]]
                    K[s, k] += 1; D[o, v] += 1
                    for i in ast: A[s, i] += 1
                    if not ast: SOLO[s, k] += 1
                    add_gold(s, val["kill"], [k] * 2 + ast)
                    net += 1 if s == 0 else -1
                    first.setdefault("blood", s)
                    tk = tf + 3 * j; kill_log.append((tk, s, k, v))
                    note(tk, s, "kill", f"{ROLES[k]} kills {ROLES[v]}" + ("" if ast else " (solo)"))
            # --- monsters ---
            def taker(kind, feats):
                c = TAKC.get(kind) or TAKC["dragon"]  # fallback only when a fit had too few training takes
                xb = c["blue_side"] + c["per_v1_logit"] * z
                for f in feats: xb += c.get(f + "_per_1k", 0.0) * feats[f] / 1000
                return 0 if rng.random() < sig(xb) else 1
            first_drag = not drag_seq and not elder_mode  # the game's first dragon: fitted on its own (later, more to red side)
            def take_chance(kind):
                c = P["monsters"][kind]; since = max(0, (t0 - nxt[kind if kind != "elder" else "dragon"]) // 60)
                return sig(c["intercept"] + c["spawn_minute"] * (since == 0) + c["1_min_after"] * (since == 1) + c["4+_min_after"] * (since >= 4)
                           + c["per_1k_abs_lead"] * min(abs(gd) / 1000, 15) + c["fight_this_minute"] * fought
                           + c.get("first_dragon", 0.0) * (kind == "dragon" and first_drag) + c.get("objectives_style_sum", 0.0) * obj_s)
            lanef = {"gd": gd, "jng": role_lead[1], "mid": role_lead[2], "top": role_lead[0], "bot2": role_lead[3] + role_lead[4], "net60k": net * 1000,
                     "objk": obj_d * 1000, "first1k": 1000 * first_drag}
            if nxt["dragon"] is not None and nxt["dragon"] < t0 + 60:
                kind = "elder" if elder_mode else "dragon"
                if rng.random() < take_chance(kind if kind in P["monsters"] else "dragon"):
                    feats = {k: lanef[k] for k in (["gd", "jng", "bot2", "mid", "net60k", "objk", "first1k"] if kind == "dragon" else ["gd", "net60k", "objk"])}
                    s = taker(kind if kind in P["taker"] else "dragon", feats)
                    tt = max(t0, nxt["dragon"]) + rng.uniform(0, 50)
                    if kind == "elder":
                        elder_n[s] += 1; elder_until[s] = tt + ELDER_BUFF; nxt["dragon"] = tt + 360
                        first.setdefault("elder", s); note(tt, s, "elder", "Elder Dragon")
                    else:
                        if len(drag_seq) < 2:
                            opts = [i for i, ty in enumerate(self.dtypes) if ty not in drag_seq]
                            pp = self.dprob[opts] / self.dprob[opts].sum(); ty = self.dtypes[int(rng.choice(opts, p=pp))]
                        else:
                            if soul_type is None:
                                opts = list(range(len(self.dtypes))); ty = self.dtypes[int(rng.choice(opts, p=self.dprob))]; soul_type = ty
                            ty = soul_type
                        drag_seq.append(ty); drag[s].append(ty); add_gold(s, val["dragon_n"])
                        first.setdefault("dragon", s); ftime.setdefault("dragon", tt); note(tt, s, "dragon", f"{ty} dragon")
                        if len(drag[s]) >= 4 and not elder_mode:
                            soul[s] = ty; elder_mode = True; note(tt, s, "soul", f"{ty} soul")
                        nxt["dragon"] = tt + (360 if elder_mode else 300)
            for kind in ("grub", "herald"):
                if not taken_once[kind] and nxt[kind] < t0 + 60 and kind in P["monsters"]:
                    if rng.random() < take_chance(kind):
                        s = taker(kind, {k: lanef[k] for k in ["gd", "jng", "top", "mid", "net60k", "objk"]})
                        tt = max(t0, nxt[kind]) + rng.uniform(0, 50); taken_once[kind] = True
                        if kind == "grub":
                            n_own = 3 if rng.random() < P["grubs_split"]["one_team_all"] else 2
                            grubs[s] += n_own; grubs[1 - s] += 3 - n_own; first.setdefault("grub", s); add_gold(s, val["grub"] * n_own); add_gold(1 - s, val["grub"] * (3 - n_own))
                            note(tt, s, "grubs", f"{n_own} void grubs")
                        else:
                            heralds[s] += 1; herald_t[s] = tt; first.setdefault("herald", s); add_gold(s, val["herald"]); note(tt, s, "herald", "Rift Herald")
            if nxt["baron"] is not None and nxt["baron"] < t0 + 60:
                if rng.random() < take_chance("baron"):
                    s = taker("baron", {k: lanef[k] for k in ["gd", "net60k", "objk"]})
                    tt = max(t0, nxt["baron"]) + rng.uniform(0, 50)
                    barons[s] += 1; baron_until[s] = tt + BARON_BUFF; nxt["baron"] = tt + 360; add_gold(s, val["baron"])
                    first.setdefault("baron", s); ftime.setdefault("baron", tt); note(tt, s, "baron", "Baron Nashor")
            # --- towers: segments lane by lane, then base ---
            sc = SEGC
            for s in (0, 1):
                sg = 1 if s == 0 else -1; o = 1 - s
                for li, L in enumerate(LANES):
                    if seg[s][li] >= 15: continue
                    tier = seg[s][li] // 5
                    xb = (sc["intercept"] + self.seg_ph[PHN[sum(m >= p for p in PH) - 1]] + sc["tier T2"] * (tier == 1) + sc["tier T3"] * (tier == 2)
                          + sc["mid"] * (L == "MID") + sc["bot"] * (L == "BOT") + sc["per_1k_lane_lead"] * max(-8, min(8, lane_lead(s, L) / 1000))
                          + sc["per_1k_team_lead"] * max(-15, min(15, sg * gd / 1000)) + sc["per_v1_logit"] * sg * z
                          + sc["baron"] * (baron_until[s] > t0) + sc["elder"] * (elder_until[s] > t0)
                          + sc["herald_last_3min"] * (t0 - herald_t[s] < 180) + sc["own_grubs"] * grubs[s] + sc.get("siege_style", 0.0) * sg * siege_d + sc.get("siege_style_sum", 0.0) * siege_s
                          + sc.get("net_kills_this_minute", 0.0) * max(-5, min(5, sg * net))
                          + sc.get("T2 x mid", 0.0) * (tier == 1 and L == "MID") + sc.get("T2 x bot", 0.0) * (tier == 1 and L == "BOT")
                          + sc.get("T3 x mid", 0.0) * (tier == 2 and L == "MID") + sc.get("T3 x bot", 0.0) * (tier == 2 and L == "BOT")
                          + sc.get("lane_segments_last_minute", 0.0) * min(5, prevseg[s][li]) + sc.get("T3_x_baron", 0.0) * (tier == 2) * (baron_until[s] > t0))
                    if SPC is not None:  # tower pushes: a push starts with the fitted chance, its size drawn from real pushes
                        n = 0
                        if rng.random() < sig(xb):
                            sz, pz = self.spush["0_early" if tier == 0 and m < 14 else str(tier)]; n = int(rng.choice(sz, p=pz))
                    else:
                        n = self.count(rng, math.exp(xb), "segments", m)
                    n = min(n, 15 - seg[s][li]); prevseg[s][li] = n
                    for _ in range(n):
                        seg[s][li] += 1
                        add_gold(s, val["plate_early"] if m < 14 else val["plate"], LANE_ROLES[L])
                        if seg[s][li] % 5 == 0:
                            towers[s] += 1; add_gold(s, val["tower"], LANE_ROLES[L]); first.setdefault("tower", s); ftime.setdefault("tower", t0 + 30)
                            note(t0 + rng.uniform(0, 59), s, "tower", f"T{seg[s][li] // 5} {L}")
                opn = [li for li in range(3) if seg[s][li] >= 15]
                for li in opn:
                    if open_t[s][li] is None: open_t[s][li] = t0
                if not opn: continue
                down = [li for li in range(3) if inhib_back[s][li] > t0]
                bc = PUSHC  # a push: the chance of any base take this minute, then how many (real push sizes)
                xb = (bc["intercept"] + bc["from 25"] * (m >= 25) + bc["from 35"] * (m >= 35) + bc["per_1k_lead"] * max(-15, min(15, sg * gd / 1000))
                      + bc["per_v1_logit"] * sg * z + bc["baron"] * (baron_until[s] > t0) + bc["elder"] * (elder_until[s] > t0)
                      + bc["enemy_inhibs_down"] * len(down) + bc["open_lanes"] * len(opn) + bc.get("siege_style", 0.0) * sg * siege_d + bc.get("siege_style_sum", 0.0) * siege_s
                      + bc.get("lane_just_opened", 0.0) * any(open_t[s][li] >= t0 - 60 for li in opn)
                      + bc.get("base_take_last_minute", 0.0) * (last_base[s] >= t0 - 60)
                      + bc.get("net_kills_this_minute", 0.0) * max(-5, min(5, sg * net)))
                sz, pr_ = self.push["inhib_down" if down else "no_inhib_down"]
                npush = int(rng.choice(sz, p=pr_)) if rng.random() < sig(xb) else 0
                if npush: last_base[s] = t0
                for _ in range(npush):
                    down = [li for li in range(3) if inhib_back[s][li] > t0]
                    up_inh = [li for li in opn if inhib_back[s][li] <= t0]
                    tt = t0 + rng.uniform(0, 59)
                    if down and (not up_inh or rng.random() < P["nexus_tier_share"]):
                        if nx_towers[s] > 0:
                            nx_towers[s] -= 1; towers[s] += 1; add_gold(s, val["tower"]); note(tt, s, "tower", "nexus tower")
                        else:
                            winner, t_end = s, tt; note(tt, s, "nexus", "Nexus"); break
                    elif up_inh:
                        li = int(rng.choice(up_inh)); inhib_back[s][li] = tt + INHIB_BACK; inhibs[s] += 1; add_gold(s, val["inhib"])
                        note(tt, s, "inhib", f"inhibitor {LANES[li]}")
                if winner is not None: break
            if winner is not None: break
        if winner is None:  # time cap (counted in the tests)
            winner, t_end = (0 if gd >= 0 else 1), 60 * cal["max_min"]; capped = True
        else: capped = False
        sec = int(t_end); mins = sec / 60
        tk = K.sum(axis=1)
        ps = {}
        for s, side in enumerate(["blue", "red"]):
            sg = 1 if s == 0 else -1; ps[side] = {}
            kp = np.array([(K[s, i] + A[s, i]) / max(1, tk[s]) for i in range(5)])
            dm = np.array([self.P["box"][r]["dmg_mean"] + self.P["box"][r]["dmg_per_kp"] * (kp[i] - self.P["box"][r]["kp_mean"])
                           + rng.normal(0, self.P["box"][r]["dmg_sd_resid"]) for i, r in enumerate(ROLES)]).clip(0.02)
            dm /= dm.sum()
            r15 = gd_at.get("roles15", farm + gold)
            for i, r in enumerate(ROLES):
                b = self.P["box"][r]
                ps[side][r] = {"k": int(K[s, i]), "d": int(D[s, i]), "a": int(A[s, i]), "kp": round(float(kp[i]), 3), "dmgS": round(float(dm[i]), 3),
                               "csd": int(round(sg * b["cs_per_1k_gold_15"] * r15[i] / 1000)), "vis": int(max(0, rng.normal(b["vspm_mean"], b["vspm_sd"])) * mins),
                               "solo": int(SOLO[s, i])}
        return {"winner": ["blue", "red"][winner], "sec": sec, "kills": [int(tk[0]), int(tk[1])], "ps": ps,
                "dr": drag, "soul": soul, "elders": elder_n, "ba": barons, "grubs": grubs, "heralds": heralds, "towers": towers, "inhibs": inhibs,
                "first": {k: ["blue", "red"][v] for k, v in first.items()}, "first_t": {k: int(v) for k, v in ftime.items()},
                "roles5": [float(v) for v in gd_at.get("roles5", np.full(5, np.nan))],
                "g15": float(gd_at.get(15, np.nan)), "gd": {k: float(v) for k, v in gd_at.items() if isinstance(k, int)},
                "roles15": [float(v) for v in gd_at.get("roles15", np.full(5, np.nan))], "roles10": [float(v) for v in gd_at.get("roles10", np.full(5, np.nan))],
                "capped": capped, "steps": sorted(steps, key=lambda e: e["t"]) if log else []}


if __name__ == "__main__":
    import sys
    P = json.load(open(sys.argv[1]))
    sim = Sim(P)
    g = sim.run({"z": 0.4}, seed=1, log=True)
    print(g["winner"], g["sec"] // 60, g["kills"], g["towers"], g["dr"], g["ba"])
    for e in g["steps"][:40]: print(f'{e["t"] // 60:2d}:{e["t"] % 60:02d} {e["side"]:4s} {e["text"]}')
    g2 = sim.run({"z": 0.4}, seed=1); print("same seed same game:", g2["winner"] == g["winner"] and g2["sec"] == g["sec"] and g2["kills"] == g["kills"])
