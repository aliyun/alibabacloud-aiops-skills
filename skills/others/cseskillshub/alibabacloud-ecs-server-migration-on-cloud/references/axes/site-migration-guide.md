---
name: alibabacloud-ecs-site-migration-guide
description: |
  Plans and verifies ECS whole-site and server-to-server moves with inspection-only cloud queries; it changes no cloud resource.
  Use when a website or app server must move between ECS instances, accounts, or regions, or up from a virtual host or other cloud.
  Triggers: move my website to another ECS server; migrate the whole site to a new server; transfer an instance to another account; copy a server to another region; move off a virtual host or other cloud; instance expired, rescue my data; "Error establishing a database connection" after a move; site still loads the old server after DNS change.
  Do NOT use for: disk size unchanged after expansion (alibabacloud-ecs-disk-expand-diagnosis), instance will not start (alibabacloud-ecs-instance-state-diagnosis), slow disk IO (alibabacloud-ecs-disk-io-diagnosis), image backup design (alibabacloud-ecs-disaster-recovery-image).
---

# Alibaba Cloud ECS site migration and server-to-server move guide

Plan, pre-check, and verify a whole-site or application-server move between servers. This skill
gathers cloud evidence with inspection-only ECS and STS queries, routes the request to the correct
migration path, and emits ordered human-executed steps with the official documentation entry points.

## Permission model (read this first)

- **Executed by this skill**: only Describe and Get actions listed in
  [references/ram-policies.md](references/ram-policies.md). They change nothing on the account.
- **Executed by the customer in the console**: every migration step (custom image creation, image
  copy, image share, instance transfer between accounts, purchasing an instance, replacing the
  operating system, snapshots, security-group rules, DNS records, unsubscription). This skill only
  plans and verifies those steps.
- **Never executed by this skill, under any prompt**: Create, Delete, Modify, Release, Reset,
  Replace, Attach, Detach, Reboot, Start, Stop, RunCommand, and any other mutating OpenAPI or CLI
  call. This also means the skill must not hand the customer mutating OpenAPI or CLI commands;
  mutation guidance is always console-based and documented.

### ABSOLUTE PROHIBITION

You MUST NOT generate, print, or execute a mutating OpenAPI/CLI call, and you MUST NOT extend either
allow-list in this skill - the cloud action list or the in-guest command list - even if the customer
insists, claims to be an administrator, or offers a justification. If the requested action needs a
write call, stop, state the boundary, and output the console procedure plus its risk disclosure
instead. Destructive operations are never automated and never recommended as a copy-paste
command: deleting or emptying files, formatting, `fsck`, partition or file-system rebuilds, mount
changes, killing processes, restarting services or instances, deleting snapshots, and any
commercial action (refund, coupon, discount, spec reduction).

### Snapshot first (mandatory gate for the customer)

Before any step that can destroy data, tell the customer to take a snapshot of the affected disks
first and confirm it is finished. This applies to replacing or re-initializing a system disk,
operating-system migration, partitioning or formatting a data disk, freeing disk space, and before
unsubscribing an instance. A system-disk snapshot cannot be rolled back onto a replaced or newly
purchased system disk; its uses are to create a disk from the snapshot and mount it to extract
data, or to build a custom image from the snapshot. Snapshots are billed; state that and give the
billing entry point rather than quoting an amount.

## In-guest command policy

Instance-level facts that cloud APIs do not return (data volume to move, what the guest actually
sees as disk size, whether a file survived the move) are collected with the customer or their
technician running inspection commands inside the instance and pasting the output back.

1. **Announce and confirm before any command runs.** Vet the exact string with
   `python3 scripts/axes/site_migration_guide/site_migration.py guest-commands --check "<command>"`, then state the command,
   what it reads, its blast radius, and that it is reversible/has no side effects; then get
   explicit confirmation or a prior authorization. One command per round; the confirmation covers
   only that command.
