# System Dependencies

Install essential system packages and configure the base system.

## Essential System Packages

```dockerfile
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    wget \
    curl \
    vim \
    ca-certificates \
    locales \
    build-essential \
    jq \
    dnsutils \
    ffmpeg \
    tzdata \
    strace \
    gdb && \
    rm -rf /var/lib/apt/lists/*
```

**Package Purposes:**
- `wget`, `curl` - Download tools
- `vim` - Text editor
- `ca-certificates` - SSL certificates
- `locales` - Locale support
- `build-essential` - Compilation tools (gcc, make, etc.)
- `jq` - JSON processor
- `dnsutils` - DNS utilities
- `ffmpeg` - Media processing
- `tzdata` - Timezone data
- `strace`, `gdb` - Debugging tools

## Locale and Timezone Configuration

```dockerfile
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LC_CTYPE=en_US.UTF-8
ENV TZ="Asia/Shanghai"
ENV TERM=xterm-256color

RUN locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8
```

## Miniforge Installation Pattern

```dockerfile
ENV MINIFORGE_HOME="/py-runtime"
ENV PATH="${MINIFORGE_HOME}/bin:${PATH}"

RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O miniforge.sh && \
    bash miniforge.sh -b -p ${MINIFORGE_HOME} && \
    rm -rf miniforge.sh
```

**Why Miniforge:**
- Conda-forge distribution (no Anaconda repo needed)
- Smaller footprint than Miniconda
- BSD-3-Clause license (unrestricted commercial use)

## ossfs2 Installation Pattern

```dockerfile
# Install ossfs2 for OSS filesystem mounting (x86_64 only)
RUN ARCH=$(echo ${TARGETARCH:-amd64} | sed 's/amd64/x86_64/' | sed 's/arm64/aarch64/') && \
    if [ "$ARCH" = "x86_64" ]; then \
        wget -O ossfs2_2.0.3.1_linux_x86_64.deb "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20260123/ynfgkj/ossfs2_2.0.3.1_linux_x86_64.deb?spm=a2c4g.11186623.0.0.82ac640fdy2HPL&file=ossfs2_2.0.3.1_linux_x86_64.deb" && \
        dpkg -i ossfs2_2.0.3.1_linux_x86_64.deb && \
        ossfs2 --version && \
        rm -rf ossfs2_2.0.3.1_linux_x86_64.deb; \
    else \
        echo "Warning: ossfs2 official packages not available for $ARCH"; \
    fi
```

**Note:** ossfs2 only available for x86_64. For aarch64, users need to build from source.

## Related Guides

- **[Package Management](package-management.md)** - Installing Python packages
- **[Dockerfile Templates](dockerfile-templates.md)** - Complete base setup template

---

**Part of [Custom Runtime Image Guides](README.md)**