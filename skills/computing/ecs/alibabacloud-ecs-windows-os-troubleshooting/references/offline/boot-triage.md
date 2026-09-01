# Boot Evidence Pre-Analysis

## Function Description

Before performing offline troubleshooting, pre-analyze screenshots provided by the user to extract fault clues, narrow the troubleshooting scope, and provide an initial direction for subsequent offline diagnosis.

**Important**: The problem clues found during pre-analysis are **inputs** to the subsequent detailed offline diagnosis, not the final conclusion. After discovering problems, you MUST continue executing the complete offline diagnostic steps (mounting disk, loading registry, step-by-step troubleshooting). The goal is to output actionable fix plans. The only condition under which offline diagnosis may be exited is: evidence shows the system has booted normally.

**Inputs**:
- Screenshot: **Optional**, only allowed to be provided by the user or obtained from context. **Never obtain real-time screenshots via tools**: the instance currently being diagnosed (diagnostic instance) is necessarily in a running state, and its screen does not represent the failure instance's "first scene of boot failure" and has no diagnostic value. If the user does not provide one and no screenshot is available in context, skip screenshot analysis and proceed directly to subsequent offline troubleshooting

**Output**: Evidence summary + initial routing direction (list of troubleshooting files to prioritize), as the initial input for subsequent path planning

This file is a fault pre-analysis reference and does not contain fix action recommendations.

## Step Selection Guide

This file contains 1 diagnostic step. Select and execute based on available evidence:

| Condition | Recommended Steps |
|-----------|-------------------|
| User has provided screenshot or context contains screenshot | Step 1 (Screenshot Analysis) |
| No screenshot available | Skip Step 1, proceed directly to subsequent offline troubleshooting |

---

## Diagnostic Steps

### Step 1: Screenshot Analysis (Optional)

Screenshots reflect the instance's current screen state and are direct evidence for determining where the boot failure stopped.

#### Screenshot Acquisition

- If the user has provided a screenshot or one is available in context, proceed directly to analysis
- If not provided, may ask the user for a "first scene of boot failure" screenshot of the failed instance
- **Never obtain real-time screenshots via tools**: The current instance is a running diagnostic instance; real-time screenshots cannot reflect the failure instance's boot scene
- If the user still does not provide one, skip this step and proceed directly to subsequent offline troubleshooting
- **All-black screenshot caution**: a VNC/console capture taken with no active session usually yields an all-black image -- a capture artifact, not necessarily a "no output at all" boot scene. Never conclude P1 from an all-black capture alone: cross-check the capture timestamp against the reported fault time, the console instance status, and, when available, the offline event log (last event timestamp); if still ambiguous, ask the user to recapture during an observed boot attempt in console VNC

#### Secondary Phenomenon Identification for Multiple Boot Failures

After Windows boot failure, the system automatically attempts to restart. After multiple consecutive restart failures, the following two secondary phenomena may appear (neither is the first scene of the fault):

1. **WinRE Recovery Interface**: "Choose an option" (or its localized equivalent) etc.
2. **Boot Manager Summary Error**: `Info: After multiple tries, the operating system on your PC failed to start, so it needs to be repaired.` (The error code shown in the Status field at this point is a summary status code and may not reflect the true root cause)

If the screenshot falls into either of the above cases, advise the user:

> The current screenshot shows a secondary phenomenon after consecutive system boot failures, not the first scene of the fault. It is recommended to restart the instance via the console, observe the boot process in VNC, and capture the actual first boot failure scene (such as BSOD error code, Boot Manager first error screen, etc.) and provide the screenshot.

Even if the user only provides a secondary phenomenon screenshot, subsequent offline troubleshooting can still continue. It is not mandatory for the user to provide a first-scene screenshot.

#### Analysis Approach

Every analysis branch's conclusion MUST append a stage determination field (`Stage = Px`, per the Boot/Session Stage Determination section in SKILL.md) as the initial input for the offline event-log stage evidence collection and routing. When the branch cannot pin a stage (e.g., secondary-phenomenon screenshot), mark it `Stage = undetermined`.

