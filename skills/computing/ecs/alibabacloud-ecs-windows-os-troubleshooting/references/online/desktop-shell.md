# Desktop Shell Diagnostics

## Function Description

Diagnoses Windows logon Shell configuration, Explorer.exe process status, taskbar/start menu responsiveness, Console session status, DWM and DPI scaling. Covers 7 known issues. Covers stage P5 (Shell/user desktop) of the boot/session stage model defined in SKILL.md.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Black screen or only command-line window after logon, no desktop | Step 1 (Logon Shell configuration) |
| Only wallpaper with no taskbar after logon | Step 2 (Explorer.exe process status) |
| No response when clicking taskbar or start menu | Step 3 (Taskbar/Start menu responsiveness) |
| Blank desktop, Explorer not loading desktop folder | Step 2 (Explorer.exe process status) |
| Window transparency effects disappeared, dragging lag | Step 4 (DWM status) |
| Application interface blurry, element sizes incorrect | Step 5 (DPI scaling) |
| VNC black screen, console unresponsive | Step 6 (Console session status) |

## Diagnostic Steps

### Step 1: Check Logon Shell Configuration

**Data Collection**:

> Collection target: Obtain WinLogon Shell configuration, confirm the default Shell program launched after logon

**Analysis Approach**:

- PowerShell script: [desktop-shell.ps1](references/online/scripts/desktop-shell.ps1) Section Step 1

1. Check Shell configuration:
   - Normal: Shell is `explorer.exe`
   - Abnormal: Shell is empty or points to non-standard program -> **Root cause**: Logon Shell configuration abnormal, desktop cannot be displayed after logon, **Severity**: Critical
2. Check Userinit configuration:
   - Normal: Contains `userinit.exe` path
   - Abnormal: Empty or points to abnormal program -> **Root cause**: Userinit configuration abnormal, logon process cannot initialize properly, **Severity**: Critical

> If Shell configuration is abnormal and C:\ permissions also have issues, see -> [identity-permission.md](references/online/identity-permission.md)

### Step 2: Check Explorer.exe Process Status

**Data Collection**:

> Collection target: Check whether Explorer.exe process is running and its resource usage

**Analysis Approach**:

- PowerShell script: [desktop-shell.ps1](references/online/scripts/desktop-shell.ps1) Section Step 2

1. Check whether Explorer process exists:
   - Normal: At least one explorer.exe instance running
   - Abnormal: Not running -> **Root cause**: Explorer.exe not started, desktop/taskbar/start menu unavailable, **Severity**: Critical
2. Check crash events:
   - Frequent Explorer crash events found -> **Root cause**: Explorer.exe repeatedly crashing, possibly caused by third-party Shell extensions or corrupted configuration, **Severity**: Warning

### Step 3: Check Taskbar/Start Menu Responsiveness

**Data Collection**:

> Collection target: Check services and configurations related to taskbar and start menu

**Analysis Approach**:

- PowerShell script: [desktop-shell.ps1](references/online/scripts/desktop-shell.ps1) Section Step 3

1. Check Shell Experience Host process (Windows 10+):
   - Normal: Both ShellExperienceHost and StartMenuExperienceHost are running
   - Abnormal: Process not running -> **Root cause**: Start menu experience process not started, start menu may be unresponsive, **Severity**: Warning

### Step 4: Check DWM Status

**Data Collection**:

> Collection target: Check Desktop Window Manager service and process status

**Analysis Approach**:

- PowerShell script: [desktop-shell.ps1](references/online/scripts/desktop-shell.ps1) Section Step 4

1. Check DWM service and process:
   - Normal: UxSms service running, dwm.exe process exists
   - Abnormal: UxSms not running or dwm.exe does not exist -> **Root cause**: DWM not started, window transparency effects and composite rendering unavailable, **Severity**: Warning

### Step 5: Check DPI Scaling

**Data Collection**:

> Collection target: Obtain system DPI scaling settings

**Analysis Approach**:

- PowerShell script: [desktop-shell.ps1](references/online/scripts/desktop-shell.ps1) Section Step 5

1. Check DPI scaling ratio:
   - Normal: 96 DPI (100%) or a reasonable scaling ratio
   - Abnormal: Abnormally high or abnormally low DPI value -> **Root cause**: DPI scaling configuration abnormal, causing application interface blur or incorrect element sizes, **Severity**: Info

### Step 6: Check Console Session Status

**Data Collection**:

> Collection target: Obtain all RD session information, focus on Console session status

**Analysis Approach**:

- PowerShell script: [desktop-shell.ps1](references/online/scripts/desktop-shell.ps1) Section Step 6

1. Check Console session status:
   - Normal: Console session State is Connected or Active
   - Abnormal: Console session State is not Connected/Active (e.g. Disc/Down), or Console session not found -> **Root cause**: Console session status abnormal, may cause VNC connection black screen or system unresponsive (ConsoleSessionStatusError), **Severity**: Warning

> Console session is the Windows physical console session (Session 0 or 1). If its status is abnormal, it may cause VNC connection black screen or system unresponsive.

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Step 1 Shell configuration abnormal and C:\ permissions have issues | -> [identity-permission.md](references/online/identity-permission.md) |
| Conditional jump | Explorer crash caused by suspicious program | -> [security-malware.md](references/online/security-malware.md) |
| Chain successor | No root cause confirmed in this file | -> [desktop-app.md](references/online/desktop-app.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [desktop-shell.md](references/online/fixes/desktop-shell.md).
