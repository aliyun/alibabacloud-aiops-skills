# Storage SMB Diagnostics

## Function Description

Diagnoses Windows SMB Client access to shared file issues. Covers Guest authentication restrictions, missing network components, LanmanWorkstation ProviderOrder misconfiguration, encryption/signing configuration incompatibility, Windows Server 2025 enforced signing causing third-party SMB connection failures (system error C05D0003), and other issue items.

**Input**: User problem description (required), error code/Event ID/screenshot (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Error code C05D0003 (computer configured to require SMB sign-in) | Step 1 (SMB signing configuration) |
| Can see shares but access denied (Access Denied) | Step 4 (Guest access policy) -> Step 1 (encryption/signing configuration) |
| Error code 0xC0000022 or 0x80070005 | Step 4 (Guest access) -> Step 1 (encryption configuration) |
| Windows 10/Server 2016+ cannot access shares | Step 4 (Guest access policy) -> Step 1 (SMB configuration) |
| Error code 1272 (organization's security policy blocks unauthenticated guest access) | Step 4 (Guest access policy) |
| Shared folder inaccessible, network path not found | Step 2 (network components) -> Step 3 (network discovery and ports) |
| Slow SMB connection or poor transfer performance | Step 1 (SMB multichannel/compression) |

## Diagnostic Steps

### Step 1: SMB Client Configuration Check

**Data Collection**:

> Collection target: Obtain SMB client encryption configuration, signing requirements and other security settings, as well as the protocol version of current connections

- PowerShell script: [storage-smb.ps1](references/online/scripts/storage-smb.ps1) Section Step 1

**Analysis Approach**:

1. Check SMB signing configuration (client):
   - Normal state: EnableSecuritySignature = True (signing supported), RequireSecuritySignature = False (signing on demand)
   - Abnormal state: RequireSecuritySignature = True and connecting to third-party SMB server may cause connection failure
   - Note: Windows Server 2025 enables RequireSecuritySignature = True by default, while third-party SMB servers (e.g., NAS, Linux Samba, cloud storage) may not support signing, causing system error C05D0003 at connection time

2. Check the protocol version of current connection:
   - Normal state: Using SMBv2 or SMBv3 (Dialect shows 2.x or 3.x)
   - Abnormal state: Connection uses SMBv1 (Dialect = 1.0), poor performance and security

3. Check SMB encryption configuration:
   - Normal state: EnableEncryption = False (encrypt on demand) or True (force encryption)
   - Abnormal state: Encryption configuration incompatible with server, may cause connection failure

4. Check SMB multichannel and compression features (SMB 3.x):
   - Normal state: Get-SmbConnection shows normal connection
   - Abnormal state: Multichannel not enabled but network adapter supports it, may result in suboptimal performance

### Step 2: Network Component Status Check

**Data Collection**:

> Collection target: Obtain installation and enabled status of Microsoft Network Client component, as well as LanmanWorkstation service status and network provider order configuration

- PowerShell script: [storage-smb.ps1](references/online/scripts/storage-smb.ps1) Section Step 2

**Analysis Approach**:

1. Check Microsoft Network Client (ms_msclient):
   - Normal state: Component installed and enabled
   - Abnormal state: Component not installed or not enabled, will be unable to access SMB shares
   - Note: This component is required for accessing SMB/CIFS network resources

2. Check LanmanWorkstation service status:
   - Normal state: Service status is Running
   - Abnormal state: Service not running or startup type is Disabled, SMB Client functionality will be unavailable
   - Note: LanmanWorkstation service is the core service of SMB Client, responsible for establishing and maintaining connections with remote servers

3. Check network provider order (ProviderOrder):
   - Normal state: ProviderOrder registry value includes "LanmanWorkstation"
   - Abnormal state: LanmanWorkstation not in ProviderOrder, SMB connection will fail

### Step 3: Network Discovery Configuration Check

**Data Collection**:

> Collection target: Obtain network discovery feature status, related service status, and SMB port listening status

- PowerShell script: [storage-smb.ps1](references/online/scripts/storage-smb.ps1) Section Step 3

**Analysis Approach**:

1. Check network discovery related services:
   - Normal state: Service startup type is Manual, status of Stopped or Running are both acceptable
   - Abnormal state: Service is disabled, will be unable to discover other devices on the network
   - Abnormal state: Service startup type is Automatic but status is Stopped and cannot start, network discovery feature abnormal
   - Note: These services start manually by default, run on demand, and do not need to remain in Running state

2. Check firewall rules:
   - First check firewall profile status:
     - If the firewall for the current network profile (Private/Public) is disabled -> skip firewall rule check, firewall will not block network discovery
     - If firewall is enabled -> continue checking network discovery rules
   - Normal state: Network discovery firewall rule enabled (private network profile)
   - Abnormal state: Firewall enabled but network discovery rule disabled, network discovery will be blocked
   - Note: Need to check both Chinese and English rule group names

3. Check SMB port listening:
   - Normal state: TCP port 445 is listening (SMB over TCP)
   - Abnormal state: Port 445 not listening, Server service not started or SMB port occupied
   - Note: Modern Windows uses SMB over TCP (445), no longer depends on NetBIOS (137-139)

### Step 4: Guest Access Policy Check

**Data Collection**:

> Collection target: Obtain Windows system version and Guest authentication policy configuration, especially the Insecure Guest Logons setting for Windows 10/Server 2016 and above

- PowerShell script: [storage-smb.ps1](references/online/scripts/storage-smb.ps1) Section Step 4

**Analysis Approach**:

1. Check system version impact on Guest access:
   - Windows Server 2016/Windows 10 1607 and above disable insecure Guest access by default
   - Windows Server 2012 R2/Windows 8.1 and earlier allow Guest access by default
   - Abnormal state: New system attempts to access shares requiring Guest authentication but AllowInsecureGuestAuth not enabled, Windows 10/Server 2016+ blocks insecure Guest logon by default

2. Check AllowInsecureGuestAuth registry value:
   - Normal state: AllowInsecureGuestAuth = 1 (allow Guest access) or share does not require Guest authentication
   - Abnormal state: AllowInsecureGuestAuth = 0 or null (deny Guest access) and share requires Guest authentication, Guest authentication will be blocked
   - Note: This registry value controls whether insecure Guest authentication is allowed

3. Check LSA anonymous access restrictions:
   - Normal state: RestrictAnonymous = 0 or 1 (allow enumeration)
   - Abnormal state: RestrictAnonymous = 2 (deny anonymous enumeration), may affect share browsing
   - Note: LSA policy controls anonymous user enumeration permissions for SAM accounts and shares

4. Check LMCompatibilityLevel (LAN Manager authentication level):
   - Normal state: LMCompatibilityLevel = 3 (send NTLMv2 only) or higher
   - Abnormal state: LMCompatibilityLevel = 0 or 1 (allow LM and NTLM), security risk
   - Note: This value affects the authentication protocol used for SMB connections

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 2 network component missing or not enabled | -> [networking-tcpip.md](references/online/networking-tcpip.md) (check network configuration and components) |
| Parameterized reference | Step 3 network discovery blocked by firewall or port 445 not listening | -> [networking-firewall.md](references/online/networking-firewall.md) (check inbound TCP 445 port rules) |
| Conditional jump | Step 1 or Step 4 finds SMB encryption/signing/Guest policy configuration issue causing connection failure | -> [system-gpo.md](references/online/system-gpo.md) (check SMB security policy configuration in Group Policy) |
| Chained successor | Root cause not confirmed in this file, user reports share access issue | -> [networking-tcpip.md](references/online/networking-tcpip.md) (check basic network connectivity) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [storage-smb.md](references/online/fixes/storage-smb.md).
