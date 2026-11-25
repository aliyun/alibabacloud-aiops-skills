#!/usr/bin/env python3
"""
_constants.py -- embedded constants and reference data for the ECS instance
clone guide skill.

SECURITY: this module is static data plus limits only. It performs no network
calls, no subprocess calls and no credential handling. The whole skill is
strictly READ-ONLY: the two ECS APIs its scripts may invoke are
DescribeInstances and DescribeInstanceStatus (both read-only queries), plus
the STS caller-identity check. This skill NEVER executes commands inside a
customer instance and NEVER performs a write operation on the customer's
behalf; every change (image creation, image copy, image share, replace
operating system, clone wizard, purchase, snapshot) is executed by the
customer in the console after an explicit risk notice.

Platform rule MUST 1.1.2: scripts/ may contain executable code only, so every
matrix, checklist and FAQ entry used by the entry scripts is embedded here as
Python constants. There are no data files under scripts/.

Evidence discipline: the knowledge below is distilled from the confirmed
requirements dossier for this tier (real support-ticket conversations, the
verified read-only API contracts, and help-center documents captured during
research). Where the dossier could not verify a claim against an official
document body, the entry carries an explicit "verify before quoting" marker
and says whether the wording came from a support agent conversation. Nothing
here is invented; masked or missing source facts stay marked as such.
"""

SKILL_NAME = "alibabacloud-ecs-server-migration-on-cloud: instance-clone-guide"

# ---------------------------------------------------------------------------
# API / endpoint metadata (documentation values; the aliyun CLI resolves its
# own metadata and regional endpoint from the configured region)
# ---------------------------------------------------------------------------
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"
STS_ENDPOINT = "sts.aliyuncs.com"

# The ONLY (product, action) pairs this skill may invoke. The shared CLI layer
# enforces this whitelist and rejects anything else -- a hard guardrail that
# keeps the read-only guarantee true even if a caller is written wrong.
# NOTE: image/snapshot-side read APIs are deliberately NOT part of this skill:
# the tier contract verified only instance-side reads, so image progress and
# image disk association come from the customer's own console screenshots.
ALLOWED_ACTIONS = (
    (ECS_PRODUCT, "DescribeInstances"),
    (ECS_PRODUCT, "DescribeInstanceStatus"),
    (STS_PRODUCT, "GetCallerIdentity"),
)

# ---------------------------------------------------------------------------
# Timeouts and limits
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT = 60        # seconds; every CLI subprocess call carries this
MAX_RESULTS = 100           # DescribeInstances page size (NextToken style)
MAX_PAGES = 20              # pagination guardrail
STATUS_BATCH_LIMIT = 50     # max InstanceId.N entries per status call
TABLE_ROW_LIMIT = 200       # rows rendered in the human-readable table

# ---------------------------------------------------------------------------
# Official documentation links captured for this tier. Captured form is kept
# verbatim from the research hits / ticket conversations; VERIFY each link and
# its wording against the help center before quoting it to a customer
# (requirements dossier 8-9).
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "clone-instances": {
        "title": "Clone ECS instances (console feature)",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/clone-instances.md",
        "note": "Productized clone entry; applies within one account and one region.",
    },
    "create-custom-image": {
        "title": "Create a custom image from an instance",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance",
        "note": "Chain step 1; includes the data-disk selection checkbox.",
    },
    "copy-image": {
        "title": "Copy a custom image",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image",
        "note": "Chain step for cross-region; customers commonly lose the image "
                "here by looking in the wrong region.",
    },
    "share-image": {
        "title": "Share a custom image",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image",
        "note": "Chain step for cross-account; direction is source account "
                "shares to the target account UID.",
    },
    "replace-os": {
        "title": "Replace the operating system of an instance",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance",
        "note": "Landing step on an existing target instance. HIGH RISK: wipes "
                "the target system disk.",
    },
    "create-snapshot": {
        "title": "Create a snapshot",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
        "alt_url": "https://help.aliyun.com/document_detail/25455.html",
        "note": "Mandatory backup step before any replace-operating-system "
                "guidance.",
    },
    "snapshot-billing": {
        "title": "Snapshot billing rules",
        "url": "https://help.aliyun.com/document_detail/56159.html",
        "note": "Cost wording for clone-related snapshot charges.",
    },
    "delete-snapshot": {
        "title": "Delete snapshots",
        "url": "https://help.aliyun.com/document_detail/128131.html",
        "note": "Post-verification cleanup so leftover snapshots stop billing.",
    },
    "export-image": {
        "title": "Export a custom image",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image",
        "note": "Target action for the on-premises goal; carries the "
                "export-limit list below.",
    },
    "oos-overview": {
        "title": "Operation Orchestration Service (OOS) overview",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/overview-3.md",
        "note": "Sibling capability for batch provisioning orchestration; this "
                "skill only recognizes and hands off.",
    },
    "bt-panel-deploy": {
        "title": "Purchase a Linux instance and deploy the BT panel from the console",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/purchase-a-linux-instance-and-deploy-bt-panel-from-the-console.md",
        "note": "Relevant to re-binding panel sites after the IP changes.",
    },
    "what-is-ecs": {
        "title": "What is ECS",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
        "note": "Background wording for non-technical customers (instance / "
                "region / account concepts).",
    },
    "cli-install": {
        "title": "Install and configure the aliyun CLI",
        "url": "https://help.aliyun.com/document_detail/121541.html",
        "note": "Prerequisite tool.",
    },
}

