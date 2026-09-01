$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Group Policy Application Status Check ---
try {
    $gpr = gpresult /r /scope:computer 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step1 gpresult: exit=$LASTEXITCODE $(($gpr | Out-String).Trim())" }
    $gpr
} catch {
    Write-Host ("ERROR step1 gpresult: " + $_.Exception.Message)
}

try {
    # Filter ProviderName/Level in FilterHashtable directly: pulling the latest N entries
    # of the whole System log and filtering afterwards almost always returns nothing
    # (System log is high-volume; GroupPolicy events are sparse).
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-GroupPolicy'; Level=1,2,3} -MaxEvents 20 |
      Select-Object TimeCreated, Id, LevelDisplayName, Message |
      Format-Table -AutoSize -Wrap
} catch {
    Write-Host ("ERROR step1 grouppolicy-events: " + $_.Exception.Message)
}

# --- Step 2: AppLocker/Software Restriction Policy Check ---
try {
    Get-WinEvent -LogName 'Microsoft-Windows-AppLocker/EXE and DLL' -MaxEvents 20 |
      Select-Object TimeCreated, Id, LevelDisplayName, Message |
      Format-Table -AutoSize -Wrap
} catch {
    Write-Host ("ERROR step2 applocker-events (channel may not exist): " + $_.Exception.Message)
}

try {
    # Policy key absent = SRP not configured, which is the finding itself
    $srpPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Safer\CodeIdentifiers'
    if (Test-Path $srpPath) {
        Get-ItemProperty -Path $srpPath |
          Select-Object DefaultLevel, TransparentEnabled, PolicyScope |
          Format-Table -AutoSize
    } else {
        Write-Output '(Software Restriction Policy not configured)'
    }
} catch {
    Write-Host ("ERROR step2 srp-policy: " + $_.Exception.Message)
}

# --- Step 3: Drive Mapping Check ---
try {
    # HKCU:\Network\* may match nothing (no mapped drives) -- wildcard Get-ItemProperty
    # returns $null without error; absence of mapped drives is a normal finding.
    Get-ItemProperty -Path 'HKCU:\Network\*' |
      Select-Object PSChildName, RemotePath, UserName |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 mapped-drives-registry: " + $_.Exception.Message)
}
try {
    Get-PSDrive -PSProvider FileSystem | Where-Object { $_.DisplayRoot -ne $null } |
      Select-Object Name, DisplayRoot |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 psdrives: " + $_.Exception.Message)
}

# --- Step 4: Driver Installation Policy Check ---
try {
    # DeviceInstallDisabled absent = installation allowed (default)
    $diPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\DeviceInstall\Parameters'
    if (Test-Path $diPath) {
        Get-ItemProperty -Path $diPath |
          Select-Object DeviceInstallDisabled | Format-Table -AutoSize
    } else { Write-Output 'DeviceInstall\Parameters: (not configured - driver installation not disabled)' }
} catch {
    Write-Host ("ERROR step4 deviceinstall-policy: " + $_.Exception.Message)
}
try {
    $ppPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\PlugPlay\Parameters'
    if (Test-Path $ppPath) {
        Get-ItemProperty -Path $ppPath |
          Select-Object DeviceInstallDisabled | Format-Table -AutoSize
    } else { Write-Output 'PlugPlay\Parameters: (not configured - driver installation not disabled)' }
} catch {
    Write-Host ("ERROR step4 plugplay-policy: " + $_.Exception.Message)
}
