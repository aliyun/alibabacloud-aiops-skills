$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: SMB Client Configuration Check ---

try {
    Get-SmbClientConfiguration |
        Select-Object EnableSecuritySignature, EnableEncryption, RequireSecuritySignature |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 smb-client-config: " + $_.Exception.Message)
}

try {
    # No active SMB sessions is a normal state (returns nothing / errors on some builds)
    Get-SmbConnection |
        Select-Object ServerName, Dialect, Encrypted, Signed, ShareName |
        Format-List
} catch {
    Write-Host ("ERROR step1 smb-connections: " + $_.Exception.Message)
}

# --- Step 2: Network Component Status Check ---

try {
    $netcfgOut = netcfg -s n 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR step2 netcfg: exit=$LASTEXITCODE $(($netcfgOut | Out-String).Trim())" }
    $netcfgOut
} catch {
    Write-Host ("ERROR step2 netcfg: " + $_.Exception.Message)
}

try {
    Get-NetAdapterBinding |
        Where-Object { $_.ComponentID -eq "ms_msclient" } |
        Select-Object Name, ComponentID, DisplayName, Enabled |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 msclient-binding: " + $_.Exception.Message)
}

try {
    Get-Service -Name LanmanWorkstation |
        Select-Object Name, Status, StartType |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 lanman-workstation: " + $_.Exception.Message)
}

try {
    Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\NetworkProvider\Order" |
        Select-Object ProviderOrder |
        Format-List
} catch {
    Write-Host ("ERROR step2 provider-order: " + $_.Exception.Message)
}

# --- Step 3: Network Discovery Configuration Check ---

try {
    $services = @("fdPHost", "FDResPub", "lmhosts")
    Get-Service -Name $services |
        Select-Object Name, DisplayName, Status, StartType |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 discovery-services: " + $_.Exception.Message)
}

try {
    Get-NetFirewallRule -DisplayGroup "Network Discovery" |
        Select-Object DisplayName, Enabled, Profile, Direction |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 discovery-firewall: " + $_.Exception.Message)
}

try {
    # Empty result = nothing listening on 445 (itself an important SMB finding)
    Get-NetTCPConnection -LocalPort 445 -State Listen |
        Select-Object LocalPort, State, OwningProcess |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step3 port-445-listen: " + $_.Exception.Message)
}

# --- Step 4: Guest Access Policy Check ---

try {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object Caption, Version, BuildNumber |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 os-info: " + $_.Exception.Message)
}

try {
    # AllowInsecureGuestAuth is optional; absence = default behavior (the finding itself)
    Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" |
        Select-Object AllowInsecureGuestAuth |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 insecure-guest-auth: " + $_.Exception.Message)
}

try {
    Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" |
        Select-Object LMCompatibilityLevel, RestrictAnonymous, RestrictAnonymousSAM |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step4 lsa-policy: " + $_.Exception.Message)
}
