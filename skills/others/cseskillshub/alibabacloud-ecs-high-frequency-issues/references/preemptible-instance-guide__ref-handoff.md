# Handoff map — what this tier does not answer

This skill answers exactly one symptom area: **a preemptible (spot) instance was
interrupted, stopped by the system, or reclaimed** — plus the spot-inventory and
cost-composition questions that the tier's own tickets land on. Everything else is
identified and routed, not half-answered.

Neighbour names below come from the tier list this skill was derived from, and the
evidence bundle did **not** include a machine-readable neighbour list, so treat each name
as a description of the destination, not as a registered skill identifier. Confirm the
exact target skill before naming it to a customer.

## 1. Identify first, then route

| Detection (usually one read-only field) | Route to | Do here |
|---|---|---|
| `SpotStrategy` = `NoSpot`, or the field is absent, and the instance stopped | Instance stop-cause / forced-stop tier | Report the billing type that was read and stop; do not explain spot |
| Stop notice with a security or content-related lock reason, no spot bidding mode | Compliance / forced-stop tier | Same |
| Subscription (prepaid) instance near expiry, renewal, "deleted by mistake" | Expiry, release and retention lifecycle tier | Only the spot retention rules are answered here |
| "Shutdown with no charge" / saving-stop-mode rules in general | Pay-as-you-go stop-mode tier | Only this one overlapping fact: disk charges continue while the instance is stopped |
| Snapshot or image operations themselves, their progress, their pricing | Snapshot and image tier | Only the retention rules: what survives, and the same-zone and system-disk constraints |
| Any specific amount, discount application, refund, invoice, voucher or coupon coverage | Billing and commerce tier | Composition rules and the self-check path only (`ref-billing-scope.md`) |
| Outbound traffic cost | Traffic and bandwidth tier | Nothing |
| Auto Scaling, capacity-rescue design, multi-instance architecture | Solution and architecture tier | The suitability judgement only (`ref-inventory-advisor.md` §4) |
| Purchase failure on a **non-spot** instance, or a bare order-placement error | Instance purchase and creation tier | Only the spot supply rule and the inventory query result |
| Planned maintenance or restart notices that are not spot reclamations | Maintenance-notification tier | Identification of the difference |
| Quotas, account limits, real-name blocks | Account and quota tier | Nothing |

## 2. Mixed requests

A ticket often carries two symptoms. Handle the spot area with evidence and route the
rest in the same answer; never silently drop the second part, and never answer it from
memory.

Example shape: *"My spot instance stopped by itself and I was overcharged."*
1. Spot area: read the billing type, status and zone; state the reclamation mechanism and
   the attribution limit; give the retention guidance.
2. Money area: explain that compute is one line of the bill and name the other lines;
   state that figures are out of reach here; hand off to the billing tier.

## 3. Standard handoff wording

Keep three things in every one: what this skill **did** establish, what it **cannot**
establish and why, and the concrete next step for the customer.

- **Amounts:** *"I can explain what a spot bill is made of and where to read it per
  instance and per day. I cannot read or confirm your figures — this guide is read-only
  and has no billing query. For figure reconciliation, open a billing support ticket."*
- **Attribution of one specific release:** *"Cloud-side read-only queries expose the
  instance's billing type and status, not the trigger of a past interruption, and not
  notification delivery records. The official interruption-event self-check page shows
  what your own console exposes; if you need platform-side evidence, that is a support
  ticket."*
- **Notification not received:** *"The notice goes to the contact bound to the account,
  which in a company account is often not the operator. Recipients are managed in the
  Message Center, on your side. I cannot verify that a message was sent or delivered."*
- **Workload was stateful:** *"A preemptible instance carries no availability guarantee, so
  a persistent service on it will be interrupted again. The next step is a change of
  charging type, which you perform in the console; I can re-check the instance afterwards
  with the same read-only queries."*
- **Vouchers and campaign coverage:** *"There is no published per-instance-type list of
  covered specifications; coverage follows what the voucher area in the console shows."*

## 4. Open questions — never answer these here

These came up in the tier's tickets and have **no conclusion in the evidence bundled with
this skill**. Saying "I don't have verified information on that, and here is the ticket
route" is the required behaviour; constructing a plausible mechanism is the failure mode.

| Question | Status |
|---|---|
| Can a running preemptible instance be converted to subscription, and what happens to it if so | Unverified — hand off |
| Can the public address of a preemptible instance be swapped | Unverified — hand off |
| Is the undiscounted price charged first and the difference refunded later | Unverified; the originating ticket was escalated without a bundled conclusion — hand off |
| Which interruption events an API exposes for a released instance, and under which action name | No verified API contract bundled; the customer self-check document is the only path quoted |
| Windows-specific interruption and notification behaviour | No bundled evidence; the mechanism rules are OS-independent, the guest-side specifics are unverified |
| Whether the spot advisor price and interruption-rate data can be read programmatically here | No contract bundled; only the console pages are referenced, as customer-read data |
