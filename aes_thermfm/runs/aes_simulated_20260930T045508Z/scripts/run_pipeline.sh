#!/usr/bin/env bash
# Linux + Docker, with the archived vendor directory and compatible Python env.
set -euo pipefail
ROOT=${1:?Usage: bash scripts/run_pipeline.sh ABSOLUTE_ROOT PYTHON_EXECUTABLE}
PYTHON=${2:?Specify the Python executable with Therm-FM dependencies}
IMAGE='openroad/orfs@sha256:94d3c1c19b47e8ef2c3a9b32cb9dc6e5c18817ffb71f03e28ec67d6fa0a44512'
test -d "$ROOT/vendor/checkpoint_IND8C_GWL2_T"
bash "$ROOT/scripts/run_openroad.sh" "$ROOT"
docker run --rm --cpus=2 --memory=4g -v "$ROOT:/work" "$IMAGE" bash -c \
  'source /OpenROAD-flow-scripts/env.sh; openroad -exit /work/scripts/export_power.tcl' \
  > "$ROOT/logs/export_power.log" 2>&1
"$PYTHON" "$ROOT/scripts/build_inputs.py" --root "$ROOT" > "$ROOT/logs/build_inputs.log" 2>&1
"$PYTHON" "$ROOT/scripts/infer.py" \
  --repo "$ROOT/vendor/Therm-FM" \
  --checkpoint "$ROOT/vendor/checkpoint_IND8C_GWL2_T" \
  --input "$ROOT/inputs/thermfm/input.mat" \
  --output-dir "$ROOT/outputs/aes_inference" > "$ROOT/logs/aes_inference.log" 2>&1
"$PYTHON" "$ROOT/scripts/analyze_results.py" --root "$ROOT" > "$ROOT/logs/analyze_results.log" 2>&1
