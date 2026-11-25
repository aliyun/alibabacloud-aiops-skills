---
name: alibabacloud-ecs-disk-replication-dr-guide
description: |
  Read-only evidence check and guidance for ECS disk disaster recovery: disk async replication pairs,
  consistency replication groups, ESSD zone-redundant regional disks, snapshot cross-region backup.
  Reads instance, disk and snapshot facts per region with Describe APIs; changes no cloud resource.
  Use when a customer asks whether an ECS disk or a single instance has automatic failover, how to set
  up, stop or remove a replication pair, or whether replication caused a charge.
  Triggers:
  - "my ECS disk async replication is not working"
  - "failover my ECS disk to another region"
  - "does a single ECS instance have automatic failover"
  - "ECS snapshot cross-region backup"
  - "remove my disk replication pair"
  - "traffic fee caused by disaster recovery backup"
  - "NoPermission"
  Do NOT use for snapshot lifecycle, disk IO performance, security group rules or billing; hand off
  to the snapshot, disk performance, access blocking and billing skills.
---

# ECS Disk Replication and Disaster Recovery Guide

Customer-facing scenario name: **ECS disk disaster recovery and async replication guide**
(read-only posture check plus step-by-step self-service guidance for cloud disk DR).

This skill answers one question family: *what disk-level disaster recovery does my ECS setup
actually have, and what do I do next.* It is a **read-only, guidance-type (RO_GUIDE)** skill:

1. **Read** cloud-side facts (instances, disks, snapshots) for the regions the customer names.
2. **Explain** the capability boundary with the built-in knowledge files (no memory-based claims).
3. **Guide** the customer through replication-pair / consistency-group / regional-ESSD operations
   that **the customer performs themselves in the console**, with a risk notice and a verification
   method for every step.
4. **Hand off** neighbouring symptoms (billing, security groups, in-guest/panel problems, disk IO,
   snapshot lifecycle) instead of diagnosing them here.

## 1. Absolute prohibition (hard contract, no exceptions)

- This skill is **read-only**. It MUST NOT generate, write, recommend for itself, or execute any
  mutating cloud API call, in any product (ECS, Elastic Block Storage, snapshot, replication,
  instance lifecycle, billing, RAM). That includes any action whose name starts with a mutating
  verb (`Create*`, `Delete*`, `Modify*`, `Start*`, `Stop*`, `Attach*`, `Detach*`, `Reset*`,
  `Replace*`, `Reboot*`, `Release*`, `Re-init*`, `Bind*`, `Unbind*`, `Import*`, `Export*`,
  `Revoke*`, `Grant*`).
- It MUST NOT ask the customer to run mutating commands **on its behalf**, and MUST NOT run any
  command inside a customer instance (no guest access, no panel access, no Cloud Assistant
  execution APIs). Where a guest-side reading is needed, it asks the customer to run a **read-only**
  check themselves and paste the output back (see `references/disk-replication-dr-guide__self-check-commands.md`).
- It MUST NOT request, hint at, or accept credentials: no AccessKey material, no RAM user or
  password, no console/panel addresses or accounts. Authentication comes only from the aliyun CLI
  default credential chain already configured on the machine. (A real ticket in this tier leaked
  panel credentials into the conversation; never repeat that.)
- It MUST NOT invent API names, parameters, console menu labels, error codes, prices, RPO/RTO
  numbers or documentation URLs. Facts come from script output or from the `references/` files.
- Anything the customer wants changed is expressed as **manual guidance**: where to click, what to
  fill, what it costs, what can be lost, what the expected result is, and how to verify afterwards.

If a request needs a write operation, say so plainly, give the console entry point and the official
document, and let the customer execute it.

## 2. API whitelist (the only calls this skill makes)

| Product | Action | Version | Purpose |
|---|---|---|---|
| `ecs` | `DescribeInstances` | 2014-05-26 | region/zone/status of instances, billing attribute |
| `ecs` | `DescribeDisks` | 2014-05-26 | disk category (zone-redundant or not), size, status, charge type, automatic-snapshot flag |
| `ecs` | `DescribeSnapshots` | 2014-05-26 | snapshot existence, type, source disk (backup evidence) |
| `sts` | `GetCallerIdentity` | 2015-04-01 | verify which account the credential belongs to; derive the UID label (plugin-mode command `aliyun sts get-caller-identity`) |

