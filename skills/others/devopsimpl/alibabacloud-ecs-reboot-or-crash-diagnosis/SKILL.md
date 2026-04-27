---
name: alibabacloud-ecs-reboot-or-crash-diagnosis
description: Diagnose ECS instance reboot or crash issues. First checks for abnormal maintenance events, then uses Cloud Assistant to check for internal restarts or kernel panics. Use this skill when users report ECS instance unexpected reboot, crash, abnormal shutdown, kernel panic, or OOM. Supports vmcore file analysis, kdump configuration, system log analysis, and Windows crash dump analysis.
metadata:
  pattern: pipeline
  steps: "5"
  required_params: "instance_id, region_id"
  domain: aiops
  owner: ecs-team
  contact: ecs-agent@alibaba-inc.com
  ai-mode: disabled
---

# ECS Instance Reboot/Crash Diagnosis

Diagnose root cause of ECS instance unexpected reboot or crash. Uses standard workflow: check platform maintenance events first, then check internal system logs. Supports both Linux and Windows systems.

## Required Parameters

Before starting diagnosis, **must** obtain the following parameters from user:

| Parameter | Description | Example |
|------|------|------|
| `INSTANCE_ID` | ECS instance ID | `i-bp1a2b3c4d5e6f7g8h9j` |
| `REGION_ID` | Region ID | `cn-hangzhou` |

**If user does not provide any of the above parameters, must ask user first. Do not start diagnosis.**

## Mandatory Execution Rules

1. **Must obtain parameters first** — Instance ID and Region ID are required. Must ask user if missing.
2. **Standard workflow cannot be skipped** — Must execute in order: Maintenance Event Check → OSType Detection → System Log Check
3. **Must check Cloud Assistant status before diagnostics** — Before executing Step 3A/3B, must verify Cloud Assistant is running via `DescribeCloudAssistantStatus`. If not running, provide alternative diagnostic approaches.
4. **All diagnostic conclusions must be based on actual data** — No fabrication, speculation, or assumptions
5. **Output format must be strictly followed** — After diagnosis, **must read the complete template in `references/output-format.md`**, output strictly according to template structure. No free-form output, no omitted sections, no changed hierarchy. Every placeholder `{...}` in the template must be filled with actual data.

---

## Prerequisites

### CLI Tools
- **aliyun-cli 3.3.3+** (required) — For calling Alibaba Cloud API
- Installation & configuration: see [CLI Installation Guide](../../cli-installation-guide.md)

### AI-Mode Configuration (Required)
Before using aliyun CLI commands, must configure AI-Mode:

```bash
# Enable AI-Mode
aliyun configure ai-mode enable

# Set user-agent for skill identification
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-reboot-or-crash-diagnosis"

# Update plugins
aliyun plugin update
```

**After diagnosis complete, disable AI-Mode:**
```bash
aliyun configure ai-mode disable
```

### Alibaba Cloud Credentials
Credentials must be pre-configured **outside of agent session**. Agent only verifies:
```bash
aliyun configure list
```

### Instance Requirements
- **Cloud Assistant client must be installed and running** on the instance
  - Alibaba Cloud Linux: Pre-installed by default
  - Ubuntu/CentOS/Other: May require manual installation, check with `DescribeCloudAssistantStatus` API
  - Installation guide: https://help.aliyun.com/document_detail/64930.html
- Instance status must be Running
- **Note:** If Cloud Assistant is not running, diagnostic commands cannot be executed remotely. Must provide manual diagnostic steps to user.

---

## Required RAM Permissions

See **[RAM Policies](references/ram-policies.md)** for the complete permission list and custom policy example.

---

## Step 1: Confirm Instance Information (Cannot Skip)

**Verify instance exists and get basic information:**

```bash
aliyun ecs describe-instances \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-ids '["<INSTANCE_ID>"]'
```

Confirm from returned JSON:
- `RegionId` — Region ID (matches user provided)
- `Status` — Instance status (Running/Stopped)
- `InstanceName` — Instance name
- `OSType` — Operating system type (**windows / linux**)

**Record OSType for Step 3 branch selection.**

---

## Step 2: Check ECS Maintenance Events

**Query instance historical system events to determine if platform maintenance caused reboot:**

```bash
aliyun ecs describe-instance-history-events \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID> \
  --event-cycle-status Executed
```

**Event Analysis:**

| Event Type | Meaning | Determination | Next Step |
|---|---|---|---|
| `SystemMaintenance.Reboot` | Reboot caused by system maintenance | Platform-initiated maintenance | Inform user, no further investigation needed |
| `SystemFailure.Reboot` | Reboot caused by underlying hardware/system failure | Platform infrastructure failure | Suggest instance migration or contact support |
| `InstanceFailure.Reboot` | Reboot caused by instance-level failure | **Instance internal issue detected by platform** | **Must continue to Step 3 for system log check** |
| `InstanceExpiration.Stop` | Instance stopped due to expiration | Billing issue | Need renewal, no further investigation |
| No relevant events | No platform maintenance events found | Not platform-initiated | Continue to Step 3 |

