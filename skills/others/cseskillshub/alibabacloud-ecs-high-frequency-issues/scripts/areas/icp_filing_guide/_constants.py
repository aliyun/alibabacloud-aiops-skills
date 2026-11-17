#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and read-only knowledge for the ECS ICP
filing guide skill
===========================================================================
SECURITY: This skill is strictly READ-ONLY. This module holds no credentials
and performs no I/O: authentication is resolved exclusively by the aliyun CLI
default credential chain (never by anything in this file).

Per platform rule MUST 1.1.2, scripts/ may contain executable code only, so
every piece of static reference data (API metadata, region scan list,
eligibility rule model, filing knowledge distilled from real support tickets,
escalation routing) is embedded here as Python constants. There are no data
files in this skill.

EVIDENCE DISCIPLINE: every entry of ICP_FILING_KNOWLEDGE carries the support
ticket identifiers it was distilled from and a confidence flag. Entries marked
"summary-only" come from a ticket summary whose customer-support transcript
could not be re-read, so the script prints them with an explicit
"verify with a filing specialist" caveat instead of presenting them as
authoritative policy.
"""

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-icp-filing-guide"

# Central, region-less endpoints. ECS and VPC are regional: the CLI resolves
# the regional endpoint from --region, so no endpoint is pinned for them.
STS_ENDPOINT = "sts.aliyuncs.com"

# API versions actually called (the aliyun CLI carries its own metadata; these
# values are for report transparency and for related_apis.yaml alignment).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "vpc": "2016-04-28",
    "sts": "2015-04-01",
}

# Read-only API whitelist. Anything outside this set must never be called.
API_WHITELIST = {
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeSecurityGroups"),
    ("ecs", "DescribeSecurityGroupAttribute"),
    ("vpc", "DescribeEipAddresses"),
    ("sts", "GetCallerIdentity"),
}

# ---------------------------------------------------------------------------
# Limits and timeouts
# ---------------------------------------------------------------------------

# Per-call timeout for every aliyun CLI subprocess invocation (MUST 7.6.1).
DEFAULT_TIMEOUT = 60

# Page sizes and hard pagination guardrails.
PAGE_SIZE = 50
MAX_PAGES = 20
MAX_SG_RULES = 1000

# Cap on the number of regions one eligibility scan may visit, so a
# full-account sweep cannot fan out without bound.
MAX_REGION_SCAN = 20

# Cap on the number of security groups inspected in one access triage.
MAX_SECURITY_GROUPS_CHECKED = 10

# ---------------------------------------------------------------------------
# Chinese mainland regions (eligibility criterion 1 scan targets)
# ---------------------------------------------------------------------------
# These identifiers are used for ONE purpose only: as scan targets for the
# account-wide "which instance can carry a filing service code" sweep, because
# the filing rule requires the server to sit in a Chinese mainland node.
# They are NOT an assertion about every region Alibaba Cloud operates, and the
# eligibility verdict for a specific instance always reads the RegionId the
# API actually returned. Override with --regions when the customer's instance
# lives somewhere else.
#
# cn-hongkong is deliberately absent: it is not a mainland node for filing
# purposes, so an instance there never satisfies criterion 1.
MAINLAND_REGIONS = (
    "cn-qingdao",
    "cn-beijing",
    "cn-zhangjiakou",
    "cn-huhehaote",
    "cn-wulanchabu",
    "cn-hangzhou",
    "cn-shanghai",
    "cn-shenzhen",
    "cn-heyuan",
    "cn-guangzhou",
    "cn-chengdu",
    "cn-nanjing",
    "cn-fuzhou",
    "cn-wuhan-lr",
)

# Subscription length required for a filing-capable server, in months.
# OFFICIAL RULE (备案服务器检查, see SUBSCRIPTION_TERM_DOC): the billing method
# must be subscription and the PURCHASED length must be longer than 3 months,
# cumulative renewals included. The rule is explicitly independent of how long
# the server has been used and of the term still remaining.
MIN_SUBSCRIPTION_MONTHS = 3

# Official wording of the subscription-term condition. The Chinese sentence is
# the verbatim source; the English line is what the report prints.
SUBSCRIPTION_TERM_RULE_ZH = (
    "购买服务器计费方式为包年包月，且购买时长大于3个月（含续费累计），"
    "与服务器使用时间、剩余期限均无关"
)
SUBSCRIPTION_TERM_RULE = (
    "Subscription (pre-paid) billing with a purchased length longer than "
    f"{MIN_SUBSCRIPTION_MONTHS} months, cumulative renewals included. The rule "
    "is unrelated to how long the server has been in use and unrelated to the "
    "term remaining."
)
SUBSCRIPTION_TERM_EXCLUSIONS = (
    "Pay-as-you-go (PostPaid) servers do not qualify until they are converted "
    "to subscription.",
    "Free-trial ECS servers never satisfy the requirement.",
)
SUBSCRIPTION_TERM_DOC = (
    "https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/"
    "icp-filing-server-access-information-check"
)
# Printed whenever the cumulative purchased length cannot be read from the API.
PURCHASED_TERM_HINT = (
    "Read this instance's cumulative purchased length (original purchase plus "
    "renewals) in the billing center (费用中心); no action in this skill's "
    "read-only whitelist returns renewal history, and the remaining term is not "
    "the criterion."
)

# Expiry sentinel used by the API for instances with no fixed term (a
# pay-as-you-go instance reports an effectively unlimited expiry).
NO_FIXED_TERM_YEAR = 2099

# ---------------------------------------------------------------------------
# Ports that public website traffic needs (access triage)
# ---------------------------------------------------------------------------
WEB_PORTS = (80, 443)

# Customer-visible browser connection-reset symptoms that route to the
# security-group triage path FIRST, never to a filing conclusion.
CONNECTION_RESET_SYMPTOMS = (
    "err_connection_closed",
    "err_connection_reset",
)

# ---------------------------------------------------------------------------
# Filing knowledge distilled from real support tickets
# ---------------------------------------------------------------------------
# confidence:
#   "transcript-verified" -- the support transcript was read and matches
#   "summary-only"        -- only the ticket summary was available (the
#                            transcript pull failed); always caveated
#   "partial-transcript"  -- the transcript was truncated mid-conversation
ICP_FILING_KNOWLEDGE = {
    "filing-server-conditions": {
        "title": "What makes an ECS instance able to carry an ICP filing service code",
        "confidence": "transcript-verified",
        "tickets": ("T-C097A6CB", "T-5A6AABCB"),
        "points": (
            "Three conditions must hold at the same time on the server: it sits "
            "in a Chinese mainland node, its billing method is subscription "
            "(pre-paid) with a PURCHASED length longer than 3 months counted "
            "cumulatively across renewals, and public bandwidth is enabled on "
            "it.",
            "The official wording of the term condition is: 购买服务器计费方式"
            "为包年包月，且购买时长大于3个月（含续费累计），与服务器使用时间、"
            "剩余期限均无关 -- the criterion is the purchased length, not how "
            "long the server has run and not how much term is left.",
            "Two official exclusions: a pay-as-you-go (PostPaid) server only "
            "qualifies after it is converted to subscription, and a free-trial "
            "ECS server never satisfies the requirement.",
            "Buying a paid filing service code does NOT bypass these conditions: "
            "the code has to bind to an instance in the same account that "
            "already meets them. This is the most common reason a customer sees "
            "\"no instance to select\" while binding a code.",
            "After a compliant instance is purchased, the system generates a "
            "free filing service code for it automatically, so a separately "
            "purchased paid code is usually unnecessary and can be refunded.",
            "Filing-side state (how many codes the account holds, whether a "
            "code was already used) cannot be read from the public cloud APIs "
            "used here; the customer checks it in the ICP Filing console.",
        ),
        "docs": (
            "https://help.aliyun.com/knowledge_detail/36891.html",
            "https://help.aliyun.com/zh/icp-filing/basic-icp-service/"
            "user-guide/icp-filing-server-access-information-check",
        ),
    },
    "service-code-binding": {
        "title": "Binding a filing service code when no instance is offered",
        "confidence": "transcript-verified",
        "tickets": ("T-C097A6CB",),
        "points": (
            "The binding list is populated only with instances of the SAME "
            "account that satisfy the three server conditions; an empty list "
            "means no such instance exists yet, not a console defect.",
            "Order of operations for a customer who already paid for a code: "
            "first purchase a compliant mainland subscription instance with "
            "public bandwidth, then bind (or let the automatically generated "
            "free code be used), then submit the filing.",
            "Refunding an unused paid code, and any purchase advice, are "
            "commercial actions: they are handed to a human specialist, never "
            "executed by this skill.",
            "A managed filing service (paid filing concierge) exists as an "
            "alternative for customers who do not want to self-submit.",
        ),
        "docs": (
            "https://gs.aliyun.com/product/butler",
            "https://www.aliyun.com/product/ecs",
        ),
    },
    "review-timelines": {
        "title": "How long the filing review takes",
        "confidence": "transcript-verified",
        "tickets": ("T-2E81A6EC",),
        "points": (
            "Provider first review: 1-2 working days. Provincial communications "
            "administration review: 1-20 working days.",
            "Inside the normal window no expedite is possible; do not promise "
            "a faster review.",
            "Review progress is filing-side data. This skill cannot read it: "
            "point the customer to the ICP Filing console or a filing agent.",
        ),
        "docs": (),
    },
    "deregister-and-refile": {
        "title": "What cancelling a filing really costs",
        "confidence": "transcript-verified",
        "tickets": ("T-2E81A6EC",),
        "points": (
            "Once the filing is cancelled, every domain under that filing "
            "record stops being servable from a mainland server until a new "
            "filing passes.",
            "Re-filing requires a NEW filing service code: a code already used "
            "by the cancelled record cannot be reused.",
            "Two routes exist and only the customer chooses between them: a "
            "paid migration service that keeps the site online, or the free "
            "cancel-and-reapply path that interrupts access.",
            "The outage window is the difference between the two routes: state "
            "it explicitly instead of only describing the steps.",
        ),
        "docs": (),
    },
    "cross-provider-access-transfer": {
        "title": "Adding a new provider's access for an already filed domain",
        "confidence": "summary-only",
        "tickets": ("T-5A6AABCB",),
        "points": (
            "Adding access at a second provider does not change the existing "
            "filing number.",
            "The original provider's access does not have to be cancelled "
            "first.",
            "Summary-only evidence: confirm the current wording with a filing "
            "specialist before quoting it as policy.",
        ),
        "docs": (),
    },
    "entity-change-and-instance-transfer": {
        "title": "Changing the filing subject, and moving an instance between accounts",
        "confidence": "transcript-verified",
        "tickets": ("T-2E81A6EC",),
        "points": (
            "An ECS instance cannot be transferred directly between two "
            "accounts whose enterprise verification subjects differ.",
            "The documented alternative is: create a custom image, share it "
            "with the target account, create a new instance from it. The "
            "instance ID and the public IP both change, so DNS records and any "
            "IP-based allow-lists must be updated afterwards.",
            "Filing subject information and domain registration information "
            "must stay consistent with each other; a mismatch is what forces "
            "the subject-change route in the first place.",
            "Image creation, sharing and instance creation are write "
            "operations: this skill only explains them, it never runs them.",
        ),
        "docs": (
            "https://help.aliyun.com/knowledge_detail/35816.html",
            "https://help.aliyun.com/document_detail/151401.html",
            "https://help.aliyun.com/knowledge_detail/281188.html",
        ),
    },
    "subject-type-vs-site-purpose": {
        "title": "Personal or enterprise subject for a given site",
        "confidence": "summary-only",
        "tickets": ("T-1F986C3F",),
        "points": (
            "Site content that involves payment or transaction handling needs "
            "an enterprise filing subject; a personal subject does not cover "
            "it.",
            "The \"individual developer\" option in a purchase page is not a "
            "statement about what a filing subject may publish.",
            "Summary-only evidence: the exact subject rule for a specific "
            "business scope must be answered by a filing specialist.",
        ),
        "docs": (),
    },
    "unfiled-vs-port-blocked": {
        "title": "Does an unfiled domain close a port?",
        "confidence": "summary-only",
        "tickets": ("T-D9F63B3E", "T-63E5332F"),
        "points": (
            "No. Being unfiled does not shut a listening port down; a failing "
            "80/443 connection with a correct security group normally means "
            "nothing is listening inside the guest, or the security group "
            "inbound rule is missing.",
            "Conversely, a browser symptom that cuts an established connection "
            "mid-request (err_connection_closed / err_connection_reset) is the "
            "classic shape of an inbound-rule interception, not of a filing "
            "sync delay.",
            "The correct order is always: prove the network path first with "
            "read-only cloud queries, then discuss filing state.",
            "Summary-only for T-D9F63B3E: the transcript pull failed.",
        ),
        "docs": (
            "https://help.aliyun.com/zh/ecs/user-guide/manage-security-group-rules",
        ),
    },
    "pre-filing-testing": {
        "title": "Testing the site before the filing passes",
        "confidence": "partial-transcript",
        "tickets": ("T-348424F9", "T-FC32DAA3"),
        "points": (
            "Before a filing passes, the site can be exercised through the "
            "public IP address directly, which is the standard pre-launch "
            "smoke test.",
            "While a filing is in progress the domain may be blocked on "
            "mainline HTTP/HTTPS access; keep the test on the IP path.",
            "Evidence is thin here (phone-record tickets and a summary whose "
            "cause attribution was never confirmed in the transcript): treat "
            "this as guidance to try, not as a filing policy statement.",
        ),
        "docs": (),
    },
    "renewal-and-filing-codes": {
        "title": "Renewal, expiry and the myth of gifted filing codes",
        "confidence": "transcript-verified",
        "tickets": ("T-5E8C9693", "T-25ADE062", "T-8BE7BCE3"),
        "points": (
            "Renewing an instance does not change its specifications.",
            "The unified answer for \"does renewal come with a filing service "
            "code\" is: no such promotion could be verified for this order; "
            "the quoted promotional price is the activity price. Do not "
            "generalise this to every order - it is one ticket's evidence.",
            "Whether the website stays reachable depends on the server that "
            "hosts it still being in use, not on the filing itself: letting "
            "the instance lapse takes the site down.",
            "Renewal, extension and pricing are commercial operations: this "
            "skill only states the read-only instance status and routes the "
            "rest to a human.",
            "For an account restricted by compliance review, the extension "
            "allowance quoted in the transcript was one day, one instance, "
            "once per calendar year; the unblocking itself is a human action.",
        ),
        "docs": ("https://help.aliyun.com/document_detail/116043.html",),
    },
    "classified-protection-materials": {
        "title": "Classified-protection (MLPS) paperwork is not an ICP filing",
        "confidence": "transcript-verified",
        "tickets": ("T-0631D05C", "T-96F0322C"),
        "points": (
            "A classified-protection filing certificate or assessment report "
            "is a different compliance track from an ICP filing number; the "
            "word \"filing\" in both makes customers merge them.",
            "Those materials come from a fixed official request form; a "
            "specialist answers within 3 working days, and the free security "
            "architecture consultation checkbox can be ticked on the same form.",
            "This skill only routes: it neither submits the form nor tracks "
            "its approval.",
        ),
        "docs": ("https://page.aliyun.com/form/act294450682/index.htm",),
    },
    "saas-to-self-hosted": {
        "title": "Moving from a SaaS site builder to a self-hosted ECS site",
        "confidence": "summary-only",
        "tickets": ("T-AAD67A7B",),
        "points": (
            "Content built on a SaaS site builder cannot be exported and "
            "deployed onto an ECS instance; a self-hosted site is rebuilt.",
            "Switching the hosting form of an already filed domain to a "
            "mainland ECS instance is an access change on the filing side and "
            "needs the filing console state, which no read-only cloud API "
            "exposes here.",
            "Summary-only evidence: confirm with a filing specialist.",
        ),
        "docs": ("https://help.aliyun.com/zh/ecs/user-guide/build-a-website.md",),
    },
    "website-served-elsewhere": {
        "title": "The filed domain is not served by the ECS instance at all",
        "confidence": "partial-transcript",
        "tickets": ("T-3A6324B3",),
        "points": (
            "A filed domain can be served by object storage plus a content "
            "delivery network while the ECS instance bought for the filing "
            "code serves nothing; that is legitimate, not a fault.",
            "Establish where the domain actually resolves before diagnosing "
            "the instance: the answer is in the DNS records, which the "
            "customer reads in the DNS console.",
            "Transcript was cut off at an attachment (the clarification "
            "happened on the phone): treat as context, not policy.",
        ),
        "docs": (),
    },
}

# Ordering used by --list-topics.
KNOWLEDGE_ORDER = (
    "filing-server-conditions",
    "service-code-binding",
    "review-timelines",
    "deregister-and-refile",
    "cross-provider-access-transfer",
    "entity-change-and-instance-transfer",
    "subject-type-vs-site-purpose",
    "unfiled-vs-port-blocked",
    "pre-filing-testing",
    "renewal-and-filing-codes",
    "classified-protection-materials",
    "saas-to-self-hosted",
    "website-served-elsewhere",
)

# ---------------------------------------------------------------------------
# Escalation routing (capability C4): identify, state the boundary, route
# ---------------------------------------------------------------------------
# Each entry: how the request reveals itself, what the skill may still say,
# and where the work actually goes.
ESCALATION_ROUTES = {
    "filing-progress-and-administration-review": {
        "signals": (
            "review progress", "administration review", "expedite the filing",
            "why is my filing still under review", "filing order status",
        ),
        "skill_may_say": (
            "Timelines (1-2 working days provider review, 1-20 working days "
            "administration review, no expedite inside the normal window) and "
            "the read-only server evidence."
        ),
        "route_to": (
            "ICP Filing console for the live order state, or a filing "
            "specialist / paid filing concierge service."
        ),
        "tickets": ("T-2E81A6EC", "T-C097A6CB"),
    },
    "commercial-actions": {
        "signals": (
            "buy", "purchase", "refund", "unsubscribe", "renew", "extend",
            "price", "discount", "invoice", "whitelist my top-up",
        ),
        "skill_may_say": (
            "Instance status, charge type, remaining term and expiry read "
            "from DescribeInstances, plus the official rule that filing "
            "eligibility needs mainland subscription billing whose purchased "
            "length is longer than 3 months including renewals (the remaining "
            "term is not the criterion) together with public bandwidth."
        ),
        "route_to": (
            "A human commerce specialist through a support ticket. The "
            "refund-rules document is offered as a link only."
        ),
        "tickets": ("T-C097A6CB", "T-2E81A6EC", "T-8BE7BCE3", "T-25ADE062"),
    },
    "in-guest-and-deployment-work": {
        "signals": (
            "install", "IIS", ".NET", "password", "web server not starting",
            "certificate on the server", "patch", "service is listening",
        ),
        "skill_may_say": (
            "The cloud-side verdict (which port the security group does or "
            "does not allow, which instance and region is involved) and the "
            "self-check commands the customer can run inside the guest."
        ),
        "route_to": (
            "alibabacloud-ecs-diagnose or a server-side specialist; this "
            "skill never logs into an instance and never accepts remote "
            "credentials."
        ),
        "tickets": ("T-B57F5477", "T-348424F9"),
    },
    "dns-record-work": {
        "signals": (
            "resolve", "A record", "record for the root domain",
            "DNS propagation", "subdomain works but main domain does not",
        ),
        "skill_may_say": (
            "That the instance's public address and its region, which a record "
            "must point at, and the exact self-check path in the DNS console."
        ),
        "route_to": (
            "The customer's own DNS console (the record for the root host is "
            "an @ A/CNAME record pointing at the instance address). This "
            "skill holds no DNS read or write contract."
        ),
        "tickets": ("T-16AB330B", "T-3BE66325"),
    },
    "classified-protection-and-other-compliance": {
        "signals": (
            "classified protection", "MLPS", "security compliance report",
            "level-2 protection certificate",
        ),
        "skill_may_say": (
            "The distinction from an ICP filing and the fixed official request "
            "form entry with its 3-working-day answer window."
        ),
        "route_to": "The official compliance-material request form (submit it yourself).",
        "tickets": ("T-0631D05C", "T-96F0322C"),
    },
    "account-compliance-restriction": {
        "signals": (
            "cannot top up", "renewal blocked", "risk control",
            "enterprise subject shows revoked", "extend the expiry",
        ),
        "skill_may_say": (
            "The instance's expiry and status, plus the data-loss risk of "
            "letting it lapse."
        ),
        "route_to": (
            "A human support ticket: unblocking an account is a platform "
            "permission no API in this skill's whitelist can grant."
        ),
        "tickets": ("T-8BE7BCE3",),
    },
}

# ---------------------------------------------------------------------------
# Console and documentation entry points shown to customers
# ---------------------------------------------------------------------------
# Every URL below was quoted by a support engineer in an injected ticket
# transcript. None of them was re-verified by an official documentation search
# in this development round (only build-a-website.md was), so the report labels
# them "agent-quoted, re-verify before quoting" -- see references/icp-filing-guide__help-links.md.
CUSTOMER_ENTRY_POINTS = {
    "icp_filing_console": {
        "label": "ICP Filing console (live filing order state, service codes)",
        "note": "Filing status is only readable here; no cloud API in this "
                "skill's whitelist exposes it.",
        "tickets": ("T-C097A6CB", "T-FC32DAA3"),
    },
    "security_group_console": {
        "label": "ECS console > Security Groups > Inbound rules",
        "console_path": "ecs.console.aliyun.com/securityGroupDetail/region/"
                        "{region}/groupId/{groupId}/detail/intranetIngress",
        "note": "Where the customer adds the 80/443 inbound rule themselves; "
                "this skill never writes it.",
        "tickets": ("T-63E5332F",),
    },
    "dns_console": {
        "label": "Alibaba Cloud DNS console",
        "note": "Check that the root domain has an @ record pointing at the "
                "instance's public address.",
        "tickets": ("T-16AB330B", "T-3BE66325"),
    },
    "filing_concierge": {
        "label": "Paid filing concierge",
        "url": "https://gs.aliyun.com/product/butler",
        "tickets": ("T-C097A6CB",),
    },
    "compliance_material_form": {
        "label": "Compliance material request form (classified protection etc.)",
        "url": "https://page.aliyun.com/form/act294450682/index.htm",
        "tickets": ("T-0631D05C", "T-96F0322C"),
    },
    "ecs_purchase": {
        "label": "ECS purchase page (for a filing-capable server)",
        "url": "https://www.aliyun.com/product/ecs",
        "tickets": ("T-C097A6CB",),
    },
}

# ---------------------------------------------------------------------------
# Report contracts
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# What no read-only cloud API can answer; printed verbatim whenever a verdict
# could otherwise be over-read as a filing conclusion.
API_BLIND_SPOTS = (
    "The live filing order state, filing number, filing subject and service-code "
    "inventory (no filing-data API is in this skill's read-only whitelist).",
    "The cumulative purchased length of an instance (original purchase plus "
    "every renewal): the instance query returns billing method, creation and "
    "expiry only, so the billing center (费用中心) remains the authority for the "
    "3-month purchase condition.",
    "DNS record contents (no DNS read API is in the whitelist): whether the root "
    "domain has an @ record is read by the customer in the DNS console.",
    "What is listening inside the guest operating system (this skill never runs "
    "a command on the instance).",
    "Certificate chain and web-application behaviour seen by the visitor's browser.",
)
