# Handoff Scripts (Neighbor Symptoms: Identify, Route, Do Not Diagnose)

This tier answers billing-mode selection and conversion only. Mixed tickets
are the norm in this pool (e.g. one ticket asking about memory upgrade +
fee detail + traffic charge together), so triage is a first-class output:
recognize the neighbor symptom, say plainly it belongs elsewhere, hand over
the right pointer, and keep the billing-relevant slice here when one
exists.

> Tier names below are symptom-area labels from the requirement document
> and are pending alignment with the batch tier list; the one verified
> existing online skill is `alibabacloud-ecs-diagnose` (dedup check this
> round).

## Routing table

| Customer symptom (recognition cue) | Say / do here | Route to |
|---|---|---|
| Instance unreachable, crashes, boot stuck, performance faults | "This is an instance-health question, not billing" | `alibabacloud-ecs-diagnose` (existing online skill) |
| Upgrade / downgrade CPU, memory, instance family | Billing-side note only: conversion and spec change are separate operations | Spec-change tier; cite: https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md |
| Disk capacity expansion, or "new size not visible inside the OS" | This tier answers only "how is the expanded disk billed" (subsequent disk expansions bill pay-as-you-go [ticket-summary T-DACEA392]) | Block-storage expansion tier; OS-side verification goes to the customer's own read-only commands or the cloud-assistant / remote-connection tier |
| Fixed bandwidth vs pay-by-traffic rework, traffic-cost optimization | Explain why the traffic charge exists (residual checklist row 3), then hand off the rework | Bandwidth-config tier; cite: https://help.aliyun.com/zh/ecs/user-guide/modify-the-bandwidth-configurations.md ; optimization quotes -> sales manager |
| Bill line-item audit, invoice issuance, refund arrival tracking, quota deduction balances | "Money records live in the Billing Center; here is where to look / paste from" | Finance/billing tier + customer self-check screenshots |
| IP geo-attribution mismatch, latency/path quality, replace-my-IP | Note that third-party IP databases can lag real region assignment [ticket-summary T-ED6D702C] | Network/IP tier |
| Snapshots, security add-ons, other products' independent charges | Point at the owning product console (residual checklist rows 2/4); disposal steps stay with those products | Their own product tiers |
| Anything needing data from INSIDE the guest OS | "Please run this read-only command yourself and paste the output" | Customer self-help, or cloud-assistant / remote-connection tier |
| Campaign prices, 99/199-style activity eligibility, discounts | Never confirm eligibility or amounts; "the sales manager finalizes campaign pricing" | Sales manager handoff |
| Account-security items inside a billing ticket (e.g. SMS code not arriving) | Not billing; acknowledge and separate | Account-tier handoff [ticket-summary T-AABC1FF1 side question] |

## Ready-to-send handoff sentences

- Sales/pricing: "Billing-mode mechanics I can answer right here; the
  specific activity-package price and eligibility are confirmed by a sales
  manager, so I am routing that part to them. Everything I state below
  avoids promising any number."
- Finance detail: "I can read whatever bill screenshot you paste from the
  Billing Center, but pulling line items, invoiceable amounts, or refund
  progress is an account-side query outside this advisory's read-only
  surface. The Billing Center (or the billing support tier) is the right
  channel for the records themselves."
- Spec change: "Changing memory/CPU is an upgrade/downgrade operation with
  its own rules document (configuration-change overview above); the
  billing-method question itself I keep answering here."
- Guest OS state: "What the operating system actually sees (disk sizes in
  use, mounted capacity) cannot be read through cloud APIs from here.
  Please run the read-only command I list and paste its output -- or use
  the remote-connection/cloud-assistant channel -- and I will interpret
  it."

## Anti-patterns (learned from mixed tickets)

1. Do not answer three mixed questions in one blur (T-DA4AEB3C pattern):
   split them, label which part this tier owns, hand off the rest.
2. Do not fabricate usage numbers a colleague "would have looked up"
   (T-EDF10007 closed unresolved precisely because traffic data was never
   fetched): ask for the export instead.
3. Do not treat "the console shows it" as "this skill can see it": every
   Billing-Center-only value is a customer self-check item.
