$ProgressPreference = 'SilentlyContinue'

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: CBS Service and Pending State Check ---
try {
    Get-Service -Name @('TrustedInstaller','msiserver','BITS','CryptSvc') |
      Select-Object Name, DisplayName, Status, StartType |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 cbs-services: " + $_.Exception.Message)
}
try {
    # RebootPending/RebootRequired values are optional (absence = no pending reboot);
    # read the whole key once and access properties, which are null when absent.
    $cbsKey = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing'
    $cbsProps = Get-ItemProperty -Path $cbsKey
    [PSCustomObject]@{
      RebootPending   = $cbsProps.RebootPending
      RebootRequired  = $cbsProps.RebootRequired
    } | Format-List
} catch {
    Write-Host ("ERROR step1 cbs-reboot-flags: " + $_.Exception.Message)
}
try {
    $cbsKey = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing'
    $pendingPkgs = Get-ChildItem "$cbsKey\PackagesPending"
    Write-Output "CBS PackagesPending count: $(if ($pendingPkgs) { $pendingPkgs.Count } else { 0 })"
} catch {
    # PackagesPending subkey absent simply means nothing is pending
    Write-Output "CBS PackagesPending count: 0 (key not present: $($_.Exception.Message))"
}

# --- Step 2: CBS.log Error Analysis ---
try {
    $cbsLog = "$env:SystemRoot\Logs\CBS\CBS.log"
    if (Test-Path $cbsLog) {
      Select-String -Path $cbsLog -Pattern 'Failed|Corruption|Duplicate object|0x800f0|0x80073712' |
        Select-Object -Last 50 LineNumber, Line |
        Format-List
    } else { Write-Output 'CBS.log not found' }
} catch {
    Write-Host ("ERROR step2 cbs-log-scan: " + $_.Exception.Message)
}

# --- Step 3: DISM.log Error Analysis ---
try {
    $dismLog = "$env:SystemRoot\Logs\DISM\dism.log"
    if (Test-Path $dismLog) {
      Select-String -Path $dismLog -Pattern 'HRESULT|OpenPackage failed|EnableFeature failed|Error' |
        Select-Object -Last 30 LineNumber, Line |
        Format-List
    } else { Write-Output 'dism.log not found' }
} catch {
    Write-Host ("ERROR step3 dism-log-scan: " + $_.Exception.Message)
}

# --- Step 4: Feature and Package Installation Status Check ---
try {
    # Windows features not in Installed/Enabled state (Server: Get-WindowsFeature; Client: Get-WindowsOptionalFeature)
    $hasFeatureCmd = $false
    try { $null = Get-Command Get-WindowsFeature; $hasFeatureCmd = $true } catch { }
    if ($hasFeatureCmd) {
      Get-WindowsFeature |
        Where-Object { $_.InstallState -ne 'Installed' } |
        Select-Object Name, InstallState |
        Format-Table -AutoSize
    } else {
      Get-WindowsOptionalFeature -Online |
        Where-Object { $_.State -ne 'Enabled' -and $_.State -ne 'Disabled' } |
        Select-Object FeatureName, State |
        Format-Table -AutoSize
    }
} catch {
    Write-Host ("ERROR step4 feature-state: " + $_.Exception.Message)
}
try {
    $dismPkgs = DISM /Online /Get-Packages /Format:Table 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step4 dism-get-packages: exit=$LASTEXITCODE $(($dismPkgs | Out-String).Trim())" }
    $dismPkgs | Select-String -Pattern 'Install Pending|Resolving Pending|Staged|No packages found'
} catch {
    Write-Host ("ERROR step4 dism-get-packages: " + $_.Exception.Message)
}
try {
    # CBS package metadata database integrity (empty on both signals CbsPackageDatabaseLost)
    Write-Output "Get-Hotfix count: $((Get-Hotfix | Measure-Object).Count)"
} catch {
    Write-Host ("ERROR step4 get-hotfix: " + $_.Exception.Message)
}
try {
    Write-Output "Servicing\Packages entries: $((Get-ChildItem "$env:SystemRoot\Servicing\Packages" | Measure-Object).Count)"
} catch {
    Write-Host ("ERROR step4 servicing-packages-dir: " + $_.Exception.Message)
}

# --- Step 5: Component Store Health Check ---
try {
    $checkHealth = DISM /Online /Cleanup-Image /CheckHealth 2>&1
    Write-Output "DISM CheckHealth exit code: $LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step5 dism-checkhealth: exit=$LASTEXITCODE $(($checkHealth | Out-String).Trim())" }
    $checkHealth
} catch {
    Write-Host ("ERROR step5 dism-checkhealth: " + $_.Exception.Message)
}