**Important Notes for InstanceFailure.Reboot:**
- This event indicates the platform detected an instance-level anomaly and triggered automatic recovery
- Common causes: kernel panic, OOM, system hang, critical process failure
- **Must execute Step 3** to check system logs for root cause
- Even if no obvious errors in logs, the instance may have been unresponsive at kernel level

**If maintenance event found:**
- Clearly inform user of reboot cause (event type, time, reason)
- Provide handling suggestions
- End diagnosis flow

**If no maintenance event found:**
- Continue to Step 3, check internal system logs based on OSType

---

## Step 3A: Linux System Diagnosis (Execute when OSType is linux)

### Step 3A.1: Check Cloud Assistant Status (Mandatory)

**Before executing diagnostic commands, verify Cloud Assistant is running:**

```bash
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID>
```

**Check the response:**
```json
{
  "InstanceCloudAssistantStatusSet": {
    "InstanceCloudAssistantStatus": [
      {
        "InstanceId": "i-xxx",
        "RegionId": "cn-xxx",
        "CloudAssistantStatus": "true",
        "LastHeartbeatTime": "2026-04-09T07:26:58Z"
      }
    ]
  }
}
```

**Important Notes:**
- `CloudAssistantStatus` is a **string** ("true"/"false"), not boolean
- Check `LastHeartbeatTime` to ensure it's recent (within last few minutes)
- Even if status is "true", RunCommand may still fail if service is unstable
- **Always check RunCommand execution result** and handle failures gracefully
- **Ubuntu vs RHEL differences:**
  - RHEL/CentOS/Alibaba Cloud Linux: Service name is `kdump`, crash files named `vmcore-*`
  - Ubuntu/Debian: Service name is `kdump-tools`, crash files named `dump.*` and `dmesg.*`
  - Diagnostic script now checks both service names and all crash file types

