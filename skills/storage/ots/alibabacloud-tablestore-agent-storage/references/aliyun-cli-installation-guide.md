# Alibaba Cloud CLI Installation Guide

Official documentation: https://help.aliyun.com/zh/cli/

> **Version requirement:** Alibaba Cloud CLI version must be >= 3.3.1 to use plugin mode.

---

## Installation

### Linux

**Method 1: One-click Bash script installation (recommended)**

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

Install a specific historical version:

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)" -- -V 3.0.277
```

**Method 2: TGZ installation package**

```bash
# AMD64
curl https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz -o aliyun-cli-linux-latest.tgz

# ARM64
curl https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz -o aliyun-cli-linux-latest.tgz

# Extract and install
tar xzvf aliyun-cli-linux-latest.tgz
sudo mv ./aliyun /usr/local/bin/
```

---

### macOS

**Method 1: PKG installation package (recommended)**

Open the following link in your browser to download and double-click to install:

```
https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg
```

**Method 2: Homebrew**

```bash
brew install aliyun-cli
```

Users in mainland China who encounter network issues can first switch to Homebrew mirror sources:

```bash
export HOMEBREW_INSTALL_FROM_API=1
export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.ustc.edu.cn/brew.git"
export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.ustc.edu.cn/homebrew-core.git"
export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"
export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"
brew update
brew install aliyun-cli
```

**Method 3: One-click Bash script installation**

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

**Method 4: TGZ installation package**

```bash
curl https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz -o aliyun-cli-macosx-latest-universal.tgz
tar xzvf aliyun-cli-macosx-latest-universal.tgz
sudo mv ./aliyun /usr/local/bin
```

---

### Windows

**Method 1: GUI installation**

Visit the [GitHub Release page](https://github.com/aliyun/aliyun-cli/releases) to download the latest `.exe` installer, then double-click to run and follow the prompts to install.

**Method 2: PowerShell script**

```powershell
# Download and install (using AMD64 as an example)
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
Expand-Archive -Path "aliyun-cli.zip" -DestinationPath "C:\aliyun-cli"
# Add C:\aliyun-cli to the system PATH environment variable
```

---

## Verify Installation

```bash
aliyun version
```

If a version number is output (e.g., `3.0.277`), the installation is successful. Confirm that the version is >= 3.3.1.

---

## Enable Automatic Plugin Installation

```bash
aliyun configure set --auto-plugin-install true
```

---

## Configure Credentials

```bash
aliyun configure
```

Follow the prompts to enter:
- `Access Key Id`
- `Access Key Secret`
- `Default Region Id` (e.g., `cn-hangzhou`)
- `Default Language` (`zh` or `en`)

### Supported Authentication Modes

| Mode | Description | Configure Command |
|------|-------------|-------------------|
| AK | AccessKey ID/Secret (default) | `aliyun configure --mode AK` |
| RamRoleArn | RAM role assumption | `aliyun configure --mode RamRoleArn` |
| EcsRamRole | ECS instance role | `aliyun configure --mode EcsRamRole` |
| OIDC | OIDC role assumption | `aliyun configure --mode OIDC` |

**View current credential configuration:**

```bash
aliyun configure list
```

> **Security rules:**
> - Do not use `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` or similar methods to print AK/SK
> - Do not pass plaintext AK/SK directly in command line
> - Only use `aliyun configure list` to check credential status

---

## Update CLI

```bash
# Linux / macOS (installed via Bash script)
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"

# macOS (installed via Homebrew)
brew upgrade aliyun-cli
```

---

## References

- Official documentation: https://help.aliyun.com/zh/cli/
- GitHub: https://github.com/aliyun/aliyun-cli
- Linux installation: https://help.aliyun.com/zh/cli/install-cli-on-linux
- macOS installation: https://help.aliyun.com/zh/cli/install-cli-on-macos
- Windows installation: https://help.aliyun.com/zh/cli/install-cli-on-windows
