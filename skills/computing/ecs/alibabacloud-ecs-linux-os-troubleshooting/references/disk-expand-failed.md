# Unable to Online Resize a Cloud Disk, Disk Partition, or File System

## Confirm Whether It Is a GuestOS Issue

1. **Use `DescribeCloudAssistantStatus` to check the Cloud Assistant status and confirm that GuestOS has started normally.**
   - Otherwise, first troubleshoot according to [guestos-not-running](guestos-not-running.md).
   - Yes: continue.
2. **Use `DescribeDisks` to confirm whether cloud disk expansion succeeded.**
   - Expansion did not succeed: submit a support ticket.
   - Expansion succeeded: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- virtio_blk / nvme_core driver
- growpart
- resize2fs / xfs_growfs, etc.

### Issue Localization

For partition and file system troubleshooting, refer to [guestos-disk-fs](utils/guestos-disk-fs.md).

1. Does GuestOS recognize the entire cloud disk as the new size?
   - Cannot, and kernel ≤ 3.6: online resizing is not supported and a reboot is required.
   - Cannot, and kernel > 3.6: submit a support ticket.
   - Can: continue.
2. Partition expansion may have failed. Recommend that the user manually run `growpart` to try partition expansion.
3. File system expansion may have failed. Recommend that the user manually run `resize2fs` or `xfs_growfs` to try file system expansion.
