# Linux NFS Mount Error Reference

## Error 1: mount.nfs: No such device

**Cause**: The `options sunrpc tcp_slot_table_entries=128` configuration in `/etc/modprobe.d/sunrpc.conf` was incorrectly written as `tcp_slot_entries=128`, preventing the sunrpc module from loading properly.

**Resolution steps**:
1. Check configuration file: `cat /etc/modprobe.d/sunrpc.conf`
2. Correct the configuration to `options sunrpc tcp_slot_table_entries=128`
3. Load the module: `modprobe sunrpc`
4. Retry the mount

## Error 2: mount: can't find /root/nas in /etc/fstab

**Cause**: Incorrect mount command format.

**Resolution steps**: Use the correct mount command:

```bash
# General Purpose NAS - NFS v3
sudo mount -t nfs -o vers=3,nolock,proto=tcp,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport <mount-target-address>:/ /mnt

# General Purpose NAS - NFS v4
sudo mount -t nfs -o vers=4,minorversion=0,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport <mount-target-address>:/ /mnt

# Extreme NAS
sudo mount -t nfs -o vers=3,nolock,noacl,proto=tcp,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport <mount-target-address>:/share /mnt
```

## Error 3: mount.nfs: Operation not permitted (NFSv4)

**Symptom**: NFSv4.0 mount reports `mount.nfs: Operation not permitted` or `mount.nfs: an incorrect mount option was specified`, but NFSv3 mounts successfully.

**Cause**: The ECS hostname conflicts with another ECS hostname, and the conflicting ECS has already mounted the same NFS mount target using NFSv4.0.

**Resolution steps**:
1. Set a unique identifier:
   ```bash
   echo 'install nfs /sbin/modprobe --ignore-install nfs nfs4_unique_id=`cat /sys/class/dmi/id/product_uuid`' >> /etc/modprobe.d/nfs.conf
   ```
2. Restart the ECS instance during off-peak hours
3. Alternatively, unmount all NFS file systems, run `rmmod` to unload NFSv4.0 and NFS kernel modules, then remount

## Error 4: access denied by server while mounting .../<dir>

**Cause**: When mounting a subdirectory, the specified NAS subdirectory `<dir>` does not exist.

**Resolution steps**:
1. Mount the NAS root directory first: `sudo mount -t nfs ... <mount-target-address>:/ /mnt`
2. Create the required subdirectory: `mkdir /mnt/<dir>`
3. Unmount the root directory: `sudo umount /mnt`
4. Remount the subdirectory: `sudo mount -t nfs ... <mount-target-address>:/<dir> /mnt`

## Error 5: Auto-mount failure on boot (CentOS 7)

**Cause**: CentOS 7.0 does not process non-local file systems in fstab by default; `remote-fs.target` service is in disabled state.

**Solution A (Recommended)**:
```bash
systemctl start remote-fs.target
systemctl enable remote-fs.target
```

**Solution B (Temporary)**:
```bash
[ ! -f /etc/rc.local ] && echo '#!/bin/bash' > /etc/rc.local
echo "mount -a -t nfs" >> /etc/rc.local
chmod +x /etc/rc.local
```

## Error 6: Container NAS mount reports access denied

**Error**: `access denied by server while mounting <mount-address>`

**Possible causes**:
1. Mount directory does not exist
2. Container startup user lacks root privileges
3. Mount target permission group does not include the container IP

**Troubleshooting steps**:
1. Verify the mount directory exists: `cd <mount-directory>`
2. Confirm container user privileges; container must run in `privileged` mode
3. Check permission group rules in NAS console to verify the container IP is included

## NFS Client Installation Commands

| Operating System | Installation Command |
|-----------------|---------------------|
| CentOS / RHEL / Alibaba Cloud Linux | `sudo yum install -y nfs-utils` |
| Ubuntu / Debian | `sudo apt-get install -y nfs-common` |
| OpenSUSE / SLES | `sudo zypper install -y nfs-client` |

## Auto-Check Script

```bash
# Download
wget https://nas-client-tools.oss-cn-hangzhou.aliyuncs.com/linux_client/check_alinas_nfs_mount.py -P /tmp/

# Execute (replace with actual mount target address and local path)
python2.7 /tmp/check_alinas_nfs_mount.py file-system-id.region.nas.aliyuncs.com:/ /mnt
```
