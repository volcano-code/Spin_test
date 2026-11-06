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

"${DOCKER[@]}" build --pull \
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
  --env P1="$P1_REL" --env RUN_REL="$RUN_REL" --env OUT="/output/$RUN_REL" \
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
    python - <<'PY'
    from pathlib import Path
    vals={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        f=line.split()
        if len(f)>=3 and f[1].isdigit() and f[2]=="kB":
            vals[f[0].rstrip(":")]=int(f[1])*1024
    assert vals["SwapTotal"]==0, vals
    assert vals["MemTotal"]>=20*1024**3, vals
    print("FORMAL_CONTAINER_RESOURCE_PRECHECK",{
      "MemTotal_bytes":vals["MemTotal"],
      "SwapTotal_bytes":vals["SwapTotal"],
      "memory.max":Path("/sys/fs/cgroup/memory.max").read_text().strip(),
      "memory.swap.max":Path("/sys/fs/cgroup/memory.swap.max").read_text().strip()
    })
    PY

    # Preflight is read-only and must pass before native build or factory work.
    /opt/w4-venv/bin/python "$P1/p21_m6_replay.py" preflight \
      --output "$OUT/P21_RESOURCE_PREFLIGHT.json"
    /opt/w4-venv/bin/python - <<'PY'
    import json,os
    from pathlib import Path
    p=Path(os.environ["OUT"])/"P21_RESOURCE_PREFLIGHT.json"
    r=json.loads(p.read_text())
    assert r["status"]=="ADMITTED_RESOURCE_POLICY_ONLY",r
    assert r["formal_M6_executed"] is False
    print("P21_RESOURCE_PREFLIGHT_PASS")
    PY
' 2>&1 | tee "$RUN_DIR/container-resource-preflight.log"

# Build the three real native modules from the frozen Core/Cherchi source.
"${DOCKER[@]}" run --rm --init \
  --memory=24g --memory-swap=24g --cpus=8 --cgroupns=private \
  --mount "type=bind,src=$W4_ROOT,dst=/work/w4,readonly" \
  --mount "type=bind,src=$W0_ROOT,dst=/work/w0,readonly" \
  --mount "type=bind,src=$CORE_ROOT,dst=/work/core" \
  --mount "type=bind,src=$P27_ROOT,dst=/output" \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp --env GIT_CONFIG_GLOBAL=/tmp/gitconfig \
  --env P1="$P1_REL" --env RUN_REL="$RUN_REL" \
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

    /opt/w4-venv/bin/python "$P1/p20_build_native_ci.py" \
      --source-checkout /work/core \
      --build-root "$OUT/native-build" \
      --evidence "$OUT/native-build-evidence" \
      --timeout-seconds 2400

    python - <<'PY'
    import json,os
    from pathlib import Path
    p=Path(os.environ["OUT"])/"native-build-evidence/P20_NATIVE_BUILD_REPORT.json"
    r=json.loads(p.read_text())
    assert r["status"]=="BUILT_AND_IMPORT_VERIFIED_NO_GEOMETRY",r
    assert r["import_probe"]["imports_verified"] is True
    assert r["import_probe"]["geometry_calls"]==0
    assert set(r["native_modules"])=={"_make_it_stand","_cherchi_core_boolean","_cherchi_rational_moments"}
    print("P27_NATIVE_BUILD_PASS",r["native_modules"])
    PY

    export PYTHONPATH="/work/w0:/work/core/python:$P1:$OUT/native-build/core/python:$OUT/native-build/cherchi/python"
    /opt/w4-venv/bin/python "$P1/p20_owned_material_audit.py" \
      --output "$OUT/P20_OWNED_MATERIAL_PREPARATION.json" \
      --pins-output "$OUT/P20_NATIVE_SIX_PINS.json" \
      --seconds 900

    python - <<'PY'
    import json,os
    from pathlib import Path
    out=Path(os.environ["OUT"])
    r=json.loads((out/"P20_OWNED_MATERIAL_PREPARATION.json").read_text())
    assert r["completed"] is True,r
    result=r["result"]
    part=result["native_M_equals_F_plus_D_partition"]
    assert part["complete_partition"] and part["union_equals_whole"]
    assert part["no_positive_volume_overlap"]
    assert part["missing_whole_content"] is False and part["excess_union_content"] is False
    assert result["all_ten_exact_additivity_residuals_zero"] is True
    pins=json.loads((out/"P20_NATIVE_SIX_PINS.json").read_text())
    assert pins==result["observed_six_pins"]
    print("P27_P20_OWNED_MFD_PREPARATION_PASS",pins)
    PY

    /opt/w4-venv/bin/python "$P1/p21_m6_replay.py" preflight \
      --output "$OUT/P21_RESOURCE_PREFLIGHT_FINAL.json"
    /opt/w4-venv/bin/python "$P1/p21_m6_replay.py" register \
      --w0-checkout /work/w0 \
      --pins "$OUT/P20_NATIVE_SIX_PINS.json" \
      --python-path "$OUT/native-build/core/python" \
      --python-path "$OUT/native-build/cherchi/python" \
      --output "$OUT/P21_PRERUN_LOCK.json"

    python - <<'PY'
    import hashlib,json,os
    from pathlib import Path
    out=Path(os.environ["OUT"])
    lock=json.loads((out/"P21_PRERUN_LOCK.json").read_text())
    assert lock["w0_commit"]=="5bab2eb2616df306906a6887a273f68acfa49320"
    assert lock["registration_is_independent_attestation"] is False
    assert lock["registration_grants_scientific_admission"] is False
    assert all(value is False for value in lock["admission"].values())
    digest=hashlib.sha256((out/"P21_PRERUN_LOCK.json").read_bytes()).hexdigest()
    (out/"P21_PRERUN_LOCK_SHA256.txt").write_text(digest+"\n")
    print("P27_PRERUN_LOCK_CREATED_NO_NATIVE_M6_EXECUTION")
    print("P27_LOCK_SHA256="+digest)
    PY
' 

echo
echo "P27 preparation completed. No formal M6 geometry audit has been executed."
echo "Run directory: $RUN_DIR"
echo "Pre-run lock: $RUN_DIR/P21_PRERUN_LOCK.json"
echo "Pre-run lock SHA-256:"
cat "$RUN_DIR/P21_PRERUN_LOCK_SHA256.txt"
echo
echo "Independently review/register this digest before running p27_execute_formal_m6.sh."
