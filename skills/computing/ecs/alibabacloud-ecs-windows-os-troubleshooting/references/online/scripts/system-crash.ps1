$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: BugCheck BSOD Event Check ---
try {
    # Default window: last 30 days. When the user provides a crash time point,
    # MUST narrow StartTime/EndTime around it to avoid missing recent crashes.
    $crashStart = (Get-Date).AddDays(-30)
    # Filter ProviderName in FilterHashtable directly: Event ID 1001 also comes from
    # other sources, "latest N + filter afterwards" can miss BugCheck entries.
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='BugCheck'; Id=1001; StartTime=$crashStart} -MaxEvents 10 |
      Select-Object TimeCreated, Id, Message |
      Format-Table -AutoSize -Wrap
} catch {
    Write-Host ("ERROR step1 bugcheck-events: " + $_.Exception.Message)
}

# --- Step 2: Crash Dump Configuration Check ---
try {
    # Individual values are optional (e.g. no dump configured); whole-key read keeps
    # absent values as nulls, which is itself the finding.
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' |
      Select-Object CrashDumpEnabled, DumpFile, MinidumpDir, AutoReboot, LogEvent |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 crash-control: " + $_.Exception.Message)
}
