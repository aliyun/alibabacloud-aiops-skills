# Common Diagnostic Scenarios

This document lists common diagnostic scenarios and expected outputs for the ecs-reboot-or-crash skill.

---

## Linux Scenarios

### Scenario 1: System Maintenance Reboot

```
Diagnosis Result:
- Found event: SystemMaintenance.Reboot
- Event time: 2025-03-20 10:00:00
- Reason: Planned system maintenance

Conclusion: Instance reboot was caused by Alibaba Cloud platform maintenance, which is normal ops activity.
```

---

### Scenario 2: Kernel Panic + vmcore Available

```
Diagnosis Result:
- No maintenance events found
- Cloud Assistant found: "Kernel panic - not syncing" record in dmesg
- Kdump service status: active
- Found vmcore: /var/crash/127.0.0.1-2025-03-20-10:30:00/vmcore (2.5G)
- vmcore time: 2025-03-20 10:30:00

vmcore-dmesg.txt analysis:
- Panic reason: Kernel panic - not syncing: Fatal exception in interrupt
- Crash location: RIP: 0010:nvme_queue_rq+0x1a2/0x4d0 [nvme]
- Involved module: nvme driver
- Call stack: nvme_queue_rq -> blk_mq_dispatch_rq_list -> ...

Conclusion: Instance rebooted due to NVMe driver abnormality causing kernel crash, vmcore dump file generated.
Suggestion: Check NVMe driver version, upgrade driver or kernel if needed. Use crash tool for deeper vmcore analysis.
```

---

### Scenario 3: Kernel Panic + No vmcore

```
Diagnosis Result:
- No maintenance events found
- Cloud Assistant found: "Kernel panic" record in dmesg
- Kdump service status: inactive
- Found vmcore: No

Conclusion: Instance rebooted due to kernel crash, but kdump not configured or not working, unable to capture vmcore.
Suggestion: Configure kdump service to capture vmcore on next crash for root cause analysis.
```

---

### Scenario 4: OOM with panic_on_oom Enabled

```
Diagnosis Result:
- No maintenance events found
- Cloud Assistant found: "Out of memory: Kill process" record in /var/log/messages
- vm.panic_on_oom: 1 (OOM triggers kernel panic)
- Kdump service status: active
- Found vmcore: Yes

Conclusion: OOM event triggered kernel panic because vm.panic_on_oom=1, causing system reboot.
Suggestions:
1. Disable panic_on_oom: sysctl -w vm.panic_on_oom=0 (add to /etc/sysctl.conf for persistence)
2. Optimize application memory usage or upgrade instance type
3. Review OOM killed processes to identify memory-hungry applications
```

---

### Scenario 5: OOM Killer Only

```
Diagnosis Result:
- No maintenance events found
- Cloud Assistant found: "Out of memory: Kill process" record in /var/log/messages
- vm.panic_on_oom: 0 (OOM only kills process, no panic)
- No kernel panic records found

Conclusion: Instance triggered OOM Killer due to insufficient memory, some processes were terminated but system continued running.
Suggestion: Optimize application memory usage, or upgrade instance type.
```

---

## Windows Scenarios

### Scenario 6: BSOD with Memory Dump

```
Diagnosis Result:
- No maintenance events found
- Unexpected shutdown event: Event ID 41 (Kernel-Power)
- BSOD events found in WER logs
- Memory dump configuration: Automatic memory dump (CrashDumpEnabled=7)
- Memory dump file found: C:\Windows\MEMORY.DMP (4.2 GB)
- Dump time: 2025-03-20 10:30:00

Conclusion: Windows BSOD crash occurred, memory dump captured.
Suggestion: Download MEMORY.DMP and analyze with WinDbg:
1. Install Windows Debugging Tools
2. Open dump file in WinDbg
3. Run: !analyze -v
```

---

### Scenario 7: BSOD without Dump (Not Configured)

```
Diagnosis Result:
- No maintenance events found
- Unexpected shutdown event: Event ID 41 (Kernel-Power)
- BSOD events found in WER logs
- Memory dump configuration: None (CrashDumpEnabled=0)
- Memory dump file: Not found

Conclusion: Windows BSOD crash occurred but memory dump was not configured.
Suggestions:
1. Enable memory dump: System Properties > Advanced > Startup and Recovery > Settings
2. Select "Automatic memory dump" or "Kernel memory dump"
3. Ensure pagefile is configured and has sufficient space
```

---

### Scenario 8: BSOD without Dump (Pagefile Issue)

```
Diagnosis Result:
- No maintenance events found
- Unexpected shutdown event: Event ID 41 (Kernel-Power)
- Memory dump configuration: Automatic memory dump (CrashDumpEnabled=7)
- Pagefile: Not configured
- Memory dump file: Not found

Conclusion: Windows BSOD crash occurred but memory dump was not captured because pagefile is not configured.
Suggestions:
1. Configure pagefile: System Properties > Advanced > Performance > Settings > Advanced > Virtual memory
2. Set pagefile size to at least RAM size + 1MB
3. Reboot for pagefile changes to take effect
```

---

### Scenario 9: Minidump Available

```
Diagnosis Result:
- No maintenance events found
- Unexpected shutdown event: Event ID 41 (Kernel-Power)
- Memory dump configuration: Small memory dump (CrashDumpEnabled=3)
- Minidump files found in C:\Windows\Minidump:
  - 032025-12345-01.dmp (128 KB, 2025-03-20 10:30:00)

Conclusion: Windows crash occurred, minidump captured.
Suggestion: Analyze minidump with WinDbg Preview (Microsoft Store) or BlueScreenView tool.
```

---

### Scenario 10: Application Crash Causing Instability

```
Diagnosis Result:
- No maintenance events found
- No unexpected shutdown events
- Application crash events found: Multiple crashes of {application_name}.exe
- No system crash dump files

Conclusion: Application crashes detected but no system-level crash. System remained running.
Suggestions:
1. Check application logs for crash details
2. Verify application compatibility with Windows version
3. Check for application updates or known issues
```
