# Unable to remotely log on to the instance through SSH

## Determine whether this is a GuestOS issue

1. **Use `DescribeCloudAssistantStatus` to view the Cloud Assistant status and confirm whether GuestOS has started normally.**
   - No: troubleshoot according to [guestos-not-running](guestos-not-running.md) first.
   - Yes: continue.
2. **Use `DescribeSecurityGroups` to confirm whether the security group allows inbound SSH.**
   - No: configure the rule first.
   - Yes: continue.

## Troubleshooting process inside GuestOS

### Related components

- NIC IP and routes
- Firewall
- sshd and its configuration
- PAM
- Shell and dependent libraries

### Problem diagnosis

1. **Does the `ssh` logon error match a [known issue](https://help.aliyun.com/zh/ecs/support/troubleshooting-guidelines-when-you-cannot-remotely-log-on-to-a-linux-instance-through-ssh#0b2ba7509557s)?**
   - Yes: follow that document.
   - No: continue.
2. **Can Cloud Assistant Session Manager log on to GuestOS?**
   - Yes: this is mostly a PAM issue. Follow [guestos-pam](utils/guestos-pam.md).
   - No: continue.
3. **Can Cloud Assistant execute commands inside GuestOS?**
   - Cannot execute or reports the `SystemDefaultShellNotFound` error: this is mostly a Shell issue. First enter the chroot environment according to [guestos-pe-prep](utils/guestos-pe-prep.md), and then troubleshoot according to [guestos-shell](utils/guestos-shell.md).
   - Can execute: troubleshoot according to [guestos-shell](utils/guestos-shell.md).
4. **Does the sshd user exist?**
   - Run `getent passwd sshd` and `grep -E "^sshd:" /etc/passwd /etc/group /etc/shadow`, then compare the results:
     - `getent` finds the sshd user: this is normal. Continue with the subsequent investigation.
     - `getent` does not find it, but sshd entries exist in `/etc/passwd`, `/etc/group`, and `/etc/shadow`: this indicates that an incorrect `/etc/nsswitch.conf` configuration breaks NSS resolution. Run `grep -E "^(passwd|group|shadow):" /etc/nsswitch.conf` to check the data source configuration of the `passwd`, `group`, and `shadow` lines. If a fix is required and the nscd service exists, remember to clear the cache with `nscd`.
     - Neither finds it: the sshd user is missing and must be recreated (`useradd -r -s /usr/sbin/nologin -d /run/sshd sshd`).
