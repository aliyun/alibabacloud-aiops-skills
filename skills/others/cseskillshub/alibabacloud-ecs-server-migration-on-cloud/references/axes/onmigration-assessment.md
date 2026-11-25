---
name: alibabacloud-ecs-onmigration-assessment
description: |
  Assess whether an on-premises, VMware, physical, or other-cloud server (Tencent Cloud, AWS) can be migrated onto Alibaba Cloud ECS, choose the path, and identify Server Migration Center (SMC) errors. Use when: "move our machine-room servers to Alibaba Cloud", "server on another cloud expired, can it be imported", "SMC migration task stuck in Syncing", "after migration the instance stays Starting or SSH does not work", "port unreachable after migration", "SMC service-linked role cannot be created". Do NOT use for disk space or inode cleanup; a resize that did not apply (alibabacloud-ecs-disk-expand-diagnosis); instance state (alibabacloud-ecs-instance-state-diagnosis); slow disk IO (alibabacloud-ecs-disk-io-diagnosis); an image copy inside one account (alibabacloud-ecs-disaster-recovery-image); website move steps (alibabacloud-ecs-site-migration-guide); kernel SMC-R "can not stat /proc/sys/net/smc/tcp2smc"; refunds; ICP filing.
---

# ECS migration-to-Alibaba-Cloud assessment

This skill answers one question set: can this server move onto Alibaba Cloud ECS, by
which path, at what cost and risk, and what does a migration-tool failure mean. It
reads cloud state, judges it against built-in knowledge, and writes an evidence-based
report. Where a repair would be needed, it lists the step for a human operator instead
of performing it.

Read `references/onmigration-assessment__migration-paths.md` for path selection, `references/onmigration-assessment__os-support.md` for
release and service-level posture, `references/onmigration-assessment__smc-errors.md` for failure recognition,
`references/onmigration-assessment__post-migration-checks.md` for the after-move checklist, and
`references/ram-policies.md` for the permissions below.

## Permission model

This skill is not restricted to queries. It has three tiers, and the tier decides the
gate.

1. **Cloud queries** run automatically: `DescribeInstances`, `DescribeInstanceStatus`,
   `DescribeDisks`, `DescribeAvailableResource`, `DescribeCloudAssistantStatus`,
   `DescribeInvocations`, and `sts:GetCallerIdentity`.
2. **One inspection command inside the guest**, issued with `ecs:run-command`. Allowed
   content is fixed in `GUEST_PROBES` in `scripts/axes/onmigration_assessment/_constants.py`: `df -h`, `df -i`,
   `du -x --max-depth=1`, `lsof +L1`, `findmnt`, `stat`, `ls -la`, `wc -l`, and the
   Windows equivalents `Get-Volume`, `Get-PSDrive`, `Get-ChildItem`. One command per
   call, never chained.
3. **One low-risk reversible write**, `ecs:create-snapshot`, used only as snapshot
   before change.

### Mandatory gate on tiers 2 and 3

Before any guest command or snapshot, you MUST state in the conversation what will run,
which instance or disk it affects, that it changes nothing (tier 2) or that it creates a
billable snapshot (tier 3), and whether it is reversible. You MUST then obtain the
customer's confirmation, and that confirmation covers that single command or that single
disk only. `scripts/axes/onmigration_assessment/assess_migration.py` prints the notice and refuses to act until
`--confirm yes` is passed; never pass the flag yourself, and never reuse a confirmation
from an earlier step.

### ABSOLUTE PROHIBITION

Never generate, run, or recommend for automated execution any action outside the
allow-list in `references/ram-policies.md`. Specifically never: delete or clear files,
format a disk, run `fsck` or `e2fsck`, rebuild a boot loader, change a partition table,
resize a file system, replace an operating system, restart a service, stop or reboot an
instance, uninstall an agent, delete a snapshot or image, change a RAM policy, rewrite
network configuration, or issue any refund or order. Do not assemble `aliyun` CLI
commands by hand: call `scripts/axes/onmigration_assessment/assess_migration.py` only. If the customer asks for one
of these, explain the boundary and write out the manual step with its risk, including
the snapshot that must exist first.

If a requested command is not on the allow-list, refuse it and say why: report
`REFUSED` with the reason, then offer the manual step for the customer or operator to
run. Do not silently substitute a different command.

## Observability

Every call carries a User-Agent built by `build_user_agent` in `scripts/axes/onmigration_assessment/_cli.py`
from the template:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

where `{skill}` is this skill's name, and `{session-id}` is a 32-character hex
string (`uuid.uuid4().hex`, 32 lowercase hex digits), generated once per script
run and printed in the report header as `session_id`, so any call can be traced
back to one assessment.

## Credentials

The scripts rely on the default credential chain that the CLI already resolves: an
environment profile, `aliyun configure`, or an instance role. They never read, write,
print, or ask for an AccessKey pair, a key secret, or a security token, and all error
text passes through `mask_secrets` before it is shown. If a call is refused, report the
missing action from `references/ram-policies.md`; a refused call appears as `NoPermission`
or `ImplicitDeny`.

