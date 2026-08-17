
# Kernel and Initrd Stage Troubleshooting

## Kernel Loading Stage

Use dmesg, or follow [guestos-console-log](guestos-console-log.md) to obtain the serial console log, and determine whether the kernel stage, such as from “Linux version ...” to “Unpacking initramfs...”, is normal. Kernel issues are mostly related to instance types, kernel versions, and underlying virtualization. It is recommended to submit an Alibaba Cloud ticket for assistance.

## Initrd Stage

The initrd stage spans from initramfs extraction to rootfs remounting. Failures often enter emergency.target. After `chroot /mnt`, run `journalctl -b 0` to view startup errors and locate the exception. Common exceptions include missing virtio/nvme disk drivers in initrd, missing fstab mount-point devices/directories, and abnormal systemd services under `/lib/systemd/system/` inside initrd.
