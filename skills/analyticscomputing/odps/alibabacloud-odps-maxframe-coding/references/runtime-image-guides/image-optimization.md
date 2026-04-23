# Image Optimization

Optimize your custom MaxFrame DPE runtime image for size and build speed.

## Size Reduction Strategies

**1. Select Only Needed Python Versions**
- Single version: 0.8-1.2 GB
- 3 versions: 1.5-2.5 GB
- All versions: 3-5 GB

**2. Conda Clean Pattern**
```dockerfile
RUN conda clean -afy
```
Removes:
- Package tarballs (200-500 MB)
- Index cache (10-50 MB)
- Lock files (<1 MB)

**3. Apt Clean Pattern**
```dockerfile
RUN apt-get update && apt-get install -y packages && \
    rm -rf /var/lib/apt/lists/*
```

**4. Multi-Stage Builds (Advanced)**
```dockerfile
# Stage 1: Build
FROM ubuntu:22.04 AS builder
# ... installation steps ...

# Stage 2: Runtime
FROM ubuntu:22.04
COPY --from=builder /py-runtime /py-runtime
```

## .dockerignore Patterns

Create `.dockerignore` file:
```
# Git
.git
.gitignore

# Documentation
*.md
docs/

# Python
__pycache__
*.pyc
*.pyo
.pytest_cache/

# Virtual environments
venv/
env/

# IDE
.vscode/
.idea/

# Build artifacts
dist/
build/

# Credentials
.env
*.pem
*.key
```

## Build Time Optimization

**Layer Caching Strategy:**
```dockerfile
# Layer 1: Rarely changes (system packages)
RUN apt-get update && apt-get install -y \
    wget curl vim build-essential

# Layer 2: Rarely changes (Miniforge)
RUN wget ... && bash miniforge.sh ...

# Layer 3: Occasionally changes (Python environments)
RUN conda create -n py311 python=3.11

# Layer 4: Frequently changes (user packages)
RUN conda install -n py311 your-packages
```

## Related Guides

- **[Python Environment Strategy](python-environment-strategy.md)** - Version selection impacts size
- **[Package Management](package-management.md)** - Package cleanup patterns

---

**Part of [Custom Runtime Image Guides](README.md)**