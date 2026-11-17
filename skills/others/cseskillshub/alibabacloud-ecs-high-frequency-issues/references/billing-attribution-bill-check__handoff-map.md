# M6 — Boundary Map: What This Skill Hands Off (and with what evidence)

This skill owns ONE vertical: attributing money to product x billing item x
region x resource x usage x price x payable/deducted, and reconciling bill
amounts. Anything beyond that is identified, evidenced and routed. The
attribution result is the input to every handoff below — do the attribution
FIRST, it usually shortens the ticket immediately.

## Handoff table

| Customer symptom | Boundary fact | Route to |
|---|---|---|
| "Which addresses did my traffic go to / who accessed my server / was I attacked" | Historical per-connection traffic is NOT retained or provided cloud-side (data privacy); only aggregate metering and monitoring curves exist | Guest-side business logs, Network Intelligence Service flow analysis (retro but paid, activation is a deliberate paid action), or an on-machine tool such as iftop (free, live-only, not retroactive); a network-traffic troubleshoot skill / manual analysis — never this skill |
| "Cancel / waive this fee, give me a coupon, this is unfair" | Accrued fees cannot be cancelled by any diagnostic; compensation and waivers are commercial judgments | Duty manager / business manager via ticket; this skill outputs the amount evidence only |
| "Switch my billing mode / renew / upgrade / buy or unsubscribe a package / release this resource" | All cloud changes are outside a read-only skill | Manual console paths (see `stop-billing-guide.md`); pricing and discounts via business manager |
| "Who performed this operation, from which account, API or console?" | Operation provenance belongs to the audit trail, and some field-level origins need backend lookup | ActionTrail console (entry in `bill-console-paths.md`); if the event name/owner is not exposed there, ticket for backend verification |
| "Explain OSS / Security Center / CDN / CDT / Cloud Backup's own billing rules" | This skill attributes the fee to that product and item, then stops | That product's billing channel |
| "Create / delete snapshots, bind auto-snapshot policies" | Snapshot fee attribution stays here; snapshot operations belong elsewhere | `alibabacloud-ebs-disk-snapshot-management` |
| "The exported bill disagrees with the backend console by a big gap" (after the four-layer reconcile) | Bill-system data consistency is a product-side question | Backend review ticket with the evidence pack; state the provisional/timing caliber (`billing-timing-and-caliber.md`) first — it dissolves most apparent gaps |

## Evidence pack contents (what a handoff ticket must carry)

The scripts emit `evidence_pack` in JSON mode; when handing off, include:

- account UID (from the identity pre-check), billing cycle, query mode;
- the exact bill rows: product, billing item, region, resource ID, usage,
  unit, list price, payable / package-deducted / coupon-deducted amounts
  (full decimals preserved);
- monitor-side numbers when a cross-check ran (window, period, totals);
- every degraded/failed call with its error code (NoPermission /
  ImplicitDeny / InvalidParameter / Throttling.User / ...).

## Fixed customer-facing wordings (from real resolutions)

- Traffic forensics: "For data-privacy reasons, historical traffic cannot
  be traced back to specific destinations or sources; we can attribute the
  fee to instance, day and billing item — which is what this report
  does."
- Waiver demand: "Accrued fees cannot be cancelled through support
  diagnostics; I am passing the amount evidence to a colleague for a
  commercial review."
- "Detail page is empty": not a data fault by default — walk the month /
  statistic-dimension switch first (see `bill-console-paths.md`).
- Package "correctly associated but still not deducted": rules exhausted →
  escalate with the evidence pack; never concede or deny a system fault.
