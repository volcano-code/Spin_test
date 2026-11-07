# W6 fVDB high-resolution implementation prerequisite (not installed)

Pinned project source: `openvdb/fvdb-core@b263e7d5bcc2fef155d57c4aa14c5f76f8b9356c`.
Author official documentation (at same pin):
https://github.com/openvdb/fvdb-core/blob/b263e7d5bcc2fef155d57c4aa14c5f76f8b9356c/docs/installation.rst
License: Apache-2.0, preserve original notices and runtime dependencies.

**Environment split required**. W6 CPU CI uses Python 3.10 +
PyTorch 2.5.1. The pinned fVDB installation matrix lists Linux:
- fVDB 0.4: PyTorch 2.10, Python 3.10-3.13, CUDA 12.8 or 13.0.
- fVDB 0.5: PyTorch 2.11, Python 3.10-3.14, CUDA 13.0/13.2.
- fVDB 0.6: PyTorch 2.13, Python 3.10-3.15, CUDA 13.0/13.2.
The table is documentation for matched prebuilt packages; it does not
establish availability/success of an install on the user's host.

Do NOT upgrade the existing W6 torch2.5.1 CI in place or assume the
user's CUDA driver supports these versions. The preliminary CPU-only
M9b sparse_bridge accepts sparse cell coordinates at a 512^3 domain,
but does NOT use fVDB or run full 512^3 PINO spectral layers.

Local host read-only audit before choosing an isolated environment:
```bash
nvidia-smi
nvcc --version || true
python - <<'PY'
import sys
print(sys.version)
try:
 import torch
 print("torch", torch.__version__, "cuda", torch.version.cuda)
 print("cuda_available", torch.cuda.is_available())
except Exception as e: print("torch unavailable", str(e))
PY
```

When selecting a compatible local host, use a separate env and pinned
official fVDB wheel/source, then stress-test 64^3/128^3/256^3/512^3
with variable active-material percentages. Compare material mass,
ten moments, memory allocation, throughput, cold/warm encoding, original
PINO head r/J, and fallback; never report synthetic 4,096 sparse
indices as proof of full 512^3 capacity or original CUDA integration.

**Current status**: source/license/dependency contract only. Not
built, GPU-ran, weight-trained, or bound to real Cherchi geometry.
