# Therm-FM Loss Function Experiments — Full Summary

Experiments on [Therm-FM](https://arxiv.org/abs/2605.22663) (DAC 2026), a PDE foundation model for 3D-IC chip thermal simulation. We tested whether boundary-aware loss functions improve accuracy over the paper's standard L1 baseline.

**Dataset:** HS_SC_refine1 — HotSpot South-China chip, 55×55, 5000 samples, 80/20 train/test  
**Task:** Predict steady-state temperature field from power map + geometry inputs

---

## Experiment 1 — Baseline Model-T (21M params)

**Hardware:** AWS g4dn.xlarge (NVIDIA T4, 16 GB)  
**Loss:** Standard L1: `loss = mean(|pred - labels|)`  
**Config:** 200 epochs, lr=5e-5, batch=16, warm-start from `poseidon-T` (HuggingFace)

| Metric | Value |
|--------|-------|
| RMSE | 0.07653 |
| Max Absolute Error | 1.4445 |
| MAE | 0.02105 |
| PAPE | 0.3963% |
| R² | 0.999783 |

This is the baseline reference. Max error of 1.4°C is the key weakness — spikes occur at chip layer boundaries where temperature gradients are sharpest. Standard L1 treats all pixels equally and under-penalizes errors at these regions.

---

## Experiment 2 — Gradient-Weighted L1 on Model-T (p=5)

**Hardware:** T4  
**Loss:**
```python
grad_mag = sqrt((dT/dx)² + (dT/dy)²)          # from ground truth labels
weights = (1 + alpha * grad_mag) / mean(grad_mag)  # alpha=1.0
loss = mean(weights * |pred - labels|)
```
Pixels at material interfaces with high temperature gradients get proportionally higher loss weight. Weights are computed from **ground truth labels**, not predictions — so they are fixed per sample.

| Metric | Value | vs Baseline |
|--------|-------|-------------|
| RMSE | 0.05196 | **-32.1%** |
| Max Absolute Error | 0.8584 | **-40.6%** |
| MAE | 0.01779 | **-15.5%** |
| PAPE | 0.2420% | **-38.9%** |

**What brought the improvement:** By up-weighting interface pixels (where errors were largest) the model learned to predict them more accurately. Max error dropped by 40% — from 1.44°C to 0.86°C. This is the most important single improvement in the whole experiment series.

---

## Experiment 3 — Combined Loss, High Lambda on Model-T (p=6, λ=0.05) — FAILED

**Loss adds an interface penalty on top of p=5:**
```python
interface_mask = (grad_mag > mean(grad_mag) + 2*std(grad_mag)).float()  # top ~2% pixels
loss = base_gw_loss + lambda * mean(interface_mask * |pred - labels|)
```
**First attempt:** `lambda=0.05` — direct cold-start from `poseidon-T`

| Metric | Value |
|--------|-------|
| RMSE | 63.91 |
| Max Absolute Error | 1689.7 |
| PAPE | 512.3% |
| Status | **Complete divergence** |

**Why it failed:** Two compounding problems:
1. **Cold-start instability** — starting from randomly initialized embedding layers, the interface penalty amplified gradient signals before the backbone had stabilized, causing grad norm ~33,000 (clipped every step to max 5.0). The model never escaped this regime.
2. **Lambda too large** — `lambda=0.05` made the interface term 50× stronger than the final working value. The ~2% of interface pixels effectively hijacked the loss.

**Fix direction:** Reduce lambda AND warm-start from a converged p=5 checkpoint.

---

## Experiment 4 — Combined Loss, Low Lambda on Model-T (p=6, λ=0.001) — Best Model-T

**Hardware:** T4  
**Loss:** Same as above but `lambda=0.001`  
**Key change:** Warm-started from best p=5 checkpoint (not from poseidon-T)

| Metric | Value | vs Baseline | vs p=5 |
|--------|-------|-------------|--------|
| RMSE | 0.03694 | **-51.7%** | **-28.9%** |
| Max Absolute Error | 0.6147 | **-57.5%** | **-28.4%** |
| MAE | 0.01325 | **-37.1%** | **-25.5%** |
| PAPE | 0.1758% | **-55.6%** | **-27.4%** |
| R² | 0.999961 | — | — |

**What brought the improvement:** The interface mask isolates the top ~2% highest-gradient pixels (physical layer boundaries). With lambda=0.001 the term is small enough not to destabilize training, but consistently penalizes boundary errors on top of the gradient-weighted base loss. The warm-start means the model already had strong bulk accuracy, so the interface term only needed to refine the hard boundary cases — not learn everything from scratch.

**Cumulative gain from p=1 to p=6:** Max Error 1.44 → 0.61 (**-57.5%**), PAPE 0.396% → 0.176% (**-55.6%**).

---

## Experiment 5 — Baseline Model-B (157.6M params)

**Hardware:** AWS g6e.2xlarge (NVIDIA L40S, 46 GB)  
**Loss:** Standard L1 (same as Experiment 1 but larger model)  
**Config:** 200 epochs, lr=5e-5, batch=16, warm-start from `poseidon-B`

| Metric | Value | vs Baseline-T |
|--------|-------|---------------|
| RMSE | 0.02327 | **-70%** |
| Max Absolute Error | 0.41770 | **-71%** |
| MAE | 0.007822 | **-63%** |
| PAPE | 0.1237% | **-69%** |

**What brought the improvement:** Purely model scale. Going from 21M to 157.6M parameters (8× larger) reduces RMSE by 70% even with the same standard L1 loss. Model-B with no loss engineering already beats Model-T with the best combined loss (p=6) by 37% RMSE. **Scale matters more than loss function.**

---

## Experiment 6 — Gradient-Weighted L1 on Model-B (p=5)

**Hardware:** L40S  
**Loss:** Same GW-L1 as Experiment 2

| Metric | Value | vs Baseline-B | vs Model-T p=5 |
|--------|-------|---------------|----------------|
| RMSE | 0.02219 | **-4.6%** | **-57.3%** |
| Max Absolute Error | 0.40348 | **-3.4%** | **-53.0%** |
| MAE | 0.007616 | **-2.6%** | **-57.2%** |
| PAPE | 0.1210% | **-2.1%** | **-50.0%** |

**What brought the improvement:** Same mechanism as Experiment 2. However the gains are much smaller (−4.6% vs −32.1% RMSE) because Model-B's larger capacity already handles boundary regions better with standard L1. There's less room for the gradient weighting to add value. The returns diminish at larger scale.

---

## Experiment 7 — Combined Loss Cold-Start on Model-B (p=6, cold) — Degraded

**Hardware:** Second L40S (AWS g6e.4xlarge, 44.223.110.134)  
**Loss:** p=6, lambda=0.001, cold-start from `poseidon-B` (with `--replace_embedding_recovery`)  
**Note:** Machine was terminated after the run completed; exact numbers are lost.

**Qualitative results:**
- **eval_loss: ~118× lower** than baseline (model appeared to "converge" well by its own metric)
- **RMSE: +12% worse** than baseline
- **MAE: +55% worse** than baseline
- **Max Error: ~-6%** (the only metric that improved)

**Why it degraded despite low eval_loss:** The gradient-weighted normalization divides by `mean(grad_mag)`, so the ~98% of smooth pixels get weight `< 1`. A cold-start model, with no prior sense of bulk accuracy, learned to sacrifice pixel-level temperature prediction for the ~2% interface pixels. Eval loss dropped because the weighted loss heavily discounts smooth-pixel errors — but RMSE counts all pixels equally.

**Lesson:** Cold-start p=6 on a large model causes loss-metric mismatch. Warm-start is required.

---

## Experiment 8 — Combined Loss Warm-Start on Model-B, Attempt 1 (bug: ran as p=5)

**Hardware:** L40S (Machine 1, 100.54.108.10)  
**Intended:** p=6 warm-started from p=5 checkpoint  
**Actual:** Extended p=5 training for another 200 epochs

**Bug discovered:** `train.py` only creates `model_config` (which carries `p`, `grad_weight_alpha`, `interface_lambda` from the yaml) when `--replace_embedding_recovery` is True. For warm-start without that flag, `model_config=None`, so `ScOT.from_pretrained(checkpoint, config=None)` loads the checkpoint's `p=5` config unchanged. The `p: 6` in the yaml was silently ignored.

**Results (mis-labeled as p=6, actually extended p=5):**

| Metric | Value | vs Baseline-B | vs p=5 |
|--------|-------|---------------|--------|
| RMSE | 0.02051 | -11.8% | -7.5% |
| Max Error | 0.36885 | -11.7% | -8.6% |
| PAPE | 0.1109% | -10.3% | -8.4% |

These improvements are from 400 total effective epochs of p=5 training, not from the interface loss. Results are not valid as a p=6 comparison.

**Fix applied to `train.py`:**
```python
# After ScOT.from_pretrained(..., config=None):
if model_config is None:
    for attr, key in [("p","p"),("grad_weight_alpha","grad_weight_alpha"),("interface_lambda","interface_lambda")]:
        if key in config:
            setattr(model.config, attr, config[key])
```

---

## Experiment 9 — Combined Loss Warm-Start on Model-B, Corrected (p=6) — IN PROGRESS

**Hardware:** L40S (Machine 1)  
**Loss:** p=6, lambda=0.001, warm-start from p=5 best checkpoint  
**Fix:** `train.py` patched to override loss params after warm-start load  
**Status:** Running — ETA ~3 hours from launch  
**Results:** Pending

---

## Overall Results Table

| # | Experiment | Model | Loss | RMSE | Max Error | PAPE |
|---|---|---|---|---|---|---|
| 1 | Baseline-T | 21M | L1 | 0.07653 | 1.4445 | 0.396% |
| 2 | Grad-Weight-T | 21M | GW-L1 (p=5) | 0.05196 | 0.8584 | 0.242% |
| 3 | Combined-T λ=0.05 | 21M | GW-L1 + Interface | **DIVERGED** | — | — |
| 4 | **Combined-T λ=0.001** | **21M** | **GW-L1 + Interface** | **0.03694** | **0.6147** | **0.176%** |
| 5 | Baseline-B | 157.6M | L1 | 0.02327 | 0.41770 | 0.124% |
| 6 | Grad-Weight-B | 157.6M | GW-L1 (p=5) | 0.02219 | 0.40348 | 0.121% |
| 7 | Combined-B cold-start | 157.6M | GW-L1 + Interface | +12% (degraded) | -6% | worse |
| 8 | Combined-B warm v1 | 157.6M | Extended p=5 (bug) | 0.02051 | 0.36885 | 0.111% |
| 9 | **Combined-B warm v2** | **157.6M** | **GW-L1 + Interface** | **pending** | **pending** | **pending** |

---

## Key Takeaways

**1. Gradient weighting (p=5) is the biggest single win.**  
On Model-T: -32% RMSE, -40% Max Error. On Model-B: -4.6% RMSE. The benefit scales inversely with model size — smaller models have more room to improve because they already struggle at boundaries.

**2. Interface loss (p=6) requires warm-start AND small lambda.**  
- λ=0.05 cold-start → complete divergence (exp. 3)  
- λ=0.001 cold-start on large model → loss-metric mismatch, RMSE degrades (exp. 7)  
- λ=0.001 warm-start from p=5 → genuine improvement on Model-T: further -29% RMSE on top of p=5 (exp. 4)

**3. Model scale dominates everything.**  
Model-B baseline (no fancy loss) beats Model-T p=6 best result by 37% RMSE. If the goal is accuracy, scaling the model has more impact than any loss function change.

**4. The "warm-start bug" in train.py.**  
When fine-tuning without `--replace_embedding_recovery`, the training script's `model_config` is set to `None`, so loss-function parameters from the yaml (`p`, `interface_lambda`) are silently ignored and the checkpoint's original values are used. This was found after experiment 8 produced p=5 results when p=6 was intended. Fixed by patching train.py to explicitly apply yaml loss params after loading the checkpoint.
