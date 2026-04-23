# Testing and Validation

Validate your custom MaxFrame DPE runtime image.

## Health Check Commands

**Test basic Python:**
```bash
docker run --rm <image> conda run -n py311 python --version
# Expected: Python 3.11.x
```

**Test GPU availability:**
```bash
docker run --rm --gpus all <image> python -c "import torch; print(torch.cuda.is_available())"
# Expected: True
```

**Test package import:**
```bash
docker run --rm <image> conda run -n py311 python -c "import transformers; print(transformers.__version__)"
# Expected: Version number
```

## Environment Verification

**List all environments:**
```bash
docker run --rm <image> conda env list
```

**Check Python in each environment:**
```bash
docker run --rm <image> bash -c "for env in py310 py311 py312; do echo $env:; conda run -n $env python --version; done"
```

## Package Import Tests

**Test multiple packages:**
```bash
docker run --rm <image> conda run -n py311 python -c "
import sys
packages = ['transformers', 'torch', 'pandas']
for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        print(f'{pkg}: {version}')
    except ImportError as e:
        print(f'{pkg}: FAILED - {e}')
"
```

## Integration Test with MaxFrame

```python
# test_maxframe.py
from maxframe.session import new_session
import maxframe.dataframe as md

session = new_session(image="your-image:v1")

# Test basic operation
df = md.read_odps_table("test_table")
print(df.head())

session.destroy()
```

## Image Size Check

```bash
docker images <image:tag>
# Expected sizes:
# - Single Python: 0.8-1.2 GB
# - 3 Pythons: 1.5-2.5 GB
# - All Pythons: 3-5 GB
```

## Summary Checklist

Before deploying, verify:

- [ ] Python version correct
- [ ] All packages importable
- [ ] MF_PYTHON_EXECUTABLE correctly set
- [ ] GPU available (if GPU image)
- [ ] Image size reasonable
- [ ] Integration test passes

## Related Guides

- **[Dockerfile Templates](dockerfile-templates.md)** - Template 8 includes verification
- **[Common Scenarios](common-scenarios.md)** - Examples include verification steps

---

**Part of [Custom Runtime Image Guides](README.md)**