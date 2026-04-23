# Package Management

Install Python packages in your custom MaxFrame DPE runtime image.

## Conda vs pip Decision Guide

**Use Conda when:**
- Binary packages available (faster installation)
- Complex dependencies (C/C++ libraries)
- Scientific computing packages (numpy, scipy, pandas)
- ML frameworks (pytorch, tensorflow)

**Use pip when:**
- Python-only packages not in conda
- Latest versions not yet in conda
- Packages only available on PyPI

## Conda-forge Best Practices

**Why Miniforge over Miniconda:**
- ✅ Uses conda-forge channel by default
- ✅ Community-driven, open-source
- ✅ Smaller initial footprint
- ✅ No Anaconda repository configuration needed
- ✅ Better for conda-forge-first installations

**Channel Configuration:**
```dockerfile
# Configure conda to use conda-forge only
RUN conda config --remove channels defaults || true && \
    conda config --add channels conda-forge && \
    conda config --set channel_priority strict && \
    conda config --set show_channel_urls true
```

## Mirror Acceleration (China Region)

For faster downloads in China region, configure mirrors:

**Conda Mirror (Tsinghua):**
```dockerfile
# Use Tsinghua mirror for conda-forge (faster in China)
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/ && \
    conda config --set show_channel_urls yes
```

**Pip Mirror (Aliyun):**
```dockerfile
# Configure pip to use Aliyun mirror (faster in China)
RUN mkdir -p ~/.pip && \
    echo "[global]\n\
index-url = https://mirrors.aliyun.com/pypi/simple/\n\
trusted-host = mirrors.aliyun.com" > ~/.pip/pip.conf
```

**Complete Mirror Setup:**
```dockerfile
# Ubuntu packages - Aliyun mirror
RUN echo "deb http://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse\n\
deb http://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse\n\
deb http://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse\n\
deb http://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse" \
    > /etc/apt/sources.list

# Conda packages - Tsinghua mirror
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/ && \
    conda config --set show_channel_urls yes

# Pip packages - Aliyun mirror
RUN mkdir -p ~/.pip && \
    echo "[global]\n\
index-url = https://mirrors.aliyun.com/pypi/simple/\n\
trusted-host = mirrors.aliyun.com" > ~/.pip/pip.conf
```

## Package Installation Patterns

**Pattern 1: Simple Installation (no version constraints)**
```dockerfile
RUN conda install -n py311 -c conda-forge \
    requests \
    beautifulsoup4 \
    lxml && \
    conda clean -afy
```

**Pattern 2: Version Pinning**
```dockerfile
RUN conda install -n py311 -c conda-forge \
    pandas=1.5 \
    numpy=1.23 \
    scipy=1.9 && \
    conda clean -afy
```

**Pattern 3: Flexible Constraints**
```dockerfile
RUN conda install -n py311 -c conda-forge \
    "pandas>=1.5,<2.0" \
    "numpy>=1.23" && \
    conda clean -afy
```

**Pattern 4: Multi-Environment Installation Loop**
```dockerfile
# Install packages in all selected Python environments
RUN for env in py310 py311 py312; do \
        echo "Installing packages in $env..." && \
        conda install -n $env --override-channels \
            -c conda-forge \
            transformers accelerate datasets; \
    done && \
    conda clean -afy
```

**Pattern 5: PyTorch from pytorch Channel**
```dockerfile
# Add pytorch channel when installing torch packages
RUN for env in py311; do \
        conda install -n $env --override-channels \
            -c pytorch \
            -c conda-forge \
            pytorch torchvision torchaudio; \
    done && \
    conda clean -afy
```

## GPU Package Handling

**PyTorch with CUDA (Recommended via pip):**
```dockerfile
# Install PyTorch with CUDA support via pip (not conda)
RUN pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124
```

**Why pip for PyTorch+CUDA:**
- PyTorch provides optimized CUDA builds via pip
- Easier CUDA variant selection (cu124, cu121, cu118)
- Better compatibility with CUDA toolkit installed in image

## Pip Fallback Pattern

When package not available in conda-forge:
```dockerfile
# Install via pip in each environment
RUN for env in py311; do \
        conda run -n $env pip install --no-cache-dir \
            some-pip-only-package \
            another-package; \
    done
```

## Related Guides

- **[GPU/CUDA Configuration](gpu-cuda-configuration.md)** - PyTorch with CUDA setup
- **[Python Environment Strategy](python-environment-strategy.md)** - Multi-environment architecture
- **[Image Optimization](image-optimization.md)** - Cleaning package cache

---

**Part of [Custom Runtime Image Guides](README.md)**