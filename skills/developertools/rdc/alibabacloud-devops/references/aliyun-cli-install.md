# Alibaba Cloud CLI Installation Guide

> Source: [如何安装、初始化配置和使用云效 CLI](https://help.aliyun.com/zh/yunxiao/developer-reference/how-to-install-initialize-and-use-the-apsara-devops-cli)

## 1. Installation by OS

### macOS

#### Method A: Homebrew (Recommended)

```bash
brew install aliyun-cli
```

> **Mirror for China mainland users** (optional): If network issues occur, configure Homebrew to use a mirror:
> ```bash
> export HOMEBREW_INSTALL_FROM_API=1
> export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.ustc.edu.cn/brew.git"
> export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.ustc.edu.cn/homebrew-core.git"
> export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"
> export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"
> brew update
> ```

#### Method B: Bash Script

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

Install a specific version:

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)" -- -V 3.3.5
```

#### Method C: PKG Installer (GUI)

Download: [aliyun-cli-latest.pkg](https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg)

Historical versions: [GitHub Releases](https://github.com/aliyun/aliyun-cli/releases) (package name format: `aliyun-cli-<version>.pkg`)

#### Method D: TGZ Archive

```bash
curl https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz -o aliyun-cli-macosx-latest-universal.tgz
tar xzvf aliyun-cli-macosx-latest-universal.tgz
sudo mv ./aliyun /usr/local/bin/
```

---

### Linux

#### Method A: Bash Script (Recommended)

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

Install a specific version:

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)" -- -V 3.3.18
```

#### Method B: TGZ Archive

**AMD64:**
```bash
curl https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz -o aliyun-cli-linux-latest.tgz
```

**ARM64:**
```bash
curl https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz -o aliyun-cli-linux-latest.tgz
```

Extract and install:
```bash
tar xzvf aliyun-cli-linux-latest.tgz
sudo mv ./aliyun /usr/local/bin/
```

---

### Windows

#### Method A: PowerShell Script

Create `Install-CLI-Windows.ps1` with the following content, then run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\Example\Install-CLI-Windows.ps1
```

Specify version and install directory:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\Example\Install-CLI-Windows.ps1 -Version 3.3.15 -InstallDir "C:\ExampleDir\AliyunCLI"
```

Default install directory: `C:\Users\<USERNAME>\AppData\Local\AliyunCLI`

<details>
<summary>Install-CLI-Windows.ps1 full script</summary>

```powershell
# Install-CLI-Windows.ps1
# Purpose: Install Alibaba Cloud CLI on Windows AMD64 systems.
# Supports custom version and install directory. Only modifies User-level and Process-level PATH.

[CmdletBinding()]
param (
    [string]$Version = "latest",
    [string]$InstallDir = "$env:LOCALAPPDATA",
    [switch]$Help
)

function Show-Usage {
    Write-Output @"

      Alibaba Cloud Command Line Interface Installer

    -Help                 Display this help and exit

    -Version VERSION      Custom CLI version. Default is 'latest'

    -InstallDir PATH      Custom installation directory. Default is:
                          $InstallDir\AliyunCLI

"@
}

function Write-ErrorExit {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

if ($PSBoundParameters['Help']) {
    Show-Usage
    exit 0
}

$OSArchitecture = (Get-WmiObject -Class Win32_OperatingSystem).OSArchitecture
$ProcessorArchitecture = [int](Get-WmiObject -Class Win32_Processor).Architecture

if (-not ($OSArchitecture -match "64") -or $ProcessorArchitecture -ne 9) {
    Write-ErrorExit "Alibaba Cloud CLI only supports Windows AMD64 systems."
}

$DownloadUrl = "https://aliyuncli.alicdn.com/aliyun-cli-windows-$Version-amd64.zip"

$tempPath = $env:TEMP
$randomName = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 8)
$DownloadDir = Join-Path -Path $tempPath -ChildPath $randomName
New-Item -ItemType Directory -Path $DownloadDir | Out-Null

try {
    $InstallDir = Join-Path $InstallDir "AliyunCLI"
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    $ZipPath = Join-Path $DownloadDir "aliyun-cli.zip"
    Start-BitsTransfer -Source $DownloadUrl -Destination $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath $DownloadDir -Force
    Move-Item -Path "$DownloadDir\aliyun.exe" -Destination "$InstallDir\" -Force

    $Key = 'HKCU:\Environment'
    $CurrentPath = (Get-ItemProperty -Path $Key -Name PATH).PATH

    if ([string]::IsNullOrEmpty($CurrentPath)) {
        $NewPath = $InstallDir
    } else {
        if ($CurrentPath -notlike "*$InstallDir*") {
            $NewPath = "$CurrentPath;$InstallDir"
        } else {
            $NewPath = $CurrentPath
        }
    }

    if ($NewPath -ne $CurrentPath) {
        Set-ItemProperty -Path $Key -Name PATH -Value $NewPath
        $env:PATH += ";$InstallDir"
    }
} catch {
    Write-ErrorExit "Failed to install Alibaba Cloud CLI: $_"
} finally {
    Remove-Item -Path $DownloadDir -Recurse -Force | Out-Null
}
```
</details>

