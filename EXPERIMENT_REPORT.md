# Therm-FM Loss Function Experiments — Full Report

## Background

**Therm-FM** is a neural operator (SwinV2 encoder + ConvNeXt decoder) for steady-state and transient 3D-IC chip thermal simulation. It is pretrained on fluid dynamics PDEs (Poseidon) and fine-tuned on chip temperature data using a two-stage multi-fidelity approach.

The paper (arXiv 2605.22663) uses a standard L1 loss uniformly across all spatial pixels. The hypothesis tested here is that boundary-aware weighting — focusing the optimizer on high-temperature-gradient pixels near material interfaces — can improve accuracy at the locations that matter most.

---

## Hypothesis

3D-IC chips have dramatic material property jumps: copper vias (k ≈ 385 W/m·K) surrounded by SiO₂ (k ≈ 1.4 W/m·K), a ~275× ratio. These interfaces create sharp temperature gradients that are hardest to predict accurately. Standard L1 loss treats all pixels equally, so the dominant contribution comes from flat-temperature regions (most of the chip area), leaving the sharp-boundary regions under-optimized.

**Proposed fix:** Weight each pixel's loss by the magnitude of the ground-truth temperature gradient at that pixel. High-gradient pixels near material interfaces get more loss signal; flat regions get less.

---

## Experiments

### Experiment 1 — Baseline (p=1, L1 loss)

**Loss:**
```
L = mean(|ŷ - y|)
```
Standard pixel-wise L1. No spatial weighting.

**Config:** `configs/run_exp_gradweight_T.yaml` with `p: 1`

---

### Experiment 2 — Gradient-Weighted L1 (p=5)

**Loss:**
```
∇T_x[i,j] = T[i,j+1] - T[i,j]          (x-direction finite difference on labels)
∇T_y[i,j] = T[i+1,j] - T[i,j]          (y-direction finite difference on labels)
grad_mag[i,j] = sqrt(∇T_x² + ∇T_y² + ε)

weights[i,j] = (1 + α · grad_mag[i,j]) / mean(1 + α · grad_mag)

L = mean(weights · |ŷ - y|)
```

Key design choices:
- Gradients computed on **labels** (ground truth), not predictions — constant during backprop, zero overhead
- `weights / weights.mean()` normalization — keeps loss magnitude comparable to p=1, no LR retuning needed
- `ε = 1e-8` in sqrt — prevents NaN at zero-gradient pixels
- Finite differences (not Sobel) — simpler, sufficient for uniform grids
- L1 base (not L2) — bounded constant per-pixel gradient, avoids exponential divergence at high-weight pixels

**Config:** `configs/run_exp_gradweight_T.yaml` with `p: 5`, `grad_weight_alpha: 1.0`

---

### Experiment 3 — Combined (p=6): Gradient-Weight + Interface Penalty

**Loss:**
```
base_loss = mean(weights · |ŷ - y|)          (same as p=5)

interface_mask[i,j] = 1 if grad_mag[i,j] > mean(grad_mag) + 2·std(grad_mag)
                      0 otherwise             (top ~2% highest-gradient pixels)

interface_loss = mean(interface_mask · |ŷ - y|)

L = base_loss + λ · interface_loss
```

Two complementary effects:
- **base_loss** applies soft continuous gradient weighting across all pixels
- **interface_loss** applies a hard binary penalty specifically at the ~2% of pixels with the sharpest thermal gradients (material interfaces)

Together: every pixel weighted proportionally to gradient, **plus** an explicit extra penalty at the true interface locations.

**Config:** `configs/run_exp_combined_T.yaml` with `p: 6`, `grad_weight_alpha: 1.0`, `interface_lambda: 0.05`

---

## Code Changes

### `scOT/model.py`

Two additions to `ScOTConfig.__init__`:
```python
grad_weight_alpha: float = 1.0,   # gradient weighting strength
interface_lambda: float = 0.05,   # interface penalty weight
```

Two new loss branches in `ScOT.forward()` (after the p=4 PINN branch):

**p=5 (gradient-weighted L1):**
```python
elif self.config.p == 5:
    dT_dx = labels[:, :, :, 1:] - labels[:, :, :, :-1]
    dT_dx = F.pad(dT_dx, (0, 1, 0, 0), mode='replicate')
    dT_dy = labels[:, :, 1:, :] - labels[:, :, :-1, :]
    dT_dy = F.pad(dT_dy, (0, 0, 0, 1), mode='replicate')
    grad_mag = torch.sqrt(dT_dx ** 2 + dT_dy ** 2 + 1e-8)
    weights = 1.0 + self.config.grad_weight_alpha * grad_mag
    weights = weights / weights.mean()
    loss = (weights * (prediction - labels).abs()).mean()
```

**p=6 (combined):**
```python
elif self.config.p == 6:
    dT_dx = labels[:, :, :, 1:] - labels[:, :, :, :-1]
    dT_dx = F.pad(dT_dx, (0, 1, 0, 0), mode='replicate')
    dT_dy = labels[:, :, 1:, :] - labels[:, :, :-1, :]
    dT_dy = F.pad(dT_dy, (0, 0, 0, 1), mode='replicate')
    grad_mag = torch.sqrt(dT_dx ** 2 + dT_dy ** 2 + 1e-8)
    weights = 1.0 + self.config.grad_weight_alpha * grad_mag
    weights = weights / weights.mean()
    base_loss = (weights * (prediction - labels).abs()).mean()
    interface_mask = (grad_mag > grad_mag.mean() + 2 * grad_mag.std()).float()
    interface_loss = (interface_mask * (prediction - labels).abs()).mean()
    loss = base_loss + self.config.interface_lambda * interface_loss
```

