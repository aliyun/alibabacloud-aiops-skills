---
name: alibabacloud-ecs-high-frequency-issues
area: image-billing-cleanup
description: |
  Explains ECS image and snapshot charges and finds what is safe to clean up: lists images with the instances referencing them, names the billing item behind a fee, routes console refusal text, and prints cleanup candidates with the deletion order. Never deletes an image or a snapshot; mutating actions are approval-gated.
  Use when image or snapshot fees are unclear, an image cannot be deleted, or the image blocks unsubscription or conversion.
  Triggers: image billing; snapshot keeps charging; cannot delete image; unsubscribe blocked by image; "please replace with a public image"; "marketplace image, conversion is not supported".
  Do NOT use: image create/copy/share/restore (alibabacloud-ecs-disaster-recovery-image); disk full or resize (area:disk-expand-diagnosis); instance will not start (area:instance-state-diagnosis); slow disk IO (area:resource-bottleneck); ACR container images.
---

# ECS Image Billing and Cleanup

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Answers three questions about Alibaba Cloud ECS images and snapshots, from
evidence instead of memory:

1. **What is actually being charged** - image versus snapshot versus block
   storage versus outbound traffic, and how the image and snapshot charges
   relate.
2. **What can safely be cleaned up** - which images are leftovers, which
   instance still references them, which snapshot must be deleted after its
   image, and what deletion does and does not affect.
3. **Why an unsubscription or a billing-method conversion is refused** - the
   image association behind the console refusal, and the fixed chain that
   unblocks it.

Operation type is **RO+G**: inventory queries plus approval-gated actions and
manual guidance. This skill never deletes an image, never deletes a snapshot,
never replaces an operating system and never submits an order.

## Execution Principle

- The ONLY way to reach Alibaba Cloud from this skill is
  `scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py` (and `scripts/areas/image_billing_cleanup/sts_token.py` for the
  identity pre-check). Both are invoked with `python3 <relative script path>`.
- Do NOT hand-build `aliyun` commands, do NOT call an OpenAPI action directly,
  do NOT bypass the entry script, and do NOT paste a customer-supplied command
  string into a guest invocation. The entry script refuses any action outside
  its built-in whitelist before a subprocess starts.
- Every statement in the final answer must come from script output, from the
  `references/` knowledge files, or from the customer's own words. If a query
  returns nothing or fails, say so as a limitation. Never fill a gap from
  memory, and never invent an image id, a snapshot id, a price or a document
  link.
- Modes `scope` and `faq` make no cloud call at all and are always safe to run.

## Permission Model and Approval Gates

Three classes of action, enforced by the script and by the rules below.

### Class 1 - automatic inventory queries

`ecs:DescribeInstances`, `ecs:DescribeImages`, `ecs:DescribeDisks`,
`ecs:DescribeInvocations`, `sts:GetCallerIdentity`. These change nothing and
run without asking. See [references/ram-policies.md](references/ram-policies.md)
for the exact permission points.

### Class 2 - approval-gated actions (MUST tell, then confirm)

| Gated action | What it does | Script mode |
| --- | --- | --- |
| `CreateSnapshot` (Class B — no declared grant) | Creates ONE backup snapshot of ONE disk | `snapshot-backup` |
| `RunCommand` (Class B — no declared grant) | Delivers ONE whitelisted, non-mutating inspection command inside the instance | `guest-check` |
| local file write | Writes the cleanup-candidate list to a brand-new file in the system temporary directory | `inventory --save-list` |

MUST do all of the following **before** adding `--confirm`:

1. Tell the customer the exact action or command text that will run.
2. Tell them the blast radius (which single resource, which single instance).
3. Tell them whether it is reversible, and what it will cost - a new snapshot is
   billable storage.
4. Get an explicit approval for THAT action. One approval covers ONE action and
   ONE invocation; it never carries over to the next command, the next disk or
   the next run.

Without `--confirm` the script prints the plan, changes nothing and returns
`STATUS: DEGRADED`. That is the intended behaviour: relay the plan, ask, and
only then re-run with `--confirm`.

