#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Instance Start/Stop Anomaly
==========================================================================
SECURITY: This module carries NO credentials and no paths to credentials.
Authentication is resolved exclusively by the aliyun CLI default credential
chain. The action surface below is deliberately split into (a) cloud evidence
queries that run automatically, and (b) two gated operations (in-guest
command dispatch, snapshot creation) that the entry script refuses to call
without an explicit one-time confirmation flag from the operator.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all reference tables (state machine, dwell-time window, guest command
whitelist, symptom anchors for triage, handoff map, risk notices, document
links) are embedded here as Python constants. There are no data files.

Customer wording below is intentionally bilingual: tickets arrive in Chinese
or English, and the anchor table is what the --symptom matcher runs against.
Report and console guidance text stays English per the batch output rule.
"""

import re

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-instance-start-stop-anomaly"

# User-Agent template: {skill_name} and {session_id} are filled per run.
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

# Polling budget for one gated in-guest command read-back.
INVOCATION_POLL_INTERVAL_SECONDS = 8
INVOCATION_POLL_MAX = 6

# Pagination guardrail for Describe* list calls.
MAX_PAGES = 10
PAGE_SIZE = 50

# ---------------------------------------------------------------------------
# API surface (verified in the batch api-info pass)
# ---------------------------------------------------------------------------

# Versions actually used by this batch's verified surface. The CloudMonitor
# version column came back empty from verification; the CLI resolves its own
# metadata, so nothing is guessed here (tracked as an open verification item).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "cms": "",
    "sts": "2015-04-01",
}

ECS_PRODUCT = "ecs"
CMS_PRODUCT = "cms"
STS_PRODUCT = "sts"

# Runtime whitelist. _cli.call() refuses anything outside this set; the two
# gated actions are additionally blocked unless the operator passes
# --confirmed after the customer approved that exact single operation.
ALLOWED_ACTIONS = {
    "ecs": {
        "DescribeInstances",
        "DescribeInstancesFullStatus",
        "DescribeInstanceHistoryEvents",
        "DescribeDisks",
        "DescribeSnapshots",
        "DescribeInvocations",
        "RunCommand",      # gated: dispatches ONE whitelisted, non-mutating command
        "CreateSnapshot",  # gated: snapshot-first before any manual recovery step
    },
    "cms": {"DescribeMetricLast"},
    "sts": {"GetCallerIdentity"},
}

# Actions that are NEVER callable from this skill (manual steps only). The
# guidance for these lives in references/instance-start-stop-anomaly__risk-scripts-and-manual-steps.md.
NEVER_CALLED_ACTIONS = (
    "StartInstance",
    "StopInstance",
    "RebootInstance",
    "ReplaceSystemDisk",
    "ReInitDisk",
    "ResetDisk",          # snapshot rollback family -- customer-executed (ResetDisk or console)
    "DeleteSnapshot",
    "DeleteDisk",
    "DeleteInstance",
    "ResizeDisk",
    "ModifyInstanceSpec",
    "ModifyPrepayInstanceSpec",
    "AuthorizeSecurityGroup",
    "RevokeSecurityGroup",
)

# ---------------------------------------------------------------------------
# Instance state machine
# ---------------------------------------------------------------------------

# DescribeInstances Status enum.
STATUS_PENDING = "Pending"
STATUS_STARTING = "Starting"
STATUS_RUNNING = "Running"
STATUS_STOPPING = "Stopping"
STATUS_STOPPED = "Stopped"

# Intermediate states where the hypervisor is mid-transition. The console may
# additionally show an "operating system starting" phase label while the guest
# boots inside the Starting state.
MIDDLE_STATES = (STATUS_PENDING, STATUS_STARTING, STATUS_STOPPING)

# Dwell-time guidance consolidated from the ticket evidence:
#   normal stop/reboot flow: 5-10 minutes typical, hard ceiling 15 minutes,
#   and NO manual intervention is possible while the instance sits in
#   "Stopping". Beyond the ceiling the case is treated as a real anomaly.
EXPECTED_DWELL_MINUTES = (5, 10)
MAX_EXPECTED_DWELL_MINUTES = 15

# ---------------------------------------------------------------------------
# CloudMonitor readings (C3)
# ---------------------------------------------------------------------------

CMS_NAMESPACE = "acs_ecs_dashboard"

# NOTE (open verification item from the requirements doc): the metric name
# set below is the batch's expected reading plan, not a live-verified list.
# Every metric is fetched independently and any failure degrades to a [WARN]
# line without blocking the rest of the diagnosis. Memory-level metrics are
# only reported when the CloudMonitor guest agent is installed.
CMS_METRICS = (
    # (metric name, why this skill reads it, agent-in-guest required?)
    ("CPUUtilization", "post-start CPU activity: did the guest begin booting", False),
    ("memory_usedutilization", "memory saturation behind a hung stop/reboot", True),
    ("DiskReadBPS", "disk read saturation elongating the shutdown flow", False),
    ("DiskWriteBPS", "dirty-page flush pressure during stop/reboot", False),
)

# ---------------------------------------------------------------------------
# Gated in-guest evidence commands (C6)
# ---------------------------------------------------------------------------
# STRICT whitelist. Each entry is one complete, non-mutating shell command
# (or PowerShell read cmdlet). The operator confirms EXACTLY one key per run.
# Anything outside this map -- including compound command strings, pipes to
# writers, or unlisted readers -- is refused and downgraded to a
# "customer runs it in VNC/SSH and pastes the reading" request.

GUEST_COMMANDS = {
    "linux": {
        "findmnt": {
            "command": "findmnt",
            "type": "RunShellScript",
            "purpose": "mounted filesystem tree as the guest currently sees it",
            "arg": False,
        },
        "df-h": {
            "command": "df -h",
            "type": "RunShellScript",
            "purpose": "filesystem usage table (space) for every mounted volume",
            "arg": False,
        },
        "df-i": {
            "command": "df -i",
            "type": "RunShellScript",
            "purpose": "inode usage per filesystem (mount exists but full inode)",
            "arg": False,
        },
        "stat": {
            "command": "stat",
            "type": "RunShellScript",
            "purpose": "file/directory facts on one guest path (existence, "
                       "mount backing, timestamps)",
            "arg": True,
        },
        "ls-by-uuid": {
            "command": "ls -l /dev/disk/by-uuid",
            "type": "RunShellScript",
            "purpose": "UUID-to-device map used when comparing the mount table "
                       "with what the cloud side says is attached",
            "arg": False,
        },
    },
    "windows": {
        "get-volume": {
            "command": "Get-Volume",
            "type": "RunPowerShellScript",
            "purpose": "volume list with health and size as the guest sees it",
            "arg": False,
        },
        "get-psdrive": {
            "command": "Get-PSDrive",
            "type": "RunPowerShellScript",
            "purpose": "mounted drives and free space inside the guest",
            "arg": False,
        },
        "get-childitem": {
            "command": "Get-ChildItem",
            "type": "RunPowerShellScript",
            "purpose": "non-mutating listing of one guest path",
            "arg": True,
        },
    },
}

# A single path argument is appended ONLY when it matches this shape:
# absolute, conservative character set, no traversal, no shell metachars.
GUEST_ARG_RE = re.compile(r"^/[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$")
GUEST_ARG_WIN_RE = re.compile(r"^[A-Za-z]:\\[A-Za-z0-9 ._\\-]{0,119}$")

# Readings this skill deliberately does NOT auto-run (outside the approved
# whitelist). Each row is the fallback the operator offers the customer:
# run it yourself over VNC/SSH and paste the output back.
FALLBACK_READINGS = (
    {
        "topic": "mount table the guest will apply at next boot",
        "customer_command": "cat /etc/fstab",
        "why_not_auto": "not on the approved command whitelist; handled as a "
                        "customer-paste reading",
    },
    {
        "topic": "failed boot units",
        "customer_command": "systemctl list-units --failed",
        "why_not_auto": "not on the approved command whitelist",
    },
    {
        "topic": "previous boot error log",
        "customer_command": "journalctl -b -1 -p err",
        "why_not_auto": "not on the approved command whitelist",
    },
    {
        "topic": "kernel ring buffer of the last boot",
        "customer_command": "dmesg | tail -n 200",
        "why_not_auto": "not on the approved command whitelist",
    },
    {
        "topic": "reboot history",
        "customer_command": "last -x reboot | head -n 20",
        "why_not_auto": "not on the approved command whitelist",
    },
    {
        "topic": "block devices as the guest sees them",
        "customer_command": "lsblk",
        "why_not_auto": "not on the approved command whitelist (compare with "
                        "the cloud-side disk inventory instead when the guest "
                        "is reachable through the whitelist)",
    },
    {
        "topic": "process-level load at the time of the hang",
        "customer_command": "atop -r /var/log/atop/<YYYYMMDD> (after deploying "
                            "atop beforehand)",
        "why_not_auto": "historical per-process data exists nowhere on the "
                        "cloud side; atop must be installed in advance",
    },
    {
        "topic": "Windows boot/system events",
        "customer_command": "Get-WinEvent -LogName System -MaxEvents 100",
        "why_not_auto": "not on the approved command whitelist",
    },
)

# ---------------------------------------------------------------------------
# Triage anchors: customer-visible symptoms -> candidate root cause / routing
# ---------------------------------------------------------------------------
# Matching is case-insensitive substring on the raw customer wording
# (screenshots and OCR text are routinely garbled, so anchors are short and
# OCR-tolerant). action: investigate | handoff | declare-unsupported.

SYMPTOM_ANCHORS = (
    # ---- instance-level boot failure families (kept here) ----
    {
        "id": "boot-disk-damage",
        "anchors": ["operating system wasn", "no bootable device",
                    "ntldr is missing", "invalid boot disk",
                    "inaccessible boot device"],
        "family": "system disk damage / boot loader failure",
        "action": "investigate",
        "note": "boot chain on the system disk is broken; recovery is the "
                "snapshot-rollback / attach-and-copy-data path, done by the "
                "customer in the console after a fresh snapshot",
    },
    {
        "id": "fstab-mount",
        "anchors": ["fstab", "a dependency failed", "give root password",
                    "emergency mode", "entered emergency mode",
                    "timed out waiting for device",
                    "startup is finished waiting",
                    "数据盘没有挂载", "挂载失败", "重启后数据丢了"],
        "family": "mount entry in the boot-time mount table points at a device "
                  "that does not exist (or the reverse: disk attached but no "
                  "auto-mount configured)",
        "action": "investigate",
        "note": "cross-check the cloud-side disk inventory against the guest "
                "mount view; fixing the mount line is a manual customer step",
    },
    {
        "id": "cloudinit-meta",
        "anchors": ["100.100.100.200", "meta-data/instance-id",
                    "is unreachable", "errno 101", "netuork",
                    "dev-getty", "serial getty", "cloud-init"],
        "family": "boot-stage dependency timeout (metadata service / getty "
                  "unit) often after a network or security-group change",
        "action": "investigate",
        "note": "root cause frequently tied to a customer network/security-"
                "group edit; route the config part to the connection skills",
    },
    {
        "id": "resource-exhaustion",
        "anchors": ["cannot allocate memory", "allocate memory", "oom",
                    "out of memory", "fork:", "内存不足", "内存跑高",
                    "卡死", "夯住"],
        "family": "memory / process-count / IO exhaustion: the guest hangs, "
                  "which stretches stop and boot phases",
        "action": "investigate",
        "note": "qualify with CloudMonitor readings; historical process data "
                "is only available if atop was installed before the incident",
    },
    {
        "id": "force-stop-request",
        "anchors": ["强制停止", "强制重启", "force stop", "force reboot",
                    "force restart", "cannot be stopped", "无法停止",
                    "停止失败", "关机失败", "无法关机", "重启失败",
                    "无法重启", "卡在停止", "一直停止", "stuck in stopping",
                    "长时间处于停止", "一直卡在"],
        "family": "instance parked in an intermediate transition "
                  "(Stopping/Starting) and the customer wants it forced",
        "action": "investigate",
        "note": "within the 15-minute ceiling nothing can intervene; beyond "
                "it escalate with evidence -- this skill never forces state",
    },
    {
        "id": "boot-stuck",
        "anchors": ["无法进入系统", "进不了系统", "进不去", "起不来",
                    "无法启动", "无法正常启动", "启动失败", "一直启动",
                    "处于启动中", "操作系统启动中", "无法开机",
                    "won't boot", "cannot boot", "boot failure",
                    "stuck in starting", "cannot start", "won't start",
                    "booting for", "系统崩溃"],
        "family": "start failure / long 'operating system starting' phase",
        "action": "investigate",
        "note": "enter the boot-failure decision tree",
    },
    # ---- handoff signatures (recognized, NOT solved here) ----
    {
        "id": "guest-service-failure",
        "anchors": ["address already in use", "bind() to", "could not bind",
                    "ibdata1", "got signal 6", "(2002) can't connect",
                    "can't connect to local server", "winrm",
                    ".net framework", "iis", "nginx", "apache", "php-fpm",
                    "tomcat", "redis", "docker", "crond", "systemd服务",
                    "服务启动失败", "网站打不开 服务", "windows服务",
                    "开机无法启动 服务", "预部署任务失败"],
        "family": "guest-OS service / middleware that fails INSIDE a booted "
                  "system",
        "action": "handoff",
        "target": "os-troubleshooting",
        "note": "verify the instance is Running first (the cloud-side fact "
                "that debunks 'the platform stopped my service'); if data "
                "vanished after a reboot, keep it here for the mount "
                "cross-check before handing off",
    },
    {
        "id": "login-credential",
        "anchors": ["access denied", "login incorrect", "password",
                    "ssh 连不上", "无法远程", "连不上服务器", "rdp",
                    "远程桌面", "重置密码", "隧道"],
        "family": "reachability / credential problem behind a booted system",
        "action": "handoff",
        "target": "connection-credential",
        "note": "offline password reset requires an instance reboot to take "
                "effect -- that coupling is the only start/stop fact here",
    },
    {
        "id": "disk-capacity",
        "anchors": ["disk is full", "no space left", "空间已满",
                    "空间满", "inode", "日志占满"],
        "family": "disk capacity / inode exhaustion",
        "action": "handoff",
        "target": "disk-capacity",
        "note": "when capacity fullness is the reason boot/stop stalls, "
                "attribute here, hand the cleanup to the capacity skill",
    },
    {
        "id": "snapshot-ops",
        "anchors": ["快照无法删除", "delete snapshot", "snapshot billing",
                    "快照计费"],
        "family": "snapshot lifecycle / billing operations",
        "action": "handoff",
        "target": "snapshot-billing",
        "note": "noise signature; route to snapshot/billing support",
    },
    {
        "id": "account-block",
        "anchors": ["验证码", "手机号", "verification code", "account review",
                    "二次校验"],
        "family": "account-side verification blocking console operations",
        "action": "handoff",
        "target": "account-security",
        "note": "cannot be bypassed by any diagnostic; state the boundary",
    },
    {
        "id": "non-ecs-product",
        "anchors": ["轻量应用服务器", "simple application server", "swas",
                    "无影", "wuying", "cloud desktop", "云电脑"],
        "family": "not an ECS instance",
        "action": "declare-unsupported",
        "note": "declare out of scope and point at the owning product",
    },
    {
        "id": "spec-change-billing",
        "anchors": ["降配", "升配收费", "退订", "refund", "unsubscribe",
                    "变配咨询"],
        "family": "spec-change / billing consultation (this skill only covers "
                  "the reboot the change requires)",
        "action": "handoff",
        "target": "spec-change",
        "note": "configuration changes need an instance restart to take "
                "effect -- hand the commercial part elsewhere",
    },
)

HANDOFF_TARGETS = {
    "os-troubleshooting": {
        "skill": "alibabacloud-ecs-linux-os-troubleshooting",
        "windows_variant_note": "Windows service/component failures go to the "
                                "corresponding Windows OS-support skill",
        "evidence_to_attach": [
            "instance id / region and the Running status check output",
            "the service error text or screenshot lines the customer pasted",
            "the boot timestamp (so 'did it start on its own later' is clear)",
        ],
    },
    "connection-credential": {
        "skill": "the ECS connection and logon-credential support tier "
                 "(SSH or RDP reachability, security-group port rules, "
                 "password reset); when in doubt route via "
                 "alibabacloud-ecs-linux-os-troubleshooting",
        "evidence_to_attach": [
            "Running status + health check (instance level is healthy)",
            "VNC observation whether the login prompt itself is reachable",
            "which reset path was used (online vs offline)",
        ],
    },
    "disk-capacity": {
        "skill": "area:disk-expand-diagnosis",
        "evidence_to_attach": ["df -h / df -i reading (whitelisted) or the "
                               "customer's pasted usage screenshot"],
    },
    "disk-io": {
        "skill": "area:resource-bottleneck",
        "evidence_to_attach": ["CMS disk read/write readings collected here"],
    },
    "disk-expand": {
        "skill": "area:disk-expand-diagnosis",
        "evidence_to_attach": ["DescribeDisks size list collected here"],
    },
    "snapshot-ops": {
        "skill": "the ECS snapshot lifecycle and billing support tier",
        "evidence_to_attach": ["DescribeSnapshots inventory collected here"],
    },
    "account-security": {
        "skill": None,
        "evidence_to_attach": ["state that the console operation is blocked "
                               "by account verification, not by ECS"],
    },
    "spec-change": {
        "skill": "the ECS instance configuration-change and billing tier "
                 "(this skill only covers the reboot the change requires)",
        "evidence_to_attach": ["the instance type and the reboot requirement"],
    },
}

# ---------------------------------------------------------------------------
# Customer-facing guidance constants (English wording, per batch rule)
# ---------------------------------------------------------------------------

# Standard restart risk notice (four points), relayed before any manual
# start/stop/reboot step the customer performs in the console.
REBOOT_RISK_NOTICE = (
    "1. The operation interrupts running workloads.",
    "2. Data still in memory (not yet written to disk) can be lost.",
    "3. Create a snapshot of every affected disk first so the state is "
       "recoverable.",
    "4. Applications not enabled for autostart will need a manual start "
       "after the instance comes back.",
)

STOP_DWELL_NOTICE = (
    "A normal stop/reboot lets the operating system release processes and "
    "memory, flush dirty data to the cloud disk, unmount filesystems and "
    "then shut the kernel down. The console shows Running -> Stopping -> "
    "Starting -> Running. This takes 5-10 minutes and can reach 15 minutes; "
    "while the instance is in Stopping NOTHING can intervene, including a "
    "forced stop."
)

SNAPSHOT_BILLING_NOTICE = (
    "Snapshots are billed pay-as-you-go for their stored size. Keep them "
    "only as long as the incident needs them and delete the temporary ones "
    "afterwards from the console."
)

ROLLBACK_MANUAL_NOTICE = (
    "A snapshot rollback overwrites the current disk content and is "
    "irreversible. Rollback (ResetDisk) can only be executed by the account "
    "holder in the console -- this skill never triggers it, and neither "
    "support nor an agent should be expected to do it on the customer's "
    "behalf. Before any rollback or re-initialization, create a fresh "
    "snapshot of the CURRENT state first."
)

ECONOMICAL_MODE_NOTE = (
    "If the instance was stopped in economical mode (no-change stop mode), "
    "computing resources were released and a later start can fail when the "
    "zone is short of the instance type's capacity. A failed restart of a "
    "NoCharged instance is a capacity question, not a guest-OS question."
)

BOUNDARY_MESSAGE = (
    "Alibaba Cloud does not stop, restart or touch programs running inside "
    "your server. Guest-side services are owned by the guest OS skills; "
    "this skill covers only the instance-level start/stop state machine and "
    "the boot path facts needed to route correctly."
)

# ---------------------------------------------------------------------------
# Official documentation links (from the batch help-search evidence pass)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "start-instance": "https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md",
    "stop-instance": "https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md",
    "restart-instances": "https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md",
    "economical-mode": "https://help.aliyun.com/zh/ecs/user-guide/economical-mode.md",
    "vnc-login": "https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc.md",
    "spec-change-overview": "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md",
    "release-instance": "https://help.aliyun.com/zh/ecs/user-guide/release-an-instance.md",
    "custom-image-from-snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-a-snapshot-1.md",
    "what-is-ecs": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
    "data-protection-schemes": "https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md",
    "preemptible-recovery": "https://help.aliyun.com/zh/ecs/user-guide/preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md",
    "rollback-disk": "https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot-1",
    "create-snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "snapshot-billing": "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "share-custom-image": "https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image",
    "atop-monitoring": "https://help.aliyun.com/zh/ecs/use-cases/use-the-atop-tool-to-monitor-linux-system-metrics",
    "security-groups": "https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups",
    "windows-virtual-memory": "https://help.aliyun.com/zh/ecs/support/how-to-configure-virtual-memory-for-windows-instances",
    "os-replace": "https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance",
    "credential-management": "https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management",
    "instance-states": "https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance",
}
