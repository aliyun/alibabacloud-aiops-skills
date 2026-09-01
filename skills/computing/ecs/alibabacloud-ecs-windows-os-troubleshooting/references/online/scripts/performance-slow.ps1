$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: CPU Usage ---
try {
    Get-Counter '\Processor(*)\% Processor Time' -SampleInterval 1 -MaxSamples 2 | Select-Object -Last 1 | ForEach-Object {
        $_.CounterSamples | Select-Object InstanceName, @{Name='CpuPercent';Expression={[math]::Round($_.CookedValue, 1)}} | Sort-Object CpuPercent -Descending
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 cpu-counter: " + $_.Exception.Message)
}

try {
    Get-Counter '\Process(*)\% Processor Time' -SampleInterval 1 -MaxSamples 1 | ForEach-Object {
        $_.CounterSamples | Where-Object { $_.InstanceName -notin '_Total','Idle' } | Select-Object InstanceName, @{Name='CpuPercent';Expression={[math]::Round($_.CookedValue / [Environment]::ProcessorCount, 1)}} | Sort-Object CpuPercent -Descending | Select-Object -First 5
    } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 process-cpu-counter: " + $_.Exception.Message)
}

# --- Step 2: Memory Usage and Handle Count ---
try {
    $os = Get-CimInstance Win32_OperatingSystem
    [PSCustomObject]@{
        VisibleMemoryMB       = [math]::Round($os.TotalVisibleMemorySize / 1024)
        FreePhysicalMemoryMB  = [math]::Round($os.FreePhysicalMemory / 1024)
        MemoryUsagePercent    = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 1)
    } | Format-List
} catch {
    Write-Host ("ERROR step2 os-memory: " + $_.Exception.Message)
}

try {
    $procs = Get-CimInstance Win32_Process
    [PSCustomObject]@{ TotalHandleCount = ($procs | Measure-Object HandleCount -Sum).Sum } | Format-List
    $procs | Sort-Object WorkingSetSize -Descending | Select-Object -First 5 ProcessId, Name, @{Name='MemoryMB';Expression={[math]::Round($_.WorkingSetSize / 1MB, 1)}}, HandleCount | Format-Table -AutoSize
    $procs | Sort-Object HandleCount -Descending | Select-Object -First 5 ProcessId, Name, HandleCount, @{Name='MemoryMB';Expression={[math]::Round($_.WorkingSetSize / 1MB, 1)}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 process-memory: " + $_.Exception.Message)
}

# --- Step 3: Page File Configuration ---
try {
    $mm = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
    if ($mm) {
        [PSCustomObject]@{ PagingFiles = $mm.PagingFiles; ExistingPageFiles = $mm.ExistingPageFiles } | Format-List
    }
} catch {
    Write-Host ("ERROR step3 memory-management-registry: " + $_.Exception.Message)
}
try {
    (Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile
} catch {
    Write-Host ("ERROR step3 auto-managed-pagefile: " + $_.Exception.Message)
}
try {
    Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage | Format-Table -AutoSize
    Get-CimInstance Win32_PageFileSetting | Select-Object Name, InitialSize, MaximumSize | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 pagefile-usage: " + $_.Exception.Message)
}
try {
    Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl" | Select-Object CrashDumpEnabled, DumpFile, MinidumpDir | Format-List
} catch {
    Write-Host ("ERROR step3 crash-control-registry: " + $_.Exception.Message)
}

# --- Step 4: Hardware Reserved Memory ---
# Report raw values only; do NOT compute reserved here. GetPhysicallyInstalledSystemMemory is
# SMBIOS-based and on ECS VMs has been observed to return the OS-visible amount (Installed ==
# Visible, e.g. both 8046 MB on an 8 GB instance), so Installed - Visible is always ~0.
# Hardware reserved is derived in analysis as instance-type memory (describe-instances Memory) - VisiblePhysicalMB.
try {
    $kernel32 = $null
    try {
        $kernel32 = Add-Type -MemberDefinition @'
[DllImport("kernel32.dll")]
public static extern bool GetPhysicallyInstalledSystemMemory(out ulong TotalMemoryInKilobytes);
'@ -Name 'NativeMemory' -Namespace 'Win32' -PassThru
    } catch {
        Write-Host ("ERROR step4 add-type-native-memory (SMBIOS query unavailable, e.g. ConstrainedLanguage): " + $_.Exception.Message)
    }
    [UInt64]$installedKB = 0
    $smbiosQueryOk = $false
    if ($kernel32) { $smbiosQueryOk = [Win32.NativeMemory]::GetPhysicallyInstalledSystemMemory([ref]$installedKB) }
    if ($os) {
        $visiblePhysical = $os.TotalVisibleMemorySize * 1024
        [PSCustomObject]@{
            SMBIOSQueryOk    = $smbiosQueryOk
            SMBIOSInstalledMB = [math]::Round($installedKB / 1024)
            VisiblePhysicalMB = [math]::Round($visiblePhysical / 1MB)
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step4 hardware-memory: " + $_.Exception.Message)
}

# --- Step 5: Hyper-Threading Status ---
try {
    Get-CimInstance Win32_Processor | Select-Object DeviceID, NumberOfCores, NumberOfLogicalProcessors, @{Name='HyperThreading';Expression={
        if ($_.NumberOfLogicalProcessors -gt $_.NumberOfCores) { 'Enabled' } else { 'Disabled' }
    }} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 processor-info: " + $_.Exception.Message)
}

try {
    if ($mm) {
        [PSCustomObject]@{
            FeatureSettingsOverride     = $mm.FeatureSettingsOverride
            FeatureSettingsOverrideMask = $mm.FeatureSettingsOverrideMask
        } | Format-List
    }
} catch {
    Write-Host ("ERROR step5 ht-registry: " + $_.Exception.Message)
}

# --- Step 6: BCD Boot Configuration Limitations ---
try {
    $bcd = bcdedit /enum 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step6 bcdedit: exit=$LASTEXITCODE $(($bcd | Out-String).Trim())" }
    $bcd
} catch {
    Write-Host ("ERROR step6 bcdedit: " + $_.Exception.Message)
}

# --- Step 7: Power Plan ---
try {
    $activeScheme = powercfg /getactivescheme 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 powercfg-active: exit=$LASTEXITCODE $(($activeScheme | Out-String).Trim())" }
    $activeScheme
    $schemeList = powercfg /list 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step7 powercfg-list: exit=$LASTEXITCODE $(($schemeList | Out-String).Trim())" }
    $schemeList
} catch {
    Write-Host ("ERROR step7 powercfg: " + $_.Exception.Message)
}

# --- Step 8: File System Filter Driver Check ---
try {
    $fltmc = fltmc filters 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step8 fltmc: exit=$LASTEXITCODE $(($fltmc | Out-String).Trim())" }
    $fltmc
} catch {
    Write-Host ("ERROR step8 fltmc: " + $_.Exception.Message)
}