**Snapshot first.** Before any cleanup or space-releasing decision, a current
backup of every disk whose content still matters must exist - either created
through the gated `snapshot-backup` mode or by the customer in the console.
Pure inventory and pure billing answers need no snapshot.

### Class 3 - ABSOLUTE PROHIBITION (never executed, only described)

This skill MUST NOT generate, invoke, schedule, or tell another agent to invoke
any of the following, and MUST NOT hand the customer a command that performs
them:

- deleting an image or a snapshot (`DeleteImage`, `DeleteSnapshot` and any
  equivalent), revoking or granting an image share;
- replacing the operating system or a system disk, re-initializing a disk,
  formatting, re-partitioning, resizing;
- releasing, stopping, starting, rebooting or renewing an instance;
- unsubscribing, downgrading, refunding, applying vouchers or any other billing
  or commercial action;
- any guest command outside the whitelist below, and any command built from
  customer text.

These stay **manual console steps for the customer**, printed with their risk
and their irreversibility. When the customer asks this skill to perform one,
refuse, explain the boundary, print the manual steps from
[references/image-billing-cleanup__unblock-runbook.md](references/image-billing-cleanup__unblock-runbook.md) or
[references/image-billing-cleanup__cleanup-checklist.md](references/image-billing-cleanup__cleanup-checklist.md), and point to
the console entry.

### Guest inspection command whitelist

Only these keys can be delivered, one per approval. The command text is fixed
in `scripts/areas/image_billing_cleanup/_constants.py`; the customer cannot supply it.

| Key | OS | Command | Answers |
| --- | --- | --- | --- |
| `disk-usage` | linux | `df -h` | used and free space per file system |
| `file-count-usage` | linux | `df -i` | whether the inode / file-count limit is exhausted |
| `mount-layout` | linux | `findmnt` | which disk and partition back each mount point |
| `deleted-open-files` | linux | `lsof +L1` | space still held by deleted-but-open files |
| `path-size` | linux | `du -x --max-depth=1 <path>` | size of one directory tree, to size a backup |
| `windows-volume-usage` | windows | `Get-Volume` | used and free space per NTFS volume |
| `windows-drive-usage` | windows | `Get-PSDrive` | used and free space per drive letter |

Guest readings are an **auxiliary** path in this scenario: the main judgements
(image source, reference relationships, deletion order, billing wording) are all
answered from cloud inventory plus the reference documents. Use a guest command
only when the decision needs the real used space inside the file system, for
example before deciding whether a snapshot is worth keeping or how large a
backup will be. Windows has no `df -i` equivalent, so no file-count conclusion
is drawn for Windows instances.

## Workflow

### Step 0 - confirm the account

```
python3 scripts/areas/image_billing_cleanup/sts_token.py
```

Image and snapshot charges are per account, and a cross-account transfer leaves
them in the SOURCE account, so state the UID the report covers. On failure the
helper prints the corrective step; never ask the customer for a credential.

### Step 1 - route the question

| Customer question | Mode |
| --- | --- |
| Unsubscription or conversion refused, with or without the console text | `unblock-check` |
| What is this charge, does the image cost money, how do I stop it | `faq` |
| Can I delete this image, what is safe to clean up, still charged after release | `inventory` |
| Is there data left I need, how big is the backup | `guest-check` (gated) |
| Read the output of a command already delivered | `invocation-result` |
| Create the approved backup snapshot before a cleanup | `snapshot-backup` (gated) |
| Which actions does this skill support at all | `scope` |
| Another symptom area (disk full, instance will not start, slow IO, recovery) | hand off, see [references/image-billing-cleanup__handoff-map.md](references/image-billing-cleanup__handoff-map.md) |

### Step 2 - run the mode

```
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py scope
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py faq --topic image-vs-snapshot-billing
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py unblock-check --region cn-hangzhou --instance-id i-xxxxxxxx
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py inventory --region cn-hangzhou
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py guest-check --region cn-hangzhou --instance-id i-xxxxxxxx --command disk-usage
python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py snapshot-backup --region cn-hangzhou --disk-id d-xxxxxxxx
```

