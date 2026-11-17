#!/usr/bin/env python3
"""
_constants.py -- Embedded static knowledge for the ECS Punishment Appeal Guide
==============================================================================
SECURITY: This skill is strictly READ-ONLY. This module holds no credentials
and performs no calls; authentication is resolved exclusively by the aliyun
CLI default credential chain. No explicit AK/SK handling exists anywhere in
this package.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (punishment-tier model, appeal-material checklists,
timeliness wording, handoff rules, official document links) is embedded here
as Python constants. There are no data files in scripts/.

Every knowledge item below is distilled from real support-ticket practice for
this symptom area (violation punishments, forced stops, rectification and
unblock appeals). The API-visible evidence and the API-invisible boundary are
stated explicitly so the Agent never over-claims what a read-only query can
prove.
"""

# ---------------------------------------------------------------------------
# Identity of this skill (observability User-Agent)
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-punishment-appeal-guide"

# ---------------------------------------------------------------------------
# Product / API metadata (verified API surface for this tier)
# ---------------------------------------------------------------------------

ECS_PRODUCT = "ecs"          # plugin mode: lowercase-hyphenated commands
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"          # plugin mode: lowercase-hyphenated commands
STS_API_VERSION = "2015-04-01"
STS_COMMAND = "get-caller-identity"

# The ONLY OpenAPI actions this skill may invoke. Anything outside this
# whitelist is out of scope and must never be called.
API_WHITELIST = [
    "DescribeInstances",
    "DescribeInstanceStatus",
    "DescribeSecurityGroups",
    "DescribeSecurityGroupAttribute",
]

# ---------------------------------------------------------------------------
# Timeouts / limits (MUST 7.6.1: every CLI subprocess call carries a timeout)
# ---------------------------------------------------------------------------

CALL_TIMEOUT_SECONDS = 60    # per CLI invocation
RETRY_MAX_ATTEMPTS = 3       # transient errors: throttling / 5xx / timeout
RETRY_BACKOFF_SECONDS = 2    # wait before retry N is N * 2s
PAGE_SIZE = 100              # DescribeInstances page size
STATUS_PAGE_SIZE = 50        # DescribeInstanceStatus page size
MAX_PAGES = 5                # pagination guardrail per query
MAX_SG_DETAIL_LOOKUPS = 5    # cap on DescribeSecurityGroupAttribute calls

# ---------------------------------------------------------------------------
# Punishment-tier model (7 tiers; classification knowledge)
# ---------------------------------------------------------------------------
# Each tier: label, what it means, customer wording cues (matched against the
# symptom hint and the notice keyword), what the read-only ECS queries can
# prove for it, what NO cloud API can show (privacy / platform-side data),
# the appeal-material checklist key, the guidance path key.