1. Identify Boot Manager error screen:
   - Characteristics: Black background + `Windows Boot Manager` title, or error screen with `File:` / `Status:` / `Info:` fields
   - Extract information: Error code (`Status` field), involved file path (`File` field), error description (`Info` field)
   - Error code classification and routing:

   | Error Code | Typical File Path | Root Cause | Routing |
   |-----------|-------------------|------------|---------|
   | `0xC0000001` | None / `winload.exe` | osdevice inaccessible / winload.exe corrupted | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC000000E` | `winload.exe` | osdevice inaccessible | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC000000F` | `winload.exe` | BCD corrupted / referenced device in boot configuration does not exist | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC0000011` | `\drivers\<Binary>` | Driver file version mismatch with OS version | -> [driver.md](references/offline/driver.md) |
   | `0xC0000017` | `winload.exe` | Insufficient disk space / severe fragmentation / page file anomaly | -> [bcd-boot.md](references/offline/bcd-boot.md) -> [system-config.md](references/offline/system-config.md) |
   | `0xC0000034` | `\Boot\BCD` | BCD file corrupted | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC0000098` | `\<Binary>` | Critical driver version mismatch with OS version | -> [driver.md](references/offline/driver.md) |
   | `0xC0000102` | -- | Driver file content corrupted / disk structure inaccessible | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC000014C` | `\config\system` | Registry hive corrupted or not properly closed | -> [system-config.md](references/offline/system-config.md) |
   | `0xC0000221` | `ntoskrnl.exe` | Kernel file corrupted / file system corrupted | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC0000225` | `\drivers\<driver>.sys` / None | Critical driver missing / boot device inaccessible / system registry corrupted | -> [driver.md](references/offline/driver.md) -> [system-config.md](references/offline/system-config.md) |
   | `0xC0000359` | `\drivers\<Binary>` | System file is 32-bit, needs replacement with 64-bit | -> [system-config.md](references/offline/system-config.md) |
   | `0xC0000428` | `winload.exe` | Digital signature verification failed (preview version expired) | -> [system-config.md](references/offline/system-config.md) (not fixable) |
   | `0xC00000BA` | `\drivers\<filename>` | System file missing or corrupted | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | `0xC0000605` | `winload.exe` | Preview version expired | -> [system-config.md](references/offline/system-config.md) (not fixable) |
   | No error code | `\Boot\BCD` | BCD corrupted / osdevice unknown | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | No error code | `\drivers\<Binary>` | Critical driver missing or corrupted | -> [driver.md](references/offline/driver.md) |
   | No error code | `\config\system` | system registry missing or corrupted | -> [system-config.md](references/offline/system-config.md) |

2. Identify BSOD:
   - Characteristics: Blue background + `:( Your PC ran into a problem` or full-screen blue + STOP error code
   - Extract information: Stop Code, fault module name (e.g., `ntoskrnl.exe`, `viostor.sys`)
   - Routing mapping:

   | Stop Code | Description | Routing |
   |-----------|-------------|---------|
   | `INACCESSIBLE_BOOT_DEVICE` / `0x7B` | Boot sector or disk driver missing | -> [driver.md](references/offline/driver.md) |
   | `CRITICAL_PROCESS_DIED` / `0xEF` | Critical process abnormal exit | -> [system-config.md](references/offline/system-config.md) |
   | `CRITICAL_SERVICE_FAILED` / `0x5A` | Critical service startup failed | -> [system-config.md](references/offline/system-config.md) |
   | `BAD_SYSTEM_CONFIG_INFO` / `0x74` | SYSTEM registry corrupted | -> [system-config.md](references/offline/system-config.md) |
   | `SYSTEM_THREAD_EXCEPTION_NOT_HANDLED` / `0x7E` | Driver or registry hive abnormality | -> [driver.md](references/offline/driver.md) -> [system-config.md](references/offline/system-config.md) |
   | `KERNEL_DATA_INPAGE_ERROR` / `0x7A` | Disk I/O error | -> [driver.md](references/offline/driver.md) |
   | Other Stop Code | -- | Analyze using general knowledge, dynamic routing |

3. Identify no bootable device / boot missing:
   - `no bootable device` -> Primary suspicion is system disk not mounted -> [environment.md](references/offline/environment.md) Step 3 disk presentation check (route to [driver.md](references/offline/driver.md) -> [bcd-boot.md](references/offline/bcd-boot.md) only when disk presentation is normal)
   - `An operating system wasn't found` -> No available system boot -> [bcd-boot.md](references/offline/bcd-boot.md)
   - `missing operating system` -> System files missing -> [bcd-boot.md](references/offline/bcd-boot.md)
   - `bootmgr is missing` -> bootmgr file corrupted or missing -> [bcd-boot.md](references/offline/bcd-boot.md)

