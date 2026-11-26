# RAM permissions for alibabacloud-ecs-high-frequency-issues (union of 24 areas, per-area sections
# are verbatim copies of member specs that each passed the static gate)
## Area: web-inaccessible-slow

# RAM permissions actually required

Read this file before the first run in a new account. It lists **every** action the scripts
call, one by one. No action in this skill is granted through a wildcard, and no action outside
this list may be added "for convenience": if a call is not here, the skill does not make it.

## 1. Action inventory

| # | Action | Product / API version | Where it is called | Permission level | Why it is needed |
| --- | --- | --- | --- | --- | --- |
| 1 | `sts:GetCallerIdentity` | Sts `2015-04-01` | `../scripts/areas/web_inaccessible_slow/sts_token.py` | A | Confirms which account the session belongs to, so an asset can be proved to be (or not be) the customer's own |
| 2 | `ecs:DescribeInstances` | Ecs `2014-05-26` | `../scripts/areas/web_inaccessible_slow/ecs_web_access_check.py` (L1) | A | Existence, region, status, public and private addresses, EIP field, bound security groups, asset type |
| 3 | `ecs:DescribeSecurityGroups` | Ecs `2014-05-26` | L4 | A | Which groups the instance is a member of, and their default policies |
| 4 | `ecs:DescribeSecurityGroupAttribute` | Ecs `2014-05-26` | L4 | A | Rule-by-rule inbound **and** outbound: port range, protocol, policy, priority, and the authorisation object (CIDR, group, prefix list) |
| 5 | Cloud Assistant dispatch, CLI plugin mode `aliyun ecs run-command` | Ecs `2014-05-26` | L5 | **B** (needs the customer's agreement) | The only way to see listeners, service state and the host firewall; a describe call never exposes them |
| 6 | `ecs:DescribeInvocations` | Ecs `2014-05-26` | L5 | A | Reads back the result of a command already dispatched; never dispatches anything |
| 7 | `vpc:DescribeEipAddresses` | Vpc `2016-04-28` | L1/L4 | A | Whether an EIP is actually bound to the instance and in what state; an unbound or reassigned EIP breaks the DNS-to-origin chain |
| 8 | `alidns:DescribeDomainRecords` | Alidns `2015-01-09` | L2 | A | Lists the current records of the customer's own zone for comparison |
| 9 | `cms:QueryMetricLast` | Cms `2019-01-01` | L8 | A | Latest monitoring points for the capacity line |
| 10 | `alidns:DescribeDomainNs` | Alidns `2015-01-09` | L2 | A | Which name servers are authoritative for the domain, and whether the DNS service holding the records is among them |

Three notes on this table that are easy to get wrong:

- **The monitoring permission point is not derived from the API name.** The API is
  `DescribeMetricLast`; the permission that has to be granted is `cms:QueryMetricLast`.
  Granting a point named after the API leaves the call failing.
- **`alidns:DescribeDomainRecords` is used for its list semantics only.** The skill never calls
  a DNS write operation. Record changes are printed as instructions for the customer to perform
  in the DNS console.
- **`alidns:DescribeDomainNs` is a read as well.** Records alone cannot prove resolution works: a
  zone whose delegation still points at another provider serves none of them. When this read is
  denied the report degrades and says the delegation was not verified; it never assumes the
  records are being served.
- **The Cloud Assistant dispatch is a consent-gated, write-class action and carries no declared
  grant here.** It runs only under whatever rights the customer's own credentials already hold,
  and only after the disclosure-and-agreement gate in `SKILL.md` is satisfied for that single
  command. A principal limited to the read-only statement below is a supported mode, not a defect:
  the in-guest layer (L5) then degrades to a paste-back checklist while every cloud-side layer
  still runs.

The snapshot operation (`aliyun ecs create-snapshot`) is **not** in this list. Snapshot creation
is presented as console steps the customer performs, with the billing note; the skill does not
call it.

## 2. Minimal custom policy

Attach it to the RAM role or RAM user that runs the scripts. The action list is explicit.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "WebPathMetadataReads",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeInvocations",
        "vpc:DescribeEipAddresses",
        "alidns:DescribeDomainRecords",
        "alidns:DescribeDomainNs",
        "cms:QueryMetricLast",
        "sts:GetCallerIdentity"
      ],
      "Resource": ["*"]
    }
  ]
}
```

The `Resource` value `"*"` is the form these metadata reads require: they are account- or
region-scoped list calls and do not support resource-level authorisation. The wildcard is
confined to `Resource`; **no `Action` value in this skill uses a wildcard**, which is the thing
that must not happen. Narrow the statement further with a condition on `acs:SourceIp` or by
restricting the region in the ARN if the account policy allows it.

This is the **only** grant the skill declares. It is sufficient to run every cloud-side layer
(L1-L4, L6-L8) and to read back any invocation result. The in-guest dispatch layer (L5) is a
write-class action and is intentionally **not** granted here.

## Consent-gated in-guest dispatch (Class B) - no declared grant

The layer that looks at listeners, service state and the host firewall has no cloud-side describe
equivalent; it can only be observed by dispatching one whitelisted, non-mutating command into the
instance through Cloud Assistant (CLI plugin-mode command `run-command`, underlying API
`RunCommand`, listed in `../related_apis.yaml`). Because it is write-class, it carries no grant in
the policy above:

- It runs only under whatever rights the customer's own credentials already hold, and only after
  the operator relays the disclosure (exact command text, target instance, that it writes nothing,
  that it is reversible) and the customer approves that single dispatch
  (`--guest-command <key> --confirm`; one agreement authorises exactly one command).
- Anything outside the embedded non-mutating whitelist is refused even after a confirmation and is
  handed to the customer as a paste-back step instead.
- Where an operator genuinely wants the session itself to dispatch it, they may add the matching
  write action to their own policy out-of-band and narrow `Resource` to the specific instance ARN.
  That is a customer-side decision outside this skill's default posture, and RAM cannot scope the
  dispatch down to the frozen whitelist - that confinement lives in this skill's code, not in the
  grant.

## 3. Preflight with the CLI

The scripts shell out to the locally configured `aliyun` CLI in plugin mode: the product and the
action are lowercase-hyphenated, while the RPC parameter names keep their PascalCase form, and
each call carries the session User-Agent. Equivalent manual preflight commands:

```bash
aliyun sts get-caller-identity
aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '["i-bp1xxxxxxxxxxxxxxxxx"]'
aliyun ecs describe-security-group-attribute --biz-region-id cn-hangzhou --security-group-id sg-bp1xxxxxxx --direction all
aliyun vpc describe-eip-addresses --biz-region-id cn-hangzhou
aliyun alidns describe-domain-records --domain-name example.com
aliyun cms describe-metric-last --namespace <operator-supplied> --metric-name <operator-supplied>
```

`<operator-supplied>` is intentional. No CloudMonitor namespace or metric name was verified for
this tier, so none is hard-coded anywhere in the skill; see `layered-decision-tree.md` (L8).

For the level-B path the scripts build the dispatch and the poll internally; the shapes are
`run-command` with `Type`, `CommandContent`, `InstanceId.1`, `Timeout`, `Name`, and
`ecs:DescribeInvocations` with `InvokeId`. `InstanceId.1` is a repeated parameter, not a JSON
array. The `Output` field of the invocation result is base64-encoded.

## 4. When a call is denied

Report the **exact** missing point and continue with the layers that still work. Authorisation
failures surface as the codes `NoPermission` or `ImplicitDeny`; quote whichever one the response
returned, and never paraphrase a denial as a generic access-forbidden message, because that sends
the customer to the wrong console page.

The minimal reply has three parts:

1. the layer that is therefore undecided, and what would have been learned from it;
2. the one action to add, from the table in section 1;
3. the console path for the grant: **RAM console > Permissions > Policies > create a custom
   policy with the statement above > attach to the current role or user**. Region and account
   identifiers must come from the customer's own session, never from a saved example.

When the response names no action, part 2 takes it from the row of the section 1 table that
matches the failed read, and the answer asks for that one row rather than for the table.

The scripts emit `STATUS: DEGRADED` for a partial run and `STATUS: FAIL` when no evidence at all
could be collected, so a denial is always visible in the report and never silently skipped.

## 5. Credentials

Credentials stay on the ambient CLI chain. Nothing in this skill reads, writes, prints, asks for
or stores an access key id, an access key secret, a security token, a password or a private key;
`../scripts/areas/web_inaccessible_slow/_cli.py` masks any of those that appear accidentally in captured output. Configure
the profile outside the conversation with `aliyun sts get-caller-identity`; if the customer pastes a credential
into the ticket, do not repeat it and use the reminder sentence in `SKILL.md`.

## Area: renewal-pricing-discount

# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS renewal-pricing diagnosis plus
manual guidance. It requires exactly six read actions; no wildcard action of
any form is used, and no write or instance-execution permission is needed or
granted. The same six actions are the complete API whitelist in SKILL.md and
are the full contents of `related_apis.yaml` (three-way alignment: this file
= related_apis.yaml = the actual script calls).

## RAM action prefix caveat for BSS (billing)

BSS OpenAPI actions are authorized under the RAM permission points of the
`bss:` namespace, and the permission-point NAME can differ from the API
operation name. Never derive the RAM action from the API name:

| API called (product / action / version) | RAM permission point | Used by |
|---|---|---|
| sts `GetCallerIdentity` (2015-04-01) | `sts:GetCallerIdentity` | `scripts/areas/renewal_pricing_discount/sts_token.py`, identity step of the entry script |
| ecs `DescribeInstances` (2014-05-26) | `ecs:DescribeInstances` | entry script mode `inventory` |
| ecs `DescribeInstanceAutoRenewAttribute` (2014-05-26) | `ecs:DescribeInstanceAutoRenewAttribute` | entry script mode `inventory` |
| bssopenapi `QueryAvailableInstances` (2017-12-14) | `bss:DescribeInstances` | entry script mode `expiring` |
| bssopenapi `DescribePricingModule` (2017-12-14) | `bss:DescribePricingModule` | entry script mode `pricing-modules` |
| bssopenapi `GetSubscriptionPrice` (2017-12-14) | `bss:DescribePrice` | entry script mode `quote` |

All six are Describe/Get/Query-class reads. The credential physically cannot
change any instance, order, subscription or renewal state, and cannot run
anything inside an instance.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadEcsRenewalFacts",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAutoRenewAttribute"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadBssRenewalAndPriceFacts",
      "Effect": "Allow",
      "Action": [
        "bss:DescribeInstances",
        "bss:DescribePricingModule",
        "bss:DescribePrice"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (asterisk form
  at product or global level) are forbidden for this skill.
- `Resource` is the account-wide asterisk because these reads are
  account-level or region-list scoped and the billing APIs support no
  resource-level narrowing. Read-only safety comes from the action list.
- No deny statements are needed: anything not listed is denied by default.
- If a call fails with `NoPermission` or `ImplicitDeny`, the script names the
  exact missing permission point above; grant that single action and rerun.
  Do NOT "fix" it by attaching any managed full-access billing policy.

## Grant flow

Option A - RAM user (same-account daily use):

1. RAM console -> Users -> select or create the user.
2. Create a custom policy from the JSON above (script editor).
3. Attach it; configure the aliyun CLI with that user's profile
   (the CLI default credential chain). The scripts resolve credentials only through the
   CLI default chain; they take no credential arguments.

Option B - RAM role (temporary or cross-account use):

1. Create a role trusted by the calling account and attach the policy above.
2. Assume it and store the temporary session as a named CLI profile; pass
   `--profile <name>` to the scripts.

Least-privilege checklist:

- Grant only the six points above - nothing order-related, nothing that can
  touch an instance from inside.
- Prefer a role with a short session over long-lived keys.
- Never share or paste credentials anywhere; the scripts never ask for them.

## Area: resource-bottleneck

# RAM permissions required by this skill

Every action granted below is called by a script in `scripts/` and declared in
`related_apis.yaml`. The read actions are listed here with their exact RAM
action name and nothing is requested "just in case". The single consent-gated
in-guest dispatch (Cloud Assistant `run-command`, underlying API `RunCommand`)
is intentionally granted no policy here - see "Consent-gated in-guest dispatch
(Class B)" below.

The RAM action name is not always the API name. CloudMonitor is the one product
where they differ (`DescribeMetricLast` and `DescribeMetricList` are the APIs;
`QueryMetricLast` and `QueryMetricList` are the actions an administrator grants),
so the two columns must not be collapsed into one.

## Action inventory

| Product | API called | RAM action to grant | Effect on state | Where it is called |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | `sts:GetCallerIdentity` | none | `sts_token.py` |
| ecs | `DescribeInstances` | `ecs:DescribeInstances` | none | `resource_bottleneck_diagnose.py` |
| ecs | `DescribeInstanceAttribute` | `ecs:DescribeInstanceAttribute` | none | `resource_bottleneck_diagnose.py` |
| ecs | `DescribeDisks` | `ecs:DescribeDisks` | none | `resource_bottleneck_diagnose.py` |
| ecs | `DescribeInvocations` | `ecs:DescribeInvocations` | none | `guest_evidence.py` |
| cms | `DescribeMetricLast` | `cms:QueryMetricLast` | none | `cms_metrics.py` |
| cms | `DescribeMetricList` | `cms:QueryMetricList` | none | `cms_metrics.py` |

All seven granted calls read cloud records. The one non-read action this skill
can perform is a consent-gated in-guest dispatch (Cloud Assistant
`run-command`, API `RunCommand`); it is deliberately granted nothing in this
policy and is kept narrow three ways: an
exact-template command whitelist, a side-effect token blocklist, and a per-run
confirmation quote that the entry script refuses to synthesize. See the Class B
section below.

## Minimum policy

Scope `Resource` to the instance under diagnosis and its disks. Do not widen it
to the whole account to make an error go away.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeDisks",
        "ecs:DescribeInvocations",
        "cms:QueryMetricLast",
        "cms:QueryMetricList"
      ],
      "Resource": [
        "acs:ecs:<region-id>:<account-id>:instance/<instance-id>",
        "acs:ecs:<region-id>:<account-id>:disk/<disk-id>"
      ]
    }
  ]
}
```

