# Security Certificates Diagnosis

## Overview

Diagnoses Windows root certificate status, certificate chain integrity, TLS protocol version/cipher suite, and driver signing root certificates. Covers 4 known issue items.

**Input**: User problem description (required)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|----------------------|-------------------|
| HTTPS access reports certificate error, API call failure | Step 1 (root certificate status) |
| SSL/TLS connection failure | Step 2 (certificate chain integrity) |
| TLS handshake failure, some HTTPS sites or APIs inaccessible | Step 3 (TLS protocol version/cipher suite) |
| Driver installation prompts "publisher not trusted" | Step 4 (driver signing root certificate) |

## Diagnostic Steps

### Step 1: Check Root Certificate Status

**Data Collection**:

> Collection target: Obtain the certificate list and expiration status in the trusted root certificate store on this machine

**Analysis Approach**:

- PowerShell script: [security-certificates.ps1](references/online/scripts/security-certificates.ps1) Section Step 1

1. Check for expired root certificates:
   - Normal: No expired root certificates, or expired certificates are non-critical
   - Abnormal: Critical Microsoft root certificate expired or missing -> **Root cause**: Critical root certificate missing or expired; will cause HTTPS access, driver signature verification, Windows Update, etc. to fail, **Severity**: Critical

### Step 2: Check Certificate Chain Integrity

**Data Collection**:

> Collection target: Check the certificate chain status in the intermediate certificate store and personal certificate store

**Analysis Approach**:

- PowerShell script: [security-certificates.ps1](references/online/scripts/security-certificates.ps1) Section Step 2

1. Check intermediate certificate expiration:
   - Normal: No expired intermediate certificates that affect critical services
   - Abnormal: A large number of expired intermediate certificates -> **Root cause**: Expired intermediate certificates causing certificate chain validation failure, **Severity**: Warning
2. Check personal certificate chain status:
   - Normal: All certificate chains built successfully
   - Abnormal: Certificate chain build failure (missing intermediate certificate, untrusted root certificate, etc.) -> **Root cause**: Incomplete certificate chain; related SSL/TLS services will fail, **Severity**: Critical

### Step 3: Check TLS Protocol Version/Cipher Suite

**Data Collection**:

> Collection target: Obtain system TLS/SSL protocol version enablement status and cipher suite configuration

**Analysis Approach**:

- PowerShell script: [security-certificates.ps1](references/online/scripts/security-certificates.ps1) Section Step 3

1. Check TLS protocol version:
   - Normal: TLS 1.2 enabled, SSL 2.0/3.0 disabled
   - Abnormal: TLS 1.2 explicitly disabled (Enabled=0) -> **Root cause**: TLS 1.2 disabled; a large number of modern websites and APIs will be inaccessible, **Severity**: Critical
   - Abnormal: Only TLS 1.0/1.1 enabled, TLS 1.2 not enabled -> **Root cause**: Only outdated TLS versions supported; security risk and reduced compatibility, **Severity**: Warning
2. Check cipher suite policy:
   - Normal: No restrictive policy configured; system default is used
   - Abnormal: Policy restricts necessary cipher suites -> **Root cause**: Cipher suite policy too restrictive; some TLS connections will fail, **Severity**: Warning

### Step 4: Check Driver Signing Root Certificate

**Data Collection**:

> Collection target: Check whether the Microsoft code signing root certificate required for driver signing exists

**Analysis Approach**:

- PowerShell script: [security-certificates.ps1](references/online/scripts/security-certificates.ps1) Section Step 4

1. Check driver signing root certificate:
   - Normal: All critical code signing certificates present and not expired
   - Abnormal: Critical code signing certificate missing -> **Root cause**: Driver signing root certificate missing; driver installation will prompt "publisher not trusted," **Severity**: Critical
2. Check driver signing policy:
   - Normal: Policy is 1 (warn) or 2 (block)
   - Abnormal: Policy is 0 (ignore) may allow unsigned drivers to load -> **Root cause**: Driver signature verification disabled; security risk, **Severity**: Warning

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|-------------------|-------------|
| Conditional jump | Step 3 TLS configuration abnormality affecting RDP connection | -> [rdp-certificate.md](references/online/rdp-certificate.md) |
| Conditional jump | Step 4 driver signing certificate missing | -> [cloud-driver.md](references/online/cloud-driver.md) |
| Chain successor | Root cause not confirmed in this file | -> [security-bitlocker.md](references/online/security-bitlocker.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [security-certificates.md](references/online/fixes/security-certificates.md).
