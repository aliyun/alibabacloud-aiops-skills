# Bandwidth, billing mode and activation matrix

Facts on this page come from the ticket corpus of this tier and the official pages listed in
[console-entrypoints.md](bandwidth-modify-guide__console-entrypoints.md). Where the corpus disagreed with itself, the item
is not asserted here; it is recorded in [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).

## 1. Two dimensions that are not the same thing

This single distinction accounts for most of the tier's confusion, including first-line answers
that contradicted each other.

| Dimension | Values | What it pays for | Where it is changed |
| --- | --- | --- | --- |
| Instance charge type | subscription, pay-as-you-go | the compute instance, its system disk, the image licence | renewal and billing center |
| Bandwidth billing mode | fixed bandwidth, pay-by-traffic | outbound public bandwidth only | the bandwidth change entry |

Consequences worth stating out loud to a customer:

* A subscription does **not** include a traffic allowance. Choosing pay-by-traffic on a
  subscription instance is normal and is not a conflict; that traffic is billed afterwards and can
  accumulate even while the instance itself is prepaid.
* Renewing an instance does not change its bandwidth billing mode, and changing the bandwidth
  billing mode does not change the renewal price of the instance.
* Each resource item is billed on its own: bandwidth, disk and compute are priced and paid
  separately. A customer who "already paid for the server" has not paid for the traffic.

## 2. What actually takes effect, and when

| Change | Restart needed | When it becomes visible |
| --- | --- | --- |
| Public bandwidth value, up or down | no | immediately after payment |
| Bandwidth billing mode conversion | no | after the conversion is confirmed on its page |
| CPU and memory specification | yes | only once the instance restarts |
| Renewal with a configuration change | depends on the configuration part | at the term boundary |

* Bandwidth and specification are different areas. Telling a customer to reboot for a bandwidth-only
  change is wrong, and telling them a spec change is live before the reboot is equally wrong.
* A paid order and an effective configuration are separate facts. Always read the live value before
  concluding that a change is missing.
* Before a specification restart, three cautions belong in the answer: pick an off-peak window,
  stop the application so buffered writes reach the disk, and take a snapshot first. Snapshots are
  billable resources, so warn that the snapshot itself costs money. The skill does not take
  snapshots; it points at the console entry.

## 3. Fixed public IP versus EIP

| Shape of the public address | Can the address be changed? | Path |
| --- | --- | --- |
| Fixed public IP assigned to the instance | not in place | five-step EIP path |
| Already bound to an EIP | yes | unbind, apply another, bind it |
| No public address at all | nothing to change | buy bandwidth or bind an EIP first |

`--intent ip-swap` prints the path; see [eip-swap-runbook.md](bandwidth-modify-guide__eip-swap-runbook.md).

## 4. Temporary upgrade versus a normal change

| | Temporary bandwidth upgrade | Normal bandwidth change |
| --- | --- | --- |
| Fits | planned, repeating, short peaks | sustained growth |
| Instance shape it applies to | subscription instance on fixed bandwidth | subscription and pay-as-you-go |
| Reverts by itself | yes, at the end of the window | no |
| Repeating schedule | drive it from the OOS bandwidth maintenance task | n/a |

* A temporary upgrade takes effect once it is paid.
* **Cancelling a temporary upgrade that has not yet taken effect has no separate "cancel order"
  entry.** The console route is the same **Change Bandwidth** page: set the bandwidth back
  to its original value there, and do not set it to 0. Ticket `T-EBA03F4B` (2026-09) is exactly this
  case: the customer searched for an order-cancel or downgrade entry and found none, and support
  walked them through Change Bandwidth. Say "Change Bandwidth is the cancel entry", not "there is no cancel entry".
* Once the temporary upgrade is already in effect, cancelling it is a bandwidth change with its own
  billing implications; read the live value first and use the console preview before quoting money.
* The selectable duration window, and any statement about how often it may be used, are **not**
  asserted here. Both are published parameters: read the official page and the console selector for
  the case, and quote what the page shows. See [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).
* The decision that matters first is whether the peak really reached the ceiling. That is a
  monitoring reading, not a configuration value; see section 6.

## 5. Inbound bandwidth follows outbound

Published rule, confirmed by the ticket corpus:

* purchased outbound **below 10 Mbit/s** → inbound ceiling is 10 Mbit/s;
* purchased outbound **at or above 10 Mbit/s** → inbound equals the purchased outbound value.

The script prints both live values plus the value the rule predicts, so a customer who insists that
download is slow while upload is fine gets an evidence-based answer instead of an opinion.

## 6. Deciding whether bandwidth is the real limit

1. Read the configured outbound value with `DescribeInstances`.
2. Ask for the console bandwidth monitoring chart over the affected window, or the customer's own
   business-side counter for the same window.
3. Peak close to the configured value → capacity problem: section 4 decides temporary or permanent.
4. Peak far below the configured value → not a capacity problem: hand off with the two numbers
   attached, per [handoff-matrix.md](bandwidth-modify-guide__handoff-matrix.md). ICMP-based tests can show loss that the
   real TCP path does not, so do not treat ping loss as proof of a bandwidth fault.

This skill prints no utilisation figure of its own; the absence is declared in every run's
limitations block. See [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).

## 7. Money rules that can be explained, and the one thing that cannot

Explainable, in words:

* A downgrade cannot be revoked afterwards. Restoring the old value is a new change, priced as a
  difference, and it is not guaranteed to cost what the original purchase cost.
* Discounts are not inherited across a configuration change. A discounted or campaign order
  converts at its discounted rate only for that order.
* Leaving a campaign price is permanent: once the configuration changes, renewals are priced at the
  standard rate rather than the campaign rate.
* Converting fixed bandwidth to pay-by-traffic prorates and refunds the bandwidth portion
  automatically, and that refund can be zero when the original order carried a discount.
* A five-day unconditional refund is available for some purchases, but a coupon spent on them is
  not returned.
* The bandwidth change page enforces whatever floor applies to that instance shape and region. Read
  the floor from the page; do not promise a specific minimum, and do not promise that zero is
  reachable. See [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).

Not explainable, ever:

* any concrete refund amount, price difference, configuration fee or renewal total. The three
  sanctioned answers are the console preview, the price configurator, and a commercial follow-up.
* The preview method is precise and worth teaching: open the change or conversion page, set the
  target, read the estimated amount on the confirmation page, and do not confirm the order.
* Campaign pages list fixed configurations, so an overseas or non-standard selection is a
  commercial conversation, not a self-service one.
