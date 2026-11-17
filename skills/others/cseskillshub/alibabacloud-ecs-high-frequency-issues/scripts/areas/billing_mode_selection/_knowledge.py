#!/usr/bin/env python3
"""
_knowledge.py -- Embedded guidance knowledge for the ECS billing-mode skill
===========================================================================
SECURITY: READ-ONLY advisory knowledge. Nothing in this module executes
anything or handles credentials; it is the single source of the guidance
text emitted by `billing_mode_advisor.py` (kept as Python constants per
platform rule MUST 1.1.2 -- scripts/ must not contain data files).

Every statement carries a provenance tag:
  [verified-dialog]  confirmed verbatim in a real support-ticket dialogue
                     (the ticket id is named);
  [ticket-summary]   taken from a ticket summary whose full dialogue was
                     not re-checked this round -- treat as directional;
  [official-doc]     from the injected official help-document list -- quote
                     the URL, do not paraphrase numeric limits from memory;
  [console-entry]    a customer console URL observed in ticket dialogues --
                     verify reachability before quoting to a customer.

Anti-hallucination rules baked into this data: the skill NEVER states
prices, quotas, refund amounts, trial expiry dates or savings-plan
balances as facts -- those live only in the customer's Billing Center.
The guidance text always routes such numbers to customer self-check.
"""

# ---------------------------------------------------------------------------
# Intent classification: (intent id -> match phrases, lowercase substrings)
# Order matters only for tie-breaking; scores are summed.
# ---------------------------------------------------------------------------
INTENT_PATTERNS: dict[str, list[str]] = {
    "payg_to_subscription": [
        "to subscription", "convert to subscription", "change to subscription",
        "switch to subscription", "turn into subscription", "buy by year",
        "monthly year plan", "prepaid", "pre-paid", "fixed monthly fee",
        "entry not visible", "button not visible", "cannot find convert",
        "to yearly", "to annual",
        "convert to prepaid", "change to prepaid",
    ],
    "subscription_to_payg": [
        "to pay-as-you-go", "to pay as you go", "switch to pay",
        "convert to pay", "change to pay", "turn to pay", "post-paid",
        "postpaid", "pay per use", "unsubscribe and repurchase", "release and rebuy",
        "to hourly", "by the hour", "convert to postpaid", "cancel my yearly",
        "stop yearly",
    ],
    "residual_billing": [
        "still charged", "still billed", "still being charged", "keep charging",
        "charged after", "billed after", "unexpected charge", "extra charge",
        "why am i charged", "where does this fee come from", "costs keep coming",
    ],
    "expiry_handling": [
        "expire", "expired", "expiry", "about to expire", "due date",
        "renew", "unsubscribe", "refund", "when will it be released",
        "auto release", "delete the server", "how to get rid",
    ],
    "selection": [
        "which is cheaper", "which one cheaper", "more economical", "cost effective",
        "how to choose", "how do i choose", "what's the difference",
        "whats the difference", "difference between", "which billing",
        "pay by year", "worth it", "save money", "compare billing",
        "free trial", "savings plan", "99 a year", "199 a year",
        "cheaper", "cost more", "which plan", "plan is better",
        "pay per hour", "hourly or yearly", "monthly or yearly", "long term",
    ],
}

INTENT_LABELS: dict[str, str] = {
    "payg_to_subscription": "Convert pay-as-you-go -> subscription (change billing method to monthly/yearly)",
    "subscription_to_payg": "Convert subscription -> pay-as-you-go (with refund rules and auto-release risks)",
    "residual_billing": "Residual billing after a conversion or release (which items keep billing pay-as-you-go)",
    "expiry_handling": "Expiry / renewal / early unsubscription handling for subscription instances",
    "selection": "Billing-model selection consulting (which mode fits, how to pilot cheaply)",
    "overview": "General inventory + triage (no single intent detected yet)",
}

