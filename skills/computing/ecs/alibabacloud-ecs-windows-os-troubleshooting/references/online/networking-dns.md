# DNS Diagnostics

## Function Description

Diagnoses Windows DNS client service and resolution issues. Covers DNS service status, server configuration, cache status, hosts file, domain name resolution test, DNS suffix and NRPT configuration, and other scenarios.

**Input**: User problem description (required), inaccessible domain name (optional)
**Output**: Root cause list (root_cause / severity / evidence / explanation / fix)

## Step Selection Guide

**Not all steps need to be executed.** Select relevant steps based on the user's described problem symptoms:

| User Problem Symptom | Recommended Steps |
|-------------|---------------|
| DNS completely unavailable | Step 1 (DNS service) -> Step 2 (Server config) -> Step 5 (Resolution test) |
| Specific domain name resolution failure | Step 4 (hosts file) -> Step 5 (Resolution test) -> Step 3 (Cache check) |
| DNS resolution slow | Step 3 (Cache check) -> Step 2 (Server config) |
| Domain name resolves to wrong IP | Step 4 (hosts file) -> Step 3 (Cache pollution) -> Step 5 (Resolution test) |
| Intranet domain name resolution failure | Step 6 (DNS suffix and NRPT) -> Step 2 (Server config) |

## Diagnostic Steps

### Step 1: DNS Client Service Status Check

**Data Collection**:

> Collection target: Obtain the running status and startup type of the DNS Client service (Dnscache)

- PowerShell script: [networking-dns.ps1](references/online/scripts/networking-dns.ps1) Section Step 1

**Analysis Approach**:

1. Check DNS Client service status:
   - Normal: Service is running
   - Abnormal: Service not running -> **Root cause**: DNS Client service not running, domain name resolution failed, **Severity**: Critical
   - Abnormal: Service startup type is Disabled -> **Root cause**: DNS Client service disabled, **Severity**: Critical

### Step 2: DNS Server Configuration Check

**Data Collection**:

> Collection target: Obtain DNS server address configuration for all network interfaces, including interface alias and index

- PowerShell script: [networking-dns.ps1](references/online/scripts/networking-dns.ps1) Section Step 2

**Analysis Approach**:

1. Check if DNS server is configured:
   - Normal: At least one valid DNS server IP configured
   - Abnormal: No DNS server configured -> **Root cause**: No DNS server configured, **Severity**: Critical

2. Check if DNS server is Alibaba Cloud DNS (typical configuration for cloud servers):
   - Normal: Using Alibaba Cloud VPC DNS (100.100.2.136 or 100.100.2.138)
   - Abnormal: Using public DNS and VPC network policy blocks it -> **Root cause**: DNS server configuration not suitable for VPC environment, **Severity**: Warning

### Step 3: DNS Cache Status Check

**Data Collection**:

> Collection target: Obtain DNS cache records to check for cache pollution, resolution failures, or hosts file mappings

- PowerShell script: [networking-dns.ps1](references/online/scripts/networking-dns.ps1) Section Step 3

**Analysis Approach**:

1. Check DNS cache status:
   - Normal: Has cache records with successful status
   - Abnormal: Large number of cache failure records (Status != Success) -> **Root cause**: DNS cache pollution, **Severity**: Warning
   - Abnormal: No cache and frequent query failures -> **Root cause**: DNS resolution continuously failing, **Severity**: Warning

2. Check if hosts file mappings are effective:
   - Cache record characteristics for hosts file entries: TimeToLive = 0, Section = Answer
   - Normal: Domains in hosts file exist in cache with TTL=0
   - Abnormal: Hosts file has configuration but no corresponding records in cache -> **Root cause**: Hosts file not effective or format error, **Severity**: Warning

3. Check for error records in cache:
   - Look for records with negative Status values (e.g., 9003 = DNS_ERROR_RCODE_NAME_ERROR)
   - Abnormal: Specific domain has large number of failure records in cache -> **Root cause**: DNS cache contains failed query results, **Severity**: Warning

### Step 4: Hosts File Check

**Data Collection**:

> Collection target: Obtain hosts file content, check for manual domain name mappings or misconfigurations

- PowerShell script: [networking-dns.ps1](references/online/scripts/networking-dns.ps1) Section Step 4

