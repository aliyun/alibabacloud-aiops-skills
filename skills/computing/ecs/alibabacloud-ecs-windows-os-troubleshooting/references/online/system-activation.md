# System Activation Diagnostics

## Function Description

Diagnoses Windows activation related issues: Software Protection Service (sppsvc) service status abnormality, KMS activation status check, product key (GVLK) validation, KMS port firewall blocking, KMS server connectivity, activation-related event log errors. Covers 6 known issue items.

**Input**: User problem description (required), error code/Event ID (optional, used to narrow down troubleshooting scope)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| Desktop shows Activate Windows watermark, reduced functionality | Step 2 (KMS activation status) -> Step 3 (product key and KMS configuration) |
| slmgr /ato reports error, activation failure | Step 1 (sppsvc service) -> Step 2 (KMS activation status) -> Step 3 (product key and KMS configuration) |
| Activation timeout, error 0x80072EE7 / 0x8007232B | Step 3 (product key and KMS configuration) -> Step 4 (activation event log) |
| Error 0xC004F074 (KMS unavailable) | Step 3 (product key and KMS configuration) -> Step 4 (activation event log) |
| Error 0xC004F06C (invalid timestamp) | Step 4 (activation event log) |
| Activation errors in event log (Event ID 8198 / 8193) | Step 4 (activation event log) -> Step 1 (sppsvc service) -> Step 2 (KMS activation status) |
| Product key invalid or mismatched | Step 3 (product key and KMS configuration) |
| Error 0xC004E002 / 0xC004E015 (licensing store abnormality) | Step 2 (KMS activation status) -> Step 1 (sppsvc service), fix see "Tokens.dat Rebuild" |
| Repeated activation failure, key and network both normal | Step 1 (sppsvc service) -> Step 2 (KMS activation status), fix see "Tokens.dat Rebuild" |

## Diagnostic Steps

### Step 1: sppsvc Service Status Check

**Data Collection**:

> Collection target: Obtain service status, startup type, and runtime information of Software Protection Service (sppsvc) to determine whether the service can work normally

- PowerShell script: [system-activation.ps1](references/online/scripts/system-activation.ps1) Section Step 1

**Analysis Approach**:

1. Check whether the service exists:
   - Normal: Query returns sppsvc service record
   - Abnormal: Query returns no results, service does not exist -> **Root cause**: sppsvc service corrupted or missing, **Severity**: Warning

2. Check service startup type:
   - Normal: Startup type is Auto or Manual (sppsvc starts on demand, not being in Running state is not abnormal in itself)
   - Abnormal: Startup type is Disabled -> **Root cause**: sppsvc service disabled, **Severity**: Warning

3. Check service configuration integrity:
   - Normal: Status is OK, no abnormal exit codes
   - Abnormal: Status abnormal or non-zero exit codes exist -> **Root cause**: sppsvc service configuration corrupted, **Severity**: Warning

> Note: sppsvc is an on-demand trigger service (Trigger Start); being in Stopped state when no activation operation is in progress is normal, as long as it is not Disabled or corrupted. If this step detects sppsvc abnormality, subsequent activation status check (Step 2) results are unreliable; prioritize fixing sppsvc.

### Step 2: KMS Activation Status Check

**Data Collection**:

> Collection target: Query volume licensing product information from the WMI software licensing database to obtain activation status and license status reason codes

- PowerShell script: [system-activation.ps1](references/online/scripts/system-activation.ps1) Section Step 2

**Analysis Approach**:

1. Check whether licensed product records exist:
   - Normal: At least one record with a partial product key is returned
   - Abnormal: No records -> indicates the system has no product key installed; may need to reinstall GVLK

2. Check activation status (LicenseStatus):
   - Normal: At least one record with LicenseStatus = 1 (Licensed) exists
   - Abnormal: All records have LicenseStatus not equal to 1 -> **Root cause**: Windows not activated via KMS, **Severity**: Critical
     - Common status value meanings:
       - 0 (Unlicensed): No valid license found
       - 2 (OOB Grace Period): Initial grace period after installation
       - 3 (OOT Grace Period): Out-of-tolerance grace period
       - 4 (Non-Genuine Grace Period): Non-genuine detected
       - 6 (Extended Grace Period): Extended grace period

