# System Crash Diagnostic Fix

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Enable Crash Dump (CrashDumpNotEnabled)

**Applicable Root cause**: CrashDumpNotEnabled

```powershell
# Enable Automatic Memory Dump (recommended)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Name 'CrashDumpEnabled' -Value 7 -Type DWord
# Ensure auto-reboot is enabled
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Name 'AutoReboot' -Value 1 -Type DWord
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Name CrashDumpEnabled, AutoReboot | Select-Object CrashDumpEnabled, AutoReboot
```

Expected result: `CrashDumpEnabled` value is `7`, `AutoReboot` value is `1`

> Once enabled, the next BSOD will generate a dump file at %SystemRoot%\MEMORY.DMP for analysis.

**Risk notes**:
- **Session impact**: None; registry change only, no service restart or session disruption.
- **Persistence scope**: Survives reboot (registry change in CrashControl key).
- **Rollback command**: `Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\CrashControl' -Name 'CrashDumpEnabled' -Value 0 -Type DWord`

### Fix 2: Analyze BugCheck BSOD Dump (CriticalEvent -- BugCheck)

**Applicable Root cause**: CriticalEvent (BugCheck type)

1. Confirm MEMORY.DMP or Minidump file exists:
   ```powershell
   Get-ChildItem -Path "$env:SystemRoot\MEMORY.DMP" -ErrorAction SilentlyContinue
   Get-ChildItem -Path "$env:SystemRoot\Minidump\*.dmp" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5
   ```
2. Analyze the dump file contents to identify the BSOD root cause; if analysis capability is insufficient, provide the dump file path information to the user and recommend expert analysis
3. Look up the BugCheck Code in the Microsoft BugCheck Code Reference documentation

**Verification**:

```powershell
Get-ChildItem -Path "$env:SystemRoot\MEMORY.DMP" -ErrorAction SilentlyContinue
Get-ChildItem -Path "$env:SystemRoot\Minidump\*.dmp" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

Expected result: MEMORY.DMP or a .dmp file exists in the Minidump directory, with a recent modification time

**Risk notes**:
- **Session impact**: None; read-only analysis of dump files, no system changes.
- **Persistence scope**: No system changes made; dump files remain on disk.
- **Rollback command**: No rollback needed (no changes made to the system).

### Fix 3: Pre-enable Kernel Memory Dump and NMI (to prepare for core collection during the next Hang recurrence)

**Applicable scenario**: Hang scenarios require NMI core collection to capture live evidence, but the instance has already recovered; pre-enable while the instance is healthy so that when the next Hang occurs, collection can be triggered while frozen (NMI depends on kernel memory dump, so dump must be enabled before NMI)

```powershell
# 1. Enable kernel memory dump (skip if already enabled)
acs-plugin-manager --exec --plugin ecs_dump_config_win -p "--status"
acs-plugin-manager --exec --plugin ecs_dump_config_win -p "--enable"

# 2. Enable NMI
acs-plugin-manager --exec --plugin ecs_nmi_config_win -p "--status"
acs-plugin-manager --exec --plugin ecs_nmi_config_win -p "--enable"
```

**Verification**: Run the `--status` query for both plugins again to confirm both are in enabled state

> Only Windows Server 2012R2 / 2016 / 2019 / 2022 / 2025 are supported; triggering NMI collection will cause the instance to BSOD and reboot, which is an offline scenario (handled by the offline crash-hang diagnostic), operated manually by the user and requires explicit confirmation.

**Risk notes**:
- **Session impact**: None during enablement; however, triggering NMI during a future Hang will cause a BSOD and reboot, disconnecting all sessions.
- **Persistence scope**: Survives reboot (dump and NMI configuration are persistent).
- **Rollback command**: `acs-plugin-manager --exec --plugin ecs_dump_config_win -p "--disable"; acs-plugin-manager --exec --plugin ecs_nmi_config_win -p "--disable"`
