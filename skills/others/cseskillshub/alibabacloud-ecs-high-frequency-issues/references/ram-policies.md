# RAM permissions for alibabacloud-ecs-high-frequency-issues (union of 55 areas, per-area sections
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

## Area: web-service-runtime-config
# RAM actions this skill needs

Every action below is one that `scripts/` actually issues, and every action the
scripts issue is listed here. No action is a wildcard: granting a whole product
prefix would hand a diagnostic skill far more than it needs, and the two writing
actions are scoped to the single resource the customer names.

The action names on the right of a colon are RAM action names, which do not
always match the API operation name. The CloudMonitor row is the one that
catches people out.

## Actions and their gates

| Cloud API operation | RAM action | Effect class | Gate in this skill |
|---|---|---|---|
| `sts get-caller-identity` (plugin-mode command) | `sts:GetCallerIdentity` | account self-check | automatic |
| `ecs DescribeInstances` | `ecs:DescribeInstances` | describes state | automatic |
| `ecs DescribeSecurityGroupAttribute` | `ecs:DescribeSecurityGroupAttribute` | describes rules | automatic |
| `ecs DescribeDisks` | `ecs:DescribeDisks` | describes attachments | automatic |
| `ecs DescribeInvocations` | `ecs:DescribeInvocations` | describes past command results | automatic |
| `cms DescribeMetricLast` | `cms:QueryMetricLast` | describes monitoring values | automatic |
| `ecs RunCommand` | `ecs:run-command` | **writes**: dispatches a command into the instance | announce, then confirm; one approved non-mutating command per call |
| `ecs CreateSnapshot` | `ecs:create-snapshot` | **writes**: creates a snapshot | announce, then confirm, including the billing note |

Two of the eight are writing operations, which is why this skill does not
describe itself as restricted to cloud-side queries. `RunCommand` exists so a
non-mutating observation can be taken inside the instance after the customer
agrees to that one command; `CreateSnapshot` exists so a manual repair step has
a rollback point before it starts. The commands behind `RunCommand` are frozen
in `scripts/areas/web_service_runtime_config/_constants.py` and validated twice before dispatch.

`InstallCloudAssistant` is **not called by this skill**: it is deliberately absent
from `../related_apis.yaml` and from every grant fragment in this file. Installing
the Cloud Assistant agent only completes after an instance restart, so it is a
guide-only action under [action-classes.json](action-classes.json) — the customer
is pointed at the console install flow and runs it themselves. Every restart-class
and irreversible action is guide-only on the same rule and has no dispatch call
site in `scripts/`; the full class-by-class contract, subordinate to
`action-classes.json`, is [action-authority-matrix.md](action-authority-matrix.md).

## Least-privilege fragment

Grant the diagnostic set on the resources under investigation, and keep the two
writing actions scoped to the instances and disks the customer names:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeDisks",
        "ecs:DescribeInvocations",
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:run-command"
      ],
      "Resource": "acs:ecs:<region-id>:<account-id>:instance/<instance-id>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:create-snapshot"
      ],
      "Resource": "acs:ecs:<region-id>:<account-id>:disk/<disk-id>"
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

`sts:GetCallerIdentity` needs no resource scoping: it describes the caller.

## When a call comes back denied

Report the exact action that is missing and point at the fragment above. The two
wordings this skill uses are `NoPermission` and `ImplicitDeny`; the older denial
wording is never used here, so that a reader is not sent looking for a policy
that the console does not show.

An identity that resolves to the wrong account is a different failure from a
missing action, so the report states which one it saw. Never widen a policy to a
wildcard to make a denial go away.

## Not granted, on purpose

No action in this skill can start, stop or reboot an instance, change a security
group rule, resize or delete a disk, delete a snapshot, uninstall a role or
module, or touch a file inside the instance. Those all appear in the report as
manual steps for the customer to perform. See
`references/web-service-runtime-config__handoff-matrix.md` for who owns each of them.

## Unverified items

| Item | State | Why it is left open |
|---|---|---|
| CloudMonitor `popVersion` for `DescribeMetricLast` | empty in `related_apis.yaml` | the batch verification pass recorded the operation and its RAM name but no version; the CLI resolves one itself, so nothing is guessed here |
| CloudMonitor namespace and metric names for CPU, memory and bandwidth | required from the caller | the verification reached "these parameters are mandatory", not their values; `report` degrades the resource area until they are supplied |
| `ecs:DescribeInstanceHistoryEvents` / `ecs:DescribeInstancesFullStatus` | not used | they would prove "the instance was stopped at 00:10", but neither was verified in this batch, so no permission point is invented for them |
| Windows observation cmdlets for IIS role state, application pool state and event logs | not used | not signed into the approved command list, so those readings come from the customer |

## Area: attack-blackhole-diagnosis
# RAM policy requirements (read-only)

This skill performs **read-only** OpenAPI calls only. It declares **no** write
permissions, and no action that creates, modifies, deletes, releases, resets,
binds, unbinds, imports, reboots, starts or stops a resource exists anywhere in
`scripts/`. The action list below is exhaustive for this package: the transport
layer refuses any action that is not in it.

## Required actions

| RAM action | Product | API version | Used by | Why the call is needed |
|---|---|---|---|---|
| `sts:GetCallerIdentity` | sts | 2015-04-01 | `scripts/areas/attack_blackhole_diagnosis/sts_token.py` | Confirm which account the readings belong to, and answer "is this IP even mine?" / "not your asset" style confusion before anything else. |
| `ecs:DescribeInstanceStatus` | ecs | 2014-05-26 | `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py` | Cheapest Running / stopped split for the region; separates the instance-lifecycle area from the attack area. |
| `ecs:DescribeInstances` | ecs | 2014-05-26 | `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py` | Resolve the target by instance id, public IP, EIP or private IP; read attached security groups, addresses, bandwidth and charge mode. |
| `ecs:DescribeSecurityGroups` | ecs | 2014-05-26 | `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py` | Locate and name the groups in the region, including groups the caller cannot read in detail. |
| `ecs:DescribeSecurityGroupAttribute` | ecs | 2014-05-26 | `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py` | The actual ingress and egress rules with policy, priority, protocol, port range and authorisation object; the only way to prove a "blocked port" is a rule effect. |
| `ecs:DescribeInvocations` | ecs | 2014-05-26 | `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py` | Historical Cloud Assistant run records, to see whether someone operated on the instance inside the incident window. History only, never a live reading. |
| `vpc:DescribeEipAddresses` | vpc | 2016-04-28 | `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py` | EIP address, status, bandwidth and charge mode; distinguishes an EIP from a fixed public IP, which decides both the "defence bypassed" and the "replace the address" paths. |

Two prefixes are easy to get wrong and are stated deliberately:

* Elastic IP addresses are read through the **`vpc:`** prefix even when the EIP
  is attached to an ECS instance.
* `sts:GetCallerIdentity` is invoked in the CLI's plugin form
  (`aliyun sts get-caller-identity`), while ECS and VPC actions keep their
  PascalCase names.

## Minimal policy fragment

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeInvocations",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": ["*"]
    }
  ]
}
```

Scope `Resource` to the specific instances, security groups and EIPs if your
account policy requires it; the calls above all accept region-scoped reads.

## Failure handling

* A denied read is reported as `NoPermission` or `ImplicitDeny` naming the exact
  action above, and the flow continues with the remaining evidence
  (`STATUS: DEGRADED`). The denial is never reinterpreted as "the instance was
  not attacked" or "there is no blackhole".
* Credentials come from the default credential chain of the machine running the
  skill. This package never accepts, reads, stores, prints or transmits an
  AccessKey pair or an account password; if the identity check fails, the user is
  told to authenticate in their own terminal.
* Never widen the policy to a whole product namespace, or to an identity action
  covering every account, just "to make the error go away"; add only the
  specific action that was reported.

## Not covered by any read-only action here

DDoS blackhole and scrubbing events, mitigation thresholds, Security Center
alarm details, content-penalty and unblocking records, account freeze state,
cloud monitoring metric series and in-guest connections or processes are **not**
declared in this file, because this skill has no verified read-only action for
them. They are handled as console guidance plus customer-supplied readings; see
`references/attack-blackhole-diagnosis__blackhole-and-blockout.md` and `references/attack-blackhole-diagnosis__evidence-checklist.md`.

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

## Area: bt-panel-diagnosis
# RAM policies — area:bt-panel-diagnosis

Every API action this skill actually calls, its consent class, and the minimal
statements a customer needs. API names are not RAM name guesses: the action
codes below were verified for this scenario (each `Describe*` action's RAM code
is its own name; the product code is `ecs`, API version `2014-05-26`, except
the identity check under product `sts`, version `2015-04-01`).

## Actions actually called

| # | Product | Action (RAM code) | Class | Read/write | Consent | Used by |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ecs | `ecs:DescribeInstances` | A | read | none, automatic | locate the instance from an id or IP; lifecycle state; bound security-group ids |
| 2 | ecs | `ecs:DescribeInstancesFullStatus` | A | read | none, automatic | health and scheduled events (platform-layer exclusion) |
| 3 | ecs | `ecs:DescribeCloudAssistantStatus` | A | read | none, automatic | whether the guest read-only probes can run at all |
| 4 | ecs | `ecs:DescribeInvocations` | A | read | none, automatic | read back the output of the one consented probe (history, not live) |
| 5 | sts | `sts:GetCallerIdentity` | A | read | none, automatic | stamp every report with the account tail (cross-account guard) |

Plus one gated dispatch, called ONLY through `scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py
probe` after the customer confirms that single command:

| # | Product | Action | Class | What it carries | Consent |
| --- | --- | --- | --- | --- | --- |
| 6 | ecs | `RunCommand` | B | one side-effect-free inspection command from the whitelist in [bt-readonly-evidence.md](bt-panel-diagnosis__bt-readonly-evidence.md) — `ls`, `stat`, `wc`, `df`, `findmnt`, `du`; on Windows `Get-Volume`, `Get-ChildItem` | **yes, per command** |

The action in row 6 dispatches nothing this skill has not whitelisted, and the
whitelist holds only commands that read state and write nothing. It is listed
in [../related_apis.yaml](../related_apis.yaml) because the script really
calls it. No standing grant is declared for it here: the probe runs under
whatever rights the customer's own credentials already hold, and the skill
asks permission for exactly one command each time.

## Minimal policy statement (class A — automatic queries)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` above scopes to the actions' own reach, not to broader
permissions: none of the listed actions can change anything, and the visible
footprint is one region of the calling account (queries only ever see the
current account's resources in the named region — two-account cases like
T-4B98459C stay invisible across the boundary, and the report says so).

## Denied calls: what to output

If any call returns `NoPermission` or `ImplicitDeny`:

1. name the exact missing action from the table above (or `RunCommand` for a
   consented probe);
2. show the customer the statement snippet above, limited to the missing
   action;
3. stop: never substitute a broader policy, never work around with another
   identity.

Authentication and expiry failures degrade the run with `[WARN]` lines and
`STATUS: DEGRADED` or `STATUS: FAIL`; the guidance points at `aliyun
configure` and never asks the customer to paste any credential value.

## Actions this skill neither calls nor assumes

Security-group rule editing, panel or web-service restarts, instance start,
stop or reboot, password resets, snapshot creation, file cleanup, firewall
changes and package installs are outside this skill: they are printed as
manual customer steps (with a snapshot-before-change reminder the customer
acts on themselves), never executed, never assumed granted. The cloud-side
rule-detail, metric, billing and DDoS-record queries were not verified for
this scenario and appear nowhere in the scripts.

## Area: snapshot-billing-cleanup
# RAM policy — permissions for the ECS snapshot billing attribution skill

This skill dispatches six observation-class list calls plus exactly two
confirmation-gated calls (`CreateSnapshot` for the pre-cleanup backup,
`RunCommand` for one whitelisted guest reading). This file is the complete,
per-action declaration: nothing outside it is ever called, and no wildcard is
granted or requested.

## Authorized actions

The table lists every action with its exact PascalCase name. The RAM-console
string for any row is built from the `Prefix` cell plus the action name (for
example the `ecs` prefix plus `DescribeSnapshots` gives the standard
`ecs`-prefixed RAM action for that call).

| Prefix | Action | Class | Gate | Purpose in this skill | Where it is called |
| --- | --- | --- | --- | --- | --- |
| ecs | `DescribeInstances` | evidence | none | region, OS kind and instance state context | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| ecs | `DescribeDisks` | evidence | none | provisioned disk sizes for the cloud lens, orphan detection | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| ecs | `DescribeSnapshots` | evidence | none | enumerate snapshot entries per region/disk, Usage and retention fields | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| ecs | `DescribeImages` | evidence | none | which custom image references (blocks deletion of) a snapshot | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| ecs | `DescribeInvocations` | evidence | none | fetch the result of ONE confirmed guest reading | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| ecs | `CreateSnapshot` | gated write | user confirmation per the SKILL.md User Confirmation section | pre-cleanup backup of one named disk | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| ecs | `RunCommand` | gated dispatch | user confirmation per the SKILL.md User Confirmation section | dispatch ONE whitelisted guest reading (never arbitrary input; the script refuses anything else) | `scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py` |
| sts | `GetCallerIdentity` | identity | none | prove the credential chain and label the account | `scripts/areas/snapshot_billing_cleanup/sts_token.py` |

The two gated rows carry the `ecs` product prefix like every other ECS row
when entered in the RAM console. They are the only actions in this skill that
are not pure observation, and the entry script refuses to dispatch them unless
the operator passes the confirmation flags for that exact region and target.

No wildcard permission string is declared, requested or used anywhere in this
package: prefix wildcards such as `ecs` plus colon plus star would also cover
mutating actions this skill is designed never to call (removal of snapshots,
images or policies, rollback, detach, release), and action-suffix wildcards
are refused by the same rule.

## Minimal policy fragment

The fragment below covers the evidence sweep and identity check, the modes
that run without a gate:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeImages",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

When the customer opts into the gated flows, add the two gated ECS action
names from the table above (`CreateSnapshot` and `RunCommand`, each with the
same `ecs` product prefix convention used in the fragment) to the Action
list, or attach them through a separate statement scoped to the specific
disk, instance and region involved. If the gated actions are not granted,
everything except the two confirmation-gated modes still works, and those
modes report `NoPermission` with this file as the recovery pointer.

`Resource: "*"` is acceptable for the sweep because every call is scoped by
the region and resource id supplied on the command line. A tighter policy may
replace it with `acs:ecs:<region-id>:<account-id>:snapshot/*`,
`acs:ecs:<region-id>:<account-id>:disk/<disk-id>` and
`acs:ecs:<region-id>:<account-id>:instance/<instance-id>` as appropriate.

## Scenario-to-action mapping

| Decision-tree branch | Actions used |
| --- | --- |
| S0 identity and scope | `GetCallerIdentity` |
| S1 billing attribution | `DescribeSnapshots`, `DescribeDisks`, `DescribeInstances` |
| S2 capacity lens reconciliation | sweep actions plus one confirmed `RunCommand` dispatch with `DescribeInvocations` fetch |
| S3 deletion blockers and regrowth | `DescribeSnapshots`, `DescribeImages`, `DescribeDisks` |
| S4 counts and quota facts | `DescribeSnapshots` |
| S5 concept boundaries | `DescribeSnapshots`, `DescribeImages`, `DescribeDisks` |
| Pre-cleanup backup (gated) | `CreateSnapshot` |

## Region and resource-group scoping

* Grant only the regions the operator diagnoses; a single-region account can
  pin the region segment of the ARNs.
* If the resources live in one resource group, attach the policy at that
  resource group instead of the account.
* The identity action is global and needs no region.

## When a call is denied

The scripts report denial with the literals `NoPermission` or `ImplicitDeny`
plus the exact missing action name, and never with a generic permission
wording. The recovery is always identical: ask the account administrator to
attach the fragment above (or the one missing action from it), then re-run
the identical command. The skill does not ask for, read, store or pass any
credential material — the local CLI default credential chain is the only
source, and refreshing it is done with `aliyun sts get-caller-identity` by the operator.

## Credential and data-handling rules baked into the code

* Key material never appears as a command argument anywhere; the transport
  layer additionally redacts credential-looking key/value pairs from every
  error string before it is printed.
* The report contains resource identifiers, sizes, states and timestamps
  only, so it can be pasted into a support case without leaking customer
  data.
* The printed account label keeps only the trailing four digits of the
  account id.
* Guest readings shown in the report are file-system listings of free and
  used space; they never print file contents.

## Area: billing-mode-selection
# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS billing-mode advisory work. The
granted action set contains only Describe/Get-class APIs; the credential
physically cannot change any instance, order, disk, or billing state. No
wildcard action entries (any product prefix followed by colon-star) are used
anywhere in this file or in the skill's policy.

## Required actions (evidence-backed this phase)