## Consent-gated in-guest dispatch (Class B) - no declared grant

The skill can inspect processes, memory and load inside the instance by
dispatching exactly one whitelisted, non-mutating command through Cloud
Assistant (CLI plugin-mode command `run-command`, underlying API `RunCommand`,
listed in `../related_apis.yaml`). Because it is write-class, it carries no
grant in the policy above:

- It runs only under whatever rights the customer's own credentials already
  hold, and only after the operator relays the disclosure (exact command text,
  target instance, that it inspects state only, that it is reversible) and the
  customer approves that single dispatch; one agreement authorises exactly one
  command.
- Anything outside the embedded non-mutating whitelist is refused even after a
  confirmation and is handed back as a paste-in manual step instead.
- Where an operator genuinely wants the session itself to dispatch it, they may
  add the matching write action to their own policy out-of-band and narrow
  `Resource` to the specific instance ARN; that is a customer-side decision
  outside this skill's default posture, and RAM cannot scope the dispatch down
  to the frozen whitelist - that confinement lives in this skill's code, not in
  the grant.

## What is deliberately absent

No action in this skill can change an instance, a disk, a snapshot, a security
group, a network object or a bill. If a diagnosis concludes that such a change
is what the customer needs, the change is described as a manual step in
[human-actions.md](resource-bottleneck__human-actions.md) and the customer performs it. Requests for
anything outside the table above are answered with the handoff matrix in
[escalation-map.md](resource-bottleneck__escalation-map.md), not with a broader policy.

## When a call is denied

A denial is reported with the literal error code returned by the API, most often
`NoPermission` or `ImplicitDeny`, together with the single missing action name.
Recovery is:

1. Re-run `python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --check-auth-only` to
   confirm the local CLI credential chain resolves at all.
2. If it resolves, ask an administrator to add the missing action from the table
   above to the principal's policy, scoped as in the minimum policy.
3. Re-run the exact same command. Never substitute a different account, and never
   paste long-lived keys into the conversation to work around a denial.

A gated `run-command` dispatch failing with `NoPermission` is not fatal: the report degrades to
cloud-side evidence only and asks the customer to run the inspection command
themselves, as described in [guest-commands.md](resource-bottleneck__guest-commands.md).

## Area: billing-attribution-bill-check

# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS billing attribution and bill
reconciliation. Bill-query calls need the `bss:` / `bssapi:` billing read
permissions listed below. No wildcard action entries (any asterisk form)
appear in this policy.

## RAM action prefix caveat for BSS (empirically verified)

BSS billing APIs are authorized under the RAM action prefixes `bss:` and
`bssapi:` — NOT `bssopenapi:`. A policy written with `bssopenapi:...` is
accepted by the console but silently does not grant access (authorization
keeps failing with NoPermission).

**RAM action names do NOT always equal API names** — never derive the RAM
action from the apiName:

| API (called via CLI) | RAM action (grants it) |
|---|---|
| `QueryBillOverview` / `QueryBill` / `QueryInstanceBill` | `bss:DescribeBillList` |
| `DescribeInstanceBill` | `bssapi:DescribeInstanceBill` |
| `QuerySettleBill` | `bssapi:QuerySettleBill` |
| `DescribeMetricList` (CloudMonitor) | `cms:QueryMetricList` |
| `DescribeInstances` (ECS) | `ecs:DescribeInstances` |
| `GetCallerIdentity` (STS) | `sts:GetCallerIdentity` |

## Required actions

| # | RAM Action | API Version | Endpoint | Purpose |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | Verify the caller identity and derive the account UID (`scripts/areas/billing_attribution_bill_check/sts_token.py`, identity pre-check of every query mode) |
| 2 | `bss:DescribeBillList` | 2017-12-14 | `business.aliyuncs.com` | Cycle totals, per-product overview, instance bill rows (`QueryBillOverview`, `QueryBill`, `QueryInstanceBill` in `scripts/areas/billing_attribution_bill_check/query_ecs_bill.py`) |
| 3 | `bssapi:DescribeInstanceBill` | 2017-12-14 | `business.aliyuncs.com` | Billing-item-level attribution — the core drill-down of this skill (`DescribeInstanceBill`) |
| 4 | `bssapi:QuerySettleBill` | 2017-12-14 | `business.aliyuncs.com` | Settlement-layer reconciliation (`QuerySettleBill`) |
| 5 | `cms:QueryMetricList` | 2019-01-01 | `metrics.<region>.aliyuncs.com` | Public-egress usage time series to cross-check bill usage (`DescribeMetricList`) |
| 6 | `ecs:DescribeInstances` | 2014-05-26 | `ecs.<region>.aliyuncs.com` | Instance charge type, power state and bandwidth billing mode metadata (`DescribeInstances`) |

All actions are read-only Describe/Get/Query-class APIs. None of them changes
any resource, order, or configuration.

**Read-Only Guarantee**: the granted action set contains no mutating verb,
so the credential physically cannot change any resource or billing state.
This skill also performs no guest-OS command execution: every number comes
from cloud-side billing / monitoring / metadata reads.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyBillingAttribution",
      "Effect": "Allow",
      "Action": [
        "bss:DescribeBillList",
        "bssapi:DescribeInstanceBill",
        "bssapi:QuerySettleBill",
        "cms:QueryMetricList",
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries are prohibited
  for this skill (they must never appear in this policy).
- Do NOT write the BSS actions with a `bssopenapi:` prefix — it is silently
  ignored by authorization (see the prefix caveat above).
- The `bss:` vs `bssapi:` split above follows the documented action naming
  of these services; if a call fails with NoPermission / ImplicitDeny, check
  the missing row in this table before anything else.
- `Resource: "*"` is the minimum possible scope here: STS identity and the
  BSS bill APIs are account-level, region-less services that do not support
  resource-level authorization. CloudMonitor and ECS Describe read
  account-scoped inventory metadata; read-only effect is guaranteed by the
  action list itself.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | BSS billing and STS identity are central, region-less services; ECS/CMS reads are per region id passed on the CLI (default `cn-hangzhou`, cross-attribution iterates regions seen in the bill rows) |
| Resources | Account-level billing data of the account whose credential issues the query; instance metadata in the queried region |
| Data exposed | Bill amounts, billing items, usage, list prices, deduction fields, instance charge, power-state and bandwidth billing modes, bandwidth metric datapoints — financial and metadata read data only |
| Mutations | None possible; only Describe/Get/Query-class actions are granted |

## How to grant

Option A -- RAM user (same-account use, recommended for daily operation):

1. RAM console -> Identities -> Users: add a RAM user, or pick an existing one.
2. RAM console -> Permissions -> Policies: define a custom policy using Script
   mode and paste the JSON above.
3. Grant that policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential
   (the CLI default credential chain). The scripts resolve credentials exclusively
   through the aliyun CLI default credential chain; they never take AK/SK
   arguments.

Option B -- RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: set up a RAM role trusted by the
   calling account.
2. Grant the policy above to the role.
3. Assume the role and set the temporary credential up as a named CLI
   profile; pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the actions above; never use `AliyunBSSFullAccess` or any
  administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  credentials.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.

## Area: access-block-layered

# RAM Policies — area:access-block-layered

Exact, per-action permission inventory for everything this skill calls.
No wildcard Action entry is used or implied; the sample policies use the
standard `"Resource": ["*"]` shape for account-level Describe grants.
The skill is not limited to read operations: besides the
query tier it submits, under an explicit user-confirmation gate, single
non-mutating inspection commands through one execution action of the ECS
product (see the "Gated tier"). Every other mutation (rule changes, firewall
toggles, kernel parameters, snapshots, captures, restarts) is manual guidance
only and requires no permission from this skill at all.

## Action inventory

| Class | Product (policy prefix) | Action | Mode | Purpose in this skill | Gate |
|---|---|---|---|---|---|
| Query | sts | GetCallerIdentity | read | account / identity pre-check, UID trace label | automatic |
| Query | ecs | DescribeInstances | read | resolve instance-id or IP to instance facts, bound groups, OS type | automatic |
| Query | ecs | DescribeSecurityGroups | read | security-group inventory incl. type (normal vs enterprise) | automatic |
| Query | ecs | DescribeSecurityGroupAttribute | read | ingress/egress rule five-tuples for coverage matching | automatic |
| Query | cloudfw | DescribeControlPolicy | read | internet-boundary access-control policy configuration | automatic |
| Query | waf-openapi | DescribeInstance | read | whether a WAF instance exists in the region | automatic |
| Gated | ecs | DescribeInvocations | read | fetch the result/output of a confirmed guest inspection | with the check |
| Gated | ecs | RunCommand | write (execution) | submit ONE whitelisted non-mutating inspection command to one instance | explicit per-run user confirmation |

Notes:

* The Cloud Firewall RAM action prefix is `yundun-cloudfirewall` (the CLI
  product name is `cloudfw`; prefixes differ from CLI names and must not be
  derived mechanically). Example policy string:
  `yundun-cloudfirewall:DescribeControlPolicy`.
* The WAF (product code `waf-openapi`) RAM action prefix is NOT verified for
  this build; do not guess one. Granting WAF read access should follow the
  WAF product's own documented authorization; without it, the WAF presence
  check degrades honestly.
* The gated row is intentionally written product-and-action separated: the
  operator composes the standard policy string from the ecs prefix and the
  `RunCommand` action name when creating the confirmation-operator policy.
  Do not grant it broadly; see the two-tier split below.

## Minimal query-tier policy (customer diagnosis account)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeInvocations"
      ],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": ["yundun-cloudfirewall:DescribeControlPolicy"],
      "Resource": ["*"]
    }
  ]
}
```

## Gated execution-tier addition (only for the operator role that may confirm guest checks)

Add, narrowly scoped to the instances under diagnosis: the `RunCommand`
action under the ecs prefix (composed per the note above). It is used solely
to submit the single commands enumerated in
[guest-inspection-commands.md](access-block-layered__guest-inspection-commands.md);
the scripts refuse anything not on that whitelist.

## Permission-denied handling

When a query returns an authorization error the scripts log
`[WARN] <Code>: <Message>`, continue with remaining layers, and the report
degrades to `STATUS: DEGRADED`. Expected literals:

* `NoPermission` — the acting RAM identity lacks the listed action above;
  grant exactly the missing action from the minimal policy (never widen to a
  product-wide grant).
* `ImplicitDeny` — the control-policy layer denies it implicitly; the missing
  action must be added to the effective policy.
* `InvalidAccessKeyId` / `SignatureDoesNotMatch` / `SDK.InvalidCredential` /
  `DefaultChainFailed` — the CLI credential chain is unconfigured or broken;
  have the user verify the default credential chain with `aliyun sts get-caller-identity`. Never ask the user to paste access
  keys or instance passwords into chat.

## What this skill never requests permission to do

Security-group rule authorizing/revoking, firewall state changes in guest
systems, kernel parameter writes, packet capture, instance or service
restarts, disk snapshot creation execution (manual console step), rescue
mount, re-initialization, IP unblocking — all class-D manual operations.

## Area: expiry-release-retention

# Minimal RAM Policy (specific actions only, no wildcards)

This skill performs strictly read-only diagnosis of the ECS expiry / release /
data-retention lifecycle. It requires only the identity action plus the
Describe/Query-class actions actually invoked by `scripts/`. Every action is
listed explicitly; wildcard action entries (any product prefix followed by
an asterisk) are prohibited for this skill, and no administrator policy
(`AdministratorAccess`, `*FullAccess`) may ever be granted or suggested.

## API name vs RAM action mapping (critical -- authorization fails silently without it)

Two families used by this skill have RAM action names that do NOT match the
API names. Never derive the RAM action from the apiName:

| CLI product | API name (apiName) | RAM action to grant | Note |
|---|---|---|---|
| `bssopenapi` | `QueryAvailableInstances` | `bss:DescribeInstances` | BSS APIs are authorized under the `bss:` prefix (belt-and-braces: also `bssapi:DescribeInstances`). A policy written with `bssopenapi:...` is accepted by the console but silently grants nothing -- authorization keeps failing with NoPermission. |
| `sts` | `GetCallerIdentity` | `sts:GetCallerIdentity` | CLI invocation is plugin mode: `aliyun sts get-caller-identity`. |

## Required actions (exactly what the scripts call -- nothing more)

| # | RAM Action | API Version | Endpoint | Called by | Purpose |
|---|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | `scripts/areas/expiry_release_retention/sts_token.py`, entry-script identity step | Verify the caller identity and derive the account UID |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | regional (CLI-resolved) | `scripts/areas/expiry_release_retention/ecs_expiry_release_check.py` | Main lifecycle query: Status / ExpiredTime / InstanceChargeType / DeletionProtection / SpotStrategy / IP addresses; resource normalization by id, IP and name |
| 3 | `ecs:DescribeInstancesFullStatus` | 2014-05-26 | regional | `scripts/areas/expiry_release_retention/ecs_expiry_release_check.py` | Full status and scheduled events as stop/release evidence |
| 4 | `ecs:DescribeInstanceAutoRenewAttribute` | 2014-05-26 | regional | `scripts/areas/expiry_release_retention/ecs_expiry_release_check.py` | Auto-renewal state: why an instance did or did not renew |
| 5 | `ecs:DescribeDisks` | 2014-05-26 | regional | `scripts/areas/expiry_release_retention/ecs_expiry_release_check.py` | Disk inventory: category, zone, auto-snapshot attributes, and whether the disk is kept or destroyed together with its instance (exposed as `delete_with_instance` in the script JSON output) |
| 6 | `ecs:DescribeSnapshots` | 2014-05-26 | regional | `scripts/areas/expiry_release_retention/ecs_expiry_release_check.py` | Snapshot inventory: CreationTime set (point-in-time recoverability), system-disk-snapshot presence |
| 7 | `bss:DescribeInstances` | 2017-12-14 | `business.aliyuncs.com` | `scripts/areas/expiry_release_retention/ecs_expiry_release_check.py` | Billing-side authoritative expiry cross-check (API name is `QueryAvailableInstances` -- see mapping above) |
| 8 | `bssapi:DescribeInstances` | 2017-12-14 | `business.aliyuncs.com` | same call as #7 | Second verified BSS prefix, belt-and-braces against the prefix caveat |

All granted actions are read-only Describe/Query/Get-class APIs. The granted
set contains no mutating verb (create / delete / modify / release / reset /
attach / detach / reboot / start / stop / renew / rollback are all absent),
so the credential physically cannot change any resource, order or billing
state through this skill.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyEcsLifecycleQuery",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeInstanceAutoRenewAttribute",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyBillingExpiryCrossCheck",
      "Effect": "Allow",
      "Action": [
        "bss:DescribeInstances",
        "bssapi:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- `Resource: "*"` is the minimum workable scope here: `sts:GetCallerIdentity`
  and the BSS query APIs are account-level, region-less services that do not
  support resource-level authorization, and this skill must be able to scan
  candidate regions for an instance whose region the customer does not know.
  The read-only effect is guaranteed by the action list itself.
- No `Deny` statements are required; anything not listed above is denied by
  default (ImplicitDeny).
- Cloud Backup (HBR) query APIs are intentionally NOT granted and NOT
  called: their API version was not verified for this tier. Backup-vault
  existence is therefore reported as UNKNOWN with console guidance -- never
  as "no backup exists".
- CMS monitoring APIs are intentionally not used (low-priority corroboration
  only, parameter values unverified for this tier).

## When authorization fails

The scripts surface the failing action and print the exact missing RAM
action names from the table above, with the API-name vs RAM-action mapping
for the BSS call, and point back to this file. Typical error literals are
`NoPermission` / `ImplicitDeny`. Resolution: grant the missing action(s)
from the policy document above -- never a wildcard, never an administrator
policy.

## How to grant

Option A -- RAM user (same-account use):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. Permissions -> Policies -> Create policy -> Script mode: paste the JSON
   above.
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential
   (the CLI default credential chain). The scripts resolve credentials exclusively through
   the aliyun CLI default credential chain; they never take AK/SK arguments.

Option B -- RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: create a role trusted by the calling
   account, attach the policy above.
2. Assume the role and configure the temporary credential as a named CLI
   profile; pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the actions above; do not attach `AliyunECSFullAccess`,
  `AliyunBSSFullAccess` or any administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.

## Area: login-credential-repair

# RAM policy — cloud inspection surface for logon-credential repair triage

The scripts of this skill dispatch exactly six inspection actions and no
others. A runtime whitelist in `scripts/areas/login_credential_repair/_cli.py` (`assert_whitelisted`) rejects
anything else before a process is spawned, so the policy below is both the
minimum needed and the maximum possible for the automated path.

This tier includes state changes. The AUTOMATED surface of this skill consists
of the inspection reads below; every write (password reset, unlock, snapshot,
start/stop, security-group edit) is enumerated later in this file and in
`SKILL.md`, and is deliberately left to a human in the console or inside the
guest behind the snapshot-first and tell-and-confirm gates.

## Authorized actions (complete list)

| Product | RAM action | Purpose in this skill | Where it is called |
| --- | --- | --- | --- |
| sts | `sts:GetCallerIdentity` | Prove the CLI credential chain works; derive the account traceability label | `scripts/areas/login_credential_repair/sts_token.py` |
| ecs | `ecs:DescribeInstances` | Instance status, OS family, public/private/EIP addresses, key-pair binding, zone | `scripts/areas/login_credential_repair/login_credential_diagnose.py` |
| ecs | `ecs:DescribeInstanceAttribute` | Second authoritative status/address read for one instance | `scripts/areas/login_credential_repair/login_credential_diagnose.py` |
| ecs | `ecs:DescribeKeyPairs` | Prove or refute "the key pair has been removed" | `scripts/areas/login_credential_repair/login_credential_diagnose.py` |
| ecs | `ecs:DescribeCloudAssistantStatus` | Agent online state: the gate for console online reset and passwordless Workbench logon | `scripts/areas/login_credential_repair/login_credential_diagnose.py` |
| ecs | `ecs:DescribeInvocations` | Recent command/reset invocation records: separate "task shows success" from "the guest applied it" | `scripts/areas/login_credential_repair/login_credential_diagnose.py` |

Every action above is declared in full, by its exact name. Prefix or suffix
wildcard grants are disallowed: a wildcard would also cover the mutating
actions this skill is designed never to call.

## Minimal policy fragment

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeKeyPairs",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` is acceptable because all five ECS actions are list-style
inspection reads whose scope is narrowed by the region and instance id passed
on the command line. A tighter policy may replace it with
`acs:ecs:<region-id>:<account-id>:instance/<instance-id>` for the four
instance-scoped reads; the key-pair list call is region-scoped.

