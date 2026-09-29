# Bottlenecks before scaling AES → OpenROAD → Therm-FM

Audit date: 2026-09-29. Based on the saved run, new local rasterization measurements, source inspection, and a read-only remote capacity check.

## Decision

The format conversion and model execution work. The next milestone should be **one physically specified AES thermal case with reference temperatures**, before increasing chip size, layer count, or training-set size. The dominant unresolved issue is whether the inputs describe the same physical problem the model has learned. Fast, finite predictions do not settle that question.

No new OpenROAD run, model inference, workload simulation, or thermal-solver run was performed in this audit. Original predictions are unchanged. Larger-grid checks below measure power-map construction only, not thermal accuracy or GPU cost.

## Prioritized findings

### 1. Thermal configuration and reference labels — first blocker

OpenROAD supplied a single-die electrical layout. The adapter supplies an assumed 200 µm heat-source thickness, AES power in slot 0, and no heat generation in slot 1. There is no matched AES package, material stack, interface resistance, or cooling reference. The z channels contain identifiers 1 and 2, not physical heights.

The paper explicitly states that material/structural information is fixed within each benchmark case and captured through adaptation, rather than supplied as an explicit input channel ([Section III-A](https://arxiv.org/html/2605.22663v2#S3.SS1)). Our checkpoint therefore cannot be configured for an arbitrary package merely by editing x/y/z. This is consistent with its `use_conditioning=false` configuration and eight input channels.

Required next artifact: a versioned stack description specifying each physical layer's dimensions/materials, heat-generation region, interfaces, boundary conditions, ambient/coolant temperature, and mapping of output planes. Establish the source-channel unit and scaling from the original dataset generator. Then generate a solver reference for exactly those inputs. Until then, absolute AES temperatures and AES error metrics are unestablished.

### 2. Electrical activity — uncertain power, even with a correct layout

The deliberate activity-0.10 estimate is 17.8554 mW. The stock flow report is 434.837 mW, about 24.35 times larger, under different activity assumptions. The three deliberate activities span 8.8654–29.0929 mW, a factor of 3.28. These differences are evidence of sensitivity to assumptions, not a measured power-error bound.

Required next artifact: an AES testbench with functional checks and representative reset, idle, and encryption windows. Import workload-derived VCD/SAIF activity with correct hierarchy mapping; record which signal activities were annotated and which still use defaults, clock treatment, workload duration, library corner, and voltage. Compare all three power components on the same netlist/SPEF. OpenSTA supports simulation-derived activity; see its [command reference](https://opensta.readthedocs.io/en/latest/Commands/).

The present export assigns each cell's entire power to its rectangular footprint, including associated switching power. This is a thermal-source approximation; wire heating and local transistor heat generation are not separately resolved. More accurate activity alone does not remove that approximation. Temperature-dependent leakage feedback is also absent: the current pipeline passes electrical power to the thermal model once.

### 3. Checkpoint transfer — temperature response needs verification

The single source-domain check has MAE 0.02267 K, which supports the inference implementation only. It provides no AES accuracy estimate or general error tolerance.

At 17.8554 mW, the saved native-die prediction changes its mean by +0.02745 K relative to its zero-source input; the 1 mm embedding changes by +0.001434 K. The new audit found that 5.24% and 5.37% of output points, respectively, cool by more than 0.001 K relative to zero source. The largest local decreases are approximately 0.0710 K and 0.00858 K. These are diagnostic differences, not errors measured against a solver. The 0.001 K cutoff merely excludes tiny sign changes; it is not an accepted accuracy specification.

For passive, fixed-property conduction with unchanged boundary conditions, adding nonnegative heat should not reduce temperature. Test this property against a matched solver, as well as source scaling and superposition when the solver assumptions are linear. Do not infer that the approximately 353 K offset is the correct AES operating temperature. Nonuniform prescribed boundaries can themselves produce a nonuniform zero-source field, so zero-source structure alone does not prove a defect.

Evaluate the untouched checkpoint first, then fine-tune on target-stack solver data. Hold out workload/spatial patterns, rather than random pixels or near-duplicate scalings of one map. Report per-layer error, hotspot magnitude/location, and error in interlayer temperature differences. A scalar sweep of one fixed map cannot establish generalization to new layouts.

### 4. Spatial resolution — verified information loss

At activity 0.10, 14,461 of the 32,004 physical instances have positive exported power. Median powered-cell dimensions are 0.76 × 1.40 µm.

| Domain / grid | Grid spacing | Intervals across AES width | Bins with positive power | Peak source density, W/m³ |
|---|---:|---:|---:|---:|
| Native / 101² | 2.4985 × 2.506 µm | 100 | 6,181 | 7.589e10 |
| 1 mm / 101² | 10 µm | 24.985 | 442 | 7.774e9 |
| 1 mm / 201² | 5 µm | 49.97 | 1,682 | 1.881e10 |
| 1 mm / 401² | 2.5 µm | 99.94 | 6,199 | 7.602e10 |
| 1 mm / 1001² | 1 µm | 249.85 | 31,507 | 2.452e11 |

All eight checked maps (four resolutions in each domain) conserve total power within 1e-12 W; their recorded integration errors were zero at the stored floating-point precision. The 101² maps match the original saved power arrays within strict numerical tolerances. Conservation does not preserve local peaks: the embedded 401² map has about 9.78 times the peak source density of its 101² version despite identical total watts.

These are power-density differences, not predictions of a corresponding temperature-peak increase. Thermal diffusion can smooth cell-scale details. Determine the required resolution through convergence of the thermal reference and hotspot metrics. Rasterize directly from cell rectangles at each resolution; enlarging an existing coarse image cannot recover discarded information.

The existing `infer.py` rejects a grid different from the configured 101². The model's recovery layer also uses configuration-derived grid dimensions. This is a limitation of the current configured inference path, not proof that the Therm-FM architecture cannot adapt to other resolutions. Larger-grid execution and accuracy need separate checks. Independent thermal tiles are also not automatically valid, because heat crosses tile boundaries.

### 5. More chip layers — interface and modeling work

The selected checkpoint has eight input and two output channels, corresponding to two layer slots. Appending a third layer's four fields will not work with the unchanged input projection; an additional output plane also needs a compatible output head and normalization. Reuse of the backbone is possible in principle, but adaptation and reference data are required.

A real stacked design additionally requires block-to-die partitioning, per-die layout/power, aligned die coordinate systems, vertical interconnect treatment, and thermal descriptions of bonding/TSV/interface regions. The current single-die AES plus zero-source slot is not evidence that those steps have been completed. Physical material layers and predicted temperature planes need not have a one-to-one correspondence; record their mapping explicitly.

### 6. Compute, memory, storage — separate measured costs from projections

| Stage | Evidence | Scaling implication |
|---|---|---|
| Detailed routing | Saved elapsed time 232.24 s, peak 1123.81 MiB | Largest recorded stage; reuse a fixed routed layout for workload/power sweeps |
| Power-map rasterization | New local runs: 0.235–0.267 s per map across tested sizes | Currently inexpensive; excludes CSV reads, tensor construction and file writing |
| Therm-FM forward | Existing L40S median 27.64 ms at 101², batch 1 | Does not establish higher-resolution or training throughput |
| Remote storage | Fresh `df`: 146G total, 138G used, 7.4G available, 95% used | Insufficient headroom for large sweeps; expand or relocate before generating data |

The new timing parser sums detailed per-log elapsed values to 372.25 s. The original ORFS summary sums integer-truncated displayed values to 365 s. Both refer to saved logs, not two different runs, and neither is a measured full experiment wall-clock duration. Do not extrapolate larger-design runtime linearly from this AES point; congestion, macros, and timing targets change difficulty.

Uncompressed storage arithmetic for 10,000 samples, with eight input and two output float32 channels:

| Grid | Input + output per sample | 10,000 pairs |
|---|---:|---:|
| 101² | 0.389 MiB | 3.80 GiB |
| 201² | 1.541 MiB | 15.05 GiB |
| 401² | 6.134 MiB | 59.90 GiB |
| 1001² | 38.223 MiB | 373.27 GiB |

These are array-size calculations, not measured compressed files, training memory, or GPU memory. The current builder uses float64: 10,000 inputs alone at 401² would occupy about 95.84 GiB uncompressed. `infer.py` reads the whole HDF5 dataset and normalizes it before forwarding one sample at a time, so batch size 1 does not bound host memory. A scaled runner should stream HDF5 chunks, normalize bounded batches, and write outputs incrementally. Keep geometry and reusable coordinates once where the storage contract permits.

### 7. Automation — prototype is specialized to one run

`run_openroad.sh` hard-codes the AES design, Nangate45, resource limits, and container name. `export_power.tcl` hard-codes the final path, platform, and activities. `build_inputs.py` fixes two slots, source assignment, eight cases, coordinate modes, and thickness default. The combined wrapper was assembled after the original individually executed steps; a full second wrapper replay has not been demonstrated.

Before batch operation, introduce a per-run manifest for design/platform/constraints/activity/stack/checkpoint, unique run and container names, checkpoint compatibility checks, per-stage status/timing, and resume support. Cache stages by their actual dependencies: changing activity requires power extraction and thermal steps, not another placement/routing run. Changing layout or constraints invalidates the relevant upstream outputs. Keep provenance checks on every run; file existence alone is insufficient.

The current local default Python lacks h5py, although NumPy is available. The audit consequently reuses the exact raster function via AST extraction and runs without h5py. The archived compatible remote environment remains the original inference environment. Do not advertise the pipeline as a dependency-free local command.

## Ordered next experiments and completion evidence

1. **Fix the physical contract.** Recover dataset source units; choose one explicit target stack and cooling setup; validate layer/output-plane mapping. Produce a stack manifest and solver input reviewed for dimensional consistency.
2. **Fix activity provenance on this layout.** Run checked AES workloads; quantify activity annotation coverage/defaults; save per-window power and the source trace. Resolve timing before treating this as an operating implementation: the existing design has -38 ps setup slack and 19 violations.
3. **Generate a small matched solver set.** Start with zero-source diagnostic, idle, and active workload windows; compare coarse and finer solver grids. A pilot of roughly 20–30 varied cases is a proposed starting budget, not a promise of sufficient training data. Record solver time, mesh convergence, and heat-balance residuals.
4. **Establish thermal error.** Test zero-shot and then adaptation with a held-out split; compare against the same solver. Choose error tolerances based on the intended thermal decision, with solver numerical error comfortably smaller. Include interlayer temperature differences and hotspot locations, not only mean MAE.
5. **Scale one axis at a time.** First test 101² → 201² → 401² on the same physical case with a compatible model path; then larger layouts; then extra active dies. Measure complete runtime, CPU/GPU peak memory, storage, and reference error at each step. Reserve enough storage before starting; do not silently discard older artifacts.

## Reproduce this audit

```bash
python3 scripts/audit_scaling.py --root /absolute/path/to/aes_thermfm
```

Requires NumPy only. Detailed metrics and platform information are in `outputs/scaling_audit/audit.json`. The script checks baseline-map agreement and conservation, benchmarks the exact saved raster function, reanalyzes saved predictions, and extracts elapsed/memory values from saved logs. The audit source hash identifies the exact raster implementation. Timing values are single observations rather than a statistical performance study.
