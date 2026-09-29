# Therm-FM: New Design Pipeline
## From Verilog + Constraints to Thermal Map

---

## Overview

Therm-FM is a **surrogate model** — it replaces a slow thermal simulator with a fast neural
network after being trained on (power map → temperature) pairs. Running a new design requires:

1. EDA flow: Verilog → placed layout → per-cell power map
2. Thermal simulator: power map → temperature labels (training data generation)
3. Fine-tune Therm-FM on those pairs
4. Run inference for any new power scenario

---

## Step 1 — Logic Synthesis

**Input:** RTL Verilog, timing constraints (.sdc), technology library (.lib, .lef)

**Tools:** Yosys (open-source) or Synopsys DC / Cadence Genus

```bash
# Yosys example
yosys -p "
  read_verilog design.v
  synth -top top_module
  dfflibmap -liberty tech.lib
  abc -liberty tech.lib
  write_verilog netlist.v
"
```

**Output:** Gate-level netlist (netlist.v)

---

## Step 2 — Place & Route

**Input:** Synthesized netlist, technology LEF/DEF, floorplan constraints

**Tools:** OpenROAD (open-source) or Cadence Innovus / Synopsys ICC2

```bash
# OpenROAD
openroad -exit flow.tcl
```

**Output:**
- `design.def` — placed layout (each cell has x,y coordinates)
- Routing info, power rails

---

## Step 3 — Power Analysis

**Goal:** Get power dissipated per cell in Watts

**Two components:**
- **Static (leakage):** directly from technology library
- **Dynamic (switching):** requires switching activity

```bash
# Get switching activity from RTL simulation
vcs -R design.v testbench.v -o sim
./sim +vcd=toggle.vcd

# PrimeTime-PX
pt_shell -f power_analysis.tcl   # outputs per-cell power → power.rpt
```

**Open-source alternative:** OpenSTA + toggling rates from simulation

**Output:** Per-cell power report (`power.rpt`) with cell name → Watts mapping

---

## Step 4 — Generate Spatial Power Map

**Goal:** Map cell-level power → 2D grid (H×W) per die layer

**Resolution must match the training data of the model you will fine-tune from:**

```
HS_SC_refine2:  87×87
HS_QC_refine2:  63×63
HS_OC_refine2:  151×151
IND chips:      101×101
```

**Script:** Parse DEF for cell placements + power report for cell power:

```python
import numpy as np

# chip physical dimensions in meters
chip_W_m = 1e-3          # e.g. 1 mm
chip_H_m = 1e-3
grid_H, grid_W = 87, 87  # must match model training resolution

power_map = np.zeros((num_layers, grid_H, grid_W), dtype=np.float32)

for cell in placed_cells:
    cell_x_m, cell_y_m = cell.x_um * 1e-6, cell.y_um * 1e-6
    cell_layer = cell.die_layer            # 0-indexed
    cell_power_W = power_report[cell.name]

    # map to grid
    gi = int(cell_y_m / chip_H_m * grid_H)
    gj = int(cell_x_m / chip_W_m * grid_W)
    gi, gj = min(gi, grid_H-1), min(gj, grid_W-1)

    # power density W/m^2
    cell_area_m2 = chip_W_m * chip_H_m / (grid_H * grid_W)
    power_map[cell_layer, gi, gj] += cell_power_W / cell_area_m2
```

**Output:** `power_map.npy` — shape (L, H, W), units W/m²

---

## Step 5 — Generate Temperature Labels with Thermal Simulator

**This step is required to build training data.**
Therm-FM needs (power map → steady-state temperature) pairs.

**Tools:**
- HotSpot (academic, free): 2D and 3D RC thermal models
- ANSYS Icepak / Cadence Celsius: commercial, high accuracy
- Custom FEM/FDM solver

```bash
# HotSpot example (2D)
hotspot -c hotspot.config -f power_map.ptrace -o temperature.grid

# For 3D-IC: use layer stacks, thermal interface materials, boundary conditions
```

**You need N samples** (different power scenarios) for training:
- Vary power patterns: different workloads, utilization levels
- Min ~1000 samples; datasets in this repo use N=5000

**Output:** `output.mat` — shape (N, L, H, W), temperature in Kelvin

---

## Step 6 — Create input.mat

**Input format:**
```
input.mat: (N, 4, L, H, W)   ← HDF5 file, key "data"
  Dim 1 (P=0): power density  [W/m²]
  Dim 1 (P=1): x-coordinate   [m or normalized]
  Dim 1 (P=2): y-coordinate   [m or normalized]
  Dim 1 (P=3): z-position     [m or layer index]
```

Verified from normalization constants (HS_SC_refine2):
- mean[P=0]=18.69 → power density (large physical values)
- mean[P=1]=mean[P=2]=0.008 → x,y coordinates (small physical values)
- mean[P=3]=0.0 → z-position layer 0

