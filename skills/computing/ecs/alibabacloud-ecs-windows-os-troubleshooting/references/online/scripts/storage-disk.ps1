$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Disk Status and Attribute Check ---

try {
    # === Part A: PowerShell view (may miss dynamic/foreign/offline disks) ===
    Get-Disk |
        Select-Object Number, FriendlyName, SerialNumber, UniqueId, OperationalStatus, HealthStatus, PartitionStyle, Size, AllocatedSize, NumberOfPartitions, IsOffline, IsReadOnly, IsBoot, IsSystem |
        Format-List
} catch {
    Write-Host ("ERROR step1 get-disk: " + $_.Exception.Message)
}

try {
    # SAN policy (determines whether new disks come online automatically)
    (Get-StorageSetting).NewDiskPolicy
} catch {
    Write-Host ("ERROR step1 storage-setting: " + $_.Exception.Message)
}

try {
    # === Part B: Diskpart view (complete physical disk picture at the lower level, including Dyn marker) ===
    $dpOutput = "list disk" | diskpart 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step1 diskpart-list-disk: exit=$LASTEXITCODE $(($dpOutput | Out-String).Trim())" }
    Write-Host "=== Diskpart Raw Output ==="
    $dpOutput
} catch {
    Write-Host ("ERROR step1 diskpart-list-disk: " + $_.Exception.Message)
}

try {
    # === Part C: Dual verification - find disks that exist in Diskpart but not in Get-Disk (missed disks) ===
    $psDisks = Get-Disk | Select-Object -ExpandProperty Number
    $dpDiskNumbers = [regex]::Matches(($dpOutput | Out-String), 'Disk\s+(\d+)') | ForEach-Object { [int]$_.Groups[1].Value }
    $missingDisks = $dpDiskNumbers | Where-Object { $psDisks -notcontains $_ }

    if ($missingDisks) {
        Write-Host "!!! WARNING: Disks found in Diskpart but MISSING in Get-Disk (Likely Dynamic/Foreign/Offline): $missingDisks !!!"
        try {
            foreach ($d in $missingDisks) {
                Get-CimInstance Win32_DiskDrive | Where-Object { $_.Index -eq $d } |
                    Select-Object Index, Caption, Status, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
            }
        } catch {
            Write-Host ("ERROR step1 missing-disk-detail: " + $_.Exception.Message)
        }
        try {
            Get-CimInstance Win32_Volume | Where-Object { $_.DriveLetter } |
                Select-Object DriveLetter, FileSystem, @{N='SizeGB';E={[math]::Round($_.Capacity/1GB,2)}}, @{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,2)}} |
                Format-Table -AutoSize
        } catch {
            Write-Host ("ERROR step1 missing-disk-volumes: " + $_.Exception.Message)
        }
    } else {
        Write-Host "INFO: No discrepancy between Diskpart and Get-Disk."
    }
} catch {
    Write-Host ("ERROR step1 diskpart-crosscheck: " + $_.Exception.Message)
}

try {
    # === Part D: Detect if Dyn marker (dynamic disk) exists in Diskpart output ===
    $dynDisks = [regex]::Matches(($dpOutput | Out-String), 'Disk\s+(\d+).*?\bDyn\b') | ForEach-Object { [int]$_.Groups[1].Value }
    if ($dynDisks) {
        Write-Host "!!! DYNAMIC DISKS DETECTED: $dynDisks !!!"
    }
} catch {
    Write-Host ("ERROR step1 dynamic-disk-detect: " + $_.Exception.Message)
}

# --- Step 2: Partition Table and Space Allocation Check ---

try {
    Get-Disk |
        Select-Object Number, SerialNumber, PartitionStyle, Size, AllocatedSize, NumberOfPartitions, @{N='UnallocatedGB';E={[math]::Round(($_.Size - $_.AllocatedSize)/1GB, 2)}} |
        Format-List
} catch {
    Write-Host ("ERROR step2 disk-allocation: " + $_.Exception.Message)
}

try {
    Get-Partition |
        Select-Object DiskNumber, PartitionNumber, Type, Size, Offset, DriveLetter, IsActive, IsBoot, IsSystem, GptType, MbrType |
        Format-List
} catch {
    Write-Host ("ERROR step2 get-partition: " + $_.Exception.Message)
}

# --- Step 3: Partition Status and Mount Check ---

