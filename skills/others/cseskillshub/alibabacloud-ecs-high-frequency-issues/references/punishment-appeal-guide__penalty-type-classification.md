# Punishment-Type Classification (7-Tier Model)

How to tell WHICH kind of action the customer actually faces. The tier is
the FIRST branching decision of this skill: it selects the evidence queries
that matter, the remediation list, the appeal materials, the channel wording
and the timeliness promise. Real tickets show the support engineer always
starts here ("is it the account, the instance, or just a URL?") before any
document collection.

## The seven tiers

| # | Tier | What happened | Typical customer wording | Verified queries that help | What NO query can show |
|---|------|---------------|--------------------------|----------------------------|------------------------|
| 1 | account | Risk-control action on the whole account (freeze / restricted use) triggered by outbound attack behavior or admission checks | "my account is frozen", "cannot log in, risk control", "restricted use" | instance facts to plan cost reduction; login/console failures corroborate | freeze cause, release timestamp, review progress |
| 2 | instance | The instance itself was force-stopped / locked / shut down by the platform security policy | "server was force stopped", "instance locked", "whole server shut down" | DescribeInstances Status + OperationLocks lock reasons; DescribeInstanceStatus | the punishment record itself |
| 3 | url | Only a URL / website is blocked for illegal or non-compliant content; the instance usually still runs | "website blocked", "illegal page taken down", "how do I appeal the content" | Running + no lock proves instance is untouched (a classic misunderstanding, see tier 7) | which exact URL, content detail (privacy-restricted) |
| 4 | port | Egress-port restriction: default outbound port-25 mail block, tunnel/VPN blocks | "port 25 closed", "cannot send mail", "VPN blocked" | security-group rules for comparison (a platform egress policy does NOT appear in them) | platform egress policy, supervisory blocks |
| 5 | transaction | Order / payment / renewal intercepted by transaction risk control | "cannot pay", "order blocked", "renewal gives UnknownError" | none on this surface (ECS facts stay normal) | the risk verdict and its release |
| 6 | judicial | Police / court / supervisory-authority requests or supervisory-level blocking | "police asked", "case filing", "supervisory authority blocked" | none (run NO query for this tier) | everything; the cloud provider is not the decision maker |
| 7 | unverified | "It is blocked" claimed without a notice, while cloud facts are normal | "my IP is blocked", "site unreachable from everywhere" | existence + status + lock reasons + security-group rules to rule configuration gaps in/out | cross-border reachability, domain expiry, third-party (registrar) blocks |

## Decision tree (mirrored by the entry script)

```
Input: notice wording (console message / SMS / email), asset identifiers,
       region, symptom keywords
 |
 +-- No notice at all, only "it is blocked"
 |    +-- run the four read-only checks:
 |         exists? Running? platform lock reasons? do SG rules explain it?
 |         +-- all normal -> tier 7 UNVERIFIED. Ask the fixed key question:
 |         |     "how exactly did you judge it blocked, and from where?"
 |         |     Never endorse the claim without a notice; hand off plain
 |         |     reachability faults (see handoff-map).
 |         +-- abnormal status / lock -> classify from the notice text below
 |
 +-- Notice present, classify its text:
      +-- police / court / supervisory .......................... tier 6
      +-- payment / order / renewal / UnknownError ............. tier 5
      +-- port 25 / SMTP / VPN / egress ........................ tier 4 (handoff)
      +-- account frozen / login restricted / risk control ..... tier 1
      +-- instance locked / force stopped / shut down .......... tier 2
      +-- URL / website / content violation block .............. tier 3
      +-- ambiguous or multi-match -> prefer the tier the cloud
          facts corroborate (locks -> 2; Running -> 3), then confirm
          with the customer.
```

## Evidence-to-conclusion rules (no fabrication)

1. A `Running` status with an unchanged instance is PROOF the server body
   was not closed: a "server shut down" claim under those facts is a URL
   block or a third-party restriction (real tickets: URL blocked while SSH
   still worked; domain expiry mistaken for a ban).
2. Platform lock reasons present in DescribeInstances output corroborate
   tier 2/1; their absence does NOT disprove an account-level or
   supervisory action — those live outside this read surface entirely.
3. Security-group rules that fail to explain the outage are a required
   pre-check before accepting "the platform blocked me": if a plain rule
   gap explains it, this is the access-block area, not a punishment.
4. If the queried region/account shows no such resource, the FIRST
   conclusion is ownership/region mismatch, not "not blocked" — real
   tickets show cross-account confusion; punishment records are
   account-scoped.
5. The citable console error in this tier's evidence is `ErrorCode:
   UnknownError` plus a RequestId (transaction risk-control interception);
   do not invent other codes — no punishment-specific error code was
   verified for this area.

## The four verified read-only queries

| Action | Product / version | Key inputs | What it answers here |
|--------|-------------------|-----------|----------------------|
| DescribeInstances | ecs / 2014-05-26 | RegionId, optional InstanceIds / PublicIpAddresses | exists? Status? lock reasons (OperationLocks)? public IPs? attached SGs? charge type? |
| DescribeInstanceStatus | ecs / 2014-05-26 | RegionId, optional InstanceId.n | fast status cross-check for many instances |
| DescribeSecurityGroups | ecs / 2014-05-26 | RegionId | inventory to bind instance SGs and spot the relevant group |
| DescribeSecurityGroupAttribute | ecs / 2014-05-26 | RegionId, SecurityGroupId | ingress/egress rule comparison: platform action vs configuration gap |

Plus `sts:GetCallerIdentity` (account label of the evidence). Nothing else
is authorized for this skill.

## Boundary honesty (stated in every report)

Punishment records, violating-content detail (privacy-restricted: the
platform does not disclose content specifics to the customer), appeal/review
progress, account-side risk verdicts and supervisory blocks are NOT visible
through any query available to this skill. They are carried only by the
notice the customer received, and they resolve through the appeal / manual
channels described in [appeal-materials-and-channels.md](punishment-appeal-guide__appeal-materials-and-channels.md).
