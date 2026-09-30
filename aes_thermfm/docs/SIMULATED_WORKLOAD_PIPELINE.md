# AES pipeline with simulated workload activity

## Purpose and scope

Replace the original vectorless switching assumptions with switching activity recorded from functional simulation of a freshly routed AES netlist. This adds an independently checked transaction workload; it does not establish a physical AES package or thermal accuracy.

## Starting inputs and complete flow

1. Copy the stock ORFS AES RTL, floorplan DEF and design configuration from the pinned ORFS image into the new run's `inputs/` directory.
2. Change the source SDC clock period from 0.82 ns to 2.0 ns (500 MHz). Retain the stock 20% I/O-delay rule, so I/O delays become 0.4 ns. The source virtual-clock latency remains 0.210 ns. Use these saved RTL/SDC/DEF files explicitly in the run configuration.
3. Run fresh Yosys synthesis and OpenROAD floorplanning, placement, clock-tree synthesis, routing and parasitic extraction. Check final setup and hold timing; do not reuse the earlier routed netlist.
4. Generate 272 AES-128 plaintext/reference pairs: the standard known-answer vector followed by deterministic pseudorandom blocks (Python seed 20260930), all using key `000102030405060708090a0b0c0d0e0f`. OpenSSL produces the reference ciphertexts, and its first result is checked against the known expected `69c4e0d86a7b0430d8cdb78070b4c55a`.
5. Generate functional standard-cell Verilog models from the same Nangate45 Liberty using Yosys. Simulate the **final routed gate-level netlist** with Icarus Verilog and `aes_workload_tb.v`. No SDF delays are annotated. Each encryption output must match the independent reference; timeouts and mismatches are fatal.
6. Use 16 encryptions as warm-up; record the next 256. Run two separate workloads: `busy` (zero extra gap cycles between requests) and `gapped` (16 extra cycles after each encryption). "Busy" does not mean a pipelined one-block-per-clock AES engine. Each transaction waits for completion. The gapped case keeps the clock running; internal logic may continue switching without new requests.
7. Record all DUT hierarchy signals in VCD after warm-up. Preserve the raw recording and rebase its timestamps to zero for a precisely defined measurement interval. Audit ciphertext count, clock transitions, time base and X/Z records. Read the VCD with the exact scope `aes_workload_tb/dut`, and inspect activity annotation coverage.
8. In a fresh OpenROAD process for each workload, read final ODB/SDC/SPEF and Liberty; import VCD using `read_vcd`; export per-cell power and placement. **No `set_power_activity` assumptions are applied in this path.** Any unmatched or propagated signal activities must be reported rather than described as direct simulation coverage.
9. Allocate cell watts to the spatial grid with exact rectangular overlap. Verify power conservation, generate the native-die and hypothetical 1 mm-domain cases plus zero-source diagnostics, then run the saved IND-8C Therm-FM-T checkpoint.
10. Save power reports, VCD provenance/coverage, tensors, temperature arrays, readable figures and numeric summaries. Temperatures are predictions without matching AES thermal-solver references.

## Reproduce

Requirements: Linux/x86_64, Docker, network access for the ORFS image and Icarus package, and a compatible inference Python environment (see `vendor/requirements-inference.txt`). The vendor directory must contain the actual checkpoint weights and executed model source; weights are not in Git. The simulator Dockerfile builds on the pinned ORFS image; the installed Icarus version and resulting image identity are recorded per run.

From this experiment directory, choose a directory that does not yet exist:

```bash
bash scripts/run_simulated_pipeline.sh \
  /absolute/path/to/new_aes_run \
  /path/to/inference/python \
  /absolute/path/to/aes_thermfm/vendor
```

`run_physical.sh` and `finish_run.sh` expose the same stages separately. The initial new experiment executes these stages separately so tool preparation can overlap physical design. Its logs establish the stages actually run; the combined fresh-directory wrapper is not claimed as separately retested end to end.

## Remaining assumptions

- These are selected synthetic transaction workloads, not measured application traffic. Fixed key, request gaps, clock, reset sequence and plaintext distribution are explicit choices.
- Functional gate simulation without SDF does not capture physical delay-induced glitches or prove timing-aware functional behavior. Static timing is checked separately.
- Nangate45 typical power models at 1.10 V and 25°C remain in use; no electrothermal leakage feedback is applied. Stock SDC omits explicit clock uncertainty, input drive/transition and output load.
- The 2 ns clock and newly implemented layout differ from the old 0.82 ns run. Power differences between the runs cannot be attributed solely to replacing assumed activity.
- Cell power is spread uniformly over cell footprints, including associated interconnect switching power. Heat-source thickness remains assumed at 200 µm; industrial dataset scaling still needs confirmation.
- AES still occupies slot 0 of the two-slot checkpoint; slot 1 is synthetic zero power. The 1 mm case is a hypothetical embedding. Package, material interfaces and cooling are not matched to a real AES assembly.
- The checkpoint has not been trained or validated for this AES thermal setup. Simulation-derived activity improves the source estimate; it does not make the predicted temperatures validated.

## Key files per run

- `inputs/rtl/`, `inputs/orfs_config/`: actual physical-design starting files.
- `inputs/workload/`: plaintext/ciphertext vectors, workload metadata, generated functional cell models.
- `flow/results/nangate45/aes/base/6_final.*`: newly routed design and extracted parasitics.
- `logs/simulation_*.log`: ciphertext checks and exact measured interval.
- `outputs/workload/*.vcd`: raw and zero-origin waveforms (large; may be kept outside Git).
- `outputs/workload/activity_audit.json`: waveform checks and activity annotation reports.
- `outputs/cells_busy.csv`, `outputs/cells_gapped.csv`: simulated-activity per-cell power.
- `inputs/thermfm/`: raw input tensor, case metadata and conservation arrays.
- `outputs/aes_inference/`: predictions, numeric summaries and power/temperature figures.

## Interpreting time and archived waveforms

The VCD interval is used to estimate **average electrical power** for each workload. That average power is passed to the steady-state thermal checkpoint. A predicted map is not the temperature reached 6.656 or 14.848 µs after power-on, and no thermal transient is simulated.

Large raw and rebased VCD files may be losslessly compressed to `.vcd.gz` after verification. The activity audit records the SHA-256 of the uncompressed rebased VCD; each `.time_origin.json` records the uncompressed raw VCD hash. Decompress the rebased file before rerunning the current audit/export scripts against an archived run. Compressed traces and compiled simulator executables are ignored by Git; provenance JSON, reports and results are retained.
