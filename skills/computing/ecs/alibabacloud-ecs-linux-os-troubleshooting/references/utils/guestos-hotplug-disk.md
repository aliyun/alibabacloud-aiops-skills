
# Hotplug and Disk Device Recognition Troubleshooting

Troubleshooting steps for disk hotplug kernel support and device recognition after online attachment inside GuestOS.

## Hotplug Kernel Parameters

1. Run `cat /boot/$(uname -r)` or a similar command to check whether `CONFIG_HOTPLUG_PCI_PCIE`, `CONFIG_HOTPLUG_PCI`, and `CONFIG_HOTPLUG_PCI_ACPI` are all set to `y`.
   - All set to y indicates support.
   - `is not set` requires rebuilding the kernel.
   - `m` requires loading the corresponding module.

## Disk Device Recognition

1. Query the serial number (SN) of the newly added disk through `DescribeDisks` (the xxx part of d-xxx). Refer to [Query the serial number of a cloud disk](https://help.aliyun.com/zh/ecs/user-guide/query-the-serial-number-of-a-disk).
2. Run `ls -l /dev/disk/by-id` to check whether the corresponding `virtio-{SN}` exists. If it does not exist, this is an underlying virtualization issue. If it exists, the disk has been recognized successfully.
3. Run `fdisk -l` to confirm whether the disk is unformatted or unpartitioned. A newly added disk is a raw disk and must be partitioned and formatted before use. References: [Attach a data disk](https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk), [Detach and reattach a data disk](https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk)
