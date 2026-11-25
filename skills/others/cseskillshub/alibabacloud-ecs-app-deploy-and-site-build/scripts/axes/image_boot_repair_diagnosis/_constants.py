#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS image detection / repair-failure
/ boot-repair diagnosis
================================================================================
SECURITY: This skill is read-only on the cloud side. Authentication is
resolved exclusively by the aliyun CLI default credential chain; this module
never reads, writes, caches or logs any AccessKey ID / Secret. No credential
handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
ALL reference knowledge (detection-item semantics, repair-failure error-code
mapping, boot-failure signatures, the guest read-only command whitelist, the
boundary-handoff routes and the official documentation links) is embedded
here as Python constants, distilled from real ECS support tickets and the
cited official help pages. There are NO data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity and channel constants
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-image-boot-repair-diagnosis"

# User-Agent template (observability). Every API call made by the scripts
# carries: AlibabaCloud-Agent-Skills/{skill_name}/{session_id}
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

# API versions actually called (informational; the aliyun CLI carries its own
# metadata). ECS read API version verified live on 2026-09-16.
API_VERSION_ECS = "2014-05-26"
API_VERSION_STS = "2015-04-01"

DEFAULT_REGION = "cn-hangzhou"
DEFAULT_TIMEOUT = 60        # per-call timeout in seconds (MUST 7.6.1)
PROBE_POLL_TIMEOUT = 90     # max seconds spent polling one guest probe result
PROBE_POLL_INTERVAL = 5     # seconds between status read-backs

# Query guardrails
MAX_PAGES = 10              # page-loop guardrail per list API
PAGE_SIZE = 50              # records per page (ECS list APIs allow >= 50)

# ---------------------------------------------------------------------------
# API names used by the scripts (verified via `aliyun ecs <Action> --help`
# offline metadata and, for the read actions, live read-only calls on
# 2026-09-16 under the evaluation role). Do not call anything outside this
# list -- the SKILL.md API whitelist is authoritative.
# ---------------------------------------------------------------------------

API_DESCRIBE_INSTANCES = "DescribeInstances"
API_DESCRIBE_IMAGES = "DescribeImages"
API_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"
API_DESCRIBE_INVOCATIONS = "DescribeInvocations"
API_RUN_COMMAND = "RunCommand"
API_GET_CALLER_IDENTITY = "GetCallerIdentity"

# ---------------------------------------------------------------------------
# Guest read-only command whitelist (low-risk operations list, class B)
# ---------------------------------------------------------------------------
# One whitelisted command is dispatched per consent, and only to read actual
# in-guest state that no cloud API can see. Commands are named by their first
# token; `stat`/`ls` additionally require exactly one plain absolute-path
# argument. Anything else is refused -- see classify_guest_command() and
# references/guest-readonly-commands.md.

GUEST_COMMAND_WHITELIST = {
    "findmnt": (
        "shows the mounts that are actually live in this boot, to diff "
        "against what the image's fstab declares"
    ),
    "stat": (
        "existence and type of ONE declared mount-target directory or one "
        "documented component directory; no file contents are read"
    ),
    "ls": (
        "listing of ONE mount-target directory or one documented component "
        "directory; no file contents are read"
    ),
}

# Explicitly NOT on the whitelist. Kept so a reviewer sees the boundary is a
# decision, not an oversight; the entry script quotes these back when a
# request is refused.
GUEST_COMMAND_DENY_LIST = [
    ("cat", "reads file contents (e.g. the fstab file itself): outside the "
            "low-risk read-only list; the customer is asked to paste the "
            "file instead"),
    ("grep", "content search over files: outside the low-risk read-only "
             "list"),
    ("sed", "can rewrite files in place: a write"),
    ("vi", "an editor: a write"),
    ("systemctl", "service state and control, including status queries: "
                  "outside the low-risk read-only list"),
    ("lsblk", "block-device enumeration: outside the low-risk read-only "
              "list"),
    ("blkid", "filesystem probing: outside the low-risk read-only list"),
    ("fdisk", "partition tooling: refused even read-only listing"),
    ("mount", "changes mount state: a write"),
    ("umount", "changes mount state: a write"),
    ("grub", "bootloader inspection or regeneration: never run here; the "
             "customer-facing repair paths live in references/handoff.md"),
    ("apt", "package management: a write"),
    ("yum", "package management: a write"),
    ("dnf", "package management: a write"),
]

