# Pipeline constraints verification

Date: 2026-09-30. Scope: saved AES design and the checkpoint actually used. No configuration or model weights changed.

## Verified from the source and final files

- Top module `aes_cipher_top`; 258 non-clock input bits (`rst`, `ld`, 128 `key`, 128 `text_in`) and 129 output bits (`done`, 128 `text_out`). Exact bit-name sets match final SDC delay annotations.
- Source and final SDC specify two clocks at 0.82 ns: physical `clk` and virtual `vclk_clk`. Frequency is approximately 1.2195 GHz.
- Input and output delay: 0.164 ns, or 20% of the period. All non-clock input/output bits have annotations. Source SDC does not specify separate minimum and maximum I/O values.
- Initial latency is 0.210 ns on both clocks. Final physical clock uses propagated clock-tree delay; virtual clock retains 0.210 ns. This is expected for a clock-tree result rather than a lost final physical-clock constraint.
- Initial DEF uses 2000 database units per µm and a 499700 × 501200 database-unit die. Converted dimensions match the final 249.85 × 250.60 µm geometry.
- Final SDC has no explicit `set_clock_uncertainty`, `set_driving_cell`, `set_input_transition` or `set_load`. These omissions need review against the intended environment; all-port delay coverage does not prove a realistic system specification.
- Nangate45 typical library declares 1 ns time units, nominal 1.10 V and 25°C. SPEF explicitly declares ns, pF and ohm units. OpenSTA performs the file-unit conversions.
- The saved checkpoint specifies 101 × 101, 8 input channels and 2 outputs. The input is compatible with that configuration but includes a synthetic zero-power second slot.

## Fresh analysis and satisfaction of constraints

Reloaded final ODB, SDC, typical Liberty and extracted SPEF into the pinned OpenROAD image. Ran `report_units`, `check_setup -verbose`, and worst-slack reports for max/min timing. No `check_setup` diagnostic appeared. OpenROAD did warn that the hierarchical flow is under development. Fresh rounded worst slack agrees with saved metrics: max -0.04 ns, min +0.11 ns.

The saved detailed metrics show setup worst slack -0.0380276 ns with 19 violations: the 0.82 ns target is NOT met. Hold worst slack is +0.10568 ns with zero violations. Saved slew/capacitance violation metrics are zero. The detailed router reports zero DRC errors and zero antenna nets/pins. These are analyzed-corner/router results, not full foundry sign-off or functional AES certification.

## Unverified physical inputs

Power uses assumed switching activity and duty, without AES workload traces. The thermal adapter assumes 200 µm source thickness and supplies a second, zero-source slot to the IND-8C checkpoint. Actual package materials, interfaces, cooling and matched AES labels remain missing. Exact industrial source-field scaling needs confirmation from dataset-generation provenance. Tensor checks and power conservation do not establish temperature accuracy.

## Reproduction and evidence

- `presentation/.build/verify_constraints.py`: source/final file checks.
- `presentation/.build/check_constraints.tcl`: fresh OpenSTA load/check commands.
- `presentation/.build/opensta_constraint_check.log`: complete fresh output.
- `presentation/constraints_verification.json`: machine-readable findings.
- `inputs/orfs_config/constraint.sdc`, `config.mk`, `aes_ng45_fp.def`.
- `flow/results/nangate45/aes/base/6_final.sdc`, `.odb`, `.spef`.
- `flow/logs/nangate45/aes/base/6_report.json`.