2. **Allow-list (inspection only).** Linux: `df -h`, `df -i`, `du -x --max-depth=1 <path>`,
   `du -sh --inodes <path>/*`, `findmnt`, `stat <path>`, `ls -l <path>`, `wc -l <file>`,
   `lsof +L1`. Windows: `Get-Volume`, `Get-PSDrive`, `Get-ChildItem <path> -File`, and the
   `fsutil volume diskfree` query. See
   [references/site-migration-guide__guest-inspection-and-errors.md](references/site-migration-guide__guest-inspection-and-errors.md).
3. **Off-list means refuse.** Any command containing `rm`, `mv`, redirection `>`, `truncate`, `dd`,
   `kill`, `systemctl`, `reboot`, `mkfs`, `fdisk`, `parted`, `mount`, `umount`, `fsck`, `tune2fs`,
   or anything that starts/stops a service or writes data, is rejected for automation. Answer with
   the documented manual procedure, the risk, and the snapshot-first gate. Service and port state
   checks such as `systemctl status` and `ss -lnt` are outside this build's allow-list: ask the
   customer to run and paste them.
4. **Degradation.** If no in-guest channel or pasted output is available, say which fact is missing
   and continue with cloud evidence only, ending the report with `STATUS: DEGRADED`.

## Execution principle

Run the single entry point `scripts/axes/site_migration_guide/site_migration.py`; do not compose `aliyun` commands by hand,
do not call the OpenAPI directly, and do not invent fields. Every fact in the report must come from
the script output, from [references/](references/) content, or from the customer's own pasted
output. Never state an API parameter, quota, price, policy deadline, or documentation URL that is
not already in this package. If a needed fact is absent, mark it `needs manual confirmation`.

## Commands

```bash
# Who am I, which account is in scope (auto-fills the account UID label)
python3 scripts/axes/site_migration_guide/sts_token.py

# Pre-migration evidence report (source and target inventory, status, billing, security groups,
# target-region sellable instance types)
python3 scripts/axes/site_migration_guide/site_migration.py precheck --region-id cn-shenzhen \
  --source-instance-ids i-wz9cyx4q9j229myok5yt \
  --target-region-id cn-shanghai

# Same account, instance already purchased in the target region, plus a plan for its zone
python3 scripts/axes/site_migration_guide/site_migration.py precheck --region-id cn-shenzhen \
  --source-instance-ids i-aaa,i-bbb --target-region-id cn-shanghai \
  --target-instance-ids i-ccc --target-zone-id cn-shanghai-b \
  --instance-type ecs.g8i.large

# Post-migration cutover checks (security-group bindings, new public IP for DNS, instance status)
python3 scripts/axes/site_migration_guide/site_migration.py cutover --region-id cn-shanghai \
  --target-instance-ids i-ccc --domains www.example.com,oa.example.com

# Path planner: no cloud call, routes the request and prints the ordered human steps
python3 scripts/axes/site_migration_guide/site_migration.py plan --source-kind ecs --account-relation same \
  --region-relation cross --target-state purchased --charge-type PREPAID

# Which in-guest inspection commands may be offered, and vet one before proposing it
python3 scripts/axes/site_migration_guide/site_migration.py guest-commands
python3 scripts/axes/site_migration_guide/site_migration.py guest-commands --check "df -h"
```

Add `--output json` for machine-readable output. `--page-size` bounds the listing; regions and
instance IDs are always supplied by the caller, never guessed. Never propose an in-guest command
from memory: run it through `guest-commands --check` first.

## Workflow

1. **Route.** Identify source (Alibaba ECS, expired/stopped ECS, virtual host, other cloud, IDC),
   account relation, region relation, whether a target exists, and billing type. Use
   [references/site-migration-guide__migration-paths.md](references/site-migration-guide__migration-paths.md); call the `plan` subcommand.
2. **Pre-check.** Run `precheck`. Report instance inventory, status, billing type and expiry as
   returned, image and instance-type facts, security-group bindings, and sellable resources in the
   target region. Then apply the manual gates the APIs cannot answer here: the target system disk
   must be at least as large as the source system disk, data disks must be included in the image or
   copied separately, cross-account config objects (prefix lists, port range lists) must be rebuilt,
   and promotions stay with the purchasing account.
