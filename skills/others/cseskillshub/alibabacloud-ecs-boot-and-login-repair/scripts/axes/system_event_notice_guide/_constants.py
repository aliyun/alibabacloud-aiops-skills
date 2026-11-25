"""Constants and embedded reference tables for the ECS system event notice skill.

All knowledge used for interpretation lives in this module as code constants.
Every statement carries a `basis` marker so a reader can tell official wording
from wording observed in customer reports and not yet re-verified.
"""

SKILL_NAME = "alibabacloud-ecs-system-event-notice-guide"
SKILL_TITLE = "ECS system events and scheduled maintenance notice guide"

# ---------------------------------------------------------------- CLI runtime
ALIYUN_BIN = "aliyun"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}"
CLI_TIMEOUT_SECONDS = 20
MAX_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 0.6
PAGE_SIZE = 50
MAX_PAGES = 20
MAX_INSTANCE_IDS = 100

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"

STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"
STS_ACTION_PLUGIN_MODE = "GetCallerIdentity"
STS_ACTION_NAME = "GetCallerIdentity"

# Closed allowlist of the (product, action) pairs this skill may call. The shared
# call layer refuses anything else, so a read-only run cannot drift into a change
# call even if a later edit adds one.
ALLOWED_READ_ACTIONS = (
    (ECS_PRODUCT, ACTION_DESCRIBE_INSTANCES),
    (ECS_PRODUCT, ACTION_DESCRIBE_INSTANCE_STATUS),
    (STS_PRODUCT, STS_ACTION_PLUGIN_MODE),
)

RETRYABLE_ERROR_TOKENS = (
    "throttling",
    "serviceunavailable",
    "internalerror",
    "unavailable",
    "timeout",
    "timed out",
    "connectionreset",
    "connection refused",
    "500",
    "502",
    "503",
    "504",
)

# Canonical labels emitted by this skill for authorization failures.
AUTH_FAIL_NO_PERMISSION = "NoPermission"
AUTH_FAIL_IMPLICIT_DENY = "ImplicitDeny"
AUTH_ERROR_TOKENS = (
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "access denied",
    "permissiondenied",
    "forb",
    "denied",
    "deny",
    "unauthor",
    "invalidaccesskey",
    "signaturedoesnotmatch",
    "not authorized",
)

# Field names whose values are masked in every message this skill prints.
SENSITIVE_VALUE_TOKENS = (
    "accesskeyid",
    "accesskeysecret",
    "access_key",
    "securitytoken",
    "sts_token",
    "signature",
    "password",
    "privatekey",
)

# ---------------------------------------------------------------- Doc sources
# URLs come from the ECS help centre index and from wording quoted by Alibaba
# Cloud support. None of them has been re-fetched by this build; see
# `DOC_VERIFICATION_NOTE` and references/event-status-semantics.md.
DOC_SYSTEM_EVENTS_OVERVIEW = (
    "https://help.aliyun.com/zh/ecs/user-guide/overview-of-ecs-system-events.md"
)
DOC_SYSTEM_EVENTS_EXPLANATION = "https://help.aliyun.com/document_detail/57052.html"
DOC_IDENTIFY_INSTANCE_ISSUES = (
    "https://help.aliyun.com/zh/ecs/user-guide/identify-and-troubleshoot-instance-issues.md"
)
DOC_RESOURCE_RESERVATION_EVENTS = (
    "https://help.aliyun.com/zh/ecs/user-guide/resource-reservation-event.md"
)
DOC_FEATURE_OVERVIEW = (
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "product-function-custom-node-ecs-normal.md"
)
DOC_CREATE_IMAGE_FROM_INSTANCE = (
    "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance"
)
DOC_COPY_IMAGE = "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image"
DOC_CREATE_FROM_IMAGE = (
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "create-an-ecs-instance-by-using-a-custom-image"
)
DOC_SLA_CLAIM = "https://usercenter2.aliyun.com/sla/availabilityhome"

