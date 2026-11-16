# Staged restart guidance

The sequence, the timings and the risk wording follow the Alibaba Cloud documents on
restarting an ECS instance and on troubleshooting abnormal start or stop behaviour:
https://help.aliyun.com/zh/ecs/user-guide/restart-instances
https://help.aliyun.com/zh/ecs/support/examples-of-start-or-stop-abnormal-common-problems

This skill only guides a restart. It never executes one: no `kill`, no `pkill`, no
`systemctl restart`, and no call of the ECS reboot operation.

## Order: lightest action first

1. **Recover the single abnormal process.** Restart only the offending service through
   whatever the customer's own supervisor uses. This is the preferred step because it
   leaves the rest of the instance and any buffered data untouched.
2. **Reboot the instance normally**, from the console or by the customer's own
   automation. Expect roughly 3 to 5 minutes; the documented worst case is about 20
   minutes.
3. **Force a reboot only as the last resort.** It is equivalent to pulling the power:
   the file system can be left inconsistent and unwritten data can be lost. Use it only
   when the instance answers nothing at all, including the VNC session.

## Before a normal reboot

- Choose a low-traffic window.
- Stop the application first, so business data is not written mid-flight.
- Take a snapshot of the important disks if the data matters; the snapshot itself is a
  separate decision the customer makes.
- Note this documented difference: when a change to the instance requires a reboot to
  take effect (underlying maintenance, a spec change), only the console or API reboot
  applies it. A reboot issued inside the guest operating system does not.

## If the instance stays in a transitional state

When an instance remains stuck while starting or stopping, guide the customer to the
official troubleshooting page and to two console artifacts that do not need a login:
the instance screen capture and a VNC session. Both show what the boot process is
waiting on, which is the usual reason a memory-starved instance does not come back.

## After any reboot

Process information in memory is gone, so the incident cannot be reconstructed unless a
recorder was already running. The skill therefore pairs every restart with the atop
deployment advice in [atop.md](atop.md), including enabling its service so that it
starts again after the next reboot.