## Workflow

1. **Split at the door.** Is this a move onto Alibaba Cloud, a migration-tool failure, a
   mechanism question, or something else? Kernel `SMC-R` and RDMA wording is a different
   feature; see the homonym section of `references/onmigration-assessment__os-support.md` before going further.
2. **Collect the facts that decide everything.** Source kind (machine room, VMware,
   hyper-converged, physical, other cloud, ECS, image file), release, disk layout
   including local and encrypted disks, target region and account and family, what has to
   move, and any special constraint such as a smaller target disk or a source that can no
   longer be logged into.
3. **Read the cloud side** when the source or target is already an ECS instance.
4. **Read the guest side** when provisioned sizes are not enough: bytes in use for a
   shrink decision, mount layout for the migration scope, and existence of boot and
   network configuration. For a source that is not an ECS instance, either ask the
   customer to run the same allow-list command and paste the output, or have them
   register the machine as a managed host first; registration is their action, not this
   skill's.
5. **Report** the verdict, the candidate paths, the preconditions, the risks and cost
   items, and the evidence list. Anything that needs a change is written as a manual step.

## Commands

```
python3 scripts/axes/onmigration_assessment/assess_migration.py whoami
python3 scripts/axes/onmigration_assessment/assess_migration.py assess --region-id cn-hangzhou --instance-id i-xxx
python3 scripts/axes/onmigration_assessment/assess_migration.py assess --region-id cn-hangzhou --instance-id i-xxx --shrink --cross-account
python3 scripts/axes/onmigration_assessment/assess_migration.py source-inventory --region-id cn-hangzhou --instance-id i-xxx,i-yyy
python3 scripts/axes/onmigration_assessment/assess_migration.py target-availability --region-id cn-hangzhou --destination-resource InstanceType --instance-type ecs.g9i.large
python3 scripts/axes/onmigration_assessment/assess_migration.py guest-probe --region-id cn-hangzhou --instance-id i-xxx --probe df-h --os-type linux
python3 scripts/axes/onmigration_assessment/assess_migration.py guest-probe --region-id cn-hangzhou --instance-id i-xxx --probe stat --os-type linux --path /boot/grub2 --confirm yes
python3 scripts/axes/onmigration_assessment/assess_migration.py invocation-result --region-id cn-hangzhou --invoke-id t-xxx
python3 scripts/axes/onmigration_assessment/assess_migration.py protect-snapshot --region-id cn-hangzhou --disk-id d-xxx --confirm yes
python3 scripts/axes/onmigration_assessment/assess_migration.py route "the task has been stuck in Syncing for two hours"
```

`guest-probe` and `protect-snapshot` print the notice and stop without `--confirm yes`.
Run them once without the flag, relay the notice, and only re-run after the customer
agrees.

## Report contract

Transcribe the script's `Summary`, `STATUS`, and `NEXT_ACTION` lines as they are; the
script emits one of:

- `STATUS: OK` — every input needed for the verdict was obtained.
- `STATUS: DEGRADED` — a reading is missing, for example an instance that was not
  returned, an agent that is not online, or a source that cannot be reached. Say which
  item is missing and ask the customer for that reading instead of inferring it.
- `STATUS: FAIL` — nothing could be assessed, or a gated action was refused.

State every parameter the script filled in automatically, such as the region and the
account, and quote only numbers the API returned. An empty result is a finding, not a
licence to guess.

## Boundaries

| The case is really about | Where it goes |
| --- | --- |
| A disk resize that did not apply | `alibabacloud-ecs-disk-expand-diagnosis` |
| An instance stuck in a start or stop state, no migration behind it | `alibabacloud-ecs-instance-state-diagnosis` |
| Slow disk throughput | `alibabacloud-ecs-disk-io-diagnosis` |
| Space or file-count exhaustion needing cleanup | the capacity skill; here a capacity reading only feeds a sizing decision |
| An image or snapshot copy inside one account and region | `alibabacloud-ecs-disaster-recovery-image` |
| Executing an agreed website or server move step by step | `alibabacloud-ecs-site-migration-guide` |
| Installing a different distribution on the same machine | the system-disk replacement flow |
| Kernel `SMC-R`, `tcp2smc`, RDMA | not migration: explain, then point at the SMC-R guide |
| Money, filing, facility addresses, compensation | a human agent |

## Layout

```
SKILL.md
related_apis.yaml
scripts/axes/onmigration_assessment/assess_migration.py
scripts/axes/onmigration_assessment/_cli.py
scripts/axes/onmigration_assessment/_constants.py
scripts/axes/onmigration_assessment/sts_token.py
scripts/requirements.txt
references/ram-policies.md
references/onmigration-assessment__migration-paths.md
references/onmigration-assessment__os-support.md
references/onmigration-assessment__smc-errors.md
references/onmigration-assessment__post-migration-checks.md
```
