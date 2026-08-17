# The Instance Is Already in the Running State, but GuestOS Has Not Started Normally

## Confirm Whether It Is a GuestOS Issue

1. Use `DescribeImageSupportInstanceTypes` to verify whether the current image supports the instance type of the instance.
   - The current instance type is not in the supported list: the image and the instance type are incompatible, which causes startup failure. Provide the conclusion and recommend replacing the image or changing the instance type.
   - It is in the supported list: continue.
2. Use `DescribeInstances` and `DescribeImages` to obtain instance type and image information. Determine whether the instance type boot mode, image boot mode, and instance boot mode match: [UEFI/BIOS boot mode](https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-using-the-uefi-boot-mode-and-bios-boot-mode#d3b42dc870vzq).
   - Mismatch: this causes startup failure.
   - Match: continue.
3. If it is a FreeBSD image (confirm the image type through `DescribeInstances`): it must meet the conditions for running on Alibaba Cloud: [FreeBSD operating system compatibility](https://help.aliyun.com/zh/ecs/user-guide/the-freebsd-operating-system-compatibility?spm=a2c4g.11186623.help-menu-25365.d_4_2_15_2_5.288eb11ewWYENa).
   - Does not meet the conditions: this causes startup failure.
   - Meets the conditions: continue.
4. If it is a confidential instance (confirm the instance type and the TDX/heterogeneous confidential computing instance type lists through `DescribeInstanceTypes`): confirm whether the image supports the TDX/heterogeneous confidential environment: [Build a TDX confidential computing environment and remote attestation service](https://help.aliyun.com/zh/ecs/user-guide/build-a-tdx-confidential-computing-environment), [Build a heterogeneous confidential computing environment](https://help.aliyun.com/zh/ecs/user-guide/build-a-heterogeneous-confidential-computing-environment).
   - Not supported: this causes startup failure.
   - Supported: continue.
5. Use the instance type and OS information obtained from `DescribeImage` and `DescribeInstances` to verify compatibility between the instance type, operating system, and AMD/Intel: [Compatibility between AMD instance type generations and operating systems](https://help.aliyun.com/zh/ecs/user-guide/compatibility-between-amd-instance-types-and-operating-systems), [Intel instance type and operating system compatibility](https://help.aliyun.com/zh/ecs/user-guide/intel-instance-specifications-and-operating-system-compatibility).
   - Incompatible: this causes startup failure.
   - Compatible: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- Bootloaders such as GRUB and their configuration
- Kernel and configuration
- init process and configuration
- File system mounting and configuration
- Main system services and configuration

### Issue Localization

1. Confirm whether GuestOS has started normally. If it has started normally, this does not belong to this phenomenon domain; return the conclusion to the user directly.
   - Use `GetInstanceScreenshot` to view the VNC screenshot, or follow [guestos-console-log](utils/guestos-console-log.md) to obtain the serial console log. Reaching the login screen can be considered successful startup.
   - Use `DescribeCloudAssistantStatus` to view the Cloud Assistant status. A normal Cloud Assistant status usually indicates that the system has started.
2. If GuestOS has not started normally, use `GetInstanceScreenshot` to view the VNC screenshot and follow [guestos-console-log](utils/guestos-console-log.md) to obtain and analyze the serial console log (use the `Startup stuck` keywords). Check whether it contains abnormal startup logs and analyze the abnormal information.
   - **You may output a conclusion based on the serial console log or the screenshot and end the investigation only when all of the following conditions are met**:
     1. The serial console log or the screenshot contains an **explicit and specific** error, such as `/etc/fstab` referencing a nonexistent disk path, a systemd circular dependency, an explicit file system or disk error, or a missing virtio driver, rather than a generic symptom such as a GRUB boot failure.
     2. The error **uniquely points to a single root cause**, with no multiple indistinguishable possibilities. For example, a GRUB boot failure may involve a missing initrd, an incorrect GRUB configuration file, and other root causes, so the investigation cannot end in that case.
     3. An **actionable remediation plan** can already be provided based on it.
   - **If any of the preceding conditions is not met**, treat the result as "root cause not clear". **Do not guess or draw a conclusion based on incomplete information**, and you MUST continue with the offline troubleshooting in step 3.
3. When the result is "root cause not clear", enter offline troubleshooting. This workflow requires stopping the problematic instance and detaching its system disk, which interrupts the instance, so **you must first confirm with the user whether the instance can be stopped and obtain the required rescue instance**. After confirmation, refer to [guestos-pe-prep](utils/guestos-pe-prep.md) to prepare the offline troubleshooting environment (PE), then troubleshoot the Linux startup stages inside PE by component:
   1. [guestos-boot](utils/guestos-boot.md) — Boot-stage troubleshooting
   2. [guestos-grub](utils/guestos-grub.md) — GRUB boot-stage troubleshooting
   3. [guestos-kernel-initrd](utils/guestos-kernel-initrd.md) — Kernel and Initrd-stage troubleshooting
   4. [guestos-systemd](utils/guestos-systemd.md) — systemd and system service-stage troubleshooting
