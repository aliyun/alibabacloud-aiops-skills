# Identity User Profiles Diagnostics

## Function Description

Diagnoses Windows user profile corruption, folder redirection failures, and performance issues caused by custom/default user profiles. Covers 3 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Step |
|-------------|---------------|
| Loads a temporary profile after login, all desktop settings lost | Step 1 (User Profile Status) |
| Desktop/Documents folder points to an unreachable path | Step 2 (Folder Redirection) |
| Slow login, system performance degradation after login, abnormal application of custom/default user profile | Step 3 (Custom/Default User Profile Check) |

## Diagnostic Steps

### Step 1: User Profile Status Check

**Data Collection**:

> Collection target: Check user profile registry entries, confirm whether corruption or temporary profiles exist

- PowerShell script: [identity-user-profiles.ps1](references/online/scripts/identity-user-profiles.ps1) Section Step 1

**Analysis Approach**:

1. Check profile registry entries:
   - Normal: All profiles have normal State and no .bak copies
   - Abnormal: Profile registry entry ending with .bak exists -> **Root cause**: User profile corrupted, system loaded a temporary profile, **Severity**: Critical
   - Abnormal: ProfileImagePath points to TEMP directory -> **Root cause**: Temporary profile is in use, **Severity**: Critical

> When a user profile is corrupted, Windows creates a temporary profile. The user will find that all desktop settings, files, etc. are lost.

### Step 2: Folder Redirection Check

**Data Collection**:

> Collection target: Check user Shell folder redirection configuration

- PowerShell script: [identity-user-profiles.ps1](references/online/scripts/identity-user-profiles.ps1) Section Step 2

**Analysis Approach**:

1. Check Shell Folders accessibility:
   - Normal: All Shell Folders paths are accessible
   - Abnormal: Redirection target unreachable (network path disconnected) -> **Root cause**: Folder redirection failed, user cannot access Desktop/Documents, **Severity**: Warning

### Step 3: Custom/Default User Profile WebCache Check

**Data Collection**:

> Collection target: Check for Event ID 454 (ESENT database recovery/restore failure). WebCacheLock.dat and the WebCache folder normally exist in all user profiles and should not be used as diagnostic criteria. The root cause of KB 4056823 is: when customizing the default user profile, the source account's cached database lock copy is copied into Default, and when new users log in, the database cannot initialize, producing Event ID 454.

- PowerShell script: [identity-user-profiles.ps1](references/online/scripts/identity-user-profiles.ps1) Section Step 3

**Analysis Approach**:

1. Check for Event ID 454:
   - Normal: No Event ID 454 records
   - Abnormal: Event ID 454 exists, and Message contains "Database recovery/restore failed" -> **Root cause**: Default user profile contains a locked copy of another user's cached database, database initialization fails when new users log in, **Severity**: Critical

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Redirection target is a network path and unreachable | -> [networking-dns.md](references/online/networking-dns.md) |
| Conditional jump | Slow login / performance abnormality, and Step 3 did not confirm root cause | -> [performance-slow.md](references/online/performance-slow.md) |
| Chained successor | Root cause not confirmed in this file | -> [identity-permission.md](references/online/identity-permission.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [identity-user-profiles.md](references/online/fixes/identity-user-profiles.md).
