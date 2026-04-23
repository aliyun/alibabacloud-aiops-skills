# Base Image Selection

Choose the right Ubuntu version for your custom MaxFrame DPE runtime image.

## Ubuntu 22.04 vs 24.04 Comparison

| Feature | Ubuntu 22.04 | Ubuntu 24.04 |
|---------|--------------|--------------|
| **CUDA Support** | ✅ Excellent (12.4, 12.1, 11.8) | ⚠️ Limited testing |
| **Package Stability** | ✅ Very stable, LTS until 2027 | 🔄 Newer packages, LTS until 2029 |
| **ML Libraries** | ✅ Fully tested (PyTorch, TensorFlow) | ⚠️ Some incompatibilities possible |
| **Production Ready** | ✅ Yes, battle-tested | ⚠️ Emerging adoption |
| **Best For** | GPU/ML workloads, production | Modern development, non-GPU |

## Decision Framework

**Choose Ubuntu 22.04 when:**
- GPU/CUDA support needed (ML, deep learning)
- Production deployments requiring maximum stability
- Using PyTorch, TensorFlow, or other ML frameworks
- Need battle-tested, widely-validated environment

**Choose Ubuntu 24.04 when:**
- Latest system packages required
- Modern Python development (3.12 integration)
- Non-GPU workloads
- Want newest LTS with longer support window

## Recommendation Matrix

| Use Case | Recommended Base | Reason |
|----------|------------------|---------|
| ML/AI with GPU | Ubuntu 22.04 | Best CUDA compatibility |
| ML/AI CPU-only | Ubuntu 22.04 | Stable ML libraries |
| Data processing | Ubuntu 22.04 or 24.04 | Either works well |
| Modern Python dev | Ubuntu 24.04 | Latest packages |
| Production critical | Ubuntu 22.04 | Maximum stability |

## Dockerfile Pattern

```dockerfile
# Ubuntu 22.04 (for GPU/ML)
FROM ubuntu:22.04

# OR Ubuntu 24.04 (for modern development)
FROM ubuntu:24.04
```

## Related Guides

- **[GPU/CUDA Configuration](gpu-cuda-configuration.md)** - GPU setup requires Ubuntu 22.04
- **[Dockerfile Templates](dockerfile-templates.md)** - Ready-to-use templates
- **[Common Scenarios](common-scenarios.md)** - Example Dockerfiles by use case

---

**Part of [Custom Runtime Image Guides](README.md)**