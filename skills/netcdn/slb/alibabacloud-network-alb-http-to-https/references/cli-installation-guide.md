# Aliyun CLI Installation Guide

Install or upgrade Aliyun CLI to a version that supports automatic product plugin installation.

> **Aliyun CLI 3.3.1+**: Use version `3.3.1` or later so published product plugins can be installed automatically when needed.

## Installation

### macOS

**Using Homebrew (Recommended)**

```bash
brew install aliyun-cli
brew upgrade aliyun-cli
aliyun version
```

**Using Binary**

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz
tar -xzf aliyun-cli-macosx-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/
aliyun version
```

### Linux

**x86_64**

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/
aliyun version
```

**ARM64**

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz
tar -xzf aliyun-cli-linux-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/
aliyun version
```

### Windows

**Using Binary**

1. Download `https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip`.
2. Extract the ZIP file.
3. Add the extracted directory to `PATH`.
4. Open a new Command Prompt or PowerShell window.
5. Run `aliyun version`.

**Using PowerShell**

```powershell
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli
$env:Path += ";C:\aliyun-cli"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)
aliyun version
```

## After Installation

1. Confirm `aliyun version` reports `>= 3.3.1`.
2. Return to the calling skill and follow its `Authentication` section for credential checks.
3. Run `aliyun configure set --auto-plugin-install true` if the calling skill requires automatic product plugin installation.

## Notes

- This reference covers CLI installation and upgrade only.
- Do not use this document as a credential setup guide inside an agent session.
- Follow the calling skill's security rules for authentication and secret handling.
