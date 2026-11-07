#!/usr/bin/env bash
# W4 P30-B: genuine 12-point Cherchi diagnostic pilot, ONLY after independent
# W0/W2 owner-branch receipts and separate external P30B lock registration.
# Nothing in this script grants derivative smoothness, Newton or training.
set -euo pipefail

: "${P27_BASE:?Set P27_BASE to the existing P27 host directory}"
: "${P30B_W4_ROOT:?Set P30B_W4_ROOT to a separate updated W4 checkout}"
: "${P30B_W0_REVIEW_ROOT:?Set P30B_W0_REVIEW_ROOT to reviewed W0 owner branch}"
: "${P30B_W2_REVIEW_ROOT:?Set P30B_W2_REVIEW_ROOT to reviewed W2 teacher branch}"
: "${P30B_PLAN:?Set P30B_PLAN to the original P30_UNEXECUTED_TANGENT_PLAN.json}"
: "${P30B_ARCHIVE:?Set P30B_ARCHIVE to exact P27_FORMAL_M6_EVIDENCE.tar.gz}"
: "${P30B_LOCK:?Set P30B_LOCK to the externally reviewed P30-B lock JSON}"
: "${P30B_EXTERNAL_LOCK_SHA256:?Independent reviewer must register P30B lock SHA256}"
: "${P30B_EXEC_DIR:?Set P30B_EXEC_DIR to a new experiment directory under P27_ROOT}"

W4="$(realpath "$P30B_W4_ROOT")"
W0_REVIEW="$(realpath "$P30B_W0_REVIEW_ROOT")"
W2_REVIEW="$(realpath "$P30B_W2_REVIEW_ROOT")"
P27_BASE="$(realpath "$P27_BASE")"
W0_SOURCE="$P27_BASE/repo-w0"
CORE="$P27_BASE/repo-core"
RUNS="$P27_BASE/runs"
PLAN="$(realpath "$P30B_PLAN")"
ARCHIVE="$(realpath "$P30B_ARCHIVE")"
LOCK="$(realpath "$P30B_LOCK")"
OUTPUT="$(realpath -m "$P30B_EXEC_DIR")"
P1="research/SpinIt2014_Teapot_20261018/P1"
P30="research/SpinIt2014_Teapot_20261018/P30"
IMAGE="w4-p27-formal-m6:20261106"
P27_RUN_REL="formal-m6-20261106T091202Z"

# These checks are a host fail-closed preflight, not a replacement for the
# independent owner and teacher approvals verified inside the native worker.
test -f "$W4/$P30/p30b_native_sampler.py"
test -f "$W4/$P30/p30b_authority.py"
test -f "$W4/$P1/P20_native_request.json"
test -f "$RUNS/$P27_RUN_REL/P21_PRERUN_LOCK.json"
test -f "$RUNS/$P27_RUN_REL/P20_NATIVE_SIX_PINS.json"
test "$(git -C "$W0_SOURCE" rev-parse HEAD)" = "5bab2eb2616df306906a6887a273f68acfa49320"
test "$(git -C "$CORE" rev-parse HEAD)" = "58fd12c1306c1c01679a19172e276eef0cb30542"

# The imported modules must remain byte-identical to the official P27 build.
test "$(sha256sum "$LOCK" | awk '{print $1}')" = "$P30B_EXTERNAL_LOCK_SHA256"
test "$(sha256sum "$PLAN" | awk '{print $1}')" = "fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc"
test "$(sha256sum "$ARCHIVE" | awk '{print $1}')" = "6827a0951ce8201e4bea5585ba4e2b485b4652c830604b06592e5a0146583e89"

case "$OUTPUT" in
  "$RUNS"/p30b-*) ;;
  *) echo "P30B output MUST be under P27_ROOT/p30b-* (no source or P27 overwrite)." >&2; exit 3 ;;