```python
import h5py
import numpy as np

N, L, H, W = 5000, 2, 87, 87
inputs = np.zeros((N, 4, L, H, W), dtype=np.float32)

# x,y coordinate grids (same for all samples and layers)
x_grid = np.tile(np.linspace(0, chip_W_m, W), (H, 1)).astype(np.float32)
y_grid = np.tile(np.linspace(0, chip_H_m, H), (W, 1)).T.astype(np.float32)
z_vals = np.array([layer_heights[l] for l in range(L)], dtype=np.float32)

for n in range(N):
    for l in range(L):
        inputs[n, 0, l] = power_maps[n, l]         # W/m²
        inputs[n, 1, l] = x_grid
        inputs[n, 2, l] = y_grid
        inputs[n, 3, l] = z_vals[l]                # scalar broadcast

with h5py.File("input.mat", "w") as f:
    f.create_dataset("data", data=inputs, compression="gzip")
```

---

## Step 7 — Compute or Reuse Normalization Constants

**Option A — Compute from your training data:**
```python
# Pass no --stats_json to train.py → auto-computed from training split
# Then save the computed stats for inference
```

**Option B — Reuse existing chip constants (if geometry is similar):**
```
data/thermal_steady/normalization_constants/thermal_steady/
├── HS_SC_normalization_constants.json
├── HS_QC_normalization_constants.json
├── HS_OC_normalization_constants.json
├── IND_8C_normalization_constants.json
└── IND_32C_normalization_constants.json
```

JSON structure:
```json
{
  "input":  {"mean": [L*P values],  "std": [L*P values]},
  "output": {"mean": [L values],    "std": [L values]}
}
```

---

## Step 8 — Fine-tune Therm-FM

```bash
accelerate launch scOT/train.py \
    --config configs/multichip_exp/baseline_L2_HS_SC_refine1.yaml \
    --data_path data/thermal_steady/YOUR_CHIP \
    --checkpoint_path checkpoints/your_chip \
    --finetune_from checkpoints/pretrained/poseidon-T \
    --replace_embedding_recovery \
    --stats_json data/thermal_steady/normalization_constants/thermal_steady/YOUR_CHIP_normalization_constants.json \
    --wandb_project_name Therm-FM \
    --wandb_run_name your_chip_baseline_T
```

Key config parameters (from paper):
```yaml
model_name:   T           # Therm-FM-T (20.7M params)
num_epochs:   200
batch_size:   40
lr:           0.00005
lr_scheduler: cosine
weight_decay: 0.000001
train_ratio:  0.8         # 80% train, 20% test
p:            2           # L2/MSE loss (baseline)
```

---

## Step 9 — Run Inference on New Power Scenario

```bash
python scOT/inference.py \
    --mode save_samples \
    --model_path checkpoints/your_chip \
    --data_path data/thermal_steady/YOUR_CHIP \
    --stats_json data/thermal_steady/normalization_constants/thermal_steady/YOUR_CHIP_normalization_constants.json \
    --output_path predictions/your_chip_temperature.mat
```

Or use `eval_multichip_v2.py` for paper-exact metrics:
```bash
python eval_multichip_v2.py \
    --ckpt_dir checkpoints/your_chip \
    --data_dir data/thermal_steady/YOUR_CHIP \
    --norm_dir data/thermal_steady/normalization_constants/thermal_steady \
    --prefix YOUR_CHIP \
    --out results/your_chip_metrics.json
```

---

## Step 10 — Post-process Output

```python
import h5py
import numpy as np
import json

# Load predictions and denormalize
with h5py.File("predictions/your_chip_temperature.mat", "r") as f:
    pred_norm = f["data"][:]            # (N, L, H, W) — normalized

with open("YOUR_CHIP_normalization_constants.json") as f:
    stats = json.load(f)["output"]

mean = np.array(stats["mean"]).reshape(L, 1, 1)
std  = np.array(stats["std"]).reshape(L, 1, 1)
temp_K = pred_norm * std + mean         # Kelvin

# Hotspot detection
temp_C = temp_K - 273.15
max_temp = temp_C.max(axis=(2, 3))     # (N, L) — per sample per layer
print(f"Max temperature: {temp_C.max():.1f} °C")
print(f"Hotspot location: {np.unravel_index(temp_C.argmax(), temp_C.shape)}")
```

---

## Summary

```
Verilog + .sdc
     ↓  synthesis (Yosys / DC)
Gate-level netlist
     ↓  place & route (OpenROAD / Innovus)
Placed layout (.def) + power map (.rpt)
     ↓  power analysis (OpenSTA / PrimeTime-PX)
Per-cell power → spatial power grid  [W/m², shape: (L, H, W)]
     ↓  thermal simulator (HotSpot / ANSYS)  ← generates training labels
(power, temperature) pairs  [N samples]
     ↓  format as input.mat / output.mat  [(N,4,L,H,W) / (N,L,H,W)]
     ↓  fine-tune Therm-FM  (train.py, 200 epochs)
Fine-tuned checkpoint
     ↓  inference.py / eval_multichip_v2.py
Temperature map  [(N, L, H, W) in Kelvin]
```

---

## Key Constraints

| Constraint | Value |
|---|---|
| Grid resolution | Must match training data (e.g. 87×87 for HS_SC) |
| Input key in .mat | `data` |
| HDF5 format | MATLAB v7.3 (h5py compatible) |
| Coordinate units | Meters (physical) or consistent with training |
| Training samples | Minimum ~1000; paper uses 5000 |
| Model init | Always start from `poseidon-T` pretrained checkpoint |
| Train ratio | 0.8 for HS-type chips, 0.9 for IND-type chips |
