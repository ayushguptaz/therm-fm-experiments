#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:-/home/ubuntu/aes_thermfm_20260929}
IMAGE='openroad/orfs@sha256:94d3c1c19b47e8ef2c3a9b32cb9dc6e5c18817ffb71f03e28ec67d6fa0a44512'
mkdir -p "$ROOT"/{logs,inputs,outputs,flow,vendor}
docker image inspect "$IMAGE" > "$ROOT/outputs/openroad_image.json"
docker run --rm --name aes-thermfm-flow-20260929 --cpus=4 --memory=8g \
  -v "$ROOT:/work" "$IMAGE" bash -c '
set -euo pipefail
cd /OpenROAD-flow-scripts
source ./env.sh
mkdir -p /work/inputs/rtl /work/inputs/orfs_config
cp flow/designs/src/aes/* /work/inputs/rtl/
cp flow/designs/nangate45/aes/* /work/inputs/orfs_config/
cp flow/platforms/nangate45/config.mk /work/inputs/orfs_config/platform_config.mk
if [ ! -d /work/vendor/nangate45 ]; then
  cp -r flow/platforms/nangate45 /work/vendor/
fi
cp LICENSE_BUILD_RUN_SCRIPTS /work/vendor/ORFS_LICENSE
openroad -version > /work/outputs/openroad_version.txt
yosys -V > /work/outputs/yosys_version.txt
cd flow
make DESIGN_CONFIG=designs/nangate45/aes/config.mk WORK_HOME=/work/flow NUM_CORES=4
' > "$ROOT/logs/openroad_flow.log" 2>&1
