# RDP Certificate Diagnostics

## Feature Description

Diagnoses remote desktop certificate-related issues. Covers RDP certificate source and status (per-WinStation check of SSLCertificateSHA1Hash / SelfSignedCertificate fallback, validity period, private key accessibility), MachineKeys directory and TLS private key file permissions (associated with certificate HasPrivateKey status), system drive root directory permissions, totaling 3 diagnostic steps.

**Input**: User problem description (required), RDP certificate warning or Internal error (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| RDP certificate warning, untrusted certificate, certificate expired | Step 1 (Certificate Source and Status) |
| Internal error, certificate cannot be updated | Step 2 (MachineKeys and TLS Private Key Permissions) -> Step 1 (Certificate Source and Status) |
| TLS negotiation failure, private key access denied, HasPrivateKey = false | Step 1 (Certificate Source and Status) -> Step 2 (MachineKeys and TLS Private Key Permissions) |
| RDP connection failure and no issues found in other steps | Step 3 (System Drive Root Directory Permissions) |

## Diagnostic Steps

### Step 1: RDP Certificate Source and Status Check

**Data Collection**: Read global default self-signed certificate definition (SelfSignedCertificate / SelfSignedCertStore), check Certificate Propagation Service (CertPropSvc) running status, enumerate all WinStation certificate configurations (SSLCertificateSHA1Hash / SelfSignedCertificate fallback), and find certificate details (validity period, issuer, private key status) in both My and Remote Desktop certificate stores

- PowerShell script: [rdp-certificate.ps1](references/online/scripts/rdp-certificate.ps1) Section Step 1

**Analysis**:

> **Determination Scope Constraint (MUST)**: This step only performs anomaly determination on certificates **actually bound and used by WinStations** (certificates resolved in Step 1: custom certificate pointed to by SSLCertificateSHA1Hash, or the fallback global default self-signed certificate). The collection output includes **all** certificates in the My / Remote Desktop stores (for locating bound certificates by thumbprint); certificates not bound to any WinStation, even if expired, self-signed, or without a private key, do **not constitute an RDP root cause** -- RDP connections will not use them; if there is informational value, at most annotate them separately as "Other Findings" at the Unrelated level (noting that the certificate is not used by RDP), and do not determine them as the root cause or associated anomaly for this issue.

1. Check global self-signed certificate definition:
   - Normal: SelfSignedCertificate is set under WinStations key, SelfSignedCertStore is "Remote Desktop" or has a clear value
   - Abnormal: SelfSignedCertificate not set and all WinStations have no SSLCertificateSHA1Hash -> TermService may not have initialized properly, **Severity**: Warning
   - Note: When all WinStations have SSLCertificateSHA1Hash configured (using custom certificates), the global default self-signed certificate will not be used by RDP, and its absence or anomaly does not constitute a root cause

2. Check Certificate Properties Service (CertPropSvc):
   - Normal: Service is running
   - Abnormal: Service not running -> **Root cause**: Certificate Properties Service not running, certificates may not auto-renew in domain environments, **Severity**: Warning

3. Identify certificate source for each WinStation:
   - Source = Custom -> SSLCertificateSHA1Hash configured, using custom certificate, search in both `Cert:\LocalMachine\My` and `Cert:\LocalMachine\Remote Desktop` stores (My takes priority)
   - Source = SelfSigned (default) -> SSLCertificateSHA1Hash not configured, fallback to global default self-signed certificate, storage location specified by SelfSignedCertStore (usually `Cert:\LocalMachine\Remote Desktop`)
   - Both sources are normal behavior and do not constitute an anomaly

4. Verify the resolved certificate for each WinStation:
   - Certificate does not exist (thumbprint not found in either My or Remote Desktop store) -> **Root cause**: RDP certificate missing (annotate StationName and Source), may encounter Internal error during connection, **Severity**: Critical
   - NotAfter < current time -> **Root cause**: RDP certificate expired, certificate warning will appear during connection, **Severity**: Warning
   - Subject == Issuer -> Self-signed certificate, client will display certificate warning, **Severity**: Info
   - HasPrivateKey is false -> **Root cause**: Certificate private key not accessible, TermService cannot complete TLS handshake -> must jump to **Step 2** to check MachineKeys permissions, **Severity**: Critical

### Step 2: MachineKeys and TLS Private Key Permission Check

**Data Collection**: Check MachineKeys directory permissions, ProgramData path configuration, and TLS private key file permissions. When Step 1 finds certificate HasPrivateKey = false, this step is mandatory; the private key of the RDP self-signed certificate is stored in files with the f686aace prefix in the MachineKeys directory

- PowerShell script: [rdp-certificate.ps1](references/online/scripts/rdp-certificate.ps1) Section Step 2

**Analysis**:

1. Check whether the MachineKeys directory exists:
   - Normal: Directory exists
   - Abnormal: Directory does not exist -> **Root cause**: MachineKeys directory missing, certificates cannot be created or updated, **Severity**: Critical

2. Check key account permissions:
   - Normal: Administrators has Full Control, Everyone has Read and Write permissions
   - Abnormal: Everyone has no Read permission -> **Root cause**: MachineKeys permissions abnormal, RDP certificate cannot be updated, **Severity**: Critical
   - Abnormal: Administrators has no Full Control -> **Root cause**: MachineKeys permissions tampered, **Severity**: Critical

3. Check TLS private key files (f686aace prefix, corresponding to RDP self-signed certificate private key; directly associated with HasPrivateKey = false in Step 1):
   - Prerequisite: If output shows `[Error] Unable to read MachineKeys directory contents`, it indicates directory permission anomaly prevents file enumeration; in this case, private key file query results are unreliable, and the output root cause should note "Private key status to be confirmed after directory permissions are fixed due to MachineKeys directory permission anomaly"
   - Normal: File exists, NETWORK SERVICE has Read permission, SYSTEM has Full Control
   - Abnormal: File does not exist -> **Root cause**: TLS private key file missing, RDP TLS negotiation will fail (corresponds to Step 1 certificate HasPrivateKey = false), **Severity**: Critical
   - Abnormal: NETWORK SERVICE has no Read permission -> **Root cause**: TLS private key access denied, TermService cannot read private key, **Severity**: Critical
   - Abnormal: SYSTEM has no Full Control -> **Root cause**: TLS private key access denied, **Severity**: Critical

### Step 3: System Drive Root Directory Permission Check

**Data Collection**: Check key account permissions on the system drive root directory (C:\), ensure TermService can normally access system files

- PowerShell script: [rdp-certificate.ps1](references/online/scripts/rdp-certificate.ps1) Section Step 3

**Analysis**:

1. Check BUILTIN\Users permissions:
   - Normal: BUILTIN\Users has Read and Execute permissions (ReadAndExecute)
   - Abnormal: BUILTIN\Users lacks Read and Execute permissions -> **Root cause**: System drive root directory permissions abnormal, may cause RDP connection failure, **Severity**: Critical

2. Check whether NT AUTHORITY\SERVICE has an explicit deny ACE:
   - Normal: Output is empty or only contains Allow type ACEs (by default has required permissions through inheritance, no explicit entries is normal)
   - Abnormal: An entry with AccessControlType = Deny exists -> **Root cause**: System drive root directory explicitly denies service account access, TermService may not be able to read system files, **Severity**: Critical

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional jump | Step 1 HasPrivateKey = false | -> Step 2 (MachineKeys and TLS Private Key Permissions) |
| Conditional jump | Step 2 MachineKeys permissions abnormal | -> [identity-permission.md](references/online/identity-permission.md) |
| Conditional jump | Step 3 system drive permissions abnormal | -> [identity-permission.md](references/online/identity-permission.md) |
| Chain successor | No root cause confirmed in this file, user reports RDP certificate issue | -> No chained successor (certificate issues are usually located within this file; if no root cause is confirmed, redirect to [rdp-service.md](references/online/rdp-service.md) for broader RDP troubleshooting) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [rdp-certificate.md](references/online/fixes/rdp-certificate.md).