# ---------------------------------------------------------------------------
# Clone solution matrix (capability: path selection + step-by-step guidance).
# Every step is a CUSTOMER-executed console action; this skill only narrates
# entries, expected results, fallbacks, risks and fees, then verifies facts
# with read-only instance queries.
# ---------------------------------------------------------------------------
CLONE_PATHS = {
    "same-account-same-region": {
        "label": "Same account, same region",
        "summary": "Use the console clone-ECS-instances wizard first; fall back "
                   "to the custom-image chain inside one region.",
        "steps": [
            {
                "entry": "ECS console -> Instances (source region)",
                "action": "Locate the source instance; note instance ID, zone, "
                          "instance type, image ID and whether extra data disks "
                          "must be copied.",
                "expect": "The source facts are on screen.",
                "fallback": "Cross-check them read-only: python3 "
                            "scripts/clone_readiness_check.py --region-id "
                            "<region> --instance-ids <i-source>",
            },
            {
                "entry": "ECS console -> the clone-instances wizard for the "
                         "selected instance (official guide: see "
                         "references/clone-solution-matrix.md)",
                "action": "Follow the wizard. It copies configuration and data "
                          "through an image/snapshot and creates the new "
                          "instance. The customer performs every click.",
                "expect": "A clone task starts and the wizard reports the new "
                          "instance ID(s).",
                "fallback": "If the wizard does not cover this case, run the "
                            "custom-image chain inside the same region "
                            "(create custom image -> build from it).",
            },
            {
                "entry": "Images -> Custom Images -> the image created for the "
                         "clone -> Detail",
                "action": "Verify the disks associated with the image, "
                          "especially data disks.",
                "expect": "The image detail lists the expected system disk and "
                          "each selected data disk.",
                "fallback": "If a data disk is missing, the image was built "
                            "without ticking it at creation time -- recreate "
                            "the image with the disk selected.",
            },
            {
                "entry": "Read-only verification",
                "action": "After the clone reports completion (or failure), run "
                          "scripts/clone_readiness_check.py for the region.",
                "expect": "The new instance exists with Running/Stopped status "
                          "as intended.",
                "fallback": "A failure page is NOT proof nothing was created; "
                            "see the fake-failure topic before retrying.",
            },
        ],
        "risk_notices": ["clone-fees", "source-impact"],
    },
    "same-account-cross-region": {
        "label": "Same account, different region",
        "summary": "Custom-image chain: create image -> copy image to the "
                   "destination region -> build there.",
        "steps": [
            {
                "entry": "ECS console -> Instances -> source instance -> Create "
                         "Custom Image (official guide: create-a-custom-image)",
                "action": "Create the custom image and TICK every data disk "
                          "that must be copied. The customer performs this "
                          "write step.",
                "expect": "A custom image appears in Images -> Custom Images "
                          "with progress; status becomes Available when done.",
                "fallback": "The image list capacity shows only the system "
                          "disk size; associated data disks are visible on the "
                          "image detail page once creation completes.",
            },
            {
                "entry": "Images -> Custom Images -> the image -> Copy Image "
                         "(official guide: copy-an-image)",
                "action": "Copy the image to the destination region.",
                "expect": "A copy task exists in the destination region; its "
                          "status becomes Available.",
                "fallback": "Cross-region copy incurs inter-region traffic "
                          "fees; if the copy is missing, look in the "
                          "destination region selector first.",
            },
            {
                "entry": "ECS console -> destination region -> Create instance "
                         "from the custom image",
                "action": "Buy the new instance from the copied image, select "
                          "vSwitch, security group, disk sizes and billing "
                          "mode.",
                "expect": "The instance is created and starts from the copied "
                          "environment.",
                "fallback": "To land on an EXISTING target instance instead, "
                          "use the replace-operating-system landing step below "
                          "and heed its wipe warning.",
            },
        ],
        "risk_notices": ["clone-fees", "source-impact", "first-snapshot-slow"],
    },
    "cross-account-same-region": {
        "label": "Different accounts, same region",
        "summary": "Custom-image chain with a share step: create image -> "
                   "share it with the target account UID -> target builds.",
        "steps": [
            {
                "entry": "Source account: create a custom image (same guidance "
                         "as the cross-region path step 1)",
                "action": "Create the image and tick the needed data disks.",
                "expect": "Image status Available in the source account.",
                "fallback": "Verify associated disks on the image detail page.",
            },
            {
                "entry": "Source account: Images -> Custom Images -> Share "
                         "Image (official guide: share-a-custom-image)",
                "action": "Share the image with the target account UID. "
                          "Sharing is pushed by the source; the target cannot "
                          "pull.",
                "expect": "The target account sees the image under Images -> "
                          "Shared Images in the same region.",
                "fallback": "If the target cannot see it, re-check both UIDs, "
                          "the region selector and the shared-images tab.",
            },
            {
                "entry": "Target account: create an instance from the shared "
                         "image, or replace-operating-system on an existing "
                         "target instance",
                "action": "Build in the target account. The target account "
                          "pays for its own new instance and snapshots it "
                          "creates.",
                "expect": "The cloned environment runs under the target "
                          "account.",
                "fallback": "Read-only cross-check in the TARGET account's "
                            "credential/profile -- this skill's queries only "
                            "see the account behind the configured credential.",
            },
        ],
        "risk_notices": ["clone-fees", "cross-account-visibility"],
    },
    "cross-account-cross-region": {
        "label": "Different accounts AND different regions",
        "summary": "The full four-step chain observed in real tickets: create "
                   "custom image -> copy it to the destination region -> share "
                   "the copy with the target account -> target builds.",
        "steps": [
            {
                "entry": "Source account: create a custom image from the source "
                         "instance (tick needed data disks)",
                "action": "Customer performs the image creation in the source "
                          "account and region.",
                "expect": "Image status Available in the source region.",
                "fallback": "First custom image takes a full snapshot and can "
                          "run long; see the progress-triage topic.",
            },
            {
                "entry": "Source account: copy the image to the destination "
                         "region",
                "action": "Start the cross-region copy.",
                "expect": "A copy task appears and later becomes Available in "
                          "the destination region.",
                "fallback": "Inter-region traffic fees apply; keep the task "
                          "screenshot for support.",
            },
            {
                "entry": "Source account: share the DESTINATION-REGION copy "
                         "with the target account UID",
                "action": "Share AFTER the copy so the image is visible to the "
                          "target account in the destination region.",
                "expect": "The target account sees it under Shared Images in "
                          "the destination region.",
                "fallback": "A share of the source-region image does not make "
                          "it appear in the destination region for the target; "
                          "share the regional copy.",
            },
            {
                "entry": "Target account: build from the shared image (new "
                         "purchase) or replace-operating-system (existing "
                         "target instance)",
                "action": "Customer performs the landing write step in the "
                          "target account. Before replace-operating-system: "
                          "snapshot the target system disk and acknowledge "
                          "the wipe risk.",
                "expect": "The environment runs in the target account and "
                          "region.",
                "fallback": "Verify results with the readiness check run under "
                            "target-account credentials.",
            },
        ],
        "risk_notices": ["replace-os-wipes", "clone-fees", "first-snapshot-slow",
                         "cross-account-visibility"],
    },
}

