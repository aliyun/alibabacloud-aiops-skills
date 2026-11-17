# M3: Handoff Matrix (identify, then route -- never handle here)

This skill handles exactly one area: ECS support-ticket follow-up wording
and service-complaint material preparation. Every other symptom is detected
by `scripts/areas/service_escalation_guide/ecs_service_escalation.py --screen` and handed off below with
its target skill. Detection lives in `scripts/areas/service_escalation_guide/_constants.py`
(TECHNICAL_ROUTES / ADJACENT_ROUTES); this module is the human-readable
version plus the delivery wording. Keep service-process materials
collected so far -- the handoff message carries them so the customer never
repeats themselves.

## Handoff targets

| Customer wording (detected symptom) | Area | Handoff target | This skill's action |
|---|---|---|---|
| "disk full", "no space left on device", "inode exhausted", "too many small files" | disk capacity / inode usage | `area:disk-expand-diagnosis` | identify + hand off; never run capacity diagnostics or guest reads |
| "expanded the disk but the size did not change", "partition/volume not extended" | disk expansion effectiveness | `area:disk-expand-diagnosis` | identify + hand off |
| "instance won't start", "stuck stopping", "left in an intermediate state" | instance lifecycle state | `area:instance-state-diagnosis` | identify + hand off |
| "the disk IO is slow", "latency high", "IOPS below spec" | disk performance | `area:resource-bottleneck` | identify + hand off |
| "out of stock", "sold out", "cannot buy/upgrade" | inventory / specification change | `area:instance-modify-diagnosis` | identify + hand off; no inventory read (its API permission point is not granted for this tier) |
| "my account is penalized / banned, I appeal" | violation punishment appeal | `area:punishment-appeal-guide` | identify + hand off; an appeal is NOT a ticket follow-up |
| "refund me", "unsubscribe" | commercial (refund) | `area:unsubscribe-refund` | identify + hand off; never negotiate or promise amounts |
| "I need an invoice / contract" | commercial (finance docs) | finance document flow in the console, otherwise a ticket (no skill owns invoice/contract issuance) | identify + hand off |
| "transfer this account / change owner" | account ownership | `the Alibaba Cloud account ownership transfer process (console ticket; no skill here performs it)` | identify + hand off |
| "have someone call me", "want a business manager" | business contact | `the customer's account manager or a console ticket asking for a callback (no callback is promised here)` | identify + route; promise no callback |
| "product idea", "feature request", "you should add" | product suggestion | product feedback process (no published skill owns it; the console feedback flow, otherwise a human ticket) | identify + route; a suggestion is not a complaint package |
| "that was a test ticket / submitted by mistake" | invalid ticket | `closing the ticket in the console with a note (no diagnosis is needed)` | explanatory wording; do not build follow-up material for it |
| technical symptom inside a follow-up ("no reply and the disk is full") | composite | technical target first, service area second | state that chasing the ticket never substitutes for fixing the fault; then finish the package |

## Handoff wording template

> What you are describing is the **<area>** question, not the ticket-process
> question this guide handles, so I am routing you to **<target skill>** --
> and so you do not repeat yourself, here are your ticket number and
> timeline as collected so far: <facts>. This guide does not change, expedite
> or speak for the ticket.

## Composite-request order (mandatory)

1. Resolve any open technical area first (customer picks the technical
   skill; the package travels with the ticket number).
2. Then deliver the follow-up/complaint package for the original ticket.
3. Commercial demands (refund, compensation, penalty) never enter the
   package -- they leave through their own handoff row above.
