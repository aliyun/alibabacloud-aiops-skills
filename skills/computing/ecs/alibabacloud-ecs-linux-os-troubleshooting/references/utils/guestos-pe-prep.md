# Preparing an Offline Troubleshooting Environment

This document describes the standard process for **detaching the system disk of the problematic instance and attaching it to a rescue instance** to perform offline troubleshooting. The workflow changes ECS resource state. Before each state-changing stage, explain the exact operation, affected instance or disk, rollback path, and possible downtime or credential impact, then obtain explicit user consent.

## Table of Contents

- [Preparing an Offline Troubleshooting Environment](#preparing-an-offline-troubleshooting-environment)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites and Constraints](#prerequisites-and-constraints)
  - [Safety Gates](#safety-gates)
  - [Preparation Steps](#preparation-steps)
  - [Rollback After Troubleshooting Is Complete](#rollback-after-troubleshooting-is-complete)

## Prerequisites and Constraints

- The user must provide a **rescue instance**, and the **rescue instance** and the problematic instance must be in the **same zone** (a cloud disk can only be attached to an instance in the same AZ).
- The system disk of the problematic instance must have `Portable=true` (`cloud_essd` / `cloud_auto` / `cloud_ssd` and other elastic cloud disks satisfy this by default).
- The problematic instance must first be stopped to `Status=Stopped` before its system disk can be detached.
- It is recommended that the **rescue instance** use the same distribution and major version as the problematic instance (to avoid command/library incompatibility after chroot), and that the rescue instance be in the `Running` state.
- **Cloud Assistant on the rescue instance must be online** (`CloudAssistantStatus` is the string `"true"`); otherwise, the subsequent `RunCommand` delivery of the mount script will fail. If it is `"false"`, inform the user.

> ⚠️ System disk reattachment is restricted by policy for some accounts/regions. If `AttachDisk` reports an error such as `InvalidDisk.SystemDiskAttach`, restore the environment and terminate the subsequent process.

## Safety Gates

Before executing this workflow:

1. Validate all IDs, region values, JSON literals, and credential inputs.
2. Record the original state of the problematic instance and disk.
3. Ask for explicit confirmation before each state-changing stage.
4. Prefer graceful stop. Use `--force-stop true` only after the user explicitly confirms force stop because the GuestOS is unresponsive or a graceful stop timed out.
5. Use bounded waits for every polling step: poll every 10 to 20 seconds, stop after 10 minutes or 30 attempts, and report the last observed status before deciding the next action.
6. If any stage fails, stop immediately and execute only the rollback step that restores the disk to the last confirmed safe state.

## Preparation Steps

1. **Stop the problematic instance** and poll until `Status=Stopped`. Start with graceful stop; use `--force-stop true` only after explicit user confirmation. Use `--stopped-mode KeepCharging`, because the economical mode `StopCharging` releases the auto-assigned public IP address of a pay-as-you-go VPC instance, so the instance would come back with a different public IP after the troubleshooting:
   ```bash
   aliyun ecs stop-instance --region <region> --instance-id <bad-i-xxx> --stopped-mode KeepCharging \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
   aliyun ecs describe-instances --biz-region-id <region> --instance-ids '["<bad-i-xxx>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Instances.Instance[0].Status'
   ```

2. **Locate the system disk ID and zone of the problematic instance**, and verify that the rescue instance is in the same AZ:
   ```bash
   # Obtain the system disk DiskId / ZoneId / Portable.
   aliyun ecs describe-disks --biz-region-id <region> --instance-id <bad-i-xxx> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq '.Disks.Disk[] | select(.Type=="system") | {DiskId, ZoneId, Category, Portable}'

   # Verify that the rescue instance ZoneId is the same.
   aliyun ecs describe-instances --biz-region-id <region> --instance-ids '["<rescue-i-xxx>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Instances.Instance[0].ZoneId'

   # Verify that Cloud Assistant is online on the rescue instance (CloudAssistantStatus must be true).
   aliyun ecs describe-cloud-assistant-status --biz-region-id <region> --instance-id <rescue-i-xxx> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq '.InstanceCloudAssistantStatusSet.InstanceCloudAssistantStatus[0] | {CloudAssistantStatus, CloudAssistantVersion}'
   ```

3. **Detach the system disk from the problematic instance** and poll until `Disk.Status=Available`:
   ```bash
   aliyun ecs detach-disk --region <region> --instance-id <bad-i-xxx> --disk-id <system-disk-id> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
   aliyun ecs describe-disks --biz-region-id <region> --disk-ids '["<system-disk-id>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Disks.Disk[0].Status'
   ```

4. **Attach the disk to the rescue instance** (the rescue instance can remain Running and the disk is hot-attached as a data disk), and poll until `Disk.Status=In_use` and the `Device` field has been assigned:
   ```bash
   aliyun ecs attach-disk --region <region> --instance-id <rescue-i-xxx> --disk-id <system-disk-id> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
   aliyun ecs describe-disks --biz-region-id <region> --disk-ids '["<system-disk-id>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq '.Disks.Disk[0] | {Status, Type, Device, InstanceId}'
   ```

   After being attached to the rescue instance, the disk `Type` changes from `system` to `data` (this is expected behavior; it will return to `system` after the disk is attached back to the original instance).

   Note that the `Device` value reported by the control plane, such as `/dev/xvdb`, does **not** necessarily match the device name inside the rescue instance, which is typically `/dev/vdb`. This is why the next step locates the disk by serial number instead of by device name.

5. **Use Cloud Assistant to mount the root file system of the problematic disk on the rescue instance**: For Alibaba Cloud virtio-blk / NVMe, the disk `SERIAL` field exposed in GuestOS is the cloud disk `DiskId` with the `d-` prefix removed (for example, `d-bp19xdd4d6utncfv6r6f` ↔ SN `bp19xdd4d6utncfv6r6f`). Based on this, you can **precisely locate the newly attached problematic disk** inside the rescue instance and avoid guessing the device name by `/dev/vdb`.

   ```bash
   EXPECTED_SN=$(echo "<system-disk-id>" | sed 's/^d-//')

   CMD=$(cat <<'EOF' | sed "s/__EXPECTED_SN__/$EXPECTED_SN/"
   #!/bin/bash
   set -euo pipefail
   EXPECTED_SN='__EXPECTED_SN__'

   # 1) Locate the block device of the problematic disk: try lsblk SERIAL → udevadm ID_SERIAL → nvme id-ctrl in order.
   DISK_DEV=""
   for d in $(lsblk -dn -o NAME); do
     sn=$(lsblk -dn -o NAME,SERIAL | awk -v n="$d" '$1==n && $2!="" {print $2; exit}')
     [ -z "$sn" ] && sn=$(udevadm info --query=property --name="/dev/$d" 2>/dev/null \
       | awk -F= '$1=="ID_SERIAL_SHORT"{print $2; exit}')
     [ -z "$sn" ] && [[ "$d" == nvme* ]] && command -v nvme >/dev/null 2>&1 \
       && sn=$(nvme id-ctrl "/dev/$d" 2>/dev/null | awk '/^sn[[:space:]]*:/{print $NF; exit}')
     if [ "$sn" = "$EXPECTED_SN" ]; then DISK_DEV="$d"; break; fi
   done
   [ -n "$DISK_DEV" ] || { echo "FATAL: no block device with serial=$EXPECTED_SN" >&2; exit 1; }
   echo "Matched block device: /dev/$DISK_DEV"

   # 2) Iterate over all partitions on the disk. If any of the three marker files exists, identify it as the root partition.
   ROOT_PART=""
   PROBE=/tmp/_root_probe; mkdir -p "$PROBE"
   for p in $(lsblk -ln -o NAME,TYPE "/dev/$DISK_DEV" | awk '$2=="part"{print $1}'); do
     if mount -o ro "/dev/$p" "$PROBE" 2>/dev/null; then
       if [ -f "$PROBE/etc/fstab" ] || [ -f "$PROBE/etc/passwd" ] || [ -f "$PROBE/etc/shadow" ]; then
         ROOT_PART="$p"; umount "$PROBE"; break
       fi
       umount "$PROBE"
     fi
   done
   rmdir "$PROBE" 2>/dev/null || true
   [ -n "$ROOT_PART" ] || { echo "FATAL: no rootfs partition on /dev/$DISK_DEV" >&2; exit 1; }
   echo "Root partition: /dev/$ROOT_PART"

   # 3) Mount the root partition.
   mkdir -p /mnt
   mount "/dev/$ROOT_PART" /mnt

   # 4) Parse /mnt/etc/fstab. If an EFI entry exists (mount point is /boot/efi or type is vfat), mount it as well. The optional EFI entry may be in one of four forms: UUID= / LABEL= / PARTUUID= / /dev/*, and must be converted to a device path with blkid.
   EFI_LINE=$(awk '$1 !~ /^#/ && NF>=3 && ($2=="/boot/efi" || $2=="/boot/EFI" || $3=="vfat") {print; exit}' /mnt/etc/fstab || true)
   if [ -n "$EFI_LINE" ]; then
     EFI_SRC=$(echo "$EFI_LINE" | awk '{print $1}')
     EFI_MNT=$(echo "$EFI_LINE" | awk '{print $2}')
     case "$EFI_SRC" in
       UUID=*)     EFI_DEV=$(blkid -U "${EFI_SRC#UUID=}" || true) ;;
       LABEL=*)    EFI_DEV=$(blkid -L "${EFI_SRC#LABEL=}" || true) ;;
       PARTUUID=*) EFI_DEV=$(blkid -t "PARTUUID=${EFI_SRC#PARTUUID=}" -o device | head -n1 || true) ;;
       /dev/*)     EFI_DEV="$EFI_SRC" ;;
       *)          EFI_DEV="" ;;
     esac
     if [ -n "$EFI_DEV" ] && [ -b "$EFI_DEV" ]; then
       mkdir -p "/mnt$EFI_MNT"
       mount "$EFI_DEV" "/mnt$EFI_MNT"
       echo "Mounted EFI: $EFI_DEV -> /mnt$EFI_MNT"
     fi
   fi

   # 5) Bind mount runtime file systems.
   for d in dev dev/pts dev/shm proc sys run tmp; do
     mkdir -p "/mnt/$d"
     mount --bind "/$d" "/mnt/$d"
   done
   echo "OK: /dev/$ROOT_PART mounted at /mnt with bind mounts"
   EOF
   )

   INVOKE_ID=$(aliyun ecs run-command \
     --biz-region-id <region> \
     --type RunShellScript \
     --instance-id <rescue-i-xxx> \
     --command-content "$CMD" \
     --timeout 600 \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.InvokeId')

   # Poll the execution status until InvokeRecordStatus=Finished.
   aliyun ecs describe-invocations --biz-region-id <region> --invoke-id "$INVOKE_ID" \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq '.Invocations.Invocation[0] | {InvokeStatus, InvocationStatus: .InvokeInstances.InvokeInstance[0].InvocationStatus}'

   # Fetch the script output (Output is base64 and must be decoded).
   aliyun ecs describe-invocation-results --biz-region-id <region> --invoke-id "$INVOKE_ID" \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' | base64 -d
   ```

   If the output contains `OK: /dev/<root-part> mounted at /mnt with bind mounts`, the problematic disk has been mounted successfully.

## Rollback After Troubleshooting Is Complete

1. **Use Cloud Assistant to unmount all mount points of the problematic disk on the rescue instance**.

   ```bash
   INVOKE_ID=$(aliyun ecs run-command \
     --biz-region-id <region> \
     --type RunShellScript \
     --instance-id <rescue-i-xxx> \
     --command-content 'umount -R -l /mnt; ! findmnt /mnt' \
     --timeout 60 \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.InvokeId')

   aliyun ecs describe-invocation-results --biz-region-id <region> --invoke-id "$INVOKE_ID" \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Invocation.InvocationResults.InvocationResult[0].Output' | base64 -d
   ```

2. Detach the cloud disk from the rescue instance and poll until `Disk.Status=Available`:
   ```bash
   aliyun ecs detach-disk --region <region> --instance-id <rescue-i-xxx> --disk-id <system-disk-id> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
   aliyun ecs describe-disks --biz-region-id <region> --disk-ids '["<system-disk-id>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Disks.Disk[0].Status'
   ```

3. **Reattach the disk to the problematic instance as the system disk**. API limitation: When `AttachDisk` attaches the disk to the system disk slot `/dev/xvda`, either `--password` or `--biz-key-pair-name` must be provided at the same time (the API treats this as the “reset system disk” path, which is a hard requirement at the documentation layer). Without a credential the call fails with `InvalidParameter.AllEmpty`, and passing `--bootable true` instead of `--device` does not avoid this requirement. If **`--device` is not specified**, the disk is automatically attached as a data disk slot, such as `/dev/xvdc`, and the original instance will fail to start because it has no system disk. **Choose one of the following two credential methods, and inform the user and obtain consent in either case**:

   - Method A: Reuse an existing key pair in the region. The public key is injected into `/root/.ssh/authorized_keys` on the disk, and the original password remains usable:
     ```bash
     aliyun ecs attach-disk --region <region> --instance-id <bad-i-xxx> --disk-id <system-disk-id> --device /dev/xvda --biz-key-pair-name <existing-keypair> \
       --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
     ```
   - Method B: Inject a new password. This applies when the original instance is not bound to a KeyPair and password overwrite is acceptable. **The password must be enclosed in single quotes** to prevent the local shell from parsing special characters (`&` `$` `*` `;` `!`, etc.; password complexity requirements: 8–30 characters and at least three of the following categories: uppercase letters, lowercase letters, digits, and special characters):
     ```bash
     aliyun ecs attach-disk --region <region> --instance-id <bad-i-xxx> --disk-id <system-disk-id> --device /dev/xvda --password '<new-pwd>' \
       --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
     ```

   Poll until `Disk.Status=In_use`, `Type=system`, and `Device=/dev/xvda`:
   ```bash
   aliyun ecs describe-disks --biz-region-id <region> --disk-ids '["<system-disk-id>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq '.Disks.Disk[0] | {Status, Type, Device, InstanceId}'
   ```

4. Start the problematic instance and verify whether it has started normally:
   ```bash
   aliyun ecs start-instance --region <region> --instance-id <bad-i-xxx> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id>
   aliyun ecs describe-instances --biz-region-id <region> --instance-ids '["<bad-i-xxx>"]' \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq -r '.Instances.Instance[0].Status'
   ```

   **Preferred: Use the Cloud Assistant heartbeat to determine that GuestOS has started successfully**. `DescribeCloudAssistantStatus` returning `CloudAssistantStatus=true` is equivalent to GuestOS being online:
   ```bash
   aliyun ecs describe-cloud-assistant-status --biz-region-id <region> --instance-id <bad-i-xxx> \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-linux-os-troubleshooting/<session-id> \
     | jq '.InstanceCloudAssistantStatusSet.InstanceCloudAssistantStatus[0] | {CloudAssistantStatus, LastHeartbeatTime, LastInvokedTime}'
   ```

   If the instance still has not started normally, inform the user.
