# Error codes and customer-visible strings

Two levels, never mixed:

- **(a) Customer-visible error codes registered for this tier** - only
  `OperationDenied.NoStock` and `StoragePerformanceReachLimit` (tier
  registry). Nothing else may be presented as an official error code.
- **(b) Ticket-observed error strings** - verbatim console/API texts seen in
  the reviewed ticket set. They are matched and routed ONLY; they are not
  official codes and no handling beyond the cited evidence may be derived
  from them.

## (a) Registered customer-visible codes

### OperationDenied.NoStock

- Meaning: no stock for the requested instance type in the requested zone
  right now; also returned when starting an instance whose previous change
  left it stopped and the host resources are gone.
- Console wording that belongs to THIS handling line (level (b) aliases):
  sold-out / insufficient-inventory wording and `CheckError.Inventory`.
- Skill handling: run the entry script with `--error-string` for triage,
  then `--check-inventory` (plus `--region-id` / `--target-type`) for the
  live per-zone stock, and let the script's substitute scan offer same-tier
  types that ARE in stock. Always state the instantaneous-stock caveat
  (see `references/spec-change-purchase__inventory-fallback.md`).
- Evidence anchors (reviewed tickets): `T-EB859CCC` (start blocked by
  NoStock; the way out was a spec change to an in-stock type, then start);
  `T-7EF1DFC9` (a type temporarily sold out, then available again within
  minutes).

### StoragePerformanceReachLimit

- Registered as a customer-visible code of this tier by the tier registry,
  BUT the 40-ticket review of this tier contains NO case demonstrating its
  triggering scenario. Its detailed disposition is a pending manual-review
  item (requirements section 8-7).
- Hard rule: do NOT invent an explanation, cause or fix steps for this code.
- Interim handling: acknowledge the code verbatim; when it arrives with
  slow-disk symptoms, the disk IO area is outside this tier - hand off to
  `area:resource-bottleneck` per `references/spec-change-purchase__handoff-map.md`.

## (b) Ticket-observed strings (match and route only)

| Verbatim string | Evidence | Meaning and fixed handling |
|---|---|---|
| `The maximum number of refund vcpu is exceeded: refund ecs vcpu quota limited by user quota: [1121024] used: [1157296] need: [37888]` (numbers vary per case) | `T-BCD8AD09` | REFUND vCPU quota exhausted. Echo the three bracketed numbers verbatim; ask WHICH instances are being downgraded (the reviewed case involved two); draft the increase-application material (`references/spec-change-purchase__quota-triage.md`); submission and approval are human-only; after approval the customer retries the downgrade (~5 min propagation observed). |
| `Your available quota is insufficient.` | `T-F23EA8D8` | MULTI-CAUSE. In the reviewed case the real cause was an OVERDUE balance, not a quota cap. Fixed order: billing center first, quota application second - never send the customer to a useless quota increase before the balance check. |
| Console prompt reporting that the account has reached the regional quota cap for ECS | `T-E48C384D` | Genuine regional quota cap: self-service application entry + "reasonable amount, detailed reason" coaching. Approval state is not queryable from this tier; an application in the under-approval state LOCKS that quota item (no re-submit) - `T-26C336BF`. |
| `HomeDirNotFound: Home directory /home/ecs-assist-user is not found.` | `T-4B0C62F0` | NOT a change failure: the spec change itself had succeeded (verify with `--verify-effective`); the symptom is inside the guest OS. Hand off per `references/spec-change-purchase__handoff-map.md`; mention the usual on-machine prerequisites (snapshot first, agreed downtime, authorization form). |
| `Request DescribeImages error ... Code: InternalError ...` (with RequestId) | `T-DB1C8E03` | Service-side query error sometimes adjacent to a quota change; the reviewed evidence never established a causal quota link - do not assert one. Collect RequestId + region + zone + spec and hand off to a human. |
| Sold-out / insufficient-inventory console wording; `CheckError.Inventory` | `T-9FD79CD0`, `T-F3FCB834` | Same handling line as `OperationDenied.NoStock`; do not present them as separate codes. |

## Red lines (from the evidence discipline)

- `T-F2F8EF51`: a support agent GUESSED that an auto-refunded upgrade order
  was caused by missing stock; nothing verified it. The skill may only
  phrase this as an UNVERIFIED hypothesis, run the stock check, and hand
  order inspection to a human. Never encode "auto refund = out of stock" as
  a rule.
- `T-ADB1836D`: a website showed "quota insufficient"-style text that came
  from the customer's OWN web application, not from Alibaba Cloud. Attribute
  quota wording by source (console / API vs customer program pages) before
  running any quota flow.
- Never restate a level-(b) string as an official error code, and never
  attach handling steps that the cited evidence does not show.
