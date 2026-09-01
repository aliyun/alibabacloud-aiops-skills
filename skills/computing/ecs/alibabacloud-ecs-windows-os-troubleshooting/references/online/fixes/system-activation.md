# System Activation Diagnostic Fix Plan

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: sppsvc Service Corrupted or Disabled

**Fix operation**:

```powershell
#requires -RunAsAdministrator
# Fix: Enable and start the sppsvc service
# Risk: No risk in starting the service itself

# Set sppsvc startup type to Automatic (Delayed Start)
Set-Service -Name 'sppsvc' -StartupType Automatic
# Start the service
Start-Service -Name 'sppsvc'
```

**Verification**:

```powershell
Get-Service -Name 'sppsvc' | Format-List Name, Status, StartType
```

Expected result: StartType = Automatic, Status = Running (or Stopped when there is no activation operation is also acceptable; the key is that StartType is not Disabled)

**Risk notes**:

- **Session impact**: None, starting the service does not affect existing connections.
- **Persistence scope**: StartupType changes retained across reboot.
- **Rollback command**: `Set-Service -Name 'sppsvc' -StartupType Manual`
- **Note**: Starting the sppsvc service has no side effects. If the service cannot start due to corrupted system files, you may need to run `sfc /scannow` to repair system files.

### Root cause: Windows Not Activated via KMS

**Fix operation**:

```powershell
#requires -RunAsAdministrator
# Fix: Manually trigger KMS activation
# Risk: Only attempts activation without modifying system configuration

# Attempt online activation
cscript //Nologo C:\windows\system32\slmgr.vbs /ato
```

**Verification**:

```powershell
cscript //Nologo C:\windows\system32\slmgr.vbs /dli
```

Expected result: License Status shows Licensed

**Risk notes**:

- **Session impact**: None, only triggers an activation attempt.
- **Persistence scope**: Persists after successful activation.
- **Rollback command**: No rollback needed (only attempts activation).
- **Note**: `slmgr /ato` only triggers an activation attempt and does not modify any system configuration. If activation fails, further troubleshooting is needed based on the error code.

### Root cause: Product Key Does Not Match GVLK

**Fix operation**:

Select the corresponding GVLK from the table below based on the operating system version, then execute the install and activation commands:

| Windows Server Version | GVLK |
|------------------------|------|
| Server 2025 Datacenter | D764K-2NDRG-47T6Q-P8T8W-YP6DF |
| Server 2025 Standard | TVRH6-WHNXV-R9WG3-9XRFY-MY832 |
| Server 2022 Datacenter | WX4NM-KYWYW-QJJR4-XV3QB-6VM33 |
| Server 2022 Standard | VDYBN-27WPP-V4HQT-9VMD4-VMK7H |
| Server 2019 Datacenter | WMDGN-G9PQG-XVVXX-R3X43-63DFG |
| Server 2019 Standard | N69G4-B89J2-4G8F4-WWYCC-J464C |
| Server 2019 Essentials | WVDHN-86M7X-466P6-VHXV7-YY726 |
| Server 2016 Datacenter | CB7KF-BWN84-R7R2Y-793K2-8XDDG |
| Server 2016 Standard | WC2BQ-8NRM3-FDDYY-2BFGV-KHKQY |
| Server 2016 Essentials | JCKRF-N37P4-C2D82-9YXRT-4M63B |
| Server 2012 R2 Datacenter | W3GGN-FT8W3-Y4M27-J84CP-Q3VJ9 |
| Server 2012 R2 Standard | D2N9P-3P6X9-2R39C-7RTCD-MDVJX |
| Server 2012 R2 Essentials | KNC87-3J2TX-XB4WP-VCPJV-M4FWM |
| Server 2012 Datacenter | 48HP8-DN98B-MYWDG-T2DCC-8W83P |
| Server 2012 Standard | XC9B7-NBPP2-83J2H-RHMBY-92BT4 |
| Server 2008 R2 Datacenter | 74YFP-3QFB3-KQT8W-PMXWJ-7M648 |
| Server 2008 R2 Enterprise | 489J6-VHDMP-X63PK-3K798-CPX3Y |
| Server 2008 R2 Standard | YC6KT-GKW9T-YTKYR-T4X34-R7VHC |

> The table above covers common Alibaba Cloud ECS versions.

```powershell
#requires -RunAsAdministrator
# Fix: Install the correct GVLK and reactivate
# Risk: Replaces the current product key; if currently using non-KMS activation (e.g., retail key), this will switch to KMS activation mode
# Note: Select the appropriate GVLK from the table above based on the actual OS version and replace the key below

# Install GVLK
cscript //Nologo C:\windows\system32\slmgr.vbs /ipk <SelectCorrespondingGVLKFromTableAbove>

# Reactivate
cscript //Nologo C:\windows\system32\slmgr.vbs /ato
```

**Verification**:

```powershell
cscript //Nologo C:\windows\system32\slmgr.vbs /dli
```

Expected result: Displays the correct Windows version name and License Status: Licensed

**Risk notes**:

- **Session impact**: None, installing the key does not affect existing connections.
- **Persistence scope**: Product key replacement is permanent.
- **Rollback command**: `cscript //Nologo C:\windows\system32\slmgr.vbs /ipk <OriginalProductKey>`
- **Note**: Installing a GVLK replaces the current product key. If the instance was originally activated via non-KMS method (such as retail key or MAK key), this operation will switch to KMS activation mode. Confirm with the user that KMS activation is desired before proceeding.

