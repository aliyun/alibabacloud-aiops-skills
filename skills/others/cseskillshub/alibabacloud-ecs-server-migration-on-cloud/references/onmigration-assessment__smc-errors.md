# Recognising migration-tool failures

This page turns a symptom into a likely cause and a next step. Every row was taken
from a previously handled case where the customer saw exactly this, and each one is
re-checkable against the official help centre pages linked below. The skill identifies
and lists evidence; the repair is carried out by a person, after a snapshot.

## What to collect before judging anything

Ask for these together, in one message, instead of going back and forth:

1. The error text as shown in the console, copied rather than photographed.
2. The migration task identifier, the source name, and the region.
3. The source operating system and its exact release.
4. The tail of the client log on the source, under
   `/smc/go2aliyun_client*_linux_x86_64/Logs`.
5. For an in-place operating-system migration, the upgrade log at
   `/var/log/leapp/leapp-upgrade.log`.
6. Whether the task was submitted more than once for the same source.
7. After a completed migration: the target instance id, its instance type and
   family, and whether the image was self-created, copied, shared, or imported.

Only `DescribeInvocations` history and customer-supplied readings are available: the
migration task itself has no API called by this skill, so a console screenshot or a
log tail is the evidence, not a guess.

## Symptom table

| What is seen | Likely cause | Next step, by a person |
| --- | --- | --- |
| Task sits at "Syncing" and the progress does not move | The client on the source stopped reporting, or a second task for the same source competes with it | Read the client log tail, cancel the duplicate, restart the single remaining task |
| Submitting the task fails, or the disk size cannot be changed | The source is still associated with a workgroup | Remove the workgroup association, then re-submit |
| A shrink request is rejected although the plan looks right | The requested target is not above the bytes actually in use, or a partition is larger than the target | Take a `df -h` reading inside the source, then set a target above the used space |
| An in-place operating-system migration fails or stops part-way | Package and repository conflicts left in the image: duplicate repositories, a missing release package, or a vendored Python library clashing with the system one | Read the upgrade log, resolve the named conflicts manually, re-run. Removing packages is never done automatically |
| An instance built from a migrated or imported image stays in "Starting" | Boot loader written for the source device layout, or the block-device driver absent on an NVMe family | Hand off to the boot-repair flow; snapshot first, then rebuild the boot loader from a rescue instance |
| Console reporting differs from the actual result | Migration finished but the selected target release differed from what was expected | Compare the release inside the guest with the requested one before trusting the console line |
| VNC works, SSH is refused or times out | The guest network interface did not come up, a leftover deny file blocks the session, or the host keys went missing when the image was rebuilt | Log in through VNC, check the interface and the deny file, regenerate the host keys manually |
| A newly added public port is unreachable after a migration | A third-party control panel inserting firewall rules ahead of container port publishing, not the migration and not address translation | Test in order: security group, guest firewall, panel rules, local listener |
| Creating the service-linked role fails | Resource Access Control has not been activated for the account, or the sub-account lacks the grant | Activate it and grant the actions in `ram-policies.md`, then retry |
| An error mentioning `tcp2smc` or `SMC-R` | Not the migration tool: the kernel shared-memory transport over RDMA | Explain the difference, see `os-support.md` |

## Device naming after a move

A migrated or imported image often keeps the device names of the source. On an
NVMe-based family the root and data devices appear as `/dev/nvme0n1p1` and
`/dev/nvme1n1` rather than `/dev/vda` and `/dev/vdb`. Any repair command, fstab entry,
or script that names a device literally will point at the wrong disk. Verify the
mapping from inside the guest before quoting a fix that uses a device path.

Reference: [Adjust the I/O timeout for NVMe drives in a Windows instance](https://help.aliyun.com/zh/ecs/user-guide/adjust-the-i-o-timeout-for-nvme-drives-in-a-windows-instance.md)

## Increments, images, and cost

- Incremental synchronisation copies what changed since the previous run; it does not
  re-copy the whole disk. A final full pass still happens at cutover.
- Migration can leave images behind. An image retained after a move keeps being billed
  and keeps its dependency on the snapshots underneath it; deleting those snapshots
  breaks the image.
- Cost items to name in advance: snapshot storage, image copies across regions,
  outbound traffic, object storage used by an import, and the target instance itself.

Reference: [Apply an automatic snapshot policy](https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-applyautosnapshotpolicy.md)