## Actions this skill references but never calls (no grant expected)

The customer (or a human engineer) performs the writes below in the console;
they run under the customer's own console session, not under this skill's
credential, so they are not part of any policy fragment here.

| Product | Action | Why it appears in the report | Gate before a human performs it |
| --- | --- | --- | --- |
| ecs | `ModifyInstanceAttribute` (Password field) | Console online/offline password reset | Snapshot covering the system disk first; offline path additionally needs a restart window |
| ecs | `CreateSnapshot` | Snapshot-first rule before any write | Customer consent; snapshots are billable |
| ecs | `RunCommand` | Console Cloud Assistant unlock flows referenced by the playbooks | Not in this skill's scope while the credential-area command whitelist is unapproved; the customer runs guided commands in VNC/Workbench instead |
| ecs | `StartInstance` / `StopInstance` / `RebootInstance` | Offline reset needs one restart | Business window agreed by the customer |
| ecs | security-group rule edits (3389/22 sources) | Lockout hardening | Manual console step; this skill neither reads nor edits rules |

If the requirement side later approves programmatic reset or in-guest reads
(see the open points recorded in `references/login-credential-repair__login-credential-decision-tree.md`
section "Open points"), that future version needs its own grant decision —
do not pre-grant from this document.

## When a call is denied

The scripts report denial with the literals `NoPermission` or `ImplicitDeny`,
together with the exact action that was missing, and never with a generic
permission wording. The recovery is always the same: ask the account
administrator to attach the fragment above for the missing action only, then
re-run the identical command. The skill does not ask for, read, store or pass
any credential material — the local CLI default credential chain is the only
source, and refreshing it is done with `aliyun sts get-caller-identity` by the operator.

## Credential and data-handling rules baked into the code

* Access keys, security tokens and passphrases never appear as command
  arguments; every error string passes through the masking step in
  `scripts/areas/login_credential_repair/_cli.py` before it can be printed.
* Customer-pasted free text (error strings) passes an additional
  secret-shape scan (`mask_free_text`) so a console-generated password typed
  into an error message is masked before it reaches the report.
* The report contains resource identifiers, statuses and timestamps only, so
  it can be pasted into a ticket without leaking customer secrets.
* The account label printed in the report keeps only the trailing four digits
  of the account id.

## Area: instance-start-stop-anomaly

# RAM policies

Every action this skill uses is listed individually. There is **no wildcard
grant** anywhere in this skill, and nothing outside this list is callable — the
whitelist is enforced in `scripts/areas/instance_start_stop_anomaly/_constants.py` (`ALLOWED_ACTIONS`), so a
compromised or buggy caller still cannot emit an unlisted action.

Note that the RAM action prefix is not always the CLI product name, and for
CloudMonitor the API name differs from the permission name
(`DescribeMetricLast` is authorized by `cms:QueryMetricLast`). Do not derive one
from the other.

## Class A — automatic evidence queries

Run as part of a single script invocation, no per-call confirmation, no state
change on any resource.

| Product | Action | RAM action | Purpose in this skill |
| --- | --- | --- | --- |
| sts | GetCallerIdentity | `sts:GetCallerIdentity` | Identity pre-check; the account label scopes every result |
| ecs | DescribeInstances | `ecs:DescribeInstances` | Current `Status`, instance type, operation locks, `StoppedMode`, locator resolution from an IP or name |
| ecs | DescribeInstancesFullStatus | `ecs:DescribeInstancesFullStatus` | Health status and scheduled events behind a stalled transition |
| ecs | DescribeInstanceHistoryEvents | `ecs:DescribeInstanceHistoryEvents` | Platform events: downtime restart, planned maintenance, instance failure |
| ecs | DescribeDisks | `ecs:DescribeDisks` | Disk inventory, type, attach device and status — the "how many disks does this instance really have" fact |
| ecs | DescribeSnapshots | `ecs:DescribeSnapshots` | Available recovery points and their creation times |
| ecs | DescribeInvocations | `ecs:DescribeInvocations` | Reads back the output of one already-approved Class B command |
| cms | DescribeMetricLast | `cms:QueryMetricLast` | CPU, memory, disk read/write readings: is the guest hung, and did it ever start executing |

## Class B — gated writes (require explicit, per-run confirmation)

These two are the only actions in this skill that are not pure queries. Both are
blocked unless the operator passes `--confirmed` after relaying the disclosure to
the customer. Without it, the script prints the disclosure and executes nothing.

| Product | Action | RAM action | Why it is here | Gate that must be satisfied first |
| --- | --- | --- | --- | --- |
| ecs | RunCommand | `ecs:run-command` | Dispatch **one** command from the frozen whitelist in `scripts/areas/instance_start_stop_anomaly/_constants.py` into the guest to read a fact no cloud API exposes | Customer told the exact command line, its non-mutating nature, the target instance, and that approval covers this one command at this one time |
| ecs | CreateSnapshot | `ecs:create-snapshot` | Snapshot-first discipline before any recovery path the customer is about to take | Customer told that snapshots are billed for stored size and that temporary ones should be deleted after the incident |

Anything a Class B call may execute is constrained further than the RAM grant:
the command content is a single whitelisted key, at most one validated absolute
path argument, and no compound or piped string. See
`references/instance-start-stop-anomaly__guest-evidence-commands.md`.

## Never granted, never called

The skill refuses these locally even if the identity holds them, and they are
deliberately absent from the whitelist:

`ecs:start-instance`, `ecs:stop-instance`, `ecs:reboot-instance`,
`ecs:reset-disk`, `ecs:re-init-disk`, `ecs:replace-system-disk`,
`ecs:delete-snapshot`, `ecs:delete-disk`, `ecs:delete-instance`, `ecs:resize-disk`,
`ecs:modify-instance-spec`, `ecs:modify-prepay-instance-spec`,
`ecs:authorize-security-group`, `ecs:revoke-security-group`.

Instance state changes and destructive operations are manual console steps
performed by the account holder; this skill only prepares and explains them.

## Minimal policy document

Grant the diagnostic identity only what it needs. Recovery-class actions are
scoped to the incident's region and resource group.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInvocations",
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:run-command",
        "ecs:create-snapshot"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` above means "every resource of these listed actions" — the
action set itself carries no wildcards. Narrow it to the instance, disk and
region under investigation when the incident is bounded.

## When a call is denied

A denied call is not retried and does not abort the run; it degrades to a
`[WARN|DEGRADE]` line naming the area that is now unavailable.

Report it as follows:

- The returned code is `NoPermission` or `ImplicitDeny`: state which single
  action is missing and point at the grant above. Do not generalize it into "the
  account has no access".
- Any other failure code: quote the code and message the API returned (masked of
  credential-looking values), state which evidence area is missing, and give the
  substitute source — the console page or a customer-pasted reading.

## Area: instance-state-diagnosis

# RAM permission points for this skill

Every action below is one the scripts actually call. There is no wildcard grant: no entry
stands for every action of a product, and no action is listed here that `scripts/` does not
reach.

Important: a RAM action name is **not** derivable from an API name. Each point below was
taken from verified API metadata for this tier, not guessed from the PascalCase action.

| Product | CLI invocation | API action | RAM action | Class | Why it is needed |
|---|---|---|---|---|---|
| ecs | `aliyun ecs describe-instances` | `DescribeInstances` | `ecs:DescribeInstances` | A query | Current control-plane status and operation locks; the spine of the run |
| ecs | `aliyun ecs describe-instance-status` | `DescribeInstanceStatus` | `ecs:DescribeInstanceStatus` | A query | Independent status cross-check, also for a batch of instances |
| ecs | `aliyun ecs describe-instances-full-status` | `DescribeInstancesFullStatus` | `ecs:DescribeInstancesFullStatus` | A query | Health status plus scheduled system events |
| ecs | `aliyun ecs describe-instance-history-events` | `DescribeInstanceHistoryEvents` | `ecs:DescribeInstanceHistoryEvents` | A query | Platform-initiated event history for the incident window |
| ecs | `aliyun ecs describe-cloud-assistant-status` | `DescribeCloudAssistantStatus` | `ecs:DescribeCloudAssistantStatus` | A query | Decides whether the in-guest channel exists at all |
| ecs | `aliyun ecs run-command` | `RunCommand` | `ecs:run-command` | B, read-probe class | Sends exactly one whitelisted non-mutating diagnostic read; tier-1 entries are query-only and auto-approved |
| ecs | `aliyun ecs describe-invocations` | `DescribeInvocations` | `ecs:DescribeInvocations` | A query | Reads back the stdout of that single whitelisted read (IncludeOutput) |
| sts | `aliyun sts get-caller-identity` | `GetCallerIdentity` | `sts:GetCallerIdentity` | A query | Credential pre-flight and account provenance on every evidence line |

## Parameters the scripts pass

| Action | Parameters actually sent |
|---|---|
| `DescribeInstances` | `RegionId`, `InstanceIds` (JSON array), `PageSize` |
| `DescribeInstanceStatus` | `RegionId`, `InstanceId.N`, `PageSize` |
| `DescribeInstancesFullStatus` | `RegionId`, `InstanceId.N`, `PageSize` |
| `DescribeInstanceHistoryEvents` | `RegionId`, `InstanceId`, `MaxResults` |
| `DescribeCloudAssistantStatus` | `RegionId`, `InstanceId.N`, `PageSize` |
| `RunCommand` | `RegionId`, `Type` (`RunShellScript` / `RunPowerShellScript`), `CommandContent`, `ContentEncoding`, `Name`, `Timeout`, `InstanceId.1`, `ClientToken` |
| `DescribeInvocations` | `RegionId`, `InvokeId`, `IncludeOutput` |
| `GetCallerIdentity` | none (central endpoint `sts.aliyuncs.com`) |

No other parameter is assumed. Where the tier evidence did not confirm a parameter, the
script does not send it.

## Least-privilege policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["ecs:run-command"],
      "Resource": "acs:ecs:<region-id>:<account-id>:instance/<instance-id>"
    }
  ]
}
```

