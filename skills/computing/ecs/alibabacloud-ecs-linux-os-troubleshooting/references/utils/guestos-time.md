
# Time Configuration Troubleshooting

This document describes troubleshooting steps for time zones and NTP/chrony time synchronization inside GuestOS.

## Troubleshooting Steps

1. Run `ls -la /etc/localtime` to confirm whether it is a symlink pointing to a file under `/usr/share/zoneinfo/`. If it is not, it is recommended to change it to the corresponding symlink.
2. Check whether the ntp server in the NTP/chrony configuration is the Alibaba Cloud NTP server. Reference: [Configure NTP service to ensure accurate instance time](https://help.aliyun.com/zh/ecs/user-guide/alibaba-cloud-ntp-server#1d2319ae414lc)
3. Confirm whether the NTP/chrony service has started.
4. Run `journalctl -u ntp` or `journalctl -u chronyd` to view logs and check whether there are obvious errors.
5. Run `ls -la /etc/localtime` to check whether the time zone is consistent with the time zone configured in `/etc/timezone`. If it is inconsistent, recommend that the user modify `/etc/timezone` to make it consistent with `/etc/localtime`.
