# Storage VSS (Volume Shadow Copy Service) Diagnostic Fix Plan

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: VSS Service Disabled

**Fix operation**:

```powershell
# Restore VSS service and Software Shadow Copy Provider startup type to Manual
Set-Service -Name VSS -StartupType Manual
Set-Service -Name swprv -StartupType Manual

# Start VSS service
Start-Service -Name VSS
```

**Verification**:

```powershell
Get-Service -Name VSS, swprv | Select-Object Name, Status, StartType
```

Expected result: Startup type is Manual, VSS service starts normally

**Risk notes**:

- **Session impact**: None, modifying service startup type does not affect existing connections.
- **Persistence scope**: Written to service configuration, retained across reboot.
- **Rollback command**: `Set-Service -Name VSS -StartupType Manual; Set-Service -Name swprv -StartupType Manual`

---

### Root cause: VSS Dependent Services Abnormal

**Fix operation**:

```powershell
# Ensure dependent services have correct startup type and are running
$deps = @('EventSystem', 'RpcSs', 'DcomLaunch')
foreach ($svc in $deps) {
    Set-Service -Name $svc -StartupType Automatic -ErrorAction SilentlyContinue
    Start-Service -Name $svc -ErrorAction SilentlyContinue
}

# Restart VSS service
Restart-Service -Name VSS -Force -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
Get-Service -Name EventSystem, RpcSs, DcomLaunch, VSS | Select-Object Name, Status, StartType
```

Expected result: All services in Running state

**Risk notes**:

- **Session impact**: Restarting core services may briefly affect other applications that depend on them.
- **Persistence scope**: Current session only; services auto-start after reboot.
- **Rollback command**: No rollback needed; the operation restores normal service operation.

---

### Root cause: VSS Writer Status Abnormal

**Fix operation**:

The fix is done in two steps: first attempt to restart the control service corresponding to the abnormal Writer; if that is ineffective, proceed with VSS component re-registration.

```powershell
# Step 1: Restart the control service corresponding to the abnormal Writer
# Based on Step 2 diagnosis, replace <ServiceName> with actual control service name
# Common mappings:
#   System Writer        -> CryptSvc
#   WMI Writer           -> Winmgmt
#   COM+ REGDB Writer    -> COMSysApp
#   Task Scheduler Writer -> Schedule
#   BITS Writer          -> BITS
#   SqlServerWriter      -> MSSQLSERVER
Restart-Service -Name <ServiceName> -Force
```

```powershell
# Step 2 (only execute if Step 1 is ineffective): Re-register VSS components
Stop-Service -Name vss -Force
regsvr32 /s ole32.dll
regsvr32 /s vss_ps.dll
vssvc /register
Start-Service -Name vss
```

**Verification**:

```powershell
vssadmin list writers
```

Expected result: All Writer statuses are Stable

**Risk notes**:

- **Session impact**: Restarting the control service briefly interrupts the functionality managed by that service (e.g., restarting MSSQLSERVER causes SQL Server to be briefly unavailable).
- **Persistence scope**: Current session only; services auto-recover after reboot.
- **Rollback command**: No rollback needed; the operation restores Writer normal state.
- **Note**: Evaluate business impact before executing. Step 2 re-registration of VSS components does not modify data and carries low risk.

---

### Root cause: VSS Provider Registration Abnormal

**Fix operation**:

```powershell
# Re-register Windows built-in VSS Provider
Stop-Service -Name swprv -Force
Start-Service -Name swprv

# Re-register VSS service
Stop-Service -Name vss -Force
vssvc /register
Start-Service -Name vss
```

**Verification**:

```powershell
vssadmin list providers
```

Expected result: Microsoft Software Shadow Copy provider 1.0 listed normally

**Risk notes**:

- **Session impact**: None, re-registration does not affect existing connections.
- **Persistence scope**: Current session only; service auto-loads after restart.
- **Rollback command**: No rollback needed; the operation does not modify data.

---

### Root cause: Third-Party VSS Provider Residual

**Fix operation**:

