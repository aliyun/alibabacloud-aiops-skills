#!/usr/bin/env python3
"""
_constants.py -- Embedded static knowledge for the ECS disk type &
performance-level change guide
===========================================================================
SECURITY BOUNDARY: this skill changes NO cloud resource and writes NOTHING
inside any instance. Cloud access is Describe / List / Get queries only; the
single dispatching action it can use is RunCommand, and only for the fixed
allowlist of non-mutating guest diagnostics defined below, after the customer
was told which command runs and confirmed that one call. Everything else is
handed to the customer as manual steps. This module contains no credentials
and performs no I/O of any kind. Authentication, wherever the skill queries
the cloud, is resolved exclusively by the aliyun CLI default credential chain.

Per platform rule 1.1.2 the scripts/ directory may only contain executable
code, so every table (performance formulas, change matrix, console steps,
guest command allowlist, alert glossary, FAQ knowledge, handoff boundaries,
document library) is embedded here as a Python constant. There are no data
files.

Provenance discipline: numeric ceilings and rules below carry a provenance
tag and, where available, the source support ticket whose customer-service
reply states the number. Values tagged "official-pattern" or "derived" come
from the published block-storage specification pages referenced in
references/disk-pl-change-guide__performance-formulas.md. The live console display and the cited
official page are always the final authority; this skill quotes them, never
invents them.
"""

# ---------------------------------------------------------------------------
# Skill identity & call mechanics
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-disk-pl-change-guide"

# Per-call subprocess timeouts (platform rule 7.6.1: every CLI call is bounded).
DEFAULT_TIMEOUT = 60
HEAVY_CALL_TIMEOUT = 120

# API versions actually used (informational; the aliyun CLI carries metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "cms": "2019-01-01",
    "sts": "2015-04-01",
}

# Pagination guardrails.
MAX_RESULTS = 50
MAX_PAGES = 10

# Cloud Assistant dispatch bounds for the allowlisted guest diagnostics:
# at most GUEST_POLL_MAX polls of GUEST_POLL_INTERVAL seconds each, so one
# confirmation can never hold the script longer than ~60s of waiting.
GUEST_POLL_INTERVAL = 5
GUEST_POLL_MAX = 12
# The command itself is capped at this many seconds inside the guest.
GUEST_COMMAND_TIMEOUT = 30
# Relayed command output is truncated to this many characters.
GUEST_OUTPUT_LIMIT = 4000

# Best-effort region inference from an `d-<prefix>...` / `i-<prefix>...`
# resource-id prefix. Only the well-known mainland prefixes are modeled; an
# unknown prefix must be asked, never guessed.
ZONE_PREFIX_REGIONS = {
    "bp": "cn-hangzhou",
    "2ze": "cn-beijing",
    "uf": "cn-shanghai",
    "wz": "cn-shenzhen",
    "8vb": "cn-zhangjiakou",
    "hnd": "ap-northeast-1",
    "t4n": "ap-southeast-1",
}

# ---------------------------------------------------------------------------
# Disk categories & performance levels
# ---------------------------------------------------------------------------

# DescribeDisks `Category` value -> canonical English display name.
CATEGORY_NAMES = {
    "cloud_efficiency": "Ultra disk (efficient cloud disk)",
    "cloud_ssd": "SSD disk",
    "cloud_essd": "ESSD (Performance Level PL0/PL1/PL2/PL3)",
    "cloud_essd_entry": "ESSD Entry disk",
    "cloud_auto": "ESSD AutoPL disk",
    "cloud_regional_disk_auto": "Regional ESSD disk",
    "cloud": "Basic disk",
    "cloud_essd_pl0": "ESSD PL0 disk (legacy category token)",
    "cloud_auto_perf": "ESSD AutoPL disk (performance-suffix token)",
}

# Categories that carry a fixed performance level in `PerformanceLevel`.
FIXED_PL_CATEGORY = "cloud_essd"

PL_RANK = {"PL0": 0, "PL1": 1, "PL2": 2, "PL3": 3}

# ---------------------------------------------------------------------------
# Per-disk IOPS / throughput ceilings, capacity c in GiB
# ---------------------------------------------------------------------------
# Each curve is {"base": b, "per_gib": s, "cap": N} meaning
#     ceiling(c) = min(b + s * c, N)   (cap None = no cap column modeled).
# Provenance levels:
#   "ticket-verified"  -- the exact number appears in a real support-ticket
#                         customer-service reply or customer calculation.
#   "official-pattern" -- published block-storage specification pages
#                         (see references/disk-pl-change-guide__performance-formulas.md).
#   "derived"          -- consistent with the published pattern but not seen
#                         verbatim; confirm against the official page before
#                         quoting the number to the customer.

