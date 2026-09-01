# RDP Licensing Diagnostics

## Feature Description

Diagnoses Windows Remote Desktop Services (RDS) licensing status and licensing mode configuration issues. Covers RDS Session Host role installation status, licensing mode configuration, Grace Period expiration, license server connectivity, totaling 4 known issue items.

**Input**: User problem description (required), licensing error message during RDP connection (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Symptom | Recommended Steps |
|-------------|---------------|
| Multiple users prompted "licensing mode is not configured" when connecting | Step 1 (RDSH Role) -> Step 2 (Licensing Mode) |
| Prompt "Remote Desktop license expired" or exceeds maximum connections | Step 3 (Grace Period) -> Step 4 (License Server) |
| Cannot connect after 120-day trial period expires | Step 3 (Grace Period) -> Step 2 (Licensing Mode) -> Step 4 (License Server) |
| RDS CAL licensing issue | Step 2 (Licensing Mode) -> Step 4 (License Server) |

## Diagnostic Steps

### Step 1: Remote Desktop Session Host Role Check

**Data Collection**: Pre-check RDS base service status (TermService/SessionEnv/UmRdpService), check Remote Desktop Session Host (RDSH) role and RD Licensing role installation status, determine whether the current server requires RDS licensing

- PowerShell script: [rdp-licensing.ps1](references/online/scripts/rdp-licensing.ps1) Section Step 1

**Analysis**:

1. Quick pre-check of RDS base service status:
   - Normal: TermService / SessionEnv / UmRdpService all Running -> Continue licensing check
   - Abnormal: Any service not running -> **Jump to [rdp-service.md](references/online/rdp-service.md)** to troubleshoot service issues, do not make root cause determination in this file

2. Check whether RDSH role is installed:
   - Normal (RDSH role not installed): Server only supports the default 2 management sessions, no RDS licensing required, licensing issues not applicable
   - Abnormal (RDSH role installed but licensing not configured): Need to continue checking licensing configuration -> execute subsequent steps

3. Check whether RD Licensing role is installed:
   - Normal: RD Licensing role installed (this machine serves as the license server)
   - Information: Not installed -> Need to configure an external license server

> Note: If the RDSH role is not installed, subsequent steps can be skipped. Windows Server provides 2 concurrent management remote desktop sessions by default and does not require RDS CALs.

### Step 2: RDS Licensing Mode Configuration Check

**Data Collection**: Pre-check TerminalServerMode to determine whether in Application Server mode, get RDS licensing mode configuration (LicensingType/LicensingName/PolicySourceLicensingType/PossibleLicensingTypes) and license server address (GetSpecifiedLicenseServerList)

- PowerShell script: [rdp-licensing.ps1](references/online/scripts/rdp-licensing.ps1) Section Step 2

**Analysis**:

0. Pre-check RDSH Application Server mode:
   - TerminalServerMode = 0 -> **Normal**: Currently in Remote Desktop for Administration mode, only supports default 2 management sessions, no RDS licensing configuration required, subsequent Step 3/4 can be skipped
   - TerminalServerMode = 1 -> RDSH installed and in Application Server mode, continue licensing check

1. Check whether licensing mode is configured:
   - Normal: LicensingType = 2 (Per Device) or 4 (Per User)
   - Abnormal: LicensingType not configured or value abnormal -> **Root cause**: RDS licensing mode not configured, multiple users will be prompted "licensing mode is not configured" when connecting, **Severity**: Critical

2. Check whether license server is configured:
   - Normal: GetSpecifiedLicenseServerList returns a valid license server address
   - Abnormal: License server not configured -> **Root cause**: RDS license server not configured, will be unable to obtain CALs after Grace Period expires, **Severity**: Warning

### Step 3: Grace Period Status Check

**Data Collection**: Pre-check TerminalServerMode, query RDS Grace Period remaining days (GetGracePeriodDays) and license key pack information (Win32_TSLicenseKeyPack: KeyPackType/TotalLicenses/IssuedLicenses/AvailableLicenses)

- PowerShell script: [rdp-licensing.ps1](references/online/scripts/rdp-licensing.ps1) Section Step 3

**Analysis**:

> Prerequisite: TerminalServerMode = 1 (RDSH installed and in Application Server mode). If TerminalServerMode = 0, this step is not applicable and should be skipped normally.

1. Check Grace Period status:
   - Normal: GetGracePeriodDays returns remaining days > 0, or licensing is correctly configured and Grace Period is not needed
   - Abnormal: Grace Period expired (remaining days = 0 or call failed) -> **Root cause**: RDS 120-day trial period has expired, new remote desktop connections will be rejected, **Severity**: Critical

2. Check issued licenses:
   - Normal: Available licenses exist
   - Abnormal: Available license count is 0 -> **Root cause**: RDS CALs exhausted, new users/devices cannot obtain licenses, **Severity**: Critical

### Step 4: License Server Connectivity Check

**Data Collection**: Pre-check TerminalServerMode, get license server address (GetSpecifiedLicenseServerList) and connectivity status (GetTStoLSConnectivityStatus), check local TermServLicensing service status, query license server discovery results (Win32_TSDeploymentLicensing)

- PowerShell script: [rdp-licensing.ps1](references/online/scripts/rdp-licensing.ps1) Section Step 4

**Analysis**:

> Prerequisite: TerminalServerMode = 1 (RDSH installed and in Application Server mode). If TerminalServerMode = 0, this step is not applicable and should be skipped normally.

1. Check whether license server address is configured:
   - Normal: GetSpecifiedLicenseServerList returns a valid license server address
   - Abnormal: Not configured -> Refer to Step 2 root cause

2. Check connectivity to the license server:
   - Normal: GetTStoLSConnectivityStatus returns normal connectivity
   - Abnormal: Connectivity abnormal -> **Root cause**: RDS license server unreachable, cannot obtain or validate CALs, **Severity**: Critical

3. Check local licensing service status (if this machine serves as the license server):
   - Normal: TermServLicensing service is running
   - Abnormal: Service stopped -> **Root cause**: Local RD Licensing service not running, **Severity**: Critical

> If you suspect the firewall is blocking licensing communication, see -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP port 135 rules)

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Parameterized reference | Firewall blocking license server communication | -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP port 135 rules) |
| Conditional jump | RDP connection itself cannot be established | -> [rdp-service.md](references/online/rdp-service.md) |
| Chain successor | No root cause confirmed in this file, user reports RDP connection issue | -> [rdp-service.md](references/online/rdp-service.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [rdp-licensing.md](references/online/fixes/rdp-licensing.md).
