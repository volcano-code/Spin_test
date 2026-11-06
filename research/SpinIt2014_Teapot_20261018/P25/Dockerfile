FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git pkg-config ca-certificates \
    libgmp-dev libmpfr-dev libboost-thread-dev libboost-system-dev \
    python3 python3-dev python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/w4-venv
ENV PATH="/opt/w4-venv/bin:${PATH}" \
    PYTHONNOUSERSITE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN /opt/w4-venv/bin/python -m pip install --no-cache-dir \
    numpy==2.3.5 \
    scipy==1.17.0 \
    trimesh==4.12.2 \
    networkx==3.7 \
    cmake==3.31.6 \
    ninja==1.11.1.4 \
    pybind11==3.0.1

WORKDIR /work
CMD ["bash"]
