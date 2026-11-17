#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS preemptible (spot) guide
==========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain (environment or ~/.aliyun/config.json). No AccessKey material
is ever handled by this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (API metadata, query limits, spot-interruption rule
statements, official documentation URLs distilled from the tier evidence
bundle) is embedded here as Python constants. There are NO data files in this
skill.

Rule statements below were distilled from real support tickets and from the
official Alibaba Cloud help documents listed in DOC_URLS. The document URLs
were recorded from the tier evidence bundle (aliyun-help-search snapshot) and
were NOT re-fetched while packaging; re-verify against the live official
documents before quoting version-sensitive values to a customer.
"""

# ---------------------------------------------------------------------------
# Skill identity (observability User-Agent)
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-preemptible-instance-guide"

# User-Agent template attached to every CLI invocation of a run.
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

# ---------------------------------------------------------------------------
# API metadata
# ---------------------------------------------------------------------------

# Central STS endpoint (region-less identity service).
STS_ENDPOINT = "sts.aliyuncs.com"

# ECS is a regional service: the aliyun CLI resolves the ecs.<region>
# endpoint from the --region flag, so no fixed endpoint is pinned for it.

# API versions (informational; the aliyun CLI carries its own metadata and
# related_apis.yaml declares the authoritative popVersion values).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Timeouts and query limits
# ---------------------------------------------------------------------------

# MUST 7.6.1: every CLI subprocess invocation is given this timeout (seconds).
DEFAULT_TIMEOUT = 60

PAGE_SIZE = 50             # page size for DescribeInstanceStatus / DescribeInstances
MAX_PAGES = 10             # hard guardrail for pagination loops
MAX_TARGET_IDS = 10        # max instance ids accepted for one targeted check
MAX_SWEEP_INSTANCES = 200  # max instances enriched with details during a sweep
DESCRIBE_IDS_CHUNK = 50    # instance ids per DescribeInstances chunk call

# ---------------------------------------------------------------------------
# Spot (preemptible) semantics
# ---------------------------------------------------------------------------

# DescribeInstances .Instances[].SpotStrategy values that mark a preemptible
# (spot) instance. "NoSpot" means a regular pay-as-you-go or subscription
# instance.
SPOT_STRATEGIES = ("SpotWithPriceLimit", "SpotAsPriceGo")
NO_SPOT = "NoSpot"
SPOT_STRATEGY_MEANINGS = {
    "NoSpot": "not a preemptible instance (regular pay-as-you-go or subscription)",
    "SpotWithPriceLimit": ("preemptible with a user-defined maximum hourly price "
                           "(bid ceiling); interrupted when the market price "
                           "exceeds the ceiling or when idle inventory changes"),
    "SpotAsPriceGo": ("preemptible priced automatically at the market price; "
                      "interrupted when idle inventory changes or supply/demand "
                      "fluctuates"),
}

# Instance Status values (DescribeInstances / DescribeInstanceStatus).
STATUS_STOPPED = "Stopped"
STATUS_STOPPING = "Stopping"
STATUS_RUNNING = "Running"
TRANSITIONAL_STATUSES = ("Pending", "Starting")

# OperationLocks LockReason token associated with an imminent preemptible
# reclamation in the official DescribeInstances documentation. Matched
# case-insensitively; the raw value is always echoed verbatim as well.
RECYCLING_LOCK_TOKEN = "recycling"

# DescribeAvailableResource .StatusCategory values for a supported resource.
# Raw values are always echoed; the meanings below are the documented ones.
STATUS_CATEGORY_MEANINGS = {
    "WithStock": "in stock - purchasable now",
    "ClosedWithStock": "inventory limited or sale restricted - treat as unreliable",
    "WithoutStock": "sold out - not purchasable at query time",
}
STATUS_CATEGORY_MEANING_FALLBACK = "value echoed as returned by the API (not in the bundled mapping)"

# Inventory verdicts derived by the entry script (pure function).
INVENTORY_IN_STOCK = "SPOT_IN_STOCK"
INVENTORY_LIMITED = "SPOT_LIMITED"
INVENTORY_SOLD_OUT = "SPOT_SOLD_OUT"
INVENTORY_NO_DATA = "SPOT_NO_DATA"

# Instance-check verdicts derived by the entry script (pure function).
VERDICT_SPOT_STOPPED = "SPOT_STOPPED_OR_INTERRUPTED"
VERDICT_SPOT_RUNNING = "SPOT_RUNNING"
VERDICT_SPOT_TRANSITIONAL = "SPOT_TRANSITIONAL"
VERDICT_NOT_SPOT_STOPPED = "NOT_SPOT_STOPPED"
VERDICT_NOT_SPOT_OTHER = "NOT_SPOT_OTHER"
VERDICT_UNKNOWN = "BILLING_TYPE_UNKNOWN"
VERDICT_NOT_FOUND = "INSTANCE_NOT_FOUND"

# ---------------------------------------------------------------------------
# Rule statements (official-doc grounded; echoed in script output verbatim)
# ---------------------------------------------------------------------------

DOC_EVIDENCE_NOTE = (
    "Documentation URLs bundled with this skill were recorded from the tier "
    "evidence bundle (aliyun-help-search snapshot) and were not re-fetched "
    "while packaging; cite the live official document for version-sensitive "
    "values."
)

RULE_MECHANISM = (
    "A preemptible (spot) instance is billed at a heavily discounted, "
    "market-driven price against idle inventory. Alibaba Cloud automatically "
    "interrupts the instance when the market price exceeds the bid ceiling or "
    "when idle inventory changes. What an interruption does to the instance "
    "depends on the interruption mode chosen at creation: 'direct release' "
    "releases the compute resources together with the fixed public IP, the "
    "fixed bandwidth and the cloud disks, while 'stop-charging' reclaims the "
    "compute resources, the fixed public IP and the fixed bandwidth but keeps "
    "the cloud disks, the elastic IP address and the snapshots, which continue "
    "to be billed. The interruption mode cannot be changed after the instance "
    "is created. Usage duration is either a fixed 1-hour guarantee (no "
    "interruption inside the first hour after creation) or 'no guaranteed "
    "duration' (interruptible at any time); once the guaranteed duration is "
    "exceeded the instance is released 5 minutes after the interruption "
    "notice, so the advance notice is the entire reaction window. A released "
    "instance and data on disks that were released together with it cannot be "
    "recovered."
)

# The two interruption modes verbatim from the official spot-instance
# documentation, split out because they decide whether the disks and the
# public address survive an interruption and who keeps paying for them.
RULE_INTERRUPTION_MODES = (
    "Interruption modes (固定为创建时选择，创建后不支持修改): "
    "(1) Direct release (直接释放): the compute resources (vCPU/GPU and "
    "memory), the fixed public IP, the fixed bandwidth and the cloud disks "
    "(system disk and data disks) are all released with the instance, so the "
    "data on those disks goes with it and cannot be recovered. "
    "(2) Stop-charging (节省停机): the compute resources, the fixed public IP "
    "and the fixed bandwidth are reclaimed, while the cloud disks, the "
    "elastic IP address (EIP) and the snapshots are retained and continue to "
    "be billed while they exist. After a stop-charging interruption the "
    "instance may fail to restart, because the inventory of that instance "
    "type in that zone is insufficient or because the floating market price "
    "has risen above the customer's bid."
)

# Guaranteed usage duration (稳定使用时长) chosen at creation.
RULE_USAGE_DURATION = (
    "Guaranteed usage duration (使用时长): either 1 hour - the instance is not "
    "interrupted during the first hour after it is created - or no guaranteed "
    "duration, where the instance can be interrupted at any time. The setting "
    "is fixed at creation and cannot be modified afterwards. Once the "
    "guaranteed duration is exceeded, an interruption notice is sent about 5 "
    "minutes in advance and the instance is released when that window ends; "
    "check the interruption mode first, because only the stop-charging mode "
    "keeps the disks and the EIP."
)

RULE_BALANCE_IRRELEVANT = (
    "Account balance does not prevent interruption: a spot instance can be "
    "reclaimed while the account has sufficient balance. Bidding modes only "
    "address the price trigger - no bidding mode prevents inventory-driven "
    "reclamation."
)

RULE_NOTIFICATION = (
    "Interruption notices are sent to the notification channels bound to the "
    "account (for example the mobile number bound to the primary account) and "
    "read like: your preemptible instance will enter the stopped state due to "
    "inventory changes (wording is localized). Notice delivery time is not the "
    "release time - SMS delivery can lag the actual release. Recipients are "
    "managed by the customer in the Message Center; this skill cannot query "
    "notification delivery records."
)

RULE_ATTRIBUTION_LIMIT = (
    "Which trigger applied (market price above the bid ceiling vs. idle "
    "inventory change) is NOT readable from the whitelisted read-only APIs, "
    "and released instances stop appearing in query results. Do not guess the "
    "trigger: point the customer to the official 'query the interruption "
    "events of preemptible instances' self-check path, ask for the customer's "
    "bidding mode to explain it against the rules, and route platform-side "
    "evidence requests to a support ticket."
)

RULE_DATA_RETENTION = (
    "In the direct-release interruption mode (直接释放), disks of a "
    "preemptible instance are released together with the instance and their "
    "data is deleted. In the stop-charging interruption mode (节省停机) the "
    "cloud disks, the elastic IP address and the snapshots are retained and "
    "keep being billed after the interruption. Protection is prepared BEFORE "
    "an interruption (customer-executed): snapshots or automatic snapshot "
    "policies, disks configured not to be released with the instance, custom "
    "images (which require a system-disk snapshot), or external backups "
    "(OSS/NAS). A retained former system disk can only be re-attached as a "
    "DATA disk of a new instance in the SAME zone. Details: "
    "references/preemptible-instance-guide__ref-data-retention.md."
)

RULE_INVENTORY_SUPPLY = (
    "Preemptible capacity comes from idle inventory. When a zone/type is sold "
    "out, purchase fails and there is no committed restock time - nobody can "
    "promise when supply returns. The Spot Instance Advisor console pages "
    "(real-time and historical data) help the customer pick low-interruption "
    "regions and instance types; details: references/preemptible-instance-guide__ref-inventory-advisor.md."
)

RULE_BILLING_SCOPE = (
    "This skill explains billing SCOPE only and never reads or reconciles "
    "amounts (no billing API is whitelisted). Beyond the spot compute price "
    "(which fluctuates with supply and demand), a bill can also carry public "
    "bandwidth, system/data disk, and disk performance-burst items; the "
    "release day is still billed for the running period, and disks kept after "
    "a stop or released-with-instance=off keep accruing disk fees. Amount "
    "reconciliation, refunds and invoices are handed off; self-check paths: "
    "references/preemptible-instance-guide__ref-billing-scope.md."
)

RULE_SUITABILITY = (
    "Preemptible instances suit stateless, fault-tolerant, interruptible "
    "workloads (elastic web tiers, batch/compute jobs, CI, rendering, test "
    "environments). They are NOT suitable for persistent stateful workloads "
    "such as databases. Architecture design (for example Auto Scaling based "
    "solutions) is out of scope and handed off; details: "
    "references/preemptible-instance-guide__ref-inventory-advisor.md and references/preemptible-instance-guide__ref-handoff.md."
)

RULE_OS_CONFIDENCE = (
    "These mechanism conclusions depend on the billing type and cloud-side "
    "rules only - they are operating-system independent (confidence: high). "
    "Windows-specific interruption-notification behavior carries no bundled "
    "evidence (confidence: low / unverified); do not assert it."
)

# ---------------------------------------------------------------------------
# Official documentation (URLs recorded verbatim from the tier evidence
# bundle; see DOC_EVIDENCE_NOTE above)
# ---------------------------------------------------------------------------

DOC_URLS = {
    "spot-overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/what-is-a-spot-instance.md"),
    "ecs-overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md"),
    "create-spot-instance": (
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-spot-instance.md"),
    "spot-advisor": (
        "https://help.aliyun.com/zh/ecs/user-guide/spot-instance-advisor.md"),
    "data-retention-recovery": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md"),
    "data-retention-numbered": (
        "https://help.aliyun.com/document_detail/439255.html"),
    "interruption-events": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "query-the-interruption-events-of-preemptible-instances.md"),
    "ecs-feature-overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "product-function-custom-node-ecs-normal.md"),
}

# Console / doc entries recorded from real ticket dialogs (agent-provided);
# re-verify before quoting to a customer.
TICKET_DERIVED_ENTRIES = {
    "spot-advisor-realtime-console": (
        "https://ecs.console.aliyun.com/spotAdvisor/realTimeData"),
    "spot-advisor-history-console": (
        "https://ecs.console.aliyun.com/spotAdvisor/historyData"),
    "billing-details-doc": (
        "https://help.aliyun.com/zh/ecs/view-billing-details#title-jx3-hqs-6hn"),
}
