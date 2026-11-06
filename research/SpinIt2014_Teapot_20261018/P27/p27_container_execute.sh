#!/usr/bin/env bash
set -euo pipefail
: "${RUN_REL:?RUN_REL required}"
: "${OUT:?OUT required}"
: "${EXEC_REL:?EXEC_REL required}"
: "${P27_LOCK_SHA256:?P27_LOCK_SHA256 required}"

readonly P1_REL="research/SpinIt2014_Teapot_20261018/P1"
P1="/work/w4/$P1_REL"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

git config --global --add safe.directory /work/w4
git config --global --add safe.directory /work/w0
git config --global --add safe.directory /work/core
git config --global --add safe.directory /work/core/libigl

test "$(cat /sys/fs/cgroup/memory.max)" = "25769803776"
test "$(cat /sys/fs/cgroup/memory.swap.max)" = "0"
/opt/w4-venv/bin/python - <<'PY'
import hashlib,os
from pathlib import Path
p=Path(os.environ["OUT"])/"P21_PRERUN_LOCK.json"
actual=hashlib.sha256(p.read_bytes()).hexdigest()
assert actual==os.environ["P27_LOCK_SHA256"],(actual,os.environ["P27_LOCK_SHA256"])
print("P27_EXTERNAL_PRERUN_LOCK_SHA_VERIFIED",actual)
PY

# This is the first command in the P27 path that invokes formal M6.
# The P21 wrapper preserves the same-call capture and the unchanged P20/W0 audit.
/opt/w4-venv/bin/python "$P1/p21_m6_replay.py" execute \
  --lock "$OUT/P21_PRERUN_LOCK.json" \
  --lock-sha256 "$P27_LOCK_SHA256" \
  --output-directory "/output/$EXEC_REL"
