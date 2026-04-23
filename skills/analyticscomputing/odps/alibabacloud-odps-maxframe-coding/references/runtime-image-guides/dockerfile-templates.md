# Dockerfile Templates

Ready-to-use Dockerfile section templates for building custom runtime images.

## Template 1: Header/Metadata Section

```dockerfile
# Custom MaxFrame DPE Runtime Image
# Generated with best practices from runtime-image-guides/
#
# Configuration:
# - Base: Ubuntu 22.04 (stable, CUDA support)
# - Python: 3.11 (performance, production-ready)
# - GPU: CUDA 12.4, PyTorch 2.6.0+cu124
# - Packages: transformers, accelerate, datasets

FROM ubuntu:22.04

# Metadata
LABEL maintainer="user-defined"
LABEL description="Custom MaxFrame DPE runtime for ML workloads"
LABEL version="1.0"
```

## Template 2: Base Setup Section

```dockerfile
# Section: Base Image
# Pattern: Ubuntu 22.04 for ML/GPU workloads (best CUDA compatibility)
FROM ubuntu:22.04

# Use Aliyun mirror for Ubuntu packages (faster in China)
RUN echo "deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse\n\
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse\n\
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse\n\
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse" \
    > /etc/apt/sources.list

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LC_CTYPE=en_US.UTF-8
ENV TZ="Asia/Shanghai"
ENV TERM=xterm-256color

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    wget curl vim ca-certificates locales \
    build-essential jq dnsutils ffmpeg tzdata strace gdb && \
    locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8 && \
    rm -rf /var/lib/apt/lists/*
```

## Template 3: Conda Setup Section

```dockerfile
# Section: Miniforge Installation
# Pattern: Miniforge over Miniconda (conda-forge by default, no Anaconda repo)
ENV MINIFORGE_HOME="/py-runtime"
ENV PATH="${MINIFORGE_HOME}/bin:${PATH}"

RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && \
    bash miniforge.sh -b -p ${MINIFORGE_HOME} && \
    rm -rf miniforge.sh

# Configure conda to use conda-forge with Tsinghua mirror (faster in China)
RUN conda config --remove channels defaults || true && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/ && \
    conda config --set channel_priority strict && \
    conda config --set show_channel_urls yes

# Configure pip to use Aliyun mirror (faster in China)
RUN mkdir -p ~/.pip && \
    echo "[global]\n\
index-url = https://mirrors.aliyun.com/pypi/simple/\n\
trusted-host = mirrors.aliyun.com" > ~/.pip/pip.conf

# Section: Python Environment Creation
# Pattern: Single environment for production (Python 3.11)
RUN conda create -y -n py311 python=3.11 --override-channels -c conda-forge && \
    conda clean -afy
```

## Template 4: Multi-Python Setup Section

```dockerfile
# Create multiple Python environments
RUN conda create -y -n py310 python=3.10 --override-channels -c conda-forge && \
    conda create -y -n py311 python=3.11 --override-channels -c conda-forge && \
    conda create -y -n py312 python=3.12 --override-channels -c conda-forge && \
    conda clean -afy
```

## Template 5: GPU/CUDA Setup Section

```dockerfile
# Section: CUDA Installation
# Pattern: Ubuntu 22.04 + CUDA 12.4 (recommended for PyTorch)
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin && \
    mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && rm -rf cuda-keyring_*.deb

RUN apt-get update && apt-get install -y cuda-toolkit && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH

# Section: PyTorch with CUDA
# Pattern: PyTorch 2.6.0+cu124 (CUDA 12.4 compatible)
RUN pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124
```

## Template 6: Package Installation Section

```dockerfile
# Section: User Packages
# Pattern: Conda installation in all environments (from best practices guide)
RUN for env in py310 py311 py312; do \
        echo "Installing packages in $env..." && \
        conda install -n $env --override-channels \
            -c conda-forge \
            transformers accelerate datasets; \
    done && \
    conda clean -afy
```

## Template 7: Environment Configuration Section

```dockerfile
# Section: Environment Variables
# CRITICAL: MF_PYTHON_EXECUTABLE pattern (MaxFrame runtime detection)
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python
# Pattern: Always use conda environment path, never system Python

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV TZ="Asia/Shanghai"
```

## Template 8: Verification Section

```dockerfile
# Section: Verification
# Pattern: Health checks from best practices guide
RUN echo "=== Python Environments ===" && \
    conda env list && \
    echo "=== Default Python (py311) ===" && \
    conda run -n py311 python --version

CMD ["conda", "run", "-n", "py311", "python"]
```

## Usage

Combine templates based on your requirements:
1. Start with Template 1 (Header)
2. Add Template 2 (Base Setup) - always required
3. Add Template 3 (Conda Setup) - always required
4. Add Template 4 (Multi-Python) OR use single environment in Template 3
5. Add Template 5 (GPU/CUDA) - if GPU support needed
6. Add Template 6 (Package Installation) - customize with your packages
7. Add Template 7 (Environment Config) - always required
8. Add Template 8 (Verification) - always recommended

## Related Guides

- **[Common Scenarios](common-scenarios.md)** - Complete example Dockerfiles
- **[Testing and Validation](testing-validation.md)** - How to test generated images

---

**Part of [Custom Runtime Image Guides](README.md)**