3. Analyze license status reason code (LicenseStatusReason):
   - This value is an HRESULT error code; the problem direction can be determined based on the error code:

     | Error Code | Meaning | Problem Direction |
     |--------|------|----------|
     | 0xC004F074 | KMS server unavailable | Network/KMS configuration |
     | 0xC004F06C | Invalid request timestamp (client and KMS time skew > 4 hours) | Time sync, see -> [system-time.md](references/online/system-time.md) |
     | 0xC004F042 | Specified KMS cannot be used | KMS configuration |
     | 0xC004F038 | KMS count insufficient (Server needs >= 5) | KMS host configuration |
     | 0xC004F069 | Product key not found | Key installation |
     | 0xC004F00F | Product key does not match Windows edition | Key version |
     | 0xC004F063 | OEM edition activation method mismatch | Activation method (non-KMS) |
     | 0xC004F015 | Entered license key does not match currently installed Windows SKU | Key version |
     | 0xC004E002 | Software licensing service reports license store format inconsistency | Tokens.dat corrupted |
     | 0xC004E015 | License consumption failed (EULA acceptance failed) | Tokens.dat corrupted |
     | 0xC004C003 | Product key blocked | Key validity |
     | 0x8007232B | DNS name does not exist | DNS/network |
     | 0x8007267C | DNS server not configured | DNS/network |
     | 0x80072EE7 | Server name or address cannot be resolved | DNS/network |
     | 0x8007000D | Invalid data (product key format error) | Key format |
     | 0x80070005 | Access denied | Permissions (administrator required) |

   - Classification rules:
     - Network/DNS errors (0x8007xxxx) -> KMS server reachability issue. Among them, 0x8007232B / 0x8007267C / 0x80072EE7 are DNS resolution errors, see -> [networking-dns.md](references/online/networking-dns.md) (check DNS client service and DNS server configuration)
     - License errors (0xC004xxxx) -> Key or licensing configuration issue, see Step 2 (activation status check) and Step 3 (product key and KMS configuration check) in this file
     - 0xC004F06C -> Specifically points to time sync issue, see -> [system-time.md](references/online/system-time.md)
     - 0xC004E0xx -> Tokens.dat corrupted, see "Tokens.dat Rebuild" in fix recommendations

### Step 3: Product Key and KMS Configuration Check

**Data Collection**:

> Collection target: Obtain operating system version information, installed product key (last 5 digits) and KMS server configuration, and check firewall rules for KMS port

- PowerShell script: [system-activation.ps1](references/online/scripts/system-activation.ps1) Section Step 3

**Analysis Approach**:

1. Verify whether the product key (GVLK) matches the operating system version:
   - Compare the last 5 characters of the installed key with the expected GVLK value for the corresponding Windows Server version
   - Expected last 5 digits for each version:

     | Windows Server Version | Expected Last 5 Digits |
     |---------------------|------------|
     | Server 2025 Datacenter | YP6DF |
     | Server 2025 Standard | MY832 |
     | Server 2022 Datacenter | 6VM33 |
     | Server 2022 Standard | VMK7H |
     | Server 2019 Datacenter | 63DFG |
     | Server 2019 Standard | J464C |
     | Server 2019 Essentials | YY726 |
     | Server 2016 Datacenter | 8XDDG |
     | Server 2016 Standard | KHKQY |
     | Server 2016 Essentials | 4M63B |
     | Server 2012 R2 Datacenter | Q3VJ9 |
     | Server 2012 R2 Standard | MDVJX |
     | Server 2012 R2 Essentials | M4FWM |
     | Server 2012 Datacenter | 8W83P |
     | Server 2012 Standard | 92BT4 |
     | Server 2008 R2 Datacenter | 7M648 |
     | Server 2008 R2 Enterprise | CPX3Y |
     | Server 2008 R2 Standard | R7VHC |

   - Normal: Last 5 digits of key match expected value
   - Abnormal: Last 5 digits of key do not match or are empty -> **Root cause**: Product key does not match the GVLK for the current operating system version, **Severity**: Critical
   - Note: An incorrect product key (e.g., from another version, retail key, or MAK key) will cause KMS activation failure even if network connectivity and KMS server configuration are correct

2. Check KMS port firewall rules:
   - Normal: No outbound rule blocking TCP 1688 (or custom KMS port)
   - Abnormal: Outbound blocking rule covering KMS port exists -> **Root cause**: Firewall blocks KMS communication port, **Severity**: Warning
   - Note: KMS activation requires the client to communicate with the KMS server via TCP 1688 (default); firewall blocking this port will cause activation timeout

