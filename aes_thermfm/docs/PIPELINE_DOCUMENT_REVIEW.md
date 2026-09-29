# Review of THERM_FM_PIPELINE.md

Reviewed 2026-09-30 at GitHub commit `6def77bf34dc98952b1b7b4e91a3a1bee17d50de`.

Source: https://github.com/ayushguptaz/therm-fm-experiments/blob/6def77bf34dc98952b1b7b4e91a3a1bee17d50de/THERM_FM_PIPELINE.md

The local copy in `/Users/ayush/therm-fm-experiments` is byte-identical to that online version. The reviewed snapshot, source metadata and inference CLI check are under `docs/pipeline_review/`. This review does not modify or publish the GitHub document.

## Verdict

The overall development sequence is appropriate: implement a circuit, estimate spatial power, generate temperatures for a defined thermal setup, adapt a surrogate, and predict held-out power scenarios. The document is not yet an executable, physically specified run guide. Its command examples and several stated requirements need correction.

The executed code used for comparison is the archived Therm-FM snapshot at upstream commit `1c338d0fbe0dca25311eb896a9ea136a4f3d3cb1`, with the archived local modifications. A different installed version may have different CLI options and must be pinned explicitly.

## Findings by document line

1. **Lines 248–253: inference command does not match the inspected CLI.** The actual `scOT/inference.py` does not accept `--stats_json` or `--output_path`. Its parser requires `--file`, `--data_path`, and (in this snapshot) `--ckpt_dir`; `save_samples` also uses the dataset selector. The documented command lacks required arguments. Verified by executing only the actual argparse construction statements, without model imports. See `pipeline_review/cli_check.json`.

2. **Lines 275–284: expected prediction file does not follow from Step 9.** The inspected `save_samples` branch writes `inputs.npy`, `labels.npy`, and `outputs.npy`, not an HDF5 temperature MAT file. Its thermal dataset loader requires input and output files, making it a labeled evaluation path, not arbitrary label-free inference. Our dedicated `scripts/infer.py` supplies the latter and writes temperatures already converted to kelvin. Applying Step 10 to that output would denormalize twice. Document the exact inference implementation, file format and normalization state together.

3. **Line 135: incorrect HotSpot invocation.** `-f` takes a floorplan, while `-p` takes the power trace. `-o` is a transient temperature trace, not a request for a steady-state grid. A schematic grid-mode invocation is `hotspot -c hotspot.config -f design.flp -p workloads.ptrace -model_type grid -grid_steady_file temperature.grid`, with the necessary materials/stack options for the chosen configuration. This is an illustrative corrected syntax, not a tested solver run. The solver output also needs an explicit conversion to HDF5 `output.mat`. Source: https://github.com/uvahotspot/HotSpot/blob/master/examples/example2/run.sh

4. **Lines 114–119, 153, 178: W/m² is not an established universal Therm-FM input unit.** W/m² denotes areal heat generation. Volumetric heat generation uses W/m³ and requires division by source thickness as well as area. Our industrial adapter uses the volumetric interpretation, while original industrial generator scaling still requires confirmation. The HotSpot-derived arrays have different conventions that cannot be inferred from their magnitudes. A channel mean of 18.69 does not prove the field's physical units or meaning. Declare units and scaling from the selected data generator/checkpoint, not from a guessed range.

5. **Lines 104–116 and 172–174: raster and coordinate discretizations disagree.** The raster bins use H/W equal intervals over the domain, whereas `linspace(0,width,W)` describes endpoint nodes with W−1 intervals. Pick either cell-centred bins with matching coordinates or endpoint nodes with matching control volumes. Our existing adapter uses endpoint nodes and half-width edge control volumes. The example also assigns an entire cell to one bin, omits die-origin handling, and silently clamps high out-of-range positions. Negative positions can index the array from the end. Use valid cell bounds, explicit origins and exact overlap allocation. Point assignment can conserve total watts but loses spatial detail.

6. **Line 106 and the absence of a physical stack specification: DEF does not automatically supply a generic `cell.die_layer`.** A multi-die workflow must explicitly assign instances to dies, align their coordinates, and describe materials, thicknesses, interfaces and cooling. Output temperature planes also need a defined mapping. A single die does not justify an invented second die. The current AES adapter's synthetic second slot was only an execution experiment. The paper states that each benchmark's structural information is fixed and implicit in adaptation. Source: https://arxiv.org/html/2605.22663v2#S3.SS1

7. **Lines 142 and 324: no general 1,000-sample minimum.** The paper tests low-data adaptation and cross-chip transfer, including 10–30 target samples in particular industrial transfers. That does not guarantee those counts will suffice for AES, but it contradicts a universal minimum. The actual inspected industrial datasets contain 1,000 samples, while the inspected HotSpot dataset contains 5,000. Determine a target data budget through held-out error and learning curves. Source: https://arxiv.org/html/2605.22663v2#S4.SS8

8. **Lines 83, 100 and 320: original source training resolution is not an immutable requirement during adaptation.** The present AES inference script enforces its checkpoint's configured size. However, training constructs `ScOTConfig(image_size=resolution, num_channels=input_dim, num_out_channels=output_dim)` from the target dataset when adapting embedding/recovery. The table of dataset sizes is a set of examples, not a list of all permissible resolutions. Matching shapes is still necessary in any configured forward path, and cross-resolution accuracy must be evaluated.

