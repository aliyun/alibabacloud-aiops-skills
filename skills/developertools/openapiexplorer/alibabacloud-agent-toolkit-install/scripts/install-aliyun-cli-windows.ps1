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

Write-Output @"
..............888888888888888888888 ........=8888888888888888888D=..............
...........88888888888888888888888 ..........D8888888888888888888888I...........
.........,8888888888888ZI: ...........................=Z88D8888888888D..........
.........+88888888 ..........................................88888888D..........
.........+88888888 .......Welcome to use Alibaba Cloud.......O8888888D..........
.........+88888888 ............. ************* ..............O8888888D..........
.........+88888888 .... Command Line Interface(Reloaded) ....O8888888D..........
.........+88888888...........................................88888888D..........
..........D888888888888DO+. ..........................?ND888888888888D..........
...........O8888888888888888888888...........D8888888888888888888888=...........
............ .:D8888888888888888888.........78888888888888888888O ..............
"@

$OSArchitecture = (Get-WmiObject -Class Win32_OperatingSystem).OSArchitecture
$ProcessorArchitecture = [int](Get-WmiObject -Class Win32_Processor).Architecture

if (-not ($OSArchitecture -match "64") -or $ProcessorArchitecture -ne 9) {
    Write-ErrorExit "Alibaba Cloud CLI only supports Windows AMD64 systems. Please run on a compatible system."
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
