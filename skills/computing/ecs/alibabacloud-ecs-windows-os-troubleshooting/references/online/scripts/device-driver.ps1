$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check Device Status and Error Codes ---
try {
    $allDevices = Get-CimInstance Win32_PnPEntity
    $errorDevices = $allDevices | Where-Object { $_.ConfigManagerErrorCode -ne 0 }
    Write-Host "Total PnP devices: $($allDevices.Count)"
    if ($errorDevices) {
        Write-Host "Found $($errorDevices.Count) devices with errors:"
        $errorDevices | Select-Object Name, DeviceID, ConfigManagerErrorCode, Status | Format-Table -AutoSize
    } else {
        Write-Host "All PnP devices are working properly (no error codes)"
    }
} catch {
    Write-Host ("ERROR step1 pnp-devices: " + $_.Exception.Message)
}

# --- Step 2: Check Driver Installation and Signing Status ---
try {
    $drivers = Get-WindowsDriver -Online | Where-Object { $_.Driver -like 'oem*' }
    if ($drivers) {
        Write-Host "Installed third-party drivers: $($drivers.Count)"
        $drivers | Select-Object Driver, OriginalFileName, ProviderName, Date, Version | Format-List
    } else {
        Write-Host "No third-party drivers found or Get-WindowsDriver not available"
    }
} catch {
    Write-Host ("ERROR step2 third-party-drivers: " + $_.Exception.Message)
}

try {
    $codeIntegrity = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CI' -Name 'UMCIAuditMode').UMCIAuditMode
    Write-Host "UMCI Audit Mode: $codeIntegrity"
} catch {
    Write-Host ("ERROR step2 umci-audit-mode: " + $_.Exception.Message)
}

try {
    $bcd = bcdedit /enum '{current}' 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 bcdedit: exit=$LASTEXITCODE $(($bcd | Out-String).Trim())" }
    $testSigning = $bcd | Select-String 'testsigning'
    if ($testSigning) {
        Write-Host "Test Signing: $testSigning"
    } else {
        Write-Host "Test Signing: Not enabled (normal)"
    }
} catch {
    Write-Host ("ERROR step2 test-signing: " + $_.Exception.Message)
}

# --- Step 3: Check Driver Version and Update Status ---
try {
    $driverServices = Get-CimInstance Win32_SystemDriver | Where-Object { $_.State -ne 'Running' -and $_.StartMode -ne 'Disabled' }
    if ($driverServices) {
        Write-Host "Non-running driver services (not disabled):"
        $driverServices | Select-Object Name, DisplayName, State, StartMode, PathName | Format-List
    } else {
        Write-Host "All expected driver services are running"
    }
} catch {
    Write-Host ("ERROR step3 driver-services: " + $_.Exception.Message)
}