# Landing-mode wording shared by all paths.
LANDING_MODES = {
    "existing-instance": {
        "label": "Target already has an instance (replace its system)",
        "wording": "Use the replace-the-operating-system flow with the custom "
                   "or shared image. MANDATORY RISK NOTICE: this wipes the "
                   "target system disk; take a manual snapshot of the target "
                   "first and get explicit customer acknowledgment before "
                   "continuing the guidance.",
    },
    "new-purchase": {
        "label": "No target yet (buy from the image)",
        "wording": "Create a new instance selecting the custom (or shared) "
                   "image on the purchase page; the new instance keeps the "
                   "image's environment under a NEW instance ID and NEW IP.",
    },
}

# ---------------------------------------------------------------------------
# Customer goals that leave this skill's scope -> recognition + handoff wording
# ---------------------------------------------------------------------------
GOAL_HANDOFFS = {
    "export-offline": {
        "label": "Copy the environment to an on-premises / non-Alibaba host",
        "wording": "Exporting a custom image is the cloud-to-offline route and "
                   "it is platform-limited; the migration product (SMC) moves "
                   "servers INTO Alibaba Cloud only, never outbound. See the "
                   "export-limits and smc-direction topics, then the image "
                   "export / offline rebuild guidance area.",
    },
    "batch-scale": {
        "label": "Batch provisioning with host-name rules / scaling",
        "wording": "Bulk cloning with orchestration belongs to the "
                   "operations-orchestration capability area (OOS), not to "
                   "one-instance clone guidance. OOS overview document is "
                   "listed in references/handoff-map.md; this skill neither "
                   "designs nor runs templates.",
    },
}

