---
name: alibabacloud-nas-mount-diagnosis
description: Diagnose and troubleshoot Alibaba Cloud NAS mount failures. Use when users encounter NAS mount errors on Linux or Windows, including NFS and SMB protocol mount failures, network connectivity issues, permission group misconfigurations, security group port blocks, or specific error codes like "mount.nfs No such device", "access denied by server", Windows system error 53/58/64/67/85/1231/1272/1312/3227320323, and auto-mount failures on boot. Covers both General Purpose NAS and Extreme NAS file systems. Also handles container (K8s/Docker) NAS mount issues, cross-VPC/cross-account mount problems, and ECS cloud assistant batch mount failures.
license: Apache-2.0
compatibility: >
  Requires aliyun CLI >= 3.0.0 (Alibaba Cloud CLI tool).
  Requires valid AccessKey credentials configured (aliyun configure).
  Script execution requires Python >= 3.6.
metadata:
  domain: aiops
  owner: nas-team
  contact: nas-agent@alibaba-inc.com
allowed-tools: Bash Read aliyun
---

# NAS Mount Failure Troubleshooting

Diagnose and resolve Alibaba Cloud NAS mount failures, covering NFS/SMB protocol mount scenarios on Linux/Windows systems.

## Prerequisites

### CLI Tools
- **aliyun CLI**: Used to query NAS file systems, mount targets, permission groups, ECS security groups, etc.
- Installation reference: https://help.aliyun.com/document_detail/139508.html

### aliyun CLI Initialization

Before each diagnosis, update plugins to avoid timeout during auto-install:

```bash
aliyun plugin update
```

**CLI usage notes:**
- aliyun CLI outputs JSON by default. Do NOT add `--output json` or any output format flags — they will cause errors.
- If a command fails due to plugin auto-installation (timeout or prompt), run `aliyun plugin update` first, then retry the exact same command.
- If a command times out, retry it — do NOT skip it or substitute with data from other API responses.

## Observability

All `aliyun` CLI invocations during a diagnosis session MUST include the `--user-agent` flag for tracing:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-nas-mount-diagnosis/{session-id}
```

**session-id generation rule:**
- Generate once at the start of each diagnosis session
- Format: 32-character lowercase hexadecimal string (e.g. `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`)
- Use the same session-id consistently across all CLI calls within the session
- Example generation: `python3 -c "import uuid; print(uuid.uuid4().hex)"`

**Example usage:**
```bash
aliyun nas describe-file-systems --file-system-id 18bfd49621 --region cn-beijing --user-agent AlibabaCloud-Agent-Skills/alibabacloud-nas-mount-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

> **Forbidden:** Do NOT use deprecated mechanisms such as `aliyun configure ai-mode`, `export ALIBABA_CLOUD_USER_AGENT`, or any global UA configuration. Always pass `--user-agent` per-command.

### Alibaba Cloud Credentials
Credentials must be configured via aliyun CLI profile. Reference: https://help.aliyun.com/document_detail/123181.html

### Network Requirements
- The machine running the diagnosis must have access to Alibaba Cloud OpenAPI
- For remote ECS diagnosis, SSH access or Cloud Assistant installation is required

## Required RAM Permissions

This skill only performs read-only diagnostic operations without any write operations. See `references/ram-policies.md` for the complete list of required RAM permissions and recommended policies.

## Workflow

### Step 1: Collect Basic Information

Before starting troubleshooting, collect the following information from the user:

| Information | How to Ask |
|-------------|-----------|
| **Mount target address** | "Please provide the NAS mount target address, e.g. `file-system-id.region.nas.aliyuncs.com`" |
| **File system protocol** | "Is the mount using NFS or SMB protocol?" |
| **Operating system** | "Is the ECS instance running Linux or Windows? What specific version?" |
| **Error message** | "Please provide the complete error message" |
| **Mount command** | "Please provide the mount command you executed" |
| **Region** | "The region where the NAS file system is located (e.g. cn-hangzhou)" |

#### Identifying NAS Type and Extracting File System ID from Mount Target Address

