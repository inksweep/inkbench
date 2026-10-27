#!/bin/bash
# setup_inkbench.sh - idempotent setup of inkbench on a Linux GPU node.
#
#   bash node/setup_inkbench.sh       [INKBENCH_ROOT=/data/inkbench] [UV=/path/to/uv] [PYV=3.14.10] [GPUS=0] [CPUS=0-15]
#
# Steps (each skipped when done; log: $ROOT/logs/setup_inkbench.log; writes $VENV/READY at the end):
#   1 uv >= 0.9 (an older uv only knows CPython 3.14 pre-releases, on which torch's cp314 wheels crash; a pinned uv is
#     then installed under $ROOT/tools), CPython $PYV (an exact final release), the venv $ROOT/venv-inkbench
#   2 torch + torchvision from the PyTorch cu129 index (as an extra index), everything else from PyPI
#     (node/requirements.txt); then OpenCV's manylinux2014 wheel, pinned by sha256, on Linux x86_64 (the manylinux_2_28
#     wheels bundle an OpenSSL whose FIPS self-test aborts `import cv2` on FIPS kernels)
#   3 ScrollPrize/villa at $VILLA_COMMIT (blob-less sparse checkout of vesuvius/ only; the GPL volume-cartographer tree
#     is not checked out), its vesuvius package installed with --no-deps
#   4 inksweep 0.1.0 from PyPI and inkbench (editable), both --no-deps (step 2 installed their dependencies)
#   5 import and CUDA checks; the checkpoints of every default reader, sha256-verified, into $ROOT/checkpoints
#   6 the test suite (CPU) -> TESTS_OK; READY
set -euo pipefail
source "$(dirname "$0")/common.sh"
log_to setup_inkbench
UV_MIN=0.9
UV_PIN=${UV_PIN:-0.13.6}
TOOLS=$ROOT/tools
TORCH_SPEC=${TORCH_SPEC:-torch==2.13.0+cu129}
TORCHVISION_SPEC=${TORCHVISION_SPEC:-torchvision==0.28.0+cu129}     # timm (imported by villa's model builder) needs it
TORCH_INDEX=${TORCH_INDEX:-https://download.pytorch.org/whl/cu129}
INKSWEEP_SPEC=${INKSWEEP_SPEC:-inksweep==0.1.0}
OPENCV_WHEEL_URL=https://files.pythonhosted.org/packages/2b/97/8170e9819764c47e436c130d3ff6cfb73b58f923eae9d3a03d8982b04aec/opencv_python_headless-5.0.0.93-cp37-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
OPENCV_WHEEL_SHA256=09a872a157c1376ab922a69bbf22f9a95bcc7b658a9d8b436a60212b02b2eeb4
step() { echo "-- $*"; }
version_ge() { [[ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" == "$2" ]]; }   # $1 >= $2
uv_version() { "$1" --version | awk '{print $2}'; }

step "1 uv, python $PYV, venv"
[[ -n $UV && -x $UV ]] || { echo "uv not found: set UV=/path/to/uv (uv >= $UV_MIN)"; exit 2; }
if ! version_ge "$(uv_version "$UV")" "$UV_MIN"; then
  echo "uv $(uv_version "$UV") is older than $UV_MIN: installing uv $UV_PIN under $TOOLS"
  if [[ ! -x $TOOLS/uv-$UV_PIN/bin/uv ]]; then
    "$UV" venv -q --python 3.12 "$TOOLS/uv-$UV_PIN"
    "$UV" pip install -q --python "$TOOLS/uv-$UV_PIN/bin/python" "uv==$UV_PIN"
  fi
  UV=$TOOLS/uv-$UV_PIN/bin/uv
fi
echo "uv: $UV ($(uv_version "$UV"))"
"$UV" python install "$PYV"
[[ -x $PY ]] || "$UV" venv --python "$PYV" "$VENV"
"$PY" -c 'import sys; assert sys.version_info.releaselevel == "final", sys.version; print("python", sys.version.split()[0])' \
  || { echo "$VENV runs a pre-release Python; delete it and rerun"; exit 2; }

step "2 torch + pinned packages"
REQ_SHA=$(sha256sum "$NODE_DIR/requirements.txt" | cut -d' ' -f1)
if [[ ! -f $VENV/.torch_ok ]]; then
  "$UV" pip install --python "$PY" --extra-index-url "$TORCH_INDEX" "$TORCH_SPEC" "$TORCHVISION_SPEC"
  touch "$VENV/.torch_ok"
fi
if [[ $(cat "$VENV/.deps_ok" 2>/dev/null) != "$REQ_SHA" ]]; then    # re-run whenever the pins change
  "$UV" pip install --python "$PY" -r "$NODE_DIR/requirements.txt"
  "$PY" -c "import torch; assert torch.__version__.startswith('${TORCH_SPEC#torch==}'.split('+')[0]), torch.__version__"
  echo "$REQ_SHA" > "$VENV/.deps_ok"
  rm -f "$VENV/.opencv_manylinux2014_ok"
fi
if [[ $(uname -s) == Linux && $(uname -m) == x86_64 && ! -f $VENV/.opencv_manylinux2014_ok ]]; then
  [[ $(cat /proc/sys/crypto/fips_enabled 2>/dev/null || echo 0) == 1 ]] && echo "FIPS kernel: OpenCV's manylinux2014 build is required"
  WHL=$ROOT/wheels/$(basename "$OPENCV_WHEEL_URL")
  if [[ ! -f $WHL ]] || ! echo "$OPENCV_WHEEL_SHA256  $WHL" | sha256sum -c --quiet - 2>/dev/null; then
    mkdir -p "$ROOT/wheels"
    curl -fsSL --retry 5 "$OPENCV_WHEEL_URL" -o "$WHL.part"
    echo "$OPENCV_WHEEL_SHA256  $WHL.part" | sha256sum -c --quiet - || { echo "OpenCV wheel sha256 mismatch"; exit 2; }
    mv "$WHL.part" "$WHL"
  fi
  "$UV" pip install --python "$PY" --reinstall --no-deps "$WHL"
  touch "$VENV/.opencv_manylinux2014_ok"
fi
"$PY" -c "import cv2; print('cv2', cv2.__version__)" || { echo "import cv2 fails in $VENV"; exit 2; }

step "3 villa $VILLA_COMMIT"
if [[ ! -d $VILLA/.git ]]; then
  git clone -q --filter=blob:none --no-checkout https://github.com/ScrollPrize/villa.git "$VILLA"
  git -C "$VILLA" sparse-checkout set --cone vesuvius
fi
if [[ $(git -C "$VILLA" rev-parse HEAD 2>/dev/null || true) != "$VILLA_COMMIT" ]]; then
  git -C "$VILLA" fetch -q --filter=blob:none origin "$VILLA_COMMIT" || true
  git -C "$VILLA" checkout -q "$VILLA_COMMIT"
fi
[[ $(git -C "$VILLA" rev-parse HEAD) == "$VILLA_COMMIT" ]] || { echo "villa is not at $VILLA_COMMIT"; exit 2; }
if [[ ! -f $VENV/.villa_ok ]]; then
  "$UV" pip install --python "$PY" --no-deps -e "$VILLA/vesuvius"
  touch "$VENV/.villa_ok"
fi

step "4 inksweep + inkbench"
"$UV" pip install --python "$PY" --no-deps "$INKSWEEP_SPEC"
"$UV" pip install --python "$PY" --no-deps -e "$REPO"

step "5 import, CUDA and checkpoint checks"
CUDA_VISIBLE_DEVICES=$GPUS "$PY" - <<'PYEOF'
import cv2, numpy, torch, zarr
import inkbench, inksweep
from vesuvius.ink_detection.models.model import make_model  # noqa: F401
print("inkbench", inkbench.__version__, "inksweep", inksweep.__version__, "numpy", numpy.__version__,
      "zarr", zarr.__version__, "torch", torch.__version__, "cv2", cv2.__version__)
print("cuda", torch.cuda.is_available(), torch.cuda.device_count(), "GPUs visible")
assert torch.cuda.is_available(), "no CUDA"
PYEOF
"$PY" - <<'PYEOF'
from inksweep.readers import get_reader
from inkbench.cli import PREDICT_READERS
from inkbench.predict import fetch_checkpoint
for name in PREDICT_READERS.split(","):
    for key in get_reader(name).checkpoints:
        print(name, key, fetch_checkpoint(key))
PYEOF

step "6 tests"
rm -f "$VENV/TESTS_OK"
if (cd "$REPO" && CUDA_VISIBLE_DEVICES= nice -n 10 taskset -c "$CPUS" "$PY" -m pytest -q tests); then
  touch "$VENV/TESTS_OK"
else
  echo "WARNING: tests failed (see above); READY is still written so the evaluation can report"
fi
date -u +%FT%TZ > "$VENV/READY"
echo "READY: $VENV"
