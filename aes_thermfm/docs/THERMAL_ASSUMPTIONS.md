# Thermal and data-contract assumptions

## What this run can establish

This is a new-design pipeline experiment, not a thermal sign-off. The routed AES power is real library-based estimation under assumed activity. The temperature output is a trained Therm-FM network's extrapolation, without target-design training or a matched thermal reference.

## Electrical design

- Stock ORFS AES encryption core, Nangate45 typical library and stock constraints (0.82 ns clock).
- Routing/extraction from the pinned ORFS container.
- Three vectorless global/input switching activities: 0.02, 0.10, 0.20 transitions per clock cycle; duty 0.5. This is not an AES workload simulation and is not derived from a VCD/SAIF trace.
- Distribute each cell's estimated total internal+switching+leakage power uniformly over its placed footprint. Interconnect switching dissipation is assigned to its associated cell by this approximation, not separately localized along wires.

## Thermal adapter

- Model: user's IND-8C-trained Therm-FM-T GW-L2 alpha=0.5 checkpoint, 101×101, 8 input channels, 2 output layers.
- Preserve actual AES die dimensions. x/y are centered and expressed in mm, assuming the industrial dataset's -0.5..0.5 coordinates denote the paper's 1 mm square. This unit inference is recorded, not silently treated as proof from the loader.
- Two layer slots are required by the checkpoint. AES occupies slot 0; slot 1 has zero heat generation. This is an explicitly hypothetical AES-plus-passive-layer stack, not a physical 3D AES implementation.
- Use 0.2 mm heat-source thickness as an exploratory assumption from the industrial active-layer thickness in the paper. It is not inferred from OpenROAD; a thin transistor heat-source layer would yield very different volumetric density.
- Power channel is supplied in W/m³ under the paper's stated volumetric-source interpretation. Exact industrial data-generation scaling is not available in the inspected loader; the real dataset has values near 1e11, while HotSpot has values near 1..25. These conventions must not be interchanged without provenance.
- The z inputs are the checkpoint's layer identifiers 1 and 2, not physical distances. No temperature or fabricated labels are supplied at inference.
- Package materials and cooling are learned implicitly by the selected checkpoint. This adapter cannot make them match a new die by changing coordinates. Ambient/cooling assumptions cannot be enforced through this checkpoint's eight-channel input.

## Spatial rasterization

Represent 101×101 endpoint coordinates with node-centered control volumes: interior boundaries lie midway between nodes, outer boundaries coincide with the die edges. Boundary cells have half-width volumes. Allocate each placed cell's power by exact rectangular overlap with these volumes. Divide each volume's allocated watts by its area and assumed thickness. Verify the integral of the density recovers the original cell-power total.

## Diagnostics

Run the three electrical activity cases and a synthetic all-zero heat-source case for each of two coordinate domains:

1. `native_die`: actual AES die width/height, centered at zero.
2. `benchmark_1mm_embedding`: place the same unscaled cell footprints and watts at the center of a hypothetical 1 mm square thermal die. Empty surrounding silicon has zero heat generation. This matches the observed industrial coordinate range; it is not the native routed die. No power scaling or footprint stretching is performed.

The all-zero case tests the pretrained model's offset and extrapolation behavior; it is not an electrical zero-activity power estimate (which would still have leakage).

No AES RMSE/MAE will be claimed without reference temperatures for a matching physical stack. A held-out IND-8C sample tests only the inference implementation.