DISPOSE_TIERS = {
    "account": {
        "label": "Account-level action (risk-control freeze / restriction)",
        "cues": [
            "account frozen", "account freeze", "frozen by risk control",
            "cannot log in", "login restricted", "restricted use",
            "risk control", "account locked",
        ],
        "api_evidence": (
            "Account-level actions are NOT visible through the ECS read "
            "queries: when the identity itself is restricted, even read "
            "calls may fail with a permission error. Instance facts "
            "(still Running, still billing) can be used to plan cost "
            "reduction while the action stands."
        ),
        "invisible": (
            "Freeze cause detail, the automatic release timestamp and any "
            "manual review outcome live on the risk-control side; no query "
            "API was verified for them."
        ),
        "materials_key": "account",
        "talk_keys": ["no_earlier_release", "principal_authorization"],
        "path": (
            "Read the ORIGINAL freeze notice (console message / SMS / "
            "email) with the customer, extract the release timestamp, and "
            "route to the manual appeal channel. If pay-as-you-go billing "
            "is the concern, give the remote-login plus stop-instance "
            "guidance and the billing caveat (see the official doc link)."
        ),
    },
    "instance": {
        "label": "Instance-level forced stop / platform lock",
        "cues": [
            "force stopped", "forced stop", "was stopped", "already stopped",
            "shut down", "shutdown", "instance locked", "locked",
            "service suspended", "server closed", "illegal block",
            "security management policy",
        ],
        "api_evidence": (
            "DescribeInstances (Status, OperationLocks lock reasons) and "
            "DescribeInstanceStatus can show whether the instance really "
            "sits in a stopped or locked state versus still Running."
        ),
        "invisible": (
            "The punishment record itself, the violating content detail and "
            "the appeal progress are platform-side data with no verified "
            "query API; only the notice text the customer received has them."
        ),
        "materials_key": "content",
        "talk_keys": ["review_order", "principal_authorization"],
        "path": (
            "Confirm the instance fact via read-only queries; when the "
            "notice is a platform action, walk the remediation checklist "
            "first, then the appeal-material list and channel. After an "
            "unblock, re-run this script to verify the status returned to "
            "Running as the closing evidence."
        ),
    },
    "url": {
        "label": "URL / website content block (instance may be untouched)",
        "cues": [
            "website blocked", "url blocked", "page blocked", "site down",
            "illegal content", "violation content", "pornography",
            "gambling", "fraud sample", "defaced", "tampered",
            "how do i appeal", "appeal",
        ],
        "api_evidence": (
            "When DescribeInstances reports Running and no platform lock is "
            "present, a 'server shut down' claim is usually a URL-level "
            "block, not an instance-level one: the instance is reachable "
            "even though the page is blocked."
        ),
        "invisible": (
            "Which exact URL was blocked and why is privacy-restricted: "
            "the platform does not disclose violating-content detail to "
            "the customer; follow the notice plus remediation instead."
        ),
        "materials_key": "content",
        "talk_keys": ["no_content_detail", "review_order"],
        "path": (
            "Distinguish URL-level from instance-level with the read-only "
            "facts; give the content self-inspection checklist, the "
            "deletion-evidence requirement, then materials plus channel."
        ),
    },
    "port": {
        "label": "Egress port / outbound-path restriction",
        "cues": [
            "port 25", "smtp", "outbound port", "egress blocked",
            "vpn blocked", "udp 443", "cannot send mail",
        ],
        "api_evidence": (
            "Security-group rules can be read and compared, but a platform "
            "egress policy on a port (e.g. the default outbound 25/SMTP "
            "block) is NOT represented in any security-group attribute."
        ),
        "invisible": (
            "Platform egress policy and supervisory-level blocking are "
            "not queryable; neither can this skill lift them."
        ),
        "materials_key": "port",
        "talk_keys": ["regulator_beyond_cloud", "email_area_handoff"],
        "path": (
            "Identify and hand off: mail sending on port 25 belongs to the "
            "adjacent email-sending area; supervisory blocking of tunnel "
            "protocols gets the fixed talk plus compliant alternatives "
            "(VNC / Workbench, bastion host, VPN gateway product)."
        ),
    },
    "transaction": {
        "label": "Transaction risk control (order / payment / renewal intercepted)",
        "cues": [
            "cannot pay", "payment blocked", "order intercepted",
            "cannot purchase", "renewal blocked", "checkout failed",
            "unknownerror",
        ],
        "api_evidence": (
            "Nothing on the ECS read surface relates to transaction risk "
            "control; this tier is decided entirely by the notice text and "
            "the error the console returned (for example ErrorCode: "
            "UnknownError plus a RequestId)."
        ),
        "invisible": (
            "The risk-control verdict and its release are account-side "
            "manual review; no query API was verified for them."
        ),
        "materials_key": "transaction",
        "talk_keys": ["principal_authorization", "review_order"],
        "path": (
            "State the required verification material UP FRONT (a photo of "
            "the account principal holding the ID card, portrait side; a "
            "student certificate or a plain ID screenshot is not accepted "
            "as a substitute), then point to the self-service appeal tool "
            "in the notice. Some verdicts are final; escalation goes to a "
            "duty manager, never to this skill."
        ),
    },
    "judicial": {
        "label": "Judicial / regulatory / law-enforcement request",
        "cues": [
            "police", "public security", "court", "judicial", "case",
            "report a case", "investigation", "cooperation request",
            "supervisory authority", "summoned for interview",
        ],
        "api_evidence": (
            "None. This tier is handled without any cloud query: the cloud "
            "provider is not the decision maker here."
        ),
        "invisible": (
            "Everything: supervisory-level blocks and judicial data "
            "disclosure bypass the cloud support channel entirely."
        ),
        "materials_key": "judicial",
        "talk_keys": ["judicial_fixed_talk"],
        "path": (
            "Use the fixed talk verbatim: the cloud provider cannot pull "
            "third-party data for an individual, cannot issue stamped "
            "evidence letters, and law enforcement must use the formal "
            "cooperation channel. Run no queries for this request."
        ),
    },
    "unverified": {
        "label": "Unverified block claim (no notice, cloud facts normal)",
        "cues": [
            "ip blocked", "cannot access", "unreachable from the mainland",
            "domain unreachable", "connection refused everywhere",
        ],
        "api_evidence": (
            "The four read-only queries prove: the instance exists in this "
            "region and account, its Status value, its lock reasons, and "
            "whether a security-group rule explains the reported failure."
        ),
        "invisible": (
            "Cross-border reachability, local-network conditions, domain "
            "expiry and third-party (registrar) blocking are outside the "
            "cloud read surface."
        ),
        "materials_key": "none",
        "talk_keys": ["ask_judgement_basis"],
        "path": (
            "Ask the fixed key question first: how exactly was the 'blocked' "
            "conclusion reached, and from where was it tested. Without a "
            "notice document this skill never endorses the claim. If a "
            "plain reachability fault remains, hand off to the connectivity "
            "area; if the resource is not visible, verify region and "
            "account ownership before anything else."
        ),
    },
}

