"""Constants and embedded reference knowledge for the relocation guide skill.

Every lookup table this skill needs is embedded here as a Python constant, so
``scripts/`` holds executable code only. Facts carry a provenance tag:

* ``dialogue``   - confirmed from a first-hand support conversation transcript
* ``summary``    - confirmed only from a historical case summary (lower confidence)
* ``official``   - quoted from the official Alibaba Cloud help page named in ``docs``
* ``design``     - this skill's own reading/branching logic, not a quoted fact
"""

SKILL_NAME = "alibabacloud-ecs-instance-relocation-guide"
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

ALIYUN_BIN = "aliyun"
CALL_TIMEOUT_SECONDS = 30
STS_TIMEOUT_SECONDS = 20
MAX_RETRIES = 2
BACKOFF_BASE_SECONDS = 1.0
PAGE_SIZE = 50
MAX_PAGES = 20

# Exhaustive list of API operations this skill is allowed to call. All are reads.
READ_API_ALLOWLIST = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus",
    "ecs:DescribeAvailableResource",
    "sts:GetCallerIdentity",
)

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

DOCS = {
    "change_types_across_zones":
        "https://help.aliyun.com/zh/ecs/user-guide/change-instance-types-across-zones.md",
    "migration_due_to_underlying_upgrade":
        "https://help.aliyun.com/zh/ecs/user-guide/instance-migration-due-to-upgrades-at-the-underlying-layer.md",
    "regional_essd_disks":
        "https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md",
    "create_disk_from_snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot.md",
    "disk_disaster_recovery_overview":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-8.md",
    "eni_overview":
        "https://help.aliyun.com/zh/ecs/user-guide/eni-overview.md",
    "how_to_buy_ecs":
        "https://help.aliyun.com/zh/ecs/user-guide/a-picture-is-to-teach-you-how-to-buy-cloud-server-ecs.md",
    "custom_image_from_instance":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance",
    "custom_image_from_snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-a-snapshot-1",
    "copy_image":
        "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image",
    "share_custom_image":
        "https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image",
    "create_instance_by_custom_image":
        "https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image",
    "ecs_ownership_transfer":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "how-to-cross-account-transfer-migration-ecs-instance",
    "replace_operating_system":
        "https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance",
    "migrate_operating_system":
        "https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance",
    "create_snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "copy_snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/copy-a-snapshot",
    "share_snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/share-a-snapshot",
    "snapshot_pricing": "https://help.aliyun.com/document_detail/56159.html",
    "snapshot_backup_guide": "https://help.aliyun.com/document_detail/25455.html",
    "refund_entry": "https://usercenter2.aliyun.com/refund/refund",
    "refund_destinations":
        "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations",
    "refund_rules": "https://help.aliyun.com/document_detail/116043.html",
}

SNAPSHOT_FIRST_NOTICE = (
    "SNAPSHOT-FIRST RULE: before any operating-system replacement, any "
    "cross-zone change, and any image or snapshot clean-up, take a manual "
    "snapshot of every affected disk and confirm it reached the available "
    "state. Replacing the operating system wipes the system disk; a snapshot "
    "is the only fast rollback. Custom images themselves are not charged, but "
    "the snapshot they generate is, and copying a snapshot is billed "
    "separately."
)

