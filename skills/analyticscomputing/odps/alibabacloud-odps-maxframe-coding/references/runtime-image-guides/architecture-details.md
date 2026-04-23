# Base DPE Runtime Image Details

> **For workflow guidance:** See [README.md](README.md) for the recommended conversational workflow and decision frameworks. This file provides supplemental architecture details about the base DPE runtime.

## Building from Scratch (Public Images)

### Why Build from Scratch?

The custom DPE runtime skill builds images from scratch using public images for the following reasons:

- **No dependency on internal registries** - No need for alibaba-inc registry access
- **Full control over base image** - Customize every layer
- **Public and accessible to all users** - Anyone can build without special permissions
- **Reproducible builds** - Same Dockerfile produces same results anywhere

### Base Components

1. **Ubuntu 22.04** - Public base OS
   - LTS release with long-term support
   - Stable package repository
   - Wide compatibility

2. **Miniforge** - Conda-forge distribution (preferred over Miniconda)
   - Uses conda-forge channel by default
   - Community-driven, open-source
   - Smaller footprint than Miniconda
   - No Anaconda repository needed

3. **System Utilities** - Essential tools
   - vim, curl, wget, jq, dnsutils
   - build-essential for compiling packages
   - ca-certificates, locales
   - ffmpeg for media processing

4. **MaxFrame SDK** - Automatically verified and installed
   - `maxframe>=2.0.0`
   - `pyodps` - MaxCompute Python SDK

5. **User Packages** - Installed in all Python environments via conda

## Miniforge vs Miniconda

### Why Miniforge?

**Miniforge** (our choice):
- ✅ Uses conda-forge channel by default
- ✅ Community-driven, open-source
- ✅ Smaller initial footprint
- ✅ No Anaconda repository configuration needed
- ✅ Better for conda-forge-first installations

**Miniconda**:
- ❌ Uses Anaconda defaults by default
- ❌ Requires manual channel configuration
- ❌ Larger initial size
- ❌ Anaconda terms of service considerations

## Python Environments Architecture

### Multi-Environment Setup

The custom DPE runtime creates **isolated conda environments** for each selected Python version, matching the official DPE runtime pattern:

```
/py-runtime/                    # MINIFORGE_HOME
├── bin/                        # Conda executables
│   ├── conda
│   ├── pip
│   └── python -> ../envs/py310/bin/python
├── envs/                       # Conda environments
│   ├── py37/                   # Python 3.7 environment
│   │   ├── bin/
│   │   │   ├── python -> python3.7
│   │   │   └── pip
│   │   └── lib/python3.7/site-packages/
│   ├── py38/                   # Python 3.8 environment
│   ├── py39/                   # Python 3.9 environment
│   ├── py310/                  # Python 3.10 environment (default)
│   ├── py311/                  # Python 3.11 environment
│   └── py312/                  # Python 3.12 environment
└── pkgs/                       # Package cache
```

#### Default Environment

The default environment is set via `CONDA_DEFAULT_ENV` environment variable, typically the **highest selected Python version** (e.g., `py312` if all versions selected).

**CRITICAL: MF_PYTHON_EXECUTABLE Environment Variable**

MaxFrame enforces the `MF_PYTHON_EXECUTABLE` environment variable to detect the Python executable at runtime. This **MUST** be configured correctly:

```dockerfile
ENV CONDA_DEFAULT_ENV=py311
ENV MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python
```

**Path pattern:**
```
/py-runtime/envs/<env_name>/bin/python
```

**Why this is critical:**
- MaxFrame uses this variable to locate the Python interpreter for job execution
- Incorrect path will cause runtime failures
- Must point to the conda environment's Python executable, not system Python

**Default selection logic:**
1. If Python 3.11 is in selected versions → `MF_PYTHON_EXECUTABLE=/py-runtime/envs/py311/bin/python`
2. Otherwise → Uses highest selected version

### Default Environment

