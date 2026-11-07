# W6 P13b optional 128³ native P-CRAFT Fourier CPU capacity gate

This is an isolated **single forward/backward** with
`source=128, PINO Fourier operator grid=128` (actual factorized
F-FNO/U-FNO on 2,097,152 sites). It is intentionally not combined
with the 32/64 four-arm optimization job. The experiment runs in a
fresh GitHub Actions CPU process with 20-minute limit.

Requirements:
- Retain the exact P-CRAFT encoder/head and DensiCrafter density
  gradient contract, no replacement by an alternative backbone.
- Record full source voxel count and native Fourier spatial count,
  finite density gradient, protected 2-cell shell, independent
  discretized material cut difference, peak process resident memory
  and CPU seconds.
- If capacity fails, do not retry silently with a lower grid and
  claim 128³ passed; leave CI failed and fall back to verified 64³.
- This is *not* a trained 128³ predictive model, no true Cherchi
  teacher, no native Newton derivative certification, no fVDB CUDA,
  no 256/512³ training or end-to-end Heart/Teapot/Noodles output.
- 128³ dense Fourier may use significant CPU RAM; source resolution
  scales cubically. The production 512³ goal should use sparse
  fVDB/multiscale detail, with on-device peak VRAM and accuracy
  evidence, not dense 512³ CPU FFT extrapolation.

Independent CI run of the prior 64³ native and 128³/32³ grid probe:
https://github.com/volcano-code/Spin_test/actions/runs/42391852853