# Constraints applied per relocation scenario.
SCENARIO_CONSTRAINTS = {
    "cross-region": (
        {
            "id": "region-immutable",
            "provenance": "dialogue",
            "text": (
                "The region of an ECS instance cannot be changed after the "
                "instance exists. 'Moving to another region' always means "
                "building the target in the destination region from an image "
                "or a backup, then releasing the old instance by your own "
                "decision."
            ),
        },
        {
            "id": "image-chain-steps",
            "provenance": "dialogue",
            "text": (
                "Standard chain: snapshot each disk, build a custom image from "
                "the system-disk snapshot, copy the image (and the snapshot) to "
                "the destination region, then either replace the operating "
                "system of an existing target instance with the copied image or "
                "launch a new instance from it, and rebuild data disks from "
                "their snapshots."
            ),
            "docs": ("custom_image_from_instance", "copy_image",
                     "create_instance_by_custom_image", "replace_operating_system"),
        },
        {
            "id": "custom-image-system-disk-only",
            "provenance": "dialogue",
            "text": (
                "A custom image built from an instance covers the system disk "
                "by default; data disks need their own snapshots and a separate "
                "rebuild step."
            ),
            "docs": ("create_disk_from_snapshot",),
        },
        {
            "id": "ip-and-dns",
            "provenance": "dialogue",
            "text": (
                "Cross-region relocation changes the public address. Plan the "
                "cutover: DNS records, client allowlists, and any licence "
                "bound to the old address."
            ),
        },
    ),
    "cross-account": (
        {
            "id": "pick-the-route-first",
            "provenance": "design",
            "text": (
                "Cross-account work splits into three routes and the destination "
                "decides which one applies: keep this very instance in the same "
                "region and zone (official ownership transfer), change the "
                "region, the zone or the specification (image and snapshot "
                "sharing, or Server Migration Service), or the instance is "
                "preemptible (rebuild only). Choose the route before booking any "
                "downtime."
            ),
        },
        {
            "id": "ownership-transfer",
            "provenance": "official",
            "text": (
                "Route 1 - official ECS ownership transfer (resource transfer). "
                "It moves the ownership of one instance from one account to "
                "another. It supports subscription (pre-paid) and pay-as-you-go "
                "instances and does NOT support preemptible instances. It only "
                "changes which account owns the instance: the region, the zone, "
                "the instance type, the cloud disks (system disk plus data "
                "disks) and the fixed public IP configuration all stay exactly "
                "as they were. Snapshots and custom images are NOT transferred "
                "with it. The operation takes about half an hour, Alibaba Cloud "
                "does not charge for it, and from then on the target account "
                "pays the running costs."
            ),
            "docs": ("ecs_ownership_transfer",),
        },
        {
            "id": "ownership-transfer-prerequisites",
            "provenance": "official",
            "text": (
                "Prerequisites of the ownership transfer: stop the running "
                "instance before the operation, and prepare a VPC, a vSwitch and "
                "a security group in the target account for the same region and "
                "zone. The instance is placed in the target account's VPC, so "
                "its network location and its reachability change, and the "
                "private IP address may change as well; the security group rules "
                "become the target account's. An elastic IP is not carried over "
                "(unbind it first). Plan the DNS, allowlist, RAM and monitoring "
                "cut-over after the transfer."
            ),
            "docs": ("ecs_ownership_transfer",),
        },
        {
            "id": "share-then-build",
            "provenance": "dialogue",
            "text": (
                "Route 2 - a different region, a different zone or a different "
                "specification. The ownership transfer cannot do that, so the "
                "target is built: share the custom image and the snapshots with "
                "the destination account and use them there, or let Server "
                "Migration Service produce a new instance. Granting RAM rights "
                "across accounts is a manual task outside this skill."
            ),
            "docs": ("share_custom_image", "share_snapshot"),
        },
        {
            "id": "preemptible-rebuild-only",
            "provenance": "official",
            "text": (
                "Route 3 - a preemptible (spot) instance. It cannot be "
                "transferred, so it is rebuilt in the destination account from "
                "a custom image or from the application deployment, and it stays "
                "a preemptible instance there. Say this plainly instead of "
                "promising a transfer."
            ),
        },
        {
            "id": "target-disk-not-smaller",
            "provenance": "dialogue",
            "text": (
                "The target system disk must be at least as large as the source "
                "image. A smaller target (an 80 GiB source image onto a 40 GiB "
                "target) fails: enlarge the target disk first."
            ),
        },
        {
            "id": "target-system-disk-wiped",
            "provenance": "summary",
            "text": (
                "Applying a shared image to an existing instance goes through "
                "the operating-system replacement flow, which clears the system "
                "disk of that instance. Back up the target as well as the "
                "source. (Case-summary evidence; confirm in the console warning "
                "before proceeding.)"
            ),
            "docs": ("replace_operating_system", "snapshot_backup_guide"),
        },
        {
            "id": "source-untouched",
            "provenance": "dialogue",
            "text": (
                "Image and snapshot operations do not disturb the source "
                "instance; it keeps running while the copy is built."
            ),
        },
        {
            "id": "smc-vs-image",
            "provenance": "dialogue",
            "text": (
                "Server Migration Service produces a new instance, so it belongs "
                "to route 2 as well: use it when the destination must differ in "
                "region, zone or specification, or when the operating system "
                "cannot be imaged cleanly. When the goal is to load data into an "
                "instance that already exists in the other account, the image "
                "plus snapshot chain gives more control; when the goal is that "
                "same instance under new ownership, neither applies - use the "
                "ownership transfer."
            ),
        },
    ),
    "cross-zone": (
        {
            "id": "same-zone-attach-limit",
            "provenance": "dialogue",
            "text": (
                "A data disk can only be attached inside its own zone. An "
                "instance moved to another zone cannot keep its old data disk; "
                "rebuild the disk from a snapshot in the destination zone, or "
                "copy the files over the network."
            ),
            "docs": ("create_disk_from_snapshot", "regional_essd_disks"),
        },
        {
            "id": "private-ip-changes",
            "provenance": "dialogue",
            "text": (
                "After a cross-zone change the private address always changes "
                "(you may edit it afterwards); the fixed public address is "
                "retained where allocation permits, otherwise a new one is "
                "issued."
            ),
            "docs": ("change_types_across_zones",),
        },
        {
            "id": "order-must-be-paid",
            "provenance": "summary",
            "text": (
                "A cross-zone change is only executed after its order is paid. "
                "'No progress after I started it' usually means an unpaid order "
                "is waiting in the billing console."
            ),
        },
        {
            "id": "dependent-private-resources",
            "provenance": "summary",
            "text": (
                "Private-address dependencies block the change even while the "
                "instance is stopped: custom route entries, remote-session "
                "records, data-sync tasks. Clear them in their own consoles "
                "first."
            ),
        },
        {
            "id": "managed-eni",
            "provenance": "dialogue",
            "text": (
                "An elastic network interface owned by a managed cluster cannot "
                "be deleted by hand; it is released with the cluster. When its "
                "vSwitch is being retired, change the vSwitch of the interface "
                "instead."
            ),
            "docs": ("eni_overview",),
        },
        {
            "id": "eip-rebind",
            "provenance": "summary",
            "text": (
                "An elastic IP address is unbound from the old instance and "
                "bound to the target within the same region; that is a manual "
                "console step."
            ),
        },
    ),
    "platform-retirement": (
        {
            "id": "no-automatic-move",
            "provenance": "dialogue",
            "text": (
                "The platform does not move your instance for you. A retirement "
                "notice obliges you to run the relocation yourself inside the "
                "announced window."
            ),
            "docs": ("migration_due_to_underlying_upgrade",),
        },
        {
            "id": "retained-window-not-guaranteed",
            "provenance": "dialogue",
            "text": (
                "During a retirement window an instance may be kept while its "
                "residual value is refunded automatically, but service levels "
                "are not guaranteed and the instance can be released at any "
                "moment. Treat the window as urgent, not as extra time."
            ),
        },
        {
            "id": "entitlement-is-manual",
            "provenance": "dialogue",
            "text": (
                "Remaining subscription time cannot be transferred to another "
                "region or instance; unsubscription and any compensation are "
                "decided by manual commercial review. This skill never promises "
                "an amount, a voucher, or an extension."
            ),
            "docs": ("refund_rules", "refund_destinations"),
        },
    ),
    "os-change": (
        {
            "id": "windows-major-upgrade",
            "provenance": "dialogue",
            "text": (
                "Windows Server cannot be upgraded across more than one major "
                "version in place. Either use the operating-system migration "
                "feature step by step, or back up and replace the operating "
                "system and redeploy the software."
            ),
            "docs": ("migrate_operating_system", "replace_operating_system"),
        },
        {
            "id": "overseas-os-family-swap",
            "provenance": "summary",
            "text": (
                "Historical handling reports that Windows-to-Linux replacement "
                "is not supported in some overseas regions. No official rule "
                "page is cited here, so confirm it in the console for your "
                "region before planning around it."
            ),
        },
    ),
}