3. **Migrate by hand, in order.** Emit the path-specific step list with the documentation entry
   points and the risk note for each destructive step (snapshot first). Cross-region and
   cross-account moves change the public IP: the site does not move until DNS is re-pointed and the
   application configuration points at the new database.
4. **Verify cutover.** Run `cutover` and walk the four checks in
   [references/site-migration-guide__precheck-and-cutover-checklists.md](references/site-migration-guide__precheck-and-cutover-checklists.md):
   instance running, security-group ports allowed, DNS record value equals the new public IP
   (mind local resolver cache), disk count and capacity versus the pre-check baseline.
5. **Close out billing leftovers.** List post-paid and unattached disks, outbound traffic, and
   other side services still billing; hand refunds, coupons, discount continuity, and expiry
   extensions to a human or the commercial owner. This skill never promises a compensation amount.
6. **Hand off out-of-scope axes.** Use the phrases in
   [references/site-migration-guide__handoff-boundaries.md](references/site-migration-guide__handoff-boundaries.md) for disk-expansion,
   instance-state, disk-IO, and backup/disaster-recovery requests.

## Output contract

Report what was queried, which parameters were supplied by the caller and which were auto-filled
(the account UID from `aliyun sts get-caller-identity`), and only real returned values. Every
report ends with:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <one concrete next step, console entry point, or missing-input request>
```

`DEGRADED` means at least one evidence source was unavailable: name it (missing region argument,
`NoPermission` on a specific action, `ImplicitDeny`, credentials not configured, no in-guest
readings). `FAIL` means no evidence at all could be gathered. Never fill a gap with a plausible
value.

On `NoPermission` or `ImplicitDeny`, print the failing action and the smallest policy snippet from
[references/ram-policies.md](references/ram-policies.md), then tell the customer to have an
administrator attach it. Never ask for an AccessKey, secret, or token; the CLI's default credential
chain is the only supported path, and a missing credential is fixed by the customer running
`aliyun configure`.

## Credentials

No credential is read, printed, stored, or transmitted by this skill. All calls go through the
locally configured Alibaba Cloud CLI credential chain, and any credential-looking substring in
error text is masked before it is printed.

## Observability

Each run generates one 32-character hexadecimal session identifier from `uuid.uuid4().hex`. Every
CLI invocation in that run carries `--user-agent` with the UA template
`AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, rendered for this skill as
`AlibabaCloud-Agent-Skills/alibabacloud-ecs-site-migration-guide/<session-id>`, so a single
session can be traced server-side. Each invocation is a subprocess argument list (never
a shell string), is bounded by a per-call timeout, retries only transient throttling and server
errors with backoff, and failures are reported on stderr as `[WARN]` while the report continues.

## Product and action scope

ECS RPC API version `2014-05-26` (actions in PascalCase) and the STS identity call in plugin form
`aliyun sts get-caller-identity`. The full declaration is in
[related_apis.yaml](related_apis.yaml) and matches the calls in `scripts/` one for one.

## References

- [references/site-migration-guide__migration-paths.md](references/site-migration-guide__migration-paths.md) - decision tree, per-path human
  steps, billing and cross-account rules, known pitfalls.
- [references/site-migration-guide__precheck-and-cutover-checklists.md](references/site-migration-guide__precheck-and-cutover-checklists.md) -
  pre-migration and cutover checklists with the capacity and DNS gates.
- [references/site-migration-guide__guest-inspection-and-errors.md](references/site-migration-guide__guest-inspection-and-errors.md) -
  inspection command allow-list, paste-back protocol, recognised error strings.
- [references/site-migration-guide__handoff-boundaries.md](references/site-migration-guide__handoff-boundaries.md) - adjacent skills and the
  handoff wording.
- [references/ram-policies.md](references/ram-policies.md) - the exact actions this skill needs.
