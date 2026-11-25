# Incident and SLA guide: reboots, planned maintenance, and availability impact

Scope: the customer's instance restarted on its own, or a maintenance notice arrived, and
the customer wants the cause and any availability compensation. Related:
[migration checklist](migration-checklist.md), [fees and refunds](billing-dispute-guide.md),
[hand-off boundaries](handoff-boundaries.md).

## Critical boundary: attribution depends on customer evidence

This skill has no cloud API to read the platform's instance system event on the customer's
behalf (the injected contract exposes only `DescribeInstances`). The ticket back-end that a
human agent uses to read "the message the server received" is NOT available here. Therefore
attribution is NOT self-proved: ask the customer to paste the SMS / message-center text or a
screenshot of the ECS console instance-event page, then classify from that evidence. If the
customer cannot produce any notice, do not guess; use the two-branch fallback at the bottom.

## Classify the event from the customer's notice

- `SystemMaintenance.Reboot` (planned maintenance)
  - Cause: a latent risk detected on the underlying host. The platform schedules a reboot
    window and normally notifies roughly 24 to 48 hours ahead.
  - What the customer can do: within the notified window, a restart can often be moved to a
    low-peak time. Console path: ECS > Instances > select instance > More > Instance Status >
    Restart. Restart offers a Normal mode and a Force Restart mode; Force Restart can lose
    unwritten data, so prefer Normal and use force only when the guest is unresponsive.
  - Common misunderstanding: the customer did not notice the advance notice and reads it as an
    unrequested forced reboot.
- `SystemFailure.Reboot` (unexpected host failure)
  - Cause: an unexpected software/hardware failure on the underlying host; the platform
    restarted the instance and migrated it to a healthy host to recover service. Notification
    typically follows the event.
  - What the customer should own: enable application auto-start on boot and add application-
    level redundancy so a single host event does not take the service down.
  - Event reference doc: https://help.aliyun.com/zh/ecs/user-guide/summary

## Availability compensation (SLA) wording, standardized

Compensation is APPLICATION-BASED, not automatic. Uniform statement to give every customer:

- A request can be filed after the 5th working day of each month, for the previous month's
  instances that did not meet the availability commitment.
- The request must be filed within 2 months after the end of the affected month; overdue
  requests are not accepted.
- Terms: https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud201909241949_62160.html
- Entry points seen in tickets (a legacy and a current console path; confirm the authoritative
  one before submitting):
  - https://usercenter2.aliyun.com/sla/availabilityhome
  - https://billing-cost.console.aliyun.com/sla/availabilityhome

Deadline re-verify: after the customer submits, ask them to paste back the acceptance status
so the two-month limit and the filing month are tracked. Do not promise an approval outcome.

## The value this adds over an inconsistent ticket

Real tickets showed different agents giving different answers on the same symptom (one closed
without ever mentioning the SLA route, others provided it). This guide makes one uniform
wording the default: classify the event, give the correct self-service step, and always state
the SLA application route and its deadline.

## Two-branch fallback when no notice/evidence is available

- Suspected platform event but no proof in hand: give the SLA route and its filing deadline,
  and mark the conclusion "attribution not self-proved, relies on customer evidence".
- Cannot determine at all: record the request and route to a human for back-end diagnosis;
  this skill does not fabricate a cause.
