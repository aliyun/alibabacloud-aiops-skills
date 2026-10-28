# Status reading and completion criteria

Knowledge cross-checked against the official documentation on **2026-07-31**.

This file maps what the read-only APIs actually return onto the customer-facing
answer. The governing rule is the one customers most often get wrong:

> A snapshot is finished when its **upload reaches 100%**, i.e. when `Status`
> becomes `accomplished`. Anything still reading "creating" or "uploading to OSS"
> is **not** a usable backup, however long it has been running.

Never report "done" from the presence of a record. Report it from the status.

## DescribeSnapshots - status values

`ecs:DescribeSnapshots`, product `ecs`, version `2014-05-26`. Records arrive
under `Snapshots.Snapshot`.

| `Status` | Meaning | Answer to give |
|---|---|---|
| `progressing` | Still being created / uploaded to OSS | **Not complete.** The snapshot cannot be relied on for rollback yet. Expected to last a while on a first run - see the full-versus-incremental section |
| `accomplished` | Upload finished | **Complete and usable.** This is the only status that supports "your backup is ready" |
| `failed` | Creation failed | Not usable. Do not restate a cause the API did not report; tell the customer to retry and, if it repeats, to open a ticket with the snapshot id |
| anything else / absent | Value this skill does not map | Report the raw value verbatim and say it is not recognised. **Never** translate an unlisted value by guessing what it probably means |

If a progress-style field is present in the response, the report echoes it; when
it is absent, the report says the API did not return it rather than assuming 0%
or 100%. `Status` alone is the authoritative completion signal.

Other fields the report consumes, all read as facts:

| Field | Use |
|---|---|
| `SnapshotId`, `SnapshotName` | Identify the record for the customer |
| `CreationTime` | Line disks up: identical values across distinct source disks are the observable signature of one group operation |
| `SourceDiskId`, `SourceDiskType` | Tie each snapshot to its disk, and distinguish system from data |
| `Category` | Report `standard` versus `archive` as returned; never infer storage tier from region |
| `Usage` | Report as returned when the customer asks whether a snapshot is already tied to an image |

## Telling a group apart from independent snapshots

No read operation verified for this skill returns the group object itself, and it
is not confirmed that the snapshot records carry a group identifier. So:

1. Read the snapshots for the instance (or for each disk in scope).
2. Compare `CreationTime` across the distinct source disks.
3. **One shared value** across two or more disks is consistent with a single
   group operation.
4. **Several different values** means these are independent snapshots and are
   **not** a point-in-time consistent set - which is exactly what per-disk
   automatic policies produce, even when several disks share the same policy.
5. State the matching as inference, and ask the customer to confirm the group
   entry in the console. Say "the API did not return the group object"; do not
   say "you have no group".

## Duration: full versus incremental

* The first snapshot of a disk is **full**: it copies everything, and it is slow.
* Later snapshots are **incremental**: only changed blocks are copied, and they
  are markedly faster.
* One measured reference point from a real case: roughly **30 minutes for 6
  disks** on a first run. Quote it as an example of what a first run can look
  like - never as a target, an expected time, or a timeout.
* Real duration depends on data volume and change rate, neither of which this
  skill can measure. If the customer asks "is it normal to still be waiting",
  answer with the full-versus-incremental rule plus the actual status, and say
  whether that status is still progressing.

## Region isolation: the first thing to rule out

Instances, disks and snapshots are isolated per region. An empty result is
therefore ambiguous, and the report must disambiguate it rather than reporting a
missing resource:

1. Ask which region the customer's console shows, and re-run with that
   `--region-id`.
2. Only conclude "no records in this region" once the region is confirmed.
3. The skill reads one region per invocation; to cover several regions, run it
   once per region and keep the evidence separate.

## DescribeInstances - instance state

`ecs:DescribeInstances`, product `ecs`, version `2014-05-26`. Records arrive
under `Instances.Instance`.

Relevant to this tier mainly as the rollback precondition:

| `Status` | Relevance here |
|---|---|
| `Stopped` | Satisfies the documented stop-before-rollback precondition |
| `Running` | Rollback needs the instance stopped first; take a fresh backup of the current state before stopping |
| `Pending`, `Starting`, `Stopping` | Transitional; report the value and say the state is mid-change rather than asserting a precondition is met |
| absent / other | Report verbatim and mark the precondition unverified |

Reading the state is not changing it. This skill never stops, starts or restarts
an instance; stopping and restarting are customer console actions.

## DescribeDisks - disk state and category

`ecs:DescribeDisks`, product `ecs`, version `2014-05-26`. Records arrive under
`Disks.Disk`.

* `Category` decides the ESSD-family element (see
  [precheck-checklist.md](precheck-checklist.md) A3). Categories missing from the
  embedded table are reported as unknown, not forced into the nearest bucket.
* `DiskType` distinguishes system from data disks.
* `Size` and `Status` are reported per disk as facts.
* `EnableAutomatedSnapshotPolicy` and `AutoSnapshotPolicyId` show that policies
  are associated **per disk** - the evidence behind the "an automatic policy
  cannot keep several disks consistent" answer.

## Failed and partial reads

A read that fails does not stop the run, and never becomes a silent gap:

* Each failure prints a `[WARN]` line naming the action that failed.
* The affected element is listed under **Limitations** as "not verified from the
  API", and the answer for it falls back to the documented rule wording.
* Overall `STATUS` becomes `DEGRADED` when usable evidence remains, `FAIL` when
  none does.
* A `NoPermission` or `ImplicitDeny` refusal additionally names the single
  missing RAM action and the minimal policy to attach - see
  [ram-policies.md](ram-policies.md).
* Transient failures (throttling, 5xx, timeout) are retried inside the shared CLI
  layer with bounded backoff; anything else is surfaced, not retried.
