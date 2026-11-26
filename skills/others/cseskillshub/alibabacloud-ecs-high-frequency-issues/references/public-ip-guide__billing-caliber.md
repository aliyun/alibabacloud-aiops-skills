# Billing and renewal caliber

What may be said about money, and what may never be.

## The two models

| Question | Fixed public IP | EIP |
| --- | --- | --- |
| What pays for bandwidth | the instance's public bandwidth setting | the EIP's own bandwidth or traffic setting |
| Is there a separate item | no | yes: a configuration fee, plus bandwidth or traffic |
| What renews it | the instance renewal | its own renewal, on the EIP page |
| What happens at instance release | the address goes back to the pool; only the 7-day reclaim path can bring it back | the EIP stays allocated and keeps being billed |
| Cost of switching to the other model | one way only: the fixed public IP can be converted into an EIP, never back | no reverse conversion exists: an EIP cannot become a fixed public IP again, so that type is only reachable by releasing the address and allocating a new one, which changes it |

Say plainly that they are two different models, because the recurring complaint is
"the EIP should renew with the machine" and, on the other side, "the guidance itself
created this charge".

## Read the current billing mode before advising anything

The most expensive mistake in the recorded cases was advice given without checking
what the instance is already billed on: a customer reported that charges appeared
after following a change path, and the query showed the bandwidth had already been
on the pay-by-traffic model beforehand. So the report always states, from the
returned fields, before any recommendation:

- `InstanceChargeType`: subscription or pay-as-you-go for the instance;
- `InternetChargeType` and `InternetMaxBandwidthOut`: how the instance's public
  bandwidth is billed and how much it is;
- for an EIP, `ChargeType` (its own subscription) and `InternetChargeType` (bandwidth
  or traffic), plus `Bandwidth` and `Status`.

If a field did not come back, say it did not come back. Never fill the gap from
memory, and never restate a value the customer recited as if it were verified.

## What this skill never does

- It does not compute a refund, a price difference, a renewal price, or a daily fee.
  In the recorded cases the answer to each of the five fee questions a customer asked
  was the same: the estimated fee is shown on the console conversion or buy page
  before confirming, for that account, with its discounts. Point there.
- It does not touch the promotional or campaign renewal terms: a changed configuration
  can lose the original campaign price, and whether it does is shown at the moment of
  the change.
- It does not run or schedule the billing-method switch, the conversion, the
  allocation, the unbind, or the release. Those are the customer's clicks, and the
  release of an EIP is final.
- It does not handle billing disputes. Those go to a support ticket with the state
  block attached.

## Figures that appear in the source material

Each of these is a case figure. Carry the qualifier, or leave the number out:

| Figure as recorded | How it may be repeated |
| --- | --- |
| daily configuration fee of 0.72 CNY for a small EIP in an overseas region | "one overseas case recorded 0.72 CNY per day; confirm the current price on the buy page" |
| release cycle of 14 days on a certain account type, with release protection not overriding it | "some account types recycle sooner than the standard window, and protection does not override that; the account owner confirms the cycle" |
| available balance above 100 CNY on the destination account for a transfer | "a case recorded a 100 CNY threshold; confirm the current requirement in the transfer document" |

The 7-day reclaim window for a released public address is **not** a case figure: it
is the documented platform rule. State it as the rule, together with its two failure
conditions (the window has passed, or another account already holds the address). Do
not present it as a ticket-only or "ask support" path.

Internal-only hosts and account consoles never appear in a customer-facing answer.

## Where the customer looks

| Need | Entry |
| --- | --- |
| the estimated fee of a switch or conversion | the console page for that change, before confirming |
| EIP list, status, bandwidth, release | `https://vpc.console.aliyun.com/eip/{region-id}/eips`, with the customer's region |
| reclaiming a released address inside the 7-day window | the same EIP page, the apply-for-a-specific-address entry (the `AllocateEipAddressPro` call behind it takes the address in `IpAddress`); the customer performs it |
| new EIP purchase and its subscription price | the EIP product buy page, with the target region selected |
| renewal of the instance and of the EIP separately | `https://billing-cost.console.aliyun.com/renew/manual` |
| historical purchases | the order management page of the billing console |

Documentation for the bandwidth side:
https://help.aliyun.com/zh/ecs/user-guide/modify-the-bandwidth-of-an-eip.md and
https://help.aliyun.com/zh/ecs/user-guide/network-bandwidth.md. A pure bandwidth
up- or down-grade, with no address question in it, belongs to the bandwidth
modification guide in the advanced-network-diagnostics extension package; this
skill keeps only the billing-method switch that is a precondition of an address
change.
