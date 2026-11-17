# Guest diagnostic command policy

No call to the platform can tell you what an operating system sees. Device enumeration,
filesystem presence, mount points and volume state exist only inside the instance, so this
skill collects them by delivering a command. That is why the skill is not confined to
describe calls, and it is exactly why the delivery path is constrained harder than anything
else in the package.

## Three independent constraints

1. **Content.** Only a command that appears verbatim in `GUEST_COMMAND_WHITELIST_LINUX` or
   `GUEST_COMMAND_WHITELIST_WINDOWS` in
   [../scripts/areas/disk_attach_os_visibility/_constants.py](../scripts/areas/disk_attach_os_visibility/_constants.py) can be delivered. Compare byte for
   byte after whitespace normalisation. No shell composition, no redirection, no pipes, no
   arguments appended, no `&&`, no `;`, no variable, no wrapper.
2. **Disclosure.** Before the flag `--confirmed` may be passed, the customer has been told
   the exact command, that it prints information and changes nothing, that it runs inside
   their instance, that the output is read once and discarded, and that they may run it
   themselves and paste the result instead.
3. **Scope.** One command per delivery, one confirmation per command. An agreement for
   `lsblk -f` is not an agreement for `df -h`.

`scripts/areas/disk_attach_os_visibility/guest_probe.py` enforces 1 and 2 in code: without `--confirmed` it exits before
any call and prints the disclosure it wants read aloud; a command outside the list is
refused with the reason and the approved alternatives. Passing `--print-only` shows the
request that would be made without making it.

## Approved commands and what each proves

| Command | Family | Proves | Notes |
| --- | --- | --- | --- |
| `lsblk` | Linux | Which block devices exist, and their size | The join key between a disk id and a device name |
| `lsblk -f` | Linux | Filesystem type, label, uuid, mount point | An empty filesystem column is link 4 broken |
| `fdisk -l` | Linux | Partition table view | Second opinion when `lsblk` looks inconsistent |
| `cat /proc/partitions` | Linux | What the kernel itself registered | Separates a userspace listing problem from a kernel one |
| `df -h` | Linux | Mounted filesystems and usage | The listing customers quote when they say the disk is missing |
| `findmnt` | Linux | The mount tree with source and target | Best evidence for a hidden directory |
| `Get-Volume` | Windows | Filesystem, health, operational state, capacity | A volume that is offline or letterless explains an absent drive |
| `Get-PSDrive` | Windows | Which paths currently resolve | Confirms what a customer can actually open |
| `fsutil fsinfo drives` | Windows | Which drive letters exist | Cross-check after a reinstall |

Sizes, filesystem types and mount points are matched against the control-plane facts by
[../scripts/areas/disk_attach_os_visibility/report_builder.py](../scripts/areas/disk_attach_os_visibility/report_builder.py) with a tolerance, and the raw
text is always reproduced in the report so the customer can check the reading itself.

## Deliberately excluded

The approved list for the product family is an upper bound; the commands above are a
subset chosen for these five links. The following stay on the human side, so the customer
runs them and pastes the output:

| Command | Why it is not delivered |
| --- | --- |
| `blkid` | Not on the approved list. `lsblk -f` carries the same uuid and type information. |
| `stat <path>` | Path arguments turn an allow-list into a pattern; mount evidence comes from `df -h` and `findmnt`. |
| `cat /etc/fstab` | Reading a customer configuration file is outside this list. Automatic mounting after reboot is explained from the fstab guidance document instead. |
| `lsblk -o <columns>` | Column variants are not approved, so serial-number matching is not used; see the naming map. |
| `Get-Disk` | Not on the approved list, so a Windows volume that is offline is inferred from `Get-Volume` state rather than from the disk object. |
| `mount`, `umount`, `mkfs`, `fdisk` with a device, `parted`, `growpart`, `diskpart`, `fsck`, anything writing to a device | These change data. They are guidance only, with the risk named and a recovery point checked first. |
| `reboot`, service restarts, agent installation | Power and lifecycle actions are never issued from here. |

## When delivery is not possible

Cloud Assistant must be present and reachable on the instance, and the caller needs the
`ecs:run-command` permission. If the delivery fails, if the agent is absent, or if the
customer declines, the report keeps the cloud half and marks the OS half
`OS_READINGS_UNAVAILABLE`. That is a degraded run by design: the alternative, guessing at
what the guest sees, is how a supporter ends up pointing a customer at the wrong device.

## One thing to verify on the operator's own machine

Commands are delivered with a Cloud Assistant command type selected from
`COMMAND_TYPE_BY_OS`. Confirm the accepted values on the local CLI build before the first
delivery with `aliyun ecs run-command --help`. If the values differ, update that constant
rather than inventing a new parameter, and keep the approved command list untouched.