# ---------------------------------------------------------------------------
# Appeal-material checklists (standardized from real ticket practice)
# ---------------------------------------------------------------------------
# Every appeal must be submitted by (or with written authorization from) the
# verified principal of the account: materials whose subject does not match
# the account real-name subject are rejected. This is the authorization
# branch of this tier.

MATERIAL_CHECKLISTS = {
    "content": {
        "title": "Content-violation appeal (instance / URL level)",
        "items": [
            "Detailed business description of the affected site or service",
            "Business license of the account's real-name subject",
            "ICP filing number of the domain (when the service is a website)",
            "Official website / service link",
            "The violating URL(s) named in the notice (as far as disclosed)",
            "Screenshot evidence that the content was deleted or fixed",
            "Instance ID / public IP of the affected asset",
        ],
        "note": (
            "A plain 'my qualifications are complete, so I cannot be "
            "violating' is not a defense path: review is content-based, "
            "and submitting the full list once avoids repeated rounds."
        ),
    },
    "account": {
        "title": "Account-level freeze / risk-control appeal",
        "items": [
            "Account ID and the freeze notice text (console message / SMS / email)",
            "Business license of the real-name subject",
            "Legal-representative identity verification as demanded by the notice",
            "Business description and typical usage statement",
            "Authorization proof when a representative submits on behalf of the subject",
        ],
        "note": (
            "If the automatic release timestamp is already in the notice, "
            "waiting it out is usually faster than an appeal: automatic "
            "release cannot be advanced by hand."
        ),
    },
    "transaction": {
        "title": "Transaction risk-control (order / payment) appeal",
        "items": [
            "Photo of the account holder holding the ID card (portrait side visible)",
            "Account registration information consistent with the certificate",
            "Order / RequestId reference when available",
        ],
        "note": (
            "Real tickets show student certificates and plain ID screenshots "
            "being rejected: prepare the person-held portrait photo FIRST to "
            "avoid an invalid-material tug of war."
        ),
    },
    "port": {
        "title": "Egress-port requests (out of this skill's scope)",
        "items": [
            "This area hands off; the adjacent email-sending area owns "
            "port-25 mail applications, and supervisory tunnel blocks "
            "cannot be appealed through the cloud platform at all.",
        ],
        "note": "Hand off instead of collecting materials here.",
    },
    "judicial": {
        "title": "Judicial / regulatory requests (no cloud-side submission)",
        "items": [
            "No material is collected through this skill: law-enforcement "
            "cooperation runs through the official government-agency "
            "channel, individuals file with local police.",
        ],
        "note": "Deliver the fixed talk; do not query, promise or proxy.",
    },
    "none": {
        "title": "No material list applies yet",
        "items": [
            "Establish the facts first: obtain the original notice text "
            "from the customer, or re-check reachability evidence before "
            "framing any appeal.",
        ],
        "note": "Never endorse an 'unblocked' claim that has no notice.",
    },
}