# Customer-visible error wording and the handling list for each.
ERROR_BRANCHES = (
    {
        "phrase": "instance type in the destination zone is out of stock",
        "provenance": "summary",
        "meaning": (
            "The target zone has no capacity for that instance type right now; "
            "availability changes per zone and per minute."
        ),
        "actions": (
            "Re-check with the read-only stock preflight against every candidate zone.",
            "Try another zone in the same region, or another instance type in the same family.",
            "For a purchase-time failure, void the order and re-order in a zone that has stock.",
        ),
    },
    {
        "phrase": "reverse dependencies or route dependencies on the private ip",
        "provenance": "summary",
        "meaning": (
            "Resources bound to the instance's private address still reference "
            "it, so the zone change is refused. Stopping the instance does not "
            "clear them."
        ),
        "actions": (
            "Review custom route entries in the VPC route tables.",
            "Review remote-session and data-sync tasks that recorded this private address.",
            "Remove or re-point the references, then start the change again.",
        ),
    },
    {
        "phrase": "no visible progress after starting the zone change",
        "provenance": "summary",
        "meaning": "The relocation order exists but is unpaid, so nothing runs.",
        "actions": (
            "Open the order list and pay or cancel the pending relocation order.",
            "Confirm the instance status afterwards with the read-only status query.",
        ),
    },
    {
        "phrase": "operating system type replacement is not supported",
        "provenance": "summary",
        "meaning": (
            "The region or image combination rejects a cross-family operating "
            "system replacement."
        ),
        "actions": (
            "Confirm the target image family in the console for this region.",
            "If unsupported, plan a rebuild in place plus a data restore instead.",
        ),
    },
)

