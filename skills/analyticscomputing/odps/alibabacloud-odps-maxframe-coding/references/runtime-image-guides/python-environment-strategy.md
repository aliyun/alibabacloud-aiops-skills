# Python Environment Strategy

Configure Python environments for your custom MaxFrame DPE runtime image.

## Multi-Environment Architecture

The custom DPE runtime creates isolated conda environments for each Python version:

```
/py-runtime/                    # MINIFORGE_HOME
├── bin/                        # Conda executables
│   ├── conda
│   ├── pip
│   └── python -> ../envs/py311/bin/python
├── envs/                       # Conda environments
│   ├── py37/                   # Python 3.7 environment
│   │   └── bin/python3.7
│   ├── py38/                   # Python 3.8 environment
│   ├── py39/                   # Python 3.9 environment
│   ├── py310/                  # Python 3.10 environment
│   ├── py311/                  # Python 3.11 environment (recommended default)
│   └── py312/                  # Python 3.12 environment
└── pkgs/                       # Package cache
```

## Environment Naming Pattern

**Pattern:** `py<version>` (no dots)
- Python 3.7 → `py37`
- Python 3.8 → `py38`
- Python 3.9 → `py39`
- Python 3.10 → `py310`
- Python 3.11 → `py311`
- Python 3.12 → `py312`

## Version Selection Guidelines

**Python 3.7:**
- ✅ Wide package compatibility
- ⚠️ End of life (EOL): June 2023
- **Use only for legacy compatibility**

**Python 3.8:**
- ✅ Good package support
- ⚠️ EOL: October 2024
- Stable, but aging

**Python 3.9:**
- ✅ Excellent package support
- ✅ Stable and well-tested
- **Good balance for most use cases**

**Python 3.10:**
- ✅ Latest stable features
- ✅ Excellent package support
- **Good balance of features and stability**

**Python 3.11 (Recommended for production):**
- ✅ Significant performance improvements
- ✅ Excellent package support
- ✅ Modern, efficient
- **Best for production deployments**

**Python 3.12:**
- ✅ Latest Python features
- ⚠️ Some packages may not be available yet
- **Use for cutting-edge development**

## Size/Stability/Flexibility Trade-offs

| Configuration | Image Size | Flexibility | Build Time | Use Case |
|--------------|------------|-------------|------------|----------|
| **Single version (3.11)** | 0.8-1.2 GB | Minimal | 2-5 min | Production |
| **3 versions (3.10-3.12)** | 1.5-2.5 GB | Medium | 5-10 min | Development |
| **All versions (3.7-3.12)** | 3-5 GB | Maximum | 10-20 min | Testing/compatibility |

## MF_PYTHON_EXECUTABLE Pattern (CRITICAL)

**Why Critical:** MaxFrame uses this environment variable to detect the Python executable at runtime. Incorrect configuration will cause runtime failures.

**Pattern:**
```dockerfile
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/<env_name>/bin/python
```

**Path Structure:** `/py-runtime/envs/<env_name>/bin/python`

**Example:**
```dockerfile
# Default to Python 3.11
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python
```

**Default Selection Logic:**
1. If Python 3.11 is in selected versions → Use `py311` as default
2. Otherwise → Use highest selected version (e.g., `py312` if 3.12 is highest)

**Dockerfile Pattern:**
```dockerfile
# For Python 3.11 only
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python

# For multi-Python (3.10, 3.11, 3.12) - default to 3.11
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python
```

## Related Guides

- **[Package Management](package-management.md)** - Installing packages in environments
- **[Environment Variables](environment-variables.md)** - All environment variable patterns
- **[Dockerfile Templates](dockerfile-templates.md)** - Environment creation templates

---

**Part of [Custom Runtime Image Guides](README.md)**