### Root cause: Firewall Blocks KMS Communication Port

**Fix operation**:

```powershell
#requires -RunAsAdministrator
# Fix: Add firewall rule to allow KMS port outbound communication
# Risk: Adds a new outbound allow rule without affecting existing rules

New-NetFirewallRule -DisplayName "Allow KMS Activation (TCP 1688 Outbound)" `
    -Direction Outbound -Action Allow -Protocol TCP -RemotePort 1688 `
    -Profile Any -Enabled True
```

**Verification**:

```powershell
# Verify the rule has been created
Get-NetFirewallRule -DisplayName "Allow KMS Activation (TCP 1688 Outbound)" | Format-List DisplayName, Enabled, Direction, Action

# Test KMS port connectivity (Alibaba Cloud KMS server)
Test-NetConnection -ComputerName kms.cloud.aliyuncs.com -Port 1688
```

Expected result: Rule enabled with direction Outbound and Action Allow; Test-NetConnection shows TcpTestSucceeded: True

**Risk notes**:

- **Session impact**: None, only adds a rule without affecting existing connections.
- **Persistence scope**: Firewall rule persists, retained across reboot.
- **Rollback command**: `Remove-NetFirewallRule -DisplayName 'Allow KMS Activation (TCP 1688 Outbound)'`
- **Note**: Only adds a new outbound allow rule; does not delete or modify existing firewall rules. If there is an explicit block rule with higher priority, you may also need to disable or delete that block rule.

### Root cause: KMS Server Unreachable

**Fix operation**:

```powershell
#requires -RunAsAdministrator
# Fix: Set Alibaba Cloud KMS server address and reactivate
# Risk: Modifies KMS server configuration; applicable only to Alibaba Cloud ECS instances

# Set KMS server to Alibaba Cloud internal address
cscript //Nologo C:\windows\system32\slmgr.vbs /skms kms.cloud.aliyuncs.com:1688

# Reactivate
cscript //Nologo C:\windows\system32\slmgr.vbs /ato
```

**Verification**:

```powershell
# Verify connectivity
Test-NetConnection -ComputerName kms.cloud.aliyuncs.com -Port 1688 -WarningAction SilentlyContinue |
    Select-Object ComputerName, RemotePort, TcpTestSucceeded | Format-List

cscript //Nologo C:\windows\system32\slmgr.vbs /dli
```

Expected result: TcpTestSucceeded = True, License Status = Licensed

**Risk notes**:

- **Session impact**: None, modifying KMS server configuration does not affect existing connections.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: `cscript //Nologo C:\windows\system32\slmgr.vbs /ckms` (clears custom KMS server configuration)
- **Note**: `/skms` modifies the KMS server configuration in the registry. If the instance already has a custom KMS server (non-Alibaba Cloud default), confirm with the user before proceeding.

### Root cause: Tokens.dat Corrupted (Activation License Database Corrupted)

When the sppsvc service is normal, the product key is correct, and KMS network is reachable, but activation still repeatedly fails, the license token file (Tokens.dat) may be corrupted. Typical error codes: 0xC004E002 (license store format inconsistency), 0xC004E015 (license consumption failure).

**Fix operation**:

```powershell
#requires -RunAsAdministrator
# Fix: Rebuild Tokens.dat license token file
# Risk: Clears all current license states; requires reinstalling the product key and reactivating

# 1. Stop Software Protection service
Stop-Service -Name sppsvc -Force

# 2. Rename Tokens.dat (backup) -- select path according to OS version:
# -- Windows Server 2012 R2 and above (including Win 8.1/10/11):
Rename-Item "$env:windir\system32\spp\store\2.0\tokens.dat" "tokens.dat.bak" -Force
# -- Windows Server 2012 (including Win 8):
# Rename-Item "$env:windir\system32\spp\store\tokens.dat" "tokens.dat.bak" -Force
# -- Windows Server 2008 R2 (including Win 7):
# Rename-Item "$env:windir\ServiceProfiles\NetworkService\AppData\Roaming\Microsoft\SoftwareProtectionPlatform\tokens.dat" "tokens.dat.bak" -Force

# 3. Restart Software Protection service (Tokens.dat will be regenerated automatically)
Start-Service -Name sppsvc

# 4. Reinstall license
cscript //Nologo C:\windows\system32\slmgr.vbs /rilc

# 5. Restart computer (first restart)
# Restart-Computer -Force

# 6. After restart, reinstall GVLK (select the corresponding version from the key table above)
cscript //Nologo C:\windows\system32\slmgr.vbs /ipk <CorrespondingVersionGVLK>

# 7. Activate
cscript //Nologo C:\windows\system32\slmgr.vbs /ato

# 8. Restart computer again (second restart to ensure full effect)
# Restart-Computer -Force
```

**Verification**:

```powershell
cscript //Nologo C:\windows\system32\slmgr.vbs /dli
```

Expected result: License Status = Licensed

**Risk notes**:

- **Session impact**: None, but after rebuilding, you need to reinstall the product key and reboot twice.
- **Persistence scope**: Clears all license states; permanent after rebuild.
- **Rollback command**: Cannot be rolled back (need to reinstall product key).
- **Note**: Rebuilding Tokens.dat clears all license states; you must reinstall the product key after the operation. Make sure to record the current GVLK before proceeding. According to Microsoft official documentation (KB2736303), this fix requires two computer reboots to fully take effect. Note that the Tokens.dat storage path differs across Windows versions; be sure to select the correct path based on the operating system version.
