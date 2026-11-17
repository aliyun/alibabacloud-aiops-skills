#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Instance-State Diagnosis
======================================================================
SECURITY: This skill is RO+G (read queries + manual guidance). Every Alibaba
Cloud API access goes through the aliyun CLI default credential chain; this
module never reads, prints, caches or passes any credential value. No access
key or secret material exists anywhere in this codebase.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so all
static reference data (API metadata, the state-machine timeout baseline,
boot-failure branch knowledge, the guest diagnostic command whitelist, handoff
statements) is embedded here as Python constants. There are NO data files.

Knowledge provenance: every timeout, error string, and branch below is distilled
from real ECS support-ticket dialogues and official help.aliyun.com articles for
the "instance start/stop state anomaly" tier; nothing is invented.
"""

import re

# ---------------------------------------------------------------------------
# API metadata (all actions below were existence-verified for this tier)
# ---------------------------------------------------------------------------

# ECS is regional: the CLI resolves ecs.<region>.aliyuncs.com from --region.
# STS is central (region-less), so the endpoint is pinned.
STS_ENDPOINT = "sts.aliyuncs.com"

API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

SKILL_NAME = "alibabacloud-ecs-instance-state-diagnosis"

DEFAULT_REGION = "cn-hangzhou"

# Per-call subprocess timeout for every aliyun CLI invocation (MUST 7.6.1).
DEFAULT_TIMEOUT = 60

# Guardrails for list queries.
MAX_RESULTS = 100
MAX_PAGES = 20
MAX_BATCH_INSTANCES = 10

# ---------------------------------------------------------------------------
# Control-plane instance state machine (DescribeInstances Status values)
# ---------------------------------------------------------------------------
STATUS_PENDING = "Pending"
STATUS_STARTING = "Starting"
STATUS_RUNNING = "Running"
STATUS_STOPPING = "Stopping"
STATUS_STOPPED = "Stopped"

INSTANCE_STATUSES = {
    "Pending": "creation / transition accepted, not booting yet",
    "Starting": "the hypervisor is bringing the instance up",
    "Running": "control plane reports the instance up (guest may still be booting)",
    "Stopping": "the OS shutdown flow is in progress",
    "Stopped": "the instance is down (by request, expiry, or crash handling)",
}

# ---------------------------------------------------------------------------
# Time / state baseline (converged from five inconsistent human wordings in
# real tickets: 5~10 / 8~10 / 8~15 / 10~15 / 10~20 minutes). Single baseline:
#   <= EXPECTED_MAX_MINUTES in Stopping  -> within expectations, wait
#   <= ESCALATE_MINUTES                  -> borderline, keep watching
#   >  ESCALATE_MINUTES                  -> escalate (snapshot first, then
#                                            VNC check / manual intervention)
# ---------------------------------------------------------------------------
STOPPING_EXPECTED_MAX_MINUTES = 15.0
STOPPING_ESCALATE_MINUTES = 20.0
STOPPING_TYPICAL_MINUTES = "5-15"

STARTING_EXPECTED_MAX_MINUTES = 5.0
STARTING_ESCALATE_MINUTES = 15.0

# Normal console shutdown-flow wording shown to customers verbatim.
NORMAL_STOPPING_EXPLANATION = (
    "A console stop/reboot first runs the guest OS shutdown flow: releasing "
    "processes and persisting memory/cache data to the block storage. When the "
    "host was under load or heavy IO, this takes {} minutes and the instance "
    "stays in 'Stopping' the whole time. No one -- the console, support, or the "
    "platform -- can intervene, accelerate, or force-stop during this window; "
    "a force operation issued now fails with a task conflict, which is expected "
    "behaviour, not a new fault. The instance comes up automatically once the "
    "flow completes.".format(STOPPING_TYPICAL_MINUTES))

STATUS_SYNC_NOTE = (
    "The console state display can lag the control plane by a short while. If "
    "the API already reports the target state (e.g. Running), ask the customer "
    "to refresh the instance list page before treating the console text as a "
    "fault.")

# ---------------------------------------------------------------------------
# Boot-failure / start-failure branch table. Each branch maps a customer
# quotable signal (console state text, error string, or code) to the layer it
# belongs to, the manual guidance, and an optional handoff target.
# Signals marked evidence=console are read from the customer's own console
# error text; the skill never obtains boot-phase screens by API.
# ---------------------------------------------------------------------------
BOOT_FAILURE_BRANCHES = {
    "nostock": {
        "signal": "OperationDenied.NoStock",
        "layer": "resource availability (cloud side)",
        "verdict": "The instance type is sold out in the current zone, so a "
                   "start/create is refused. This is capacity, not a system fault.",
        "manual_guidance": "In the console use Change Instance Type to a "
                           "in-stock type in the same region, migrate the "
                           "instance to another zone/region, or retry later "
                           "(stock refills dynamically). If the goal is only to "
                           "extract data before releasing, first take a custom "
                           "image (packages system + data disks) or snapshots.",
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/change-the-instance-types-of-subscription-instances",
    },
    "grub_rescue": {
        "signal": "VNC shows the 'grub >' rescue prompt; 'ls' reports "
                  "'unknown filesystem' for partitions",
        "layer": "bootloader (guest boot stage)",
        "verdict": "Boot chain damaged after an update/change; the instance "
                   "never reaches the OS, so remote access fails as a symptom.",
        "manual_guidance": "Ask the customer to capture the VNC boot screen "
                           "(four checks: GRUB menu / fsck / emergency or dracut "
                           "prompt / kernel panic). Repair boot manually AFTER a "
                           "snapshot; a snapshot rollback of the system disk is "
                           "the alternative the customer may prefer. Both are "
                           "manual, boot-repair knowledge lives with the OS team.",
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot",
    },
    "custom_image": {
        "signal": "Instance created from a custom / imported image will not "
                  "boot at all",
        "layer": "image compliance (guest boot stage)",
        "verdict": "Images must be cloud-ready: cloud-init plus virtio (NVMe) "
                   "drivers installed BEFORE import, and no interactive "
                   "installer stage. An image that still needs an OS install on "
                   "first boot can never come up on ECS.",
        "manual_guidance": "Verify the image was prepared per the import guide "
                           "(cloud-init + virtio). Re-make the image: install a "
                           "temporary pay-as-you-go data disk, then snapshot it "
                           "and build the image from that snapshot. Driver "
                           "presence cannot be asserted by public read APIs; "
                           "this stays a guided check with the customer.",
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/import-an-image",
    },
    "fstab_emergency": {
        "signal": "Boot drops into emergency/recovery mode; auto-mount config "
                  "references a disk device that no longer exists",
        "layer": "filesystem auto-mount (guest boot stage)",
        "verdict": "An /etc/fstab entry pointing at a missing data disk blocks "
                   "normal boot; the instance looks 'stuck starting' or drops "
                   "to a recovery shell.",
        "manual_guidance": "Manually comment out the offending fstab line "
                           "(customer-executed edit; the skill never rewrites "
                           "files), or attach a repair disk to fix it. Snapshot "
                           "first. Once booting, configure correct auto-mount "
                           "for the data disk.",
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/workbench-system-management.md",
    },
    "disk_full_boot": {
        "signal": "Instance reaches Running but network/services never "
                  "initialize; system disk is 100% used (or inodes exhausted)",
        "layer": "capacity blocking boot (identify here, fix in capacity tier)",
        "verdict": "A full system disk (or exhausted inodes) can break boot-time "
                   "initialization (e.g. the NIC never comes up), which looks "
                   "like 'the server will not start'.",
        "manual_guidance": "Take a snapshot, then the customer cleans space or "
                           "expands the disk; boot-blocking capacity is a real "
                           "cause but the cleanup itself belongs to the "
                           "disk-capacity skill. Layer judgement only.",
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    },
    "atkbd_noise": {
        "signal": "atkbd serio0: Unknown key pressed",
        "layer": "harmless log line",
        "verdict": "Virtual-keyboard driver compatibility warning during reboot; "
                   "generally does NOT block boot. Do not treat as the root "
                   "cause; continue the four-check VNC stage judgement.",
        "manual_guidance": "Ignore for causation; run the VNC four checks "
                           "(GRUB / fsck / emergency / panic) instead.",
        "doc": "",
    },
    "bios_boot_order": {
        "signal": "Customer recently touched boot order / entered BIOS to "
                  "select the system",
        "layer": "boot entry (console/BIOS)",
        "verdict": "Boot device selection changed or reset; the instance boots "
                   "the wrong or no device.",
        "manual_guidance": "Ask the customer whether any BIOS/boot-order change "
                           "was made; restore the default boot path from the "
                           "console VNC session (manual).",
        "doc": "https://help.aliyun.com/zh/ecs/user-guide/restart-instances",
    },
    "expiry_stop": {
        "signal": "Stopped + lock reason financial / subscription expired; "
                  "'will not start'",
        "layer": "account lifecycle (not a fault)",
        "verdict": "The instance was shut down by the platform because the "
                   "subscription expired. Start is blocked until renewed.",
        "manual_guidance": "Renew in the billing console (manual commercial "
                           "action; the skill never transacts). If renewal is "
                           "not immediate, create a custom image first to keep "
                           "the environment. An expiry timestamp visible in the "
                           "customer's own console is authoritative.",
        "doc": "https://help.aliyun.com/zh/ecs/manually-renew-an-instance-1",
    },
    "intrusion": {
        "signal": "Tampered system files (e.g. /etc/passwd), miner alerts, "
                  "ransomware, Cloud Assistant agent destroyed",
        "layer": "security incident",
        "verdict": "Boot or recovery failures are downstream of an intrusion; "
                   "diagnosis must not 'repair' an incident scene.",
        "manual_guidance": "Snapshot all disks immediately (evidence + rollback), "
                           "then engage security response; restoring Cloud "
                           "Assistant may require re-initializing the system "
                           "disk (manual, destructive, customer-executed).",
        "doc": "https://hbr.console.aliyun.com/",
    },
}

# Service-layer look-alikes that must NOT be chased here (dedup area vs the
# OS-troubleshooting skill): they prove the instance is up, the fault is inside.
SERVICE_LAYER_COUNTEREXAMPLES = [
    "A returned 404 page IS produced by the web server itself -- the service is "
    "running; '404' is not 'service failed to start'.",
    "Port 80 answering while port 443 times out points at the certificate / "
    "HTTPS listener, not at the instance state.",
    "After a snapshot rollback, application processes stay stopped unless they "
    "were configured for autostart -- 'program down after rollback' is a guest "
    "service fact, not an instance-boot failure.",
    "SSH banner visible but login unusable, or RDP handshake visible but the "
    "desktop hangs, indicates resource exhaustion inside a Running guest "
    "(memory/OOM or saturated disk IO), not a control-plane start/stop fault.",
]

# ---------------------------------------------------------------------------
# Guest diagnostic commands: each one only reports, never changes guest data.
# Two tiers, mirroring the batch low-risk-operations checklist:
#   auto_sendable=True  -- on the shipped checklist; MAY be dispatched as ONE
#                          command through RunCommand after explicit customer
#                          confirmation.
#   auto_sendable=False -- required by this tier's evidence but pending
#                          checklist extension; NEVER dispatched by this skill.
#                          The plan output asks the customer to run it and
#                          paste back.
# Commands are fixed constants (enum keys, no free text): one dispatch = one
# command; any token from the disallowed list kills the dispatch.
# ---------------------------------------------------------------------------
DISALLOWED_COMMAND_TOKENS = (
    "rm ", "mv ", "cp ", "dd ", "mkfs", "fdisk", "parted", "truncate",
    "kill", "pkill", "reboot", "shutdown", "halt", "poweroff", "init ",
    "mount", "umount", "sed -i", "chmod", "chown", "chattr", "useradd",
    "userdel", "passwd", "iptables", "systemctl restart", "systemctl stop",
    "systemctl start", "systemctl enable", "systemctl disable", "service ",
    ">", ">>", "curl ", "wget ", "rm -", "format", "diskpart",
)

GUEST_COMMANDS = {
    # --- tier-1: on the batch checklist, auto-sendable after confirmation ---
    "disk-usage": {
        "os": "linux", "cmd": "df -h", "auto_sendable": True,
        "purpose": "filesystem space usage (boot-blocking full disk check)",
    },
    "disk-inodes": {
        "os": "linux", "cmd": "df -i", "auto_sendable": True,
        "purpose": "inode usage (exhausted inodes can block boot and login)",
    },
    "mount-table": {
        "os": "linux", "cmd": "findmnt", "auto_sendable": True,
        "purpose": "current mount table vs fstab expectations",
    },
    "windows-volume-usage": {
        "os": "windows", "cmd": "Get-Volume", "auto_sendable": True,
        "purpose": "volume space usage on Windows guests",
    },
    # 2026-10-20 promoted to tier-1: the memory-exhaustion fact (small-spec
    # 'hangs, disk IO pegged' tickets) is only readable via free/ps inside the
    # guest; pure read, same double guard as disk-usage (Round8: F6 legs ranked
    # the right hypothesis with zero measured reads).
    "memory-usage": {
        "os": "linux", "cmd": "free -h", "auto_sendable": True,
        "purpose": "available memory / swap (OOM hang identification)",
    },
    "oom-traces": {
        "os": "linux", "cmd": "dmesg | tail -n 100", "auto_sendable": False,
        "purpose": "kernel ring tail for OOM-killer evidence",
    },
    "fstab-content": {
        "os": "linux", "cmd": "cat /etc/fstab", "auto_sendable": True,
        "purpose": ("auto-mount entries vs actually attached devices; a UUID here "
                    "missing from mount-table/lsblk is the stale-fstab root cause"),
    },
    # 2026-10-21 promoted to tier-1 after R13 A-line F2-sshd-deny: the guest had a
    # hardening drop-in setting PasswordAuthentication no, but `cat /etc/ssh/sshd_config`
    # only shows the `Include sshd_config.d/*.conf` line and `ls -l` only shows that a
    # drop-in exists - neither yields the EFFECTIVE value, so the leg had no way to
    # confirm the injected fact and mis-attributed a security-group Drop. `sshd -T`
    # prints the include-merged runtime configuration; read-only, exits immediately.
    "sshd-effective": {
        "os": "linux", "cmd": "sshd -T", "auto_sendable": True,
        "purpose": ("effective (include-merged) sshd configuration - password/root-login "
                    "policy and port as actually applied by the daemon, which the main "
                    "sshd_config file alone cannot show once a drop-in sets them"),
    },
    "dns-resolver": {
        "os": "linux", "cmd": "cat /etc/resolv.conf", "auto_sendable": False,
        "purpose": "resolver configuration (boot-time name failures)",
    },
    "listening-ports": {
        "os": "linux", "cmd": "netstat -lntu", "auto_sendable": False,
        "purpose": "listening sockets (service actually up vs not)",
    },
    "service-autostart": {
        "os": "linux", "cmd": "systemctl is-enabled sshd NetworkManager",
        "auto_sendable": False,
        "purpose": "boot autostart state of key units (status verb only)",
    },
    "atop-present": {
        "os": "linux", "cmd": "command -v atop", "auto_sendable": False,
        "purpose": "whether atop history exists for after-the-fact attribution",
    },
}

def guest_command_names():
    return sorted(GUEST_COMMANDS)

def is_clean_guest_command(cmd):
    """Guard: a whitelisted constant must contain no disallowed token.

    Single-word tokens are matched at word boundaries so legitimate command names
    that merely contain one (findmnt vs mount) are not rejected; multi-word patterns
    and shell redirect symbols stay substring checks.

    Pure; used both at import time (self-test) and before any dispatch.
    """
    text = " %s " % cmd.lower()
    for token in DISALLOWED_COMMAND_TOKENS:
        needle = token.strip()
        if not needle:
            continue
        if " " in needle or needle.strip("<>&|;") in ("", ">", ">>"):
            if needle in text:
                return False
            continue
        if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(needle), text):
            return False
    return True

# Command type values for RunCommand (Cloud Assistant script kinds).
RUN_COMMAND_TYPE_LINUX = "RunShellScript"
RUN_COMMAND_TYPE_WINDOWS = "RunPowerShellScript"

GUEST_CHANNEL_BLOCKED = (
    "Cloud Assistant is not installed / offline on this instance, so no guest "
    "reading can be dispatched. Fallback: ask the customer to run the exact "
    "single non-mutating command inside the instance (Workbench/VNC or SSH) and "
    "paste back. An infected or manually removed agent shows the same symptom; "
    "re-installing is a manual step per the Cloud Assistant docs.")

# ---------------------------------------------------------------------------
# Evidence-trust wording for the recurring customer emotion "did Alibaba Cloud
# touch my server": always answer with verifiable facts, never a bare denial.
# ---------------------------------------------------------------------------
TRUST_STATEMENT = (
    "The platform does not stop your services or edit files inside your "
    "instance; start/stop/reboot operations initiated from the console are "
    "also visible in your own operation records. Provide checkable items: the "
    "authorization timestamp, security-center alert presence, monitoring "
    "curves around the incident minute, and the instance operation history.")

# ---------------------------------------------------------------------------
# Handoff statements (boundary lines vs sibling skills / manual handling)
# ---------------------------------------------------------------------------
HANDOFFS = {
    "os_service": (
        "The instance itself is Running and Cloud Assistant is reachable, so "
        "the failure is at the guest service layer (unit status / logs / port / "
        "DNS inside the OS). Hand off to alibabacloud-ecs-linux-os-troubleshooting; "
        "carry the known readings so the customer is not asked twice."),
    "capacity": (
        "Boot is blocked by filesystem usage on the guest disk. Space/inode "
        "cleanup belongs to area:disk-expand-diagnosis; it always "
        "takes a snapshot before any cleanup."),
    "io_perf": (
        "Disk BPS/IOPS reached the ceiling of the instance type or disk "
        "performance level. area:resource-bottleneck covers spec "
        "limits and performance tuning."),
    "expand": (
        "The disk is attached but the partition/filesystem is not expanded -- "
        "that is area:disk-expand-diagnosis, not a boot fault."),
    "security": (
        "Signs of intrusion were found (tampered system files, miner behaviour, "
        "destroyed agents). Security incident response is out of scope here: "
        "snapshot the disks first, then engage the security team."),
    "billing": (
        "This instance is stopped because the subscription expired. Renewal "
        "(or building a custom image to preserve the environment meanwhile) is "
        "a commercial action the customer performs in the console; this skill "
        "never transacts."),
}

# ---------------------------------------------------------------------------
# Snapshot-first discipline (hard gate before ANY cleanup / repair / stop-
# restart guidance) and the customer-facing billing wording.
# ---------------------------------------------------------------------------
SNAPSHOT_FIRST_RULE = (
    "Before guiding ANY cleanup, boot repair, rollback, forced operation, or "
    "stop/restart of an abnormal instance, the customer must first create a "
    "snapshot of every disk involved and wait until it reaches 100%. The skill "
    "itself never calls a snapshot API; it emits the console steps, the billing "
    "note, and the three risk notes below.")

SNAPSHOT_BILLING_NOTE = (
    "Snapshots are billed separately (order of 0.12 CNY per GB-month; roughly "
    "0.4 CNY/day for a 100 GB disk -- the official snapshot pricing page is "
    "authoritative). Delete them once the operation is verified.")

SNAPSHOT_RISK_NOTES = (
    "1) a stop/restart interrupts running business briefly; "
    "2) data still in memory/cache is lost on a forced stop -- prefer the "
    "graceful flow and let it finish; "
    "3) stop application writes (and check autostart settings) before any "
    "rollback or re-initialization, because apps will be down afterwards until "
    "started or enabled.")

# ---------------------------------------------------------------------------
# Official documentation and console links (real URLs, canonical forms)
# ---------------------------------------------------------------------------
HELP_DOCS = {
    "stopping_timeout": "https://help.aliyun.com/zh/ecs/support/when-an-ecs-instance-is-stopped-or-restarted-in-the",
    "state_display_lag": "https://help.aliyun.com/zh/ecs/the-ecs-instance-remains-in-the-stopped-state-when-it-is-successfully-stopped-or-restarted-in-the-console",
    "restart_instances": "https://help.aliyun.com/zh/ecs/user-guide/restart-instances",
    "atop_metrics": "https://help.aliyun.com/zh/ecs/use-cases/use-the-atop-tool-to-monitor-linux-system-metrics",
    "atop_history": "https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools",
    "swap_linux": "https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance",
    "swap_windows": "https://help.aliyun.com/zh/ecs/support/how-to-configure-virtual-memory-for-windows-instances",
    "snapshot_create": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "snapshot_billing": "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "snapshot_delete": "https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1",
    "snapshot_rollback": "https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot",
    "disk_reinit": "https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk",
    "image_import": "https://help.aliyun.com/zh/ecs/user-guide/import-an-image",
    "image_from_instance": "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance",
    "image_share": "https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image",
    "renew_instance": "https://help.aliyun.com/zh/ecs/manually-renew-an-instance-1",
    "workbench_system": "https://help.aliyun.com/zh/ecs/user-guide/workbench-system-management.md",
    "cloud_assistant_stop": "https://help.aliyun.com/zh/ecs/user-guide/stop-and-uninstall-the-cloud-assistant-agent",
    "rdp_session_end": "https://help.aliyun.com/zh/ecs/via-remote-desktop-connection-windows-server-2022-instances-of-ecs-system-prompt-remote-desktop-services-session-is-over-you-may-be-one-of-the-following-causes-error",
    "renew_subscription": "https://help.aliyun.com/zh/ecs/manually-renew-an-instance-1",
}

CONSOLE_LINKS = {
    "instance_list": "https://ecs.console.aliyun.com/server/region/<regionId>",
    "cloud_assistant": "https://ecs.console.aliyun.com/cloud-assistant/region",
    "snapshots": "https://ecs.console.aliyun.com/snapshot/region/<regionId>",
    "security_group": "https://ecs.console.aliyun.com/securityGroup/region/<regionId>",
    "images": "https://ecs.console.aliyun.com/image",
    "host_monitor": "https://cloudmonitor.console.aliyun.com/hostMonitor/",
}

# Pre-baked answers for the manual atop / swap tail steps (customer-executed).
ATOP_MANUAL_STEP = (
    "After recovery, install atop manually so the NEXT hang is attributable: "
    "yum install atop -y && sed -i \"s#600#30#g\" /etc/sysconfig/atop && "
    "systemctl enable atop && systemctl start atop  "
    "(LOGINTERVAL=30, LOGGENERATIONS=7; on Alibaba Cloud Linux 3/4 first run "
    "yum update and install the epel-release rpm. Without atop pre-installed, "
    "which process saturated the host at the incident minute is unrecoverable "
    "-- state this honestly.)")

# VNC four-check stage judgement (manual; no API can fetch the boot screen).
VNC_FOUR_CHECKS = (
    "Open console VNC and watch the boot screen for: 1) stuck at the GRUB menu; "
    "2) fsck running long or erroring; 3) 'Emergency mode' or dracut rescue "
    "prompt; 4) kernel panic output. Each maps to a branch in the boot-failure "
    "reference. The boot screen cannot be captured by any cloud API -- "
    "this observation is inherently human (customer or operator) via VNC.")
