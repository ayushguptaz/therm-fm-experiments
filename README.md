# Therm-FM Loss Function Experiments

Experiments on top of [Therm-FM](https://github.com/haiyangxin/Therm-FM) (arXiv 2605.22663) — a PDE foundation model for 3D-IC chip thermal simulation.

**Goal:** Test whether boundary-aware loss functions reduce maximum temperature error and PAPE (Peak Absolute Percentage Error), the two primary accuracy signals for thermal simulation.

## Results Summary

| Experiment | Loss | RMSE (°C) | Max Error (°C) | MAE (°C) | PAPE (%) | vs Baseline |
|---|---|---|---|---|---|---|
| Baseline | L1 (p=1) | 0.0765 | 1.444 | 0.02105 | 0.396 | — |
| **Grad-Weight** | GW-L1 (p=5) | **0.0520** | **0.858** | **0.01779** | **0.242** | Max **-41%**, PAPE **-39%** |
| Combined | GW-L1 + Interface (p=6) | — | — | — | — | ❌ Did not converge (lambda=0.05 too large) |

> p=6 failure: `grad_norm ~33000` throughout all 200 epochs — interface penalty conflicted with base loss. Fix: reduce `interface_lambda` from 0.05 → 0.001.

> Dataset: HS-SC-refine1 (HotSpot South-China chip, 55×55, 5000 samples, 80/20 train-test)
> Model: Therm-FM-T (21M params, SwinV2 encoder + ConvNeXt decoder)

## Repository Structure

```
├── README.md                    # This file
├── EXPERIMENT_REPORT.md         # Full end-to-end writeup
├── DATASET.md                   # Dataset description
├── configs/
│   ├── run_exp_gradweight_T.yaml   # p=5 training config
│   └── run_exp_combined_T.yaml     # p=6 training config
├── patches/
│   ├── model_loss_extensions.patch  # Diff for scOT/model.py
│   └── train_nan_fix.patch          # Diff for scOT/train.py
└── results/
    ├── baseline_metrics.json
    └── gradweight_metrics.json
```

## Quick Start

```bash
# Clone the original Therm-FM repo
git clone https://github.com/haiyangxin/Therm-FM
cd Therm-FM

# Apply patches
git apply ../therm-fm-experiments/patches/model_loss_extensions.patch
git apply ../therm-fm-experiments/patches/train_nan_fix.patch

# Run grad-weight experiment
accelerate launch scOT/train.py \
  --config configs/run_exp_gradweight_T.yaml \
  --data_path data/thermal_steady/HS_SC_refine1 \
  --checkpoint_path checkpoints/exp/gradweight_T \
  --finetune_from checkpoints/pretrained/poseidon-T-converted \
  --replace_embedding_recovery \
  --wandb_project_name ThermFM-exp \
  --wandb_run_name gradweight_T_HS_SC_r1
```

## Paper Reference

Xin et al., "Therm-FM: Foundation Model is ALL YOU NEED for 3D-ICs Thermal Simulation", DAC 2026. arXiv:2605.22663