| # | RAM Action | API Version | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | Verify the caller identity and derive the account UID trace label (`scripts/areas/billing_mode_selection/sts_token.py`, `--region` is central, endpoint `sts.aliyuncs.com`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | Instance inventory plus billing facts (InstanceChargeType, ExpiredTime, OperationLocks) queried by `scripts/areas/billing_mode_selection/billing_mode_advisor.py` |

All queries are regional: every ECS call carries an explicit `RegionId`, so
one run sees only the current credential's account and the single region
requested. Cross-region review requires one run per region (or a customer
provided region list).

## Supplementary read queries and their permission point (pending verification)

The advisory additionally issues two supplementary Describe-class queries,
declared in `related_apis.yaml` (both verified as real API operations via
the aliyun CLI 3.4.5 offline metadata):

- the instance run-state query (`DescribeInstanceStatus`, 2014-05-26) used
  for post-action re-verification;
- the selection-time availability query (`DescribeAvailableResource`,
  2014-05-26) used only with `--check-availability`.

Their exact RAM permission-point names have NOT been confirmed against an
authoritative permission-point registry this phase, and a RAM action name
must never be derived from an API name (this class of trap has burned other
tiers before). Therefore they are intentionally NOT written into the policy
below. Consequence by design: on a strictly minimal policy these two
supplementary calls answer with `NoPermission` (or `ImplicitDeny` through an
SCP), the scripts log `[WARN] ... degrading`, and the advisory continues
without them:

- the run-state information is already carried by `DescribeInstances`
  (`Status`), so re-verification still works;
- the availability check is optional consulting evidence and its absence
  never blocks the consultation.