# ---------------------------------------------------------------------------
# Fee and risk wording (customer-visible)
# ---------------------------------------------------------------------------
FEE_ITEMS = [
    "Creating a custom image itself is free, but it creates snapshots by "
    "default and snapshot storage is charged continuously.",
    "Cross-region image copy incurs inter-region traffic fees.",
    "A new instance (clone wizard or purchase from image) is billed under the "
    "target account's normal instance pricing; confirm the purchase page "
    "amount before the customer orders.",
    "Snapshots left behind after a clone keep charging; delete unneeded "
    "snapshots once verification is done (customer action).",
    "Billing figures are owned by the official snapshot-billing document; the "
    "example below is a quoted support-agent figure, not a price promise.",
]

RISK_NOTICES = {
    "replace-os-wipes": "Replace the operating system clears the target "
                        "instance's system disk. Mandatory order in guidance: "
                        "(1) state the wipe risk, (2) advise a manual snapshot "
                        "of the target first, (3) get the customer's explicit "
                        "acknowledgment, (4) only then describe the next "
                        "console step.",
    "clone-fees": "State the fee composition (free image + billable snapshots "
                  "+ cross-region copy traffic + new-instance charges) before "
                  "the customer starts the chain.",
    "source-impact": "Cloning goes through image/snapshot copying: the SOURCE "
                     "instance is not modified and keeps serving. Recommend "
                     "operating at low traffic and snapshotting first anyway.",
    "first-snapshot-slow": "The first custom image requires a full snapshot "
                           "and can take much longer than later incremental "
                           "ones; some regions run under sustained snapshot-"
                           "service load (the specific region was masked in "
                           "the source evidence). Never promise a completion "
                           "time.",
    "cross-account-visibility": "Hard data boundary: read-only queries -- "
                                "including a human agent's tools -- see only "
                                "the account behind the configured credential "
                                "and only the queried region. Facts about the "
                                "other account's instances are always customer "
                                "self-check items (screenshot), never a query "
                                "this skill can run.",
    "data-disk-checkbox": "A data disk is copied only when it was ticked at "
                          "image-creation time; the image list capacity column "
                          "shows the system-disk size only. Verify the "
                          "association on the image detail page.",
    "downtime-not-required": "Creating an image or cloning does not require "
                             "stopping the source instance; data written while "
                             "the snapshot is taken is not included, so for a "
                             "point-in-time consistent copy, pause writes or "
                             "stop the service during capture.",
    "managed-oss-bucket": "The clone/image pipeline uses an Alibaba-managed "
                          "OSS bucket to carry the image data. It is invisible "
                          "to the user, requires no OSS activation, and no "
                          "user-visible bucket needs to be chosen.",
}

# Quoted from a support-agent conversation as an illustration; VERIFY against
# the current official price page before quoting to a customer.
SNAPSHOT_PRICE_EXAMPLE = "Illustration quoted in a real support conversation: " \
                         "about 0.016 CNY per 100 GB snapshot-hour " \
                         "(about 0.4 CNY per day). Official snapshot-billing " \
                         "document is the authority."

