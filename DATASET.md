# Dataset Description

## Overview

All experiments use the **HotSpot South-China refine1 (HS-SC-refine1)** dataset from the Therm-FM paper.

- **Chip family:** HotSpot South-China (HS-SC) — academic 3D-IC benchmark
- **Resolution:** 55 × 55 pixels in-plane, 2 vertical layers
- **Samples:** 5,000 steady-state simulations
- **Split:** 80% train (4,000) / 20% test (1,000)
- **Source:** Google Drive linked from [haiyangxin/Therm-FM](https://github.com/haiyangxin/Therm-FM)

## Why HS-SC-refine1 (not refine2)?

The Therm-FM paper evaluates on **refine2** (87×87), which has higher spatial resolution. We used **refine1** (55×55) to fit within T4 GPU memory (16GB) at batch_size=40. The results are not directly comparable to paper Table numbers but the relative improvements between experiments are valid.

## File Format

Each dataset folder contains two HDF5 MATLAB v7.3 files:

```
HS_SC_refine1/
├── input.mat    # shape: (5000, 4, 2, 55, 55)
└── output.mat   # shape: (5000, 2, 55, 55)
```

### Input tensor `(N, P, L, H, W)`

| Axis | Symbol | Meaning |
|---|---|---|
| N | 5000 | Number of simulation samples |
| P | 4 | Input channels |
| L | 2 | Number of vertical chip layers |
| H, W | 55, 55 | In-plane spatial resolution |

Input channels:
| Index | Field | Description |
|---|---|---|
| 0 | p | Volumetric power density (W/m³) |
| 1 | x | x-coordinate (normalized) |
| 2 | y | y-coordinate (normalized) |
| 3 | z | z-coordinate / layer index |

### Output tensor `(N, L, H, W)`

Steady-state temperature field per layer (Kelvin, normalized to zero mean unit variance per training set statistics).

`output[n, l, h, w]` = temperature at sample n, layer l, spatial position (h, w).

## All Available Datasets

| Folder | Chip | Layers | H×W | Samples |
|---|---|---|---|---|
| HS_SC_refine1 | South-China | 2 | 55×55 | 5000 |
| HS_SC_refine2 | South-China | 2 | 87×87 | 5000 |
| HS_QC_refine1 | Quad-Core | 2 | 39×39 | 5000 |
| HS_QC_refine2 | Quad-Core | 2 | 63×63 | 5000 |
| HS_OC_refine1 | Octa-Core | 3 | 85×85 | 5000 |
| HS_OC_refine2 | Octa-Core | 3 | 151×151 | 5000 |
| IND_8C | Industrial 8-core | — | — | proprietary |
| IND_32C | Industrial 32-core | — | — | proprietary |

## Physics Context

3D-IC chips have extreme thermal conductivity contrasts:
- Copper vias / interconnects: k ≈ 385 W/m·K
- Silicon dioxide (interlayer): k ≈ 1.4 W/m·K
- Ratio: **≈275×**

This creates sharp temperature gradients at material boundaries, which are:
1. Hard to predict accurately with uniform-loss training
2. Critical for thermal reliability — hot-spot detection and PAPE are the primary engineering metrics

## Normalization

The dataset is normalized using pre-computed statistics in `data/normalization_constants/`. Input and output tensors are z-score normalized per channel group. The model operates on normalized values; `test_additional_metrics.json` reports errors in the **original physical units (°C / K)** after denormalization.
