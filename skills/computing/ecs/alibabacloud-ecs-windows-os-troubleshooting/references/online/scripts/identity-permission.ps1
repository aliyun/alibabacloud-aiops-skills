$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: System Drive Root Directory Permission Check ---

try {
    (Get-Acl "$env:SystemDrive\").Access |
        Select-Object IdentityReference, FileSystemRights, AccessControlType, IsInherited, InheritanceFlags, PropagationFlags |
        Format-List
} catch {
    Write-Host ("ERROR step1 systemdrive-acl: " + $_.Exception.Message)
}

# --- Step 2: User Group Membership and Remote Logon Permission Check ---

foreach ($group in @('Administrators','Remote Desktop Users','Users')) {
    Write-Host "=== $group ==="
    try {
        Get-LocalGroupMember -Group $group |
            Select-Object Name, ObjectClass, PrincipalSource |
            Format-Table -AutoSize
    } catch {
        Write-Host ("ERROR step2 group-members-" + $group + ": " + $_.Exception.Message)
    }
}

# --- Step 3: Temp Folder Permission Check ---

try {
    (Get-Acl $env:TEMP).Access |
        Select-Object IdentityReference, FileSystemRights, AccessControlType, IsInherited, InheritanceFlags, PropagationFlags |
        Format-List
} catch {
    Write-Host ("ERROR step3 temp-acl: " + $_.Exception.Message)
}

# --- Step 4: ForceGuest Configuration Check ---

try {
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'ForceGuest' |
        Select-Object ForceGuest |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 forceguest: " + $_.Exception.Message)
}

# --- Step 5: Remote Logon Deny Policy Check ---

try {
    $secOut = secedit /export /cfg "$env:TEMP\secpol_rdp.cfg" /quiet 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step5 secedit-export: exit=$LASTEXITCODE $(($secOut | Out-String).Trim())" }
    $deny = Get-Content "$env:TEMP\secpol_rdp.cfg" | Select-String 'SeDenyRemoteInteractiveLogonRight' | ForEach-Object { $_.Line }
    $allow = Get-Content "$env:TEMP\secpol_rdp.cfg" | Select-String 'SeRemoteInteractiveLogonRight' | ForEach-Object { $_.Line }
    Write-Host "SeDenyRemoteInteractiveLogonRight: $(if ($deny) { $deny } else { '(not configured)' })"
    Write-Host "SeRemoteInteractiveLogonRight: $(if ($allow) { $allow } else { '(not configured)' })"
} catch {
    Write-Host ("ERROR step5 secpol-rdp: " + $_.Exception.Message)
} finally {
    Remove-Item "$env:TEMP\secpol_rdp.cfg" -Force -ErrorAction SilentlyContinue
}

# --- Step 6: Guest Account Status Check ---

try {
    Get-LocalUser -Name 'Guest' |
        Select-Object Name, Enabled, LastLogon |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step6 guest-account: " + $_.Exception.Message)
}