PERF_FORMULAS = {
    "cloud_essd_entry": {
        "label": "ESSD Entry",
        "iops": {
            "base": 1800, "per_gib": 8, "cap": None,
            "provenance": "ticket-verified",
            "evidence": ("1800 + 8 * capacity: 100 GiB -> 2600 IOPS "
                         "(ticket T-DA6C3114); 40 GiB -> 2120 IOPS "
                         "(customer calculation in ticket T-EE75C111)"),
        },
        "throughput_mbps": {
            "base": 100, "per_gib": 0.25, "cap": 150,
            "provenance": "derived",
            "evidence": "ESSD Entry throughput curve on the official specs page",
        },
    },
    "PL0": {
        "label": "ESSD PL0",
        "iops": {
            "base": 1800, "per_gib": 12, "cap": 10000,
            "provenance": "ticket-verified",
            "evidence": ("min(1800 + 12 * capacity, 10000): 100 GiB -> 3000 "
                         "IOPS; ~684 GiB needed to reach the 10000 cap "
                         "(ticket T-B525FD49)"),
        },
        "throughput_mbps": {
            "base": 100, "per_gib": 0.25, "cap": 180,
            "provenance": "ticket-verified",
            "evidence": ("min(100 + 0.25 * capacity, 180): 100 GiB -> 125 "
                         "MB/s, 200 GiB -> 150 MB/s (customer calculation "
                         "confirmed in ticket T-CC0FA37F)"),
        },
    },
    "PL1": {
        "label": "ESSD PL1",
        "iops": {
            "base": 1800, "per_gib": 50, "cap": 50000,
            "provenance": "official-pattern",
            "evidence": "published ESSD spec table",
        },
        "throughput_mbps": {
            "base": 120, "per_gib": 0.5, "cap": 350,
            "provenance": "official-pattern",
            "evidence": "published ESSD spec table",
        },
    },
    "PL2": {
        "label": "ESSD PL2",
        "iops": {
            "base": 1800, "per_gib": 50, "cap": 100000,
            "provenance": "official-pattern",
            "evidence": "published ESSD spec table",
        },
        "throughput_mbps": {
            "base": 120, "per_gib": 0.5, "cap": 750,
            "provenance": "ticket-verified",
            "evidence": ("the 750 MB/s PL2 ceiling was discussed in ticket "
                         "T-39B4EB79 (and proved NOT to be the binding "
                         "limit there -- the instance bandwidth was)"),
        },
    },
    "PL3": {
        "label": "ESSD PL3",
        "iops": {
            "base": 1800, "per_gib": 50, "cap": 1000000,
            "provenance": "official-pattern",
            "evidence": "published ESSD spec table",
        },
        "throughput_mbps": {
            "base": 120, "per_gib": 0.5, "cap": 4000,
            "provenance": "official-pattern",
            "evidence": "published ESSD spec table",
        },
    },
    "cloud_efficiency": {
        "label": "Ultra disk (efficient cloud disk)",
        "iops": {
            "base": 1800, "per_gib": 8, "cap": 5000,
            "provenance": "ticket-verified",
            "evidence": ("cap 5000 IOPS corroborated by the customer table "
                         "in ticket T-DA6C3114 (800 GiB -> 5000); growth "
                         "coefficient per the official page - verify before "
                         "quoting mid-curve values"),
        },
        "throughput_mbps": {
            "base": 100, "per_gib": 0.15, "cap": 140,
            "provenance": "official-pattern",
            "evidence": "published ultra-disk spec table",
        },
    },
    "cloud_ssd": {
        "label": "SSD disk",
        "iops": {
            "base": None, "per_gib": None, "cap": 25000,
            "provenance": "official-pattern",
            "evidence": "SSD disk ceiling is a fixed maximum (no growth curve modeled)",
        },
        "throughput_mbps": {
            "base": None, "per_gib": None, "cap": 300,
            "provenance": "official-pattern",
            "evidence": "SSD disk ceiling is a fixed maximum (no growth curve modeled)",
        },
    },
}

# ESSD AutoPL: capacity and performance are DECOUPLED; quoting a single
# formula would be wrong. The caliber rule below is the ticket-verified
# statement of how to read the limits.
AUTOPPL_NOTES = {
    "label": "ESSD AutoPL",
    "iops": {
        "base": 1800, "per_gib": 50, "cap": 50000,
        "provenance": "derived",
        "evidence": ("baseline curve follows the published AutoPL page; "
                     "pre-provisioned IOPS is purchased separately and "
                     "raises the usable baseline, burst is an independent "
                     "ceiling above it -- always read BOTH from the disk's "
                     "own console row, never compute them here"),
    },
    "throughput_mbps": {
        "base": 120, "per_gib": 0.5, "cap": 350,
        "provenance": "derived",
        "evidence": "baseline throughput curve; burst ceiling per the official AutoPL page",
    },
}

