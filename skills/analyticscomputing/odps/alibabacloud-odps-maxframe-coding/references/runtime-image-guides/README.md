# Custom Runtime Image Guides

Comprehensive guides for building custom MaxFrame DPE runtime images through conversational workflow.

## Guide Structure

### Core Guides

1. **[Base Image Selection](base-image-selection.md)** (60 lines)
   - Ubuntu 22.04 vs 24.04 comparison
   - Decision framework and recommendation matrix
   - Use case specific recommendations

2. **[Python Environment Strategy](python-environment-strategy.md)** (110 lines)
   - Multi-environment architecture
   - Version selection guidelines (3.7-3.12)
   - MF_PYTHON_EXECUTABLE configuration (CRITICAL)

3. **[Package Management](package-management.md)** (160 lines)
   - Conda vs pip decision guide
   - Mirror acceleration (China region)
   - Installation patterns and best practices
   - GPU package handling

4. **[GPU/CUDA Configuration](gpu-cuda-configuration.md)** (80 lines)
   - CUDA version compatibility matrix
   - Platform considerations
   - Complete GPU setup patterns
   - PyTorch with CUDA installation

5. **[System Dependencies](system-dependencies.md)** (90 lines)
   - Essential system packages
   - Locale and timezone configuration
   - Miniforge installation
   - ossfs2 installation

6. **[Environment Variables](environment-variables.md)** (50 lines)
   - Required environment variables
   - MF_PYTHON_EXECUTABLE (CRITICAL)
   - Optional custom variables

7. **[Image Optimization](image-optimization.md)** (100 lines)
   - Size reduction strategies
   - Build time optimization
   - .dockerignore patterns
   - Layer caching strategy

8. **[Dockerfile Templates](dockerfile-templates.md)** (160 lines)
   - 8 complete section templates
   - Header, base setup, conda, GPU, packages, environment, verification
   - Ready-to-use patterns

9. **[Common Scenarios](common-scenarios.md)** (110 lines)
   - Basic ML runtime (GPU)
   - Data processing runtime (CPU, multi-Python)
   - Minimal single-Python runtime

10. **[Testing and Validation](testing-validation.md)** (90 lines)
    - Health check commands
    - Environment verification
    - Package import tests
    - Integration tests

### Supplementary Guides

- **[Architecture Details](architecture-details.md)** (435 lines)
  - Building from scratch with public images
  - Miniforge vs Miniconda comparison
  - Python environment architecture
  - Resource considerations

- **[Conda Best Practices](conda-best-practices.md)** (476 lines)
  - Multi-environment strategy
  - Channel configuration
  - Package installation patterns
  - GPU package considerations

- **[Practical Guides](practical-guides.md)** (477 lines)
  - Conda distribution selection
  - GPU/CUDA support details
  - Common scenarios with detailed explanations
  - Best practices checklist

## Quick Navigation

**I want to...**

- Choose between Ubuntu 22.04 and 24.04 → [Base Image Selection](base-image-selection.md)
- Decide which Python versions to use → [Python Environment Strategy](python-environment-strategy.md)
- Install packages with conda or pip → [Package Management](package-management.md)
- Set up GPU/CUDA support → [GPU/CUDA Configuration](gpu-cuda-configuration.md)
- Optimize image size → [Image Optimization](image-optimization.md)
- Get ready-to-use Dockerfile sections → [Dockerfile Templates](dockerfile-templates.md)
- See example Dockerfiles → [Common Scenarios](common-scenarios.md)
- Test my custom image → [Testing and Validation](testing-validation.md)

## Conversational Workflow

All guides support the conversational workflow documented in **SKILL.md "Scenario 4: Create Custom Runtime Image"**.

The skill will:
1. Read these guides to understand best practices
2. Ask questions about your requirements
3. Guide decisions with explanations
4. Build Dockerfile section-by-section
5. Create support files and test instructions

## Related Resources

- **SKILL.md** - Main skill workflow
- **Examples** - `assets/examples/` - Working MaxFrame code examples
- **Operator Selection** - `references/operator-selector.md` - Finding MaxFrame operators

---

**All guides designed for the conversational approach - learn patterns, understand decisions, build confidently.**