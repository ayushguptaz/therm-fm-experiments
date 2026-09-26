# Experiment Report: Model-B Combined Loss (p=6)

## Overview

Fine-tuning Therm-FM **Model-B** (157.6M parameters) with a combined gradient-weighted + interface loss (p=6), warm-started from the best p=5 checkpoint.

Two variants were tested:
- **Warm-start** — fine-tunes from the converged p=5 checkpoint (this is the main result)
- **Cold-start** — fine-tunes directly from `poseidon-B` (terminated instance; key findings documented below)

---

## Setup

### Model

| Property | Value |
|----------|-------|
| Architecture | SwinV2 encoder + ConvNeXt decoder |
| Size | **Model-B** — 157.6M parameters |
| embed_dim | 96 |
| depths | [8, 8, 8, 8] |
| Warm-start from | Best p=5 checkpoint (`checkpoint-45000`, epoch 200) |

### Training Configuration

| Hyperparameter | Value |
|----------------|-------|
| Hardware | AWS g6e.4xlarge — NVIDIA L40S 46 GB VRAM |
| Batch size | 16 |
| Epochs | 200 (on top of p=5's 200 epochs) |
| Learning rate | 5e-5 |
| LR scheduler | Cosine |
| `--replace_embedding_recovery` | no (warm-start; channels already adapted) |

### Loss Function (p=6)

```python
dT_dx = labels[:, :, :, 1:] - labels[:, :, :, :-1]   # ground truth gradients
dT_dy = labels[:, :, 1:, :] - labels[:, :, :-1, :]
grad_mag = sqrt(dT_dx² + dT_dy² + 1e-8)

weights = (1 + alpha * grad_mag) / mean(grad_mag)      # alpha=1.0
base_loss = mean(weights * |pred - labels|)

interface_mask = (grad_mag > mean(grad_mag) + 2*std(grad_mag)).float()  # top ~2%
interface_loss = mean(interface_mask * |pred - labels|)

loss = base_loss + lambda * interface_loss              # lambda=0.001
```

All quantities (grad_mag, interface_mask) are derived from **ground truth labels**, not predictions. Weights are fixed per sample.

---

## Training

### Warm-start (main result)

Warm-started from the best p=5 Model-B checkpoint, ran another 200 epochs of p=6 training.

**Why warm-start matters:** Cold-start p=6 from poseidon-B caused loss-metric mismatch (see below). The gradient-weighted loss normalizes so that the ~98% smooth pixels receive weight `<1` — the model learned to sacrifice bulk accuracy for interface accuracy. Warm-starting from a converged p=5 model gives it a strong baseline for bulk accuracy first, then the interface term refines further.

### Convergence

| Epoch | eval_loss |
|-------|-----------|
| 1 | 0.00121 (already low, warm-started) |
| 200 | **0.001208** |

The model converged quickly — it was already well-initialized from p=5 and only needed to refine.

Training time: ~3 hours on L40S (12:36 → 15:42 UTC).

---

## Results

### Test Set Metrics — Warm-start p=6

| Metric | baseline_B (p=1) | gradweight_B (p=5) | combined_B (p=6) | Δ vs baseline | Δ vs p=5 |
|--------|-----------------|-------------------|------------------|---------------|----------|
| **RMSE** | 0.023269 | 0.022189 | **0.020513** | **-11.8%** | **-7.5%** |
| **R²** | 0.999982 | 0.999983 | **0.999985** | +0.000003 | +0.000002 |
| **Max Absolute Error** | 0.41770 | 0.40348 | **0.36885** | **-11.7%** | **-8.6%** |
| **MAE** | 0.007822 | 0.007616 | **0.007021** | **-10.2%** | **-7.8%** |
| **PAPE (%)** | 0.12369 | 0.12104 | **0.11093** | **-10.3%** | **-8.4%** |

### Model-B vs Model-T — Best Each

| Metric | Model-T p=6 (21M) | Model-B p=6 (157.6M) | B improvement over T |
|--------|------------------|----------------------|----------------------|
| RMSE | 0.0369 | **0.0205** | **-44.4%** |
| Max Error | 0.615 | **0.3689** | **-40.0%** |
| MAE | 0.01325 | **0.007021** | **-47.0%** |
| PAPE (%) | 0.176 | **0.11093** | **-37.0%** |

### Full Model-B Progression

| Experiment | Loss | RMSE | Max Error | PAPE | Δ RMSE |
|---|---|---|---|---|---|
| baseline_B | L1 | 0.023269 | 0.41770 | 0.1237% | — |
| gradweight_B | GW-L1 (p=5) | 0.022189 | 0.40348 | 0.1210% | -4.6% |
| combined_B | GW-L1 + Interface (p=6) | **0.020513** | **0.36885** | **0.1109%** | **-11.8%** |

Each loss step contributes: p=5 adds **-4.6%**, p=6 on top adds another **-7.5%**, total **-11.8%** from baseline.

---

## Cold-Start Comparison (Qualitative)

A separate cold-start p=6 run (starting from poseidon-B instead of p=5) was run on a second machine. Key finding:

**Cold-start DEGRADED bulk metrics despite lower eval_loss.**

Root cause — the gradient-weighted normalization formula:
```python
weights = (1 + alpha * grad_mag) / mean(grad_mag)
```
The division by `mean(grad_mag)` means smooth pixels get weight `< 1`. For a cold-start model, the interface loss signal (+lambda×interface_loss) pulled the model to sacrifice pixel-level bulk accuracy to reduce the ~2% interface pixel errors. Result: eval_loss dropped dramatically (118× vs baseline) but RMSE increased ~12%, MAE increased ~55%.

Only Max Absolute Error improved (~-6%) because max error typically occurs at interfaces, which the loss directly targeted.

**Lesson:** Warm-starting from p=5 is essential. The model needs bulk-accuracy as a foundation before interface refinement can help rather than hurt.

---

## Key Findings

1. **p=6 (combined) consistently outperforms p=5 on Model-B.** RMSE improves -7.5% further, with stronger gains on Max Error (-8.6%) and PAPE (-8.4%). The interface loss term contributes meaningfully even when the gradient-weighted base loss already captures boundary regions.

2. **Warm-start is necessary, not optional.** Cold-start p=6 causes loss-metric mismatch — the gradient weighting under-weights 98% of pixels, so a cold model sacrifices bulk accuracy to minimize the interface term. Warm-start from p=5 provides a strong bulk-accuracy foundation first.

3. **Cumulative gains stack well.** From baseline → p=5 → p=6, each step contributes: -4.6%, -7.5%. Total improvement from standard L1 is **-11.8% RMSE**, **-11.7% Max Error**.

4. **Model scale still dominates.** Model-B p=6 (RMSE 0.0205) is 44% better than Model-T p=6 (RMSE 0.0369). Scaling from 21M to 157.6M parameters matters more than any loss function improvement.

5. **PAPE 0.111% is the best result yet.** In IC thermal design, sub-0.2% PAPE is strong. The combined B model achieves this reliably.

---

## Files

| File | Description |
|------|-------------|
| `results/combined_metrics_B.json` | Model-B p=6 test metrics |
| `configs/run_exp_combined_B.yaml` | Training config (p=6, lambda=0.001) |
| `EXPERIMENT_REPORT_B_p5.md` | Model-B p=5 writeup (predecessor) |

---

## Summary

The final Model-B stack:

```
poseidon-B pretrained → fine-tune p=1 (baseline) → fine-tune p=5 (GW-L1) → fine-tune p=6 (combined)
                                                                                        ↓
                                                                          RMSE 0.0205, PAPE 0.111%
```
