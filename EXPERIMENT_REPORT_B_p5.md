# Experiment Report: Model-B Gradient-Weighted Loss (p=5)

## Overview

Fine-tuning Therm-FM **Model-B** (157.6M parameters) on the HS_SC_refine1 thermal dataset with a gradient-weighted L1 loss (p=5), and comparing against a Model-B L1 baseline (p=1).

Both runs use the same pretrained backbone (`camlab-ethz/poseidon-B`) and training config.

---

## Setup

### Model

| Property | Value |
|----------|-------|
| Architecture | SwinV2 encoder + ConvNeXt decoder |
| Size | **Model-B** — 157.6M parameters |
| embed_dim | 96 |
| depths | [8, 8, 8, 8] |
| Pretrained from | `camlab-ethz/poseidon-B` (HuggingFace) |
| Input channels | 8 (thermal: power map + geometry) |
| Output channels | 2 (temperature field) |

### Training Configuration

| Hyperparameter | Value |
|----------------|-------|
| Hardware | AWS g6e.2xlarge — NVIDIA L40S 46 GB VRAM |
| Batch size | 16 |
| Epochs | 200 |
| Learning rate | 5e-5 |
| LR embedding recovery | 5e-4 |
| LR scheduler | Cosine |
| Max grad norm | 5.0 |
| Train/val split | 80/20 |
| Dataset samples | 5000 |
| `--replace_embedding_recovery` | yes (input/output channel mismatch with poseidon-B) |

### Loss Functions

**Baseline (p=1) — standard L1:**
```
loss = mean(|pred - labels|)
```

**Gradient-Weighted L1 (p=5):**
```python
dT_dx = labels[:, :, :, 1:] - labels[:, :, :, :-1]   # spatial gradient of ground truth
dT_dy = labels[:, :, 1:, :] - labels[:, :, :-1, :]
grad_mag = sqrt(dT_dx² + dT_dy²)
weights = (1 + alpha * grad_mag) / mean(grad_mag)      # alpha=1.0
loss = mean(weights * |pred - labels|)
```

The weights are derived entirely from the **ground truth labels** (not predictions), so they are fixed per sample. Pixels at material interfaces with sharp temperature gradients receive proportionally higher loss weight.

---

## Training

Both experiments ran sequentially on the same machine as a chained script (`run_all_B.sh`):

1. `baseline_B` (p=1) — ~3 hours
2. `gradweight_B` (p=5) — ~3 hours

Total wall-clock: ~6 hours on a single L40S.

### Convergence (eval_loss on validation set)

| Epoch | baseline_B eval_loss | gradweight_B eval_loss |
|-------|---------------------|----------------------|
| 1 | 0.1555 | — |
| 2 | — | 0.00948 |
| 33 | — | 0.00476 |
| 122 | 0.00292 | — |
| 146 | 0.00209 | — |
| 168 | 0.002355 | — |
| 167 | — | 0.001451 |
| 200 | 0.002355 | **0.001360** |

Both models converged fully by epoch 200. gradweight_B achieved ~42% lower final eval_loss than baseline_B.

---

## Results

### Test Set Metrics

| Metric | baseline_B (p=1) | gradweight_B (p=5) | Δ vs baseline |
|--------|-----------------|-------------------|---------------|
| **RMSE** | 0.023269 | **0.022189** | **-4.6%** |
| **R²** | 0.999982 | **0.999983** | +0.0001 |
| **Max Absolute Error** | 0.41770 | **0.40348** | **-3.4%** |
| **MAE** | 0.007822 | **0.007616** | **-2.6%** |
| **PAPE (%)** | 0.12369 | **0.12104** | **-2.1%** |

### Model-B vs Model-T Comparison (p=5)

| Metric | Model-T p=5 (21M) | Model-B p=5 (157.6M) | B improvement over T |
|--------|------------------|----------------------|----------------------|
| RMSE | 0.05196 | **0.02219** | **-57.3%** |
| Max Error | 0.85839 | **0.40348** | **-53.0%** |
| MAE | 0.01779 | **0.007616** | **-57.2%** |
| PAPE (%) | 0.24201 | **0.12104** | **-50.0%** |

---

## Key Findings

1. **Model-B p=5 outperforms all prior Model-T results.** The 157.6M parameter model achieves RMSE 0.02219, which is better than even Model-T p=6 combined loss (RMSE 0.0369). Scale matters more than loss function for this task.

2. **Gradient-weighted loss gives modest gains on Model-B.** p=5 improves RMSE by -4.6% over Model-B baseline, compared to -32.1% for Model-T. The larger model is already better at capturing interface regions with standard L1, leaving less room for gradient weighting to help.

3. **Absolute error is low.** RMSE 0.022°C and MAE 0.0076°C on a thermal field suggests the model is highly accurate for IC thermal prediction at this scale.

4. **Model-B baseline is already stronger than Model-T p=6.** This indicates that for practical deployment, using Model-B with standard loss (simpler, faster to train) may be preferred unless further gains from p=5/p=6 are confirmed.

---

## Files

| File | Description |
|------|-------------|
| `results/baseline_metrics_B.json` | Model-B p=1 test metrics |
| `results/gradweight_metrics_B.json` | Model-B p=5 test metrics with deltas |
| `configs/run_exp_baseline_B.yaml` | Training config for baseline_B |
| `configs/run_exp_gradweight_B.yaml` | Training config for gradweight_B |

---

## Next

- **combined_B (p=6)** — two variants currently training:
  - Warm-start from gradweight_B p=5 best checkpoint (Machine 1, ~2.4 hrs)
  - Cold-start from poseidon-B directly (Machine 2, ~25 min — near completion)
- Results will be added to `EXPERIMENT_REPORT_B_p6.md` once available