# ---------------------------------------------------------------------------
# FAQ topics (offline knowledge served by scripts/clone_guidance.py)
# ---------------------------------------------------------------------------
FAQ_TOPICS = {
    "data-disk-included": {
        "question": "Does cloning also copy my data disks?",
        "answer": "Only disks ticked at custom-image creation time are part of "
                  "the image. A disk like /dev/vdb1 is NOT copied unless you "
                  "selected it when creating the image.",
        "guidance": "Ask the customer to recreate or verify via the image "
                    "detail page, which lists every disk associated with the "
                    "image (customer console action).",
    },
    "image-capacity-display": {
        "question": "My image shows 300 GB but my disk is 5 TB -- did the "
                    "clone go wrong?",
        "answer": "No. While an image is still being created, the list shows "
                  "only the system-disk capacity. After it reaches 100%, open "
                  "the image detail page to see the associated data disks.",
        "guidance": "Direct the customer to Images -> Custom Images -> click "
                    "the image ID -> detail page (support-agent-verified "
                    "wording).",
    },
    "shutdown-needed": {
        "question": "Must I stop the instance to clone it?",
        "answer": "No. Cloning a running instance is supported. The boundary: "
                  "data written while the image/snapshot is captured is not in "
                  "the image, so if you need a consistent point-in-time copy, "
                  "pause the writes (or stop the service) during capture.",
    },
    "source-impact": {
        "question": "Will cloning affect the source server?",
        "answer": "The source instance is not modified by image creation or "
                  "cloning; it keeps serving traffic. Operating at low peak "
                  "and taking a manual snapshot first is still recommended.",
    },
    "managed-oss-bucket": {
        "question": "The clone says the image uploads to OSS but I never "
                    "activated OSS. Where does my data go?",
        "answer": "The pipeline uses a service-managed OSS bucket owned by "
                  "the platform: it is not visible in the customer's console, "
                  "needs no activation, and stores only the temporary image "
                  "object. This message is expected, not a fault.",
    },
    "export-limits": {
        "question": "Why can't I export my custom image to run it offline?",
        "answer": "Support-agent wording (verify against the official export "
                  "document before quoting): export is not supported for "
                  "encrypted images, for custom images derived from a cloud "
                  "marketplace image, and for Windows Server operating-system "
                  "images. The marketplace-image restriction is a platform "
                  "policy and cannot be bypassed.",
        "guidance": "Recognize the case (check the source instance's image "
                    "type in the console; the customer can see it under "
                    "instance details), then give the degraded alternative: "
                    "back up the data locally, rebuild the environment on the "
                    "local server and import the data.",
    },
    "smc-direction": {
        "question": "Can SMC migrate an ECS instance down to my IDC?",
        "answer": "No. SMC (Server Migration Center) migrates servers FROM "
                  "on-premises or other clouds INTO Alibaba Cloud ECS; it has "
                  "no reverse direction.",
    },
    "marketplace-image-source": {
        "question": "My instance runs on a marketplace image. What breaks?",
        "answer": "Cloning within the cloud still works, but custom images "
                  "derived from marketplace images cannot be exported "
                  "(license/policy limit). Decide the goal first: in-cloud "
                  "clone -> normal chain; offline export -> blocked, see the "
                  "export-limits alternative.",
    },
    "clone-fees": {
        "question": "What will cloning cost me?",
        "answer": "Custom-image creation is free but billable snapshots are "
                  "created by default; a cross-region copy incurs traffic "
                  "fees; the new instance is billed normally. Leftover "
                  "snapshots keep charging until deleted.",
        "guidance": "List the fee composition before guiding the chain, and "
                    "end the guidance with the snapshot-cleanup step.",
    },
    "snapshot-price-example": {
        "question": "Roughly how much does a snapshot cost?",
        "answer": SNAPSHOT_PRICE_EXAMPLE,
    },
    "fake-failure": {
        "question": "The page says the clone FAILED -- should I just retry?",
        "answer": "Do not retry blindly. A sub-task failure (for example the "
                  "image-copy step) can be displayed as a whole-operation "
                  "failure while the instances and resource stacks were "
                  "actually created -- a real ticket ended with 25 duplicated "
                  "instances and an overdue balance after a blind retry.",
        "guidance": "First verify existence read-only: run "
                    "scripts/clone_readiness_check.py for the region (and the "
                    "instance-name prefix if cloned instances follow a naming "
                    "pattern), plus the console instance list and resource-"
                    "stack list under the correct account and region. If "
                    "resources exist despite the failure page, stop, record "
                    "IDs and time, and open a human support ticket about the "
                    "status display and charges.",
    },
    "first-snapshot-slow": {
        "question": "Is it normal that the first clone is very slow?",
        "answer": "Yes, it can be: the first custom image takes a FULL "
                  "snapshot, and some regions run under sustained "
                  "snapshot-service load. Real tickets resolved by waiting; "
                  "no official duration standard exists, so no time promise.",
    },
    "ip-change-rebind": {
        "question": "After cloning, the IP changed -- what must I re-bind?",
        "answer": "A cloned instance gets a new private and (unless EIP-based) "
                  "new public IP. Re-point DNS records, web-panel site "
                  "bindings (for example the BT/BaoTa panel), whitelists on "
                  "partner systems, and any license bound to the old IP.",
        "guidance": "IP retention or IP transfer is a sibling capability "
                    "area (public IP / EIP guidance), not clone guidance; "
                    "hand off with the collected old/new IP facts.",
    },
    "guest-identity-uuid": {
        "question": "The cloned machine boots the wrong disk / collides with "
                    "the source (same UUIDs).",
        "answer": "Disk copies from one image can carry identical filesystem "
                  "UUIDs, partition UUIDs and EFI identifiers; a root=UUID "
                  "kernel parameter may then resolve to the clone data disk "
                  "and break boot. This is a guest-side condition this skill "
                  "cannot read from the cloud API.",
        "guidance": "Ask the customer to run READ-ONLY checks inside their own "
                    "OS and paste back the output (blkid, ls -l "
                    "/dev/disk/by-uuid, ls -l /dev/disk/by-partuuid), or hand "
                    "off to the remote-connection / Cloud Assistant sibling "
                    "area for in-guest remediation. In the source ticket the "
                    "customer recovered by rebuilding from the data-disk "
                    "snapshot; frame that only as a customer option.",
    },
    "monitor-agent-duplicate": {
        "question": "The clone and the source keep swapping Cloud Monitor "
                    "data.",
        "answer": "A cloned host can keep the source's monitoring-agent "
                  "identity files, so the service cannot distinguish the two "
                  "machines and data jumps between them.",
        "guidance": "Guest-side fix (removing/moving agent identity files and "
                    "restarting the probe) belongs to the Cloud Monitor "
                    "sibling area; this skill only identifies the symptom, "
                    "collects both instance IDs, and hands off.",
    },
    "cross-account-visibility": {
        "question": "Can you check the other account's server for me?",
        "answer": "No. Read-only queries see only the account behind the "
                  "configured credential and only the queried region -- human "
                  "agents face the same boundary. Any fact about the other "
                  "account is a customer self-check item (login there, "
                  "screenshot it back).",
    },
    "windows-scope": {
        "question": "Any special wording for Windows instances?",
        "answer": "This release of the skill does not carry Windows-specific "
                  "clone wording: no ticket evidence for a Windows source "
                  "instance existed. The only Windows fact on file is the "
                  "quoted export restriction (Windows Server OS images cannot "
                  "be exported), which is part of the export-limits list.",
    },
    "spec-sufficiency": {
        "question": "Will 2 vCPU / 4 GiB run my Java shop application?",
        "answer": "Out of scope: this skill states the read-only spec facts of "
                  "the target instance and does not judge whether a spec can "
                  "carry a customer's business workload -- even the human "
                  "tickets closed such questions by phone without a written "
                  "conclusion. Suggest a load test on the clone before "
                  "cutting over.",
    },
}

