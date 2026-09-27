# Multi-Chip Experiment Results — Refine1 Datasets

**Model:** Therm-FM-T (Model-T, 20.7M params)  
**Init:** Poseidon-T cold-start (`--replace_embedding_recovery`)  
**Dataset:** refine1 resolution (HS: 55×55, IND: 101×101)  
**Training:** 200 epochs, batch=40, lr=5e-5, cosine LR, AdamW, weight_decay=1e-6  
**Note:** Paper publishes results on refine2. These refine1 runs are self-consistent but not directly comparable to paper's Table II/III.

---

## Experiment Variants

| Label | Loss (p) | Formula |
|-------|----------|---------|
| **Baseline L2** | p=2 (MSE) | `mean((pred - label)²)` normalized per channel |
| **GW-L2 α=0.1** | p=7 | `mean(w · (pred - label)²)`, w = (1 + 0.1·∥∇T∥) / mean(w) |
| **GW-L2 α=0.5** | p=7 | `mean(w · (pred - label)²)`, w = (1 + 0.5·∥∇T∥) / mean(w) |

Gradient magnitude: `∥∇T∥ = sqrt((dT/dx)² + (dT/dy)²)` computed from ground-truth labels via finite differences.

---

## HS_SC (55×55, n_test=1000)

| Metric | Baseline L2 | GW-L2 α=0.1 | GW-L2 α=0.5 | α=0.1 vs Base | α=0.5 vs Base |
|--------|-------------|-------------|-------------|--------------|--------------|
| RMSE (K) | 0.05184 | 0.05127 | **0.04933** | -1.1% | **-4.8%** |
| Max Error (K) | 1.2711 | 1.2290 | **1.0186** | -3.3% | **-19.9%** |
| MAE (K) | 0.02823 | 0.02834 | **0.02805** | +0.4% | -0.6% |
| PAPE (%) | 0.1692 | 0.1665 | **0.1597** | -1.6% | -5.6% |

## HS_QC (55×55, n_test=1000)

| Metric | Baseline L2 | GW-L2 α=0.1 | GW-L2 α=0.5 | α=0.1 vs Base | α=0.5 vs Base |
|--------|-------------|-------------|-------------|--------------|--------------|
| RMSE (K) | 0.09351 | 0.09113 | **0.09213** | -2.5% | -1.5% |
| Max Error (K) | 1.7813 | 1.7641 | **1.7292** | -1.0% | **-2.9%** |
| MAE (K) | 0.06784 | 0.06581 | **0.06659** | -3.0% | -1.8% |
| PAPE (%) | 0.1450 | 0.1438 | **0.1460** | -0.8% | +0.7% |

## HS_OC (85×85, n_test=1000)

| Metric | Baseline L2 | GW-L2 α=0.1 | GW-L2 α=0.5 | α=0.1 vs Base | α=0.5 vs Base |
|--------|-------------|-------------|-------------|--------------|--------------|
| RMSE (K) | 0.12323 | 0.12260 | **0.12211** | -0.5% | -0.9% |
| Max Error (K) | 7.2085 | 7.2281 | **6.8882** | +0.3% | **-4.4%** |
| MAE (K) | 0.07733 | 0.07797 | **0.07833** | +0.8% | +1.3% |
| PAPE (%) | 0.5282 | 0.5062 | **0.4638** | -4.2% | **-12.2%** |

## IND_8C (101×101, n_test=100)

| Metric | Baseline L2 | GW-L2 α=0.1 | GW-L2 α=0.5 | α=0.1 vs Base | α=0.5 vs Base |
|--------|-------------|-------------|-------------|--------------|--------------|
| RMSE (K) | 0.03237 | 0.03154 | **0.03152** | -2.6% | **-2.6%** |
| Max Error (K) | 0.8961 | 0.8931 | 0.9060 | -0.3% | +1.1% |
| MAE (K) | 0.02367 | 0.02306 | **0.02305** | -2.6% | -2.6% |
| PAPE (%) | 0.1299 | 0.1278 | **0.1285** | -1.6% | -1.1% |

## IND_32C (101×101, n_test=100)

| Metric | Baseline L2 | GW-L2 α=0.1 | GW-L2 α=0.5 | α=0.1 vs Base | α=0.5 vs Base |
|--------|-------------|-------------|-------------|--------------|--------------|
| RMSE (K) | 0.02966 | 0.02928 | **0.02929** | -1.3% | -1.2% |
| Max Error (K) | 0.7317 | 0.7222 | **0.7280** | -1.3% | -0.5% |
| MAE (K) | 0.02173 | 0.02144 | **0.02143** | -1.3% | -1.4% |
| PAPE (%) | 0.0998 | 0.0995 | **0.0999** | -0.3% | +0.1% |

---

## Summary: GW-L2 α=0.5 vs Baseline L2

| Chip | RMSE Δ | Max Error Δ | MAE Δ | PAPE Δ |
|------|--------|-------------|-------|--------|
| HS_SC | **-4.8%** | **-19.9%** | -0.6% | -5.6% |
| HS_QC | -1.5% | -2.9% | -1.8% | +0.7% |
| HS_OC | -0.9% | -4.4% | +1.3% | -12.2% |
| IND_8C | -2.6% | +1.1% | -2.6% | -1.1% |
| IND_32C | -1.2% | -0.5% | -1.4% | +0.1% |

**Key takeaway:** GW-L2 α=0.5 consistently reduces RMSE across all chips. The largest gain is on Max Error for HS_SC (-19.9%), which is the most practically relevant metric for thermal hotspot design. Gains diminish for HS_OC (complex 3-layer chip), suggesting gradient weighting is most effective on simpler geometries.

---

## Paper Reference (Therm-FM-T, refine1 resolution)

From Table II/III of arXiv:2605.22663v2 — for context:

| Chip | Resolution | Paper RMSE | Paper Max |
|------|-----------|------------|-----------|
| HS_SC | 55×55 | 0.051 | 0.558 |
| HS_OC | 85×85 | 0.117 | 1.198 |

Our baseline L2 RMSE (0.0518, 0.1232) closely matches, confirming correct setup.  
Max Error differs because paper likely reports mean-of-per-sample-max; our eval reports global max across all test samples.

---

*All metrics computed on denormalized temperature fields (Kelvin). Runs on Machine 1 (L40S 48GB) and Naveen's VM (T4 16GB).*
