# common.sh - sourced by the node scripts. Layout (everything under ROOT, derived from this file's location when the
# repository is deployed at $ROOT/src/inkbench; override with INKBENCH_ROOT):
#   $ROOT/src/inkbench        this repository
#   $ROOT/venv-inkbench       the venv: CPython 3.14, torch, inksweep, villa's vesuvius package, inkbench
#   $ROOT/data                benchmark inputs (about 30 GB)        $ROOT/results       maps, scores, tables
#   $ROOT/checkpoints         reader weights (sha256-pinned)        $ROOT/logs          logs and PID files
#   $ROOT/villa-<commit>      the organisers' villa repository (vesuvius package only)
# Durable copies of the small result files go to $DURABLE_DIR when it is set.
# GPU / CPU pinning: GPUS (default 0) and CPUS (default: every core); jobs run with nice -n 10.
set -euo pipefail
NODE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$NODE_DIR/.." && pwd)
ROOT=${INKBENCH_ROOT:-$(cd "$REPO/../.." && pwd)}
VENV=${INKBENCH_VENV:-$ROOT/venv-inkbench}
PY=$VENV/bin/python
IB=$VENV/bin/inkbench
LOGS=$ROOT/logs
VILLA_COMMIT=0fb38c45b488e192566ea83ae36369cb6db92652      # the villa commit inksweep 0.1.0 runs
VILLA=$ROOT/villa-${VILLA_COMMIT:0:8}
PYV=${PYV:-3.14.10}             # an exact final CPython release (villa's vesuvius package needs 3.14)
UV=${UV:-$(command -v uv || echo /usr/local/bin/uv)}
GPUS=${GPUS:-0}
CPUS=${CPUS:-0-$(($(nproc) - 1))}
DURABLE_DIR=${DURABLE_DIR:-}
export INKBENCH_ROOT=$ROOT INKBENCH_DATA=$ROOT/data INKBENCH_RESULTS=$ROOT/results INKBENCH_CKPT=$ROOT/checkpoints
export UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT:-600} UV_LINK_MODE=copy PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-8}
mkdir -p "$INKBENCH_DATA" "$INKBENCH_RESULTS" "$LOGS"

# log_to NAME: tee everything to $LOGS/NAME.log, record the PID, report the exit status
log_to() {
  local name=$1
  LOG=$LOGS/$name.log
  echo $$ > "$LOGS/$name.pid"
  exec > >(tee -a "$LOG") 2>&1
  echo "== $(date -u +%FT%TZ) $name start (pid $$, host $(hostname), GPUS=$GPUS CPUS=$CPUS)"
  trap 'rc=$?; echo "== $(date -u +%FT%TZ) '"$name"' exit $rc"; rm -f "$LOGS/'"$name"'.pid"' EXIT
}

require_ready() {
  [[ -f $VENV/READY ]] || { echo "inkbench venv not ready: run node/setup_inkbench.sh"; exit 3; }
  [[ -f $VENV/TESTS_OK ]] || echo "WARNING: the test suite did not pass at setup (see $LOGS/setup_inkbench.log)"
}

# pinned CMD...: run on the configured GPUs and CPUs at low priority
pinned() { CUDA_VISIBLE_DEVICES=$GPUS nice -n 10 taskset -c "$CPUS" "$@"; }

# durable_copy SRC SUBDIR: copy the small result files (json, md, log) to the durable folder, if configured;
# maps, block statistics and benchmark data stay on the node
durable_copy() {
  [[ -n $DURABLE_DIR ]] || { echo "(DURABLE_DIR not set: no durable copy of $1)"; return 0; }
  [[ -d $1 ]] || { echo "(nothing to copy: $1)"; return 0; }
  local dest=$DURABLE_DIR/$2
  mkdir -p "$dest"
  rsync -a --prune-empty-dirs --exclude='preds/' --include='*/' --include='*.json' --include='*.jsonl' \
        --include='*.md' --include='*.log' --exclude='*' "$1"/ "$dest"/ && echo "copied results of $1 -> $dest"
}
