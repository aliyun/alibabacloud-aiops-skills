# Documentation register (clues only - URLs pending verification)

Hard rule for this file (inherited from requirements section 8-2): help
links may only be registered after they are returned by an official help
search. The current injection produced ZERO usable help-search hits, so
this file lists ONLY document clues and search keywords captured from what
support agents actually referenced inside the reviewed ticket dialogs.

- The `slug:` clues below are ticket-dialog clues, NOT verified URLs. Do
  not assemble a URL from a slug.
- Until the register is backfilled, customer-facing output points the
  customer to the named official document **by title** in the help center
  and to the console entry points below; the skill never guesses a link.
- Backfill order: first the slugged/numbered clues below (resolve them via
  the official help search, register the returned title + URL verbatim),
  then the topic rows without clues (re-run the help search by keyword).

## Verified backfill (2026-11-12)

Three clues below are now resolved to live-verified URLs and frozen as anchors
in `references/doc-anchors.json` (soft-404 judged, body hash checked):

- `change-the-instance-types-of-subscription-instances` -> anchor `spec-change-purchase__change-types-prereq`
- `instance-families-that-support-instance-type-changes` -> anchor `spec-change-purchase__family-compatibility`
- `modify-the-bandwidth-configurations` -> anchor `spec-change-purchase__bandwidth-modify`

The runtime cites these through the anchor leg. The remaining clues stay
unverified until resolved the same way; no link is assembled from a slug.

## Clues captured from ticket dialogs

| Topic | Clue as seen in dialog | Evidence |
|---|---|---|
| Subscription instance type change (upgrade/downgrade) operation and limits | slug: `change-the-instance-types-of-subscription-instances` | `T-B4443584`, `T-91459169` |
| Which instance families support type changes | slug: `instance-families-that-support-instance-type-changes` | `T-B4443584` (notice 5) |
| Temporary bandwidth upgrade window (limits in `references/spec-change-purchase__change-rules.md`) | slug: `temporary-bandwidth-upgrade` | `T-91459169` |
| Quota management and self-service increase application | slug + anchor: `quota-management#c3adabff96ubw` | `T-E48C384D` |
| Snapshot creation steps | document number cited by the agent: 25455 | `T-4B0C62F0` |
| Snapshot billing | document number cited by the agent: 56159 | `T-4B0C62F0` |

## Topics still needing a search (no dialog clue)

Search keywords to run against the official help center (register results
here, with title + URL, once verified):

- upgrade operation and limits for pay-as-you-go and subscription
  instances ("upgrade instance type", "instance type change limit")
- reboot and effectiveness of a spec change ("restart to take effect",
  "reboot instance")
- public bandwidth billing conversion ("change bandwidth billing",
  "pay-by-traffic")
- fixed public IP to EIP conversion and release ("convert to EIP",
  "associate EIP", "release EIP")
- EIP pricing items ("EIP billing item", "EIP configuration fee")
- inventory shortage wording and cross-zone fallback ("sold out",
  "instance type available resource")
- new purchase flow and system-disk choice ("custom purchase",
  "system disk")
- discontinued instance types and successors ("retired instance type")
- downgrade refund rules and promotional-plan renewal ("downgrade
  refund", "99 plan")
- charge-type conversion and associated resource billing ("convert to
  subscription", "pay-as-you-go to subscription")
- refund-credit / refund-vCPU quota explanations ("refund vcpu quota")

## Console entry points (safe to output; not help links)

These are product console routes named in the reviewed dialogs, distinct
from documentation URLs:

- The instance-type sellability page of the buy flow
  (`ecs-buy.aliyun.com/ecs#/instanceTypeByRegion` as pasted by the agent
  in `T-F2F8EF51`): per-region saleable spec listing for self-check.
- The common buy console (`common-buy.aliyun.com`, as pointed to in
  `T-402BBB88`) for reading a price before committing.
- The ECS console instance list and its change-configuration entry for
  the customer to perform changes (the customer always confirms in the
  console).
- The Billing Management console (balance / orders / refunds) - the
  billing-first check from `references/spec-change-purchase__quota-triage.md`.
- The quota center console page for self-service quota applications.
