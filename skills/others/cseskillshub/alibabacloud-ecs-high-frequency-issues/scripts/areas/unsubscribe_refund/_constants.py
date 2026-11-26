#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Unsubscribe & Refund Guide
========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (endpoints, query limits, the unsubscription/refund
rule corpus distilled from real support tickets, the mandatory risk notice and
the confirmation-checklist template) is embedded here as Python constants.
There are NO data files in scripts/.
"""

# ---------------------------------------------------------------------------
# OpenAPI endpoints / versions / limits
# ---------------------------------------------------------------------------

# Central BSS OpenAPI endpoint (region-less billing service).
BSS_ENDPOINT = "business.aliyuncs.com"
# Central STS endpoint (region-less).
STS_ENDPOINT = "sts.aliyuncs.com"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "bssopenapi": "2017-12-14",
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# Single per-call timeout for every CLI invocation (MUST 7.6.1).
DEFAULT_TIMEOUT = 60

# BSS DescribeInstanceBill page size (API maximum for MaxResults is 300).
MAX_RESULTS = 300
# PageNum/PageSize style pagination (QueryAvailableInstances /
# QueryInstanceBill / ecs DescribeInstances).
PAGE_SIZE = 50
ECS_PAGE_SIZE = 100
# Hard guardrail on the number of pages fetched per pagination loop.
MAX_PAGES = 20

# BSS product code of ECS (lowercase; used as the ProductCode filter).
ECS_PRODUCT_CODE = "ecs"

# Regions scanned by default when the user gives no region (mainland China
# regions that carry the overwhelming majority of subscription ECS
# instances, plus Hong Kong). Narrowed with --region; every auto-swept
# region is declared in the report.
DEFAULT_SCAN_REGIONS = [
    "cn-hangzhou",
    "cn-shanghai",
    "cn-beijing",
    "cn-zhangjiakou",
    "cn-huhehaote",
    "cn-wulanchabu",
    "cn-shenzhen",
    "cn-heyuan",
    "cn-guangzhou",
    "cn-chengdu",
    "cn-hongkong",
]

# ---------------------------------------------------------------------------
# Manual self-service entries (verbatim URLs referenced by support agents in
# the analyzed tickets; the skill NEVER submits anything on these pages --
# it only outputs the link plus the risk notice).
# ---------------------------------------------------------------------------
MANUAL_ENTRIES = {
    "self_refund": "https://usercenter2.aliyun.com/refund/refund",
    "refund_center": "https://billing-cost.console.aliyun.com/refund/refund",
    "order_list": "https://billing-cost.console.aliyun.com/order/list",
    "invoice_records": "https://billing-cost.console.aliyun.com/invoice/home/record/aliyun",
    "ecs_release_console": "https://ecs.console.aliyun.com/server/region",
}

# Official rule documents. The cancel-subscription page was verified live
# (HTTP 200) during development and is the current canonical target of the
# legacy document_detail/116043 citation seen in tickets; the two remaining
# URLs are verbatim citations from support-agent replies in the analyzed
# tickets and must be relayed with that provenance.
OFFICIAL_DOCS = {
    "unsubscription_rules": "https://help.aliyun.com/zh/user-center/cancel-subscription/",
    "unsubscription_rules_legacy": "https://help.aliyun.com/document_detail/116043.html",
    "ecs_refund_instructions": "https://help.aliyun.com/zh/ecs/refund-instructions",
    "refund_destinations": "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations",
    "release_an_instance": "https://help.aliyun.com/zh/ecs/user-guide/release-an-instance",
    # `rds_savings_plan_faq` was removed: it is an RDS deduction-rules page that
    # says nothing about unsubscribing or refunding, and `spn-` plans belong to
    # Billing and Cost Management, not RDS. Keeping it here invites re-citing a
    # live page that does not support the claim. See decision D22.
}

# ---------------------------------------------------------------------------
# Refund / unsubscription rule corpus (capability CL-C).
# Every entry carries `source`:
#   "official-doc"     -- rule stated on an Alibaba Cloud help page (URL in
#                         `refs`), fetched-and-confirmed reachable at skill
#                         build time;
#   "ticket-statement" -- wording verified only from support-agent replies in
#                         the analyzed tickets (no authoritative doc located;
#                         relayed honestly as the support-team position).
# ---------------------------------------------------------------------------
RULE_TOPICS = {
    "five-day-no-reason": {
        "question": "What is the five-day no-reason refund, and who qualifies?",
        "answer": (
            "Newly purchased subscription (prepaid) ECS instances that meet "
            "the five-day no-reason window can be self-serviced for a full "
            "refund from the refund center. Eligibility of each instance is "
            "shown on the refund page itself -- the API layer cannot be used "
            "to declare the final verdict. The support workflow in practice: "
            "verify the instance belongs to the current account, check it "
            "within the window, then send the self-service refund entry plus "
            "the five-point notice."
        ),
        "source": "official-doc",
        "refs": ["unsubscription_rules", "unsubscription_rules_legacy"],
    },
    "annual-one-instance-limit": {
        "question": "Is the five-day no-reason refund limited per year?",
        "answer": (
            "Yes, and the quota is smaller than most customers expect. "
            "Official wording: each user, for each product, may request the "
            "five-day no-reason full refund on ONE instance per natural year "
            "(January 1 to December 31). In that scenario a subscription ECS "
            "instance shares the one-per-year quota with resource packages and "
            "reserved instance coupons, so spending the quota on one of them "
            "consumes it for the ECS instance too. This account-level usage "
            "count has NO query API: state the rule, and let the refund page "
            "be the final checker."
        ),
        "source": "official-doc",
        "refs": ["ecs_refund_instructions"],
    },
    "refund-timing": {
        "question": "How long does a refund take to arrive?",
        # Range, not a single number: two official pages disagree. The refund
        # destination page says "about 2 business days" (three times in one
        # page) while the ECS refund instructions say "2-3 business days". Picking
        # the lower bound creates a complaint on day 3, so the answer keeps the
        # range and hands the authoritative check to the refund order page and
        # the income/expense details. See decisions D1 and D18.
        "answer": (
            "Refunds generally return within about 2-3 business days along the "
            "original payment path, or fall back to the account balance "
            "depending on the invoiced-amount branch below. Official pages state "
            "this window differently (about 2 business days on the refund "
            "destination page, 2-3 business days in the ECS refund "
            "instructions), so do not promise a single day count: the arrival "
            "time and destination shown on the refund order page and in the "
            "income/expense details are authoritative."
        ),
        "source": "official-doc",
        "refs": ["refund_destinations", "ecs_refund_instructions"],
    },
    "refund-destination-branch": {
        "question": "Where does the refund money go -- original payment path or account balance?",
        "answer": (
            "For orders whose invoice has already been issued, the refund "
            "path depends on the account's invoiceable amount: if the refund "
            "amount is NOT greater than (current invoiceable amount + this "
            "month's non-invoiceable amount), the money prefers the original "
            "payment path; if it is greater, the money goes directly to the "
            "Alibaba Cloud account balance. The invoiceable-amount figures "
            "have NO query API in this skill's whitelist: relay the branch "
            "rule and the refund page as the authority."
        ),
        # The branch rule and both thresholds are stated verbatim on the cited
        # official page; labelling this a support position understated evidence
        # the answer was already carrying. See decisions D22 and the P0 audit.
        "source": "official-doc",
        "refs": ["refund_destinations"],
    },
    "gift-vouchers-void": {
        "question": "What happens to vouchers and free gifts after a refund?",
        "answer": (
            "After a refund, gifts attached to the order (cash vouchers, "
            "coupons, extended service periods) are voided and cleared. For "
            "the voucher-paid portion only the residual value is refundable; "
            "if a voucher had already expired, it cannot be reused after the "
            "unsubscription. The inventory of currently effective coupons can "
            "be listed with QueryCashCoupons (mode --estimate)."
        ),
        "source": "ticket-statement",
        "refs": [],
    },
    "retention-after-refund": {
        "question": "What happens to the instance and its data after the refund completes?",
        "answer": (
            "A refunded subscription instance enters the 'expired after refund' "
            "state, and the retention period is per resource, not one single "
            "window. Official wording: vCPU, memory and the fixed public IP are "
            "released within 24 HOURS of the refund; cloud disks are released "
            "within 15 DAYS of the refund. If the 'release disk with instance' "
            "switch is turned off, the disks are detached and KEPT when the "
            "instance is released. So the compute resources and the fixed public "
            "IP go first, the disks follow, and data survives only while its "
            "disk exists: take a snapshot before submitting, and treat anything "
            "still on the instance after the 24-hour mark as already fragile. "
            "An unsubscription made by mistake can sometimes be undone: the "
            "official advice is to go to the ECS console and renew the "
            "unsubscribed instance manually as soon as possible, BEFORE its "
            "resources are released - after such a recovery the instance may "
            "still have lost data or changed its fixed public IP, so this is a "
            "rescue, not a cancellation of the refund."
        ),
        "source": "official-doc",
        "refs": ["ecs_refund_instructions"],
    },
    "expiry-manual-release": {
        "question": "If I do not unsubscribe before expiry, can I release it later?",
        # The old wording said the instance "is kept for 15 days and then
        # auto-released", which is the coarse form and hides a customer-visible
        # risk: within those 15 days there is a 过期回收中 sub-stage where the
        # local disks are still there but the LOCAL-DISK DATA IS ALREADY CLEARED.
        # A customer who reads "kept for 15 days" as "my data is kept for 15
        # days" can lose local-disk data while still inside the window. The
        # three-stage form below is the official table verbatim. See decision D4.
        "answer": (
            "Yes. Only an instance that is already expired or stopped-after-refund "
            "can be released directly; an unexpired subscription instance must be "
            "unsubscribed first. After expiry the retention is THREE stages, not a "
            "flat 15 days: (1) within 15 days after expiry, state 'expired' -- "
            "compute resources (vCPU/GPU/memory), the local disks AND the local-disk "
            "data are all kept; the instance is stopped but can still be renewed "
            "normally and renewal pushes the expiry date out; (2) within 15 days "
            "after expiry, state 'expiry recycling' -- compute resources are "
            "released and the local disks are kept BUT THE LOCAL-DISK DATA IS "
            "ALREADY CLEARED, so do not treat stage 1 and stage 2 as the same "
            "window; (3) from 00:00 on day 16 -- compute resources are released "
            "and the local disks with their data are released. Cloud disks are "
            "separate: if 'release cloud disk together with the instance' is "
            "turned off, the disk survives as a pay-as-you-go disk and KEEPS "
            "BILLING. This is the normal expiry lifecycle and is NOT the refund "
            "case: after a refund the instance enters the 'expired after refund' "
            "state, where vCPU, memory and the fixed public IP go within 24 hours "
            "and the cloud disks within 15 days (see the retention-after-refund "
            "topic). Refund eligibility and expiry lifecycle are two different "
            "questions."
        ),
        "source": "official-doc",
        "refs": ["release_an_instance"],
    },
    "downgrade-irreversible": {
        "question": "I downgraded the instance and received a partial refund; can I cancel the downgrade?",
        "answer": (
            "No. Once a downgrade (spec-reduction) order is paid and takes "
            "effect it cannot be cancelled or revoked. To restore the "
            "previous configuration, upgrade the instance again and pay the "
            "difference. The downgrade refund itself is computed "
            "automatically by the system from the remaining duration and the "
            "configuration price difference -- the actually credited amount "
            "is authoritative, never a hand-computed figure."
        ),
        "source": "ticket-statement",
        "refs": [],
    },
    "campaign-order-independent": {
        "question": "Can I cancel a campaign-priced order and keep the campaign price on reorder?",
        "answer": (
            "Campaign/combo offers apply per product: separate discounted "
            "products cannot be merged by paying the difference. Whether the "
            "campaign price still applies after cancel-and-reorder has NO "
            "query API -- support agents answered this ad hoc per campaign "
            "terms. This skill must degrade (STATUS: DEGRADED) on the "
            "eligibility question and point to the campaign page / human "
            "support instead of promising a price."
        ),
        "source": "ticket-statement",
        "refs": [],
    },
    "savings-plan-no-unsubscribe": {
        "question": "Can a savings plan (spn-...) be unsubscribed and refunded?",
        "answer": (
            "Savings plans are generally NOT self-service refundable. The "
            "plan itself deducts pay-as-you-go fees of the covered instance; "
            "once the covered instance is released, the plan stops "
            "incurring/offsetting charges for it. Exceptions require manual "
            "commercial approval (the tickets show a special-approval path: "
            "'after special application we can unsubscribe it, the used part "
            "is not refunded'). For an RDS-side plan, hand off to the RDS "
            "product line."
        ),
        "source": "ticket-statement",
        # refs deliberately EMPTY. It used to cite
        # zh/rds/product-overview/faq-about-savings-plans, which is live but does
        # not support this claim: that page is entirely about which RDS billing
        # items an RDS savings plan may deduct, and never mentions unsubscribing
        # or refunding. It is also the wrong product -- `spn-` is a Billing and
        # Cost Management savings plan, not an RDS one. Citing a live page that
        # does not say the thing is worse than citing nothing, because it looks
        # verified. No correct authority has been located yet, so this stays a
        # support position. See decision D22 (WRONG-PRODUCT).
        "refs": [],
    },
    "flexible-plan-no-repurchase": {
        "question": "Any restriction after unsubscribing a flexible (elastic) edition plan?",
        "answer": (
            "Yes -- verified wording: after the flexible-edition refund is "
            "processed, the flexible edition can NOT be purchased again. "
            "Warn the customer before they request such an unsubscription."
        ),
        "source": "ticket-statement",
        "refs": [],
    },
    "stop-vs-release": {
        "question": "Is stopping the instance the same as releasing it (for stopping charges)?",
        "answer": (
            "No. Stopping an instance only shuts it down and stops billing "
            "of the COMPUTE resource in that mode, while the system still "
            "keeps the disks, public IP and image and keeps charging them. "
            "Releasing removes the instance and, with the default 'release "
            "disk with instance' switch, its disks too -- the data on a "
            "released disk is gone unless a snapshot or an image holds it, so "
            "snapshot first. If that switch is turned off, the disks are "
            "detached and kept, and the data survives on the retained disk "
            "(storage charges continue). Releasing is a customer-side manual "
            "console action; this skill only provides the steps and the "
            "console entry."
        ),
        "source": "official-doc",
        "refs": ["release_an_instance", "ecs_refund_instructions"],
    },
    "withdraw-reserve": {
        "question": "Why can my account balance not be withdrawn, and when?",
        "answer": (
            "While pay-as-you-go resources (ECS, SLB, ...) still exist under "
            "the account, the system reserves 100 CNY of the balance against "
            "overdue risk, so a smaller balance cannot be withdrawn. After "
            "releasing all such resources, withdrawal can normally be "
            "applied for 24 hours later. Refunds that land in the balance "
            "also consume the invoiceable amount and can further affect "
            "withdrawal. This support-side wording has no located official "
            "doc; relay it as the support position and point to the billing "
            "console for the actual withdrawal attempt."
        ),
        "source": "ticket-statement",
        "refs": [],
    },
    "apply-not-final": {
        "question": "I already asked support / submitted something -- is the refund done?",
        "answer": (
            "Not necessarily. A refund is only in flight after an actual "
            "unsubscription ORDER exists; verbal/chat requests are not "
            "submissions. Some assisted unsubscriptions additionally require "
            "the customer to click the confirmation tool themselves ('the "
            "product can be unsubscribed only after you confirm in the "
            "confirmation tool'). Verify with the order list page and the "
            "refund center rather than assuming a prior request succeeded."
        ),
        "source": "ticket-statement",
        # refs deliberately EMPTY. It pointed at a key `order_list` that does not
        # exist in OFFICIAL_DOCS, so the renderer silently dropped it and the
        # customer saw "no located official page" while the author believed a
        # reference existed. The order list is a CONSOLE page, not a help
        # document: console URLs cannot be liveness-checked unauthenticated (they
        # all answer 200 then redirect to login), so they are not valid doc refs
        # here. The answer text already names the order list page and the refund
        # center as the checks to run. See decisions D10-2 and D22 (DANGLING-REF).
        "refs": [],
    },
}

# ---------------------------------------------------------------------------
# Mandatory five-point notice relayed before any self-service refund
# (verbatim rule content from the ticket scripts, translated; capability CL-A
# step R2 -- MUST be output in full BEFORE guiding a customer to submit).
# ---------------------------------------------------------------------------
FIVE_POINT_NOTICE = [
    ("Eligibility check",
     "The refundable instances of this account and their eligibility (five-"
     "day no-reason or non-full refund) are listed in the refund center at "
     "submission time; that page is the authority."),
    ("Annual limit",
     "Each user, per product, may use the five-day no-reason refund on one "
     "instance per natural year (Jan 1 - Dec 31); a subscription ECS instance "
     "shares that one-per-year quota with resource packages and reserved "
     "instance coupons."),
    ("Timing and destination",
     "Refunds normally return within about 2 business days. If the refund "
     "amount exceeds the current invoiceable amount, the money returns "
     "directly to the Alibaba Cloud account balance; otherwise the original "
     "payment path is preferred."),
    ("Gifts voided and retention is per resource",
     "After a refund, attached gifts (cash vouchers, coupons, extended "
     "service periods) are voided and cleared. The instance itself enters the "
     "'expired after refund' state: vCPU, memory and the fixed public IP are "
     "released within 24 hours, the cloud disks within 15 days (a disk is "
     "kept if 'release disk with instance' is off). Snapshot first; before the "
     "resources are released, renewing the unsubscribed instance manually in "
     "the ECS console can still rescue it, although data loss or a changed "
     "fixed public IP may remain."),
    ("Amount and rules",
     "The refund page shows the exact refundable amount -- confirm it before "
     "submitting. Full rules: " + OFFICIAL_DOCS["unsubscription_rules"]),
]

# ---------------------------------------------------------------------------
# Six-item per-line confirmation template (capability CL-F; structure reused
# from the closed-loop ticket script, generalized). The customer must confirm
# each line before any assisted/manual unsubscription is requested.
# ---------------------------------------------------------------------------
SIX_ITEM_CONFIRMATION = [
    "Refund reason (one line, factual).",
    "Target resource: instance ID(s) and the related order number(s) "
    "(order numbers are relayed masked, e.g. 20**...**85).",
    "Voucher rule: the voucher-paid portion only refunds the residual "
    "value; an expired voucher cannot be reused after unsubscription.",
    "Billing after release: instances currently covered by this "
    "resource revert to normal pay-as-you-go billing once the covering "
    "subscription is released.",
    "Refund amount: confirmed as the exact figure shown on the refund "
    "page (this skill never states a final amount).",
    "Repurchase limits: edition-level limits acknowledged (e.g. a "
    "flexible-edition plan cannot be re-purchased after refund).",
]

# ---------------------------------------------------------------------------
# Resource-ID prefix triage (capability CL-E).
# ---------------------------------------------------------------------------
ID_PREFIX_TRIAGE = {
    "i-": {
        "kind": "ECS instance",
        "route": "Standard refund flow: --inventory for eligibility "
                 "listing, --estimate for reference amounts, then the "
                 "self-service refund entry plus the five-point notice.",
    },
    "spn-": {
        "kind": "Savings plan",
        "route": "Not self-service refundable: explain rules "
                 "(--rules savings-plan-no-unsubscribe), check whether the "
                 "covered instance is already released (no further "
                 "deduction/charges), and point to a manual ticket for the "
                 "special-approval path. Never promise an approval.",
    },
    "rm-": {
        "kind": "RDS instance",
        "route": "Cross-product handoff: commercial actions on RDS (or any "
                 "non-ECS product) go to that product line's ticket queue. "
                 "This skill only explains the ECS-side linkage.",
    },
}

# ---------------------------------------------------------------------------
# Adjacent-skill handoff table (scope boundary).
# ---------------------------------------------------------------------------
HANDOFF_SKILLS = {
    "renewal price or campaign discount path": "area:renewal-pricing-discount",
    "why a charge occurred / bill reconciliation": "area:billing-attribution-bill-check",
    "expiry and auto-release lifecycle questions": "area:expiry-release-retention",
    "overdue suspension / free-trial expiry stop-billing": "area:arrears-trial-billing-stop",
    "charge-type conversion (subscription <-> pay-as-you-go)": "billing mode selection in the account-and-service-process extension package",
    "spec-change / upgrade purchase feasibility": "area:instance-modify-diagnosis",
}
