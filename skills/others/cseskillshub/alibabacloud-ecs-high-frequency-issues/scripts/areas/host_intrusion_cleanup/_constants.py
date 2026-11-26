#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS host intrusion cleanup guidance
==============================================================================
SECURITY: This module carries NO credentials and no paths to credentials.
Authentication is resolved exclusively by the aliyun CLI default credential
chain. The action surface below is deliberately split into (a) cloud evidence
queries that run automatically, and (b) two gated operations (in-guest
non-mutating forensics dispatch, evidence snapshot creation) that the entry
script refuses to call without an explicit one-time confirmation flag from the
operator.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
every reference table (action whitelist, guest forensics command whitelist,
alert taxonomy, triage anchors, handoff map, hardening checklist, document
links) is embedded here as a Python constant. There are no data files.

The four guest forensics categories are frozen by this tier's contract:
process state, network-connection state, scheduled-task state, startup-item
state. Any reading outside these four categories is refused and downgraded to
a customer-paste request.
"""

import re

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-host-intrusion-cleanup"

# User-Agent template: {skill_name} and {session_id} are filled per run.
# {session_id} is a 32-character hex string (uuid4().hex).
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

# ---------------------------------------------------------------------------
# CLI transport
# ---------------------------------------------------------------------------

CLI_BIN = "aliyun"

# Wall-clock timeout applied to EVERY CLI subprocess call (MUST 7.6.1).
CLI_TIMEOUT_SECONDS = 60

# Transient-error retry budget (linear backoff: 2s, 4s).
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

# Polling budget for one gated in-guest forensics read-back.
INVOCATION_POLL_INTERVAL_SECONDS = 8
INVOCATION_POLL_MAX = 6

# Pagination guardrails for list-style queries.
MAX_PAGES = 10
PAGE_SIZE = 50

# ---------------------------------------------------------------------------
# API surface (verified in the batch api-info pass for this tier)
# ---------------------------------------------------------------------------

API_VERSIONS = {
    "ecs": "2014-05-26",
    "sas": "2018-12-03",
    "cms": "2019-01-01",
    "hbr": "2017-09-08",
    "sts": "2015-04-01",
}

# Runtime whitelist. _cli.call() refuses anything outside this set; the two
# gated actions are additionally blocked unless the operator passes
# --confirmed after the customer approved that exact single operation.
ALLOWED_ACTIONS = {
    "ecs": {
        "DescribeSnapshots",   # recovery-point inventory (ransom judgment)
        "DescribeInvocations", # reads back ONE already-approved forensics run
        "RunCommand",     # gated: dispatches ONE whitelisted non-mutating probe
        "CreateSnapshot", # gated: snapshot-first before any cleanup guidance
    },
    "sas": {
        "DescribeSuspEvents",
        "DescribeVersionConfig",
        "DescribeFieldStatistics",
        "DescribeExposedInstanceList",
    },
    "cms": {"DescribeMetricLast"},
    "hbr": {"DescribeRestoreJobs2"},
    "sts": {"GetCallerIdentity"},
}

# Central / region-templated endpoints (verified against the batch evidence
# pass: Security Center is addressed through its central endpoint, Cloud
# Monitor through a region-templated endpoint).
PRODUCT_ENDPOINTS = {"sas": "tds.aliyuncs.com"}
PRODUCT_ENDPOINT_TMPLS = {"cms": "metrics.{region}.aliyuncs.com"}

# Plugin-mode products: the CLI command is the lowercase-hyphenated form of
# the action name. Checked against aliyun CLI 3.4.5 on the build host:
#   `aliyun sts get-caller-identity`      -> accepted
#   `aliyun hbr describe-restore-jobs2`   -> REJECTED ("not a valid built-in
#       command"; it would need the separate aliyun-cli-hbr plugin), so Cloud
#       Backup stays on the built-in metadata form: product `hbr` with the
#       PascalCase action name `DescribeRestoreJobs2`, which the same CLI
#       accepts.
# Every other product here runs in plugin mode (lowercase-hyphenated).
PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

# Actions that are NEVER callable from this skill (manual console steps or
# other tiers). Destructive cleanup (deleting/quarantining files, killing
# processes, rebooting, rolling back a disk, editing security groups,
# unblocking appeals, deleting snapshots) stays human-only.
NEVER_CALLED_ACTIONS = (
    "DeleteSnapshot",
    "DeleteDisk",
    "DeleteInstance",
    "ResetDisk",            # snapshot rollback -- customer console or the equivalent OpenAPI
    "ReInitDisk",
    "ReplaceSystemDisk",
    "StartInstance",
    "StopInstance",
    "RebootInstance",
    "AuthorizeSecurityGroup",
    "RevokeSecurityGroup",
    "ModifySecurityGroupRule",
    "ModifyInstanceAttribute",
    "ResetPassword",
)

# ---------------------------------------------------------------------------
# CloudMonitor reading (miner corroboration)
# ---------------------------------------------------------------------------

CMS_NAMESPACE = "acs_ecs_dashboard"

# NOTE: the metric dimension set below is the reading plan consolidated from
# the ticket evidence (sustained high CPU as a mining corroboration signal);
# it is not a live-verified metric dictionary. Every metric is fetched
# independently and any failure degrades to a [WARN] line without blocking
# the rest of the diagnosis.
CMS_METRICS = (
    ("CPUUtilization", "sustained-high CPU: the classic miner signature",
     False),
)

# A CPU average at or above this percentage over the sampled window is
# reported as "consistent with a resource-exhaustion pattern" -- it
# corroborates, never proves, a mining finding.
CMS_CPU_SUSPECT_PERCENT = 80.0

# ---------------------------------------------------------------------------
# Cloud Backup (HBR) restore-job query (the file-backup area)
# ---------------------------------------------------------------------------
# Values verified against aliyun CLI 3.4.5 metadata for DescribeRestoreJobs2:
# Edition accepts STANDARD (the API default) and BASIC, and RestoreType
# ECS_FILE is the documented value for "restore ECS files". Both editions are
# queried so a customer on either one is answered from data rather than from
# an assumption about which vault they hold.
HBR_RESTORE_EDITIONS = ("STANDARD", "BASIC")
HBR_RESTORE_TYPE = "ECS_FILE"
HBR_PAGE_SIZE = 20

# ---------------------------------------------------------------------------
# Alert taxonomy: Security Center event names -> intrusion branch
# ---------------------------------------------------------------------------
# Matching is case-insensitive substring over the event name / description
# returned by DescribeSuspEvents. branch: ransom | miner | webshell | other.

ALERT_CATEGORY_ANCHORS = (
    {"branch": "ransom", "anchors": (
        "ransom", "encrypt", "locker", "勒索")},
    {"branch": "miner", "anchors": (
        "mining", "miner", "xmrig", "kdevtmpfsi", "kinsing", "sysrv",
        "minerd", "coin", "挖矿")},
    {"branch": "webshell", "anchors": (
        "webshell", "web shell", "tamper", "website", "backup_file_web",
        "malicious file", "挂马", "网站后门")},
    {"branch": "miner", "anchors": (
        "trojan", "backdoor", "worm", "virus", "malicious process",
        "malware", "reverse shell", "DDoS", "木马", "恶意程序", "后门")},
    {"branch": "entry", "anchors": (
        "brute force", "brute-force", "logon", "login", "abnormal",
        "weak password", "爆破", "异地登录")},
)

BRANCH_LABELS = {
    "ransom": "ransomware / encrypted data recovery",
    "miner": "mining / virus / trojan intrusion",
    "webshell": "website defacement / webshell / content tampering",
    "entry": "entry-vector signal (exposed port or suspicious logon)",
    "other": "uncategorized Security Center alert",
}

# ---------------------------------------------------------------------------
# Triage anchors: verbatim customer wording -> branch or handoff
# ---------------------------------------------------------------------------
# Tickets arrive in Chinese or English; the anchor table is what the
# --symptom matcher runs against (short, OCR-tolerant fragments). Report and
# guidance text always renders in English.

SYMPTOM_ANCHORS = (
    {
        "id": "ransom-encryption",
        "branch": "ransom",
        "anchors": ["ransom", "encrypted my file", "files are encrypted",
                    "readme.txt", "bitcoin", "ransom note", "lock file",
                    "勒索", "加密了我的文件", "赎金", "锁文件", "比特币"],
        "note": "confirm encryption in-guest only through the four "
                "whitelisted forensics reads; the recoverability judgment "
                "(K4) is the value the skill adds",
    },
    {
        "id": "miner-virus-trojan",
        "branch": "miner",
        "anchors": ["mining", "miner", "virus", "trojan", "malware",
                    "backdoor", "worm", "xmrig", "kdevtmpfsi", "malicious "
                    "process", "poisoned", "挖矿", "矿池", "病毒", "木马",
                    "恶意程序", "后门", "蠕虫", "僵尸", "中毒"],
        "note": "check whether alerts keep recurring after handling: that "
                "points at an unpatched application vulnerability, not a "
                "detection failure",
    },
    {
        "id": "web-defacement",
        "branch": "webshell",
        "anchors": ["webshell", "defaced", "hacked", "tamper", "black link",
                    "gambling", "redirect", "homepage changed", "injected",
                    "illegal page", "挂马", "篡改", "黑链", "被入侵", "植入",
                    "首页被改", "跳转博彩", "违法页面", "木马文件"],
        "note": "triage DNS -> origin -> code; a webshell detection with "
                "nothing flagged by the scan engine usually means the "
                "attacker edited page content directly",
    },
    {
        "id": "penalty-block",
        "branch": "handoff-unblock",
        "anchors": ["cannot connect anymore", "connection cut by alibaba",
                    "blocked public network", "unblock", "penalty",
                    "解封", "被处罚", "断网"],
        "action": "handoff",
        "target": "unblock-appeal",
        "note": "identify the combination (mining alert + sudden loss of "
                "public connectivity) as a platform security penalty; the "
                "release request is a self-service application the customer "
                "submits on the Security Center penalty records page, and "
                "the human channel is the escalation after a rejection",
    },
    {
        "id": "disk-capacity-area",
        "branch": "handoff",
        "anchors": ["disk is full", "no space left", "inode", "空间已满",
                    "空间不够"],
        "action": "handoff",
        "target": "disk-capacity",
        "note": "capacity/inode is the sibling tier's area; do not dispatch "
                "df/du/lsof from this skill",
    },
    {
        "id": "ddos-blackhole",
        "branch": "handoff",
        "anchors": ["ddos", "blackhole", "black hole", "流量攻击", "黑洞"],
        "action": "handoff",
        "target": "ddos-cc",
        "note": "volumetric attack handling is a different tier",
    },
    {
        "id": "virtual-host-product",
        "branch": "handoff",
        "anchors": ["virtual host", "云虚拟主机", "ftp account only",
                    "hosting control panel"],
        "action": "handoff",
        "target": "virtual-host",
        "note": "web hosting products have no remote logon and no ECS API "
                "surface; recognize early and route (ticket pattern: a "
                "customer searched ECS entry points for a virtual host)",
    },
    {
        "id": "business-legal",
        "branch": "handoff",
        "anchors": ["refund", "unsubscribe", "withdraw", "lawyer letter",
                    "certificate of ransomware", "invoice", "contract",
                    "退订", "退款", "提现", "律师函", "勒索证明", "合同"],
        "action": "handoff",
        "target": "human-channel",
        "note": "commercial and legal demands are outside the technical "
                "scope; preserve evidence, then hand to the human channel",
    },
)

# ---------------------------------------------------------------------------
# Self-service penalty-release entry (Security Center)
# ---------------------------------------------------------------------------
# A platform security penalty (mining/malware alert plus a public-connectivity
# block) is NOT ticket-only. Security Center exposes a self-service "apply to
# release the penalty" page over the penalty / security-control records; the
# attack-and-blackhole axis (now in the security-audit-and-intrusion-response
# extension package) registers the same URL as
# PENALTY_RELEASE_URL and names it "penalty record list and the self-service
# 'apply to release the penalty' page". This area only CITES the entry: the
# customer submits the application, the platform decides the review, and this
# skill never predicts the outcome or any time window.
PENALTY_RELEASE_URL = (
    "https://yundun.console.aliyun.com/?p=scnew#/sc/event/resources"
)

HANDOFF_TARGETS = {
    "mining-deep-dive": {
        "skill": "alibabacloud-mining-attack-diagnosis",
        "evidence_to_attach": ["DescribeSuspEvents mining rows",
                               "exposure rows from the security area"],
    },
    "os-faults": {
        "skill": "alibabacloud-ecs-linux-os-troubleshooting",
        "evidence_to_attach": ["statement that Security Center showed no "
                               "intrusion alerts for this instance"],
    },
    "disk-capacity": {
        "skill": "area:disk-expand-diagnosis",
        "evidence_to_attach": ["which symptom wording triggered the route"],
    },
    "ddos-cc": {
        "skill": None,
        "evidence_to_attach": ["the traffic symptom and when it started",
                               "Security Center alert list (usually empty for "
                               "a volumetric attack)"],
        "manual_note": ("volumetric attack handling and blackhole lifting "
                        "belong to the DDoS/CC tier; this skill only records "
                        "that the symptom is a traffic attack, not an "
                        "intrusion"),
    },
    "unblock-appeal": {
        "skill": None,
        "evidence_to_attach": ["mining/malware alert list",
                               "the moment public connectivity was lost",
                               "the cleanup and hardening steps completed"],
        "manual_note": ("after the infection is cleaned and the host is "
                        "hardened, the customer submits a self-service "
                        "release application on the penalty records page in "
                        "Security Center (" + PENALTY_RELEASE_URL + "); this "
                        "skill cannot submit it. The review conclusion is "
                        "decided by the platform and this skill does not "
                        "predict the outcome or how long it takes -- the "
                        "status shown on that page is authoritative. Escalate "
                        "to the human support/appeal channel only after the "
                        "self-service application is rejected"),
    },
    "virtual-host": {
        "skill": None,
        "evidence_to_attach": ["the product-name check result (not ECS)"],
        "manual_note": ("web hosting products: handle malicious files "
                        "through the hosting control panel file manager or "
                        "FTP; see references/host-intrusion-cleanup__help-docs.md"),
    },
    "human-channel": {
        "skill": None,
        "evidence_to_attach": ["the preserved evidence report"],
        "manual_note": ("billing/legal requests go to the human support "
                        "channel; this skill only preserves technical "
                        "evidence"),
    },
}

# ---------------------------------------------------------------------------
# Gated in-guest forensics commands (frozen whitelist: FOUR categories)
# ---------------------------------------------------------------------------
# Each entry is one complete, non-mutating statement. The operator confirms
# EXACTLY one key per run. Anything outside this map -- compound strings,
# pipes, redirection, file writers, process killers, service controls -- is
# refused by construction and becomes a customer-paste request.

GUEST_COMMANDS = {
    "linux": {
        "processes": {
            "command": "ps aux",
            "type": "RunShellScript",
            "category": "process state",
            "purpose": "the full live process table with CPU/memory share",
            "read_how": "flag unknown high-CPU names, paths under world-"
                        "writable directories, and processes whose binary "
                        "path is deleted or hidden",
        },
        "connections": {
            "command": "ss -antp",
            "type": "RunShellScript",
            "category": "network-connection state",
            "purpose": "established/listening sockets with owning process",
            "read_how": "flag ESTABLISHED sessions to foreign hosts on "
                        "non-business ports (pool ports such as 3333/5555/"
                        "7777/14444 are common), and listeners on odd high "
                        "ports; if ss is absent the customer can paste "
                        "`netstat -antp` instead",
        },
        "cron-tasks": {
            "command": "ls -lR /etc/crontab /etc/cron.d /etc/cron.daily "
                       "/etc/cron.hourly /etc/cron.weekly /var/spool/cron",
            "type": "RunShellScript",
            "category": "scheduled-task state",
            "purpose": "enumerate every system cron location and the "
                       "spooled user crontabs",
            "read_how": "flag cron entries whose target script lives in a "
                        "world-writable directory or has a random-looking "
                        "name; 'cannot access' lines are normal on minimal "
                        "systems",
        },
        "startup-items": {
            "command": "systemctl list-unit-files --state=enabled "
                       "--no-pager",
            "type": "RunShellScript",
            "category": "startup-item state",
            "purpose": "the enabled boot-time unit list as the guest will "
                       "apply it",
            "read_how": "flag enabled units with random or impersonating "
                        "names; cross-check against the package manager's "
                        "known units",
        },
    },
    "windows": {
        "processes": {
            "command": "tasklist",
            "type": "RunPowerShellScript",
            "category": "process state",
            "purpose": "live process list (the same reading the support "
                       "engineer asked customers to run in tickets)",
            "read_how": "flag processes whose name impersonates a system "
                        "binary but runs from an unusual path, and "
                        "high-CPU entries with unknown image names",
        },
        "connections": {
            "command": "netstat -ano",
            "type": "RunPowerShellScript",
            "category": "network-connection state",
            "purpose": "every socket with its owning PID",
            "read_how": "pair the suspicious remote IP + PID with the "
                        "tasklist output (the ticket-proven two-step)",
        },
        "cron-tasks": {
            "command": "schtasks /query /fo TABLE",
            "type": "RunPowerShellScript",
            "category": "scheduled-task state",
            "purpose": "scheduled-task list in compact table form",
            "read_how": "flag tasks scheduled to run scripts from "
                        "AppData/Temp or random names",
        },
        "startup-items": {
            "command": "Get-ItemProperty "
                       "HKLM:\\Software\\Microsoft\\Windows\\"
                       "CurrentVersion\\Run",
            "type": "RunPowerShellScript",
            "category": "startup-item state",
            "purpose": "the machine-wide Run key entries",
            "read_how": "flag Run entries pointing at Temp/AppData or "
                        "randomly named binaries",
        },
    },
}

GUEST_COMMAND_CATEGORIES = ("processes", "connections", "cron-tasks",
                            "startup-items")

# Readings outside the four whitelisted categories: the customer runs them
# and pastes the output back. This skill never dispatches them.
FALLBACK_READINGS = (
    {
        "topic": "web root with modification times (defacement triage)",
        "customer_command": "ls -laR /var/www/html | head -n 200",
        "why_not_auto": "file-content inspection is outside the four "
                        "frozen forensics categories of this tier",
    },
    {
        "topic": "recently changed scripts anywhere on disk",
        "customer_command": "find / -xdev -name '*.php' -mtime -7 "
                            "2>/dev/null | head -n 50",
        "why_not_auto": "outside the frozen categories; customer-paste "
                        "reading",
    },
    {
        "topic": "recently modified files under world-writable dirs",
        "customer_command": "find /tmp /var/tmp /dev/shm -type f -mtime -3 "
                            "2>/dev/null | head -n 50",
        "why_not_auto": "outside the frozen categories; customer-paste "
                        "reading",
    },
    {
        "topic": "root-owned setuid binaries snapshot",
        "customer_command": "find / -xdev -perm -4000 -type f 2>/dev/null "
                            "| head -n 50",
        "why_not_auto": "outside the frozen categories; customer-paste "
                        "reading",
    },
    {
        "topic": "Windows: suspicious binaries behind known PIDs",
        "customer_command": "Get-Process | Select-Object Id,Path "
                            "-ErrorAction SilentlyContinue",
        "why_not_auto": "outside the frozen categories; customer-paste "
                        "reading",
    },
    {
        "topic": "login history (who entered, from where)",
        "customer_command": "last -x | head -n 30 ; "
                            "grep -i failed /var/log/auth.log | tail -n 50",
        "why_not_auto": "outside the frozen categories; customer-paste "
                        "reading",
    },
)

# ---------------------------------------------------------------------------
# Customer-facing guidance constants (English wording, per batch rule)
# ---------------------------------------------------------------------------

SNAPSHOT_BILLING_NOTICE = (
    "Snapshots are billed pay-as-you-go for their stored size (a rough "
    "order of magnitude: a 100 GB disk yields on the order of CNY 0.016 "
    "per hour while the snapshot is stored). Keep an evidence snapshot "
    "only as long as the incident needs it, then delete it from the "
    "console or through DeleteSnapshot (a customer-executed step this skill never "
    "performs)."
)

SNAPSHOT_FIRST_RULE = (
    "MANDATORY before ANY cleanup or handling guidance: create a current-"
    "state evidence snapshot first (this skill can do it through the "
    "gated snapshot write, or the customer in the console). Pure "
    "evidence-gathering does not need one."
)

ENCRYPTED_STATE_SNAPSHOT_NOTICE = (
    "A snapshot taken of an ALREADY-ENCRYPTED disk preserves the crime "
    "scene but cannot restore the original data: snapshotting after the "
    "encryption does not undo it. Recovery comes only from a snapshot or "
    "file backup created BEFORE the incident window."
)

BACKUP_RETENTION_NOTICE = (
    "The most common reason a ransomware case turns unrecoverable is a "
    "backup policy mistake: retention set to 1 day (or 24h), manual "
    "snapshot pausing, or deleted snapshots. A deleted snapshot is gone "
    "for good; the platform does not keep a hidden copy."
)

ROLLBACK_MANUAL_NOTICE = (
    "A snapshot rollback (re-initializing a disk from a snapshot) "
    "overwrites current disk content and is IRREVERSIBLE. The account "
    "holder executes it in the console or the equivalent OpenAPI -- this skill never "
    "triggers it, and support cannot do it on the customer's behalf. "
    "Roll back the system disk first, then data disks; before rolling "
    "back, create a fresh snapshot of the CURRENT state."
)

RECOVERY_UNCERTAIN_NOTICE = (
    "When no snapshot or file backup predates the incident, the platform "
    "cannot restore the data and does not decrypt ransomware-encrypted "
    "files. Decryption attempts belong to specialized third parties "
    "found through the Alibaba Cloud Marketplace; treat any paid "
    "promise of guaranteed decryption with caution."
)

SHARED_RESPONSIBILITY_NOTICE = (
    "Alibaba Cloud secures the cloud platform; the guest operating "
    "system, applications, data and access control inside an ECS "
    "instance are the customer's responsibility (the IaaS "
    "responsibility-sharing model). The platform keeps no application-"
    "level access logs of customer services and cannot attribute who "
    "connected to a customer database or web app; it also does not "
    "issue forensic certificates for ransomware incidents."
)

RECURRENCE_NOTICE = (
    "Alerts that keep reappearing after handling almost always mean the "
    "entry vulnerability was never fixed (unpatched application, weak "
    "password, exposed admin/database port), not that the scan failed. "
    "Killing the process without patching the hole re-delivers the "
    "payload."
)

HARDENING_CHECKLIST = (
    "1. Restrict the security group so that SSH (22) / RDP (3389) accept "
    "connections only from named office IPs -- never 0.0.0.0/0; open "
    "only the business ports the service truly serves.",
    "2. Close or firewalls-protect every management and database port "
    "(3306/6379/8069/11211/9200 and similar); a single permissive rule "
    "among several bound security groups exposes the port.",
    "3. Set strong, unique passwords for every account on the host and "
    "rotate them after an intrusion.",
    "4. Upgrade the affected application/framework to a fixed version "
    "(the recurring-infection root cause in this tier's tickets is "
    "usually an exploited application vulnerability).",
    "5. Take disk snapshots regularly with a sane retention (NOT 1 "
    "day/24h) and an auto-snapshot policy for recurring protection.",
    "6. Patch high-risk system and application vulnerabilities promptly "
    "-- and always create a snapshot BEFORE patching or cleaning, so a "
    "bad update is reversible.",
)

ENTRY_VECTOR_HINTS = {
    "3389": "Windows remote desktop exposed to the whole internet: the "
            "top ransomware/brute-force entry in this tier's tickets",
    "22": "SSH exposed to the whole internet: brute-force and weak-"
          "password entry",
    "0.0.0.0/0": "an allow-all source CIDR on any port is the single "
                  "most common exposure finding",
}

# ---------------------------------------------------------------------------
# Official documentation links (batch help-search evidence pass; the
# references/host-intrusion-cleanup__help-docs.md file separates verified from as-pasted links)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "security-overview": "https://help.aliyun.com/zh/ecs/user-guide/security-overview.md",
    "best-security-practices": "https://help.aliyun.com/zh/ecs/user-guide/best-security-practices.md",
    "mining-virus-guide": "https://help.aliyun.com/zh/ecs/user-guide/mining-virus-protection-and-handling-guide.md",
    "data-backup": "https://help.aliyun.com/zh/ecs/user-guide/data-backup.md",
    "data-protection-schemes": "https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md",
    "network-bandwidth": "https://help.aliyun.com/zh/ecs/user-guide/network-bandwidth.md",
    "what-is-ecs": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
    "create-snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "rollback-disk": "https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot",
    "ransomware-protection": "https://help.aliyun.com/zh/security-center/use-cases/comprehensive-protection-plan-against-ransomware-attacks",
    "hardening-list": "https://help.aliyun.com/document_detail/60787.html",
    "snapshot-billing": "https://help.aliyun.com/document_detail/56159.html",
    "delete-snapshot": "https://help.aliyun.com/document_detail/128131.html",
    "windows-bandwidth": "https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances",
    "illegal-domain-info": "https://help.aliyun.com/zh/dws/support/what-to-do-if-a-domain-name-contains-illegal-information",
    "uninstall-aegis": "https://help.aliyun.com/document_detail/68616.html",
    "virtual-host-malware-1": "https://help.aliyun.com/document_detail/85221.html",
    "virtual-host-malware-2": "https://help.aliyun.com/document_detail/211342.html",
    "virtual-host-malware-3": "https://help.aliyun.com/document_detail/312524.html",
    "marketplace": "http://market.aliyun.com/",
    "sas-console": "https://yundun.console.aliyun.com/",
}

# ---------------------------------------------------------------------------
# Validation shapes
# ---------------------------------------------------------------------------

REGION_RE = re.compile(r"^[a-z][a-z0-9-]{2,29}$")
INSTANCE_RE = re.compile(r"^i-[a-z0-9]{6,32}$")
DISK_RE = re.compile(r"^d-[a-z0-9]{6,32}$")
_OCTET = r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"
IPV4_RE = re.compile(r"^%s\.%s\.%s\.%s$" % (_OCTET, _OCTET, _OCTET, _OCTET))

# The report file the operator may ask for lands under this prefix only when
# --report-file is given; it is a NEW file the operator names.
REPORT_FILE_NOTE = (
    "the evidence report is written ONLY to the operator-chosen --report-"
    "file path (a new file; an existing path is never overwritten)."
)
