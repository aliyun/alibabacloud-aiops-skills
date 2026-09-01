$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Kerberos Clock Skew Check ---

try {
    $cs = Get-CimInstance Win32_ComputerSystem
    $localTime = Get-Date
    Write-Output "Local Time: $localTime"
} catch {
    Write-Host ("ERROR step1 computer-system: " + $_.Exception.Message)
}
try {
    $w32status = w32tm /query /status 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step1 w32tm-status: exit=$LASTEXITCODE $(($w32status | Out-String).Trim())" }
    $w32status
} catch {
    Write-Host ("ERROR step1 w32tm-status: " + $_.Exception.Message)
}
try {
    if ($cs -and $cs.PartOfDomain) {
        $target = $env:LOGONSERVER.TrimStart('\\')
        Write-Host "Stripchart target: $target"
        $strip = w32tm /stripchart /computer:$target /samples:1 /dataonly 2>&1
        if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step1 w32tm-stripchart: exit=$LASTEXITCODE $(($strip | Out-String).Trim())" }
        $strip
    } else {
        Write-Host "INFO: Computer is not domain-joined, skipping DC time comparison"
    }
} catch {
    Write-Host ("ERROR step1 w32tm-stripchart: " + $_.Exception.Message)
}

# --- Step 2: NTLM Authentication Configuration Check ---

try {
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' |
        Select-Object LmCompatibilityLevel, NoLmHash |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 ntlm-lsa: " + $_.Exception.Message)
}

# --- Step 3: SPN Configuration Check ---

try {
    $csSPN = Get-CimInstance Win32_ComputerSystem
    if ($csSPN -and $csSPN.PartOfDomain) {
        $spn = setspn -L $env:COMPUTERNAME 2>&1
        if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 setspn: exit=$LASTEXITCODE $(($spn | Out-String).Trim())" }
        $spn
    } else {
        Write-Host "INFO: Computer is not domain-joined, SPN check not applicable"
    }
} catch {
    Write-Host ("ERROR step3 setspn: " + $_.Exception.Message)
}
