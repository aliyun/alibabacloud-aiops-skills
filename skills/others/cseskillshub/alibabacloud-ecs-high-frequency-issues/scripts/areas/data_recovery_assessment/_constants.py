#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS data-recovery assessment skill
================================================================================
SECURITY: This skill is strictly READ-ONLY on the cloud side. It never reads,
prints or forwards any credential; authentication is resolved exclusively by
the aliyun CLI default credential chain. No AccessKey / Secret handling
anywhere in this module.

Per platform rule 1.1.2, scripts/ may contain executable code only, so every
piece of reference knowledge (assessment taxonomy, recoverability matrix,
customer self-check items, recovery guidance templates, expectation-management
wording, handoff rules, official documentation index) is embedded here as
Python constants. There are no data files in scripts/.
"""

import re

# ---------------------------------------------------------------------------
# Skill identity and API metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-data-recovery-assessment"

ECS_PRODUCT = "ecs"
STS_PRODUCT = "sts"

# API versions actually called by this skill (informational; the aliyun CLI
# carries its own request metadata).
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

DEFAULT_REGION = "cn-hangzhou"

# Per-call subprocess timeout (platform rule 7.6.1).
DEFAULT_TIMEOUT = 60

# DescribeInstances page size / page guardrails.
PAGE_SIZE = 50
MAX_PAGES = 10

# ---------------------------------------------------------------------------
# Instance status interpretation (DescribeInstances Status field, read-only)
# ---------------------------------------------------------------------------

INSTANCE_STATUS_MEANING = {
    "Running": ("The instance still exists in this account and region and is "
                "running. Data-loss assessment continues on the disk/backup "
                "evidence side."),
    "Stopped": ("The instance exists but is stopped. Stopping does not erase "
                "disk data; check whether a reinstallation, re-initialization "
                "or rollback happened around the loss event."),
    "Pending": "The instance is being provisioned; wait and re-check.",
    "Starting": "The instance is starting; wait and re-check.",
    "Stopping": "The instance is stopping; wait and re-check.",
}

NOT_VISIBLE_NOTE = (
    "The instance was not returned by the read-only query for the current "
    "account and region. Three possibilities, in the order they should be "
    "excluded: (1) the instance lives in a DIFFERENT region or a DIFFERENT "
    "account than the credential in use (this query only sees the current "
    "account and the requested region); (2) it was released after expiry or "
    "manual deletion; (3) the instance id or region is mistyped. Ask the "
    "customer to confirm the region and account and to paste the release or "
    "expiry notification they received before any conclusion is drawn."
)

# ---------------------------------------------------------------------------
# Loss-event taxonomy (capability C3)
# ---------------------------------------------------------------------------

LOSS_TYPES = {
    "mistaken-delete": {
        "label": "Files, directories or database objects deleted by mistake",
        "customer-wording": [
            "I accidentally deleted files / a folder / my project code",
            "someone dropped a database or table",
            "rm -rf was run by mistake",
        ],
        "key-question": ("Which path or database was lost, on which disk "
                         "(system disk or data disk), and has the instance "
                         "kept writing to that disk since?"),
    },
    "mistaken-format": {
        "label": "A partition or disk was formatted by mistake",
        "customer-wording": [
            "I formatted the disk / partition by mistake",
            "the volume was re-initialized",
        ],
        "key-question": ("Was the formatted volume on the system disk, a "
                         "data disk or a local disk, and were snapshots "
                         "enabled for that disk?"),
    },
    "system-reinstall": {
        "label": "Operating system reset / replaced or system disk re-initialized",
        "customer-wording": [
            "I reinstalled the operating system and the old files are gone",
            "the previous staff changed the OS and data disappeared",
        ],
        "key-question": ("Replacing the operating system clears the system "
                         "disk only; data disks keep their content. Confirm "
                         "where the lost data lived and whether any snapshot "
                         "of the OLD system disk exists."),
    },
    "config-downgrade": {
        "label": "Files lost around a specification downgrade / rebuild",
        "customer-wording": [
            "data disappeared after I downgraded the instance configuration",
        ],
        "key-question": ("Whether the change rebuilt the system disk. Explain "
                         "the change itself through the instance-change tier; "
                         "this skill only assesses the lost data."),
    },
    "expiry-release": {
        "label": "Instance expired and was reclaimed / released",
        "customer-wording": [
            "my instance expired and is now gone, is my data gone too",
            "the server was reclaimed after the renewal window",
        ],
        "key-question": ("Was the instance released, and did any snapshot, "
                         "custom image or backup survive the release? Note "
                         "the cloud-disk versus local-disk retention "
                         "difference before concluding."),
    },
    "intrusion-deletion": {
        "label": "Data deleted or encrypted by an attacker or ransomware",
        "customer-wording": [
            "hackers dropped my database",
            "ransomware encrypted my files",
        ],
        "key-question": ("Inventory every surviving backup. Malware cleanup, "
                         "forensics and hardening belong to the host-intrusion "
                         "tier; this skill only assesses data recoverability."),
    },
    "cache-not-persisted": {
        "label": "In-memory data (Redis-style caches) lost after a restart",
        "customer-wording": [
            "after the instance rebooted my cache data is empty",
        ],
        "key-question": ("Was the data only in memory without persistence "
                         "enabled? A restart never erases disk data, but "
                         "un-persisted cache content was never on disk and "
                         "cannot be recovered from the cloud side."),
    },
    "suspected-loss": {
        "label": "Data appears lost but may only be unmounted or moved",
        "customer-wording": [
            "my files are gone after the reboot",
            "the website says the directory does not exist",
        ],
        "key-question": ("Before treating this as data loss, have the "
                         "customer run read-only checks inside the instance "
                         "themselves (lsblk, df -h, mount, find) and paste "
                         "the output: a changed application storage path or a "
                         "disk that was not auto-mounted is NOT data loss."),
    },
    "unknown": {
        "label": "Loss event not yet classified",
        "customer-wording": [],
        "key-question": "Ask the customer what operation preceded the loss.",
    },
}

# ---------------------------------------------------------------------------
# Data carrier and backup-asset taxonomy (capability C2)
# ---------------------------------------------------------------------------

CARRIERS = {
    "system-disk": "Lost data lived on the system disk.",
    "data-disk": "Lost data lived on a data disk.",
    "local-disk": ("Lost data lived on a LOCAL disk (instance-storage disk). "
                   "Local-disk content is cleared as soon as the instance "
                   "enters the recycling phase; snapshots cannot cover local "
                   "disks."),
    "memory-cache": ("Lost data lived only in memory (cache process without "
                     "persistence); it was never written to any disk."),
    "unknown": "Carrier not yet identified.",
}

# asset_class: where the backup protects from; time_scope: whether the backup
# point can match the customer's needed moment; image_capable: whether the
# asset can rebuild a full system environment (custom image only; a data-disk
# snapshot CANNOT be turned into a custom image).
BACKUP_ASSETS = {
    "none": {
        "label": "Customer confirmed: no snapshot, no image, no backup copy",
        "asset_class": "none",
        "image_capable": False,
    },
    "system-disk-snapshot": {
        "label": "Snapshot taken from the SYSTEM disk",
        "asset_class": "disk",
        "image_capable": False,
    },
    "data-disk-snapshot": {
        "label": "Snapshot taken from a DATA disk",
        "asset_class": "disk",
        "image_capable": False,
    },
    "auto-snapshot-policy": {
        "label": "Automatic snapshot policy attached to the disk",
        "asset_class": "disk",
        "image_capable": False,
    },
    "custom-image": {
        "label": "Custom image of the instance",
        "asset_class": "instance",
        "image_capable": True,
    },
    "ecs-file-backup": {
        "label": "ECS file backup (essential edition) backup history exists",
        "asset_class": "file",
        "image_capable": False,
    },
    "cloud-backup": {
        "label": "Cloud Backup (HBR) backup of the files or database",
        "asset_class": "file",
        "image_capable": False,
    },
    "database-backup": {
        "label": "Logical database dump / backup file kept by the customer",
        "asset_class": "file",
        "image_capable": False,
    },
    "binlog": {
        "label": "Database binary logs / write-ahead logs retained",
        "asset_class": "file",
        "image_capable": False,
    },
    "local-copy": {
        "label": "A local copy on the customer side (PC, NAS, another server)",
        "asset_class": "file",
        "image_capable": False,
    },
    "unknown": {
        "label": "Backup situation not checked yet",
        "asset_class": "unknown",
        "image_capable": False,
    },
}

# ---------------------------------------------------------------------------
# Recoverability verdicts (capability C4)
# ---------------------------------------------------------------------------

VERDICT_RECOVERABLE = "RECOVERABLE"
VERDICT_EXTRACTION = "DATA-EXTRACTION-ONLY"
VERDICT_OLDER_POINT = "OLDER-BACKUP-POINT-ONLY"
VERDICT_NOT_RECOVERABLE = "NOT-RECOVERABLE"
VERDICT_INSUFFICIENT = "INSUFFICIENT-EVIDENCE"
VERDICT_NOT_A_LOSS = "NOT-A-DATA-LOSS"

# Strongest-to-weakest ordering used when several backup assets are present.
VERDICT_STRENGTH = [
    VERDICT_RECOVERABLE,
    VERDICT_EXTRACTION,
    VERDICT_OLDER_POINT,
    VERDICT_NOT_A_LOSS,
    VERDICT_INSUFFICIENT,
    VERDICT_NOT_RECOVERABLE,
]

VERDICT_MEANING = {
    VERDICT_RECOVERABLE: ("A backup asset of the right class and point in "
                          "time exists; the state covered by that backup can "
                          "be restored by the customer via console guidance."),
    VERDICT_EXTRACTION: ("The whole state cannot be rolled back, but data "
                         "survives inside a backup asset that can be attached "
                         "as a new disk and mined file by file."),
    VERDICT_OLDER_POINT: ("A backup exists but only covers an OLDER point in "
                         "time than the customer needs; restore to the "
                         "available point or extract from it, and reconcile "
                         "the gap manually."),
    VERDICT_NOT_RECOVERABLE: ("No backup asset exists and the carrier was "
                              "cleared (released / re-initialized / "
                              "overwritten / never persisted). Alibaba Cloud "
                              "platform-side means cannot bring the data "
                              "back; the conclusion is delivered with the "
                              "expectation-management template."),
    VERDICT_INSUFFICIENT: ("Evidence is incomplete; recoverability cannot be "
                           "judged yet. NEVER promise a positive outcome at "
                           "this stage; run the customer self-check list."),
    VERDICT_NOT_A_LOSS: ("Symptoms suggest the data may still exist (wrong "
                         "path, disk not mounted, un-persisted cache); prove "
                         "or disprove with read-only guest checks before any "
                         "recovery wording is used."),
}

# ---------------------------------------------------------------------------
# Customer self-check checklist (capability C2, four-element guidance)
# ---------------------------------------------------------------------------
# Each item: what to look for / console entry / object to open / expected
# result / fallback. The customer pastes the result (text or screenshot) back;
# the skill has no verified read-only API for backup-asset history, so this
# checklist is the designed evidence source, not a workaround.

SELF_CHECK_ITEMS = [
    {
        "asset": "Manual snapshots",
        "entry": "ECS console -> Storage & Snapshots -> Snapshots (switch to "
                 "the region of the lost disk first)",
        "object": "Snapshot list, filtered by the disk id of the lost volume",
        "expected": "One or more snapshots whose creation time predates the "
                    "loss event; note for each whether it belongs to the "
                    "SYSTEM disk or a DATA disk (the Source Disk column).",
        "fallback": "Empty list or region mismatch: re-check the region, then "
                    "record 'no manual snapshot' as a confirmed negative.",
    },
    {
        "asset": "Automatic snapshot policies",
        "entry": "ECS console -> Storage & Snapshots -> Auto Snapshot Policy",
        "object": "Policy list and its bound disks",
        "expected": "Either a bound policy with produced snapshots, or "
                    "confirmation that no policy was ever attached.",
        "fallback": "No policy found: record 'no auto snapshots' as a "
                    "confirmed negative.",
    },
    {
        "asset": "Custom images",
        "entry": "ECS console -> Images -> Custom Images",
        "object": "Image list for the region of the instance",
        "expected": "An image created before the loss; only a CUSTOM IMAGE "
                    "can rebuild a full system environment (a data-disk "
                    "snapshot cannot be converted into an image).",
        "fallback": "No image: record 'no custom image' as a confirmed "
                    "negative.",
    },
    {
        "asset": "ECS file backup (essential edition)",
        "entry": "ECS console -> Backup -> ECS File Backup (backup history "
                 "page of the region, e.g. ecs.console.aliyun.com/"
                 "fileBackup/region/<region-id>)",
        "object": "Backup history for the instance",
        "expected": "Backup records whose time predates the loss.",
        "fallback": "Empty: record 'no file backup'. Product-side restore "
                    "operations belong to "
                    "alibabacloud-cloudbackup-ecs-file-backup-essential-edition.",
    },
    {
        "asset": "Cloud Backup / database backup files / binlog",
        "entry": "Customer side: database server settings, log paths, NAS or "
                 "offline copies",
        "object": "Dump files, binlog retention window, third-party backup "
                  "console",
        "expected": "Any surviving logical backup or log that covers the "
                    "needed point in time.",
        "fallback": "Nothing kept: record 'no logical backup, no binlog'.",
    },
    {
        "asset": "Write activity after the loss",
        "entry": "Customer side, read-only checks only",
        "object": "Whether the affected disk kept serving production after "
                  "the deletion (writes can overwrite deleted data)",
        "expected": "Ideally no new writes; if the disk is still in use, "
                    "stop non-essential writes and take a safety-net snapshot "
                    "of the CURRENT state before any risky recovery action.",
        "fallback": "Unknown: treat overwrite risk as 'possible', which "
                    "lowers confidence but never produces a positive "
                    "recovery promise.",
    },
]

# ---------------------------------------------------------------------------
# Recovery path guidance (capability C5): per-path steps, each step written
# with entry / object / expected result / rollback fallback, plus mandatory
# risk notices. The customer performs every action; the skill only guides.
# ---------------------------------------------------------------------------

SAFETY_NET_STEP = (
    "Before any recovery action: on the CURRENT state of the affected disk, "
    "take one manual snapshot from the console first (small extra snapshot "
    "storage fee applies, billed per the snapshot pricing document; on the "
    "order of CNY 0.4 per 100 GB per day at standard rate, but treat the "
    "official pricing page as the authority). The safety net preserves the "
    "present state in case the recovery attempt makes things worse."
)

RECOVERY_PATHS = {
    "snapshot-rollback-system-disk": {
        "when": "A SYSTEM-disk snapshot covering the needed point exists and "
                "the loss sits on the system disk.",
        "steps": [
            SAFETY_NET_STEP,
            "Stop the application workload so in-memory data is flushed to "
            "disk, then stop the instance (console instance list -> the "
            "instance -> instance status).",
            "Open the snapshot of the system disk and start the rollback "
            "wizard; read the displayed impact notice (rollback replaces the "
            "system disk content with the snapshot moment) and confirm.",
            "Start the instance, then MANUALLY start the website / database "
            "services if they have no autostart: a snapshot rollback restores "
            "the FILE DATA state of the snapshot moment, NOT the running "
            "state of that moment.",
            "Verify: files and databases match the snapshot date; services "
            "answer; recent writes after the snapshot date are gone by "
            "design - reconcile them from application logs if needed.",
        ],
        "risk-notices": [
            "Rollback restores file-data state, not process/service state; "
            "programs without autostart must be started manually.",
            "All disk writes made after the snapshot moment are lost.",
            "Perform during a low-traffic window; restart drops unsaved "
            "in-memory data.",
        ],
    },
    "snapshot-new-disk-extraction": {
        "when": "Only a DATA-disk snapshot exists (or must not be rolled "
                "back over live data), and the goal is to copy files out.",
        "steps": [
            "From the snapshot, create a new disk in the SAME zone as the "
            "rescue instance (snapshots are zone-bound).",
            "Attach the new disk to an instance and mount it inside the "
            "guest (customer-side Linux/Windows disk management per the "
            "data-recovery best-practice documents).",
            "Copy only the needed files to the target location; verify "
            "checksums or counts before deleting anything.",
            "Unmount and release the temporary disk when extraction is "
            "done (release is done manually by the customer in the console; "
            "this skill never performs it).",
        ],
        "risk-notices": [
            "A data-disk snapshot canNOT be turned into a custom image and "
            "therefore canNOT replace a system disk wholesale; extraction is "
            "the only use.",
            "Creating extra disks incurs charges; delete the temporary disk "
            "after extraction to stop them.",
        ],
    },
    "custom-image-rebuild": {
        "when": "The old instance is gone (released or system disk wiped) but "
                "a custom image created before the loss exists.",
        "steps": [
            "Purchase a new instance (or change the system of an existing "
            "one) selecting that custom image as the source; the image "
            "rebuilds the system environment as of its creation moment.",
            "Start the services manually if they had no autostart.",
            "Re-attach data disks if they survived, and verify applications "
            "against the image date.",
        ],
        "risk-notices": [
            "The image only carries the state up to its creation date; "
            "later data needs separate reconciliation.",
        ],
    },
    "file-backup-restore": {
        "when": "ECS file backup (essential edition) history covers the "
                "needed point in time.",
        "steps": [
            "Open the file-backup history for the instance and start a "
            "restore job to a chosen path.",
            "Verify restored files at the destination before pointing the "
            "application at them.",
        ],
        "risk-notices": [
            "Backup-product operation details belong to "
            "alibabacloud-cloudbackup-ecs-file-backup-essential-edition; "
            "this skill stops at assessment and routing.",
        ],
    },
    "guest-side-recovery-practice": {
        "when": "Deleted files on a still-existing disk with no backup "
                "covering the moment; best-practice tools may help if "
                "overwrites stayed low.",
        "steps": [
            "Have the customer stop writing to the affected disk immediately.",
            "Ask the customer to grant login authorization for the in-guest "
            "attempt; they run every command themselves and paste output back.",
            "Ask the customer which kind of file was lost: an OS/system file "
            "(copy it from a healthy instance on the same OS) or a business file.",
            "Have the customer establish what was removed: run history and "
            "filter it for the delete command (for example history | grep rm) "
            "and paste the output back.",
            "Have the customer run the official Linux/Windows data-recovery "
            "best-practice tooling inside the guest on a clone attached as a "
            "secondary device, never in place, and copy recovered files to a "
            "DIFFERENT disk before re-verifying.",
        ],
        "risk-notices": [
            "Have the customer know recovery success is NOT guaranteed once "
            "data blocks were overwritten; set expectations before spending "
            "effort.",
        ],
    },
    "rebuild-from-scratch": {
        "when": "Verdict is NOT-RECOVERABLE and the business must move on.",
        "steps": [
            "Buy a new instance, or restore from any surviving partial asset "
            "(older image, file backup, local copy, database dump).",
            "Re-deploy the app; restore the newest surviving dump, replay "
            "retained logs, then reconcile the gap with business records.",
            "Before going live: auto-snapshot policy on every important disk, "
            "and one backup copy kept OFF the instance.",
        ],
        "risk-notices": [
            "The original released instance cannot be brought back; only a "
            "new purchase reproduces the configuration.",
        ],
    },
}

SNAPSHOT_FIRST_NOTICE = (
    "Have the customer take a snapshot of the current disks before any "
    "rollback/re-init/write step, so a failed attempt cannot lose more data.")

# ---------------------------------------------------------------------------
# Expectation management (capability C6): fixed wording for hard messages,
# phrasing sourced from reviewed support conversations.
# ---------------------------------------------------------------------------

EXPECTATION_LINES = {
    "no-auto-backup": (
        "Alibaba Cloud does not keep an automatic copy of customer data "
        "inside an ECS instance. Snapshots, images and backups only exist "
        "if the customer created or configured them beforehand."),
    "release-is-permanent": (
        "After an instance is released and the retention window passed, the "
        "disk data is permanently deleted; paying the overdue bill does NOT "
        "bring the old instance or its data back. The configuration can be "
        "reproduced by purchasing a new instance, and a custom image (if one "
        "exists) restores the system environment quickly."),
    "reinstall-clears-system-disk": (
        "Replacing the operating system (or re-initializing the system disk) "
        "clears the SYSTEM disk only; attached data disks keep their content. "
        "Lost data on the system disk without a prior snapshot cannot be "
        "restored by the platform."),
    "rollback-is-data-state": (
        "A snapshot rollback restores the file-data state at the snapshot "
        "creation moment - it does not restore the running state of services "
        "from back then; programs without autostart must be started manually "
        "afterwards."),
    "cache-not-on-disk": (
        "Data held only in a cache process (for example Redis without "
        "persistence) was never written to disk; a restart clearing it is "
        "not a recoverable disk-data loss."),
    "local-disk-retention": (
        "Cloud disks stay retrievable for a limited retention window after "
        "expiry (about fifteen days per the renewal notices), while LOCAL "
        "(instance-storage) disks are cleared once the instance enters the "
        "recycling phase. Check which disk type the data lived on."),
    "no-stamped-attestation": (
        "A stamped official certificate stating that data cannot be "
        "recovered is not issued - human support can only cite the public "
        "documentation as well. Direct such requests to the human support "
        "channel; this skill neither issues nor promises them."),
    "third-party-recovery": (
        "Have the customer know ransomware decryption and deep forensic "
        "recovery are outside Alibaba Cloud platform support and outside this "
        "skill: they need a specialized third-party service."),
    "deletion-on-live-disk": (
        "No snapshot or image covers the loss, but the files were deleted on a "
        "disk that STILL EXISTS: that rules out a platform-side restore, not a "
        "file-level recovery attempt. Whether anything is recoverable depends "
        "on how much was written to the disk afterwards, so it is not settled "
        "until the guest-side attempt is made."),
}

PREVENTION_ACTIONS = [
    "Attach an automatic snapshot policy to every disk holding business data "
    "(see the auto-snapshot-policy document in references/data-recovery-assessment__doc-index.md).",
    "For databases, combine snapshots with application-consistent backups or "
    "a Cloud Backup plan, and keep dumps off the instance.",
    "Renew before expiry, enable renewal reminders, and never rely on the "
    "post-expiry retention window as a backup.",
    "Keep at least one copy of critical data away from the instance itself.",
]

# ---------------------------------------------------------------------------
# Neighboring-tier recognition and handoff (capability C7)
# ---------------------------------------------------------------------------

HANDOFF_RULES = {
    "deleted-instance-lifecycle": {
        "signal": ("The customer asks whether the DELETED/EXPIRED INSTANCE "
                   "ITSELF can come back, retention countdowns, release "
                   "notices - not (or not only) the disk data."),
        "target": ("area:expiry-release-retention (expiry, release "
                   "and data-retention lifecycle tier)"),
        "safety-note": ("Before handing over, make sure any surviving disk "
                        "data is snapshotted or exported first."),
    },
    "backup-product-operations": {
        "signal": ("The customer wants to enable, configure or operate the "
                   "file-backup / Cloud Backup product itself."),
        "target": ("alibabacloud-cloudbackup-ecs-file-backup-essential-edition"),
        "safety-note": ("This skill stays on assessment and step guidance; "
                        "product-side backup/restore execution routes there."),
    },
    "snapshot-execution": {
        "signal": ("The customer asks the assistant to PERFORM rollback, OS "
                   "replacement or disk re-initialization, or to verify a "
                   "write action on their behalf."),
        "target": ("write-action console operations: performed manually by "
                   "the customer with this skill's checklist; tier name "
                   "pending batch alignment"),
        "safety-note": "Safety-net snapshot of the current state first.",
    },
    "host-intrusion": {
        "signal": ("The customer asks for virus / ransomware removal, "
                   "intrusion forensics or hardening; data recovery is only "
                   "a side request."),
        "target": ("host-intrusion cleanup tier - name pending batch "
                   "alignment"),
        "safety-note": ("Take a safety-net snapshot before any cleanup so "
                        "the encrypted/infected state stays analyzable."),
    },
    "connectivity-incident": {
        "signal": ("Public-network access, blackhole filtering, stuck "
                   "start/stop - no data actually lost."),
        "target": ("connectivity / instance-lifecycle operation tiers - "
                   "names pending batch alignment"),
        "safety-note": "Ask once whether data loss accompanied the incident; "
                       "if not, hand off.",
    },
    "billing-account": {
        "signal": ("The core ask is money or account permissions (charge "
                   "type conversion, renewal, real-name review, RAM rights). "
                   "Data survival is only an attached worry."),
        "target": ("billing / account / RAM tiers - names pending batch "
                   "alignment; handle here only the data-preservation "
                   "sub-question"),
        "safety-note": ("If expiry is imminent, run the pre-expiry data "
                        "preservation guidance before the account process "
                        "completes."),
    },
    "guest-evidence-needed": {
        "signal": ("Closure requires reading inside the instance (mounts, "
                   "paths, service state)."),
        "target": ("hand back to the customer as read-only commands to run "
                   "and paste, or route to the remote-connection / Cloud "
                   "Assistant tiers - names pending batch alignment"),
        "safety-note": ("This skill never executes anything inside the "
                        "instance."),
    },
}

# ---------------------------------------------------------------------------
# Official documentation index (capability support; source labels per entry)
# ---------------------------------------------------------------------------
# source: "help-search" = injected aliyun-help-search hit (reviewed during
# requirements analysis); "support-conversation" = link the customer-service
# side actually sent in reviewed ticket conversations, pending a freshness
# re-check before quoting numbers. Never cite a URL that is not listed here.

DOC_INDEX = [
    {
        "key": "linux-recovery",
        "title": ("Best practices for data recovery on a Linux instance"),
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "best-practices-for-linux-instance-data-recovery.md"),
        "use": "Guest-side recovery practice for deleted files on Linux.",
        "source": "help-search",
    },
    {
        "key": "windows-recovery",
        "title": ("Best practices for restoring data on Windows instances"),
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "best-practices-for-restoring-data-on-windows-instances.md"),
        "use": "Guest-side recovery practice for deleted files on Windows.",
        "source": "help-search",
    },
    {
        "key": "auto-snapshot-policy",
        "title": "Automatic snapshot policies",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "automatically-create-snapshots.md"),
        "use": "Prevention: schedule snapshots per disk after an incident.",
        "source": "help-search",
    },
    {
        "key": "app-consistent-snapshot",
        "title": "Application-consistent snapshots",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "create-application-consistent-snapshots-in-the-ecs-console.md"),
        "use": "Database workload backup design guidance.",
        "source": "help-search",
    },
    {
        "key": "local-disks",
        "title": "Local disks",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/local-disks.md"),
        "use": ("Why local-disk data is cleared in the recycling phase and "
                "cannot be snapshotted."),
        "source": "help-search",
    },
    {
        "key": "replace-os",
        "title": "Replace the operating system of an instance",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "replace-the-operating-system-of-an-instance-1.md"),
        "use": ("Official statement that replacing the OS clears the system "
                "disk only."),
        "source": "help-search",
    },
    {
        "key": "custom-image-overview",
        "title": "Custom image overview",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/overview-36.md"),
        "use": "Image-based environment rebuild path.",
        "source": "help-search",
    },
    {
        "key": "snapshot-create",
        "title": "Create a snapshot",
        "url": "https://help.aliyun.com/document_detail/25455.html",
        "use": "Safety-net snapshot step the customer performs.",
        "source": "support-conversation",
    },
    {
        "key": "snapshot-billing",
        "title": "Snapshot billing",
        "url": "https://help.aliyun.com/document_detail/56159.html",
        "use": "Authoritative cost statement for snapshot fees.",
        "source": "support-conversation",
    },
    {
        "key": "snapshot-delete",
        "title": "Delete a snapshot",
        "url": "https://help.aliyun.com/document_detail/128131.html",
        "use": "Cleanup after recovery, done manually by the customer.",
        "source": "support-conversation",
    },
    {
        "key": "reinit-system-disk",
        "title": "Re-initialize a system disk",
        "url": "https://help.aliyun.com/document_detail/25449.html",
        "use": ("Destructive console action; only cited to explain its "
                "preconditions and irreversibility to the customer."),
        "source": "support-conversation",
    },
    {
        "key": "disk-from-snapshot",
        "title": "Create a disk from a snapshot",
        "url": "https://help.aliyun.com/document_detail/32317.html",
        "use": "Data-extraction path: build a disk from a snapshot.",
        "source": "support-conversation",
    },
    {
        "key": "file-backup-console",
        "title": "ECS file backup console entry",
        "url": "ecs.console.aliyun.com/fileBackup/region/<region-id>",
        "use": ("Console path where the customer checks file-backup history "
                "themselves."),
        "source": "support-conversation",
    },
]

# ---------------------------------------------------------------------------
# Permission-error customer wording (literal codes are platform-fixed:
# NoPermission / ImplicitDeny; the other literal must never appear).
# ---------------------------------------------------------------------------

PERMISSION_FAILURE_NOTE = (
    "The read-only query was rejected by authorization. The missing RAM "
    "action is named in the [WARN] line above; grant at least "
    "ecs:DescribeInstances (and sts:GetCallerIdentity for the identity "
    "check) as shown in references/ram-policies.md. Expect error literals "
    "NoPermission or ImplicitDeny; re-run once the policy is attached."
)


INTENT_DOC_LINKS = {
    "restart": "https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md",
    "create_disk": "https://help.aliyun.com/zh/ecs/user-guide/create-a-disk.md",
    "snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot.md",
    "rollback": ("https://help.aliyun.com/zh/ecs/user-guide/"
                 "roll-back-a-disk-by-using-a-snapshot-1.md"),
    "password": ("https://help.aliyun.com/zh/ecs/user-guide/"
                 "reset-the-logon-password-of-an-instance.md"),
    "instance_type": ("https://help.aliyun.com/zh/ecs/user-guide/"
                      "change-the-instance-types-of-subscription-instances.md"),
    "replace_os": ("https://help.aliyun.com/zh/ecs/user-guide/"
                   "replace-the-operating-system-of-an-instance-1.md"),
    "os_migration": "https://help.aliyun.com/document_detail/472022.html",
    "disk_console": "https://ecs.console.aliyun.com/disk/",
    "resize_disk": "https://help.aliyun.com/zh/ecs/user-guide/resize-linux-cloud-disks.md",
}

LOSS_WORDING_RE = re.compile(
    r"丢失|丢了|丢光|没了|不见|找不到|消失|误删|误格|删掉|删除了|删了|"
    r"被删|被格|格式化|重装|重做|更换了系统|换了系统|回滚|恢复|找回|还原|"
    r"勒索|中毒|病毒|黑客|攻击|加密了|释放|到期|清空|清掉|数据没了|"
    r"\brm\s+-rf\b|\bdrop\s+(?:table|database)\b|lost|deleted|missing|"
    r"ransom|encrypted|reclaim", re.I)

LOSS_TYPE_PATTERNS = (
    ("intrusion-deletion", re.compile(
        r"勒索|中毒|病毒|黑客|攻击|被入侵|挖矿|加密了|ransom|hack|intrusion|encrypt", re.I)),
    ("expiry-release", re.compile(
        r"到期|过期|释放|回收|欠费|停机很久|另一台.{0,8}找不到|"
        r"实例.{0,6}找不到|服务器.{0,6}找不到|expire|released|reclaim", re.I)),
    ("mistaken-format", re.compile(
        r"误格|格式化了|被格式化|重新初始化|初始化了|format", re.I)),
    ("system-reinstall", re.compile(
        r"重装|重做系统|更换\s*了?\s*系统|换了系统|重置了系统|重置操作系统|reinstall", re.I)),
    ("config-downgrade", re.compile(
        r"降配|降配置|降低配置|downgrade", re.I)),
    ("cache-not-persisted", re.compile(
        r"(?:重启|重新启动|reboot)[^。；\n]{0,16}(?:缓存|内存)|"
        r"(?:缓存|内存)[^。；\n]{0,12}(?:没了|清空|丢失)", re.I)),
    ("mistaken-delete", re.compile(
        r"误删|误删除|删掉了|删除了|删了|被删|\brm\s+-rf\b|"
        r"\bdrop\s+(?:table|database)\b|deleted", re.I)),
    ("suspected-loss", re.compile(
        r"丢失|丢了|没了|不见了|消失|找不到|找回|数据没了|lost|missing", re.I)),
)

CONSULT_TOPICS = (
    ("snapshot_rollback_effect", re.compile(
        r"快照[^。；\n]{0,12}(?:恢复|回滚)[^。；\n]{0,16}(?:影响|会不会|是否)|"
        r"(?:回滚|恢复)[^。；\n]{0,10}快照[^。；\n]{0,12}(?:影响|配置|安全)")),
    ("login_credential", re.compile(
        r"(?:查看|获取|忘记|不知道|查)[^。；\n]{0,10}(?:用户名|密码|登录名|凭证)|"
        r"用户名[^。；\n]{0,6}(?:及|和|与)[^。；\n]{0,6}密码")),
    ("os_upgrade", re.compile(
        r"升级[^。；\n]{0,10}(?:系统|操作系统|windows|版本)|"
        r"(?:系统|操作系统)[^。；\n]{0,8}升级|"
        r"20(?:08|12|16|19|22)[^。；\n]{0,12}(?:升级|换|迁移)", re.I)),
    ("clear_cache", re.compile(
        r"清理?[^。；\n]{0,6}缓存|缓存[^。；\n]{0,6}清理?|清缓存")),
    ("create_disk", re.compile(
        r"新建[^。；\n]{0,6}(?:云盘|磁盘|数据盘)|创建[^。；\n]{0,6}(?:云盘|磁盘|数据盘)|"
        r"买[^。；\n]{0,6}(?:云盘|数据盘)")),
    ("upgrade_entry", re.compile(
        r"(?:升级|扩容|加大|增加)[^。；\n]{0,12}(?:磁盘|云盘|硬盘|内存|配置)|"
        r"(?:磁盘|云盘|内存)[^。；\n]{0,8}(?:升级|扩容)[^。；\n]{0,10}(?:在哪|哪里|怎么|如何)")),
    ("reboot_instance", re.compile(
        r"(?:如何|怎么|怎样|在哪|哪里)[^。；\n]{0,8}重启|"
        r"重启[^。；\n]{0,8}(?:服务器|实例|机器)[^。；\n]{0,6}(?:？|\?|吗|呢)?$")),
)

CONSULT_LOSS_OVERRIDE = ("snapshot_rollback_effect",)

LOSS_BRANCH_TOPICS = (
    ("reboot_mount_loss", re.compile(
        r"(?:重启|重新启动|reboot)[^。；\n]{0,24}(?:数据|文件|东西|目录)[^。；\n]{0,10}"
        r"(?:丢失|丢了|没了|不见|消失)|(?:数据|文件)[^。；\n]{0,10}(?:丢失|不见)"
        r"[^。；\n]{0,12}(?:重启|重新启动)", re.I)),
    ("db_exposed_intrusion", re.compile(
        r"(?:mongodb|mysql|redis|数据库|mongo)[^。；\n]{0,40}"
        r"(?:黑客|攻击|勒索|入侵|中毒|病毒)|(?:黑客|攻击|勒索|入侵)[^。；\n]{0,30}"
        r"(?:mongodb|mysql|redis|数据库)", re.I)),
    ("instance_missing", re.compile(
        r"(?:实例|服务器|机器|主机)[^。；\n]{0,12}(?:找不到|不见了|没有了|消失|看不到)|"
        r"(?:另一台|另一部|其中一台)[^。；\n]{0,10}(?:服务器|实例|机器)")),
)

LOSS_BRANCH_LINES = {
    "reboot_mount_loss": [
        "Files gone from a mount point after a reboot usually mean the data disk was "
        "not auto-mounted: have the customer approve one read-only Cloud Assistant "
        "command or paste `lsblk -f` and `cat /etc/fstab`.",
        "Have the customer snapshot the disks first, then mount the data disk at its "
        "ORIGINAL empty directory and confirm the files reappear; never format it.",
        "Have the customer persist it with a UUID entry and defaults,nofail in "
        "/etc/fstab, then run mount -a, so the next boot cannot lose it again.",
    ],
    "db_exposed_intrusion": [
        "Have the customer check whether the database port is open to 0.0.0.0/0 in the "
        "security group: an exposed database port is the usual way the password gets "
        "cracked.",
        "Have the customer log into the database and look for a ransom note, then "
        "restrict that inbound rule to the VPC CIDR only, or remove it if no public "
        "access is needed.",
        "Without a snapshot or backup the data cannot be recovered; decryption and "
        "forensics need a specialized third party. Snapshot first before any attempt.",
    ],
    "instance_missing": [
        "Have the customer confirm which instance is missing (id or public IP): this "
        "run reads only the current account and region, so another account or region "
        "is not visible here.",
        "Have the customer check ECS console -> Instances plus the expired/released "
        "list and the order history: an instance released after expiry cannot be "
        "brought back.",
        "Have the customer look for a surviving snapshot or custom image of it and "
        "create a new disk from that to recover the data; snapshot before writing.",
    ],
}

CONSULT_STEPS = {
    "reboot_instance": [
        "Have the customer restart in ECS console -> Instances -> target instance -> "
        "Restart; it stops then starts the instance, so the workload is interrupted.",
        "Have the customer stop the application, flush data to disk and snapshot the "
        "disks first; a forced restart loses data still only in memory.",
        "Have the customer confirm the business programs start on boot, or start them "
        "by hand afterwards. Steps: " + INTENT_DOC_LINKS["restart"],
    ],
    "clear_cache": [
        "Cache means temporary files held on the server; a restart normally clears "
        "them, so have the customer restart in ECS console -> Instances -> Restart.",
        "Have the customer separate cache from disk capacity: capacity is the files "
        "already stored, and deleting them frees space only after a snapshot or a "
        "local backup.",
        "Have the customer confirm the business programs start on boot before "
        "restarting, otherwise they must start them by hand afterwards.",
    ],
    "create_disk": [
        "Have the customer confirm the use case first: a normal ECS data disk is "
        "created in the disk console at " + INTENT_DOC_LINKS["disk_console"] + " -> Create.",
        "Have the customer snapshot the existing disks before attaching or "
        "initializing anything, so a mistake cannot lose data.",
        "Create a disk: " + INTENT_DOC_LINKS["create_disk"] + " ; snapshot first: "
        + INTENT_DOC_LINKS["snapshot"],
    ],
    "snapshot_rollback_effect": [
        "Rolling a disk back to a snapshot overwrites EVERY change made after that "
        "snapshot: security policy, website configuration and system settings included.",
        "Have the customer back up the current configuration, or snapshot the disk "
        "now, so they can roll forward again if the older point is not what they wanted.",
        "Rollback is irreversible and only targets the original disk. See "
        + INTENT_DOC_LINKS["rollback"],
    ],
    "upgrade_entry": [
        "Resize in Storage & Snapshots -> Disks, then grow the partition/filesystem in "
        "the guest. Disk speed is separate: raise ESSD PL / AutoPL, change category, or "
        "pick a storage-enhanced type. " + INTENT_DOC_LINKS["resize_disk"],
        "Memory is separate: confirm the instance is under this account, then console "
        "-> Instances -> open it -> All Actions -> Change Instance Type -> pick a type "
        "-> pay.",
        "A type change needs a restart, so plan off-peak; if stopped, start it after "
        "paying. " + INTENT_DOC_LINKS["instance_type"],
    ],
    "login_credential": [
        "There is no default password. Have the customer read the logon name (Linux "
        "root, Windows Administrator) and try ONLINE Reset Password first: no restart.",
        "Online reset depends on the Cloud Assistant Agent in the instance; if it "
        "fails, offline reset does need a restart, which interrupts the workload.",
        "Have the customer snapshot first and plan a low-traffic window for any "
        "restart. See " + INTENT_DOC_LINKS["password"],
    ],
    "os_upgrade": [
        "Have the customer name the target OS and confirm the instance is under this "
        "account: a replace releases the old system disk and erases it for good.",
        "To keep the system-disk data, use OS migration instead of a replace: "
        + INTENT_DOC_LINKS["os_migration"] + " ; snapshot first either way.",
        "A paid image and added system-disk capacity are charged; re-check the price "
        "on the official site. " + INTENT_DOC_LINKS["replace_os"],
    ],
}

AGENT_OFFLINE_DOC = (
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "stop-and-uninstall-the-cloud-assistant-agent.md")
AGENT_OFFLINE_RE = re.compile(
    r"(?:云助手|云监控|云安全中心|插件|\bagent\b)[^。；\n]{0,24}"
    r"(?:失效|消失|不见|离线|停止|停了|没了|未运行|掉线|无法连接)"
    r"|(?:失效|消失|不见|离线|停止|停了|没了)[^。；\n]{0,16}"
    r"(?:云助手|云监控|插件|\bagent\b)", re.I)
AGENT_OFFLINE_PROCEDURE_RE = re.compile(
    r"(?:如何|怎么|怎样|能否|可以|想要?)[^。；\n]{0,12}(?:停止|卸载|关闭|禁用)")
AGENT_OFFLINE_LINES = (
    "Have the customer check the Agent first: plugins vanishing after a reboot "
    "usually mean the Cloud Assistant and monitoring agents were stopped.",
    "Have the customer log in over VNC and start BOTH agents on boot: Cloud Assistant "
    "(`systemctl start aliyun.service`; Aliyun Assist Service on Windows) and the "
    "CloudMonitor plugin `argusagent`.",
    "Have the customer read only after the Agent is online: a stopped Agent accepts "
    "no command, and a forced reboot drops writes still only in memory.",
)


def agent_offline_signal(question):
    text = question or ""
    if AGENT_OFFLINE_PROCEDURE_RE.search(text):
        return False
    return bool(AGENT_OFFLINE_RE.search(text))

DEFAULT_LOSS_LINES = (
    "Have the customer name the exact lost path or file, when it vanished and the "
    "instance id, then stop writing to that disk.",
    "Have the customer snapshot first and list historical snapshots in ECS console "
    "-> Snapshots: with one, roll back or build a new disk from it; without one the "
    "platform cannot restore.",
    "Have the customer grant login authorization and trace it with `history | grep rm`; "
    "with no snapshot, testdisk or a third-party recovery service is the only path.",
)