### `scOT/train.py`

**1. Config params wired from YAML:**
```python
# Before (hardcoded p=2):
p=2,

# After:
p=config.get("p", 1),
grad_weight_alpha=config.get("grad_weight_alpha", 1.0),
interface_lambda=config.get("interface_lambda", 0.05),
```

**2. NaN fixup after `from_pretrained` with `ignore_mismatched_sizes=True`:**

When loading a pretrained checkpoint with mismatched embedding/recovery layer shapes, HuggingFace leaves those weights uninitialized (NaN). Without the fix, NaN propagates through the first forward pass and corrupts the optimizer state permanently.

```python
import torch.nn as nn_init
for name, param in model.named_parameters():
    if torch.isnan(param).any() or torch.isinf(param).any():
        if 'weight' in name and param.dim() >= 2:
            nn_init.init.xavier_normal_(param.data)
        else:
            nn_init.init.zeros_(param.data)
```

---

## Results

### Dataset: HS-SC-refine1

- **Chip:** HotSpot South-China (academic benchmark)
- **Resolution:** 55 × 55 pixels per layer, 2 layers
- **Samples:** 5000 total (4000 train / 1000 test, 80/20 split)
- **Inputs:** 4-channel (power density + xyz coordinates)
- **Outputs:** Steady-state temperature per layer (Kelvin, normalized)

### Hardware
- GPU: NVIDIA T4 16GB (AWS g4dn.xlarge)
- Training time: ~50 min per 200-epoch run

### Baseline (p=1)

```json
{
  "rmse": 0.07652606971201198,
  "r2": 0.9997831408679485,
  "max_absolute_error": 1.4444886779785155,
  "mean_absolute_error": 0.021048819756135345,
  "mape_percent": 0.006111344716109351,
  "pape_percent": 0.3963272252585739
}
```

### Gradient-Weighted L1 (p=5)

```json
{
  "rmse": 0.05196354874663783,
  "r2": 0.9999200248718262,
  "max_absolute_error": 0.8583876495361328,
  "mean_absolute_error": 0.017789671272970736,
  "mape_percent": 0.0052077986703577,
  "pape_percent": 0.2420056202710839
}
```

**Improvements over baseline:**

| Metric | Baseline | Grad-Weight | Δ |
|---|---|---|---|
| RMSE | 0.0765°C | **0.0520°C** | **-32%** |
| Max Error | 1.444°C | **0.858°C** | **-41%** |
| MAE | 0.02105°C | 0.01779°C | -15% |
| PAPE | 0.396% | **0.242%** | **-39%** |
| R² | 0.99978 | 0.99992 | +0.00014 |

### Combined (p=6) — pending

Results will be added when the 200-epoch run completes.

---

## Bugs Encountered

### 1. Wrong `F.pad` tuple for 4D tensors
`F.pad(tensor, (0, 1), mode='replicate')` dispatches to the 1D spatial padding routine which expects a 3D input. For 4D `(B, C, H, W)` tensors, a 4-tuple is required: `(0, 1, 0, 0)` for right-only W padding. Fixed in both p=5 and p=6.

### 2. Gradient-weighted L2 diverges
Initial implementation used `(prediction - labels) ** 2`. With normalized labels reaching ~12 units and weights up to 5×, the L2 loss compounds quadratically over epochs, causing attention softmax overflow → NaN after ~160 training steps. Fixed by switching to L1 (`.abs()`), which has bounded ±1 per-pixel gradients.

### 3. NaN from stale checkpoints
When restarting training after a failed run, the HuggingFace Trainer resumes from the most recent checkpoint in the output directory. If that checkpoint has a corrupted optimizer state (NaN AdamW moments from the broken run), training immediately produces NaN loss. Fixed by deleting the full experiment output directory before relaunching.

### 4. NaN from `ignore_mismatched_sizes`
`ScOT.from_pretrained(..., ignore_mismatched_sizes=True)` leaves `patch_recovery.projection.weight` as NaN when shapes don't match. The NaN propagates to the output on the first forward pass. Fixed by the post-load NaN fixup loop (see code changes above).

---

## Notes on What Didn't Work

**Curvature-based interface loss (second derivatives of prediction):**
```python
flux_x = pred_dx[:, :, :, :-1] - pred_dx[:, :, :, 1:]  # Laplacian of prediction
```
In early training, the randomly-initialized recovery layer produces predictions with large-magnitude high-frequency spatial noise. Second differences of these values overflow fp32 → inf → `inf × 0 = NaN` when multiplied by a boundary mask with some zero entries.

**Gradient-matching interface loss (first differences of prediction):**
```python
interface_loss = (interface_mask * ((pred_dx - dT_dx).abs() + ...)).mean()
```
With prediction magnitudes ~100–1000× larger than labels in early training, this term dominates the total loss (≈10^18), producing ∞ gradient norms and catastrophic weight updates even with grad clipping.

**Root cause:** Any interface loss term that uses `prediction` derivatives — rather than pure `(prediction - labels)` — is numerically unstable during the critical early training phase when the randomly-reinitialized recovery head is far from convergence. The binary MAE penalty (`interface_mask * |ŷ - y|`) avoids this entirely since `|ŷ - y|` is the same quantity as the base loss and is already handled stably by gradient clipping.
