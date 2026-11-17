# Read-only API usage and its limits

Product `ecs`, API version `2014-05-26`; product `sts`, API version `2015-04-01`. Each
action below is verified present in the CLI metadata and is the only reason the report
can state a cloud fact. The RPC-style products keep the PascalCase action name on the
command line, while the identity probe uses the plugin-style lower-case hyphenated form:

```text
aliyun ecs describe-instances --region-id <region> --instance-ids '["i-xxxx","i-yyyy"]'
aliyun ecs describe-instance-status --region-id <region> --instance-id.1 i-xxxx
aliyun sts get-caller-identity
```

`scripts/axes/invalid_ticket_triage/_cli.py` builds these as argument lists (never a shell string), adds
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-invalid-ticket-triage/<session-id>`
to every call including retries, applies a per-call timeout, and masks anything
credential-shaped before it reaches stderr or the report.

| Action | Required | Used here for | Notes on parameters |
|---|---|---|---|
| `DescribeInstances` | `RegionId` | visibility and ownership of an id quoted in the ticket | `InstanceIds` is a JSON array string, so it is produced with `json.dumps`; `PageSize` is set to the id count so all results return in one page |
| `DescribeInstanceStatus` | `RegionId` | optional running-state corroboration | repeated `InstanceId.n` keys, `n` from 1; only called when every requested id was already visible |
| `GetCallerIdentity` | none | labels the account scope of the read | called only when `--show-caller` is passed; a verification on its own never triggers it |

Fields read from the response, all optional: `InstanceId`, `InstanceName`, `Status`,
`InstanceType`, `InstanceChargeType`, `RegionId`, `ZoneId`, `CreationTime`. A field the
service did not return is printed as `not returned` rather than filled in.

## Not used, and why

`DescribeAvailableResource` appears in the tier contract but the judgement chain has no
use for purchase-availability data, and the contract supplied no RAM action point for
it - an action point is never derived from an interface name. It is therefore neither
called nor declared in `related_apis.yaml` or [ram-policies.md](ram-policies.md).

## Visibility boundary

Read calls see only the account behind the current credentials and only the region in
`RegionId`. Consequences that must appear in the report verbatim in spirit:

- An id with no record means "not visible to these credentials in this region". It is
  not evidence that the id is wrong, fake or gone. A cross-account instance, an
  instance in another region and a released instance are indistinguishable here, and
  automated-probe tickets are typically cross-account - so "empty result" is the
  expected outcome for those, not a finding.
- No `RegionId` means no call: the report says the ids stayed unverified.
- Files submitted with the ticket and masked order numbers stay unreachable; this skill
  holds no order-interface capability, so the report asks for the complete number or
  routes to a human instead of guessing.

## Errors and honest degradation

The reviewed batch supplied no quotable error-code table for this tier, and no code is
invented here. Handling is keyed on the literals the CLI actually returns:

| Situation | Behaviour |
|---|---|
| `NoPermission`, `ImplicitDeny`, `AccessDenied`, `InvalidAccessKeyId` | name the missing action and point at the minimal statement in [ram-policies.md](ram-policies.md); credentials come from the default chain, so the customer is never asked for a key pair or a token |
| `Throttling`, `Throttling.User`, `ServiceUnavailable`, `InternalError`, timeouts | retry within a bounded count and backoff in `scripts/axes/invalid_ticket_triage/_cli.py`, then record a `LIMITATION` line |
| CLI absent, unparsable body, unknown action | report the failure, keep the text-only verdict, set `STATUS: DEGRADED` |
| Empty instance list | report "not visible", keep the verdict on the text evidence |

A failed read never blocks the judgement: types A, B and C rest on the customer's own
words, and the instance check only adds or removes a fact line.

## OS-related wording

The judgement and the read-only checks are independent of the guest operating system. If
a ticket mentions Windows or another system image, that text travels only as handoff
context; this tier has no in-instance equivalent, and per the boundary in
[SKILL.md](../SKILL.md) nothing is executed inside an instance.

## Rule wordings quoted in tickets

Promotional purchase limits, the 5-day no-reason return condition and disk shrink
behaviour were quoted by agents as point-in-time statements, so the report prints the
review date of these rules. Two documents appear in the evidence:

- ECS free trial usage scenarios:
  `https://help.aliyun.com/zh/ecs/user-guide/usage-scenarios-for-the-ecs-free-trial.md`
- Unsubscription rules, as quoted by the agent in ticket 000F4RUDD8:
  `https://help.aliyun.com/document_detail/431646.html`

No version identifier was available for either document in the reviewed batch. Re-verify
before quoting either to a customer. Official handling procedure for test or invalid
tickets, the meaning of the pending-customer-confirmation and auto-close states, and the
purchase limit of the promotional machine type had no document hit in the searched set;
they stay flagged for a human.
