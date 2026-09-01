# Identity Account Diagnostics

## Function Description

Diagnoses Windows account lockout status, password and lockout policies, password expiration, and built-in Administrator account existence. Covers 4 diagnostic steps.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Step |
|-------------|---------------|
| Cannot log in despite correct password, prompted "account is currently locked out" | Step 1 (Account Lockout Status) |
| Password cannot be set, prompted that complexity/length requirements are not met | Step 2 (Password and Lockout Policy) |
| Account frequently locked out, suspected brute force attack | Step 1 + Step 2 |
| Password suddenly expired, RDP prompts to change password | Step 3 (Password Expiration Status) |
| Cannot log in after password reset, automated script execution fails | Step 4 (Built-in Administrator Account) |

## Diagnostic Steps

### Step 1: Account Lockout Status Check

**Data Collection**:

> Collection target: Check lockout and disabled status of local user accounts, and trace the lockout source

- PowerShell script: [identity-account.ps1](references/online/scripts/identity-account.ps1) Section Step 1

**Analysis Approach**:

1. Check account lockout status:
   - Normal: No account is locked (Lockout=False)
   - Abnormal: Account with Lockout=True or EventID 4740 events exist -> **Root cause**: Account is locked (RDPAccountLocked), **Severity**: Critical
2. Lockout source tracing (when 4740 events are found):
   - **Analysis principle: Group by source IP first, attribute independently for each group, never merge inferences across records**
   - Group 4625 events by SourceNetworkAddress, report failure count, time range, and LogonType separately for each group
   - Source is local machine (SourceIP is `-` or `127.0.0.1`) -> Investigate scheduled tasks/services using old passwords (see service account investigation below)
   - Source is external IP -> Brute force attack, recommend restricting RDP source IPs or enabling NLA
   - When both local and external sources exist, report them separately; do not attribute local failures to external IPs
   - The CallerComputerName in 4740 events indicates the machine that processed the lockout (local account lockout always shows the local machine name), which is not equivalent to the attack source
   - LogonType=10 indicates RDP login attempt, LogonType=3 indicates network logon (SMB/network authentication)
3. Service account credential expiration investigation (when lockout source is local):
   - Check Windows services running under the account: `Get-CimInstance Win32_Service | Where-Object { $_.StartName -like '*<LockedUser>*' }`
   - Check scheduled tasks using the account: `Get-ScheduledTask | Where-Object { $_.Principal.UserId -like '*<LockedUser>*' }`
   - If services/tasks using old passwords are found -> **Root cause**: Service credential expiration causes repeated authentication failures triggering lockout
4. Check account disabled status (excluding DefaultAccount/WDAGUtilityAccount/Guest):
   - Normal: Target account Disabled=False
   - Abnormal: User account Disabled=True -> **Root cause**: Account is disabled (RDPAccountDisabled), **Severity**: Warning

### Step 2: Password and Lockout Policy Check

**Data Collection**:

> Collection target: Obtain complete configuration of local password policy and account lockout policy

- PowerShell script: [identity-account.ps1](references/online/scripts/identity-account.ps1) Section Step 2

**Analysis Approach**:

1. Check password policy configuration:
   - Normal: Minimum password length >= 8, PasswordComplexity = 1 (enabled)
   - Abnormal: Minimum length is 0 -> Empty passwords allowed, high security risk, **Severity**: Warning
   - Abnormal: Minimum password length too high (>14) or complexity configuration unreasonable -> May cause difficulty in setting passwords
2. Check account lockout policy:
   - Lockout threshold is 0 (never lock) -> Accounts will not be locked due to incorrect passwords, brute force attacks are unimpeded
   - Lockout threshold too low (e.g., 3 attempts) -> Account lockout easily triggered
   - Lockout duration too long -> Wait time after lockout is too long
   - Recommended configuration: threshold=5~10, duration=15~30min, observation window=15~30min

### Step 3: Password Expiration Status Check

**Data Collection**:

> Collection target: Check whether user passwords have expired or are about to expire

- PowerShell script: [identity-account.ps1](references/online/scripts/identity-account.ps1) Section Step 3

**Analysis Approach**:

1. Check password expiration status:
   - Normal: All enabled user passwords are not expired
   - Abnormal: Enabled user password has expired -> **Root cause**: Password has expired, may cause RDP login failure, **Severity**: Warning

### Step 4: Built-in Administrator Account Check

**Data Collection**:

> Collection target: Confirm whether the built-in Administrator account exists

- PowerShell script: [identity-account.ps1](references/online/scripts/identity-account.ps1) Section Step 4

**Analysis Approach**:

1. Check Administrator account existence:
   - Normal: Administrator account exists
   - Abnormal: Administrator account does not exist -> **Root cause**: Built-in administrator account missing (AdminUserNotExist), **Severity**: Warning

> Alibaba Cloud ECS instances typically perform password reset and management operations through the Administrator account.

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Account locked and user reports RDP login failure | -> [rdp-auth.md](references/online/rdp-auth.md) (check remote login permissions and ForceGuest configuration) |
| Conditional jump | Domain account related issues (domain login failure, Secure Channel abnormality) | -> [identity-ad.md](references/online/identity-ad.md) |
| Conditional jump | Account disabled and involves Group Policy | -> [system-gpo.md](references/online/system-gpo.md) |
| Conditional jump | Password/lockout policy suspected to be pushed via GPO (locally modified but restored by gpupdate) | -> [system-gpo.md](references/online/system-gpo.md) (Step 1 to confirm GPO source) |
| Conditional jump | Password expiration or lockout policy causing Kerberos authentication abnormality | -> [identity-auth.md](references/online/identity-auth.md) |
| Chained successor | Root cause not confirmed in this file, need further check of user permissions and group membership | -> [identity-permission.md](references/online/identity-permission.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [identity-account.md](references/online/fixes/identity-account.md).
