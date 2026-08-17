# cloud-init and User-Data Troubleshooting

Troubleshooting steps related to cloud-init and User-Data execution inside GuestOS.

## 1. Accessing the meta-server

Run `curl --connect-timeout 5 --max-time 10 100.100.100.200` to check whether it is inaccessible. If it is inaccessible, refer to [Unable to access Metaserver](https://help.aliyun.com/zh/ecs/support/a-linux-instance-cannot-access-the-metaserver).

## 2. Whether User-Data Is Delivered

Run `curl --connect-timeout 5 --max-time 10 http://100.100.100.200/latest/user-data` to check whether content exists. If no content exists, User-Data is not configured.

## 3. User-Data Execution Frequency and Semaphores

User-Data is generally per-instance. After execution, a semaphore is generated under `/var/lib/cloud/instances/i-xxxx/sem/`. On the next boot, if the semaphore exists, it will not execute again. If this is the second boot after the instance was created, User-Data will not execute.

## 4. User-Data Content Format

1. The first line must start with `#!` and comply with the User-Data standard. Reference documentation: [Initialize instances with custom data](https://help.aliyun.com/zh/ecs/user-guide/overview-of-ecs-instance-user-data).
2. Check whether script files such as `part-001` exist under `/var/lib/cloud/instance/scripts/`. If they do not exist, the user-data format is incorrect.
3. If `/var/log/cloud-init.log` contains content similar to `Unhandled non-multipart`, it indicates a format error.

## 5. cloud-init Configuration and the fw_cfg File

1. Check whether cloud-init is installed and enabled at boot. If it does not exist or is not correctly enabled at boot, the User-Data feature will be abnormal.
2. Check whether `/sys/firmware/qemu_fw_cfg/by_name/etc/cloud-init/vendor-data/raw` exists, and whether `/etc/cloud/cloud.cfg.d/aliyun_cloud.cfg` is symlinked to the preceding raw file. If it does not exist or is not correctly symlinked, the cloud-init feature will be abnormal.

## 6. cloud-init Process Terminated Unexpectedly

1. Check whether `/var/log/cloud-init.log` contains keywords such as `failed run of stage` or `Exit code: -9`, or whether the log stops abruptly at a stage with no further output. Either symptom indicates that the cloud-init process was terminated before it finished.
2. **Killed by OOM**: when the system runs out of memory, the kernel OOM Killer terminates processes. Check the system logs (`dmesg -T | grep -i -E 'oom-killer|Killed process'`) to confirm whether a cloud-init related process was killed by OOM.

## 7. Script Execution Return Value

If `/var/log/cloud-init.log` contains content similar to `Failed running .../part-001 [1]`, `[1]` is the script exit code. A non-zero value indicates a problem with the script itself, and the user must check the script content.