```powershell
# First confirm residual third-party Provider (get Provider Id from Step 3 diagnosis)
vssadmin list providers

# Remove residual third-party Provider from registry (replace <Provider-GUID> with actual value)
# Note: This operation requires administrator privileges
# Remove-Item -Path "HKLM:\SYSTEM\CurrentControlSet\Services\VSS\Providers\<Provider-GUID>" -Recurse -Force
```

**Verification**:

```powershell
vssadmin list providers
vssadmin create shadow /for=C:
```

Expected result: Only Microsoft built-in Provider listed, snapshot created successfully

**Risk notes**:

- **Session impact**: None, only modifies registry.
- **Persistence scope**: Written to registry, retained across reboot.
- **Rollback command**: Manually re-add registry key `HKLM:\SYSTEM\CurrentControlSet\Services\VSS\Providers\<Provider-GUID>`
- **Note**: After deletion, the corresponding backup software's snapshot functionality will be unavailable. Confirm that the corresponding backup software has been uninstalled before proceeding.

---

### Root cause: VSS Snapshot Storage Space Insufficient

**Fix operation**:

```powershell
# Option 1: Clean old VSS snapshots to free space (specify by volume)
vssadmin delete shadows /for=<DriveLetter>: /oldest /quiet

# Option 2: Adjust VSS storage space limit
vssadmin resize shadowstorage /for=<DriveLetter>: /on=<DriveLetter>: /maxsize=<Size>GB

# Option 3: Clear all snapshots and reconfigure
# vssadmin delete shadows /all /quiet
```

**Verification**:

```powershell
vssadmin list shadowstorage
vssadmin create shadow /for=<DriveLetter>:
```

Expected result: Storage space utilization decreased, new snapshot created successfully

**Risk notes**:

- **Session impact**: None, only cleans snapshot storage.
- **Persistence scope**: Snapshots permanently deleted, cannot be undone.
- **Rollback command**: None, deleted snapshots cannot be recovered.
- **Note**: Deleting VSS snapshots loses corresponding system restore points and file version history. Prefer Option 1 (only delete oldest snapshot) or Option 2 (increase the limit).

---

### Root cause: VSS Event Log Reports Errors

**Note**:

VSS event log errors are typically symptoms of other root causes. They need to be associated with the corresponding root cause based on the specific Event ID for fix:

| Event ID | Associated Root Cause | Fix Direction |
|----------|----------------------|---------------|
| 8193 | VSS Dependent Services Abnormal / Provider Registration Abnormal | Check COM component registration and dependent services |
| 8194 | VSS Writer Status Abnormal | Restart the control service of the abnormal Writer |
| 12289 | VSS Provider Registration Abnormal / Third-Party Provider Residual | Check Provider registration |
| 12293 / 12298 | Disk I/O Performance Issue | Reduce disk load and retry, or perform backup during off-peak hours |

If Event ID 12293 / 12298 occurs frequently, it indicates that disk I/O latency is too high for VSS operations to complete within the timeout window. Investigate storage performance issues (refer to the storage-hardware diagnostic section)

---

### Root cause: Backup Execution Failed

**Fix operation**:

```powershell
# Ensure Windows Server Backup feature is installed
Install-WindowsFeature -Name Windows-Server-Backup -IncludeManagementTools

# Re-run backup (example: backup system state, replace <BackupTarget> with actual path)
# wbadmin start systemstatebackup -backuptarget:<BackupTarget>
```

**Verification**:

```powershell
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Backup'; StartTime=(Get-Date).AddDays(-1)} -MaxEvents 5 -ErrorAction SilentlyContinue | Select-Object TimeCreated, LevelDisplayName, Message
```

Expected result: Backup completed successfully with no error events

**Risk notes**:

- **Session impact**: Backup process consumes CPU/disk I/O and may affect business performance.
- **Persistence scope**: Feature installation writes to system configuration, retained across reboot.
- **Rollback command**: `Remove-WindowsFeature -Name Windows-Server-Backup`
- **Note**: It is recommended to perform backup operations during a maintenance window.
