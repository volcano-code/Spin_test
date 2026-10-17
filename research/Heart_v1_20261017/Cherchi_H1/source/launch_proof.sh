#!/bin/bash
set -eu
R=/mnt/data/heart_native
export LD_LIBRARY_PATH="$R/build-cherchi-fixed2/gnu_14.2_cxx20_64_release:$R/runtime-extra/lib:$R/build-gcc/compiler-runtime:$R/prefix/lib" PYTHONPATH="$R/build-cherchi-fixed2/python:$R/build-gcc/python" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd /mnt/data/Heart_Cherchi_H1
exec timeout -s TERM 150s python -u source/compare_independent_exact_set.py