If the user provides a mount target address, the NAS type, Region, and file system ID can be extracted directly from the domain format without additional questions:

| NAS Type | Mount Target Domain Format | Example | File System ID Extraction Rule |
|----------|---------------------------|---------|-------------------------------|
| **General Purpose** | `<fsid>-<suffix>.<region>.nas.aliyuncs.com` | `18bfd49621-nyh99.cn-beijing.nas.aliyuncs.com` | fsid = part before first `-` → `18bfd49621` |
| **Extreme** | `<hex-id>-<suffix>.<region>.extreme.nas.aliyuncs.com` | `014020e9-ohem.cn-beijing.extreme.nas.aliyuncs.com` | fsid = `extreme-` + part before first `-` → `extreme-014020e9` |

**Quick identification:** Domain containing `.extreme.` indicates Extreme NAS; otherwise it is General Purpose NAS. Region can be extracted directly from the second segment of the domain (e.g. `cn-beijing`).

### Step 2: Pre-checks

Before deep troubleshooting, confirm the following basic conditions:

1. **Mount target status check** — Call `DescribeMountTargets` API to check mount target VPC and status. This API MUST be called independently and return successfully (2xx); do NOT substitute with data from other APIs like `DescribeFileSystems`.
   ```bash
   aliyun nas describe-mount-targets --file-system-id <file-system-id> --region <region>
   ```
   If the mount target is hibernated, instruct the user to re-enable it via the console or OpenAPI.

   > **Important:** If `DescribeMountTargets` returns 404 or an error, the most likely cause is an incorrect `--region` value. Extract the correct region from the mount target domain (e.g. `xxx.cn-beijing.nas.aliyuncs.com` → region is `cn-beijing`) and retry.

2. **Account balance check** — Confirm the account is not in arrears. Overdue payment will stop NAS service.

3. **File system info query** — Get file system type and protocol information
   ```bash
   aliyun nas describe-file-systems --file-system-id <file-system-id> --region <region>
   ```

### Quick Diagnosis: Error Message Pattern Matching

Before entering the full troubleshooting workflow, check if the error message can directly identify the issue:

- **Error contains `access denied by server while mounting` AND mount path includes a subdirectory** (e.g. `:/data`, `:/share/subdir`) → **Most likely cause: subdirectory does not exist**. For both General Purpose and Extreme NAS, manually mounting a subdirectory will not auto-create it; a non-existent subdirectory reports access denied. Solution: mount root directory `:/` first, create the subdirectory, then remount the subdirectory.
- **Error `mount.nfs: No such device`** → sunrpc module misconfiguration, see "Common Error Quick Reference" table.
- **Error contains Windows system error code** → See "Common Error Quick Reference" table directly.

If the issue cannot be quickly identified from the error message, proceed to the scenario-based troubleshooting below.

### Step 3: Scenario-Based Troubleshooting

Based on the user's operating system and protocol type, enter the corresponding troubleshooting flow:

#### Scenario A: Linux NFS Protocol Mount Failure

Recommend the user first run the official auto-check script for quick diagnosis:

```bash
# Download auto-check script
wget --timeout=30 https://nas-client-tools.oss-cn-hangzhou.aliyuncs.com/linux_client/check_alinas_nfs_mount.py -P /tmp/

# Run check
python2.7 /tmp/check_alinas_nfs_mount.py <mount-target-address>:/ /mnt
```

If the auto script cannot locate the issue, proceed to manual troubleshooting. See `references/nfs-linux-errors.md`.