# Shell metacharacters: their presence anywhere in the assembled string aborts
# the call before dispatch (they could smuggle a second command).
SHELL_METACHARACTER_RE = r"[;&|<>`$(){}\n\r*\"]"

# ---------------------------------------------------------------------------
# Image-detection item semantics (detection-result axis)
# ---------------------------------------------------------------------------
# Keyed by a stable slug; `match` lists lowercase substrings that, when found
# in a customer-pasted detection report, select the item. Every field here is
# traceable to a real support ticket or a cited official help page; anything
# the evidence does not settle is marked "not settled by docs" and is NOT
# asserted more strongly than that.

DETECTION_ITEMS = {
    "mount-target-dir-not-found": {
        "match": ["disk.mounttargetdirnotfound", "mounttargetdirnotfound"],
        "label": "Disk.MountTargetDirNotFound (reported as critical)",
        "meaning": (
            "The image's fstab declares a mount target directory that does "
            "not exist inside the image. Most often it is a data-disk or "
            "template-era leftover entry on instances that only carry a "
            "system disk; observed across every custom image of one "
            "account, across regions, on this axis."
        ),
        "import_impact": (
            "It does not block import or snapshot/backup validity; it is a "
            "content warning about the image. 'Critical' here is the "
            "detection grade, NOT a verdict that the backup is unusable."
        ),
        "boot_impact": (
            "Whether the missing target actually blocks boot depends on the "
            "fstab options of that line (network/file-system-type flags "
            "change the behavior); this is exactly why a read-only guest "
            "check is needed before calling it ignorable."
        ),
        "guest_check": [
            "findmnt",
            "stat <each declared mount target directory>",
            "ls <each declared mount target directory>",
        ],
        "manual_steps": (
            "Manual, customer-run only: comment out the stale fstab line "
            "for the device that no longer exists (or point it at a "
            "directory that exists), boot-test, then rebuild the custom "
            "image and re-run image detection."
        ),
        "doc": "detect-custom-images-and-repair",
    },
    "cloud-assistant-warn": {
        "match": ["cloudassistant", "cloud assistant"],
        "label": "CloudAssistant not installed (WARN)",
        "meaning": (
            "The custom image (typically a locally prepared, OS-vendor "
            "minimal image) does not ship the Cloud Assistant agent, which "
            "official and marketplace images integrate automatically."
        ),
        "import_impact": (
            "This is a WARN, not an import blocker: WARN-level items do "
            "not stop image use. Whether a WARN must be fixed before an "
            "OS-level feature works is NOT settled by the docs for every "
            "WARN; do not promise either way -- the agent install is a "
            "separate, customer-run step after first boot."
        ),
        "boot_impact": "Absent agent does not block boot.",
        "guest_check": [
            "ls <the agent install directory from the official install "
            "doc; never guessed>",
            "stat <the same directory>",
        ],
        "manual_steps": (
            "Manual, customer-run only: install the agent per the official "
            "install doc on a running instance made from the image, then "
            "rebuild the image; agent runtime faults belong to the Cloud "
            "Assistant axis (handoff.md)."
        ),
        "doc": "check-whether-an-image-meets-import-requirements",
    },
    "security-center-agent-warn": {
        "match": ["securitycenteragent", "security center agent", "aegis"],
        "label": "SecurityCenterAgent (Aegis) not installed (WARN)",
        "meaning": (
            "The image does not ship the Security Center agent; official "
            "and marketplace images normally integrate it."
        ),
        "import_impact": (
            "WARN: does not block import. Whether it is mandatory is NOT "
            "settled by the docs quoted in this batch; state that openly."
        ),
        "boot_impact": "Absent agent does not block boot.",
        "guest_check": [
            "stat <the agent install directory from the official install "
            "doc; never guessed>",
        ],
        "manual_steps": (
            "Manual, customer-run only: install per the official Security "
            "Center agent doc on a running instance, then rebuild the "
            "image; agent runtime belongs to the security axis."
        ),
        "doc": "check-whether-an-image-meets-import-requirements",
    },
    "nvme-driver-adaptation": {
        "match": ["nvme"],
        "label": "NVMe driver not adapted (instance-family compatibility)",
        "meaning": (
            "Newer instance families attach the system disk as an NVMe "
            "device; an imported custom image whose kernel/initramfs "
            "lacks NVMe support cannot be selected for those families."
        ),
        "import_impact": (
            "Import succeeds; instance-type selection fails later, which "
            "is exactly what customers report ('the image cannot be "
            "chosen when buying an 8i-family instance')."
        ),
        "boot_impact": (
            "On NVMe-only families the guest cannot mount its system disk "
            "without the driver: the symptom reads as boot failure."
        ),
        "guest_check": [
            "stat /dev",
        ],
        "guest_check_note": (
            "stat of /dev only after the guest boots on a compatible "
            "family: it shows whether NVMe device nodes exist; this reads "
            "no file contents."
        ),
        "manual_steps": (
            "Manual: rebuild the image with a kernel/initramfs that "
            "carries the NVMe driver; whether an image advertises NVMe "
            "support can be read from the DescribeImages Features field "
            "when the account-visible record carries it; otherwise rely "
            "on the purchase-time error."
        ),
        "doc": "import-a-custom-image",
    },
    "image-format-header": {
        "match": ["invalid image format in header"],
        "label": "Invalid image format in header (import failure)",
        "meaning": (
            "The uploaded raw/VMDK/QCOW2 file's header does not satisfy "
            "the import format requirements -- a classic case is a "
            "Workstation-produced VMDK with a descriptor split across "
            "subfiles."
        ),
        "import_impact": "Hard import blocker: nothing to diagnose inside "
                         "the guest; the fix is local file conversion.",
        "boot_impact": "Not applicable (image never lands).",
        "guest_check": [],
        "manual_steps": (
            "Manual, customer-side: flatten/convert the disk with the "
            "vendor tool (e.g. qemu-img convert / vmware-vdiskmanager) "
            "to a format the import doc accepts, re-upload, re-import. "
            "Exact format requirements are defined by the import doc -- "
            "cite it, do not improvise flags."
        ),
        "doc": "import-a-custom-image",
    },
}

