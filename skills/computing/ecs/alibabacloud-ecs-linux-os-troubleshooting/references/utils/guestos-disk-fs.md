
# Disk Partition and File System Troubleshooting

Troubleshooting steps for disk partition tables, partitions, file systems, and mount configuration inside GuestOS.

## 1. Device Names and udev Rules

If the issue is a device name change after reboot, check whether udev rules caused the device name to be renamed.
   - If yes, comment out the udev rules and reboot.
   - Otherwise, under multiple PCI buses, device names may be assigned asynchronously. It is recommended to use [persistent block device naming](https://wiki.archlinux.org/title/Persistent_block_device_naming) in `/etc/fstab`.

## 2. Partition Tables and Partitions

Run `fdisk -l <device>` or `parted <device> print` to check whether the partition table and partitions are normal and as expected.

## 3. File System Information

Run `blkid | grep <device>` to check whether the file system information is as expected.

## 4. Mount Information

Run `grep <device> /proc/mounts` to check whether the mount state is as expected.
