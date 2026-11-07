# W6 P13b operator grid vs source density grid CPU probes

**Do not conflate input voxel resolution with PINO Fourier resolution.**

The earlier P13b four-arm 32³/64³ source-density experiment and 128³
gradient smoke used PINO encoder.grid_size=8 and exposed severe
material/moment aliasing under soft surrogate optimization.

This additional independent cloud run checks actual factorized-Fourier
P-CRAFT U-FNO operator grids 8³,16³,32³,64³ with source 64³, plus
a 128³ source with 32³ Fourier grid. These are **one forward/backward**
each, not trained full high-resolution neural models.

- Every test runs in an independent Python process for CPU RSS.
- Width/modes/layers remain small (4/2/2) and original PINO main
  architecture is unchanged.
- A constructed fine material pair has same coarse 8³ voxel averages,
  but different independently discretized physical ten cut moments.
  At PINO grid=8 the encoder alone cannot distinguish the two, while
  at PINO grid>=16 it can preserve the difference in the preparation
  tensor. This does NOT prove the downstream trained predictor is
  accurate; it only establishes a representational resolution port.
- Reverse-mode density gradients come from actual PINO ten moment head.
- 64³ full PINO Fourier operator is an exploratory CPU feasibility test;
  if it fails due to memory/toolchain, report failure and prioritize
  32³ operator + sparse high-res feature interfaces.
- This probe uses synthetic voxel cubes, not CAD/voxel strengths or
  formal W2 Cherchi labels.
- Full 128³/256³/512³ **trained** PINO and official fVDB CUDA remain
  unverified pending separate local GPU stress and a high-frequency
  detail-preserving architecture.