Each environment is named `py<version>`:
- Python 3.7 → `py37`
- Python 3.8 → `py38`
- Python 3.9 → `py39`
- Python 3.10 → `py310` (typically default)
- Python 3.11 → `py311`
- Python 3.12 → `py312`

### Default Environment

The default environment is set via `CONDA_DEFAULT_ENV` environment variable, typically the **highest selected Python version** (e.g., `py312` if all versions selected).

**How to use different environments:**

```bash
# Default environment
docker run --rm image:tag python script.py

# Specific environment
docker run --rm image:tag conda run -n py39 python script.py

# Interactive shell in specific environment
docker run -it image:tag conda run -n py310 bash
```

## Installation Strategy

### System-Level vs Conda Packages

**System-level (via apt-get):**
- Build tools (build-essential, gcc, etc.)
- System utilities (vim, curl, wget, jq)
- Libraries with system dependencies (ffmpeg)
- Locale and timezone configuration

**Conda packages (in each environment):**
- Python interpreter
- Python packages (user-requested + MaxFrame SDK)
- Conda-managed libraries

This separation ensures:
- Stable base system
- Isolated Python environments
- Proper dependency management
- Reproducible builds

### MaxFrame SDK Installation

**Note:** MaxFrame SDK and pyodps are **NOT required** in the custom runtime image.

These packages are installed at the **client side** (where MaxFrame code is developed and executed), not in the DPE runtime service. The custom runtime image runs on the MaxCompute cluster and only needs user-specific dependencies for your processing logic.

**Architecture:**
- **Client side**: MaxFrame SDK + pyodps installed (where you write and submit code)
- **DPE runtime (cluster)**: No MaxFrame SDK needed - executes submitted code
- **Custom image**: Only user packages (transformers, pandas, numpy, etc.)

**Why NOT install in custom runtime?**
- MaxFrame SDK is a client-side library for code development
- DPE runtime only needs user-specific dependencies for data processing
- Installing SDK in runtime duplicates packages and increases image size
- Focus on packages required by your processing logic only

## Resource Considerations

### Image Size

| Configuration | Approximate Size |
|--------------|------------------|
| All versions (3.7-3.12) | 3-5 GB |
| 3 versions (e.g., 3.10-3.12) | 1.5-2.5 GB |
| Single version (e.g., 3.10) | 0.8-1.2 GB |

**Size reduction strategies:**
- Select only needed Python versions
- Use `conda clean -afy` to remove cache
- Avoid unnecessary packages
- Use multi-stage builds (advanced)

### Build Time

| Configuration | Approximate Build Time |
|--------------|------------------------|
| All versions (3.7-3.12) | 10-20 minutes |
| 3 versions | 5-10 minutes |
| Single version | 2-5 minutes |

**Factors affecting build time:**
- Number of Python environments
- Number and size of user packages
- Network speed (conda package download)
- CPU and disk I/O

### Runtime Memory

Each Python environment is independent. When a job runs:
- Only one environment is active
- Memory usage depends on the packages in that environment
- No overhead from other environments

## Version Compatibility

### Python Version Selection

**Python 3.7**:
- ✅ Wide package compatibility
- ⚠️ End of life (EOL): June 2023
- Use only for legacy compatibility

**Python 3.8**:
- ✅ Good package support
- ⚠️ EOL: October 2024
- Stable, but aging

**Python 3.9**:
- ✅ Excellent package support
- ✅ Stable and well-tested
- Good balance for most use cases

**Python 3.10** (recommended default):
- ✅ Latest stable features
- ✅ Excellent package support
- Good balance of features and stability

**Python 3.11**:
- ✅ Significant performance improvements
- ✅ Good package support
- Modern, efficient

**Python 3.12**:
- ✅ Latest Python features
- ⚠️ Some packages may not be available yet
- Use for cutting-edge development

### Package Version Compatibility

When specifying package versions:
- Check conda-forge availability for all selected Python versions
- Test compatibility across versions
- Consider using version ranges instead of pinned versions

**Example:**
```bash
# Good: flexible version range
--packages "pandas>=1.5,<2.0" "numpy>=1.23"

# May cause issues: too specific
--packages "pandas==1.5.3" "numpy==1.23.5"
```