# ---------------------------------------------------------------------------
# Progress / stuck triage (capability: K3). Thresholds are deliberately
# RELATIVE: no official duration standard exists; the dossier's "30 minutes"
# figures came from customer narration only.
# ---------------------------------------------------------------------------
TRIAGE_COLLECT_FIRST = [
    "instance ID(s) of the source and target",
    "full page screenshot showing the progress bar, image/clone name and the "
    "region selector",
    "start time of the clone/image operation and the currently shown progress",
    "whether this is the FIRST custom image for this account and region",
    "approximate disk size being captured (system disk + any ticked data disks)",
]

TRIAGE_BRANCHES = {
    "in-progress": {
        "verdict": "progressing",
        "wording": "The reported progress is above 0%, so the task is moving. "
                   "The first custom image takes a full snapshot and can run "
                   "for a long time; some regions additionally run under "
                   "sustained snapshot-service load (exact regions were masked "
                   "in the evidence used to build this skill). Wait and "
                   "re-check periodically; no completion time can be promised.",
        "next": "Ask for a fresh screenshot after a reasonable wait; if "
                "progress stops advancing for much longer than this account's "
                "own history, move to the escalate branch.",
    },
    "stuck-zero-long": {
        "verdict": "possible-stuck",
        "wording": "Progress has stayed at 0% for significantly longer than "
                   "this account's usual clone/image completion time. This "
                   "skill cannot see the platform-side task queue, and a "
                   "human support session could not either -- the real "
                   "tickets that looked like this were escalated, so do the "
                   "same.",
        "next": "Output the human-ticket handoff with the collected evidence "
                "list; do not declare the task failed and do not retry before "
                "running the existence check (fake-failure risk).",
    },
    "stuck-zero-default": {
        "verdict": "unknown-duration",
        "wording": "Progress is 0% but there is no baseline for what is normal "
                   "for this account. 0% alone is not proof of a fault: the "
                   "first full-snapshot image can legitimately sit at 0% "
                   "early on.",
        "next": "Ask whether this is the first custom image and how long has "
                "passed versus typical past runs; re-check later; escalate "
                "only once it clearly exceeds the customer's own baseline.",
    },
    "stuck-zero-not-first": {
        "verdict": "possible-stuck",
        "wording": "Progress is 0% and this is not the first custom image, so "
                   "the full-snapshot warm-up explanation does not apply here. "
                   "With no completion-time baseline on record this is still "
                   "not proof of a fault: the platform-side task queue is "
                   "invisible to this skill, exactly as it is to a human "
                   "support session.",
        "next": "Collect the evidence list and output the human-ticket "
                "handoff; do not declare the task failed and do not retry "
                "before running the existence check (fake-failure risk).",
    },
    "info-missing": {
        "verdict": "insufficient-facts",
        "wording": "Not enough facts to triage yet; conclusions are withheld "
                   "instead of guessed.",
        "next": "Request the TRIAGE_COLLECT_FIRST items (see references/"
                "progress-triage.md), then re-run.",
    },
}

