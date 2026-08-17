# The SSH key pair being configured does not take effect

## Determine whether this is a GuestOS issue

- This domain has no prerequisite boundary determination. Go directly to troubleshooting inside GuestOS.

## Troubleshooting process inside GuestOS

### Related components

- cloud-init
- fw_cfg
- Shell and its dependencies
- ssh configuration, permissions, and attributes

### Problem diagnosis

1. Troubleshoot cloud-init according to [guestos-cloud-init](utils/guestos-cloud-init.md). If no issue is found, continue.
2. Can Cloud Assistant execute the `ls` command?
   - No: first mount PE according to [guestos-pe-prep](utils/guestos-pe-prep.md), and then troubleshoot according to [guestos-shell](utils/guestos-shell.md).
   - Yes: continue troubleshooting.
