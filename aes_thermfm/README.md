# AES → OpenROAD → Therm-FM

**Latest:** [completed simulated-workload run](runs/aes_simulated_20260930T045508Z/README.md), using fresh physical design and VCD-derived activity.

Original exploratory pipeline, 2026-09-29 (IST). **The pipeline runs; the AES temperature predictions are not physically validated.**

Start with [RESULTS_AND_BOTTLENECKS.md](RESULTS_AND_BOTTLENECKS.md). The chronological record is [WORK_LOG.md](WORK_LOG.md), and all thermal assumptions are in [docs/THERMAL_ASSUMPTIONS.md](docs/THERMAL_ASSUMPTIONS.md).

Follow-up: [SCALING_AUDIT.md](docs/SCALING_AUDIT.md) prioritizes the blockers, measures power-map resolution loss and raster cost, projects dataset storage, and specifies the next validation experiments. Raw audit results: `outputs/scaling_audit/audit.json`.

Controlled experiment: [LAYER_COUPLING_TEST.md](docs/LAYER_COUPLING_TEST.md) holds AES inputs fixed and changes only the other layer's power. The AES prediction changes, establishing input dependence in this checkpoint. This does not compare a passive layer with physical removal of that layer.

Presentation: [AES_ThermFM_Pipeline_Verified.pptx](presentation/output/AES_ThermFM_Pipeline_Verified.pptx) explains the starting files, every processing stage, tensor construction and outputs. [CONSTRAINTS_VERIFICATION.md](docs/CONSTRAINTS_VERIFICATION.md) records exact SDC port coverage and a fresh OpenSTA check of the final design.

[PIPELINE_DOCUMENT_REVIEW.md](docs/PIPELINE_DOCUMENT_REVIEW.md) reviews the separately published `THERM_FM_PIPELINE.md`, with line-specific corrections, CLI checks and a corrected workflow.

## Git checkout

Model weights are excluded by the repository ignore rules. See [GIT_ARCHIVE.md](docs/GIT_ARCHIVE.md) for checkpoint restoration and the scope of this snapshot before running inference.

## Simulation-based workload pipeline

The new [simulated-workload flow](docs/SIMULATED_WORKLOAD_PIPELINE.md) starts from AES RTL and constraints, creates a fresh routed design, verifies encryption transactions in gate-level simulation, imports VCD switching activity, and generates new power and temperature maps. It uses a 2 ns clock and explicit busy/gapped workloads. Thermal-stack assumptions remain unvalidated.

## Executed flow

```text
AES Verilog + Nangate45 LIB/LEF + SDC
   → Yosys synthesis
   → OpenROAD floorplan / placement / clock tree / routing
   → final DEF / ODB / GDS / netlist / SDC / extracted SPEF
   → OpenSTA per-cell power under explicit vectorless activity
   → exact-overlap power rasterization
   → input.mat [8, 4, 2, 101, 101]
   → archived trained Therm-FM-T + original normalization
   → predictions.mat [8, 2, 101, 101] + numerical diagnostics + maps
```

AES is the Advanced Encryption Standard. The design is the existing OpenCores-derived `aes_cipher_top` supplied by ORFS. This run did not develop or functionally certify a new cryptographic implementation.

## Files to inspect

| Path | Contents |
|---|---|
| `inputs/rtl/` | Actual AES RTL used, README and license |
| `inputs/orfs_config/` | Actual stock design config, floorplan and timing constraints |
| `vendor/nangate45/` | Technology files copied from the executed image |
| `flow/results/nangate45/aes/base/6_final.*` | Final routed design, including extracted parasitics |
| `flow/logs/`, `flow/reports/` | Actual flow metrics and reports |
| `outputs/cells_0.10.csv` | Cell footprints and power in watts at activity 0.10 |
| `outputs/power_*.rpt` | OpenSTA reports at three activity assumptions |
| `inputs/thermfm/input.mat` | Raw model inputs; HDF5 dataset named `data` |
| `inputs/thermfm/cases.json` | Meaning and assumptions of each of the eight samples |
| `inputs/thermfm/conservation_arrays.npz` | Watts and control volumes for auditing integration |
| `outputs/source_sanity/` | Held-out source-benchmark check, not AES accuracy |
| `inputs/source_sanity/` | Actual IND-8C sample 999 input/reference pair, copied for replay |
| `outputs/aes_inference/` | Predictions, temperatures, maps, timings and diagnostics |
| `outputs/replay_check/` | Second inference using the archived source and checkpoint |
| `vendor/checkpoint_IND8C_GWL2_T/` | Actual weights, config and normalization used |
| `vendor/Therm-FM/` | Executed model source snapshot and upstream commit identifier |
| `vendor/requirements-frozen.txt` | Executed Python environment package versions |
| `MANIFEST.sha256` | Artifact hashes |

`outputs/verification.json` records nine successful integrity checks. Archived-source/weight replay produced bitwise-identical AES predictions. This verifies execution and persistence, not physical accuracy.

`input.mat`/`predictions.mat` use the HDF5 key/shape contract read by Therm-FM; they are not guaranteed MATLAB `load`-compatible v7.3 files. No fabricated `output.mat` labels were created.

## Reproduce inference only

Use a compatible Linux Python environment (executed: Python 3.10, Torch 2.4.0+cu121; complete versions are archived). `vendor/requirements-inference.txt` lists the direct dependencies; choose a matching PyTorch build for the machine. Paths below refer to this experiment's root. A CPU fallback exists in the script but was not benchmarked.

```bash
ROOT=/absolute/path/to/aes_thermfm
PYTHON=/path/to/compatible/environment/bin/python
"$PYTHON" "$ROOT/scripts/infer.py" \
  --repo "$ROOT/vendor/Therm-FM" \
  --checkpoint "$ROOT/vendor/checkpoint_IND8C_GWL2_T" \
  --input "$ROOT/inputs/thermfm/input.mat" \
  --output-dir "$ROOT/outputs/my_replay"
```

This does not call the training/evaluation dataset loader, which expects labels and dataset splits. It calls the same ScOT model directly, with verified layer-major channel ordering and checkpoint statistics.

## Reproduce the complete pipeline

Use a **new directory** on Linux/x86_64 with Docker and a compatible Python environment. Copy this experiment's `scripts/` and `vendor/` directories into it. The script writes its own `inputs/`, `flow/`, `logs/`, and `outputs/` and uses a pinned public ORFS image. It must not run concurrently with another container named `aes-thermfm-flow-20260929`.

```bash
bash /absolute/path/to/new_run/scripts/run_pipeline.sh \
  /absolute/path/to/new_run \
  /path/to/compatible/environment/bin/python
```

The individual shell steps in `run_pipeline.sh` were executed during this experiment. The combined wrapper was assembled afterward; a second full physical-design run was not performed. Inference replay from the archived assets was checked separately.

Remote execution directory: `/home/ubuntu/aes_thermfm_20260929` on the existing `ubuntu@100.54.108.10` L40S host. Local review copy: `/Users/ayush/Arch_Gen/aes_thermfm`.
