---
name: alibabacloud-ecs-idc-address-query
description: |
  Read-only resolver for where an Alibaba Cloud ECS instance physically runs. By
  instance id or public IP it reports the region, availability zone, and the
  public city-level location of the region, then states the confidentiality
  boundary and routes street-address, stamped-document, ISP/carrier and
  other-product requests to the right channel. Use when a customer asks: where
  is my ECS instance physically located; server room / machine room / data
  center address; physical location of instance i-...; which city or zone hosts
  this public IP; proof of server location for compliance; NoPermission or
  ImplicitDeny on a location query. Do NOT use for the ICP filing workflow
  itself (use alibabacloud-ecs-icp-filing-guide), for recovering an expired or
  already-gone instance or its data, or for RDS / Redis / SLB resources.
---

# ECS instance physical (data-center) location query — read-only

This skill answers one narrow question: *where does my ECS instance physically
run?* It resolves an instance id or a public IP to its **region, availability
zone, and the public city-level name of that region**, states the confidentiality
boundary, and hands off anything beyond that boundary. It is fully read-only.

## Read-only scope and ABSOLUTE PROHIBITION

- **This skill is read-only.** It performs only the API actions in the whitelist
  below, all `Describe*` / `Get*` reads. It applies no change to any cloud
  resource.
- **ABSOLUTE PROHIBITION.** Never generate, run, or suggest a state-changing API
  (`Modify*`, `Create*`, `Delete*`, `Release*`, `Reset*`, `Attach*`, `Detach*`,
  `Reboot*`, `Start*`, `Stop*`, `Put*`, ...), including "a change command for the
  user to paste". The whitelist is exhaustive; anything not listed is prohibited
  to execute from this skill.
- **Never enter the guest OS.** Physical machine-room location is not a
  in-instance fact; do not run, generate, or recommend any command inside the
  instance. Do not use Cloud Assistant / Workbench here.
- **Never fabricate a confidential location.** Do not invent or guess a
  district/street-level data-center address, a facility/building name, a
  rack/slot position, an ISP/carrier detail, or a documentation URL. Report only
  what the read APIs and the embedded public region table return; anything
  finer is routed to the ticket channel.

## API whitelist (the only actions this skill may call)

| Product | Action | Access |
|---|---|---|
| ecs | `DescribeInstances` | read |
| ecs | `DescribeInstanceStatus` | read |
| ecs | `DescribeAvailableResource` | read |
| sts | `GetCallerIdentity` | read |

See `references/ram-policies.md` for the exact minimal policy and
`related_apis.yaml` for the declared product/version of each call.

## Execution principle

The agent runs the single entry script and relays its output; it **must not**
hand-compose `aliyun` commands or bypass the entry point. Every cloud read goes
through `scripts/axes/idc_address_query/_cli.py`, which enforces per-call timeouts, transient-error
retry, credential masking, and the observability User-Agent.

Entry point: `scripts/axes/idc_address_query/idc_address_query.py`

```
python3 scripts/axes/idc_address_query/idc_address_query.py --instance-id i-2zeixxxx
python3 scripts/axes/idc_address_query/idc_address_query.py --public-ip 47.92.163.139 --region cn-hangzhou
python3 scripts/axes/idc_address_query/idc_address_query.py --instance-id i-aaaa,i-bbbb
python3 scripts/axes/idc_address_query/idc_address_query.py --check-availability --region cn-hangzhou
python3 scripts/axes/idc_address_query/idc_address_query.py --show-handoff
```

Credential self-check: `python3 scripts/axes/idc_address_query/sts_token.py`

Credentials come from the aliyun CLI default credential chain. This skill never
reads, prints, stores, or requests an access key id or secret; set up
credentials out of band with `aliyun configure`.

## Inputs and pre-flight validation

One identifier is required: an ECS instance id (`i-...`, up to 100, repeated or
comma-separated) or a public IP. Optionally pass `--region` to avoid a
multi-region scan. If nothing is supplied the script prints the input guidance and
returns `STATUS: FAIL` rather than guessing — this is the fix for tickets that
closed simply because no instance id was ever given. Always act from the account
that **owns** the resource; a resource of another account is reported with the
cross-account refusal, never looked up by guessing. Full detail:
`references/idc-address-query__handoff-and-inputs.md`.

## Handling the request

1. Validate that an id or IP is present; otherwise emit input guidance.
2. Resolve the account via `GetCallerIdentity` for the owning-UID wording.
3. Locate the resource with `DescribeInstances` (optionally confirmed by
   `DescribeInstanceStatus`); report region, zone, status, IPs, and the public
   city-level location.
4. Append the confidentiality / safe-use / ticket guidance for anything finer than
   city level.
5. Route adjacent asks through the handoff matrix (`--show-handoff`).

Decision tree and symptom mapping: `references/idc-address-query__decision-tree.md`.
Handoff matrix and disclosure boundary: `references/idc-address-query__handoff-and-inputs.md`.

## Authentication failure output

On a denied or unauthorized read, report the customer-facing literals
`NoPermission` or `ImplicitDeny`, name the exact missing action from the whitelist,
and point to the minimal policy in `references/ram-policies.md`. Do not surface
any other authorization label. Never fall back to a change or a guest command.

## Output contract

Relay the script's report verbatim. It ends with two machine-checkable lines:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <human guidance, or "None">
```

State only values the read APIs returned, declare any auto-filled parameter
(region / account UID), and give human-only guidance. This skill never applies a
change and never supplies a confidential address, facility name, rack position,
ISP detail, or invented document link.

## Observability

Every read-only CLI call made by `scripts/` carries a per-run session User-Agent
built from a 32-hex `uuid4` value, in the form:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

Here `{skill}` resolves to the skill name
`alibabacloud-ecs-idc-address-query`, and `{session-id}` is generated in
`scripts/axes/idc_address_query/_cli.py` (`uuid.uuid4().hex`, a 32-character lowercase hex string,
created once per run) and attached to each call via `--user-agent`. No
credential material is ever placed in the User-Agent, logs, or command line.
