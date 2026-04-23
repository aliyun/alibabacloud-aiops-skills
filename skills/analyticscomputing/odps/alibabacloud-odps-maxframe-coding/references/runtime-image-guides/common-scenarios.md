# Common Scenarios

Complete Dockerfile examples for common use cases.

## Scenario 1: Basic ML Runtime (GPU)

```dockerfile
FROM ubuntu:22.04

# System setup
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    wget curl vim ca-certificates locales build-essential jq && \
    rm -rf /var/lib/apt/lists/*

# Miniforge setup
ENV MINIFORGE_HOME="/py-runtime"
ENV PATH="${MINIFORGE_HOME}/bin:${PATH}"
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && \
    bash miniforge.sh -b -p ${MINIFORGE_HOME} && rm -rf miniforge.sh

# Python 3.11
RUN conda create -y -n py311 python=3.11 -c conda-forge && conda clean -afy

# CUDA 12.4
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin && \
    mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && rm -rf cuda-keyring_*.deb && \
    apt-get update && apt-get install -y cuda-toolkit && rm -rf /var/lib/apt/lists/*
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH

# PyTorch with CUDA
RUN pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 --index-url https://download.pytorch.org/whl/cu124

# User packages
RUN conda install -n py311 -c conda-forge transformers accelerate && conda clean -afy

# Environment config
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python

CMD ["conda", "run", "-n", "py311", "python"]
```

## Scenario 2: Data Processing Runtime (CPU, Multi-Python)

```dockerfile
FROM ubuntu:22.04

# System setup
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    wget curl vim ca-certificates locales build-essential && \
    rm -rf /var/lib/apt/lists/*

# Miniforge setup
ENV MINIFORGE_HOME="/py-runtime"
ENV PATH="${MINIFORGE_HOME}/bin:${PATH}"
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && \
    bash miniforge.sh -b -p ${MINIFORGE_HOME} && rm -rf miniforge.sh

# Multiple Python versions
RUN conda create -y -n py310 python=3.10 -c conda-forge && \
    conda create -y -n py311 python=3.11 -c conda-forge && \
    conda create -y -n py312 python=3.12 -c conda-forge && \
    conda clean -afy

# Install packages in all environments
RUN for env in py310 py311 py312; do \
        conda install -n $env -c conda-forge pandas dask polars pyarrow; \
    done && conda clean -afy

# Environment config
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python

CMD ["conda", "run", "-n", "py311", "python"]
```

## Scenario 3: Minimal Single-Python Runtime

```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y wget curl && rm -rf /var/lib/apt/lists/*

ENV MINIFORGE_HOME="/py-runtime"
ENV PATH="${MINIFORGE_HOME}/bin:${PATH}"
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && \
    bash miniforge.sh -b -p ${MINIFORGE_HOME} && rm -rf miniforge.sh

RUN conda create -y -n py311 python=3.11 -c conda-forge && conda clean -afy

RUN conda install -n py311 -c conda-forge pandas numpy && conda clean -afy

ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python

CMD ["conda", "run", "-n", "py311", "python"]
```

## Related Guides

- **[Dockerfile Templates](dockerfile-templates.md)** - Individual section templates
- **[Testing and Validation](testing-validation.md)** - How to test these examples

---

**Part of [Custom Runtime Image Guides](README.md)**