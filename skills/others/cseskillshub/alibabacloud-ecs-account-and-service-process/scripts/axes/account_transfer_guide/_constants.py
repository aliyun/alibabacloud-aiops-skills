#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS cross-account transfer guide
==============================================================================
SECURITY: No credential handling of any kind lives in this module. All cloud
authentication is resolved exclusively by the aliyun CLI default credential
chain elsewhere; this file is plain Python constants.

Per the skill package layout, scripts/ holds executable code only, so
every table this skill consults (transfer conditions, direction verdicts,
console blocker catalog, post-transfer checklist, image-migration steps,
account rules, official help links, hand-off routes) is embedded here as a
Python constant. There are NO data files in scripts/.

All customer-facing facts below were distilled from real Alibaba Cloud
support-ticket dialogues and the official help-center documents cited in
references/help-links.md. Where a rule is supported by a single ticket
summary only (not re-verified against the full dialogue), the entry carries
an explicit "verify against the official docs / a support ticket" caveat and
must never be presented to the customer as a certain verdict.
"""

# ---------------------------------------------------------------------------
# Skill identity and API metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-account-transfer-guide"

# API versions actually invoked (informational; the aliyun CLI carries its own
# metadata). ECS read/write actions use the 2014-05-26 RPC version; STS is the
# central 2015-04-01 service.
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# Central STS endpoint (region-less).
STS_ENDPOINT = "sts.aliyuncs.com"

# Defensive default region for the region-less STS call only. Every ECS query
# MUST receive the real region of the target instance from --region-id.
DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Timeouts and limits (every CLI subprocess call uses these)
# ---------------------------------------------------------------------------

# Per-call timeout in seconds for every aliyun CLI subprocess invocation.
API_TIMEOUT_SECONDS = 60
# Overall run budget guard for one entry-script execution, in seconds.
RUN_BUDGET_SECONDS = 300
# Page size for NextToken-paginated ECS list queries (API max 100).
MAX_RESULTS = 100
# Hard guardrail on pages fetched per query loop.
MAX_PAGES = 20
# Cap on instances rendered in one precheck report (the JSON keeps all).
MAX_INSTANCE_REPORT = 20

# ---------------------------------------------------------------------------
# API allowlist (anything outside this list is absolutely prohibited)
# ---------------------------------------------------------------------------

# Query-class actions the scripts may invoke automatically (no per-call
# confirmation needed because none of them changes any resource):
ALLOWED_QUERY_ACTIONS = {
    "ecs": [
        "DescribeInstances",
        "DescribeInstanceStatus",
        "DescribeAvailableResource",
    ],
    "sts": ["GetCallerIdentity"],
}

# The ONLY action with a write effect, and it is confirmation-gated: the
# entry script refuses to invoke it until --confirm yes is passed, and the
# agent must first explain to the user what will run, its impact, and its
# reversibility (see SKILL.md "User Confirmation").
GATED_WRITE_ACTION = {
    "ecs": ["CreateSnapshot"],
}

# Actions intentionally NOT enabled in v1 (capability boundary only; they
# must never be called by this skill):
#   - Cloud Assistant command execution actions (RunCommand / InvokeCommand):
#     transfer-eligibility evidence lives entirely account-side and
#     instance-side; no referenced ticket needed in-guest readings.
#   - CMS monitoring reads: reserved at the permission-document level only.
NOT_ENABLED_ACTIONS_NOTE = (
    "Cloud Assistant command execution and CloudMonitor metric reads are "
    "kept as documented capability boundaries; v1 never calls them. If a "
    "customer insists on in-guest verification of migrated data, decline "
    "gracefully and hand the reading task to the customer."
)

# ---------------------------------------------------------------------------
# K1 -- transfer direction matrix (who may transfer to whom)
# ---------------------------------------------------------------------------
# Evidence levels:
#   "dialogue-verified"  : re-confirmed in a real ticket dialogue transcript
#   "summary-only"       : only a ticket summary exists; verify before quoting
#   "weak"               : partially evidenced; keep hedged

DIRECTION_MATRIX = {
    "enterprise->enterprise": {
        "verdict": "CONDITIONAL",
        "rule": (
            "Enterprise accounts can transfer instances only to another "
            "account whose real-name verification is the SAME enterprise "
            "entity AND the enterprise name must be IDENTICAL."
        ),
        "evidence": "dialogue-verified (three independent tickets agree)",
        "caveat": "",
    },
    "individual->enterprise": {
        "verdict": "ELIGIBLE_WITH_CONDITIONS",
        "rule": (
            "An individual-verified account CAN transfer to an enterprise "
            "account, but the official transfer-limitations section applies; "
            "the customer must read it before starting."
        ),
        "evidence": "dialogue-verified",
        "caveat": (
            "Always cite the limitations anchor: "
            "https://help.aliyun.com/zh/ecs/user-guide/"
            "how-to-cross-account-transfer-migration-ecs-instance#babb9b36856x4"
        ),
    },
    "enterprise->individual": {
        "verdict": "LIKELY_NOT_ELIGIBLE",
        "rule": (
            "Enterprise-verified accounts to individual accounts are not "
            "supported in the transfer flow, even when the legal "
            "representative is the same natural person."
        ),
        "evidence": "summary-only (phone-record ticket; not re-verified)",
        "caveat": (
            "Present as 'not supported per support evidence; confirm against "
            "the official transfer-limitations section before promising'."
        ),
    },
    "individual->individual": {
        "verdict": "LIKELY_ELIGIBLE",
        "rule": (
            "Individual-to-individual transfers are generally accepted when "
            "both accounts are plain personal real-name accounts; the "
            "support flow still evaluates the five hard conditions."
        ),
        "evidence": "weak (dialogue continued without an explicit yes)",
        "caveat": (
            "Say 'treat as eligible pending the standard review; confirm the "
            "outcome in the transfer result', never guarantee."
        ),
    },
}

# Reasons that override or downgrade any direction above.
OVERRIDE_REASONS = {
    "cross_region": {
        "verdict": "NOT_ELIGIBLE",
        "text": (
            "Cross-region transfer is never supported: the instance and the "
            "destination vSwitch must be in the same region and zone."
        ),
        "evidence": "dialogue-verified",
    },
    "campaign_yes": {
        "verdict": "NOT_ELIGIBLE",
        "text": (
            "Instances bought through marketing campaigns / discounted "
            "activity purchases frequently do not support direct transfer to "
            "another account; use the image-share migration path instead."
        ),
        "evidence": "dialogue-verified",
    },
    "campaign_unknown": {
        "verdict": "NEEDS_MANUAL_REVIEW",
        "text": (
            "Whether the instance came from a campaign or discount purchase "
            "is not visible to this skill; ask the customer, and if unclear, "
            "have the backend verify via a support ticket before starting."
        ),
        "evidence": "dialogue-verified (discount state needs backend review)",
    },
    "reseller_yes": {
        "verdict": "NEEDS_MANUAL_REVIEW",
        "text": (
            "Per one (summary-only) ticket, distribution / non-direct "
            "customer accounts could not transfer; treat the account "
            "relationship as a manual backend check before promising."
        ),
        "evidence": "summary-only",
    },
    "entity_relation_unknown": {
        "verdict": "NEEDS_MANUAL_REVIEW",
        "text": (
            "The verified legal entity of each account cannot be queried "
            "through any read API available to this skill; the customer must "
            "compare both real-name entities in Account Center, or open a "
            "ticket for backend verification."
        ),
        "evidence": "dialogue-verified (support asked the customer directly)",
    },
    "entity_relation_different": {
        "verdict": "NOT_ELIGIBLE",
        "text": (
            "Different verified entities cannot transfer between each other "
            "(for enterprises even the same company type with a different "
            "registered name is enough to block the transfer)."
        ),
        "evidence": "dialogue-verified",
    },
}

# Facts asked for in every --assess run, so the agent collects them first.
ASSESS_INPUT_HELP = (
    "Needed for a feasibility verdict: source account real-name type "
    "(individual or enterprise), target account real-name type, whether both "
    "accounts show the identical verified entity name, whether the instance "
    "was a campaign / discounted purchase, whether either account is a "
    "distribution (reseller) customer, and whether the instance and target "
    "vSwitch are in the same region and zone."
)

# ---------------------------------------------------------------------------
# K2 -- the five hard pre-transfer conditions, quoted verbatim in most
# support answers (two independent ticket dialogues recited them almost
# word-for-word, which is why they are fixed as a checklist here)
# ---------------------------------------------------------------------------

TRANSFER_CONDITIONS = [
    {
        "id": "same-entity",
        "text": (
            "Enterprise-to-enterprise transfers only work between accounts "
            "verified under the same enterprise entity with an identical "
            "enterprise name."
        ),
        "auto_checkable": False,
        "how": "Customer self-declaration; backend review via ticket.",
    },
    {
        "id": "same-vpc-zone",
        "text": (
            "The vSwitch and security group filled in during the transfer "
            "must be in the SAME VPC, and the destination vSwitch must be in "
            "the SAME ZONE as the instance. Cross-region transfer is "
            "unsupported."
        ),
        "auto_checkable": True,
        "how": (
            "DescribeInstances reports the instance zone / VPC / vSwitch / "
            "security groups; DescribeAvailableResource pre-checks zone "
            "sellability."
        ),
    },
    {
        "id": "target-balance",
        "text": (
            "If the target account already holds pay-as-you-go resources, "
            "its available balance (cash plus credit line) must exceed "
            "100 CNY."
        ),
        "auto_checkable": False,
        "how": "Target-account owner checks Billing Center; not queryable here.",
    },
    {
        "id": "unbind-first",
        "text": (
            "Resources bound to the ECS instance must be unbound before the "
            "transfer, e.g. an associated EIP or an SSH key pair."
        ),
        "auto_checkable": True,
        "how": "DescribeInstances lists bound EIP and key-pair fields.",
    },
    {
        "id": "instance-type-limits",
        "text": (
            "Some instances cannot be transferred at all (campaign or "
            "discount purchases, special account relationships); read the "
            "official limitations section before starting."
        ),
        "auto_checkable": False,
        "how": "Customer declaration + the official limitations anchor.",
    },
]

TRANSFER_TIMING = {
    "typical": (
        "An online ECS transfer usually completes in about 30 minutes "
        "(dialogue-verified support wording; never promise expedited review)."
    ),
    "frequency": (
        "One ticket summary states an instance may be transferred only once "
        "per half year; this is NOT re-verified -- quote it only as 'support "
        "guidance says roughly once per half year; confirm in the official "
        "limitations section'."
    ),
    "offline_review": (
        "Domain offline account-transfer reviews take about 5 working days "
        "(dialogue-verified)."
    ),
}

# ---------------------------------------------------------------------------
# K6 -- console blocker catalog (strings customers actually paste)
# ---------------------------------------------------------------------------
# match: lowercase substrings searched in the customer's wording; the two
# CJK literals reproduce the exact console/status strings from tickets so a
# pasted Chinese error still routes correctly.

BLOCKERS = [
    {
        "id": "vswitch-not-selectable",
        "match": [
            "vswitch cannot", "cannot select vswitch", "vswitch greyed",
            "switch cannot be selected", "配置交换机后无法选择",
        ],
        "meaning": (
            "The transfer wizard only offers vSwitches that are in the same "
            "VPC AND the same zone as the instance. An empty or unselectable "
            "list means no such vSwitch exists yet in the instance's zone."
        ),
        "actions": [
            "Run --precheck to read the instance's ZoneId and VpcId.",
            "Create (or pick) a vSwitch in that exact VPC + zone, then "
            "retry the transfer wizard.",
        ],
    },
    {
        "id": "transfer-failed",
        "match": ["transfer failed", "cannot transfer", "unable to transfer",
                  "过户失败"],
        "meaning": (
            "Five common root causes: campaign / discounted purchase, "
            "verified-entity mismatch, bound resources not detached "
            "(EIP / key pair), cross-region attempt, target balance below "
            "the threshold."
        ),
        "actions": [
            "Run --assess with both accounts' real-name types and entity "
            "relation, then --precheck for the machine-side facts.",
            "If all five causes are excluded, submit a ticket attaching the "
            "instance id, both account UIDs, and the exact error text.",
        ],
    },
    {
        "id": "under-review",
        "match": ["under review", "审核中", "pending review", "in review"],
        "meaning": (
            "Per ticket evidence, an 'under review' state means a transfer "
            "application is in review (typically re-submitted after an "
            "earlier attempt failed). Single-source reading -- confirm in "
            "the transfer history page."
        ),
        "actions": [
            "Wait for the review to settle before re-submitting; a typical "
            "online transfer takes about 30 minutes.",
            "Check the transfer record in the console; open a ticket with "
            "the instance id and both UIDs if it stalls.",
        ],
    },
    {
        "id": "realname-type-mismatch",
        "match": ["authentication type", "real-name", "realname",
                  "实名认证类型不一致"],
        "meaning": (
            "The console rejected the direction: the two accounts' "
            "real-name verification types are inconsistent (e.g. an "
            "enterprise account transferring toward an individual account)."
        ),
        "actions": [
            "Run --assess with --source-type/--target-type/--entity-relation "
            "to see the direction rule and evidence level.",
            "If the direction is not supported, switch to the image-share "
            "migration path (--guide image-migration).",
        ],
    },
    {
        "id": "instance-id-unknown",
        "match": ["instance id where", "where to find the instance",
                  "cannot find instance id"],
        "meaning": (
            "The customer cannot locate the instance ID needed by the "
            "transfer form (a real ticket pain point)."
        ),
        "actions": [
            "Run --precheck --region-id <region> with no instance id: the "
            "script lists every instance with its ID, zone, and network "
            "bindings.",
        ],
    },
]

GENERIC_BLOCKER_FALLBACK = {
    "meaning": (
        "No catalogued blocker matched the pasted text."
    ),
    "actions": [
        "Run --assess and --precheck to gather the standard evidence.",
        "If blocked, submit a support ticket attaching: instance id, source "
        "and target account UIDs, and the exact on-screen error text.",
    ],
}

# ---------------------------------------------------------------------------
# K3 -- image-share migration fallback (the canonical alternative path)
# ---------------------------------------------------------------------------

IMAGE_MIGRATION_STEPS = [
    {
        "step": 1,
        "title": "Create a custom image from the source instance",
        "detail": (
            "In the source account's ECS console, create a custom image from "
            "the instance (this also creates the underlying snapshots)."
        ),
    },
    {
        "step": 2,
        "title": "Copy the image to the destination region first (only when "
                 "the target instance lives in another region)",
        "detail": (
            "Cross-account AND cross-region sharing requires copying the "
            "image into the target region BEFORE sharing. The copy creates "
            "new snapshots in the target region which incur snapshot storage "
            "fees; the copied snapshots stay independently retained in the "
            "target region regardless of the source image."
        ),
    },
    {
        "step": 3,
        "title": "Share the image with the destination account UID",
        "detail": (
            "Share the (region-local) custom image to the target account's "
            "16-digit UID. The UID can be read by the target account itself "
            "with scripts/sts_token.py; it cannot be looked up across "
            "accounts."
        ),
    },
    {
        "step": 4,
        "title": "In the destination account, use the shared image",
        "detail": (
            "Either purchase a NEW instance from the shared image, or, on an "
            "EXISTING target instance, use the console entry 'Replace "
            "Operating System (re-select image)'. Use the standard entry "
            "wording 'Replace Operating System': telling a customer to look "
            "for 'reset image' caused a real rework round in a ticket."
        ),
    },
]

IMAGE_MIGRATION_RULES = [
    (
        "SNAPSHOT-FIRST (mandatory): replacing the target instance's system "
        "disk with the shared image PERMANENTLY DESTROYS the existing system "
        "disk data. Before guiding or performing such an OS replacement, "
        "create a snapshot backup of the current system disk first (the "
        "skill runs --create-snapshot only after the user confirms)."
    ),
    (
        "The image itself is data at rest: creating and sharing it changes "
        "nothing on the running source instance."
    ),
    (
        "A new instance from the shared image gets a NEW public IP; the old "
        "public IP cannot move across accounts with an image."
    ),
    (
        "Shared/custom images and snapshots do not migrate with an instance "
        "transferred through the transfer flow -- transferred instances keep "
        "their snapshots behind in the SOURCE account."
    ),
    (
        "Alternatively the Server Migration Center (SMC) exists for server "
        "moving; this skill has no verified SMC procedure link, so mention "
        "it only as an option to confirm via the official docs or a ticket."
    ),
]

# What the confirmation dialog must say before a CreateSnapshot run.
SNAPSHOT_IMPACT = [
    "What runs: one ECS snapshot-creation request (CreateSnapshot) against "
    "the exact disk id the user supplied.",
    "Impact: a new snapshot appears in the account's snapshot list and "
    "starts incurring snapshot storage fees until it is deleted by a human.",
    "Reversibility: a snapshot is a copy -- deleting it later (manually, "
    "by the customer) removes the backup; creating it never touches the "
    "disk contents.",
]

# ---------------------------------------------------------------------------
# K4 -- post-transfer verification checklist
# ---------------------------------------------------------------------------

POST_TRANSFER_CHECKLIST = [
    {
        "item": "public-ip",
        "text": (
            "The public IP changes: EIPs must be unbound before the transfer "
            "and do NOT follow the instance automatically. To keep a usable "
            "public address, bind a new EIP after the transfer, or transfer "
            "the pay-as-you-go EIP separately -- EIP transfer only works for "
            "post-paid EIPs and, for enterprise sources, only toward an "
            "enterprise account with the identical verified entity name."
        ),
    },
    {
        "item": "snapshots-stay",
        "text": (
            "Snapshots and custom images do NOT move with the instance; they "
            "stay in the source account under ECS console > Storage & "
            "Snapshots > Snapshots. Plan sharing or copying before the "
            "transfer if the new owner needs them."
        ),
    },
    {
        "item": "dns",
        "text": (
            "Every DNS record pointing at the old IP must be updated to the "
            "new one; global propagation can take up to 48 hours. Verify "
            "with the global DNS probe tool linked in references/help-links.md."
        ),
    },
    {
        "item": "third-party-authorization",
        "text": (
            "Third-party platforms whose authorization or whitelists "
            "hard-code the old public IP break the moment the IP changes -- "
            "inventory those integrations before transferring."
        ),
    },
    {
        "item": "icp-filing",
        "text": (
            "Ticket evidence says an already-filed (ICP) domain usually "
            "needs only its DNS record repointed, not a fresh filing, after "
            "the IP changes. This is conservative wording from a phone-only "
            "ticket: always add 'verify against the official ICP filing "
            "rules' and never quote it as certain."
        ),
    },
    {
        "item": "discount-lost",
        "text": (
            "An instance that participated in a discount campaign cannot "
            "take part in discount campaigns again after being transferred "
            "(confirmed backend wording)."
        ),
    },
    {
        "item": "billing-owner",
        "text": (
            "After a successful transfer the new account owns the instance "
            "and its charges; account balances, resource packages and "
            "invoices never move between accounts."
        ),
    },
]

# ---------------------------------------------------------------------------
# K5 -- related products and account rules
# ---------------------------------------------------------------------------

ACCOUNT_RULES = [
    {
        "id": "phone-binding",
        "text": (
            "One mobile phone number may bind at most 6 Alibaba Cloud "
            "accounts -- 'I accidentally registered a second account' is "
            "usually explained by this rule, not a bug."
        ),
    },
    {
        "id": "domain-transfer",
        "text": (
            "Domains DO support account-to-account transfer on a separate "
            "track: online transfer takes effect in real time (domain must "
            "be within validity and real-name verified); offline transfer "
            "needs about 5 working days of review."
        ),
    },
    {
        "id": "database-no-transfer",
        "text": (
            "Managed databases (ApsaraDB RDS and similar) do NOT support "
            "the ECS transfer flow. Identify the symptom and hand off to "
            "the database product line via a ticket; do not improvise a "
            "migration plan for them here."
        ),
    },
    {
        "id": "terminology",
        "text": (
            "'Private IP address' and 'intranet IP address' are the same "
            "thing; clarify when the customer asks."
        ),
    },
    {
        "id": "unsubscribe-refund",
        "text": (
            "Unsubscription and refunds are commercial actions performed by "
            "a human in Billing Management (Orders > unsubscribe) -- this "
            "skill only points to the console entry and never executes or "
            "simulates them."
        ),
    },
    {
        "id": "cancel-and-reregister",
        "text": (
            "'Close the account and register a new one' loses data and can "
            "affect ICP filings; if raised, warn about both risks and refer "
            "to the account-center human process."
        ),
    },
]

# ---------------------------------------------------------------------------
# K7 -- hand-off routing to sibling skills / other product lines
# ---------------------------------------------------------------------------
# Checked in order; transfer-context text stays in scope even when it also
# mentions a routed keyword.

HANDOFF_RULES = [
    {
        "match": ["database", "rds", "polardb", "mongodb", "redis", "云数据库"],
        "route": "database product line (human ticket)",
        "line": (
            "Managed databases do not support the ECS transfer flow; route "
            "to the database product line via a support ticket."
        ),
    },
    {
        "match": ["refund", "unsubscribe", "退订", "invoice", "waive"],
        "route": "Billing Center human support",
        "line": (
            "Refund / unsubscription is a commercial process: point to "
            "Billing Management (Orders) and human support; never simulate "
            "an outcome."
        ),
    },
    {
        "scope_guard": ["transfer", "过户", "account", "entity", "merge",
                        "buy wrong", "wrong account", "过户", "主体"],
        "then": "IN_SCOPE",
    },
    {
        "match": ["expand", "resize", "扩容", "partition", "new disk size",
                  "not taking effect after"],
        "route": "alibabacloud-ecs-disk-expand-diagnosis",
        "line": (
            "Disk expansion / partition not taking effect belongs to the "
            "disk-expand diagnosis skill."
        ),
    },
    {
        "match": ["cannot start", "cannot stop", "stuck in starting",
                  "stuck in stopping", "restart hang", "启停"],
        "route": "alibabacloud-ecs-instance-state-diagnosis",
        "line": (
            "Instance stuck in a start/stop state belongs to the "
            "instance-state diagnosis skill."
        ),
    },
    {
        "match": ["io slow", "slow disk", "iops", "io latency", "磁盘io"],
        "route": "alibabacloud-ecs-disk-io-diagnosis",
        "line": "Disk IO performance issues belong to the disk-io skill.",
    },
]

# ---------------------------------------------------------------------------
# Official help links (only URLs actually quoted inside ticket dialogues;
# no link was invented or completed -- see references/help-links.md)
# ---------------------------------------------------------------------------

HELP_LINKS = {
    "transfer-core": [
        {
            "label": "ECS cross-account transfer (overview + flow anchor "
                      "+ limitations anchor)",
            "url": "https://help.aliyun.com/zh/ecs/user-guide/"
                   "how-to-cross-account-transfer-migration-ecs-instance",
            "anchors": ["#0be63e3029ta3 (transfer flow)",
                        "#babb9b36856x4 (limitations)"],
        },
    ],
    "image-migration": [
        {"label": "Copy a custom image (cross-region first)",
         "url": "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image"},
        {"label": "Use a shared image in the target account",
         "url": "https://help.aliyun.com/zh/ecs/user-guide/use-shared-images"},
        {"label": "Create a snapshot (backup before OS replacement)",
         "url": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot"},
        {"label": "Snapshot storage fees",
         "url": "https://help.aliyun.com/zh/ecs/snapshots-1"},
    ],
    "domain-transfer": [
        {"label": "Domain account transfer, online path",
         "url": "https://help.aliyun.com/document_detail/124001.html#d53627b882rfn"},
        {"label": "Domain account transfer, offline path",
         "url": "https://help.aliyun.com/document_detail/124001.html#a74e034dbfi3q"},
        {"label": "How to move a domain between accounts",
         "url": "https://help.aliyun.com/document_detail/120984.html#8bc770b0a5oqw"},
    ],
    "eip-transfer": [
        {"label": "Transfer a pay-as-you-go EIP across accounts",
         "url": "https://help.aliyun.com/zh/eip/transfer-pay-as-you-go-eip"},
    ],
    "dns": [
        {"label": "Cloud DNS console (update records)",
         "url": "https://dns.console.aliyun.com/#/dns/domainList"},
        {"label": "Modify a DNS record (48h propagation wording)",
         "url": "https://help.aliyun.com/zh/dns/modify-a-dns-record"},
        {"label": "Global DNS probe (verify propagation)",
         "url": "https://boce.aliyun.com/detect/dns"},
    ],
    "account-rules": [
        {"label": "Phone-number binding limit (6 accounts)",
         "url": "https://help.aliyun.com/document_detail/37222.html"},
        {"label": "Account basics and limits",
         "url": "https://help.aliyun.com/document_detail/2977405.html#12d241f9dcjp8"},
    ],
    "weakly-related": [
        {"label": "Start an instance (console)",
         "url": "https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md",
         "note": "post-transfer restart only"},
        {"label": "Restart instances (console)",
         "url": "https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md",
         "note": "post-transfer restart only"},
    ],
    "campaign-entry-pages": [
        {"label": "Benefits page (activity entrances)",
         "url": "https://www.aliyun.com/benefit",
         "note": "quoted verbatim from a 2025-08 ticket with tracking "
                 "parameters stripped; activity pages change over time"},
        {"label": "99-CNY ECS campaign page",
         "url": "https://www.aliyun.com/activity/ecs/99program",
         "note": "same caveat as above"},
    ],
    "missing-verify-manually": [
        {"label": "SMC server migration center procedure",
         "url": "", "note": "no URL evidenced in tickets; verify before use"},
        {"label": "ICP filing change wording",
         "url": "", "note": "no URL evidenced; keep hedged"},
        {"label": "Console direct link for Replace Operating System",
         "url": "", "note": "no URL evidenced; describe the entry instead"},
        {"label": "Unsubscription procedure",
         "url": "", "note": "no URL evidenced; point to Billing Center"},
    ],
}

# ---------------------------------------------------------------------------
# Guest-command capability boundary (NOT enabled in v1)
# ---------------------------------------------------------------------------
# If a future release ever enables in-guest read-only diagnostics, these are
# the hard rules carried from the batch low-risk operation list. v1 must not
# execute any of them.

GUEST_COMMAND_BOUNDARY = {
    "status": "NOT ENABLED in v1 -- no in-guest command is ever executed",
    "whitelist": ["df -h", "df -i", "du", "lsblk", "lsof +L1", "cat /etc/fstab"],
    "rules": [
        "Only one whitelisted, non-mutating command per request, after "
        "telling the user what runs and getting confirmation.",
        "Anything outside the whitelist is refused without exception.",
        "On failure or missing authorization, degrade with STATUS: DEGRADED "
        "and ask the customer to paste the reading instead.",
        "Destructive classes (delete / format / release / detach / refund / "
        "cancel) are never executed or scripted -- human steps only.",
    ],
}

# ---------------------------------------------------------------------------
# Console operation wording (the actual transfer click is the customer's)
# ---------------------------------------------------------------------------

CONSOLE_FLOW_NOTE = (
    "The transfer itself is started and accepted by the customer in the ECS "
    "console transfer flow (source account initiates, target account "
    "accepts; about 30 minutes end to end). This skill deliberately does "
    "NOT automate the transfer: no transfer-initiation OpenAPI appears in "
    "the verified evidence, so nothing is invented here."
)
