# Unable to reset a user's password in the system

There are several ways to reset a system user's password:
1. After logging on to the instance, use the chpasswd/passwd command to change the password.
2. Change the instance logon password through Cloud Assistant.
3. In the ECS console, **reset the password online**.
4. Through the ECS console or the ModifyInstanceAttribute API, **reset the password offline**.

## Determine whether this is a GuestOS issue

1. For methods 2 and 3, confirm that Cloud Assistant can execute other commands. Otherwise, this is an issue with Cloud Assistant itself.

## Troubleshooting process inside GuestOS

### Related components

- Shell and dependencies
- Permissions and attributes of `/etc/passwd` and `/etc/shadow`
- chpasswd/passwd tools

For method 4, the following may also be involved:

- ISO stage
- cloud-init
- fw_cfg

### Problem diagnosis

1. Can you log on to the shell and execute simple commands?
   - No: first prepare the offline troubleshooting environment by following [guestos-pe-prep](utils/guestos-pe-prep.md), and then troubleshoot in the chroot environment according to [guestos-shell](utils/guestos-shell.md).
   - Yes: continue.
2. Can you manually change the password with chpasswd/passwd?
   - No: in most cases, the command or its dependencies are damaged. First prepare the offline troubleshooting environment by following [guestos-pe-prep](utils/guestos-pe-prep.md), and then troubleshoot in the chroot environment according to [guestos-shell](utils/guestos-shell.md).
   - Yes: submit a ticket.
3. **For method 4 only, troubleshoot by following these steps:**
   - Troubleshoot according to [guestos-cloud-init](utils/guestos-cloud-init.md).
     - Issue found: provide the conclusion and repair suggestions.
     - No issue found: submit a ticket.
