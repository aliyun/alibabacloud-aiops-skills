# Read-Only Precheck Queries

What the two whitelisted ECS reads give this skill, how to read each field, and,
more importantly, where their authority ends.

Both calls go through `scripts/axes/website_build_guide/_cli.py`, one region at a time, with a bounded
per-call timeout. The API's own published request and response definition is the
source of truth for parameter names and field shapes; the scripts implement it,
and nothing here should be quoted as a parameter list from memory.

## 1. `ecs DescribeInstances` (version `2014-05-26`)

**Parameters this skill sends**

| Parameter | Value | Why |
|---|---|---|
| `RegionId` | the region the customer supplies | ECS inventory is regional; there is no all-region read |
| `PageNumber` / `PageSize` | walked automatically | an instance list can exceed one page |
| `InstanceIds` | only when the customer named a target | narrows the inventory to the machine under discussion |

**Fields the report uses, and what they mean for a build**

| Response field | Meaning | Use in the guide |
|---|---|---|
| `InstanceId`, `InstanceName` | the machine and its label | confirms the target with the customer before any walkthrough |
| `Status` | lifecycle state (`Pending`, `Running`, `Starting`, `Stopping`, `Stopped`) | `Running` is the precondition for stages 1 onward |
| `RegionId`, `ZoneId` | location | cross-checks the customer's assumption about where they bought |
| `InstanceType`, `InstanceChargeType` | size and billing mode | context only; never a basis for a commercial conclusion |
| `OSName`, `ImageId` | image identity | decides the stage 1 user name and the stage 2 flavour options |
| `InstanceNetworkType` | `vpc` or classic | shapes how the public address appears |
| `PublicIpAddress` / `EipAddress.IpAddress` | public address(es) | stage 5 fills the `A` record from these, and nothing else |
| `VpcAttributes.PrivateIpAddress`, `VpcAttributes.VpcId` | private side | explains why a public address is required for external access |
| `SecurityGroupIds` | bound groups | recorded so the access-check stage knows which group the customer must inspect **in the console themselves** - this skill does not read group rules |

A missing field is reported as missing. An empty address list, for instance, is
stated as "no public address returned" - never silently replaced with a
guess.

## 2. `ecs DescribeInstanceStatus` (version `2014-05-26`)

**Parameters:** `RegionId`, plus automatic paging.

**Fields:** `InstanceStatuses.InstanceStatus[]` with `InstanceId` and `Status`.

Its purpose is narrow: an independent second read of the same state, taken a
moment after the first. When the two disagree, the report says so and treats the
state as in transition rather than picking the more convenient answer.

## 3. `sts GetCallerIdentity`

No parameters, no RAM action required. Returns the account the credentials
belong to. Used **only** as a label in the report header so a result can be tied
to the account that produced it. It is not a probe of anything the customer owns
and is not a substitute for the inventory.

---

## Where the read-only view ends

Everything below is invisible to these calls. Each item becomes a paste-back
question in [customer-selfcheck.md](customer-selfcheck.md), or a hand-off in
[handoff-rules.md](handoff-rules.md) - never an assumption.

| Not visible | Consequence |
|---|---|
| Whether a site entry exists in a control panel | Ticket root causes of the "domain resolves but serves nothing" kind cannot be closed from the cloud side |
| Document-root contents, uploaded files, file permissions | Stage 4 completion is the customer's evidence |
| Whether a web service is running or listening | Stage 2 and stage 6 depend on customer output |
| The customer's local DNS view and browser result | Only their pasted result can close the loop |
| Entitlements of non-ECS products (for example, how many filing service codes a purchased website-building product includes) | Direct the customer to that product's own console page; do not infer from an ECS read |
| Anything in another region or another account | A single-region empty result is never "you own no server" |

## Interpretation rules

1. **Evidence, then statement.** Every cloud-side claim in the report traces to a
   field actually returned in that run.
2. **Empty is a finding with a caveat**, not an absence of resources.
3. **Never claim a guest-side or panel-side fact.** If the answer would require
   entering the instance, ask for the read-only command output instead.
4. **Partial data degrades visibly.** A failed read leaves a `[WARN|DEGRADE]`
   line and an entry in the report's degradation log, and the overall `STATUS`
   drops to `DEGRADED`.
