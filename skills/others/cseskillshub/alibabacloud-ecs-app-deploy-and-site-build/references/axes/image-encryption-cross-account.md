---
name: alibabacloud-ecs-image-encryption-cross-account
description: |
  Read-only evidence and console guidance for encrypted ECS custom images
  shared, copied or launched across Alibaba Cloud accounts. Calls only
  DescribeImages, DescribeInstances and DescribeInstanceStatus. Changes no
  resource, runs no in-guest command.
  Use when the customer mentions any of:
  encrypted image cannot be shared with another account
  cross-account sharing of an encrypted custom image
  copy an encrypted image to another region or re-encrypt it
  shared encrypted image not visible in the recipient account
  launch from a shared encrypted image fails unless Encrypted is true
  encrypted image cannot be exported
  AliyunECSShareEncryptImageDefaultRole
  NoPermission / ImplicitDeny on an image query
  Do NOT use for unencrypted image copy or import/export, disk or snapshot
  encryption, KMS key lifecycle, image billing or replacing an OS; use the
  matching ECS image, disk-encryption or billing skill instead.
---

# ECS Encrypted Image — Cross-Account and Encryption Limits (Read-Only Guide)

## 1. What this skill does

This skill answers one narrow question with cloud evidence instead of assumption:

> Is this ECS custom image encrypted, and what does that fact legally allow when the
> image is shared, copied, or used from **another** Alibaba Cloud account?

It is a **read-only guide (RO_GUIDE)**. It gathers facts with three `Describe*`
calls, prints an evidence report, and hands the customer the exact console steps for
the disposal action. The customer performs every change in the console. This skill
never performs one.

## 2. ABSOLUTE PROHIBITION — read-only, no writes, no in-guest commands

The following are hard boundaries, not preferences:

- **Never invoke a mutating API.** No create, modify, delete, copy, share, export,
  cancel-share or attach operation, from any product, in any form — not through the
  `aliyun` CLI, not through a helper script, and not by printing a command line for
  the customer to run that changes a resource.
- **Never execute anything inside a customer instance.** No remote command execution
  is available to this skill and none may be improvised. When guest-side readings are
  needed, ask the customer to run a read-only command themselves and paste the output
  back, or hand the request off (see `references/image-encryption-cross-account__customer-selfcheck.md`).
- **No credentials are handled, requested, printed or stored.** The scripts use the
  default Alibaba Cloud credential chain of the caller's own environment. Never write
  an access key or a security token into a file, a command line, a log, or a chat
  message, and never ask the customer to paste one. Any error text passing through the
  scripts is masked first (`AccessKeyId`, `AccessKeySecret`, `SecurityToken`,
  `Password`, `Signature` values become `***`).
- **Commercial, approval and quota-raise workflows** get the process and the material
  list only. Nothing is submitted on the customer's behalf.
- **Peer-account state is permanently invisible** from the caller's credentials. Do not
  guess it, and do not ask for the peer's credentials to "just check". Degrade to a
  customer self-check instead.

**Enforced read-only whitelist** (also enforced in code by `scripts/axes/image_encryption_cross_account/_cli.py`, which
raises `ReadOnlyWhitelistViolation` for anything else):

| Action | Product | API version | Purpose |
| --- | --- | --- | --- |
| `DescribeImages` | ecs | 2014-05-26 | encryption mapping, status, progress, share flags |
| `DescribeInstances` | ecs | 2014-05-26 | which instance used which image |
| `DescribeInstanceStatus` | ecs | 2014-05-26 | instance running state context |
| `get-caller-identity` | sts | 2015-04-01 | label the report with the account actually queried |

RAM permission points, a minimal policy, and the `NoPermission` / `ImplicitDeny`
handling procedure are in [`references/ram-policies.md`](references/ram-policies.md).
No wildcard action is used anywhere in this package, and no write action is declared
in `related_apis.yaml`.

## 3. Prerequisites

1. Alibaba Cloud CLI installed and configured with the **default credential chain**
   (`aliyun configure`, a RAM role, or an assumed-role profile) for the account that
   owns — or received — the image.
2. The RAM policy from `references/ram-policies.md` attached to that identity.
3. Python 3 only, standard library only — see `scripts/requirements.txt`. No third-party
   install step is required.

## 4. How to run — one entry point only

Run **only** the single entry script. It performs the identity label, the image query,
optional instance context, the routing, and the guidance in one pass. Do not call the
private modules (`scripts/axes/image_encryption_cross_account/_cli.py`, `scripts/axes/image_encryption_cross_account/_constants.py`) directly and do not
compose your own `aliyun ecs describe...` command lines.

```bash
python3 scripts/axes/image_encryption_cross_account/image_cross_account_check.py \
  --region-id cn-hangzhou \
  --image-id m-bp1xxxxxxxx \
  --intent share-encrypted
```

| Flag | Meaning |
| --- | --- |
| `--region-id` | **required**; one region per run, no silent default |
| `--image-id` | comma-separated image ids |
| `--image-name` | name pattern matched by the API |
| `--owner-alias` | `self` / `system` / `others` / `marketplace` |
| `--peer-account-id` | account id the customer believes is the owner or the recipient |
| `--resource-group-id` | narrow the query to one resource group |
| `--instance-id` | comma-separated instance ids for instance context |
| `--with-instances` | also list instances built from the matched images |
| `--intent` | `verify-presence`, `share-encrypted`, `copy-encrypted`, `launch-from-shared`, `export-blocked`, `quota-check`, `generic` |
| `--available-only` | query `Status=Available` instead of `ALL` (see the trap in the Observability section) |
| `--skip-identity` | skip the STS identity call; an intentional skip, not a degradation |
| `--timeout` | per-call CLI timeout in seconds (default 90) |
| `--json` | machine-readable evidence block instead of the report |

