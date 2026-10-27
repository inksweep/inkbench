#!/bin/bash
# run_inkbench_eval.sh - the whole evaluation: fetch -> predict -> score -> ensemble -> table (each stage resumable).
#
#   bash node/run_inkbench_eval.sh                               # every benchmark, the published readers and ensembles
#   STAGES=table bash node/run_inkbench_eval.sh                  # re-print the tables only
#   BENCH=p0841,p1447 READERS=readerv3,readerv2 ENSEMBLES= bash node/run_inkbench_eval.sh   # a subset, no ensembles
#   PLUGINS="mine=/path/plugin.py:/path/ckpt.pt" bash node/run_inkbench_eval.sh   # add a reader of your own
#
# Prints TABLE.md (results with 95 % block-bootstrap intervals and leakage flags; the reproduction of the published
# numbers; paired comparisons against Reader V3) and copies the small result files to $DURABLE_DIR/inkbench when set.
# Exits non-zero if a stage fails; STRICT=1 also exits 3 when a reproduction row FAILs.
# Prediction uses the GPUs in GPUS (one worker each); every other stage runs on the CPUs in CPUS.
set -euo pipefail
source "$(dirname "$0")/common.sh"
log_to run_inkbench_eval
require_ready
STAGES=${STAGES:-fetch,predict,score,ensemble,table}
BENCH=${BENCH:-all}
READERS=${READERS:-readerv3,readerv2,d9v4c,dnative,hecate,v8in,v8in_released,ink9_s42,ink9_s43_060k}
ENSEMBLES=${ENSEMBLES-ens_recipe343=dnative,hecate,ink9_s42,ink9_s43 ens_v3_hecate_d9v4c=readerv3,hecate,d9v4c ens_v3_hecate=readerv3,hecate}
PLUGINS=${PLUGINS:-}
plugin_args=()
for p in $PLUGINS; do plugin_args+=(--plugin "$p"); done
# the readers to predict: the scored readers plus every ensemble member
members=$(for e in $ENSEMBLES; do echo "${e#*=}"; done | tr ',' '\n')
PREDICT=$(printf '%s\n' ${READERS//,/ } $members | awk 'NF && !seen[$0]++' | paste -sd, -)
strict=()
[[ ${STRICT:-0} == 1 ]] && strict=(--strict)
cpu() { CUDA_VISIBLE_DEVICES= nice -n 10 taskset -c "$CPUS" "$@"; }
rc=0
for stage in ${STAGES//,/ }; do
  echo "== stage $stage"
  case $stage in
    fetch)    cpu "$IB" fetch --bench "$BENCH" ;;
    predict)  pinned "$IB" predict --bench "$BENCH" --readers "$PREDICT" "${plugin_args[@]}" ;;
    score)    cpu "$IB" score --bench "$BENCH" --readers "$READERS" "${plugin_args[@]}" ;;
    ensemble) [[ -z $ENSEMBLES ]] || cpu "$IB" ensemble --bench "$BENCH" $ENSEMBLES ;;
    table)    cpu "$IB" table "${strict[@]}" || rc=$? ;;
    *)        echo "unknown stage $stage"; exit 2 ;;
  esac
done
durable_copy "$INKBENCH_RESULTS" inkbench
exit $rc
