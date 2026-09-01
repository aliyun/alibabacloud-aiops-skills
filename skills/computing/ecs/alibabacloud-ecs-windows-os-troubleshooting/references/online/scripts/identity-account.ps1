$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Account Lockout Status Check ---

try {
    Get-CimInstance -ClassName Win32_UserAccount -Filter "LocalAccount=True" |
        Select-Object Name, Disabled, Lockout, PasswordExpires, SID |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 local-accounts: " + $_.Exception.Message)
}

# Security log is high-volume; unbounded "latest N" queries miss lockouts that
# happened days ago. Default window: last 30 days; narrow around the user-reported
# lockout time point when provided.
$lockoutStart = (Get-Date).AddDays(-30)

try {
    Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4740; StartTime=$lockoutStart} -MaxEvents 10 |
        Select-Object TimeCreated, Id, @{n='TargetUser';e={$_.Properties[0].Value}}, @{n='CallerComputer';e={$_.Properties[1].Value}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 lockout-events: " + $_.Exception.Message)
}

try {
    Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4625; StartTime=$lockoutStart} -MaxEvents 20 |
        Select-Object TimeCreated, @{n='TargetUser';e={$_.Properties[5].Value}}, @{n='SourceIP';e={$_.Properties[19].Value}}, @{n='LogonType';e={$_.Properties[10].Value}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 failed-logon-events: " + $_.Exception.Message)
}

# --- Step 2: Password and Lockout Policy Check ---

try {
    $secpolCfg = "$env:TEMP\secpol_check.cfg"
    $secOut = secedit /export /cfg $secpolCfg /quiet 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 secedit-export: exit=$LASTEXITCODE $(($secOut | Out-String).Trim())" }
    Get-Content $secpolCfg |
        Select-String -Pattern '^(MinimumPasswordAge|MaximumPasswordAge|MinimumPasswordLength|PasswordComplexity|PasswordHistorySize|LockoutBadCount|LockoutDuration|ResetLockoutCount|ForceLogoffWhenHourExpire)\s*=' |
        ForEach-Object { Write-Host $_ }
} catch {
    Write-Host ("ERROR step2 secpol-export: " + $_.Exception.Message)
} finally {
    Remove-Item $secpolCfg -Force -ErrorAction SilentlyContinue
}

# --- Step 3: Password Expiration Status Check ---

try {
    Get-LocalUser |
        Select-Object Name, Enabled, PasswordExpires, PasswordLastSet, LastLogon |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 localuser-expiry: " + $_.Exception.Message)
}

# --- Step 4: Built-in Administrator Account Check ---

try {
    Get-CimInstance -ClassName Win32_UserAccount -Filter "LocalAccount=True AND Name='Administrator'" |
        Select-Object Name, Disabled, Lockout, SID |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 builtin-admin: " + $_.Exception.Message)
}