Manual troubleshooting checklist:
1. **Subdirectory mount check** — If the mount path includes a subdirectory (e.g. `:/data`, `:/share/subdir`) and the error is `access denied`, the most likely cause is the subdirectory does not exist. **This rule applies to both General Purpose and Extreme NAS**. Solution: first mount root directory `sudo mount ... <mount-target>:/ /mnt`, run `mkdir /mnt/<subdir>` to create it, then unmount and remount the subdirectory
2. **NFS client installation check** — Confirm `nfs-utils` (RHEL/CentOS) or `nfs-common` (Debian/Ubuntu) is installed
3. **Network connectivity** — `ping <mount-target-address>` to check network
4. **Port connectivity** — `telnet <mount-target-address> 2049` to check NFS port
5. **Permission group configuration** — Use API to check if permission group allows ECS access
6. **VPC consistency** — Confirm ECS and mount target are in the same VPC or connected via Cloud Enterprise Network (CEN)
7. **Security group rules** — Check if security group egress blocks NFS port 2049 (note the difference between normal and enterprise security groups; see "Security Group Rule Inspection" section)
8. **Mount command format** — Verify mount command parameters are correct

Standard mount commands are in `references/nfs-linux-errors.md` (Error 2 resolution includes standard mount commands for General Purpose NFS v3/v4 and Extreme NAS).

#### Scenario B: Windows SMB Protocol Mount Failure

Recommend the user first run the official auto-check script:

```powershell
# Download inspection script
Invoke-WebRequest -TimeoutSec 30 https://nas-client-tools.oss-cn-hangzhou.aliyuncs.com/windows_client/alinas_smb_windows_inspection.ps1 -OutFile alinas_smb_windows_inspection.ps1

# Run inspection script
.\alinas_smb_windows_inspection.ps1 -MountAddress <mount-target-address> -Locale zh-CN
```

If the auto script cannot locate the issue, proceed to manual troubleshooting based on the error code. See `references/smb-windows-errors.md`.

Manual troubleshooting checklist:
1. **Port 445 connectivity** — `telnet <mount-target-address> 445`
2. **Network services** — Confirm TCP/IP NetBIOS Helper and Workstation services are running
3. **VPC consistency** — Confirm ECS and mount target are in the same VPC
4. **Permission group configuration** — Check if permission group allows ECS IP access
5. **Mount command format** — `net use <drive-letter> \\<mount-target-address>\myshare`

#### Scenario C: Linux SMB Protocol Mount Failure

Troubleshooting steps:
1. **OS version check** — Confirm Linux version is within NAS SMB supported range (see `references/smb-linux-requirements.md`)
2. **CIFS client check** — Confirm `cifs-utils` is installed
3. **Network connectivity** — `ping <mount-target-address>` and `telnet <mount-target-address> 445`
4. **VPC and account consistency**
5. **Permission group configuration**
6. **root/sudo privileges**
7. **Mount command correctness**:
   ```bash
   sudo mount -t cifs //<mount-target-address>/myshare /mnt -o vers=2.0,guest,uid=0,gid=0,dir_mode=0755,file_mode=0755,mfsymlinks,cache=strict,rsize=1048576,wsize=1048576
   ```
8. **SELinux settings**
9. **Mount connection limit** — Maximum 1000 per file system

#### Scenario D: Windows NFS Protocol Mount Failure

Troubleshooting steps:
1. **Account consistency** — ECS and mount target belong to the same account
2. **VPC consistency**
3. **Port check** — Ports 2049 and 111
   ```powershell
   Test-NetConnection <mount-target-address> -Port 2049
   Test-NetConnection <mount-target-address> -Port 111
   ```
4. **Permission group configuration**

#### Scenario E: Container (K8s/Docker) NAS Mount Failure

When error `access denied by server while mounting <mount-address>` occurs:
1. Confirm the mount directory exists
2. Confirm the container startup user has root privileges (container must run in privileged mode)
3. Confirm the mount target permission group includes the container IP

### Step 4: API-Assisted Diagnosis

Perform automated checks via Alibaba Cloud API. **Each API below must be called independently and return 2xx**; do not skip any API by using data embedded in other API responses.

**Region determination:** All API calls below require the correct `--region`. Determine region from the mount target domain (e.g. `xxx.cn-beijing.nas.aliyuncs.com` → `cn-beijing`). If any API returns 404, verify the region is correct before retrying.

