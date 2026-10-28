# Error signals and what each one means

Only messages that were actually observed in the ticket record are quoted here.
Where the source was a console banner rather than an API code, that is stated. Do
not reconstruct a code from memory; if the customer's text is not in this file, ask
them to paste it verbatim.

## Permission and identity failures

Use these literals in reports: `NoPermission`, `ImplicitDeny`.

| Signal | Meaning | Action |
|---|---|---|
| `NoPermission` on a Describe action | the RAM identity lacks that one action | show the single missing action and the statement from `references/ram-policies.md` that grants it; do not broaden the policy |
| `ImplicitDeny` | an explicit deny or a missing grant higher up | same, plus check for a control policy |
| denied on image export with a sub-account | export needs its own image and OSS permissions, owned by the customer | route to the customer's administrator; not a snapshot problem (evidence: ticket 0005PR939W) |

## Quoted codes from this tier

| Signal | Where it comes from | Disposition |
|---|---|---|
| `InvalidUser.NotInWhiteList` - "The user is not in the white list of exporting snapshot." | `ExportSnapshot` | hard product limit; the whitelist is **not** opened on request. Say so plainly, then move to the image export path. Do not imply a form exists (evidence: ticket 000CARSFMA) |
| `0x80042304` / `VSS_E_UNEXPECTED_PROVIDER_ERROR` | guest VSS during an application-consistent snapshot | provider missing or broken; re-registration plus reboot, both human steps (evidence: ticket 000BSRFJZW) |
| `exitcode 12` from a Cloud Assistant invocation | the script stage of an application-consistent snapshot | read the invocation output via `invocation-history`; usually role or provider setup (evidence: ticket 000BSRFJZW) |
| risk-control block on enabling the snapshot service, seen after a real-name subject change | console order page | account-level appeal, not a snapshot diagnosis; hand to the account verification flow (evidence: ticket 00073S02FZ) |

## Console banners that are not API codes

Quote them as the customer sees them.

| Banner text | Real cause | Next step |
|---|---|---|
| "Order failed, your account has an anomaly" | account state, typically risk control or verification | account appeal; snapshot work resumes afterwards |
| "Overdue, cannot be used" on the policy page | arrears suspended the snapshot service | Billing and Cost Center top-up; existing snapshots keep billing while suspended |
| "Order not paid" while a resize looks ineffective | the expansion order was never paid | expansion axis, and its prerequisite snapshot is handled here first (evidence: ticket 000ACRF8K2) |
| snapshot list empty for a region | wrong region selected, or the disk is elsewhere | re-run with every region holding disks; see `references/policy-effectiveness.md` |

## Symptoms that look like errors but are not

| Customer wording | What it actually is | Evidence |
|---|---|---|
| "stuck at 59% for two hours" | slow but advancing; a second sample moved to 69% | ticket 000DGRP989 |
| "0% for 40 minutes" during a regional peak | queueing on shared capacity; nobody can accelerate it | ticket 000ACRF8K2 |
| "archived 8 days ago, nothing happened" | stale display; a refresh showed completion | ticket 000BSRFHBW (summary only) |
| "the policy is broken, no snapshots today" | policy applied after the day's trigger hour | ticket 000GJRTG60 |
| "rollback did not fix it" | the snapshot itself captured the broken state | ticket 0002HRW3LX (log truncated; rollback is a human action regardless) |

## Reporting rule

A failed or empty query is written into the report as a limitation with its code, and
the run continues on the parts that worked. Never substitute a plausible value for a
missing field: `not returned by API` is the literal used in output.
