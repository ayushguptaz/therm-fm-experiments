#!/usr/bin/env bash
# Full fresh RTL-to-temperature run. Requires Docker and a compatible Python environment.
set -euo pipefail
ROOT=${1:?Usage: bash scripts/run_simulated_pipeline.sh NEW_ABSOLUTE_ROOT PYTHON VENDOR_ROOT}
PYTHON=${2:?Specify Python executable}
VENDOR=${3:?Specify vendor directory containing model source and checkpoint weights}
SCRIPTS=$(cd "$(dirname "$0")" && pwd)
test ! -e "$ROOT"
test -f "$VENDOR/checkpoint_IND8C_GWL2_T/pytorch_model.bin"
mkdir -p "$ROOT/vendor" "$ROOT/logs"
cp -R "$SCRIPTS" "$ROOT/scripts"
ln -s "$VENDOR/Therm-FM" "$ROOT/vendor/Therm-FM"
ln -s "$VENDOR/checkpoint_IND8C_GWL2_T" "$ROOT/vendor/checkpoint_IND8C_GWL2_T"
docker build -t aes-thermfm-sim:20260930 -f "$ROOT/scripts/workload/Dockerfile.sim" "$ROOT/scripts/workload" > "$ROOT/logs/simulator_build.log" 2>&1
bash "$ROOT/scripts/workload/run_physical.sh" "$ROOT"
bash "$ROOT/scripts/workload/finish_run.sh" "$ROOT" "$PYTHON"
