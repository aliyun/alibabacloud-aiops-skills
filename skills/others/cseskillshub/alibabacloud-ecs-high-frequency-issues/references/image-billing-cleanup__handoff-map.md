# Handoff Map

This skill answers three things: what an image or snapshot costs, what can safely
be cleaned up, and why an image blocks an unsubscription or a conversion.
Everything else is recognised, named, and handed off. Recognising a boundary is
part of the job - do not stretch an answer into a neighbouring scenario.

## Boundary table

| Recognised symptom | Where it goes | What this skill still answers |
| --- | --- | --- |
| Creating an image, copying it to another region, sharing it, or restoring an instance from it | `alibabacloud-ecs-disaster-recovery-image` | Whether the objects that workflow leaves behind are billed, and how to remove them |
| Cloning an instance, cross-region migration, rebuild from a custom image | `alibabacloud-ecs-disaster-recovery-image` | The charges of the temporary images and snapshots the migration produced |
| Disk or file system full, inode or file-count limit exhausted, a resize that did not take effect, a partition that did not grow | `area:disk-expand-diagnosis` | Whether a snapshot taken during that work is still billing |
| Instance will not start, has no system disk, or is stuck in an intermediate state | `area:instance-state-diagnosis`, or human support when a machine-level repair is needed | Nothing about the boot failure itself; only the image billing question if there is one |
| Slow disk IO, latency, throughput below the specification | `area:resource-bottleneck` | Nothing |
| Container Registry (ACR) images, `docker pull` or `docker push` failures, image repository access | Container Registry support - a different product family, not an ECS instance image | Nothing; say plainly that the word "image" means something else here |
| Recovering data from a released disk or instance, or data encrypted by ransomware | Human support, with the wording below | Nothing. No skill can recover it |
| Security intrusion, a compromised instance, malicious processes | Human support through the security channel | Nothing |
| Refund progress, voucher compensation, a shutdown complaint, invoices, contracts, purchase advice | Human support or the commercial channel | Nothing. Never promise an outcome |
| What a process inside the instance is doing - web server logs, application configuration, self-calls over a public address | Human support with the customer's authorisation | The billing attribution that pointed at that traffic |

## Wording to use

### Data that cannot be recovered

> "If the snapshots and images were already deleted, the data cannot be recovered
> - not by you, not by us, and not by any tool. If a backup still exists, we can
> look at what it contains and what restoring from it would cost. I will hand this
> to human support so the options are confirmed by an engineer."

Never suggest that a released disk, a deleted snapshot or encrypted data can be
brought back, and never imply that a paid service can.

### Out-of-scope scenario

> "That part is covered by <target skill or human support>. What I can tell you
> right now is what your images and snapshots cost and which of them are safe to
> remove."

Hand off with the evidence already collected: the account UID, the region, the
image IDs, their sources, and the verdicts from the inventory.

### Commercial requests

> "Refund amounts, vouchers and compensation are commercial decisions. I can give
> you the billing facts and the exact steps that were required, and I will hand
> the refund request to human support. I cannot promise an amount or an outcome."

### Container images

> "Container Registry images are a separate product from ECS instance images, so
> they are outside what I can check here. Container Registry support is the right
> channel. If you also have ECS custom images or snapshots you want to understand
> or clean up, I can do that now."

## Staying inside this scenario

Answer these directly, they are the core of this skill:

- whether a custom image is billed and how its snapshots are billed;
- whether a marketplace image fee is legitimate and where it appears in the bill;
- how to stop the charges of an image and its snapshots, in the right order;
- whether deleting an image or a snapshot affects running instances;
- which images are leftovers after a release, a transfer or a spot reclaim;
- whether a Windows image can be exported, and what exporting a Linux image
  costs;
- why an unsubscription or a conversion is refused because of the image, and the
  chain that unblocks it.

Do not answer these, hand off instead:

- how to create, copy, share, import or restore an image;
- how to grow a disk or a file system, or why a resize did not take effect;
- why an instance will not boot or behaves slowly;
- how much a refund will be, or whether a voucher will be granted;
- any unit price. Give the formula and the document from
  [billing-facts.md](image-billing-cleanup__billing-facts.md) and point to the customer's own bill.

## Related files

- [billing-facts.md](image-billing-cleanup__billing-facts.md) - the fact card and its sources.
- [unblock-runbook.md](image-billing-cleanup__unblock-runbook.md) - refusal texts and the fixed chain.
- [cleanup-checklist.md](image-billing-cleanup__cleanup-checklist.md) - verdicts, deletion order, wording.
- [ram-policies.md](ram-policies.md) - permission points and permission errors.
