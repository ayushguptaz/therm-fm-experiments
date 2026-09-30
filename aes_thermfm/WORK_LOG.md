# AES → OpenROAD → Therm-FM work log

Started: 2026-09-29 (Asia/Kolkata).

## Objective

Run a small AES hardware design through OpenROAD, export its physical/power information, create actual Therm-FM inputs, execute a trained model, and record bottlenecks before scaling. Accuracy is exploratory; execution success is not evidence of thermal accuracy.

## Planned flow

1. Discover installed runtimes and trained model assets.
2. Synthesize/place/route the existing ORFS AES RTL with Nangate45.
3. Export placed-cell geometry and library-based estimated power with explicit switching assumptions.
4. Rasterize power conservatively and define thermal geometry/stack assumptions.
5. Inspect actual checkpoint/data channel semantics, units, ordering, normalization, and dimensions.
6. Produce checkpoint-compatible input files and run inference.
7. Verify finite outputs, power conservation, and file contracts; produce maps and a bottleneck report. Compare with a conventional reference only if a matching thermal setup can be established.

## Initial observations

- Workspace: `/Users/ayush/Arch_Gen/aes_thermfm`.
- Existing ORFS source: `/Users/ayush/ArchGen/OpenROAD-flow-scripts`; AES RTL and Nangate45 platform are present. Its AGENTS.md directs readers to README.md; both were read during discovery.
- No `openroad` or `yosys` executable on PATH. Docker client exists, daemon is stopped.
- `/Users/ayush/Therm-FM/data` is empty. `/Users/ayush/therm-fm-experiments` contains experiment reports/configs, not trained model weights.
- Existing reports mention remote Therm-FM machines. No running training process will be stopped or modified.
- Local experiment documentation has known naming inaccuracies (HS-SC means single-core). Input semantics will be checked against data/code rather than trusted from prose alone.

## Execution entries

- Initial read-only discovery completed. No flow or inference run yet.
- Started Docker Desktop locally successfully; selected the existing remote L40S host instead to run native Linux/x86 tools and reuse trained weights. Remote isolated directory: `/home/ubuntu/aes_thermfm_20260929` on `ubuntu@100.54.108.10`.
- Remote had approximately 16 GB free before installing ORFS, 9.5 GB after pull. Existing datasets/checkpoints/services are untouched. ORFS is limited to 4 CPUs and 8 GB RAM.
- Pulled official `openroad/orfs` image, pinned digest `sha256:94d3c1c19b47e8ef2c3a9b32cb9dc6e5c18817ffb71f03e28ec67d6fa0a44512`. Image bundles a matching tool/flow/platform set. Local checkout is only a reference, not the executed flow version.
- Started the stock Nangate45 AES full flow using `scripts/run_openroad.sh`; stock clock period is 0.82 ns. RTL/config provenance is copied out of the container. Tool version strings are unfortunately `unknown`/`UNKNOWN`; image digest is the reproducibility anchor.
- Inspected real datasets using `scripts/inspect_thermfm.py`. HS-SC uses x/y in 0..0.016 and z=0/0.00017, with first-channel values around 0..25. IND uses x/y in -0.5..0.5, z identifiers 1/2, and first-channel values around 1e11. These are not interchangeable conventions. Dataset inspection JSON is preserved.
- Selected user's trained IND-8C Model-T GW-L2 alpha=0.5 checkpoint (p=7), not an unmodified official paper checkpoint. No retraining is planned for the first execution test.
- Added `scripts/infer.py` for direct label-free inference, strict checkpoint-key/finite-value checks, original normalization, denormalized predictions, timing, and hashes. Started a held-out source sample (index 999) sanity check before AES inference.
- Source sanity check passed: MAE 0.02267098 K, RMSE 0.03125243 K, global maximum error 0.39338636 K on sample 999. These are one source sample's metrics, not AES metrics.
- Added cell-power export with three vectorless switching activities, a conservative overlap rasterizer, and explicit native-die versus 1 mm embedding variants. The embedding retains original cell size and watts. Native AES die from the stock floorplan is approximately 249.85×250.60 µm.
- AES reached detailed routing. Intermediate routing violations are optimization progress, not final DRC results.
- Full ORFS flow completed successfully: final DEF/ODB/GDS/SDC/Verilog/SPEF generated; final router DRC and antenna violations zero. Setup timing is not closed: worst slack -0.0380276 ns and 19 setup violations. Sum of reported stage elapsed times 365 s; reported peak memory about 1,123 MB.
- Exported 32,004 physical instances with geometry and per-cell power. Estimated totals at vectorless activity 0.02/0.10/0.20: 8.865363/17.855389/29.092921 mW. Stock flow default power report is 434.837 mW; this large difference is documented as an activity-assumption bottleneck, not silently reconciled.
- Generated eight AES-derived inputs (three activity levels + zero source × native/1 mm domains). Power density integration agrees with cell watt sums within 3.47e-18 W. Cell-level sums also agree with OpenSTA design totals within floating-point tolerance.
- Therm-FM inference succeeded for all eight cases. Median warmed synchronized forward latency 27.64 ms/sample on L40S; peak PyTorch allocated memory 106 MiB. Predictions finite, but structured zero-source fields and weak/non-monotonic local power responses prevent a physical accuracy claim.
- Saved `RESULTS_AND_BOTTLENECKS.md`, README, assumptions, scripts, logs, reports, CSVs, HDF5 inputs/predictions, NPY predictions and PNG maps. Plots were visually inspected.
- Archived the actual 83,235,819-byte checkpoint, normalization, model source snapshot/local diff, Python package versions, technology files and final physical-design outputs locally. Copied a real source sample/reference pair for future sanity checks.
- Replayed inference using only archived source/checkpoint paths in the existing compatible environment. Predictions were bitwise equal to the first AES run.
- `verify_artifacts.py`: 9 integrity checks PASS, including hashes, finite shapes, HDF5/NPY agreement, exact replay, serialized power conservation, final design files and source-sample provenance. Shell and Python script syntax checks pass.

