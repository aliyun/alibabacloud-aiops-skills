# Scenario 3: Repair Failure Error Code Interpretation and Repository/Network Troubleshooting

This scenario addresses requests like "my vulnerability repair failed — what does error code XXX mean and how do I handle it": locate the repair failure cause (error code), provide the corresponding troubleshooting actions, and systematically troubleshoot Linux package repository and network issues (the most common root cause of repair failures).

## Trigger Conditions

Example user phrasings (enter this scenario when any matches):

- "Repair failed with error code 8009 / 8001 / 8037 — what does it mean?"
- "Error code xxx — help me figure out how to solve it"
- "Repair keeps failing — is it a yum repository problem?"
- "The repair button is grayed out and unclickable"
- "The console shows repair failed — where can I see the cause details?"

## Prerequisites

1. CLI and credential checks, session-id generation: see SKILL.md. All API commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>`.
2. Confirm the failure occurred in a "one-click repair" (Linux software vulnerabilities cve / Windows system vulnerabilities sys) scenario; application vulnerabilities (app/sca) and emergency vulnerabilities (emg) never support one-click repair — route directly to the manual repair path in references/scenario-repair.md.
3. Query commands in this scenario are read operations — execute directly; re-repair is a write operation requiring user confirmation, and auto-retry is forbidden.

## Error Code Retrieval Paths

Path 1 (API approach, recommended):

```bash
aliyun sas describe-vul-list --type cve --status-list 2 --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Filter Status=2 (fix failed); take `ResultCode` (error code) and `ResultMessage` (error detail summary) from the response.

Path 2 (console approach, guide the user to view it):

Security Center console → Risk Governance → Vulnerabilities → click the number under "Fixing" (this panel shows fixing, fixed-pending-reboot, and fix-failed categories) → click the status icon of a "fix failed" vulnerability → view the failure cause, error code, and handling suggestions in the "Cause Details" dialog.

> Only excerpt the summary of actual content; all information is subject to what the console's "Cause Details" actually displays.

## Three-Part Communication Pattern (follow when interpreting any error code)

1. **Restate first**: restate the error code and its official meaning to the user ("The official meaning of 8009 is 'update process is running', i.e., ...").
2. **Then troubleshoot**: provide the corresponding troubleshooting steps (see the quick reference table below); for server-side operations, give commands one by one and explain the risks.
3. **Then retry**: explain the retry method after handling is complete. **Retry repair is a write operation — it must be confirmed with the user again before execution, and auto-retry is forbidden**; if the failure cause is an incompatible target kernel, inform the user that the console supports a "force fix" retry (risks in references/scenario-repair.md Step 6 and references/scenario-nonstandard.md Branch A).

## High-Frequency Error Code Quick Reference Table

