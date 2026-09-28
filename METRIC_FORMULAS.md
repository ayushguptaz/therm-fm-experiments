# Evaluation Metric Formulas

Source: `scOT/evaluate.py → _compute_additional_test_metrics()` from the Therm-FM codebase
(arXiv:2605.22663v2, DAC 2026)

All metrics are computed on **denormalized** predictions and labels (real physical units).
Temperature values are in **Kelvin (K)**. Percentage metrics are **unitless (%)**.

---

## Notation

```
N          = number of test samples
C          = number of output channels (temperature layers)
H x W      = spatial resolution of each channel
pred[n,c]  = predicted temperature field for sample n, channel c  (shape: H*W)
label[n,c] = ground-truth temperature field                        (shape: H*W)
diff[n,c]  = pred[n,c] - label[n,c]
eps        = 1e-8  (mask near-zero labels for percentage metrics)
```

---

## RMSE — Root Mean Squared Error (K)

```
Step 1 — per channel:
    rmse[n,c] = sqrt( mean( diff[n,c]^2 ) )

Step 2 — per sample:
    rmse[n] = mean over c of rmse[n,c]

Step 3 — final:
    RMSE = mean over n of rmse[n]
```

**Meaning:** Average (over samples) of the RMS temperature error per layer.  
**Unit:** Kelvin (K)

---

## MAE — Mean Absolute Error (K)

```
Step 1 — per channel:
    mae[n,c] = mean( |diff[n,c]| )

Step 2 — per sample:
    mae[n] = mean over c of mae[n,c]

Step 3 — final:
    MAE = mean over n of mae[n]
```

**Meaning:** Average absolute temperature error across all pixels, samples, and layers.  
**Unit:** Kelvin (K)

---

## Max Error — Mean Peak Absolute Error (K)

```
Step 1 — per channel:
    max[n,c] = max( |diff[n,c]| )    <- worst single pixel in this channel

Step 2 — per sample:
    max[n] = mean over c of max[n,c]

Step 3 — final:
    Max Error = mean over n of max[n]
```

**Meaning:** On average, what is the worst-case temperature error per test sample.  
**Unit:** Kelvin (K)  
**Note:** This is NOT the global worst pixel across all samples. It is the mean of
per-sample worst-case errors — much more representative and typically 2-3x lower
than a global max.

---

## MAPE — Mean Absolute Percentage Error (%)

```
Step 1 — per channel (only pixels where |label[n,c]| > eps):
    ratio[n,c] = |diff[n,c]| / |label[n,c]|
    mape[n,c]  = mean( ratio[n,c] ) * 100

Step 2 — per sample:
    mape[n] = mean over c of mape[n,c]

Step 3 — final:
    MAPE = mean over n of mape[n]
```

**Meaning:** Average relative error as a percentage of the true temperature.  
**Unit:** % (unitless)

---

## PAPE — Peak Absolute Percentage Error (%)

```
Step 1 — per channel (only pixels where |label[n,c]| > eps):
    ratio[n,c] = |diff[n,c]| / |label[n,c]|
    pape[n,c]  = max( ratio[n,c] ) * 100    <- worst relative error pixel

Step 2 — per sample:
    pape[n] = mean over c of pape[n,c]

Step 3 — final:
    PAPE = mean over n of pape[n]
```

**Meaning:** On average, the worst-case relative error (as % of true temperature) per sample.  
**Unit:** % (unitless)

---

## One-Line Summary

```
RMSE       = mean_N [ mean_C [ sqrt( mean_pixels[ diff^2          ] ) ] ]   (K)
MAE        = mean_N [ mean_C [       mean_pixels[ |diff|           ]   ] ]   (K)
Max Error  = mean_N [ mean_C [        max_pixels[ |diff|           ]   ] ]   (K)
MAPE       = mean_N [ mean_C [       mean_pixels[ |diff|/|label|   ]   ] ] * 100  (%)
PAPE       = mean_N [ mean_C [        max_pixels[ |diff|/|label|   ]   ] ] * 100  (%)
```

---

## Verified Against Paper Codebase

Our `eval_multichip_v2.py` implements these formulas identically to the paper's
`scOT/evaluate.py → _compute_additional_test_metrics()`.

Verification: our Baseline L2 results on refine1 match the paper's published
Therm-FM-T numbers to 3-4 significant figures on all 4 chips with published values:

```
Chip       Paper RMSE   Our RMSE    Match
---------  ----------   --------    -----
HS_SC      0.051        0.0511      ✓
HS_OC      0.117        0.1171      ✓
IND_8C     0.032        0.0322      ✓
IND_32C    0.030        0.0294      ✓
```