# Three destination-driven routes for a cross-account move. Route 1 is the
# official ownership transfer of a single instance; route 2 and 3 are rebuilds.
CROSS_ACCOUNT_BRANCHES = (
    {
        "when": ("the same instance must be kept, in the same region and the "
                 "same zone, and it is not a preemptible instance"),
        "route": ("official ECS ownership transfer (resource transfer, "
                  "\u8d44\u6e90\u8fc7\u6237) of the instance itself: "
                  + DOCS["ecs_ownership_transfer"]),
        "before": (
            "Stop the running instance first: the transfer does not run on a running instance.",
            "Prepare a VPC, a vSwitch and a security group in the target account, in the same region and zone.",
            "Unbind the elastic IP; an EIP is not carried over by the transfer.",
        ),
        "result": (
            "Region, zone, instance type and the cloud disks (system plus data) stay as they were.",
            "The fixed public IP configuration stays as it was.",
            "Ownership only: nothing is reinstalled, so the operating system and the application are untouched.",
        ),
        "tradeoffs": (
            "Snapshots and custom images are NOT transferred; share them separately if the target account needs them.",
            "The instance joins the target account's VPC, so its network location and reachability change and the private IP may change; security group rules come from the target account.",
            "Preemptible instances cannot be transferred at all.",
            "About half an hour of work, no charge for the operation; the target account pays the running cost afterwards.",
        ),
        "docs": ("ecs_ownership_transfer",),
    },
    {
        "when": ("the destination needs another region, another zone or another "
                 "specification"),
        "route": ("build the target in the destination account: share the custom "
                  "image and the snapshots and use them there, or let Server "
                  "Migration Service produce a new instance"),
        "before": (
            "Snapshot every disk of the source instance and build the custom image from the system-disk snapshot.",
            "Confirm the target system disk is at least as large as the source image.",
            "Confirm the destination zone has stock for the instance type you want.",
        ),
        "result": (
            "A new instance id, a new public address and, in most cases, a new private address.",
            "Data-disks must be rebuilt from their own snapshots in the destination.",
        ),
        "tradeoffs": (
            "Longer chain than the transfer: image build, replication and rebuild steps.",
            "Snapshot replication and the second copy are billed.",
            "More moving parts, but the only option when region, zone or specification has to change.",
        ),
        "docs": ("share_custom_image", "share_snapshot",
                 "create_instance_by_custom_image"),
    },
    {
        "when": "the instance is a preemptible (spot) instance",
        "route": ("rebuild only: image or redeploy the application in the "
                  "destination account; preemptible instances cannot be "
                  "transferred"),
        "before": (
            "Treat the source as disposable: it can be reclaimed at any moment while you copy.",
            "Keep the deployment automation and the data copy separate, so the rebuild can be repeated.",
        ),
        "result": (
            "Nothing about the instance identity: new id, new address, new capacity reservation.",
        ),
        "tradeoffs": (
            "The destination instance stays preemptible, so it can still be reclaimed there.",
            "Any stop-the-world copy has no guaranteed completion window.",
        ),
        "docs": ("ecs_ownership_transfer",),
    },
)

