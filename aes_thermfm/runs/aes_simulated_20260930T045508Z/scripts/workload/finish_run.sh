#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:?Specify root}
PYTHON=${2:?Specify Python}
bash "$ROOT/scripts/workload/run_simulation.sh" "$ROOT" "$PYTHON"
"$PYTHON" "$ROOT/scripts/workload/audit_activity.py" --root "$ROOT" > "$ROOT/logs/activity_audit.log"
"$PYTHON" "$ROOT/scripts/build_inputs.py" --root "$ROOT" --power-cases busy gapped --power-source simulated_workload > "$ROOT/logs/build_inputs.log"
"$PYTHON" "$ROOT/scripts/infer.py" --repo "$ROOT/vendor/Therm-FM" --checkpoint "$ROOT/vendor/checkpoint_IND8C_GWL2_T" --input "$ROOT/inputs/thermfm/input.mat" --output-dir "$ROOT/outputs/aes_inference" > "$ROOT/logs/aes_inference.log" 2>&1
"$PYTHON" "$ROOT/scripts/workload/summarize.py" --root "$ROOT" > "$ROOT/logs/summarize.log" 2>&1
printf 'PASS\n' > "$ROOT/outputs/workload/pipeline_status.txt"
