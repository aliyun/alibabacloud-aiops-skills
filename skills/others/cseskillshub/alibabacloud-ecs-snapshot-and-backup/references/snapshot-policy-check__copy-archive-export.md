# Cross-region copy, archive tiering and export (capability C3)

Customer wording: "copy a snapshot to another region", "the copy has been running for
a day", "why does the copied snapshot cost twice", "archive a snapshot to save
money", "download the snapshot to my laptop".

Entry point: `python3 scripts/snapshot_policy_check.py lifecycle-inventory --regions <src>,<dst>`

## Copy (cross-region replication)

- Copy is triggered **per snapshot**, once each. Two snapshots in a city copied
  individually produce two copies; an automatic policy that creates N snapshots a day
  produces N copies a day (evidence: ticket 0001ZS3DD6, where the customer's 40 CNY a
  day was exactly this: two automatic snapshots per day, each copied).
- A copy bills in two places: traffic for the copy itself, plus standard snapshot
  storage in the **destination** region. The source snapshot keeps billing as well.
  State this before the customer clicks copy.
- Archived snapshots cannot be copied. If the plan is "archive then replicate", the
  plan does not work (evidence: ticket 0001ZS3DD6).
- Duration has no committed figure: it depends on shared cross-region capacity, the
  data volume and queue depth. Do not promise a completion time. Asynchronous
  replication time control is the product mechanism for latency commitments on disk
  replication, not on snapshot copy, so it does not answer this either.
- Task state can lag reality: an "archived for 8 days, nothing happened" report
  resolved on a page refresh (evidence: ticket 000BSRFHBW summary). Re-read state
  before concluding a task is stuck.
- Copy lineage is not derivable from the actions this version calls, so
  `lifecycle-inventory` lists what exists in each region supplied and says plainly
  that lineage is missing. Ask the customer which region is the destination, then
  compare inventories.

## Archive tiering

Pre-check every archive request before the customer performs it:

| Rule | Number | Consequence if ignored |
|---|---|---|
| A standard snapshot must be retained at least this long before it can be archived | 14 days | the archive request is refused |
| An archived snapshot has a minimum stay at the archive layer | 60 days (1,440 hours) | early deletion still pays the shortfall for the remaining hours |
| Archiving is manual | - | nothing archives itself; automatic policies keep producing standard snapshots |
| Archive and standard chains bill separately | - | the customer sees two lines where they expected one |
| Archived snapshots cannot be copied cross-region | - | the disaster-recovery plan silently breaks |

Evidence for all five: ticket 00094RC1SX (the agent's own numbers) and ticket
0001ZS3DD6 (copy limitation).

## Export and download: what is and is not possible

A snapshot cannot be downloaded directly. The only supported path is:

```
snapshot -> custom image -> export the image to OSS -> download from OSS
```

(evidence: ticket 0005PR939W, where this exact chain was given)

Boundary conditions that decide whether the path exists at all:

- A custom image can be built from a **system disk** snapshot chain; a data-disk
  snapshot alone cannot produce a custom image (evidence: tickets 00021RTH5D,
  0005PR939W summaries).
- Image export is limited: Linux images only, and encrypted images, marketplace
  images and Windows images are excluded (evidence: ticket 0009LRB5RD summary).
- `ExportSnapshot` sits behind a whitelist that **is not opened on request**. The
  error `InvalidUser.NotInWhiteList` means a hard product limit, not a form to fill.
  Manage the expectation and move to the image path (evidence: ticket 000CARSFMA,
  where support confirmed the whitelist cannot be applied for).
- To get at files rather than a whole disk, an alternative is to create a temporary
  disk from the snapshot, attach it to another instance, mount it and copy what is
  needed. That is a customer action with its own cost; the console flow is documented
  in `references/help-documents.md`.
- Cross-region movement of an *image* is a different action from copying a snapshot
  and has its own rules; do not blend the two explanations.

## Expected-cost table to hand over

| Action | Billed as |
|---|---|
| create snapshot | storage of the chain increment, source region |
| copy snapshot | copy traffic + storage of the copy, destination region |
| archive snapshot | archive-layer storage (lower rate) after a 60-day minimum stay |
| snapshot to custom image | the image's own snapshot storage; export adds OSS storage and egress |
| temp disk from snapshot | the disk itself while it exists |

Executing copy, archive, image creation or export belongs to the customer. This
skill pre-checks the conditions, prices the consequence, and then verifies the
result by querying the inventory again.
