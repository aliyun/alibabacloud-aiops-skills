$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: SCSI Controller Status Check ---

try {
    Get-CimInstance -ClassName Win32_SCSIController | ForEach-Object {
        $ctrl = $_
        $device = $null
        try {
            $device = Get-CimAssociatedInstance -InputObject $ctrl -Association Win32_SCSIControllerDevice -ResultClassName Win32_PnPEntity
        } catch {
            Write-Host ("ERROR step1 scsi-child-devices($($ctrl.DeviceID)): " + $_.Exception.Message)
        }
        [PSCustomObject]@{
            DeviceID     = $ctrl.DeviceID
            Status       = $ctrl.Status
            DriverName   = $ctrl.DriverName
            ErrorCode    = $ctrl.ConfigManagerErrorCode
            DeviceCount  = @($device).Count
            DeviceInfo   = if ($device) { ($device | ForEach-Object { "$($_.DeviceID) [$($_.Status)]" }) -join '; ' } else { 'None' }
        }
    } | Format-List
} catch {
    Write-Host ("ERROR step1 scsi-controllers: " + $_.Exception.Message)
}

# --- Step 2: Disk Drive Status Check ---

try {
    Get-PnpDevice -Class DiskDrive |
        Select-Object InstanceId, FriendlyName, Status, ConfigManagerErrorCode, Service |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 disk-drive-pnp: " + $_.Exception.Message)
}

# --- Step 3: Registry Filter Driver Check ---

try {
    # UpperFilters/LowerFilters values are optional (absence = no filter drivers);
    # read the whole key and test properties instead of -Name reads that throw.
    Get-CimInstance -ClassName Win32_SCSIController | ForEach-Object {
        $ctrl = $_
        $devices = $null
        try {
            $devices = Get-CimAssociatedInstance -InputObject $ctrl -Association Win32_SCSIControllerDevice -ResultClassName Win32_PnPEntity
        } catch {
            Write-Host ("ERROR step3 scsi-child-devices($($ctrl.DeviceID)): " + $_.Exception.Message)
        }
        foreach ($dev in $devices) {
            $path = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($dev.DeviceID)"
            $regProps = Get-ItemProperty -Path $path
            $upper = $regProps.UpperFilters
            $lower = $regProps.LowerFilters
            if ($upper -or $lower) {
                $allFilters = @($upper) + @($lower) | Where-Object { $_ }
                $svcStatus = $allFilters | ForEach-Object {
                    $filterName = $_
                    try {
                        $svc = Get-Service -Name $filterName
                        "$($filterName)=$($svc.Status)"
                    } catch {
                        "$($filterName)=NotFound"
                    }
                }
                [PSCustomObject]@{
                    DeviceID       = $dev.DeviceID
                    UpperFilters   = $upper -join ', '
                    LowerFilters   = $lower -join ', '
                    ServiceStatus  = $svcStatus -join '; '
                }
            }
        }
    } | Format-List
} catch {
    Write-Host ("ERROR step3 registry-filters: " + $_.Exception.Message)
}

# --- Step 4: Disk Class Driver Check ---

function Get-ClassFilters {
    param($ClassGuidPath, $ClassName)
    try {
        $props = Get-ItemProperty -Path $ClassGuidPath
        [PSCustomObject]@{
            Class        = $ClassName
            UpperFilters = @($props.UpperFilters | Where-Object { $_ }) -join ', '
            LowerFilters = @($props.LowerFilters | Where-Object { $_ }) -join ', '
        }
    } catch {
        Write-Host ("ERROR step4 class-filters($ClassName): " + $_.Exception.Message)
    }
}

Get-ClassFilters "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e97b-e325-11ce-bfc1-08002be10318}" 'SCSIAdapter'

Get-ClassFilters "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e967-e325-11ce-bfc1-08002be10318}" 'DiskDrive'

Get-ClassFilters "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{71a27cdd-812a-11d0-bec7-08002be2092f}" 'Volume'

# --- Step 5: Storage Event Log Check ---

try {
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='disk'; Id=11; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 disk-events: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-PnP'; Id=225; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 10 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 pnp-events: " + $_.Exception.Message)
}
