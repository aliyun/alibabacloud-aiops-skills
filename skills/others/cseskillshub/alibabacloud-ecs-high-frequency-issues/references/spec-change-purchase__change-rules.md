# Change rules and risk notices

This skill performs NO cloud change. It assesses feasibility with query
calls and then guides the CUSTOMER through the console themselves. This file
is the single source for the mandatory wording that must accompany the
conclusions (the "inform-first" gate in `SKILL.md`).

## MANDATORY: the five change notices

Relay all five with every spec-change conclusion (source pattern: reviewed
tickets `T-B4443584`, `T-91459169`; a human agent delivered the identical
five-point block in both):

1. Lowering a configuration requires STOPPING the instance first; the
   business is interrupted, so run it in an off-peak window.
2. Before acting, read the Prerequisites, Limits and Billing sections of the
   official change-configuration documentation in the help center (see
   `references/spec-change-purchase__help-docs.md` for the clue list).
3. A downgrade may produce a refund equal to the price difference between
   the residual value of the old configuration and the new configuration's
   price; when the original purchase had a discount, the mid-term downgrade
   refund CAN BE 0.
4. If the instance participates in a long-term low-price promotion (for
   example the 99 plan), changing the configuration may make later renewals
   lose the promotional price.
5. Instance type changes are bound by instance-family compatibility rules
   and limits (which families support changes is an official documentation
   matter, see `references/spec-change-purchase__help-docs.md` for the clue list).

## Effectiveness statements (the three fixed sentences)

- A vCPU/memory (instance type) change takes effect only after the instance
  is RESTARTED; a paid order alone does not change the running
  configuration (`T-674C0E1A`, `T-AC1CDE4F`, `T-7EF1DFC9`).
- Internet bandwidth changes take effect IMMEDIATELY and need no restart.
- Temporary-bandwidth and EIP-related orders follow the effective time
  printed on the ORDER; verify per order instead of assuming
  (`T-B093525E`: the page showed a next-day effective time).

Restart risk that must accompany the first sentence: everything not yet
persisted from memory is lost on restart - warn application owners and stop
active writes first, and create the recommended snapshot beforehand.

## Snapshot advice (text only - this skill never creates snapshots)

Before any stop / restart / spec change, strongly recommend a disk snapshot
in the ECS console so data can be rolled back, and mention that snapshot
storage is itself billable (the reviewed agents always paired the two
documents; clue IDs in `references/spec-change-purchase__help-docs.md`). The skill's scripts never
call a snapshot interface of any kind - no snapshot action is in this tier's
contract; they only output the advice.

## Downgrade pre-flight (from `T-F3FCB834`)

Before agreeing a memory/CPU downgrade is sensible, a human agent looked at
the last seven days of utilization (~10% memory) and still advised keeping
headroom for peaks and growth. This skill cannot read OS-level utilization
(a cloud-monitoring utilization pre-check is a pending batch decision; it
would use a CMS metric query whose API and RAM names differ, and it is NOT
in this tier's contract). Until then the skill MUST NOT promise an automatic
utilization pre-check: it shows the five-question assessment and asks the
customer to self-check CPU/memory watermarks on the CloudMonitor console
page before deciding.

## Bandwidth and temporary upgrade (from `T-91459169`)

- First split the change object: instance spec (vCPU/memory) vs public
  bandwidth - feasibility, notices and effectiveness all differ.
- Feasibility depends on two instance attributes to read first: the billing
  type (PrePaid subscription vs PostPaid pay-as-you-go) and the public IP
  type (fixed public IP vs EIP). The scripts read both automatically.
- Temporary bandwidth upgrade supports RAISING the fixed public bandwidth
  for a window only; a temporary LOWER is not supported. The maximum
  selectable fixed-bandwidth value is capped - quote the limit shown on the
  console page / official temporary-upgrade doc rather than a hardcoded
  number (the support-observed cap value is pending documentation
  verification, requirements section 8-5).
- Bandwidth changes take effect immediately; no restart needed.

## Price and refund wording (estimate only)

- Cloud query prices are ESTIMATES: account-level discounts and promotion
  rules are not fully visible to the query APIs, and in the reviewed case
  even the human could not compute the exact refund (`T-402BBB88`).
- Never state an exact refund amount. Teach the safe self-check instead:
  step through the console change/conversion dialog and READ the displayed
  price / expected refund WITHOUT clicking confirm (`T-402BBB88`).
- Always append the estimate disclaimer (also embedded in
  `scripts/areas/spec_change_purchase/_constants.py` as `PRICE_DISCLAIMER`).

## Irreversible / money-losing actions: guidance only, inform-first gate

The following customer-side actions are irreversible or cost-bearing; the
skill only explains them, and MUST relay the listed notices BEFORE the
guidance steps. Full texts are in `scripts/areas/spec_change_purchase/_constants.py`
(`IRREVERSIBLE_NOTICES`):

- Stop-required downgrade: business interruption + refund may be 0 on
  discounted purchases (`T-B4443584`, `T-91459169`).
- Restart to make a spec change effective: unsaved in-memory data is lost
  (`T-674C0E1A`, `T-AC1CDE4F`, `T-7EF1DFC9`).
- Cross-availability-zone migration: the PRIVATE IP changes (`T-54655754`).
- Fixed-bandwidth to pay-by-traffic conversion plus fixed-public-IP to EIP
  conversion (`T-402BBB88`): the conversion cannot be reversed (an EIP can
  never become a fixed public IP again); the EIP adds a separate
  configuration fee (region-dependent; the support-quoted per-day number is
  pending documentation verification - quote the buy-page price instead);
  the remaining fixed-bandwidth fee is refunded at a discounted difference
  that can be 0 on discounted instances; re-converting to fixed-bandwidth
  billing later may require paying again.
- The five-step IP-refresh route (text guidance only, console-performed):
  change public bandwidth billing to pay-by-traffic, convert the fixed
  public IP to an EIP, unbind the EIP, apply for a new EIP, bind it to the
  instance. While the old EIP is not released, a newly applied EIP will not
  equal the old address (`T-402BBB88`).

## New purchase / clone as a downgrade workaround

When the target is outside the change set and the customer considers buying
a new instance or cloning instead (`T-D0BF947D`): MUST warn up front that
the IP changes - a new instance or clone gets different IP addresses, and
business dependencies bound to the old fixed public IP will break; a fixed
public IP cannot be actively refreshed except through the irreversible EIP
route above. Also note the reviewed case where the customer's IP-retention
question was never answered - this skill must always answer it with this
warning.

## Quota line boundary

Quota application is self-service ONLY (the customer submits it in the
console; `T-6D9AB6B5`), and approval is a human process. See
`references/spec-change-purchase__quota-triage.md`.
