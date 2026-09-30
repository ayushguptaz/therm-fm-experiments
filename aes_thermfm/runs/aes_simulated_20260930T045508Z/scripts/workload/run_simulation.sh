#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:?Specify absolute run root}
PYTHON=${2:?Specify Python executable}
IMAGE=${SIM_IMAGE:-aes-thermfm-sim:20260930}
mkdir -p "$ROOT/outputs/workload" "$ROOT/logs"
"$PYTHON" "$ROOT/scripts/workload/generate_vectors.py" --root "$ROOT" > "$ROOT/logs/generate_vectors.log"
docker image inspect "$IMAGE" > "$ROOT/outputs/simulator_image.json"
docker run --rm --cpus=2 --memory=4g -v "$ROOT:/work" "$IMAGE" bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
mkdir -p /work/inputs/workload
yosys -p "read_liberty -ignore_miss_func /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib; write_verilog -noattr /work/inputs/workload/nangate45_sim.v" > /work/logs/liberty_to_sim.log
iverilog -V > /work/outputs/iverilog_version.txt 2>&1
iverilog -g2012 -s aes_workload_tb -o /work/outputs/workload/aes_sim.vvp /work/scripts/workload/aes_workload_tb.v /work/flow/results/nangate45/aes/base/6_final.v /work/inputs/workload/nangate45_sim.v
for workload in busy gapped; do
  gap=0; if [ "$workload" = gapped ]; then gap=16; fi
  vvp /work/outputs/workload/aes_sim.vvp +GAP=$gap +VCD=/work/outputs/workload/$workload.raw.vcd > /work/logs/simulation_$workload.log 2>&1
  grep -q "PASS blocks=272" /work/logs/simulation_$workload.log
  python3 /work/scripts/workload/rebase_vcd.py /work/outputs/workload/$workload.raw.vcd /work/outputs/workload/$workload.vcd
  WORKLOAD=$workload openroad -exit /work/scripts/workload/export_vcd_power.tcl > /work/logs/power_$workload.log 2>&1
 done
'