esac
case "$LOCK" in
  "$RUNS"/*) ;;
  *) echo "P30B lock must be stored inside the P27 runs volume." >&2; exit 3 ;;
esac
LOCK_REL="$(realpath --relative-to="$RUNS" "$LOCK")"
OUT_REL="$(realpath --relative-to="$RUNS" "$OUTPUT")"

python3 - <<'PY'
from pathlib import Path
mem={}
for line in Path("/proc/meminfo").read_text().splitlines():
    a=line.split()
    if len(a)==3 and a[1].isdigit():
        mem[a[0][:-1]]=int(a[1])*1024
assert mem["MemTotal"]>=20*1024**3, "P30B_PHYSICAL_RAM_BELOW_20_GIB"
assert mem["SwapTotal"]==0, "P30B_HOST_SWAP_NOT_ZERO"
print("P30B_HOST", {"MemTotal_GiB":round(mem["MemTotal"]/1024**3,2),
                    "MemAvailable_GiB":round(mem["MemAvailable"]/1024**3,2),
                    "Swap_GiB":round(mem["SwapTotal"]/1024**3,2)})
if mem["MemAvailable"] < 20*1024**3:
    print("P30B_WARNING: LOW_AVAILABLE_RAM; CLOSE MEMORY-HEAVY APPLICATIONS.")
PY

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  echo "P30B: Docker unavailable" >&2; exit 4
fi
"${DOCKER[@]}" image inspect "$IMAGE" >/dev/null

# The official approval files are mandatory; no test fixture or self-authored
# W4 approval substitutes for these W0/W2-owned tracked source receipts.
W0_REL="research/NeuralMoments/contracts/P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json"
W2_REL="research/NeuralMoments/teacher/P30_TEAPOT_FEATURE_PILOT_AUTHORIZATION.json"
git -C "$W0_REVIEW" ls-tree -r --name-only HEAD -- "$W0_REL" | grep -Fx "$W0_REL"
git -C "$W2_REVIEW" ls-tree -r --name-only HEAD -- "$W2_REL" | grep -Fx "$W2_REL"

if [ "${P30B_RESUME:-0}" = "1" ]; then
  RESUME=(--resume)
else
  RESUME=()
  test ! -e "$OUTPUT" || { echo "P30B output already exists. Set P30B_RESUME=1." >&2; exit 5; }
fi

PYTHONPATH="/work/w0:/work/core/python:/work/w4/$P1:/output/$P27_RUN_REL/native-build/core/python:/output/$P27_RUN_REL/native-build/cherchi/python"

"${DOCKER[@]}" run --rm --init \
  --memory=24g --memory-swap=24g --cpus=8 --cgroupns=private \
  --mount "type=bind,src=$W4,dst=/work/w4,readonly" \
  --mount "type=bind,src=$W0_SOURCE,dst=/work/w0,readonly" \
  --mount "type=bind,src=$CORE,dst=/work/core,readonly" \
  --mount "type=bind,src=$W0_REVIEW,dst=/work/w0-review,readonly" \
  --mount "type=bind,src=$W2_REVIEW,dst=/work/w2-review,readonly" \
  --mount "type=bind,src=$RUNS,dst=/output" \
  --mount "type=bind,src=$PLAN,dst=/private/P30_UNEXECUTED_TANGENT_PLAN.json,readonly" \
  --mount "type=bind,src=$ARCHIVE,dst=/private/P27_FORMAL_M6_EVIDENCE.tar.gz,readonly" \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp --env GIT_CONFIG_GLOBAL=/tmp/gitconfig \
  --env PYTHONPATH="$PYTHONPATH" \
  --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 --env MKL_NUM_THREADS=1 \
  --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONNOUSERSITE=1 \
  --entrypoint /opt/w4-venv/bin/python \
  "$IMAGE" "/work/w4/$P30/p30b_native_sampler.py" \
  --mode batch \
  --w4-root /work/w4 --w0-source-root /work/w0 --core-root /work/core \
  --w0-review-root /work/w0-review --w2-review-root /work/w2-review \
  --plan /private/P30_UNEXECUTED_TANGENT_PLAN.json \
  --archive /private/P27_FORMAL_M6_EVIDENCE.tar.gz \
  --p20-request "/work/w4/$P1/P20_native_request.json" \
  --registered-lock "/output/$LOCK_REL" \
  --external-lock-sha "$P30B_EXTERNAL_LOCK_SHA256" \
  --p27-run-dir "/output/$P27_RUN_REL" \
  --output-dir "/output/$OUT_REL" "${RESUME[@]}"

echo "P30B_PILOT_WRAPPER_RETURNED. Preserve every attempt, including failures."
echo "Evidence: $OUTPUT"
echo "Even a complete 12/12 run is DIAGNOSTIC ONLY, not smoothness/Newton/Teacher admission."