Flags: `--profile` and `--json` are accepted by every mode. `--region` is
required by every cloud mode and optional for `faq` (where it only shapes the
suggested next step). `--confirm` exists only on the three gated modes -
`inventory` (with `--save-list`), `guest-check` and `snapshot-backup`; passing it
anywhere else is an error. Remaining flags are per mode: `--message` or
`--message-branch` for `unblock-check`, `--save-list` for `inventory`,
`--command` and `--path` for `guest-check`, `--invoke-id` for
`invocation-result`, `--disk-id`, `--instance-id` and `--snapshot-name` for
`snapshot-backup`.

`--region` is never guessed silently. Take it from the customer or the ticket;
if it had to be assumed, say which region the report covers and that image,
snapshot and instance objects are region-scoped, so the inventory must be
repeated per region.

When the customer quotes a console refusal in a language other than English, do
not translate it into `--message`; pick the matching `--message-branch` key
instead. The five keys and their meanings are listed by
`python3 scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py scope` and in
[references/image-billing-cleanup__unblock-runbook.md](references/image-billing-cleanup__unblock-runbook.md).

### Step 3 - report

Follow the output contract below, then work through the matching reference file
with the customer.

## API Whitelist

| Action | RAM action | Class | Used for |
| --- | --- | --- | --- |
| `DescribeInstances` | `ecs:DescribeInstances` | automatic | instance list, billing method, the image each instance runs |
| `DescribeImages` | `ecs:DescribeImages` | automatic | image source, status, size, the snapshots behind it, reference check |
| `DescribeDisks` | `ecs:DescribeDisks` | automatic | the disk a backup snapshot will be taken from |
| `DescribeInvocations` | `ecs:DescribeInvocations` | automatic | output of an already delivered inspection command |
| `GetCallerIdentity` | `sts:GetCallerIdentity` | automatic | the account UID the report covers |
| `RunCommand` (Class B — no declared grant) | dispatched via `aliyun ecs run-command ...` (CLI plugin mode); the real RAM action name is assembled only on customer opt-in, by their own admin | gated | one whitelisted inspection command |
| `CreateSnapshot` (Class B — no declared grant) | bare API operation name here; the RAM action is paired with the service prefix only when the customer opts in | gated | the one mandatory pre-cleanup backup snapshot |

Nothing outside this table may be called. Snapshot object-level details
(per-snapshot capacity, retention policy, exact fee) and bill amounts are NOT
queryable through this whitelist: point the customer to the console snapshots
page and to the bill details instead, as described in
[references/image-billing-cleanup__billing-facts.md](references/image-billing-cleanup__billing-facts.md).

## Observability

