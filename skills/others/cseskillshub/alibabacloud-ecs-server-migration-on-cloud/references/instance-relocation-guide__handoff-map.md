# Hand-off map

The trigger wording of this tier is broad - "move", "change", "transfer",
"zone", "region", "server", "disk", "website" - so many requests that are not
relocation decisions arrive with exactly these words. Recognise them early and
send them on, with the read-only evidence already collected.

Only a few sibling skills are named with confidence in this package:
`alibabacloud-ecs-disaster-recovery-image`, `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis`,
`alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` and `alibabacloud-ecs-high-frequency-issues: resource-bottleneck`.
Every other destination is written generically as "another specialised
capability" or "manual support" until its naming is confirmed; do not invent a
skill name in a customer reply.

## Hand-off table

| Symptom that arrives | Belongs to | Reply shape |
| --- | --- | --- |
| Building, copying, sharing or restoring an image; recovering a service from an image | `alibabacloud-ecs-disaster-recovery-image` | This skill decides whether a move is possible and which path applies; the image lifecycle itself belongs there |
| A disk expansion that did not take effect, a partition that was not extended | `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis` | Hand over after noting the instance and zone facts |
| An instance that will not start, or is stuck between states | `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` | Report the queried state, then hand over; a restart is not this skill's action |
| Slow disk IO, performance below the instance type | `alibabacloud-ecs-high-frequency-issues: resource-bottleneck` | Hand over; the relocation path is not the cause to chase |
| Free space or inode usage inside the guest | another specialised capability | No in-guest command is run here; return a manual checklist instead |
| Unsubscription, refund, residual value, renewal pricing, coupon or extension requests | manual commercial review | State that remaining time cannot be transferred, link the unsubscription rules, promise nothing |
| Stock sold out during a purchase, an order that cannot be paid | another specialised capability | The read-only capacity query can confirm "no capacity reported", then hand over |
| Actually executing an operating-system replacement | another specialised capability | This skill states the constraints and the snapshot-first rule only |
| Private connectivity between an instance and a managed database | another specialised capability | Do not be misled by a region word in the question; that is a network symptom |
| Private IP has reverse DNS or route dependencies that must be preserved across the move | the customer's VPC/PrivateZone or DNS owner, or manual support | This area reports the dependency as a blocker and which addresses change; editing or carrying the reverse record/route is outside it |
| An instance that the console does not list | another specialised capability | The read-only query can show whether the instance exists in that region, which is often the whole answer |
| A Simple Application Server that was bought by mistake | another specialised capability | Product line confusion; hand over with the observed product |
| The physical address of the machine room | manual support | No read-only query exists; do not guess a city |
| Whole-site or cross-cloud application migration | another specialised capability | Application and DNS cut-over planning is a different scope |
| Changing the deployment set of an instance | not a relocation | Placement change, different rules |
| A specification change inside the same zone | not a relocation | Same-zone change; only cross-zone moves are handled here |

## How a hand-off is worded

1. State what was already established by the read-only queries, so the customer
   does not repeat it.
2. State plainly which part of the request is outside this skill and why.
3. Give the destination: the named sibling skill when the table names one,
   otherwise "another specialised capability" or "manual support", plus the
   console entry that is always safe to offer.
4. Never execute the change as a substitute for the hand-off, and never quote an
   internal queue identifier in the reply.

## Example replies

Cross-account clone request that turns out to be about image permissions:

> The source instance is in region A, zone a, type B, prepaid until a date; it is
> still running normally. Sharing an image to another account and the permissions
> around it are handled by the image capability rather than here. What this skill
> confirms for you is the path and the size floor: the target system disk must be
> at least as large as the source image.

Refund request attached to a retirement notice:

> The technical side is yours to run: the move is not done for you, and the
> retained period is not guaranteed service. The money side, including any
> transfer of remaining time, is decided by commercial review; this skill cannot
> promise an amount. The unsubscription rules are linked in the migration paths
> reference.

Instance "missing" from the console while a zone change is planned:

> The read-only query does return it: region A, zone a, running. That points at a
> console or filter issue rather than a relocation issue, which is a different
> capability.
