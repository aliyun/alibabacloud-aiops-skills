# M5 — Stopping Billing: Manual Steps and Risk Statements

**This skill is read-only.** It never stops, converts, unsubscribes,
deletes or removes anything. It quantifies what is still in fee, then
hands the customer the exact manual path with the risk statement that
support staff use verbatim in tickets.

## The one rule that ends most tickets

Stopping is not stopping-billing. A pay-as-you-go instance keeps billing
while stopped (normal stop keeps even the spec fee); **only resource
removal ends the charge chain**, and removal is irreversible.

Economical (savings) stop suspends ONLY:
- instance specification fee,
- fixed public bandwidth fee,
- image license fee.

It does NOT suspend: system/data disks, snapshots, EIP holding, pay-per-
traffic usage accrued around the stop, and the previous cycle's settlement
that hits the balance at the start of the next month.

## Per-item guidance (manual, customer-side)

| Still in fee | Manual path | Risk statement to attach |
|---|---|---|
| Pay-as-you-go instance no longer needed | ECS console -> Instances -> select region/resource group -> instance state -> release (after backing up) | Release is irreversible; local disks, disks flagged "release with instance", and auto snapshots released together with those disks all disappear with it |
| Unattached cloud disk | Confirm unused -> copy/snapshot the data -> disk delete in console | Deleted disk data is unrecoverable |
| Snapshots keeping accruing capacity | Snapshot list per region -> remove unneeded snapshots; unbind disks from the auto-snapshot policy (operations owned by the snapshot-management skill) | Deleted snapshots cannot be recovered; incremental chains change billed size only gradually |
| Public traffic on a monthly instance | Change the instance's bandwidth billing mode to fixed bandwidth, or buy a shared traffic plan / upgrade to CDT | Changing the billing mode creates a fee-change order itself; configuration-change orders may not carry a discount — quotes are commercial handling |
| Another product discovered during attribution (e.g. Security Center pay-as-you-go) | Turn the product's own pay-as-you-go switches off in its console | A resource package for that product, once exhausted or expired, does NOT stop the pay-as-you-go feature from billing |
| Arrears blocking services | Top up at the billing center | Long-term overdue accounts eventually lose pay-as-you-go resources |

## What never belongs in this file's output

- Any promise to cancel / waive / refund an already-issued charge:
  "accrued fees cannot be cancelled" is the fixed customer-facing
  statement; waivers, coupons and compensation are duty/business-manager
  decisions (handoff).
- Any executed cloud change: the skill states paths, the customer acts.
- Discount or price quotes: commercial negotiation is out of scope.
