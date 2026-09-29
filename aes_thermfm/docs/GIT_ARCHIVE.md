# Git archive of the AES pipeline

This directory contains the scripts, input tensors, AES RTL and constraints, final physical-design artifacts, model source/configuration, saved predictions, verification reports, and presentation from the local experiment. The original complete archive remains at `/Users/ayush/Arch_Gen/aes_thermfm`.

## Checkpoint required for inference

The repository ignores model weights (`*.bin`, `*.safetensors`). The 83,235,819-byte `vendor/checkpoint_IND8C_GWL2_T/pytorch_model.bin` is therefore not committed. Rendering scratch files and Python caches are also excluded. Saved results can be reviewed without the weights; running inference and `scripts/verify_artifacts.py` requires restoring them.

From the repository root on the original machine:

```bash
cp /Users/ayush/Arch_Gen/aes_thermfm/vendor/checkpoint_IND8C_GWL2_T/pytorch_model.bin aes_thermfm/vendor/checkpoint_IND8C_GWL2_T/
shasum -a 256 aes_thermfm/vendor/checkpoint_IND8C_GWL2_T/pytorch_model.bin
```

Expected SHA-256: `633794c27ec3379cb534d38b1569aec296a7fb51127eabeb69b4bd40c6e632d9`.

On another machine, obtain this exact checkpoint from the experiment owner. No public checkpoint download is supplied. The original normalization and model configuration are committed alongside its expected location.

`MANIFEST.sha256` covers the files included in this Git snapshot, excluding itself. Historical verification reports describe the original run with its checkpoint present; they are not a claim that inference was rerun while creating this commit.

The combined pipeline wrapper was assembled after the individual stages ran and was not rerun end to end. AES temperatures remain exploratory predictions without a matching thermal-solver reference. See `THERMAL_ASSUMPTIONS.md`, `CONSTRAINTS_VERIFICATION.md`, and `PIPELINE_DOCUMENT_REVIEW.md` for limitations and corrections to the earlier root-level pipeline guide.
