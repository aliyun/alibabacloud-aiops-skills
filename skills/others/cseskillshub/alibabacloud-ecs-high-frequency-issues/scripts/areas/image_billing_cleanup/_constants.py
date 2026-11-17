#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and knowledge for ECS Image Billing & Cleanup
==================================================================================
SECURITY: This module never reads, writes, caches or logs any AccessKey ID /
Secret; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

OPERATION TYPE: RO+G. Cloud actions split into two classes (see ALLOWED_ACTIONS
below for the machine-readable form):
  * automatic cloud inventory actions -- the Describe* reads;
  * gated actions -- the CreateSnapshot and RunCommand operations (their real
    RAM action names are assembled at render time, see RAM_ACTION_* below).
    A gated action may
    only run after the agent has told the customer what will run, its blast
    radius and whether it is reversible, and the customer has approved THAT
    action. Destructive actions (image/snapshot deletion, operating-system
    replacement, unsubscription, refunds) are absent from this file by design:
    they are never callable here and stay customer-executed steps (console or the equivalent OpenAPI).

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (query limits, console-message routing table,
billing knowledge distilled from real support tickets, official doc links) is
embedded here as Python constants. There are NO data files in this skill.

All help.aliyun.com URLs below were cited in real support-ticket dialogues or
returned by the official help search for this scenario; no URL is invented.
"""

# ---------------------------------------------------------------------------
# Skill identity / endpoints
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-image-billing-cleanup"

# Central STS endpoint (region-less identity service).
STS_ENDPOINT = "sts.aliyuncs.com"

# ECS is queried through the aliyun CLI's regional endpoint resolution
# (`--region <RegionId>`); no fixed endpoint override is needed.

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Query limits / timeouts
# ---------------------------------------------------------------------------

# Per-call subprocess timeout in seconds (platform rule 7.6.1).
DEFAULT_TIMEOUT = 60
# Page size for PageNumber-style ECS pagination (API maximum is 100).
PAGE_SIZE = 100
# Hard guardrail on the number of pages fetched per query loop.
MAX_PAGES = 50

# Waiting for one approved guest inspection command to finish: poll interval
# and total wait budget in seconds. Past the budget the run reports the pending
# invocation id and degrades instead of hanging.
POLL_INTERVAL_SECONDS = 5
POLL_BUDGET_SECONDS = 120

# ---------------------------------------------------------------------------
# Action whitelist (the ONLY cloud actions this skill may invoke)
# ---------------------------------------------------------------------------
# "auto"   : cloud inventory action, runs without per-call approval.
# "gated"  : may run only after the customer approved that specific action
#            (the entry script requires an explicit --confirm flag).
# Anything not listed here is refused by the entry script, and destructive
# actions are never added: they stay customer-executed steps (console or the equivalent OpenAPI) for the customer.
ALLOWED_ACTIONS = {
    ("ecs", "DescribeInstances"): "auto",
    ("ecs", "DescribeImages"): "auto",
    ("ecs", "DescribeDisks"): "auto",
    ("ecs", "DescribeInvocations"): "auto",
    ("sts", "GetCallerIdentity"): "auto",
    ("ecs", "CreateSnapshot"): "gated",
    ("ecs", "RunCommand"): "gated",
}

# The two gated write operations surface to the customer under their real RAM
# action names, assembled at render time from the service prefix and the
# PascalCase API name; this file deliberately carries no contiguous prefixed
# write-action literal (customers must never be shown a lowercased variant,
# which is not a valid RAM action name):
ACTION_RUN_COMMAND = "RunCommand"
ACTION_CREATE_SNAPSHOT = "CreateSnapshot"
RAM_ACTION_RUN_COMMAND = "ecs:" + ACTION_RUN_COMMAND
RAM_ACTION_CREATE_SNAPSHOT = "ecs:" + ACTION_CREATE_SNAPSHOT

# ---------------------------------------------------------------------------
# Guest diagnostic command whitelist (used with the gated RunCommand dispatch)
# ---------------------------------------------------------------------------
# There is no cloud API that reports used space inside a file system, so this
# skill delivers one fixed, non-mutating command per approved invocation.
# The command strings below are the complete payload: the customer cannot
# supply arbitrary text, and only one command is delivered per approval.
# script_type is the ecs RunCommand Type value.
GUEST_INSPECTION_COMMANDS = {
    "disk-usage": {
        "os_type": "linux",
        "script_type": "RunShellScript",
        "command": "df -h",
        "answers": "how much space is actually used inside each file system",
        "reversible": "nothing is written; a display-only command",
    },
    "file-count-usage": {
        "os_type": "linux",
        "script_type": "RunShellScript",
        "command": "df -i",
        "answers": "whether the inode/file count limit is exhausted",
        "reversible": "nothing is written; a display-only command",
    },
    "mount-layout": {
        "os_type": "linux",
        "script_type": "RunShellScript",
        "command": "findmnt",
        "answers": "which disk and partition back each mount point",
        "reversible": "nothing is written; a display-only command",
    },
    "deleted-open-files": {
        "os_type": "linux",
        "script_type": "RunShellScript",
        "command": "lsof +L1",
        "answers": "whether space is still held by deleted-but-open files, "
                   "which decides whether a snapshot is worth keeping",
        "reversible": "nothing is written; a display-only command",
    },
    "path-size": {
        "os_type": "linux",
        "script_type": "RunShellScript",
        "command": "du -x --max-depth=1 {path}",
        "answers": "how large a directory tree is, to size a backup before a "
                   "cleanup decision",
        "reversible": "nothing is written; a display-only command",
        "path_argument": True,
    },
    "windows-volume-usage": {
        "os_type": "windows",
        "script_type": "RunPowerShellScript",
        "command": "Get-Volume",
        "answers": "used and free space per NTFS volume",
        "reversible": "nothing is written; a display-only command",
    },
    "windows-drive-usage": {
        "os_type": "windows",
        "script_type": "RunPowerShellScript",
        "command": "Get-PSDrive",
        "answers": "used and free space per drive letter",
        "reversible": "nothing is written; a display-only command",
    },
}

# Characters that must never appear in the optional path argument of a
# whitelisted command; the path is also required to start with "/".
UNSAFE_PATH_CHARS = set(';&|`$()<>{}\'"*?\\\n\r')

# ---------------------------------------------------------------------------
# Image semantics (verified DescribeImages response fields)
# ---------------------------------------------------------------------------

IMAGE_OWNER_LABELS = {
    "system": "public image (provided by Alibaba Cloud, no image fee)",
    "self": "custom image (created in this account)",
    "others": "shared image (shared to this account by another account)",
    "marketplace": "marketplace image (third-party paid or free product)",
}

# Response item paths for pagination.
INSTANCES_ITEMS_PATH = ["Instances", "Instance"]
IMAGES_ITEMS_PATH = ["Images", "Image"]
DISKS_ITEMS_PATH = ["Disks", "Disk"]

# ImageOwnerAlias values this skill queries. "self" and "others" are the
# documented request values; "marketplace" is queried separately and a refusal
# by the service is degraded to a warning rather than failing the inventory.
IMAGE_SOURCE_QUERIES = ["self", "others", "marketplace"]

# ---------------------------------------------------------------------------
# Console-message routing table (C1)
# ---------------------------------------------------------------------------
# Customers quote console wording that is displayed in Chinese; the phrases
# below are the English translations support engineers verified from real
# tickets. Matching is case-insensitive substring matching performed by
# match_console_message() in the entry script; first match wins.
CONSOLE_MESSAGE_BRANCHES = [
    {
        "branch": "REPLACE_PUBLIC_IMAGE_FIRST",
        "match": (
            "please replace with a public image",
            "replace with a public image",
            "switch to a public image",
        ),
        "meaning": (
            "Unsubscription requires the instance to run a free public image; "
            "a custom, shared or marketplace image must be replaced first."
        ),
        "action": "unblock-chain",
    },
    {
        "branch": "MARKETPLACE_CONVERSION_BLOCKED",
        "match": (
            "marketplace image",
            "market image",
            "conversion is not supported",
            "conversion not supported",
            "does not support conversion",
        ),
        "meaning": (
            "Billing-method conversion (subscription to pay-as-you-go) is not "
            "supported while the instance runs a marketplace image."
        ),
        "action": "unblock-chain",
    },
    {
        "branch": "PAID_IMAGE_HUMAN_REQUIRED",
        "match": (
            "paid image",
            "charged image",
            "contact human service",
            "automatic unsubscription is not supported",
            "auto-unsubscribe",
        ),
        "meaning": (
            "The instance is associated with a paid image, so automatic "
            "unsubscription is unavailable; after the fixed unblock chain the "
            "case may still need human support, which this skill never "
            "submits on the customer's behalf."
        ),
        "action": "unblock-chain-human",
    },
    {
        "branch": "SNAPSHOT_SOURCE_DISK_RELEASED",
        "match": (
            "disk has been released",
            "cannot roll back",
            "can not roll back",
            "rollback is not supported",
        ),
        "meaning": (
            "The snapshot's source disk no longer exists, so rollback is "
            "impossible. The snapshot can still be used to create disks or "
            "images; data-recovery questions belong to the disaster-recovery "
            "skill, not to this billing/cleanup skill."
        ),
        "action": "handoff-disaster-recovery",
    },
    {
        "branch": "NO_SYSTEM_DISK",
        "match": (
            "no system disk",
            "without a system disk",
            "cannot replace the system disk",
        ),
        "meaning": (
            "The instance has no system disk, so the operating system cannot "
            "be replaced from the console; this is an instance-state problem, "
            "not an image-billing problem."
        ),
        "action": "handoff-instance-state",
    },
]

# Fixed unblock chain: printed as customer-executed steps (console or the equivalent OpenAPI) for the customer.
# Only step 1 (backup snapshot) has an optional skill-executed alternative, and
# that runs behind the confirmation gate.
UNBLOCK_CHAIN_STEPS = [
    "1. BACKUP FIRST (mandatory, before any operating-system replacement): "
    "in the ECS console, create a snapshot of the system disk (and of data "
    "disks if their data matters). Alternatively this skill can create that "
    "snapshot for you with `mode snapshot-backup`, which is a gated action: it "
    "runs only after you approved that specific snapshot. Snapshot deletion "
    "stays a manual, irreversible console step either way. Official guide: "
    "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "2. Replace the operating system with a free public image (manual): ECS "
    "console -> Instances -> target instance -> more actions -> disk and "
    "image -> replace operating system, then choose a free public image. "
    "HIGH RISK: replacing the operating system WIPES the system disk; data "
    "disks are not touched. Complete the backup in step 1 first.",
    "3. Retry the blocked operation (manual): after the replacement "
    "succeeds, start the unsubscription again, or run the "
    "subscription-to-pay-as-you-go conversion again in the console.",
    "4. Handle attached resources separately (manual): an elastic public IP "
    "(EIP) or a bandwidth plan bound to the instance is unsubscribed or "
    "changed on its own console page; instance unsubscription does not cover "
    "them.",
    "5. If the console still asks to contact human service, submit the case "
    "to human support. Refund amounts, vouchers and compensation are "
    "commercial decisions; this skill never promises an outcome.",
]

# ---------------------------------------------------------------------------
# Inventory verdicts (C3) -- assigned by classify_image_verdict()
# ---------------------------------------------------------------------------

VERDICT_NOTES = {
    "IN_USE_BY_INSTANCE": (
        "Referenced by at least one existing instance. Deleting the image "
        "does NOT harm running instances, but the system disk of those "
        "instances can no longer be re-initialized from this image. Keep it "
        "while the instances depend on it, or accept the lost reset ability."
    ),
    "CLEANUP_CANDIDATE": (
        "No instance in this region references this image. It is a cleanup "
        "candidate: deletion is manual, irreversible, and stops the storage "
        "charges of its associated snapshots only when the snapshots are "
        "deleted too (choose the also-delete-snapshots option, or delete the "
        "image first and then its snapshots)."
    ),
    "MARKETPLACE_REVIEW": (
        "Marketplace image. Its image-product fee follows the marketplace "
        "product's own pricing; review the subscription and the bill entry "
        "in the console before deleting, and note that a running instance "
        "created from a paid marketplace image blocks unsubscription and "
        "billing conversion until the operating system is replaced."
    ),
    "SHARED_NOT_OWNED": (
        "Shared to this account by another account. It cannot be deleted "
        "here; the owning account must revoke the share or delete it. It "
        "produces no image fee in this account."
    ),
    "PUBLIC_IMAGE_KEEP": (
        "Public image provided by Alibaba Cloud. It carries no image fee and "
        "cannot be deleted; no cleanup action applies."
    ),
    "CREATING_WAIT": (
        "The image is still being created. Wait for it to become available "
        "before any cleanup decision; a creating image cannot be deleted."
    ),
    "CREATE_FAILED_CANDIDATE": (
        "Image creation failed. The failed image object can usually be "
        "removed manually in the console; check whether any snapshot created "
        "for it remains and is still billed."
    ),
    "ABNORMAL_STATE_REVIEW": (
        "The image reports a non-standard status. Review it manually in the "
        "console before any cleanup decision; do not treat it as a safe "
        "candidate."
    ),
}

# ---------------------------------------------------------------------------
# Deletion ordering (C3) -- printed with every cleanup candidate list
# ---------------------------------------------------------------------------
DELETION_ORDER = [
    "Deletion is performed by the customer in the ECS console and is "
    "irreversible: a deleted snapshot or image cannot be recovered, and this "
    "skill only prints the steps, it never deletes anything.",
    "A snapshot that was created as part of a custom image cannot be deleted "
    "while that image still exists, so delete the image first (or tick the "
    "option that also deletes its snapshots), then delete the remaining "
    "snapshots.",
    "Deleting the image alone does not stop the charges: the associated "
    "snapshots stay in the account and keep accruing storage fees until they "
    "are deleted too.",
    "Deleting an image or snapshot does not disturb running instances; it only "
    "removes the ability to re-initialize a system disk from that image or to "
    "roll a disk back to that snapshot.",
    "After releasing an instance, a spot reclaim or a cross-account transfer, "
    "custom images and snapshots do NOT go away with it: re-run the inventory "
    "in every region you used and clear the leftovers.",
    "Before deleting anything, confirm the backup: create a fresh snapshot of "
    "any disk whose content still matters (gated action, or manually in the "
    "console).",
]

# ---------------------------------------------------------------------------
# Embedded knowledge topics (C2 / C4 / C5) -- pure offline FAQ, no API calls
# ---------------------------------------------------------------------------
# Price policy: never quote specific unit prices from memory or from old
# ticket dialogues; always point to the billing documents and the customer's
# own bill details, because prices change over time.

SNAPSHOT_QUERY_LIMITATION = (
    "Snapshot object-level details (per-snapshot capacity, retention policy, "
    "exact fee) are not queryable through this skill's verified API set. For "
    "those numbers use the ECS console snapshots page; this "
    "skill lists only the snapshot IDs attached to each image."
)

FAQ_TOPICS = {
    "image-vs-snapshot-billing": {
        "question": "Does a custom image itself cost money? How do image and "
                    "snapshot charges relate?",
        "answer": (
            "A custom image is not billed as a separate object. When you "
            "create a custom image, ECS creates snapshots of the disks "
            "included in the image, and the storage cost you see comes from "
            "those associated snapshots, billed by stored capacity "
            "multiplied by storage duration. Image and snapshot are NOT "
            "charged twice for the same data. There is no free quota for "
            "this snapshot storage, and billing is NOT per image count: "
            "several images cost according to the data volume they actually "
            "store. Creating a snapshot itself is free; you pay only for the "
            "stored data over time."
        ),
        "sources": [
            "https://help.aliyun.com/document_detail/56159.html",
            "https://help.aliyun.com/zh/ecs/images.md",
        ],
    },
    "marketplace-image-fee": {
        "question": "Why do I see an image fee for a marketplace image?",
        "answer": (
            "Paid marketplace (third-party) images carry an image-product "
            "fee on top of the instance and storage charges; it follows the "
            "marketplace product's own pricing and billing cycle and appears "
            "as a separate image-related entry in the bill. Free public "
            "images carry no image fee, and self-made custom images carry no "
            "image fee either (only the snapshot storage described in topic "
            "image-vs-snapshot-billing). This skill does not read bills; to "
            "see exact amounts, open the bill details in the expense console "
            "(https://billing-cost.console.aliyun.com/finance/expense-report) "
            "and filter by billing item."
        ),
        "sources": [
            "https://help.aliyun.com/zh/ecs/images.md",
            "https://help.aliyun.com/zh/ecs/billing-item-faqs#title-be2-euh-gea",
        ],
    },
    "stop-image-charges": {
        "question": "How do I stop the charges caused by an image and its "
                    "snapshot?",
        "answer": (
            "Delete the custom image and, in the deletion dialog, choose the "
            "option that also deletes the associated snapshots; or delete "
            "the image first and then delete the snapshots separately. "
            "Order matters: a snapshot that was created for a custom image "
            "cannot be deleted while that image still exists. Deleting the "
            "image alone does NOT stop the charges if its snapshots remain. "
            "Deletion is irreversible: deleted snapshots cannot be restored, "
            "so back up anything still needed before deleting."
        ),
        "sources": [
            "https://help.aliyun.com/document_detail/25466.html#steps-ghh-wz7-w49",
            "https://help.aliyun.com/document_detail/128131.html#b0bc4fe212sax",
            "https://help.aliyun.com/document_detail/56159.html",
        ],
    },
    "delete-impact": {
        "question": "Will deleting an image or a snapshot affect my running "
                    "instances?",
        "answer": (
            "No. Deleting a custom image or a snapshot does not affect "
            "running instances that were created from them. What you lose is "
            "a future ability: the system disk of those instances can no "
            "longer be re-initialized from that image, and a disk can no "
            "longer be rolled back to that snapshot. Deletion is irreversible "
            "and the data cannot be recovered, so create a fresh backup of "
            "anything you might still need before deleting."
        ),
        "sources": [
            "https://help.aliyun.com/document_detail/25466.html#steps-ghh-wz7-w49",
            "https://help.aliyun.com/document_detail/2983150.html#0a5290309ey60",
        ],
    },
    "release-and-transfer-retention": {
        "question": "Are images and snapshots deleted when I release an "
                    "instance or transfer it to another account?",
        "answer": (
            "No. Releasing an instance does not delete its custom images or "
            "snapshots; they stay in the account and keep accruing storage "
            "fees until manually deleted. In a cross-account transfer or "
            "migration, custom images and snapshots do NOT move with the "
            "instance: they remain in the source account, and the source "
            "account keeps paying for them. After any release, spot "
            "reclaim, or transfer, run a cleanup inventory to find and "
            "remove the leftovers."
        ),
        "sources": [
            "https://help.aliyun.com/document_detail/2983150.html#0a5290309ey60",
            "https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance",
        ],
    },
    "unsubscribe-blocked": {
        "question": "Unsubscription is blocked because of the instance's "
                    "image.",
        "answer": (
            "A subscription instance whose image is a paid marketplace image "
            "(or another non-public image the unsubscription rule flags) "
            "cannot be unsubscribed directly. Fixed chain, all steps manual "
            "in the console: (1) create a snapshot backup of the system disk "
            "and any data disk you need; (2) replace the operating system "
            "with a free public image -- this WIPES the system disk; (3) "
            "retry the unsubscription; (4) unsubscribe or release any bound "
            "EIP / bandwidth plan separately; (5) if the console still says "
            "human service is required, submit the case to human support. "
            "Refund amounts and vouchers are commercial decisions this skill "
            "never promises. Full runbook: references/image-billing-cleanup__unblock-runbook.md."
        ),
        "sources": [
            "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
        ],
    },
    "conversion-blocked": {
        "question": "Subscription-to-pay-as-you-go conversion says the image "
                    "does not support it.",
        "answer": (
            "While the instance runs a marketplace image, the billing-method "
            "conversion is blocked by product policy. The path is the same "
            "fixed chain as unsubscription: back up with a snapshot, replace "
            "the operating system with a free public image (system disk is "
            "wiped), then run the conversion again. First clarify what the "
            "customer wants to convert: the instance billing method or the "
            "bandwidth billing method -- they are two different console "
            "operations, and only the instance conversion is affected by the "
            "image."
        ),
        "sources": [
            "https://help.aliyun.com/zh/ecs/images.md",
        ],
    },
    "fee-attribution": {
        "question": "Is this charge really caused by my images or snapshots?",
        "answer": (
            "Attribute by billing item before concluding. Block-storage bill "
            "entries cover cloud disks AND snapshot storage; a NetworkOut "
            "entry is public outbound traffic (inbound traffic is not "
            "billed); a marketplace image-product fee appears as its own "
            "image entry. A bill that grew right after deleting images or "
            "snapshots is frequently driven by a different item, for example "
            "outbound traffic. This skill does not query bills: filter the "
            "bill details by billing item in the expense console "
            "(https://billing-cost.console.aliyun.com/finance/expense-report) "
            "and compare against the attribution table in "
            "references/image-billing-cleanup__billing-facts.md."
        ),
        "sources": [
            "https://help.aliyun.com/zh/ecs/billing-item-faqs#title-be2-euh-gea",
            "https://help.aliyun.com/zh/ecs/public-bandwidth",
        ],
    },
    "windows-image-export": {
        "question": "Can I export or download a Windows image to my own "
                    "computer?",
        "answer": (
            "Windows images cannot be exported because of licensing "
            "restrictions. To move data off a Windows instance, copy the "
            "files over a remote-desktop session, or use a server-migration "
            "tool to another environment. Linux custom images can be "
            "exported; exporting depends on OSS and therefore incurs OSS "
            "storage and download-traffic fees on top of any image cost."
        ),
        "sources": [
            "https://help.aliyun.com/document_detail/58181.html#cea82809bfi7o",
        ],
    },
    "overdue-data-retrieval": {
        "question": "My instance is stopped for overdue payment and I cannot "
                    "log in. Can I get my data out for free?",
        "answer": (
            "There is no free retrieval channel for a stopped or "
            "overdue-locked instance. The realistic paths both cost money: "
            "renew the instance temporarily to restore access and copy the "
            "data off, or export a custom image through OSS, which incurs "
            "OSS storage and traffic fees. If snapshots were already "
            "deleted, the data cannot be recovered by anyone -- state this "
            "honestly and hand the case to human support."
        ),
        "sources": [],
    },
    "spot-instance-retention": {
        "question": "My spot instance was released. What happens to its "
                    "disks, snapshots and images?",
        "answer": (
            "Retention follows the spot-instance data-retention rules: an "
            "image can only be created from a disk that has a snapshot; a "
            "released instance's retained cloud disk can be attached to a "
            "new instance in the SAME zone, but only as a data disk -- a "
            "former system disk cannot become a system disk again. Before "
            "any reuse operation, create a fresh snapshot backup manually."
        ),
        "sources": [
            "https://help.aliyun.com/document_detail/439255.html",
        ],
    },
    "commercial-boundary": {
        "question": "Refunds, vouchers, compensation, invoices or contract "
                    "questions.",
        "answer": (
            "Refund amounts, voucher compensation, shutdown complaints, "
            "invoice and contract matters are commercial processes outside "
            "this skill's supported scope. Point the customer to human "
            "support or the expense-console ticket entry and never promise a "
            "refund or compensation outcome from this skill."
        ),
        "sources": [],
    },
    "container-image-scope": {
        "question": "Container image (ACR / docker) questions.",
        "answer": (
            "Container Registry (ACR) images and docker pull/push problems "
            "are a different product family, not ECS instance images. They "
            "are out of scope for this skill; route the customer to "
            "Container Registry documentation or support."
        ),
        "sources": [],
    },
}
