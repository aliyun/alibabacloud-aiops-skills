
# sshd Service and Configuration Troubleshooting

This document describes troubleshooting steps for the sshd service and its configuration inside GuestOS.

## Troubleshooting Steps

1. Run `sudo systemctl status sshd.service` (RHEL/SUSE) or `sudo systemctl status ssh.service` (Debian) to check the sshd status and whether there are obvious failures.
2. Run `sudo sshd -t` to check whether `/etc/ssh/sshd_config` reports any obvious errors.

- Reference: [Permission denied and similar errors](https://help.aliyun.com/zh/ecs/support/what-do-i-do-if-the-permission-denied-please-try-again-error-message-appears-when-i-log-on-to-a-linux-instance-as-the-root-user-by-using-ssh).
