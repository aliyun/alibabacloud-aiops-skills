# Data retention and recovery after a spot reclamation

Scope: what survives reclamation, the limits of each retention route, and the guidance
this skill gives **as steps for the customer to perform**. This skill never takes a
snapshot, never changes a disk attribute, and never attaches anything — it states the
rules, lists what is needed, and warns about impact.

Primary source:
`https://help.aliyun.com/zh/ecs/user-guide/preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md`
(the numbered-document form of the same content is
`https://help.aliyun.com/document_detail/439255.html`).
Creation-time options: `https://help.aliyun.com/zh/ecs/user-guide/create-a-spot-instance.md`.
Links were recorded from the tier evidence bundle and not re-fetched while packaging;
confirm before quoting option labels, which the console renames more often than rules.

## 1. Which losses apply depends on the interruption mode

- **Direct release mode** (the release-everything interruption mode): a spot instance's
  disks **go away with the instance**, and their data is deleted. Nothing in this skill can
  undo that. Therefore: **no snapshot, no retained disk, no image → the environment is
  gone.** This is a final answer, not a partial one. Give it once, clearly, then move to
  prevention.
- **Stop-charging mode** (`StopCharging`): the compute resources, the fixed public IP and
  the fixed bandwidth are reclaimed, while the **cloud disks, the elastic IP address and
  the snapshots are retained and keep being billed**. Nothing is lost — but the customer is
  still paying, and a later **restart can fail** when the zone/instance-type inventory is
  short or the floating market price rises above their bid. That restart failure is the
  usual follow-up question after this mode; see `ref-spot-mechanism.md` §3.
- So the first branch is **not** "was there a snapshot", it is **"which interruption mode
  does this instance use"**. Never assume direct release; never promise "the disk is
  definitely gone" before the mode is known.
- Retention is prepared **before** the interruption. A customer asking after the release
  can only be told what could have worked and what to do next time — plus, if they do
  hold an earlier snapshot or image, the rebuild route in §4.

## 2. Retention routes and what each one actually preserves

| Route | Preserves | Limits the customer must be told |
|---|---|---|
| Snapshot of the system disk | The content, restorable to a volume / usable for an image | Must exist beforehand; snapshots of retained disks are billed on their own (see `ref-billing-scope.md`) |
| Snapshot of a data disk | That disk's content | Same as above, per disk |
| Disk marked as **not** going away with the instance | The disk itself, after the instance is gone | A setting chosen at creation for the instance's disks; the disk keeps being charged while it sits there |
| Custom image | A bootable template | Requires a **system-disk** snapshot; an image cannot be made from a data-disk snapshot alone |
| External storage (object storage / file storage) | Data kept off the instance entirely | The application must write there; the local disk is still disposable |
| Keeping the instance's environment by hand (rebuild scripts, container images) | Reproducibility | The usual engineering answer for stateless tiers |

**The trap in every ticket of this type:** "keep the disk" is not "keep the system".

- A former **system disk** retained after reclamation can only be attached to a **new
  instance as a data disk**. It does not boot anything and does not put the old system
  back.
- The new instance and the retained disk must be in the **same zone**. Different zone →
  the attachment is not possible, which is why `ref-inventory-advisor.md` matters even
  for a customer who only asked about data.
- To get a bootable system back: a **system-disk snapshot** from before the release → an
  image or a volume from that snapshot → a new instance.

## 3. What this skill can and cannot see

| Question | Here | How |
|---|---|---|
| Does the instance still exist, in which zone, with which status and bidding mode | Yes | `DescribeInstances` / `DescribeInstanceStatus` |
| Was the billing type spot at all (so: is this even a reclamation) | Yes | same read |
| Which disks the customer retained, and their attributes | **No** | ask the customer, or route to the disk / snapshot tier |
| Which snapshots or images exist, their progress, their cost | **No** | the customer lists them in the console; the snapshot tier owns them |
| Whether a specific restore will fit a zone that still has spot stock | Partly | `DescribeAvailableResource` for the zone, then state the same-zone constraint |

Never guess a disk or snapshot inventory. If the customer needs the association made,
ask them to paste the disk ids and zone, then apply the rules above.

## 4. Guidance to give the customer (they perform it)

State the impact first, then the path. Both branches below are console work by the
customer; this skill only re-reads the read-only facts afterwards.

**A. Instance still running, wants to keep the data next time**

> Impact warning to state: reclamation is not scheduled and cannot be deferred on
> demand; anything not protected before the notice is lost, and the notice gives about
> five minutes. Protection settings apply to the disks that exist; a disk kept alive also
> keeps being billed.

1. Take a snapshot of each disk that matters (system disk first, since it is the one that
   gates image creation), or attach an automatic snapshot policy so this is not manual.
2. For disks that must outlive the instance, turn off the "release with the instance"
   behaviour on them.
3. Keep application data off the local disk: object storage, file storage, or a managed
   database. This is the only route that survives a whole-instance loss without a restore.
4. Optional, for a repeatable boot environment: make a custom image from the system-disk
   snapshot.
5. Confirm the recipient of interruption notices in the Message Center is a person who
   can act within the protection period — see `ref-spot-mechanism.md` §2.

**B. Instance already gone; customer holds an earlier snapshot or image**

1. From the image, or from a volume made from the system-disk snapshot, start a new
   instance. The charge is normal for whatever charging type the new instance uses; a
   new instance is not automatically a spot one, and if the workload needs stability the
   customer should choose a stable charging type.
2. Attach a retained former data disk, or a volume made from a data-disk snapshot, to a
   new instance **in the same zone** as that disk.
3. Attach a retained former **system disk** as a **data disk** only, then copy what was
   needed out of it; the running system comes from the new instance's own system disk.
4. This skill can re-check the zone of any still-visible instance with the read-only
   query, which is how the same-zone constraint gets verified rather than remembered.

**C. Instance already gone, nothing protected**

> Final answer: the environment and the data on disks that went with the instance cannot
> be recovered, by the customer, by this skill, or by support.

Then, and only then: prevention list from branch A, and — if the workload is
stateful — the suitability judgement in `ref-inventory-advisor.md` plus a stability
option the customer performs themselves. If the customer instead asserts platform
responsibility, that is a support-ticket conversation, not a technical one.

## 5. Public address and instance identity, when a spot instance is rebuilt

Frequently asked alongside retention, answered only where the rule is firm:

- A released instance's addresses are not preserved by this skill's reading; if an
  address must survive, the customer needs an address resource that is independent of the
  instance, and that resource and the instance must be in the same region. Detailed
  address work is outside this tier.
- A new instance gets a new private address; a retained disk does not move the old
  address with it.

Do not extend beyond this: whether a spot instance's public address can be swapped, and
whether a spot instance can be moved to another charging type, have **no evidence in this
bundle** — see `ref-handoff.md`.
