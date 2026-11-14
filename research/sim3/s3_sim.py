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
import json, math, itertools
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
        # pushes follow dead players (opt-in, 14 Nov; research/sim4/s4_deadpush.py): size tables by enemies dead, real gaps and delays
        tab_ = lambda d_: (np.array([int(z_) for z_ in d_]), np.array(list(d_.values())) / sum(d_.values()))
        self.dp = None
        if P.get("dead_push"):
            dp_ = P["dead_push"]; self.dp = {"seg": {k_: tab_(v_) for k_, v_ in dp_["segment_size"].items()}, "base": {k_: tab_(v_) for k_, v_ in dp_["base_size"].items()},
                                             "gap": tab_(dp_["gap"]), "delay": tab_(dp_["delay"])}
        self.push_k = {k_: (np.array([int(z_) for z_ in d_["size"]]), np.array(list(d_["size"].values())) / sum(d_["size"].values()))
                       for k_, d_ in P["base_push_kills"]["size"].items()} if P.get("base_push_kills") else {}
        # lane-level play (opt-in, 12 Nov; fits from s3_lanelevel.py): each role's lead at 15 is the fitted lane model at full
        # strength with the real leftover spread, and early kills lean toward the roles winning their lane
        self.LL = None
        if P.get("lane_level"):
            ll = P["lane_level"]; kr = ll["kill_role"]; lk = "lean_per_1k_expected_lead" if "event_gold" in ll else "lean_per_1k_own_lead"
            self.LL = {"chol": np.linalg.cholesky(np.array(ll["cov15"]) + np.eye(5)), "z": np.array([ll["coef"][r]["z"] for r in ROLES]),
                       "ak": np.array(kr["killer"]["role_intercepts"]), "bk": kr["killer"][lk],
                       "av": np.array(kr["victim"]["role_intercepts"]), "bv": kr["victim"][lk], "ev": None}
            if "event_gold" in ll:  # second version: early kills, deaths, assists and plates move the role's gold by their fitted worth
                # plates: version 3 fits (12 Nov) carry a value for a plate in the role's own lane and one for another lane, paid before
                # 15:00; version 2 fits carry one small "team_plate" value, paid before 14:00 (kept so its runs replay)
                eg = ll["event_gold"]; pk = ("own_lane_plate", "other_lane_plate") if "own_lane_plate" in eg["top"] else ("team_plate",)
                self.LL["ev"] = {k: np.array([eg[r][k] for r in ROLES]) for k in ("own_kill", "own_death", "own_assist") + pk}
                self.LL["z_pre"] = np.array([ll["coef_pregame"][r]["z"] for r in ROLES])
        dt = P["dragon_types"]["first_two_share"]; self.dtypes = list(dt.keys()); self.dprob = np.array(list(dt.values())); self.dprob /= self.dprob.sum()
        # fight players (opt-in, 13 Nov; research/sim4/s4_participants.py): every (side A set, side B set) pair's chance per window x kills group
        self.FP = None
        if P.get("fight_players"):
            fp = P["fight_players"]["players"]; subs = [frozenset(c) for n_ in range(1, 6) for c in itertools.combinations(range(5), n_)]
            WN_ = ["0-4", "5-9", "10-14", "15-24", "25+"]; NBN_ = ["1", "2", "3+"]; probs = []
            pairs = list(itertools.combinations(range(5), 2))
            LWN_ = ["0-4", "5-9", "10-14", "15+"]
            WITH = {lw: np.array([sum(fp["same_side_pair"][lw][f"{ROLES[i]}+{ROLES[j]}"] for i, j in pairs if i in s_ and j in s_) for s_ in subs]) for lw in LWN_}
            CROSS = {lw: np.array([[sum(fp["across"][lw][f"{ROLES[i]}~{ROLES[j]}"] for i in a_ for j in b_) for b_ in subs] for a_ in subs]) for lw in LWN_}
            for wi_, w_ in enumerate(WN_):
                within, cross = WITH[LWN_[min(wi_, 3)]], CROSS[LWN_[min(wi_, 3)]]
                for nb_ in NBN_:
                    ra = fp["role_A"][f"{w_}|{nb_}"]; rb = fp["role_B"][f"{w_}|{nb_}"]
                    ua = np.array([sum(ra[ROLES[i]] for i in s_) for s_ in subs]) + within; ub = np.array([sum(rb[ROLES[i]] for i in s_) for s_ in subs]) + within
                    u = (ua[:, None] + ub[None, :] + cross).reshape(-1); pz = np.exp(u - u.max()); probs.append(pz / pz.sum())
            self.FP = {"subs": [sorted(x) for x in subs], "probs": probs, "WN": WN_, "k": P["fight_players"]["killer"], "v": P["fight_players"]["victim"], "a": P["fight_players"]["assist"]}

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
        if cal.get("seg_lane_tier", "on") == "on" and P.get("segment_push_lane_tier"):  # default from 11 Nov (Luke, 7 Nov: keep; tested 6 Nov, 7f): lane x tier push terms; "off" = the earlier sim
            SPC = dict(P["segment_push_lane_tier"]["coef"]); SEGC = SPC
        cutS = cutB = 99
        if cal.get("push_fight", "off") == "on" and P.get("segment_push_fight"):  # opt-in (10 Nov, 7g): won fights turn into towers and base pushes
            SPC = dict(P["segment_push_fight"]["coef"]); SEGC = SPC; PUSHC = P["base_push_fight"]["coef"]
            cutS = P["segment_push_fight"].get("clear_fight_cutoff") or 99; cutB = P["base_push_fight"].get("clear_fight_cutoff") or 99  # fitted cutoffs (training games)
        if cal.get("push_fight", "off") == "simple" and P.get("segment_push_fight_simple"):  # opt-in (11 Nov): last minute's kills edge only, no flag
            SPC = dict(P["segment_push_fight_simple"]["coef"]); SEGC = SPC; PUSHC = P["base_push_fight_simple"]["coef"]
        ENDS = P["endings"] if (cal.get("endings", "off") == "on" and P.get("endings")) else None  # opt-in (12 Nov): endings follow won fights
        if ENDS is not None: PUSHC = ENDS["start"]["coef"]
        if cal.get("within", "off") == "on" and P.get("segment_push_within"):  # opt-in (6 Nov test): lead effects fitted within games
            SPC = P["segment_push_within"]["coef"]; SEGC = SPC; PUSHC = P["base_push_within"]["coef"]; TAKC = P["taker_within"]; FB = P["gold_feedback_within"]
        # game form: the pooled gold-lead effect on who wins fights partly reflects "this team is stronger in this game";
        # fitted within games instead (0.048 v 0.125 per 1k), with a once-per-game form draw (spread measured on training games)
        form = 0.0
        if P.get("kill_side_within") and cal.get("form", "off") == "within":  # opt-in; tested 5 Nov and not kept (report 7d)
            KSC = dict(P["kill_side_within"]["coef"], per_v1_logit=KSC["per_v1_logit"]); form = rng.normal(0, P["kill_side_within"]["game_form_sd"])
        LL = self.LL if (cal.get("lane_level", "off") == "on" and self.LL is not None and "ll_m0" in x) else None
        if LL is not None:  # x["ll_m0"]: the fitted lead per role without the z term (v1's own log-odds, not scaled by gain)
            lane_end = np.array(x["ll_m0"], float) + LL["z"] * x["z"] + LL["chol"] @ rng.standard_normal(5)
            # what the kill lean reads: first version the lane's drawn result; second version the lead expected before the game
            lean = lane_end if LL["ev"] is None else np.array(x["ll_e0"], float) + LL["z_pre"] * x["z"]
        else:
            lane_end = cal["lane_mu"] * self.lane_mean(x, z, 15) + math.sqrt(cal["lane_k"]) * (self.L15 @ rng.standard_normal(5))
        # lane-aware early kills (opt-in, 13 Nov; research/sim4/s4_earlykills.py): before 15:00 killer and victim are drawn as a pair
        # (lanes, lean on expected leads, who is already in the fight), then assists; fight counts, types and sizes get early-window terms
        # cal["early_kills"]: "on" = both parts; "pairs" = only the kill pairs and assists; "counts" = only the early fight counts, types and sizes;
        # "pairs_flat" = only the kill pairs, with the sim's usual flat assist rates; "on_flat" = kill pairs (flat assists) + early counts (13 Nov tests)
        EKM = cal.get("early_kills", "off"); EK = EKM in ("on", "pairs", "pairs_flat", "on_flat") and bool(P.get("early_kills")); EKC = EKM in ("on", "counts", "on_flat")
        EKP = P["early_kills"]["pair"] if EK else None; EKA = P["early_kills"]["assist"] if EK else None
        EWN = ["0-4", "5-9", "10-14"]; LANEID = [0, -1, 1, 2, 2]; e_lead = lean if (LL is not None and LL["ev"] is not None) else None
        # events keep their order (opt-in, 13 Nov): each event happens no earlier than the one before it, so a minute's events keep the
        # order the sim plays them and nothing comes after the Nexus. Same random draws; only the times (and what they feed) move.
        EO = cal.get("event_order", "off") == "on"; cur = [0.0]
        FPon = cal.get("fight_players", "off") == "on" and self.FP is not None  # who is in each fight (13 Nov): kills and assists only among them
        # the game's first dragon has its own fitted taker (opt-in, 13 Nov; research/sim4/s4_firstdragon.py): lane leads incl. bot duo and top
        # base pushes follow kills (opt-in, 14 Nov; research/sim4/s4_basepush.py): cal["push_kills"] = "size" draws a push's size from real
        # pushes by enemy inhibitor down x the side's own kills in the start minute (0 / 1-2 / 3+); "on" also uses the start model with own and
        # enemy kills this and last minute counted separately. Same random draws in the same order as the default; only the tables change.
        PK = cal.get("push_kills", "off") if P.get("base_push_kills") else "off"
        # death timers (opt-in, 14 Nov; research/sim4/s4_deathtimer.py, League wiki + Riot patch notes): a dead player is out of every fight
        # (can't kill, assist or die) until respawning; the wait follows the role's level (real XP curve) and the game time
        DT = P.get("death_timer") if cal.get("death_timers", "off") == "on" else None
        respawn = [[-1.0] * 5, [-1.0] * 5]
        # pushes follow dead players (opt-in, 14 Nov, needs death timers): the most enemy / own players dead at once this minute feed the tower and
        # base push chances (refitted with those inputs) and how far a push runs; structures fall after the fight that killed the defenders,
        # each one a real gap after the last (part C)
        DP = P.get("dead_push") if (cal.get("dead_push", "off") == "on" and DT is not None and self.dp is not None) else None
        dead_iv = [[], []]
        DSH = P.get("dmg_share") if cal.get("dmg_effects", "off") == "on" else None
        if DP is not None: SPC = dict(DP["segment"]); SEGC = SPC; PUSHC = DP["base"]
        def max_dead(iv, a, b):
            pts = sorted([(max(s_, a), 1) for s_, e_ in iv if s_ < b and e_ > a] + [(min(e_, b), -1) for s_, e_ in iv if s_ < b and e_ > a], key=lambda q: (q[0], q[1]))
            cur_ = best = 0
            for _, d_ in pts: cur_ += d_; best = max(best, cur_)
            return best
        dgrp = lambda n_: "0" if n_ == 0 else "1-2" if n_ <= 2 else "3+"
        def death_wait(role_i, t):
            c = DT["role_xp"][ROLES[role_i]]
            xp = float(np.interp(t, [0, 600, 900, 1200, 1500], [0, *c])) if t <= 1500 else min(DT["xp_levels"][-1], c[3] + (c[3] - c[2]) / 300 * (t - 1500))
            lv = int(np.searchsorted(DT["xp_levels"], xp, side="right")); tf_ = DT["time_factor"]; f = 0.0; prev = tf_["start_s"]
            for end, per in tf_["per_step"]:
                if t > prev: f += per * (min(t, end) - prev) // tf_["step_s"]
                prev = end
            return DT["base_wait"][min(17, lv - 1)] * (1 + min(tf_["cap"], f))
        FDT = (P["taker_first_dragon"]["timing" if TIM else "side"]) if (cal.get("first_dragon_taker", "off") == "on" and P.get("taker_first_dragon")) else None
        def at(d_):
            if not EO: return d_
            cur[0] = max(cur[0], d_); return cur[0]
        farm = np.zeros(5); gold = np.zeros(5)                 # per role, blue minus red: farm part and everything else
        K = np.zeros((2, 5), int); D = np.zeros((2, 5), int); A = np.zeros((2, 5), int); SOLO = np.zeros((2, 5), int)
        seg = [[0, 0, 0], [0, 0, 0]]                           # segments side s has taken in each enemy lane (15 = lane open)
        prevseg = [[0, 0, 0], [0, 0, 0]]                       # segments taken in that lane last minute (a push already rolling)
        inhib_back = [[-1, -1, -1], [-1, -1, -1]]             # when side s's enemy inhibitor in each lane comes back (-1 = up)
        open_t = [[None] * 3, [None] * 3]; last_base = [-1e9, -1e9]                      # minute each enemy lane opened (inhibitor turret down)
        nx_towers = [2, 2]; drag = [[], []]; soul = [None, None]; elder_n = [0, 0]; barons = [0, 0]; grubs = [0, 0]; heralds = [0, 0]
        towers = [0, 0]; inhibs = [0, 0]; first = {}; ftime = {}; first_lane = {}
        baron_until = [-1, -1]; elder_until = [-1, -1]; herald_t = [-1e9, -1e9]
        nxt = {"dragon": SPAWN["dragon"], "grub": SPAWN["grub"], "herald": SPAWN["herald"], "baron": SPAWN["baron"]}
        taken_once = {"grub": False, "herald": False}
        elder_mode = False; soul_type = None; drag_seq = []
        steps = []; gd_at = {}; kill_log = []; winner = None; t_end = None; prev_nf = 0; net = 0; prev_net = 0; kc = [0, 0]; prev_kc = [0, 0]
        val = P["gold"]
        def add_gold(side, amount, roles=None):
            # every event's gold lands on the roles the way real team gold swings do (fitted shares, laning v after 15:00);
            # `roles` is kept for the play-by-play only
            if LL is not None and m < 15: return  # the lane leads to 15:00 already hold this gold (they were fitted to real leads)
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
            if m == 15: gd_at["kd15"] = (K[0] - D[0]) - (K[1] - D[1])  # each role's kills minus deaths by 15:00, blue minus red (for the lane checks)
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
                           + fc["monster_up"] * mon_up + fc["buff_up"] * (bdir != 0 or edir != 0) + fc.get("pace_style", 0.0) * pace_s
                           + fc.get("minutes_before_14", 0.0) * (min(m, 14) - 14))
            TYPED = cal.get("fight_model") == "typed" and P.get("fight_typed")  # opt-in (10 Nov, report 7g): fight types, held in check
            ew = 0 if m < 5 else 1 if m < 10 else 2
            ew_term = lambda c_: (c_.get("early 0-4", 0.0) * (m < 5) + c_.get("early 5-9", 0.0) * (5 <= m < 10)) if (EKC and TYPED) else 0.0
            if TYPED:
                FTc = P["fight_typed"]; cc = FTc["count_early"]["coef"] if (EKC and FTc.get("count_early")) else FTc["count"]["coef"]; ph_i = PHN[sum(m >= p for p in PH) - 1]
                k2 = sum(1 for e_ in kill_log if t0 - 120 <= e_[0] < t0); fprev = 1 if prev_nf > 0 else 0
                feat = {"per_1k_abs_lead": min(abs(gd) / 1000, 15), "monster_up": mon_up, "buff_up": (bdir != 0 or edir != 0)}
                lam = math.exp(cc["intercept"] + cc.get(f"phase {ph_i}", 0.0) + sum(cc[k_] * v_ for k_, v_ in feat.items())
                               + cc["pace_style"] * pace_s + cc["fight_last_minute"] * fprev + cc["log1p_kills_last_2min"] * math.log1p(k2) + ew_term(cc))
            nf = int(rng.poisson(lam)) if TYPED else self.count(rng, lam, "fights", m); prev_net = net; net = 0; fought = nf > 0; prev_nf = nf; prev_kc = kc; kc = [0, 0]
            for _ in range(nf):
                if TYPED:
                    TC = FTc["type_early"]["coef"] if (EKC and FTc.get("type_early")) else FTc["type"]["coef"]
                    zt = [0.0] + [tc["intercept"] + tc.get(f"phase {ph_i}", 0.0) + sum(tc[k_] * v_ for k_, v_ in feat.items()) + tc["log1p_kills_last_2min"] * math.log1p(k2) + ew_term(tc)
                                  for tc in (TC["skirmish"], TC["teamfight"])]
                    pt = np.exp(np.array(zt) - max(zt)); ftype = ["small", "skirmish", "teamfight"][int(rng.choice(3, p=pt / pt.sum()))]
                    st_ = FTc["size_table_early"][ftype]["0-4" if m < 5 else "5-9" if m < 10 else "10-13"] if (EKC and m < 14 and FTc.get("size_table_early")) else FTc["size_table"][ftype][FPH(m)]; sizes = np.array([int(a_) for a_ in st_]); pr = np.array(list(st_.values())); pr = pr / pr.sum()
                else:
                    sizes, pr = self.fsize[FPH(m)]
                n = int(rng.choice(sizes, p=pr))
                ks = KSC
                zk = cal.get("kill_z_phase", {}).get("0-13" if m < 14 else "14-24" if m < 25 else "25+", 1.0)  # opt-in (6 Nov test): strength in kills by phase
                p = sig(ks["intercept"] + ks["per_1k_gold_lead"] * gd / 1000 + ks["per_v1_logit"] * z * zk + ks["baron"] * bdir + ks["elder"] * edir + form
                        + ks.get("skirmish_style_early", 0.0) * skirm_d * (m < 15)
                        + rng.normal(0, cal.get("fight_eps_phase", {}).get("0-13" if m < 14 else "14-24" if m < 25 else "25+", cal["fight_eps"])))
                tf = at(t0 + rng.uniform(0, 55)); dead = [set(), set()]; inv = [set(), set()]; lanes_in = set()
                if DT is not None: dead = [{i for i in range(5) if respawn[0][i] > tf}, {i for i in range(5) if respawn[1][i] > tf}]
                part = None
                for j in range(n):
                    s = 0 if rng.random() < p else 1; o = 1 - s
                    if FPon:  # fight players: drawn with the first kill (side A = that kill's side), then every kill among them
                        fpw = 0 if m < 5 else 1 if m < 10 else 2 if m < 15 else 3 if m < 25 else 4; FPd = self.FP
                        if j == 0:
                            pp_ = FPd["probs"][fpw * 3 + (0 if n == 1 else 1 if n == 2 else 2)]
                            if DT is not None and (dead[0] or dead[1]):
                                ok_ = np.array([not (set(FPd["subs"][q // 31]) & dead[s]) and not (set(FPd["subs"][q % 31]) & dead[o]) for q in range(len(pp_))], float)
                                pp_ = pp_ * ok_
                                if pp_.sum() <= 0: break  # one side has nobody alive: no fight
                                pp_ = pp_ / pp_.sum()
                            ci = int(rng.choice(len(pp_), p=pp_))
                            part = {s: FPd["subs"][ci // 31], o: FPd["subs"][ci % 31]}
                        if part is None: continue
                        ck = [i for i in part[s] if i not in dead[s]]; cv = [i for i in part[o] if i not in dead[o]]
                        if not ck or not cv: continue
                        sgs, sgo = (1 if s == 0 else -1), (1 if o == 0 else -1); wn_ = FPd["WN"][fpw]
                        def pick_role(c_, tab, sg_):
                            u_ = np.array([tab["role"][wn_][ROLES[i]] + tab["lean_per_1k_before_15"] * (sg_ * e_lead[i] / 1000 if (m < 15 and e_lead is not None) else 0.0) for i in c_])
                            pz = np.exp(u_ - u_.max()); return c_[int(rng.choice(len(c_), p=pz / pz.sum()))]
                        k = pick_role(ck, FPd["k"], sgs); v = pick_role(cv, FPd["v"], sgo)
                        dead[o].add(v); fa = FPd["a"]
                        nbf = 0 if n == 1 else 1 if n == 2 else 2
                        ast = [i for i in ck if i != k and i not in dead[s] and rng.random() < sig(fa["window " + wn_] + (fa["role " + ROLES[i]] if i else 0.0)
                               + fa["same_lane_as_killer"] * (LANEID[i] >= 0 and LANEID[i] == LANEID[k]) + fa["same_lane_as_victim"] * (LANEID[i] >= 0 and LANEID[i] == LANEID[v])
                               + fa["one_kill_fight"] * (nbf == 0) + fa["two_kill_fight"] * (nbf == 1) + fa["already_in_a_kill"] * (i in inv[s]))]
                        inv[s].update([k] + ast)
                        K[s, k] += 1; D[o, v] += 1
                        for i in ast: A[s, i] += 1
                        if not ast: SOLO[s, k] += 1
                        add_gold(s, val["kill"], [k] * 2 + ast)
                        if LL is not None and LL["ev"] is not None and m < 15:
                            E_ = LL["ev"]; gold[k] += sgs * E_["own_kill"][k]; gold[v] -= sgs * E_["own_death"][v]
                            for i in ast: gold[i] += sgs * E_["own_assist"][i]
                        net += 1 if s == 0 else -1; kc[s] += 1; first.setdefault("blood", s)
                        tk = at(tf + 3 * j); kill_log.append((tk, s, k, v))
                        if DT is not None: respawn[o][v] = tk + death_wait(v, tk); dead_iv[o].append((tk, respawn[o][v]))
                        note(tk, s, "kill", f"{ROLES[k]} kills {ROLES[v]}" + ("" if ast else " (solo)")); continue
                    alive_v = [i for i in range(5) if i not in dead[o]]
                    if not alive_v: continue
                    if DT is not None and len(dead[s]) == 5: continue
                    if EK and m < 15:  # lane-aware early kills: the pair, then assists (13 Nov)
                        alive_k = [i for i in range(5) if i not in dead[s]] or list(range(5)); sgs, sgo = (1 if s == 0 else -1), (1 if o == 0 else -1)
                        pairs, u = [], []
                        for k in alive_k:
                            for v in alive_v:
                                pn = ROLES[k] + ">" + ROLES[v]
                                x_ = (EKP["pair"][pn] + EKP["window"][EWN[ew]][pn] + EKP["lean_killer_per_1k"] * (sgs * e_lead[k] / 1000 if e_lead is not None else 0.0)
                                      + EKP["lean_victim_per_1k"] * (sgo * e_lead[v] / 1000 if e_lead is not None else 0.0))
                                if j > 0:
                                    x_ += (EKP["follow_killer_in_fight"] * (k in inv[s]) + EKP["follow_victim_in_fight"] * (v in inv[o])
                                           + EKP["follow_killer_lane_in_fight"] * (LANEID[k] >= 0 and LANEID[k] in lanes_in) + EKP["follow_victim_lane_in_fight"] * (LANEID[v] >= 0 and LANEID[v] in lanes_in))
                                pairs.append((k, v)); u.append(x_)
                        u = np.array(u); pu = np.exp(u - u.max()); pu = pu / pu.sum()
                        k, v = pairs[int(rng.choice(len(pairs), p=pu))]
                        dead[o].add(v)
                        if EKM in ("pairs_flat", "on_flat"): ast = [i for i in alive_k if i != k and i not in dead[s] and rng.random() < self.ap[i]]
                        else:
                            ast = [i for i in alive_k if i != k and i not in dead[s] and rng.random() < sig(EKA["window " + EWN[ew]] + (EKA["role " + ROLES[i]] if i else 0.0)
                                   + EKA["same_lane_as_killer"] * (LANEID[i] >= 0 and LANEID[i] == LANEID[k]) + EKA["same_lane_as_victim"] * (LANEID[i] >= 0 and LANEID[i] == LANEID[v])
                                   + EKA["already_in_fight"] * (j > 0 and i in inv[s]))]
                        K[s, k] += 1; D[o, v] += 1
                        for i in ast: A[s, i] += 1
                        if not ast: SOLO[s, k] += 1
                        add_gold(s, val["kill"], [k] * 2 + ast)
                        if LL is not None and LL["ev"] is not None:
                            E_ = LL["ev"]; gold[k] += sgs * E_["own_kill"][k]; gold[v] -= sgs * E_["own_death"][v]
                            for i in ast: gold[i] += sgs * E_["own_assist"][i]
                        inv[s].update([k] + ast); inv[o].add(v)
                        for i in [k, v] + ast:
                            if LANEID[i] >= 0: lanes_in.add(LANEID[i])
                        net += 1 if s == 0 else -1; kc[s] += 1; first.setdefault("blood", s)
                        tk = at(tf + 3 * j); kill_log.append((tk, s, k, v))
                        if DT is not None: respawn[o][v] = tk + death_wait(v, tk); dead_iv[o].append((tk, respawn[o][v]))
                        note(tk, s, "kill", f"{ROLES[k]} kills {ROLES[v]}" + ("" if ast else " (solo)")); continue
                    early_ll = LL is not None and m < 15
                    if early_ll:  # victim: roles behind in their own lane die more (fitted lean)
                        wv = np.exp(LL["av"][alive_v] + LL["bv"] * (1 if o == 0 else -1) * lean[alive_v] / 1000); wv /= wv.sum()
                    else: wv = self.dw[alive_v] / self.dw[alive_v].sum()
                    v = int(rng.choice(alive_v, p=wv)); dead[o].add(v)
                    alive_k = [i for i in range(5) if i not in dead[s]] or list(range(5))
                    if early_ll:  # killer: roles ahead in their own lane get more of the kills (fitted lean)
                        wk = np.exp(LL["ak"][alive_k] + LL["bk"] * (1 if s == 0 else -1) * lean[alive_k] / 1000); wk /= wk.sum()
                    else: wk = self.kw[alive_k] / self.kw[alive_k].sum()
                    k = int(rng.choice(alive_k, p=wk))
                    ast = [i for i in range(5) if i != k and i not in dead[s] and rng.random() < self.ap[i]]
                    K[s, k] += 1; D[o, v] += 1
                    for i in ast: A[s, i] += 1
                    if not ast: SOLO[s, k] += 1
                    add_gold(s, val["kill"], [k] * 2 + ast)
                    if early_ll and LL["ev"] is not None:
                        sg_ = 1 if s == 0 else -1; E_ = LL["ev"]
                        gold[k] += sg_ * E_["own_kill"][k]; gold[v] -= sg_ * E_["own_death"][v]
                        for i in ast: gold[i] += sg_ * E_["own_assist"][i]
                    net += 1 if s == 0 else -1; kc[s] += 1
                    first.setdefault("blood", s)
                    tk = at(tf + 3 * j); kill_log.append((tk, s, k, v))
                    if DT is not None: respawn[o][v] = tk + death_wait(v, tk); dead_iv[o].append((tk, respawn[o][v]))
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
                    if FDT is not None and kind == "dragon" and first_drag:
                        xb_ = FDT["blue_side"] + FDT["per_v1_logit"] * z + sum(FDT.get(f_ + "_per_1k", 0.0) * lanef[f_] / 1000 for f_ in ["gd", "jng", "bot2", "mid", "top", "net60k", "objk"])
                        s = 0 if rng.random() < sig(xb_) else 1
                    else: s = taker(kind if kind in P["taker"] else "dragon", feats)
                    tt = at(max(t0, nxt["dragon"]) + rng.uniform(0, 50))
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
                        tt = at(max(t0, nxt[kind]) + rng.uniform(0, 50)); taken_once[kind] = True
                        if kind == "grub":
                            n_own = 3 if rng.random() < P["grubs_split"]["one_team_all"] else 2
                            grubs[s] += n_own; grubs[1 - s] += 3 - n_own; first.setdefault("grub", s); add_gold(s, val["grub"] * n_own); add_gold(1 - s, val["grub"] * (3 - n_own))
                            note(tt, s, "grubs", f"{n_own} void grubs")
                        else:
                            heralds[s] += 1; herald_t[s] = tt; first.setdefault("herald", s); add_gold(s, val["herald"]); note(tt, s, "herald", "Rift Herald")
            if nxt["baron"] is not None and nxt["baron"] < t0 + 60:
                if rng.random() < take_chance("baron"):
                    s = taker("baron", {k: lanef[k] for k in ["gd", "net60k", "objk"]})
                    tt = at(max(t0, nxt["baron"]) + rng.uniform(0, 50))
                    barons[s] += 1; baron_until[s] = tt + BARON_BUFF; nxt["baron"] = tt + 360; add_gold(s, val["baron"])
                    first.setdefault("baron", s); ftime.setdefault("baron", tt); note(tt, s, "baron", "Baron Nashor")
            # --- towers: segments lane by lane, then base ---
            sc = SEGC
            # 12 Nov: the phase terms were always read from the segment-count fit (P["segments"]), not from the push fit in use, so pushes
            # from 20:00 came too often (+0.07 to +0.22 on the log-odds). cal["seg_phase"] = "own" reads them from the push fit in use:
            # the default from 12 Nov (Luke: fix it). cal["seg_phase"] = "segments" is the sim as it was, so earlier runs replay.
            seg_ph = {p_: sc.get(f"phase {p_}", 0.0) for p_ in PHN} if cal.get("seg_phase", "own") == "own" else self.seg_ph
            for s in (0, 1):
                sg = 1 if s == 0 else -1; o = 1 - s
                en_ = ow_ = 0; st_t = [None]
                if DP is not None:
                    en_ = max_dead(dead_iv[o], t0, t0 + 60); ow_ = max_dead(dead_iv[s], t0, t0 + 60)
                def stime(s=s, en_=en_, st_t=st_t):
                    if st_t[0] is None:
                        lk = [e_[0] for e_ in kill_log if e_[1] == s and e_[0] >= t0]
                        sz_, pz_ = self.dp["delay"] if (en_ > 0 and lk) else (None, None)
                        st_t[0] = (max(lk) + int(rng.choice(sz_, p=pz_))) if sz_ is not None else t0 + rng.uniform(0, 59)
                    else:
                        sz_, pz_ = self.dp["gap"]; st_t[0] += int(rng.choice(sz_, p=pz_))
                    return at(st_t[0])
                for li, L in enumerate(LANES):
                    if seg[s][li] >= 15: continue
                    tier = seg[s][li] // 5
                    xb = (sc["intercept"] + seg_ph[PHN[sum(m >= p for p in PH) - 1]] + sc["tier T2"] * (tier == 1) + sc["tier T3"] * (tier == 2)
                          + sc["mid"] * (L == "MID") + sc["bot"] * (L == "BOT") + sc["per_1k_lane_lead"] * max(-8, min(8, lane_lead(s, L) / 1000))
                          + sc["per_1k_team_lead"] * max(-15, min(15, sg * gd / 1000)) + sc["per_v1_logit"] * sg * z
                          + sc["baron"] * (baron_until[s] > t0) + sc["elder"] * (elder_until[s] > t0)
                          + sc["herald_last_3min"] * (t0 - herald_t[s] < 180) + sc["own_grubs"] * grubs[s] + sc.get("siege_style", 0.0) * sg * siege_d + sc.get("siege_style_sum", 0.0) * siege_s
                          + sc.get("net_kills_this_minute", 0.0) * max(-5, min(5, sg * net))
                          + sc.get("T2 x mid", 0.0) * (tier == 1 and L == "MID") + sc.get("T2 x bot", 0.0) * (tier == 1 and L == "BOT")
                          + sc.get("T3 x mid", 0.0) * (tier == 2 and L == "MID") + sc.get("T3 x bot", 0.0) * (tier == 2 and L == "BOT")
                          + sc.get("T1 early x mid", 0.0) * (tier == 0 and m < 14 and L == "MID") + sc.get("T1 early x bot", 0.0) * (tier == 0 and m < 14 and L == "BOT") + sc.get("tower_segments_down", 0.0) * (seg[s][li] % 5)
                          + (sc.get(f"T{tier + 1} x phase {PHN[sum(m >= p for p in PH) - 1]}", 0.0) if tier else 0.0) + sc.get("minutes_before_14", 0.0) * (min(m, 14) - 14)
                          + sc.get("lane_segments_last_minute", 0.0) * min(5, prevseg[s][li]) + sc.get("T3_x_baron", 0.0) * (tier == 2) * (baron_until[s] > t0)
                          + sc.get("net_kills_last_minute", 0.0) * max(-5, min(5, sg * prev_net)) + sc.get("clear_fight_win", 0.0) * (sg * net >= cutS or sg * prev_net >= cutS)
                          + sc.get("enemies_dead_max", 0.0) * en_ + sc.get("own_dead_max", 0.0) * ow_)
                    if SPC is not None:  # tower pushes: a push starts with the fitted chance, its size drawn from real pushes
                        n = 0
                        if rng.random() < sig(xb):
                            key_ = "0_early" if tier == 0 and m < 14 else str(tier)
                            sz, pz = self.dp["seg"].get(key_ + "|" + dgrp(en_), self.spush[key_]) if DP is not None else self.spush[key_]; n = int(rng.choice(sz, p=pz))
                    else:
                        n = self.count(rng, math.exp(xb), "segments", m)
                    n = min(n, 15 - seg[s][li]); prevseg[s][li] = n
                    for _ in range(n):
                        seg[s][li] += 1
                        add_gold(s, val["plate_early"] if m < 14 else val["plate"], LANE_ROLES[L])
                        if LL is not None and LL["ev"] is not None:
                            if "own_lane_plate" in LL["ev"]:
                                if m < 15:
                                    pv = LL["ev"]["other_lane_plate"].copy(); own_ = LANE_ROLES[L] + [1]; pv[own_] = LL["ev"]["own_lane_plate"][own_]; gold[:] += sg * pv
                            elif m < 14: gold[:] += sg * LL["ev"]["team_plate"]
                        if seg[s][li] % 5 == 0:
                            towers[s] += 1; add_gold(s, val["tower"], LANE_ROLES[L]); first.setdefault("tower", s); twt = stime() if DP is not None else at(t0 + rng.uniform(0, 59))
                            ftime.setdefault("tower", twt if EO else t0 + 30); first_lane.setdefault("tower", L)
                            note(twt, s, "tower", f"T{seg[s][li] // 5} {L}")
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
                      + bc.get("net_kills_this_minute", 0.0) * max(-5, min(5, sg * net))
                      + bc.get("net_kills_last_minute", 0.0) * max(-5, min(5, sg * prev_net)) + bc.get("clear_fight_win", 0.0) * (sg * net >= cutB or sg * prev_net >= cutB)
                      + (bc.get("net_kills_this_minute_x_time", 0.0) * max(-5, min(5, sg * net)) + bc.get("net_kills_last_minute_x_time", 0.0) * max(-5, min(5, sg * prev_net))) * (m - 25) / 10
                      + bc.get("enemies_dead_max", 0.0) * en_ + bc.get("own_dead_max", 0.0) * ow_)
                if PK == "on":  # own and enemy kills this and last minute, counted separately
                    pc_ = P["base_push_kills"]["start"]
                    xb = (pc_["intercept"] + pc_["from 25"] * (m >= 25) + pc_["from 35"] * (m >= 35) + pc_["per_1k_lead"] * max(-15, min(15, sg * gd / 1000))
                          + pc_["per_v1_logit"] * sg * z + pc_["baron"] * (baron_until[s] > t0) + pc_["elder"] * (elder_until[s] > t0)
                          + pc_["enemy_inhibs_down"] * len(down) + pc_["open_lanes"] * len(opn) + pc_["siege_style_sum"] * siege_s
                          + pc_["lane_just_opened"] * any(open_t[s][li] >= t0 - 60 for li in opn) + pc_["base_take_last_minute"] * (last_base[s] >= t0 - 60)
                          + pc_["own_kills_this_minute"] * min(5, kc[s]) + pc_["enemy_kills_this_minute"] * min(5, kc[o])
                          + pc_["own_kills_last_minute"] * min(5, prev_kc[s]) + pc_["enemy_kills_last_minute"] * min(5, prev_kc[o]))
                if PK != "off":  # how far the push runs follows the kills that opened it
                    kg_ = "0" if kc[s] == 0 else "1-2" if kc[s] <= 2 else "3+"
                    sz, pr_ = self.push_k[("inhib down" if down else "no inhib down") + "|" + kg_]
                    npush = int(rng.choice(sz, p=pr_)) if rng.random() < sig(xb) else 0
                elif ENDS is not None:  # is this the push that ends the game (fitted chance)? then its size from real pushes of that kind
                    npush = 0
                    if rng.random() < sig(xb):
                        ec = ENDS["ends_game"]["coef"]; nk2 = max(-5, min(8, sg * (net + prev_net))); tm_ = (m - 25) / 10
                        kind = "ends" if rng.random() < sig(ec["intercept"] + ec["enemy_inhib_down"] * bool(down) + ec["kills_edge_2min"] * nk2 + ec["time"] * tm_ + ec["kills_edge_2min_x_time"] * nk2 * tm_) else "other"
                        tb = ENDS["size_by_kind"][("inhib_down" if down else "no_inhib_down") + "|" + kind]
                        npush = int(rng.choice([int(k_) for k_ in tb], p=np.array(list(tb.values())) / sum(tb.values())))
                elif DP is not None:  # how far the push runs follows how many defenders are dead
                    st_k = "inhib_down" if down else "no_inhib_down"
                    sz, pr_ = self.dp["base"].get(st_k + "|" + dgrp(en_), self.push[st_k])
                    npush = int(rng.choice(sz, p=pr_)) if rng.random() < sig(xb) else 0
                else:
                    sz, pr_ = self.push["inhib_down" if down else "no_inhib_down"]
                    npush = int(rng.choice(sz, p=pr_)) if rng.random() < sig(xb) else 0
                if npush: last_base[s] = t0
                for _ in range(npush):
                    down = [li for li in range(3) if inhib_back[s][li] > t0]
                    up_inh = [li for li in opn if inhib_back[s][li] <= t0]
                    tt = stime() if DP is not None else at(t0 + rng.uniform(0, 59))
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
            if DSH is not None:  # damage share by player and champion (opt-in, 14 Nov; research/sim4/s4_dmgshare.py): x["dmg_eff"][s][i] = player + champion effect
                bb_ = DSH["base"]; eff_ = x.get("dmg_eff", [[0.0] * 5, [0.0] * 5])[s]
                dm = np.array([bb_[r]["mean"] + bb_[r]["per_kp"] * (kp[i] - bb_[r]["kp_mean"]) + eff_[i] + rng.normal(0, DSH["resid_sd_by_role"][r]) for i, r in enumerate(ROLES)]).clip(0.02)
            else:
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
                "kd15": [int(v) for v in gd_at.get("kd15", (K[0] - D[0]) - (K[1] - D[1]))], "first_tower_lane": first_lane.get("tower", ""),
                "capped": capped, "steps": sorted(steps, key=lambda e: e["t"]) if log else []}


if __name__ == "__main__":
    import sys
    P = json.load(open(sys.argv[1]))
    sim = Sim(P)
    g = sim.run({"z": 0.4}, seed=1, log=True)
    print(g["winner"], g["sec"] // 60, g["kills"], g["towers"], g["dr"], g["ba"])
    for e in g["steps"][:40]: print(f'{e["t"] // 60:2d}:{e["t"] % 60:02d} {e["side"]:4s} {e["text"]}')
    g2 = sim.run({"z": 0.4}, seed=1); print("same seed same game:", g2["winner"] == g["winner"] and g2["sec"] == g["sec"] and g2["kills"] == g["kills"])
