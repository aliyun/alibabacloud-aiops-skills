
# systemd and System Service Stage Troubleshooting

Use systemd as an example. In initramfs, init is usually symlinked to systemd. After services inside ramfs are started, initrd-switch-root switches to rootfs, and then systemd under the root directory is executed. This stage spans from “Switch Root” or “Welcome to ...” in the serial console to the appearance of the login prompt.

If the system hangs during this stage, the serial console logs and VNC screen are often stuck on a specific line, for example because a systemd service is abnormal and blocks startup.

## Troubleshooting Steps

1. After `chroot /mnt`, analyze the boot logs with `journalctl`.
2. Temporarily disable suspicious services, such as renaming `xxx.service` to `.bak`.
3. Set `LogLevel=debug` in `/etc/systemd/system.conf`, then view detailed logs after reboot.
4. If a service anomaly is found in the systemd logs, troubleshoot the unit and execution logic of the specific abnormal service.