# ---------------------------------------------------------------------------
# Image-repair failure semantics (repair-failure axis)
# ---------------------------------------------------------------------------
# The repair task provisions transient pay-as-you-go resources in the
# customer's own account (a transition VPC, VSwitch and security group, then
# one instance) and runs a repair script there. Customers paste the pipeline
# log; this skill never fetches it (no read-only task-detail API was verified
# for this scenario -- see references/ram-policies.md).

REPAIR_STAGES = [
    ("transition-network", ["create transition vpc", "vswitch",
                            "securitygroup"],
     "transition network resources (VPC / VSwitch / security group)"),
    ("transition-instance", ["createinstance"],
     "the transition pay-as-you-go instance order"),
    ("guest-repair-script", ["start executing the imagepipeline",
                             "runcommand", "repair script"],
     "the repair script phase on the transition instance"),
    ("release", ["failed to prepare transition resources",
                 "start releasing resources"],
     "transition-resource rollback"),
]

REPAIR_ERROR_CODES = {
    "InvalidAccountStatus.NotEnoughBalance": {
        "root_cause": (
            "Account balance is below the postpaid-ordering threshold: the "
            "repair flow must first order a pay-as-you-go transition "
            "instance, and ordering postpaid products requires an account "
            "balance of at least 100 CNY (the repair itself spends far "
            "less). The failure lands at the CreateInstance step, so the "
            "transition network lines above it succeed."
        ),
        "conclusion": (
            "NOT an image-content problem: nothing inside the image failed. "
            "The repair never reached the guest-script stage."
        ),
        "exit_path": (
            "Manual: top up the account balance, then re-trigger image "
            "repair from the console image-detection page (the customer "
            "does this; this skill never triggers or executes a repair). "
            "Note the transient instance is billed while it runs and is "
            "released afterwards."
        ),
        "task_page_note": (
            "When the task-management page shows a status that contradicts "
            "the log error, report both sources verbatim and recommend "
            "console/human verification; do not declare success or "
            "invent a page-status mechanism -- the task-page semantics are "
            "NOT settled by any verified doc in this batch."
        ),
    },
}

