/* Game-state simulator (sim session 4, 13 Nov 2026): a port of research/sim3/s3_sim.py to the browser.
   Every event is a random draw from chances fitted to real games (the tables in js/sim-tables.js); nothing is scripted to a result.
   The same inputs and seed replay the same game. JS and Python random generators differ, so single games don't match the research
   sim one for one; averages over many games must (checked by research/sim4/port_check.html).
   Ported: the default sim (lane x tier pushes, tower-push phase fix), draft styles as timing ("timing") or side ("side"),
   fight types ("typed"), won-fight pushes ("on" / "simple"), lane-level play (fit version 2 or 3).
   Not ported (opt-in research variants that were not kept): "within", game form, "endings", kill_z_phase, fight_eps_phase. */
(function(){
"use strict";
const ROLES = ["top", "jng", "mid", "bot", "sup"];
const LANES = ["TOP", "MID", "BOT"], LANE_ROLES = {TOP: [0], MID: [2], BOT: [3, 4]};
const PH = [0, 14, 20, 25, 30, 35], PHN = ["0-13", "14-19", "20-24", "25-29", "30-34", "35+"];
const phOf = m => { let n = 0; for(const p of PH) if(m >= p) n++; return PHN[n - 1]; };
const FPH = m => m < 14 ? "0-13" : m < 25 ? "14-24" : m < 35 ? "25-34" : "35+";
const SPAWN = {dragon: 300, grub: 480, herald: 900, baron: 1200};
const BARON_BUFF = 180, ELDER_BUFF = 150, INHIB_BACK = 300;
const sig = x => 1 / (1 + Math.exp(-x));
const DEFAULT_CAL = {gain: 1, lane_mu: 1, lane_k: 1, fight_eps: 0, max_min: 70, style_mode: "side"};
const g0 = (o, k, d) => (o && o[k] != null) ? o[k] : d;   // Python dict.get
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/* ---- seeded random generator (sfc32, seeded through splitmix32 from a number) ---- */
function RNG(seed){
  let s = (Math.floor(Math.abs(seed)) % 4294967296) >>> 0, hi = Math.floor(Math.abs(seed) / 4294967296) >>> 0;
  const sm = () => { s = (s + 0x9e3779b9) >>> 0; let z = s ^ hi; z = Math.imul(z ^ (z >>> 16), 0x85ebca6b); z = Math.imul(z ^ (z >>> 13), 0xc2b2ae35); return (z ^ (z >>> 16)) >>> 0; };
  let a = sm(), b = sm(), c = sm(), d = sm(), spare = null;
  const u32 = () => { a >>>= 0; b >>>= 0; c >>>= 0; d >>>= 0; let t = (a + b) | 0; a = b ^ (b >>> 9); b = (c + (c << 3)) | 0; c = (c << 21) | (c >>> 11); d = (d + 1) | 0; t = (t + d) | 0; c = (c + t) | 0; return t >>> 0; };
  for(let i = 0; i < 12; i++) u32();
  const R = {};
  R.random = () => (u32() + u32() / 4294967296) / 4294967296;     // [0, 1)
  R.uniform = (lo, hi_) => lo + (hi_ - lo) * R.random();
  R.normal = (mu, sd) => { let z; if(spare != null){ z = spare; spare = null; } else { let u = 0, v = 0; while(!u) u = R.random(); v = R.random();
    const r = Math.sqrt(-2 * Math.log(u)); z = r * Math.cos(2 * Math.PI * v); spare = r * Math.sin(2 * Math.PI * v); } return (mu || 0) + (sd == null ? 1 : sd) * z; };
  R.poisson = mu => { if(!(mu > 0)) return 0; if(mu > 60) return Math.max(0, Math.round(R.normal(mu, Math.sqrt(mu))));
    const L = Math.exp(-mu); let k = 0, p = 1; do { k++; p *= R.random(); } while(p > L); return k - 1; };
  R.gamma = shape => { if(shape < 1){ const u = R.random(); return R.gamma(1 + shape) * Math.pow(u || 1e-300, 1 / shape); }
    const d_ = shape - 1 / 3, c_ = 1 / Math.sqrt(9 * d_);
    for(;;){ let x, v; do { x = R.normal(); v = 1 + c_ * x; } while(v <= 0); v = v * v * v; const u = R.random();
      if(u < 1 - 0.0331 * x * x * x * x || Math.log(u) < 0.5 * x * x + d_ * (1 - v + Math.log(v))) return d_ * v; } };
  R.negbin = (n, p) => R.poisson(R.gamma(n) * (1 - p) / p);       // numpy negative_binomial(n, p): failures before n successes
  R.pick = (vals, probs) => { let u = R.random(), acc = 0; for(let i = 0; i < vals.length; i++){ acc += probs[i]; if(u < acc) return vals[i]; } return vals[vals.length - 1]; };
  R.pickUniform = vals => vals[Math.min(vals.length - 1, Math.floor(R.random() * vals.length))];
  return R;
}

function cholesky(M){ const n = M.length, L = M.map(() => new Array(n).fill(0));
  for(let i = 0; i < n; i++) for(let j = 0; j <= i; j++){ let s = M[i][j]; for(let k = 0; k < j; k++) s -= L[i][k] * L[j][k];
    L[i][j] = i === j ? Math.sqrt(Math.max(s, 1e-12)) : s / L[j][j]; } return L; }
const plusEye = M => M.map((r, i) => r.map((v, j) => v + (i === j ? 1 : 0)));
const matVec = (L, v) => L.map(r => r.reduce((s, x, j) => s + x * v[j], 0));
const norm = a => { const s = a.reduce((x, y) => x + y, 0); return a.map(x => x / s); };
const table = t => { const ks = Object.keys(t); return [ks.map(Number), norm(ks.map(k => t[k]))]; };

class Sim {
  constructor(P, cal){
    this.P = P; this.cal = Object.assign({}, DEFAULT_CAL, cal || {});
    this.L15 = cholesky(plusEye(P.lane_cov15));
    const d10 = P.lane_cov10.map((r, i) => r[i]), d15 = P.lane_cov15.map((r, i) => r[i]);
    const mr = d10.reduce((s, v, i) => s + Math.sqrt(v / d15[i]), 0) / d10.length;
    this.A = Math.log(mr) / Math.log(10 / 15);
    this.ph = {}; this.segPh = {}; PHN.forEach(p => { this.ph[p] = g0(P.fights, "phase " + p, 0); this.segPh[p] = g0(P.segments, "phase " + p, 0); });
    this.fsize = {}; for(const ph in P.fight_size_table) this.fsize[ph] = table(P.fight_size_table[ph]);
    const ks = P.role_kill_share, ds = P.role_death_share, ap = P.role_assist_per_team_kill;
    this.kw = norm(ROLES.map(r => ks[r])); this.dw = norm(ROLES.map(r => ds[r]));
    this.ap = ROLES.map(r => Math.min(0.95, ap[r] / Math.max(1e-6, 1 - ks[r])));
    this.gs = norm(ROLES.map(r => P.box[r].gold_share));
    const sw = P.gold_swing_share || {};
    this.swLane = norm(ROLES.map((r, i) => g0(sw.laning, r, this.gs[i]))); this.swLate = norm(ROLES.map((r, i) => g0(sw.after, r, this.gs[i])));
    this.spush = {};
    if(P.segment_push){ for(const k in P.segment_push.size_dist) this.spush[k] = table(P.segment_push.size_dist[k]);
      ["0_early", "0", "1", "2"].forEach(k => { if(!this.spush[k]) this.spush[k] = this.spush["0"] || [[1], [1]]; }); }
    this.push = {}; const bp = P.base_push.size_dist_by_state || {no_inhib_down: P.base_push.size_dist, inhib_down: P.base_push.size_dist};
    for(const st in bp) this.push[st] = table(bp[st]);
    this.LL = null;
    if(P.lane_level){ const ll = P.lane_level, kr = ll.kill_role, lk = ll.event_gold ? "lean_per_1k_expected_lead" : "lean_per_1k_own_lead";
      this.LL = {chol: cholesky(plusEye(ll.cov15)), z: ROLES.map(r => ll.coef[r].z), ak: kr.killer.role_intercepts, bk: kr.killer[lk],
        av: kr.victim.role_intercepts, bv: kr.victim[lk], ev: null};
      if(ll.event_gold){ const eg = ll.event_gold, pk = eg.top.own_lane_plate != null ? ["own_lane_plate", "other_lane_plate"] : ["team_plate"];
        this.LL.ev = {}; ["own_kill", "own_death", "own_assist", ...pk].forEach(k => { this.LL.ev[k] = ROLES.map(r => eg[r][k]); });
        this.LL.zPre = ROLES.map(r => ll.coef_pregame[r].z); } }
    const dt = P.dragon_types.first_two_share; this.dtypes = Object.keys(dt); this.dprob = norm(this.dtypes.map(k => dt[k]));
    /* fight players (opt-in, 13 Nov; research/sim4/s4_participants.py): every (side A set, side B set) pair's chance per window x kills group */
    this.FP = null;
    if(P.fight_players){ const fp = P.fight_players.players, subs = [], combos = (k, start, cur_) => { if(cur_.length === k){ subs.push(cur_.slice()); return; }
        for(let i = start; i < 5; i++){ cur_.push(i); combos(k, i + 1, cur_); cur_.pop(); } };
      for(let n_ = 1; n_ <= 5; n_++) combos(n_, 0, []);
      const pairs = []; for(let i = 0; i < 5; i++) for(let j = i + 1; j < 5; j++) pairs.push([i, j]);
      const WN_ = ["0-4", "5-9", "10-14", "15-24", "25+"], NBN_ = ["1", "2", "3+"], LWN_ = ["0-4", "5-9", "10-14", "15+"], probs = [];
      const sum = a => a.reduce((x, y) => x + y, 0);
      const WITH = {}, CROSS = {};
      LWN_.forEach(lw => { WITH[lw] = subs.map(s_ => sum(pairs.filter(([i, j]) => s_.includes(i) && s_.includes(j)).map(([i, j]) => fp.same_side_pair[lw][ROLES[i] + "+" + ROLES[j]])));
        CROSS[lw] = subs.map(a_ => subs.map(b_ => sum(a_.flatMap(i => b_.map(j => fp.across[lw][ROLES[i] + "~" + ROLES[j]]))))); });
      WN_.forEach((w_, wi_) => { const lw = LWN_[Math.min(wi_, 3)], within = WITH[lw], cross = CROSS[lw];
        NBN_.forEach(nb_ => { const ra = fp.role_A[w_ + "|" + nb_], rb = fp.role_B[w_ + "|" + nb_];
          const ua = subs.map((s_, q) => sum(s_.map(i => ra[ROLES[i]])) + within[q]), ub = subs.map((s_, q) => sum(s_.map(i => rb[ROLES[i]])) + within[q]);
          const u = []; ua.forEach((x, a_) => ub.forEach((y, b_) => u.push(x + y + cross[a_][b_])));
          const mx = Math.max(...u); probs.push(norm(u.map(x => Math.exp(x - mx)))); }); });
      this.FP = {subs, probs, idx: probs[0].map((_, q) => q), WN: WN_, k: P.fight_players.killer, v: P.fight_players.victim, a: P.fight_players.assist}; }
  }
  count(rng, mu, kind, m){
    const phi = g0(g0(this.P.dispersion || {}, kind, {}), phOf(m), 1);
    if(phi <= 1.01 || mu <= 0) return rng.poisson(mu);
    return rng.negbin(mu / (phi - 1), 1 / phi);
  }
  laneMean(x, z, m){ return ROLES.map((r, i) => { const [a, bz, bs, bc] = this.P.lanes[r][String(m)];
    return a + bz * z + bs * (x.skill_gap || [0, 0, 0, 0, 0])[i] + bc * (x["cg" + m] || [0, 0, 0, 0, 0])[i]; }); }

  /* x: {z, skill_gap[5], cg15[5], siege_d, obj_d, skirm_d, pace_s, siege_s, obj_s, ll_m0[5], ll_e0[5]}; log = keep the play-by-play */
  run(x, seed, log){
    const P = this.P, cal = this.cal, rng = RNG(seed);
    const z = x.z * cal.gain;
    const siege_d = x.siege_d || 0, obj_d = x.obj_d || 0, skirm_d = x.skirm_d || 0, pace_s = x.pace_s || 0, siege_s = x.siege_s || 0, obj_s = x.obj_s || 0;
    const TIM = cal.style_mode === "timing";
    let SPC = (P.segment_push && g0(cal, "seg_mode", "push") === "push") ? P.segment_push.coef : null;
    let SEGC = SPC != null ? SPC : (TIM ? P.segments_timing : P.segments), PUSHC = TIM ? P.base_push_timing : P.base_push.coef;
    const KSC = TIM ? P.kill_side_timing : P.kill_side, TAKC = TIM ? P.taker_timing : P.taker, FB = P.gold_feedback;
    if(g0(cal, "seg_lane_tier", "on") === "on" && P.segment_push_lane_tier){ SPC = P.segment_push_lane_tier.coef; SEGC = SPC; }
    let cutS = 99, cutB = 99;
    if(g0(cal, "push_fight", "off") === "on" && P.segment_push_fight){ SPC = P.segment_push_fight.coef; SEGC = SPC; PUSHC = P.base_push_fight.coef;
      cutS = P.segment_push_fight.clear_fight_cutoff || 99; cutB = P.base_push_fight.clear_fight_cutoff || 99; }
    if(g0(cal, "push_fight", "off") === "simple" && P.segment_push_fight_simple){ SPC = P.segment_push_fight_simple.coef; SEGC = SPC; PUSHC = P.base_push_fight_simple.coef; }
    const LL = (g0(cal, "lane_level", "off") === "on" && this.LL && x.ll_m0) ? this.LL : null;
    let laneEnd, lean = null;
    if(LL){ const nz = ROLES.map(() => rng.normal()), c = matVec(LL.chol, nz);
      laneEnd = ROLES.map((r, i) => x.ll_m0[i] + LL.z[i] * x.z + c[i]);
      lean = LL.ev == null ? laneEnd : ROLES.map((r, i) => x.ll_e0[i] + LL.zPre[i] * x.z);
    } else { const mu = this.laneMean(x, z, 15), nz = ROLES.map(() => rng.normal()), c = matVec(this.L15, nz), k = Math.sqrt(cal.lane_k);
      laneEnd = mu.map((v, i) => cal.lane_mu * v + k * c[i]); }
    /* lane-aware early kills (opt-in, 13 Nov): cal.early_kills = "on" with P.early_kills (research/sim4/s4_earlykills.py) */
    /* "on" = both parts; "pairs" = kill pairs and assists only; "counts" = early fight counts, types and sizes only */
    const EKM = g0(cal, "early_kills", "off"), EKC = EKM === "on" || EKM === "counts" || EKM === "on_flat", EK = ["on", "pairs", "pairs_flat", "on_flat"].includes(EKM) && !!P.early_kills, EKP = EK ? P.early_kills.pair : null, EKA = EK ? P.early_kills.assist : null;
    const EWN = ["0-4", "5-9", "10-14"], LANEID = [0, -1, 1, 2, 2], eLead = LL && LL.ev ? lean : null;
    /* events keep their order (opt-in, 13 Nov): each event happens no earlier than the one before it, so a minute's events keep the
       order the sim plays them and nothing comes after the Nexus. Same random draws; only the times (and what they feed) move. */
    const EO = g0(cal, "event_order", "off") === "on"; let cur = 0; const at = d => EO ? (cur = Math.max(cur, d)) : d;
    const FPon = g0(cal, "fight_players", "off") === "on" && !!this.FP;  /* who is in each fight (13 Nov): kills and assists only among them */
    /* the game's first dragon has its own fitted taker (opt-in, 13 Nov; research/sim4/s4_firstdragon.py) */
    const FDT = (g0(cal, "first_dragon_taker", "off") === "on" && P.taker_first_dragon) ? P.taker_first_dragon[TIM ? "timing" : "side"] : null;
    const farm = [0, 0, 0, 0, 0], gold = [0, 0, 0, 0, 0];
    const mk = () => [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]];
    const K = mk(), D = mk(), A = mk(), SOLO = mk();
    const seg = [[0, 0, 0], [0, 0, 0]], prevseg = [[0, 0, 0], [0, 0, 0]], inhibBack = [[-1, -1, -1], [-1, -1, -1]];
    const openT = [[null, null, null], [null, null, null]], lastBase = [-1e9, -1e9];
    const nxTowers = [2, 2], drag = [[], []], soul = [null, null], elderN = [0, 0], barons = [0, 0], grubs = [0, 0], heralds = [0, 0];
    const towers = [0, 0], inhibs = [0, 0], first = {}, ftime = {}, firstLane = {};
    const baronUntil = [-1, -1], elderUntil = [-1, -1], heraldT = [-1e9, -1e9];
    const nxt = {dragon: SPAWN.dragon, grub: SPAWN.grub, herald: SPAWN.herald, baron: SPAWN.baron};
    const takenOnce = {grub: false, herald: false};
    let elderMode = false, soulType = null; const dragSeq = [];
    const steps = [], gdAt = {}, kd = {}, killLog = [], fights = []; let fid = 0; let winner = null, tEnd = null, prevNf = 0, net = 0, prevNet = 0, gd = 0, m = 0;
    const val = P.gold;
    const sd = s => s === 0 ? 1 : -1;
    const addGold = (side, amount) => { if(LL && m < 15) return; const w = m < 15 ? this.swLane : this.swLate; for(let i = 0; i < 5; i++) gold[i] += sd(side) * amount * w[i]; };
    const note = (t, side, kind, text, who) => { if(log) steps.push(Object.assign({t: Math.floor(t), side: side == null ? "" : ["blue", "red"][side], kind, text}, who || {})); };
    const setd = (o, k, v) => { if(!(k in o)) o[k] = v; };

    for(m = 0; m <= cal.max_min; m++){
      const t0 = 60 * m;
      const laneLead = (s, L) => sd(s) * LANE_ROLES[L].reduce((a, i) => a + farm[i] + gold[i], 0);
      gd = 0; for(let i = 0; i < 5; i++) gd += farm[i] + gold[i]; gdAt[m] = gd;
      if(m === 5 || m === 10 || m === 15) kd["roles" + m] = farm.map((f, i) => f + gold[i]);
      if(m === 15) kd.kd15 = ROLES.map((r, i) => (K[0][i] - D[0][i]) - (K[1][i] - D[1][i]));
      const roleLead = farm.map((f, i) => f + gold[i]);
      const ph = phOf(m);
      /* laning / gold drift */
      if(m < 15){ const f0 = Math.pow(m / 15, this.A), f1 = Math.pow((m + 1) / 15, this.A); for(let i = 0; i < 5; i++) farm[i] += laneEnd[i] * (f1 - f0); }
      else { let d = val.drift + val.per_v1_logit_per_min * z + FB.per_1k_lead * gd / 1000 + (m >= 20 ? FB.extra_per_1k_after_20 * gd / 1000 : 0);
        d += rng.normal(0, P.gold_noise_sd) * g0(cal, "gold_noise_k", 1); for(let i = 0; i < 5; i++) gold[i] += d * this.swLate[i]; }
      const bdir = (baronUntil[0] > t0 ? 1 : 0) - (baronUntil[1] > t0 ? 1 : 0), edir = (elderUntil[0] > t0 ? 1 : 0) - (elderUntil[1] > t0 ? 1 : 0);
      const monUp = ["dragon", "baron"].some(k => nxt[k] != null && nxt[k] <= t0) ? 1 : 0, buffUp = (bdir !== 0 || edir !== 0) ? 1 : 0;
      /* fights */
      const fc = P.fights;
      let lam = Math.exp(fc.intercept + this.ph[ph] + fc.per_1k_abs_lead * Math.min(Math.abs(gd) / 1000, 15) + fc.monster_up * monUp + fc.buff_up * buffUp
        + g0(fc, "pace_style", 0) * pace_s + g0(fc, "minutes_before_14", 0) * (Math.min(m, 14) - 14));
      const TYPED = cal.fight_model === "typed" && P.fight_typed;
      const ew = m < 5 ? 0 : m < 10 ? 1 : 2, ewTerm = c => (EKC && TYPED ? g0(c, "early 0-4", 0) * (m < 5) + g0(c, "early 5-9", 0) * (m >= 5 && m < 10) : 0);
      let FTc, feat, k2 = 0;
      if(TYPED){ FTc = P.fight_typed; const cc = (EKC && FTc.count_early) ? FTc.count_early.coef : FTc.count.coef;
        for(const e of killLog) if(t0 - 120 <= e[0] && e[0] < t0) k2++;
        const fprev = prevNf > 0 ? 1 : 0;
        feat = {per_1k_abs_lead: Math.min(Math.abs(gd) / 1000, 15), monster_up: monUp, buff_up: buffUp};
        lam = Math.exp(cc.intercept + g0(cc, "phase " + ph, 0) + Object.keys(feat).reduce((s, k) => s + cc[k] * feat[k], 0)
          + cc.pace_style * pace_s + cc.fight_last_minute * fprev + cc.log1p_kills_last_2min * Math.log1p(k2) + ewTerm(cc)); }
      const nf = TYPED ? rng.poisson(lam) : this.count(rng, lam, "fights", m);
      prevNet = net; net = 0; const fought = nf > 0 ? 1 : 0; prevNf = nf;
      for(let f = 0; f < nf; f++){
        let sizes, pr, ftype = null; const fk = [0, 0];
        if(TYPED){ const TC = (EKC && FTc.type_early) ? FTc.type_early.coef : FTc.type.coef;
          const zt = [0, ...["skirmish", "teamfight"].map(t => { const tc = TC[t];
            return tc.intercept + g0(tc, "phase " + ph, 0) + Object.keys(feat).reduce((s, k) => s + tc[k] * feat[k], 0) + tc.log1p_kills_last_2min * Math.log1p(k2) + ewTerm(tc); })];
          const mx = Math.max(...zt), pt = norm(zt.map(v => Math.exp(v - mx)));
          ftype = rng.pick(["small", "skirmish", "teamfight"], pt);
          [sizes, pr] = table(EKC && m < 14 && FTc.size_table_early ? FTc.size_table_early[ftype][m < 5 ? "0-4" : m < 10 ? "5-9" : "10-13"] : FTc.size_table[ftype][FPH(m)]);
        } else [sizes, pr] = this.fsize[FPH(m)];
        const n = rng.pick(sizes, pr), ks = KSC;
        const p = sig(ks.intercept + ks.per_1k_gold_lead * gd / 1000 + ks.per_v1_logit * z + ks.baron * bdir + ks.elder * edir
          + g0(ks, "skirmish_style_early", 0) * skirm_d * (m < 15 ? 1 : 0) + rng.normal(0, cal.fight_eps));
        const tf = at(t0 + rng.uniform(0, 55)), dead = [new Set(), new Set()], inv = [new Set(), new Set()], lanesIn = new Set();
        let part = null;
        for(let j = 0; j < n; j++){
          const s = rng.random() < p ? 0 : 1, o = 1 - s;
          if(FPon){  /* fight players: drawn with the first kill (side A = that kill's side), then every kill among them */
            const FPd = this.FP, fpw = m < 5 ? 0 : m < 10 ? 1 : m < 15 ? 2 : m < 25 ? 3 : 4, nbf = n === 1 ? 0 : n === 2 ? 1 : 2;
            if(j === 0){ const ci = rng.pick(FPd.idx, FPd.probs[fpw * 3 + nbf]); part = {}; part[s] = FPd.subs[Math.floor(ci / 31)]; part[o] = FPd.subs[ci % 31]; }
            const ck = part[s].filter(i => !dead[s].has(i)), cv = part[o].filter(i => !dead[o].has(i));
            if(!ck.length || !cv.length) continue;
            const wn_ = FPd.WN[fpw];
            const pickRole = (c_, tab, sg_) => { const u_ = c_.map(i => tab.role[wn_][ROLES[i]] + tab.lean_per_1k_before_15 * (m < 15 && eLead ? sg_ * eLead[i] / 1000 : 0));
              const mx = Math.max(...u_); return rng.pick(c_, norm(u_.map(x_ => Math.exp(x_ - mx)))); };
            const k = pickRole(ck, FPd.k, sd(s)), v = pickRole(cv, FPd.v, sd(o));
            dead[o].add(v); const fa = FPd.a;
            const ast = ck.filter(i => i !== k && !dead[s].has(i) && rng.random() < sig(fa["window " + wn_] + (i ? fa["role " + ROLES[i]] : 0)
              + fa.same_lane_as_killer * (LANEID[i] >= 0 && LANEID[i] === LANEID[k]) + fa.same_lane_as_victim * (LANEID[i] >= 0 && LANEID[i] === LANEID[v])
              + fa.one_kill_fight * (nbf === 0) + fa.two_kill_fight * (nbf === 1) + fa.already_in_a_kill * inv[s].has(i)));
            inv[s].add(k); ast.forEach(i => inv[s].add(i));
            K[s][k]++; D[o][v]++; ast.forEach(i => A[s][i]++); if(!ast.length) SOLO[s][k]++;
            addGold(s, val.kill);
            if(LL && LL.ev && m < 15){ const g = sd(s), E = LL.ev; gold[k] += g * E.own_kill[k]; gold[v] -= g * E.own_death[v]; ast.forEach(i => { gold[i] += g * E.own_assist[i]; }); }
            net += sd(s); setd(first, "blood", s);
            const tk = at(tf + 3 * j); killLog.push([tk, s, k, v, ast]);
            fk[s]++; note(tk, s, "kill", `${ROLES[k]} kills ${ROLES[v]}` + (ast.length ? "" : " (solo)"), {k, v, ast, f: fid});
            continue;
          }
          const aliveV = [0, 1, 2, 3, 4].filter(i => !dead[o].has(i));
          if(!aliveV.length) continue;
          if(EK && m < 15){  /* lane-aware early kills (13 Nov): killer and victim drawn as a pair, then assists (research/sim4/s4_earlykills.py) */
            let aliveK = [0, 1, 2, 3, 4].filter(i => !dead[s].has(i)); if(!aliveK.length) aliveK = [0, 1, 2, 3, 4];
            const pairs = [], u = [];
            for(const k of aliveK) for(const v of aliveV){ const pn = ROLES[k] + ">" + ROLES[v];
              let x_ = EKP.pair[pn] + EKP.window[EWN[ew]][pn] + EKP.lean_killer_per_1k * (eLead ? sd(s) * eLead[k] / 1000 : 0) + EKP.lean_victim_per_1k * (eLead ? sd(o) * eLead[v] / 1000 : 0);
              if(j > 0) x_ += EKP.follow_killer_in_fight * inv[s].has(k) + EKP.follow_victim_in_fight * inv[o].has(v)
                + EKP.follow_killer_lane_in_fight * (LANEID[k] >= 0 && lanesIn.has(LANEID[k])) + EKP.follow_victim_lane_in_fight * (LANEID[v] >= 0 && lanesIn.has(LANEID[v]));
              pairs.push([k, v]); u.push(x_); }
            const mx = Math.max(...u), [k, v] = rng.pick(pairs, norm(u.map(x_ => Math.exp(x_ - mx))));
            dead[o].add(v);
            const ast = (EKM === "pairs_flat" || EKM === "on_flat") ? aliveK.filter(i => i !== k && !dead[s].has(i) && rng.random() < this.ap[i]) : aliveK.filter(i => i !== k && !dead[s].has(i) && rng.random() < sig(EKA["window " + EWN[ew]] + (i ? EKA["role " + ROLES[i]] : 0)
              + EKA.same_lane_as_killer * (LANEID[i] >= 0 && LANEID[i] === LANEID[k]) + EKA.same_lane_as_victim * (LANEID[i] >= 0 && LANEID[i] === LANEID[v]) + EKA.already_in_fight * (j > 0 && inv[s].has(i))));
            K[s][k]++; D[o][v]++; ast.forEach(i => A[s][i]++); if(!ast.length) SOLO[s][k]++;
            addGold(s, val.kill);
            if(LL && LL.ev){ const g = sd(s), E = LL.ev; gold[k] += g * E.own_kill[k]; gold[v] -= g * E.own_death[v]; ast.forEach(i => { gold[i] += g * E.own_assist[i]; }); }
            inv[s].add(k); ast.forEach(i => inv[s].add(i)); inv[o].add(v); [k, v, ...ast].forEach(i => { if(LANEID[i] >= 0) lanesIn.add(LANEID[i]); });
            net += sd(s); setd(first, "blood", s);
            const tk = at(tf + 3 * j); killLog.push([tk, s, k, v, ast]);
            fk[s]++; note(tk, s, "kill", `${ROLES[k]} kills ${ROLES[v]}` + (ast.length ? "" : " (solo)"), {k, v, ast, f: fid});
            continue;
          }
          const earlyLL = LL && m < 15;
          const wv = earlyLL ? norm(aliveV.map(i => Math.exp(LL.av[i] + LL.bv * sd(o) * lean[i] / 1000))) : norm(aliveV.map(i => this.dw[i]));
          const v = rng.pick(aliveV, wv); dead[o].add(v);
          let aliveK = [0, 1, 2, 3, 4].filter(i => !dead[s].has(i)); if(!aliveK.length) aliveK = [0, 1, 2, 3, 4];
          const wk = earlyLL ? norm(aliveK.map(i => Math.exp(LL.ak[i] + LL.bk * sd(s) * lean[i] / 1000))) : norm(aliveK.map(i => this.kw[i]));
          const k = rng.pick(aliveK, wk);
          const ast = [0, 1, 2, 3, 4].filter(i => i !== k && !dead[s].has(i) && rng.random() < this.ap[i]);
          K[s][k]++; D[o][v]++; ast.forEach(i => A[s][i]++); if(!ast.length) SOLO[s][k]++;
          addGold(s, val.kill);
          if(earlyLL && LL.ev){ const g = sd(s), E = LL.ev; gold[k] += g * E.own_kill[k]; gold[v] -= g * E.own_death[v]; ast.forEach(i => { gold[i] += g * E.own_assist[i]; }); }
          net += sd(s); setd(first, "blood", s);
          const tk = at(tf + 3 * j); killLog.push([tk, s, k, v]);
          fk[s]++; note(tk, s, "kill", `${ROLES[k]} kills ${ROLES[v]}` + (ast.length ? "" : " (solo)"), {k, v, ast, f: fid});
        }
        /* the fight's record for the play-by-play (13 Nov; no random draws): kills each side, the fight type drawn, gold lead going in */
        if(log && (fk[0] || fk[1])) fights.push({t: Math.floor(tf), f: fid, b: fk[0], r: fk[1], type: ftype, gd});
        fid++;
      }
      /* monsters */
      const taker = (kind, feats) => { const c = TAKC[kind] || TAKC.dragon; let xb = c.blue_side + c.per_v1_logit * z;
        for(const f in feats) xb += g0(c, f + "_per_1k", 0) * feats[f] / 1000; return rng.random() < sig(xb) ? 0 : 1; };
      const firstDrag = !dragSeq.length && !elderMode;
      const takeChance = kind => { const c = P.monsters[kind], since = Math.max(0, Math.floor((t0 - nxt[kind !== "elder" ? kind : "dragon"]) / 60));
        return sig(c.intercept + c.spawn_minute * (since === 0) + c["1_min_after"] * (since === 1) + c["4+_min_after"] * (since >= 4)
          + c.per_1k_abs_lead * Math.min(Math.abs(gd) / 1000, 15) + c.fight_this_minute * fought
          + g0(c, "first_dragon", 0) * (kind === "dragon" && firstDrag ? 1 : 0) + g0(c, "objectives_style_sum", 0) * obj_s); };
      const lanef = {gd, jng: roleLead[1], mid: roleLead[2], top: roleLead[0], bot2: roleLead[3] + roleLead[4], net60k: net * 1000, objk: obj_d * 1000, first1k: 1000 * (firstDrag ? 1 : 0)};
      const pickF = ks_ => { const o = {}; ks_.forEach(k => { o[k] = lanef[k]; }); return o; };
      if(nxt.dragon != null && nxt.dragon < t0 + 60){
        const kind = elderMode ? "elder" : "dragon";
        if(rng.random() < takeChance(P.monsters[kind] ? kind : "dragon")){
          const feats = pickF(kind === "dragon" ? ["gd", "jng", "bot2", "mid", "net60k", "objk", "first1k"] : ["gd", "net60k", "objk"]);
          let s;
          if(FDT && kind === "dragon" && firstDrag){ const xb_ = FDT.blue_side + FDT.per_v1_logit * z + ["gd", "jng", "bot2", "mid", "top", "net60k", "objk"].reduce((a_, f_) => a_ + g0(FDT, f_ + "_per_1k", 0) * lanef[f_] / 1000, 0);
            s = rng.random() < sig(xb_) ? 0 : 1; }
          else s = taker(P.taker[kind] ? kind : "dragon", feats);
          const tt = at(Math.max(t0, nxt.dragon) + rng.uniform(0, 50));
          if(kind === "elder"){ elderN[s]++; elderUntil[s] = tt + ELDER_BUFF; nxt.dragon = tt + 360; setd(first, "elder", s); note(tt, s, "elder", "Elder Dragon"); }
          else {
            let ty;
            if(dragSeq.length < 2){ const opts = this.dtypes.map((t, i) => i).filter(i => !dragSeq.includes(this.dtypes[i])); ty = this.dtypes[rng.pick(opts, norm(opts.map(i => this.dprob[i])))]; }
            else { if(soulType == null){ soulType = this.dtypes[rng.pick(this.dtypes.map((t, i) => i), this.dprob)]; } ty = soulType; }
            dragSeq.push(ty); drag[s].push(ty); addGold(s, val.dragon_n);
            setd(first, "dragon", s); setd(ftime, "dragon", tt); note(tt, s, "dragon", `${ty} dragon`);
            if(drag[s].length >= 4 && !elderMode){ soul[s] = ty; elderMode = true; note(tt, s, "soul", `${ty} soul`); }
            nxt.dragon = tt + (elderMode ? 360 : 300);
          }
        }
      }
      for(const kind of ["grub", "herald"]){
        if(!takenOnce[kind] && nxt[kind] < t0 + 60 && P.monsters[kind] && rng.random() < takeChance(kind)){
          const s = taker(kind, pickF(["gd", "jng", "top", "mid", "net60k", "objk"]));
          const tt = at(Math.max(t0, nxt[kind]) + rng.uniform(0, 50)); takenOnce[kind] = true;
          if(kind === "grub"){ const nOwn = rng.random() < P.grubs_split.one_team_all ? 3 : 2;
            grubs[s] += nOwn; grubs[1 - s] += 3 - nOwn; setd(first, "grub", s); addGold(s, val.grub * nOwn); addGold(1 - s, val.grub * (3 - nOwn)); note(tt, s, "grubs", `${nOwn} void grubs`); }
          else { heralds[s]++; heraldT[s] = tt; setd(first, "herald", s); addGold(s, val.herald); note(tt, s, "herald", "Rift Herald"); }
        }
      }
      if(nxt.baron != null && nxt.baron < t0 + 60 && rng.random() < takeChance("baron")){
        const s = taker("baron", pickF(["gd", "net60k", "objk"])), tt = at(Math.max(t0, nxt.baron) + rng.uniform(0, 50));
        barons[s]++; baronUntil[s] = tt + BARON_BUFF; nxt.baron = tt + 360; addGold(s, val.baron);
        setd(first, "baron", s); setd(ftime, "baron", tt); note(tt, s, "baron", "Baron Nashor");
      }
      /* towers: segments lane by lane, then base */
      const sc = SEGC, segPh = g0(cal, "seg_phase", "own") === "own" ? (k => g0(sc, "phase " + k, 0)) : (k => this.segPh[k]);
      for(const s of [0, 1]){
        const sg = sd(s);
        for(let li = 0; li < 3; li++){
          const L = LANES[li]; if(seg[s][li] >= 15) continue;
          const tier = Math.floor(seg[s][li] / 5);
          const xb = sc.intercept + segPh(ph) + sc["tier T2"] * (tier === 1) + sc["tier T3"] * (tier === 2)
            + sc.mid * (L === "MID") + sc.bot * (L === "BOT") + sc.per_1k_lane_lead * clamp(laneLead(s, L) / 1000, -8, 8)
            + sc.per_1k_team_lead * clamp(sg * gd / 1000, -15, 15) + sc.per_v1_logit * sg * z
            + sc.baron * (baronUntil[s] > t0) + sc.elder * (elderUntil[s] > t0)
            + sc.herald_last_3min * (t0 - heraldT[s] < 180) + sc.own_grubs * grubs[s] + g0(sc, "siege_style", 0) * sg * siege_d + g0(sc, "siege_style_sum", 0) * siege_s
            + g0(sc, "net_kills_this_minute", 0) * clamp(sg * net, -5, 5)
            + g0(sc, "T2 x mid", 0) * (tier === 1 && L === "MID") + g0(sc, "T2 x bot", 0) * (tier === 1 && L === "BOT")
            + g0(sc, "T3 x mid", 0) * (tier === 2 && L === "MID") + g0(sc, "T3 x bot", 0) * (tier === 2 && L === "BOT")
            + g0(sc, "T1 early x mid", 0) * (tier === 0 && m < 14 && L === "MID") + g0(sc, "T1 early x bot", 0) * (tier === 0 && m < 14 && L === "BOT") + g0(sc, "tower_segments_down", 0) * (seg[s][li] % 5)
            + (tier ? g0(sc, `T${tier + 1} x phase ${ph}`, 0) : 0) + g0(sc, "minutes_before_14", 0) * (Math.min(m, 14) - 14)
            + g0(sc, "lane_segments_last_minute", 0) * Math.min(5, prevseg[s][li]) + g0(sc, "T3_x_baron", 0) * (tier === 2) * (baronUntil[s] > t0)
            + g0(sc, "net_kills_last_minute", 0) * clamp(sg * prevNet, -5, 5) + g0(sc, "clear_fight_win", 0) * (sg * net >= cutS || sg * prevNet >= cutS);
          let n = 0;
          if(SPC != null){ if(rng.random() < sig(xb)){ const [sz, pz] = this.spush[tier === 0 && m < 14 ? "0_early" : String(tier)]; n = rng.pick(sz, pz); } }
          else n = this.count(rng, Math.exp(xb), "segments", m);
          n = Math.min(n, 15 - seg[s][li]); prevseg[s][li] = n;
          for(let q = 0; q < n; q++){
            seg[s][li]++;
            addGold(s, m < 14 ? val.plate_early : val.plate);
            if(LL && LL.ev){
              if(LL.ev.own_lane_plate){ if(m < 15){ const own = [...LANE_ROLES[L], 1]; for(let i = 0; i < 5; i++) gold[i] += sg * (own.includes(i) ? LL.ev.own_lane_plate[i] : LL.ev.other_lane_plate[i]); } }
              else if(m < 14){ for(let i = 0; i < 5; i++) gold[i] += sg * LL.ev.team_plate[i]; }
            }
            if(seg[s][li] % 5 === 0){ towers[s]++; addGold(s, val.tower); setd(first, "tower", s); const twt = at(t0 + rng.uniform(0, 59)); setd(ftime, "tower", EO ? twt : t0 + 30); setd(firstLane, "tower", L);
              note(twt, s, "tower", `T${seg[s][li] / 5} ${L}`); }
          }
        }
        const opn = [0, 1, 2].filter(li => seg[s][li] >= 15);
        opn.forEach(li => { if(openT[s][li] == null) openT[s][li] = t0; });
        if(!opn.length) continue;
        let down = [0, 1, 2].filter(li => inhibBack[s][li] > t0);
        const bc = PUSHC;
        const xb = bc.intercept + bc["from 25"] * (m >= 25) + bc["from 35"] * (m >= 35) + bc.per_1k_lead * clamp(sg * gd / 1000, -15, 15)
          + bc.per_v1_logit * sg * z + bc.baron * (baronUntil[s] > t0) + bc.elder * (elderUntil[s] > t0)
          + bc.enemy_inhibs_down * down.length + bc.open_lanes * opn.length + g0(bc, "siege_style", 0) * sg * siege_d + g0(bc, "siege_style_sum", 0) * siege_s
          + g0(bc, "lane_just_opened", 0) * opn.some(li => openT[s][li] >= t0 - 60)
          + g0(bc, "base_take_last_minute", 0) * (lastBase[s] >= t0 - 60)
          + g0(bc, "net_kills_this_minute", 0) * clamp(sg * net, -5, 5)
          + g0(bc, "net_kills_last_minute", 0) * clamp(sg * prevNet, -5, 5) + g0(bc, "clear_fight_win", 0) * (sg * net >= cutB || sg * prevNet >= cutB)
          + (g0(bc, "net_kills_this_minute_x_time", 0) * clamp(sg * net, -5, 5) + g0(bc, "net_kills_last_minute_x_time", 0) * clamp(sg * prevNet, -5, 5)) * (m - 25) / 10;
        const [sz, prz] = this.push[down.length ? "inhib_down" : "no_inhib_down"];
        const npush = rng.random() < sig(xb) ? rng.pick(sz, prz) : 0;
        if(npush) lastBase[s] = t0;
        for(let q = 0; q < npush; q++){
          down = [0, 1, 2].filter(li => inhibBack[s][li] > t0);
          const upInh = opn.filter(li => inhibBack[s][li] <= t0), tt = at(t0 + rng.uniform(0, 59));
          if(down.length && (!upInh.length || rng.random() < P.nexus_tier_share)){
            if(nxTowers[s] > 0){ nxTowers[s]--; towers[s]++; addGold(s, val.tower); note(tt, s, "tower", "nexus tower"); }
            else { winner = s; tEnd = tt; note(tt, s, "nexus", "Nexus"); break; }
          } else if(upInh.length){ const li = rng.pickUniform(upInh); inhibBack[s][li] = tt + INHIB_BACK; inhibs[s]++; addGold(s, val.inhib); note(tt, s, "inhib", `inhibitor ${LANES[li]}`); }
        }
        if(winner != null) break;
      }
      if(winner != null) break;
    }
    let capped = false;
    if(winner == null){ winner = gd >= 0 ? 0 : 1; tEnd = 60 * cal.max_min; capped = true; }
    const sec = Math.floor(tEnd), mins = sec / 60, tk = [K[0].reduce((a, b) => a + b, 0), K[1].reduce((a, b) => a + b, 0)];
    const ps = {};
    [0, 1].forEach(s => { const side = ["blue", "red"][s], sg = sd(s); ps[side] = {};
      const kp = ROLES.map((r, i) => (K[s][i] + A[s][i]) / Math.max(1, tk[s]));
      const dm = norm(ROLES.map((r, i) => { const b = P.box[r]; return Math.max(0.02, b.dmg_mean + b.dmg_per_kp * (kp[i] - b.kp_mean) + rng.normal(0, b.dmg_sd_resid)); }));
      const r15 = kd.roles15 || farm.map((f, i) => f + gold[i]);
      ROLES.forEach((r, i) => { const b = P.box[r];
        ps[side][r] = {k: K[s][i], d: D[s][i], a: A[s][i], kp: Math.round(kp[i] * 1000) / 1000, dmgS: Math.round(dm[i] * 1000) / 1000,
          csd: Math.round(sg * b.cs_per_1k_gold_15 * r15[i] / 1000), vis: Math.floor(Math.max(0, rng.normal(b.vspm_mean, b.vspm_sd)) * mins), solo: SOLO[s][i]}; }); });
    const nan5 = [NaN, NaN, NaN, NaN, NaN];
    return {winner: ["blue", "red"][winner], sec, kills: tk, ps, dr: drag, soul, elders: elderN, ba: barons, grubs, heralds, towers, inhibs,
      first: Object.fromEntries(Object.entries(first).map(([k, v]) => [k, ["blue", "red"][v]])), first_t: Object.fromEntries(Object.entries(ftime).map(([k, v]) => [k, Math.floor(v)])),
      roles5: kd.roles5 || nan5, g15: gdAt[15] != null ? gdAt[15] : NaN, gd: gdAt, roles15: kd.roles15 || nan5, roles10: kd.roles10 || nan5,
      kd15: kd.kd15 || ROLES.map((r, i) => (K[0][i] - D[0][i]) - (K[1][i] - D[1][i])), first_tower_lane: firstLane.tower || "",
      capped, steps: log ? steps.sort((a, b) => a.t - b.t) : [], fights};
  }
}
/* ---- app bridge (sim session 4, 13 Nov): the sim's inputs from js/sim-tables.js, as research/sim4/s4_tables.py builds them ----
   ids are the app's team ids (e.g. "GEN"); champs = {top, jng, mid, bot, sup} champion names. Lookups missing from the tables count 0
   (as in the fit: a champion or pair never seen adds nothing). */
const lg1 = n => Math.log1p(n || 0);
/* v1, who wins before the draft (research/local/sim1/v1_all/v1_league_fresh.py): team part, plus each player's skill estimates with the
   league shift for the home league, blue minus red */
function v1z(T, blueId, redId){
  const V = T.v1, tb = V.teams[blueId] || {team: 0, league: 0, home: ""}, tr = V.teams[redId] || {team: 0, league: 0, home: ""};
  const team = (tb.team + tb.league - tr.team - tr.league + V.blue) / V.temp * V.w.team_part;
  let players = 0;
  [[blueId, tb, 1], [redId, tr, -1]].forEach(([id, t, sg]) => { const Lh = V.league_strength[t.home] || 0;
    ROLES.forEach(r => { const p = T.players[id + "|" + r]; if(!p) return;
      T.main_skills[r].forEach(f => { const e = p.skills[f]; if(e != null) players += sg * (V.w[r + "_" + f] || 0) * (e + V.league_shift[r] * Lh); }); }); });
  return {z: team + players, team, players};
}
function sideFeats(T, id, champs){
  const f = {}, st = {siege: 0, objectives: 0, skirmish: 0, pace: 0}, SK = {siege: "sieg", objectives: "obje", skirmish: "skir", pace: "pace"};
  ROLES.forEach(r => { const c = champs[r], cr = (T.champs[c] || {})[r] || {}, p = T.players[id + "|" + r];
    f["comfort_" + r] = lg1(((T.comfort[id + "|" + r]) || {})[c]); f["strength_" + r] = cr.str || 0;
    f["cgold_" + r] = cr.cgold || 0; f["ckd_" + r] = cr.ckd || 0; f["skill_" + r] = p && p.lane_skill != null ? p.lane_skill : null;
    for(const k in st) st[k] += cr[SK[k]] || 0; });
  f.together = lg1(T.together[id]); f.synergy = T.synergy[champs.bot + "|" + champs.sup] || 0;
  return {f, st};
}
/* x for Sim.run, plus what the result screen shows "on paper" (each role's expected gold lead at 15, blue minus red) */
function inputs(T, blueId, redId, champsB, champsR){
  const V = v1z(T, blueId, redId), B = sideFeats(T, blueId, champsB), R = sideFeats(T, redId, champsR), LLF = T.P.lane_level;
  ROLES.forEach(r => { if(B.f["skill_" + r] == null || R.f["skill_" + r] == null){ B.f["skill_" + r] = 0; R.f["skill_" + r] = 0; } });
  const m0 = [], e0 = [], exp15 = [];
  ROLES.forEach(r => { const cs = LLF.inputs[r], c = LLF.coef[r], cp = LLF.coef_pregame[r];
    m0.push(cs.reduce((s, k) => s + c[k] * (B.f[k] - R.f[k]), c.const)); e0.push(cs.reduce((s, k) => s + cp[k] * (B.f[k] - R.f[k]), cp.const));
    exp15.push(m0[m0.length - 1] + c.z * V.z); });
  const sb = B.st, sr = R.st;
  return {x: {z: V.z, ll_m0: m0, ll_e0: e0, siege_d: sb.siege - sr.siege, obj_d: sb.objectives - sr.objectives, skirm_d: sb.skirmish - sr.skirmish,
    pace_s: sb.pace + sr.pace, siege_s: sb.siege + sr.siege, obj_s: sb.objectives + sr.objectives}, v1: V, exp15, featB: B.f, featR: R.f};
}
/* Player of the Game, version C (research/sim4/s4_pog.py; Luke 6 Nov): each player's score from the box score plus the fitted role term
   (the award model's full score). Rating, one scale for every role (Luke 14 Nov: supports rated too high): that full score's percentile
   among all real major-league player-games (2026, before the tables' cutoff), / 10. The reference has the same number of games in each
   role, so the all-role percentile is the average of the within-role percentiles of (full score - that role's term).
   The award goes to the winner with the highest full score (research/sim4/pog_options_test.py: right 52% on held-out award games v 41%
   for a draw); pogChances still gives each winner's fitted chance for display.
   st = {k, d, a, kp, dmgS, csd, vpm} */
const POG_X = {kills: "k", deaths: "d", assists: "a", kp: "kp", damageshare: "dmgS", csd15: "csd", vspm: "vpm"};
function pogScore(T, st){ const G = T.pog; let s = 0; for(const c in POG_X) s += G.w[c] * (st[POG_X[c]] - G.mean[c]) / G.sd[c]; return s; }
function pctIn(q, s){
  if(s <= q[0]) return 0; if(s >= q[q.length - 1]) return 100;
  let i = 0; while(q[i + 1] < s) i++;
  const lo = q[i], hi = q[i + 1]; return i + (hi > lo ? (s - lo) / (hi - lo) : 0.5);
}
function pogRating(T, role, st){
  const w = T.pog.w, u = pogScore(T, st) + (w["r_" + role] || 0);
  return ROLES.reduce((a, r) => a + pctIn(T.pog.pct[r], u - (w["r_" + r] || 0)), 0) / ROLES.length / 10;
}
function pogChances(T, stats){  /* stats[role] for the winning side → {role: chance} */
  const u = ROLES.map(r => pogScore(T, stats[r]) + (T.pog.w["r_" + r] || 0)), mx = Math.max(...u), e = u.map(x => Math.exp(x - mx)), s = e.reduce((a, b) => a + b, 0);
  const o = {}; ROLES.forEach((r, i) => { o[r] = e[i] / s; }); return o;
}
window.SIM_ENGINE = {Sim, RNG, ROLES, v1z, inputs, pogScore, pogRating, pogChances};
})();
