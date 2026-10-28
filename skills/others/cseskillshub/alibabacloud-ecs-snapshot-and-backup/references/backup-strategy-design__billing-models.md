# Billing Models for ECS Backup Design (Never a Committed Amount)

Knowledge module for capability "billing model and cost example". The
evidence-batch document set is described in
[references/backup-mechanisms-and-limits.md](backup-mechanisms-and-limits.md);
re-verify each URL's current text before quoting figures. **This skill quotes
billing MODELS and parameterized examples only.**

## 1. The official no-commitment stance

Snapshot charges depend on the real changed-data volume and how retention
actually executes, so a fixed monthly amount CANNOT be promised in advance
(the support line itself refuses a fixed quote on this; ticket evidence:
"weekly increment 100M does not mean snapshot capacity grows only 100M").
The deliverable is always: model + formula + worked example from CUSTOMER
inputs + the uncertainty statement.

## 2. Snapshot storage billing model

- Meter: snapshot storage usage (GB) held per region over time,
  pay-as-you-go; standard and archived snapshots have different rates.
  Rates live in the snapshot billing docs
  ([path A](https://help.aliyun.com/zh/ecs/snapshots-1),
  [path B](https://help.aliyun.com/zh/ecs/product-overview/snapshots-1) —
  which path is canonical is an open item; check both).
- Usage semantics (see also [misconceptions.md](misconceptions.md)):
  - first snapshot of a disk = full copy of used blocks;
  - later snapshots = incremental at BLOCK level (changed blocks only);
  - deleted files keep their blocks occupied until every referencing
    snapshot is gone;
  - the console's per-snapshot size is the RESTORE full amount, not the
    billed increment;
  - a rebuild/init-disk cycle can reset the growth baseline (destructive
    operation; customer decision, out of scope for this skill beyond naming
    the mechanism).
- Rule of thumb for sizing (lower bound, block effects push it up):

  ```text
  steady usage (GB) ~= used-data base + daily change (GB) x retention days
  ```

## 3. Cross-region copy billing model

- Per copy operation: one cross-region copy TRAFFIC fee + standard snapshot
  STORAGE fee in the destination region.
- Copies follow snapshots one-to-one: "create N snapshots, get N copies" —
  an automatic policy taking snapshots twice a day and copying each one
  produces two copy billings per day per disk. Design levers:
  snapshot more often locally, copy less often; or copy only selected
  snapshots.
- Archived snapshots cannot be copied across regions.
- The dedicated "copy snapshot" feature page was NOT located in the evidence
  batch; describe the mechanism from the billing docs and avoid quoting
  unverified feature URLs.

## 4. File backup and database backup

- ECS file backup basic edition: free, with the limits in
  [backup-mechanisms-and-limits.md](backup-mechanisms-and-limits.md) (fixed
  30-day retention, DB directories excluded, fail-on-full).
- Cloud Backup (file/database backup): paid under the Cloud Backup billing
  model — [billing methods and billable items](https://help.aliyun.com/zh/cloud-backup/product-overview/billing-methods-and-billable-items).
  Database backup fees are NOT snapshot fees; keep them in separate model
  lines in any estimate.

## 5. Resource packages / cost-optimization hand-off boundary

- Per the official OSS resource-plan overview, a Standard-LRS storage
  package can deduct ECS snapshot storage fees (same statement verified in
  the sibling OSS billing skill on 2026-09-02; re-verify before quoting).
- Savings plans: [purchase savings plan](https://help.aliyun.com/zh/ecs/purchase-savings-plan)
  is an instance-cost lever, not a snapshot lever.
- Package purchase, refunds, and commercial negotiation are ACCOUNT/COMMERCIAL
  processes: state the boundary, point to the console or human support
  (see [routing.md](routing.md)); never promise a package size or a price.

## 6. Standard report wording for any cost question

Every cost answer MUST contain, verbatim in spirit:

1. the applicable billing MODEL (which fees, metered on what);
2. a PARAMETERIZED example computed from customer-provided volumes
   (mark them "customer-provided");
3. the sentence: "Backup charges depend on the real changed-data volume and
   retention execution; a fixed amount cannot be committed in advance.";
4. the doc references with the verification-date note.
