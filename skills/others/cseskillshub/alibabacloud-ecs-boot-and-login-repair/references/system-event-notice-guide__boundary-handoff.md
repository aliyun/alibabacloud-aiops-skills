# Boundary and handoff

This tier answers one symptom axis: a customer received, or thinks they received, a
system event or scheduled maintenance notice, and asks why, what the state means,
what the deadline is, and what to do about it. Everything else is recognised,
answered only as far as the notice goes, and handed off. Identifying the boundary
**is** part of the answer; silently attempting the work is not.

## Handoff table

| Adjacent symptom | What this skill still does | Where it stops | Hand it to |
|---|---|---|---|
| Instance stuck in Starting, stop or start failing, no error message, VNC needed | Report the status the read returned, and whether the maintenance event explains the moment | Any start/stop failure triage, console session, re-scheduling | Instance start and stop failure skill |
| Reading guest logs, proving what happened inside the OS, suspected intrusion or unexplained configuration change inside the instance | Confirm whether a platform-side event record explains the restart; hand over the self-check list and interpret what the customer pastes back | Logging in, running any command inside the instance, incident investigation | Guest access or operating system investigation skill; security incident skill when intrusion is suspected |
| CloudMonitor metric disagrees with `top`, iowait accounting, alert rule thresholds | State that the event feed carries no per-disk, per-process, or percentage detail | Metric interpretation and alert rule design | Monitoring and alerting skill |
| Which disk is saturated, what the throughput limit should be, disk category to buy | Explain what the storage performance event code actually means | Disk-level bottleneck location and sizing | Block storage performance skill |
| Region or zone closure: image copy, cross-region rebuild, remaining subscription value, refund, coupon, SLA claim | Interpret the closure notice and list the official migration steps in order | Performing migration, and every commercial or billing decision | Migration skill plus billing or unsubscribe skill; commercial approvals go to a human handler |
| Compensation eligibility and payout for a downtime incident | Quote the SLA page and the reporting window as a rule | Judging eligibility, filing or tracking the claim | Account billing channel |
| Anything needing a change: rebooting for the customer, moving the automatic time, taking a snapshot, submitting a request | Refuse the action and give the console path plus the ticket route | Execution itself | The customer, in the console |

## How to hand off

Name the gap, then give one concrete alternative. Three sentences, no hedging:

```
This needs <guest log access / a configuration change / a commercial approval>,
which is outside this read-only skill.
You can <the step plus the document>, or submit a ticket for <category>.
What I can still confirm is <the facts already read>.
```

Keep the last line: a customer handed off without their facts has to repeat the
whole investigation at the next stop.

## Phrases that signal a handoff

These openings almost always mean the question has left this tier. Read the notice
part, answer it, then hand off the rest:

- "can you log in and check"
- "why did it not come back up"
- "restart it for me" / "push the window to Sunday"
- "which disk is the problem and what percentage"
- "monitoring says 99% but `top` says 20%"
- "transfer the remaining months to the new instance"
- "someone got into my server"

## What is never answered here, in any form

- Any write, including a command drafted for the customer to run against a cloud
  resource.
- Host health, physical machine identity, and migration destination: not published
  to customers, and the honest answer is that neither this skill nor the console
  can show it, so a ticket is the only route.
- Progress inside an offline or human process: a reschedule approval, a refund, a
  manual audit.
- A confident answer built on a value the reads did not return.
