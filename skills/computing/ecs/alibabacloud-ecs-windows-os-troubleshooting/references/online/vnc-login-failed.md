# VNC Login Failure Troubleshooting

## Function Description

Troubleshooting file for inability to log in to an instance via VNC, covering the `GuestOS.VNCLoginFailed` problem domain (domain definition see [WORKFLOW-GUIDE.md](references/online/WORKFLOW-GUIDE.md) "Online Problem Domain Routing Table"): VNC black screen, white screen disconnection, no response. The troubleshooting sequence is "VNC output check -> Memory 100% render failure evaluation -> GPU/bare metal specification evaluation". Covers stage P4 (Winlogon/logon UI) of the boot/session stage model defined in SKILL.md.

**Input**: User problem description (required), Instance ID (required), VNC screen screenshot (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Trigger Conditions

- User reports console VNC black screen, white screen, disconnection, or no display
- Classification matches "Unable to log in to instance via VNC (`VNCLoginFailed`)"

## Step Selection Guide

This file contains 3 diagnostic steps, executed in order; Step 1 results determine the subsequent branch:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| VNC black screen/white screen/no display | Step 1 -> Step 2 -> Step 3 |
| VNC screen normal but no response to operations | After Step 1, go to [desktop-shell.md](references/online/desktop-shell.md) (Console session state) |

## Diagnostic Steps

### Step 1: VNC Output Check (Management Plane)

**Data Collection**: Open the instance VNC via the cloud platform console or obtain a console screenshot/screen output, confirm the display status (black screen / white screen / disconnected / normal desktop / BSOD / boot screen); also confirm the instance running status

> This step is completed on the management plane; there is no in-instance collection script. When the instance status is "Not Running" or the screen shows a boot/BSOD screen, redirect to the offline chain or [system-crash.md](references/online/system-crash.md); do not continue in this file.

> **All-black capture caution**: a VNC/console capture taken with no attached session usually yields an all-black image -- a capture artifact, not necessarily a genuine black screen. Before branching on an all-black scene, secondary-confirm it: cross-check the capture timestamp against the reported fault time, the instance status, and recent event-log evidence (last event timestamp / BugCheck); when ambiguous, recapture after a console restart while observing the boot attempt.

**Analysis Approach**:

1. Branch by display status:
   - Screen is normal desktop but keyboard/mouse unresponsive -> Go to [desktop-shell.md](references/online/desktop-shell.md) to check Console session state
   - Screen shows BSOD/boot abnormality -> Redirect to corresponding offline chain or [system-crash.md](references/online/system-crash.md)
   - Screen is completely black or white screen then disconnects, instance status "Running" -> Continue to Step 2
2. Record the VNC screen status as subsequent evaluation evidence

### Step 2: Memory 100% Render Failure Evaluation

**Data Collection**: Collect total memory and available memory, Top 10 memory-consuming processes, memory resource exhaustion events (Event 2004); evaluate whether memory exhaustion caused VNC render failure

- PowerShell script: [vnc-login-failed.ps1](references/online/scripts/vnc-login-failed.ps1) Section Step 2

**Analysis Approach**:

1. Check memory level and exhaustion evidence:
   - Normal: Available memory sufficient (>=500MB), no 2004 events
   - Abnormal: Available memory near 0 (usage 100%) or recent 2004 memory exhaustion events exist -> **Root cause**: Memory exhaustion causing VNC render failure (MemoryExhaustionVNCRenderFailure), **Severity**: Critical; record Top memory processes as evidence, fix direction is to terminate abnormally consuming processes or upgrade configuration; fix recommendation routes to [performance-slow.md](references/online/performance-slow.md) for in-depth identification of consumption sources

### Step 3: GPU/Bare Metal Specification Evaluation

**Data Collection**: Collect display controller and driver status, machine type clues (manufacturer/model), display-related Error/Warning events (Display/dxgkrnl/GPU driver); combine with management plane instance specification information to determine whether it is a GPU/bare metal specification

- PowerShell script: [vnc-login-failed.ps1](references/online/scripts/vnc-login-failed.ps1) Section Step 3

**Analysis Approach**:

1. Check display driver and specification association:
   - Normal: Display controller status normal, driver complete, no display-related error events
   - Abnormal: Instance is GPU/bare metal specification and display driver is missing/abnormal (Status not OK, driver error code, dxgkrnl/GPU driver error events) -> **Root cause**: GPU/bare metal specification display driver abnormality causing no VNC output (DisplayDriverFault), **Severity**: Critical; fix recommendation routes to [device-driver.md](references/online/fixes/device-driver.md) (driver reinstall/rollback)
2. All normal -> Record the troubleshooting scope as-is, recommend combining with management plane VNC backend troubleshooting (non-GuestOS root cause) and escalate to expert support

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 1 screen normal but unresponsive | -> [desktop-shell.md](references/online/desktop-shell.md) |
| Conditional jump | Step 1 screen shows BSOD/boot abnormality | -> [system-crash.md](references/online/system-crash.md) / Offline chain |
| Conditional jump | Step 2 confirms memory exhaustion | -> [performance-slow.md](references/online/performance-slow.md) to identify consumption source |
| Conditional jump | Step 3 confirms display driver abnormality | -> [device-driver.md](references/online/fixes/device-driver.md) (driver reinstall/rollback) |
| Chain successor | Root cause not confirmed in this file | -> Record troubleshooting scope and all findings as-is, recommend combining with management plane troubleshooting and escalate to expert support |

## Fix Recommendations

Fix plans for root causes confirmed in this file are addressed by the conditional jump targets in the Cross-References table above: memory exhaustion -> [performance-slow.md](references/online/performance-slow.md); GPU/bare metal display driver abnormality -> [fixes/device-driver.md](references/online/fixes/device-driver.md) (driver reinstall/rollback); non-GuestOS (management plane) root causes -> no GuestOS fix, escalate per the chain successor row.
