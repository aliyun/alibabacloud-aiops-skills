# Conda Best Practices for Custom DPE Images with Multi-Python Support

## Overview

This guide covers best practices for using conda in custom MaxFrame DPE runtime images with support for multiple Python versions (3.7-3.12).

## Multi-Environment Strategy

### Why Multiple Environments?

The custom DPE runtime creates isolated conda environments for each Python version to:

1. **Match official DPE runtime pattern** - Same architecture as official images
2. **Provide flexibility** - Users can choose Python version at runtime
3. **Ensure compatibility** - Different Python versions for different jobs
4. **Enable testing** - Test code across multiple Python versions

### Environment Structure

```
/py-runtime/envs/
├── py37/     # Python 3.7
├── py38/     # Python 3.8
├── py39/     # Python 3.9
├── py310/    # Python 3.10 (typically default)
├── py311/    # Python 3.11
└── py312/    # Python 3.12
```

### Installation Pattern

**User packages are installed in ALL selected Python environments:**

```dockerfile
RUN for env in py37 py38 py39 py310 py311 py312; do \
        conda install -n $env -c conda-forge \
            transformers \
            torch \
            pandas; \
    done && \
    conda clean -afy
```

This ensures consistency across all environments.

## Why Use Conda

Conda provides several advantages for managing custom packages in DPE runtime images:

- **Dependency Management**: Automatic resolution of complex dependencies
- **Binary Packages**: Pre-compiled binaries for faster installation
- **Environment Isolation**: Separate user packages from system packages
- **Cross-Platform**: Consistent behavior across different systems
- **Version Control**: Precise version pinning and updates

## Conda Channels

### Recommended Channels

```bash
# Default channels (in order of priority)
conda-forge      # Community-maintained, most packages
pytorch          # PyTorch and related packages
defaults         # Official Anaconda packages
```

### Channel Priority

Set channel priority in Dockerfile:

```dockerfile
RUN conda config --add channels conda-forge && \
    conda config --add channels pytorch && \
    conda config --set channel_priority strict
```

**Why strict priority?**
- Prevents package conflicts
- Ensures packages come from preferred channels
- Faster dependency resolution

## Package Installation Patterns

### Pattern 1: Simple Installation

For straightforward packages without version constraints:

```dockerfile
RUN conda install -y -c conda-forge \
    requests \
    beautifulsoup4 \
    lxml \
    && conda clean -afy
```

### Pattern 2: Version Pinning

For specific versions:

```dockerfile
RUN conda install -y -c conda-forge \
    pandas=1.5 \
    numpy=1.23 \
    scipy=1.9 \
    && conda clean -afy
```

### Pattern 3: Flexible Constraints

For minimum versions:

```dockerfile
RUN conda install -y -c conda-forge \
    "pandas>=1.5,<2.0" \
    "numpy>=1.23" \
    && conda clean -afy
```

### Pattern 4: Multi-Channel

For packages from different channels:

```dockerfile
RUN conda install -y -c pytorch -c conda-forge \
    pytorch=2.0 \
    torchvision \
    transformers \
    && conda clean -afy
```

### Pattern 5: From Multiple Channels

When packages come from multiple sources:

```dockerfile
# Install PyTorch from pytorch channel
RUN conda install -y -c pytorch pytorch=2.0 torchvision

# Install other packages from conda-forge
RUN conda install -y -c conda-forge \
    transformers \
    datasets \
    && conda clean -afy
```

## Cleanup for Smaller Images

### Essential Cleanup Command

Always run after installation:

```dockerfile
RUN conda clean -afy
```

This removes:
- Package tarballs
- Index cache
- Lock files
- Unused packages

### Estimated Space Savings

| Component | Space Saved |
|-----------|-------------|
| Package cache | 200-500 MB |
| Index cache | 10-50 MB |
| Lock files | < 1 MB |
| **Total** | **210-550 MB** |

## Environment Variables

### Common Conda Variables

```dockerfile
# Conda configuration
ENV CONDA_AUTO_UPDATE_CONDA=false
ENV CONDA_CHANNELS=conda-forge,pytorch

# Package caches (use tmpfs during build)
ENV CONDA_PKGS_DIRS=/tmp/conda_pkgs

# Disable unnecessary features
ENV CONDA_AUTO_ACTIVATE_BASE=false
```

## Conda vs pip

### When to Use Conda

- Binary packages available (faster installation)
- Complex dependencies (C/C++ libraries)
- Scientific computing packages (numpy, scipy, pandas)
- ML frameworks (pytorch, tensorflow)

### When to Use pip

- Python-only packages not in conda
- Latest versions not yet in conda
- Packages only available on PyPI

### Mixed Approach

If pip is needed:

```dockerfile
# Install conda packages first
RUN conda install -y -c conda-forge \
    numpy \
    pandas \
    && conda clean -afy

# Then install pip-only packages
RUN pip install --no-cache-dir \
    some-pip-only-package \
    another-package
```

## GPU Package Considerations

