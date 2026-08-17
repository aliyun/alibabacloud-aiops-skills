
# DNS Configuration Troubleshooting

This document describes troubleshooting steps for DNS configuration inside GuestOS, such as `/etc/resolv.conf`.

## Troubleshooting Steps

1. Use `ls -hal /etc/resolv.conf` to check whether the file is a regular file or a symbolic link.
  - **Regular file**: Configure `nameserver ...` in `/etc/resolv.conf` as Alibaba Cloud DNS, such as `100.100.2.136` and `100.100.2.138`.
  - **Symbolic link**: This indicates that the actual DNS configuration is not in `/etc/resolv.conf`. It is related to the network configuration service in use. Try troubleshooting according to the documentation for the relevant network configuration service.
