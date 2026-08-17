# Abnormal Clock Drift

## Confirm Whether It Is a GuestOS Issue

1. There is no prerequisite boundary judgment. Enter GuestOS-internal investigation directly.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- NTP/chrony service
- Time zone configuration

### Issue Localization

1. Use `DescribeImages` to check the image `standardizedTimeZone` tag and verify whether it is consistent with the behavior of the third line in `/etc/adjtime` inside the instance.
   - Inconsistent: recommend modifying `/etc/adjtime` so that it matches the tag behavior.
   - Consistent: continue to the next step.
2. Run `timedatectl status` to check whether the system time configuration meets expectations.
   - Does not meet expectations: troubleshoot according to [guestos-time](utils/guestos-time.md).
   - Meets expectations: continue to the next step.
3. Check whether the RTC time meets expectations.
   - Does not meet expectations: if the user has manually changed the time or time zone, recommend that the user run `hwclock -w` or reboot the instance to refresh RTC.
   - Meets expectations: continue to the next step.
4. Check whether an abnormal process is changing the time.

If the auditd service is running: use audit to trace the `clock_adjtime` and `clock_settime` system calls and check whether an abnormal process is changing the time.

```bash
auditctl -a always,exit -F arch=b64 -S adjtimex -S settimeofday -S clock_settime -S clock_adjtime -k time-change
auditctl -a always,exit -F arch=b32 -S adjtimex -S settimeofday -S clock_settime -S clock_adjtime -k time-change
```

If the auditd service is not running: use the [tracepoint tool](utils/tracepoint-perf-tools.md) to inspect the `syscalls:sys_enter_clock_adjtime` and `syscalls:sys_enter_clock_settime` system call hooks and check whether an abnormal process is changing the time.

   - Found: provide the conclusion and remediation recommendations.
   - Not found: continue to the next step.
5. If the time shown by `dmesg -T` differs significantly from the time shown by `journalctl`, run `cat /sys/devices/system/clocksource/clocksource0/current_clocksource` to check whether the current clocksource is `kvm-clock`.
   - Yes: this may be a long-standing virtualization issue in which the time in the register advances slowly. Recommend adding the `clocksource=tsc` kernel command-line parameter to set `current_clocksource` to `tsc`.
   - No: continue investigating other possible causes.