# ---------------------------------------------------------------------------
# Official documentation pointers (injected help-search hits = [official-doc];
# dialogue-quoted links = [console-entry]/[verified-dialog], flag to re-verify)
# ---------------------------------------------------------------------------
DOC_LINKS: dict[str, dict[str, str]] = {
    "billing-overview": {
        "title": "ECS billing methods overview",
        "url": "https://help.aliyun.com/zh/ecs/overview-of-billing-methods.md",
        "source": "[official-doc] injected help-search hit",
    },
    "billing-best-practices": {
        "title": "ECS payment-type selection best practices",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-ecs-billing-methods.md",
        "source": "[official-doc] injected help-search hit",
    },
    "buy-guide": {
        "title": "ECS purchase flow illustrated (incl. billing type choice)",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/a-picture-is-to-teach-you-how-to-buy-cloud-server-ecs.md",
        "source": "[official-doc] injected help-search hit",
    },
    "what-is-ecs": {
        "title": "What is ECS",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
        "source": "[official-doc] injected help-search hit",
    },
    "free-trial-expiry": {
        "title": "What to do when the ECS free trial is about to expire",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md",
        "source": "[official-doc] injected help-search hit",
    },
    "spec-change-overview": {
        "title": "Upgrade/downgrade (instance configuration change) overview",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md",
        "source": "[official-doc] injected help-search hit; also the handoff reference for the spec-change tier",
    },
    "bandwidth-change": {
        "title": "Modify fixed public bandwidth",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/modify-the-bandwidth-configurations.md",
        "source": "[official-doc] injected help-search hit; bandwidth billing rework is a neighbor symptom -- hand off, quote as pointer only",
    },
    "sub-to-payg-ticket": {
        "title": "Change instance billing method from subscription to pay-as-you-go",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-of-an-instance-from-subscription-to-pay-as-you-go",
        "source": "[verified-dialog] quoted by support in ticket T-C3E9D9B3; NOTE the direction on the page must be re-checked before quoting (dialogue wording and URL slug disagreed there)",
    },
    "refund-destinations": {
        "title": "Unsubscription refund destinations",
        "url": "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations",
        "source": "[verified-dialog] quoted in ticket T-263837C7; reachability not re-verified this round",
    },
    "unsubscription-rules": {
        "title": "Unsubscription rules",
        "url": "https://help.aliyun.com/zh/user-center/user-guide/unsubscription-rules",
        "source": "[verified-dialog] quoted in ticket T-263837C7; reachability not re-verified this round",
    },
}

CONSOLE_ENTRIES: dict[str, dict[str, str]] = {
    "ecs-home": {
        "title": "ECS console home (instance inventory per region)",
        "url": "https://ecs.console.aliyun.com/home",
        "source": "[console-entry] observed in ticket T-C3E9D9B3 dialogue",
    },
    "refund-page": {
        "title": "Billing Management unsubscription page",
        "url": "https://billing-cost.console.aliyun.com/refund/refund",
        "source": "[console-entry] observed in ticket T-263837C7 dialogue; the exact refundable amount shown on this page is the only authority",
    },
}

# ---------------------------------------------------------------------------
# Shared pre-checks (run before any conversion guidance is handed over)
# ---------------------------------------------------------------------------
PRECHECKS_COMMON: list[str] = [
    "Account in arrears? A past-due balance hides the console conversion entry and blocks disk detach/release. "
    "Observed signal: DescribeInstances OperationLocks carrying lock reason 'financial'. If in doubt ask the customer to check the "
    "Billing Center balance; resolving arrears is a customer top-up action, this skill never acts on money. [ticket-summary T-AABC1FF1]",
    "Promotional-price instances: converting or downgrading an instance bought under an activity price does NOT refund the price "
    "difference. Warn before guiding. [ticket-summary T-F740449A]",
    "Backup first: before ANY irreversible change the customer should create a snapshot or custom image in the console themselves; "
    "released data cannot be recovered. [ticket-summary T-381ADD6C / T-263837C7 notice 1]",
    "Scope expectation: converting the INSTANCE billing method does not automatically convert attached pay-as-you-go data disks, "
    "snapshots, or traffic-billed bandwidth. Run the residual-billing checklist alongside. [ticket-summary T-49041DCA / T-DF87DFC7]",
]

