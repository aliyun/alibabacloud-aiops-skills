# Linux SMB Mount System Requirements

## Supported Linux OS Versions

Due to limited SMB protocol compatibility on Linux systems, NAS SMB protocol file systems only support the following versions:

| Operating System | Minimum Version |
|-----------------|----------------|
| CentOS | CentOS 7.6 64-bit: 3.10.0-957.21.3.el7.x86_64 or above |
| Alibaba Cloud Linux | 2.1903 64-bit: 4.19.43-13.2.al7.x86_64 or above |
| Alibaba Cloud Linux 3 | 3.2104 64-bit: 5.10.23-4.al8.x86_64 or above |
| Debian | Debian 9.10 64-bit: 4.9.0-9-amd64 or above |
| Ubuntu | Ubuntu 18.04 64-bit: 4.15.0-52-generic or above |
| OpenSUSE | OpenSUSE 42.3 64-bit: 4.4.90-28-default or above |
| SUSE Linux | Enterprise Server 12 SP2 64-bit: 4.4.74-92.35-default or above |
| CoreOS | CoreOS 2079.4.0 64-bit: 4.19.43-coreos or above |

Check current kernel version: `uname -r`

## CIFS Client Installation Check

| Operating System | Check Command | Installation Command |
|-----------------|--------------|---------------------|
| Ubuntu / Debian | `sudo apt list cifs-utils` | `sudo apt-get install -y cifs-utils` |
| RHEL / CentOS | `sudo yum list cifs-utils` | `sudo yum install -y cifs-utils` |
| OpenSUSE / SLES | `sudo zypper search -i cifs-utils` | `sudo zypper install -y cifs-utils` |
| CoreOS | `which mount.cifs` | — |

## Linux SMB Mount Troubleshooting Flow

1. **OS version check** — Confirm it is in the supported list
2. **CIFS client check** — Confirm `cifs-utils` is installed or `mount.cifs` is in PATH
3. **Network connectivity check** — `ping <mount-target-address>`
4. **Account consistency** — ECS and SMB file system belong to the same Alibaba Cloud account (or connected via CEN)
5. **VPC consistency** — ECS and SMB file system are in the same VPC (or connected via CEN)
6. **Port 445 check** — `telnet <mount-target-address> 445`; if blocked, add port 445 rule in security group
7. **Permission group check** — Confirm permission group allows ECS access
8. **Admin privileges** — Confirm root or sudo access is available
9. **Mount command check**:
   ```bash
   sudo mount -t cifs //<mount-target-address>/myshare /mnt -o vers=2.0,guest,uid=0,gid=0,dir_mode=0755,file_mode=0755,mfsymlinks,cache=strict,rsize=1048576,wsize=1048576
   ```
10. **SELinux check** — Confirm SELinux settings for the mount target directory are correct
11. **Connection count check** — Maximum 1000 compute nodes per file system

If all checks pass but mounting still fails, collect `/var/log/messages` and `dmesg` output and submit a support ticket.
