# Known limitations of this version

State these in the report instead of working around them. Each entry says what is
missing, why, and what evidence to use instead.

## API coverage

The only actions wired into the scripts are the six listed in
`references/ram-policies.md` and declared in `related_apis.yaml`. That leaves real
gaps:

| Missing capability | Consequence for the report | Instead |
|---|---|---|
| auto snapshot policy listing and its disk associations | policy names, schedules, trigger hours and binding counts cannot be read | derive coverage from disks plus automatic-type snapshots (`policy-coverage`), or filter `DescribeDisks` by a `--policy-id` the customer supplies, and state that the schedule itself is unconfirmed |
| snapshot chain capacity | the billed figure is unavailable; `SourceDiskSize` is a disk size, an upper bound | console snapshot chain view; `lifecycle-inventory` labels the estimate as not the billed amount |
| snapshot consistency groups | application-consistent group outcomes are not directly visible | infer from snapshot records plus Cloud Assistant history |
| snapshot copy, archive tiering, retention modification | these stay guided console steps | `references/copy-archive-export.md` |
| Cloud Assistant agent status | "agent offline" can only be inferred from failed invocations | ask the customer to confirm the agent, per `references/guest-inspection.md` |
| region listing | regions are never enumerated automatically | require `--regions` with every region holding disks; ask rather than assume |
| Cloud Monitor metrics | write-rate context during a creation window is not queried | guided guest readings; see the parameter note below |
| account arrears and risk-control state | no query exists, so those branches are prompted, not judged | console banner; route per `references/handoff-boundaries.md` |

Two rules made these absences deliberate: an action may not be added to a script, a
config file or a RAM list before its existence, read/write nature, required
parameters and RAM action name are verified; and the permission point must never be
guessed. The requirements document tracks the same items as open.

## A naming trap for whoever adds Cloud Monitor

`DescribeMetricLast` is authorised by `cms:QueryMetricLast`: the API name and the RAM
action name differ. Writing the API name into a policy yields a denial that looks like
a missing grant. Its metric dimensions and period parameters are also still
unconfirmed here, which is why the metric reading is not part of this version.

## Evidence quality from the ticket record

Facts sourced from a summary rather than a dialogue are marked "(summary only)" where
they appear, and carry less weight. Three classes of gap were recorded upstream:

- Threads whose dialogue was never retrieved, so only the summary exists.
- Threads truncated mid-conversation. Notably ticket 000BSRFJZW (the application-
  consistent case) ends in "checking" - the claimed success after a reboot is **not**
  in the log, so section 4 of `references/snapshot-lifecycle.md` presents the repair
  ladder as hypotheses to test, not as a proven fix. Tickets 0002HRW3LX and
  0008MRX2NY are truncated the same way.
- Phone-only tickets with no transcript, where the agent's steps cannot be reviewed at
  all.

One contradiction inside a retrieved thread was resolved rather than repeated: the
snapshot-size statements in ticket 0001FRZPLN conflict with each other, and the chain
formula from ticket 00094RC1SX is used because the console view and the bill both
follow it. See `references/snapshot-billing-facts.md`.

## Method limits

- One sample cannot distinguish a stalled task from a slow one; `--polls 3` exists so
  the verdict rests on two readings.
- Reports describe the account returned by `sts:GetCallerIdentity`. Multi-account or
  cross-account questions, and "who created this" attribution beyond the API fields, are
  outside what these queries can see; operation audit trails remain a manual
  service-side investigation, which is the pattern in ticket 0001ZS4R16 where support
  itself could not resolve the source from the console.
- Estimates use one reference unit price for mainland standard snapshots. Regional
  pricing, packages and promotional rates are not modelled; the Billing and Cost
  Center is authoritative.
- Nothing here accelerates a queued task, opens a closed whitelist, or diagnoses a
  genuine fault on the service side. Those are the three places where this skill is
  expected to reach the same answer a human engineer would and stop.