```bash
# 1. Query file system information
aliyun nas describe-file-systems --file-system-id <fs-id> --region <region>

# 2. Query mount targets — MUST call separately to get VPC, status, and access group
aliyun nas describe-mount-targets --file-system-id <fs-id> --region <region>

# 3. Query permission group rules — check if ECS IP is in the allow list
aliyun nas describe-access-rules --access-group-name <access-group-name> --region <region>

# 4. Query ECS instance information — get VPC ID and private IP
aliyun ecs describe-instances --instance-ids '["<instance-id>"]' --biz-region-id <region>

# 5. Query security group rules — check if port is allowed
aliyun ecs describe-security-group-attribute --security-group-id <sg-id> --biz-region-id <region>
```

**Diagnosis logic:**
- Compare ECS VpcId with mount target VpcId for consistency. When VPCs differ, probe network connectivity on ECS via Cloud Assistant (DNS resolution, ping, port probe) to determine if connectivity has been established via CEN
- Check if permission group rules include the ECS private IP or its subnet
- Check if security group egress rules allow the target port (NFS: 2049, SMB: 445), considering security group type and default rules (see "Security Group Rule Inspection" section)

### Security Group Rule Inspection

Security groups are divided into **Normal Security Groups** and **Enterprise Security Groups**, with different default access control rules that must be distinguished during diagnosis:

#### Normal vs Enterprise Security Group Default Rules

| Security Group Type | Inbound Default Rule | Outbound Default Rule |
|--------------------|---------------------|----------------------|
| **Normal** | Only allows intranet traffic from instances within the same security group | **Allows all traffic** |
| **Enterprise** | Denies all traffic | Denies all traffic |

**Key difference:** Normal security groups **allow all outbound traffic by default**. Even without explicit outbound rules matching NFS 2049 or SMB 445 ports, traffic can still pass. Only enterprise security groups require explicit outbound rules.

#### How to Determine Security Group Type

Query the `SecurityGroupType` field via `describe-security-groups` API:
```bash
aliyun ecs describe-security-groups --security-group-id <sg-id> --biz-region-id <region>
```
- `SecurityGroupType: normal` → Normal security group
- `SecurityGroupType: enterprise` → Enterprise security group

The `InnerAccessPolicy` field from `describe-security-group-attribute` can also help:
- `InnerAccessPolicy: Accept` → Normal security group (intra-group connectivity)
- Enterprise security groups do not have this field or have a different value

#### Security Group Diagnosis Flow

1. **Determine security group type** (Normal or Enterprise)
2. **If Normal security group:**
   - Outbound allows all traffic by default, typically will not block NAS mount
   - Only need to check for explicit **Drop rules** blocking NAS-related ports
   - Only custom Drop rules matching NAS ports will cause mount failure
3. **If Enterprise security group:**
   - Outbound denies all traffic by default, explicit Allow rules are required
   - Confirm Allow rules exist for TCP egress to NAS mount target IP (NFS: 2049, SMB: 445)
   - If corresponding rules are missing, they need to be added

#### Security Group Rule Matching Strategy

When an ECS is associated with multiple security groups, rule matching order:
1. Aggregate rules from all security groups
2. Sort by priority (lower number = higher priority)
3. At the same priority, Drop rules take precedence over Accept rules
4. If no custom rule matches, use security group default rules

#### Security Group Always-Allowed Special Traffic

