#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS burstable instance guide
==========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (API metadata, burstable-instance family rules,
baseline-performance readings, billing mechanics, monitoring guidance and
handoff routes distilled from real support tickets) is embedded here as Python
constants. There are NO data files in this skill.

Evidence discipline: every knowledge entry names its source (official
help.aliyun.com document URLs and/or support-ticket readings). Rules that
depend on versioned facts (rates, console paths, baseline percentages) are
flagged: the current official document version is the final authority and
must be re-verified by a human before release. Numeric credit balances,
advance/excess credit readings and the current performance mode are NOT
machine-verified for this skill: the report tells the customer to read them
in the ECS console / CloudMonitor instead of guessing.
"""

# ---------------------------------------------------------------------------
# Skill identity & API metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-burstable-instance-guide"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "cms": "2019-01-01",
    "sts": "2015-04-01",
}

# Central STS endpoint (region-less).
STS_ENDPOINT = "sts.aliyuncs.com"

# ---------------------------------------------------------------------------
# Timeouts & limits (MUST 7.6.1: every CLI subprocess call passes a timeout)
# ---------------------------------------------------------------------------

# Default per-call timeout in seconds for every aliyun CLI invocation.
DEFAULT_TIMEOUT = 60

# Page size used when enumerating instances (ECS DescribeInstances PageSize).
PAGE_SIZE = 100

# Hard guardrail on pagination loops.
MAX_PAGES = 50

# ---------------------------------------------------------------------------
# Burstable-instance classification rules
# ---------------------------------------------------------------------------
# The FIRST branch of every verdict: is the instance a burstable (t-series)
# instance at all? Detection uses the InstanceTypeFamily field returned by
# DescribeInstances (e.g. "ecs.t5", "ecs.t6"); a family whose name starts with
# "ecs.t" followed by a digit is treated as burstable (t-series). Families
# with confirmed support evidence are listed explicitly; the pattern catches
# later t-series variants instead of fabricating a catalog for them.

BURSTABLE_FAMILIES_EXPLICIT = {"ecs.t5", "ecs.t6"}

# Non-burstable families named in this tier's ticket evidence as the
# upgrade destination ("c5 has no CPU credits and no baseline limit",
# ticket T-BDB55096; c6/c7, g6/g7 recommended there). Any family NOT listed
# as burstable is reported as "not burstable by this rule" with the official
# instance-family document cited for verification.
NON_BURSTABLE_FAMILIES_EVIDENCED = {"ecs.c5", "ecs.c6", "ecs.c7", "ecs.g6", "ecs.g7"}

# Baseline CPU percentage readings that THIS tier's evidence actually
# provides (support-ticket transcripts). Deliberately sparse: per-instance
# baseline values differ per instance type, and inventing a full table would
# violate the no-fabrication rule. When the queried instance type is not in
# this map, the report must say "baseline not machine-verified" and point to
# the console instance detail / official overview document.
BASELINE_PCT_EVIDENCED = {
    # "ecs.t5-c1m2.xlarge": baseline 25% (stated verbatim in tickets
    # T-408C886A and T-BEE1DF3D for that exact type)
    "ecs.t5-c1m2.xlarge": 25.0,
}

# ---------------------------------------------------------------------------
# CloudMonitor constants for the OPTIONAL metric-freshness re-check
# ---------------------------------------------------------------------------
# The namespace/metric pair below is the basic hypervisor-reported CPU usage
# metric for ECS instances; it is used ONLY to re-check whether a queried
# metric carries datapoints (monitoring-visibility symptom, ticket T-094911FC).
# Credit-specific metric identities (exact per-instance credit curves) were
# NOT confirmed by this tier's injected contract: the report therefore tells
# the customer to read credit curves in the console and never fabricates
# credit numbers from this API. See references/burstable-instance-guide__monitoring-setup.md.
CMS_NAMESPACE_ECS = "acs_ecs_dashboard"
CMS_METRIC_CPU = "CPUUtilization"

# ---------------------------------------------------------------------------
# Official documentation links (all URLs come from this tier's injected
# evidence: aliyun-help-search hits and links actually sent by support
# engineers in ticket transcripts). Relative to the doc-version caveat above:
# cite them, never paraphrase rates/paths from memory.
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "burst-overview": "https://help.aliyun.com/zh/ecs/user-guide/burst-performance-instance-overview.md",
    "burst-benefits": "https://help.aliyun.com/zh/ecs/user-guide/benefits-1.md",
    "burst-billing": "https://help.aliyun.com/zh/ecs/user-guide/billing.md",
    "burst-create": "https://help.aliyun.com/zh/ecs/user-guide/create-a-burstable-instance.md",
    "instance-families": "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families.md",
    "general-purpose-families": "https://help.aliyun.com/zh/ecs/user-guide/general-purpose-instance-families.md",
    "instance-overview": "https://help.aliyun.com/zh/ecs/user-guide/overview-52.md",
    "limitations": "https://help.aliyun.com/zh/ecs/user-guide/limitations.md",
    "what-is-ecs": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
    "product-functions": "https://help.aliyun.com/zh/ecs/user-guide/product-function-custom-node-ecs-normal.md",
    "switch-mode": "https://help.aliyun.com/zh/ecs/user-guide/switch-the-performance-mode-of-a-burstable-instance",
    "monitor-burstable": "https://help.aliyun.com/zh/ecs/user-guide/monitor-burstable-instances#title-u46-0k1-kwy",
    "constrained-event": "https://help.aliyun.com/document_detail/143663.html#section-glx-g6x-cn4",
    "credit-examples": "https://help.aliyun.com/document_detail/90635.html#section-vrz-uqg-06z",
    "mode-faq": "https://help.aliyun.com/document_detail/90634.html#related-links-atz-8da-bw4",
    "burst-what-is": "https://help.aliyun.com/document_detail/59977.html#section-6ut-bug-7h0",
    "standard-mode": "https://help.aliyun.com/document_detail/59977.html#af710c5244av5",
    "excess-credit-fee": "https://help.aliyun.com/document_detail/90581.html#section-lqi-vqf-dsc",
    "cost-alert": "https://help.aliyun.com/zh/user-center/cost-alert",
    "cms-agent-install": "https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/install-and-uninstall-the-cloudmonitor-agent-for-cpp",
    "cloud-backup-issues": "https://help.aliyun.com/zh/cloud-backup/support/ecs-file-backup-essential-edition-related-issues/",
    "billing-console": "https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance",
    "snapshot-create": "https://help.aliyun.com/document_detail/25455.html",
    "snapshot-billing": "https://help.aliyun.com/document_detail/56159.html",
}

# ---------------------------------------------------------------------------
# Customer-facing knowledge (topics). Each answer cites its official doc
# link(s); rate/limit values are the ones that appear in this tier's ticket
# evidence and are flagged as "verify against the current official page".
# ---------------------------------------------------------------------------

KNOWLEDGE_TOPICS = {
    "credit-rules": {
        "title": "CPU and disk burst credits: what the performance-constrained alert and the performance-burst fee mean",
        "key_points": [
            "A 'performance burst' fee is not necessarily CPU-side: heavy disk "
            "I/O (formatting a newly attached data disk, mkfs, large copy, "
            "image deployment) above the instance's baseline disk throughput "
            "is converted into IOPS credits and billed even with the vCPU "
            "idle (ticket T-96728BB0: 1T disk format, ~500 MB/s vs 350 MB/s "
            "baseline for ~30 s, ~350k IOPS credits at 0.02 CNY/10k = ~0.5 "
            "CNY). Check the charge timestamp against disk operations before "
            "attributing it to CPU.",
            "A burstable (t-series) instance runs on CPU credits: it accrues "
            "credits while below its baseline CPU utilization and spends them "
            "while above. When credits reach zero in the standard (performance-"
            "constrained) mode the instance is pinned to its baseline "
            "performance. The restriction is triggered by exhaustion, not by "
            "crossing some warning threshold (ticket T-3612BE31).",
            "The 'burstable instance performance constrained' system "
            "notification is about CPU credits only - it does NOT mean memory "
            "or disk is exhausted and it is NOT evidence of an attack "
            "(ticket T-584B88C6). This alert semantics does not apply to the "
            "separate disk-side burst charge described above.",
            "How long the instance stays at baseline depends on the workload "
            "and the credit accrual rate of the specific instance type: while "
            "usage stays below baseline, credits slowly rebuild. Do not quote "
            "a fabricated recovery time; cite the official credit-change "
            "examples.",
            "Baseline is a percentage of the instance's own vCPU capacity: "
            "e.g. a 4-vCPU instance with a 25% baseline can use about the "
            "equivalent of 1 core sustained (ticket T-BEE1DF3D).",
            "In unlimited mode, newly accrued credits are first spent "
            "repaying any advanced (borrowed) credits, so the visible balance "
            "may stay flat even though usage is low (ticket T-E42721B9).",
        ],
        "docs": ["burst-what-is", "credit-examples", "constrained-event", "standard-mode"],
        "verification": "Credit rules are versioned; re-verify against the current official document before quoting numbers to the customer.",
    },
    "billing": {
        "title": "Excess credits on a prepaid (subscription) bill",
        "key_points": [
            "A subscription (prepaid) burstable instance can still carry a "
            "pay-as-you-go line: with the no-performance-constraint (unlimited) "
            "mode ON, after accrued and advanced credits are spent the "
            "instance keeps running above baseline and every extra credit is "
            "billed as an 'excess credits' postpaid charge (tickets "
            "T-2F07C4BD, T-E42721B9).",
            "Rate seen in this tier's ticket evidence: 0.005 CNY per credit "
            "(ticket T-5664EC80). The official excess-credit fee page is the "
            "authority - verify before quoting; the monthly cost depends on "
            "actual CPU usage and duration and CANNOT be computed exactly in "
            "advance.",
            "Spending order in unlimited mode: accrued credits -> advanced "
            "credits -> excess credits (billed). Repayment order when usage "
            "drops: new credits repay advanced credits first.",
            "There is no default real-time alert for excess-credit charges: "
            "the account cost/balance alert and the CloudMonitor credit-"
            "threshold alarm are TWO different features (root cause of tickets "
            "T-6F237607 and T-0495147E). Configure the credit-threshold alarm "
            "for early warning and the cost alert for bill-level warnings.",
            "Bill disputes, refunds, waivers and compensation vouchers are "
            "commercial processes: this read-only skill explains the rules "
            "and hands off to a human ticket.",
        ],
        "docs": ["burst-billing", "excess-credit-fee", "cost-alert", "switch-mode", "billing-console"],
        "verification": "Rates and billing dimensions are versioned; re-verify against the current official pages before quoting.",
    },
    "mode-switch": {
        "title": "Turning the unlimited (no performance constraint) mode on/off - customer console steps",
        "key_points": [
            "Console path stated in ticket evidence: ECS console > Instances "
            "> select the instance > More > Instance Attributes > turn on/off "
            "the no-performance-constraint mode (tickets T-E42721B9, "
            "T-AECC16D7). Always also cite the official switch-mode document; "
            "console menus change with versions.",
            "MANDATORY WARNING BEFORE the customer turns the mode OFF: with "
            "no credits in hand, performance drops to the baseline "
            "immediately; workloads that were running above baseline (web "
            "sites, browsers on the server) become slow or look unreachable "
            "(real lesson of tickets T-2F07C4BD and T-BEE1DF3D).",
            "MANDATORY WARNING BEFORE turning it ON: unlimited mode can "
            "generate excess-credit charges continuously while the load stays "
            "above baseline; keep the credit-threshold alarm and cost alert "
            "configured.",
            "This skill NEVER performs the switch itself: it gives the path, "
            "the risks and the official link; the customer clicks.",
        ],
        "docs": ["switch-mode", "mode-faq", "burst-overview"],
        "verification": "Console paths are versioned; re-verify against the current official document before quoting.",
    },
    "monitoring": {
        "title": "Seeing credits and getting alerts before things break",
        "key_points": [
            "Credit consumption/accrual curves are viewed in the ECS console "
            "monitoring tab or CloudMonitor for the instance, and a "
            "credit-threshold alarm gives advance warning instead of the "
            "'only noticed when the site was down' pattern of ticket "
            "T-584B88C6. Follow the official monitor-burstable-instances "
            "document for the current metric list and alarm setup.",
            "The performance-constrained system notification itself is "
            "documented under ECS instance system events.",
            "If OS-level metrics show a 'collecting' state (no data) the "
            "usual cause is the CloudMonitor agent not being installed - the "
            "customer installs it following the official agent document (this "
            "skill never runs commands inside the instance). "
            "Hypervisor-reported basic CPU keeps working without the agent.",
            "Historical in-guest process attribution is NOT available "
            "cloud-side: the OS performance tools store no history (ticket "
            "T-584B88C6). The customer either inspects the process list AT "
            "the spike moment or deploys their own collector (e.g. atop on "
            "Linux, suggested in tickets). This skill explains, not "
            "executes.",
        ],
        "docs": ["monitor-burstable", "constrained-event", "cms-agent-install"],
        "verification": "Metric lists and console alarm steps are versioned; re-verify against the current official documents.",
    },
    "sizing": {
        "title": "Is upgrading really a fix? Burstable vs non-burstable",
        "key_points": [
            "Upgrading to another instance type INSIDE the t-series does not "
            "remove the credit mechanism - the target still has a baseline "
            "and can be constrained (ticket T-BDB55096: t5 -> t5 stays "
            "limited).",
            "To remove the limitation entirely, change to a non-burstable "
            "family (e.g. compute-optimized c5/c6/c7 or general-purpose "
            "g6/g7): those have no CPU credits and no baseline restriction "
            "(c5 explicitly confirmed in ticket T-BDB55096). The official "
            "instance-family catalog is the authority for any family name.",
            "A spec change requires a restart and takes roughly 3-5 minutes "
            "(11+ if abnormal, ticket T-408C886A): operate in a low-traffic "
            "window, stop the applications first, and create a snapshot "
            "backup before the change. Restart, snapshot and spec change are "
            "all executed by the customer (or via the commercial change "
            "process); this skill only explains the prerequisites and the "
            "rule verdict for the target type.",
            "Deciding 'is the baseline enough for my workload' needs the "
            "customer's own load profile: compare sustained CPU against "
            "baseline-percent x vCPU; the skill supplies the math, the "
            "customer supplies the usage picture.",
        ],
        "docs": ["instance-families", "general-purpose-families", "limitations", "burst-benefits", "snapshot-create"],
        "verification": "Family availability and spec-change timing are versioned; re-verify against the current official pages.",
    },
    "handoff": {
        "title": "What this read-only skill does NOT do (and where it goes instead)",
        "key_points": [
            "In-guest commands (top, resource monitor, installing atop), "
            "agent installation, mode switch, spec change, reboot, snapshot: "
            "the customer performs them; this skill provides steps, risks "
            "and official links only, and re-verifies visible facts "
            "read-only afterwards.",
            "Historical process attribution of a CPU spike: not available "
            "cloud-side; hand-off sentence: 'The cloud side cannot replay "
            "which process consumed CPU in the past; check the OS process "
            "list at the moment of the spike or deploy your own collector.'",
            "Bill refund / waiver / voucher disputes: human ticket (billing "
            "support); the skill only explains the rule behind the charge.",
            "Website or port unreachable AFTER the credit explanation: "
            "usually not caused by baseline throttling alone (ticket "
            "T-DCC05ABE); route to the website/connectivity troubleshooting "
            "track.",
            "Suspected host-level contention (CPU steal, live migration "
            "impact): out of scope; human ticket.",
            "Cloud backup client problems co-occurring with a credit question "
            "are a different area; route to the backup support track.",
        ],
        "docs": ["handoff-note-cloud-backup", "what-is-ecs"],
        "verification": "Routing names reflect this tier's ticket evidence; align with the batch boundary list when it ships.",
    },
}

# Extra doc links used by the handoff topic.
DOC_LINKS["handoff-note-cloud-backup"] = DOC_LINKS["cloud-backup-issues"]

TOPIC_ORDER = ["credit-rules", "billing", "mode-switch", "monitoring", "sizing", "handoff"]

# ---------------------------------------------------------------------------
# Charge-item recognition (customer-visible bill vocabulary)
# ---------------------------------------------------------------------------
# The postpaid line a prepaid burstable instance grows is the "excess
# credits" charge (named in tickets T-2F07C4BD / T-6F237607). Detection is a
# normalized substring match so the customer can paste whatever the bill
# export says; anything credit-related but unmatched asks for the exact
# billing-item label instead of guessing.

EXCESS_CREDIT_CHARGE_TOKENS = ("excess credit", "excesscredit", "excess-credit")