## Final state

Requested execution experiment completed. Physical validation, workload-derived switching activity, target-stack simulation and target fine-tuning remain future experiments, explicitly listed in the bottleneck report. No existing jobs were stopped, source/checkpoint files edited, or datasets deleted. ORFS run containers use `--rm` and exited; the Docker daemon/image remain available. Local Docker Desktop was started during discovery but did not run the experiment.

## Completion criteria

- Traceable RTL/technology/tool/model provenance.
- Actual OpenROAD outputs and estimated spatial power.
- Therm-FM input tensors and saved predictions from real weights.
- Markdown instructions and explicit unresolved physical/domain assumptions.

## Follow-up scaling audit — 2026-09-29

- User requested exploration of bottlenecks before scaling. Reviewed saved physical/power/thermal reports, adapter/inference/model code, and the paper's explicit statement that structural information is implicit in benchmark adaptation.
- Added `scripts/audit_scaling.py` and `docs/SCALING_AUDIT.md`. The audit executes the exact raster function extracted from `build_inputs.py`, without triggering its CLI or requiring the locally missing h5py package. NumPy 2.4.6 on local macOS was used; this is not the original GPU inference environment.
- Measured four grids (101, 201, 401, 1001 per side) for each of two domains at activity 0.10. All eight power integrations pass; both 101-grid power arrays match saved artifacts. Raster-only times were 0.235–0.267 seconds in one observation per case.
- Found 14,461 positive-power instances and median powered-cell size 0.76 × 1.40 µm. At 1 mm / 101², AES spans about 25 intervals across each side and only 442 bins contain power. At 401², 6,199 bins contain power and peak source density is 9.78 times higher, with identical total watts. This does not measure temperature accuracy.
- Reanalyzed saved predictions with a 1 mK negative-response cutoff; saved metrics in `outputs/scaling_audit/audit.json`. No model inference was rerun and no ground-truth labels were fabricated.
- Extracted detailed saved stage timings: routing 232.24 seconds; sum of recorded elapsed values 372.25 seconds. Confirmed the original 365-second total is the sum of integer-truncated stage entries, not a conflicting experiment result.
- Read-only remote capacity check found 7.4G available and 95% disk utilization. Saved its output in `outputs/scaling_audit/remote_capacity.txt`; did not delete data or stop jobs.
- Documented actual inference limitations (whole-dataset host-memory loading; configured 101²/8-input/2-output contract), hard-coded AES automation, proposed validation gates, and uncompressed storage arithmetic. Larger-grid model performance and thermal-solver cost remain unmeasured.
- Updated README navigation. Original inputs, checkpoint weights, and temperature predictions are unchanged. Refreshed the artifact manifest to include this follow-up; changes to pre-existing files are limited to README and this work log.