CALIBER_RULE = (
    "ESSD AutoPL dual caliber: if performance burst is NOT enabled, the "
    "baseline ceiling (which includes any pre-provisioned IOPS shown on the "
    "disk row) applies; if burst IS enabled, the burst ceiling applies for "
    "short peaks. Steady workloads fit the fixed-PL ESSD series; volatile "
    "spiky workloads fit AutoPL. (customer-service answer in ticket "
    "T-851CC73C)"
)

# Instance-side storage bandwidth: the binding limit is the SMALLER of the
# instance-spec ceiling and the disk ceiling. The per-instance-type numbers
# live in the official instance-family spec table, which is why the script
# reports the family and points there instead of guessing.
INSTANCE_BANDWIDTH_RULE = {
    "rule": (
        "Actual usable disk bandwidth/IOPS = min(instance-type storage "
        "bandwidth ceiling, per-disk performance ceiling). Raising the disk "
        "PL only helps while the disk is the smaller side."
    ),
    "example": (
        "Worked example (ticket T-39B4EB79): ecs.u1-c1m2.4xlarge carries a "
        "3 Gbit/s storage bandwidth baseline = 3000/8 = 375 MB/s. The disk "
        "was already ESSD PL2 (750 MB/s disk ceiling), so every throughput "
        "alert was caused by the INSTANCE side, not by the disk level."
    ),
    "bit_to_byte": "divide Gbit/s by 8 to get MB/s (1 byte = 8 bits)",
}

# Alert-code glossary (customer-visible alert reason codes).
ALERT_GLOSSARY = {
    "EcsBaseBPS": {
        "meaning": (
            "The alert was triggered by the instance-type baseline storage "
            "bandwidth ceiling, NOT by the cloud disk performance being "
            "exhausted."
        ),
        "fix": (
            "Change (upgrade) the instance type to raise the instance-side "
            "bandwidth ceiling; changing the disk performance level will "
            "not help once the instance side is the smaller value."
        ),
        "evidence": "diagnosis in ticket T-39B4EB79",
    },
}

# ---------------------------------------------------------------------------
# Change matrix: allowed directions & one-way rules
# ---------------------------------------------------------------------------
# verdicts: ALLOWED_ONLINE / ALLOWED / DENIED_ONE_WAY / VERIFY_OFFICIAL /
#           NOT_APPLICABLE

CHANGE_MATRIX_RULES = [
    {
        "id": "essd-pl-up",
        "transition": "ESSD fixed PL -> higher fixed PL (e.g. PL0 to PL1)",
        "verdict": "ALLOWED_ONLINE",
        "note": ("online operation, no instance restart; expect brief IO "
                 "fluctuation, run off-peak; take a snapshot first "
                 "(ticket T-984F24BA)"),
    },
    {
        "id": "essd-pl-down",
        "transition": "ESSD fixed PL -> lower fixed PL (downgrade)",
        "verdict": "VERIFY_OFFICIAL",
        "note": ("upgrade is confirmed online-capable; for a downgrade "
                 "direction confirm availability on the console change page "
                 "and the official ESSD page before promising it"),
    },
    {
        "id": "pl-to-autopl",
        "transition": "ESSD fixed PL / Entry -> ESSD AutoPL",
        "verdict": "ALLOWED",
        "note": ("supported; irreversible in the other direction -- once on "
                 "AutoPL the disk can never go back to a fixed PL "
                 "(ticket T-B525FD49); data is preserved, snapshot first"),
    },
    {
        "id": "autopl-to-pl",
        "transition": "ESSD AutoPL -> PL0 / PL1 / any fixed PL",
        "verdict": "DENIED_ONE_WAY",
        "note": ("ESSD AutoPL disks do NOT support changing back to PL0 or "
                 "PL1 (verbatim rule from ticket T-B525FD49): once a disk "
                 "was changed from PL0 to AutoPL it cannot be switched "
                 "back to a fixed performance level"),
    },
    {
        "id": "autopl-category-change",
        "transition": "ESSD AutoPL -> other disk CATEGORY (e.g. ultra/SSD)",
        "verdict": "DENIED_ONE_WAY",
        "note": "same one-way boundary as the AutoPL-to-PL rule; verify on the console entry",
    },
    {
        "id": "efficiency-to-essd",
        "transition": "Ultra disk (efficient cloud disk) / SSD disk -> ESSD family (PL0/PL1/... )",
        "verdict": "ALLOWED_ONLINE",
        "note": ("data is preserved by the online category change; take a "
                 "snapshot before proceeding (asked in ticket T-584A7DD3); "
                 "system disk and data disk differ in which PLs are "
                 "selectable - the console shows the applicable set "
                 "(ticket T-E10A0001)"),
    },
    {
        "id": "essd-to-efficiency",
        "transition": "ESSD family -> Ultra disk / SSD disk (reverse category change)",
        "verdict": "VERIFY_OFFICIAL",
        "note": "the category-change page lists currently supported source/target pairs; confirm there",
    },
    {
        "id": "entry-to-fixed-pl",
        "transition": "ESSD Entry -> ESSD PL0/PL1 (upgrade out of Entry)",
        "verdict": "VERIFY_OFFICIAL",
        "note": ("commonly raised after hitting the low Entry ceiling "
                 "(40 GiB Entry = 2120 IOPS, ticket T-EE75C111); confirm the "
                 "exact source/target pair on the console change entry"),
    },
    {
        "id": "regional-excluded",
        "transition": "Regional ESSD (cloud_regional_disk_auto)",
        "verdict": "NOT_APPLICABLE",
        "note": "regional ESSD disks follow their own spec/limit page and are excluded from the ordinary change matrix",
    },
    {
        "id": "capacity-shrink",
        "transition": "Reduce disk capacity (e.g. 700 GiB -> 400 GiB)",
        "verdict": "NOT_APPLICABLE",
        "note": "capacity shrinking is a different symptom area; hand off per references/disk-pl-change-guide__handoff-boundaries.md (ticket T-E10A0001)",
    },
]

