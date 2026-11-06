#!/usr/bin/env bash
set -euo pipefail

: "${W4_ROOT:?Set W4_ROOT to the W4 branch checkout}"
: "${W0_ROOT:?Set W0_ROOT to the fixed W0 worktree}"
: "${CORE_ROOT:?Set CORE_ROOT to the frozen Core worktree}"
: "${P27_ROOT:?Set P27_ROOT to the formal M6 evidence directory}"
: "${P27_LOCK_SHA256:?Set P27_LOCK_SHA256 only after independently registering the pre-run lock digest}"

readonly IMAGE="w4-p27-formal-m6:20261106"
readonly P1_REL="research/SpinIt2014_Teapot_20261018/P1"
readonly W0_COMMIT="5bab2eb2616df306906a6887a273f68acfa49320"
readonly CORE_COMMIT="58fd12c1306c1c01679a19172e276eef0cb30542"

W4_ROOT="$(realpath "$W4_ROOT")"
W0_ROOT="$(realpath "$W0_ROOT")"
CORE_ROOT="$(realpath "$CORE_ROOT")"
P27_ROOT="$(realpath "$P27_ROOT")"
P1="$W4_ROOT/$P1_REL"
RUN_REL="$(cat "$P27_ROOT/LATEST_RUN_DIR")"
RUN_DIR="$P27_ROOT/$RUN_REL"
LOCK="$RUN_DIR/P21_PRERUN_LOCK.json"
test -s "$LOCK"
observed_lock_sha="$(sha256sum "$LOCK" | awk '{print $1}')"
if [[ "$observed_lock_sha" != "$P27_LOCK_SHA256" ]]; then
  echo "External lock SHA mismatch; refusing formal execution." >&2
  exit 3
fi
test "$(git -C "$W0_ROOT" rev-parse HEAD)" = "$W0_COMMIT"
test "$(git -C "$CORE_ROOT" rev-parse HEAD)" = "$CORE_COMMIT"

python3 - <<'PY'
from pathlib import Path
values={}
for line in Path("/proc/meminfo").read_text().splitlines():
    f=line.split()
    if len(f)>=3 and f[1].isdigit() and f[2]=="kB":
        values[f[0].rstrip(":")]=int(f[1])*1024
assert values["MemTotal"]>=20*1024**3,values
assert values["SwapTotal"]==0,values
print("HOST_RESOURCE_PRECHECK",{
 "MemTotal_bytes":values["MemTotal"],
 "MemAvailable_bytes":values.get("MemAvailable"),
 "SwapTotal_bytes":values["SwapTotal"]
})
PY

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  echo "Docker daemon unavailable." >&2; exit 4
fi

EXEC_REL="$RUN_REL/formal-m6-run-$(date -u +%Y%m%dT%H%M%SZ)"
"${DOCKER[@]}" run --rm --init \
  --memory=24g --memory-swap=24g --cpus=8 --cgroupns=private \
  --mount "type=bind,src=$W4_ROOT,dst=/work/w4,readonly" \
  --mount "type=bind,src=$W0_ROOT,dst=/work/w0,readonly" \
  --mount "type=bind,src=$CORE_ROOT,dst=/work/core" \
  --mount "type=bind,src=$P27_ROOT,dst=/output" \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp --env GIT_CONFIG_GLOBAL=/tmp/gitconfig \
  --env P1="$P1_REL" --env RUN_REL="$RUN_REL" --env EXEC_REL="$EXEC_REL" \
  --env P27_LOCK_SHA256="$P27_LOCK_SHA256" \
  --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 --env MKL_NUM_THREADS=1 \
  "$IMAGE" bash -lc '
    set -euo pipefail
    P1="/work/w4/$P1"
    OUT="/output/$RUN_REL"
    export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
    git config --global --add safe.directory /work/w4
    git config --global --add safe.directory /work/w0
    git config --global --add safe.directory /work/core
    git config --global --add safe.directory /work/core/libigl
    test "$(cat /sys/fs/cgroup/memory.max)" = "25769803776"
    test "$(cat /sys/fs/cgroup/memory.swap.max)" = "0"
    test "$(sha256sum "$OUT/P21_PRERUN_LOCK.json" | awk "{print \$1}")" = "$P27_LOCK_SHA256"
    /opt/w4-venv/bin/python "$P1/p21_m6_replay.py" execute \
      --lock "$OUT/P21_PRERUN_LOCK.json" \
      --lock-sha256 "$P27_LOCK_SHA256" \
      --output-directory "/output/$EXEC_REL"
  '

echo "Formal M6 execution returned. Preserve and inspect:"
echo "$P27_ROOT/$EXEC_REL"
echo "Do not infer W0 owner, W2 teacher, derivative-neighborhood, Newton, training, or physical admission from a geometry-only pass."