## Controlled second-layer intervention — 2026-09-30

- User asked whether adding a zero-power second layer changes the AES prediction or whether the layers are independent. Designed a test of input dependence, explicitly distinguishing it from physical layer removal, which this fixed two-slot checkpoint cannot represent.
- Added and ran `scripts/check_layer_coupling.py` in the existing compatible remote environment using archived Therm-FM source, weights, normalization, and `infer.py`. Saved 12 inputs/predictions: native and embedded domains, each with second-layer source 0×, 0.5×, 1×, 2× AES, horizontally flipped 1×, and a repeated zero source.
- Assertions verify every first-layer input field and all coordinate fields are unchanged. Both baseline predictions reproduce the original saved AES outputs bitwise; duplicate zero-source cases are bitwise equal. All outputs are finite.
- Native domain: adding 17.8554 mW to the second slot changes the AES map by +0.01020 K in mean, with maximum absolute local change 0.14291 K. Adding 35.7108 mW yields +0.02055 K mean and 0.27519 K maximum absolute change. Some points decrease (down to -0.12776 K for the 1× case), so the result demonstrates learned dependence, not validated physical coupling.
- Embedded domain: 1× second-layer power produces +0.000535 K mean and 0.02459 K maximum absolute local change in AES. Changing the second source's spatial pattern at constant total power also changes AES outputs in both domains.
- Saved raw inputs, cases, predictions, provenance report, numerical comparison, graph, and `docs/LAYER_COUPLING_TEST.md`. Original AES input/output arrays and checkpoints remain unchanged. No training, OpenROAD rerun, or thermal solver was invoked.

## Pipeline presentation and constraint verification — 2026-09-30

- User requested a PowerPoint covering all input files and the complete Verilog-to-temperature pipeline, with constraint verification. Created an 18-slide editable deck using the presentations skill and bundled Artifact Tool runtime. Included the actual power/temperature figure and evidence references in slide notes.
- Verified exact port-name coverage in final SDC: 258 non-clock input bits and 129 output bits each have 0.164 ns delay annotations. Physical and virtual clocks both retain the 0.82 ns period. Final physical clock is propagated, while the virtual clock retains 0.210 ns latency.
- Checked initial DEF database-unit conversion against final geometry: 249.85 × 250.60 µm. Confirmed Liberty nominal 1.10 V / 25°C and time units, SPEF units, and checkpoint 101² / 8-input / 2-output contract.
- Reloaded the final design into the pinned remote OpenROAD container and ran `check_setup -verbose` plus max/min worst-slack reports. No check_setup diagnostics appeared. Rounded slack is -0.04 ns setup and +0.11 ns hold, consistent with saved detailed metrics. A hierarchical-flow development warning remains in the full log.
- Identified absent explicit final-SDC clock uncertainty, input drive/transition and output-load commands. Documented these as environmental-specification gaps, without modifying the design or asserting that all engineering requirements are satisfied.
- Saved `docs/CONSTRAINTS_VERIFICATION.md`, `presentation/constraints_verification.json`, and fresh command/log evidence under `presentation/.build/`. Deck distinguishes timing failure, verified input formatting and unresolved physical thermal assumptions.
- Original layout, source, checkpoint and numerical temperature files are unchanged. Presentation build and intermediate previews remain in the private `.build` directory.

## Review of published pipeline guide — 2026-09-30

