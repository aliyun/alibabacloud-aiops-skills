# Desktop Printing Diagnostics

## Function Description

Diagnoses Windows Print Spooler service, print driver installation, and print output status. Covers 3 known issues.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Print service stopped, print queue stuck | Step 1 (Print Spooler service) |
| Cannot add printer, driver installation error | Step 2 (Print driver installation) |
| Print job submitted but no output or garbled output | Step 3 (Print output status) |

## Diagnostic Steps

### Step 1: Check Print Spooler Service

**Data Collection**:

> Collection target: Obtain Print Spooler service status and print queue information

**Analysis Approach**:

- PowerShell script: [desktop-printing.ps1](references/online/scripts/desktop-printing.ps1) Section Step 1

1. Check Spooler service status:
   - Normal: Status is Running
   - Abnormal: Service not running -> **Root cause**: Print Spooler service not started, print functionality completely unavailable, **Severity**: Critical
   - Abnormal: Service startup type is Disabled -> **Root cause**: Print Spooler service disabled (possibly for security hardening purposes), **Severity**: Warning
2. Check print queue:
   - Abnormal: Large number of print jobs queued with Error status -> **Root cause**: Print queue blocked, print jobs cannot be processed, **Severity**: Warning
3. Check Spooler crash events:
   - Frequent crashes -> **Root cause**: Print Spooler repeatedly crashing, possibly caused by corrupted print driver or print job, **Severity**: Critical

### Step 2: Check Print Driver Installation

**Data Collection**:

> Collection target: Obtain installed printer and print driver list

**Analysis Approach**:

- PowerShell script: [desktop-printing.ps1](references/online/scripts/desktop-printing.ps1) Section Step 2

1. Check printer status:
   - Normal: PrinterStatus is Idle or Printing
   - Abnormal: PrinterStatus is Error or Offline -> **Root cause**: Printer status abnormal, possibly driver issue or port configuration error, **Severity**: Warning
2. Check driver installation:
   - Abnormal: Printer has no corresponding driver -> **Root cause**: Print driver not installed, cannot print normally, **Severity**: Critical
3. Check TCP/IP port:
   - Abnormal: Port address misconfigured or unreachable -> **Root cause**: Print port configuration abnormal, **Severity**: Warning

### Step 3: Check Print Output Status

**Data Collection**:

> Collection target: Check print Spool directory and recent print events

**Analysis Approach**:

- PowerShell script: [desktop-printing.ps1](references/online/scripts/desktop-printing.ps1) Section Step 3
- PrintService/Operational is a non-standard channel, fallback to manual execution by user when collector does not support it

1. Check Spool directory:
   - Normal: Directory exists, few files (no backlog)
   - Abnormal: Large number of files accumulated or occupying large space -> **Root cause**: Print Spool files accumulated, may cause Spooler service crash or insufficient disk space, **Severity**: Warning
2. Check print event log:
   - Focus on error events, especially driver load failures, port communication failures, etc.
   - Such events -> correlate to specific root causes (driver issue/network issue/permission issue)

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Print port network unreachable | -> [networking-tcpip.md](references/online/networking-tcpip.md) |
| Conditional jump | Spool directory permission issue | -> [identity-permission.md](references/online/identity-permission.md) |
| Chain successor | No root cause confirmed in this file | -> [device-driver.md](references/online/device-driver.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [desktop-printing.md](references/online/fixes/desktop-printing.md).
