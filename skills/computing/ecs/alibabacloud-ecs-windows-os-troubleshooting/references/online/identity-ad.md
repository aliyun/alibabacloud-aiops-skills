# Identity Active Directory Diagnostics

## Function Description

Diagnoses Windows SID conflicts, domain secure channel status, domain controller reachability, computer account password, and LDAPS connections. Covers 5 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Step |
|-------------|---------------|
| Multiple domain machines experiencing authentication abnormality or permission confusion | Step 1 (SID Conflict) |
| Prompted "the trust relationship between this workstation and the primary domain failed", cannot log in with domain account | Step 2 (Domain Secure Channel Status) |
| Domain login timeout, Group Policy cannot update, domain resource access fails | Step 3 (Domain Controller Reachability) |
| Cannot join domain after reboot, prompted computer account verification failure | Step 4 (Computer Account Password) |
| LDAP over SSL connection failure, domain service secure communication abnormality | Step 5 (LDAPS Connection) |

## Diagnostic Steps

### Step 1: Check SID Conflict

**Data Collection**:

> Collection target: Obtain the local machine SID to determine whether a SID duplication exists (typically occurs in cloned image scenarios without Sysprep)

- PowerShell script: [identity-ad.ps1](references/online/scripts/identity-ad.ps1) Section Step 1

**Analysis Approach**:

1. Check image state:
   - Normal: ImageState is `IMAGE_STATE_COMPLETE`
   - Abnormal: ImageState is not `IMAGE_STATE_COMPLETE` (e.g., `IMAGE_STATE_GENERALIZE_RESEAL_TO_OOBE`) -> **Root cause**: Sysprep not completed, SID conflict may exist, **Severity**: Warning
2. Check GeneralizationState:
   - Normal: GeneralizationState = 7 (generalization completed)
   - Abnormal: Other values -> **Root cause**: System has not been through proper Sysprep generalization, multiple cloned instances may share the same SID, **Severity**: Warning

### Step 2: Check Domain Secure Channel Status

**Data Collection**:

> Collection target: Verify whether the secure channel between the local machine and domain controller is normal, and domain membership information

- PowerShell script: [identity-ad.ps1](references/online/scripts/identity-ad.ps1) Section Step 2

**Analysis Approach**:

1. Check whether the computer is domain-joined:
   - If PartOfDomain is False, this step does not need to continue
2. Check secure channel test result:
   - Normal: Test-ComputerSecureChannel returns True
   - Abnormal: Returns False or throws an exception -> **Root cause**: Domain secure channel is broken, domain account login and Group Policy updates will fail, **Severity**: Critical
3. Check Netlogon service status:
   - Normal: Status is Running
   - Abnormal: Service not running -> **Root cause**: Netlogon service not started causing secure channel unavailable, **Severity**: Critical

### Step 3: Check Domain Controller Reachability

**Data Collection**:

> Collection target: Verify DNS resolution and network reachability of the domain controller

- PowerShell script: [identity-ad.ps1](references/online/scripts/identity-ad.ps1) Section Step 3

**Analysis Approach**:

1. Check DC SRV record resolution:
   - Normal: At least one _ldap._tcp.dc._msdcs SRV record can be resolved
   - Abnormal: Resolution fails -> **Root cause**: DNS cannot resolve domain controller SRV records, domain services unavailable, **Severity**: Critical
2. Check LDAP port connectivity:
   - Normal: TCP port 389 is reachable
   - Abnormal: Connection fails -> **Root cause**: Domain controller LDAP port unreachable, **Severity**: Critical
3. Check Kerberos port connectivity:
   - Normal: TCP port 88 is reachable
   - Abnormal: Connection fails -> **Root cause**: Domain controller Kerberos port unreachable, domain authentication will fail, **Severity**: Critical

> If the domain controller is unreachable but basic network connectivity is normal, see -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP 88/389/636 port rules)

### Step 4: Check Computer Account Password

**Data Collection**:

> Collection target: Obtain the last update time of the computer account password and password change policy configuration

- PowerShell script: [identity-ad.ps1](references/online/scripts/identity-ad.ps1) Section Step 4

**Analysis Approach**:

1. Check password change policy:
   - Normal: DisablePasswordChange is 0 or does not exist
   - Abnormal: DisablePasswordChange is 1 -> **Root cause**: Computer account password auto-change is disabled, may lead to secure channel trust failure over time, **Severity**: Warning
2. Check Netlogon events:
   - Focus on EventID 5722 (computer account password verification failure), 5723 (secure channel setup failure)
   - Such events appear -> **Root cause**: Computer account password out of sync with domain controller, **Severity**: Critical

### Step 5: Check LDAPS Connection

**Data Collection**:

> Collection target: Verify connectivity and certificate status of LDAP over SSL (port 636)

- PowerShell script: [identity-ad.ps1](references/online/scripts/identity-ad.ps1) Section Step 5

**Analysis Approach**:

1. Check LDAPS port connectivity:
   - Normal: TCP port 636 is reachable
   - Abnormal: Connection fails -> **Root cause**: LDAPS port unreachable, encrypted LDAP communication unavailable, **Severity**: Warning
2. Check LDAP client signing policy:
   - Normal: Value is 0 or 1 (not required or negotiate signing)
   - Abnormal: Value is 2 and LDAPS is unavailable -> **Root cause**: LDAP client requires signing but LDAPS connection fails, domain communication will be blocked, **Severity**: Critical

> If LDAPS certificate issues, see -> [security-certificates.md](references/online/security-certificates.md)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 3 domain controller port unreachable but basic network connectivity is normal | -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP 88/389/636 port rules) |
| Conditional jump | Step 5 LDAPS certificate issues | -> [security-certificates.md](references/online/security-certificates.md) |
| Conditional jump | Domain time out of sync causing Kerberos authentication failure | -> [system-time.md](references/online/system-time.md) |
| Chained successor | Root cause not confirmed in this file | -> None (domain-related issues are typically located within this file) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [identity-ad.md](references/online/fixes/identity-ad.md).