DOC_VERIFICATION_NOTE = (
    "Reference URLs were collected from the ECS help index and from wording "
    "quoted by Alibaba Cloud support; this build has not re-fetched them, so "
    "quote a rule to the customer only after opening the linked page."
)

BASIS_OFFICIAL = "official doc (URL listed, page not re-fetched by this build)"
BASIS_OBSERVED = "wording observed in customer reports; not verified against the official doc"

# --------------------------------------------------------- Fixed report blocks
LIMITATION_EVENT_RECORDS = (
    "This skill cannot read the instance system event list or its state, "
    "because no event-read action has been verified for it yet. The report "
    "therefore contains instance facts and notice wording only. Absence of "
    "event data in this report is NOT a statement that no event exists: open "
    "the scheduled O&M events page in the ECS console, or submit a ticket."
)

LIMITATION_HOST_HEALTH = (
    "Underlying host health, the physical machine an instance currently runs "
    "on, and the destination of a migration are not exposed to customers "
    "through any supported read API. If this information is required, submit "
    "a ticket so that support can check it on the platform side."
)

LIMITATION_NO_WRITE = (
    "Rebooting, rescheduling, cancelling, snapshotting and claiming compensation "
    "are performed by the customer in the console or by a human ticket handler. "
    "This skill only explains the rules and the steps."
)

NEXT_ACTION_DEFAULT = (
    "Read the report, confirm the instance facts with the customer, then let "
    "the customer perform the listed console steps. Do not run any change."
)

NEXT_ACTION_NEEDS_INSTANCE = (
    "Ask the customer for the instance ID or the IP address shown in the "
    "notice, plus the region, then re-run the entry script."
)

NEXT_ACTION_DEGRADED = (
    "Report what could not be read, keep the notice interpretation as "
    "reference-only, and point the customer at the console events page or a "
    "ticket for the missing facts."
)