**If CloudAssistantStatus is false or command fails:**
- Cloud Assistant is not installed or not running on the instance
- **Cannot proceed with remote diagnostic commands**
- **Alternative approaches:**
  1. Guide user to SSH into the instance and check logs manually
  2. Provide manual diagnostic commands for user to execute
  3. Suggest installing Cloud Assistant: [Installation Guide](https://help.aliyun.com/document_detail/64930.html)
  4. Check instance monitoring data via CloudMonitor API

**If CloudAssistantStatus is true:**
- Proceed to Step 3A.2

### Step 3A.2: Execute Linux Diagnostic Script

Execute Linux diagnostic script via Cloud Assistant to check:
- System reboot records (`last reboot`, `/var/log/messages` or `/var/log/syslog`)
- Kernel Panic records (`dmesg`)
- OOM records and `vm.panic_on_oom` configuration
- Kdump configuration and crash dump file status
- **Crash dump files**: vmcore (RHEL/CentOS) or dump.*/dmesg.* (Ubuntu/Debian)

**Complete diagnostic commands: see [diagnostic-commands.md](references/diagnostic-commands.md#linux-system-diagnosis)**

**Linux Result Analysis:**

| Finding | Possible Cause | Suggestion |
|---|---|---|
| Kernel Panic + crash dump (vmcore/dump.*) | Kernel crash, dump file generated | Read dmesg.* file for panic reason, contact Alibaba Cloud technical support for deep analysis |
| Kernel Panic + no crash dump | Kernel crash, but kdump not configured or not working | **Proceed to Step 5**: Recommend Kdump configuration for future crash capture |
| OOM + panic_on_oom=1 | OOM triggered kernel panic | Disable panic_on_oom or increase memory |
| OOM Killer | Memory insufficient causing process killed | Optimize memory usage or upgrade instance type |
| SysRq triggered crash | Manual crash trigger via `/proc/sysrq-trigger` | Check if intentional test, review bash history and audit logs |
| Normal reboot records | User or program triggered reboot | Check cron jobs or ops scripts |
| No abnormal records | No system-level issues found | May be external factors, suggest monitoring |

---

## Step 3B: Windows System Diagnosis (Execute when OSType is windows)

### Step 3B.1: Check Cloud Assistant Status (Mandatory)

**Before executing diagnostic commands, verify Cloud Assistant is running:**

```bash
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID>
```

**Check the response:**
- `CloudAssistantStatus: true` — Cloud Assistant is running, proceed to Step 3B.2
- `CloudAssistantStatus: false` — Cloud Assistant is not running
  - **Cannot proceed with remote diagnostic commands**
  - Guide user to SSH/RDP into instance and run diagnostics manually
  - Suggest reinstalling Cloud Assistant: [Windows Installation Guide](https://help.aliyun.com/document_detail/64930.html)

### Step 3B.2: Execute Windows Diagnostic Script

Execute Windows diagnostic script via Cloud Assistant to check:
- System uptime and unexpected shutdown events (Event ID 41, 1074, 6008, 6006)
- Memory dump configuration and pagefile settings
- MEMORY.DMP and minidump files existence
- BSOD events and application crashes

**Complete diagnostic commands: see [diagnostic-commands.md](references/diagnostic-commands.md#windows-system-diagnosis)**

**Windows Result Analysis:**

| Finding | Possible Cause | Suggestion |
|---|---|---|
| Event 41 (Kernel-Power) | Unexpected shutdown/crash | Check for BSOD, dump files |
| Dump configured + dump file exists | System crashed and captured dump | Contact Alibaba Cloud technical support for dump file analysis |
| Dump configured + no dump file | Crash occurred but no dump captured | Check pagefile and disk space |
| Dump not configured | Crash dumps disabled | Enable memory dump for diagnosis |
| BSOD events found | Blue screen crash occurred | Check bug check code in dump |
| No abnormal events | No system-level crash records | May be power issue or external factor |

---

## Step 3.5: Get Cloud Assistant Command Output (Required after Step 3)

After executing diagnostic script via `RunCommand`, query the execution result:

```bash
aliyun ecs describe-invocations \
  --biz-region-id <REGION_ID> \
  --region <REGION_ID> \
  --instance-id <INSTANCE_ID> \
  --invoke-id <INVOKE_ID>
```

**Important Notes:**
- Use `--instance-id` (not `--instance-id.1`) for describe-invocations API
- The `InvokeId` is returned by the `RunCommand` API call
- Decode the `Output` field from Base64 to get diagnostic results
- Check `InvokeStatus` to ensure command execution completed successfully

---

## Step 4: Analyze Crash Dump Files

If Step 3 found crash dump files (vmcore on Linux, MEMORY.DMP/minidump on Windows), perform preliminary analysis.

**Complete analysis commands: see [diagnostic-commands.md](references/diagnostic-commands.md#crash-dump-analysis)**

> **Important:** If Linux vmcore files need deep analysis or Windows dump files (MEMORY.DMP/minidump) are found, recommend the user contact Alibaba Cloud technical support team for professional crash dump analysis assistance.

---

## Step 5: Recommend Kdump Configuration (If Not Configured)

**If Step 3A found Kernel Panic records but no vmcore files, must advise user to configure Kdump.**

### When to Recommend Kdump Configuration

- Kernel panic records found in dmesg or system logs, but `/var/crash` has no vmcore files
- Kdump service status shows `inactive` or `failed`
- `/proc/cmdline` does not contain `crashkernel=` parameter

### Key Points to Communicate

1. **Why Kdump is needed**: Without Kdump, kernel crashes will not generate vmcore files, making root cause analysis impossible.

2. **Configuration requirements**:
   - Reserve memory for crash kernel via `crashkernel=` kernel parameter
   - Enable and start the kdump (RHEL/CentOS) or kdump-tools (Ubuntu/Debian) service
   - Ensure sufficient disk space in `/var/crash` (or configured path)

3. **Configuration reference**: Provide guidance from [diagnostic-commands.md](references/diagnostic-commands.md#kdump-配置建议)

### Kdump Configuration Steps Summary

**RHEL/CentOS/Alibaba Cloud Linux:**
1. Install: `yum install -y kexec-tools`
2. Add `crashkernel=auto` to kernel parameters in `/etc/default/grub`
3. Run `grub2-mkconfig -o /boot/grub2/grub.cfg`
4. Reboot the instance
5. Enable: `systemctl enable --now kdump`

**Ubuntu/Debian:**
1. Install: `apt-get install -y kdump-tools`
2. Set `USE_KDUMP=1` in `/etc/default/kdump-tools`
3. Run `update-grub` (crashkernel parameter usually auto-added)
4. Reboot the instance
5. Verify: `systemctl status kdump-tools`

### Windows Memory Dump Configuration

If Step 3B found BSOD events but no dump files:
1. Verify pagefile is configured and has sufficient size
2. Enable memory dump: System Properties → Advanced → Startup and Recovery → Settings
3. Select "Automatic memory dump" or "Kernel memory dump"
4. Ensure `CrashDumpEnabled` registry value is not 0

---

## Final Output (Must execute after diagnosis complete)

**After all diagnostic steps complete, must do both of the following:**

1. **Read `references/output-format.md`** — Get complete output format template
2. **Output strictly according to template structure** — Choose corresponding template based on actual result

---

## References

- **[Output Format](references/output-format.md)** — Diagnostic result output template
- **[Common Scenarios](references/scenarios.md)** — Typical problem diagnosis examples
- **[Diagnostic Commands](references/diagnostic-commands.md)** — Complete diagnostic scripts and analysis commands