4. Identify UEFI Interactive Shell:
   - Characteristics: `UEFI Interactive Shell` / `Shell>` prompt (may have `FS0:\>` device prefix)
   - Two common root causes: (1) NvVars boot variables BootOrder lacks Windows Boot Manager entry (firmware falls back to Shell); (2) Image is MBR/BIOS boot mode but instance boot mode is UEFI, boot mode mismatch
   - Offline disk scenario does not support directly troubleshooting UEFI Shell (fix requires manually executing bcfg and other commands in VNC UEFI Shell); when disk partition check shows no abnormalities, NvVars boot variable anomaly can be a suspicion direction, guiding the user to check UEFI boot configuration in console VNC; if determined to be boot file missing/corrupted, proceed to [bcd-boot.md](references/offline/bcd-boot.md)

5. Identify digital signature verification failure:
   - Characteristics: `windows cannot verify the digital signature for this file` (or its localized equivalent) + `\Windows\System32\Drivers\`
   - Common in Windows 2008 R2: Does not support SHA256 algorithm, cannot recognize SHA256-signed driver files
   - Routing mapping: -> [driver.md](references/offline/driver.md) -> [system-config.md](references/offline/system-config.md)

6. Identify file system check (CHKDSK):
   - Characteristics: `Checking file system on` / `CHKDSK is verifying files` / `CHKDSK is verifying indexes`
   - Indicates the system disk file system has an abnormality, triggering disk self-check
   - Routing mapping: -> [bcd-boot.md](references/offline/bcd-boot.md)

7. Identify Recovery Environment (WinRE):
   - Characteristics: `Choose an option` / `Troubleshoot` / `Recovery` / `Choose your keyboard layout` / `Windows Error Recovery` (or their localized equivalents)
   - Indicates consecutive system boot failures or file corruption/driver incompatibility triggered automatic recovery
   - Routing mapping: -> [bcd-boot.md](references/offline/bcd-boot.md) -> [driver.md](references/offline/driver.md)

8. Identify Sysprep interruption:
   - Characteristics: `The computer unexpectedly restarted or encountered an error` / `Windows installation cannot proceed` (or their localized equivalents)
   - Indicates Sysprep did not complete normally due to instance restart, causing OS initialization abnormality
   - Routing mapping: -> [system-config.md](references/offline/system-config.md)

9. Identify Advanced Boot Options:
   - Characteristics: `Advanced Boot Options` / Safe Mode selection menu
   - Indicates the system detected a boot abnormality and entered advanced options
   - Routing mapping: -> [bcd-boot.md](references/offline/bcd-boot.md) -> [system-config.md](references/offline/system-config.md)

10. Identify Windows Logo stuck:
    - Characteristics: Windows Logo + spinning dots animation, no progress for an extended period
    - Routing mapping: -> [bcd-boot.md](references/offline/bcd-boot.md) -> [driver.md](references/offline/driver.md)

11. Identify black screen (five-tier discrimination; stage definitions follow the Boot/Session Stage Determination section in SKILL.md):

   | Screen phenomenon | Stage | Routing |
   |-------------------|-------|---------|
   | No output at all (not even the logo) | P1 | -> [bcd-boot.md](references/offline/bcd-boot.md) |
   | Blinking cursor only (bootmgr handed off, no logo) | P1/P2 boundary | -> [bcd-boot.md](references/offline/bcd-boot.md); if clean, switch to the P2 chain |
   | Black screen or reboot loop after the logo | P2 | P2 kernel-load chain: boot-start services -> filter drivers -> [driver.md](references/offline/driver.md) -> [device-tree.md](references/offline/device-tree.md) |
   | Black screen after the logon UI flashes briefly | P4 | -> [system-config.md](references/offline/system-config.md) (Winlogon items) -> [driver.md](references/offline/driver.md) (display driver) |
   | Black screen WITH a movable mouse pointer | P5 (kernel + win32k alive) | -> [system-config.md](references/offline/system-config.md) (Shell/Userinit) -> [cloud-agent.md](references/offline/cloud-agent.md) |
   | Black screen after reaching the desktop | P5 | same as above + display driver |

---

## Cross-References

| Type | Trigger Condition | Target |
|------|-------------------|--------|
| Chain successor | Boot chain / BCD issue | -> bcd-boot.md |
| Chain successor | Disk / partition issue | -> disk-partition.md |
| Chain successor | Storage driver issue | -> driver.md |
| Chain successor | BitLocker / encryption signs | -> bitlocker.md |
| Chain successor | Black screen / Shell not started / system configuration issue | -> system-config.md |
| Chain successor | Cloud Assist / vminit / AliyunService issue | -> cloud-agent.md |
| Chain successor | Network configuration issue | -> network.md |
| Chain successor | Disk environment / mount status issue | -> environment.md |
| Chain successor | Registry configuration issue | -> registry.md |
