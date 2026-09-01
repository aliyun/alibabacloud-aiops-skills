# Security BitLocker Diagnosis

## Overview

Diagnoses Windows BitLocker encryption status and recovery key status. Covers 2 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|----------------------|-------------------|
| System prompts for recovery key at startup | Step 1 (BitLocker encryption status) |
| Cannot access encrypted disk data | Step 2 (recovery key status) |

## Diagnostic Steps

### Step 1: Check BitLocker Encryption Status

**Data Collection**:

> Collection target: Obtain BitLocker encryption status, protection method, and unlock status for all volumes

**Analysis Approach**:

- PowerShell script: [security-bitlocker.ps1](references/online/scripts/security-bitlocker.ps1) Section Step 1

1. Check whether the BitLocker service exists:
   - If the service does not exist, BitLocker is not installed; no need to continue this step
2. Check volume encryption status:
   - Normal: ProtectionStatus = 0 (not encrypted) or ProtectionStatus = 1 and ConversionStatus = 1 (encrypted)
   - Abnormal: ConversionStatus = 2/4 (encryption in progress/paused) -> **Root cause**: BitLocker encryption incomplete; disk I/O performance may be affected, **Severity**: Warning
   - Abnormal: ProtectionStatus = 1 and the system requires recovery key input -> **Root cause**: BitLocker triggered recovery mode; system cannot boot normally, **Severity**: Critical

### Step 2: Check Recovery Key Status

**Data Collection**:

> Collection target: Check whether BitLocker recovery key protectors exist; confirm recovery key availability

**Analysis Approach**:

- PowerShell script: [security-bitlocker.ps1](references/online/scripts/security-bitlocker.ps1) Section Step 2

1. Check key protectors:
   - Normal: At least one key protector exists (e.g., TPM, NumericalPassword, etc.)
   - Abnormal: No key protector -> **Root cause**: BitLocker encrypted volume has no recovery key; once recovery mode is triggered, it cannot be unlocked, **Severity**: Critical
2. Check BitLocker event logs:
   - Focus on error and warning events, especially TPM communication failures, key protector failures, etc.
   - Such events found -> **Root cause**: BitLocker runtime error; may trigger recovery mode, **Severity**: Warning

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|-------------------|-------------|
| Conditional jump | BitLocker causing disk I/O performance degradation | -> [performance-slow.md](references/online/performance-slow.md) |
| Chain successor | Root cause not confirmed in this file | -> [storage-disk.md](references/online/storage-disk.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [security-bitlocker.md](references/online/fixes/security-bitlocker.md).