PRECHECKS_PAYG_TO_SUB: list[str] = [
    "Confirm direction: pay-as-you-go -> subscription is available only while the instance is in normal status and the account is not "
    "in arrears; arrears hides the entry (see common pre-checks). [ticket-summary T-AABC1FF1]",
    "Conversion does not interrupt the running service or the data on the instance. [ticket-summary T-AABC1FF1 support statement]",
    "Pricing for the subscription term is shown by the console order page at click time; this skill never quotes prices. Campaign "
    "packages (e.g. yearly activity offers) eligibility questions go to a sales manager. [verified-dialog T-E089159A pattern]",
]

PRECHECKS_SUB_TO_PAYG: list[str] = [
    "After the switch the instance is billed hourly and an arrears balance can trigger automatic release with data NOT recoverable. "
    "Snapshot/custom image backup FIRST, by the customer, in the console. [ticket-summary T-381ADD6C]",
    "Refund destination rules (verified wording): refunds default to the original payment channel; if the refund amount exceeds the "
    "account's invoiceable amount, it goes to the account balance instead. [verified-dialog T-3CA25349]",
    "To run pay-as-you-go at all, the combined account balance and vouchers must be at least 100 CNY. [verified-dialog T-3CA25349]",
    "The exact refundable amount is only known on the console refund/order page at submission time; never promise a number. [verified-dialog T-263837C7 notice 5]",
]

# ---------------------------------------------------------------------------
# Conversion guidance: customer-performed console steps. Each step is
# (entry, target, expected-result, fallback) phrased so a non-technical
# customer can follow it; the skill itself performs NOTHING.
# ---------------------------------------------------------------------------
CONVERSION_GUIDES: dict[str, dict[str, object]] = {
    "payg_to_subscription": {
        "heading": "Guide: switch a pay-as-you-go instance to subscription (customer performs all steps)",
        "steps": [
            "Open the ECS console instance list for the target region: https://ecs.console.aliyun.com/home "
            "[console-entry from ticket T-C3E9D9B3].",
            "Locate the exact instance: match by instance id first, then by name / public IP. Do not act on an ambiguous match -- "
            "ticket T-C3E9D9B3 shows even support staff can quote the wrong id, so echo the id + name + IP back for confirmation.",
            "In the instance row action menu (or the instance detail page) open the billing-method change entry -- console wording "
            "is along the lines of 'Change Billing Method' / 'Convert to Subscription'. If NO such entry appears, walk the arrears "
            "pre-check first (arrears hides it), then the status pre-check (the instance must be in a normal, non-locked state).",
            "Choose the subscription term on the order page, review the amount displayed THERE (the only price authority), and submit "
            "after the customer confirms the amount on screen.",
            "Expected result: the instance billing field becomes subscription (PrePaid) within minutes; the service keeps running.",
            "Fallback: if submission fails, capture the exact on-screen message. Two arrears codes are documented for "
            "ModifyInstanceChargeType -- DiskExpiredOrInArrears (400, 'Your account has an overdue payment for the specified "
            "instance.', official Chinese description: 指定的实例已欠费) and InvalidAccountStatus.NotEnoughBalance (403, "
            "'Your account does not have enough balance.'). Both mean the customer must fund the account in the Billing Center "
            "themselves and retry. InstanceExpiredOrInArrears is NOT a conversion error -- it belongs to StopInstance (403, "
            "'The specified operation is denied as your prepay instance is expired (prepay mode) or in arrears (afterpay mode).') "
            "and means a stop request was rejected, so never quote it as the conversion failure.",
        ],
        "reverify": "Re-run this advisory (same --region-id / --instance-ids) and confirm InstanceChargeType changed to PrePaid and "
                    "an ExpiredTime appeared; the renewal/expiry date is then visible in the console instance list too.",
    },
    "subscription_to_payg": {
        "heading": "Guide: switch a subscription instance to pay-as-you-go (customer performs all steps)",
        "steps": [
            "BACKUP FIRST (customer, console): create snapshots of every data disk / system disk you cannot lose; after the switch, "
            "arrears can auto-release the instance and the data cannot be recovered. [lesson of ticket T-381ADD6C]",
            "Read the risk acknowledgement (below) to the customer and get an explicit acknowledgement before proceeding.",
            "Open the ECS console instance list for the target region and locate the exact instance (id + name + IP echo-back).",
            "Use the billing-method change entry toward pay-as-you-go; the authoritative console page for this direction is the "
            "subscription-to-pay-as-you-go help document listed in this advisory's References section -- check the direction printed "
            "on the page before following it (ticket T-C3E9D9B3 showed a wrong-direction link slip).",
            "On the order page review the REFUND / residual-value amount shown THERE (never predicted here): refunds default back to "
            "the original payment channel; amounts above the invoiceable quota go to the account balance. [verified-dialog T-3CA25349]",
            "Expected result: the instance becomes pay-as-you-go (PostPaid); the remaining prepaid value is refunded per the rules "
            "shown on the page, typically within about 2 working days after success. [verified-dialog T-263837C7 notice 2]",
            "Fallback: if the entry is missing or submission errors, capture the exact message; lock reasons ('financial') and "
            "promotional-activity constraints are the two known blockers in this tier's tickets.",
        ],
        "reverify": "Re-run this advisory and confirm InstanceChargeType is now PostPaid; then walk the residual-billing checklist so "
                    "no related item (data disks, bandwidth, snapshots) keeps charging unnoticed.",
    },
}

