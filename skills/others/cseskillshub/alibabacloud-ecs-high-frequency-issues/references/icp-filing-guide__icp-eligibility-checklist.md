# ICP Filing Server Eligibility Checklist (C1)

Who should read this: the agent, when the customer asks why an ICP filing
service code cannot be bound ("the binding page shows no selectable
instance"), or which server can carry a new filing.

Source of every rule below: real support-ticket conversations recorded in the
Evidence section, plus the official filing-server list for condition 2. Nothing
here is model memory; the script
`scripts/areas/icp_filing_guide/icp_filing_check.py eligibility` reproduces the checks read-only from
`ecs:DescribeInstances` data.

## The three conditions for a filing-eligible server

An ICP filing service code must be bound to an Alibaba Cloud server instance
that satisfies ALL of the following, in the SAME account as the code:

1. **Mainland China node.** The instance's `RegionId` must be one of the
   mainland China regions (the scan list is embedded in
   `scripts/areas/icp_filing_guide/_constants.py`; `cn-hongkong` is not a mainland node for filing
   purposes). Evidence read from the API: `RegionId` of each instance.
2. **Subscription billing whose PURCHASED length is longer than 3 months,
   cumulative renewals included.** Official wording (server-access eligibility check,
   <https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-server-access-information-check>):
   "The billing method must be subscription, and the purchased length must exceed
   3 months, cumulative renewals included; the result is unrelated to how long the
   server has been used and to the term remaining."
   - subscription billing, and the purchased length (original purchase plus
     every renewal) longer than 3 months; the rule is explicitly **unrelated to
     how long the server has been used and unrelated to the term remaining**.
   The instance must be `InstanceChargeType = PrePaid`. Per-condition states are
   `pass` / `fail` / `unknown`:
   - `PostPaid` (pay-as-you-go) -> `fail`, outright; the official rule says to
     convert it to subscription first;
   - a free-trial ECS server -> never qualifies (official exclusion); the API
     does not flag trials, so relay the rule when a short purchase is seen;
   - `PrePaid` with a known cumulative purchased length longer than 3 months
     -> `pass`, no matter how much term is left (12 months bought with 2 months
     left is still compliant);
   - `PrePaid` where the cumulative purchased length cannot be read -> `unknown`,
     never `fail`. The instance query returns billing method, `CreationTime` and
     `ExpiredTime` only and no renewal history, so:
     - `--purchased-months N` (figure read in the billing center) is
       used when supplied, and decides the condition on its own;
     - otherwise the `CreationTime` -> `ExpiredTime` span is used as a labelled
       approximation of the purchased length. It covers the original purchase
       plus renewals, but an expired-then-renewed gap can inflate it, so a
       borderline case is confirmed in the billing center;
     - the **remaining term is never used as a failure criterion**: a server
       that is about to expire is not disqualified by this rule;
   - `PrePaid` but `ExpiredTime` missing/unparseable or reporting the
     no-fixed-term sentinel year (2099), or `CreationTime` missing -> `unknown`.
   `InstanceChargeType` absent is also `unknown`. An `unknown` never becomes a
   silent pass: it forces the instance verdict to `needs_confirmation` and is
   printed with an explicit "read the cumulative purchased length in the billing
   center" caveat.
3. **Public bandwidth allocated.** Tested in this order, first hit wins:
   - `InternetMaxBandwidthOut > 0` -> `pass`;
   - else an associated elastic IP (`EipAddress.IpAddress`) -> `pass`;
   - else a fixed public address (`PublicIpAddress.IpAddress[]`) -> `pass`,
     printed with a caveat to confirm the bandwidth value on the instance page
     (the bandwidth attribute itself reads 0 in this combination);
   - none of the three -> `fail`: the internet cannot reach it.

## Verdicts produced by the script

Per instance (report field `verdict` inside each instance row):

| Verdict | Meaning |
|---|---|
| `eligible` | All three conditions confirmed from API data; the free filing service code generated for such an instance can be bound here |
| `not_eligible` | At least one condition failed; the report lists the exact missing conditions per instance |
| `needs_confirmation` | No condition failed, but at least one could not be read from the API (typically the subscription term); the customer must confirm it in the console |

Account-wide (the report's top-level `verdict`):

| Verdict | Meaning |
|---|---|
| `ELIGIBLE_INSTANCE_FOUND` | At least one instance is `eligible`; the report lists them with region and public addresses |
| `NO_ELIGIBLE_INSTANCE` | Instances were seen, but none satisfies all three conditions; the per-instance detail names what is missing |
| `NONE_FOUND` | No instance was visible in the scanned regions at all. This is a finding, not an error - unless the report also lists regions that failed to answer, in which case it is a permission/configuration gap and must not be read as an empty account |

## Service-code rules (from ticket conversations)

- Buying a qualifying subscription ECS instance **auto-generates a free
  filing service code** for the account; a separately purchased paid code is
  usually unnecessary. [T-C097A6CB, transcript-verified]
- "No selectable instance" on the binding page means **no instance in the
  account meets all three conditions** - this is what the support engineer's
  manual "we checked your account" step found, and exactly what the
  eligibility scan reproduces. [T-C097A6CB, transcript-verified]
- Whether an **unused paid** service code is refundable is a commercial
  question: route to the commercial specialist; refund details are subject to
  specialist confirmation. [T-C097A6CB / T-2E81A6EC wording; no official
  refund document was retrieved for codes specifically]
- A service code **already consumed** by a filing cannot be reused; cancelling
  a filing and re-filing requires a new code. [T-2E81A6EC,
  transcript-verified]
- The paid **filing butler** service exists for customers who want handled
  filing; show the entry point, never place an order. [T-C097A6CB]

## What the cloud APIs cannot show (ask the customer)

- The filing service code inventory itself (how many codes exist, free vs
  paid, used vs unused): no filing-data API is in this skill's whitelist.
  Ask for an ICP Filing console screenshot.
- The domain's real-name registration data: filing information must match the
  domain real-name information; the customer confirms this in the domain
  console.
- Whether a specific website content requires an enterprise subject (e.g.
  content involving payment transactions): summary-level ticket wording only
  - defer to the filing specialist. [T-1F986C3F, summary-only]

## Agent behaviour rules

1. Run `python3 scripts/areas/icp_filing_guide/icp_filing_check.py eligibility` (add `--regions`
   only when the customer names a region outside the default scan list; the
   auto-filled scan list must be declared in the final report).
2. Relay the verdicts and the per-instance missing conditions verbatim from
   the script output; never re-judge eligibility yourself.
3. When the account has NO eligible instance, say so plainly and route
   purchase questions to the commercial entry point
   (`references/icp-filing-guide__escalation-map.md`); this skill never places orders or quotes
   prices.
4. When an eligible instance exists but binding still fails, route to the
   filing specialist - the remaining causes live in filing-side data this
   skill cannot read.

## Evidence

| Ticket | Status | What it grounds |
|---|---|---|
| T-C097A6CB | transcript-verified | the three conditions, free-code auto-generation, "no selectable instance" root cause, butler service, paid-code refund routing |
| T-5A6AABCB | summary-only | the same server preconditions restated for access-filing migration |
| T-2E81A6EC | transcript-verified | consumed codes cannot be reused; cancel-and-refile consequences |
| T-1F986C3F | summary-only | individual vs enterprise subject questions defer to the specialist |

Official links cited by the engineers in those tickets are collected in
`references/icp-filing-guide__help-links.md` with their verification status.
