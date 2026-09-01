# CBS Component Service Diagnostic Fix Plan

> **Confirmation gate**: Every fix in this file is subject to SKILL.md Principle 6. Present the selected fix(es) with risk notes and an explicit confirmation request, then END the turn. Execute only after the user's explicit confirmation arrives in a later turn. The user's original "troubleshoot and fix" request is NOT confirmation -- phrasings such as "pre-authorized by the task" or "proceeding since the repair was already requested" are prohibited.

## Fix Recommendations

### Fix 1: Restore CBS Component Installation Service (CbsInstallerServiceInvalid)

**Applicable root cause**: CbsInstallerServiceInvalid

```powershell
# Restore TrustedInstaller (Windows Modules Installer) and dependent services
Set-Service -Name TrustedInstaller -StartupType Manual -ErrorAction SilentlyContinue
Start-Service -Name TrustedInstaller -ErrorAction SilentlyContinue
foreach ($svc in @('msiserver','BITS','CryptSvc')) {
  if ((Get-Service -Name $svc -ErrorAction SilentlyContinue).StartType -eq 'Disabled') {
    Set-Service -Name $svc -StartupType Manual -ErrorAction SilentlyContinue
  }
}
```

**Risk notes**: Session impact: Does not disconnect RDP. Persistence scope: Startup type changes retained across reboot. Rollback command: Revert to original startup type. Note: TrustedInstaller is normally Manual (started on demand); do not set it to Automatic persistent.

### Fix 2: Complete Pending Component Installation Operations (CbsRebootPending / FeatureInstallPending)

**Applicable root cause**: CbsRebootPending, FeatureInstallPending

```powershell
# Reboot to let CBS finish pending operations, then retry the installation
Restart-Computer -Force
```

**Risk notes**: Session impact: Reboot will disconnect RDP session; unsaved data will be lost. Persistence scope: Pending operations complete during reboot. Rollback command: Not applicable. Note: If pending state still exists after reboot (CBS.log reports pending package installation failure), proceed to the corresponding Fix in [system-update.md](references/online/fixes/system-update.md) (reset update cache and pending operations).

### Fix 3: Component Store and System File Repair (ComponentStoreCorrupted)

**Applicable root cause**: ComponentStoreCorrupted (SystemFileCorrupted in the update domain also reuses this fix)

```powershell
# Step A: repair component store via DISM (may take 10-20 minutes)
DISM /Online /Cleanup-Image /RestoreHealth
# Step B: run SFC after DISM completes
sfc /scannow
# Step C: reboot and retry the failed installation
Write-Host "Repair finished. Please reboot and retry the installation."
```

**Risk notes**: Session impact: Does not disconnect RDP, but CPU/disk usage increases during DISM/SFC execution. Persistence scope: Repair results retained across reboot. Rollback command: Irreversible (only repairs corrupted files, does not change user configuration); DISM defaults to pulling repair source from Windows Update. If the repair source is unreachable (reports 0x800f081f) and no matching version installation media is available on the instance, specifying a local install.wim source is not feasible on the cloud; proceed directly to Fix 6 (Cloud Assistant plugin ISO in-place repair). Note: After repair, it is recommended to run `sfc /scannow` again to confirm no remaining corrupted items.

### Fix 4: Specify Feature Installation Source (0x800f081f / 0x800f0906 / 0x800f0907 Source Missing)

**Applicable root cause**: CBS.log reports 0x800f081f (installation source not found), 0x800f0907 (no alternate source and policy prohibits downloading payload from WU), commonly seen with enabling on-demand features such as .NET 3.5

```powershell
# Option A: enable feature from local source (sxs folder of matching install media, e.g. D:\sources\sxs)
DISM /Online /Enable-Feature /FeatureName:NetFx3 /All /Source:D:\sources\sxs /LimitAccess
# Option B: allow downloading feature payload from Windows Update instead of WSUS (GP policy)
# Policy: Computer Configuration > Administrative Templates > System
#   "Specify settings for optional component installation and component repair" = Enabled
#   check "Contact Windows Update directly to download repair content instead of WSUS"
#   or set "Alternate source file path" (share containing \sources\sxs, or WIM:<path>\install.wim:<index>)
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Servicing' -Name 'UseWindowsUpdate' -Value 2 -Type DWord
gpupdate /force
```

**Risk notes**: Session impact: Does not disconnect RDP. Persistence scope: Option B policy/registry changes retained across reboot. Rollback command: Option B delete the created registry value or revert policy to original configuration then `gpupdate /force`; Option A has no persistent changes. Note: Option A source must match the system version and the current account must have at least read permission on the source path; the source file set must be complete and valid (common causes: path does not contain required files, no read permission, file set corrupted/incomplete/version mismatch); replace `FeatureName` with the actual failed feature (e.g., `IIS-WebServerRole`). Option A depends on the `\sources\sxs` of matching version installation media; on the cloud, you need to mount a matching version ISO via console/platform first. If no media is available, use Option B or proceed to Fix 6. Known issue: On Windows Server 2012 R2 images, enabling .NET 3.5 after installing recent security patches will report source files not found; you need to uninstall recently installed security patches (`wusa /uninstall /kb:<KBNumber>`) and reboot before installing.

### Fix 5: Retry Feature Installation After Repair

**Applicable root cause**: Verification operation after prerequisite Fix completion

```powershell
# Server roles/features (replace <FeatureName> with the failed feature, e.g. Web-Server)
Install-WindowsFeature -Name <FeatureName> -IncludeManagementTools
# Or via DISM (client systems / optional features)
# DISM /Online /Enable-Feature /FeatureName:<FeatureName> /All
```

**Risk notes**: Session impact: Does not disconnect RDP; IIS and other role installations take several minutes. Persistence scope: Installation results retained across reboot. Rollback command: `Uninstall-WindowsFeature -Name <FeatureName>` or `DISM /Online /Disable-Feature /FeatureName:<FeatureName>`. Note: If retry still fails, re-collect the latest CBS.log error lines (corresponding to diagnostic Step 2 collection script) and continue troubleshooting.

### Fix 6: ISO In-Place Upgrade Repair (Component Store Severely Corrupted and DISM/SFC Ineffective)

**Applicable root cause**: ComponentStoreCorrupted and Fix 3 ineffective, CbsPackageDatabaseLost, or matching Step 2 feature patterns (manifest missing, component no winner conflict, etc.)

```powershell
# Option A: Cloud Assistant plugin (mounts matching-version ISO and performs in-place upgrade repair)
acs-plugin-manager.exe -e -P Windows_RestoreAndUpdate -p "-ByMedia iso -AutoUpgrade -Autoreboot"
# Option B: manual in-place upgrade (mount same-version install ISO, keep files/settings/apps)
# Mount-DiskImage <ISO path>, then run setup.exe from the mounted drive:
#   setup.exe /auto upgrade /dynamicupdate disable
```

**Risk notes**: Session impact: Upgrade process will reboot multiple times, RDP interrupted, takes a long time (typically 30+ minutes). Persistence scope: User data, apps, and configurations are retained; system files and component store are rebuilt from the same version image. Rollback command: Irreversible; MUST create a system disk snapshot before proceeding; on failure, roll back to the pre-incident snapshot. Note: ISO version MUST match the current system version (major version and language must match); cross-version will upgrade rather than repair; if system disk free space is insufficient, clean up first before proceeding.
