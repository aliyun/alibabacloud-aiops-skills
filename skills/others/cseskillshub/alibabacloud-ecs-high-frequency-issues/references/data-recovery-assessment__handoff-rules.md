# Handoff Rules (neighbouring symptoms: recognize, state boundary, route)

This skill answers exactly one question per engagement: *can the lost data
be recovered, on which evidence, and through which guided manual path?*
Everything else is recognized and routed; diagnosing neighbour topics here
would produce misleading answers.

| # | Signal in the customer's words | Route to | Before handing over |
|---|---|---|---|
| 1 | "Can the DELETED / expired INSTANCE itself come back?", retention countdowns, release notices | `area:expiry-release-retention` (expiry, release and retention lifecycle) | If any disk still exists and data on it matters, guide the data-preservation assessment first (this skill keeps that sub-question) |
| 2 | "How do I switch on / configure the file-backup product / Cloud Backup?" | `alibabacloud-cloudbackup-ecs-file-backup-essential-edition` (product onboarding and backup/restore operations) | This skill's role ends at "which backup exists / is needed and what it can restore" |
| 3 | "You roll it back for me / you re-install the system for me / confirm my write action worked" | Write actions stay manual: the customer performs them in the console with this skill's pre-action checklist; executing tiers are pending batch alignment | Always the safety-net snapshot first, then the risk acknowledgement |
| 4 | Virus / ransomware removal, intrusion tracing, port hardening (data recovery is a side request) | Host-intrusion cleanup tier (name pending batch alignment) | Inventory surviving backups here; keep the encrypted state intact via a snapshot before cleanup |
| 5 | Cannot connect, DDoS blackhole, instance stuck starting/stopping, no GUI desktop -- data not actually lost | Connectivity / instance-operation tiers (names pending batch alignment) | Ask once: "is any data actually missing?" If yes, keep the data sub-question here; route the rest |
| 6 | Charge-type conversion, renewal mechanics, refund, real-name review, RAM sub-account rights | Billing / account / RAM tiers (names pending batch alignment) | If expiry is imminent, run the pre-expiry data-preservation guidance before the account process finishes |
| 7 | Closure needs reading inside the instance (mounts, paths, service state, binlog presence) | Hand the customer read-only commands to run and paste back; otherwise route to remote-connection / Cloud Assistant tiers (names pending batch alignment) | This skill never executes in-guest commands -- saying so is part of the handoff wording |
| 8 | Requests for compensation, goodwill refunds, or a stamped "unrecoverable" certificate | Human support channel | Deliver the evidence summary; state that neither the skill nor human practice issues such certificates; never simulate an outcome |

## Handoff wording template

> "The missing-data question I can assess here is *whether the lost content
> is recoverable and how*. What you describe is mainly [neighbour topic],
> which belongs to [route]; I will not guess at it from here. Before we
> move: [before-handing-over action]."

Keep the data-preservation urgency first: every minute of continued writes
lowers extraction odds, so route quickly, not politely.