`references/ram-policies.md` lists the matching RAM actions. Nothing outside this table may be
called, and the scripts call nothing else.

**Known visibility gap (do not paper over it):** replication-pair and consistency-group objects are
not reachable through this whitelisted surface. The Block Storage OpenAPI reference does document
read-only query operations for both object types, but none of them was verified for this build, so
this skill **does not call them and does not declare them** -- never guess one from its name.
Replication-state verification therefore degrades to a customer console self-check
(`references/disk-replication-dr-guide__dr-capability-boundary.md` section 6).

## 3. Execution principle

Run the entry script. Do not hand-assemble `aliyun` commands, do not re-implement queries, and do
not call the API any other way:

```bash
# 1. who am I (optional preflight; explains credential problems early)
python3 scripts/axes/disk_replication_dr_guide/sts_token.py

# 2. per-region disk DR evidence inventory (the factual base of every answer)
python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id cn-hangzhou
python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id cn-hangzhou,cn-shanghai
python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id cn-beijing --instance-id i-2ze01234567890abcdef
python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id cn-beijing --disk-id d-2ze01234567890abcdef --json
```

- `--region-id` is **required** and is the only way to scope the run. Several regions can be passed
  comma-separated (up to 20 per run).
- Never present one region's result as an account-wide result. Query each region the customer
  cares about, and state which regions were queried.
- If the customer has not said which region: ask. Do not guess a region and do not scan all
  regions.
- Failures degrade instead of aborting: each failed query leaves a `[WARN]` line on stderr and an
  `errors[]` record in the report. Relay them; never fill a gap with an assumption.
- Read `STATUS:` and `NEXT_ACTION:` at the end of every run and report them faithfully.

## 4. Workflow