try {
    Get-Partition | ForEach-Object {
        $part = $_
        $vol = $null
        try { $vol = $part | Get-Volume } catch { Write-Host ("ERROR step3 get-volume(disk $($part.DiskNumber) part $($part.PartitionNumber)): " + $_.Exception.Message) }
        [PSCustomObject]@{
            DiskNumber      = $part.DiskNumber
            PartitionNumber = $part.PartitionNumber
            Type            = $part.Type
            Size            = $part.Size
            Offset          = $part.Offset
            DriveLetter     = $part.DriveLetter
            FileSystem      = if ($vol) { $vol.FileSystem } else { 'N/A' }
            FileSystemLabel = if ($vol) { $vol.FileSystemLabel } else { 'N/A' }
            AllocationUnitSize = if ($vol) { $vol.AllocationUnitSize } else { 0 }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 partition-volume-map: " + $_.Exception.Message)
}

try {
    Get-Disk | ForEach-Object {
        $disk = $_
        $lastPart = Get-Partition -DiskNumber $disk.Number | Sort-Object Offset | Select-Object -Last 1
        if ($lastPart) {
            $supported = $null
            try { $supported = $lastPart | Get-PartitionSupportedSize } catch { Write-Host ("ERROR step3 supported-size(disk $($disk.Number) part $($lastPart.PartitionNumber)): " + $_.Exception.Message) }
            [PSCustomObject]@{
                DiskNumber      = $disk.Number
                PartitionNumber = $lastPart.PartitionNumber
                CurrentSizeGB   = [math]::Round($lastPart.Size/1GB, 2)
                MaxSizeGB       = if ($supported) { [math]::Round($supported.SizeMax/1GB, 2) } else { 'N/A' }
                Expandable      = if ($supported) { $supported.SizeMax -gt $lastPart.Size } else { $false }
            }
        }
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 expand-capability: " + $_.Exception.Message)
}

try {
    # Auto-mount status (when automount is disabled, new volumes will not be assigned drive letters automatically)
    $autoMount = "automount" | diskpart 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 diskpart-automount: exit=$LASTEXITCODE $(($autoMount | Out-String).Trim())" }
    $autoMount
} catch {
    Write-Host ("ERROR step3 diskpart-automount: " + $_.Exception.Message)
}

# --- Step 4: Volume Capacity and Cluster Size Limit Check ---

try {
    Get-Volume |
        Where-Object { $_.DriveLetter -and $_.FileSystem } |
        Select-Object DriveLetter, FileSystem, AllocationUnitSize, Size, SizeRemaining, @{N='SizeGB';E={[math]::Round($_.Size/1GB, 2)}}, @{N='ClusterSizeKB';E={$_.AllocationUnitSize/1KB}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 volume-cluster-size: " + $_.Exception.Message)
}

# --- Step 5: Volume Space Utilization Check ---

try {
    Get-Volume |
        Where-Object { $_.DriveLetter } |
        Select-Object DriveLetter, FileSystem, FileSystemLabel, @{N='SizeGB';E={[math]::Round($_.Size/1GB, 2)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB, 2)}}, @{N='UsedPercent';E={if($_.Size -gt 0){[math]::Round(($_.Size - $_.SizeRemaining)/$_.Size * 100, 1)}else{0}}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 volume-usage: " + $_.Exception.Message)
}

# --- Step 6: File System Health Check ---

try {
    Get-Volume |
        Where-Object { $_.FileSystem -eq 'NTFS' -and $_.DriveLetter } | ForEach-Object {
        Write-Output "=== $($_.DriveLetter): ==="
        $fsinfo = fsutil fsinfo ntfsinfo "$($_.DriveLetter):" 2>&1
        if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step6 fsutil-ntfsinfo($($_.DriveLetter)): exit=$LASTEXITCODE $(($fsinfo | Out-String).Trim())" }
        $fsinfo
    }
} catch {
    Write-Host ("ERROR step6 fsutil-ntfsinfo: " + $_.Exception.Message)
}

try {
    # CHKDSK / Wininit events in the last 7 days
    # Filter ProviderName in FilterHashtable directly: the Application log is
    # high-volume, so "latest N + filter afterwards" returns nothing.
    Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Chkdsk','Wininit'; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 chkdsk-events: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Ntfs'; Level=2,3; StartTime=(Get-Date).AddDays(-7)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 ntfs-events: " + $_.Exception.Message)
}
