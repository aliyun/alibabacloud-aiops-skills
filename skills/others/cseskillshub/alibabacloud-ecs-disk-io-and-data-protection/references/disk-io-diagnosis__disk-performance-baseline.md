# Disk performance ceilings and how to apply them

## 0. Status of the numbers in this file

Each figure carries a provenance tag. Read the tag before quoting the figure.

| Tag | Meaning | How to use |
|---|---|---|
| `formula-stated-in-source-material` | a capacity-derived rule taken from the material this tier was built from | compute with it, and show the arithmetic to the customer |
| `agent-stated-needs-doc-confirmation` | a figure a support engineer quoted, not yet re-checked against the published performance page | quote as "the ceiling for this configuration is X", and confirm against the block storage performance document before presenting it as a service commitment |
| `no-official-guidance` | the platform publishes no figure for this category | say exactly that. Never substitute a number from a similar-looking category |

The open item is deliberate: the authoritative per-category table has to be verified
against the block storage performance page listed in `help-topics.md`. Until that check is
recorded here, the second tag stays on every fixed number below.

## 1. The rule that settles most disputes

**A catalogue maximum is not a per-disk guarantee.** For a solid-tier volume the reachable
IOPS grows with capacity, so the headline number of the family is only attainable at a
capacity above a threshold.

Worked example, which is the single most common case:

```
category  = enterprise SSD, performance level 0
capacity  = 501 GiB
IOPS      = min(10000, 1800 + 12 x 501) = 7812
```

The customer comparing that disk against the family headline of 10000 will see a permanent
shortfall and conclude the disk is throttled. The family headline needs **684 GiB or more**
to become reachable at performance level 0. A peak of 1200 to 1600 IOPS on a 501 GiB volume
is 20 percent of its own ceiling, so the disk is nowhere near being limited, and an external
monitoring template that warns at a fixed number for all disks will keep firing for the
wrong reason.

## 2. Ceiling table

| Category | Level | IOPS ceiling | Throughput ceiling | Provenance | Notes |
|---|---|---|---|---|---|
| enterprise SSD | PL0 | `min(10000, 1800 + 12 x GiB)` | 180 MB/s stated ceiling | `formula-stated-in-source-material` for IOPS, `agent-stated-needs-doc-confirmation` otherwise | 684 GiB needed to reach 10000 IOPS. The per-capacity throughput rule is **not** verified here, so on a small volume treat 180 MB/s as an upper bound that may not be reachable |
| enterprise SSD | PL1 | 50000 | 350 MB/s | `agent-stated-needs-doc-confirmation` | The usual database complaint is a throughput touch at 350 MB/s while IOPS sits low |
| enterprise SSD | PL2 | not carried in this package | 750 MB/s | `agent-stated-needs-doc-confirmation` | Read the IOPS figure from the performance page before comparing IOPS |
| enterprise SSD | PL3 | not carried | not carried | `no-official-guidance` (as far as this package goes) | Do not guess; look it up or say it is unverified |
| ESSD AutoPL | n/a | provisioned, decoupled from capacity | provisioned, decoupled | `no-official-guidance` for a fixed number | Performance is configured per disk: baseline plus provisioned IOPS plus burst. Read that disk's own configuration instead of applying a table |
| ESSD regional-redundant | n/a | as published for the class | as published | `agent-stated-needs-doc-confirmation` | Appears mainly as an upgrade target from PL1 data disks |
| standard SSD / ultra disk / legacy | n/a | not derived from capacity here | not derived | `no-official-guidance` | Read the ceiling from the performance page |
| local SSD (previous generation) | n/a | up to 12000 random IOPS | not carried | `agent-stated-needs-doc-confirmation` | **Must** be labelled as previous-generation local SSD. It is not a local HDD figure |
| local HDD (newer generations) | n/a | none published | throughput only | `no-official-guidance` | Say there is no official IOPS guidance figure. Throughput SLA complaints can still be investigated |

A mis-citation of the local SSD row above, applied to a local HDD, was caught by the
customer on the spot. Generation labelling is not decoration.

## 3. The instance is the second bound

A disk never delivers more than its instance allows.

```
effective ceiling = min(disk ceiling, instance-type ceiling)
```

The scripts read the storage-related fields the instance-type response actually returns and
list them under their own names, because the mapping of those field names to an IOPS or
throughput bound is not confirmed inside this package. Where a confirmed instance bound is
known, pass it explicitly with `--instance-iops-ceiling` or `--instance-mbps-ceiling` and it
is applied as the minimum.

Consequence to state whenever the instance binds: upgrading the disk performance level
alone changes nothing. The instance type has to be raised in the same step. This is what a
"storage performance reached the specification limit" notice can mean when the disk itself
is not the limit.

## 4. Comparing a measurement with a ceiling

```
utilisation = measured peak / effective ceiling
```

| Utilisation | Verdict | Wording |
|---|---|---|
| at or above 95 percent | at ceiling | the disk reached its own limit; sustained occurrence justifies evaluating an upgrade, an isolated spike does not |
| 80 to 95 percent | near ceiling | possible limiting; only call it throttling when an alert names this disk and window |
| 50 to 80 percent | mid range | the ceiling does not explain the symptom |
| below 50 percent | well below | the disk was not throttled; look outside the disk |

Additional rules:

- One row per disk. A case with two disks can have one disk exceeding both limits and the
  other exceeding throughput only; merging them into "the disks are fine" or "the disks are
  throttled" is the error customers complain about most: the alert did not say which disk.
- Compare IOPS against the IOPS ceiling and throughput against the throughput ceiling. A
  throughput-bound workload shows a low IOPS figure that is not a defect.
- Units: throughput ceilings are in MB/s here. A monitoring series in bytes per second has
  to be divided by 1048576 first; the scripts do that when the metric is declared with the
  `bytes` kind.
- Latency is not a ceiling comparison. A 60 ms average latency at 300 MB/s on a disk whose
  throughput ceiling is 350 MB/s means the workload runs close to its limit; the direction to
  look is a higher performance class, not an application tuning knob.
- Report the sampling window with every number. A peak over 14 days and a peak over 1 hour
  answer different questions, and presenting several windows side by side is what lets a
  customer see that the disk is fine while memory has been at 90 percent for two weeks.
- Treat CPU spikes as spikes and averages separately; the maximum value on a CPU chart is
  usually not what matters, while for IOPS a momentary touch does matter.
- If the memory series is empty, say the memory dimension could not be judged rather than
  implying memory was healthy.

## 5. Upgrade directions and their limits

Only after the evidence shows a sustained ceiling touch:

- Performance level up, e.g. PL1 to PL2 or PL3, or to AutoPL when capacity and performance
  need to be configured separately.
- A PL1 data disk can also move to a regional-redundant class where that is offered.
- Subscription instances may raise the performance configuration but not lower it.
- A modification of a running volume may briefly affect its throughput without interrupting
  the service or risking data; perform it in a low-traffic period and take a snapshot first.
- If the instance binds the ceiling, change the instance type as well.

Fee, refund and downgrade questions are commercial and leave this skill immediately.
