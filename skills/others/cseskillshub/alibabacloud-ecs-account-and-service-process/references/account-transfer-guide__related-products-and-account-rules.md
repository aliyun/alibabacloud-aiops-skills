# M4 — Related products, account rules, and routing

The tier's tickets are rarely ECS-only: customers "move whole accounts" and
mix domains, databases, EIPs and billing questions into one request. Answer
the ECS axis, then give each mixed-in product its own rule card — this
module is the rule set `scripts/axes/account_transfer_guide/transfer_guide.py --guide account-rules`
and `--handoff` emit from.

## Domains (they DO move between accounts)

Unlike an active campaign ECS instance, domains have a first-class account
transfer with two paths (dialogue-verified, docs in M5):

* **Online transfer** — takes effect in real time; the domain must be
  within its validity period and real-name verified.
* **Offline transfer** — about **5 working days** of review.

Quote both paths whenever a customer "moved accounts" and has domains, so
they do not assume domains are stuck with the server.

## Managed databases (they do NOT move this way)

ApsaraDB RDS and other managed database products do not support the ECS
transfer flow — real tickets end with "forwarded to the database
specialist". Recognition: the request mentions database + another account.
Action: state the boundary, hand off to the database product line through
a support ticket; never improvise a database migration plan here.

## EIPs

An EIP is an independent resource with its own transfer flow: only
pay-as-you-go EIPs qualify, and enterprise sources require an
enterprise-verified target with the identical entity name. See M3 item 1
for links. Key phrasing from tickets: "unbind the EIP before the
transfer; the EIP does not ride along".

## Account mechanics

* **One phone number binds at most 6 accounts** — this is why "I somehow
  own two accounts" happens; it is a rule, not a bug (doc in M5).
* **Private IP == intranet IP**: same concept, different wording; clarify
  when asked.
* **"Associate the instance with another team/organization"** cannot be
  solved by re-registering accounts lightly: closing an account destroys
  its data and can affect ICP filings; warn, then refer to the human
  account-center process.
* **Unsubscription / refund** (e.g. "bought in the wrong account, want a
  refund to re-buy elsewhere"): commercial flow — the customer operates it
  in Billing Management (Orders; confirm the exact instance ID first;
  refunds return along the original payment channel). This skill points to
  the console entry only and never executes or simulates the flow. No
  verified procedure URL was evidenced for the unsubscription doc, so do
  not cite one — describe the entry instead.

## Routing table (`--handoff` engine order)

Checked in this exact order — the first match wins:

| Symptom signal | Route |
| --- | --- |
| database / RDS / PolarDB / MongoDB / Redis | database product line (human ticket) |
| refund / unsubscribe / invoice / waiver | Billing Center human support |
| mentions transfer / account / entity / merge context | STAYS IN SCOPE here |
| disk expansion or partition "not taking effect" after resize | `alibabacloud-ecs-disk-expand-diagnosis` |
| instance stuck starting / stopping / rebooting | `alibabacloud-ecs-instance-state-diagnosis` |
| slow disk IO / IOPS / latency | `alibabacloud-ecs-disk-io-diagnosis` |
| none of the above | stay in scope; continue with `--assess` |

Hand-off wording template: "That symptom belongs to <target>; I am routing
you there with your original wording attached. Your transfer question stays
open with me — we can continue it any time."