# ---------------------------------------------------------------------------
# Fixed customer-facing talks (verbatim wording, ticket-derived)
# ---------------------------------------------------------------------------

FIXED_TALKS = {
    "review_order": (
        "Appeals are assessed by a dedicated specialist in queue order. "
        "Based on established practice the result normally arrives the "
        "same day and within 3 calendar days at the latest, through the "
        "console message / SMS channel quoted in your notice. Neither an "
        "approval outcome nor an expedited slot can be guaranteed."
    ),
    "no_earlier_release": (
        "This restriction releases automatically at the timestamp stated "
        "in your notice. An automatic release cannot be advanced manually, "
        "so treat that timestamp as the authoritative unblock time."
    ),
    "no_content_detail": (
        "For privacy and process reasons the platform does not disclose "
        "the violating content detail to the customer. Remediation and the "
        "formal appeal are the only supported paths; the review result is "
        "synchronized back through the notice channel."
    ),
    "principal_authorization": (
        "An appeal is only accepted when it is submitted by the verified "
        "real-name subject of the account, or by a representative holding "
        "an authorization for that subject. Materials whose subject differs "
        "from the account subject will not pass review."
    ),
    "judicial_fixed_talk": (
        "The cloud provider cannot provide third-party data to an "
        "individual, cannot issue officially stamped evidence letters, and "
        "cannot act on behalf of a private party in an investigation. "
        "Individuals should file a report with local police; law-enforcement "
        "bodies must use the formal cooperation channel with our compliance "
        "team. No query is executed through this skill for such a request."
    ),
    "regulator_beyond_cloud": (
        "This restriction originates from a supervisory authority outside "
        "the cloud platform: Alibaba Cloud cannot lift it, and an appeal "
        "filed here will not change it. Compliant remote-access "
        "alternatives are VNC / Workbench login, a bastion host, or a "
        "managed VPN gateway product."
    ),
    "email_area_handoff": (
        "Outbound port 25 mail sending is governed by an anti-spam default "
        "policy owned by the adjacent email-sending area, not by this "
        "punishment workflow; hand the case there instead of collecting "
        "appeal materials here."
    ),
    "ask_judgement_basis": (
        "Before treating this as a platform action, please state how the "
        "'blocked' conclusion was reached: which address was tested, from "
        "which network, and whether an official notice was received. "
        "Without such evidence the claim is recorded as unverified and "
        "this skill will not certify a block."
    ),
}

# ---------------------------------------------------------------------------
# Remediation guidance blocks (customer-executed; this skill guides only)
# ---------------------------------------------------------------------------
# Hard rule echoed in every guidance output: take a manual snapshot / backup
# in the console BEFORE deleting or changing anything. This skill never
# performs the snapshot itself and never enters the guest.