Every OpenAPI call carries a User-Agent so one diagnosis can be correlated.
Each call appends `--user-agent` filled from this template (`{skill}` is this
skill's name, `area:image-billing-cleanup`):

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

`{session-id}` is a 32-character hex string (`uuid.uuid4().hex`) generated once
per script run, printed to stderr as `[_cli] session-id: <session-id>`, and
returned in the `--json` envelope as `session_id` together with the full
`user_agent`. Quote the session id when a run has to be handed to human support.

Timeouts and retries are fixed in the shared layer: 60 seconds per call, a
5-second poll interval with a 120-second budget while waiting for a delivered
command, and up to 3 attempts with a 2s/4s backoff for transient failures
(throttling, 5xx, timeout). A non-transient failure is reported immediately and
never retried blindly.

## Credentials and Permission Errors

- Authentication comes only from the Alibaba Cloud CLI default credential chain.
  This skill never asks for, reads, stores, prints, caches or forwards an
  AccessKey ID or Secret, and never writes a credential cache file. Error text
  is masked before it can reach the report.
- If credentials are missing, the guidance is `aliyun sts get-caller-identity` - nothing else.
- If a call is rejected for permission reasons, the surfaced code is
  `NoPermission` or `ImplicitDeny`. Report which single action is missing and
  point to the minimal policy snippet in
  [references/ram-policies.md](references/ram-policies.md). Never describe a
  permission rejection as a product defect, and never widen the request to work
  around it.

## Output Contract

Every run of the entry script ends with:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <one concrete next step>
```

- `OK` - the question was answered from returned data or built-in knowledge.
- `DEGRADED` - answered with a stated limitation: a refused inventory source, an
  unmatched console text, a missing snapshot detail, a pending guest invocation,
  or a gated action that was planned but not approved.
- `FAIL` - the evidence needed for the conclusion could not be obtained.

When relaying a result:

1. Report the script `Summary` and `STATUS` faithfully; do not upgrade a
   `DEGRADED` or `FAIL` run into a confident answer.
2. Quote only values that were actually returned, and name the account UID and
   region the report covers, including any parameter that had to be assumed.
3. List every limitation the run printed under `Limitations of this run`.
4. Never quote a unit price. Give the billing formula (stored capacity x storage
   duration, no free quota, not per image count) and the official document, as
   written in [references/image-billing-cleanup__billing-facts.md](references/image-billing-cleanup__billing-facts.md).
5. Attach the irreversibility warning to every deletion instruction: a deleted
   image or snapshot cannot be recovered, and deleting an image alone does not
   stop the charges of its snapshots.
6. End with the single `NEXT_ACTION`. Refund, voucher, compensation, invoice and
   contract requests go to human support with no promise of an outcome.

## Boundaries and Handoff

Stay inside this scenario. Recognise, then hand off:

| Recognised symptom | Where it goes |
| --- | --- |
| Copying, sharing, restoring or exporting an image as a workflow | `alibabacloud-ecs-disaster-recovery-image` |
| Disk or file system full, inode exhausted, resize not effective | `area:disk-expand-diagnosis` |
| Instance will not start, no system disk, stuck in an intermediate state | `area:instance-state-diagnosis` |
| Slow disk IO, performance below the specification | `area:resource-bottleneck` |
| Container registry (ACR) or `docker pull` images | not an ECS instance image; container registry support |
| Data recovery with no snapshot and no image left | nobody can recover it; use the unified wording in [references/image-billing-cleanup__handoff-map.md](references/image-billing-cleanup__handoff-map.md) |
| Refund, voucher, compensation, shutdown complaint, contract | human support or the commercial channel |

This skill still answers the billing and cleanup part of a handed-off case: what
the objects left behind by a recovery, a migration or a clone cost, and how to
remove them. Export limits and export fees are answered here, not handed off - a
Windows image cannot be exported because of licensing, and a Linux export depends
on OSS and therefore costs OSS storage and download traffic. See
[references/image-billing-cleanup__billing-facts.md](references/image-billing-cleanup__billing-facts.md).

## References

- [references/ram-policies.md](references/ram-policies.md) - exact permission
  points, minimal policy snippets, permission-error wording.
- [references/image-billing-cleanup__billing-facts.md](references/image-billing-cleanup__billing-facts.md) - the billing fact
  card: image versus snapshot, fee attribution, export limits, price policy.
- [references/image-billing-cleanup__unblock-runbook.md](references/image-billing-cleanup__unblock-runbook.md) - console
  refusal texts, branch keys, the fixed unblock chain.
- [references/image-billing-cleanup__cleanup-checklist.md](references/image-billing-cleanup__cleanup-checklist.md) - cleanup
  verdicts, deletion order, irreversibility wording.
- [references/image-billing-cleanup__handoff-map.md](references/image-billing-cleanup__handoff-map.md) - boundary table and
  handoff wording.
- `scripts/areas/image_billing_cleanup/ecs_image_billing_cleanup.py` - single entry point; `scope` prints
  the live whitelist, the gates and the deletion order.
- `scripts/areas/image_billing_cleanup/sts_token.py` - caller identity pre-check.
- `scripts/areas/image_billing_cleanup/_cli.py`, `scripts/areas/image_billing_cleanup/_constants.py` - shared invocation layer and
  embedded knowledge; `scripts/requirements.txt` - standard library only.
