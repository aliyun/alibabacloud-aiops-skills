#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Renewal Pricing & Discount Diagnosis
==================================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (endpoints, API versions, query limits, the
price-mismatch attribution tree B1-B11, billing-scope glossary, customer
page-string patterns, handoff templates and risk notices) is embedded here as
Python constants. The readable long-form versions live under references/.
"""

# ---------------------------------------------------------------------------
# Skill identity & observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-renewal-pricing-discount"

# ---------------------------------------------------------------------------
# OpenAPI metadata (verified against the api-info surface of this tier)
# ---------------------------------------------------------------------------

# Central BSS (billing) OpenAPI endpoint (region-less billing service).
BSS_ENDPOINT = "business.aliyuncs.com"
# Central STS endpoint (region-less).
STS_ENDPOINT = "sts.aliyuncs.com"

API_VERSIONS = {
    "bssopenapi": "2017-12-14",
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# ECS product code used for BSS pricing/renewal queries on subscription ECS.
ECS_PRODUCT_CODE = "ecs"
ECS_SUBSCRIPTION_TYPE = "Subscription"

# ---------------------------------------------------------------------------
# Timeouts / pagination guardrails
# ---------------------------------------------------------------------------

# Per-call subprocess timeout (MUST 7.6.1).
DEFAULT_TIMEOUT = 60

# Page sizes.
ECS_PAGE_SIZE = 100          # DescribeInstances PageSize (ECS max 100)
BSS_PAGE_SIZE = 50           # QueryAvailableInstances PageSize
MAX_PAGES = 20               # hard guardrail per pagination loop

# BSS SubscriptionType enum values accepted by the pricing APIs (public
# contract of bssopenapi): Subscription (prepaid) or PayAsYouGo.
BSS_SUBSCRIPTION_TYPES = {"Subscription", "PayAsYouGo"}

# ---------------------------------------------------------------------------
# Mandatory disclaimer attached to EVERY amount this skill outputs.
# Mirrors the human-agent line "the console real-time price prevails" seen in
# real tickets; the trial price is a list-price composition only.
# ---------------------------------------------------------------------------

PRICE_DISCLAIMER = (
    "List-price trial only: account-specific discounts, vouchers, negotiated "
    "commercial terms and activity eligibility are NOT reflected. The final "
    "payable amount is the real-time price shown on the ECS purchase page / "
    "console checkout. This skill never states what the customer must pay."
)

# ---------------------------------------------------------------------------
# Expiry-window thresholds (days) for the renewal risk list.
# ---------------------------------------------------------------------------
EXPIRY_URGENT_DAYS = 7
EXPIRY_WARNING_DAYS = 30

# ---------------------------------------------------------------------------
# Price-mismatch attribution tree (branches B1-B11).
#
# Each branch: trigger keyword phrases (lower-case, matched against the
# customer's own wording or a quoted console page string), the evidence-based
# attribution statement, the manual guidance this skill outputs, and the
# reference file carrying the full playbook text. Root causes distilled from
# real support-ticket dialogues; see references/renewal-pricing-discount__price-mismatch-playbook.md.
# ---------------------------------------------------------------------------

MISMATCH_BRANCHES = [
    {
        "id": "B1",
        "name": "Discount tier follows the remaining subscription duration",
        "keywords": [
            "price changed", "price change", "price rose",
            "price is higher than", "more expensive than last",
            "upgrade price different", "was cheaper", "cheaper before",
            "changed in two days", "discount tier", "5.5", "6.5",
            "two years", "remaining duration", "renew first",
        ],
        "attribution": (
            "Long-term discount tiers are matched against the instance's "
            "REMAINING subscription duration at the moment of the order. "
            "Crossing a whole-year threshold (e.g. falling below 2 years to "
            "go from the 2-year tier to the 1-year tier) silently lowers the "
            "tier, so the same upgrade quotes higher a few days later. The "
            "console already shows the best price for the current remaining "
            "duration; the tier cannot be manually pinned to a better one. "
            "Renewing to extend the validity makes the system re-match the "
            "tier on the new duration, but a single-month renewal order "
            "usually carries no discount."
        ),
        "guidance": (
            "1) Run the inventory mode to read the real ExpiredTime. "
            "2) Demo the tier jump with the quote mode across several "
            "--service-period-quantity values (list-price trial). "
            "3) If a better commercial price is wanted, hand off via the "
            "handoff mode (business channel). Never promise a discount."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b1",
    },
    {
        "id": "B2",
        "name": "Discount permission not refreshed / low-price order voided",
        "keywords": [
            "shows a discount but payment", "discount but checkout",
            "checkout charges", "full price at checkout", "full price at payment",
            "checkout shows original price", "price at checkout", "discount gone",
            "199", "renewal order voided", "voided order",
        ],
        "attribution": (
            "A known system behavior: after a previous (possibly voided) "
            "renewal order, the discount entitlement may not be refreshed "
            "immediately, so the payment page reverts to the original price. "
            "Operators report a refresh window of roughly 2-3 hours - an "
            "empirical figure, NOT a service-level commitment."
        ),
        "guidance": (
            "Standard recovery sequence (ALL steps are performed by the "
            "customer in the console; this skill never operates orders): "
            "1) void the high-priced unpaid renewal order on the order page; "
            "2) wait for the system to refresh the discount entitlement; "
            "3) regenerate the renewal order and check the price before "
            "paying. If the original price persists, fall through to B3."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b2",
    },
    {
        "id": "B3",
        "name": "Activity eligibility mismatch - appeal path",
        "keywords": [
            "activity price", "promotion price", "not eligible",
            "appeal", "qualification", "review rejected", "audit failed",
            "renewal shows 1000", "should have the discount",
        ],
        "attribution": (
            "The account may not satisfy the participation conditions of the "
            "promotional activity (e.g. same-person purchase rules). The "
            "self-service center hosts an eligibility diagnosis + appeal "
            "tool; a reviewer answers within about one business day and the "
            "result is delivered in the ticket/SM message. Front-line support "
            "cannot see or override the review reason; re-submitting the same "
            "blurry material usually does not change the outcome - clearer "
            "evidence is required."
        ),
        "guidance": (
            "Output the appeal path only: self-service-center tool entry, "
            "material requirements (clear, legible proof), and the explicit "
            "statement that this skill cannot predict review outcomes. Use "
            "the handoff mode with --channel appeal."
        ),
        "reference": "references/renewal-pricing-discount__discount-routing.md#appeal",
    },
    {
        "id": "B4",
        "name": "Flash-sale stock sold out - page auto-switches to another offer",
        "keywords": [
            "flash sale", "seckill", "rush price", "38", "68",
            "sold out", "limited time", "grab",
        ],
        "attribution": (
            "Limited-time sale units are per-session and stock-limited. Once "
            "sold out, the entry page automatically displays the next "
            "best offer the account enjoys (e.g. a new-user price), which is "
            "why the displayed price and the checkout price can differ "
            "legitimately. (Sample evidence comes from a Simple Application "
            "Server ticket; the mechanism description is generic.)"
        ),
        "guidance": (
            "Explain the stock mechanism, point to the announced sale "
            "sessions, and state that no stock or price can be reserved or "
            "promised. For non-ECS products, hand off to that product's "
            "channel (see references/renewal-pricing-discount__boundary-handoff.md)."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b4",
    },
    {
        "id": "B5",
        "name": "Activity commodities are independent - no pay-the-difference swap",
        "keywords": [
            "pay the difference", "price difference swap", "change the bundle",
            "combined package", "cancel and reorder", "re-order the activity",
            "different product",
        ],
        "attribution": (
            "Different activity bundles (e.g. a plain instance vs an "
            "instance+database combo) are independent commodities: they "
            "cannot be exchanged by paying the difference. Cancelling the "
            "original unpaid/valid activity order and placing a new one can "
            "still qualify for the activity price, subject to the activity "
            "rules at ordering time. Back up data before any refund-rebuy "
            "cycle."
        ),
        "guidance": (
            "State the commodity-independence rule, point to the order list "
            "page for self-check, and remind that ordering, cancelling and "
            "paying are console actions performed by the customer only."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b5",
    },
    {
        "id": "B6",
        "name": "Billing-method change triggered a new payment",
        "keywords": [
            "asked to pay after", "why pay 700", "payment prompt after change",
            "changed billing method", "switched to pay-as-you-go",
            "temporary upgrade", "conversion re-payment", "per gb",
        ],
        "attribution": (
            "What the customer believed was a 'temporary upgrade' may have "
            "been a subscription-to-pay-as-you-go billing-method conversion, "
            "which requires a fresh payment. Bandwidth billed by traffic "
            "charges outbound internet traffic (publicly documented "
            "reference rate 0.8 CNY/GB; inbound is not charged), which also "
            "produces surprise payment prompts."
        ),
        "guidance": (
            "Read the instance's current InstanceChargeType and "
            "InternetChargeType via the inventory mode, explain which change "
            "requires payment, and cite the public-bandwidth billing doc. "
            "Traffic-ANOMALY forensics (who used the traffic) is out of "
            "scope - hand off per references/renewal-pricing-discount__boundary-handoff.md."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b6",
    },
    {
        "id": "B7",
        "name": "Downgrade/unsubscribe refund computes to 0 (or far below expectation)",
        "keywords": [
            "refund is 0", "refund shows 0", "refund 0 yuan", "shows zero",
            "nothing to refund", "downgrade refund", "unsubscribe refund",
            "unsubscription request submission failed", "submission failed",
            "proportional refund", "refund by remaining days",
        ],
        "attribution": (
            "Refunds are computed by the system, not by staff: downgrade "
            "refund = remaining cost of the old spec - purchase cost of the "
            "new spec, with the consumed amount re-priced at ORIGINAL list "
            "price and discount rules; usage under 30 days may apply a 1.5 "
            "factor. For non-full unsubscription the used period is also "
            "converted at original price - so an item bought deep on "
            "discount can refund to 0 CNY. Converting fixed bandwidth to "
            "traffic billing can likewise refund 0 when discounts applied."
        ),
        "guidance": (
            "Output the formula narrative PLUS the mandatory risk notices "
            "(references/renewal-pricing-discount__refund-downgrade-risks.md) and the console entries "
            "(order management page; the checkout 'expected refund' figure). "
            "NEVER hand-compute a refund figure and never submit unsubscriptions."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b7",
    },
    {
        "id": "B8",
        "name": "Upgrade top-up costs more than buying the same spec new",
        "keywords": [
            "upgrade costs more than new", "more than a new purchase",
            "price inversion", "top-up higher", "difference is higher",
            "buy new instead",
        ],
        "attribution": (
            "Typical causes: the original order carried account/activity "
            "discounts whose residual value differs from the current new-"
            "purchase promotions, or a configuration mismatch between the "
            "two compared prices. Evidence strength: this branch rests on a "
            "phone-summary only (dialogue not verifiable), so it is output "
            "as a candidate cause list, not a conclusion."
        ),
        "guidance": (
            "Run the quote mode for both paths (upgrade order vs renewal/"
            "new-purchase composition) as list-price trials, compare item "
            "by item, and remind that refund-rebuy means data-migration and "
            "asset-loss risk decisions belong to the customer. The exact paid "
            "amount always comes from the console checkout page."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b8",
    },
    {
        "id": "B9",
        "name": "Independent billing items confused with each other",
        "keywords": [
            "already paid why", "paid but stopped", "paid but still charged",
            "domain renewal", "separate charge", "extra charge",
            "why another payment", "different item",
        ],
        "attribution": (
            "Renewal/billing objects are independent: a domain renewal does "
            "not renew an ECS instance; EIP carries its own data + "
            "configuration fees; Cloud Security Center pay-as-you-go items "
            "accrue separately; ECS snapshot storage bills independently of "
            "the instance. A payment the customer associates with the "
            "instance may belong to another commodity entirely."
        ),
        "guidance": (
            "Use the inventory + expiring modes to list which resources are "
            "actually expiring/overdue in this account, then name the "
            "specific item. Guide the order list page for payment matching. "
            "Snapshot mechanics and domain handling are hand-offs."
        ),
        "reference": "references/renewal-pricing-discount__pricing-glossary.md#independent-items",
    },
    {
        "id": "B10",
        "name": "A remaining-term pro-rata figure misread as a whole-cycle fee",
        "keywords": [
            "is this monthly", "whole month", "per remaining",
            "207", "less than expected", "why so small", "remaining validity",
            "difference price",
        ],
        "attribution": (
            "Console amounts next to an upgrade/expansion often cover only "
            "the REMAINING validity period (a pro-rata difference to the end "
            "of the subscription), not a whole month/year; the final renewal "
            "price is additionally shaped by discounts and vouchers. "
            "(Evidence from a phone call summary; weakly verified.)"
        ),
        "guidance": (
            "Explain the pro-rata semantics, then point to the purchase or "
            "expansion page real-time quote for both the current remainder "
            "and a full cycle. Never assert what the number 'means' beyond "
            "the page label."
        ),
        "reference": "references/renewal-pricing-discount__price-mismatch-playbook.md#b10",
    },
    {
        "id": "B11",
        "name": "Changing configuration can forfeit long-term low-price activity renewals",
        "keywords": [
            "99 plan", "low price activity", "lose the discount after upgrade",
            "renewal no longer 99", "changed config and lost", "activity renewal price",
        ],
        "attribution": (
            "Participating in a long-term low-price activity (e.g. the "
            "99 CNY/year program) can be invalidated for FUTURE renewals "
            "once the instance configuration is changed - a rule the "
            "console does not shout before the change. The change itself is "
            "irreversible regarding the activity entitlement in many cases."
        ),
        "guidance": (
            "Pre-change risk notice FIRST: warn that a configuration change "
            "may forfeit the activity renewal price, and advise reading the "
            "activity terms. The change and its checkout price are executed "
            "and verified by the customer in the console or through the equivalent OpenAPI."
        ),
        "reference": "references/renewal-pricing-discount__refund-downgrade-risks.md#activity-forfeit",
    },
]

# ---------------------------------------------------------------------------
# Customer-visible page strings (from ticket dialogues). Used only for
# matching/explanation; no API-side error-code table was injected for this
# tier, so none is invented.
# ---------------------------------------------------------------------------

PAGE_STRINGS = {
    "unsubscription_submit_failed": (
        "unknown exception, unsubscription request submission failed, "
        "please contact customer service"
    ),
    "checkout_reverts_to_original": (
        "the renewal page shows a discounted price but the payment page "
        "shows the original price"
    ),
    "renewal_above_expectation": "renewal shows around 1000 CNY",
    "flash_sale_price_switch": (
        "front page shows 38 CNY but the checkout page shows 68 CNY"
    ),
    "downgrade_order_not_applied": (
        "the downgrade order is paid but the instance still shows the old "
        "bandwidth / public IP"
    ),
}

# ---------------------------------------------------------------------------
# Mandatory pre-output risk notices (from the ticket record; output BEFORE
# any manual guidance about downgrade/refund/conversion).
# ---------------------------------------------------------------------------

RISK_NOTICES = [
    "Downgrading configuration stops the instance and interrupts business; "
    "the operation is irreversible and may cause asset loss.",
    "With purchase discounts applied, a downgrade or unsubscription refund "
    "can compute to 0 CNY.",
    "Changing configuration of an instance bought through a long-term "
    "low-price activity (e.g. 99 CNY/year) may forfeit the discounted "
    "renewal price.",
    "On refund the instance data is cleared immediately, vouchers/coupons "
    "are not returned, promotional gifts are voided, and auto-snapshot-"
    "on-disk-release policies can delete snapshots together with disks.",
    "A refund confirmation link has a short validity (about 3 days reported) "
    "and the refundable amount decreases the later it is exercised.",
    "Converting a fixed public IP to an EIP is one-way (cannot convert "
    "back); EIP carries extra configuration fees.",
    "Downgrade requires stopping the instance; schedule in an off-peak window.",
]

# ---------------------------------------------------------------------------
# Handoff information-package templates (channel-based routing).
# ---------------------------------------------------------------------------

HANDOFF_CHANNELS = {
    "business": {
        "when": (
            "Discount approval, negotiated quotes, waivers, itemized cost "
            "statements, channel/partner issues."
        ),
        "boundary_line": (
            "After-sales technical support has no discount-approval or "
            "quoting authority; commercial terms are handled by the account "
            "business manager."
        ),
        "fields": [
            "Account UID (from sts_token.py; never guessed)",
            "Instance ID(s) and region",
            "Instance type, data disks, bandwidth (from inventory mode)",
            "Expiration time and auto-renewal state (from inventory mode)",
            "Request type: discount / quote / waiver / cost breakdown",
            "Expected outcome stated by the customer",
            "Paths already attempted by the customer",
            "Contact details: supplied BY THE CUSTOMER to the business "
            "channel directly - this skill never collects them",
        ],
    },
    "appeal": {
        "when": "Activity eligibility doubts (branch B3).",
        "boundary_line": (
            "Eligibility review is performed by a dedicated team; support "
            "cannot see or alter the review reason."
        ),
        "fields": [
            "Activity name / order page price claimed",
            "Instance ID, region, account UID",
            "Materials: clear, legible, matching the listed requirements",
            "Reminder: do not re-submit the same rejected material",
            "No outcome may be predicted or promised",
        ],
    },
    "console": {
        "when": "Self-service facts: orders, real-time prices, unsubscriptions.",
        "boundary_line": "Data and prices below are authoritative pages.",
        "fields": [
            "Purchase page (real-time quotes): ecs.console.aliyun.com "
            "-> create instance / renew / upgrade wizards",
            "Order management: billing-cost.console.aliyun.com/order/list",
            "Renewal list / unsubscription of not-yet-effective renewals: "
            "billing-cost.console.aliyun.com/refund/renew-list",
            "Bill detail by instance: expense center console",
        ],
    },
    "other-skill": {
        "when": "Out-of-scope symptoms identified (see boundary-handoff map).",
        "boundary_line": (
            "Symptom identified as outside the renewal-pricing area; "
            "handing off."
        ),
        "fields": [
            "Disk expansion and post-expand partition/filesystem steps -> "
            "area:disk-expand-diagnosis",
            "Instance will not start / recovery after expiry stop -> "
            "area:instance-state-diagnosis",
            "Configuration-change EXECUTION, EIP conversion steps -> "
            "change-spec skills + human console operation",
            "Traffic-source forensics for cost spikes -> cost-anomaly "
            "troubleshooting channel",
            "Snapshot mechanics and snapshot billing -> snapshot/backup "
            "skill",
            "Invoices / contracts / corporate payment -> finance channel",
            "Resource-package / savings-plan deduction -> cost-optimization "
            "channel",
            "Non-ECS products (Simple Application Server, Cloud Web "
            "Hosting, RDS, domains) -> that product's channel",
        ],
    },
}

# ---------------------------------------------------------------------------
# Glossary of pricing terms (compact; full text in
# references/renewal-pricing-discount__pricing-glossary.md).
# ---------------------------------------------------------------------------

GLOSSARY = {
    "list-price": "Catalog price composed from billing modules (instance "
                  "type, disks, bandwidth); before account-specific terms.",
    "discount-tier": "Duration- or activity-bound discount matched "
                     "automatically on order time.",
    "pro-rata-difference": "Charge covering only the remaining validity "
                           "until the current subscription expiry, not a "
                           "full cycle.",
    "non-full-unsubscription": "Unsubscription whose used period is "
                               "re-priced at original price, often leaving "
                               "a small or 0 refund.",
    "downgrade-refund-formula": "remaining cost of old spec - purchase cost "
                                "of new spec; consumed part re-priced at "
                                "original price; under 30 days may apply a "
                                "1.5 factor.",
    "by-bandwidth-vs-by-traffic": "Fixed bandwidth caps peak and bills a "
                                  "flat fee; traffic billing charges "
                                  "outbound GB (reference 0.8 CNY/GB, "
                                  "inbound free).",
    "activity-commodity": "Promotional bundles are separate commodities; "
                          "no difference-payment swaps between them.",
}

# ---------------------------------------------------------------------------
# Offline self-test: attribution routing must be deterministic and never
# raise on empty/garbage input (pure-function boundary assertions).
# ---------------------------------------------------------------------------

def _self_test_branch_match(text):
    """Return branch ids whose keywords appear (case-insensitive) in text."""
    low = (text or "").lower()
    hits = []
    for branch in MISMATCH_BRANCHES:
        for kw in branch["keywords"]:
            if kw.lower() in low:
                hits.append(branch["id"])
                break
    return hits


# Runs at import; a failure here means the routing table is broken.
assert _self_test_branch_match("") == []
# Regression: every phrase advertised in the SKILL.md description MUST route
# to its expected branch.
assert "B1" in _self_test_branch_match(
    "renewal price is higher than last time")
assert "B2" in _self_test_branch_match(
    "renewal page shows a discount but checkout charges full price")
assert "B1" in _self_test_branch_match("upgrade price changed in two days")
assert "B7" in _self_test_branch_match("downgrade refund shows 0")
assert "B7" in _self_test_branch_match(
    "unsubscription request submission failed, contact customer service")
assert "B11" in _self_test_branch_match("99 plan renewal discount")
assert "B7" in _self_test_branch_match(
    "my downgrade refund shows 0 yuan, I expected a proportional refund")
assert "B2" in _self_test_branch_match(
    "renewal page shows a discount but payment page shows the full price 199")
assert "B11" in _self_test_branch_match(
    "will I lose the 99 plan renewal discount")
assert all(set(b) >= {"id", "name", "keywords", "attribution", "guidance",
                      "reference"} for b in MISMATCH_BRANCHES)