- Reviewed the requested `ayushguptaz/therm-fm-experiments/THERM_FM_PIPELINE.md` at commit `6def77bf34dc98952b1b7b4e91a3a1bee17d50de`. Confirmed its local copy is byte-identical to the downloaded source. Saved snapshot and metadata under `docs/pipeline_review/`.
- Compared its steps with the archived executed Therm-FM code, adapter and source-data inspection, the paper, and official HotSpot usage. Executed only the inference parser's AST statements to confirm unsupported flags and required arguments, without launching model inference or training.
- Saved `docs/PIPELINE_DOCUMENT_REVIEW.md` with line-specific findings and a corrected development/inference sequence. Important findings: invalid inference command/output expectations, incorrect HotSpot flags, unestablished generic power units, inconsistent bin/node coordinates, incomplete physical stack specification, unsupported minimum sample count, overly rigid resolution/initialization rules, normalization/split inaccuracies, and missing executable dependencies in the published experiment repository.
- The high-level design/data/adaptation sequence is sound, but the guide should not be treated as runnable as written. No GitHub file or original experiment artifact was changed. This turn performed review and documentation only.

## Git archive preparation — 2026-09-30

Copied the completed local experiment into `therm-fm-experiments/aes_thermfm/` for version control. Included scripts, inputs, routed artifacts, reports, predictions, vendor source/configuration and the verified presentation. Excluded ignored checkpoint weights, Python caches and presentation scratch builds. Documented checkpoint restoration in `docs/GIT_ARCHIVE.md` and regenerated the manifest for the committed subset. This archival step does not rerun the physical-design or inference experiments.

## Simulation-based workload rerun — started 2026-09-30

User requested a new RTL-to-temperature run with simulated activity. Preparing an isolated `aes_simulated_20260930T045508Z` run. Using a 2 ns clock instead of the earlier failing 0.82 ns target; gate-level functional simulation with independent OpenSSL ciphertext checks, 16 warm-up plus 256 measured blocks, fixed key, deterministic plaintext seed, and 0/16-cycle request gaps. No SDF delays: glitch power remains unmeasured. Thermal checkpoint, hypothetical second slot and 200 µm heat-source thickness remain exploratory assumptions. Results pending.

### Fresh physical design and simulated workload checks

- Fresh flow completed from archived RTL/DEF and modified source SDC at `/home/ubuntu/aes_simulated_20260930T045508Z`. Final setup slack +0.591159 ns, hold slack +0.106381 ns, zero setup/hold violations and zero detailed-router DRC errors. 29,153 physical instances; 12,842 reported standard cells. Flow summary stage total 349 seconds (rounded by the flow).
- Both functional gate-level simulations passed all 272 independent OpenSSL ciphertext comparisons. After 16 warm-up blocks, busy measured 256 blocks over 6.656 µs and gapped measured 256 over 14.848 µs. No SDF delay annotation was used.
- Busy VCD imported with 47,763 annotated pins and zero unannotated pins; summed per-cell power 0.02015545598327506 W. Gapped import and final waveform audit/inference are pending at this log entry.
- Raw waveforms reached hundreds of MB to over 1 GB per scenario. Timestamp rebasing preserves signal values and avoids including the pre-recording warm-up interval in the power window. Raw and rebased traces are retained for provenance and will be compressed for storage.

- Gapped VCD also imported with 47,763 annotated pins and zero unannotated pins. Summed per-cell power is 0.01994478662257171 W, about 1.05% below busy despite the longer request gaps. The clock and internal AES state-update logic continue running between requests; gaps are not equivalent to clock gating. Full waveform validation precedes inference.

### Simulated-workload run completed

Both complete waveform scans passed with zero X/Z records and zero unannotated pins. All six inputs conserved power; Therm-FM produced finite `[6,2,101,101]` temperature arrays. Native AES-slot means: busy 352.227840 K, gapped 352.227385 K; these are unvalidated model predictions. Forward median approximately 28.93 ms. Saved the compact review archive under `runs/aes_simulated_20260930T045508Z/`; verified all 158 transferred file hashes. Large raw and rebased VCD recordings remain on the execution host, compressed for storage; retrieval instructions and exact provenance hashes are in the run README and JSON reports. Busy plot visually reviewed; final review/checks continue below.

Final review: both power/temperature figures inspected; all 158 review-archive hashes passed. The new scripts pass Python syntax and shell syntax checks. The remote run reports `PASS`. No AES thermal accuracy is claimed; raw traces remain on the execution host and all selected results are available locally.