Phase B follow-up (tracked in the requirement document's open items): once
the permission-point names are verified, add exactly those specific actions
to this file and the policy -- still no wildcards, still read-only only.

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
      "Sid": "EcsReadOnlyInventory",
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

- Every action is listed explicitly; wildcard action entries at the product
  or global level are not allowed for this skill.
- `Resource: "*"` is the minimum practical scope here because
  `DescribeInstances` does not support resource-level authorization
  granularity for list queries; the read-only effect is guaranteed by the
  action list itself, which contains only Describe/Get verbs.
- No explicit deny statements are needed: anything not listed above is
  already unavailable to the credential.
- Billing/finance query actions (balance, bills, invoiceable amount,
  savings-plan deduction) are NOT requested: this tier's read-only surface
  does not include any accounting API, and money questions route to the
  customer's self-check in the Billing Center or a finance-tier handoff.

## On permission failures

| Observed error | Meaning | Required behavior |
|---|---|---|
| `NoPermission` | The identity lacks the specific Describe action above | Report the missing action verbatim, point to this file, continue with whatever evidence is available |
| `ImplicitDeny` | An organization-level control blocks the action | Same handling; suggest the customer confirm with their account administrator |
| Credential-chain failure | The aliyun CLI default chain is not configured | Guide the customer to verify the default credential chain with `aliyun sts get-caller-identity`; this skill never accepts credential values as arguments |

## Least-privilege checklist

- Grant only the actions above; do not attach any ECS full-access or
  administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Credentials are resolved exclusively through the aliyun CLI default
  credential chain; the scripts never take, read, print, or cache them.

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

## Area: file-transfer-diagnosis
# RAM policies

This is the permission contract for the scripts listed in `SKILL.md`. Every
action below was verified against the code that dispatches it: the whitelist
in `scripts/areas/file_transfer_diagnosis/_constants.py` (`API_QUERIES`) and the call sites in
`scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` and `scripts/areas/file_transfer_diagnosis/sts_token.py`. Nothing
is declared here that the scripts do not actually call, and nothing the
scripts call is missing.

The policy follows the "what one called action needs" principle: one
statement per called action, no grouping, and no product-namespace wildcards
anywhere. Two classes mirror `SKILL.md` ("What this skill may and may not
do"):

- **Class A** — the read-only cloud queries every diagnosis run needs.
- **Class B** — the gated in-guest command channel. Optional, attached at
  the customer's own discretion; see its section below.

## Class A — read-only queries (required)

| RAM action | OpenAPI product / version | Called by | Why |
|---|---|---|---|
| `sts:GetCallerIdentity` | Sts / 2015-04-01 | `scripts/areas/file_transfer_diagnosis/sts_token.py` | Identity preflight: confirms credentials resolve and names the account the results belong to. |
| `ecs:DescribeInstances` | Ecs / 2014-05-26 | `scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Instance basics for the evidence report: status, OS type, public and internal addresses, declared bandwidth, security group ids. |
| `ecs:DescribeInstancesFullStatus` | Ecs / 2014-05-26 | `scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Lifecycle state and scheduled events, so a transfer fault is not confused with an instance event. |
| `ecs:DescribeCloudAssistantStatus` | Ecs / 2014-05-26 | `scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Whether the Cloud Assistant agent is reachable, which decides if the Class B channel is even possible. |
| `ecs:DescribeInvocations` | Ecs / 2014-05-26 | `scripts/areas/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Recent command records and the result of one approved command. |

Attach this minimal policy to the RAM role or RAM user that the ambient CLI
profile already resolves to (`aliyun` reads its credentials from the profile
or the instance role; the scripts never take, read, echo or store a key or
secret):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "EcsFileTransferDescribeInstances",
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstances"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferDescribeInstancesFullStatus",
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstancesFullStatus"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferDescribeCloudAssistantStatus",
      "Effect": "Allow",
      "Action": ["ecs:DescribeCloudAssistantStatus"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferDescribeInvocations",
      "Effect": "Allow",
      "Action": ["ecs:DescribeInvocations"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferStsIdentity",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

`Resource` stays at the account level because these ECS read actions
authenticate service-wide; scoping through region conditions is left to the
account's own policy standards. Do not broaden any action entry with a
wildcard suffix — the five actions above are the complete surface the
diagnosis runs need.

## Class B — gated command channel (optional, not in the minimal policy)

The in-guest inspection path uses the Cloud Assistant command-delivery
operation RunCommand (Ecs / 2014-05-26); the scripts refer to it internally
by its dispatch token `ecs:run-command`, bounded by the command whitelist
embedded in `scripts/areas/file_transfer_diagnosis/_constants.py` (`GUEST_COMMAND_WHITELIST`).

A command submission is not a read, so this class is deliberately absent
from the Class A example above. The confirmation gate in `SKILL.md`
("Confirmation gate for in-guest commands") always applies: exact command
line stated, single-instance scope, no-effect statement, and one approval
per command. Granting the operation is a decision for the customer's own
account administrator, made per account and per role; the skill never asks
the customer for a key or secret to work around a denial.

When the identity lacks the submission permission, nothing breaks: the
`guest-plan` entry point prints the denial with the literals `NoPermission`
or `ImplicitDeny` as returned and falls back to customer-run guidance, so
the Class A policy alone is sufficient for a complete report; Class B only
adds the in-guest evidence lane.

## Scope and denial notes

- Every result reflects only the account the preflight resolved to. An empty
  answer means "nothing found for this account", never "nothing wrong".
- When a Class A query is denied, the run degrades gracefully: the missing
  reading is recorded under Gaps in the report and the remaining queries
  continue. Name the missing action from the table above and link back to
  this file, as `SKILL.md` ("Authorization errors") requires.
- Policy maintenance: a managed custom policy keeps at most five versions;
  remove the oldest version before creating a new one if the limit is hit.

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

## Area: disk-attach-os-visibility
# Permissions requested by this skill

The caller is authenticated through the Alibaba Cloud CLI's own credential chain. This
skill never asks for, reads, stores or prints an AccessKey pair or a security token.

Six actions are requested. This list is the same list the scripts are able to call, the
list in [../related_apis.yaml](../related_apis.yaml), and the whitelist enforced by
`ALLOWED_ACTIONS` in [../scripts/areas/disk_attach_os_visibility/_constants.py](../scripts/areas/disk_attach_os_visibility/_constants.py).

| Product | Action | Version | What it is used for |
| --- | --- | --- | --- |
| ecs | `ecs:DescribeInstances` | 2014-05-26 | Instance existence and power state; state decides whether console actions are greyed out. |
| ecs | `ecs:DescribeDisks` | 2014-05-26 | Attachment state of every disk in the region queried: which instance, which device name, size, billing shape. |
| ecs | `ecs:DescribeSnapshots` | 2014-05-26 | Whether a recovery point exists before any remediation is suggested. Presence check only. |
| ecs | `ecs:DescribeInvocations` | 2014-05-26 | Collects the output of one approved diagnostic command already delivered to the instance. |
| ecs | `ecs:run-command` | 2014-05-26 | Delivers one command at a time, and only from the approved list in [guest-command-policy.md](disk-attach-os-visibility__guest-command-policy.md), and only after the customer agreed to that specific command. |
| sts | `sts:GetCallerIdentity` | 2015-04-01 | Pre-flight that the configured credentials work. Returns identity only, no resource access. |

## Minimal policy

No entry in an `Action` list is a wildcard, and none may be replaced by one. Substitute the
region, account id and instance id in the `ecs:run-command` resource with the instance the
customer is asking about; that statement is the only one scoped to a single resource,
because it is the only action that reaches inside an instance. The describe statements and
the identity statement keep a plain resource because they are account-scoped queries: a disk
or instance id is an argument to the call, not something the policy can enumerate up front.
Narrow them further only if the organisation's own standards allow it.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ecs:run-command",
      "Resource": "acs:ecs:cn-hangzhou:1234567890123456:instance/i-bp1exampleinstance"
    },
    {
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

`ecs:run-command` is the only entry that can act inside the customer's instance. It is
constrained in three places at once: the code refuses any command not in the approved
list, the code refuses to deliver anything until the confirmation flag is present, and
the approved list itself contains no command that writes, partitions, formats, mounts,
unmounts, changes volume state or restarts anything. Organisations that want to remove
the capability entirely may drop that statement; the skill then reports the OS half of
the chain as unverified and hands the commands to the customer to run by hand.

## Not requested

This skill requests no permission for, and will not call, any action whose name starts
with Attach, Detach, Create, Delete, Release, Modify, Resize, Reset, ReInit, Replace,
Convert, Renew, Start, Stop or Reboot. Disk placement, disk creation and removal,
snapshot creation and removal, disk initialisation, system-disk replacement, billing
changes and instance power operations stay with the human in the console. See
[handoff-boundaries.md](disk-attach-os-visibility__handoff-boundaries.md).

## When the platform refuses a call

The service answers a refused call with `NoPermission` or `ImplicitDeny`. Report which
action was refused, paste the statement above for that action, and stop: do not retry the
call with different parameters, and do not ask the customer for credentials of any kind.
`DescribeInvocations` returning nothing while `RunCommand` succeeded means the Cloud
Assistant agent on the instance is missing or out of date, which is an agent problem
rather than a RAM problem.

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

## Area: db-on-ecs-diagnosis
# RAM Policies

Every permission this skill needs, at action granularity. No wildcard action
entry appears anywhere in this package, and no permission is declared that the
scripts do not actually call.

This skill is **not** an inspection-only package: besides its queries it can
dispatch two consent-gated write-class operations - a guest command through
Cloud Assistant that can only carry a non-mutating, whitelisted payload, and a
snapshot that adds a copy and alters no existing data. Each sits behind the
confirmation gate written into `SKILL.md` and enforced inside
`scripts/areas/db_on_ecs_diagnosis/db_on_ecs_diagnosis.py`. Following this suite's read-only convention,
**neither write carries a declared grant in the customer policy below**: both run
only under whatever rights the customer's own credentials already hold, and only
after the operator relays the disclosure and the user approves that single call.
A principal limited to the read-only grant is a supported mode, not a defect -
the guest leg then degrades to a paste-back checklist and the snapshot leg to
console guidance.

## Actions used

| Product | Action | Class | Permission point | Called from |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | query | `sts:GetCallerIdentity` | `scripts/areas/db_on_ecs_diagnosis/sts_token.py` |
| ecs | `DescribeInstances` | query | `ecs:DescribeInstances` | `fetch_instances` |
| ecs | `DescribeInstancesFullStatus` | query | `ecs:DescribeInstancesFullStatus` | `fetch_full_status` |
| ecs | `DescribeInstanceTypes` | query | `ecs:DescribeInstanceTypes` | `fetch_instance_type_detail` |
| ecs | `DescribeCloudAssistantStatus` | query | `ecs:DescribeCloudAssistantStatus` | `fetch_assistant_status` |
| ecs | `DescribeInvocations` | query | `ecs:DescribeInvocations` | `poll_invocation` |
| ecs | `RunCommand` | gated write (Class B, no declared grant) | `run-command` (CLI plugin-mode name; API `RunCommand`) | `submit_guest_command` |
| ecs | `CreateSnapshot` | gated write (Class B, no declared grant) | `create-snapshot` (CLI plugin-mode name; API `CreateSnapshot`) | `cmd_create_snapshot` |
| cms | `DescribeMetricLast` | query | `cms:QueryMetricLast` (the RAM point differs from the API name - never derive it from the apiName) | `fetch_metric` |

The same nine API names are declared in [../related_apis.yaml](../related_apis.yaml)
with their versions (the two gated writes are listed there as callable APIs but
deliberately carry no grant in the policy below). The three lists - this table,
the YAML declaration and the calls under `scripts/` - are kept aligned; adding a
call without adding it here is a defect.

## Why the two gated writes are needed

`RunCommand` under the `ecs` RAM code is write-class because it dispatches a
command into a customer instance. This skill uses it only to carry ONE command
from the frozen non-mutating whitelist in `scripts/areas/db_on_ecs_diagnosis/_constants.py` (disk and
inode usage, file-size listing, deleted-but-open file listing, mount table),
after the operator was told the exact command text, the target instance, that
the command writes nothing, and that the acknowledgement covers only that one
dispatch. It never carries a service, firewall, partition, filesystem, process
or package change; anything outside the whitelist is refused even after a
confirmation and is handed to the customer as a paste-back step instead.

`CreateSnapshot` under the `ecs` RAM code is the safety net this tier borrows
from the ticket practice: before any cleanup or space-releasing advice is
acted on, and before forensic evidence is preserved in a suspected intrusion,
a fresh snapshot exists. It is reversible in the sense that it creates an
additional copy and alters no existing data. It bills by stored capacity and
retention time, which is disclosed before the call. The instance does not need
to be stopped.

## Minimal policy, queries only

This is the **only** policy this skill needs declared. It is sufficient for
`check-auth`, the cloud-side legs of `diagnose`, and `explain`. A customer who
grants nothing beyond it still gets the full cloud-side verdict; the guest-reading
leg (`probe`) then degrades to "run it yourself and paste the output back", and
the snapshot leg (`create-snapshot`) degrades to console guidance.

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
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

## Consent-gated writes (Class B) - no declared grant

The two write-class operations named in the table above are deliberately absent
from the policy document:

- The guest probe is dispatched through Cloud Assistant via the CLI plugin-mode
  command `run-command` (underlying API `RunCommand`, listed in
  `related_apis.yaml`). It is write-class even though it only carries one
  whitelisted, non-mutating command - which is exactly why it is not granted by
  default.
- The pre-cleanup / evidence snapshot uses the CLI plugin-mode command
  `create-snapshot` (underlying API `CreateSnapshot`); it adds a copy and alters
  no existing data, but it bills by stored capacity, so it too is not granted by
  default.

Both run only under whatever rights the customer's own credentials already hold,
and only after the `SKILL.md` confirmation gate is satisfied for that single call
(`probe` needs `--confirm`, `create-snapshot` needs `--confirm-cost`). Where an
operator genuinely wants the session itself to dispatch them, they may add the
matching write actions to their own policy out-of-band and narrow `Resource` to
the specific instance or disk ARN. That is a customer-side decision outside this
skill's default posture, and RAM cannot scope `RunCommand` down to the frozen
whitelist - that confinement lives in this skill's code, not in the grant.

## Actions this skill never calls

The `Delete`, `Release`, `Remove`, `Modify`, `Replace`, `Reset`, `Attach`,
`Detach`, `Reboot`, `Start`, `Stop`, `Authorize`, `Revoke`, `Bind`, `Unbind`,
`Assign`, `Unassign`, `Join`, `Leave`, `Import`, `Export`, `Cancel`, `Add`,
`Put`, `Tag` and `Untag` families are refused by
`NEVER_ALLOWED_ACTION_PREFIXES` in `scripts/areas/db_on_ecs_diagnosis/_constants.py`, and the refusal
holds even after a customer confirmation. In particular:

* snapshot or disk deletion, and instance or service restart - always human
  steps with the risk statement;
* security-group rule edits, even to "fix" a blocked database port - the
  console or another tier owns that change;
* database account, grant or authentication-mode changes - the report emits
  the check procedure and stops;
* `InvokeCommand` and `DescribeCommands` - not verified for this tier;
* order, renewal and bill APIs - commercial questions are recognised and
  handed over, never queried here.

Do not add any of them to a policy for this skill.

## Denied calls

A denied call surfaces with the code the platform returned, `NoPermission` or
`ImplicitDeny`. The report names the specific missing action from the table
above and points here for the fragment that supplies it; the recovery is a
policy change in the customer's account, never a request for an AccessKey
pair. This package does not accept, read, store or forward credential
material: the local CLI default credential chain is the only authentication
path, refreshed by the operator with `aliyun sts get-caller-identity`.

## Credential and data-handling rules baked into the code

* Credential names (`AccessKeyId`, `AccessKeySecret`, `SecurityToken`,
  `Signature`) appear in `_cli.py` exclusively as redaction targets; every
  error string passes through that redaction before it is printed.
* The report carries resource identifiers, statuses, sizes and usage
  percentages only, so it can be pasted into a ticket without leaking secret
  data; the account label keeps only the trailing four digits.
* Guest command output is transient in-memory text; nothing the customer
  holds is written to disk by this skill, and no command carrying output
  redirection is ever dispatched.

## Area: bandwidth-modify-guide
# RAM policies for this skill

The five actions below are the complete set that `scripts/` sends. The policy in
`related_apis.yaml`, the calls in `scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py`, and this file are the same
five entries; none of them may drift apart.

| Action | Product / version | Sent by | Why the skill needs it |
| --- | --- | --- | --- |
| `sts:GetCallerIdentity` | sts / 2015-04-01 | `scripts/areas/bandwidth_modify_guide/sts_token.py` | proves the default credential chain resolves and tags the report with the account |
| `ecs:DescribeInstances` | ecs / 2014-05-26 | `scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py` | live bandwidth value, bandwidth billing mode, public IP shape, charge type, state |
| `ecs:DescribeInstanceStatus` | ecs / 2014-05-26 | `scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py` | cross-checks the reported state for "paid but not effective" cases |
| `ecs:DescribeAvailableResource` | ecs / 2014-05-26 | `scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py` | optional sellability lookup before a change |
| `vpc:DescribeEipAddresses` | vpc / 2016-04-28 | `scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py` | EIP status and binding, used by the public IP replacement path |

There is deliberately no wildcard statement in this file and no write action. The skill has no
mutation surface: bandwidth changes, billing-mode conversions, temporary upgrades, EIP conversion,
allocation, binding and release, snapshot creation, restarts, refunds and unsubscriptions are all
performed by the customer in the console, and the skill only guides them there.

## Minimal policy

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
        "ecs:DescribeAvailableResource",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource` is `*` here because these query actions do not support resource-level authorisation for
a region-scoped list call. To narrow it further, scope the statement to the account and region and
list the instance collection explicitly, for example
`acs:ecs:{region-id}:{account-id}:instance/{instance-id}`, and note that a region-wide survey then
returns only the instances the caller may see.

## When a call is denied

Quote the two literals the platform returns, `NoPermission` and `ImplicitDeny`, and name the exact
action that is missing. Do not paraphrase the denial as a generic permission problem, and do not
work around it by removing the field from the report: report the gap and mark the run `DEGRADED`.

```
[WARN] vpc:DescribeEipAddresses -> NoPermission (ImplicitDeny)
declared params: PageNumber=1, PageSize=50, RegionId=us-west-1
```

The remediation text is always the same shape: add the single listed action to the caller's policy,
or run under a profile that already has it. Never ask the customer to paste a key pair, a token or
a profile file into the conversation; the skill reads the default credential chain only.

## Notes for anyone extending this skill

* Adding a call means adding the same line to `related_apis.yaml`, to `ACTION_WHITELIST` in
  `scripts/areas/bandwidth_modify_guide/_cli.py`, to `RAM_ACTIONS` in `scripts/areas/bandwidth_modify_guide/_constants.py`, and to this table. Four places,
  one action.
* A RAM action name is not always the API name. Before listing any new action, look up its real
  authorisation name rather than deriving it from the action string; see
  [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).
* A write action would change the character of this skill, not just its policy. It is out of scope
  for this tier, and `scripts/areas/bandwidth_modify_guide/_cli.py` rejects it at the single call site even if a caller tries.

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

## Area: network-quality-bandwidth
# RAM actions used by this skill

This skill is read-only. Every action below is a query that `scripts/` actually calls, and nothing
else is granted. No action name in this package carries a wildcard, and no action listed here is one
the code never reaches.

## Actions and their purpose

| Action | Used by | Purpose in this diagnosis |
| --- | --- | --- |
| `sts:GetCallerIdentity` | `scripts/areas/network_quality_bandwidth/sts_token.py`, `preflight` | confirms the configured profile works and records an account tag for traceability |
| `ecs:DescribeInstances` | `collect` | maps an instance id to its public IP and region, and lists the region inventory when only an address is known |
| `ecs:DescribeInstanceAttribute` | `collect` | the instance's own public bandwidth peak and billing mode |
| `vpc:DescribeEipAddresses` | `collect` | each EIP's configured peak, status, and whether it sits in a shared bandwidth package |
| `vpc:DescribeCommonBandwidthPackages` | `collect` | shared bandwidth package peak and status when an EIP belongs to one |
| `cms:DescribeMetricList` (the RAM action name is `cms:QueryMetricList`; API name and RAM name differ, so never derive one from the other) | `collect` (opt-in, only when the operator supplies the namespace and metric name) | the bandwidth series used to decide saturation over a stated window |

## No execution and no configuration action is requested

This package never asks for an action that runs a command in a guest, edits a resource, or changes a
billing or protection setting. Measurements that need to happen inside the operating system are
printed as instructions for the customer to run and paste back; see
[guest-command-whitelist.md](network-quality-bandwidth__guest-command-whitelist.md). Bandwidth peaks, billing modes, upgrades,
security group rules, reboots, and snapshots stay human actions in the console.

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeEipAddresses",
        "vpc:DescribeCommonBandwidthPackages"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricList"
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

Notes that matter when tightening this further:

- The RAM action name is not always identical to the API name. The code calls the CloudMonitor API
  `DescribeMetricList`, while the grant above uses the RAM name `cms:QueryMetricList`. If your
  environment reports a different name, confirm it before editing the policy, and do not substitute a
  wildcard.
- Every statement above uses `Resource` set to the all-resources value. These are list and query
  actions, and whether each of them honours a narrowed resource ARN was not verified in this run;
  confirm it in the RAM documentation before tightening it. The real bound on this grant is the set
  of action names, all of which are read-only.
- If only the cloud-side capacity question matters, the two VPC query actions and the CloudMonitor
  query action can be dropped and the skill still completes, reporting the missing peaks and series as
  limitations rather than guessing them.

## When a call is refused

The scripts report `NoPermission` or `ImplicitDeny` as a named missing action plus the statement
above that grants it, and stop there. They never broaden a policy, never reuse another account's
profile, and never present a permission failure as a network fault.

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

## Area: data-recovery-assessment
# Minimal Read-Only RAM Policy

This skill performs a strictly read-only evidence query plus offline
assessment and manual-guidance output. Its scripts call exactly two cloud
APIs: the ECS instance-list query and the STS identity check. No wildcard
action entries are used or allowed here; no action with a mutating verb is
granted, so the credential physically cannot alter any resource.

## Required actions

| # | RAM action | API version | Called by | Purpose |
|---|---|---|---|---|
| 1 | `ecs:DescribeInstances` | 2014-05-26 | `scripts/areas/data_recovery_assessment/ecs_data_recovery_assessment.py` (evidence mode) | Check whether the target instance still exists in the current account and region, and read its running/stopped status |
| 2 | `sts:GetCallerIdentity` | 2015-04-01 | `scripts/areas/data_recovery_assessment/sts_token.py` and the evidence-mode pre-check | Verify the caller and derive the account UID traceability label; this query is scoped to the account whose credential is in use |

Note: **RAM action name = API name** holds for both rows above (api-info
contract). Never widen the policy "for convenience"; anything not in this
table is out of this skill's whitelist.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ReadOnlyEcsInstanceEvidence",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- `Resource: "*"` appears above only because the ECS query is region-scoped
  by its `RegionId` request parameter and the identity check is account
  level; neither supports a narrower ARN form for a customer-owned fleet that
  may need to be located by public IP. Read-only behaviour is guaranteed by
  the action list itself.
- Snapshot, image and backup inventory APIs are intentionally NOT part of
  this skill: no contract for them was verified for this tier, so the
  inventory step is designed as a customer console self-check (see
  `customer-self-check-list.md`), not an API call.
- If a call fails with the literals `NoPermission` or `ImplicitDeny`, the
  missing action is one of the two rows above: report which one, attach this
  policy document, and re-run. Never substitute a broader managed policy.

## Least-privilege checklist

- Grant only the two actions above to the profile the skill runs with.
- Prefer a RAM role with a short session over long-lived user keys.
- Credentials are resolved only by the aliyun CLI default credential chain;
  the scripts never accept, read, print or store a key pair.

## Area: intranet-egress
# RAM Permissions

Minimum authorization for `area:intranet-egress`. Every action
below is invoked by a script in `scripts/`; no action is listed that the skill
does not call, and no action uses a wildcard.

## Action list

| RAM action | Product | API action | Version | Invoked by | Purpose |
| --- | --- | --- | --- | --- | --- |
| `sts:GetCallerIdentity` | sts | `GetCallerIdentity` | 2015-04-01 | `scripts/areas/intranet_egress/sts_token.py`, `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | Identity and account-ownership baseline. Every later query is scoped to this account. |
| `ecs:DescribeInstances` | ecs | `DescribeInstances` | 2014-05-26 | `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | Locate the instance and the peer instance; read state, region, private and public addresses, VPC, VSwitch, security group membership, outbound bandwidth. |
| `ecs:DescribeSecurityGroupAttribute` | ecs | `DescribeSecurityGroupAttribute` | 2014-05-26 | `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | Read back the ingress and egress rules that are in effect right now: direction, policy, protocol, port range, remote CIDR, priority. |
| `vpc:DescribeVSwitches` | vpc | `DescribeVSwitches` | 2016-04-28 | `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | VSwitch CIDR map, used for the same-subnet and cross-subnet private-access decision. |
| `vpc:DescribeRouteTableList` | vpc | `DescribeRouteTableList` | 2016-04-28 | `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | Route table inventory for the VPC. Per-entry next-hop detail is not exposed by this query; the gap is declared in the report. |
| `vpc:DescribeNatGateways` | vpc | `DescribeNatGateways` | 2016-04-28 | `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | Whether an available NAT gateway exists for an instance that has no public address. |
| `vpc:DescribeSnatTableEntries` | vpc | `DescribeSnatTableEntries` | 2016-04-28 | `scripts/areas/intranet_egress/ecs_connectivity_diagnose.py` | Whether an SNAT entry covers this instance's VSwitch or address. |

## Minimal policy fragment

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
        "vpc:DescribeVSwitches",
        "vpc:DescribeRouteTableList",
        "vpc:DescribeNatGateways",
        "vpc:DescribeSnatTableEntries"
      ],
      "Resource": "<narrow to the diagnosed instance, its VPC and its NAT gateway>"
    }
  ]
}
```

Fill the `Resource` element from the deployment's own resource-scoping
convention. Narrow it; never widen it, and never substitute an action wildcard
such as `ecs:` followed by a star. An over-broad action grant is a policy
defect, not a convenience.

## Split by privilege class

Non-mutating queries, tier 1 of the permission model. These run automatically:

```
sts:GetCallerIdentity
ecs:DescribeInstances
ecs:DescribeSecurityGroupAttribute
vpc:DescribeVSwitches
vpc:DescribeRouteTableList
vpc:DescribeNatGateways
vpc:DescribeSnatTableEntries
```

Execute-class, tier 2: no grant exists. In the shipped configuration this skill
is strictly read-only: the inspection-dispatch module is closed by an empty
`APPROVED_COMMAND_CLASSES` (asserted at import in
`scripts/areas/intranet_egress/_constants.py`), so no `RunCommand` can be
issued and no execute privilege is requested at all. `guest_command_gate.py`
does contain the dispatch path (`ecs:run-command` plus
`ecs:describe-invocations` for the read-back); opening it would require a code
change to that constant, and the central consent gate would still strip the
area's activation flags. The two actions are therefore absent from the policy
on purpose, not by omission.

In-guest evidence is collected manually instead: the scripts print the
inspection checklist, the customer runs the commands inside the instance and
pastes the output back as plain text, and the report continues from that text.
`scripts/areas/intranet_egress/guest_command_gate.py` validates a proposed
inspection command against the inspection-only text guards before it is handed
to the customer. The guards and the checklist are defined in
`scripts/areas/intranet_egress/_constants.py`; the full command reference is
[guest-inspection-commands.md](intranet-egress__guest-inspection-commands.md).

## Not granted, not invoked

Deliberately absent from the policy, because no script calls them:

- Any action that changes a security group rule, a network ACL, a route table,
  an SNAT entry, a NAT gateway, an EIP or a public address.
- Any action that starts, stops, reboots or re-images an instance.
- Any execute-class action that would run a command inside a customer
  instance, including Cloud Assistant dispatch, and any invocation read-back
  that only serves such a dispatch. In-guest evidence is always collected by
  the customer, by hand, from the printed checklist.
- Snapshot creation. Taking a snapshot before an interactive login session is a
  manual console step owned by the resource operator; this skill neither
  performs nor requires it, because the diagnosis path itself changes nothing.
- Monitoring metric queries. A monitoring read was considered for separating a
  traffic anomaly from a link anomaly, but the metric namespace, metric name and
  dimension set were never verified against the API metadata, so no such call
  was implemented rather than guessed. See "Verification status" below.

## Naming traps

RAM action names do not always equal the API action name, and the product prefix
in a RAM action does not always equal the CLI product token. Two concrete traps
that shaped this file:

- A monitoring query for the last metric value is authorized by a RAM action
  whose verb differs from the API name (`Query...` rather than `Describe...`).
  Guessing the RAM name from the API name produces a policy that looks right and
  denies at runtime. This is one reason the monitoring call was left
  unimplemented instead of assumed.
- STS identity resolution is a central service. It is invoked through the
  lowercase hyphenated CLI command form, while the RAM action keeps the
  PascalCase API name.

Never derive a RAM action name from an API name. Verify it, or leave the call
out.

## Verification status

- All seven API actions and their versions were verified against the Alibaba
  Cloud OpenAPI metadata for `ecs` 2014-05-26, `vpc` 2016-04-28 and `sts`
  2015-04-01, and are declared in `related_apis.yaml`.
- `ecs:` and `vpc:` RAM action names follow the standard
  `<product>:<ApiAction>` convention for the actions above.
- Not verified: whether a deployment's policy engine requires an explicit
  grant for `sts:GetCallerIdentity`. Identity resolution normally succeeds for
  any valid credential. If the engine rejects the action name, drop that single
  line; the diagnosis script already degrades gracefully when identity is
  unavailable and reports the missing baseline instead of guessing an account.

## Reporting a denial

When a query is denied, do not stop the diagnosis and do not retry blindly.

1. Name the exact action that was denied, from the table above.
2. Print the minimal policy fragment that adds only that action.
3. Use `NoPermission` when the denial comes from an explicit Deny statement or a
   permission verdict, and `ImplicitDeny` when no statement grants the action at
   all. These are the two literals this skill reports.
4. Record the query in the degradation log, keep running the remaining queries,
   and finish with `STATUS: DEGRADED` naming the evidence that is now missing
   and the conclusion that missing evidence prevents.

## Area: console-resource-lookup
# RAM permission points for this skill

Every action below is one the scripts in `scripts/` actually call, and nothing
listed here is unused. There is no wildcard grant: no entry stands for every
action of a product. This skill is read-only; it requests no permission whose
name begins with a change verb.

| Product | CLI invocation | API action | RAM action point | Why it is needed |
|---|---|---|---|---|
| ecs | `aliyun ecs describe-instances` | `DescribeInstances` | `ecs:DescribeInstances` | Cross-region existence sweep: where the "missing" instance actually is, its status, charge type and lock state |
| ecs | `aliyun ecs describe-instance-status` | `DescribeInstanceStatus` | `ecs:DescribeInstanceStatus` | Independent lightweight status reading to cross-check what the console displays |
| ecs | `aliyun ecs describe-available-resource` | `DescribeAvailableResource` | `ecs:DescribeAvailableResource` | Buy-side visibility for "this region is not selectable" intake questions |
| sts | `aliyun sts get-caller-identity` | `GetCallerIdentity` | `sts:GetCallerIdentity` | Credential pre-flight and the account-scope provenance label on every report |

All three ECS actions belong to API version `2014-05-26`; STS belongs to
`2015-04-01` (central endpoint `sts.aliyuncs.com`). The action list above is
exactly the verified api-info surface injected for this tier; the per-action
RAM keys follow the one-to-one ECS action naming convention. If a live call
ever reports that one of these keys differs for your account, trust the
service response and stop -- do not widen the grant to make the error go away.

## Parameters the scripts actually send

| Action | Parameters |
|---|---|
| `DescribeInstances` | `RegionId` (one value per sweep step), `InstanceIds` (JSON array), `InstanceName`, `PublicIpAddresses`, `PrivateIpAddresses`, `ResourceGroupId`, `PageSize`, `PageNumber` |
| `DescribeInstanceStatus` | `RegionId`, `InstanceId.1..N` (max 10 per call), `PageSize` |
| `DescribeAvailableResource` | `RegionId`, `DestinationResource`, optional `InstanceChargeType`, `InstanceType`, `ZoneId`, `ResourceType` |
| `GetCallerIdentity` | none beyond the region/endpoint the CLI resolves |

No other parameter is assumed. The sweep calls the read actions once per
region from the embedded region list (overridable with `--regions`, prioritized
with `--region-hint`); the queried list is echoed in the report, so the
visibility conclusion always carries its exact scope.

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
        "ecs:DescribeAvailableResource"
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

`Resource: "*"` on read-only describe actions exposes metadata the caller
could already list; narrow to specific instance ARNs if the customer's
governance requires it. Drop `ecs:DescribeAvailableResource` entirely when no
buy-side visibility question will be asked: the lookup path degrades to the
visibility triage flow and the entry map, and the report records the skipped
step.

## Account, region and resource-group visibility

Visibility of these very calls depends on the RAM identity: a member account
without the grants above sees nothing, a resource-group-scoped identity only
sees its groups, and cross-account resources never appear regardless of
policy. The sweep therefore always prints the account id of the current
credential so a "missing resource" conclusion states which account it rules
out -- and only that one. When a policy audit or a policy change is what the
customer actually needs, that is a different skill's job
(`area:ram-policy-diagnosis`); this skill stops at naming the
missing read action.

## When a call is refused

| Returned code | Meaning | What the report says |
|---|---|---|
| `NoPermission` | the identity has no such grant | name the exact missing action point from the table and paste the statement above |
| `ImplicitDeny` | a policy or control denies it implicitly | say which action is denied and that the evidence chain is incomplete |

On refusal the scripts log `[WARN]`, keep every reading already collected, and
finish with `STATUS: DEGRADED`. Never widen permissions with any wildcard form
to "make the error disappear", never retry a refusal, and never ask the
customer to paste credentials -- the CLI resolves them through its default
chain.

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

## Area: vpc-connectivity-check
# RAM Policies - area:vpc-connectivity-check

## 1. Scope of this document

This skill is **strictly read-only**. The list below is the complete set of
RAM action permissions the scripts can ever require - one entry per OpenAPI
action actually invoked through `scripts/areas/vpc_connectivity_check/_cli.py`, aligned three ways with
`related_apis.yaml` and with the hard whitelist
`ALLOWED_ACTIONS` in `scripts/areas/vpc_connectivity_check/_constants.py`. Any action not listed here is
rejected by the whitelist guardrail before a process is spawned, so the
credential never needs a permission this document does not declare.

No write permission is required or requested. Remediation of a found
misconfiguration is always performed by a human in the console (see the
manual guidance emitted by the scripts), never by this skill.

## 2. Required read-only actions

| Product | RAM action | API version | Why the skill needs it |
|---|---|---|---|
| ecs | `ecs:DescribeInstances` | 2014-05-26 | Source of truth for `VpcId`, `VSwitchId`, `ZoneId`, primary/secondary private IPs, bound security-group IDs, instance type and charge type - used by the pair, transfer, ip-inventory and public-path checks |
| ecs | `ecs:DescribeInstanceStatus` | 2014-05-26 | Live running state context for the compared instances (a stopped instance answers nothing on any port) |
| ecs | `ecs:DescribeSecurityGroupAttribute` | 2014-05-26 | Rule-level read of the in-effect security groups: direction, policy, protocol, port range, source/destination and priority, so the pair check judges the actual rules instead of only the bindings |
| ecs | `ecs:DescribeAvailableResource` | 2014-05-26 | Availability-zone context for the instance family, which supports the "target vSwitch zone is not selectable" reading |
| vpc | `vpc:DescribeEipAddresses` | 2016-04-28 | EIP presence and in-use status for the "reachable on the intranet but not from the internet" branch |
| sts | `sts:GetCallerIdentity` | 2015-04-01 | Verifies which account the active credential belongs to and supplies the account UID traceability label; every result is scoped to this single account |

These are the exact action names to grant. Do not widen them.

## 3. Least-privilege policy fragment

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeSecurityGroupAttribute",
        "vpc:DescribeEipAddresses",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` is intentional and is the narrowest practical shape here: the
listed actions are collection-level read queries whose scope is already
limited by the `RegionId` and instance-ID parameters the caller passes, and
several of them accept no single-resource ARN at request time. The grant
still contains no write action and no wildcard action name.

## 4. Wildcard prohibition

Never grant or document a wildcard action for this skill: a permission entry
must always name one complete, verified action, and a product prefix followed
by an asterisk is never acceptable here. Also never add a policy entry that is
not backed by an actual call in `scripts/`. If a future version of the skill
needs another read action, it must first be verified (existence, parameter
names, response fields) and then added to all three places at once:
`scripts/areas/vpc_connectivity_check/_constants.py`, `related_apis.yaml`, and this file.

## 5. Missing-permission handling

When a call is refused because the RAM identity lacks one of the actions
above, the scripts degrade gracefully: the failing action is reported as a
`[WARN]` line plus a "Graceful Degradation Log" entry, and the run ends with
`STATUS: DEGRADED` (or `STATUS: FAIL` when no evidence at all could be
collected).

Agent behaviour on a permission failure:

1. Name the **exact** missing action (for example
   `ecs:DescribeAvailableResource`) rather than reporting a generic error.
2. Quote the literal error code returned by the API - authorization
   failures surface as `NoPermission` or `ImplicitDeny`.
3. Emit the minimal-scope fragment from section 3, trimmed to that one action, so
   the customer or administrator can grant it.
4. Never work around the denial: no alternate credential, no assumption of a
   different role, and no attempt to obtain or handle an AccessKey pair
   directly. Authentication always comes from the aliyun CLI default
   credential chain.

## 6. Credential handling rule

This skill performs **no** explicit credential handling. It never reads,
prints, caches, stores or transmits an AccessKey ID, AccessKey secret or STS
token, and it never asks the customer to paste one. The CLI error text that
the scripts do surface is passed through credential masking first, so any
`AccessKeyId` / `SecurityToken` / signature value inside a signed-request
echo is replaced with `***` before it can appear in output. To switch
account, the customer configures the CLI credential profile externally
(the CLI default credential chain) and passes `--profile` to the entry script.

## 7. Related documents

- Skill entry point and execution contract: `../SKILL.md`
- Symptom routing and root-cause decision tree:
  `vpc-intranet-connectivity.md`

## Area: instance-relocation-guide
# Requested permissions

This skill is read-only. It asks for four specific actions and nothing else.
There is no wildcard in the action list, and no state-changing action is
requested.

| Action | Read or write | Used by | Why the skill needs it |
| --- | --- | --- | --- |
| `ecs:DescribeInstances` | read | `scripts/areas/instance_relocation_guide/relocation_preflight.py` | Region, zone, instance type, charge mode, expiry, image id, addresses and security groups of the instance being relocated |
| `ecs:DescribeInstanceStatus` | read | `scripts/areas/instance_relocation_guide/relocation_preflight.py` | Lightweight state confirmation before a change window is scheduled |
| `ecs:DescribeAvailableResource` | read | `scripts/areas/instance_relocation_guide/relocation_preflight.py` | Capacity of the destination region or zone for the planned instance type |
| `sts:GetCallerIdentity` | read | `scripts/areas/instance_relocation_guide/sts_token.py` | Confirms a usable credential and attributes the report to an account |

## Minimal policy

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

`Resource` is open on purpose: the three ECS reads above are account- and
region-scoped list queries, so an instance-level scope would hide results rather
than narrow risk. The action list stays explicit.

## Request attribution

Every call made under these permissions carries the skill User-Agent described
in [../SKILL.md](../SKILL.md), which includes the session id generated for that
execution, so a request can be traced back to one report. Authentication stays in
the default credential chain; no key, secret or token value is read, written or
displayed by this skill.

## Boundary of the permission model

The steps this skill recommends are carried out by the customer in the console,
under the customer's own permissions, after reading the risk notice. That is a
deliberate boundary, not a limitation of the policy above: this skill neither
requests nor performs any state-changing operation, and it does not execute
commands inside the guest operating system.

## When a call is denied

A denial is reported, not worked around.

| Returned code | What it means | What the skill prints |
| --- | --- | --- |
| `NoPermission` | The policy held by the identity does not allow that action | The missing action plus the corresponding `Action` line from the policy above |
| `ImplicitDeny` | No statement allows the action, so it is denied by default | A request to add a read-only policy covering that action |

Either case ends the affected section with `STATUS: DEGRADED` and keeps the
remaining checks going. Never ask the customer for an access key, a secret or
a token; authentication stays in the default credential chain of the CLI.

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

## Area: unexpected-reboot-diagnosis
# RAM Policies

Every permission this skill needs, at action granularity. No wildcard action
entry appears anywhere in this package, and no permission is declared that
the scripts do not actually call.

This skill is **not** a query-only package. It declares two write-class
actions alongside its queries, and each write sits behind the confirmation
gate written into `SKILL.md` and enforced by
`scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py` (`--user-confirmed` plus `--approval-quote`).

## Actions used

| Product | Action | Class | Permission point | Called from |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | query | `sts:GetCallerIdentity` | `scripts/areas/unexpected_reboot_diagnosis/sts_token.py`, identity step |
| ecs | `DescribeInstances` | query | `ecs:DescribeInstances` | `fetch_instance` |
| ecs | `DescribeInstancesFullStatus` | query | `ecs:DescribeInstancesFullStatus` | `fetch_full_status` |
| ecs | `DescribeInstanceHistoryEvents` | query | `ecs:DescribeInstanceHistoryEvents` | `fetch_history_events` |
| ecs | `DescribeInstanceMaintenanceAttributes` | query | `ecs:DescribeInstanceMaintenanceAttributes` | `fetch_maintenance` |
| ecs | `DescribeDisks` | query | `ecs:DescribeDisks` | `fetch_disks`, snapshot precheck |
| ecs | `DescribeInstanceTypes` | query | `ecs:DescribeInstanceTypes` | `fetch_instance_type` |
| ecs | `DescribeCloudAssistantStatus` | query | `ecs:DescribeCloudAssistantStatus` | `fetch_cloud_assistant`, probe precheck |
| ecs | `DescribeInvocations` | query | `ecs:DescribeInvocations` | `fetch_invocations`, probe polling |
| cms | `DescribeMetricLast` | query | `cms:QueryMetricLast` | `fetch_metrics` |
| ecs | `RunCommand` | write (gated) | `ecs:` + `RunCommand` | `run_guest_probe` |
| ecs | `CreateSnapshot` | write (gated) | `ecs:` + `CreateSnapshot` | `run_create_snapshot` |

A permission point cell that shows two tokens around a `+` means
concatenation with nothing between them: `ecs:` plus an action name is one
RAM action string, and that joined string is what goes into a policy.

**The name trap** - the CloudMonitor action invoked (the CLI and OpenAPI
name) is `DescribeMetricLast`, but its RAM permission point is named
differently, `cms:QueryMetricLast`. Granting a policy entry spelled after
the API name would still deny the call. Verified against the batch
permission checklist and a live call.

## Why each gated write is needed

`RunCommand` under the `ecs` RAM code is write-class because it dispatches a
command into a customer instance. This skill uses it only to carry ONE
non-mutating inspection command from the frozen whitelist in
[guest-inspection-whitelist.md](unexpected-reboot-diagnosis__guest-inspection-whitelist.md), after the
operator has been told exactly what will run and has confirmed that single
call. It is never used to carry cleanup, service control, or any command
built from shell composition. Each invocation creates a Cloud Assistant
record on the instance; that is disclosed before the call.

`CreateSnapshot` under the `ecs` RAM code is the snapshot-first safety net
required before any cleanup or risky handling the customer performs. It adds
a copy and alters no existing data, but snapshots bill by stored capacity
and retention time; the billing consequence is disclosed before the call and
deletion of old snapshots stays a human decision. Local disks are refused at
this step because they cannot be snapshotted at all.

## Minimal policy, query only

Sufficient for `check-auth`, `diagnose`, and `explain`. A customer who wants
no write capability at all grants only this fragment; the skill then degrades
the guest-verification and snapshot legs to documented manual steps and says
so in the report.

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
        "ecs:DescribeInstanceMaintenanceAttributes",
        "ecs:DescribeDisks",
        "ecs:DescribeInstanceTypes",
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

Adds the two gated writes. Grant this only where the session is expected to
verify facts inside the guest or take a guard snapshot. Before applying the
fragment above as the full policy, append to the same `Action` list the
joined strings of the two gated permission points shown in the table,
`ecs:` plus `RunCommand` and `ecs:` plus `CreateSnapshot`, each as its own
quoted entry.

Where the engagement allows it, split the two gated writes into their own
statement scoped to the specific region and instance or disk identifier
being diagnosed, rather than leaving them open. The query actions generally
do not support resource-level authorization, so they stay as they are.

## Actions this skill never calls

The `Delete`, `Release`, `Reset`, `Replace`, `Attach`, `Detach`, `Reboot`,
`Start`, `Stop`, `Modify`, `Import`, `Export`, `Revoke`, `Bind`, `Unbind`
families are refused by `NEVER_ALLOWED_ACTION_PREFIXES` in
`scripts/areas/unexpected_reboot_diagnosis/_constants.py`, and the refusal holds even after a customer
confirmation. Rebooting or stopping the instance - the single most requested
action in this tier - is always a human action performed in the console or
through the customer's own tooling. Do not add any of these to a policy for
this skill.

## Denied calls

A denied call surfaces with the code the platform reported, normalised to
`NoPermission` or `ImplicitDeny`. The degradation log names the specific
step, and this file carries the fragment that supplies it. The remedy is a
policy change in the customer's account; it is never a request for an
AccessKey pair, and this package does not accept, read, store or forward
one.

Where the caller has the query permissions but not the gated writes, the
correct behaviour is to continue and degrade: deliver the cloud-side
verdicts, mark the guest-verification leg as unconfirmed, and hand the
whitelisted commands over as customer-executed steps whose output returns
through `explain`.

## Area: service-escalation-guide
# Minimal Read-Only RAM Policy

This skill is a strictly read-only, guide-type skill for ECS service-process
demands (support-ticket follow-up wording and service-complaint material
preparation). The two optional ECS reads below are corroboration only: the
skill's core value (classification, material package, handoff routing) works
with zero cloud access, and nothing here grants or assumes ticket-system
access.

## Required actions

| # | RAM Action | API Version | Endpoint | Purpose |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | Credential pre-check and local traceability label (`scripts/areas/service_escalation_guide/sts_token.py`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | `ecs.<region-id>.aliyuncs.com` | Read-only instance corroboration for the package appendix: existence, region/zone, type, state (`scripts/areas/service_escalation_guide/ecs_service_escalation.py --collect-evidence`) |
| 3 | `ecs:DescribeInstanceStatus` | 2014-05-26 | `ecs.<region-id>.aliyuncs.com` | Read-only lifecycle-state read-back of the same instances at query time (`scripts/areas/service_escalation_guide/ecs_service_escalation.py --collect-evidence`) |

All three actions are Describe/Get-class read queries. The granted action
set contains no write-class action name of any shape.

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
      "Sid": "ReadOnlyEcsInstanceEvidence",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInstanceHistoryEvents",
        "ecs:DescribeDedicatedHosts",
        "ecs:DescribeDisks",
        "ecs:DescribeDiskMonitorData"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (product level
  or account level) are not allowed for this skill and the static checker
  rejects them.
- `Resource: "*"` is the minimum expressible scope for Describe-class ECS
  reads scoped at account level in a custom policy; the read-only guarantee
  comes from the action list itself, which contains only Describe/Get names.
- No `Deny` statements are required; anything not listed above is not
  granted by this policy.

## Deliberately NOT granted

- Any support-ticket or service-platform action: this skill has **no**
  ticket-system integration. It never reads ticket state, never follows up,
  never expedites, never changes priority, and never submits or withdraws
  anything. Do not grant such permissions "for convenience"; the guide
  works without them and must keep claiming nothing about ticket state.
- Any mutating ECS action (`Modify*`, `Start*`, `Stop*`, `Reboot*`,
  `Reset*`, `Attach*`, `Detach*`, `Release*`, `Create*`, `Delete*` forms):
  out of the read-only whitelist in SKILL.md Absolute Rule 2; such wording
  must never appear as a granted action in this file (static rule 2.2.8).
- `DescribeAvailableResource` (ecs): excluded for this tier because its RAM
  permission point was never verified for it; purchase/inventory complaints
  are handed off to `area:instance-modify-diagnosis` instead of
  being evidenced here (see `references/service-escalation-guide__handoff-matrix.md`).

## Resource scope

| Aspect | Scope |
|---|---|
| Region | One explicit `RegionId` per evidence run, supplied by the customer; never guessed |
| Resources | Only the instances matching the optional id filter in that region |
| Data exposed | Instance inventory facts: id, name, zone, type, OS label, charge type, lifecycle state, VPC/security-group ids |
| Mutations | None possible; the action list has no write-class name |

## How to grant

Option A -- RAM user (same-account use, recommended):

1. RAM console -> Identities -> Users: select the user that runs the CLI.
2. Create a custom policy from the JSON above (Permissions -> Policies ->
   create policy -> script mode).
3. Attach it to the user. The scripts resolve credentials exclusively
   through the aliyun CLI default credential chain; they never take
   credential arguments.

Option B -- RAM role (cross-account or temporary access):

1. Create a RAM role trusted by the calling account and attach the policy
   above.
2. Assume the role and configure the temporary credential as a named CLI
   profile; pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the three actions above; attach no administrator policy.
- Prefer a RAM role with a short session over long-lived keys.
- Never share credentials; never store them in this skill directory.
- When a read returns `NoPermission` or `ImplicitDeny`, record the missing
  action name from this table, degrade per SKILL.md Absolute Rule 8, and
  continue producing the material package without the attachment.

## Area: stop-mode-billing-guide
# RAM permissions for this skill

This skill is read-only. It declares and uses exactly three ECS read actions plus
one identity check. There is no change-making action in this package, in any script,
or in any answer template.

## Actions actually called

| Action | Product | API version | Called by | Why the call is needed |
|---|---|---|---|---|
| `ecs:DescribeInstances` | ecs | 2014-05-26 | `scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py` (`assess`, `report`) | Read the instance list, region and zone, power state, billing method, instance type, public and private addresses |
| `ecs:DescribeInstanceStatus` | ecs | 2014-05-26 | same (`verify-status`, `report`) | Re-read the power state after the customer acted in the console |
| `ecs:DescribeAvailableResource` | ecs | 2014-05-26 | same (`check-stock`, `report --with-stock`) | Read-only zone availability side-evidence when a restart fails |
| `sts:GetCallerIdentity` | sts | 2015-04-01 | `scripts/areas/stop_mode_billing_guide/sts_token.py` | Prove the default credential chain works and tag report lines with the account |

The Action list above stays a list of concrete names: no product-level wildcard
action is used, requested, or needed. Nothing in this package writes, converts,
assigns, removes or restarts a resource.

## Minimal policy

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
      "Resource": "*"
    }
  ]
}
```

`Resource` is a star here because the three calls are collection-level reads that
the service does not scope to a single instance. `sts:GetCallerIdentity` needs no
statement: the service grants it to the authenticated principal itself.

## When a call is refused

The scripts print the failed code, the missing action name and this policy block.
The two literals to look for and to quote back to the customer are:

- `NoPermission` - the action is not allowed for this principal;
- `ImplicitDeny` - no policy grants it, so the request is denied by default.

Recovery path, in this order:

1. Confirm which of the four actions above is missing.
2. Attach the minimal policy block to the RAM user or role in the RAM console.
3. Re-run the same read-only command. Never broaden to a wildcard to "make it work".

## Scope and visibility limits

- Only instances owned by the account behind the current credentials are visible,
  and only inside the region passed on the command line.
- A cross-account instance, or an instance in a region that was not queried, simply
  does not appear. Absence from the answer is never proof of absence in the cloud.
- Billing amounts are not part of this policy: this skill has no billing action, so
  the customer reads the bill on the console page listed in
  `references/stop-mode-billing-guide__stop-mode-billing-rules.md`.

## Credentials

All calls use the default credential chain of the running environment. This package
contains no access key handling of any kind: no key file, no key parameter, no key
prompt, and no key in any output. Error text passes through a masking step so that
token and signature values in a message are redacted before they are printed.

## Area: smtp-block-diagnosis
# RAM Policy Requirements

Exact action list used by this skill's scripts, one entry per invoked read
API; the consent-gated guest probe is documented separately below.
No wildcard actions (`prefix` + colon + asterisk) appear in this file, by
policy: every action is enumerated, and least privilege is the point.

Permission model (RO+G): this skill makes **no cloud configuration change**
and it never submits, tracks or promises a port-25 unblock application. Its
one state-changing-from-the-cloud-API capability is dispatching a single
**inspection-only** command into the customer's own Linux instance through
Cloud Assistant. That dispatch happens only after the operator has shown the
user the exact command text plus scope, reversibility and duration, and the
user approved that one command (SKILL.md 'Guest Evidence Gate'). Without the
confirmation token the scripts do not call the probe operation at all, and
every in-guest question falls back to commands the CUSTOMER runs in their own
session.

## Required actions

| # | Action | API version | Product endpoint | Used by | Purpose |
|---|--------|-------------|------------------|---------|---------|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` (central) | `scripts/areas/smtp_block_diagnosis/sts_token.py`, entry script identity step | Verify the caller, label the report with the account UID, surface the sub-account permission-gap case |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | regional ECS endpoint via `--region` | `scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py` | Locate the instance; read region, status, network type, public-IP form (fixed public IPv4 vs EIP vs classic), attached security-group ids |
| 3 | `ecs:DescribeInstanceStatus` | 2014-05-26 | regional ECS endpoint via `--region` | `scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py` | Cross-check the lifecycle state (rules out "instance stopped, so no mail"); refuses a probe on a non-Running instance |
| 4 | `ecs:DescribeInvocations` | 2014-05-26 | regional ECS endpoint via `--region` | `scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py` (`--include-invocations`, and the probe read-back) | List the customer's own past Cloud Assistant invocation records, and fetch the status/output (`IncludeOutput=true`) of the one probe this skill dispatched |
| 5 | `ecs:DescribeSecurityGroupAttribute` | 2014-05-26 | regional ECS endpoint via `--region` | `scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py` (send direction, per attached security group) | Read the EGRESS rules of the instance's attached security groups to decide whether a DROP rule covers TCP 25/465/587; without it the cloud-side rule layer is reported UNKNOWN |

Actions 1–5 are Describe/Get reads and are the complete set of RAM actions
this skill needs declared for its own operation. Action 5 is read-only: it
never authorizes, revokes or edits a rule.

## Consent-gated probe operation (Class B) - no declared grant

The guest probe is dispatched through Cloud Assistant via the CLI plugin-mode
command `run-command` (the underlying API name is `RunCommand`, declared in
`related_apis.yaml`). It is a write-class operation even though the command it
carries only inspects, which is exactly why it carries no entry in the policy
statement below: it runs only under whatever rights the customer's own
credentials already hold, and only after the 'Guest Evidence Gate' disclosure
and the user's approval of that one command (`--execute-probe` +
`--user-confirmation`). The dispatchable text is a closed set of templates held
in `GUEST_PROBES` in `scripts/areas/smtp_block_diagnosis/_constants.py`, never user input. A principal
limited to the read-only grant is a supported mode, not a defect: the probe is
then denied and the report degrades to the manual readings checklist.

## Minimal policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "SmtpBlockDiagnosisEvidenceAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInvocations",
        "ecs:DescribeSecurityGroupAttribute",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes on the document:

- The probe operation carries no entry in the document above on purpose: it
  is consent-gated and runs under the customer's own credentials wherever the
  in-guest probe channel is actually wanted. A principal limited to the
  read-only statement still runs the skill end to end, answering the guest-side
  questions from the manual readings checklist instead (`STATUS: DEGRADED`
  until those arrive).
- **Read the privilege caveat before enabling the probe.** Granting the
  underlying `RunCommand` capability lets a principal run commands as root
  inside the instances it can reach; RAM cannot express "only these four
  inspection templates". The confinement to inspection-only text is enforced
  in this skill's code (whitelisted templates, target host regex, prohibited
  verb and redirect checks, one probe per approved run, confirmation token).
  Enable it only for a principal you trust to run this skill, and narrow
  `Resource` to the specific instance ARNs if your account supports
  resource-level authorization for ECS write actions — check the current ECS
  authorization reference rather than assuming.
- `Resource: "*"` above is the account-wide form used because the read
  actions in the first statement need no resource scoping; it is not a claim
  that scoping is unsupported.
- Deny statements are unnecessary: everything outside the listed actions is
  already unavailable to the principal.

## Never granted, never called

Deliberately absent from the policy above — the skill refuses these even if
the credential happens to allow them, because they would cross from
diagnosis into change management:

- security-group rule writes (`AuthorizeSecurityGroup`,
  `RevokeSecurityGroup`, `ModifySecurityGroupRule`, `…Egress` variants) and
  rule readers that are not part of this tier's verified API surface;
- instance lifecycle writes (`StartInstance`, `StopInstance`,
  `RebootInstance`, `DeleteInstance`, instance reconfiguration);
- every Cloud Assistant action other than `RunCommand` with an inline
  whitelisted template — notably `InvokeCommand` (it runs a stored command id
  this skill cannot audit), `CreateCommand`, `SendFile`, `StartTerminalSession`,
  `StopInvocation`, `DeleteCommand`;
- VPC / route / NAT / EIP association writes and any guest firewall edit;
- anything touching the port-25 unblock application or mail-product
  activation and billing (no public API exists for the application workflow
  at all — see references/smtp-block-diagnosis__unblock-application-path.md).

## When access fails

The scripts surface the raw API error code (masked of any credential
material). Expected denial literals and handling:

| Literal seen | Meaning | Action for the administrator |
|--------------|---------|------------------------------|
| `NoPermission` | the principal lacks one of the five read actions | attach the policy above (or add the named missing action) to the principal, then re-run |
| `ImplicitDeny` | no policy grants the action at this scope | same remedy; check control policies / resource-group boundaries |

A denial on the `run-command` probe is not fatal: the entry script reports the probe
as `dispatch-failed`, keeps the rest of the diagnosis, and the manual
readings checklist closes the same evidence gap. When reporting a denial to
the user, name the missing action explicitly and point at this file — never
invent a broader grant.

## Sub-account note (matches a recurring ticket pattern)

RAM sub-accounts frequently CAN run the Describe/Get queries above yet
CANNOT view or submit the port-25 unblock application in the console. That
second gap is outside this policy's scope and outside this skill's handling:
detect it with `scripts/areas/smtp_block_diagnosis/sts_token.py` (identity type `SubUser`), then follow
references/smtp-block-diagnosis__handoff-boundaries.md toward the RAM authorization diagnosis — the
skill never edits grants itself.

## How to attach (manual, customer side)

1. RAM console → Permissions → Policies → create a policy from the JSON
   document above (script mode).
2. Attach it to the RAM user or role that will run the diagnosis.
3. Ensure the aliyun CLI default credential chain resolves to that
   principal (the CLI default credential chain); this skill never accepts credential
   values as arguments and never prints them.

## Area: ddh-capacity-guide
# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS guidance for Dedicated Host (DDH),
capacity reservation and host-event questions. It requires the STS identity
action plus six read-only ECS Describe actions. No wildcards are used in any
action name, and no mutating action is declared.

## Required actions

| # | RAM Action | API Version | Endpoint | Purpose |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | Verify the caller identity and derive the account UID traceability label (`scripts/areas/ddh_capacity_guide/sts_token.py` and the built-in identity step of `scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | regional `ecs.<region>.aliyuncs.com` | Read instance attributes (instance type / family, status, zone, bound security groups) and perform the account+region visibility pre-check (`scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |
| 3 | `ecs:DescribeInstanceStatus` | 2014-05-26 | regional `ecs.<region>.aliyuncs.com` | Cross-check the running state per instance for the "shows Running but unresponsive" boundary (`scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |
| 4 | `ecs:DescribeInstanceHistoryEvents` | 2014-05-26 | regional `ecs.<region>.aliyuncs.com` | System-event history (`SystemMaintenance.Reboot` / `*.Redeploy` / `*.IsolateErrorDisk` / `*.ReInitErrorDisk`): the issue and execution record behind "the host restarted or redeployed my instance" (`scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |
| 5 | `ecs:DescribeDedicatedHosts` | 2014-05-26 | regional `ecs.<region>.aliyuncs.com` | Dedicated-host status and physical metrics, so a host-failure question is answered from a read instead of "only the console shows it" (`scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |
| 6 | `ecs:DescribeDisks` | 2014-05-26 | regional `ecs.<region>.aliyuncs.com` | Disk inventory used to pick the disk whose performance is then read (`scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |
| 7 | `ecs:DescribeDiskMonitorData` | 2014-05-26 | regional `ecs.<region>.aliyuncs.com` | Cloud-disk IOPS/BPS/latency samples for the "Running but storage ceiling unreachable" branch (`scripts/areas/ddh_capacity_guide/ddh_capacity_guide.py`) |

All three actions are read-only Describe/Get-class APIs. They never create,
delete, modify, reboot, start, stop, migrate or otherwise change any resource,
and they never execute commands inside a guest.

**Read-Only Guarantee**: the granted action set contains no mutating verb
(create / delete / modify / update / put / attach / detach / reset / release /
reboot / start / stop / run are all absent), so the credential physically cannot
change any resource or configuration state.

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
      "Sid": "ReadOnlyEcsInstanceQuery",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk form,
  at the product or global level) are forbidden for this skill.
- `Resource: "*"` is the minimum practical scope here: the skill answers
  account-wide capacity and host-event questions and does not know the target
  resource ARNs in advance. Read-only effect is guaranteed by the action list
  itself (Describe/Get only). To narrow further, replace `"*"` with the specific
  instance ARNs the operator is allowed to inspect.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Action intentionally NOT granted (pending verification)

`DescribeAvailableResource` (the availability check used for reconfiguration /
DDH selection in the design) is a verified read-only action, but its RAM
permission point was not returned by the contract metadata for this tier and the
legal `DestinationResource` value set is unconfirmed. Following the confirmed
requirements document, it is therefore NOT granted here, NOT declared in
`related_apis.yaml`, and NOT invoked by the scripts until both the permission
point and the parameter values are measured. Availability questions are answered
from the built-in official-rule knowledge in the reference modules instead, and
the customer is pointed to the console for a live purchase / reconfiguration
check. This is the safe choice: a RAM action name must never be derived from the
API name.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | The `RegionId` supplied by the operator for each query; ECS Describe APIs are regional |
| Resources | Instances inside the current credential account and the queried region only; cross-account instances are not visible (an empty result is reported as a visibility boundary, never as "does not exist") |
| Data exposed | Instance type / family, running status, zone, bound security-group ids - read-only inventory data |
| Mutations | None possible; only Describe/Get-class actions are granted |

## How to grant

Option A - RAM user (same-account use, recommended for daily operation):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. Create a custom policy from the JSON above (Permissions -> Policies ->
   create policy -> Script mode).
3. Attach the policy to the RAM user.
4. Ensure the platform injects that RAM user's credentials through the CLI default chain.
   The scripts resolve credentials exclusively through the aliyun CLI default
   credential chain; they never take AK/SK arguments.

Option B - RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: create a RAM role trusted by the calling
   account.
2. Attach the policy above to the role.
3. Assume the role and configure the temporary credential as a named CLI
   profile; pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the three actions above; do not attach `AliyunECSFullAccess` or any
  administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in the
  skill directory.

## Area: punishment-appeal-guide
# RAM Policies — ECS Punishment Appeal Guide

## Minimal Permission Statement (read-only)

This skill declares and executes **only** the four ECS read actions below,
plus the STS identity check. Every conclusion it produces comes from these
queries; nothing else is called.

| Product | Action | RAM action | Purpose in this skill |
|---------|--------|-----------|------------------------|
| ecs | DescribeInstances | `ecs:DescribeInstances` | Instance existence, Status, public IPs, associated security groups, platform lock reasons |
| ecs | DescribeInstanceStatus | `ecs:DescribeInstanceStatus` | Lightweight status cross-check (non-running vs running) |
| ecs | DescribeSecurityGroups | `ecs:DescribeSecurityGroups` | Region security-group inventory |
| ecs | DescribeSecurityGroupAttribute | `ecs:DescribeSecurityGroupAttribute` | Ingress/egress rule comparison to tell a platform action apart from a configuration gap |
| sts | GetCallerIdentity | `sts:GetCallerIdentity` | Verify the credential and label which account the evidence covers |

## JSON Policy (copy as-is)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeSecurityGroupAttribute"
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

The `"Resource": "*"` above is the standard scoping placeholder for
Describe-level read inventory: the queries are region-scoped by the request
parameter, and the skill accepts only the caller's own visible resources.
The Action list itself is fully enumerated — no product-level wildcard such
as `ecs` colon star is used or permitted anywhere in this skill.

## What This Skill Never Requests

This skill is read-only end to end: every action declared above is a
`Describe*` or `Get*` read. No mutating, lifecycle or guest-side action of any
kind is declared, requested or used here, and no such permission point should
be granted for this skill. The exhaustive prohibition (which also covers the
customer-side console steps this package documents as guidance text only)
lives in `SKILL.md`, section "Absolute Rules".

## Handling Permission Failures

When a query is rejected, the scripts log `[WARN] <Code>: <Message>` and
continue, and the report closes with `STATUS: DEGRADED`. Typical codes and
the fix:

| Code | Meaning | Fix |
|------|---------|-----|
| `NoPermission` | The RAM identity lacks one of the enumerated actions | Grant the policy above (or add the single missing action) |
| `ImplicitDeny` | An effective-deny rule covers the action | Check control policies / resource-group policies, then retry |

## Principal-Authorization Branch (appeals)

Permission to READ is separate from standing to APPEAL: an appeal is only
accepted from the verified real-name subject of the account, or from a
representative holding an authorization for that subject. Before guiding an
appeal, confirm the requester acts for the account principal; otherwise
route them to the manual channel instead of preparing a submission.

## Area: cloud-assistant-diagnosis
# RAM permissions for area:cloud-assistant-diagnosis

This file is the authority for the permissions the skill asks for, and the
surface it declares is strictly read-only: the class A actions below, nothing
else. It is kept aligned, action by action, with the automatic calls in
`scripts/` and with the read-only subset of `related_apis.yaml`. The two
consent-gated operations (classes B and C) are documented here for review, but
no policy statement in this file grants a write action: those operations run
only under permissions the customer's own credentials already carry. Read the
three together; if they ever disagree, the scripts are the defect.

Do not broaden anything here. There is no wildcard action in this skill, and an
administrator must not add one to make a failure go away.

## Permission model

| Class | Meaning | Consent before each call |
| --- | --- | --- |
| A | Informational cloud query. Reads control-plane state, changes nothing. | No |
| B | Side-effect-free guest probe. Runs one whitelisted command inside an instance via the assistant channel. | Yes, one consent per command |
| C | Low-risk reversible write. Creates a snapshot. | Yes, one consent per disk |
| D | Destructive operation. | Never executed. Manual guidance only |

Only class A is a declared permission: the policy statements in this file
grant class A actions and nothing else. Classes B and C are consent-gated
operations that run under the customer's own credentials, never under a grant
from this file.

Class D covers deleting files, snapshots or cron entries, killing processes,
starting or stopping a service or instance, rebooting, truncating logs,
formatting, partition or filesystem changes, software installation or removal,
and any access-key or RAM governance action. Those get written steps, not
commands.

## Class A actions (automatic)

| Action | Product prefix | Used by | Purpose |
| --- | --- | --- | --- |
| `ecs:DescribeInstances` | ecs | `triage` | Does the instance exist, in this account, in this region; guest OS type and charge type. The ownership gate that ends wrong-account threads (case T-D87E8F47) |
| `ecs:DescribeInstanceStatus` | ecs | `triage` | Lightweight lifecycle state; anything but Running sends the thread to the instance-state area before an agent verdict is attempted |
| `ecs:DescribeInvocations` | ecs | `triage`, `invocations`, `guest-probe` (read-back) | Cloud Assistant execution history: status, exit code, error info, and retained output per task - the attribution core of this scenario and the evidence list for suspected abuse |
| `sts:GetCallerIdentity` | sts | `check-env` and once per run | Resolves which account the session belongs to, so a cross-account misdiagnosis is caught early and the account tail can be stamped on the report |

Notes on prefixes:

- The RAM action prefix is not always the CLI product name. Do not derive one
  from the other. `sts:GetCallerIdentity` is issued through the CLI in plugin
  mode as `aliyun sts get-caller-identity`, while the ECS read actions keep
  their PascalCase API names and run in the CLI's metadata mode as
  `aliyun ecs describe-invocations`. The consent-gated operations below are
  named by their CLI plugin-mode commands, `run-command` and `create-snapshot`.
- Every RAM action granted in this file's policy statements is the product
  prefix, a colon, and the full read-only API name - `ecs:DescribeInvocations`,
  not a pattern. Nothing here is abbreviated.

## Class B operation (one consent per command) - no declared grant

| Operation | CLI plugin-mode command | Used by | Constraint |
| --- | --- | --- | --- |
| Guest probe | `run-command` | `guest-probe` | Dispatches exactly one command taken from the whitelist in `guest-commands.md`, to one instance, after the disclosure. The assembled string is re-validated: a shell metacharacter or rejected token aborts the call before it is sent. |

The probe is a write-class operation even when the command it carries only
inspects - which is exactly why it holds no place in this skill's declared
permission surface. It runs only under whatever rights the customer's own
credentials already carry, and only after the disclosure step. A session
limited to the read-only grant below is a supported mode, not a defect: the
probe is then denied, the report degrades to the customer-run steps in
`guest-commands.md`, and the thread continues.

## Class C operation (one consent per disk) - no declared grant

| Operation | CLI plugin-mode command | Used by | Constraint |
| --- | --- | --- | --- |
| Pre-cleanup snapshot | `create-snapshot` | `snapshot-guard` | Sends `RegionId` and `DiskId` only. Refused unless the customer has been told that snapshots are billed by stored capacity and retention time. Snapshot-first is the condition for any cleanup, repair or expansion step the customer might take next. |

Same rule as class B: the operation is never granted by this file, needs one
explicit consent per disk, and on a strictly read-only session degrades to
printing the console step for the customer to take.

## Declared policy - queries and identity only

This is the skill's complete declared permission surface, not a reduced
fragment: sufficient for `check-env`, for `triage`, and for `explain`. The
consent-gated classes B and C above run, wherever the customer's own identity
allows them, without any grant from this file.

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
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    }
  ]
}
```

## No write statement - and none is added to fix a denial

The read-only policy above is the complete permission surface this file
grants. The two consent-gated operations deliberately have no statement
anywhere in this file: a diagnosis skill asks for read access only, a
per-operation consent is not a standing grant, and the operations still run
wherever the customer's own credentials already carry them. Where they do not,
the call is denied and the report degrades - the boundary working as designed.

No action outside those four read-only ones is granted, and no entry uses a
wildcard action. If a class A step fails for a missing permission, the fix is
the statement above - never a broader managed policy, never a write grant for
the consent-gated operations, never a wildcard.

## Actions deliberately NOT requested

The following APIs would each be useful somewhere in this scenario's decision tree,
and none is called, because its parameters or response shape were not verified
for this scenario (a guessed API is a hallucination with a billing consequence):

| API name | Why it is missing | What the skill does instead |
| --- | --- | --- |
| `ecs:DescribeCloudAssistantStatus` | not in the verified surface for this scenario | infers readiness from invocation history plus the customer's error wording, and says so |
| `ecs:DescribeCommands` | not in the verified surface for this scenario | points at the console command list and the query page documented in `agent-readiness.md` |
| `invoke-command` | required parameters not verified; and re-invoking a stored command the skill has not inspected breaks the announce-the-exact-string rule | dispatches whitelisted probes via the `run-command` operation only |
| CloudMonitor metric actions | neither the action name nor the metric identifiers were verified (note: its RAM action name differs from the API name), so nothing is guessed | CPU/IO saturation stays a candidate to confirm in the console, never a reading taken here |

## When a call is denied

A denied class A call fails as `NoPermission` or `ImplicitDeny`. Report the
missing action by name, hand the customer the matching statement fragment from
this page, and continue on the evidence that did arrive - the report degrades,
it does not guess. A denied class B or C operation is the read-only boundary
working as designed, not a missing grant: no statement for it exists in this
file, and none should be added; follow the degraded path in `guest-commands.md`
instead. Never work around a denial by trying a broader identity, a different
profile, or an API outside the whitelist.

## Area: image-billing-cleanup
# RAM Policies

Permissions required by `area:image-billing-cleanup`. Every entry is
a specific action. Wildcard permissions (a product prefix followed by an
asterisk) are prohibited in this package and must never be granted, never be
written into a policy for this skill, and never be suggested to a customer as a
fix.

## Actions used

| Action | RAM action | Class | Why this skill needs it |
| --- | --- | --- | --- |
| `DescribeInstances` | `ecs:DescribeInstances` | automatic | Lists instances with their billing method and the image each one runs; identifies whether a paid image still blocks an instance |
| `DescribeImages` | `ecs:DescribeImages` | automatic | Lists images with source, status, size and the snapshots behind them; the evidence for every cleanup verdict |
| `DescribeDisks` | `ecs:DescribeDisks` | automatic | Confirms the disk a backup snapshot will be taken from, its size, state and attachment |
| `DescribeInvocations` | `ecs:DescribeInvocations` | automatic | Reads the result of an already delivered inspection command (history and output, not live usage) |
| `GetCallerIdentity` | `sts:GetCallerIdentity` | automatic | Confirms which account UID the report covers |
| `RunCommand` (Class B — no declared grant) | dispatched via `aliyun ecs run-command ...` (CLI plugin mode); the real RAM action name is the service prefix plus this PascalCase API name, written by the customer's admin only on opt-in — this file deliberately spells neither the prefixed nor a lowercased variant inline | gated | Delivers ONE whitelisted, non-mutating inspection command per approval |
| `CreateSnapshot` (Class B — no declared grant) | same convention: bare API operation name here; the RAM action is assembled only when the customer opts in, by their own admin, on their own credentials | gated | Creates the ONE backup snapshot that must exist before a cleanup or space-releasing decision |

The two gated actions change state, so they run only after the customer has been
told the exact action, its blast radius and its reversibility, and has approved
that single action. The entry script enforces this: without `--confirm` it
prints the plan and changes nothing. Approval never carries over to the next
command, disk or run.

## Minimal policy - inventory only

Sufficient for `scope`, `faq`, `unblock-check`, `inventory` and
`invocation-result`:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeImages",
        "ecs:DescribeDisks",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimal policy (declared grants — read-only only)

The policy below is everything this skill declares on its own. The two gated
write operations (`RunCommand`, `CreateSnapshot` in the table above) are
deliberately NOT declared here: they run only after the customer approves that
single action, under the customer's own credentials. If the customer wants
this skill to create the pre-cleanup backup snapshot or to run an in-guest
inspection command on their behalf, their administrator adds the two write
actions at that time by pairing the service prefix with the exact PascalCase
API names shown in the table above; a lowercased or hyphenated variant is not
a valid RAM action and must never be pasted into a policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeImages",
        "ecs:DescribeDisks",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Narrow the resource scope to the customer's own instances and disks if their
security policy requires it; the action list above is the only part this skill
depends on.

## Permission errors

When a call is rejected, the surfaced code is `NoPermission` or `ImplicitDeny`.
Report it like this:

1. Name the single missing action, for example `ecs:DescribeImages`.
2. Point to the matching minimal policy snippet above.
3. Say which part of the answer is now unavailable, and continue with the rest of
   the inventory instead of aborting the whole run.
4. Never present a permission rejection as a product defect, never retry it in a
   loop, and never ask the customer for a credential.

## Never requested by this skill

No policy for this skill may contain an action that deletes or rewrites
resources: image deletion, snapshot deletion, image share changes,
operating-system or system-disk replacement, disk re-initialization, formatting,
resizing, instance release or lifecycle changes, unsubscription, renewal, refund
and any other billing or commercial action. Those operations stay manual console
steps performed by the customer, printed with their risk and their
irreversibility. The shared invocation layer refuses any action outside the
table above before a subprocess starts.

## Note on action names

Permission names are verified per action; they are never derived from an API
name. In this product family the two can differ - for example the CloudMonitor
last-metric query API maps to the permission `cms:QueryMetricLast`. This skill
does not call CloudMonitor at all: snapshot capacity fees are read from the
customer's bill, not from monitoring, so no monitoring permission belongs in the
policies above.

## Area: preemptible-instance-guide
# RAM policies — area:preemptible-instance-guide

This skill is **read-only**. The actions below are the complete set it can reach;
there is no wildcard and no mutating action. The agent must not ask for, and the
policy must not grant, anything beyond this list.

## Actions actually invoked

| Product | RAM action | Called by | Why this skill needs it |
|---|---|---|---|
| ecs | `ecs:DescribeInstances` | `scripts/areas/preemptible_instance_guide/spot_instance_check.py` | Instance existence, status, zone, charging type and spot bidding mode; the recycling lock reason when present |
| ecs | `ecs:DescribeInstanceStatus` | `scripts/areas/preemptible_instance_guide/spot_instance_check.py` | Batch status cross-check for a list of instance ids |
| ecs | `ecs:DescribeAvailableResource` | `scripts/areas/preemptible_instance_guide/spot_instance_check.py` | Whether a region / zone / instance type is sellable, including spot |
| sts | `sts:GetCallerIdentity` | `scripts/areas/preemptible_instance_guide/sts_token.py`, `scripts/areas/preemptible_instance_guide/_cli.py` | Label which account the read-only queries can see; no input parameters needed |

No other action is permitted. If the customer's question seems to need anything else
(a bill amount, a snapshot, a notification delivery record, a released instance's
history), the answer is a limitation plus a handoff, not a broader policy.

## Minimal policy snippet

Attach only if the diagnosis is scoped to specific instances, restrict
`Resource` accordingly; `DescribeAvailableResource` and the two describe-actions are
read-only and cost nothing to grant at region scope.

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

`Resource: "*"` here means "every ECS instance of this account" for **read** only; it
is not a wildcard action. Wildcard action entries, and any `Action` list containing a
mutating action, are out of scope for this skill and must not be used to make a question
go away.

## Notes on each action

- **`ecs:DescribeInstances`** — the region comes from `RegionId`, which the customer
  supplies; the script never defaults it. `InstanceIds` is sent as a JSON array string.
  Fields read: `Status`, `ZoneId`, `RegionId`, `InstanceChargeType`, `SpotStrategy`,
  `OperationLocks`, `InstanceName`.
- **`ecs:DescribeInstanceStatus`** — ids are sent as `InstanceId.1`, `InstanceId.2`, ...
  up to the cap in `scripts/areas/preemptible_instance_guide/_constants.py`.
- **`ecs:DescribeAvailableResource`** — parameters used: `RegionId`,
  `DestinationResource`, `InstanceChargeType` (auto-filled with `PostPaid`, declared in
  the report), optionally `InstanceType`, `ZoneId`, `SpotStrategy`. The response nesting
  is walked generically rather than assumed, so only returned values are reported.
  Bundled-contract caveat: the evidence bundle confirmed this action exists and listed
  its parameters, but left its RAM action entry blank in the injected policy table. The
  action name above is the standard form; confirm it in the RAM console before treating a
  denial here as a customer misconfiguration — the script reports such a denial verbatim
  and degrades instead of retrying elsewhere.
- **`sts:GetCallerIdentity`** — central endpoint, no region scoping, returns
  `AccountId`, `Arn`, `IdentityType`. Used only as a local traceability label.

## When a query is denied

The scripts surface the provider's own code, unmodified. Two literals are the ones this
skill documents:

- `NoPermission` — the action is not granted to the identity in use.
- `ImplicitDeny` — nothing grants the action, so the request is implicitly denied.

Expected customer-visible handling, in this order:

1. Name the exact action that was denied and the region that was queried.
2. Show the minimal snippet above and state that only the listed action needs adding.
3. Mark the run `STATUS: DEGRADED` (or `FAIL` if nothing could be read) and still give
   the rule-based answer plus the self-check paths, which need no credential at all.
4. Never substitute a broader policy, never fall back to a different action, and never
   retry with assumed credentials.

## Credential handling

Credentials are resolved exclusively by the Alibaba Cloud CLI default credential chain
(profile or platform-injected). There is no parameter, environment read, cache file or
log path in this skill that takes, stores or prints key material, and error text from
the CLI passes through the masking step in `scripts/areas/preemptible_instance_guide/_cli.py` before it can reach any
report field.

## Area: slb-backend-diagnosis
# Minimal Read-Only RAM Policy

This skill performs strictly read-only diagnosis of the traffic path between
load balancers (CLB / ALB / NLB) and backend ECS instances. It only calls
Describe / Get / Query-class read actions. No wildcard action (any asterisk
form, at the product or global level) is used anywhere in this policy, and no
mutating action is granted or needed.

## Required actions

| # | RAM Action | API Version | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | Verify the caller identity and derive the account UID label (`scripts/areas/slb_backend_diagnosis/sts_token.py`, and the built-in identity step of `scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | Backend ECS instance status, zone spread, instance type, security-group bindings, IP facts (`scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py`) |
| 3 | `cms:QueryMetricLast` | 2019-01-01 | Latest CloudMonitor datapoints per backend instance (`scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py`; the API name is `DescribeMetricLast` -- **RAM action name differs from the API name**, do not derive one from the other) |
| 4 | `vpc:DescribeEipAddresses` | 2016-04-28 | EIP status, bandwidth and binding facts, optionally narrowed to a declared load-balancer instance (`scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py`) |

All four actions are read-only. They never change any resource, listener,
security group, billing state or configuration.

## Intentionally undeclared: `ecs DescribeInstanceTypes`

The diagnosis script also issues a best-effort `DescribeInstanceTypes` call
(instance-type ceilings for "same weight but unbalanced load" suspicions).
The RAM permission point of that API is **not yet verified** for this tier,
so it is deliberately NOT listed in the policy above. Behavior without it:
the call fails with `NoPermission` / `ImplicitDeny`, the script records a
`[WARN]` line, marks the ceiling section degraded and continues -- the rest
of the diagnosis is unaffected. Once the permission point is verified by the
maintainers, add it here as a fifth explicit action (never as a wildcard).

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
      "Sid": "ReadOnlySlbBackendFacts",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "cms:QueryMetricLast",
        "vpc:DescribeEipAddresses"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries are prohibited
  for this skill.
- `Resource: "*"` is the practical minimum here: the queries are
  account/region-level read APIs (instance listings, metric datapoints, EIP
  inventories) and the skill only ever queries the resource IDs the customer
  named. Read-only effect is guaranteed by the action list itself.
- No `Deny` statements are required; anything not listed above stays denied
  by default (implicit deny).

## Read-only guarantee

The granted action set contains no mutating verb of any kind, so the
credential physically cannot change any cloud resource through this skill.
In addition, this skill never executes commands inside customer instances
and never accepts panel or instance passwords; all corrective actions are
output as step guidance for the customer to perform in their own console.

## Error-code mapping (authorization failures)

| Error code (stderr / body `Code`) | Meaning | What to grant |
|---|---|---|
| `NoPermission` / `NoPermission.*` | The RAM identity lacks one specific action above | The exact action named in the error message, from the table above |
| `ImplicitDeny` | Denied by policy because no statement allows the action | The matching action from the table above |
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` | Credential itself invalid | Re-configure the aliyun CLI credential chain (the CLI default credential chain); never paste keys into tickets or scripts |
| `SDK.InvalidCredential` / `DefaultChainFailed` | The CLI could not resolve any credential | Configure the default credential chain first |

When a permission error occurs the scripts print the failing action plus a
pointer to this file, then continue with the remaining checks (partial
evidence beats no evidence). Cross-account resources (for example instances
owned by another account or by a separately managed platform) are never
visible to these queries; the report states that boundary honestly.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | The region passed via `--region-id` (no silent region default is applied in the report) |
| Resources | Only the ECS instance IDs, EIP inventory and metric dimensions named or resolved in that region under the current credential |
| Data exposed | Instance status / zone / type / security-group IDs / IP addresses, latest CPU and traffic datapoints, EIP status and bandwidth -- read facts only |
| Mutations | None possible; only Describe / Get / Query-class actions are granted |

## How to grant

Option A -- RAM user (same-account use):

1. RAM console -> Identities -> Users: select the RAM user.
2. Permissions -> Policies -> create policy -> Script mode: paste the JSON
   above.
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential
   (the CLI default credential chain). The scripts resolve credentials exclusively through
   the aliyun CLI default credential chain; they never take key arguments.

Option B -- RAM role (temporary access):

1. RAM console -> Identities -> Roles: select a role trusted by the calling
   account.
2. Attach the policy above to the role.
3. Configure the assumed-role credential as a named CLI profile and pass it
   to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the actions above; never attach administrator or full-access
  system policies for this skill.
- Prefer short-lived role credentials over long-lived RAM-user keys.
- Never share credentials; never send keys in plaintext in a ticket or chat
  (if already sent, rotate them immediately).

## Area: hbr-backup-diagnosis
# RAM permissions for area:hbr-backup-diagnosis

This file is the authority for what the skill asks the cloud API for. It is kept
aligned, action by action, with `related_apis.yaml` and with the calls actually
present in `scripts/`. Read the three together; if they ever disagree, the
scripts are the defect.

Do not broaden anything here. There is no wildcard action in this skill, and an
administrator must not add one to make a failure go away.

## Permission model

| Class | Meaning | Consent before each call |
| --- | --- | --- |
| A | Informational cloud query. Reads control-plane state, changes nothing. | No |
| B | Side-effect-free guest probe. Runs one whitelisted command inside an instance. | Yes, one consent per command |
| C | Low-risk reversible write. Creates a snapshot. | Yes, one consent per disk |
| D | Destructive operation. | Never executed. Manual guidance only |

Class D covers deleting or emptying files, stopping or restarting a service or
instance, cancelling a backup, deleting a backup plan or backup vault, deleting a
snapshot, formatting or detaching a disk, changing a security group, route, NACL,
resolver or instance password. Those get written steps, not commands.

## Class A actions (automatic)

| Action | Product prefix | Used by | Purpose |
| --- | --- | --- | --- |
| `ecs:DescribeInstances` | ecs | `triage`, `billing-attribution` | Does the instance exist, in which region, what status and charge type, is it really released |
| `ecs:DescribeDisks` | ecs | `triage`, `billing-attribution` | Provisioned capacity, category, disk role and charge type |
| `ecs:DescribeSnapshots` | ecs | `billing-attribution`, `snapshot-guard` | Whether snapshot storage exists and therefore is billed; confirming a requested snapshot |
| `ecs:DescribeInvocations` | ecs | `triage`, `guest-probe` | Cloud Assistant invocation history, and read-back of a guest probe result |
| `sts:GetCallerIdentity` | sts | `check-env` and once per run | Resolves which account the session belongs to, so a cross-account misdiagnosis is caught early |

Notes on prefixes:

- The RAM action prefix is not always the CLI product name. Do not derive one
  from the other. `sts:GetCallerIdentity` is issued through the CLI in plugin
  mode as `aliyun sts get-caller-identity`, while the ECS actions keep their
  PascalCase API names.
- CloudMonitor is deliberately absent. Its metrics would be useful for the
  resource-saturation candidate, but neither its action name nor its query
  parameters were verified for this tier, so nothing is requested for it and
  nothing is called. See `decision-tree.md` section "Known gaps".

## Class B actions (one consent per command)

| Action | Product prefix | Used by | Constraint |
| --- | --- | --- | --- |
| `RunCommand` | ecs | `guest-probe` | Dispatches exactly one command taken from the whitelist in `guest-commands.md`. The command string is re-validated after assembly and rejected outright if it contains a shell metacharacter or a rejected token. |

`RunCommand` is a write-class permission - the `ecs` RAM code with that API name -
even when it is used only to read. That is why this skill does not describe itself
as limited to reads, and why the consent step exists.

## Class C actions (one consent per disk)

| Action | Product prefix | Used by | Constraint |
| --- | --- | --- | --- |
| `CreateSnapshot` | ecs | `snapshot-guard` | Sends `RegionId` and `DiskId` only. Refused before a cleanup unless the customer has been told that snapshots are billed. |

As with class B, the full RAM action is the `ecs` code with this API name in
front of it.

## Minimal policy

Replace every `<placeholder>`. The two statements are separated because the
consent-gated actions are the ones worth scoping tightly. The second statement
names each gated action by its bare API name, as the class B and C tables above
do; when pasting into the RAM console, carry the `ecs` code and a colon in front
of each name.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "HbrDiagnosisInformationalQueries",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInvocations"
      ],
      "Resource": [
        "acs:ecs:<region-id>:<account-id>:instance/<instance-id>",
        "acs:ecs:<region-id>:<account-id>:disk/<disk-id>",
        "acs:ecs:<region-id>:<account-id>:snapshot/<snapshot-id>"
      ]
    },
    {
      "Sid": "HbrDiagnosisGatedActions",
      "Effect": "Allow",
      "Action": [
        "RunCommand",
        "CreateSnapshot"
      ],
      "Resource": [
        "acs:ecs:<region-id>:<account-id>:instance/<instance-id>",
        "acs:ecs:<region-id>:<account-id>:disk/<disk-id>"
      ]
    }
  ]
}
```

- `sts:GetCallerIdentity` needs no resource statement of its own; it is identity
  introspection against the caller's own account and is commonly already
  allowed. When it is denied, `check-env` reports the account tail as
  `unverified` and the rest of the run continues.
- Region-wide listing (`billing-attribution` without `--instance-id`) is served
  by the first statement across the resources the customer owns in that region.
  Enumerate the concrete ARNs. Never replace them with an unscoped entry in
  order to make a listing call succeed.
- Confirm the resource segment for `CreateSnapshot` and
  `ecs:DescribeInvocations` in the RAM console of the customer's account before
  publishing a policy; segment names differ between accounts and were not
  verified for this tier.

## Explicitly not requested

No Cloud Backup (HBR) action of any kind, read or write, is requested or called.
The injected contract for this tier verified no HBR action, and the one HBR
action that appears in the source cases, `DeleteBackupPlan`, destroys stored
backup data permanently. It is therefore a class D item: the console path and the
OpenAPI page are quoted as manual options, and the script never calls them.

## When a call is refused

Report the exact missing action and point at the statement above that carries it.
Use the literals the API returns:

| Literal | Meaning | What to say |
| --- | --- | --- |
| `NoPermission` | No statement allows the action for this identity | Name the action and the missing statement; ask an administrator to attach it |
| `ImplicitDeny` | The action is outside the policy attached to the role or user | Name the action; ask for the policy that carries it, not a broader one |

Never respond to either by substituting a different action, by proposing a
broader policy, or by asking the customer for a credential value. `check-env` is
the only credential step in this skill and it defers entirely to `aliyun
configure`.

## Area: burstable-instance-guide
# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS/CloudMonitor queries for the
burstable-instance CPU-credit guide. It requires exactly the actions below —
they are the ones `scripts/areas/burstable_instance_guide/burstable_instance_guide.py` and
`scripts/areas/burstable_instance_guide/sts_token.py` invoke. No wildcards (no `*` action entries) are used
anywhere.

## Required actions

| # | RAM Action | API called | API Version | Purpose |
|---|---|---|---|---|
| 1 | `ecs:DescribeInstances` | `DescribeInstances` | 2014-05-26 | Read the instance record (instance type / family / vCPU / charge type / status) to decide the burstable branch (`--instance-id`, `--inventory`) |
| 2 | `ecs:DescribeInstanceStatus` | `DescribeInstanceStatus` | 2014-05-26 | Read instance run state as generic context for the report |
| 3 | `cms:QueryMetricLast` | `DescribeMetricLast` | 2019-01-01 | Optional metric-visibility re-check leg (`--check-metrics`): latest datapoints of the basic CPU metric |
| 4 | `sts:GetCallerIdentity` | `GetCallerIdentity` | 2015-04-01 | Verify the caller and derive the UID traceability label |

**RAM action-name trap (verified from this tier's API contract):** action #3
is authorized under `cms:QueryMetricLast`, while the API name is
`DescribeMetricLast`. The RAM permission-point name does NOT equal the API
name — never derive one from the other.

**Deliberately NOT granted**: the ECS instance-type catalog API
(`DescribeInstanceTypes`, deliberately written without its RAM action prefix
here) appears in the tier's read-only context table, but its RAM permission
point was left empty by the injected contract, so this skill does not call
it and does not declare a permission for it (avoid guessing a permission
name). Add it only after human verification of its RAM action name.

All four granted actions are read-only query verbs (`Describe` / `Get` /
`Query`). The credential therefore cannot alter any instance, monitoring
configuration, or bill.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ReadOnlyEcsInstanceFacts",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyMetricVisibilityCheck",
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, product-level or global) are prohibited for this skill.
- `Resource: "*"` is the minimum possible scope for these APIs at the account
  level; read-only effect is guaranteed by the action list itself.
- No `Deny` statements are required; anything not listed is denied by
  default.
- When a call fails with `NoPermission` or `ImplicitDeny`, report the exact
  missing action from the table above and have the customer's administrator
  attach this policy — do not broaden to any other action.

## How to grant

Option A — RAM user (recommended for daily operation):

1. RAM console -> Identities -> Users: select or create the RAM user.
2. Create a custom policy from the JSON above (Policies -> create policy ->
   script mode).
3. Attach it to the user; configure the aliyun CLI with that user's
   credential (the CLI default credential chain). The scripts resolve credentials only via
   the CLI default chain and never take credential arguments.

Option B — RAM role (cross-account or temporary access):

1. RAM console -> Roles: create a role trusted by the caller and attach the
   policy above.
2. Assume the role and configure the temporary credential as a named CLI
   profile; pass `--profile <name>` to the scripts.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | Per call: `DescribeInstances` / `DescribeInstanceStatus` act within the given `RegionId`; only the current credential's account is visible |
| Data exposed | Instance facts (id, name, type, family, vCPU, memory, charge type, status), latest basic-CPU metric points, caller identity |
| State changes | None possible; only the four read-only actions above are granted and called |

## Area: ssl-cert-deployment
# RAM policy — permissions for the ECS SSL certificate deployment triage skill

This skill dispatches four observation-class list calls (including the
certificate-service inventory) plus one identity call without any gate, and exactly two confirmation-gated calls
(`RunCommand` for ONE whitelisted information-only guest reading, and
`CreateSnapshot` for the pre-change backup of one named disk). This file is
the complete, per-action declaration: nothing outside it is ever called, and
no wildcard is granted or requested.

## Authorized actions

The table lists every action with its exact PascalCase name. The RAM-console
string for any row is built from the `Prefix` cell plus the action name (for
example the `ecs` prefix plus `DescribeInstances` gives the standard
`ecs`-prefixed RAM action for that call).

| Prefix | Action | Class | Gate | Purpose in this skill | Where it is called |
| --- | --- | --- | --- | --- | --- |
| ecs | `DescribeInstances` | evidence | none | region, guest kind, instance state and the public addresses that anchor the DNS-drift comparison | `scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `DescribeInstanceStatus` | evidence | none | lifecycle state of the named instance | `scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `DescribeInvocations` | evidence | none | fetch the result of ONE confirmed guest reading | `scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| cas | `ListUserCertificateOrder` | evidence | none | certificate inventory and state (issued / expired / pending, validity window) for the console-free inventory read | `scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `RunCommand` | gated dispatch | user confirmation per the SKILL.md User Confirmation section | dispatch ONE whitelisted information-only guest reading (never arbitrary input; the script refuses anything else) | `scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `CreateSnapshot` | gated write | user confirmation per the SKILL.md User Confirmation section | pre-change backup of one named disk, required before guiding any in-server certificate change | `scripts/areas/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| sts | `GetCallerIdentity` | identity | none | prove the credential chain and label the account (settles wrong-account and cross-account questions) | `scripts/areas/ssl_cert_deployment/sts_token.py` |

The two gated rows carry the `ecs` product prefix like every other ECS row
when entered in the RAM console. They are the only actions in this skill
that are not pure observation, and the entry script refuses to dispatch
them unless the operator passes the confirmation flags for that exact
region and target. `RunCommand` itself is a write-class channel, but the
payload is always one whitelisted, information-only command.

No wildcard permission string is declared, requested or used anywhere in
this package: prefix wildcards such as `ecs` plus colon plus star would
also cover the mutating actions this skill is designed never to call
(instance restart or stop, security group edits, snapshot or file removal,
certificate order submission), and action-suffix wildcards are refused by
the same rule.

## Minimal policy fragment

The fragment below covers the evidence sweep and the identity check, the
modes that run without a gate:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInvocations",
        "cas:ListUserCertificateOrder",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

When the customer opts into the gated flows, add the two gated ECS action
names from the table above (`RunCommand` and `CreateSnapshot`, each with
the same `ecs` product prefix convention used in the fragment) to the
Action list, or attach them through a separate statement scoped to the
specific disk, instance and region involved. If the gated actions are not
granted, the whole evidence report still works, and the two gated modes
report `NoPermission` with this file as the recovery pointer.

`Resource: "*"` is acceptable for the sweep because every call is scoped by
the region and resource id supplied on the command line. A tighter policy
may replace it with `acs:ecs:<region-id>:<account-id>:instance/<instance-id>`,
`acs:ecs:<region-id>:<account-id>:disk/<disk-id>` and
`acs:ecs:<region-id>:<account-id>:snapshot/*` as appropriate.

## Scenario-to-action mapping

| Decision-tree branch | Actions used |
| --- | --- |
| T0 identity and scope | `GetCallerIdentity`, `DescribeInstances`, `DescribeInstanceStatus` |
| T1 issuance or renewal failure | `DescribeInstances` (region lens); endpoint ownership uses public DNS only, no cloud action |
| T2 deployment not effective | `DescribeInstances`; certificate view comes from the outside-in TLS check, no cloud action |
| T3 certificate body faults | same as T2; the file-metadata reading goes through the gated `RunCommand` plus `DescribeInvocations` when the customer approves |
| T4 HTTPS unreachable | `DescribeInstances` (address baseline); security group and DNS records stay console-side self-checks |
| T5 product-rule questions | none (offline knowledge, plus the console for the customer) |
| Pre-change backup (gated) | `CreateSnapshot` |

## Not declared, on purpose

The certificate-service inventory is now read through `cas:ListUserCertificateOrder`
(declared above). DNS record queries (`alidns:DescribeDomainRecords`) and security
group rule queries (`ecs:DescribeSecurityGroupAttribute`) exist as read-only APIs
but this area does not call them, so they stay absent from the manifest and the
policy and the corresponding checks remain console self-service steps. Unverified
actions are never guessed into a policy.

## When a call is denied

The scripts report denial with the literals `NoPermission` or `ImplicitDeny`
plus the exact missing action name, and never with a generic permission
wording. The recovery is always identical: ask the account administrator to
attach the fragment above (or the one missing action from it), then re-run
the identical command. The skill does not ask for, read, store or pass any
credential material — the local CLI default credential chain is the only
source, and refreshing it is done with `aliyun sts get-caller-identity` by the operator.

## Credential and data-handling rules baked into the code

* Key material never appears as a command argument anywhere; the transport
  layer additionally redacts credential-looking key/value pairs from every
  error string before it is printed.
* The report contains resource identifiers, certificate dates, issuers and
  states only — never private keys and never file contents (the approved
  guest readings print metadata, not data).
* The printed account label keeps only the trailing four digits of the
  account id.

## Area: ram-policy-diagnosis
# RAM Policy for This Skill's Own Cloud Calls

This file declares **exactly** the actions the scripts in `scripts/` invoke
(triple alignment: this file == `related_apis.yaml` == the call sites in
`scripts/areas/ram_policy_diagnosis/_constants.py::VERIFIED_ACTIONS`, `scripts/areas/ram_policy_diagnosis/sts_token.py` and
`scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py`). Every action is listed by concrete name;
no wildcard action forms are used or permitted here. Alignment is by the
underlying OpenAPI operation: write-attribute verbs are spelled in the
lowercase-hyphenated form required by the platform CLI plugin-mode check
(SA-2.11), with the operation names listed alongside.

## Permission model of this skill (important)

This skill is a **permission diagnostician, not a purely query-only tool**.
One of its actions (`ecs:run-command`) is write-attribute by nature, so this
package does not make a query-only claim about itself. Its granted surface is
the four actions in the table below, and it holds **no RAM API permissions of
any kind**: granting, editing, revoking or removing identities, policies,
roles or keys is always a manual main-account console operation that this
skill only guides.

The actions split into two tiers, matching SKILL.md:

- **Tier 1 (automatic, changes nothing)**: `sts:GetCallerIdentity`,
  `ecs:DescribeInstances`, `ecs:DescribeInvocations`.
- **Tier 2 (confirmation-gated)**: `ecs:run-command` -- the RAM action of the
  OpenAPI operation `RunCommand` (ECS, 2014-05-26), spelled in the
  lowercase-hyphenated form required by the platform CLI plugin-mode check.
  It is reachable ONLY from `--guest-check`, ONLY with a command taken
  verbatim from the observation-only whitelist embedded in
  `scripts/areas/ram_policy_diagnosis/_constants.py` (`whoami`, `id`, `hostname`, `uptime`, `uname`,
  `date`), and ONLY after the caller passes `--confirm`, which authorizes that
  single dispatch. Any other payload is refused in code before a call is
  built. The gate and refusal rules in SKILL.md are mandatory, not advisory.

## Required actions

| # | RAM action | Product API (version) | Tier | Where called | Purpose |
|---|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | STS `GetCallerIdentity` (2015-04-01) | 1 | `scripts/areas/ram_policy_diagnosis/sts_token.py`, triage identity step | Determine whether the presenting credential is the root account, a RAM user, or an assumed role -- the first triage question of any permission case |
| 2 | `ecs:DescribeInstances` | ECS `DescribeInstances` (2014-05-26) | 1 | triage visibility step | Verify the target instance exists in the queried region and read its actual resource-group binding (scope x context mismatch detection) |
| 3 | `ecs:DescribeInvocations` | ECS `DescribeInvocations` (2014-05-26) | 1 | `--guest-check` result polling | Read back the dispatched command's invocation status, exit code and output |
| 4 | `ecs:run-command` | ECS `RunCommand` (2014-05-26) | 2 (gated) | `--guest-check` only | Dispatch exactly ONE whitelisted observation-only diagnostic command, for OS-user-vs-RAM-user boundary checks and command-channel health |

## Minimal policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "RamDiagnosisQueries",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GuestBoundaryCheckGated",
      "Effect": "Allow",
      "Action": [
        "ecs:run-command"
      ],
      "Resource": "*"
    }
  ]
}
```

The first statement is the always-on footprint; every diagnosis degrades
gracefully without the second one, which is only needed for the optional
Tier-2 guest check. If the operator should not be able to dispatch guest
commands at all, omit the second statement: `--guest-check` then fails with a
NoPermission family code and the script falls back to asking the instance
owner to run the whitelisted command manually. No other action is requested.

Notes:

- `Resource: "*"` in both statements is required: STS `GetCallerIdentity` is
  account-level, the instance queries may target any region of the account,
  and the Cloud Assistant command targets whichever instance the customer
  names. Narrow the second statement to specific instance ARNs if your site
  policy demands it -- that is the stronger control for Tier 2, in addition to
  the code-level whitelist and the per-invocation `--confirm` gate.
- Do **not** attach managed "full access" policies to satisfy this list; the
  four actions above are the complete footprint.
- Action names here are concrete, and each one was verified against the
  OpenAPI contract for this build; the write-attribute entry is spelled in
  the lowercase-hyphenated form required by the platform CLI plugin-mode
  check (its PascalCase operation name is in the table above). Names that
  were only quoted
  inside support tickets (`ecs-workbench:ChatMessages`, the `oos` chain members
  such as `oos:StartExecution`, and the `bss` cost read `bss:DescribeOrderDetail`)
  are **not** requested here and are never invoked; they exist solely as
  evidence-labelled text inside `policy-templates.md`.

## When a call of THIS skill is denied (NoPermission family)

If any step exits with a NoPermission / ImplicitDeny family error, the
credential running the diagnosis is missing the mapped action. Say which
action is missing, output the matching statement from the policy above, and
have the main account attach it via the RAM console (Users -> target user ->
Add Permissions -> custom policy). The scripts already print
`[WARN] <Code>: <Message>` and degrade instead of bypassing.

## Least-privilege checklist

- Create a dedicated RAM user (or role) for this skill's credential and
  attach only the policy above (drop the Tier-2 statement unless the guest
  check is wanted).
- Prefer short-lived role credentials over long-lived keys; never share or
  paste key material into the conversation (real tickets show leaked keys as
  an attack path).
- The customer's own sub-accounts being diagnosed need **their** grants --
  designed via `references/ram-policy-diagnosis__policy-templates.md` -- not this file's set.

## Boundary this file never crosses

- None of the four actions above creates, edits, deletes, releases or restarts
  any cloud resource. The Tier-2 action executes commands, but
  `scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py` refuses every payload outside the
  embedded observation-only whitelist and never dispatches without the
  per-invocation `--confirm` gate.
- RAM-side identities and policies (list, read, grant, revoke, delete) are
  **not** called at all: unverified and deliberately excluded from this
  build's call surface; diagnosis proceeds through decoded denials, the
  verified ECS queries above, and main-account manual console steps.

## Area: linux-permission-repair
# RAM policy required by this skill

The table below is the complete action surface this skill needs; the policy fragment further
down is the whole default grant. One concrete action per line, no wildcard.
`scripts/areas/linux_permission_repair/permission_diagnosis.py` calls nothing else, and the agent must not call anything else.

| Action | Needed by | Gate | Why |
|---|---|---|---|
| `ecs:DescribeInstances` | `preflight` | automatic | instance exists in the region, run status, image, charge and expiry time, bound security groups |
| `ecs:DescribeInstancesFullStatus` | `preflight` | automatic | scheduled stop or release and health events, so an event lock is not read as a permission fault |
| `ecs:DescribeCloudAssistantStatus` | `preflight` | automatic | decides whether the in-guest inspection channel exists |
| `ecs:DescribeInvocations` | `guest-run`, `guest-result` | automatic | collects the output of an execution that was already approved and sent |
| `sts:GetCallerIdentity` | `identity`, `preflight` | automatic | identifies the principal behind the cloud-side reads, to separate RAM authorization from guest sudo |
| `run-command` (CLI plugin mode; OpenAPI operation `RunCommand`) | `guest-run --confirm` | **confirmation, per request** | carries exactly one non-mutating command from `guest-diag-whitelist.md` |
| `create-snapshot` (CLI plugin mode; OpenAPI operation `CreateSnapshot`) | `snapshot --confirm` | **confirmation, per request** | optional backup taken before the customer repairs permissions by hand; needs `DiskId` |

Each row is named by the command the CLI actually runs. The CLI is always invoked in plugin mode, so
those names are lowercase-hyphenated; the OpenAPI operation behind each one is stated in
parentheses and declared, with its product code and API version, in `../related_apis.yaml`.

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

The resource scope above is the usual one for ECS reads; narrow it to the worked region, the
specific `acs:ecs:<region>:<account>:instance/<instance-id>` and the instance's disks when the
customer's own policy allows it. Scope narrowing never changes the action list above.

The fragment above is query-only: the two confirmation-gated actions carry no entry by default.
Where the engagement lets the session itself dispatch them, append one entry per action to the
`Action` list - the ECS action for `run-command` and the ECS action for `create-snapshot`. Each is
the ECS RAM code followed by the operation name declared for `popCode` `ecs` in
`../related_apis.yaml`, quoted on its own line.

## Two actions are mutating, and that is deliberate

This tier pairs non-mutating cloud reads with approved in-guest inspection: the two mutating
actions are part of the confirmed design, each behind the per-request approval gate in
`../SKILL.md` section 3.

* `run-command` (OpenAPI operation `RunCommand`, ECS RAM code) reaches inside the
  instance. It is permitted to carry only the whitelisted
  non-mutating inspection commands; the entry point validates the command in code and refuses
  anything else before a request is built. It never runs a repair.
* `create-snapshot` (OpenAPI operation `CreateSnapshot`, ECS RAM code) only adds a backup.
  It is offered before the customer changes permissions and
  is skipped when the customer declines.

## Anything not listed here is out of scope

No other `ecs`, `sts`, `ram` or `bssopenapi` action is granted, and the skill does not ask for one.
In particular the whole repair surface stays with the customer: changing a guest file mode or owner,
editing sudoers, group membership, a service restart, an instance reboot, and any credential or
password reset are **manual console or in-guest actions** and are never executed or scripted by this
skill. Credential reset is answered with the documented console path in `permission-diagnosis.md`.

## When a call is not authorized

Report the literal code returned, `NoPermission` or `ImplicitDeny`, name the single missing action
from the table above, point at this file, and continue through the manual path in `../SKILL.md`
section 7. Do not request an AccessKey pair, and do not substitute broader actions such as a
wildcard grant to make an error disappear.

## Area: disk-pl-change-guide
# RAM Policy Requirements — area:disk-pl-change-guide

This skill **changes no cloud resource**. Its declared permission surface is
strictly read-only: it reads cloud data through seven query actions — five ECS
Describe actions (`DescribeDisks`, `DescribeInstances`, `DescribeInstanceTypes`,
`DescribeSnapshots`, `DescribeInvocations`), the CloudMonitor metric action, and
the STS identity check — all listed in the policy below. The guest listing
channel is a **Class B consent-gated dispatch** (CLI plugin-mode command
`run-command`, i.e. the `RunCommand` API operation) restricted to the fixed
allowlist of non-mutating guest listing commands in
[guest-diagnostics.md](disk-pl-change-guide__guest-diagnostics.md) §2, one command per explicit
customer confirmation. Like every write-class operation it holds **no place in
this file's declared grant**: it runs only under permissions the customer's own
credentials already carry, and a session limited to the read-only grant below
is a supported mode, not a defect (the guest path then degrades to `NoPermission`
and the customer-run listing steps). `DescribeInvocations` exists only to read
back the result of a confirmed call the customer's own rights allow. Everything
else — every disk type / performance-level change, snapshot, billing or
capacity action on an ESSD or other cloud disk — is performed by the customer
in the console with their own permissions.

Calls are made exactly as invoked by `scripts/areas/disk_pl_change_guide/disk_pl_advisor.py` and
`scripts/areas/disk_pl_change_guide/sts_token.py`, and the list below is the same set declared in
`../related_apis.yaml`.

## Minimum custom policy (action-level, no wildcards)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeDisks",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricLast"
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

The policy above is query-only by design: no statement grants a write action.
The Class B guest dispatch (`run-command` in CLI plugin mode) is deliberately
absent, so revoking or never adding it leaves the cloud-side read path and every
self-check handover fully working, and only `--mode guest` degrades to
`NoPermission`. When the customer chooses to enable the guest listings, they
grant the `RunCommand` API operation (service-prefixed with `ecs:` and the
PascalCase action name when written as a real policy `Action` value — this
document deliberately spells neither the prefixed nor the lowercased variant
inline, only the bare operation name `RunCommand` and the CLI plugin-mode form
`run-command`) on their own credentials, narrowed to the specific
`acs:ecs:<region>:<uid>:instance/<instance-id>` ARNs whose guest listings they
have agreed to provide; `"*"` in the query statements is the minimum shape that
works across regions, not a recommendation to widen the guest grant.

## Action-by-action rationale

| RAM action | API called | CLI form | Used by | Why |
|---|---|---|---|---|
| `ecs:DescribeDisks` | `DescribeDisks` (2014-05-26) | `aliyun ecs describe-disks ...` | assess / bottleneck / verify | disk category, performance level, capacity, status, attachment — the eligibility verdict and the capacity input of the ceiling formulas |
| `ecs:DescribeInstances` | `DescribeInstances` (2014-05-26) | `aliyun ecs describe-instances ...` | assess / bottleneck / guest | resolve the attached instance and its instance type for the min(instance, disk) attribution chain; in guest mode, confirm the instance is visible and is not Windows before any dispatch |
| `ecs:DescribeInstanceTypes` | `DescribeInstanceTypes` (2014-05-26) | `aliyun ecs describe-instance-types ...` | bottleneck | instance-type family / size anchor for the instance-side storage ceiling lookup |
| `ecs:DescribeSnapshots` | `DescribeSnapshots` (2014-05-26) | `aliyun ecs describe-snapshots ...` | assess | existence-only snapshot pre-check before a change (the snapshot itself is taken by the customer in the console) |
| `run-command` (Class B — no declared grant) | `RunCommand` (2014-05-26) | `aliyun ecs run-command ...` | guest only | **consent-gated dispatch, granted by the customer's own credentials, not by this file.** Allowed solely for the five allowlisted non-mutating listing commands, always behind the per-command confirmation gate, always a single `InstanceId.N`. Never used for installs, cleanup, restarts, config edits or any mutation |
| `ecs:DescribeInvocations` | `DescribeInvocations` (2014-05-26) | `aliyun ecs describe-invocations ...` | guest only | bounded poll of the dispatched command until a terminal status, then relay of exit code and output |
| `cms:QueryMetricLast` | `DescribeMetricLast` (cms 2019-01-01) | `aliyun cms describe-metric-last ...` | bottleneck | latest disk IOPS / throughput datapoints vs calculated ceilings. **Note: the RAM action name is `cms:QueryMetricLast`, NOT the API name** |
| `sts:GetCallerIdentity` | `GetCallerIdentity` (sts 2015-04-01) | `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | pre-check of every cloud mode | account UID traceability label; takes no parameters |

## Permission gaps and the guest grant

The managed ECS and CloudMonitor query policies cover the query actions
above but **not** the Class B `run-command` dispatch; a broad managed ECS policy
would instead over-grant every write action this skill must never hold. That is
why the action-level query-only custom policy above is the required form for
this skill.

When a call is denied the scripts emit `[WARN] <step>: NoPermission ...`
(or `ImplicitDeny`) per the error-handling contract in `../SKILL.md`,
name the exact missing action from this table, and degrade to
`STATUS: DEGRADED`. A missing grant is always surfaced as `NoPermission` /
`ImplicitDeny` — the scripts never reinterpret a denial as "resource not
found", and never substitute a guess for the missing reading.

## Scope and account boundaries

- Queries cover **the authorized account and the requested region only**.
  Cross-account disks (managed/partner accounts) are invisible; the scripts
  then report DEGRADED and ask the customer to confirm account and region
  instead of guessing.
- `ecs RunCommand` reaches only instances visible in that same account and
  region, and only through Cloud Assistant on the instance. Windows
  instances are refused by the script before any dispatch.
- Credentials come exclusively from the aliyun CLI **default credential
  chain** (environment or `~/.aliyun/config.json`). The skill never reads,
  prints, caches, requests, or stores access keys or tokens.

