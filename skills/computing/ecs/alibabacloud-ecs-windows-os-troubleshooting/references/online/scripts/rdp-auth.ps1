$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: CredSSP Configuration Check ---

# 1. Check TSpkg.dll version (determine if CVE-2018-0886 patch is installed)
try {
    Get-Item "$env:SystemRoot\System32\TSpkg.dll" | Select-Object FullName, @{N='FileVersion';E={$_.VersionInfo.FileVersion}} | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 tspkg-version: " + $_.Exception.Message)
}

# 2. Check AllowEncryptionOracle policy configuration
try {
    Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\CredSSP\Parameters" -Name "AllowEncryptionOracle" | Select-Object AllowEncryptionOracle
} catch {
    Write-Host ("ERROR step1 credssp-oracle-policy: " + $_.Exception.Message)
}

# 3. Check Encryption Oracle Remediation configuration in Group Policy
# Path: Computer Configuration > Administrative Templates > System > Credentials Delegation > Encryption Oracle Remediation
try {
    Get-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CredentialsDelegation" -Name "AllowEncryptionOracle" | Select-Object AllowEncryptionOracle
} catch {
    Write-Host ("ERROR step1 gp-encryption-oracle: " + $_.Exception.Message)
}

# --- Step 2: Account Lockout Status Check ---

try {
    Get-CimInstance -ClassName Win32_UserAccount -Filter "LocalAccount=True AND Disabled=False" |
        Select-Object Name, Lockout, Status, Disabled | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 account-lockout: " + $_.Exception.Message)
}

# --- Step 3: Remote Logon Permission Check ---

try {
    Get-CimInstance -ClassName Win32_GroupUser |
        Where-Object { $_.GroupComponent.Name -in @('Remote Desktop Users', 'Administrators') } |
        Select-Object @{N='Group';E={$_.GroupComponent.Name}}, @{N='Member';E={$_.PartComponent.Name}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 group-members: " + $_.Exception.Message)
}

# Capture matches into variables first, then emit per section via Write-Host,
# so section headers and their content stay in order (deferred formatting would interleave them).
try {
    $secOut = secedit /export /cfg "$env:TEMP\secpol.cfg" /quiet 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step3 secedit-export: exit=$LASTEXITCODE $(($secOut | Out-String).Trim())" }
    $allowLines = Select-String -Path "$env:TEMP\secpol.cfg" -Pattern "SeRemoteInteractiveLogonRight" | ForEach-Object { $_.Line }
    $denyLines = Select-String -Path "$env:TEMP\secpol.cfg" -Pattern "SeDenyRemoteInteractiveLogonRight" | ForEach-Object { $_.Line }
    Write-Host "--- Allowed remote logon ---"
    if ($allowLines) { $allowLines | ForEach-Object { Write-Host $_ } } else { Write-Host "(not configured)" }
    Write-Host "--- Denied remote logon ---"
    if ($denyLines) { $denyLines | ForEach-Object { Write-Host $_ } } else { Write-Host "(not configured)" }
} catch {
    Write-Host ("ERROR step3 secpol-rdp-logon: " + $_.Exception.Message)
} finally {
    Remove-Item "$env:TEMP\secpol.cfg" -Force -ErrorAction SilentlyContinue
}

# --- Step 4: Security Layer Configuration Check ---

try {
    $winStationsPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations"
    Get-ChildItem -Path $winStationsPath |
        Where-Object { $_.PSChildName -ne "Console" } |
        ForEach-Object {
            $props = Get-ItemProperty -Path $_.PSPath
            [PSCustomObject]@{
                StationName        = $_.PSChildName
                SecurityLayer      = $props.SecurityLayer
                UserAuthentication = $props.UserAuthentication
            }
        } | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 winstations: " + $_.Exception.Message)
}

# --- Step 5: Password Error Audit Event Check ---

try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'Security'
        ID = 4625
        StartTime = (Get-Date).AddHours(-1)
    } -MaxEvents 10 | Select-Object TimeCreated, Id, Message
} catch {
    Write-Host ("ERROR step5 logon-failure-events: " + $_.Exception.Message)
}

# --- Step 6: ForceGuest Access Mode Check ---

# Check ForceGuest configuration (0=Classic mode, 1=Guest only mode)
try {
    Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "ForceGuest" | Select-Object ForceGuest
} catch {
    Write-Host ("ERROR step6 forceguest: " + $_.Exception.Message)
}
