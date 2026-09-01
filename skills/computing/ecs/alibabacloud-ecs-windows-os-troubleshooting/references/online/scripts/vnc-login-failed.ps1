$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 2: Memory 100% Render Failure Determination ---

try {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object @{n='TotalMB';e={[math]::Round($_.TotalVisibleMemorySize/1KB,0)}}, @{n='FreeMB';e={[math]::Round($_.FreePhysicalMemory/1KB,0)}}
} catch {
    Write-Host ("ERROR step2 os-memory: " + $_.Exception.Message)
}

try {
    Get-Process | Sort-Object WorkingSet64 -Descending |
        Select-Object -First 10 Name, Id, @{n='MemMB';e={[math]::Round($_.WorkingSet64/1MB,0)}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 top-memory-processes: " + $_.Exception.Message)
}

try {
    # Memory resource exhaustion events (Event 2004; default 30-day window, narrow around user-reported failure time when provided)
    Get-WinEvent -FilterHashtable @{LogName='System'; Id=2004; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 10 |
        Select-Object TimeCreated, Id, Message | Format-List
} catch {
    Write-Host ("ERROR step2 memory-exhaustion-events: " + $_.Exception.Message)
}

# --- Step 3: GPU/Bare Metal Specification Determination ---

try {
    Get-CimInstance Win32_VideoController |
        Select-Object Name, Status, DriverVersion, DriverDate, VideoProcessor, @{n='AdapterRAMGB';e={[math]::Round($_.AdapterRAM/1GB,1)}} | Format-List
} catch {
    Write-Host ("ERROR step3 video-controller: " + $_.Exception.Message)
}

try {
    Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory | Format-List
} catch {
    Write-Host ("ERROR step3 computer-system: " + $_.Exception.Message)
}

try {
    $startTime = (Get-Date).AddDays(-3)
    Get-WinEvent -FilterHashtable @{LogName='System'; Level=2,3; StartTime=$startTime} |
        Where-Object { $_.ProviderName -match 'Display|dxgkrnl|nvlddmkm|amdkmdag' } |
        Select-Object TimeCreated, Id, ProviderName, Message -First 20 | Format-List
} catch {
    Write-Host ("ERROR step3 display-events: " + $_.Exception.Message)
}