> The meanings and troubleshooting actions in this table are compiled from the official doc "Troubleshoot vulnerability fixing failures" (https://help.aliyun.com/zh/security-center/user-guide/troubleshoot-issues-that-cause-vulnerability-fixing-failures); error codes are continuously expanded — when no match is found, dynamically fetch the official error code page per references/doc-lookup.md to verify, and always defer to the console's "Cause Details" actual return. The error codes below apply to one-click repair of Linux software vulnerabilities and Windows system vulnerabilities.

### 1. Network and Repository Class (Linux)

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 8001 | download aegis.repo error: network anomaly or insufficient disk space — cannot download the Security Center repository file | Check network connectivity between the server and `update*.aegis.aliyun.com` (outbound 443/80, security group/firewall blocking); also check whether the disk is full |
| **8009** | **update process is running: the YUM repository in use is not Alibaba Cloud, or a repair process is already running** | Switch to the Alibaba Cloud YUM repository; if a repair process is running, retry later. **Special note**: the widely circulated claim "8009 = yum repository timeout" is inaccurate — the typical error for repository access timeout is `[Errno 12] Timeout on http://mirrors.aliyun.com/...`, plus timeout-class error codes 202/9002/9007/9008; distinguish carefully |
| 8037 | Could not resolve host: mirrors.cloud.aliyuncs.com (cannot access the Alibaba Cloud intranet repository; typical: non-Alibaba-Cloud / public-network-only hosts configured with the intranet repository) | Troubleshoot connectivity and blocking to mirrors.cloud.aliyuncs.com; if the server can access the public network, replace mirrors.cloud.aliyuncs.com with the public repository mirrors.aliyun.com in the repo files under /etc/yum.repos.d/, then retry repair |
| 8084 | Some index files failed to download (cannot access the download source; package metadata update failed) | Check whether security groups/firewalls block access to the download source |
| 8090 | The highest version upgradable from the current repository is lower than the minimum version required by the vulnerability fix | Check whether the current repository configuration is outdated or abnormal; update the repository configuration and retry |
| 256 | No more mirrors to try (third-party repository invalid, e.g., docker-ce repo 404/403) | Enter /etc/yum.repos.d/, locate the repo file with `grep -r "<invalid-repo-domain>"`, set `enabled` to 0 to disable it, then retry. Same-code scenario: **Bad GPG signature** (repository signature verification failure, typically because the server is not using the Alibaba Cloud official source) — check the current repository list with `yum repolist`, switch to the Alibaba Cloud official source (intranet mirrors.cloud.aliyuncs.com / public mirrors.aliyun.com, see Step 2), refresh the cache, and retry. Other scenarios with the same code: unfinished transactions — run `yum-complete-transaction --cleanup-only`; corrupted rpm database — run `rm -f /var/lib/rpm/__db.*`, `rpm --rebuilddb`, `yum clean all` in sequence to rebuild, then retry |
| 202 (Linux scenario) | timeout: patch installation timed out | Retry later; if the error details contain `[Errno 12] Timeout on http://mirrors.aliyun.com/...`, it is a Yum repository access timeout — troubleshoot per DNS and network steps (see the "Five-Step Generic Repository/Network Troubleshooting") |

### 2. Disk and Resource Class

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 8010 | Insufficient space in download directory /var/cache/yum/... (insufficient disk in the download directory) | Free disk space per the path in the error message, then re-run repair |
| 8080 | sh xxx killed (the repair process was killed by OOM due to insufficient memory) | Free some memory and retry |
| 8093 | no space left for creating initramfs (insufficient space in /boot; cannot create initramfs) | Clean up old kernel files under /boot and retry (cleanup procedure in references/scenario-recheck.md item #8) |

### 3. Dependency and Package Management Class (Linux)

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 8005 | /bin/rpm permit error (abnormal permissions executing /bin/rpm) | Set the /bin/rpm file permissions to 755 or 750 |
| 8012 | dpkg was interrupted (dpkg interrupted, dirty data left behind) | Run `dpkg --configure -a` on the server, then retry |
| 8019 | yum exception (the default Python environment for yum commands mismatches the yum file syntax) | Check /usr/bin/yum for syntax errors; check the Python environment configuration used to run yum |
| 8026 | Multilib version problems found (older-version package is protected and cannot be upgraded) | For high-severity vulnerabilities, manually uninstall the older-version package; for non-high-severity, suggest ignoring without upgrading |
| 8027 | A has missing requires of B (missing package dependency) | Run `yum update <package-name> --disableexcludes=all --disablerepo="*" --enablerepo="aegisbase,aegisupdates,aegisextras" --obsoletes` on the server, then re-run repair |
| 8028 | The old-version package cannot be removed normally (file permissions or service occupation) | Check permissions of package-related files, or stop the related service, then retry |
| 8033 | yum plugins protectbase enable (the ProtectBase plugin blocks package updates) | Edit /etc/yum/pluginconf.d/protectbase.conf, change `enabled = 1` to `enabled = 0`, then retry |

### 4. Kernel Class (Linux)

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 8040 | miss kernel grub file (kernel boot file missing) | Rebuild the kernel boot file and retry; CentOS 7 example: `grub2-mkconfig -o /boot/grub2/grub.cfg` |
| 8081 | blacklist process xxx is running (a blacklist process that locks the kernel config file is running) | Stop the blacklist process and retry |
| 8091 | qboot kernel (a qemu-booted kernel cannot install kernel patches) | Submit a ticket under the ECS product to resolve |
| 8094 | Signed kernel image cannot be upgraded/fixed | Ignore the vulnerability in the console, or wait for it to expire automatically |
| 8095 | vmlinuz or initramfs not exists (files not correctly generated during kernel package update) | Uninstall and reinstall the kernel package |
| 8096 | installed kernel not available in grub file (new kernel not added to grub boot entries) | Uninstall and reinstall the kernel package, or add a boot entry with the grubby command |

> Systematic handling of kernel-class errors (force-fix risks, manual kernel upgrade, old kernel cleanup) in references/scenario-nonstandard.md Branch A.

### 5. OS and Distribution Class (Linux)

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 8008 | not support this system xxx (the OS type was manually changed after detection; system mismatches the vulnerability record) | Ignore the vulnerability in the console, or wait for it to expire automatically |
| 8041 | redhat not subscription (the server is not registered with a Red Hat subscription) | Register an account on the Red Hat website and purchase a subscription (each server needs a separate subscription); if purchasing is not feasible, refer to the 8082/8083 approach of switching to the Alibaba open-source mirror site |
| 8082 / 8083 | redhat source has expired / redhat has no available source (RHEL repository expired or not configured) | Go to the Alibaba open-source mirror site (https://developer.aliyun.com/mirror) to fix the software repository, then retry |
| 8085 / 8086 | alinux / anolis source not found (Alinux/Anolis repository not correctly configured) | Reconfigure the official repository for the corresponding system at the Alibaba open-source mirror site |
| 8092 | package not available on the current system (the fix package is unavailable on the current system) | Ignore the vulnerability in the console, or wait for it to expire automatically |

### 6. Timeout Class

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 202 | timeout (patch installation timed out) | Re-run repair via the console later; contact technical support after repeated failures |
| 9002 | timeout (repair timed out; affected by network jitter or server environment) | Retry later; contact technical support if repeated retries fail |
| 9003 | xxx is already the newest version (the command succeeded and it is already the newest version, but the vulnerability persists — the repository is not new enough or not an Alibaba Cloud repository) | Set the repository to the Alibaba Cloud repository (mirrors.cloud.aliyuncs.com or mirrors.aliyun.com) and re-run repair; contact technical support if it still fails |
| 9007 | ack timeout (package upgrade execution timed out) | Retry later; contact technical support if repeated retries fail |
| 9008 | rpm collect timeout (package collection timed out) | Retry later; contact technical support if repeated retries fail |

### 7. Windows Class

| Error Code | Official Meaning (ErrorMessage summary) | Troubleshooting Action |
|---|---|---|
| 116 | download file failed (Windows patch download failed) | Re-run repair later; contact technical support after repeated failures |
| 124 | Windows Modules Installer / Windows Update service disabled | Enable the corresponding service: Win+R → services.msc → find Windows Modules Installer (and Windows Update) → right-click Start; command line: `sc config wuauserv start= auto` then `net start wuauserv` (same for the TrustedInstaller service) |
| 125 | exit code:0x00000005 (security software blocking or virus infection; process fails to start / file cannot be opened) | Troubleshoot and remove the security software blocking, then retry |
| 127 | ERROR_DISK_FULL (insufficient disk space; patch installation failed) | Free disk space (disk cleanup tool, delete temp files, move large files), then retry |
| 130 | exit code:0x00000008 (insufficient host memory) | Check memory/CPU usage; repair after returning to normal |
| 132 | exit code:0x80240017 (a patch is being installed, or an installed patch awaits reboot to take effect) | Wait for patch installation to complete; or reboot the host after confirming no impact, then repair |
| 133 | xxx.exe is running (patch installation blocked by security software) | Troubleshoot and remove the security software blocking, then retry |
| 134 | exit code:0x800F0982 (too many file system symbolic links) | Clean up the disk, reduce excessive symbolic links, run a disk check; if necessary, temporarily disable Windows Defender before installing the patch |
| 202 (Windows scenario) | timeout (patch installation timed out) | Retry later; contact technical support after repeated failures |
| 300 / 309 | rtap running error / execute rtap task fail (security software blocking causes client script execution failure) | Troubleshoot and remove the security software blocking, then retry |
| 8007 | windows update damaged (critical system files damaged; the update service cannot run) | **Create a snapshot to back up data first.** Then: stop the Windows Update service (set to Manual and stop in services.msc; if stopping fails, set to Manual, reboot, then stop) → delete all contents in C:\Windows\SoftwareDistribution → run `sfc /scannow` in an administrator cmd, reboot after completion → restart the Windows Update service (set to Automatic) → reinstall the patch and reboot afterwards; if it still fails, back up data and consider reinstalling the OS |
| 60001 | start vulfix:[Error 2] The system cannot find the file specified (security software blocking; repair process fails to start) | Troubleshoot and remove the security software blocking, then retry |

> **Must-read after the table**: error codes are continuously expanded. For an error code not in this table, query the official error code page (https://help.aliyun.com/zh/security-center/user-guide/troubleshoot-issues-that-cause-vulnerability-fixing-failures) via the dynamic retrieval chain in references/doc-lookup.md, and always defer to the console's "Cause Details" actual return.

## Error Code Quick Routing Table

After obtaining the error code, triage per this table to avoid flipping through every table:

| Error Code Pattern | Route To |
|---|---|
| 8001/8009/8037/8084/8090/256/202/9002/9003/9007/9008 (repository/network, timeout class) | Run the "Five-Step Generic Repository/Network Troubleshooting" in this doc first — resolves most cases |
| 8005/8010/8012/8019/8026/8027/8028/8033/8080 (dependency, package management, disk resources) | Handle item by item per the quick reference table (mostly single-point server-side operations); retry after handling |
| 8040/8081/8091/8093/8094/8095/8096 (kernel class) | Route to references/scenario-nonstandard.md Branch A (force-fix risks and manual kernel upgrade); for 8093, clean /boot first |
| 8008/8041/8082/8083/8085/8086/8092 (OS and distribution class) | Handle per the quick reference table; 8092/8008 are mostly ignore-or-wait-for-expiry |
| 116/124/125/127/130/132/133/134/202/300/309/8007/60001 (Windows class) | Handle per the quick reference table; for service-class issues, enable Windows Update and Windows Modules Installer first |
| No match in the table | Dynamically query the official error code page per references/doc-lookup.md |

## User Communication Key Points

Error code interpretation phrasing template (three-part example, using 8009):

1. Restate the meaning: "The error code of your failed record is 8009; its official meaning is 'update process is running' — the YUM repository your server uses is not the Alibaba Cloud repository, or a repair process is already running. By the way: the internet often explains 8009 as 'yum repository timeout', which is inaccurate — repository timeouts report Errno 12 Timeout or timeout-class codes like 202/9002, which is not your case."
2. Troubleshooting guidance: "Two suggestions: first, switch the YUM repository to the Alibaba Cloud repository (I can provide the commands); second, if a repair task was running, wait a few minutes and retry."
3. Retry confirmation: "After handling is done we need to re-initiate repair. Repair is a write operation — please confirm before I execute it, and I will not auto-retry after failures."

Other common phrasings:

- Unknown error code: "This error code is not in the high-frequency list. Let me check the latest official documentation before giving you an accurate explanation — no blind retries first."
- Repeated failures: "The same vulnerability has failed X consecutive times. I suggest completing the five-step repository/network troubleshooting first to resolve it in one pass before retrying, to avoid repeatedly occupying the repair window."
- Before high-risk Windows operations: "Next we need to stop the Windows Update service and clear the update cache directory, which briefly affects the workload. I recommend creating a snapshot first — we proceed after your confirmation."
- Result explanation (after handling): "Repository switch and cache refresh are done. I suggest re-initiating repair; success is determined by the console status changing to 'fixed / fixed-pending-reboot'."

## Five-Step Generic Repository/Network Troubleshooting (the first-choice systematic troubleshooting for repair failures)

The five steps below are the generic handling for repository/network-class errors such as 8001/8009/8037/8084/8090/256/202/9002/9003/9007/9008. Official guidance states that "preferentially using the Alibaba Cloud repository for vulnerability repair" significantly improves the repair success rate.

### Step 1: Enable "prefer Alibaba Cloud repository for vulnerability repair" in the console

Intent: make Security Center prefer the Alibaba Cloud repository during repair (an account-level setting — small change, big benefit).

```bash
aliyun sas describe-vul-config --type yum --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Query the current configuration; if not enabled, explain the benefit to the user before modifying (write operation — requires user confirmation):

```bash
aliyun sas modify-vul-config --type yum --config on --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- See references/api-reference.md for parameter value details.

### Vulnerability Management Settings Check and Modification (full modify-vul-config configuration items)

Continuing Step 1: Step 1 only used Type=yum (prefer Alibaba Cloud repository). This subsection covers all configuration items of vulnerability management settings, for handling "configuration-change requests" (users asking to adjust scan switches, scan severity, Alibaba Cloud repository, retention duration, etc.). Mapping of each configuration item to read/write channels:

| Type | Purpose | Read (describe-vul-config) | Write (modify-vul-config) |
|---|---|---|---|
| cve / sys / cms / app / emg | Detection switch per vulnerability type | Supported (Config=on/off) | Supported (Config=on/off) |
| yum | Prefer Alibaba Cloud repository for vulnerability repair | Supported | Supported (i.e., five-step Step 1) |
| scanMode | Show real-risk vulnerabilities (real-risk mode) | Supported (Config=real=real risks only/all=all vulnerabilities) | Supported (Config=real/all) |
| imageVulClean | Vulnerability retention duration (days) | Supported (Config=retention days) | Not supported: retention duration is only viewable via describe-vul-config; the modification channel is subject to official documentation |

Usage key points:

1. Check (read operation — execute directly; omitting `--type` returns all type configurations, pass `--type cve`/`--type scanMode` etc. as needed):

```bash
aliyun sas describe-vul-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

2. Modify (write operation — confirmation gate: first present the change list to the user — configuration item, current value, target value, impact description (e.g., disabling detection of a type means vulnerabilities of that type are no longer detected) — execute only after explicit user confirmation):

```bash
aliyun sas modify-vul-config --type <config-type> --config <target-value> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

3. Vulnerability scan severity (filtering cve/sys vulnerability scans by high/medium/low severity) has no corresponding API configuration item — use the console: Security Center console → Risk Governance → Vulnerabilities → Vulnerability Management Settings; the exact location of the setting is subject to official documentation — dynamic retrieval in references/doc-lookup.md (consistent with references/scenario-recheck.md troubleshooting table #4).
4. After modification, re-check with describe-vul-config to confirm it took effect (verification method in references/verification-method.md Scenario 3②); write-operation failures are not auto-retried.

### Step 2: Switch to the Alibaba Cloud repository on the server side

- Alibaba Cloud intranet machines (ECS etc.): use the intranet repository `mirrors.cloud.aliyuncs.com` (no public-network egress, faster).
- Non-Alibaba-Cloud / public-network-only machines: use the public repository `mirrors.aliyun.com` (configuring the intranet repository causes 8037).
- Repository-switching guides per system are on the Alibaba open-source mirror site: https://developer.aliyun.com/mirror (provides one-click scripts and manual configuration instructions for CentOS, Ubuntu, etc.; subject to official tutorials).
- Ubuntu brief: back up /etc/apt/sources.list, replace the repository addresses with `https://mirrors.aliyun.com/ubuntu/` (use `mirrors.cloud.aliyuncs.com` for Alibaba Cloud intranet machines); then run `apt-get update` to refresh.
- CentOS brief: back up, then edit the repo files under /etc/yum.repos.d/ (e.g., CentOS-Base.repo), pointing baseurl/mirrorlist to the corresponding paths on the Alibaba mirror site (use mirrors.cloud.aliyuncs.com for intranet machines); then run `yum clean all && yum makecache` to refresh. For CentOS 8 and later, note the vault archive repository (after a version reaches EOL, the official repository goes offline and the vault path must be used).
- Before switching, confirm the server can reach the target repository: `curl -I http://mirrors.aliyun.com/` — avoid switching to an unreachable repository. Details are subject to the mirror site's official documentation.

### Step 3: Refresh the repository cache and retry repair

```bash
yum clean all && yum makecache
```

```bash
apt-get update
```

- After the refresh, re-run repair in the console (write operation — requires user confirmation).

### Step 4: Network connectivity check

Domain and port allow-list (present to the user's network administrator):

| Purpose | Domain/CIDR | Port |
|---|---|---|
| Command delivery | jsrv*.aegis.aliyun.com | 80 |
| Plugin and repository downloads | update*.aegis.aliyun.com | 443/80 outbound |
| Alibaba Cloud public software repository | mirrors.aliyun.com | 80/443 |
| VPC intranet scenarios | 100.100.0.0/16 plus wildcard domains *.aegis.aliyun.com, *.aegis.aliyuncs.com, *.alicdn.com | 80/443 |

- Example check commands:

```bash
ping -c 4 mirrors.aliyun.com
```

```bash
nslookup update.aegis.aliyun.com
```

```bash
telnet mirrors.aliyun.com 80
```

```bash
curl -I --connect-timeout 5 http://mirrors.aliyun.com/repodata/repomd.xml
```

- Command interpretation: ping tests reachability and packet loss; nslookup verifies DNS resolution (use first for 8037-class errors); telnet/curl verify port and HTTP availability (curl preferred — status codes are visible).

### Step 5: Server-side cause checklist for "grayed-out repair button"

When the user reports the repair button is grayed out (repair conditions not met), check server-side causes item by item:

| Possible Cause | How to Determine | Handling |
|---|---|---|
| Insufficient Linux disk free space (below about 3GB) | `df -h` | Clean up the disk or expand it |
| Insufficient Windows disk free space (below about 500MB) | Check the C drive in Explorer | Clean up the disk or expand it |
| yum/apt process occupied | `ps aux \| grep -E "yum\|apt"` | Wait or kill unrelated update processes |
| Relevant files lack root permissions | Check permissions of the error path | Fix permissions (e.g., for 8005 set /bin/rpm to 755/750) |
| Windows Update service disabled | Check in services.msc | Enable the service (see error code 124) |
| No patches available for an EOL (end-of-life) system | Confirm whether the OS version has reached end of maintenance | Upgrade the OS (see references/scenario-nonstandard.md Branch E) |

> Other non-server-side causes of a grayed-out button (edition not supported, type does not support one-click repair, etc.) in references/scenario-repair.md pre-fix chain.

## Official Documentation Cross-Check Record

Differences and phrasing notes after cross-checking this table with the official doc "Troubleshoot vulnerability fixing failures" (for maintainers; no need to expand to users):

| Item | Official Page Phrasing | This Table's Handling |
|---|---|---|
| 8009 | "update process is running": YUM repository is not Alibaba Cloud, or a repair process is running | Consistent with the official phrasing; keep the special note correcting the "8009 = yum repository timeout" misinformation |
| 202 | ErrorMessage is timeout; possible cause "patch installation timeout" (listed in the Windows error code section) | 202 is included in both the timeout class and the Windows class; keep the distinction that "Errno 12 Timeout is the typical error for Yum repository access timeout" |
| 8041 | Solution is to register a Red Hat account and purchase a subscription (official docs do not mention switching repositories) | "Purchase subscription" is the primary phrasing; the open-source mirror site approach of 8082/8083 is only a supplementary hint |
| 256 | Contains multiple sub-scenarios (invalid third-party repository, Bad GPG signature, unfinished transactions, corrupted rpmdb, package conflicts, missing yum.conf) | Merged into a single row with multiple actions to avoid item-by-item bloat; the Bad GPG signature sub-scenario is supplemented by a field-tested case (see Case 5) |

## Typical Failure Combination Cases

Case 1 (compounded repository issues): a user batch-repaired 30 CentOS servers; all reported 8001 and some reported 8009. Handling: first check security-group blocking of outbound 443/80 to update*.aegis.aliyun.com (resolves 8001), then enable "prefer Alibaba Cloud repository" in the console and switch repositories (resolves 8009), refresh the cache, and retry in batches.

Case 2 (non-Alibaba-Cloud host): an RHEL host on AWS reported 8037 during repair. Cause: the host was configured with the Alibaba Cloud intranet repository mirrors.cloud.aliyuncs.com, which cannot be resolved in a public-network environment. Handling: switch to the public repository mirrors.aliyun.com. See references/scenario-nonstandard.md Branch B for details.

Case 3 (Windows service disabled): all repairs on a Windows Server failed with 124. Handling: enable Windows Update and Windows Modules Installer in services.msc, set them to Automatic, and retry repair.

Case 4 (disk near capacity): a single server reported 8010 with a grayed-out repair button. Handling: df -h showed insufficient free space on the root disk; cleaned up and retried (grayed-out button thresholds in the Step 5 checklist).

Case 5 (Bad GPG signature — field-tested): a Linux vulnerability repair failed with error code 256 and "Bad GPG signature" in the error message. Cause: the server was not using the Alibaba Cloud official source; a third-party repository's GPG signature verification failed. Handling: run `yum repolist` to confirm the current repository list, switch to the Alibaba Cloud official source (Step 2), run `yum clean all && yum makecache` to refresh, then confirm with the user before retrying repair.

## Notes and Boundaries

- **Retry discipline**: all "re-run repair" actions are write operations requiring user confirmation; auto-retry is forbidden. If the same vulnerability fails 2 or more consecutive times, complete the five-step repository/network troubleshooting before retrying, and explain this to the user.
- **Error code semantics defer to official sources**: this table is compiled from official documentation; if it conflicts with the console's "Cause Details" or the latest official documentation, the official version prevails — fetch the latest version per references/doc-lookup.md to verify.
- **8009 misinformation risk**: always explain 8009 to users per this table's phrasing (update process is running); do not perpetuate the "yum repository timeout" misinformation — repository timeouts show Errno 12 Timeout errors and 202/9002/9007/9008.
- **Agent-offline failures**: if the failure cause details point to abnormal network connectivity or an offline Agent, restore the client online first (point to the `alibabacloud-sas-install-agent` skill), then retry repair.
- Windows error codes involving stopping services, clearing directories, and sfc scans have workload impact — confirm with the user item by item and suggest creating a snapshot first.
- Server-side commands (repository switching, rpmdb rebuild, uninstalling kernel packages, etc.) all execute on the user's server, by the user or with their authorization; when providing commands, also provide risk descriptions and rollback methods (e.g., back up configuration files first).
- When multiple vulnerabilities on the same server fail consecutively with different error codes, resolve repository/network-class issues first (the first branch) — most dependency-class errors disappear afterwards.

## Related Documents

- Command parameters and response fields: [references/api-reference.md](api-reference.md)
- Dynamic retrieval of the official error code page: [references/doc-lookup.md](doc-lookup.md)
- Repair flow and pre-fix chain (retry entry): [references/scenario-repair.md](scenario-repair.md)
- Systematic handling of kernel-class errors: [references/scenario-nonstandard.md](scenario-nonstandard.md)
- EOL systems and repository-switching details: [references/scenario-nonstandard.md](scenario-nonstandard.md)
- Scenario entry and boundary overview: [../SKILL.md](../SKILL.md)