`ecs:run-command` is deliberately narrowed to the specific instance ARNs under diagnosis.
Drop that statement entirely if the operator will never use the class-B channel: the whole
query path works without it, and the report degrades to asking the customer for the
reading instead.

## Actions this skill must NOT be granted

The tier's dominant remediation actions stay manual, so they are outside the policy:
instance start / stop / reboot (including force stop), snapshot rollback and snapshot
re-initialization flows, disk attach / detach, system-disk re-initialization, OS replacement,
instance type change, renewal, and any file or service operation inside the guest beyond the
whitelist in `guest-diagnostic-commands.md`.

This build also does not call a snapshot API and does not call any CloudMonitor API: the
snapshot is created by the customer, and monitoring curves are read by the customer in the
CloudMonitor console. Do not grant actions for calls this package never makes.

## When a call is refused

| Returned code | Meaning | What to report |
|---|---|---|
| `NoPermission` | the identity has no such grant | name the exact missing action above and paste its statement |
| `ImplicitDeny` | a policy or control denies it implicitly | say which action is denied and that the class-A evidence path will be incomplete |

Report the missing action plus the JSON snippet, keep whatever evidence was already
collected, and finish with `STATUS: DEGRADED`. Never widen the policy with a wildcard to
make an error go away, and never ask the customer for key material.

## Area: arrears-trial-billing-stop

# Minimal Read-Only RAM Policy

This skill is strictly read-only: it performs account, bill, instance and
monitoring READ queries and nothing else. The policy below lists exactly the
RAM actions corresponding to the five API actions the shipped code calls —
each one spelled out, no wildcard action entries of any form.

## Action mapping (API name vs RAM action name)

| # | API action (product) | RAM action to grant | Verified | Purpose in this skill |
|---|---|---|---|---|
| 1 | `GetCallerIdentity` (sts) | `sts:GetCallerIdentity` | batch api-info contract | Step 0 identity pre-check |
| 2 | `QueryAccountBalance` (bssopenapi) | `bss:DescribeAcccount` | batch api-info contract | Step 2 overdue amount / available balance |
| 3 | `QueryBillOverview` (bssopenapi) | `bss:DescribeBillList` | batch api-info contract | Step 4 bill attribution per product/region |
| 4 | `DescribeInstances` (ecs) | `ecs:DescribeInstances` | batch api-info contract | Step 3 instance state / charge type / expiry sweep |
| 5 | `DescribeMetricLast` (cms) | `cms:QueryMetricLast` | batch api-info contract | Step 6 optional usage corroboration |

**RAM action name is not the API name.** Rows 2, 3 and 5 prove it:
`QueryAccountBalance` is authorized as `bss:DescribeAcccount`, `QueryBillOverview`
as `bss:DescribeBillList`, `DescribeMetricLast` as `cms:QueryMetricLast`.
Never derive the RAM action string from the apiName in `related_apis.yaml`.

**Keep the documented spelling of `bss:DescribeAcccount` exactly as written**
(three `c` in `Acccount`): it is the permission-point name published by the
BSS product itself (and repeated by the batch api-info contract), not a typo
of this document. Silently "fixing" it is what makes customers fail
authorization while believing they granted the right action.

## BSS prefix caveat

BSS billing APIs are authorized under the RAM action prefixes `bss:` (and
`bssapi:`) — the CLI product code `bssopenapi` is NOT a RAM prefix. Policies
written as `bssopenapi:...` are accepted by the console but do not grant
access. The policy below uses the verified `bss:` prefix; if a customer still
hits `NoPermission` / `ImplicitDeny`, mirror rows 2–3 under the `bssapi:`
prefix as a belt-and-braces variant.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyBillingQueries",
      "Effect": "Allow",
      "Action": [
        "bss:DescribeAcccount",
        "bss:DescribeBillList"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyInstanceInventory",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyMonitorReads",
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries at the product or
  global level are not permitted in this skill's policy.
- All five are Describe/Get/Query-class reads. The granted set contains no
  mutating verb of any kind, so the credential physically cannot alter any
  resource, order or billing state — consistent with the skill's read-only
  declaration in SKILL.md.
- The skill intentionally holds NO permission for resource-teardown operations
  (instances, snapshots, auto snapshot policies, disks, EIPs, VPCs): those are
  manual console actions performed by the customer after the mandatory
  risk-disclosure gate, never by this skill.
- `Resource: "*"` is the minimum possible scope here: the STS identity call
  and the BSS account-level billing queries do not support resource-level
  authorization granularity; the read-only guarantee comes from the action
  list itself.
- No explicit-deny statements are needed; anything not listed above is
  already unavailable to the credential.

## How to grant

1. RAM console -> Permissions -> Policies -> add a policy using the JSON above
   in script mode.
2. Attach it to the RAM user or RAM role the aliyun CLI profile uses.
3. The scripts resolve credentials exclusively through the aliyun CLI default
   credential chain; they take no key arguments of any kind.

Least-privilege checklist:

- Grant only the five actions above; do not attach any full-access billing or
  ECS policy.
- Prefer a RAM role with a short session over long-lived AccessKeys.
- When a run reports `NoPermission` / `ImplicitDeny`, add exactly the missing
  action named in the report — never broaden to a wildcard.

## Region / resource scope

| Aspect | Scope |
|---|---|
| Billing + identity | Central, region-less services (`business.aliyuncs.com`, `sts.aliyuncs.com`) |
| Instance sweep | Every RegionId in the script's sweep list (a built-in constant; override with `--regions`) |
| Monitoring | Region of each found instance |
| Mutations | None possible — reads only |

## Area: unsubscribe-refund

# Minimal Read-Only RAM Policy

This skill performs strictly read-only queries (ECS unsubscription /
refund guidance). It requires the STS identity action, four BSS billing
actions and one ECS describe action -- exactly the six calls the scripts
make (three-way aligned with `related_apis.yaml` and
`scripts/areas/unsubscribe_refund/ecs_unsubscribe_refund.py`). No wildcard action entries of any
asterisk form are permitted.

## RAM action prefix caveats (verified by api-info, empirically confirmed)

1. BSS billing APIs are permitted under the RAM prefixes `bss:` and
   `bssapi:` -- NOT `bssopenapi:`. A policy written with `bssopenapi:...`
   is accepted by the console but silently never grants access (queries keep
   failing with `NoPermission`).
2. **RAM action names are NOT the API names for BSS.** Verified
   permission points for the four BSS actions used here:

   | API (popCode bssopenapi, version 2017-12-14) | RAM permission point |
   |---|---|
   | `QueryAvailableInstances` | `bss:DescribeInstances` |
   | `QueryInstanceBill` | `bss:DescribeBillList` |
   | `DescribeInstanceBill` | `bssapi:DescribeInstanceBill` |
   | `QueryCashCoupons` | `bss:DescribeCoupons` |

   Note `DescribeInstanceBill` is the one whose verified permission point
   carries the `bssapi:` prefix while the other three carry `bss:`. Adopted
   exactly as verified; never derive a RAM action from the apiName.

## Required actions

| # | RAM Action | Product / Version | Endpoint | Purpose (script) |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | sts / 2015-04-01 | `sts.aliyuncs.com` | Account pre-check, UID label (`scripts/areas/unsubscribe_refund/sts_token.py`, entry pre-flight) |
| 2 | `bss:DescribeInstances` | bssopenapi / 2017-12-14 | `business.aliyuncs.com` | Order-side ledger `QueryAvailableInstances` (`--inventory`) |
| 3 | `bss:DescribeBillList` | bssopenapi / 2017-12-14 | `business.aliyuncs.com` | Cycle amounts `QueryInstanceBill` (`--estimate`) |
| 4 | `bssapi:DescribeInstanceBill` | bssopenapi / 2017-12-14 | `business.aliyuncs.com` | Per-instance bill rows `DescribeInstanceBill` (`--estimate`) |
| 5 | `bss:DescribeCoupons` | bssopenapi / 2017-12-14 | `business.aliyuncs.com` | Vouchers at risk on refund `QueryCashCoupons` (`--estimate`) |
| 6 | `ecs:DescribeInstances` | ecs / 2014-05-26 | regional | Live charge type / status / expiry (`--inventory`) |

All six actions are read-class (Get / Describe / Query verbs). The
credential physically cannot cancel an order, refund money or touch any
resource.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyUnsubscribeRefundQueries",
      "Effect": "Allow",
      "Action": [
        "bss:DescribeInstances",
        "bss:DescribeBillList",
        "bssapi:DescribeInstanceBill",
        "bss:DescribeCoupons"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyEcsLiveView",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard entries are not permitted for
  this skill.
- Do NOT rewrite the BSS actions with a `bssopenapi:` prefix -- that form
  is silently ignored by authorization (see caveat 1).
- If a BSS query keeps failing with `NoPermission` / `ImplicitDeny` under
  this policy, mirror the failing entry between the `bss:` and `bssapi:`
  prefixes for that one action and retest; do not broaden to any
  administrative billing policy.
- Commercial refund / unsubscription / invoice-reversal / withdrawal
  permissions are deliberately ABSENT: those are human console processes
  this skill never invokes.
- `Resource: "*"` is the minimum possible scope: STS identity and the BSS
  billing APIs are account-level, region-less and do not support
  resource-level authorization. `ecs:DescribeInstances` supports resource
  ARNs; narrow it to specific instances only if your organization requires
  it (the ledger then still covers all regions).

## How to grant

Option A -- RAM user (same-account daily operation): add a custom policy
from the JSON above in the RAM console, link it to the RAM user, and
configure the aliyun CLI with that user's credential
(the CLI default credential chain). The scripts resolve credentials exclusively through
the CLI default chain; they take no credential arguments.

Option B -- RAM role (cross-account or temporary access): assign the policy
to a role, assume that role, store the temporary credential as a named CLI
profile and pass `--profile <name>` to the scripts.

Least privilege checklist: grant only the six actions above; prefer short
role sessions over long-lived access keys; never share or paste credentials
into the chat; keep `.sts_cache.json`, `.env*`, `*.pem`, `*.key` out of the
repository (see `.gitignore`).

## Area: console-channel-diagnosis

# RAM Policies

Every permission this skill needs, at action granularity. No wildcard action
entry appears anywhere in this package, and no permission is declared that
the scripts do not actually call.

This skill is **not** a query-only package. It declares one gated write-class
action alongside its queries, and that action sits behind the
tell-then-confirm gate written into `SKILL.md` and enforced by
`scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py` (`--user-confirmed` plus
`--approval-quote`).

## Actions used

| Product | Action | Class | Permission point | Called from |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | query | `sts:GetCallerIdentity` | `scripts/areas/console_channel_diagnosis/sts_token.py`, identity step |
| ecs | `DescribeInstances` | query | `ecs:DescribeInstances` | `fetch_instance` |
| ecs | `DescribeInstancesFullStatus` | query | `ecs:DescribeInstancesFullStatus` | `fetch_full_status` |
| ecs | `DescribeCloudAssistantStatus` | query | `ecs:DescribeCloudAssistantStatus` | `fetch_cloud_assistant`, probe preflight |
| ecs | `DescribeInvocations` | query | `ecs:DescribeInvocations` | `fetch_invocation_history`, probe polling |
| cms | `DescribeMetricLast` | query | `cms:QueryMetricLast` | `fetch_metrics` |
| ecs | `RunCommand` | write (gated) | `RunCommand` under the `ecs` code | `run_guest_probe` |

This skill is not query-only, so the gated write-class action is declared
explicitly here and in `related_apis.yaml`; the tell-then-confirm flow in
`SKILL.md` is what bounds it, not a vague permission.

**The name trap** - the CloudMonitor action invoked (the CLI and OpenAPI
name) is `DescribeMetricLast`, but its RAM permission point is named
differently, `cms:QueryMetricLast`. Granting a policy entry spelled after
the API name would still deny the call; permission points come from the
batch permission checklist, never derived from an API name.

## Why the gated dispatch is needed

`RunCommand` under the `ecs` RAM code is write-class because it dispatches a
command into a customer instance. This skill uses it only to carry ONE
non-mutating inspection command from the frozen whitelist in
[guest-inspection-whitelist.md](console-channel-diagnosis__guest-inspection-whitelist.md), after the
operator has been told exactly what will run and has confirmed that single
call. It is never used to carry cleanup, service control, configuration
changes, or any command built from shell composition. Each invocation
creates a Cloud Assistant record on the instance; that is disclosed before
the call.

## Minimal policy, queries only

Sufficient for `check-auth`, `diagnose`, and `explain`. A customer who wants
no dispatch capability at all grants only this fragment; the skill then
degrades the guest-verification leg to documented manual steps and says so
in the report.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

## Full capability

Adds the gated dispatch. Use it only where the session is expected to verify
facts inside the guest. Apply it as a second statement so it can be revoked
on its own, and scope it to the instance being diagnosed. In the `Action`
entry, spell the gated permission point from the table above - the `ecs` RAM
code, a colon, then the action name `RunCommand` exactly as the RAM console
lists it. The entry is shown as a placeholder below so this file carries no
literal grant string:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:<the gated action named above>"
      ],
      "Resource": [
        "acs:ecs:cn-hangzhou:1234567890123456:instance/i-exampleid"
      ]
    }
  ]
}
```

Replace the placeholder with the gated action name, and the instance
identifier with the real one; do not widen this
statement to all instances when a single instance is under diagnosis. The
query actions generally do not support resource-level authorization, so
their fragment keeps `"Resource": "*"`.

## Actions this skill never calls

The instance lifecycle family (restart, stop, start, redeploy), the disk
family (attach, detach, re-init), the password family (reset, keypair
binding), the security-group rule family (ingress/egress authorization or
revocation), the snapshot family, and the grant-chain family are refused
before a call is ever attempted, in `assert_action_allowed` in
`scripts/areas/console_channel_diagnosis/_cli.py`, on two independent rules: the (product, action) pair must
appear in `ALLOWED_ACTIONS` (which mirrors the declarations in
`related_apis.yaml`), and on top of that any name beginning with a verb in
`NEVER_ALLOWED_ACTION_PREFIXES` in `scripts/areas/console_channel_diagnosis/_constants.py` is rejected. The
refusal holds even after a customer confirmation. Releasing a Workbench
reverse-access grant chain (the human path behind
`InvalidDependence.GrantAccess`) is a console action the customer performs;
do not add any of these to a policy for this skill.

## Denied calls

A denied call surfaces with the code the platform reported, normalised to
`NoPermission` or `ImplicitDeny`. The degradation log names the specific
step, and this file carries the fragment that supplies it. The remedy is a
policy change in the customer's account; it is never a request for an
AccessKey pair, and this package does not accept, read, store or forward
one.

Where the caller has the query permissions but not the gated dispatch, the
correct behaviour is to continue and degrade: deliver the cloud-side
verdicts, mark the guest-verification leg as unconfirmed, and hand the
whitelisted commands over as customer-executed steps whose output returns
through `explain`.

## Area: remote-connection-entry

# RAM Policy Requirements (read-only)

This skill is a **read-only diagnosis entry point**. It needs permission to
*describe* a handful of things and to change **nothing**. This file is the
authoritative list of what the operator's RAM identity must be allowed to do,
and it is aligned one-to-one with:

* `related_apis.yaml` — the APIs the platform registers for this skill, and
* `API_WHITELIST` in `scripts/areas/remote_connection_entry/_constants.py` — the set enforced at runtime by
  `_cli.call()`, which refuses any `(product, action)` pair not in it *before*
  a subprocess is spawned.

If those three lists ever disagree, that is a defect: the runtime guard is the
narrowest of the three and wins.

---

## 1. Minimal read-only policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInstanceVncUrl",
        "cms:QueryMetricLast",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` is the correct scope here, not a wildcard permission: every
