# Output Format Requirements

After diagnosis is complete, output results according to the following structure.

## Table of Contents

1. [Linux Diagnosis Result](#linux-diagnosis-result)
2. [Windows Diagnosis Result](#windows-diagnosis-result)

---

## Linux Diagnosis Result

```markdown
## Diagnostic Progress

### Step 1: Confirm Instance Information
> First need to confirm instance basic info and region.

- Instance ID: {instance_id}
- Region: {region_id}
- OS Type: Linux
- Current Status: {status}

### Step 2: Check Maintenance Events
> Check if platform maintenance events caused reboot.

**Findings:**
- {event_query_result}

### Step 3A: Linux System Diagnosis (if needed)
> No maintenance events found, checking internal restart or panic records.

**Cloud Assistant Status Check:**
- Cloud Assistant Running: {yes/no}
- If no: {explain why cannot proceed and provide alternative approaches}

**Findings:**
- {cloud_assistant_execution_result}

**Kdump Configuration Status:**
- Service Status: {active/inactive/active (kdump-tools)}
- Service Type: {kdump (RHEL/CentOS) / kdump-tools (Ubuntu/Debian)}
- Crash Dump Path: {configured_path}

**OOM Panic Configuration:**
- vm.panic_on_oom: {0/1}
- Impact: {OOM kills process only / OOM triggers kernel panic and reboot}

**Crash Dump File Check:**
- Found crash dumps: {yes/no}
- Dump type: {vmcore (RHEL) / dump.*+dmesg.* (Ubuntu)}
- Latest dump: {file_path, size, time}
- Panic reason (from dmesg): {panic_message_if_available}

**Alternative Diagnostic Approaches (if Cloud Assistant not available):**
```bash
# Provide these commands to user for manual execution via SSH
ssh root@{instance_public_ip}

# Check reboot history
last reboot

# Check system logs
grep -i "reboot\|shutdown\|panic\|oom" /var/log/syslog | tail -50

# Check dmesg for errors
dmesg | grep -i "panic\|oom\|error" | tail -20

# Check kdump
systemctl status kdump
ls -lh /var/crash/
```

### Step 4A: vmcore-dmesg.txt Analysis (if vmcore found)
> Found vmcore file, reading vmcore-dmesg.txt for preliminary analysis.

**Panic Reason:**
- {panic_specific_reason}

**Crash Location:**
- RIP: {function_and_address_at_crash}
- Involved Modules: {related_kernel_modules}

**Call Stack:**
```
{key_call_stack_fragment}
```

### Step 5: Kdump Configuration Recommendation (if no vmcore and kdump not configured)
> Kernel panic detected but no crash dump file found. Kdump is not properly configured.

**Current Kdump Status:**
- Service Status: {kdump_service_status}
- crashkernel Parameter: {present/absent in /proc/cmdline}
- Config File Exists: {yes/no}

**Why Kdump is Needed:**
Without Kdump configured, kernel crashes will not generate vmcore files, making root cause analysis impossible for future occurrences.

**Configuration Steps for {OS_Type}:**

{configuration_steps_based_on_os}

---

## Diagnostic Conclusion

- **Root Cause Analysis**: {root_cause}
- **Impact Scope**: {impact_scope}

---

## Recommendations

1. {recommendation_1}
2. {recommendation_2}
```

---

## Windows Diagnosis Result

```markdown
## Diagnostic Progress

### Step 1: Confirm Instance Information
> First need to confirm instance basic info and region.

- Instance ID: {instance_id}
- Region: {region_id}
- OS Type: Windows
- Current Status: {status}

### Step 2: Check Maintenance Events
> Check if platform maintenance events caused reboot.

**Findings:**
- {event_query_result}

### Step 3B: Windows System Diagnosis (if needed)
> No maintenance events found, checking Windows crash dump and event logs.

**System Uptime:**
- Last Boot Time: {last_boot_time}
- Uptime: {days} days, {hours} hours

**Unexpected Shutdown Events:**
- {shutdown_event_summary}

**Memory Dump Configuration:**
- CrashDumpEnabled: {0/1/2/3/7}
- Dump Type: {None/Complete/Kernel/Small/Automatic}
- Dump File Path: {dump_file_path}
- Pagefile: {configured/not configured}

**Memory Dump File Check:**
- Memory dump file: {found/not found}
- File size: {size}
- Last modified: {timestamp}

**Minidump Files:**
- Count: {count}
- Latest: {filename, timestamp}

**BSOD Events:**
- {bsod_event_summary}

---

## Diagnostic Conclusion

- **Root Cause Analysis**: {root_cause}
- **Impact Scope**: {impact_scope}

---

## Recommendations

1. {recommendation_1}
2. {recommendation_2}
```
