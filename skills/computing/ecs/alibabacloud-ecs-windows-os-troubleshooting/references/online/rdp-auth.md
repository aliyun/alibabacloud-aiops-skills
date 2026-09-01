# RDP Authentication Diagnostics

## Feature Description

Diagnoses remote desktop authentication and permission issues. Covers CredSSP configuration, account lockout status, remote logon permissions, security layer configuration, password error audit events, ForceGuest access mode, totaling 6 diagnostic steps.

**Input**: User problem description (required), authentication error message (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| Error "An authentication error has occurred. The function requested is not supported" or prompt "CredSSP encryption oracle remediation" | Step 1 (CredSSP Configuration) |
| Authentication error (An authentication error), not CredSSP related | Step 4 (Security Layer Configuration) -> Step 1 (CredSSP Configuration) |
| Account locked | Step 2 (Account Lockout Status) -> Step 5 (Password Error Events) |
| Password error, incorrect credentials | Step 5 (Password Error Events) -> Step 2 (Account Lockout) |
| RDP prompts password error but the password is actually correct | Step 6 (ForceGuest Access Mode) -> Step 5 (Password Error Events) |
| No remote logon permission | Step 3 (Remote Logon Permission) |
| Non-admin account remote logon failure (e.g., mapped as Guest) | Step 6 (ForceGuest Access Mode) |
| Prompt "logon denied" but user is in Remote Desktop Users group | Step 3 (Remote Logon Permission, check SeDenyRemoteInteractiveLogonRight) |

## Diagnostic Steps

### Step 1: CredSSP Configuration Check

> Background: CVE-2018-0886 is a remote code execution vulnerability in the CredSSP protocol. Microsoft released a security update in 2018 and changed the default policy from Vulnerable to Mitigated in subsequent updates, causing patched clients to be unable to connect to unpatched servers (and vice versa).

**Data Collection**: Get local CredSSP patch status (TSpkg.dll file version) and AllowEncryptionOracle policy configuration (from two sources: local registry CredSSP\Parameters and Group Policy CredentialsDelegation)

- PowerShell script: [rdp-auth.ps1](references/online/scripts/rdp-auth.ps1) Section Step 1

**Analysis**:

Meaning of the three AllowEncryptionOracle values:
- **0 (Force Updated Clients)**: Most secure, only allows patched clients to connect
- **1 (Mitigated)**: Default value, denies outbound connections to unpatched servers but allows inbound connections from unpatched clients
- **2 (Vulnerable)**: Insecure, allows connections to unpatched CredSSP hosts

Connection behavior decision matrix (server perspective):

| Server Patch | Client Patch | Force Updated (0) | Mitigated (1) | Vulnerable (2) |
|-----------|-----------|-------------------|---------------|----------------|
| Installed | Not installed | Blocked | Allowed | Allowed |
| Not installed | Installed | Blocked | Blocked | Allowed |
| Installed | Installed | Allowed | Allowed | Allowed |

1. Check TSpkg.dll version to determine patch status:
   - Determine whether the CVE-2018-0886 fix is included based on file version. Reference minimum versions: Windows Server 2016 requires >= 10.0.14393.2248, Server 2012 R2 requires >= 6.3.9600.18999, Server 2008 R2 requires >= 6.1.7601.24117
   - If version is below the corresponding baseline -> **Root cause**: Server has not installed the CredSSP security update (CVE-2018-0886), patched clients will be unable to connect, **Severity**: Critical

2. Check AllowEncryptionOracle policy:
   - Normal: Value is 0 or 1, or not configured (equivalent to 1)
   - Abnormal: Value is 2 -> **Root cause**: CredSSP policy set to Vulnerable, allows insecure connections, **Severity**: Warning
   - If user reports authentication error and value is 0 -> Force Updated mode may be blocking unpatched client connections, needs to be determined combined with patch status

### Step 2: Account Lockout Status Check

**Data Collection**: Get lockout status of all enabled local user accounts

- PowerShell script: [rdp-auth.ps1](references/online/scripts/rdp-auth.ps1) Section Step 2

**Analysis**:

1. Check whether the account is locked:
   - Normal: All accounts Lockout = False
   - Abnormal: An account Lockout = True -> **Root cause**: User account has been locked, **Severity**: Critical
   - If the user specified a particular account name, focus on that account's Lockout status

### Step 3: Remote Logon Permission Check

**Data Collection**: Get member lists of Remote Desktop Users and Administrators groups, remote logon allow and deny configurations in local security policy

- PowerShell script: [rdp-auth.ps1](references/online/scripts/rdp-auth.ps1) Section Step 3

**Analysis**:

1. Check whether the user has remote logon permission:
   - Normal: Target user is in Administrators or Remote Desktop Users group
   - Abnormal: Target user is not in any group that allows remote logon -> **Root cause**: User lacks remote logon permission, **Severity**: Critical
   - If the user did not specify an account name, list all members of both groups for LLM judgment

2. Check whether remote logon is explicitly denied:
   - Normal: SeDenyRemoteInteractiveLogonRight not configured, or target user and its groups not in the deny list
   - Abnormal: Target user or its group appears in the SeDenyRemoteInteractiveLogonRight deny list -> **Root cause**: User explicitly denied remote logon (SeDenyRemoteInteractiveLogonRight), cannot log in even if in Remote Desktop Users group, **Severity**: Critical
   - Note: Deny policy takes precedence over allow policy; even if a user is in both the allow and deny lists, the user is ultimately denied

### Step 4: Security Layer Configuration Check

**Data Collection**: Get SecurityLayer and Network Level Authentication (NLA) configuration values for all WinStations

- PowerShell script: [rdp-auth.ps1](references/online/scripts/rdp-auth.ps1) Section Step 4

**Analysis**:

1. Check security layer configuration for each WinStation:
   - Normal: SecurityLayer = 1 (Negotiate) or 2 (Force SSL)
   - Abnormal: SecurityLayer = 0 -> **Root cause**: RDP uses native security layer, lower security (annotate StationName), **Severity**: Warning

2. Check NLA configuration for each WinStation:
   - Normal: UserAuthentication = 1 (NLA enabled)
   - Abnormal: UserAuthentication = 0 -> **Root cause**: NLA not enabled, may affect some client connections (annotate StationName), **Severity**: Warning

### Step 5: Password Error Audit Event Check

**Data Collection**: Get raw logon failure event records from the last 1 hour for LLM analysis of account name, source IP, and failure reason

- PowerShell script: [rdp-auth.ps1](references/online/scripts/rdp-auth.ps1) Section Step 5

**Analysis**:

1. Check logon failure events:
   - Normal: No 4625 events or very few
   - Abnormal: Large number of 4625 events -> **Root cause**: Brute force attempt or credential configuration error, **Severity**: Warning
   - When a large number of 4625 events is found -> Jump to [identity-account.md](references/online/identity-account.md) Step 1 (Account Lockout Status Check) for detailed information: Event 4740 (lockout source), Event 4625 TargetUser / SourceIP / LogonType, service credential expiration check, etc.

### Step 6: ForceGuest Access Mode Check

**Data Collection**: Check ForceGuest configuration in local security policy, determine whether non-admin remote users are forcibly mapped to Guest

- PowerShell script: [rdp-auth.ps1](references/online/scripts/rdp-auth.ps1) Section Step 6

**Analysis**:

1. Check ForceGuest configuration:
   - Normal: ForceGuest = 0 (Classic mode, authentication using the user's own identity)
   - Abnormal: ForceGuest = 1 -> **Root cause**: ForceGuest forced guest mode, local non-admin accounts logging on remotely are mapped to the Guest account; the client presents as a password error (observed in practice: password is correct but a credential error is still reported) or insufficient permissions, **Severity**: Critical
   - Note: This setting mainly affects workgroup environments; domain environments are typically unaffected

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Step 2 account locked | -> [identity-account.md](references/online/identity-account.md) |
| Conditional jump | Step 3 lacks remote logon permission / deny policy hit | -> [identity-permission.md](references/online/identity-permission.md) Step 2/5 (membership and allow/deny policy review) |
| Conditional jump | Step 5 large number of 4625 events | -> [identity-account.md](references/online/identity-account.md) Step 1 (account lockout status + lockout source tracing) |
| Conditional jump | Step 6 ForceGuest abnormal | -> [identity-permission.md](references/online/identity-permission.md) Step 4 |
| Chain successor | No root cause confirmed in this file, user reports RDP authentication issue | -> [rdp-certificate.md](references/online/rdp-certificate.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [rdp-auth.md](references/online/fixes/rdp-auth.md).
