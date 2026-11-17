# Handoff map

Deliver this tier's facts FIRST (change set, stock, instance attributes,
error triage), then hand off. Naming rule: the sibling skill names below
come from the requirements document's transfer table; their online
availability is a pending batch-verification item (requirements section
8-8) - if the named skill does not exist in the deployed catalog, degrade
the line to "hand off to human support" without inventing a destination.

## What always stays with a human (this tier has no API for it)

| Symptom | Why it leaves | Reviewed evidence |
|---|---|---|
| Order paid but not applied; auto-refunded change order; auto-cancelled order; order effective-time questions | No order-class query API is in this tier's contract; register the order number and hand off | `T-402BBB88`, `T-F2F8EF51`, `T-DB6FCBB3`, `T-B093525E` |
| Exact refund / discount computation | Account-level discounts invisible to queries; even humans could not compute it | `T-402BBB88` |
| Quota approval, urging, cancellation, refund-credit adjustment | Internal process | `T-6D9AB6B5`, `T-BCD8AD09`, `T-8CD3F2E5`, `T-26C336BF` |
| Reservation / resource coordination / business contact | Commercial | `T-54655754`, `T-B6B7ECDB` |
| Account risk-control blocking purchases | Judgment criteria are not public; relay the message, do not speculate | `T-13A0CBFA` |
| Overdue balance handling | Billing domain; guide the customer to the Billing Management console, settlement itself is theirs or a human's | `T-F23EA8D8` |

## Routing to sibling skills

| Symptom after this tier's facts | Destination | Talk track |
|---|---|---|
| "My site is slow / crashed - do I need to upgrade?" | `alibabacloud-ecs-diagnose` | Answer the change-feasibility half with the readings ("upgrading to X is possible and costs about Y"); the root-cause half leaves: in the reviewed case the human found CPU saturation from a runaway database process and a full disk, so the upgrade question was the wrong lever; ask the customer to check CPU/memory watermarks on the CloudMonitor page before spending (`T-D35ABA20`, `T-08FC9932`, `T-5F58567D`, `T-022CD2DF`) |
| Inside-OS symptom after a change (login broken, directory missing, service down) | Human on-machine support or the matching troubleshooting skill | State "the platform-side spec already reads X, so the change action itself succeeded; this is inside the OS" (`T-4B0C62F0` `HomeDirNotFound` pattern); mention the usual prerequisites the human will ask for: snapshot first, agreed downtime window, authorization form |
| Resized disk not visible inside the OS | `area:disk-expand-diagnosis` | Capacity/partial area is out of this tier (`T-D35ABA20` showed an 80 GB disk still 60 GB inside) |
| Disk IO slow / IOPS hitting limits (any symptom combined with `StoragePerformanceReachLimit`) | `area:resource-bottleneck` | Performance-to-spec area is out of this tier; per the code's pending-review status in `references/spec-change-purchase__error-codes.md`, do not improvise an explanation (`T-022CD2DF`) |
| Instance stuck between start/stop states, no inventory explanation | `area:instance-state-diagnosis` | This tier only explains the `OperationDenied.NoStock` slice (`T-EB859CCC`) |

## Out-of-product false positives (name the boundary, route, stop)

| Wording seen | Actually about | Reviewed evidence |
|---|---|---|
| Storage capacity / snapshot-cost questions riding on "quota" keywords | OSS resource packages and snapshot billing | `T-A7A66481` |
| A quota-insufficient-style error page from the customer's own website | Customer's own web application (IIS permissions) | `T-ADB1836D` |
| Domain-binding count questions riding on "quantity limit" keywords | Cloud virtual hosting product | `T-F29AE35B` |
| Shared-bandwidth / EIP-billing / simple-application-server / legacy-kernel memory-attribute questions | Those products, not ECS changes | `T-C2E0E619`, `T-829FD34C`, `T-044B27D0` |
| Discontinued spec of another product | That product's successor packages | `T-451CEA9E` |

For these, the correct answer IS the boundary sentence plus the right door;
do not run the ECS change flow on them.
