# Alibaba Cloud CLI Installation Guide

## macOS

**Homebrew (Recommended):**

```bash
brew install aliyun-cli
```

**Manual Installation:**

```bash
# Intel chip
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz
tar -xzf aliyun-cli-macosx-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Apple Silicon (M1/M2/M3/M4)
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-arm64.tgz
tar -xzf aliyun-cli-macosx-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/
```

## Linux

```bash
# x86_64
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# ARM64
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz
tar -xzf aliyun-cli-linux-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/
```

## Windows

1. Download: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract to any directory (e.g., `C:\aliyun-cli`)
3. The directory MUST be added to the system PATH environment variable

**PowerShell Installation:**

```powershell
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\aliyun-cli", [System.EnvironmentVariableTarget]::Machine)
```

## Verify Installation

After installation, the following command MUST be executed to confirm successful installation:

```bash
aliyun version
```

A version number in the output indicates successful installation. The version MUST be >= 3.0.299 to support OAuth authentication.

After installation, the CLI MUST be updated to the latest version:

```bash
# macOS (Homebrew)
brew upgrade aliyun-cli

# macOS (manual) / Linux: re-download the latest version and overwrite
# Intel Mac
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz
tar -xzf aliyun-cli-macosx-latest-amd64.tgz && sudo mv aliyun /usr/local/bin/

# Apple Silicon Mac
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-arm64.tgz
tar -xzf aliyun-cli-macosx-latest-arm64.tgz && sudo mv aliyun /usr/local/bin/

# Linux x86_64
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz && sudo mv aliyun /usr/local/bin/

# Linux ARM64
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz
tar -xzf aliyun-cli-linux-latest-arm64.tgz && sudo mv aliyun /usr/local/bin/

# Windows PowerShell
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli -Force
```

After updating, `aliyun version` MUST be executed again to confirm the version has been updated.

## Common Issues

**command not found:** You MUST verify that the directory containing `aliyun` has been added to PATH.

```bash
which aliyun    # macOS/Linux
where aliyun    # Windows
```

## Reference

- Official documentation: https://help.aliyun.com/zh/cli/install-cli
