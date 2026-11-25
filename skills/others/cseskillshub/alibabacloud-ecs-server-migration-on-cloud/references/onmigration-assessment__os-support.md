# Operating-system posture, SLA wording, and the SMC-R homonym

## How to use this page

Screening only. The authoritative matrix is the official Server Migration Center
supported-operating-system list, which is the document to read before committing a
date to a customer. The postures below were collected from previously handled cases
where the engineer had to ask the migration team; each one is stated with how it was
obtained so it can be re-checked. Never present a screening posture as a commitment.

| Source release | Screening posture | What still has to be proven |
| --- | --- | --- |
| Red Hat Enterprise Linux 4, CentOS 4 | Not accepted by whole-server migration | Use an image import or rebuild the service |
| Red Hat Enterprise Linux 5, CentOS 5 | Accepted only on certain older instance types | Confirm the type is still sellable; a type that is no longer sold makes this path unusable |
| Red Hat Enterprise Linux 6 or 7, CentOS 6 or 7 | Generally accepted | Run a migration drill: dependencies and drivers on very old releases fail in ways the checklist does not catch |
| Windows Server 2008 and 2012 | Unconfirmed | Check the supported list first; do not schedule before it matches |
| Alibaba Cloud Linux, Ubuntu, Debian, SUSE, Open-source RHEL derivatives | Generally accepted | Confirm the exact minor release against the supported list |
| A release newer than this table | Unknown | Treat as unknown and say so; do not extrapolate from a neighbour version |

The target instance type is verified with the script sub-command
`target-availability`, which answers "can this resource actually still be bought in
this region and zone" instead of relying on a guess about retired types.

## Service level wording

The service-level agreement is not restricted by operating-system version. Some
instance families carry no service-level agreement at all, which is a property of the
family, not of the migrated system. A machine that arrives through migration is an
ordinary ECS instance afterwards.

Reference: [Alibaba Cloud service level agreement terms](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud201909241949_62160.html)

## Local disk, encryption, and expiry

- A local-disk instance loses its data when it is stopped or redeployed. Local data
  must be backed up before any migration step, and this is the item most often
  forgotten.
- Migration copies readable data. An encrypted source disk produces a target disk
  that is not encrypted. Where the source cloud's own encrypted disk must leave that
  cloud, the answer depends on the other provider and is not ours to give.
- A source that expired and can no longer be logged into cannot be migrated by the
  tool. The remaining paths are an image import or a rebuild from a backup.

## Operating-system migration is not a replacement

Migrating an operating system in place, for example CentOS 7 to Alibaba Cloud Linux 3,
is an upgrade run inside the guest. It fails on package and repository conflicts left
behind in the image, and it is not the same thing as swapping the system disk to
install a different distribution. A request to "switch this instance to Ubuntu" is a
system-disk replacement and belongs to that flow, not here.

Reference: [Migrate or upgrade the operating system of an instance](https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance.md)

## The two SMCs

`SMC` means Server Migration Center in this skill. In kernel networking, `SMC-R` means
Shared Memory Communications over RDMA. They are unrelated and share only the
abbreviation.

Signals that a request is about the kernel feature, not migration:
`tcp2smc`, `net.smc`, `modprobe smc`, `CONFIG_SMC`, `SMC-R`, RDMA wording, and an error
such as `can not stat /proc/sys/net/smc/tcp2smc`.

What to do: say plainly that this is not the migration tool, point at
[SMC-R shared memory communication configuration](https://help.aliyun.com/zh/ecs/user-guide/smc-instructions.md),
and note that whether the module is loaded is verified by a human operator running
`modprobe` checks; loading a kernel module is outside the allow-list of this skill.

## Architecture extensions worth recognising

- Elastic RDMA adaptation after a move:
  [Application adaptation for eRDMA](https://help.aliyun.com/zh/ecs/user-guide/description-of-application-adapter.md)
- Migration toward the Yitian ARM architecture:
  [EasyYitian migration tool](https://help.aliyun.com/zh/ecs/user-guide/easyyitian-migration-tools.md)
- Instance RAM role, when a workload depends on instance identity after the move:
  [Attach an instance RAM role](https://help.aliyun.com/zh/ecs/user-guide/attach-an-instance-ram-role-to-an-ecs-instance.md)
- Windows block-device timeout on newer families:
  [Adjust NVMe disk I/O timeout in a Windows instance](https://help.aliyun.com/zh/ecs/user-guide/adjust-the-i-o-timeout-for-nvme-drives-in-a-windows-instance.md)