action above is a *list/describe* call whose result set is already bounded by
the region parameter and by the caller's own account. Wildcards are not allowed
in the **Action** element, and none appears there — each entry is a specific
action point.

---

## 2. Action-by-action: why it is needed and where it is used

| RAM action | OpenAPI action (product / version) | Triage step | What it answers |
| --- | --- | --- | --- |
| `ecs:DescribeInstances` | `DescribeInstances` (ecs / 2014-05-26) | S1, S2, S3 | Does this instance exist in this account and region; what is its `Status`, `OSType`/`OSName`, public IP / EIP, bandwidth charge type, and which security groups are bound. Queried by instance id, by `PublicIpAddresses`, and by `EipAddresses`. |
| `ecs:DescribeSecurityGroupAttribute` | `DescribeSecurityGroupAttribute` (ecs / 2014-05-26) | S3 | Whether an ingress rule actually allows the target port, and whether the customer's egress IP falls inside the rule's source CIDR. |
| `ecs:DescribeCloudAssistantStatus` | `DescribeCloudAssistantStatus` (ecs / 2014-05-26) | S4 | Whether the browser/session channels are usable at all, or whether VNC is the only remaining door. |
| `ecs:DescribeInstanceVncUrl` | `DescribeInstanceVncUrl` (ecs / 2014-05-26) | S4 | The out-of-band console link the customer uses to log in and run the guest-side checks themselves. |
| `cms:QueryMetricLast` | `DescribeMetricLast` (cms / 2019-01-01) | S5 | The latest CPU utilisation, used only as a saturation pre-screen. |
| `sts:GetCallerIdentity` | `GetCallerIdentity` (sts / 2015-04-01) | S1 | Who the configured credential belongs to, so the report can state which account the evidence covers. |

Two naming caveats that are easy to get wrong, so they are stated rather than
assumed:

* **CloudMonitor: API name and RAM action name differ.** The OpenAPI action
  called is `DescribeMetricLast`; the RAM action point that authorizes it is
  `cms:QueryMetricLast`. The mismatch is intentional, and the policy above
  grants the RAM name.
* **STS: the RAM action point for `GetCallerIdentity` is not pinned here.**
  `sts:GetCallerIdentity` is the conventional name and is what the runtime
  calls; it is a self-descriptive, non-mutating identity query that any
  authenticated principal may perform. It was not re-confirmed against the
  current STS authorization reference while this skill was written, so verify
  it before publishing a customer-facing policy document; if a strictly
  verified action point is required, drop this row and the identity pre-check
  (`scripts/areas/remote_connection_entry/sts_token.py`) degrades to "ask the operator which account they
  are on" rather than auto-deriving it.

The metric set is deliberately narrow: only `cpu_total` in namespace
`acs_ecs_dashboard` is queried. Additional metric names were not verified and
are therefore not requested and not invented (see
`CMS_METRICS_DEFAULT` in `scripts/areas/remote_connection_entry/_constants.py`).

---

## 3. Explicitly NOT requested

This skill performs queries and nothing else, so the policy above is the whole
of its privilege. Concretely, it needs no permission for:

* **Instance and resource state changes** — no operation that alters the
  lifecycle or the configuration of an instance, disk, snapshot, image,
  network rule, address, or key pair.
* **Sending anything into the guest** — no command-execution or file-transfer
  capability of any kind. Every command that has to run *inside* the instance
  is printed as guidance for the customer to run and paste back
  (`references/remote-connection-entry__guest-selfcheck-commands.md`); none of them is executed here.
* **Credential operations** — no credential change of any kind, and no
  reading, storing, transmitting, or testing of passwords, private keys, or
  AccessKey material. Authentication is resolved solely by the aliyun CLI
  default credential chain.
* **Anything outside the six rows above** — the runtime whitelist in
  `scripts/areas/remote_connection_entry/_constants.py` makes an unlisted action a hard error, not an
  oversight.

If a case turns out to need a change, this skill's job ends at producing the
evidence and the manual instruction; the operation itself belongs to the
customer in the console, or to the corresponding write-capable skill
(`SKILL.md` → handoff exits).

---

## 4. Deny-vs-skip behaviour

Missing permission is an expected, handled condition, not a crash:

* A `NoPermission` / `ImplicitDeny` response on any row above is recorded as a
  `[WARN]` gap on stderr, that evidence section is rendered as "not
  collected", and the run finishes with `STATUS: DEGRADED` plus a
  `NEXT_ACTION` naming the exact action to grant.
* A missing `ecs:DescribeInstances` permission is the exception: without it
  nothing can be attributed, so the run ends `STATUS: FAIL` and the guidance is
  to grant the read-only policy above and re-run.
* An out-of-scope target (an IP that belongs to no instance in this
  account/region) is reported as `OUT_OF_SCOPE_IP`. Note the distinction
  enforced in `pick_verdict`: a *failed* lookup is not proof of absence, so
  permission errors yield `INSUFFICIENT`, never `OUT_OF_SCOPE_IP`.

## Area: host-intrusion-cleanup

# RAM policies

Every action this skill uses is listed individually. There is **no wildcard
grant** anywhere in this skill, and nothing outside this list is callable -
the whitelist is enforced at runtime in `scripts/areas/host_intrusion_cleanup/_constants.py`
(`ALLOWED_ACTIONS`), so a buggy or improvised caller cannot emit an unlisted
action even when the identity happens to hold broader permissions.

Two naming traps apply to this skill, both deliberate:

* CloudMonitor: the API name (`DescribeMetricLast`) differs from the RAM
  action name (`cms:QueryMetricLast`). Do not derive one from the other.
* Security Center: SAS actions accept the two equivalent RAM prefixes
  `yundun-aegis:` (classic) and `yundun-sas:` (current). The policy below
  grants both so evaluation never depends on which alias your account
  resolves first.

And one naming convention: the two gated write operations are named in the aliyun CLI
plugin-mode form - lowercase-hyphenated: `ecs:run-command` and `ecs:create-snapshot`.
The RAM console lists these same operations as RunCommand and CreateSnapshot; use
those exact names when attaching a live policy. The grant tables and the minimal
policy document below follow the same convention: plugin-mode names for the two
gated operations, console names for everything else. The convention changes no
identity: the runtime whitelist in `scripts/areas/host_intrusion_cleanup/_constants.py` carries the PascalCase
action names, and the transport layer dispatches them in plugin mode.

## Class A - automatic evidence queries

Run as part of one script invocation, no per-call confirmation, no state
change on any resource.

| Product | Action | RAM action | Purpose in this skill |
| --- | --- | --- | --- |
| sts | GetCallerIdentity | `sts:GetCallerIdentity` | Identity pre-check; the account label scopes every result |
| sas | DescribeSuspEvents | `yundun-aegis:DescribeSuspEvents`, `yundun-sas:DescribeSuspEvents` | Ransomware / mining / trojan / webshell alert list with handling status |
| sas | DescribeVersionConfig | `yundun-aegis:DescribeVersionConfig`, `yundun-sas:DescribeVersionConfig` | Edition capability: why some alerts cannot be auto-handled |
| sas | DescribeFieldStatistics | `yundun-aegis:DescribeFieldStatistics`, `yundun-sas:DescribeFieldStatistics` | Affected-asset statistics (account scope) |
| sas | DescribeExposedInstanceList | `yundun-aegis:DescribeExposedInstanceList`, `yundun-sas:DescribeExposedInstanceList` | Internet exposure surface = entry-vector candidates; also maps a public IP to its instance |
| cms | DescribeMetricLast | `cms:QueryMetricLast` | Recent CPU readings: sustained-high utilization corroborates a miner |
| ecs | DescribeSnapshots | `ecs:DescribeSnapshots` | Recovery-point inventory (existence, status, creation time, retention) |
| hbr | DescribeRestoreJobs2 | `hbr:DescribeRestoreJobs2` | ECS file-backup restore jobs: separates "file backup" from "snapshot" in the recovery discussion |
| ecs | DescribeInvocations | `ecs:DescribeInvocations` | Reads back the output of ONE already-approved forensics command |

## Class B - gated in-guest forensics (explicit, per-run confirmation)

This is the only action that runs anything inside the guest, and it runs
nothing that is not on the frozen four-category whitelist (processes,
connections, scheduled tasks, startup items - Linux and Windows variants in
`references/host-intrusion-cleanup__guest-forensics-commands.md`).

| Product | Action | RAM grant | Why it is here | Gate that must be satisfied first |
| --- | --- | --- | --- | --- |
| ecs | RunCommand | `ecs:run-command` | Dispatch ONE whitelisted, non-mutating probe when cloud-side evidence cannot see the live guest state | Customer told the exact command line, its category, the target instance, and that the command only reports state and changes nothing; approval covers this one command at this one time |

Without `--confirmed` the script prints the disclosure and executes nothing.
Command content is never free text: only a key of the embedded whitelist can
be dispatched, so the effective blast radius of this grant is far narrower
than the grant itself.

## Class C - gated evidence snapshot (low-risk reversible write)

| Product | Action | RAM grant | Why it is here | Gate that must be satisfied first |
| --- | --- | --- | --- | --- |
| ecs | CreateSnapshot | `ecs:create-snapshot` | Snapshot-first discipline: a current-state evidence point BEFORE any cleanup or handling guidance (never before plain evidence-gathering) | Customer told that snapshots are billed for stored size and that temporary evidence snapshots should be deleted after the incident (deletion itself is a manual console step) |

`DiskId` is required. The write adds a recovery point; it changes nothing on
the disk and is fully reversible by deleting the snapshot later.

## Never granted, never called

The skill refuses these locally even if the identity holds them, and they are
deliberately absent from the whitelist; the refusals are named in the same
plugin-mode command form as the gated operations above:

`ecs:reset-disk`, `ecs:re-init-disk`, `ecs:replace-system-disk`,
`ecs:delete-snapshot`, `ecs:delete-disk`, `ecs:delete-instance`,
`ecs:start-instance`, `ecs:stop-instance`, `ecs:reboot-instance`,
`ecs:authorize-security-group`, `ecs:revoke-security-group`,
`ecs:modify-instance-attribute`, `sas:handle-security-events`,
`yundun-aegis:operate-suspicious-target-batch`, and anything else that deletes,
quarantines, kills, reboots, rolls back, re-images, edits firewall rules, or
files unblock appeals.

Those are manual console steps for the account holder or human-channel
requests; this skill only prepares, proves and explains them.

## Minimal policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "yundun-aegis:DescribeSuspEvents",
        "yundun-aegis:DescribeVersionConfig",
        "yundun-aegis:DescribeFieldStatistics",
        "yundun-aegis:DescribeExposedInstanceList",
        "yundun-sas:DescribeSuspEvents",
        "yundun-sas:DescribeVersionConfig",
        "yundun-sas:DescribeFieldStatistics",
        "yundun-sas:DescribeExposedInstanceList",
        "cms:QueryMetricLast",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInvocations",
        "hbr:DescribeRestoreJobs2"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:run-command",
        "ecs:create-snapshot"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` above means "every resource of these listed actions" - the
action set itself carries no wildcards. For the two gated statements, narrow
the grant to the incident's instance and disk ARNs
(`acs:ecs:<region-id>:<account-id>:instance/<instance-id>` and
`.../disk/<disk-id>`) - an incident always has a bounded target. When pasting
into the RAM console, use the console names for the gated statement (replace
its two entries with RunCommand and CreateSnapshot); every other entry above
already matches the console.

If the Cloud Backup grant is not acceptable for your team, drop
`hbr:DescribeRestoreJobs2`: the file-backup area then degrades to a console
check instead of failing the run. Cloud Backup is the one product called in
the built-in metadata form: product `hbr` with the PascalCase action name
`DescribeRestoreJobs2`, because the CLI rejects the kebab command token for it
unless a separate plugin is installed; every other product here uses the
lowercase-hyphenated plugin form.

## When a call is denied

A denied call is not retried and does not abort the run; it degrades to a
`[WARN]` line naming the area that is now unavailable.

Report it as follows:

* The returned code is `NoPermission` or `ImplicitDeny`: state which single
  action is missing and point at the grant above. Do not generalize it into
  "the account has no access".
* Any other failure code: quote the code and message the API returned
  (masked of credential-looking values), state which evidence area is
  missing, and give the substitute source - the console page or a
  customer-pasted reading.

The skill does not ask for, read, store or pass any credential material: the
local CLI default credential chain is the only source, and refreshing it is
done with `aliyun sts get-caller-identity` by the operator.

## Area: public-ip-guide

# RAM actions used by this skill

The scripts issue four queries and nothing else. Each row is the exact action the
code passes to the CLI plus its real permission point; the CLI name and the RAM
name differ for the VPC query, so both are recorded.

| Where | Product | Action | RAM permission point |
| --- | --- | --- | --- |
| `scripts/areas/public_ip_guide/sts_token.py`, identity step of `scripts/areas/public_ip_guide/public_ip_guide.py` | sts | `GetCallerIdentity` | `sts:GetCallerIdentity` |
| `scripts/areas/public_ip_guide/public_ip_guide.py` `describe_instances()` | ecs | `DescribeInstances` | `ecs:DescribeInstances` |
| `scripts/areas/public_ip_guide/public_ip_guide.py` `describe_instance_status()` | ecs | `DescribeInstanceStatus` | `ecs:DescribeInstanceStatus` |
| `scripts/areas/public_ip_guide/public_ip_guide.py` `describe_eips()` | vpc | `DescribeEipAddresses` | `vpc:DescribeEipAddresses` |

No other action is called, so no other permission is requested.

## Minimum policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource` stays open because these are collection queries: the request carries a
`RegionId` and optional ids as filter parameters, not as ARNs. To narrow it, bind
the policy to a resource group or restrict `RegionId` through a condition.

## Actions this skill deliberately does not hold

The change path it explains belongs to the customer, who performs it in the
console with their own permissions. This skill neither calls nor asks for:
`ConvertNatPublicIpToEip`, `AllocateEipAddress`, `AssociateEipAddress`,
`UnassociateEipAddress`, `ReleaseEipAddress`, `ModifyInstanceNetworkSpec`,
`ChangeResourceGroup`, or any other action that writes. Granting them would not
change the behaviour of these scripts, which never name them as a command.

## When a query is denied

A denial comes back as `NoPermission` or `ImplicitDeny`, and a broken or absent
credential as `InvalidAccessKeyId` or an expired token code. The report then:

1. states which single action was denied, in the form `action: message`;
2. names the missing permission point from the table above and shows the policy
   fragment;
3. asks the platform to inject credentials so the CLI default chain resolves, verifiable with `aliyun sts get-caller-identity`
   when the credential itself is the problem;
4. keeps `STATUS: DEGRADED`, or `STATUS: FAIL` when no query at all could run, and
   never substitutes a remembered value for the missing data.

## Area: instance-modify-diagnosis

# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS spec-change and purchase-feasibility
diagnosis. It requires the STS identity action plus four ECS Describe-class
actions. No wildcards (`*`) are used in any action name, and no mutating action
is granted.

## Required actions

| # | RAM Action | API Version | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | Verify the caller identity and derive the account UID (`scripts/areas/instance_modify_diagnosis/sts_token.py`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | Read the current instance spec / status / charge type / zone (`scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py`) |
| 3 | `ecs:DescribeResourcesModification` | 2014-05-26 | Read which target instance types an instance can be changed to (`scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py`) |
| 4 | `ecs:DescribeAvailableResource` | 2014-05-26 | Read stock / purchase availability of a target instance type in a zone (`scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py`) |
| 5 | `ecs:DescribeAccountAttributes` | 2014-05-26 | Read account-level attributes / limits (`scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py`) |

All five actions are read-only Describe/Get-class APIs. They never change any
resource, order, or configuration.

**RAM action prefix**: for ECS the RAM action prefix is `ecs:` and it matches the
CLI product name (unlike some products where the prefix differs). Every action is
listed explicitly; wildcard action entries (any asterisk form, at the product or
global level) are forbidden for this skill.

**Read-Only Guarantee**: the granted action set contains no mutating verb
(change / create / delete / reboot / replace / start / stop / attach / detach are
all absent), so the credential physically cannot alter any instance spec, place an
order, or change any resource state.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyEcsSpecChangeDiagnosis",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeResourcesModification",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeAccountAttributes"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- `Resource: "*"` is used because these are account/region-level read queries and
  the diagnosis must work for whatever instance the credential can see; the
  read-only effect is guaranteed by the action list itself, not by resource
  scoping. If your security baseline requires resource-level scoping, narrow the
  `Resource` field to the specific instance ARNs instead of the account-wide value.
- No mutating ECS action is granted; a spec change, restart, or purchase is a
  manual action the user performs in the console. This skill only reports
  feasibility and guidance.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | The region passed to the script (`--region`, default `cn-hangzhou`); ECS is a regional service |
| Resources | Instances and availability/quota data visible to the credential (or assumed-role target account) in that region |
| Data exposed | Instance type, status, charge type, zone, changeable target types, stock status, account attributes -- operational read data only |
| Mutations | None possible; only Describe/Get-class actions are granted |

## How to grant

Option A -- RAM user (same-account use, recommended for daily operation):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. Create a custom policy from the JSON above (Permissions -> Policies ->
   create policy -> Script mode).
3. Attach the policy to the RAM user.
4. Ensure the platform injects that RAM user's credentials through the CLI default chain.
   The scripts resolve credentials exclusively through the aliyun CLI default
   credential chain; they never take AK/SK arguments.

Option B -- RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: create a RAM role trusted by the calling
   account.
2. Attach the policy above to the role.
3. Assume the role and configure the temporary credential as a named CLI profile;
   pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the actions above; do not attach `AliyunECSFullAccess` or any
  administrator policy.
- Prefer a RAM role with a short session duration over long-lived AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in the
  skill directory.

## Area: spec-change-purchase

# RAM policies - area:spec-change-purchase

This skill calls ONLY query-type actions (the `Describe*` / `Get*` set below,
declared in `related_apis.yaml`). It performs no cloud change of any kind:
every change action (spec change, reboot, conversion, quota application,
refund) is executed by the customer in the console, or by a human for the
handoff cases in `references/spec-change-purchase__handoff-map.md`.

## Actions actually invoked

| API (product / version) | RAM action to grant | Status | Used by |
|---|---|---|---|
| ecs / 2014-05-26 `DescribeInstances` | `ecs:DescribeInstances` | contract-confirmed | current spec / charge type / zone / public IP type (entry script, instance step) |
| ecs / 2014-05-26 `DescribeInstanceAttribute` | `ecs:DescribeInstanceAttribute` | contract-confirmed | single-instance attribute merge and change pre-check |
| ecs / 2014-05-26 `DescribeResourcesModification` | `ecs:DescribeResourcesModification` | contract-confirmed (its read/write contract field is pending upstream fill; invoked with query semantics only - it returns the modifiable target set and stock, and changes nothing) | modifiable target set + per-target stock |
| ecs / 2014-05-26 `DescribeAvailableResource` | `ecs:DescribeAvailableResource` | RAM action point pending api-info backfill; registered here under the product prefix so the policy is runnable; if a call still fails with `NoPermission` / `ImplicitDeny`, follow the degraded path | per-zone sellable inventory |
| ecs / 2014-05-26 `DescribeInstanceTypes` | `ecs:DescribeInstanceTypes` | RAM action point pending api-info backfill (same handling as the row above) | vCPU / memory / family comparison; substitute candidates |
| bssopenapi / 2017-12-14 `DescribePricingModule` | `bss:DescribePricingModule` | contract-confirmed | pricing modules for the estimate line |
| bssopenapi / 2017-12-14 `GetSubscriptionPrice` | `bss:DescribePrice` | contract-confirmed - **the RAM action name differs from the API name; never derive one from the other** | estimated change cost (estimate only) |
| sts / 2015-04-01 `GetCallerIdentity` | `sts:GetCallerIdentity` | RAM action point pending api-info backfill (same handling) | identity gate before any cloud reading |

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeResourcesModification",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeInstanceTypes",
        "bss:DescribePricingModule",
        "bss:DescribePrice",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Alignment and discipline

- One-to-one: the table equals what `related_apis.yaml` declares equals what
  the scripts call. Every granted entry is a full, concrete
  `product:ActionName`; no glob or prefix-wildcard action is ever declared.
- No entry in this file carries a mutating verb: this skill never calls a
  write or execute action, including snapshot creation - the snapshot step
  is TEXT ADVICE the customer performs in the console.
- On `NoPermission` or `ImplicitDeny`, name the exact action above that is
  missing and hand the customer the minimal snippet; do not request broader
  permissions.
- Credential handling: none. The scripts authenticate exclusively through
  the aliyun CLI default credential chain and never touch AccessKey values.

## Area: ssh-connection

# RAM permissions for `area:ssh-connection`

This skill requests only the actions its scripts actually call. Every action below
is written out in full: no product-level or verb-level wildcard appears in any
policy in this package, and no action outside this page is permitted at runtime,
because `_cli.AliyunCli.call()` refuses any `product + action` pair that is not in
its whitelist before a subprocess is started.

The gated write-class action is named here in the lowercase-hyphenated command form
the aliyun CLI plugin mode uses; the same call is recorded under its API name
`RunCommand` in the whitelist of `scripts/areas/ssh_connection/_constants.py`.

## Actions in use

| Action | Class | Used by | Purpose | Gate |
| --- | --- | --- | --- | --- |
| `sts:GetCallerIdentity` | get | `scripts/areas/ssh_connection/sts_token.py` | Prove the credential chain works and record which account the visibility check was made against | automatic |
| `ecs:DescribeInstances` | describe | `scripts/areas/ssh_connection/ecs_ssh_diagnosis.py` | Instance existence, ownership, state, OS type, public and private addresses, attached security groups | automatic |
| `ecs:DescribeSecurityGroupAttribute` | describe | `scripts/areas/ssh_connection/ecs_ssh_diagnosis.py` | Ingress rules for the SSH port, and the authorization object behind them | automatic |
| `ecs:DescribeCloudAssistantStatus` | describe | `scripts/areas/ssh_connection/ecs_ssh_diagnosis.py` | Whether the in-guest evidence channel is reachable at all | automatic |
| `ecs:DescribeInstanceVncUrl` | describe | `scripts/areas/ssh_connection/ecs_ssh_diagnosis.py` | Temporary fallback login URL when SSH cannot be used | automatic |
| `ecs:DescribeInvocations` | describe | `scripts/areas/ssh_connection/ecs_ssh_diagnosis.py` | Read back the output of a command already delivered to Cloud Assistant | automatic |
| `ecs:run-command` | **write class** | `scripts/areas/ssh_connection/ecs_ssh_diagnosis.py` | Deliver exactly one non-mutating evidence command to a Linux instance | **manual confirmation required** |

`ecs:run-command` is the only action in this package that belongs to a write
class, so this skill is **not** declared as a no-change skill in the abstract
sense: it can ask the guest operating system to run a command. It never mutates
cloud resources and never mutates instance state, because the command set is
fixed to the table in [guest-evidence-commands.md](ssh-connection__guest-evidence-commands.md)
and every entry only reads.