9. **Lines 197–204: similar geometry is insufficient reason to select normalization.** At inference, use the exact statistics associated with the trained checkpoint. For target adaptation, choose the normalization policy explicitly and keep it consistent across training, validation and inference. If recomputing statistics, use the actual training split and save them with the adapted model. Reusing statistics does not repair unit, material, or boundary-condition mismatches.

10. **Lines 239 and 326: split interpretation is incomplete.** In the inspected thermal loader, `train_ratio` reserves train plus validation. With all samples used, 0.8 corresponds approximately to 72% train, 8% validation, 20% test; 0.9 corresponds to 81%, 9%, 10%, subject to integer rounding. Explicit trajectory budgets can change train/validation counts. These ratios are experiment settings, not hard requirements of the model.

11. **Lines 221 and 258: commands reference files absent from this published repository.** Its current tree does not include the named `configs/multichip_exp/baseline_L2_HS_SC_refine1.yaml`, `eval_multichip_v2.py`, or the `scOT/` implementation. The guide must identify the separate executable checkout, commit, additional scripts, working directory, and checkpoint location. The evaluator's claim of exact paper metrics cannot be verified from this repository alone.

12. **Lines 231–240: config excerpt is not a complete directly usable configuration.** The inspected YAML loader expects `key: {value: ...}` wrappers. Training also requires dataset selection, trajectory count, warmup, clipping and other fields not shown. The repository's actual experiment YAML supplies these. Separate illustrative parameter values from a runnable YAML. Saved checkpoint output can also nest under project/run names, so Step 9 must target the actual saved model directory. The p=2 implementation can use per-channel normalized squared error; calling it unqualified plain MSE is incomplete.

13. **Line 325: starting from Poseidon-T is not mandatory.** A compatible adapted checkpoint can initialize another adaptation, and other model sizes exist. The paper explicitly evaluates cross-chip transfer from a model already trained on another thermal case. Match architecture and decide whether to replace input/output projections for the target representation.

14. **Line 322: generic h5py HDF5 output is not automatically MATLAB v7.3.** The code writes the HDF5 dataset contract consumed by the loader. It does not create all MATLAB MAT-file metadata/header conventions. Say HDF5 with key `data` unless MATLAB compatibility is separately established.

15. **Lines 20–32 and 41–52: synthesis/physical commands are illustrative stubs.** The shown Yosys command neither reads the stated SDC nor configures timing-aware mapping from it. The placement/routing stage needs timing constraints and Liberty as well as physical technology data. Record final SDC and extracted SPEF/ODB as power-analysis inputs, in addition to DEF. Our saved AES example still fails its setup target despite complete I/O delay coverage.

16. **Lines 60–67: activity and power descriptions need qualification.** OpenSTA reports internal, switching and leakage components. Dynamic power includes both internal and switching contributions. Merely passing `+vcd=...` does not establish that a testbench creates the dump; dump instrumentation and hierarchy annotation must be specified. A workload trace needs coverage/default-activity checks after mapping onto the analyzed design.

## Corrected sequence

### Build or adapt a model for a target setup

1. Pin RTL, timing/environment constraints, physical technology and floorplan configuration.
2. Synthesize, place, build the clock tree and route. Save layout, final netlist/constraints and parasitics. Check timing and geometry.
3. Estimate per-cell power using library characterizations and documented workload activity.
4. Define the physical stack, package/cooling and output planes. Map source power onto a consistent spatial discretization with verified units and conserved watts.
5. Run a thermal solver for that same setup and source distribution. Convert reference outputs into the selected tensor format.
6. Store input `[N,P,L_in,H,W]` and target `[N,L_out,H,W]`, using HDF5 key `data` for this loader. The number of predicted planes need not universally equal the number of source slots.
7. Choose a compatible pretrained backbone or thermal checkpoint, configure projections/grid as needed, and establish consistent training statistics.
8. Fine-tune, evaluate held-out cases and record thermal error and numerical convergence. Persist the actual checkpoint directory and its statistics.

### Predict a new power scenario within the supported setup

1. Create the new source map with the same physical conventions, stack and channel ordering.
2. Standardize with the checkpoint's saved statistics, then run a label-free forward pass.
3. Convert outputs to physical temperatures exactly once, save and plot them. Solver labels are not needed for each ordinary inference, but are needed to establish and periodically check accuracy.

The correct high-level architecture in the document should be retained. Its executable examples need versioned, tested scripts and its constraints must distinguish architectural requirements from choices in particular experiments.

## Code evidence

- `vendor/Therm-FM/scOT/inference.py`: CLI near line 337, sample export near line 491.
- `vendor/Therm-FM/scOT/problems/thermal/steady.py`: split near line 100, normalization near line 125, flattening near line 265.
- `vendor/Therm-FM/scOT/train.py`: YAML parsing near line 376, target model configuration near line 538, save directory near line 390.
- `scripts/infer.py`: tested label-free interface, saves already-denormalized kelvin.
- `scripts/build_inputs.py`: exact rectangular-overlap rasterization and explicit thermal assumptions.
- `docs/CONSTRAINTS_VERIFICATION.md`: actual AES timing/environment check.

Review scope: source inspection and parser validation, not execution of the document's entire training or thermal-solver workflow. No claim of target thermal accuracy.
