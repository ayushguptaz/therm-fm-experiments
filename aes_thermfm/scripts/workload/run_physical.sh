#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:?Specify a fresh absolute run directory}
IMAGE='openroad/orfs@sha256:94d3c1c19b47e8ef2c3a9b32cb9dc6e5c18817ffb71f03e28ec67d6fa0a44512'
mkdir -p "$ROOT"/{logs,inputs,outputs,flow,vendor}
test ! -e "$ROOT/flow/results/nangate45/aes/base/6_final.odb"
docker image inspect "$IMAGE" > "$ROOT/outputs/openroad_image.json"
docker run --rm --cpus=4 --memory=8g -v "$ROOT:/work" "$IMAGE" bash -c '
set -euo pipefail
cd /OpenROAD-flow-scripts
source ./env.sh
mkdir -p /work/inputs/rtl /work/inputs/orfs_config
cp flow/designs/src/aes/* /work/inputs/rtl/
cp flow/designs/nangate45/aes/* /work/inputs/orfs_config/
cp flow/platforms/nangate45/config.mk /work/inputs/orfs_config/platform_config.mk
cp LICENSE_BUILD_RUN_SCRIPTS /work/vendor/ORFS_LICENSE
sed -i "s/set clk_period 0.82/set clk_period 2.0/" /work/inputs/orfs_config/constraint.sdc
# Explicitly consume the archived starting inputs, not another design copy.
cp /work/inputs/orfs_config/config.mk /work/inputs/orfs_config/run_config.mk
cat >> /work/inputs/orfs_config/run_config.mk <<CONFIG
export VERILOG_FILES = \$(sort \$(wildcard /work/inputs/rtl/*.v))
export SDC_FILE = /work/inputs/orfs_config/constraint.sdc
export FLOORPLAN_DEF = /work/inputs/orfs_config/aes_ng45_fp.def
CONFIG
openroad -version > /work/outputs/openroad_version.txt
yosys -V > /work/outputs/yosys_version.txt
cd flow
make DESIGN_CONFIG=/work/inputs/orfs_config/run_config.mk WORK_HOME=/work/flow NUM_CORES=4
' > "$ROOT/logs/openroad_flow.log" 2>&1