ESCALATION_TEMPLATE = (
    "Human support ticket handoff. Please submit a ticket and attach: (1) "
    "source and target instance IDs, (2) the clone start time, (3) the full "
    "page screenshot showing progress and the region selector, (4) whether "
    "this is the first custom image for the account. State that no write "
    "changes were made by the customer while waiting."
)

# ---------------------------------------------------------------------------
# Post-clone verification checklist (capability: K5 + K4)
# ---------------------------------------------------------------------------
POST_CLONE_CHECKLIST = [
    {
        "item": "The new instance actually exists and has the intended status",
        "owner": "read-only query",
        "detail": "python3 scripts/clone_readiness_check.py --region-id "
                  "<region> [--instance-ids ...|--instance-name <prefix>]",
    },
    {
        "item": "No duplicate creation after a failure page (loss prevention)",
        "owner": "read-only query + console",
        "detail": "Compare the instance count for the region against "
                  "expectations; also check resource stacks. Retry only after "
                  "this check -- a shown failure may hide a successful build.",
    },
    {
        "item": "Data disks present on the clone",
        "owner": "customer console",
        "detail": "Image detail page lists associated disks; then the new "
                  "instance's disk list.",
    },
    {
        "item": "IP changed: DNS, web-panel site bindings, partner "
                 "whitelists, IP-bound licenses",
        "owner": "customer",
        "detail": "New instance means new private and public IP unless an EIP "
                  "route is used (EIP retention is a sibling area).",
    },
    {
        "item": "Security group of the new instance re-confirmed",
        "owner": "customer console",
        "detail": "The clone may reference a copied security group; verify "
                  "rule contents. Rule-behavior diagnosis is a sibling "
                  "security-group area.",
    },
    {
        "item": "Guest identity duplication risk for image-derived fleets",
        "owner": "customer in-guest (read-only self-check)",
        "detail": "Same-image machines can share filesystem/partition UUIDs, "
                  "machine-id and agent identity files; ask the customer to "
                  "run the read-only commands below inside the guest and "
                  "paste back the output, or hand off to the remote-connection "
                  "/ Cloud Assistant sibling area.",
    },
    {
        "item": "Snapshot and copy-traffic cleanup",
        "owner": "customer console",
        "detail": "Delete unneeded snapshots after verification; note "
                  "cross-region copy traffic already spent.",
    },
    {
        "item": "Fees sanity check",
        "owner": "customer + commercial handoff",
        "detail": "Review the bill for snapshot storage and copy traffic; any "
                  "compensation/refund/withdrawal request goes to the "
                  "Billing Management console or human support -- outside this "
                  "skill.",
    },
]

# Read-only commands the CUSTOMER runs inside their own OS and pastes back.
# This skill never executes anything inside an instance.
GUEST_SELF_CHECK_COMMANDS = [
    {"cmd": "blkid", "purpose": "list filesystem UUIDs of all disks"},
    {"cmd": "ls -l /dev/disk/by-uuid /dev/disk/by-partuuid",
     "purpose": "check for duplicate filesystem / partition UUIDs between "
                "source and clone disks"},
    {"cmd": "cat /etc/machine-id",
     "purpose": "check the machine identity inherited from the image"},
    {"cmd": "df -h", "purpose": "confirm which filesystems are mounted where"},
]

