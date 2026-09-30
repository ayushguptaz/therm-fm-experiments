# AES simulated-workload run — 2026-09-30

**Completed:** fresh RTL-to-routed-design flow, functional gate-level AES workload simulation, VCD-based power estimation, power-map conversion and Therm-FM inference. **Temperature accuracy remains unvalidated.**

## Results

| Workload | Measured encryptions | Measurement window | Estimated power | Predicted AES-slot mean | Predicted AES-slot peak |
|---|---:|---:|---:|---:|---:|
| busy | 256 | 6.656 µs | 20.155456 mW | 352.227840 K | 353.753706 K |
| gapped | 256 | 14.848 µs | 19.944787 mW | 352.227385 K | 353.753871 K |

Temperatures in this table refer to the AES output slot and the native die domain, not an average over both output slots. Six cases were generated: two workloads plus a synthetic zero-source diagnostic, each on the native die and a hypothetical 1 mm domain.

## What changed from the original run

- Replaced assumed global/input activity with measured transitions from gate-level simulation of the newly routed netlist. No `set_power_activity` command is used in this path.
- Changed the clock from the original failing 0.82 ns target to 2.0 ns (500 MHz); stock I/O delays therefore become 0.4 ns. Both physical and virtual clocks in the saved final SDC are 2 ns.
- Ran fresh synthesis, floorplanning, placement, CTS, routing and extraction from the saved starting RTL/DEF/SDC. The new layout has 29,153 physical instances. It is not the earlier routed design.
- Generated fixed-key synthetic workloads with seed 20260930. Busy waits for each encryption to finish before the next request; gapped adds 16 extra cycles between requests. The clock remains running.

## Verification evidence

- Every ciphertext matched independent OpenSSL AES-128 reference output: 272 checks per workload, comprising 16 warm-up and 256 measured blocks. The first reference is also checked against a standard known-answer vector.
- Both waveform audits found **zero X/Z value records**. Clock transitions and time windows agree with the 2 ns clock. Timestamps were rebased to zero after warm-up; signal values were preserved.
- OpenSTA reports **47,763 VCD-annotated pins and zero unannotated pins** for each workload.
- Final setup slack +0.591159 ns and hold slack +0.106381 ns, with zero setup/hold violations. Detailed router reports zero DRC errors. These are analyzed-corner/router checks, not full foundry sign-off.
- Maximum power-conservation error across all six maps: 3.47e-18 W.
- Finite input/output arrays and expected shapes: input `[6,4,2,101,101]`, output `[6,2,101,101]`.
- Original checkpoint weight hash verified by inference: `633794c27ec3379cb534d38b1569aec296a7fb51127eabeb69b4bd40c6e632d9`.
- Median synchronized model forward time: 28.93 ms/sample (excludes EDA, simulation, waveform audit, data preparation, loading and warm-up).
- The downloaded compact review archive passed all 158 file hashes in `REVIEW_MANIFEST.sha256`.

## Findings and remaining limits

Adding request gaps reduced estimated power by only 1.05%. The RTL continues updating internal state while the clock runs; request gaps do not imply clock gating. This is a useful reason to simulate transactions rather than assume workload occupancy directly equals switching activity.

The rebased VCD files together contain 1.69 GB of uncompressed data and 350,494,352 value records. Simulation, waveform I/O, import and full-value auditing dominate the workflow relative to neural inference. Large traces are stored compressed on the execution host; they are not included in the compact local review copy or Git.

This is functional gate-level simulation using Liberty-derived cell models, without SDF delay annotation. It does not capture physical delay-induced glitches. The workload is selected synthetic traffic, not an application trace. Power remains a library/STA estimate under that simulated activity, at the typical 1.10 V, 25°C library condition.

Thermal assumptions remain: 200 µm source thickness, uniform heat over each cell footprint, industrial source/coordinate-unit interpretation, a synthetic zero-power second slot, and checkpoint-implied package/cooling. No matching thermal solver or AES fine-tuning was performed. The maps use average power in a steady-state model; they are not temperature transients over the VCD duration.

The native zero-source AES mean is 352.184767 K, and busy increases the mean by only 0.043074 K. The predicted peak is slightly lower than the zero-source peak. Therefore the improved activity source does not establish physically reliable temperature predictions, and tiny differences between workload temperature maps should not be interpreted as validated effects.

The old and new runs also differ in clock and physical layout, so their power difference does not isolate the effect of switching-activity annotation.

## Review files

- [Busy power and temperature figure](outputs/aes_inference/busy_power_temperature.png)
- [Gapped power and temperature figure](outputs/aes_inference/gapped_power_temperature.png)
- [Numeric results](outputs/aes_inference/workload_summary.csv)
- [Workload definition](inputs/workload/workload.json)
- [Activity audit](outputs/workload/activity_audit.json)
- [Verification checks](outputs/workload/verification.json)
- [Complete method and rerun instructions](../../docs/SIMULATED_WORKLOAD_PIPELINE.md)

The original vectorless results and scripts remain saved separately in the experiment root. The new complete-flow entry point is `../../scripts/run_simulated_pipeline.sh`. Its individual stages were executed in this run; the combined convenience wrapper was not independently rerun.

## Execution location and large traces

Execution root: `/home/ubuntu/aes_simulated_20260930T045508Z` on `ubuntu@100.54.108.10`.

This directory is a compact review copy containing starting inputs, final routed artifacts, executed scripts, logs/reports, tensors, predictions and figures. Intermediate layout databases, compiled simulation executable and large waveforms are retained on the execution host. Model source and checkpoint are the shared archived versions referenced by the inference report; weights remain excluded from Git.

To retrieve one rebased waveform from the execution host, run from this review directory:

```bash
scp ubuntu@100.54.108.10:/home/ubuntu/aes_simulated_20260930T045508Z/outputs/workload/busy.vcd.gz outputs/workload/
gunzip outputs/workload/busy.vcd.gz
```

Repeat for `gapped.vcd.gz` if required. Raw recordings are `busy.raw.vcd.gz` and `gapped.raw.vcd.gz`. Uncompressed raw hashes are in the corresponding `.time_origin.json`; rebased hashes are in `activity_audit.json`. Restore/decompress these before rerunning the current waveform audit against the review copy.
