#!/usr/bin/env bash
set -euo pipefail
R=/mnt/data/noodles_v6_newrun/runtime
export LD_LIBRARY_PATH="$R/prefix/lib:$R/runtime-extra/lib:$R/build-gcc/compiler-runtime:$R/build-cherchi-fixed2/gnu_14.2_cxx20_64_release"
export PYTHONPATH="/mnt/data/Noodles_v6_C4_work/runtime:$R/workspace/project/python:$R/build-gcc/python:$R/build-cherchi-fixed2/python:$R/native-deps/python"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
exec python -u /mnt/data/Noodles_v7_paper_geometry_candidate/resume_v7_from_accepted_checkpoint.py "$@"