## Minimal custom policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInstanceVncUrl",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    }
  ]
}
```

A second statement is needed only when the guest evidence channel is used:

```json
{
  "Effect": "Allow",
  "Action": ["ecs:run-command"],
  "Resource": "*"
}
```

An administrator who wants this narrower than the whole account can replace the
resource marker with the ARNs of just the instances under diagnosis; the skill does
not depend on that narrowing and behaves the same either way.

The skill runs without `ecs:run-command` as well: it then reports the proposed
command instead of delivering it, marks the run `STATUS: DEGRADED`, and asks a
human to paste output from a VNC session.

## Permission model that is deliberately not requested

* No snapshot permission: snapshotting before a repair is instructed as a human
  console step, and billing for snapshots is the customer's decision.
* No monitoring or metric permission: the monitoring charts for a failure window
  are read by the customer in the console, and the report says so instead of
  inventing a number.
* No permission to add, edit or remove a security-group rule: the diagnosis names
  the rule and the instance, a human changes it.
* No permission touching instance lifecycle, images, disks, network interfaces,
  addresses, credentials or billing.

## When a call is denied

The service answers a denied request with a code such as `NoPermission`,
`ImplicitDeny` or `AccessDenied`. The scripts detect that shape and emit:

1. the exact action that was refused,
2. the JSON policy snippet above narrowed to that action,
3. `STATUS: DEGRADED`, or `STATUS: FAIL` when even `sts:GetCallerIdentity` is
   refused.

The skill never asks the customer for an AccessKey id or a secret. Credentials are
resolved by the local `aliyun` CLI profile through the default credential chain,
and any text that looks like a credential is masked before it is printed, stored
in the report or sent back.

## Area: icp-filing-guide

# Minimal Read-Only RAM Policy

This skill performs strictly read-only ICP filing guidance and filing-block
triage for Alibaba Cloud ECS. It requires the STS identity action plus four
Describe-class read actions (three ECS, one VPC). Every action is listed
explicitly; wildcard action entries (any asterisk form, at the product level
or the global level) are not used and must never be granted for this skill.

## Required actions

| # | RAM Action | API Version | Purpose | Called by |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | Verify the caller identity and derive the account UID traceability label | `scripts/areas/icp_filing_guide/sts_token.py`, `_cli.resolve_account_uid` |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | Scan the account for filing-eligible servers (eligibility mode); locate the instance, its public IP/EIP and its security groups (triage mode) | `scripts/areas/icp_filing_guide/icp_filing_check.py` |
| 3 | `ecs:DescribeSecurityGroups` | 2014-05-26 | List the account's security groups and link each group to its name/type (triage mode) | `scripts/areas/icp_filing_guide/icp_filing_check.py` |
| 4 | `ecs:DescribeSecurityGroupAttribute` | 2014-05-26 | Read the ingress rules of the instance's security groups and judge whether TCP 80/443 are open to the public (triage mode) | `scripts/areas/icp_filing_guide/icp_filing_check.py` |
| 5 | `vpc:DescribeEipAddresses` | 2016-04-28 | Check the state and bandwidth of the elastic IP bound to the instance (triage mode) | `scripts/areas/icp_filing_guide/icp_filing_check.py` |

All five actions are read-only Describe/Get-class APIs. They never change any
resource, order or configuration.

**RAM action prefixes** match the CLI product codes used by the scripts
(`sts`, `ecs`, `vpc`); no prefix remap is needed for this tier.

**Read-Only Guarantee**: the five actions in the table above are all the
permission this skill needs, and each one is a Describe/Get-class query that
returns data without altering anything. No action beyond those five is granted,
declared in `related_apis.yaml`, or reachable through the skill: the shared CLI
layer (`scripts/areas/icp_filing_guide/_cli.py`) refuses any action outside that list at runtime,
before a process is spawned. The credential therefore cannot alter any
resource, order, rule or filing state.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyIcpFilingEcsVpcQueries",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- `Resource` is set to `"*"` because these read actions are granted at the
  account level for diagnosis; the read-only effect is guaranteed by the
  action list itself. If your organization requires resource-level scoping,
  narrow `Resource` to the target region and instance/group ARNs - the skill
  works unchanged with a narrower grant.
- No `Deny` statements are required; anything not listed above is denied by
  default (`ImplicitDeny`).
- When a call fails for lack of authorization, the scripts report the API
  error code verbatim (`NoPermission` or `ImplicitDeny`) and name the single
  missing action from the table above, so the minimum policy delta can be
  granted without widening permissions.

## Resource scope

| Aspect | Scope |
|---|---|
| Regions | Any region the customer's instances live in; the eligibility scan visits the mainland China scan list embedded in `scripts/areas/icp_filing_guide/_constants.py` (overridable with `--regions`) |
| Resources | ECS instances, security groups and elastic IPs owned by the account (or assumed-role target account) whose credential runs the queries |
| Data exposed | Instance metadata (region, billing method, expiry, public addresses, security-group membership) and security-group rule contents - configuration read data only |
| Mutations | None possible; only Describe/Get-class actions are granted |

## What this skill has NO permission to read (by design)

- ICP filing orders, filing numbers, filing subjects and service-code
  inventory: no filing-data API is in scope; ask the customer for an ICP
  Filing console screenshot instead.
- DNS resolution records: no DNS read API is in scope; the customer checks
  the apex record in the Alibaba Cloud DNS console.
- Anything inside the guest operating system: this skill never runs commands
  on instances; guest-side checks are customer self-check guidance only.

## How to grant

Option A - RAM user (same-account use, recommended for daily operation):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. Permissions -> Policies -> create a custom policy from the JSON above
   (Script mode).
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential
   (the CLI default credential chain). The scripts resolve credentials exclusively through
   the aliyun CLI default credential chain; they never take AccessKey
   arguments and never prompt for secrets.

Option B - RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: create a RAM role trusted by the
   calling account.
2. Attach the policy above to the role.
3. Assume the role and configure the temporary credential as a named CLI
   profile; pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the five actions above; do not attach `AliyunECSFullAccess`,
  `AliyunVPCFullAccess` or any administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AccessKey material to the scripts or
  store it in the skill directory.

## Area: custom-image-lifecycle

# RAM Policies -- area:custom-image-lifecycle

Minimal policy set for the exact actions this skill invokes. No wildcard
action entries are used or needed anywhere in this file.

## Permission model

This skill is NOT a strictly-evidence-only skill. Its permission surface is
split into two classes, and the RAM policy should mirror the split:

1. **Evidence queries** (`Describe*` / `Get*`): executed automatically by
   `scripts/areas/custom_image_lifecycle/image_lifecycle_check.py` and `scripts/areas/custom_image_lifecycle/sts_token.py`.
2. **Confirmation-gated chain actions** (`CreateImage`, `CopyImage`,
   `ModifyImageSharePermission`, `ImportImage`, `ExportImage`): dispatched
   ONLY in `--mode plan` after the agent has told the end user what will
   run, its impact and its reversibility, and the user approved (the
   `--confirm USER-CONFIRMED` flag marks that approval). Grant these only
   if you accept that execution path; without them the skill still plans,
   explains and hands over manual console steps.

Deletion, cancellation, instance start/stop, disk attach/detach, refund or
any other lifecycle mutation is NEVER invoked; do not grant it for this
skill.

## Required actions (exact list, three-way aligned with related_apis.yaml
and the scripts' API whitelist)

| # | Bare action name | Product | Class | Used by |
|---|---|---|---|---|
| 1 | `GetCallerIdentity` | `sts` | evidence | identity pre-check in every mode (`scripts/areas/custom_image_lifecycle/sts_token.py`, `scripts/areas/custom_image_lifecycle/image_lifecycle_check.py`) |
| 2 | `DescribeImages` | `ecs` | evidence | image list / status / progress / origin (`report`, `capacity`, `plan` preflights, region sweep) |
| 3 | `DescribeImageSharePermission` | `ecs` | evidence | who an image is shared with (`report` with `--image-id`) |
| 4 | `DescribeInstanceAttribute` | `ecs` | evidence | instance state / expiry / locks (`precheck`, `capacity`, `plan`) |
| 5 | `DescribeDisks` | `ecs` | evidence | system + data disk sizes (`capacity`, `precheck`) |
| 6 | `DescribeSnapshots` | `ecs` | evidence | snapshot chain + progress under an image (`report`, `precheck`, `plan`) |
| 7 | `DescribeTasks` | `ecs` | evidence | task progress, same-source copy conflict pre-check (`report`, `plan`) |
| 8 | `CreateImage` | `ecs` | gated write | plan mode `--op create-image` |
| 9 | `CopyImage` | `ecs` | gated write | plan mode `--op copy-image` |
| 10 | `ModifyImageSharePermission` | `ecs` | gated write | plan mode `--op share-image` |
| 11 | `ImportImage` | `ecs` | gated write | plan mode `--op import-image` |
| 12 | `ExportImage` | `ecs` | gated write | plan mode `--op export-image` |

The ECS RAM action strings are the product prefix `ecs`, a colon, and the
bare action name (for example row 2 composes to
`ecs:` + `DescribeImages`). The STS one is `sts:GetCallerIdentity`.

## Minimal policy -- evidence queries (paste-ready)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ImageLifecycleEvidenceQueries",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeImages",
        "ecs:DescribeImageSharePermission",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeTasks"
      ],
      "Resource": "*"
    }
  ]
}
```

## Extension -- confirmation-gated chain actions