The following traffic is always allowed by security groups and cannot be blocked by rules:
- Alibaba Cloud network connectivity detection (on-demand Ping probes)
- ICMP PMTUD error messages (Path MTU Discovery)
- SLB load balancer forwarding traffic (controlled by SLB's security group/ACL)
- MetaServer access (100.100.100.200, instance metadata service)

### Step 5: Output Diagnosis Report

Output results using the following template:

```
# NAS Mount Failure Diagnosis Report

## Basic Information
- File System ID: xxx
- File System Type: General Purpose / Extreme
- Protocol Type: NFS / SMB
- Mount Target Address: xxx
- Mount Target Status: Active / Hibernated
- ECS Instance ID: xxx
- Operating System: xxx

## Check Results
| Check Item | Status | Details |
|-----------|--------|---------|
| Mount target status | ✅/❌ | ... |
| VPC consistency | ✅/❌ | ... |
| Permission group | ✅/❌ | ... |
| Security group type | Normal/Enterprise | ... |
| Security group port | ✅/❌ | Normal SG allows all egress by default; Enterprise SG requires explicit rules |
| Network connectivity | ✅/❌ | ... |
| Client installation | ✅/❌ | ... |
| Mount command format | ✅/❌ | ... |

## Root Cause
[Specific description of the identified issue]

## Solution
[List resolution steps in priority order]
```

## Common Error Quick Reference

When encountering the following specific error messages, the issue can be directly identified:

| Error Message | Root Cause | Solution |
|--------------|-----------|----------|
| `mount.nfs: No such device` | sunrpc module misconfiguration | Fix `tcp_slot_table_entries` in `/etc/modprobe.d/sunrpc.conf`, run `modprobe sunrpc` |
| `mount: can't find ... in /etc/fstab` | Incorrect mount command format | Use correct `sudo mount -t nfs -o ...` command |
| `mount.nfs: Operation not permitted` (NFSv4) | ECS hostname conflict | Run `echo 'install nfs /sbin/modprobe --ignore-install nfs nfs4_unique_id=\`cat /sys/class/dmi/id/product_uuid\`' >> /etc/modprobe.d/nfs.conf`, restart ECS |
| `access denied by server while mounting .../<dir>` | Subdirectory does not exist | Mount root directory first, create subdirectory, then remount |
| `file handle error` (Windows NFS) | Locking registry key missing | Create DWORD `Locking` with value 1 in registry `ClientForNFS\...\Mount` |
| Windows system error 53 | Network path unreachable | Check network connectivity, TCP/IP NetBIOS Helper service, LanmanWorkstation registry |
| Windows system error 58 | SMB protocol version incompatible | Confirm Windows version is 2008 R2 or above |
| Windows system error 64 | Permission group unauthorized | Check permission group rules, account balance, file system type |
| Windows system error 67 | Network service not started | Enable Workstation and TCP/IP NetBIOS Helper services |
| Windows system error 85 | Drive letter already in use | Use a different drive letter to remount |
| Windows system error 1231 | Microsoft network client not installed | Install and enable Microsoft network client and file/printer sharing |
| Windows system error 1272 | Guest access blocked by security policy | Set registry `AllowInsecureGuestAuth` to 1 |
| Windows system error 3227320323 | Digital signing policy conflict | Disable "Microsoft network client: Digitally sign communications (always)" policy |
| Windows system error 1312 | PowerShell mount username error | Enter correct workgroup name and username |
| Auto-mount failure on boot (CentOS 7) | remote-fs.target not enabled | `systemctl enable remote-fs.target` |
| Windows NFS network error 1222 | NFS client not installed | Install NFS client |

## Important Notes

- This skill only performs read-only diagnostic operations and does not modify any cloud resource configurations
- If diagnosis reveals configurations that need changes (security groups, permission groups, etc.), inform the user of the solution and let them perform the operation
- For issues that cannot be remotely diagnosed via API (e.g., ECS internal client installation status), guide the user to execute check commands on the ECS
- **Subdirectory mount access denied**: For both General Purpose and Extreme NAS, manually executing the `mount` command to mount a subdirectory will not auto-create it. A non-existent subdirectory will report `access denied by server while mounting`. The unified solution is: mount root directory first (General Purpose uses `:/`, Extreme uses `:/` or `:/share`), manually `mkdir` to create the subdirectory, then mount the subdirectory
- Extreme NAS path mapping: `:/` and `:/share` are equivalent, both point to root directory; `:/subdir` and `:/share/subdir` are equivalent, pointing to the same subdirectory
- **Always determine security group type before diagnosis**: Normal security groups allow all outbound traffic by default — do not misjudge ports as blocked just because there are no explicit outbound rules; Enterprise security groups deny outbound by default and require explicit Allow rules