The STS identity step can also be run alone when only the account label is needed:

```bash
python3 scripts/axes/image_encryption_cross_account/sts_token.py
```

## Observability

Every CLI call made by this skill carries a traceable User-Agent built from the
template

```
--user-agent AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
```

where `{skill-name}` resolves to `alibabacloud-ecs-image-encryption-cross-account`
and `{session-id}` is one 32-character hex token generated per script run
(`uuid4().hex`), shared by all calls in that run, and printed in the report header so
a customer can quote it back when an OpenAPI request needs to be traced. It contains no
customer data and no credential. Every subprocess call is bounded by a timeout, reads
no stdin, uses an argument list (never a shell string), and retries only transient
errors with a capped backoff.

Note on the default status filter: `DescribeImages` defaults to `Status=Available`,
which **hides images that are still `Creating` or `Waiting`**. The entry script queries
`ALL` by default for exactly that reason — "the image is missing" is a common false
conclusion.

## 6. Decision tree

The routing below is implemented in `build_findings()` of
[`scripts/axes/image_encryption_cross_account/image_cross_account_check.py`](scripts/axes/image_encryption_cross_account/image_cross_account_check.py);
follow the printed findings rather than re-deriving them.

```
Q0 Which account owns the image?
   |- caller's own account   -> continue; evidence is authoritative for this region
   \- a peer account         -> STOP querying. Peer state is invisible here.
                                Use references/image-encryption-cross-account__customer-selfcheck.md and mark DEGRADED.

Q1 Any image matched in this region?
   |- none with Status=ALL      -> wrong region / wrong account / id typed as name.
   |                               Report as an empty result with its causes, never as
   |                               "the image does not exist".
   \- none with --available-only -> re-run without the flag before concluding.

Q2 Encryption attribute (DescribeImages DiskDeviceMappings[].Encrypted)
   |- encrypted (>=1 mapping)  -> encrypted path: same-region share only, irreversible,
   |                              owner needs AliyunECSShareEncryptImageDefaultRole
   |                              + KMS grant -> guide-steps.md block 1
   |- not encrypted            -> this symptom axis does not apply
   |                              -> boundary-and-handoff.md
   \- Encrypted field absent   -> UNVERIFIED. Say so; confirm in console. Never infer.

Q3 Status / progress
   |- Creating, Waiting, progress < 100%    -> in flight; wait, then re-check
   \- CreateFailed, UnAvailable, Deprecated -> production problem -> hand off

Q4 Direction of the share
   |- shared out (IsSelfShared=true)    -> only the owner can view or cancel the grant
   \- received (ImageOwnerAlias=others) -> cannot re-share; launching an encrypted one
                                           requires the encryption parameter to be true

Q5 Ask is about export / quota / RAM / billing
   |- export of an encrypted image  -> documented exclusion; state it, offer the
   |                                   instance route, do not attempt anything
   |- quota ceiling                 -> two quota items, read them, customer raises it
   \- RAM / consent / approval flow -> process + material list only, never submitted
```

## 7. Output contract

Every run ends with two machine-readable lines:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single most useful next step>
```

- `OK` — the queried account's own evidence answered the question.
- `DEGRADED` — partial evidence: a peer account is involved, a field the API does not
  return was needed, a query limitation was recorded, or a permission point failed.
  Failed reads are recorded and the remaining read calls continue.
- `FAIL` — nothing usable could be read (identity unavailable, region invalid, every
  call denied). Exit code `1`; `0` otherwise.

Never upgrade a status from customer-reported information. Text the customer pasted
back is labelled `customer-reported, not verified by this skill`. Facts that the cited
documents do not establish are listed in section J of
[`references/image-encryption-cross-account__image-encryption-basis.md`](references/image-encryption-cross-account__image-encryption-basis.md) and are
handed to the customer as self-check items — they are never asserted.

## 8. References

| File | Use it for |
| --- | --- |
| [`references/ram-policies.md`](references/ram-policies.md) | the three ECS permission points, minimal policy, `NoPermission` / `ImplicitDeny` procedure |
| [`references/image-encryption-cross-account__image-encryption-basis.md`](references/image-encryption-cross-account__image-encryption-basis.md) | every factual claim with its source, the share-authorization role and policy text, quotas, what the API cannot prove, and the "not established" list |
| [`references/image-encryption-cross-account__guide-steps.md`](references/image-encryption-cross-account__guide-steps.md) | the five-element console steps to hand over (entry point / object / action / expected result / rollback / risk) |
| [`references/image-encryption-cross-account__customer-selfcheck.md`](references/image-encryption-cross-account__customer-selfcheck.md) | what to ask the owner account and the recipient account to check and paste back |
| [`references/image-encryption-cross-account__boundary-and-handoff.md`](references/image-encryption-cross-account__boundary-and-handoff.md) | when to stop and route elsewhere, with the phrasing to use |
