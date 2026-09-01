$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Event Log Full Scan ---

# User-reported time window (default 24 hours, adjust per user report)
$startTime = (Get-Date).AddDays(-1)

# System/Application/Security log Error/Critical events grouped by Event ID (identify high-frequency or anomalous events)
# Grouping brings out Source and first sample Message (truncated to 120 chars) for direct use by domain routing, avoiding redundant collection
foreach ($log in @('System', 'Application', 'Security')) {
    Write-Host "== $log =="
    try {
        Get-WinEvent -FilterHashtable @{LogName=$log; Level=1,2; StartTime=$startTime} |
            Group-Object Id |
            Sort-Object Count -Descending |
            Select-Object Count, @{n='EventID';e={$_.Name}}, @{n='Source';e={$_.Group[0].ProviderName}},
                @{n='FirstSeen';e={($_.Group | Measure-Object TimeCreated -Minimum).Minimum}},
                @{n='LastSeen';e={($_.Group | Measure-Object TimeCreated -Maximum).Maximum}},
                @{n='SampleMessage';e={$msg = $_.Group[0].Message; if ($msg) { $msg.Substring(0, [math]::Min(120, $msg.Length)) }}} -First 15 |
            Format-List
    } catch {
        # Security log typically requires audit privileges; the error is the finding
        Write-Host ("ERROR step1 event-scan($log): " + $_.Exception.Message)
    }
}

# --- Step 2: Core Service Health ---

$coreServices = @('TermService', 'RpcSs', 'Winmgmt', 'WinRM', 'wuauserv', 'CryptSvc', 'BITS', 'EventLog', 'Schedule', 'Spooler')

try {
    Get-Service -Name $coreServices | Format-Table Name, Status, StartType -AutoSize
} catch {
    Write-Host ("ERROR step2 core-services: " + $_.Exception.Message)
}

try {
    Get-CimInstance Win32_Service | Where-Object { $coreServices -contains $_.Name -and ($_.State -ne 'Running' -or $_.StartMode -eq 'Disabled') } |
        Select-Object Name, State, StartMode, PathName | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 service-wmi: " + $_.Exception.Message)
}

# --- Step 3: Disk and Storage Health ---

try {
    # Volume space usage and health status (filter out volumes with no drive letter or 0 bytes to avoid empty volume noise)
    Get-Volume | Where-Object { $_.DriveLetter -and $_.Size -gt 0 } |
        Select-Object DriveLetter, FileSystemLabel, FileSystem, HealthStatus,
            @{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},
            @{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}},
            @{n='FreePercent';e={if($_.Size -gt 0){[math]::Round($_.SizeRemaining/$_.Size*100,1)}else{0}}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 volumes: " + $_.Exception.Message)
}

try {
    Get-Disk | Select-Object Number, FriendlyName, OperationalStatus, HealthStatus, IsOffline, IsReadOnly, @{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 get-disk: " + $_.Exception.Message)
}
try {
    Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus, OperationalStatus | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 physical-disk: " + $_.Exception.Message)
}

# --- Step 4: Network Basic Connectivity ---

try {
    Get-NetAdapter | Select-Object Name, Status, LinkSpeed, InterfaceDescription | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 net-adapter: " + $_.Exception.Message)
}

try {
    # Default gateway reachability (raw True/False IS the connectivity signal)
    $gw = (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1).NextHop
    if ($gw) { Test-Connection -ComputerName $gw -Count 2 -Quiet } else { Write-Host 'No default gateway route' }
} catch {
    Write-Host ("ERROR step4 gateway-ping: " + $_.Exception.Message)
}

try {
    # DNS resolution failure is itself a first-class finding -- let the error surface
    Resolve-DnsName www.aliyun.com | Select-Object Name, Type, IPAddress | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 dns-resolve: " + $_.Exception.Message)
}

try {
    # Key port listening status (3389/80/443); empty result = not listening (the finding)
    Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3389,80,443 } |
        Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 port-listen: " + $_.Exception.Message)
}

# --- Step 5: Resource Utilization Snapshot ---

try {
    Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average | Select-Object @{n='CpuPercent';e={[math]::Round($_.Average,1)}}
} catch {
    Write-Host ("ERROR step5 cpu-load: " + $_.Exception.Message)
}

try {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object @{n='TotalMB';e={[math]::Round($_.TotalVisibleMemorySize/1KB,0)}}, @{n='FreeMB';e={[math]::Round($_.FreePhysicalMemory/1KB,0)}}
} catch {
    Write-Host ("ERROR step5 memory: " + $_.Exception.Message)
}

try {
    Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 pagefile: " + $_.Exception.Message)
}

try {
    Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, Id, CPU, @{n='MemMB';e={[math]::Round($_.WorkingSet64/1MB,0)}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 top-cpu-processes: " + $_.Exception.Message)
}
try {
    Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 Name, Id, @{n='MemMB';e={[math]::Round($_.WorkingSet64/1MB,0)}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 top-mem-processes: " + $_.Exception.Message)
}

# --- Step 6: Recent System Changes ---

try {
    Get-HotFix | Where-Object { $_.InstalledOn -and $_.InstalledOn -gt (Get-Date).AddDays(-7) } |
        Sort-Object InstalledOn -Descending | Select-Object HotFixID, InstalledOn, Description | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 hotfixes: " + $_.Exception.Message)
}

try {
    $recentDate = (Get-Date).AddDays(-7).ToString('yyyyMMdd')
    Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' |
        Where-Object { $_.InstallDate -and $_.InstallDate -ge $recentDate } |
        Select-Object DisplayName, DisplayVersion, InstallDate | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 recent-software: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='System'; Id=1074,6005,6006} -MaxEvents 3 |
        Select-Object TimeCreated, Id, Message | Format-List
} catch {
    Write-Host ("ERROR step6 power-events: " + $_.Exception.Message)
}

Write-Output "CBS RebootPending: $(Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending')"
Write-Output "WU RebootRequired: $(Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')"
try {
    # PendingFileRenameOperations absent = nothing pending; whole-key read keeps it null
    Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' | Select-Object PendingFileRenameOperations
} catch {
    Write-Host ("ERROR step6 pending-file-rename: " + $_.Exception.Message)
}

# --- Step 7: Security Baseline ---

try {
    Get-NetFirewallProfile | Select-Object Name, Enabled | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step7 firewall-profile: " + $_.Exception.Message)
}

try {
    # BitLocker status (module not installed on some SKUs - record and skip)
    $hasBitLocker = $false
    try { $null = Get-Command Get-BitLockerVolume; $hasBitLocker = $true } catch { }
    if ($hasBitLocker) {
        Get-BitLockerVolume | Select-Object MountPoint, ProtectionStatus, EncryptionMethod | Format-Table -AutoSize
    } else {
        Write-Host "BitLocker module not installed - volumes not BitLocker-managed"
    }
} catch {
    Write-Host ("ERROR step7 bitlocker: " + $_.Exception.Message)
}

try {
    # Windows Defender status (removed/uninstalled Defender makes the cmdlet fail - the error is the finding)
    Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureLastUpdated | Format-List
} catch {
    Write-Host ("ERROR step7 defender-status: " + $_.Exception.Message)
}
