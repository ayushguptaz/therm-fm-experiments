# Therm-FM Loss Function Experiments

Experiments on top of [Therm-FM](https://github.com/haiyangxin/Therm-FM) (arXiv 2605.22663) — a PDE foundation model for 3D-IC chip thermal simulation.

**Goal:** Test whether boundary-aware loss functions reduce maximum temperature error and PAPE (Peak Absolute Percentage Error), the two primary accuracy signals for thermal simulation.

## Results Summary

### Model-T (21M params) — NVIDIA T4

| Experiment | Loss | RMSE (°C) | Max Error (°C) | MAE (°C) | PAPE (%) | vs Baseline |
|---|---|---|---|---|---|---|
| Baseline-T | L1 (p=1) | 0.0765 | 1.444 | 0.02105 | 0.396% | — |
| Grad-Weight-T | GW-L1 (p=5) | 0.0520 | 0.858 | 0.01779 | 0.242% | Max **-41%**, PAPE **-39%** |
| **Combined-T** | **GW-L1 + Interface (p=6)** | **0.0369** | **0.615** | **0.01325** | **0.176%** | Max **-57%**, PAPE **-56%** |

### Model-B (157.6M params) — NVIDIA L40S

| Experiment | Loss | RMSE (°C) | Max Error (°C) | MAE (°C) | PAPE (%) | vs Baseline-B | vs Best T |
|---|---|---|---|---|---|---|---|
| Baseline-B | L1 (p=1) | 0.02327 | 0.4177 | 0.007822 | 0.1237% | — | **-70%** RMSE |
| **Grad-Weight-B** | **GW-L1 (p=5)** | **0.02219** | **0.4035** | **0.007616** | **0.1210%** | Max **-3.4%**, PAPE **-2.1%** | **-40%** RMSE vs T p=6 |
| **Combined-B** | **GW-L1 + Interface (p=6)** | **0.02051** | **0.3688** | **0.007021** | **0.1109%** | Max **-11.7%**, PAPE **-10.3%** | **-44%** RMSE vs T p=6 |

> Dataset: HS-SC-refine1 (HotSpot South-China chip, 55×55, 5000 samples, 80/20 train-test)

**Key finding (Model-B):** Model scale dominates, but loss functions still matter. Model-B baseline (157.6M) already beats Model-T p=6 (21M) by 44% RMSE. The p=5 → p=6 chain adds -11.8% cumulative RMSE vs Model-B baseline. **Warm-start is required for p=6** — cold-start causes loss-metric mismatch (+12% RMSE despite lower eval_loss).

## Repository Structure

```
├── README.md                       # This file
├── EXPERIMENTS_SUMMARY.md          # All experiments in order — key findings
├── EXPERIMENT_REPORT.md            # Model-T full writeup (p=1/p=5/p=6)
├── EXPERIMENT_REPORT_B_p5.md       # Model-B p=5 experiment report
├── EXPERIMENT_REPORT_B_p6.md       # Model-B p=6 experiment report
├── DATASET.md                      # Dataset description
├── configs/
│   ├── run_exp_gradweight_T.yaml      # Model-T p=5 config
│   ├── run_exp_combined_T.yaml        # Model-T p=6 config
│   ├── run_exp_baseline_B.yaml        # Model-B p=1 config
│   ├── run_exp_gradweight_B.yaml      # Model-B p=5 config
│   └── run_exp_combined_B.yaml        # Model-B p=6 config
├── patches/
│   ├── model_loss_extensions.patch    # Diff for scOT/model.py
│   └── train_nan_fix.patch            # Diff for scOT/train.py
└── results/
    ├── baseline_metrics.json          # Model-T p=1
    ├── gradweight_metrics.json        # Model-T p=5
    ├── combined_metrics_001.json      # Model-T p=6 (lambda=0.001, final)
    ├── baseline_metrics_B.json        # Model-B p=1
    ├── gradweight_metrics_B.json      # Model-B p=5
    └── combined_metrics_B.json        # Model-B p=6
```

## Quick Start

```bash
# Clone the original Therm-FM repo
git clone https://github.com/haiyangxin/Therm-FM
cd Therm-FM

# Apply patches
git apply ../therm-fm-experiments/patches/model_loss_extensions.patch
git apply ../therm-fm-experiments/patches/train_nan_fix.patch

# Run grad-weight experiment (p=5)
accelerate launch scOT/train.py \
  --config configs/run_exp_gradweight_T.yaml \
  --data_path data/thermal_steady/HS_SC_refine1 \
  --checkpoint_path checkpoints/exp/gradweight_T \
  --finetune_from checkpoints/pretrained/poseidon-T-converted \
  --replace_embedding_recovery \
  --wandb_project_name ThermFM-exp \
  --wandb_run_name gradweight_T_HS_SC_r1

# Run combined experiment (p=6) — warm-start from converged p=5 checkpoint
# IMPORTANT: do NOT use --replace_embedding_recovery here; warm-start from p=5 directly
accelerate launch scOT/train.py \
  --config configs/run_exp_combined_T.yaml \
  --data_path data/thermal_steady/HS_SC_refine1 \
  --checkpoint_path checkpoints/exp/combined_T_from_p5 \
  --finetune_from checkpoints/exp/gradweight_T/ThermFM-exp/gradweight_T_HS_SC_r1/checkpoint-17910 \
  --wandb_project_name ThermFM-exp \
  --wandb_run_name combined_T_from_p5_r1
```

## Paper Reference

Xin et al., "Therm-FM: Foundation Model is ALL YOU NEED for 3D-ICs Thermal Simulation", DAC 2026. arXiv:2605.22663