# ---------------------------------------------------------------------------
# Change impact statements (translated customer-service wording, tickets cited)
# ---------------------------------------------------------------------------

IMPACT_NOTES = [
    ("ESSD performance-level upgrade is an ONLINE operation; the instance "
     "does NOT need to be restarted. During the change there may be brief "
     "IO read/write fluctuation, so run it in an off-peak window. Take a "
     "snapshot before operating. (ticket T-984F24BA)"),
    ("Apart from the brief IO fluctuation during the change window, a "
     "performance-level upgrade has no other impact on the running "
     "instance, remote connections, or data integrity. (ticket T-984F24BA)"),
    ("A category change (e.g. ultra disk -> ESSD) keeps the existing data; "
     "the recommended sequence is always snapshot first, then change. "
     "(tickets T-584A7DD3 / T-984F24BA)"),
    ("Type and performance-level changes are asynchronous tasks: after "
     "submitting, watch progress in the ECS task list and re-verify with "
     "this skill (verify mode) once the task reports success."),
    ("Price difference / refund amounts are NOT quoted by this skill. "
     "Estimate in the official pricing calculator or contact your sales "
     "manager (tickets T-8FCE8F40 / T-F7B7C8A6)."),
]

# Manual console steps (the skill NEVER performs the change itself).
CONSOLE_STEPS = {
    "create-snapshot-first": [
        "ECS console -> Storage & Snapshots -> Snapshots -> Create Snapshot.",
        "Select the target disk, give the snapshot a recognizable name.",
        "Wait until the snapshot status is 'accomplished' before changing.",
        "Doc: https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    ],
    "change-performance-level": [
        "ECS console -> Storage & Snapshots -> Disks -> locate the disk "
        "(d-xxxx).",
        "Open the change / performance-level entry in the Actions column.",
        "Select the target performance level; the page shows the resulting "
        "IOPS / throughput ceiling -- read it from there.",
        "Confirm; the change runs online without a restart; watch the async "
        "task in the ECS task list.",
        "Doc: https://help.aliyun.com/zh/ecs/user-guide/essds",
    ],
    "change-category": [
        "ECS console -> Storage & Snapshots -> Disks -> locate the disk.",
        "Choose the change-category entry; pick the target category "
        "(e.g. ESSD PL0).",
        "Read the on-page constraints for system vs data disks before "
        "confirming.",
        "Doc: https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk",
        "System vs data disk difference anchor: "
        "https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk#2c5e068047vd3",
    ],
    "watch-async-task": [
        "ECS console -> O&M & Monitoring -> Task Management (async tasks) "
        "shows the change task progress.",
        "Doc: https://help.aliyun.com/zh/ecs/user-guide/ecs-task-management.md",
    ],
    "stop-autopl-burst-guide": [
        "Burst billing / disabling performance burst is a billing-area "
        "action the CUSTOMER performs; guide to:",
        "https://www.alibabacloud.com/help/zh/ecs/user-guide/modify-the-performance-configurations-of-an-essd-autopl-disk#title-o4i-xnc-cbf",
        "This skill neither performs nor promises any billing outcome.",
    ],
}

# ---------------------------------------------------------------------------
# In-guest diagnostics (capability C5): allowlisted non-mutating commands
# ---------------------------------------------------------------------------
# HARD RULE: the ONLY commands this skill dispatches into an instance are the
# fixed entries of GUEST_COMMAND_ALLOWLIST, one per confirmation, and only
# after the customer was told which command runs on which instance, what it
# touches, and that it writes nothing. Everything outside the allowlist
# (installing tools, reading log CONTENT, continuous monitors) is refused and
# converted into a customer-run step. No free-form command string, path or
# argument is ever accepted from the caller — a key selects a full command.

GUEST_SHELL_TYPE = "RunShellScript"

GUEST_COMMAND_ALLOWLIST = {
    "disk-usage": {
        "command": "df -h",
        "scope": "every mounted filesystem of the instance",
        "effect": "prints filesystem size and usage; opens no file for writing",
        "reversible": "writes nothing, so there is nothing to undo",
        "why": "fill level around a suspected disk problem",
    },
    "mount-table": {
        "command": "findmnt",
        "scope": "the kernel mount table",
        "effect": "prints which block device backs which path",
        "reversible": "writes nothing, so there is nothing to undo",
        "why": "mount-point caliber check (which disk the guest really sees)",
    },
    "stat-root-fs": {
        "command": "stat /",
        "scope": "metadata of the root filesystem entry",
        "effect": "prints inode/metadata attributes of one path",
        "reversible": "writes nothing, so there is nothing to undo",
        "why": "device backing and filesystem attributes of the root mount",
    },
    "atop-logs-present": {
        "command": "ls /var/log/atop",
        "scope": "one directory listing",
        "effect": "lists filenames only; opens no file content",
        "reversible": "writes nothing, so there is nothing to undo",
        "why": ("whether atop ever recorded anything for the incident window "
                "(the path the human agents used in tickets T-EE75C111 / "
                "T-CB4F17DF / T-CC0FA37F); reading those logs stays with the "
                "customer"),
    },
    "system-log-size": {
        "command": "wc -l /var/log/messages",
        "scope": "one system log file",
        "effect": "counts lines only; the log content is not printed",
        "reversible": "writes nothing, so there is nothing to undo",
        "why": ("how much log exists for the OOM / incident check requested in "
                "ticket T-CB4F17DF; judging the content needs the customer's "
                "own grep and paste"),
    },
}

# Announce-before-execution notice (mandatory, printed when --confirm is absent).
GUEST_ANNOUNCE_TEMPLATE = (
    "About to dispatch ONE command to instance {instance_id} through Cloud "
    "Assistant: `{command}`. Scope: {scope}. Effect: {effect}. Reversibility: "
    "{reversible}. Purpose: {why}. This confirmation covers this single "
    "command on this single instance only; every further command requires a "
    "fresh confirmation. Reply 'confirm' to run it, or 'no' and you get the "
    "same command as a self-check step to run yourself."
)

# Outside the allowlist -> never dispatched, whatever the customer asks for.
GUEST_COMMAND_REFUSALS = [
    ("atop / any package install", "installing a tool changes the system and is "
     "outside this skill's boundary", "customer installs it per the atop doc, "
     "then this skill can only check whether logs exist"),
    ("top / tload / continuous monitors", "interactive long-running process, "
     "not a one-shot listing", "customer runs it and pastes a screenshot"),
    ("lsblk -d -o name,rota", "guest device-model / rotational flag is not in "
     "the allowlist", "customer pastes the reading (ticket T-0F3C602D path); "
     "unexplained cases escalate to human support"),
    ("iostat / sar", "not in the allowlist", "customer pastes the reading; the "
     "reading rules below then apply"),
    ("grep / cat / tail of log CONTENT", "reading log bodies is content "
     "access outside the allowlist", "customer greps OOM / slow log / access "
     "log and pastes the excerpt"),
    ("any cleanup, restart, config edit, formatting, snapshot or agent "
        "install inside the guest", "mutating", "manual console or in-guest "
     "steps performed by the customer, with the risk statement"),
]

REFUSE_WORDING = (
    "This command is not in the low-risk allowlist of this skill, so the "
    "skill will not dispatch it. Run it yourself and paste the output; I "
    "will interpret what you paste."
)

# Self-service list for everything the allowlist refuses (customer-run).
GUEST_IO_ATTRIBUTION_COMMANDS = [
    "lsblk -d -o name,rota      # does the guest flag the disk as rotational? (T-0F3C602D)",
    "iostat -x 1 5              # %util vs await per device (T-4F5CBA0C reading)",
    "atop                       # per-process IO attribution across a repro window (install per the atop doc)",
    "grep -i 'out of memory\\|oom' /var/log/messages   # OOM evidence (T-CB4F17DF)",
    "# plus: database slow log, web access log around the incident window",
]

ATOP_DOCS = [
    "https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools",
    "https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics",
]

GUEST_DEGRADED_WORDING = (
    "The in-guest evidence could not be collected (Cloud Assistant offline, "
    "the call was refused, or no confirmation was given). Nothing was "
    "executed inside the instance. Falling back to: the customer runs the "
    "listed command and pastes the reading."
)

# How to read pasted iostat output (ticket-verified interpretation).
IOSTAT_READING_RULES = [
    ("High %util (97-99%) together with LOW await (e.g. 0.47-0.53 ms) means "
     "the disk is BUSY but still RESPONDING FAST -- typical of random-read "
     "workloads such as MongoDB; it is NOT by itself a performance "
     "bottleneck. (ticket T-4F5CBA0C)"),
    ("Suspect the disk only when throughput/IOPS readings sit AT the "
     "per-disk ceiling computed from the capacity formula, or when await "
     "grows together with high util."),
    ("When measured throughput is far below BOTH the disk ceiling and the "
     "instance ceiling, the cause is workload behavior inside the guest -- "
     "hand the customer the self-check list above."),
]

# ---------------------------------------------------------------------------
# FAQ knowledge (each answer grounded in the cited ticket / official page)
# ---------------------------------------------------------------------------

FAQ_TOPICS = {
    "why-iops-lower-than-doc": {
        "question": "Why is my disk IOPS limit lower than the number in the docs?",
        "answer": (
            "The big numbers in the spec tables are the CEILINGS a disk "
            "reaches only at large capacity. Per-disk IOPS/throughput grow "
            "LINEARLY with size and then stop at the per-level cap. "
            "Examples: ESSD Entry 100 GiB -> 1800+8*100 = 2600 IOPS "
            "(ticket T-DA6C3114); ESSD PL0 100 GiB -> min(1800+12*100, "
            "10000) = 3000 IOPS, and reaching the 10000 cap needs about "
            "684 GiB (ticket T-B525FD49). Run the assess mode against the "
            "real disk size to see the exact expected ceiling."
        ),
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/essds"],
    },
    "autopl-caliber": {
        "question": "Which IOPS number counts for my AutoPL disk - baseline plus burst?",
        "answer": CALIBER_RULE,
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/essd-autopl-disks.md"],
    },
    "autopl-one-way": {
        "question": "Can I change an AutoPL disk back to PL0/PL1?",
        "answer": (
            "No. ESSD AutoPL disks do not support changing back to PL0 or "
            "PL1: once a disk was changed from PL0 to AutoPL, it can never "
            "be switched back to a fixed performance level. Treat the move "
            "to AutoPL as one-way before deciding. (ticket T-B525FD49)"
        ),
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/essd-autopl-disks.md"],
    },
    "change-impact": {
        "question": "Does changing performance level / disk type affect the running business or the data?",
        "answer": (
            "Performance-level upgrade runs online without a restart; a "
            "brief IO fluctuation is possible during the change window, so "
            "operate off-peak and take a snapshot first. Apart from that "
            "fluctuation there is no impact on the instance, connections, "
            "or data integrity. (ticket T-984F24BA)"
        ),
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot"],
    },
    "upgraded-pl-still-alerts": {
        "question": "I already raised the disk to PL2 but disk-performance alerts keep firing.",
        "answer": (
            "Check the alert reason code. An EcsBaseBPS alert is triggered "
            "by the INSTANCE-TYPE baseline storage bandwidth, not by the "
            "disk. Usable throughput = min(instance bandwidth ceiling, disk "
            "ceiling): a PL2 disk (750 MB/s) on ecs.u1-c1m2.4xlarge "
            "(3 Gbit/s = 375 MB/s) is capped at 375 MB/s by the instance. "
            "Fix = change to a larger instance type, not a higher PL. "
            "(ticket T-39B4EB79)"
        ),
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families#u1"],
    },
    "util-100-percent": {
        "question": "The OS shows the disk near 100% load but monitoring IOPS is low - is the disk broken?",
        "answer": IOSTAT_READING_RULES[0],
        "docs": [],
    },
    "bps-hang": {
        "question": "My server freezes and I suspect throughput is capped at the disk limit.",
        "answer": (
            "First compute the disk's own ceiling: e.g. ESSD PL0 throughput "
            "= min(100+0.25*capacity, 180) MB/s, so a 100 GiB PL0 tops out "
            "near 125 MB/s and a period of exactly-flat ~133 MB/s reads "
            "means the disk ceiling was saturated and the server can hang "
            "while saturated (ticket T-CC0FA37F). Raising to PL1 lifts the "
            "ceiling to ~170 MB/s, but BEFORE deciding, identify WHO issues "
            "the IO: install atop in the guest, reproduce, and analyze the "
            "atop log (customer-executed). This skill can also check the "
            "cloud-side ceilings and instance bandwidth in bottleneck mode."
        ),
        "docs": ATOP_DOCS,
    },
    "rota-flag": {
        "question": "lsblk shows my AutoPL/ESSD disk with rota=1 (as a rotational disk). Is it an HDD?",
        "answer": (
            "No: ESSD AutoPL / ESSD disks are SSD-backed; a rota=1 flag "
            "seen inside the guest is a guest-side device-identification "
            "anomaly worth investigating (it can disable IO-scheduler "
            "optimizations). This skill cannot execute lsblk inside the "
            "instance; the customer pastes the reading, and unexplained "
            "cases are escalated to human support - in ticket T-0F3C602D "
            "this exact question was escalated to a specialist."
        ),
        "docs": [],
    },
    "snapshot-first": {
        "question": "Will I lose data changing disk type or performance level?",
        "answer": IMPACT_NOTES[2],
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot"],
    },
    "entry-vs-pl": {
        "question": "ESSD Entry vs PL0 - which one do I have and what is the real difference?",
        "answer": (
            "Entry: IOPS = 1800 + 8*capacity with a much lower ceiling "
            "(40 GiB Entry = 2120 IOPS, ticket T-EE75C111). PL0: IOPS = "
            "min(1800 + 12*capacity, 10000). DescribeDisks (assess mode) "
            "shows the exact Category + PerformanceLevel of the disk. When "
            "a workload keeps saturating the Entry ceiling, the usual move "
            "is upgrading the performance level (or to AutoPL - remember "
            "that direction is one-way)."
        ),
        "docs": ["https://help.aliyun.com/zh/ecs/user-guide/essds"],
    },
    "pricing": {
        "question": "How much does the upgrade cost / can you quote the price?",
        "answer": (
            "Quoting prices is out of this skill's scope: after-sales "
            "support and this skill cannot produce a binding quote. Use "
            "the official pricing calculator on the buy page or contact "
            "your sales manager. (tickets T-8FCE8F40 / T-F7B7C8A6)"
        ),
        "docs": [],
    },
}

# ---------------------------------------------------------------------------
# Handoff boundaries (symptom areas this skill identifies but does NOT treat)
# ---------------------------------------------------------------------------

HANDOFF_BOUNDARIES = [
    {
        "area": "Quotation / price of a configuration / pre-sales pricing",
        "handoff": "pricing calculator on the buy page, or the sales manager (commercial channel)",
        "never": "quote amounts or discounts",
        "evidence": "tickets T-8FCE8F40 / T-F7B7C8A6 / T-EB568736",
    },
    {
        "area": "Instance CPU/memory spec change (upgrade or downgrade the instance type)",
        "handoff": "instance-spec-change flow; docs in DOC_LINKS (change-the-instance-types...)",
        "never": "perform or promise any spec change",
        "evidence": "ticket T-A89C6F2F; note this skill DOES name instance bandwidth as a bottleneck layer",
    },
    {
        "area": "Capacity expansion or shrinking of the disk size",
        "handoff": "disk-resize flow (expansion: ResizeDisk docs; shrinking: the FAQ with the two replacement schemes)",
        "never": "execute resizing; capacity only feeds the ceiling formulas here",
        "evidence": "tickets T-E10A0001 / T-A89C6F2F",
    },
    {
        "area": "Unsubscribe / refund / stop-billing of a disk",
        "handoff": "billing channel: convert to pay-as-you-go, detach, then release per the docs (customer console actions)",
        "never": "touch billing; warn about data loss before any release",
        "evidence": "ticket T-BD63C308",
    },
    {
        "area": "AutoPL burst post-paid billing disputes and turning burst off",
        "handoff": "billing channel + the burst-config doc in CONSOLE_STEPS",
        "never": "compensate or disable anything",
        "evidence": "ticket T-9674C108",
    },
    {
        "area": "Custom images containing data disks; lightweight-server to ECS migration",
        "handoff": "image / migration flows",
        "never": "create or share images",
        "evidence": "tickets T-9C799442 / T-6A3314C0",
    },
    {
        "area": "Per-process IO attribution inside the guest (atop/iostat/slow-log/OOM reading)",
        "handoff": "the allowlisted listing commands can be dispatched after confirmation; the attribution tools themselves are run by the customer, who pastes readings (GUEST_IO_ATTRIBUTION_COMMANDS); unexplained cases -> human support",
        "never": "dispatch anything outside GUEST_COMMAND_ALLOWLIST",
        "evidence": "tickets T-EE75C111 / T-0F3C602D / T-CB4F17DF / T-CC0FA37F",
    },
    {
        "area": "Whether a platform-side background migration / replica rebuild happened",
        "handoff": "human support ticket escalation (no cloud query API exposes it)",
        "never": "assert platform-side causes without evidence",
        "evidence": "tickets T-0F3C602D / T-CB4F17DF / T-CC0FA37F",
    },
    {
        "area": "Windows instance in-guest diagnosis",
        "handoff": "human support (the ticket evidence behind this skill is Linux/console-only; no Windows guest guidance is claimed)",
        "never": "promise Windows guest-side flows",
        "evidence": "requirements doc: no Windows ticket evidence in this tier",
    },
]

# ---------------------------------------------------------------------------
# Document library (every URL is evidence-backed: injected help-search hits or
# URLs a human agent actually quoted in a ticket; verify reachability when citing)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "change-category": "https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk.md",
    "change-category-sys-vs-data": "https://help.aliyun.com/zh/ecs/user-guide/change-the-category-of-a-disk#2c5e068047vd3",
    "essd-autopl": "https://help.aliyun.com/zh/ecs/user-guide/essd-autopl-disks.md",
    "block-storage-overview": "https://help.aliyun.com/zh/ecs/user-guide/elastic-block-storage-devices.md",
    "regional-essd": "https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md",
    "ecs-task-management": "https://help.aliyun.com/zh/ecs/user-guide/ecs-task-management.md",
    "system-disk-guide": "https://help.aliyun.com/zh/ecs/user-guide/create-and-use-a-system-disk.md",
    "image-instant-access": "https://help.aliyun.com/zh/ecs/user-guide/image-instant-access.md",
    "essd-specs": "https://help.aliyun.com/zh/ecs/user-guide/essds",
    "block-storage-performance": "https://help.aliyun.com/zh/ecs/user-guide/block-storage-performance",
    "create-snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "atop-guide": ATOP_DOCS[0],
    "atop-metrics": ATOP_DOCS[1],
    "resize-shrink-faq": "https://help.aliyun.com/zh/ecs/disk-resizing-and-shrinking-faqs#title-n9f-bic-1n4",
    "autopl-burst-config": "https://www.alibabacloud.com/help/zh/ecs/user-guide/modify-the-performance-configurations-of-an-essd-autopl-disk#title-o4i-xnc-cbf",
    "autopl-intl": "https://www.alibabacloud.com/help/zh/ecs/user-guide/essd-autopl-disks",
    "block-storage-billing": "https://www.alibabacloud.com/help/zh/ecs/block-storage-devices#title-lcm-hzj-j67",
    "instance-spec-change": "https://help.aliyun.com/zh/ecs/user-guide/change-the-instance-types-of-subscription-instances",
    "instance-families-overview": "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-families#u1",
    "disk-billing-switch": "https://help.aliyun.com/zh/ecs/switch-the-billing-method-of-a-disk",
    "detach-disk": "https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk",
    "release-disk": "https://help.aliyun.com/zh/ecs/user-guide/release-a-disk",
}

VERIFICATION_NOTE = (
    "Numeric ceilings are quoted from the official specification pages "
    "listed above as corroborated by real support tickets. If the console "
    "shows a different value, trust the console and cite the official page "
    "-- never argue with the live display."
)

# ---------------------------------------------------------------------------
# CloudMonitor metric defaults for the bottleneck mode
# ---------------------------------------------------------------------------
# The exact metric availability depends on the CloudMonitor agent and disk
# type; override with --cms-namespace / --cms-metric when the console shows
# different names. Metric-query failure is a SOFT failure: it degrades with a
# [WARN] and the customer pastes console curves instead.

CMS_NAMESPACE_DEFAULT = "acs_ecs_dashboard"
CMS_DISK_METRICS_DEFAULT = [
    "DiskReadIOPS",
    "DiskWriteIOPS",
    "DiskReadBPS",
    "DiskWriteBPS",
]