REMEDIATION_BY_VIOLATION = {
    "tampered_or_injected_content": {
        "title": "Defaced / injected or linked-out content (fraud, gambling, adult)",
        "steps": [
            "First create a manual snapshot or full backup of every affected disk (console action by the customer, before any cleanup).",
            "Compare the web root against the original code package; check page titles, iframes, hidden link blocks, dynamically included files and upload directories.",
            "Delete or fix the violating pages and links; record before/after screenshots as deletion evidence.",
            "Rotate compromised credentials (CMS / panel / database accounts) and patch the entry point, or the block can recur.",
            "If the intrusion depth exceeds simple cleanup, hand off to the host-intrusion cleanup area for in-guest forensics.",
        ],
    },
    "mining_outreach_alert": {
        "title": "Outbound mining-pool / malware communication alert",
        "steps": [
            "Snapshot the disks before touching anything.",
            "Check scheduled tasks, startup services and unusual outbound connections; a security-center quarantine review is the adjacent intrusion area.",
            "Complete the cleanup inside the rectification window stated in the notice: unfinished rectification escalates to a shutdown.",
            "Keep screenshots of removed items as remediation evidence for the appeal.",
        ],
    },
    "outbound_attack": {
        "title": "Instance observed attacking outward (source of account / instance freeze)",
        "steps": [
            "Identify the abusing process or compromised site with the customer (snapshot first).",
            "Stop the traffic source: remove the webshell or shut down the offending service.",
            "Wait out or appeal the restriction per the notice; attack-behavior freezes typically release at an automatic timestamp.",
        ],
    },
    "reporting_dispute": {
        "title": "Disputed judgment (hijack, false positive, exercised-range activity)",
        "steps": [
            "Collect proof: original code comparison, access logs, and for authorized security exercises the official authorizer letter.",
            "Snapshot before any change so the disputed state remains reviewable.",
            "Submit the dispute as a written statement with the appeal materials; do not assume the reviewer can see your side without it.",
        ],
    },
    "generic_missing_detail": {
        "title": "Notice received but violating content unknown",
        "steps": [
            "Re-read the notice for the asset identifier and URL/type fields; the notice is the only reliable content carrier.",
            "Self-inspect the web root and recent change history (snapshot first).",
            "Ask Security Center / Security Group history review only through its own area; this skill stays read-only.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Billing-reduction guidance for account-level freezes
# ---------------------------------------------------------------------------

BILLING_MITIGATION = (
    "When a frozen account blocks the console but the instance is still "
    "Running, the customer can log in with SSH (or Workbench / VNC) and "
    "stop the pay-as-you-go instance to reduce charges. Even when stopped, "
    "CPU / memory / disk fees may still accrue depending on the stop mode; "
    "always end with 'the actual bill is authoritative'. This skill only "
    "quotes the guidance and the official document; it never stops or "
    "changes anything itself."
)

# ---------------------------------------------------------------------------
# Handoff rules (identify + refer; never implement in this skill)
# ---------------------------------------------------------------------------

HANDOFF_RULES = [
    {
        "match": ["blackhole", "ddos", "anti-ddos", "scrubbing", "high defense"],
        "target": "area:attack-blackhole-diagnosis",
        "say": "DDoS blackhole and anti-DDoS unblocking belong to the attack-blackhole area, not to punishment appeals.",
    },
    {
        "match": ["will not start", "stuck starting", "cannot boot", "startup failure", "shut failure"],
        "target": "area:instance-state-diagnosis",
        "say": "Start/stop faults not caused by a platform action belong to the instance-state diagnosis area.",
    },
    {
        "match": ["expand", "partition not extended", "disk not bigger"],
        "target": "area:disk-expand-diagnosis",
        "say": "Disk expansion not taking effect belongs to the disk-expand area.",
    },
    {
        "match": ["io slow", "iops", "performance below spec"],
        "target": "area:resource-bottleneck",
        "say": "Disk IO performance questions belong to the disk-io area.",
    },
    {
        "match": ["inbound rule", "outbound rule", "security group blocks", "cannot reach port"],
        "target": "area:access-block-layered",
        "say": "Security-group-only reachability questions belong to the layered access-block area.",
    },
    {
        "match": ["cleanup virus", "kill miner", "forensic scan"],
        "target": "area:host-intrusion-cleanup",
        "say": "Deep in-guest cleanup after an intrusion belongs to the host-intrusion cleanup area; this skill only supplies the remediation checklist.",
    },
    {
        "match": ["port 25", "smtp", "mass mail"],
        "target": "adjacent email-sending / port-25 area",
        "say": "Port-25 mail sending applications belong to the email-sending area.",
    },
    {
        "match": ["icp filing", "record number procedure", "public security filing"],
        "target": "area:icp-filing-guide",
        "say": "ICP and public-security filing procedures belong to the filing area.",
    },
    {
        "match": ["password forgotten", "key pair lost", "cannot log in to the instance", "vnc login issue"],
        "target": "area:login-credential-repair",
        "say": "Guest login-credential repair belongs to the login-credential area.",
    },
    {
        "match": ["lightweight", "simple application server", "swas"],
        "target": "the dedicated lightweight-server area",
        "say": "Punishment questions on Simple Application Server instances are outside this ECS skill; refer to the lightweight-server area.",
    },
    {
        "match": ["refund", "unsubscribe", "compensation"],
        "target": "manual commercial channel (support ticket)",
        "say": "Refunds and compensation are commercial processes: state the boundary, point to the console ticket entry, never proxy them.",
    },
]

# ---------------------------------------------------------------------------
# Official documentation links (help.aliyun.com only, evidence-backed set)
# ---------------------------------------------------------------------------
# Only these verified help-center URLs may be cited by this skill. The
# self-service unblock platform, the appeal form URL seen in one ticket and
# the machine-room address lookup were NOT confirmed during requirements
# review, so no link for them may be quoted until verification completes;
# guidance stays descriptive.

OFFICIAL_DOC_LINKS = {
    "stop_an_instance": (
        "https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md"
    ),
    "instance_faq": (
        "https://help.aliyun.com/zh/ecs/instance-management-and-operations-faqs.md"
    ),
    "workbench_system_management": (
        "https://help.aliyun.com/zh/ecs/user-guide/workbench-system-management.md"
    ),
    "workbench_cli_credentials": (
        "https://help.aliyun.com/zh/ecs/user-guide/install-and-configure-workbench-cli-credentials.md"
    ),
}

# ---------------------------------------------------------------------------
# API-invisible boundary (stated verbatim in every report)
# ---------------------------------------------------------------------------

INVISIBLE_SUMMARY = (
    "Not visible through any cloud query available to this skill: "
    "punishment records, violating-content detail (privacy-restricted), "
    "appeal / review progress, account-side risk-control verdicts and "
    "supervisory blocking. These are carried only by the notice the "
    "customer received and are resolved through the appeal / manual "
    "channels."
)

# ---------------------------------------------------------------------------
# Degradation fallback (used when evidence is missing or queries fail)
# ---------------------------------------------------------------------------

DEGRADED_FALLBACK = (
    "Fallback path: ask the customer for the ORIGINAL notice text "
    "(console message / SMS / email screenshot), the asset identifier "
    "(instance ID or public IP), and the region; if the read-only queries "
    "still cannot corroborate, open a manual support ticket with the "
    "notice attached instead of guessing an outcome."
)

# ---------------------------------------------------------------------------
# Status / exit-code contract
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

EXIT_CONCLUSIONS = 0   # produced a usable conclusion (OK or DEGRADED)
EXIT_NO_CONCLUSION = 1  # required evidence unavailable
