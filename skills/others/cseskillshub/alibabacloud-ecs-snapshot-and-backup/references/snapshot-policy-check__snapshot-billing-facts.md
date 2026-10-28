# Snapshot billing facts (capability C4)

Customer wording: "why am I charged for snapshots I did not create", "how do I stop
snapshot charges", "does keeping a snapshot 15 days mean 15 days of billing", "how
much will this cost".

Entry point: `python3 scripts/snapshot_policy_check.py lifecycle-inventory --regions <r1>,<r2>`

## Four statements that resolve most of these

1. **The policy is free; the snapshots are billed.** A policy costs nothing on its
   own, and an unbound `default_policy` bills nothing at all (evidence: tickets
   0001FRZPLN, 0009LR8YJD, 000AWRLY1J).
2. **Deleting a policy does not stop billing.** The snapshots already produced stay
   and keep billing until they are deleted or their retention lapses (evidence:
   tickets 000AWRLY1J, 000G2RJ8LG, 00069RU80Y).
3. **Billed capacity is the snapshot chain of a disk, not its size label.** Per disk
   the chain total is the first full snapshot plus the incremental parts of every
   later snapshot. If some snapshots are archived, the disk has two chains - one
   standard, one archived - and each bills on its own layer (evidence: ticket
   00094RC1SX, where the agent gave exactly this formula).
4. **Duration is from creation until deletion.** Retention days end the life and the
   billing of that snapshot; a snapshot with no retention bills forever, including
   after the instance is released, because manually created snapshots survive the
   instance (evidence: tickets 00094RC1SX, 0005PR939W).

## Contradiction to avoid repeating

In one thread the agent first said a snapshot's size is not the disk's capacity
(first full, then incremental) and later said the final size of each snapshot equals
the disk's capacity (evidence: ticket 0001FRZPLN, internal contradiction). The chain
formula from ticket 00094RC1SX is the one to use: it is the model the console's
"snapshot chain capacity" view and the bill are both built on. Never present a
per-snapshot size as the billed number.

## Order-of-magnitude estimate

About 0.12 CNY per GB per month for mainland standard snapshot storage, which is how
support sized a 150 GB disk's backup at roughly 0.6 CNY per day (evidence: ticket
000CART2PA, where the source figure came from the console pricing note; the constant
lives in `scripts/_constants.py`). Treat any figure computed from
`SourceDiskSize` as an upper bound: it is the disk's size, not the chain total.
`lifecycle-inventory` labels it that way on purpose.

## Deduction rules worth stating

- Only a standard-LRS storage resource package offsets snapshot storage; other
  package types do not (evidence: ticket 000GJRTG60 branch).
- Within one region a package cannot be stacked; across regions packages can be
  combined (evidence: tickets 00069RU80Y, 000AWRLY1J).
- Purchasing, refunding and offsetting charges happens in the Billing and Cost
  Center. This skill produces the evidence list (which snapshots, which disks, which
  region, what retention) and stops there; it never quotes a bill as authoritative.

## Stop-billing checklist, in the order that works

1. Shorten or unbind automatic snapshot policies, or delete them last.
2. Delete the automatic snapshots those policies produced.
3. Delete manually created snapshots, including ones inherited from a released
   instance.
4. Delete custom images that still reference remaining snapshots.
5. Re-run `lifecycle-inventory` to confirm the list is empty, and remember the
   current month's usage already accrued.

Each step is executed by the customer in the console. Snapshot and image deletion is
irreversible and is never automated by this skill.
