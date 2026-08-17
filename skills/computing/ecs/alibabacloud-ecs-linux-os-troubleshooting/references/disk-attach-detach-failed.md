# Adding or Removing a Cloud Disk Does Not Take Effect

## Confirm Whether It Is a GuestOS Issue

1. **Use `DescribeDisks` to confirm the status of the attached disk, and confirm whether the corresponding device path can be seen inside GuestOS.**
   - Cannot be seen: first troubleshoot "unable to see the newly added cloud disk".
   - Can be seen: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- kconfig configuration
- udev

### Issue Localization

1. Troubleshoot hotplug and disk device recognition according to [guestos-hotplug-disk](utils/guestos-hotplug-disk.md).
