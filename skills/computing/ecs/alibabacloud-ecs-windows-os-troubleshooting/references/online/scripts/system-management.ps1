$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: PowerShell Execution Policy Check ---
try {
    Get-ExecutionPolicy -List | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 execution-policy: " + $_.Exception.Message)
}

# --- Step 2: WinRM Service Check ---
try {
    Get-Service -Name WinRM |
      Select-Object Name, Status, StartType |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 winrm-service: " + $_.Exception.Message)
}
try {
    # "No listener configured" arrives as a non-zero exit + stderr text -- that IS the finding
    $winrmEnum = winrm enumerate winrm/config/listener 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 winrm-listener: exit=$LASTEXITCODE $(($winrmEnum | Out-String).Trim())" }
    $winrmEnum
} catch {
    Write-Host ("ERROR step2 winrm-listener: " + $_.Exception.Message)
}

# --- Step 3: WMI Repository Status Check ---
try {
    Get-Service -Name Winmgmt |
      Select-Object Name, Status, StartType |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 winmgmt-service: " + $_.Exception.Message)
}
try {
    # verifyrepository exit code: 0 = consistent, non-zero = WMI repository corruption
    $wmiVerify = winmgmt /verifyrepository 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 winmgmt-verifyrepository: exit=$LASTEXITCODE $(($wmiVerify | Out-String).Trim())" }
    $wmiVerify
} catch {
    Write-Host ("ERROR step3 winmgmt-verifyrepository: " + $_.Exception.Message)
}
try {
    Get-CimInstance -ClassName Win32_OperatingSystem |
      Select-Object Caption, Version, BuildNumber |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 os-wmi: " + $_.Exception.Message)
}

# --- Step 4: Event Log Service Check ---
try {
    Get-Service -Name EventLog |
      Select-Object Name, Status, StartType |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 eventlog-service: " + $_.Exception.Message)
}
try {
    Get-WinEvent -ListLog System, Application, Security |
      Select-Object LogName, @{N='SizeMB';E={[math]::Round($_.FileSize/1MB,1)}}, MaximumSizeInBytes, RecordCount, IsLogFull |
      Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 log-metadata: " + $_.Exception.Message)
}

# --- Step 5: MMC Console Check ---
try {
    Test-Path -Path "$env:SystemRoot\System32\mmc.exe" | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step5 mmc-presence: " + $_.Exception.Message)
}
try {
    # NDP\v4\Full key absent = .NET Framework 4.x not installed (the finding itself)
    $ndpPath = 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full'
    if (Test-Path $ndpPath) {
        Get-ItemProperty -Path $ndpPath |
          Select-Object Release, Version |
          Format-Table -AutoSize
    } else {
        Write-Output '.NET Framework 4.x Full key not found (not installed)'
    }
} catch {
    Write-Host ("ERROR step5 netfx-version: " + $_.Exception.Message)
}