RISK_ACK_SUB_TO_PAYG: list[str] = [
    "MANDATORY customer acknowledgement before guiding any irreversible step:",
    "1. After switching to pay-as-you-go, overdue balances can lead to automatic release; released data is NOT recoverable without a "
    "snapshot or custom image you created in advance.",
    "2. Instances bought under promotional/activity prices do not receive a price-difference refund on this change.",
    "3. The refund amount, destination and arrival time are exactly what the console/Billing Center shows -- this advisory never "
    "promises numbers. (Reference rules verified from dialogues: original-channel refund by default, account-balance fallback above "
    "the invoiceable amount, about 2 working days, invoiceable quota reduced accordingly, gifts/vouchers voided.)",
    "4. Data disks, snapshots, and traffic-billed bandwidth are NOT converted together with the instance; see the residual checklist.",
    "5. Ask the customer to reply that they have read items 1-4 before presenting the console steps above.",
]

# ---------------------------------------------------------------------------
# Residual-billing checklist (after conversion / release, which items keep
# being billed pay-as-you-go)
# ---------------------------------------------------------------------------
RESIDUAL_CHECKLIST: list[dict[str, str]] = [
    {
        "item": "Data disks attached to the instance",
        "why": "Converting the instance billing method does NOT convert the data-disk billing; disks stay pay-as-you-go and keep "
               "hourly bills. This exact gap produced a live ticket.",
        "where": "ECS console -> Storage & Snapshots -> Disks: check each disk's billing field; convert disk billing separately via "
                 "the console entry, or release unattached disks (customer action).",
        "source": "[ticket-summary T-49041DCA]",
    },
    {
        "item": "Snapshots",
        "why": "Snapshots are billed pay-as-you-go independently of the instance, and survive after the instance is gone.",
        "where": "ECS console -> Snapshots: list and delete what is unneeded (customer action, irreversible -- verify first).",
        "source": "[ticket-summary T-1F45414E]",
    },
    {
        "item": "Public bandwidth / outbound traffic",
        "why": "A subscription instance WITHOUT a fixed-bandwidth subscription is billed by outbound traffic pay-as-you-go -- a common "
               "'why is there an extra charge' source.",
        "where": "ECS instance detail -> bandwidth configuration; compare fixed-bandwidth vs pay-by-traffic in the console. Bandwidth "
                 "billing rework itself is a neighbor tier -- hand off (see handoff scripts).",
        "source": "[ticket-summary T-DF87DFC7]",
    },
    {
        "item": "Independent products on the same account (e.g. Security Center)",
        "why": "Products bought alongside ECS keep their own billing cycles; stopping the ECS instance does not stop them.",
        "where": "Billing Center -> Bill details by product; turn off each product from its OWN console (customer action).",
        "source": "[ticket-summary T-1F45414E]",
    },
    {
        "item": "Billing lag after release",
        "why": "Bills are issued with delay: charges appearing days after a release were accrued BEFORE it. A live ticket was closed "
               "by exactly this explanation from backend bill data.",
        "where": "Billing Center -> monthly bill detail: compare charge timestamps with the release time the customer performed.",
        "source": "[ticket-summary T-82BD6370]",
    },
]

