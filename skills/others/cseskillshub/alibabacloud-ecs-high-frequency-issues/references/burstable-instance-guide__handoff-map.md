# M5: Handoff Map — What This Skill Does NOT Do, and Where It Goes Instead

This skill covers exactly one symptom area: **burstable (t-series) instance
limited by CPU credits** — identification, rule explanation, billing
mechanics, mode-switch guidance (customer-executed), monitoring/alert setup
guidance, and "would upgrading fix it" decisions.

Everything below co-occurs with that area in real tickets but belongs to
another route. Detect it, finish the credit explanation, then hand off with
the ready sentence. (Track names marked "to be aligned" await this batch's
boundary list; keep them symptom-described until aligned.)

## Why the boundary is hard

- The skill is strictly read-only, runs only the four whitelisted read
  actions, never executes commands inside the instance, and never performs
  console operations for the customer.
- Anything requiring login into the OS, a console click, a commercial
  decision, or a host-level investigation is outside it by construction —
  give steps + official links + handoff, then re-verify visible facts
  read-only when applicable.

## Routing table (from ticket evidence)

| Co-occurring symptom | Ticket evidence | Route | Ready sentence |
|---|---|---|---|
| Website / port 80/443 unreachable, web service down | T-DCC05ABE, T-2F07C4BD tail | Connectivity troubleshoot track (`alibabacloud-ecs-vpc-publicnetwork-troubleshoot` covers public-network path; else human ticket) | "Credit throttling explains slowness, not total unreachability — the port/service itself needs the connectivity check." |
| Which process/site ate the CPU (historical attribution) | T-5926A611, T-584B88C6 | Customer-side in-guest observation at the spike moment / self-deployed collector; suspected intrusion -> human security ticket | "The cloud side cannot replay yesterday's process history; observe at the spike moment or deploy a collector (e.g. atop on Linux)." |
| Host-level contention / CPU steal / noisy-neighbor suspicion | T-7DFEF9F9 | Human ticket (hardware/host track) after the credit explanation | "Guest vs host statistics differ; if steal persists with credits healthy, only a host-side human check can settle it." |
| CloudMonitor agent missing, "collecting" state | T-094911FC | Customer self-installs per monitoring doc (this skill gives the link only) | "Empty OS-level metrics mean the monitoring agent is absent, not that credits are broken." |
| Refund / waiver / voucher / fee dispute | T-6F237607, T-0495147E | Human billing (commercial) ticket | "Fee review is a commercial decision this skill cannot make; submit a billing issue ticket." |
| Cloud backup client failures co-occurring | T-094911FC | Backup support track | "The backup error is a separate area from CPU credits; route to backup support." |
| Spec change / reboot / snapshot execution | T-408C886A, T-BDB55096 | Customer console action (prerequisites explained here) | "The change itself is yours to run in the console; here are the prerequisites: snapshot, off-peak window, stop apps." |

## Ready boundary statement (use verbatim when refusing execution)

"This skill is strictly read-only: it explains what and why, verifies facts
via Describe/Get queries, and hands every operation (console switches,
in-guest commands, spec changes, reboots, snapshots, agent installs, billing
actions) to you as documented steps or to a human ticket."

## Anti-scope-creep note

Weak models drift: when a customer says "just switch it off for me", reply
with the boundary statement + the click-path from
[mode-switch-guide.md](burstable-instance-guide__mode-switch-guide.md) + the OFF-consequence warning.
Never generate a runnable mutating command, and never present a human
ticket's likely outcome as certain.
