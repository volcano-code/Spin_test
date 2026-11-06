#!/usr/bin/env bash
set -euo pipefail

: "${W4_ROOT:?Set W4_ROOT to the W4 branch checkout}"
: "${W0_ROOT:?Set W0_ROOT to the fixed W0 worktree}"
: "${CORE_ROOT:?Set CORE_ROOT to the frozen Core worktree}"
: "${P27_ROOT:?Set P27_ROOT to a new writable evidence directory}"

readonly W0_COMMIT="5bab2eb2616df306906a6887a273f68acfa49320"
readonly CORE_COMMIT="58fd12c1306c1c01679a19172e276eef0cb30542"
readonly W4_BRANCH="research/neuralmoments-w4-teapot-p1-20261019"
readonly P1_REL="research/SpinIt2014_Teapot_20261018/P1"
readonly P25_REL="research/SpinIt2014_Teapot_20261018/P25"
readonly IMAGE="w4-p27-formal-m6:20261106"

W4_ROOT="$(realpath "$W4_ROOT")"
W0_ROOT="$(realpath "$W0_ROOT")"
CORE_ROOT="$(realpath "$CORE_ROOT")"
P27_ROOT="$(mkdir -p "$P27_ROOT" && realpath "$P27_ROOT")"
P1="$W4_ROOT/$P1_REL"
P25="$W4_ROOT/$P25_REL"

for path in "$W4_ROOT" "$W0_ROOT" "$CORE_ROOT" "$P1" "$P25"; do
  test -d "$path" || { echo "Missing directory: $path" >&2; exit 2; }
done

observed_w0="$(git -C "$W0_ROOT" rev-parse HEAD)"
observed_core="$(git -C "$CORE_ROOT" rev-parse HEAD)"
if [[ "$observed_w0" != "$W0_COMMIT" ]]; then
  echo "W0 checkout mismatch: $observed_w0" >&2; exit 3
fi
if [[ "$observed_core" != "$CORE_COMMIT" ]]; then
  echo "Core checkout mismatch: $observed_core" >&2; exit 3
fi
git -C "$W4_ROOT" status --short
git -C "$W0_ROOT" diff --exit-code HEAD --
git -C "$CORE_ROOT" diff --exit-code HEAD --

# The formal P20/P21 policy is based on physical/effective memory and host swap.
# Do not proceed on a host that fails these preconditions.
python3 - <<'PY'
from pathlib import Path
values={}
for line in Path("/proc/meminfo").read_text().splitlines():
    f=line.split()
    if len(f)>=3 and f[1].isdigit() and f[2]=="kB":
        values[f[0].rstrip(":")]=int(f[1])*1024
required=20*1024**3
assert values["MemTotal"] >= required, ("PHYSICAL_RAM_BELOW_20_GIB",values["MemTotal"])
assert values["SwapTotal"] == 0, ("HOST_SWAP_MUST_BE_ZERO",values["SwapTotal"])
print("HOST_RESOURCE_PRECHECK",{
 "MemTotal_bytes":values["MemTotal"],
 "MemAvailable_bytes":values.get("MemAvailable"),
 "SwapTotal_bytes":values["SwapTotal"],
 "minimum_physical_bytes":required
})
PY

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  echo "Docker daemon unavailable. Install/start docker.io or Docker Engine first." >&2
  exit 4
fi

RUN_TAG="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_REL="formal-m6-$RUN_TAG"
RUN_DIR="$P27_ROOT/$RUN_REL"
mkdir -p "$RUN_DIR"
if [[ -e "$RUN_DIR/P21_PRERUN_LOCK.json" ]]; then
  echo "Refusing to overwrite existing pre-run lock." >&2; exit 5
fi
printf '%s\n' "$RUN_REL" > "$P27_ROOT/LATEST_RUN_DIR"

# Reuse the already cached Ubuntu base image. A forced --pull makes
# an otherwise reproducible local build depend on Docker Hub availability.
if "${DOCKER[@]}" image inspect ubuntu:24.04 >/dev/null 2>&1; then
  echo "Using cached base image ubuntu:24.04"
else
  echo "ubuntu:24.04 is not cached; attempting one explicit pull." >&2
  "${DOCKER[@]}" pull ubuntu:24.04
fi
"${DOCKER[@]}" image inspect ubuntu:24.04 --format '{{.Id}}' | tee "$RUN_DIR/ubuntu-base-image-id.txt"

"${DOCKER[@]}" build \
  --file "$P25/Dockerfile" \
  --tag "$IMAGE" \
  "$P25"

"${DOCKER[@]}" run --rm --init \
  --memory=24g --memory-swap=24g --cpus=8 --cgroupns=private \
  --mount "type=bind,src=$W4_ROOT,dst=/work/w4,readonly" \
  --mount "type=bind,src=$W0_ROOT,dst=/work/w0,readonly" \
  --mount "type=bind,src=$CORE_ROOT,dst=/work/core" \
  --mount "type=bind,src=$P27_ROOT,dst=/output" \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp --env GIT_CONFIG_GLOBAL=/tmp/gitconfig \
  --env RUN_REL="$RUN_REL" --env OUT="/output/$RUN_REL" \
  --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 --env MKL_NUM_THREADS=1 \
  "$IMAGE" /work/w4/research/SpinIt2014_Teapot_20261018/P27/p27_container_prepare.sh

echo
echo "P27 preparation completed. No formal M6 geometry audit has been executed."
echo "Run directory: $RUN_DIR"
echo "Pre-run lock: $RUN_DIR/P21_PRERUN_LOCK.json"
echo "Pre-run lock SHA-256:"
cat "$RUN_DIR/P21_PRERUN_LOCK_SHA256.txt"
echo
echo "Independently review/register this digest before running p27_execute_formal_m6.sh."