**Analysis Approach**:

1. Check hosts file format:
   - Normal: Format is `IP address domain name`, one mapping per line
   - Abnormal: Syntax errors exist (e.g., missing spaces, IP format error) -> **Root cause**: Hosts file format error causing resolution failure, **Severity**: Warning
   - Abnormal: Duplicate domain name mappings exist -> **Root cause**: Duplicate domain names in hosts file, only first one takes effect, **Severity**: Info

2. Check if hosts file contains interfering mappings:
   - Abnormal: Common domain names mapped to wrong IP (e.g., 127.0.0.1 or 0.0.0.0) -> **Root cause**: Hosts file blocking domain name resolution, **Severity**: Critical
   - Abnormal: Contains malicious domain redirection -> **Root cause**: Hosts file tampered, **Severity**: Critical

3. Check hosts file permissions:
   - Normal: Only Administrators and SYSTEM have write permissions
   - Abnormal: Regular users have write permissions -> **Root cause**: Hosts file permissions improperly configured, **Severity**: Warning

### Step 5: Domain Name Resolution Test

**Data Collection**:

> Collection target: Test DNS resolution capability for common domain names, verify resolution order and results

- PowerShell script: [networking-dns.ps1](references/online/scripts/networking-dns.ps1) Section Step 5

**Analysis Approach**:

1. Check domain name resolution results:
   - Normal: Can resolve common domain names
   - Abnormal: Specific domain name resolution failure -> **Root cause**: Some domain name resolution failed, may be DNS server issue or domain itself issue, **Severity**: Warning
   - Abnormal: All domain name resolution failed -> **Root cause**: DNS completely unavailable, **Severity**: Critical

2. Check if resolved IP is reasonable:
   - Normal: IP address matches expectations
   - Abnormal: Resolved to wrong or private IP -> **Root cause**: DNS cache pollution or DNS hijacking, **Severity**: Critical

3. Compare resolution results from different DNS servers:
   - Normal: Different DNS servers return consistent results
   - Abnormal: Specific DNS server resolution failed -> **Root cause**: DNS server configuration not suitable for current network environment, **Severity**: Warning
   - Abnormal: Different DNS servers return inconsistent results -> **Root cause**: Resolution differences exist between DNS servers, **Severity**: Info

### Step 6: DNS Suffix and NRPT Check

**Data Collection**:

> Collection target: Obtain DNS suffix search list and Name Resolution Policy Table (NRPT) configuration

- PowerShell script: [networking-dns.ps1](references/online/scripts/networking-dns.ps1) Section Step 6
- `GuestOS:DnsServerAddress` returns per-adapter information, can partially replace `Get-DnsClient` (per-adapter suffix configuration)

**Analysis Approach**:

1. Check DNS suffix search list:
   - Normal: Correct domain name suffixes configured (e.g., Alibaba Cloud intranet domain suffix)
   - Abnormal: No suffix search list configured -> **Root cause**: Short domain names cannot be resolved, **Severity**: Warning
   - Abnormal: Suffix list contains invalid domain names -> **Root cause**: DNS suffix configuration error causing resolution delay, **Severity**: Warning

2. Check NRPT rules (if any):
   - Normal: NRPT rules configured correctly and suitable for current network environment
   - Abnormal: NRPT rules blocking specific domain name resolution -> **Root cause**: NRPT policy blocking domain name resolution, **Severity**: Warning
   - Abnormal: NRPT rules pointing to unreachable DNS server -> **Root cause**: NRPT-configured DNS server unavailable, **Severity**: Critical

## Cross-References

| Type | Trigger Condition | Jump Target |
|------|---------|--------|
| Conditional jump | Step 2 no DNS server configured | -> [networking-tcpip.md](references/online/networking-tcpip.md) (Check DHCP or network config) |
| Parameterized reference | Step 5 DNS completely unavailable but IP connectivity normal | -> [networking-firewall.md](references/online/networking-firewall.md) (Check inbound/outbound UDP/TCP 53 port rules) |
| Chained successor | This file did not confirm root cause | -> None (DNS issues are usually located within this file) |


## Fix Recommendations

Fix plans for root causes confirmed in this file are in [networking-dns.md](references/online/fixes/networking-dns.md).
