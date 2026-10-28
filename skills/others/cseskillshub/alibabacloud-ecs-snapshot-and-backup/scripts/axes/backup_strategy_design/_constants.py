#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and reference data for the
alibabacloud-ecs-backup-strategy-design skill.

SECURITY: This skill is strictly READ-ONLY. This module contains static
constants only: it performs no network calls, no subprocess calls, and no
credential handling of any kind. Authentication for the whole skill is
resolved exclusively by the aliyun CLI default credential chain; this module
never reads, writes, prints, or passes any AccessKey, Secret, or token.

Platform rule MUST 1.1.2: scripts/ may contain executable code only, so ALL
static reference knowledge (mechanism rules, billing models, policy-design
rules, failure/handoff patterns, official document URLs) is embedded here as
Python constants. There are no data files in scripts/.
"""

SKILL_NAME = "alibabacloud-ecs-backup-strategy-design"

# ---------------------------------------------------------------------------
# API / endpoint constants
# ---------------------------------------------------------------------------

STS_ENDPOINT = "sts.aliyuncs.com"
API_VERSIONS = {"ecs": "2014-05-26", "sts": "2015-04-01"}

# Default region for read-only fact queries (auto-filled and declared).
DEFAULT_REGION = "cn-hangzhou"

# Per-call timeout (seconds) applied to every CLI subprocess invocation
# (platform rule MUST 7.6.1).
DEFAULT_TIMEOUT = 60

# Pagination caps for the read-only instance queries.
PAGE_SIZE = 100              # MaxResults for DescribeInstances (max 100)
STATUS_PAGE_SIZE = 50        # PageSize for DescribeInstanceStatus (max 50)
MAX_PAGES = 20

# Upper bounds for user-supplied numeric inputs (sanity caps, not official
# product limits -- official ranges live in the linked docs).
MAX_RETENTION_DAYS = 3650
MAX_SNAPSHOTS_PER_DAY = 24
MAX_DISK_COUNT = 64
MAX_DATA_GB = 1_000_000_000

# Free-text input caps.
MAX_TEXT_LEN = 2000

# ---------------------------------------------------------------------------
# Official documentation set (source: the confirmed requirements document).
# The evidence batch runs through 2026-08-30. Per the data-boundary rule the
# set is NOT formally re-verified in this static-only development mode: every
# citation must carry the note below until each URL is re-checked.
# ---------------------------------------------------------------------------

DOC_VERIFICATION_NOTE = (
    "Document set baseline: evidence batch through 2026-08-30; not formally "
    "re-verified in this build -- re-check each URL before quoting it to a "
    "customer."
)

DOC_URLS = {
    "snapshot-overview": "https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview",
    "how-snapshots-work": "https://help.aliyun.com/zh/ecs/user-guide/how-do-snapshots-work",
    "auto-snapshot-policy": "https://help.aliyun.com/zh/ecs/user-guide/automatic-snapshot-policy",
    "enable-disable-auto-policy": "https://help.aliyun.com/zh/ecs/user-guide/enable-or-disable-an-automatic-snapshot-policy",
    "delete-auto-policy": "https://help.aliyun.com/zh/ecs/user-guide/delete-an-automatic-snapshot-policy",
    "create-snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    # Two snapshot-billing URLs were cited in the evidence batch; which one is
    # the current canonical path is an open item -- both are kept, in order.
    "snapshot-billing-a": "https://help.aliyun.com/zh/ecs/snapshots-1",
    "snapshot-billing-b": "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "pay-as-you-go": "https://help.aliyun.com/zh/ecs/pay-as-you-go-1",
    "savings-plan": "https://help.aliyun.com/zh/ecs/purchase-savings-plan",
    "cloud-backup-billing": "https://help.aliyun.com/zh/cloud-backup/product-overview/billing-methods-and-billable-items",
    "cloud-backup-db-start": "https://help.aliyun.com/zh/cloud-backup/getting-started/get-started-with-on-premises-database-backup",
    "file-backup-basic-faq": "https://help.aliyun.com/document_detail/2979167.html",
    "backup-local-disk": "https://help.aliyun.com/zh/ecs/user-guide/backup-local-disk-data.md",
    "best-practices-local-disks": "https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-local-disks.md",
    "windows-low-disk-space": "https://help.aliyun.com/zh/ecs/user-guide/handle-low-disk-space-on-windows-instances",
    "oos-disk-cleanup": "https://help.aliyun.com/zh/ecs/user-guide/use-oos-to-clear-disks-on-a-regular-basis",
    "resize-windows-cloud-disks": "https://help.aliyun.com/zh/ecs/user-guide/resize-windows-cloud-disks",
    "atop-monitor": "https://help.aliyun.com/zh/ecs/use-cases/use-the-atop-tool-to-monitor-linux-system-metrics",
    "payg-to-subscription": "https://help.aliyun.com/document_detail/49884.html",
    "host-security": "https://help.aliyun.com/zh/ecs/user-guide/enable-host-security.md",
    "app-security": "https://help.aliyun.com/zh/ecs/user-guide/application-security.md",
    "cli-install": "https://help.aliyun.com/document_detail/121541.html",
}

# ---------------------------------------------------------------------------
# User-Agent observability
# ---------------------------------------------------------------------------

# Every aliyun CLI call carries --user-agent built from this template;
# {session_id} is a per-run 32-char lowercase hex string (uuid4().hex).
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/" + SKILL_NAME + "/{session_id}"

# ---------------------------------------------------------------------------
# Backup-object -> mechanism mapping (design knowledge, one entry per object)
# ---------------------------------------------------------------------------

MECHANISM_RULES = {
    "whole-instance": {
        "label": "Whole instance / system state",
        "mechanisms": [
            "manual snapshot per disk (one-off, e.g. before a risky operation)",
            "automatic snapshot policy (periodic protection)",
        ],
        "core_rule": (
            "An automatic snapshot policy protects ONLY the disks it is "
            "applied to; a policy that was created but never applied to any "
            "disk does nothing. This is the top root cause of 'the policy is "
            "not working'."
        ),
        "single_disk_note": (
            "When the instance has only one system disk, applying the policy "
            "to that disk covers the whole system state stored on it."
        ),
        "limitations": [
            "Snapshots are crash-consistent block-level copies; a running "
            "database additionally needs an application-level backup "
            "(Cloud Backup database backup) for transactional consistency.",
            "Local disks (instance families whose type starts with ecs.i or "
            "ecs.d) do not support snapshots at all.",
        ],
        "customer_steps": [
            "ECS console > Storage & Snapshots > Automatic Snapshot Policy: "
            "create the policy (recurrence days, time points, retention "
            "days) -- you perform this in the console.",
            "Apply the policy to the specific disk(s); the binding is what "
            "makes it take effect.",
            "Before a risky operation, take a manual snapshot of each disk "
            "first (you perform it; a short retention such as 1 day is fine "
            "for one-off protection).",
        ],
        "gap_probes": [
            "Which disks exist and what data lives on each (system vs data "
            "disks)?",
            "Is any business-critical disk left uncovered?",
            "Is this instance on a local-disk family (snapshot unavailable)?",
        ],
        "docs": [
            "snapshot-overview", "how-snapshots-work", "auto-snapshot-policy",
            "enable-disable-auto-policy", "create-snapshot",
        ],
    },
    "files": {
        "label": "Selected files / directories",
        "mechanisms": [
            "ECS file backup basic edition (free)",
            "Cloud Backup file backup (paid, broader coverage)",
        ],
        "core_rule": (
            "The free file-backup basic edition has hard limits; a common "
            "mis-selection is relying on it for database directories."
        ),
        "single_disk_note": "",
        "limitations": [
            "Database software installation directories (e.g. MSSQL data "
            "directories) are NOT covered by the free basic edition.",
            "Retention is fixed at 30 days and cannot be customized.",
            "When backup capacity is exhausted, backups FAIL -- there is no "
            "automatic overwrite of the oldest data.",
        ],
        "customer_steps": [
            "Enable ECS file backup (basic edition) in the console and select "
            "the backup paths -- you perform this.",
            "Cross-check the selected paths against the limits above.",
            "For anything the basic edition cannot cover, plan Cloud Backup "
            "instead (you activate and configure it).",
        ],
        "gap_probes": [
            "Are any chosen backup paths inside a database installation "
            "directory?",
            "Is a 30-day fixed retention acceptable, or is another retention "
            "required (then file backup basic edition is the wrong tool)?",
            "Is enough backup capacity reserved so jobs do not fail on a "
            "full capacity?",
        ],
        "docs": ["file-backup-basic-faq", "snapshot-overview"],
    },
    "database": {
        "label": "Database engine data (MySQL / SQL Server / ...)",
        "mechanisms": [
            "Cloud Backup database backup (paid, application level)",
            "snapshots as a block-level safety net alongside",
        ],
        "core_rule": (
            "Databases need a dedicated mechanism: the free file backup "
            "excludes DB installation directories, and snapshots alone are "
            "crash-consistent, not application-consistent."
        ),
        "single_disk_note": "",
        "limitations": [
            "Cloud Backup database backup is a paid capability billed under "
            "the Cloud Backup billing model.",
            "Restoring a snapshot gives a disk-level point in time, not a "
            "transactionally consistent database state.",
        ],
        "customer_steps": [
            "Set up Cloud Backup database backup for the engine (you perform "
            "the configuration in the Cloud Backup console).",
            "Keep an automatic snapshot policy on the database disks as a "
            "second layer.",
        ],
        "gap_probes": [
            "Where is the DB installed (data directory path)?",
            "Is there an application-level backup, or only snapshots?",
            "What recovery point objective (acceptable data loss window) "
            "drives the backup frequency?",
        ],
        "docs": ["cloud-backup-db-start", "cloud-backup-billing"],
    },
    "local-copy": {
        "label": "Copy data to a local machine / offline",
        "mechanisms": [
            "custom image, then export the image to OSS and download it "
            "locally",
            "per-file download with customer-side transfer tooling",
        ],
        "core_rule": (
            "This is a multi-step, customer-executed process; the skill only "
            "lists the steps and the failure modes to self-check."
        ),
        "single_disk_note": "",
        "limitations": [
            "The export image to OSS process doc URL was not part of the "
            "evidence batch: search the official help site before quoting a "
            "URL for it.",
            "Non-ECS products (e.g. Web Hosting class products) have no ECS "
            "image/snapshot capability at all -- route to that product line "
            "first.",
            "Large downloads can inflate for instance-local reasons (log "
            "growth, transfer client following symlinks, mounted object "
            "storage counted as local data) -- run the download-bloat "
            "self-check topic.",
        ],
        "customer_steps": [
            "Create a custom image from the instance (you perform it).",
            "Export the image to an OSS bucket and download it locally (you "
            "perform it).",
            "For a small number of files, transfer them directly with your "
            "own client tooling instead.",
        ],
        "gap_probes": [
            "Is the source really an ECS instance (ECS image/snapshot "
            "capabilities exist there) rather than another cloud product?",
            "How much data, and does a per-file transfer beat an image "
            "export?",
        ],
        "docs": ["snapshot-overview"],
    },
    "off-site": {
        "label": "Cross-region / off-site backup",
        "mechanisms": [
            "snapshot cross-region copy (manual copy of selected snapshots, "
            "or copies produced along the automatic snapshot policy)",
        ],
        "core_rule": (
            "Copies are triggered per snapshot: however many snapshots are "
            "created, that many are copied and billed. A policy that takes "
            "2 snapshots a day and copies each one produces 2 copy billings "
            "a day per disk."
        ),
        "single_disk_note": (
            "Redesign lever: snapshot more often locally, copy fewer times "
            "(e.g. copy once a day) to cut copy traffic -- decide against "
            "the recovery point you actually need."
        ),
        "limitations": [
            "Each copy bills a cross-region copy traffic fee PLUS standard "
            "snapshot storage in the destination region.",
            "Archived snapshots cannot be copied to another region.",
        ],
        "customer_steps": [
            "Configure snapshot copy in the snapshot console (you perform "
            "it); check which snapshots the copy is applied to and how often "
            "new ones appear.",
        ],
        "gap_probes": [
            "Is off-site a compliance requirement or a disaster hedge? "
            "(drives copy frequency)",
            "How many snapshots per day does the current design produce per "
            "disk?",
        ],
        "docs": ["snapshot-billing-a", "snapshot-billing-b", "auto-snapshot-policy"],
    },
}

# Synonym normalization for --target values (lowercase lookup).
TARGET_SYNONYMS = {
    "instance": "whole-instance", "server": "whole-instance",
    "whole": "whole-instance", "system": "whole-instance",
    "disk": "whole-instance", "image": "whole-instance",
    "file": "files", "files": "files", "folder": "files",
    "directory": "files", "directories": "files",
    "database": "database", "db": "database", "sql": "database",
    "local": "local-copy", "download": "local-copy", "offline": "local-copy",
    "offsite": "off-site", "off-site": "off-site",
    "cross-region": "off-site", "remote": "off-site",
}

# Local-disk instance-family heuristic (rule knowledge, not an API field):
# instance types beginning with ecs.i<N> / ecs.d<N> are local-disk families.
# Confirm against the instance-type spec before stating it to a customer.
LOCAL_DISK_FAMILY_NOTE = (
    "Heuristic only: instance types starting with ecs.i or ecs.d (then a "
    "digit) belong to local-disk families, which do not support snapshots. "
    "Confirm with the official instance-type specification page."
)

# ---------------------------------------------------------------------------
# Billing model knowledge (NEVER a committed amount)
# ---------------------------------------------------------------------------

NO_COMMITMENT_STATEMENT = (
    "Backup charges depend on the real changed-data volume and how the "
    "retention actually executes; a fixed amount cannot be committed in "
    "advance. Only the billing model and a parameterized example are given "
    "here."
)

SNAPSHOT_CAPACITY_RULES = [
    "The first snapshot of a disk is a full copy of the used blocks; later "
    "snapshots store only the blocks that changed since earlier snapshots.",
    "Deleting a file inside the guest does NOT shrink snapshot usage: the "
    "blocks stay occupied until every snapshot referencing them is deleted.",
    "The size shown per snapshot in the console is the full amount needed "
    "to restore from it, not the incremental delta billed for that snapshot.",
    "Steady-state snapshot usage therefore grows over time and is larger "
    "than the guest's current disk usage.",
    "Snapshot storage is billed per region by snapshot usage (GB) held over "
    "time, pay-as-you-go, at the official snapshot rate (standard vs "
    "archived rates differ -- read them from the billing doc).",
    "Automatic snapshot policies offer NO 'cold backup' snapshot type "
    "selection; the archived snapshot exists but cannot be copied across "
    "regions.",
]

CROSS_REGION_COPY_RULES = [
    "A snapshot copy bills once per copy operation: a cross-region copy "
    "traffic fee plus destination-region standard snapshot storage for the "
    "copied snapshot.",
    "Copies follow the snapshots: however many snapshots are created, that "
    "many are copied ('create N, copy N').",
    "Archived snapshots cannot be copied to another region.",
]

FILE_BACKUP_BILLING_RULES = [
    "The ECS file backup basic edition is free but limited (fixed 30-day "
    "retention, database installation directories excluded, no automatic "
    "overwrite: a full capacity makes jobs fail).",
    "Cloud Backup database backup is paid under the Cloud Backup billing "
    "model (see the Cloud Backup billing-methods doc).",
]

RESOURCE_PACKAGE_NOTE = (
    "Per the official OSS resource-plan overview, a Standard-LRS storage "
    "package can deduct ECS snapshot storage fees (same evidence as the "
    "sibling OSS billing skill, verified there on 2026-09-02). Re-verify "
    "the overview before quoting; package purchase, refunds and commercial "
    "negotiation are outside this skill."
)

# ---------------------------------------------------------------------------
# Policy effectiveness verification (degraded path: no policy API here)
# ---------------------------------------------------------------------------

EFFECTIVENESS_NOT_FETCHED = (
    "Snapshot lists, automatic-snapshot-policy objects and their disk "
    "bindings, and file-backup job status are NOT FETCHED through an API by "
    "this skill (their permission points are unverified for this release; "
    "see references/ram-policies.md). Effectiveness is judged from the "
    "console self-check steps below or from the customer's console report."
)

EFFECTIVENESS_SELFCHECK_STEPS = [
    "ECS console > Automatic Snapshot Policy (region selector set to the "
    "instance's region): does the policy appear in the list?",
    "Open the policy: is it APPLIED to the target disk(s)? An empty applied-"
    "disks (binding) list means the policy never runs -- this is the root "
    "cause pattern to rule out first.",
    "ECS console > Snapshots: after the next scheduled time point, does a "
    "new automatic snapshot exist for each applied disk?",
    "If copies are expected off-site: check the destination region's "
    "snapshot list for the copied snapshot.",
]

# ---------------------------------------------------------------------------
# Failure / symptom classification rules (customer-visible English wording;
# non-English alerts are translated by the Agent before re-running)
# ---------------------------------------------------------------------------
# Order matters: first matching rule wins. Keys are lowercase substrings.
CONDITION_RULES = [
    {
        "category": "precondition_disk_full",
        "patterns": ["insufficient disk space", "disk space is not enough",
                     "no space left", "backup failed due to"],
        "route": False,
        "verdict": (
            "Backup precondition failure: the disk holding the backup "
            "agent/job path ran out of space, so no restore point was "
            "created. This is a capacity problem inside the guest, not a "
            "backup-mechanism fault."
        ),
        "customer_next_steps": [
            "Take a manual snapshot of the current disk state FIRST (you "
            "perform it) so nothing is lost during cleanup.",
            "Free space or extend the disk: follow the low-disk-space "
            "cleanup guide and, if needed, the disk extension guide (you "
            "perform both).",
            "After space is recovered, rerun the backup job and verify a "
            "restore point exists.",
        ],
        "docs": ["create-snapshot", "windows-low-disk-space",
                 "oos-disk-cleanup", "resize-windows-cloud-disks",
                 "file-backup-basic-faq"],
    },
    {
        "category": "policy_not_effective",
        "patterns": ["policy is not working", "policy not working",
                     "not taking effect", "did not create", "no snapshots",
                     "policy was created but", "backup policy does nothing"],
        "route": False,
        "verdict": (
            "Most likely the automatic snapshot policy exists but is not "
            "applied (bound) to the target disk(s): an unapplied policy "
            "never runs. A second candidate cause is checking before the "
            "first scheduled time point has passed."
        ),
        "customer_next_steps": [
            "Open the policy in the console and check the applied-disk list; "
            "apply it to the target disk(s) if empty (you perform it).",
            "Wait for the next scheduled time point, then verify a new "
            "snapshot exists in the snapshot list.",
        ],
        "docs": ["enable-disable-auto-policy", "auto-snapshot-policy"],
    },
    {
        "category": "pre_release_backup",
        "patterns": ["before i release", "before release", "releasing the",
                     "instance is going to be released", "data will be lost"],
        "route": False,
        "verdict": (
            "Once an instance is released its data is gone and NOT "
            "recoverable on the Alibaba Cloud side; back it up BEFORE the "
            "release decision takes effect."
        ),
        "customer_next_steps": [
            "Take manual snapshots of every disk now (you perform it), and "
            "if retention matters beyond release, note that snapshots can "
            "be kept independently of the instance.",
            "For full offline copies, use the custom-image export flow (see "
            "the local-copy design).",
            "Unpaid instances are released after the overdue retention "
            "period stated in the official pay-as-you-go policy page -- "
            "re-check the current period there before quoting it.",
        ],
        "docs": ["create-snapshot", "snapshot-overview", "pay-as-you-go"],
    },
    {
        "category": "ransomware_incident",
        "patterns": ["ransom", "encrypted my files", "files are encrypted",
                     "bitcoin", "deleted by hacker", "locked my files"],
        "route": True,
        "verdict": (
            "Active security incident: containment, forensics and recovery "
            "belong to the security-incident handling channel, not to "
            "backup-strategy design. Data can only be recovered from a "
            "pre-infection backup; with none, recovery is not possible from "
            "the cloud-provider side (shared-responsibility model)."
        ),
        "customer_next_steps": [
            "Hand the incident to the security emergency channel now.",
            "After containment, come back to design layered backups: "
            "snapshots plus cross-region copies plus an application-level "
            "database backup, and verify each layer actually works.",
        ],
        "docs": ["host-security", "app-security", "snapshot-overview"],
    },
    {
        "category": "connectivity_fault",
        "patterns": ["cannot connect", "can't connect", "remote access fail",
                     "vnc", "connection timed out", "cannot log in",
                     "server is stuck", "read-only disk alert"],
        "route": True,
        "verdict": (
            "Connection / performance fault: this is the instance-diagnosis "
            "channel's problem. Backup only appears here as the protective "
            "step BEFORE remediation actions."
        ),
        "customer_next_steps": [
            "Hand the fault to the instance diagnosis channel.",
            "Before any restart/repair attempt, take a manual snapshot of "
            "the disks (you perform it) so the attempt is reversible.",
        ],
        "docs": ["create-snapshot", "atop-monitor"],
    },
    {
        "category": "resize_operation",
        "patterns": ["resize", "expand the disk", "extend the partition",
                     "disk full after expansion", "c drive is still"],
        "route": True,
        "verdict": (
            "Disk extension question: the resize operation and its billing "
            "belong to the disk-expansion channel. This skill only covers "
            "the snapshot-before-resize protection advice."
        ),
        "customer_next_steps": [
            "Hand the resize request to the disk-expansion channel.",
            "Before resizing, take a manual snapshot of the target disk "
            "(you perform it) as the rollback safety net.",
        ],
        "docs": ["create-snapshot", "resize-windows-cloud-disks"],
    },
    {
        "category": "account_commercial",
        "patterns": ["refund", "invoice", "overdue", "arrears", "renewal is blocked",
                     "change the account subject", "real-name", "account cancelled",
                     "convert to subscription", "coupon"],
        "route": True,
        "verdict": (
            "Account / commercial process (billing, renewal, subject "
            "change, subscription conversion): outside backup-strategy "
            "design; no backup-side decision can unblock it. Only the "
            "backup sub-question is answered here."
        ),
        "customer_next_steps": [
            "Route the account matter to the billing/commercial channel or "
            "human support.",
            "If data must be extracted before an account deadline: take a "
            "snapshot or export an image NOW while access is functional "
            "(you perform it).",
        ],
        "docs": ["payg-to-subscription", "pay-as-you-go", "create-snapshot"],
    },
    {
        "category": "non_ecs_product",
        "patterns": ["web hosting", "virtual host", "cloud host", "lightweight"],
        "route": True,
        "verdict": (
            "The product in question is not an ECS instance: it has no ECS "
            "image/snapshot capability, so ECS backup designs do not apply. "
            "Identify the product first, then route to its product line."
        ),
        "customer_next_steps": [
            "Route to the matching product's support channel for its own "
            "backup/export options.",
            "For that product class, back up website files and databases "
            "separately at the application level (you perform it).",
        ],
        "docs": [],
    },
]

UNKNOWN_CONDITION_VERDICT = (
    "The wording could not be classified against the embedded pattern set. "
    "This skill cannot fetch backup-job internals or in-guest logs "
    "(unavailable to read-only cloud APIs); paste the exact alert text or "
    "open a support ticket."
)

# ---------------------------------------------------------------------------
# Knowledge topics (misconception clearing); doc keys reference DOC_URLS
# ---------------------------------------------------------------------------

KNOWLEDGE_TOPICS = {
    "snapshot-capacity-vs-disk-usage": {
        "question": (
            "My disk only holds a few GB but the snapshot shows a much "
            "larger size -- are snapshots full copies every time?"
        ),
        "answer": (
            "Snapshots record disk blocks, not a file list. The first "
            "snapshot of a disk is a full copy of the used blocks; later "
            "ones store only changed blocks. The console shows, per "
            "snapshot, the FULL amount needed to restore from it, while "
            "billing is based on the block-level usage over time -- so the "
            "displayed size is expected to exceed the current file usage. "
            "Deleting files does not free blocks until every snapshot "
            "referencing them is deleted."
        ),
        "docs": ["how-snapshots-work", "snapshot-billing-a"],
    },
    "cold-backup-type": {
        "question": (
            "Can I set the snapshot type to 'cold backup' in the automatic "
            "snapshot policy to save money?"
        ),
        "answer": (
            "No. An automatic snapshot policy has no 'cold backup' type "
            "selection. Archived snapshots exist as a snapshot category, "
            "but they cannot be copied to another region, so an off-site "
            "design cannot rely on them. Lower cost comes from fewer "
            "snapshots, shorter retention, and copying fewer times -- not "
            "from a policy type switch."
        ),
        "docs": ["auto-snapshot-policy", "snapshot-billing-a"],
    },
    "file-backup-overwrite": {
        "question": (
            "My file backup fills its capacity in about six days -- will it "
            "automatically overwrite the oldest data? Can I keep only six "
            "days?"
        ),
        "answer": (
            "No. The free file-backup basic edition does not overwrite the "
            "oldest data when capacity is exhausted -- backup jobs simply "
            "FAIL. Its retention is fixed at 30 days and cannot be "
            "customized. If the wanted design is 'keep exactly N days with "
            "automatic deletion', an automatic snapshot policy is the right "
            "mechanism instead."
        ),
        "docs": ["file-backup-basic-faq", "auto-snapshot-policy"],
    },
    "free-backup-covers-database": {
        "question": (
            "The free file backup is on, so my SQL Server data is backed "
            "up, right?"
        ),
        "answer": (
            "No. The free file-backup basic edition does not back up "
            "database software installation directories (the evidence "
            "pattern: an encrypted SQL Server whose data directory was "
            "excluded from every available restore point). Databases need "
            "Cloud Backup database backup (paid, application level) and/or "
            "snapshots as the block-level layer."
        ),
        "docs": ["cloud-backup-db-start", "cloud-backup-billing",
                 "file-backup-basic-faq"],
    },
    "download-size-inflation": {
        "question": (
            "My instance reports about 62 GB of data but the download to my "
            "PC is already 110 GB and growing -- is the backup broken?"
        ),
        "answer": (
            "Usually not a backup fault. Self-check these three causes on "
            "the instance (you inspect the guest yourself; this skill runs "
            "no in-guest commands): (1) log growth -- service/container logs "
            "without rotation can dwarf real data; (2) transfer clients "
            "that FOLLOW SYMLINKS can re-download the same files many times "
            "-- disable symlink following in the transfer tool; (3) mounted "
            "object storage appearing as a local folder gets counted as "
            "local data -- download from the storage console instead."
        ),
        "docs": [],
    },
    "policy-exists-vs-data-safe": {
        "question": (
            "I created an automatic snapshot policy, so my data is now "
            "recoverable, right?"
        ),
        "answer": (
            "Not until you verify two things: the policy is APPLIED to the "
            "disk(s), and a real snapshot appeared after the first schedule. "
            "'Policy created' is not 'protection active'. Re-verify after "
            "any disk rebuild/reset, since those operations can leave the "
            "binding stale or removed."
        ),
        "docs": ["enable-disable-auto-policy", "auto-snapshot-policy"],
    },
    "responsibility-boundary": {
        "question": (
            "I pay for Alibaba Cloud -- why isn't my server's data backed "
            "up for me?"
        ),
        "answer": (
            "Under the shared-responsibility model the provider keeps the "
            "infrastructure running; in-guest data, application security, "
            "and backup configuration are the customer's responsibility. "
            "Without a backup the customer holds, data loss after "
            "ransomware or accidental deletion cannot be recovered from the "
            "provider side. Design the layered plan before an incident, "
            "not after."
        ),
        "docs": ["snapshot-overview", "host-security"],
    },
    "windows-and-linux": {
        "question": "Does backup design differ for Windows instances?",
        "answer": (
            "The mechanism layer is identical (snapshots / policies / file "
            "backup / Cloud Backup cover Windows and Linux the same way). "
            "Guest-side self-check tooling differs -- for disk-usage "
            "inspection on Windows, third-party space analyzers are "
            "suggested in the evidence batch (confidence: medium; confirm "
            "against current official guidance before quoting tools)."
        ),
        "docs": ["windows-low-disk-space"],
    },
}