### CUDA Version Compatibility

Check base image CUDA version:

```dockerfile
# Verify CUDA version
RUN nvcc --version || echo "No CUDA in base image"
```

### PyTorch with CUDA

```dockerfile
# Match PyTorch version to CUDA
RUN conda install -y -c pytorch -c nvidia \
    pytorch=2.0 \
    torchvision \
    torchaudio \
    pytorch-cuda=11.8 \
    && conda clean -afy
```

### TensorFlow with CUDA

```dockerfile
RUN conda install -y -c conda-forge \
    tensorflow-gpu=2.12 \
    && conda clean -afy
```

## Troubleshooting

### Issue: Package not found

**Diagnosis**:
```bash
# Search for package
docker run --rm continuumio/miniconda3 conda search -c conda-forge package-name
```

**Solution**:
- Try different channels
- Use pip as fallback
- Check package name spelling

### Issue: Dependency conflicts

**Diagnosis**:
```dockerfile
# Enable verbose output
RUN conda install --verbose -y package-name
```

**Solution**:
- Relax version constraints
- Install packages in separate layers
- Use `conda-forge` channel (better dependency resolution)

### Issue: Slow installation

**Causes**:
- Large package dependencies
- Slow mirror servers

**Solutions**:
```dockerfile
# Use faster mirrors (China region)
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
```

### Issue: Large image size

**Diagnosis**:
```bash
# Check layer sizes
docker history your-image:tag
```

**Solutions**:
- Multi-stage builds (advanced)
- Combine installations into one layer
- Aggressive cleanup with `conda clean -afy`
- Exclude unnecessary packages

## Testing Conda Installation

### Basic Test

```dockerfile
RUN python -c "import your_package; print(your_package.__version__)"
```

### Dependency Check

```dockerfile
RUN conda list | grep -E "numpy|pandas|torch"
```

### Import Test Script

```dockerfile
COPY tests/test_imports.py /tmp/test_imports.py
RUN python /tmp/test_imports.py && rm /tmp/test_imports.py
```

## Version Management

### Pinning Conda Version

```dockerfile
RUN conda install -y conda=23.1
```

### Lock File for Reproducibility

Generate lock file:

```bash
conda env export > environment.yml
```

Use in Dockerfile:

```dockerfile
COPY environment.yml .
RUN conda env create -f environment.yml && \
    conda clean -afy
```

## Security Best Practices

### Package Verification

```dockerfile
# Verify package signatures (if available)
RUN conda config --set safety_checks enabled
```

### Vulnerability Scanning

```bash
# Scan image for vulnerabilities
docker scan your-image:tag
```

### Regular Updates

```dockerfile
# Update conda base
RUN conda update -y conda && \
    conda clean -afy
```

## Performance Optimization

### Pre-built Environments

For frequently used environments:

1. Build base image with common packages
2. Tag and push to registry
3. Use as base for custom images

### Caching Strategy

Structure Dockerfile for maximum caching:

```dockerfile
# Layer 1: Rarely changes
RUN conda install -y -c conda-forge \
    numpy pandas scipy

# Layer 2: Occasionally changes
RUN conda install -y -c conda-forge \
    transformers datasets

# Layer 3: Frequently changes
RUN conda install -y -c conda-forge \
    your-custom-package
```

## Example Dockerfiles

### ML/AI Image

```dockerfile
FROM ubuntu:22.04

# Install Miniforge and create Python environments
# ... (system setup) ...

# Install ML packages in all environments
RUN for env in py310 py311 py312; do \
        conda install -n $env -c conda-forge -c pytorch \
            pytorch=2.0 \
            torchvision \
            transformers=4.30 \
            datasets \
            accelerate; \
    done && \
    conda clean -afy

# Set cache directories
ENV TRANSFORMERS_CACHE=/tmp/transformers
ENV HF_HOME=/tmp/huggingface
```

### Data Processing Image

```dockerfile
FROM ubuntu:22.04

# Install data processing packages in all environments
RUN for env in py310 py311 py312; do \
        conda install -n $env -c conda-forge \
            dask \
            polars \
            pyarrow \
            fastparquet; \
    done && \
    conda clean -afy

# Configure memory
ENV PYTHONMALLOC=malloc
```

### Web Scraping Image

```dockerfile
FROM ubuntu:22.04

# Install web scraping packages
RUN conda install -y -c conda-forge \
    requests \
    beautifulsoup4 \
    lxml \
    selenium \
    scrapy \
    && conda clean -afy

# Install browsers (if needed)
RUN apt-get update && \
    apt-get install -y firefox && \
    rm -rf /var/lib/apt/lists/*
```

## Summary Checklist

- [ ] Configure conda channels correctly
- [ ] Set channel priority to strict
- [ ] Pin package versions for reproducibility
- [ ] Install from appropriate channels
- [ ] Always run `conda clean -afy`
- [ ] Test package imports
- [ ] Check image size
- [ ] Document installed packages
- [ ] Version control Dockerfile