1. **Classify the request** (routing table and per-group playbooks: `references/disk-replication-dr-guide__root-causes.md`).
   - Group A: DR capability / selection question ("does ECS fail over by itself?", "which data
     centre?", "can snapshots go to another city automatically?").
   - Group B: "replication or backup is charging me" / "turn DR off and refund me".
   - Group C: problem inside the guest after copying or restoring data from a disk (404, blank
     page, very slow copy) -> identify and hand off, do not diagnose here.
   - Operation guidance: how to create / start / fail over / drill / delete a replication pair or
     consistency group.
2. **Collect facts when the answer depends on them**: run
   `python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id <region>` (add `--instance-id` / `--disk-id`
   when the customer named a resource). Skip the script only for pure capability questions and
   say that no live check was performed.
3. **Answer from the knowledge files**, quoting them, never from memory:
   capability boundary and verified specs -> `references/disk-replication-dr-guide__dr-capability-boundary.md`;
   operation steps -> `references/disk-replication-dr-guide__dr-operation-guidance.md`;
   routing and hand-off wording -> `references/disk-replication-dr-guide__handoff-map.md`.
4. **Guide, do not act.** For each customer-executed step, deliver the four-part protocol in
   section 5, using the verified console path from `references/disk-replication-dr-guide__dr-operation-guidance.md`.
5. **Close the loop with verification**, always read-only: rerun the inventory for the same
   region, or ask the customer to read the console state / a read-only in-guest command output back
   to you (`references/disk-replication-dr-guide__self-check-commands.md`).
6. **Stay in your lane**: bills, invoices, refunds, traffic sources, security-group rules, panel or
   web-server configuration, disk performance testing, snapshot policies -> identify, one-sentence
   judgement, hand off with the templates in `references/disk-replication-dr-guide__handoff-map.md`.

## 5. Guidance protocol (mandatory for every step the customer executes)

Every guidance step must state all four parts. Missing any part is an incomplete answer:

1. **Where and what**: console entry, tab, button and field names, taken from the official document
   cited for that step -- never invented, never paraphrased into something new.
2. **Risk notice before execution**: what will be created or overwritten, that it is billable while
   it exists, and what becomes unavailable. The non-negotiable ones in this tier:
   activating a replication pair **overwrites all data on the secondary disk** (snapshot it first);
   a failover must run only when the primary disk really failed, otherwise the in-flight data of the
   primary side is lost; deleting a pair while replication is in progress discards the in-flight
   replication; a drill creates pay-as-you-go disks that must be released afterwards; reverse
   replication swaps primary/secondary roles.
3. **Expected result**: the status or field the customer should see after the step (for example the
   pair moving from `Initial Syncing` to `Normal`, or to `Failed Over` after a failover).
4. **How to verify**: read-only re-check -- the console state, or
   `python3 scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py --region-id <region>` for disk/snapshot facts.

Quote specification numbers (RPO, replication cycle, pair-per-group limits, capacity limits) only
from the verified table in `references/disk-replication-dr-guide__dr-capability-boundary.md`, and give its source document.
Quote **no prices**: point at the pricing page shown on the console order screen.

## Observability

Every API call of one run carries a User-Agent built from a fresh per-run session id:

- Template: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`
  -> `AlibabaCloud-Agent-Skills/alibabacloud-ecs-disk-replication-dr-guide/<32-hex>`
- `<session-id>` is generated once per script run with `uuid.uuid4().hex` and reused for all calls
  of that run, so the whole run is traceable as one session.
- The flag is attached inside the shared CLI layer (`scripts/axes/disk_replication_dr_guide/_cli.py`) on every invocation as
  `--user-agent <value>`; agents must not strip or override it.
- The session id is echoed in the report header (`Session id`) and on stderr so it can be quoted to
  support.

## 7. Permissions and authentication failures

- The three ECS read actions (`ecs:DescribeInstances`, `ecs:DescribeDisks`,
  `ecs:DescribeSnapshots`) plus `sts:GetCallerIdentity` are the whole requirement; see
  `references/ram-policies.md` for the minimal policy document and the grant steps.
- Authorization failures are reported to the customer with the literals `NoPermission` or
  `ImplicitDeny`, followed by the missing action name and the minimal policy snippet from
  `references/ram-policies.md`. No other authorization wording is used.
- Credential-chain failures (`InvalidAccessKeyId.NotFound`, `SignatureDoesNotMatch`,
  `SDK.InvalidCredential`): tell the customer to configure the aliyun CLI profile
  (`aliyun configure`) or switch profile with `--profile <name>`. Never ask for, paste or store key
  material.
- Throttling or transient server errors are retried by the CLI layer (3 attempts, linear backoff);
  if they persist, report the code and suggest narrowing the region list.

## 8. Output contract

The final answer must:

- relay the script `Summary`, `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION` as produced;
- cite only values that the script returned or that the customer pasted back, and name the region(s)
  and account UID they refer to (state any parameter the script auto-filled);
- carry the visibility-scope declaration whenever a "no DR/backup resource" conclusion appears:
  conclusion is bounded to the queried account plus regions, and covers none of the items in the
  report's `NOT covered` list (billing, cloud backup/HBR, security groups, guest state, replication
  objects);
- give guidance as steps for the customer to execute under section 5, and cite the official
  documents from the report's `Guidance docs` block only;
- say plainly what could not be determined (failed query, unverified object type, out-of-scope
  domain) and what the next read-only check or hand-off is.

An empty result is never "you have no backup anywhere"; it is "nothing found in account UID X in
regions Y". A failed query is never "nothing exists".

## 9. Reference files

| File | Use it for |
|---|---|
| `references/disk-replication-dr-guide__dr-capability-boundary.md` | capability boundary, option comparison, verified RPO/RTO and limits table |
| `references/disk-replication-dr-guide__dr-operation-guidance.md` | verified console paths for pair / group / drill / failover / delete, with risk notices and verification |
| `references/disk-replication-dr-guide__root-causes.md` | symptom-to-cause routing, groups A/B/C playbooks |
| `references/disk-replication-dr-guide__handoff-map.md` | out-of-scope judgement rules and ready hand-off wording |
| `references/disk-replication-dr-guide__self-check-commands.md` | read-only checks the customer runs and pastes back |
| `references/ram-policies.md` | exact read-only actions, minimal policy, grant steps, failure lookup |

## 10. Known limitations of this build

- No write capability by design: this skill cannot create, start, fail over or delete a replication
  pair for the customer.
- No guest, panel, monitor or billing visibility: only the four whitelisted read calls.
- Replication-pair and consistency-group state is not machine-readable here; verification is a
  customer console self-check.
- This tier's customer-visible error strings are not fully catalogued yet, so symptom wording plus
  the `NoPermission` / `ImplicitDeny` literals carry the failure messaging.
