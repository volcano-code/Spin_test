# P29 local deployment correction: RTX 5090 D, reuse first

This note supersedes the old 4090/CUDA 11.8 assumptions in the P29 expansion plan. It changes deployment preparation, not the P-CRAFT PINO research backbone.

## User-provided preflight evidence

- GPU: NVIDIA GeForce RTX 5090 D; nvidia-smi total 32607 MiB, free 28175 MiB.
- Driver: 580.178.04; installed nvcc: CUDA 12.8, V12.8.93.
- Base interpreter: Python 3.13.5, PyTorch 2.8.0+cu128; CUDA available.
- Separate existing environment: /home/lin/anaconda3/envs/trellis. Its package versions and CUDA extension compatibility are not established by the base-interpreter output.
- Available space: root 123G, /home 3.8G, /data 58G; RAM available 22 GiB, swap 0.
- Historical source candidate: /home/lin/xvxinyao/DensiCrafter/TRELLIS. Existence must be checked; do not assume or overwrite it.

## Deployment decision

1. Preserve the current NVIDIA driver and CUDA toolkit. Do not downgrade to the default CUDA 11.8/12.4 stacks in upstream convenience installers merely to match old documentation.
2. Do not install into base or alter the existing trellis, w1-native or w2-native environments in place.
3. Use /opt/w6-p29-lin on the root filesystem for this small pilot's reports and caches. Check the actual filesystem and reserve at least 40 GiB of root free space. This reserve is a project policy, not an official TRELLIS requirement.
4. Audit the existing trellis interpreter and source first. Reuse verified assets instead of downloading duplicates. Do not delete old research environments or checkpoints to make room.
5. If a replacement environment is necessary, evaluate a new Python 3.10 + PyTorch 2.8.0/cu128 + torchvision 0.23.0 environment under the root-volume workspace. This is a candidate baseline, not proof that all TRELLIS native extensions will work.
6. Retain TRELLIS v1 as the first smoke target because an existing installation may be reusable, not because the GPU is a 24GB 4090. TRELLIS.2 remains a separately tested candidate.
7. No batch generation until one image-to-mesh run and extension-kernel smoke pass; then three pilot assets, geometry audit and teacher-input packaging. Generation resolution does not certify 512-cubed PINO training.

## Delivered diagnostic

`p29_local_reuse_audit.py`, code commit `b2b40768e31651e05a309026163bef98ad4768ca`.

- Standard-library controller, offline Hugging Face settings, redirected child caches.
- Reports existing package versions, isolated imports, small FP32/FP16 CUDA matrix multiplication, source revision and a bounded checkpoint metadata scan.
- No installs, automatic repairs, model loading or generation.
- Extension imports are not extension CUDA-kernel validation.
- Nine CPU self-tests passed in the assistant execution container. The local tested Git blob is `d00d0bd2b4e3dd828558f067697a2fa743859f5f`, matching the pushed file.
- No claim of a local 5090 test or successful TRELLIS generation is made by this commit.

## Upstream compatibility references checked

- PyTorch Blackwell/cu128 support: https://pytorch.org/blog/pytorch-2-7/
- PyTorch version pairings: https://pytorch.org/get-started/previous-versions/
- TRELLIS v1 default installer: https://github.com/microsoft/TRELLIS/blob/main/setup.sh
- TRELLIS.2 default installer: https://github.com/microsoft/TRELLIS.2/blob/main/setup.sh
- Native binary/PTX compatibility: https://docs.nvidia.com/cuda/blackwell-compatibility-guide/index.html