3. Check KMS server connectivity:
   - Normal: TcpTestSucceeded is True
   - Abnormal: TcpTestSucceeded is False -> **Root cause**: KMS server unreachable, **Severity**: Critical
   - Note: Alibaba Cloud ECS instances communicate with the KMS server via internal address kms.cloud.aliyuncs.com:1688. Possible reasons for connectivity failure: firewall rule blocking (see previous item), routing abnormality, security group configuration, or KMS server-side issue

> If firewall rule check needs deeper troubleshooting (e.g., profile-level rules, WFP packet drop analysis), see -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP 1688 port rules)
>
> If connectivity fails and firewall is not blocking, see -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (check Alibaba Cloud internal service reachability)

### Step 4: Activation Event Log Check

**Data Collection**:

> Collection target: Query activation-related event logs from the last 24 hours to identify error/warning events from SPP service and activation client

- PowerShell script: [system-activation.ps1](references/online/scripts/system-activation.ps1) Section Step 4

**Analysis Approach**:

1. Check whether activation-related error events exist:
   - Normal: No Error/Warning level SPP events
   - Abnormal: Error events exist -> determine problem direction based on Event ID and error code

2. Common activation event IDs and meanings:
   - **Event ID 8198** (SPP Error): License activation failure, usually contains HRESULT error code
     - Contains 0xC004F074 -> KMS server unavailable, check Step 3 connectivity test results
     - Contains 0xC004F042 -> Product cannot be activated, check Step 3 product key
     - Contains 0xC004F06C -> Invalid timestamp, client and KMS server time skew exceeds 4 hours
     - Contains 0xC004E002 / 0xC004E015 -> Tokens.dat corrupted, see "Tokens.dat Rebuild" in fix recommendations
   - **Event ID 8200 / 900** (SPP Warning): License validation failure, usually accompanies 8198
   - **Event ID 8208** (SPP Warning): License renewal failure (7-day renewal attempt for activated system failed)
   - **Event ID 8193** (SPP Error): License acquisition failure
   - **Event ID 12288** (SPP Info): KMS client sent activation request, records target KMS host FQDN and port. Only 12288 appearing without 12289 indicates client cannot reach KMS host or did not receive response
   - **Event ID 12289** (SPP Info): KMS activation result, Activation Flag = 1 indicates success, 0 indicates failure, also records current count on KMS host
   - **Event ID 1058** (Application Warning): Activation-related licensing issue warning

3. Association between event log error codes and previous steps:
   - Network error codes (0x8007xxxx) -> associated with Step 3 firewall and connectivity check results
   - License error codes (0xC004xxxx) -> associated with Step 2 activation status and Step 3 product key check results
   - **0xC004F06C** (time skew) -> client and KMS server time difference exceeds 4 hours, need to check system time and NTP configuration

> If event log contains 0xC004F06C (invalid timestamp), see -> [system-time.md](references/online/system-time.md) (check system time and NTP sync configuration)
>
> If event log shows KMS server connection failure and Step 3 did not find firewall blocking, see -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (check KMS activation server reachability)

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Parameterized reference | Step 3 finds firewall blocking KMS port, need deeper firewall rule troubleshooting | -> [networking-firewall.md](references/online/networking-firewall.md) (check outbound TCP 1688 port rules) |
| Conditional jump | Step 2 error code is 0x8007232B / 0x8007267C / 0x80072EE7 (DNS resolution failure) | -> [networking-dns.md](references/online/networking-dns.md) (check DNS client service and DNS server configuration) |
| Conditional jump | Step 2 / Step 4 error code contains 0xC004F06C (time skew > 4 hours) | -> [system-time.md](references/online/system-time.md) (check system time and NTP sync configuration) |
| Conditional jump | Step 2 / Step 4 error code contains 0xC004E002 / 0xC004E015 (Tokens.dat corrupted) | -> "Tokens.dat Rebuild" in this file's fix recommendations |
| Conditional jump | Step 3 KMS connectivity failure and not firewall-related | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) (check Alibaba Cloud internal service reachability) |
| Chained successor | All steps in this file completed, root cause not confirmed | -> [cloud-metaserver.md](references/online/cloud-metaserver.md) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [system-activation.md](references/online/fixes/system-activation.md).
