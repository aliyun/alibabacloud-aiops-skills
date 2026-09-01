# RDP Licensing Diagnostic Fix Guide

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: RDS licensing mode not configured

**Fix**:

```powershell
# Configure RDS licensing mode to Per User
$tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting" -ErrorAction SilentlyContinue
if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName ChangeMode -Arguments @{LicensingType=4} }
Write-Host "Configured RDS licensing mode to Per User"

# If need to configure license server address (replace <LicenseServerAddress> with actual address)
# if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName AddLSToSpecifiedLicenseServerList -Arguments @{LicenseServerName="<LicenseServerAddress>"} }
```

**Verification**:

```powershell
Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting" -ErrorAction SilentlyContinue | Select-Object LicensingType, LicensingName
```

Expected result: LicensingType = 4 (Per User)

**Risk notes**:

- **Session impact**: None, only modifies licensing configuration.
- **Persistence scope**: Configuration changes persist across reboots.
- **Rollback command**: Restore the original licensing mode configuration.
- **Note**: Per User and Per Device cannot be mixed. Please confirm the purchased CAL type before configuring.

---

### Root cause: RDS 120-day trial period expired

**Fix**:

```powershell
# Note: The proper solution is to purchase and configure RDS CAL
# The following steps are for diagnostic confirmation only, administrator needs to configure correct license server in Group Policy

# 1. Configure license server (replace <LicenseServerAddress> with actual address)
# $tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting" -ErrorAction SilentlyContinue
# if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName AddLSToSpecifiedLicenseServerList -Arguments @{LicenseServerName="<LicenseServerAddress>"} }

# 2. Configure licensing mode
# if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName ChangeMode -Arguments @{LicensingType=4} }

Write-Host "Please contact administrator to configure valid RDS license server and CAL"
```

**Verification**:

```powershell
Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TSLicenseKeyPack" -ErrorAction SilentlyContinue | Select-Object KeyPackType, TotalLicenses, AvailableLicenses
```

Expected result: Available RDS CAL licenses exist

**Risk notes**:

- **Session impact**: None; this is a display-only diagnostic step, no system changes are made.
- **Persistence scope**: No changes; nothing to persist.
- **Rollback command**: Not applicable; no modifications were made.
- **Note**: This step is for diagnostic confirmation only. The fundamental solution after the Grace Period expires is to purchase legitimate RDS CALs and configure the license server in Group Policy.

---

### Root cause: RDS CALs exhausted

**Fix**:

```powershell
# View current license usage
Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TSLicenseKeyPack" -ErrorAction SilentlyContinue | Select-Object KeyPackType, ProductType, TotalLicenses, IssuedLicenses, AvailableLicenses | Format-List

# If using Per Device mode, can revoke unused device CALs
# Need to operate in RD Licensing Manager
Write-Host "Recommendation: Purchase more RDS CALs or clean up unused device licenses"
```

**Verification**:

```powershell
Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TSLicenseKeyPack" -ErrorAction SilentlyContinue | Select-Object TotalLicenses, AvailableLicenses
```

Expected result: AvailableLicenses > 0

**Risk notes**:

- **Session impact**: None, only revokes licenses.
- **Persistence scope**: License revocation is permanent.
- **Rollback command**: The related device will automatically reacquire a license on next connection.
- **Note**: Revoking device CALs may cause the related devices to need to reacquire licenses.

---

### Root cause: RDS license server unreachable

**Fix**:

```powershell
# 1. Confirm license server address is configured correctly
$tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting" -ErrorAction SilentlyContinue
if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName GetSpecifiedLicenseServerList }

# 2. Test network connectivity (replace <LicenseServerAddress> with actual address)
# Test-NetConnection -ComputerName <LicenseServerAddress> -Port 135

# 3. If firewall issue, open RPC port
# New-NetFirewallRule -DisplayName "Allow RDS Licensing RPC" -Direction Outbound -Protocol TCP -RemotePort 135 -Action Allow
```

**Verification**:

```powershell
# Replace <LicenseServerAddress> with actual address
# Test-NetConnection -ComputerName <LicenseServerAddress> -Port 135
```

Expected result: TcpTestSucceeded = True

**Risk notes**:

- **Session impact**: None, only adds a firewall rule.
- **Persistence scope**: Firewall rule persists across reboots.
- **Rollback command**: `Remove-NetFirewallRule -DisplayName 'Allow RDS Licensing RPC'`
- **Note**: Opening firewall ports increases the network attack surface; it is recommended to restrict target IPs.

---

### Root cause: Local RD Licensing service not running

**Fix**:

```powershell
# Start RD Licensing service
Set-Service -Name TermServLicensing -StartupType Automatic
Start-Service -Name TermServLicensing
Write-Host "Started RD Licensing service"
```

**Verification**:

```powershell
Get-Service -Name TermServLicensing | Select-Object Name, Status, StartType
```

Expected result: Status = Running, StartType = Automatic

**Risk notes**:

- **Session impact**: None, only starts the service.
- **Persistence scope**: StartupType change persists across reboots.
- **Rollback command**: `Stop-Service TermServLicensing; Set-Service -Name TermServLicensing -StartupType Disabled`
- **Note**: If this machine is not the license server, starting this service will not resolve the issue; a correct external license server must be configured.

---

### Root cause: RDS license server not configured

**Fix**:

```powershell
# Configure license server address (replace <LicenseServerAddress> with actual address)
$tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting" -ErrorAction SilentlyContinue
if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName AddLSToSpecifiedLicenseServerList -Arguments @{LicenseServerName="<LicenseServerAddress>"} }

# Configure licensing mode
if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName ChangeMode -Arguments @{LicensingType=4} }

Write-Host "Configured RDS license server, please confirm server address is correct"
```

**Verification**:

```powershell
$tss = Get-CimInstance -Namespace "root/CIMV2/TerminalServices" -ClassName "Win32_TerminalServiceSetting" -ErrorAction SilentlyContinue
$tss | Select-Object LicensingType | Format-Table -AutoSize
if ($tss) { Invoke-CimMethod -InputObject $tss -MethodName GetSpecifiedLicenseServerList }
```

Expected result: GetSpecifiedLicenseServerList returns a valid server address, LicensingType is 2 or 4.

**Risk notes**:

- **Session impact**: None, only modifies license server configuration.
- **Persistence scope**: Configuration changes persist across reboots.
- **Rollback command**: Remove the configured license server address.
- **Note**: Configuring an incorrect license server address will cause license acquisition to fail.
