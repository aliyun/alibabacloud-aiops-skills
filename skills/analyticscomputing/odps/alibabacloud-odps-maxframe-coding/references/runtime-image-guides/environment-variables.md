# Environment Variables

Configure environment variables for your custom MaxFrame DPE runtime image.

## Required Environment Variables

```dockerfile
# System configuration
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LC_CTYPE=en_US.UTF-8
ENV TZ="Asia/Shanghai"
ENV TERM=xterm-256color

# Miniforge/Conda paths
ENV MINIFORGE_HOME="/py-runtime"
ENV PATH="${MINIFORGE_HOME}/bin:${PATH}"

# CRITICAL: MaxFrame Python executable detection
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python
```

## MF_PYTHON_EXECUTABLE (CRITICAL)

**Purpose:** MaxFrame uses this variable to locate Python interpreter for job execution.

**Pattern:** `/py-runtime/envs/<env_name>/bin/python`

**Must point to:** Conda environment's Python executable, NOT system Python

**Incorrect paths will cause:** Runtime failures

## Optional Custom Variables

```dockerfile
# Hugging Face cache directories
ENV TRANSFORMERS_CACHE=/tmp/transformers
ENV HF_HOME=/tmp/huggingface

# Python memory allocator
ENV PYTHONMALLOC=malloc

# Conda configuration
ENV CONDA_AUTO_UPDATE_CONDA=false
```

## Related Guides

- **[Python Environment Strategy](python-environment-strategy.md)** - MF_PYTHON_EXECUTABLE details
- **[Dockerfile Templates](dockerfile-templates.md)** - Environment configuration template

---

**Part of [Custom Runtime Image Guides](README.md)**