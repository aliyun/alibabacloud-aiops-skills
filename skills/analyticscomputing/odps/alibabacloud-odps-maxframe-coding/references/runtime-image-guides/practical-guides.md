# Practical Guides for Runtime Image Creation

This document provides practical guidance for different use cases when creating custom MaxFrame DPE runtime images.

---

## Table of Contents

1. [Conda Distribution Selection](#conda-distribution-selection)
2. [GPU/CUDA Support](#gpucuda-support)
3. [Common Scenarios](#common-scenarios)
4. [Best Practices](#best-practices)

---

## Conda Distribution Selection

### Why Miniforge over Miniconda?

We **strongly recommend using Miniforge** (conda-forge distribution) instead of Miniconda or Anaconda for the following reasons:

#### License Considerations

| Distribution | License | Commercial Use | Notes |
|-------------|---------|----------------|-------|
| **Miniforge** | **BSD-3-Clause** | ✅ **Unrestricted** | Community-driven, fully open-source |
| **Miniconda** | Apache 2.0 + Anaconda ToS | ⚠️ **Restricted** | Anaconda Terms of Service may apply |
| **Anaconda** | Proprietary + Commercial ToS | ❌ **Requires License** | Commercial use requires paid license |

**Important**: Anaconda Inc.'s Terms of Service restrict commercial use of their package repositories. For enterprise/commercial use, Miniforge is the safest choice.

#### Technical Advantages of Miniforge

✅ **Better conda-forge integration**
- Pre-configured to use conda-forge channel
- No Anaconda repository needed
- Cleaner channel configuration

✅ **Smaller footprint**
- Minimal base installation
- Only conda-forge packages by default
- Faster installation

✅ **Community-driven**
- No vendor lock-in
- Transparent governance
- Open-source packages only

#### Miniconda Issues

❌ **Requires manual configuration**
- Default channels point to Anaconda
- Need to disable defaults
- More complex setup

❌ **Terms of Service complications**
- Commercial use restrictions
- May require license for enterprise
- Legal complexity

❌ **Larger initial size**
- Includes Anaconda-specific packages
- Unnecessary dependencies
- Slower builds

### How to Use Miniforge

The runtime image creator uses Miniforge by default. The generated Dockerfile includes:

```dockerfile
# Install Miniforge (conda-forge distribution)
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && \
    bash miniforge.sh -b -p ${MINIFORGE_HOME} && \
    rm -rf miniforge.sh

# Configure conda to use conda-forge only
RUN conda config --remove channels defaults || true && \
    conda config --add channels conda-forge && \
    conda config --set channel_priority strict
```

---

## GPU/CUDA Support

### When to Use GPU Runtime

Use GPU-enabled runtime when you need:

- Deep learning frameworks (PyTorch, TensorFlow)
- GPU-accelerated computing (CUDA libraries)
- Machine learning model training/inference
- Computer vision workloads
- Large-scale numerical computing

**Do NOT use GPU runtime for:**
- CPU-only data processing
- Simple ETL jobs
- Lightweight Python scripts
- Development/testing without GPU access

### CUDA Version Selection

Choose the CUDA version based on your PyTorch/TensorFlow requirements:

**Recommended Production Configuration:**
- **Ubuntu 22.04 + CUDA 12.4** - Our default recommended setup
- PyTorch 2.6.0+ with CUDA 12.4 support
- Best compatibility with modern GPUs (Ampere, Hopper)
- Latest features and performance optimizations

| CUDA Version | PyTorch Version | TensorFlow Version | CUDA Compute Capability | Base OS |
|--------------|----------------|-------------------|------------------------|---------|
| **CUDA 12.4** ✅ | PyTorch 2.6.0+ | TensorFlow 2.16+ | Compute 8.0+ (Ampere+) | **Ubuntu 22.04** (Recommended) |
| **CUDA 12.1** | PyTorch 2.6.0+ | TensorFlow 2.15+ | Compute 7.0+ (Volta+) | Ubuntu 22.04 |
| **CUDA 11.8** | PyTorch 2.6.0+ | TensorFlow 2.12+ | Compute 6.0+ (Pascal+) | Ubuntu 22.04 |

**Why Ubuntu 22.04 + CUDA 12.4 is recommended:**
- ✅ Long-term support until 2027
- ✅ Latest CUDA features and optimizations
- ✅ Best compatibility with modern ML frameworks
- ✅ Production-ready and stable
- ✅ Supports latest GPU architectures (Hopper, Ampere)

### GPU Runtime Creation

Use the conversational workflow documented in SKILL.md "Scenario 4: Create Custom Runtime Image" for GPU runtime creation.

#### Option 1: GPU Support Only (CUDA Toolkit)

Use when you need CUDA libraries but will install PyTorch/TensorFlow manually or via conda.

**Conversational Workflow Choices:**
1. **Base Image:** Select Ubuntu 22.04 (recommended for GPU)
2. **Python Versions:** Select versions (e.g., 3.10, 3.11)
3. **GPU Support:** Select "Yes - GPU-enabled with CUDA 12.4"
4. **Packages:** Specify your packages (e.g., numpy pandas scipy)

**Generated Dockerfile includes:**
- NVIDIA CUDA repository (Ubuntu 22.04)
- CUDA toolkit installation
- CUDA environment variables (CUDA_HOME, PATH)

#### Option 2: GPU + PyTorch with CUDA (Recommended)

Use when you need PyTorch with CUDA support pre-installed.

**Conversational Workflow Choices:**
1. **Base Image:** Select Ubuntu 22.04 (required for GPU)
2. **Python Versions:** Select versions (e.g., 3.10, 3.11)
3. **GPU Support:** Select "Yes - GPU-enabled with CUDA 12.4"
4. **Packages:** Specify PyTorch-dependent packages (e.g., transformers datasets accelerate)

**Generated Dockerfile includes:**
- CUDA toolkit (Ubuntu 22.04 + CUDA 12.4)
- PyTorch 2.6.0 with CUDA 12.4
- torchvision 0.21.0+cu124, torchaudio 2.6.0+cu124
- All specified user packages

#### Option 3: CPU-Only PyTorch

Use when you need PyTorch but no GPU support.

```bash
python3 scripts/generate_dockerfile.py \
    --packages pytorch torchvision torchaudio cpuonly -c pytorch \
    --python-versions 3.11 \
    --image-tag my-pytorch-cpu:v1
```

### PyTorch CUDA Compatibility

The runtime image creator automatically handles PyTorch CUDA version matching:

**Default Production Configuration (Recommended):**
```dockerfile
# Ubuntu 22.04 + CUDA 12.4 + PyTorch 2.6.0
RUN pip install torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124 --index-url https://download.pytorch.org/whl/cu124
```

**Alternative CUDA Variants:**
```dockerfile
# CUDA 12.1
RUN pip install torch==2.6.0+cu121 torchvision==0.21.0+cu121 torchaudio==2.6.0+cu121 --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.8 (legacy support)
RUN pip install torch==2.6.0+cu118 torchvision==0.21.0+cu118 torchaudio==2.6.0+cu118 --index-url https://download.pytorch.org/whl/cu118
```

**Note**: PyTorch with CUDA is installed via pip, not conda, to ensure exact CUDA variant matching.

---

## Common Scenarios

Use the conversational workflow documented in SKILL.md "Scenario 4: Create Custom Runtime Image" for all scenarios below.

### Scenario 1: NLP/LLM Inference (GPU)

**Requirements:**
- Transformers library
- PyTorch with CUDA
- Python 3.10+

**Conversational Workflow Choices:**
1. Base Image: Ubuntu 22.04 (for GPU support)
2. Python Versions: 3.10, 3.11
3. GPU Support: Yes - GPU-enabled with CUDA 12.4
4. Packages: transformers accelerate sentencepiece tokenizers

**Generated Dockerfile will include:**
- Ubuntu 22.04 base
- CUDA 12.4 toolkit
- PyTorch 2.6.0 with CUDA 12.4
- Transformers, accelerate, and related NLP libraries
- Python 3.10 and 3.11 environments

### Scenario 2: Computer Vision (GPU)

**Requirements:**
- PyTorch with CUDA
- OpenCV, PIL
- Image processing libraries

**Conversational Workflow Choices:**
1. Base Image: Ubuntu 22.04 (for GPU support)
2. Python Versions: 3.11
3. GPU Support: Yes - GPU-enabled with CUDA 12.4
4. Packages: opencv pillow scikit-image albumentations

### Scenario 3: Data Science (CPU)

**Requirements:**
- Pandas, NumPy, Scikit-learn
- Data analysis libraries
- CPU-only

**Conversational Workflow Choices:**
1. Base Image: Ubuntu 22.04 or 24.04
2. Python Versions: 3.10, 3.11, 3.12
3. GPU Support: No - CPU only
4. Packages: pandas numpy scikit-learn matplotlib seaborn

### Scenario 4: Large Language Models with vLLM/SGLang

**Requirements:**
- vLLM or SGLang for fast inference
- PyTorch with CUDA
- Latest Python

**Conversational Workflow Choices:**
1. Base Image: Ubuntu 22.04 (for GPU support)
2. Python Versions: 3.11
3. GPU Support: Yes - GPU-enabled with CUDA 12.4
4. Packages: vllm
    --pytorch-cuda-install \
    --image-tag vllm-runtime:v1

# OR for SGLang
python3 scripts/generate_dockerfile.py \
    --packages sglang transformers diffusers peft \
    --python-versions 3.10 \
    --enable-gpu \
    --cuda-variant cu124 \
    --pytorch-cuda-install \
    --image-tag sglang-runtime:v1
```

**Note**: vLLM and SGLang require specific CUDA versions. Check their documentation for compatibility.

### Scenario 5: Distributed Training with DeepSpeed

**Requirements:**
- DeepSpeed for distributed training
- PyTorch with CUDA
- MPI support

**Conversational Workflow Choices:**
1. Base Image: Ubuntu 22.04 (for GPU support)
2. Python Versions: 3.10
3. GPU Support: Yes - GPU-enabled with CUDA 12.1 (broader compatibility for DeepSpeed)
4. Packages: deepspeed mpi4py

---

## Best Practices

### 1. Python Version Selection

**Recommended**: Use Python 3.10 or 3.11 for GPU workloads

- Python 3.10+: Best compatibility with ML libraries
- Python 3.11: Best performance (significant speedup)
- Python 3.12: Latest features, but some packages may not be available

**Legacy**: Only use Python 3.7-3.9 if required for compatibility

### 2. Image Size Optimization

**Reduce image size by:**

✅ **Selecting only needed Python versions**

During conversational workflow:
- Good: Select single version (e.g., 3.11)
- Avoid: Selecting all versions if not needed

✅ **Using conda clean**
```dockerfile
RUN conda clean -afy
```

✅ **Minimizing system packages**
- Only include what you need
- Remove build dependencies if not needed

### 3. CUDA Version Strategy

**Recommended: Ubuntu 22.04 + CUDA 12.4 for Production**

**Match CUDA to your GPU hardware:**

| GPU Generation | Recommended CUDA | Base OS | Examples |
|----------------|------------------|---------|----------|
| Hopper (H100) | **CUDA 12.4** ✅ | Ubuntu 22.04 | Latest datacenters |
| Ampere (A100, A10) | **CUDA 12.4** ✅ | Ubuntu 22.04 | Modern datacenters |
| Volta (V100) | CUDA 12.1 or 11.8 | Ubuntu 22.04 | Older datacenters |
| Turing (T4) | CUDA 12.1 or 11.8 | Ubuntu 22.04 | Cloud instances |

**Match CUDA to your framework:**
- **Default**: Ubuntu 22.04 + CUDA 12.4 - Best for modern workloads
- Check PyTorch/TensorFlow compatibility
- CUDA 12.4 provides latest features and optimizations
- Use CUDA 12.1/11.8 only if required for older GPU compatibility

### 4. Security Considerations

**DO NOT include in images:**
- ❌ Credentials or API keys
- ❌ Private SSH keys
- ❌ Database passwords
- ❌ Access tokens

**DO include:**
- ✅ Public certificates (if needed)
- ✅ Configuration templates
- ✅ Documentation for required secrets

**Pass secrets at runtime:**
```bash
docker run -e ODPS_ACCESS_KEY=$ODPS_ACCESS_KEY \
           -e HUGGING_FACE_HUB_TOKEN=$HF_TOKEN \
           my-image:tag
```

### 5. Build Optimization

**Use build caching:**
```bash
# Build with cache (faster for development)
docker build -t myimage:v1 .

# Build without cache (production)
docker build --no-cache -t myimage:v1 .
```

**Multi-platform builds:**
```bash
# Build for x86_64
docker build --build-arg TARGETARCH=amd64 -t myimage:v1 .

# Build for arm64 (experimental)
docker build --build-arg TARGETARCH=arm64 -t myimage:v1 .
```

### 6. Testing Your Image

**Basic health check:**
```bash
docker run --rm myimage:v1 python --version
docker run --rm myimage:v1 conda list
```

**GPU verification:**
```bash
# Check CUDA
docker run --rm --gpus all myimage:v1 nvidia-smi
docker run --rm --gpus all myimage:v1 nvcc --version

# Check PyTorch CUDA
docker run --rm --gpus all myimage:v1 python -c "import torch; print(torch.cuda.is_available())"
```

**Package verification:**
```bash
docker run --rm myimage:v1 python -c "
import torch
import transformers
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Transformers: {transformers.__version__}')
"
```

---

## Troubleshooting

### Issue: CUDA out of memory

**Cause**: GPU memory limit exceeded

**Solution:**
1. Use smaller batch sizes
2. Enable gradient checkpointing
3. Use mixed precision training
4. Reduce model size

### Issue: PyTorch doesn't detect GPU

**Cause**: CUDA mismatch or driver issue

**Solution:**
```bash
# Check CUDA version
nvidia-smi
nvcc --version

# Check PyTorch CUDA
python -c "import torch; print(torch.version.cuda)"

# Rebuild with correct CUDA variant
--cuda-variant cu124  # Match to your system
```

### Issue: Package not found in conda-forge

**Solution:**
1. Check package name: `conda search -c conda-forge <package>`
2. Try alternative name
3. Use pip fallback:
```dockerfile
RUN pip install <package-name>
```

### Issue: Image size too large

**Solution:**
1. Use fewer Python versions
2. Remove unnecessary packages
3. Use multi-stage builds
4. Clean conda cache: `conda clean -afy`

---

## Summary

### Key Recommendations

1. **Use Miniforge** (not Miniconda) for unrestricted commercial use
2. **Match CUDA version** to your GPU hardware and framework requirements
3. **Select minimal Python versions** to reduce image size
4. **Test locally** before pushing to production
5. **Never include secrets** in Docker images

### Quick Reference

| Use Case | Python | CUDA | Command Example |
|----------|--------|------|-----------------|
| **LLM Inference** | 3.10, 3.11 | cu124 | `--enable-gpu --cuda-variant cu124 --pytorch-cuda-install` |
| **Computer Vision** | 3.11 | cu124 | `--enable-gpu --cuda-variant cu124 --pytorch-cuda-install` |
| **Data Science** | 3.10-3.12 | N/A | No GPU flags |
| **Legacy ML** | 3.9 | cu118 | `--enable-gpu --cuda-variant cu118 --pytorch-cuda-install` |

For more information, see:
- `conda_best_practices.md` - Conda usage guidelines
- `base_image_details.md` - Base image architecture
- `quick_start_guide.md` - Getting started guide