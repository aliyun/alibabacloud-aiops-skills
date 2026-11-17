# Published handoff skills (catalogue-verified 2026-11-11, re-checked 2026-11-16)

This table is the one authority for naming another skill. `scripts/_skill_handoff.py`
reads it at answer time, and a name absent from it is treated as unresolvable: the
customer-facing scrub will not deliver it and the hand-off ladder will not offer it.
Each name below was resolved against the published skill catalogue (HTTP 200 whose
`name:` frontmatter equals the requested code), so a handoff that names it reaches a
skill the customer can actually install. Add a row only on that evidence, never on
plausibility. What each one solves:

| Skill | What it owns |
|---|---|
| `alibabacloud-ecs-diagnose` | Systematic instance diagnostics: cloud-platform status checks plus in-guest checks through Cloud Assistant, for an instance that is sick, unreachable or slow. |
| `alibabacloud-ecs-snapshot-and-backup` | Snapshot and backup work on their own terms: what a snapshot costs, how the charge is calculated, and whether a restore is possible for the disk in question. |
| `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` | Whether a packet reaches the instance and comes back: public IP unreachable, ping timeout, security group blocking public access, VPC cloud-service egress. |
| `alibabacloud-ecs-linux-os-troubleshooting` | A Linux guest that will not come up or will not be entered: stuck Starting, boot stuck, SSH/VNC/Workbench login failure, in-OS service faults. |
| `alibabacloud-ecs-disaster-recovery-image` | Cross-zone recovery built on an image: create a custom image from a running instance and deploy a new instance in another zone. |
| `alibabacloud-ecs-disaster-recovery-snapshot` | Cross-zone recovery built on snapshots: recover the whole instance, or single disks, into another zone from snapshots. |
| `alibabacloud-ecs-install-extension` | Extension work on an instance: list available extensions, check applicability, one-click install. |
| `alibabacloud-ecs-health-inspection` | Periodic health inspection of instances: CPU, load, memory, disk IO BPS/IOPS, network traffic and disk capacity swept together, not one fault. |
| `alibabacloud-ecs-snapshot-and-backup` | Snapshot and backup work on their own terms: what a snapshot costs, how the charge is calculated, and whether a restore is possible for the disk in question. |

Names outside the ECS prefix, verified the same way:

| Skill | What it owns |
|---|---|
| `alibabacloud-cli-guidance` | Aliyun CLI usage: argument rules, plugin management, versions, and reading a CLI error message. |
| `alibabacloud-cloudbackup-ecs-file-backup-essential-edition` | Cloud Backup (HBR) file backup essential edition for ECS files: the backup plan itself, not an ECS-side fault. |
| `alibabacloud-ebs-disk-snapshot-management` | Block-storage disk and snapshot management on the EBS side: create, retain, roll back. |
| `alibabacloud-finops-inspect` | FinOps cost inspection across a account's billing structure, beyond one ECS line item. |
| `alibabacloud-mining-attack-diagnosis` | Mining-attack diagnosis: the incident response that follows a confirmed mining flag. |
| `alibabacloud-mtr-network-diagnosis-customer` | MTR path diagnosis run from the customer side for latency and packet loss across a route. |
| `alibabacloud-network-diagnose` | Network reachability diagnosis across the VPC and internet path, when the fault is not in the instance. |
| `alibabacloud-workbench-cli` | Workbench CLI remote connection: entering a instance through the browser-side channel. |