# ---------------------------------------------------------------------------
# Sibling-area handoff map. Route names are the tier's working labels; the
# requirements dossier notes they still need alignment against the batch's
# skill list (dossier 8-2).
# ---------------------------------------------------------------------------
HANDOFF_MAP = [
    {
        "topic": "security-group-behavior",
        "keywords": ["security group", "sg rule", "rule priority", "port",
                     "cannot access after switching", "website slow after "
                     "security group"],
        "route": "security-group guidance sibling area",
        "wording": "The issue is about rule content / precedence / behavior "
                   "after switching groups, not the clone chain itself. Hand "
                   "off with: instance ID, old and new security group IDs, "
                   "the switch timestamp, and the reproduced symptom. Two "
                   "real tickets stayed unresolved even with rule review -- "
                   "if rules look identical and behavior differs, say so "
                   "verbatim and escalate rather than guessing.",
    },
    {
        "topic": "ip-retention",
        "keywords": ["keep the same ip", "same ip", "ip changed", "eip",
                     "transfer ip", "fix ip"],
        "route": "public IP / EIP guidance sibling area",
        "wording": "IP retention/migration is allocated by the network "
                   "product, not by the clone flow. Collect the current "
                   "public IP, instance IDs and the business need, then hand "
                   "off. No written retention answer existed in the source "
                   "tickets -- do not improvise one.",
    },
    {
        "topic": "cloud-monitor-agent",
        "keywords": ["cloud monitor", "cloudmonitor", "monitoring data "
                     "jumps", "agent", "plugin data wrong"],
        "route": "Cloud Monitor guidance sibling area (guest-side)",
        "wording": "Duplicated agent identity on a cloned host requires "
                   "in-guest file operations; this skill only reads cloud "
                   "APIs. Hand off with both instance IDs and the "
                   "symptom window.",
    },
    {
        "topic": "image-export-offline",
        "keywords": ["export image", "download image", "on-premises", "idc",
                     "offline server", "smc"],
        "route": "image export / offline rebuild guidance sibling area",
        "wording": "Direction cloud-to-offline: check the export-limits list "
                   "first (encrypted image, marketplace-derived custom image, "
                   "Windows Server OS image are not exportable). SMC does not "
                   "run in this direction. Alternative path: back up data, "
                   "rebuild locally, import data.",
    },
    {
        "topic": "instance-resize",
        "keywords": ["upgrade configuration", "change instance type",
                     "resize", "cannot scale up", "more cpu"],
        "route": "instance resize / variation guidance sibling area",
        "wording": "Whether a family supports upgrade is a resize-capability "
                   "question; clone-vs-resize decisions start there. Real "
                   "tickets confirmed certain families upgrade, but this "
                   "skill states only read-only spec facts and refers the "
                   "capability question onward.",
    },
    {
        "topic": "batch-orchestration",
        "keywords": ["batch", "scaling", "many instances", "host name rule",
                     "oos", "orchestration", "automation template"],
        "route": "operations orchestration (OOS) sibling capability area",
        "wording": "Bulk provisioning with naming/orchestration rules is an "
                   "OOS template concern; cloning one instance is only one "
                   "step of it. OOS overview document is listed in "
                   "references/handoff-map.md; this skill recognizes and "
                   "hands off, it never designs templates.",
    },
    {
        "topic": "commercial-billing",
        "keywords": ["refund", "balance withdrawal", "voucher",
                     "compensation", "overdue", "unsubscribe", "deducted "
                     "wrongly"],
        "route": "Billing Management console / human commercial channel",
        "wording": "Money actions (refund, unsubscribe, balance withdrawal, "
                   "compensation vouchers) are commercial processes outside a "
                   "read-only technical skill. State the boundary, point to "
                   "the Billing Management console or ticket channel, and "
                   "never simulate an outcome.",
    },
    {
        "topic": "apsara-stack",
        "keywords": ["apsara stack", "dedicated cloud", "private cloud",
                     "enterprise edition", "localgpu", "clone installation"],
        "route": "dedicated-cloud support channel (outside public-cloud "
                 "channels entirely)",
        "wording": "The described environment is a dedicated-cloud "
                   "(Apsara Stack) deployment; public-cloud console paths "
                   "and public-cloud OpenAPI do not apply, and no public "
                   "diagnosis is possible from here. Both source tickets "
                   "received no in-session solution. Hand off to the "
                   "dedicated-cloud support channel named in the customer's "
                   "contract.",
    },
    {
        "topic": "guest-command-execution",
        "keywords": ["run a command inside my server", "check inside the os",
                     "exec in instance", "cloud assistant"],
        "route": "remote connection / Cloud Assistant sibling area",
        "wording": "This skill never executes anything inside an instance. "
                   "It can only (a) list read-only commands for the customer "
                   "to run and paste back, or (b) refer the request to the "
                   "in-guest execution capability area.",
    },
    {
        "topic": "oss-product",
        "keywords": ["webp", "image conversion", "bucket rule", "auto "
                     "convert"],
        "route": "OSS product guidance",
        "wording": "Object-storage image processing questions are unrelated "
                   "to ECS cloning; refer to the OSS documentation area.",
    },
]

# ---------------------------------------------------------------------------
# Honest-limitation notes rendered with every relevant answer
# ---------------------------------------------------------------------------
DATA_BOUNDARY_NOTES = [
    "Scope of read-only queries: ONLY the account behind the configured "
    "credential, ONLY the region given to the script. Cross-account and "
    "other-region facts never appear in these outputs; they are customer "
    "self-check items.",
    "Image/snapshot task progress is NOT visible to this skill: the tier "
    "contract verified only instance-side reads. Progress facts come from "
    "the customer's console screenshots.",
    "Page status and the platform's real result can disagree: a real clone "
    "reported as failed had actually created all instances. Conclusions "
    "about existence are taken from read-only queries and console listings, "
    "never from the task banner alone.",
    "Duration thresholds in this skill are relative (compared with the "
    "customer's own past runs); no official timing standard exists in the "
    "source evidence.",
    "The region behind one 'slow region' explanation was masked in the "
    "source evidence and is therefore kept generic here.",
    "Quoted agent wordings (export limits, snapshot price example) are "
    "marked; verify them against the official documents before repeating "
    "them as rules.",
]
