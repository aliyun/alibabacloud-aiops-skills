# Unable to log on to the instance through VNC

## Determine whether this is a GuestOS issue

1. **If the VNC page cannot be opened**
   - Use `DescribeInstances` to obtain the instance type and confirm whether VNC is supported.
     - Refer to [Instance family overview](https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families)
     - GPU instance types do not support VNC.
     - TDX instance types do not support VNC.
2. **If the issue is dual pointers in the VNC desktop environment**
   - Handle it according to [Issues when remotely connecting to an instance through VNC - Alibaba Cloud Help Center](https://help.aliyun.com/zh/ecs/support/through-vnc-or-workbench-instance-remote-connection-problems).

## Troubleshooting process inside GuestOS

### Related components

- tty and getty
- PAM
- Shell and dependent libraries

### Problem diagnosis

1. **Ask the user whether they can log on through a channel other than VNC (such as SSH, excluding Cloud Assistant).**
   - Yes: this is mostly a tty issue. Log on through SSH and then follow [guestos-tty-getty](utils/guestos-tty-getty.md).
   - No: continue.
2. **Ask the user whether they can log on through Cloud Assistant Session Manager** (use `DescribeCloudAssistantStatus` first to confirm that the Cloud Assistant Agent is online).
   - Yes: this is mostly a PAM issue. Follow [guestos-pam](utils/guestos-pam.md).
   - No: continue.
3. **Can Cloud Assistant execute the `ls` command inside GuestOS?**
   - Yes: this is mostly a tty/pty feature issue.
   - No: this is mostly Shell damage. First prepare the offline troubleshooting environment according to [guestos-pe-prep](utils/guestos-pe-prep.md), and then troubleshoot in the chroot environment according to [guestos-shell](utils/guestos-shell.md).