# Facts a cloud read cannot obtain; they stay manual.
BLIND_SPOTS = (
    "Physical location of the host machine room: resolved manually by support, no public read-only query.",
    "Payment state of a relocation order: no verified read-only query; check the order list in the console.",
    "Copy, share and replication state of images and snapshots: no read-only query is wired into this skill; verify in the console.",
    "Full list of private-address dependencies (routes, session records, sync tasks): verify resource by resource in each console.",
    "Whether your application runs correctly on the target: business verification by the customer.",
    "Disk sizes and categories attached to an instance: not part of the read-only instance query; read them in the block storage console.",
    "Retirement calendars and compensation policy: decided off-platform; quote only the notice you received.",
)

PRE_FLIGHT_CHECKLIST = (
    "For another account, settle the route first: ownership transfer when the region, zone and specification stay, otherwise an image and snapshot rebuild.",
    "Snapshot every affected disk and wait until each snapshot is usable.",
    "Confirm the target system disk is at least as large as the source image.",
    "Confirm the destination region or zone has stock for the instance type.",
    "List the data disks, elastic network interfaces and vSwitches that must move with the instance.",
    "Clear route entries, remote-session records and data-sync tasks that reference the private address.",
    "Note the public and private addresses, then plan DNS, allowlist and licence cut-over.",
    "Pay the relocation order, otherwise nothing is executed.",
    "Verify the application on the target before releasing the old instance.",
)

CUTOVER_CHECKLIST = (
    "Update DNS records to the new public address.",
    "Update client-side and database allowlists.",
    "Re-attach elastic IPs and security groups intended to move.",
    "Re-issue or re-bind licence files that were bound to the old address.",
    "Keep the source instance until the business checks on the target have passed.",
)

# Requests outside this skill's symptom area. Named sibling skills are the
# three this tier is allowed to reference; everything else uses generic
# wording until the naming is confirmed.
HANDOFFS = (
    {
        "symptom": "making, copying, sharing or restoring an image, or disaster recovery from an image",
        "target": "alibabacloud-ecs-disaster-recovery-image",
    },
    {
        "symptom": "a disk expansion that did not take effect, a partition that was not extended",
        "target": "area:disk-expand-diagnosis",
    },
    {
        "symptom": "an instance that will not start, or is stuck in an intermediate state",
        "target": "area:instance-state-diagnosis",
    },
    {
        "symptom": "slow disk IO or performance below the instance type",
        "target": "area:resource-bottleneck",
    },
    {
        "symptom": "capacity or inode usage inside the guest operating system",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "unsubscription, refund, residual value or renewal pricing",
        "target": "manual commercial review",
    },
    {
        "symptom": "sold-out stock during a purchase, or an order that cannot be paid",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "actually executing an operating-system replacement",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "private connectivity between ECS and a managed database",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "an instance that the console does not list",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "a Simple Application Server rather than an ECS instance",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "the physical address of the host machine room",
        "target": "manual support",
    },
    {
        "symptom": "whole-site or cross-cloud application migration",
        "target": "another specialised capability, handled manually",
    },
    {
        "symptom": "changing the deployment set an instance belongs to",
        "target": "not a relocation; deployment-set placement is a different operation",
    },
)
