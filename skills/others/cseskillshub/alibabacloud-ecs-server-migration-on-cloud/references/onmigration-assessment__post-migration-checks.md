# Checks after a migration, and where each failure goes

Run these before declaring a migration finished. The order matters: reachability
first, then boot, then the things that silently break later.

## 1. Reachability

| Check | How | If it fails |
| --- | --- | --- |
| The instance is running | `ecs:DescribeInstanceStatus` through the script | A machine stuck starting after a move is a boot problem, go to step 2 |
| The address really changed | `ecs:DescribeInstances`, compare against the source address | Re-point DNS after lowering the TTL; the source public address is never retained |
| Security groups exist on the target | `ecs:DescribeInstances` and the console | A migrated guest does not carry the platform security group; rebuild the rules on the target side |
| The service listens | Customer runs a local listener check inside the guest | Nothing outside can answer while the process is not listening |
| The guest firewall allows it | Customer checks the operating-system firewall | The security group and the guest firewall are two different layers |
| A control panel is not injecting rules | Customer compares panel rules against the container port publishing rules | A panel chain placed ahead of published ports is the usual cause of "the port worked before the move" |
| Interface is actually up | VNC session, customer inspects the interface | A down interface is the classic "VNC works, SSH does not" case |
| No leftover deny file blocks log-in | Inspection-only `stat` and `ls` through `guest-probe` | Editing the file is a human change, made after a snapshot |
| Host keys are present | Inspection-only `ls` on the key paths through `guest-probe` | Regenerating keys is a human change |

A static address carried over from a machine room does not match the cloud subnet.
The address of the virtual switch and its gateway come from the platform, not from the
source configuration, so a hand-written static address in a migrated image produces a
machine that is up and unreachable.

## 2. Boot and storage

| Check | How | If it fails |
| --- | --- | --- |
| Boot loader present and valid for the device layout | Inspection-only `stat` on the boot paths through `guest-probe` | Rebuilding it is outside this skill: hand off to the boot-repair flow after a snapshot |
| Block-device driver present for the target family | Compare the family against `NVME_INSTANCE_FAMILIES` in `scripts/axes/onmigration_assessment/_constants.py` | An image without the driver cannot start on that family; change the image or the family, both by a person |
| Device names match what the system expects | Inspection-only `findmnt` through `guest-probe` | Correcting a table of device names is a human change |
| Partitions fit the target disk size | `df -h` through `guest-probe` | A resize that did not apply is not a migration problem; hand off to disk expansion |

## 3. Identity and leftovers

| Check | Why |
| --- | --- |
| Instance RAM role attached, if the workload depends on instance identity | Credentials that came from the source do not follow the machine |
| Agent registrations and scheduled jobs that name the old host | They fail quietly weeks later |
| Licenses bound to hardware identifiers | A migrated machine presents different ones |
| Snapshots and images produced during the migration | They keep being billed and are depended upon by the resulting image |

Reference: [Attach an instance RAM role](https://help.aliyun.com/zh/ecs/user-guide/attach-an-instance-ram-role-to-an-ecs-instance.md)

## Hand-off table

| What the case really is | Goes to |
| --- | --- |
| A disk resize that did not apply, or a partition that is still small | The disk-expansion skill: `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis` |
| An instance stuck in an intermediate start or stop state, with no migration behind it | The instance-state skill: `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` |
| Slow disk throughput, or performance below the instance type | The disk-IO skill: `alibabacloud-ecs-disk-io-and-data-protection: disk-io-diagnosis` |
| Disk capacity or file-count exhaustion that needs cleanup | The capacity skill, not this one; here a capacity reading is only input to a sizing decision |
| A boot loader or file system that must be repaired | A human repair flow, after a snapshot |
| A different distribution on the same machine | A system-disk replacement, not a migration |
| An image or snapshot copy inside one cloud account and region | The image-based recovery skill: `alibabacloud-ecs-disaster-recovery-image` |
| Step-by-step execution of a website or server move already agreed | The site-migration guide: `alibabacloud-ecs-server-migration-on-cloud: site-migration-guide` |
| Anything commercial: money, filing, addresses of a facility, compensation | A human agent |
