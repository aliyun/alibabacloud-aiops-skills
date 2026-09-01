# Cloud Vminit Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Root cause: vminit not installed

**Fix operation**:

```powershell
# Reinstall vminit
# 1. Download the latest vminit installer from Alibaba Cloud official channel
# 2. Run the installer as Administrator
# 3. Verify the service is registered and set to Automatic startup
```

**Verification**:

```powershell
Get-Service -Name vminit -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: vminit service exists, startup type is Automatic

**Risk notes**:

- **Session impact**: None, installation does not affect existing connections.
- **Persistence scope**: Permanently installed, retained after reboot. A reboot is recommended to trigger the initialization process.
- **Rollback command**: Uninstall the vminit service (not recommended, as it will cause loss of instance initialization functionality).

---

### Root cause: vminit service not runnable

**Fix operation**:

```powershell
# Enable vminit service
Set-Service -Name vminit -StartupType Automatic

# Start vminit service
Start-Service -Name vminit
```

**Verification**:

```powershell
Get-Service -Name vminit -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType | Format-Table -AutoSize
```

Expected result: Status is Running, StartType is Automatic

**Risk notes**:

- **Session impact**: None, only modifies service configuration and starts it.
- **Persistence scope**: StartupType changes are retained after reboot.
- **Rollback command**: `Stop-Service vminit; Set-Service -Name vminit -StartupType Disabled`
- **Note**: If the vminit executable is missing, starting the service will fail. Reinstall first.

---

### Root cause: user-data script execution failure

**Fix operation**:

```powershell
# 1. Clear stale userdata cache (if system disk was replaced)
$cachePath = "$env:ProgramData\aliyun\vminit\user-data"
if (Test-Path $cachePath) {
  Remove-Item -Path $cachePath -Recurse -Force
  Write-Host 'Cleared userdata cache'
}

# 2. Restart vminit to re-fetch and execute user-data
Restart-Service -Name vminit -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
$logPath = "$env:ProgramData\aliyun\vminit\log"
$latestLog = Get-ChildItem $logPath -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latestLog) {
  Get-Content $latestLog.FullName -ErrorAction SilentlyContinue | Select-String -Pattern 'userdata|user.data|user_data' -SimpleMatch:$false
}
```

Expected result: Log shows successful userdata execution records, no error messages

**Risk notes**:

- **Session impact**: None, does not affect existing connections.
- **Persistence scope**: Cache deletion is irreversible; vminit will re-fetch and execute user-data after restart.
- **Rollback command**: Cannot be rolled back (cache has been cleared).
- **Note**: Restarting vminit will re-execute the user-data script. Confirm the script content is idempotent before proceeding.

---

### Root cause: vminit initialization log errors

**Description**:

vminit log errors are typically symptoms of other root causes. Associate them to the corresponding root cause based on specific error keywords:

| Error keyword | Associated root cause | Fix direction |
|---------|---------|--------|
| install_virtio_error | VirtIO driver installation failed | Check VirtIO driver status and version (cloud-driver diagnostic) |
| meta_server_error | Metadata service unreachable | Check metadata service endpoint connectivity (cloud-metaserver diagnostic) |
| config_passwd_error | Password configuration failed | Check password policy and user account status |
| registry_access_error | Registry access denied | Check permissions and security software blocking |
| no_system_disk | System disk not recognized | Check disk visibility and partition status (storage-disk diagnostic) |
| extend_disk_error | Disk extension failed | Check disk extension and partition/file system status (storage-disk diagnostic) |
| copy_files | File copy failed | Check disk space and file system permissions |

**Fix operation**:

```powershell
# View full log content to locate specific errors
$logPath = "$env:ProgramData\aliyun\vminit\log"
$latestLog = Get-ChildItem -Path $logPath -Filter '*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latestLog) { Get-Content $latestLog.FullName -ErrorAction SilentlyContinue }

# If the issue is resolved, restart vminit service to trigger re-initialization
Restart-Service -Name vminit -ErrorAction SilentlyContinue
```

**Verification**:

```powershell
$keywords = @('install_virtio_error','copy_files','registry_access_error','meta_server_error','config_passwd_error','no_system_disk','extend_disk_error')
$logPath = "$env:ProgramData\aliyun\vminit\log"
$latestLog = Get-ChildItem -Path $logPath -Filter '*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latestLog) {
  Get-Content $latestLog.FullName -ErrorAction SilentlyContinue | Where-Object {
    $line = $_; ($keywords | Where-Object { $line -match $_ }).Count -gt 0
  }
}
```

Expected result: No output (no error keywords)

**Risk notes**:

- **Session impact**: Restarting vminit may modify network configuration and passwords, which may affect current connections.
- **Persistence scope**: Results of vminit initialization operations are persistent.
- **Rollback command**: No unified rollback method; associate to the corresponding file's fix based on the specific error.
