$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: VirtIO Driver Package Check ---
try {
  Get-WindowsDriver -Online |
    Where-Object { @('SCSIAdapter', 'Net', 'System') -contains $_.ClassName } |
    Select-Object Driver, OriginalFileName, ClassName, ProviderName, Version, Date | Format-List
} catch {
  Write-Host ("ERROR step1 virtio-packages: " + $_.Exception.Message)
}

# --- Step 2: VirtIO Driver Version Check ---
# Version judgement uses the best installed driver package per INF (SelectBestDriver):
# Windows PnP picks the active package at boot by Rank -> Date -> Version; same-INF
# packages share Rank in practice, so select by Date (newest) then Version (highest).
# The effective .sys version is OS-guaranteed and MUST NOT be read from the
# loaded/device-bound .sys.
try {
  Get-WindowsDriver -Online |
    Where-Object { $_.OriginalFileName -match '(?i)(viostor|vioscsi|netkvm|balloon|vioser|pvpanic|fwcfg)\.inf$' } |
    Group-Object { Split-Path $_.OriginalFileName -Leaf } |
    ForEach-Object {
      $_.Group | Sort-Object Date, @{e={ if ($_.Version -as [version]) { [version]$_.Version } else { [version]'0.0.0' } }} -Descending | Select-Object -First 1
    } |
    Select-Object OriginalFileName, ProviderName, Version, Date | Format-Table -AutoSize
} catch {
  Write-Host ("ERROR step2 virtio-versions: " + $_.Exception.Message)
}

# --- Step 3: Driver Installation Policy Check ---
try {
  Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\DeviceInstall\Parameters' -Name DeviceInstallDisabled |
    Select-Object DeviceInstallDisabled
} catch {
  Write-Host ("ERROR step3 device-install-policy: " + $_.Exception.Message)
}
try {
  Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\PlugPlay\Parameters' -Name DeviceInstallDisabled |
    Select-Object DeviceInstallDisabled
} catch {
  Write-Host ("ERROR step3 plugplay-policy: " + $_.Exception.Message)
}

# --- Step 4: Xen Driver Residual Check ---
try {
  Get-WindowsDriver -Online |
    Where-Object { $_.OriginalFileName -match 'xen' } |
    Select-Object Driver, OriginalFileName, Version | Format-Table -AutoSize
} catch {
  Write-Host ("ERROR step4 xen-drivers: " + $_.Exception.Message)
}
try {
  Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\XenPCI\Parameters' -Name hide_devices |
    Select-Object hide_devices
} catch {
  Write-Host ("ERROR step4 xen-hide-devices: " + $_.Exception.Message)
}
