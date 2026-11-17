# Snapshot-first checklist

## The gate

Before guiding **any** cleanup, boot repair, rollback, forced operation, or stop/restart of
an abnormal instance: the customer snapshots **every disk involved** and waits until it
reaches 100%. Pure cloud queries and pure waiting against the time baseline need no
snapshot; the moment the guidance would change something, the snapshot comes first. This is
also the single most repeated action in this tier's real tickets, so it is not ceremony.

This skill never calls a snapshot API. It emits the steps below, the billing note, and the
risk notes, and then verifies the result by query.

## Steps the customer performs

1. Instance list `https://ecs.console.aliyun.com/server/region/<regionId>` -> select the
   instance -> create a snapshot for the system disk and each data disk involved.
2. Wait for all of them to reach 100% before continuing; a snapshot that is still in
   progress is not a rollback point.
3. Perform the operation.
4. Verify by re-running the diagnosis (status, then the guest reading that previously
   failed).
5. Delete the snapshots once the outcome is confirmed, because they keep billing.

Reference pages: create `https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot`
(document_detail/25455.html), billing
`https://help.aliyun.com/zh/ecs/product-overview/snapshots-1` (document_detail/56159.html),
delete `https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1`
(document_detail/128131.html), rollback
`https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot`.

## Billing note to state out loud

> Snapshots are billed separately, on the order of 0.12 CNY per GB-month -- roughly
> 0.4 CNY per day for a 100 GB disk. The official snapshot pricing page is authoritative,
> and the snapshots should be deleted once the operation is verified.

Skipping this is how a "why am I still being charged" ticket appears on top of the original
one. A snapshot that is referenced by a custom image cannot be deleted until the image is
removed first -- state that whenever a snapshot cleanup is part of the plan.

## Three risk notes to attach to every class-D step

1. A stop or restart briefly interrupts the running business.
2. A forced stop discards whatever is still in memory and cache; prefer letting the graceful
   shutdown flow finish.
3. Stop application writes before a rollback or re-initialization, and check autostart
   settings afterwards: after a rollback, programs stay stopped unless they were configured
   to start at boot, so "the website is down after the rollback" is expected and is a guest
   service matter, not a failed rollback.

## Post-recovery tail steps (customer-executed guidance)

- **atop**, so the next hang is attributable:
  `yum install atop -y && sed -i "s#600#30#g" /etc/sysconfig/atop && systemctl enable atop &&
  systemctl start atop` -- that is, `LOGINTERVAL=30` instead of the default 600 and
  `LOGGENERATIONS=7`. On Alibaba Cloud Linux, installing atop first needs `yum update` plus
  the matching EPEL release package. This is an installation and a service enablement: the
  customer runs it, never this skill. Without atop installed before the incident, which
  process saturated the host at the incident minute is unrecoverable -- say so instead of
  guessing.
  Docs: `https://help.aliyun.com/zh/ecs/use-cases/use-the-atop-tool-to-monitor-linux-system-metrics`,
  `https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools`,
  `https://help.aliyun.com/document_detail/101877.html`.
- **swap / virtual memory** as the mitigation when the evidence points at memory
  exhaustion: Linux
  `https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance`
  (see also `https://help.aliyun.com/knowledge_detail/42534.html`), Windows
  `https://help.aliyun.com/zh/ecs/support/how-to-configure-virtual-memory-for-windows-instances`.
  Configuring swap is a change the customer performs; the durable fix for a 1 GB instance is
  an instance-type change, which is a purchase decision and stays with the customer.
- **verify the recovery**: re-run `DescribeInstances` for the status, compare against the
  minute the customer performed the operation (their console operation records are
  authoritative), and close only when the state and the customer's own access test agree.

## Data-extraction detour

When the instance cannot be saved but the data matters, the sequence quoted in real tickets
is: custom image (packages system and data disks) or snapshots -> share the image to a test
account -> create a pay-as-you-go instance there -> or detach the disk and attach it to
another instance as a data disk to copy files out -> then release. Every step in that chain
is class D and irreversible if the wrong disk is selected, so state the disk choice twice
and tell the customer to stop and ask if anything is unclear. Docs:
`https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance`,
`https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image`,
`https://help.aliyun.com/document_detail/32317.html` (create a disk from a snapshot),
`https://help.aliyun.com/document_detail/25446.html` (attach a disk).
