#!/bin/bash
# 14 Nov: short Worlds test (94 games, 1,000 sims, seeds by game ID) for death timers (A) and A + pushes follow dead players with real timing (B, C);
# same inputs as research/local/sim4/ek/run_fdt.sh (tables fitted before 1 Sep, lane-level version 2). Run from the repo root.
set -euo pipefail
L=research/local/sim3; D=research/local/sim4/spread
export S3_TEST_LEAGUE=WLDs S3_LL_DIR=$L/ll_fit2
T="$D/params/params3.json $L/out_11nov/lanes3_features.csv research/model/sim2/v1_games.csv research/model/sim3/targets3.json $L/out/tl_fights.csv $L/out_11nov/comp3_games.csv"
for v in "typed,pf,ll,fpl,ekc,eo,fdt,dt:w_dt" "typed,pf,ll,fpl,ekc,eo,fdt,dt,dp:w_dtdp"; do o=${v%%:*}; d=${v##*:}
  t0=$(date +%s); echo "[$(date +%H:%M:%S)] $d start"; python -I research/sim3/s3_test.py $T $D/$d 1000 timing $o > $D/log_$d.txt 2>&1; echo "[$(date +%H:%M:%S)] $d done ($(( $(date +%s) - t0 )) s)"
done