# ---------------------------------------------------------------------------
# Lifecycle / expiry / unsubscription rules (all from verified dialogues)
# ---------------------------------------------------------------------------
LIFECYCLE_RULES: list[str] = [
    "Early release of a subscription instance goes through the Billing Center unsubscription page: "
    "https://billing-cost.console.aliyun.com/refund/refund -> unsubscribe resources -> ordinary cloud resources -> five-day no-reason "
    "refund or non-full refund -> select the instance -> submit. [verified-dialog T-263837C7]",
    "Five mandatory notices before the customer submits an unsubscription (verbatim checklist from the dialogue): 1) the resource is "
    "cleared and data is NOT retained -- back up first; 2) a successful refund usually returns within about 2 working days; 3) the "
    "invoiceable quota is reduced automatically after refunding; 4) gifts (vouchers, extended service periods) are voided; 5) the "
    "refundable amount is exactly what the refund page displays -- confirm it there before submitting. [verified-dialog T-263837C7]",
    "Doing nothing: an un-renewed subscription instance is auto-deleted and released 15 days after expiry; data is NOT recoverable. "
    "[verified-dialog T-263837C7]",
    "Manual release is possible from 00:00 of the day AFTER the expiry timestamp (e.g. expiry 2026-09-03 23:59:59 -> operable from "
    "2026-09-04 00:00), so the customer need not wait the full 15 days. [verified-dialog T-263837C7]",
    "The instance ExpiredTime returned by the read-only query (when present) is the anchor for every date calculation above; when the "
    "field is absent or ambiguous, ask the customer to read the expiry shown in the console instance list.",
]

# ---------------------------------------------------------------------------
# What read-only APIs CANNOT see -> customer self-check paths (never guess)
# ---------------------------------------------------------------------------
SELF_CHECK_ITEMS: list[str] = [
    "Savings-plan / free-trial remaining deduction and expiry date -> Billing Center (resource packages) by the customer; ask for a "
    "screenshot to interpret. 'Free trial' servers are pay-as-you-go instances offset by a savings plan, not a free standalone product. [ticket-summary T-C3E9D9B3 / T-52391345]",
    "Account balance and arrears amount -> Billing Center top banner (customer screenshot).",
    "Invoiceable amount and invoice timing -> invoices for a month are issuable after the 3rd of the following month. [verified-dialog T-3CA25349]",
    "Exact refundable amount / refund arrival progress -> the refund page and Billing Center order lines; account-side money queries "
    "are the finance/billing tier's job, hand off if it needs tracking.",
    "Monthly public-traffic usage -> CloudMonitor or Billing Center usage export (customer exports; then this advisory can help READ "
    "the numbers). Historical traffic is NOT obtainable through the read-only ECS APIs of this skill. [ticket-summary T-EDF10007]",
    "Whether an in-guest change (e.g. disk expansion) took effect inside the OS -> out of scope here: ask the customer to run a "
    "read-only OS command themselves and paste the output, or hand off to the cloud-assistant / remote-connection tier.",
]

