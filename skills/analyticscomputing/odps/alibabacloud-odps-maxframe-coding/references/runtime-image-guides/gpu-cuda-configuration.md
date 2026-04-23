# GPU/CUDA Configuration

Configure GPU and CUDA support for your custom MaxFrame DPE runtime image.

## CUDA Version Compatibility Matrix

| CUDA Version | Ubuntu Version | PyTorch Version | Status |
|--------------|----------------|-----------------|--------|
| **CUDA 12.4** | Ubuntu 22.04 | PyTorch 2.6.0+cu124 | ✅ Recommended |
| CUDA 12.1 | Ubuntu 22.04 | PyTorch 2.6.0+cu121 | ✅ Supported |
| CUDA 11.8 | Ubuntu 22.04 | PyTorch 2.6.0+cu118 | ✅ Supported |

**Recommended:** Ubuntu 22.04 + CUDA 12.4 + PyTorch 2.6.0+cu124

## Platform Considerations

**GPU support currently limited to x86_64 platform.**
- ✅ x86_64: Full GPU support
- ❌ aarch64: GPU not supported

## CUDA Installation Pattern (Ubuntu 22.04)

```dockerfile
# Add NVIDIA package repositories for Ubuntu 22.04
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin && \
    mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && rm -rf cuda-keyring_*.deb

# Update and install CUDA toolkit
RUN apt-get update && apt-get install -y \
    cuda-toolkit && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up CUDA environment
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
```

## PyTorch Installation with CUDA

```dockerfile
# Install PyTorch 2.6.0 with CUDA 12.4
RUN pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124
```

**CUDA Variants:**
- `cu124` - CUDA 12.4 (Recommended)
- `cu121` - CUDA 12.1
- `cu118` - CUDA 11.8

## Complete GPU Setup Pattern

```dockerfile
# 1. Install CUDA toolkit
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin && \
    mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && rm -rf cuda-keyring_*.deb && \
    apt-get update && apt-get install -y cuda-toolkit && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH

# 2. Install PyTorch with CUDA
RUN pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124

# 3. Install user packages (in conda environment)
RUN conda install -n py311 -c conda-forge \
    transformers accelerate datasets && \
    conda clean -afy
```

## Related Guides

- **[Base Image Selection](base-image-selection.md)** - Ubuntu 22.04 required for GPU
- **[Package Management](package-management.md)** - GPU package handling
- **[Dockerfile Templates](dockerfile-templates.md)** - GPU setup template

---

**Part of [Custom Runtime Image Guides](README.md)**