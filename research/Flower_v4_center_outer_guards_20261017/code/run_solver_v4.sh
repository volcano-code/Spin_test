#!/usr/bin/env bash
set -uo pipefail
BASE=/mnt/data/Spin_flower_center_guard_20261017
SRC=/mnt/data/Spin_flower_rebuild_20261017/source/project
NATIVE=/mnt/data/Spin_flower_rebuild_20261017/native
export PYTHONPATH="$BASE/code:$SRC/python:$SRC/experiments/quadric_physics_demo_20261011:$NATIVE/build-gcc/python:$NATIVE/native-deps/python"
export LD_LIBRARY_PATH="$NATIVE/prefix/lib:$NATIVE/build-gcc/compiler-runtime:${LD_LIBRARY_PATH:-}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONNOUSERSITE=1
for label in main repeat;do
 TZ=Asia/Shanghai date -Is > "$BASE/results/v4-$label-start-local.txt"
 date -u -Is > "$BASE/results/v4-$label-start-utc.txt"
 /usr/bin/timeout --signal=TERM --kill-after=10s 600s python -u "$SRC/experiments/spin_it_reproduction/faster/run_paper_table1.py" --manifest "$BASE/results/frozen-input-v4/flower-cases.json" --output "$BASE/results/v4-flower-$label.json" --starts 2 --max-restarts 8 > "$BASE/results/v4-$label.stdout.log" 2> "$BASE/results/v4-$label.stderr.log"
 rc=$?;echo "$rc" > "$BASE/results/v4-$label.exit";TZ=Asia/Shanghai date -Is > "$BASE/results/v4-$label-end-local.txt"
 [ "$rc" -eq 0 ] || exit "$rc"
done