# ---------------------------------------------------------------------------
# Selection consulting (billing-model comparison + decision rule)
# ---------------------------------------------------------------------------
SELECTION_MODEL: dict[str, object] = {
    "comparison": [
        "Subscription (pre-paid): fixed term (month/year), lower unit price, suited to 24x7 stable workloads; expiry-driven lifecycle "
        "(renew, expire, auto-release after 15 days). Instance specs can still be upgraded/downgraded within the term (spec-change tier).",
        "Pay-as-you-go (post-paid): per-second/hour billing, released anytime, suited to tests, spikes and short-lived jobs; needs a "
        "healthy balance (>=100 CNY combined balance+vouchers to open) and arrears leads to stop -> release.",
        "Either way: attached data disks, snapshots, images and public traffic may carry their OWN pay-as-you-go charges.",
    ],
    "decision_rule": "Recommended path validated in a live ticket: pilot the workload on pay-as-you-go first (release it when done, pay "
                     "only for the test window); once the workload is stable, convert that SAME instance to subscription to lock a lower "
                     "long-run price -- conversion is in-place and keeps the data. [ticket-summary T-1C279C30, support recommendation]",
    "price_policy": "This skill never quotes or commits prices, campaign eligibility (e.g. yearly activity packages), or discounts. "
                    "Console order pages are the only price authority; campaign/quote questions hand off to a sales manager. [ticket-summary T-E089159A / T-C3E9D9B3]",
}

# ---------------------------------------------------------------------------
# Neighbor-symptom handoff scripts (identify, do NOT diagnose here)
# ---------------------------------------------------------------------------
HANDOFFS: dict[str, dict[str, str]] = {
    "instance-faults": {
        "symptom": "instance unreachable / crashed / stuck booting / performance faults",
        "script": "This advisory covers billing-mode questions only. For instance health and connectivity diagnosis, use the "
                  "alibabacloud-ecs-diagnose skill.",
        "ref": "",
    },
    "spec-change": {
        "symptom": "upgrade / downgrade CPU, memory or instance family",
        "script": "Spec change is a neighbor tier; guide from the instance-configuration-change overview document and hand off.",
        "ref": "spec-change-overview",
    },
    "disk-expand": {
        "symptom": "disk capacity expansion / new size not visible inside the OS",
        "script": "Disk expansion (and making it take effect inside the OS) belongs to the block-storage expansion tier; this skill "
                  "only answers 'how is the expanded disk billed' (subsequent expansions of an existing instance's disks are billed "
                  "pay-as-you-go). [ticket-summary T-DACEA392]",
        "ref": "",
    },
    "bandwidth-billing": {
        "symptom": "switch fixed bandwidth vs pay-by-traffic / traffic-cost optimization",
        "script": "Public bandwidth billing rework is a neighbor symptom; point to the modify-fixed-bandwidth document and hand off; "
                  "optimization quotes go to a sales manager.",
        "ref": "bandwidth-change",
    },
    "finance-detail": {
        "symptom": "bill line-item audit, invoices, refund progress, quota deduction balances",
        "script": "Account-side finance queries are outside this skill's read-only ECS surface; guide the customer to the Billing "
                  "Center self-check or hand off to the billing/finance tier.",
        "ref": "",
    },
    "network-ip": {
        "symptom": "IP geo-attribution mismatch, latency / path quality, IP replacement",
        "script": "IP/quality questions are a neighbor tier; hand off after noting that third-party IP databases can lag actual region "
                  "assignment. [ticket-summary T-ED6D702C]",
        "ref": "",
    },
    "guest-inspection": {
        "symptom": "anything requiring reading data INSIDE the operating system",
        "script": "This skill never executes commands inside customer instances; ask the customer to run the read-only command and "
                  "paste the output, or hand off to the cloud-assistant / remote-connection tier.",
        "ref": "",
    },
    "sales": {
        "symptom": "campaign eligibility (99/199 activity packages), custom quotes, discounts",
        "script": "Pricing and campaign qualification is decided by a sales manager; hand the request off and do not promise amounts.",
        "ref": "",
    },
}

