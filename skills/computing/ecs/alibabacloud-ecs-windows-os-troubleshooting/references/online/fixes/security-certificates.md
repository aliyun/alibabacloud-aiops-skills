# Security Certificates Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: Critical root certificate missing or expired

**Fix operation**:

```powershell
# Update root certificates via Windows Update
certutil -generateSSTFromWU roots.sst
certutil -addstore Root roots.sst
Remove-Item roots.sst -Force
```

**Verification**:

```powershell
Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq 'A43489159A520F0D93D032CCAF37E7FE20A8B419' }
```

Expected result: Returns Microsoft Root Certificate Authority 2011 certificate information

**Risk notes**:

- **Session impact**: None; only downloading certificates.
- **Persistence scope**: Certificate installation is persistent.
- **Rollback command**: Remove the imported certificates.
- **Note**: Requires network access to Microsoft update servers; may fail in a fully offline environment.

### Root cause: TLS 1.2 disabled

**Fix operation**:

```powershell
# Enable TLS 1.2 for both Client and Server
$protocols = @('Client','Server')
foreach ($side in $protocols) {
    $path = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2\$side"
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name 'Enabled' -Value 1 -Type DWord
    Set-ItemProperty -Path $path -Name 'DisabledByDefault' -Value 0 -Type DWord
}
Write-Host "TLS 1.2 enabled. Reboot required to take effect."
```

**Verification**:

```powershell
$clientEnabled = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2\Client' -Name 'Enabled').Enabled
Write-Host "TLS 1.2 Client Enabled: $clientEnabled"
```

Expected result: Returns 1

**Risk notes**:

- **Session impact**: None; only modifying the registry, but a reboot is required to take effect.
- **Persistence scope**: Registry modifications persist across reboots.
- **Rollback command**: Delete the added TLS 1.2 registry entries.
- **Note**: Very few legacy applications may not support TLS 1.2; confirm application compatibility before enabling.

### Root cause: Driver signing root certificate missing

**Fix operation**:

```powershell
# Update root certificates via certutil
certutil -generateSSTFromWU roots.sst
certutil -addstore Root roots.sst
Remove-Item roots.sst -Force
```

**Verification**:

```powershell
Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq 'CDD4EEAE6000AC7F40C3802C171E30148030C072' }
```

Expected result: Returns Microsoft Root Certificate Authority 2010 certificate information

**Risk notes**:

- **Session impact**: None; only downloading certificates.
- **Persistence scope**: Certificate installation is persistent.
- **Rollback command**: Remove the imported certificates.
- **Note**: Same as above; requires network access to Microsoft update servers.
