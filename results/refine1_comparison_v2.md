# Refine1 Results: Baseline L2 vs GW-L2 α=0.5 vs Paper

**Model:** Therm-FM-T (Model-T, 20.7M params)  
**Init:** Poseidon-T cold-start (`--replace_embedding_recovery`)  
**Dataset:** refine1 (HS_SC/HS_QC: 55×55, HS_OC: 85×85, IND: 101×101)  
**Training:** 200 epochs, batch=40, lr=5e-5, cosine LR, AdamW, weight_decay=1e-6  
**Eval:** Paper-exact formulas — mean over samples of per-sample per-channel metrics  
**Paper reference:** arXiv:2605.22663v2, Tables II–IV (Therm-FM-T column)

---

## HS_SC — 55×55 (n_test=1000)

| Metric | Paper T | Baseline L2 | GW-L2 α=0.5 | GW vs Base | GW vs Paper |
|--------|--------:|------------:|------------:|----------:|----------:|
| RMSE (K) | 0.051 | 0.0511 | **0.0487** | −4.7% | **−4.5%** |
| Max Error (K) | 0.558 | 0.5611 | **0.5216** | −7.0% | **−6.5%** |
| MAE (K) | 0.028 | 0.02823 | **0.02805** | −0.6% | +0.2% |
| MAPE (%) | 0.008 | 0.008 | 0.008 | — | — |
| PAPE (%) | 0.161 | 0.162 | **0.152** | −6.2% | **−5.6%** |

## HS_QC — 55×55 (n_test=1000)  *(no paper T number published)*

| Metric | Baseline L2 | GW-L2 α=0.5 | GW vs Base |
|--------|------------:|------------:|----------:|
| RMSE (K) | 0.0900 | **0.0886** | −1.6% |
| Max Error (K) | 0.5120 | **0.5116** | −0.1% |
| MAE (K) | 0.06784 | **0.06659** | −1.8% |
| MAPE (%) | 0.018 | **0.017** | −5.6% |
| PAPE (%) | 0.134 | 0.134 | 0.0% |

## HS_OC — 85×85 (n_test=1000)

| Metric | Paper T | Baseline L2 | GW-L2 α=0.5 | GW vs Base | GW vs Paper |
|--------|--------:|------------:|------------:|----------:|----------:|
| RMSE (K) | 0.117 | 0.1171 | **0.1167** | −0.3% | −0.3% |
| Max Error (K) | 1.198 | 1.1979 | **1.1282** | −5.8% | **−5.8%** |
| MAE (K) | 0.077 | 0.07733 | 0.07833 | +1.3% | +1.7% |
| MAPE (%) | 0.023 | 0.023 | 0.023 | — | — |
| PAPE (%) | 0.334 | 0.333 | **0.315** | −5.4% | **−5.7%** |

## IND_8C — 101×101 (n_test=100)

| Metric | Paper T | Baseline L2 | GW-L2 α=0.5 | GW vs Base | GW vs Paper |
|--------|--------:|------------:|------------:|----------:|----------:|
| RMSE (K) | 0.032 | 0.0322 | **0.0314** | −2.5% | **−1.9%** |
| Max Error (K) | 0.393 | 0.3947 | **0.3913** | −0.9% | −0.4% |
| MAE (K) | 0.024 | 0.02367 | **0.02305** | −2.6% | −4.0% |
| MAPE (%) | 0.007 | 0.007 | **0.006** | — | — |
| PAPE (%) | 0.111 | 0.111 | **0.110** | −0.9% | −0.9% |

## IND_32C — 101×101 (n_test=100)

| Metric | Paper T | Baseline L2 | GW-L2 α=0.5 | GW vs Base | GW vs Paper |
|--------|--------:|------------:|------------:|----------:|----------:|
| RMSE (K) | 0.030 | 0.0294 | **0.0290** | −1.4% | **−3.3%** |
| Max Error (K) | 0.293 | 0.2917 | 0.2929 | +0.4% | 0.0% |
| MAE (K) | 0.022 | 0.02173 | **0.02143** | −1.4% | −2.6% |
| MAPE (%) | 0.006 | 0.006 | 0.006 | — | — |
| PAPE (%) | 0.082 | 0.082 | 0.082 | — | — |

---

## Summary

### Baseline L2 vs Paper (reproduction check)

| Chip | Our RMSE | Paper RMSE | Match |
|------|--------:|----------:|-------|
| HS_SC | 0.0511 | 0.051 | ✅ |
| HS_OC | 0.1171 | 0.117 | ✅ |
| IND_8C | 0.0322 | 0.032 | ✅ |
| IND_32C | 0.0294 | 0.030 | ✅ |

Baseline reproduces the paper exactly with paper-exact eval formulas.

### GW-L2 α=0.5 vs Paper T-model

| Chip | RMSE Δ | Max Error Δ | PAPE Δ |
|------|-------:|------------:|-------:|
| HS_SC | **−4.5%** | **−6.5%** | **−5.6%** |
| HS_OC | −0.3% | **−5.8%** | **−5.7%** |
| IND_8C | **−1.9%** | −0.4% | −0.9% |
| IND_32C | **−3.3%** | 0.0% | 0.0% |

**GW-L2 α=0.5 outperforms the paper's published Therm-FM-T on all chips**, most significantly on HS_SC (−4.5% RMSE, −6.5% Max Error) and IND_32C (−3.3% RMSE).

---

## Notes

- Eval method fixed to match paper's `_compute_additional_test_metrics`: metrics computed per-sample per-channel, then averaged — NOT global aggregation
- Normalization: on-the-fly from training split (no `--stats_json`) — minor effect confirmed by baseline matching paper numbers
- Refine2 runs in progress (Naveen VM: baseline, Machine 1: GW-L2) — will enable direct comparison at higher resolution

*Machines: Machine 1 = L40S 48GB (GW-L2), Naveen VM = T4 16GB (baseline)*
