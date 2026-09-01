# Global Baseline Health Check

## Overview

A full-dimension system baseline scan that does not depend on problem domain classification. When a problem cannot be matched to any known domain, no findings are discovered after domain-level investigation, or the user only requests "check the system" without specific fault symptoms, load this file to perform a full-dimension scan of event logs, core services, disk storage, network connectivity, resource utilization, recent changes, and security baseline, then route to relevant domain files for in-depth investigation based on scan results.

**Input**: User problem description (optional), user-reported time window (optional, default 24 hours)
**Output**: Baseline anomaly item list (each item includes severity / evidence / explanation); routing suggestions are provided when anomaly items point to specific domains; a baseline health conclusion is output when all items are normal

## Trigger Conditions

- Problem domain cannot be matched to any known domain during path planning
- No findings after domain-level investigation (unified fallback entry)
- User requests "check the system" with no specific fault symptoms

## Step Selection Guide

This file contains 7 baseline check steps, all executed in order by default; only relevant steps may be executed when the user has a clear direction:

| User Symptom | Recommended Steps |
|-------------|---------------|
| No specific symptoms / no findings across all domains | Step 1 -> Step 2 -> Step 3 -> Step 4 -> Step 5 -> Step 6 -> Step 7 |
| Suspected performance/resource issue but domain undetermined | Step 1 -> Step 5 -> Step 6 |
| Suspected change-induced issue but domain undetermined | Step 1 -> Step 6 |

## Diagnostic Steps

### Step 1: Full Event Log Scan

**Data Collection**: Collect Error/Critical level events from the System / Application / Security logs within the user-reported time window, and identify high-frequency or abnormal events by Event ID clustering (clustered output includes Source and first sample Message, which can be directly used for domain routing)

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 1

**Analysis Approach**:

1. Check high-frequency events and abnormal events in the clustering results:
   - Normal: No Error/Critical events within the time window, or only known harmless events
   - Abnormal: High-frequency events or events matching the user's symptom time exist -> Route to the corresponding domain based on event source and content (storage -> storage-*, network -> networking-*, services -> system-*, logon -> identity-* / rdp-*), **Severity**: Warning, and load the corresponding domain file for in-depth investigation based on routing results
2. Critical level events (e.g., Kernel-Power 41, BugCheck) exist -> Prioritize recording, associate with [system-crash.md](references/online/system-crash.md)

### Step 2: Core Service Health

**Data Collection**: Collect status and startup type of core services such as TermService, RpcSs, Winmgmt, WinRM, wuauserv, CryptSvc, BITS, EventLog, Schedule, Spooler

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 2

**Analysis Approach**:

1. Check core service running status and startup type:
   - Normal: All core services are running (or have on-demand startup type with no failure records)
   - Abnormal: Core service not running or disabled -> **Anomaly item**: Core service anomaly (record service name), **Severity**: Critical (RPC/WMI/EventLog and other infrastructure services) or Warning (others); route by service domain (TermService -> rdp-*, wuauserv/BITS -> system-update)

### Step 3: Disk and Storage Health

**Data Collection**: Collect space utilization and health status of each volume, disk offline/read-only status, physical disk health status

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 3

**Analysis Approach**:

1. Check volume space and health status:
   - Normal: All volumes have sufficient free space (>=10%), no offline/read-only disks, health status normal
   - Abnormal: System volume free space <10% -> **Anomaly item**: Insufficient disk space, **Severity**: Critical (system volume) or Warning (data volume)
   - Abnormal: Offline/read-only disks or health status abnormal -> **Anomaly item**: Disk status anomaly, **Severity**: Critical; route to [storage-disk.md](references/online/storage-disk.md) / [storage-hardware.md](references/online/storage-hardware.md)

### Step 4: Network Basic Connectivity

**Data Collection**: Collect network adapter status, default gateway reachability, DNS resolution test results, key port (3389/80/443) listening status

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 4

**Analysis Approach**:

1. Determine layer by layer following "network adapter -> gateway -> DNS -> port":
   - Normal: Network adapter Up, gateway reachable, DNS resolution successful, expected ports in listening state
   - Abnormal: Network adapter down / gateway unreachable / DNS resolution failed / port not listening -> **Anomaly item**: Network baseline anomaly (record the failing layer), **Severity**: Warning; route to networking-tcpip / networking-dns / networking-firewall / rdp-service by failing layer

### Step 5: Resource Utilization Snapshot

**Data Collection**: Collect CPU utilization, available memory, page file configuration, Top 5 processes (sorted by CPU and memory respectively)

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 5

**Analysis Approach**:

1. Check resource levels and consumption sources:
   - Normal: CPU <=80%, available memory >=500MB, page file configuration reasonable
   - Abnormal: CPU >80% or available memory <500MB -> **Anomaly item**: Resource level anomaly (record Top processes), **Severity**: Warning; route to [performance-slow.md](references/online/performance-slow.md)

### Step 6: Recent System Changes

**Data Collection**: Collect patches and software installed in the last 7 days, the last 3 power on/off events, pending reboot status

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 6

**Analysis Approach**:

1. Check the association between changes and the fault time window:
   - Normal: No recent changes, or changes are unrelated to the fault time
   - Abnormal: Fault onset highly coincides with a patch/software installation/restart -> **Anomaly item**: Recent change suspected of introducing anomaly (record change identifier for subsequent verification and rollback), **Severity**: Warning
   - Abnormal: Pending reboot status exists -> **Anomaly item**: System is in pending reboot state, **Severity**: Warning

### Step 7: Security Baseline

**Data Collection**: Collect firewall Profile status, BitLocker status, Windows Defender status

- PowerShell script: [system-health-check.ps1](references/online/scripts/system-health-check.ps1) Section Step 7

**Analysis Approach**:

1. Check security baseline configuration:
   - Normal: Firewall profile state -- ALL profiles disabled is the expected default configuration on Alibaba Cloud ECS (security groups provide network-layer isolation) and MUST NOT be reported as an anomaly; one or more profiles enabled is also normal. BitLocker and Defender status as expected
   - Abnormal: Protection measures abnormal (BitLocker/Defender anomalies) -> **Anomaly item**: Security baseline anomaly (record specific items), **Severity**: Warning; route to security-bitlocker / security-malware corresponding files for review
2. When security status is unrelated to the user's problem, only record honestly without forcing a root cause association

## Results Summary and Routing

- Anomaly items exist -> Load the corresponding investigation file for in-depth identification by anomaly item domain, and explain the scope covered by the baseline check
- All normal -> Honestly output the baseline health conclusion and the scope investigated, inform the user that current diagnostic capability has found no anomalies, and suggest reproducing the collection or escalating to expert support

## Cross-References

| Type | Trigger Condition | Target |
|------|---------|--------|
| Conditional routing | Step 1 event clustering points to a specific domain | -> Corresponding domain investigation file (storage-* / networking-* / system-* / rdp-* / identity-*) |
| Conditional routing | Step 3 disk status anomaly | -> [storage-disk.md](references/online/storage-disk.md) / [storage-hardware.md](references/online/storage-hardware.md) |
| Conditional routing | Step 5 resource level anomaly | -> [performance-slow.md](references/online/performance-slow.md) |
| Chain successor | All steps have no anomaly items | -> Honestly record baseline conclusion, suggest reproducing collection or escalating to expert support |

## Fix Recommendations

Fix plans for anomalies surfaced by this baseline scan are addressed by the conditional routing targets in the Cross-References table above (storage-* / networking-* / system-* / rdp-* / identity-* / performance-slow domain files); this file itself defines no fixes.