# ---------------------------------------------------------------------------
# Boot-failure signatures (boot-repair guidance axis)
# ---------------------------------------------------------------------------
# When the instance will not boot there is NO channel into the guest (the
# Cloud Assistant agent lives inside the guest), so this axis is
# root-cause-mapping plus guided self-repair, never claimed remote reads.

BOOT_SIGNATURES = {
    "grub-damage-after-kernel-upgrade": {
        "match": ["stuck at bios", "bios screen", "grub rescue",
                  "grub error", "no such device", "you need to load "
                  "the system first", "kernel upgrade", "upgrade to",
                  "after apt", "does not boot after upgrade"],
        "verdict": (
            "Bootloader (GRUB) damage candidate: the classic sequence is "
            "an in-guest distribution/kernel upgrade that rewrites or "
            "orphans the boot entries; on a verified Debian 12 -> 13 "
            "upgrade the instance froze at BIOS and only a regenerated "
            "GRUB restored boot. Other root causes (fstab blocking boot, "
            "missing NVMe driver, corrupted filesystem) stay candidates "
            "until console-side boot logs or a repair-disk inspection "
            "distinguish them."
        ),
        "why_no_guest_read": (
            "STATUS: DEGRADED on the guest-read axis: the instance cannot "
            "boot, so the Cloud Assistant agent cannot answer; nothing in "
            "this skill can read a boot sector remotely. Everything below "
            "is guidance plus customer-pasted evidence."
        ),
        "self_repair_paths": [
            "console-side diagnostic page: attach a PE/live repair disk "
            "from the instance's diagnostic UI, then repair inside that "
            "live environment (this wording comes from a verified support "
            "answer; no official URL was verified in this batch -- state "
            "the console path, do not fabricate a link)",
            "detach the system disk, attach it as a data disk to a "
            "healthy instance, chroot into it and regenerate GRUB, then "
            "detach and reattach to the source instance (verified support "
            "answer; every step is customer-run)",
        ],
        "risk_notes": [
            "Both paths stop the instance first: business interruption, "
            "in-memory data not yet flushed is lost; stop applications "
            "gracefully before.",
            "A snapshot backup before any repair is strongly recommended; "
            "snapshots are a billed feature (cite the snapshot-billing "
            "page, link below).",
            "This skill performs NONE of these steps: they are manual "
            "console operations or a human support ticket.",
        ],
        "post_repair_recheck": (
            "After the customer repairs: DescribeInstanceStatus to confirm "
            "the lifecycle state, then ask the customer to confirm the OS "
            "reaches its login/system stage, then re-run the whitelisted "
            "guest checks that motivated the repair (verify-repair mode)."
        ),
    },
    "fstab-blocked-boot": {
        "match": ["failed to mount", "mount point", "emergency mode",
                  "give root login", "dependency failed on mount"],
        "verdict": (
            "fstab mount-target defect candidate (the Disk.MountTargetDir"
            "NotFound family above): a declared mount whose target or "
            "source cannot come up can park the boot in emergency mode."
        ),
        "self_repair_paths": [
            "same two guided paths as the GRUB case (PE/live repair disk, "
            "or system-disk-on-another-instance chroot): comment the stale "
            "fstab line, then reattach and boot",
        ],
        "why_no_guest_read": "same as the GRUB case: no boot, no agent",
        "risk_notes": "same stop/snapshot/billing notes as the GRUB case",
        "post_repair_recheck": "verify-repair mode after boot returns",
    },
}

# ---------------------------------------------------------------------------
# Boundary handoff table (which axis belongs to which skill/staff)
# ---------------------------------------------------------------------------