# ------------------------------------------------------------ Notice knowledge
# `keys` are lower-case substrings matched against the notice text after the
# agent has rendered the customer's wording into English (SKILL.md, step 2).
NOTICE_FAMILIES = (
    {
        "id": "scheduled-maintenance-reboot",
        "title": "Planned maintenance reboot event (reboot required due to system maintenance)",
        "keys": (
            "system maintenance",
            "maintenance and reboot",
            "scheduled maintenance",
            "reboot due to system",
            "need to restart the instance",
            "restart the instance due to",
            "planned o&m",
            "operation and maintenance",
            "maintenance window",
        ),
        # Matching on this phrase alone cannot separate planned from unplanned.
        "generic_keys": ("operation and maintenance",),
        "why": (
            "The platform detected a potential hardware or software fault risk "
            "on the underlying host and issued a planned O&M event so the "
            "customer can move the instance to a healthy host at a chosen time. "
            "It is not caused by anything the customer configured."
        ),
        "state": (
            "Before the deadline the event is pending customer action or "
            "waiting for automatic execution; the console events page shows "
            "the current state."
        ),
        "action_required": "yes",
        "answer_deadline": (
            "The notice carries an automatic execution time. If the customer "
            "does nothing, the system reboots the instance at that time. The "
            "automatic time has no self-service reschedule entry in the "
            "console; a request to move it is handled by a ticket."
        ),
        "answer_data": (
            "A maintenance reboot does not re-deploy the instance and does not "
            "erase cloud disk data. Running processes stop, so the customer "
            "should reboot in a low-traffic window, make sure unwritten data is "
            "flushed, and create a snapshot first when the workload is critical."
        ),
        "answer_ip": (
            "A maintenance reboot keeps the private IP and the public IP of the "
            "instance unchanged."
        ),
        "options": (
            "Reboot now from the console",
            "Schedule the reboot inside the maintenance window",
            "Do nothing and let the system execute at the deadline",
        ),
        "refs": (DOC_SYSTEM_EVENTS_OVERVIEW, DOC_SYSTEM_EVENTS_EXPLANATION),
        "basis": BASIS_OFFICIAL,
    },
    {
        "id": "unplanned-down-migration",
        "title": "Unplanned event already executed: downtime migration caused by a host fault",
        "keys": (
            "unexpected restart",
            "unplanned",
            "instance restarted automatically",
            "server restarted by itself",
            "down migration",
            "host fault",
            "physical machine failure",
            "automatic restart due to",
        ),
        "why": (
            "An unexpected hardware or software fault on the underlying host "
            "made the platform migrate the instance to another host and reboot "
            "it. The action is already finished when the customer sees it."
        ),
        "state": "executed",
        "action_required": "no",
        "answer_deadline": (
            "There is nothing to schedule: the migration and reboot already "
            "happened. The event record carries the start and end time."
        ),
        "answer_data": (
            "Cloud disk data is retained. Services do not come back by "
            "themselves unless the application is configured to start on boot, "
            "so enabling auto-start is the practical follow-up."
        ),
        "answer_ip": "The private and public IP addresses do not change.",
        "options": (
            "Confirm the application started after the reboot",
            "Configure the service to start automatically on boot",
            "Claim SLA compensation from the availability SLA page if the "
            "impact qualifies (customer action, not this skill)",
        ),
        "refs": (DOC_SYSTEM_EVENTS_OVERVIEW, DOC_SLA_CLAIM),
        "basis": BASIS_OFFICIAL,
    },
    {
        "id": "event-canceled",
        "title": "Event state 'canceled'",
        "keys": (
            "canceled",
            "cancelled",
            "event was canceled",
            "automatically canceled",
            "notice disappeared",
        ),
        "why": (
            "The risk was repaired or mitigated on the platform side before the "
            "automatic execution time, or the maintenance task was completed or "
            "adjusted, so the planned event was withdrawn. A canceled event is "
            "consistent with an earlier notice; it does not mean the first "
            "notice was wrong."
        ),
        "state": "canceled",
        "action_required": "no",
        "answer_deadline": "No deadline applies once the event is canceled.",
        "answer_data": "Nothing is rebooted and no data is affected.",
        "answer_ip": "No address change is involved.",
        "options": (
            "No action needed; refresh the events page to confirm the state",
            "Keep a snapshot routine for the workload as general hygiene",
        ),
        "refs": (DOC_SYSTEM_EVENTS_OVERVIEW,),
        "basis": BASIS_OBSERVED,
    },
    {
        "id": "event-avoided",
        "title": "Event state 'avoided' after a customer-initiated reboot",
        "keys": (
            "avoided",
            "already rebooted manually",
            "i rebooted it myself",
            "risk avoided",
            "state shows avoided",
        ),
        "why": (
            "The customer rebooted the instance before the deadline, so the "
            "customer avoided the risk and the platform recorded the event as "
            "avoided. The state that says the system performed the action is a "
            "different one, so 'avoided' is the expected result of a manual "
            "reboot and not a failed execution."
        ),
        "state": "avoided",
        "action_required": "no",
        "answer_deadline": "The deadline is passed for the customer's use.",
        "answer_data": "The reboot the customer triggered behaves like any reboot.",
        "answer_ip": "No address change is involved.",
        "options": (
            "No further action needed for this event",
            "If a diagnostic still flags the instance, re-read the event state "
            "and refresh the console; state can lag behind the reboot",
        ),
        "refs": (DOC_SYSTEM_EVENTS_OVERVIEW,),
        "basis": BASIS_OBSERVED,
    },
    {
        "id": "event-executed",
        "title": "Event state 'executed'",
        "keys": ("executed", "execution completed", "already executed"),
        "why": (
            "The system carried out the planned action itself, which is the "
            "state shown when nobody rebooted the instance before the deadline."
        ),
        "state": "executed",
        "action_required": "no",
        "answer_deadline": "The action already ran at the automatic time.",
        "answer_data": "Cloud disk data is retained; application restart is the customer's task.",
        "answer_ip": "No address change is involved for a maintenance reboot.",
        "options": ("Verify the workload after the reboot", "Configure auto-start on boot"),
        "refs": (DOC_SYSTEM_EVENTS_OVERVIEW,),
        "basis": BASIS_OBSERVED,
    },
    {
        "id": "storage-performance-limit",
        "title": "Instance:StoragePerformanceReachLimit",
        "keys": (
            "storageperformancereachlimit",
            "Instance:StoragePerformanceReachLimit",
            "storage performance",
            "disk throughput limit",
        ),
        "why": (
            "The read/write throughput of the cloud disks attached to the "
            "instance reached the performance limit of the disk configuration. "
            "It is a block storage throughput limit, not a public bandwidth "
            "problem."
        ),
        "state": "alert",
        "action_required": "customer analysis",
        "answer_deadline": "Not a scheduled action; it is a performance alert.",
        "answer_data": "No data is lost; I/O is throttled while the limit holds.",
        "answer_ip": "Unrelated to IP addresses.",
        "options": (
            "Look at per-disk read/write BPS and IOPS metrics in CloudMonitor",
            "Locate the process doing the I/O on the instance (customer side)",
            "Consider a higher-performance disk category (decision and change "
            "belong to the customer and to a disk performance skill)",
        ),
        "refs": (DOC_IDENTIFY_INSTANCE_ISSUES,),
        "basis": BASIS_OBSERVED,
    },
    {
        "id": "region-shutdown",
        "title": "Region or zone closure and forced migration notice",
        "keys": (
            "region closure",
            "region will be discontinued",
            "cease of service",
            "region is being taken offline",
            "region offline notice",
            "the zone is closing",
            "migration because the region is closing",
        ),
        "why": (
            "A region or zone is being retired, so instances there must be moved "
            "by the customer before the cut-off date. The platform does not move "
            "the instance automatically."
        ),
        "state": "customer migration required",
        "action_required": "yes",
        "answer_deadline": (
            "The cut-off date in the notice is set by the platform and is not "
            "extendable by this skill."
        ),
        "answer_data": (
            "Data survives only through the migration the customer performs; "
            "after the cut-off the instance is released, so an image is the "
            "carrier of the data and configuration."
        ),
        "answer_ip": (
            "A new instance in another region gets new addresses, so the public "
            "IP changes and DNS or allow-lists must be updated."
        ),
        "options": (
            "Create a custom image from the instance",
            "Copy the image to the destination region",
            "Create a new instance from the copied image",
            "Then handle unsubscribe, refund or coupon questions through the "
            "billing and commercial channel",
        ),
        "refs": (
            DOC_CREATE_IMAGE_FROM_INSTANCE,
            DOC_COPY_IMAGE,
            DOC_CREATE_FROM_IMAGE,
        ),
        "basis": BASIS_OBSERVED,
        "handoff": "region-migration-and-commercial",
    },
    {
        "id": "local-disk-redeploy",
        "title": "Redeployment event affecting locally attached disks",
        "keys": ("redeploy", "re-deployment", "local disk will be cleared", "local disk"),
        "why": (
            "A redeployment class event moves the instance to other hardware and "
            "re-initialises locally attached disks. This is the family where data "
            "on local disks really can be lost."
        ),
        "state": "pending customer action",
        "action_required": "yes",
        "answer_deadline": (
            "The notice carries the latest time; the instance is redeployed "
            "automatically afterwards."
        ),
        "answer_data": (
            "Data on locally attached disks is destroyed by a redeployment. Back "
            "it up to a cloud disk, Object Storage Service or another persistent "
            "store before the deadline. Cloud disks of the instance are not "
            "re-initialised by a plain reboot. Confirm the exact wording of the "
            "official event overview page before answering a customer."
        ),
        "answer_ip": "The private IP is kept for the same instance.",
        "options": (
            "Back up local disk data before the deadline",
            "Reboot or redeploy inside a low-traffic window as the notice offers",
        ),
        "refs": (DOC_SYSTEM_EVENTS_OVERVIEW, DOC_SYSTEM_EVENTS_EXPLANATION),
        "basis": BASIS_OBSERVED,
        "confidence": "low: no reviewed support case was a redeployment case",
    },
    {
        "id": "auto-start-stop-confusion",
        "title": "One-off maintenance event mixed up with scheduled start/stop",
        "keys": (
            "every week",
            "weekly restart",
            "does it repeat",
            "auto shutdown timer",
            "scheduled start and stop",
            "recurring reboot",
        ),
        "why": (
            "A maintenance event is a one-off action triggered by platform "
            "conditions. A repeating start or stop pattern comes from the "
            "customer's own auto start/stop configuration, which is a different "
            "feature."
        ),
        "state": "clarification",
        "action_required": "no",
        "answer_deadline": (
            "The maintenance event has the single deadline printed in the "
            "notice; it does not recur weekly."
        ),
        "answer_data": "Neither feature erases cloud disk data.",
        "answer_ip": "Neither feature changes addresses.",
        "options": (
            "Check the auto start/stop configuration in the console if the "
            "pattern repeats",
            "Treat the maintenance notice as a one-off",
        ),
        "refs": (DOC_FEATURE_OVERVIEW,),
        "basis": BASIS_OBSERVED,
    },
    {
        "id": "os-internal-cause",
        "title": "Symptom inside the guest after an unexplained restart",
        "keys": (
            "programs all stopped",
            "firewall was turned on",
            "out of memory",
            "oom",
            "blue screen",
            "crash log",
            "task scheduler",
            "who changed my server",
        ),
        "why": (
            "The guest operating system itself may have crashed, hit memory "
            "pressure, run a scheduled task, or been touched by software inside "
            "the instance. This is outside the platform event mechanism."
        ),
        "state": "not a platform event until an event record proves otherwise",
        "action_required": "customer self-check",
        "answer_deadline": "Not applicable.",
        "answer_data": "Depends on the cause found inside the guest.",
        "answer_ip": "Not applicable.",
        "options": (
            "Read the guest logs (see references/customer-selfcheck-steps.md) "
            "and report what is found",
            "Compare with the platform-side record: if none exists, say so "
            "plainly instead of guessing",
        ),
        "refs": (DOC_IDENTIFY_INSTANCE_ISSUES,),
        "basis": BASIS_OBSERVED,
        "handoff": "guest-os-investigation",
    },
    {
        "id": "resource-reservation-event",
        "title": "Resource reservation event (adjacent family, not maintenance)",
        "keys": ("resource reservation", "capacity reservation", "reservation expiring"),
        "why": (
            "Resource reservation events describe a reserved capacity expiring "
            "or changing, which is a different family from host maintenance."
        ),
        "state": "clarification",
        "action_required": "no",
        "answer_deadline": "Follow the reservation expiry wording in its own doc.",
        "answer_data": "No instance data is involved.",
        "answer_ip": "Not applicable.",
        "options": ("Read the resource reservation event doc", "Do not merge this family with maintenance reboot answers"),
        "refs": (DOC_RESOURCE_RESERVATION_EVENTS,),
        "basis": BASIS_OFFICIAL,
        "handoff": "capacity-reservation",
    },
)

# -------------------------------------------------------- Status semantics
STATE_ENUMERATION_NOTE = (
    "These labels cover the states seen in the reviewed support cases only. The full "
    "official state machine and its exact console wording are not verified in "
    "this build; check " + DOC_SYSTEM_EVENTS_OVERVIEW + " before quoting a state "
    "name as official."
)