#### Method B: GUI (ZIP Download)

1. Download: [aliyun-cli-windows-latest-amd64.zip](https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip)
2. Extract `aliyun.exe` to target directory (e.g., `C:\AliyunCLI`)
3. Add the directory to system PATH:
   - Open System Properties → Advanced → Environment Variables
   - Find `Path` in User/System variables → Edit → New → Add the installation directory

Historical versions: [GitHub Releases](https://github.com/aliyun/aliyun-cli/releases) (package name format: `aliyun-cli-windows-<version>-amd64.zip`)

---

## 2. Verify Installation

```bash
aliyun version
```

If the output shows a version number (e.g., `3.3.15`), the installation is successful.

## 3. Update CLI

- **Version 3.3.5+ (non-Homebrew):**
  ```bash
  aliyun upgrade
  ```
  Non-interactive:
  ```bash
  aliyun upgrade --yes
  ```

- **Bash script (Linux/macOS):** Re-run the installation command:
  ```bash
  /bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
  ```

- **Homebrew (macOS):**
  ```bash
  brew update && brew upgrade aliyun-cli && brew cleanup aliyun-cli
  ```

- **GUI/TGZ/PKG:** Download the latest package and reinstall to overwrite.

- **PowerShell (Windows):** Re-run the script with the same parameters:
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File C:\Example\Install-CLI-Windows.ps1
  ```

## 4. PATH Troubleshooting

If `aliyun version` returns "command not found" after installation:

1. **Close and reopen the terminal** — PATH often requires a new session to take effect.
2. Check current executable path:
   - Linux/macOS: `which aliyun`
   - Windows: `where aliyun`
3. If the command has no output, manually add the install directory to PATH:
   - Linux/macOS: `export PATH=$PATH:/usr/local/bin`
   - Windows: Add the installation directory to the `Path` environment variable via System Properties.

## 5. Uninstall

- **Homebrew (macOS):** `brew uninstall aliyun-cli`
- **Other methods (Linux/macOS):**
  ```bash
  which aliyun
  sudo rm -v $(which aliyun)
  ```
- **Windows (PowerShell install):**
  ```powershell
  $InstallDir = Join-Path $env:LOCALAPPDATA "AliyunCLI"
  Remove-Item -Path "$InstallDir\aliyun.exe" -Force
  ```
- **Windows (GUI install):** Navigate to the install directory and delete `aliyun.exe`. Optionally remove the directory from PATH.
- **Config cleanup (all OS):** Delete `~/.aliyun` (Linux/macOS) or `C:\Users\<USERNAME>\.aliyun` (Windows).