HANDOFF_ROUTES = [
    {
        "route": "image-snapshot-billing",
        "patterns": ["how much do i pay", "storage fee", "traffic fee",
                     "down fee", "download fee", "deducted", "resource "
                     "plan", "can i delete the old image", "billing of "
                     "images", "arrears", "invoice"],
        "target_skill": "alibabacloud-ecs-image-billing-cleanup",
        "script": (
            "Image / snapshot / OSS storage and traffic billing, package "
            "deduction, and whether an old image can be deleted belong to "
            "the image billing and cleanup axis. Hand over: keep only the "
            "one fact directly relevant here -- repair needs a postpaid "
            "transition instance, hence the 100-CNY balance threshold."
        ),
    },
    {
        "route": "cloud-assistant-agent",
        "patterns": ["cloud assistant", "assist agent", "command cannot "
                     "run", "agent offline", "aegis offline"],
        "target_skill": "alibabacloud-ecs-cloud-assistant-diagnosis",
        "script": (
            "Detecting that the agent is absent is this skill; installing, "
            "upgrading or debugging the agent itself belongs to the Cloud "
            "Assistant axis."
        ),
    },
    {
        "route": "instance-start-stop-state",
        "patterns": ["stuck in starting", "stopping state", "cannot stop",
                     "force reboot", "state machine"],
        "target_skill": "alibabacloud-ecs-instance-start-stop-anomaly",
        "script": (
            "Instance lifecycle state machine anomalies (Starting / "
            "Stopping / Pending parked) belong to the instance "
            "start-stop axis; this skill covers image content and "
            "bootloader root causes once the state machine is healthy."
        ),
    },
    {
        "route": "backend-image-service",
        "patterns": ["backend", "internal error keeps repeating",
                     "retried for days"],
        "target_skill": None,
        "script": (
            "Suspected platform-side image-service faults are invisible to "
            "every cloud-side read here: say so, and file a human support "
            "ticket with this report attached."
        ),
    },
    {
        "route": "import-export-conversion",
        "patterns": ["convert", "vmdk to", "qcow2", "download the image",
                     "export to local", "tool on my laptop"],
        "target_skill": None,
        "script": (
            "Local format conversion and import/export tooling run on the "
            "customer's side: give the official doc path and the exact "
            "error mapping; this skill never touches local files."
        ),
    },
]

# ---------------------------------------------------------------------------
# Official documentation links (help.aliyun.com, verified reachable on
# 2026-08-14 from the injected help-search evidence). Only these URLs may be
# cited. NOT cited (no verified URL in this batch): the console PE/live
# repair-disk feature page, the NVMe adaptation page, the fstab-fix page,
# and both agent install pages -- their paths are described in words, and
# the report says the URL check is pending.
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "check-whether-an-image-meets-import-requirements": (
        "https://help.aliyun.com/zh/ecs/user-guide/check-whether-an-image-"
        "meets-the-import-requirements.md"
    ),
    "detect-custom-images-and-repair": (
        "https://help.aliyun.com/zh/ecs/user-guide/detect-custom-images-"
        "and-repair.md"
    ),
    "import-a-custom-image": (
        "https://help.aliyun.com/zh/ecs/user-guide/import-a-custom-image.md"
    ),
    "createimage-api": (
        "https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-"
        "05-26-createimage.md"
    ),
    "instance-overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/overview-52.md"
    ),
    "snapshot-billing": (
        "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1"
    ),
}

# ---------------------------------------------------------------------------
# Disclosure template for one consent-gated guest probe (printed verbatim)
# ---------------------------------------------------------------------------

PROBE_DISCLOSURE = [
    "What will run      : EXACTLY ONE command, shown above, inside one",
    "                       instance via the Cloud Assistant channel,",
    "                       under the customer's own credentials.",
    "Read-only nature   : the command only lists or stats paths/mounts;",
    "                       it writes nothing, installs nothing, reads no",
    "                       file contents.",
    "Blast radius       : one instance, one command, stdout text only.",
    "Reversibility      : no state change to undo; nothing persistent is",
    "                       produced inside the guest.",
    "Consent scope      : this confirmation is for THIS region, THIS",
    "                       instance and THIS command only.",
]

# Report banner
REPORT_TITLE = "ECS image detection / repair-failure / boot-repair diagnosis"