## Security Considerations

### What NOT to Include

- ❌ Hardcoded credentials
- ❌ Private SSH keys
- ❌ Internal network configurations
- ❌ Proprietary data files
- ❌ Personal access tokens

### What IS Safe to Include

- ✅ Public certificates (if needed)
- ✅ Configuration templates
- ✅ Documentation for required secrets
- ✅ Publicly available packages

### Runtime Secrets

Pass sensitive information via:
- Environment variables (from MaxCompute)
- OSS configuration (from MaxCompute)
- MaxFrame session parameters
- Docker secrets (orchestration platforms)

**Example:**
```bash
docker run -e ODPS_ACCESS_KEY_ID=$ODPS_ACCESS_KEY_ID \
           -e ODPS_ACCESS_KEY_SECRET=$ODPS_ACCESS_KEY_SECRET \
           image:tag
```

## Updates and Maintenance

### Base Image Updates

When Ubuntu or Miniforge releases updates:

1. **Pull new base image**:
   ```bash
   docker pull ubuntu:22.04
   ```

2. **Rebuild custom image**:
   ```bash
   docker build --no-cache -t image:tag .
   ```

3. **Test thoroughly**:
   - Run test scripts
   - Verify all packages
   - Check MaxFrame functionality

4. **Update version tag**:
   ```bash
   docker tag image:tag image:v2
   ```

### Package Updates

To update user packages:

1. **Use conversational workflow**:
   - Follow the workflow in SKILL.md "Scenario 4: Create Custom Runtime Image"
   - Specify updated package versions during package collection step

2. **Rebuild and test**

3. **Deploy new version**

### Conda Environment Updates

To update packages in specific environments:

```bash
# Update in one environment
docker run --rm image:tag conda run -n py310 conda update package-name

# Rebuild with updated environment
docker commit container-id image:tag
```

## Common Issues and Solutions

### Issue: Import conflicts between environments

**Cause**: Different package versions in different environments

**Solution**: Ensure consistent package installation across all selected environments (script handles this automatically)

### Issue: Permission denied when installing packages

**Cause**: Trying to modify system packages

**Solution**: Install in conda environments only (script handles this)

### Issue: Missing system libraries

**Cause**: Python packages require system dependencies

**Solution**: Add to apt-get install list in Dockerfile:
```dockerfile
RUN apt-get update && \
    apt-get install -y libgl1-mesa-glx libglib2.0-0
```

### Issue: Large image size

**Cause**: Too many Python versions or packages

**Solution**:
- Select only needed Python versions
- Remove unnecessary packages
- Use `conda clean -afy`
- Consider multi-stage builds

## Testing Custom Images

### Basic Health Check

```bash
docker run --rm image:tag conda run -n py310 python -c "
import sys
print(f'Python: {sys.version}')
import maxframe
print(f'MaxFrame: {maxframe.__version__}')
"
```

### Environment Verification

```bash
# List all environments
docker run --rm image:tag conda env list

# Test each environment
for env in py37 py38 py39 py310 py311 py312; do
    echo "Testing $env..."
    docker run --rm image:tag conda run -n $env python --version
done
```

### Package Import Test

```bash
docker run --rm image:tag conda run -n py310 python -c "
import your_package
print(f'Package version: {your_package.__version__}')
"
```

### Integration Test

```python
# test_maxframe.py
from maxframe.session import new_session
import maxframe.dataframe as md

session = new_session(image="image:tag")
df = md.read_odps_table("test_table")
print(df.head())
session.destroy()
```

## Summary

The custom DPE runtime uses:
- **Public base image**: Ubuntu 22.04
- **Miniforge**: Better conda-forge integration
- **Multi-environment**: Python 3.7-3.12 (user selectable)
- **System separation**: System packages vs conda packages
- **Client-side SDK**: MaxFrame SDK installed at client, not in runtime image

This architecture provides flexibility, isolation, and compatibility while remaining fully accessible to all users without special registry access.