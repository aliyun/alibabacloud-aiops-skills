# Identity Auth Diagnostics

## Function Description

Diagnoses Windows Kerberos clock skew, NTLM authentication configuration, and SPN configuration. Covers 3 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Step |
|-------------|---------------|
| Domain login failure, prompted excessive clock skew | Step 1 (Kerberos Clock Skew) |
| Remote access denied, NTLMv1 blocked by policy | Step 2 (NTLM Authentication Configuration) |
| Kerberos delegation failure for services such as SQL Server | Step 3 (SPN Configuration) |

## Diagnostic Steps

### Step 1: Kerberos Clock Skew Check

**Data Collection**:

> Collection target: Check the time difference between the local machine and domain controller (Kerberos allows 5 minutes skew by default)

- PowerShell script: [identity-auth.ps1](references/online/scripts/identity-auth.ps1) Section Step 1

**Analysis Approach**:

1. Check time skew with domain controller:
   - Normal: Skew < 5 minutes
   - Abnormal: Skew >= 5 minutes -> **Root cause**: Kerberos clock skew too large, will cause domain authentication failure, **Severity**: Critical
2. If unable to connect to domain controller -> Refer to [identity-ad.md](references/online/identity-ad.md) to check domain controller reachability

### Step 2: NTLM Authentication Configuration Check

**Data Collection**:

> Collection target: Check NTLM authentication level configuration

- PowerShell script: [identity-auth.ps1](references/online/scripts/identity-auth.ps1) Section Step 2

**Analysis Approach**:

1. Check LmCompatibilityLevel value:
   - 0-2: Allows NTLMv1 -> Higher security risk, but good compatibility
   - 3 (recommended): Send NTLMv2 only -> **Normal**
   - 4-5: Rejects NTLMv1 -> High security, but may cause old client authentication failures

> If LmCompatibilityLevel >= 4 and old clients fail to connect, you may need to lower this value.

### Step 3: SPN Configuration Check

**Data Collection**:

> Collection target: Check Service Principal Name registration status

- PowerShell script: [identity-auth.ps1](references/online/scripts/identity-auth.ps1) Section Step 3

**Analysis Approach**:

1. Check SPN registration:
   - Normal: SPN list displays normally
   - Abnormal: Duplicate SPNs shown or setspn reports errors -> SPN conflict may exist, affecting Kerberos delegation

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Clock skew involves NTP configuration | -> [system-time.md](references/online/system-time.md) |
| Chained successor | Root cause not confirmed in this file | -> [identity-ad.md](references/online/identity-ad.md) |

## Fix Recommendations

### Fix 1: Fix Clock Skew

**Applicable scenario**: Kerberos clock skew too large

```powershell
# Force time sync with domain controller
w32tm /resync /rediscover
# If W32Time is not running
Start-Service W32Time
w32tm /resync /rediscover
```

**Verification**:

```powershell
w32tm /query /status | Select-String "Last successful sync time"
```

Expected result: Shows recent sync time, with time skew within 5 minutes of current time

### Fix 2: Adjust NTLM Authentication Level

**Applicable scenario**: NTLM level too high causing old client failures

```powershell
# Set to send NTLMv2 only (balance security and compatibility)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'LmCompatibilityLevel' -Value 3 -Type DWord
```

**Verification**:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa' -Name 'LmCompatibilityLevel' | Select-Object LmCompatibilityLevel
```

Expected result: `LmCompatibilityLevel` value is `3`