# ---------------------------------------------------------------------------
# Embedded FAQ (knowledge questions with no account-data need)
# ---------------------------------------------------------------------------
FAQ_TOPICS: dict[str, dict[str, str]] = {
    "free-trial-mechanics": {
        "q": "Is my free-trial server a separate free product? What happens at expiry?",
        "a": "No. A 'free trial' ECS is a normal pay-as-you-go instance whose charges are deducted by a trial/savings-plan resource "
             "package. When the trial period ends or its free quota is consumed, charges fall through to the account balance, and "
             "expiry reminders are sent. Decide before expiry: convert to subscription, or release it (customer action). The exact "
             "remaining quota and expiry date are only visible in the customer's Billing Center. See the official free-trial-expiry "
             "document for the authoritative timeline.",
        "source": "[ticket-summary T-C3E9D9B3 / T-52391345] + [official-doc free-trial-expiry]",
    },
    "billing-method-difference": {
        "q": "What is the difference between subscription and pay-as-you-go?",
        "a": "Subscription = pre-paid fixed term, cheaper unit price, lifecycle driven by the expiry date. Pay-as-you-go = post-paid "
             "hourly billing, released anytime, needs a funded balance. Both modes share the same instance features; the disk, "
             "snapshot and traffic billing items may remain pay-as-you-go either way. Full current wording lives in the official "
             "billing-overview and best-practices documents cited in this advisory.",
        "source": "[official-doc billing-overview / billing-best-practices]",
    },
    "arrears-blocks-conversion": {
        "q": "Why can't I see the 'convert to subscription' entry?",
        "a": "The most common cause in this tier's tickets is an overdue balance hiding the entry; the instance status or a financial "
             "lock is the visible signal (this advisory surfaces OperationLocks from the read-only query). The customer tops up in "
             "the Billing Center first, then the entry reappears.",
        "source": "[ticket-summary T-AABC1FF1]",
    },
    "conversion-data-safety": {
        "q": "Will switching the billing method delete or interrupt my server?",
        "a": "The switch itself does not touch the data or interrupt the service (support statement in a ticket of this tier). The "
             "risk sits AFTER the switch: pay-as-you-go instances in arrears can be auto-released with unrecoverable data, so back up "
             "with snapshots first.",
        "source": "[ticket-summary T-AABC1FF1 / T-381ADD6C]",
    },
    "refund-destination": {
        "q": "Where does the money go after converting to pay-as-you-go or unsubscribing?",
        "a": "Verified rules: default is back to the original payment channel; if the refund amount exceeds the account's current "
             "invoiceable amount it goes to the account balance instead; a successful refund usually lands within about 2 working "
             "days; the invoiceable quota is reduced; vouchers/gifts attached to the order are voided. The exact figure is shown on "
             "the refund page at submission time only.",
        "source": "[verified-dialog T-3CA25349 / T-263837C7]",
    },
    "payg-opening-balance": {
        "q": "How much balance do I need to open pay-as-you-go?",
        "a": "The combined account balance and vouchers must be at least 100 CNY when opening pay-as-you-go ECS. Recharges and "
             "balance checks are customer actions in the Billing Center.",
        "source": "[verified-dialog T-3CA25349]",
    },
    "invoice-timing": {
        "q": "When can I invoice pay-as-you-go charges?",
        "a": "A month's consumption can be invoiced after the 3rd day of the following month, from the Billing Center.",
        "source": "[verified-dialog T-3CA25349]",
    },
    "expiry-release-timeline": {
        "q": "What happens when a subscription instance expires?",
        "a": "Manual release becomes possible from 00:00 the day after the expiry timestamp; if nothing is done the instance is "
             "auto-deleted 15 days after expiry and the data is unrecoverable. Renew instead via the console renewal entry.",
        "source": "[verified-dialog T-263837C7]",
    },
}
