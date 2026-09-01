$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check Print Spooler Service ---
try {
    Get-Service -Name Spooler | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 spooler-service: " + $_.Exception.Message)
}
try {
    $deps = (Get-Service -Name Spooler).DependentServices
    if ($deps) {
        Write-Host "Dependent services:"
        $deps | Select-Object Name, Status | Format-Table -AutoSize
    }
} catch {
    Write-Host ("ERROR step1 spooler-dependents: " + $_.Exception.Message)
}
try {
    $printJobs = Get-CimInstance Win32_PrintJob
    if ($printJobs) {
        Write-Host "Print jobs in queue: $($printJobs.Count)"
        $printJobs | Select-Object Document, JobStatus, Owner, Priority, Size | Format-List
    } else {
        Write-Host "No print jobs in queue"
    }
} catch {
    Write-Host ("ERROR step1 print-jobs: " + $_.Exception.Message)
}
try {
    # Filter ProviderName in FilterHashtable -- the System log is high-volume, so pulling
    # the latest N entries and filtering afterwards misses spooler crashes days ago.
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Service Control Manager'; Level=2; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 30 |
        Where-Object { $_.Message -like '*Spooler*' -or $_.Message -like '*Print*' } |
        Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 spooler-eventlog: " + $_.Exception.Message)
}

# --- Step 2: Check Printer Driver Installation ---
try {
    $printers = Get-CimInstance Win32_Printer
    if ($printers) {
        Write-Host "Installed printers: $($printers.Count)"
        $printers | Select-Object Name, DriverName, PortName, PrinterStatus, Shared | Format-List
    } else {
        Write-Host "No printers installed"
    }
} catch {
    Write-Host ("ERROR step2 printers: " + $_.Exception.Message)
}
try {
    $drivers = Get-CimInstance Win32_PrinterDriver
    if ($drivers) {
        Write-Host "`nInstalled printer drivers: $($drivers.Count)"
        $drivers | Select-Object Name, SupportedPlatform | Format-Table -AutoSize
    }
} catch {
    Write-Host ("ERROR step2 printer-drivers: " + $_.Exception.Message)
}
try {
    $ports = Get-CimInstance Win32_TCPIPPrinterPort
    if ($ports) {
        Write-Host "`nTCP/IP Printer Ports:"
        $ports | Select-Object Name, HostAddress, PortNumber | Format-Table -AutoSize
    }
} catch {
    Write-Host ("ERROR step2 printer-ports: " + $_.Exception.Message)
}

# --- Step 3: Check Print Output Status ---
try {
    $spoolDir = "$env:SystemRoot\System32\spool\PRINTERS"
    if (Test-Path $spoolDir) {
        $spoolFiles = Get-ChildItem -Path $spoolDir
        $totalSize = ($spoolFiles | Measure-Object -Property Length -Sum).Sum
        Write-Host "Spool directory: $spoolDir"
        Write-Host "Files: $($spoolFiles.Count), Total size: $([math]::Round($totalSize/1MB, 2)) MB"
    } else {
        Write-Host "Spool directory not found: $spoolDir"
    }
} catch {
    Write-Host ("ERROR step3 spool-dir: " + $_.Exception.Message)
}
try {
    Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PrintService/Operational'; Level=2,3} -MaxEvents 10 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 print-operational-log: " + $_.Exception.Message)
}
try {
    # Fallback: if Operational log is not available, check System log
    # (filter ProviderName in FilterHashtable -- latest-N-then-filter returns nothing)
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-PrintService'; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 print-system-log: " + $_.Exception.Message)
}
