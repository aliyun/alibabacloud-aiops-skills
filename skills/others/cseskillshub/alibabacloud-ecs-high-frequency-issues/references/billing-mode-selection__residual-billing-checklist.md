# Residual Billing Checklist (After a Conversion or a Release)

The dominant late-stage root cause in this tier: the customer changed or
removed the INSTANCE, but related billing items kept running
pay-as-you-go. Work through every row after any conversion or release; each
row states why it lingers and where the customer checks it themselves --
bill line items are not reachable through this skill's read-only ECS
surface.

## 1. Attached data disks (highest-frequency miss)

- Why: the instance billing conversion does NOT convert attached data
  disks; they keep hourly billing and keep appearing on bills.
  [ticket-summary T-49041DCA]
- Customer check: ECS console -> Storage & Snapshots -> Disks; inspect each
  disk's billing field; convert disk billing via its own console entry, or
  release disks no longer attached (irreversible -- confirm contents first).
- Re-verify with the advisory the next billing cycle, or against the
  customer's pasted bill-detail screenshot.

## 2. Snapshots

- Why: snapshots are billed independently of instance lifecycle and survive
  the instance. [ticket-summary T-1F45414E]
- Customer check: ECS console -> Snapshots list per region; delete
  unneeded ones (customer action, irreversible). Cross-product snapshot
  charges on bills show under their own product line.

## 3. Public bandwidth / outbound traffic

- Why: a subscription instance that never bought fixed bandwidth is billed
  by outbound traffic pay-as-you-go -- the "where does this 54 CNY come
  from" case. [ticket-summary T-DF87DFC7]
- Customer check: instance detail -> public bandwidth configuration;
  compare fixed-bandwidth vs pay-by-traffic in the console. Bandwidth
  billing REWORK itself is a neighbor symptom: see `handoff-scripts.md`
  (modify-fixed-bandwidth document pointer) - this file only explains why
  the charge exists.

## 4. Independent products (e.g. security add-ons)

- Why: products purchased next to ECS keep their own billing; stopping the
  server stops none of them. [ticket-summary T-1F45414E: instance already
  stopped yet data-disk + snapshot + security-center lines were all still
  charging]
- Customer check: Billing Center bill detail grouped by product; turn each
  product off from its OWN console. Multi-product items belong to their
  product tiers.

## 5. Billing lag after a release (not a charge at all)

- Why: bill issuance trails usage. Charges surfacing days after a release
  were accrued BEFORE it; a live ticket was resolved by comparing charge
  timestamps with the release time from backend bill data. [ticket-summary
  T-82BD6370]
- Customer check: Billing Center monthly bill detail -> item timestamps vs
  the console operation record; if a NEW charge appears strictly after the
  release with no residual item to explain it, hand off to the finance tier.

## 6. Arrears blocking the cleanup itself

- Why: while an account owes money, disks may refuse detach/release and
  conversion entries stay hidden; the customer must settle the balance
  first (customer top-up action). [ticket-summary T-1F45414E / T-AABC1FF1]
- Signal from the read-only query: `OperationLocks` carrying the `financial`
  lock reason.

## How this checklist closes

After the customer works through the rows, the advisory is re-run
(read-only) to confirm instance-side state, and the customer compares the
NEXT billing cycle for the residual lines. Money-side final authority is
always the Billing Center detail, not this skill.