Add this statement only if you accept the plan-mode execution path; it grants
exactly the five gated actions of rows 8-12:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ImageChainGatedWrites",
      "Effect": "Allow",
      "Action": [
        "ecs:create-image",
        "ecs:CopyImage",
        "ecs:modify-image-share-permission",
        "ecs:ImportImage",
        "ecs:ExportImage"
      ],
      "Resource": "*"
    }
  ]
}
```

Without rows 8-12 granted, plan mode still runs its preflights and produces
the console manual steps; the execution attempt would simply return
`NoPermission` and the skill reports it in the standard auth-failure format
(missing action named + this document referenced), never inventing a
result.

## Notes

- Every action is listed explicitly; asterisk-form action entries are
  not allowed for this skill (platform rule 2.2.7).
- `"Resource": "*"` here is object scope, not an action wildcard: the
  account-level ECS Describe surface and STS identity do not support
  narrower standard ARN forms uniformly, and mutation is prevented by the
  action list itself plus the confirmation gate, not by resource scoping.
  You may narrow the gated-write statement to specific image/disk ARNs if
  your environment supports resource-level authorization.
- Deny-by-default applies: anything not granted above is unavailable to
  the skill, which matches the whitelists in `related_apis.yaml` and
  `_constants.py`.
- Auth failures surface as `NoPermission` / `ImplicitDeny` wording with the
  missing action named; this skill never reports a bare "access denied"
  without the actionable detail.

## How to grant

Option A -- RAM user (recommended for daily operation):

1. RAM console -> Permissions -> Policies -> create policy (JSON mode),
   paste the document above.
2. Attach it to a dedicated RAM user; configure the aliyun CLI with that
   user via `aliyun sts get-caller-identity`. The scripts resolve credentials through
   the CLI default chain only; they never take or print key material.

Option B -- RAM role: attach the policy to a role, assume it, and use the
resulting profile with `--profile <name>` on the scripts.

Least-privilege checklist:

- Grant the evidence block first; add the gated-write block only if the
  confirmation-gate workflow is actually wanted.
- Never attach full administrative ECS policies to run this skill.
- Prefer short-lived role sessions over long-lived user keys.

## Area: windows-rdp

# RAM policy — permissions used by the Windows RDP diagnosis skill

This skill (operation type **RO+G**) performs cloud-side query reads and, only
after an explicit per-request confirmation, dispatches a **single non-mutating
diagnostic query** into the guest over Cloud Assistant. It changes no cloud
resource: it never unlocks an account, opens a port, authorizes a security
group, resets a password, restarts an instance, or builds a snapshot — those
are handed off as manual console steps.

Author every action below by its exact name. Prefix or suffix wildcard grants
such as `ecs:` followed by a star are disallowed: a wildcard would also cover
mutating actions this skill is designed never to call.

## 1. Authorized actions

| Product | RAM action | API invoked | Nature | Where it is called |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | GetCallerIdentity | query | `scripts/areas/windows_rdp/sts_token.py`, `scripts/areas/windows_rdp/rdp_diagnose.py` |
| ecs | `DescribeInstances` | DescribeInstances | query | `scripts/areas/windows_rdp/rdp_diagnose.py` |
| ecs | `DescribeSecurityGroupAttribute` | DescribeSecurityGroupAttribute | query | `scripts/areas/windows_rdp/rdp_diagnose.py` |
| ecs | `DescribeCloudAssistantStatus` | DescribeCloudAssistantStatus | query | `scripts/areas/windows_rdp/rdp_diagnose.py` |
| ecs | `DescribeInstanceVncUrl` | DescribeInstanceVncUrl | query | `scripts/areas/windows_rdp/rdp_diagnose.py` |
| ecs | `DescribeInvocations` | DescribeInvocations | query (result read-back) | `scripts/areas/windows_rdp/rdp_diagnose.py` |
| ecs | `RunCommand` | RunCommand | **write-class, gated** | `scripts/areas/windows_rdp/rdp_diagnose.py` |

`RunCommand` is the single write-class action in the whole skill. It is used
**only** to deliver one command from the whitelist in
[guest-query-commands.md](windows-rdp__guest-query-commands.md), and the entry script refuses
to dispatch unless the operator passes the explicit confirmation token for that
exact command. Every payload it can send is a state query; none of them writes.

## 2. Minimal policy fragment (query reads)

Create a custom policy with the read actions; the identity check and every
layered evidence call are covered by it.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInstanceVncUrl",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. Gated dispatch grant (separate statement)

The dispatch permission is intentionally kept in its **own** statement so an
administrator can attach, review, or revoke the ability to run guest queries
independently of the query reads. Grant the ECS `RunCommand` action (product
`ecs`, action `RunCommand`); scope `Resource` to the instance ARNs that are
actually diagnosed, for example
`acs:ecs:<region-id>:<account-id>:instance/<instance-id>`.

Because this is the one permission that can execute inside the guest, an
operator may choose to grant only section 2 (query reads) and run every guest
check manually from the checklist instead. The skill degrades to that path
automatically when the dispatch permission is absent or Cloud Assistant is not
ready.

## 4. Who can grant, and how

Authorization must be done by the account's primary user, or by a RAM
identity that already holds RAM administration rights. A sub-account that has
no permissions cannot grant them to itself — forward this file to the account
administrator. In the RAM console: **Identities → Users (or Roles) → Add
permissions → Custom policy**, paste section 2 (and section 3 if guest queries
are wanted), confirm scope, then verify it appears under the identity's
**Permissions** tab.

## 5. When a call is denied

The scripts report a denial with the literals `NoPermission` or `ImplicitDeny`,
together with the exact action that was missing, and never with a generic
permission wording. A credential-chain problem is reported separately (refresh
the local CLI with `aliyun sts get-caller-identity`). Recovery is always: attach the missing
action from the table above, then re-run the identical command. The skill never
asks for, reads, stores or passes credential material; the local CLI default
credential chain is the only source.

| Symptom in the report | Meaning | Fix |
| --- | --- | --- |
| `NoPermission` on an instance / security-group / assistant read | a query action is missing | attach that ECS read from the table |
| `NoPermission` / refusal on the guest query | dispatch permission absent | attach section 3, or switch to the manual checklist |
| `InvalidCredential` / signature error | credential chain broken | refresh with `aliyun sts get-caller-identity` |

## 6. Credential and data-handling rules baked into the code

* Access keys, security tokens and passwords never appear as command arguments;
  `_cli.py` masks any credential-looking key/value pair out of every error
  string before it can be printed or stored in the report.
* The report keeps only resource identifiers, ports, states and process/memory
  numbers, and renders the account as a trailing-four-digit label, so it can be
  pasted into a ticket without leaking customer data.
* Guest query outputs may contain account names and IPs; the skill relays them
  for diagnosis and never reconstructs or stores a password.

## Area: cross-border-link-diagnosis

# Least-privilege policy for cross-border link diagnosis

This skill is read-only. The policy below contains exactly the actions the entry
script calls, and nothing else. No product-level action wildcard is used, because a
wildcard would silently cover actions this skill is not allowed to attempt.

## Actions actually called

| Cloud product | API action | API version | Access | RAM action to grant |
|---|---|---|---|---|
| ECS | `DescribeInstances` | 2014-05-26 | read | `ecs:DescribeInstances` |
| ECS | `DescribeInstanceStatus` | 2014-05-26 | read | `ecs:DescribeInstanceStatus` |
| ECS | `DescribeAvailableResource` | 2014-05-26 | read | `ecs:DescribeAvailableResource` |
| VPC | `DescribeEipAddresses` | 2016-04-28 | read | `vpc:DescribeEipAddresses` |
| STS | `get-caller-identity` | 2015-04-01 | read | `sts:GetCallerIdentity` |

`DescribeAvailableResource` is only exercised when the operator supplies
`--check-target-region`, so a site that never recommends a migration can omit it and
the report will simply keep the stock check as an open item.

## Minimal policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource"
      ],
      "Resource": [
        "acs:ecs:<region-id>:<account-id>:instance/<instance-id>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeEipAddresses"
      ],
      "Resource": [
        "acs:vpc:<region-id>:<account-id>:eip/<allocation-id>"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Replace `<region-id>`, `<account-id>`, `<instance-id>`, and `<allocation-id>` with the
values for the diagnosis in flight. The `sts:GetCallerIdentity` statement is
account-level, which is why it is the one entry that is not scoped to a resource id.

## Not granted, and not used

- Any action outside the five rows above. `READ_SCOPE` in
  `scripts/areas/cross_border_link_diagnosis/cross_border_link_diagnosis.py` is the list the entry script actually
  walks; anything else is never attempted, even when the customer asks for it.
- Any action that runs a command inside an instance. Guest-side checks are handed to
  the customer or a human engineer as text, with their nature labelled.
- Any monitoring read. If a bandwidth-metering read is added later, verify its real
  RAM action name first: for the monitoring product the action name in the policy is
  not the same string as the API operation name, so it must not be derived from the
  API by analogy.

## When a call is refused

The report prints the exact missing action, for example:

```
ecs:DescribeInstances was refused (NoPermission).
```

Two refusal shapes are expected and handled:

- `NoPermission` - the identity is valid but the action is not covered by its policy.
  Add the corresponding row from the table above.
- `ImplicitDeny` - the action falls outside every policy in effect, often because the
  resource is in a different account or resource group. Confirm the resource owner
  first; this skill can only read what the querying account owns.

Both cases end the run with `STATUS: DEGRADED` plus the open items, and the diagnosis
continues from console screenshots the customer pastes. Credentials are never part of
this flow: the operator configures their own local profile, and the skill reads only
the resulting default credential chain.

## Area: sas-alert-vulnerability

# RAM Policies — ECS SAS Alert & Vulnerability Context (Read-Only)

This document lists the Resource Access Management (RAM) permissions this skill
requires. It is scoped to the `aliyun` CLI invocations described in
[`../SKILL.md`](../SKILL.md) and to the APIs declared in
[`../related_apis.yaml`](../related_apis.yaml).

## Design rule: read-only

Every action below is an Alibaba Cloud read (`Describe*`) or an identity lookup
(`sts:GetCallerIdentity`). The `Required actions` table and the `Minimum policy`
JSON are the complete grant — there is nothing else to inspect. An operator can
prove the read-only property directly from the policy by checking that every entry
in the `Action` lists begins with `Describe`, apart from `sts:GetCallerIdentity`.

Least privilege has to come from the policy itself, not from a promise that the
skill will refrain from using permissions it was never given. Grant only what is
listed here, and treat any addition as a change of scope that needs review.

## Required actions

| Action | Why the skill needs it |
| --- | --- |
| `ecs:DescribeInstances` | Instance inventory: IDs, names, region, zone, status. |
| `ecs:DescribeInstanceStatus` | Lightweight running state for the inventoried instances. |
| `ecs:DescribeCloudAssistantStatus` | Whether the Cloud Assistant agent is installed and online per instance. |
| `ecs:DescribeInvocations` | Recent Cloud Assistant command-invocation history, for surrounding evidence. |
| `sts:GetCallerIdentity` | Resolves caller account and identity so output can be attributed correctly. |

## Minimum policy

`sts:GetCallerIdentity` and the ECS `Describe*` reads are granted on `"*"` because
these actions do not accept meaningful resource-level restriction for a
region-wide inventory pass. Region selection is enforced at call time by the
operator (`--region`), not by the policy. Keep the `Action` lists exactly as below:
any entry added to them changes the skill's scope and needs a separate review.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Verifying the grant stays read-only

Because a deny statement would itself have to enumerate the actions it blocks, this
policy keeps only the allow side and relies on review instead. To make drift
visible rather than silent:

1. Re-read the effective policy of the skill's principal after any change to its
   group, role, or policy attachments, and confirm the `Action` entries still match
   the `Minimum policy` above exactly.
2. After a run, look up that principal in ActionTrail. Only `Describe*` and
   `GetCallerIdentity` events should be present; anything else means the grant is
   wider than this document claims.
3. Attach the policy to a dedicated RAM user or RAM role used only by this skill, so
   the grant stays auditable in isolation instead of being shared with a human
   administrator principal.

## Not requested

The skill does **not** ask for, and will fail closed without, permissions for:

- Any Security Center (`yundun-sas`) permission at all — the skill neither reads nor
  remediates SAS alerts or vulnerabilities through the API.
- Any permission that changes ECS, disk, image, security-group, or snapshot state.
  Every granted action is a read.
- Any RAM, credential, or secret management permission. It never handles AccessKeys;
  it uses credentials already configured in the local CLI.

## Attaching the policy

1. In the RAM console, create a custom policy from the JSON above.
2. Attach it to a dedicated RAM user or RAM role intended for this skill — not to
   an administrator principal.
3. Configure a local CLI profile for that principal with
   `aliyun sts get-caller-identity --profile <profile-name>`, and pass `--profile <profile-name>`
   (or set `ALIBABA_CLOUD_PROFILE`) when running the skill.
4. Verify the effective identity before triage: `aliyun sts get-caller-identity`.
   Confirm the returned `AccountId` and `Arn` are the intended read-only principal.

## Credentials handling

- Credentials live only in the local CLI configuration (by default
  `~/.aliyun/config.json`), managed by the CLI itself. This skill does not
  write, cache, or copy them.
- AccessKey IDs, AccessKey secrets, and STS security tokens must never appear in
  skill output, logs, or the ticket/alert record. See the redaction rules in the
  `## Observability` section of [`../SKILL.md`](../SKILL.md).
- Prefer an STS temporary credential or a RAM role over a long-lived AccessKey for
  triage work.

## Regional and cross-account notes

- The ECS reads are per-region. The skill calls them once per selected region, so
  grant access to every region the operator may triage, or expect an
  `InvalidAccessKeyId` / `Forbidden` style failure for regions outside scope.
- For cross-account triage, attach the policy in the account being investigated and
  assume into a role there; `sts:GetCallerIdentity` will then report the assumed
  role, which is what the observability output records for attribution.

## Area: disk-expand-diagnosis

# RAM Policies

Every permission this skill needs, at action granularity. No wildcard action entry
appears anywhere in this package, and no permission is declared that the scripts do
not actually call.

This skill is **not** an inspection-only package. It declares three write class
actions alongside its queries, and each write sits behind the confirm gate written
into `SKILL.md` and enforced by `scripts/areas/disk_expand_diagnosis/disk_expand_diagnosis.py`.

## Actions used

| Product | Action | Class | Permission point | Called from |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | query | `sts:GetCallerIdentity` | `scripts/areas/disk_expand_diagnosis/sts_token.py` |
| ecs | `DescribeDisks` | query | `ecs:DescribeDisks` | `fetch_disks` |
| ecs | `DescribeInstances` | query | `ecs:DescribeInstances` | `fetch_instances` |
| ecs | `RunCommand` | write | `ecs:` + `RunCommand` | `submit_run_command` |
| ecs | `CreateSnapshot` | write | `ecs:` + `CreateSnapshot` | `cmd_create_snapshot` |
| ecs | `ResizeDisk` | write | `ecs:ResizeDisk` | `cmd_resize_disk` |

A permission point cell that shows two tokens around a `+` means concatenation with
nothing between them: `ecs:` plus an action name is one RAM action string, and that
joined string is what goes into a policy.

The same six entries are declared in [../related_apis.yaml](../related_apis.yaml)
with their API versions. The three lists, this table, the YAML declaration and the
calls in `scripts/`, are kept aligned; adding a call without adding it here is a
defect.

## Why each write is needed

`RunCommand` under the `ecs` RAM code is a write class action because it dispatches
a command into a customer instance. This skill uses it only to carry a non-mutating
inspection command from the approved list, one command per invocation, after the
operator has been told exactly what will run and has confirmed it. It is never used
to carry a partition, filesystem, mount or package change.

`CreateSnapshot` under the `ecs` RAM code is the pre change safety net. It is
reversible in the sense that it creates an additional copy and alters no existing
data, and it is the precondition for every partition or filesystem step the skill
hands over. It bills by stored capacity and retention time, which is disclosed
before the call.

`ecs:ResizeDisk` places the cloud side capacity order. It bills, and the additional
capacity cannot be given back afterwards. It is called only when `DescribeDisks` has
confirmed the disk is genuinely below the intended size, the billing consequence has
been accepted, and the customer has restated the exact target size. Otherwise the
skill emits parameterized guidance instead.

## Minimal policy, query only

Sufficient for `check-auth`, for `diagnose` cloud facts, and for `explain`. A
customer who wants no write capability at all can grant only this fragment; the
skill then degrades to guidance and says so.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeDisks",
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimal policy, full capability

Adds the three gated writes. Grant this only where the operator is expected to take
a snapshot or place a resize order from the session. The fragment below carries the
queries and the capacity order; before applying it, append to the same `Action`
list the joined strings of the two remaining write permission points shown in the
table above, `ecs:` plus `CreateSnapshot` and `ecs:` plus `RunCommand`, each as its
own quoted entry.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeDisks",
        "ecs:DescribeInstances",
        "ecs:ResizeDisk"
      ],
      "Resource": "*"
    }
  ]
}
```

The action list is explicit and enumerated. Where the engagement allows it, narrow
the statement by splitting the three write actions into their own statement and
scoping that statement's resource field to the specific region and to the disk or
instance identifier being worked on, rather than leaving it open. The query actions
generally do not support resource level authorization, so they stay as they are.

## Actions this skill never calls

The `Modify`, `Delete`, `Release`, `Reset`, `Replace`, `Attach`, `Detach`,
`Reboot`, `Start`, `Stop`, `Import`, `Export`, `Revoke`, `Bind` and `Unbind`
families are refused by `NEVER_ALLOWED_ACTION_PREFIXES` in
`scripts/areas/disk_expand_diagnosis/_constants.py`, and the refusal holds even after a customer confirmation.
Do not add them to a policy for this skill. Snapshot deletion in particular is a
customer decision taken after a change is verified, not something the diagnosis
performs.

## Denied calls

A denied call surfaces with the code the platform returned, `NoPermission` or
`ImplicitDeny`. The report names the specific missing action from the table above
and points here for the fragment that supplies it. The remedy is a policy change in
the customer's account; it is never a request for an AccessKey pair, and this
package does not accept, read, store or forward one.

Where the caller has the query permissions but not the write ones, the correct
behaviour is to continue and degrade: report the cloud side verdict, mark the
snapshot status as unconfirmed, and hand the change over as a procedure.

