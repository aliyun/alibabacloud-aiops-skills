"""Constants for alibabacloud-ecs-marketplace-image-guide.

Every piece of knowledge the entry script prints lives here as a Python
constant, so no data file is shipped under scripts/ (static rule 1.1.2).
Text is ASCII-only and describes read-only fact lookup plus customer-side
guidance.
"""

SKILL_NAME = "alibabacloud-ecs-marketplace-image-guide"
SKILL_VERSION = "1.0.0"

# ---------------------------------------------------------------- transport
UA_PREFIX = "AlibabaCloud-Agent-Skills"
CLI_BINARY = "aliyun"
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
# Plugin-mode action (lower-case hyphenated), per the Alibaba Cloud CLI style.
STS_ACTION_CALLER_IDENTITY = "GetCallerIdentity"

CALL_TIMEOUT_SECONDS = 30
IDENTITY_TIMEOUT_SECONDS = 20
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0
DEFAULT_PAGE_SIZE = 50
MAX_PAGES = 20
MAX_INSTANCE_IDS = 50

RETRYABLE_CODES = (
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "InternalError",
    "ServiceUnavailable",
    "UnknownError",
    "SystemBusy",
)

# Read-only action whitelist. Nothing outside this tuple is ever invoked.
READ_ACTIONS = (
    "DescribeInstances",
    "DescribeImages",
    "DescribeInstanceStatus",
)

NO_PERMISSION_CODES = ("NoPermission", "ImplicitDeny")

# ------------------------------------------------------------------ routing
INTENTS = (
    "selection",
    "billing",
    "conversion",
    "refund",
    "system-disk",
    "transfer",
    "export",
    "authorization",
    "inventory",
    "triage",
)

SYMPTOMS = (
    "conversion-blocked",
    "boot-stuck-old-image",
    "image-not-compatible",
    "renewal-charge-question",
    "unexpected-image-charge",
    "duplicate-renewal-order",
    "refund-blocked",
    "refund-amount-missing",
    "payment-failed-on-image-change",
    "transfer-not-supported",
    "export-not-supported",
    "no-permission-on-image-change",
    "docker-pull-failure",
    "image-software-failure",
    "iso-install-request",
    "unrelated-boot-failure",
)

# Substring matching is ASCII-insensitive; the caller normalises the quoted
# console message into one of the symptom tokens above when it is localized.
SYMPTOM_KEYWORDS = {
    "conversion-blocked": (
        "marketplace image",
        "does not support conversion",
        "not support conversion",
        "conversion is not supported",
    ),
    "payment-failed-on-image-change": ("payment failed", "pay failed", "order failed"),
    "no-permission-on-image-change": (
        "nopermission",
        "implicitdeny",
        "permission denied",
        "not authorized",
        "systemdisk",
    ),
    "docker-pull-failure": ("docker", "registry-mirrors", "registry mirror", "pull"),
    "image-software-failure": ("sql server", "panel", "won't start", "cannot log in"),
    "iso-install-request": ("iso", "bring your own image"),
    "boot-stuck-old-image": ("operating system is loading", "startup abnormal"),
    "refund-amount-missing": ("refund amount", "amount is blank", "no amount"),
    "duplicate-renewal-order": ("two renewal orders", "duplicate renewal"),
    "transfer-not-supported": ("transfer", "another account"),
    "export-not-supported": ("export", "on-premises", "download image"),
    "unexpected-image-charge": ("extra fee", "billed separately"),
    "renewal-charge-question": ("renewal", "renew", "still charge"),
}

# ------------------------------------------------------------- help library
HELP_DOCS = (
    ("ECS images overview (paid image types and billing notes)",
     "https://help.aliyun.com/zh/ecs/images#62754e11b1h6r"),
    ("Change the operating system of an instance (system disk replacement)",
     "https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance"),
    ("Transfer an ECS instance across accounts (limits)",
     "https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance"),
    ("Create a custom image from an instance",
     "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance"),
    ("Export a custom image (supported scope)",
     "https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image"),
    ("Use mstsc.exe to move a file to a Windows instance",
     "https://help.aliyun.com/zh/ecs/user-guide/use-mstsc-exe-to-upload-a-file-to-a-windows-instance"),
    ("Change the preferred language of a Windows instance",
     "https://help.aliyun.com/zh/ecs/user-guide/change-the-preferred-language-of-a-windows-instance"),
    ("Create a snapshot",
     "https://help.aliyun.com/document_detail/25455.html"),
    ("Snapshot billing",
     "https://help.aliyun.com/document_detail/56159.html"),
    ("Refund rules",
     "https://help.aliyun.com/document_detail/116043.html"),
    ("Where a refund goes",
     "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations"),
    ("Self-service renewal-order cancellation entry",
     "https://usercenter2.aliyun.com/refund/renew-list"),
    ("ECS instance overview (lifecycle states)",
     "https://help.aliyun.com/zh/ecs/user-guide/overview-52.md"),
    ("Purchase a Linux instance and deploy Apache in the console",
     "https://help.aliyun.com/zh/ecs/user-guide/use-the-ecs-instance-in-the-console.md"),
    ("What is ECS",
     "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md"),
    ("ECS feature overview",
     "https://help.aliyun.com/zh/ecs/user-guide/product-function-custom-node-ecs-normal.md"),
)

# ------------------------------------------------------------ risk notices
RISK_CHANGE_OS = (
    "Changing the operating system releases the current system disk. Every file, "
    "database and configuration on that disk is permanently deleted and cannot be "
    "recovered. The instance has to be in the Stopped state first, which interrupts "
    "the workload. Confirm a backup or snapshot exists before continuing."
)
RISK_SNAPSHOT_BILLING = (
    "Snapshots are billed separately as an independent item; review the snapshot "
    "billing document before you create one."
)
RISK_IRREVERSIBLE = (
    "This submission cannot be undone. Re-read the resource identifiers shown, "
    "confirm the amount displayed on the page, and only then submit."
)
RISK_BILLING_DIFF = (
    "Switching the billing method recomputes payable amounts and can forfeit coupon "
    "or promotion value. This assistant cannot see amounts, so verify the figures on "
    "the page before submitting."
)
CUSTOMER_EXECUTES = (
    "Each step below is performed by you in the Alibaba Cloud console. This assistant "
    "is read-only: it holds no change permission and never acts on your behalf."
)

# --------------------------------------------------- knowledge: rule blocks
RULES = {
    "billing-independent": (
        "Image licensing is billed on its own schedule, independently of the instance "
        "billing method. A subscription instance that carries a paid image is charged "
        "for the image every month, and renewing the instance renews the image order in "
        "the same cycle."
    ),
    "renewal-license": (
        "When a subscription instance is renewed while it uses a paid image, such as "
        "Windows Server, Red Hat Enterprise Linux, SUSE Linux Enterprise Server or "
        "Alibaba Cloud Linux 3 Pro, the licence for that image is renewed at the same "
        "time, on the same cycle as the instance."
    ),
    "promotion-scope": (
        "Renewal promotions cover the instance side. The image order is not covered, so "
        "a discounted renewal can still show a separate image charge."
    ),
    "free-image-option": (
        "To stop image charges on a later cycle, move the instance to a free public "
        "image before the next renewal. Preconditions: a Stopped instance plus a "
        "verified backup. The data on the current system disk is not recoverable after "
        "the change."
    ),
    "stopped-required": (
        "An image change and its order payment only complete while the instance sits in "
        "the Stopped state. A payment failure on a running instance is that state gate, "
        "not a billing fault: stop the instance, confirm the backup, then pay again."
    ),
    "conversion-blocked": (
        "An instance that runs a Marketplace image cannot switch between subscription "
        "and pay-as-you-go billing. The console reports that the instance image is a "
        "Marketplace image and that conversion is not supported."
    ),
    "conversion-path": (
        "Working sequence: first change the image to an eligible public image, then "
        "convert the billing method. When picking the public image, exclude Red Hat "
        "Enterprise Linux and SUSE Linux Enterprise Server because they are also paid; "
        "Alibaba Cloud Linux is the usual choice."
    ),
    "same-message-two-entries": (
        "The same Marketplace-image conversion message also appears when a customer is "
        "working on the public IP address. In that case nothing about the image needs to "
        "change: the customer entered the instance billing-method entry by mistake and "
        "only the bandwidth billing method needs converting."
    ),
    "refund-image-fee": (
        "A paid image order that has been associated with a running instance is treated "
        "as consumed. Its fee is not refundable on its own; only the remaining value of "
        "the instance is refundable."
    ),
    "unsubscribe-precondition": (
        "Before unsubscribing an instance that carries a paid image, the image has to be "
        "changed to a public image. While a paid image is attached, the cancellation flow "
        "can refuse to proceed or show no amount."
    ),
    "renewal-order-cancellation-order": (
        "Renewal orders that have not taken effect yet cannot be cancelled self-service "
        "when a paid image is attached. A cancellation specialist handles the instance "
        "renewal order first, and the image renewal order is then cancelled "
        "automatically as a follow-on."
    ),
    "refund-tracking": (
        "Refund arrival is checked on the billing income-and-expense statement page. "
        "That data is outside the read-only APIs this assistant uses, so the customer "
        "reads it back."
    ),
    "sync-delay": (
        "After an image change, cancellation pages can lag behind for a while. Refresh, "
        "re-enter the page, wait for the state to sync and try again; if the amount "
        "still does not appear, raise a support ticket instead of submitting twice."
    ),
    "transfer-not-supported": (
        "An instance that runs a Marketplace image cannot be transferred to another "
        "account, and the self-service flow refuses it."
    ),
    "transfer-standard-limits": (
        "Standard transfer preconditions, checked by the customer: both accounts belong "
        "to the same verified enterprise subject; the instance stays in the same region, "
        "VPC and zone; account balance is above the documented threshold; Elastic IP "
        "addresses and key pairs are detached first; remaining conditions are listed in "
        "the transfer document."
    ),
    "transfer-workaround": (
        "Workaround for a Marketplace-image instance, executed by the customer: build a "
        "custom image from the source instance, share that image with the target account, "
        "then build a new instance in the target account from the shared image, and "
        "release the old resources only after the new instance is verified."
    ),
    "export-limits": (
        "Image export refuses encrypted custom images, custom images that were built "
        "from a Marketplace image, and Windows Server system images. A single data disk "
        "larger than 2 TiB has to be split before export."
    ),
    "export-workaround": (
        "When export is not possible, move data with a file transfer over Remote Desktop "
        "instead; for Windows instances the documented route is mstsc.exe session drive "
        "redirection."
    ),
    "resource-group-conflict": (
        "Marketplace images are not carried in any resource group; they sit on the "
        "Marketplace side. A RAM user whose permission is scoped to a resource group "
        "fails the forced group-scope check when selecting such an image, even though "
        "the instance itself is inside the authorized group."
    ),
    "authorization-paths": (
        "Two customer-side fixes: (1) build a custom image from the Marketplace image on "
        "another server, move that custom image into the authorized resource group, then "
        "use it; or (2) attach the Marketplace read-and-write policy plus the ECS policy "
        "to the RAM user. Caveat for path 1: if the source image is paid, the derived "
        "custom image keeps generating the image fee."
    ),
    "public-vs-marketplace": (
        "A public image ships a clean operating system only; the customer installs every "
        "software component. A Marketplace image ships preinstalled stacks, so deployment "
        "is faster, but the image is sold by a vendor and carries a licence charge."
    ),
    "language-availability": (
        "Public Windows Server images cover Simplified Chinese and English only. For "
        "other display languages, change the preferred language inside the running "
        "Windows instance. Regional and desktop distributions, such as Traditional "
        "Chinese, UnionTech UOS or Kylin variants, are looked for on the Marketplace side rather "
        "than in the public list."
    ),
    "iso-not-supported": (
        "Mounting an ISO file to install an operating system is not supported. An "
        "operating system that has no public or Marketplace listing has to go through the "
        "custom-image import flow."
    ),
    "legacy-spec-support": (
        "Old-generation Marketplace images can be restricted to specific instance "
        "families; the supported list is sometimes printed in the image name itself. When "
        "the running instance type is outside that list, the boot can stall in the "
        "loading state. Rebuild on a supported family, or select a newer image."
    ),
    "spec-list-visibility": (
        "A machine-readable supported instance-type list is not guaranteed for every "
        "Marketplace image. When the queried fields carry no supported-spec hint, this "
        "assistant says so and points the customer at the Marketplace product detail "
        "page, which is the authoritative list."
    ),
}

# --------------------------------------------- knowledge: per-symptom routing
SYMPTOM_PLAYBOOK = {
    "conversion-blocked": {
        "title": "Billing-method conversion blocked by a Marketplace image",
        "first-question": (
            "Confirm which operation is actually in front of you: changing the instance "
            "billing method, or changing the public IP address / bandwidth billing. The "
            "same message appears in both entries and the answers differ."
        ),
        "rules": ("conversion-blocked", "same-message-two-entries", "conversion-path"),
        "steps": (
            "If the goal really is a billing-method change: stop and back up, change the "
            "image to an eligible public image (exclude Red Hat and SUSE), verify the new "
            "image with this skill, then submit the billing-method conversion.",
            "If the goal is the public IP or bandwidth: leave the instance billing method "
            "alone and convert only the bandwidth billing method in the bandwidth entry.",
            "If the goal is a temporary upgrade only: tell the engineer, because a "
            "temporary upgrade does not require a billing-method conversion.",
        ),
        "risk": ("RISK_CHANGE_OS", "RISK_BILLING_DIFF", "RISK_SNAPSHOT_BILLING"),
        "recheck": (
            "Re-run this script for the same instance and confirm the image is now a "
            "public one before retrying the conversion.",
        ),
        "escalation": (
            "If the conversion page still refuses after the image is public, or if a fee "
            "difference is disputed, collect a screenshot plus the instance identifier "
            "and raise a support ticket. Do not resubmit repeatedly."
        ),
    },
    "boot-stuck-old-image": {
        "title": "Instance stuck loading after a Marketplace image purchase",
        "first-question": (
            "Ask for the instance identifier and the exact image name shown at purchase "
            "time; old Marketplace images often print the supported instance families in "
            "the name."
        ),
        "rules": ("legacy-spec-support", "spec-list-visibility"),
        "steps": (
            "Compare the running instance type with the supported families reported in "
            "the image name (this script prints both).",
            "When they do not intersect: pick a newer image, or purchase on a supported "
            "instance family. Both are customer-side purchase actions.",
            "Ask the customer to recall whether the purchase page showed an "
            "incompatibility warning; that signal is not visible to any API.",
        ),
        "risk": ("RISK_CHANGE_OS", "RISK_SNAPSHOT_BILLING"),
        "recheck": ("Re-run with --instance-id after the change to confirm the new image."),
        "escalation": (
            "If the instance type is supported by the image and boot still stalls, the "
            "cause is outside this tier: hand over to the instance-boot troubleshooting "
            "channel."
        ),
    },
    "image-not-compatible": {
        "title": "Instance type and image support list do not match",
        "first-question": "Collect instance identifier plus image identifier or exact name.",
        "rules": ("legacy-spec-support", "spec-list-visibility", "public-vs-marketplace"),
        "steps": (
            "Print the queried image fields and any supported-family hint.",
            "Guide the customer to the Marketplace product detail page for the "
            "authoritative supported instance family list.",
            "Offer alternatives: a newer image from the same vendor, a public image plus "
            "self-installed software, or a different instance family.",
        ),
        "risk": ("RISK_CHANGE_OS",),
        "recheck": ("After the change, re-run to confirm the image and type combination."),
        "escalation": ("If no compatible combination exists, raise a ticket for the vendor."),
    },
    "renewal-charge-question": {
        "title": "Whether a paid image keeps being charged on renewal",
        "first-question": "Collect the region and instance identifier for the read-only check.",
        "rules": (
            "billing-independent", "renewal-license", "promotion-scope", "free-image-option",
        ),
        "steps": (
            "Confirm from the queried facts whether the instance carries a paid image.",
            "Explain that the licence renews with the instance on the same cycle and that "
            "renewal promotions do not cover the image order.",
            "If the customer wants image charges to stop, guide the change to a free "
            "public image before the next renewal, with the backup gate.",
        ),
        "risk": ("RISK_CHANGE_OS", "RISK_SNAPSHOT_BILLING"),
        "recheck": ("Re-run to confirm the instance now uses a public image."),
        "escalation": (
            "Any dispute about a specific amount or order belongs to the billing channel; "
            "quote the order number found in the billing center, never an amount here."
        ),
    },
    "unexpected-image-charge": {
        "title": "An image charge the customer does not recognise",
        "first-question": "Collect region and instance identifier, then read the image facts.",
        "rules": ("billing-independent", "renewal-license"),
        "steps": (
            "Print the instance identifier, image identifier and image name so the charge "
            "can be attributed to the image actually attached to the instance.",
            "Explain that a preinstalled stack can come from the image itself rather than "
            "from a manual installation.",
            "For the exact amount and order lines, direct the customer to the billing "
            "center; this assistant has no billing visibility.",
        ),
        "risk": (),
        "recheck": ("Re-run after any image change to confirm the new attribution."),
        "escalation": (
            "If the customer still disputes the attribution, the documented outcome is a "
            "support ticket routed to billing; this assistant only hands over the evidence "
            "block and does not submit anything."
        ),
    },
    "duplicate-renewal-order": {
        "title": "Suspected duplicate renewal orders on an image",
        "first-question": "Ask the customer for the order numbers from the billing center.",
        "rules": ("billing-independent", "promotion-scope"),
        "steps": (
            "Restate the order numbers back to the customer so the scope is unambiguous.",
            "Explain that order-level facts are outside the read-only APIs used here.",
        ),
        "risk": (),
        "recheck": (),
        "escalation": (
            "Hand over to the Marketplace team through a support ticket carrying both "
            "order numbers. No cancellation is performed by this assistant."
        ),
    },
    "refund-blocked": {
        "title": "Cancellation or refund blocked by a paid image",
        "first-question": "Collect the instance identifier and confirm the current image.",
        "rules": (
            "unsubscribe-precondition", "refund-image-fee",
            "renewal-order-cancellation-order", "sync-delay", "refund-tracking",
        ),
        "steps": (
            "Read-only check whether a paid image is still attached; if yes, the image "
            "change comes first.",
            "Explain that a paid image fee is not refundable once associated with an "
            "instance, and that a not-yet-effective renewal order needs the specialist "
            "flow, instance order first and the image order follows automatically.",
            "Point at the self-service renewal cancellation entry and the income-and-"
            "expense statement page for the customer to use.",
            "Read out the confirmation checklist: refund reason, exact instance "
            "identifier, backup confirmed, current expiry date understood, amount shown "
            "on the page confirmed.",
        ),
        "risk": ("RISK_IRREVERSIBLE", "RISK_CHANGE_OS", "RISK_SNAPSHOT_BILLING"),
        "recheck": (
            "After the image change, re-run to confirm the public image is attached before "
            "the customer retries the cancellation page."
        ),
        "escalation": (
            "Amount confirmation, authorization cards, approval and arrival of money are "
            "human-channel steps. This assistant never claims a cancellation was done."
        ),
    },
    "refund-amount-missing": {
        "title": "Cancellation page shows no amount after an image change",
        "first-question": "Confirm the current attached image with the read-only check.",
        "rules": ("unsubscribe-precondition", "sync-delay"),
        "steps": (
            "Verify with this skill that the instance really is on a public image now.",
            "If it is, the likely cause is state propagation lag: refresh, re-enter the "
            "page, wait and try again later.",
            "If the amount is still absent, raise a support ticket rather than submitting "
            "a partial request.",
        ),
        "risk": ("RISK_IRREVERSIBLE",),
        "recheck": ("Re-run to confirm the attached image type."),
        "escalation": ("Billing channel for anything amount-related."),
    },
    "payment-failed-on-image-change": {
        "title": "Payment fails while selecting a Marketplace image on disk change",
        "first-question": "Collect the instance identifier and read its status.",
        "rules": ("stopped-required",),
        "steps": (
            "Read the instance status with this skill; the change flow requires Stopped.",
            "Guide the customer to stop the instance, confirm the backup, then resubmit "
            "the image order payment.",
            "Point at the operating-system change document for the exact entry.",
        ),
        "risk": ("RISK_CHANGE_OS", "RISK_SNAPSHOT_BILLING"),
        "recheck": ("Re-run with the status check to confirm Stopped before retrying."),
        "escalation": (
            "If the status is Stopped and payment still fails, collect the order snapshot "
            "and hand over to billing support."
        ),
    },
    "transfer-not-supported": {
        "title": "Cross-account transfer refused for a Marketplace-image instance",
        "first-question": "Read the image facts to confirm the block reason.",
        "rules": (
            "transfer-not-supported", "transfer-standard-limits", "transfer-workaround",
            "export-limits",
        ),
        "steps": (
            "State the rule, then read out the standard transfer preconditions so the "
            "customer can self-check.",
            "Offer the custom-image route: build a custom image on the source instance, "
            "share it with the target account, rebuild in the target account, verify, then "
            "release the source.",
            "Warn that a custom image derived from a paid image keeps generating the image "
            "fee, and that such a derived image is outside the export scope.",
        ),
        "risk": ("RISK_SNAPSHOT_BILLING", "RISK_IRREVERSIBLE"),
        "recheck": (
            "Re-run against the new instance in the target account to confirm the image "
            "and region are as expected."
        ),
        "escalation": (
            "Account verification subject and balance questions belong to the account "
            "channel; this assistant does not evaluate eligibility."
        ),
    },
    "export-not-supported": {
        "title": "Image export or self-managed migration refused",
        "first-question": "Confirm the image source and the operating-system type.",
        "rules": ("export-limits", "export-workaround", "transfer-workaround"),
        "steps": (
            "Read out the export scope: encrypted custom images, custom images derived "
            "from a Marketplace image and Windows Server system images are all outside it.",
            "When both blocking conditions apply, switch the goal from image export to "
            "data backup and guide file transfer over Remote Desktop.",
            "For Linux images that only exceed the disk limit, split the large data disk "
            "first.",
        ),
        "risk": ("RISK_SNAPSHOT_BILLING",),
        "recheck": ("Ask the customer to verify file sizes locally after the transfer."),
        "escalation": (
            "A supported migration path for that combination does not exist; do not "
            "improvise one, and say so plainly."
        ),
    },
    "no-permission-on-image-change": {
        "title": "Permission error while selecting a community or Marketplace image",
        "first-question": (
            "Ask for the request identifier from the error message and whether the RAM "
            "user's permission is scoped to a resource group."
        ),
        "rules": ("resource-group-conflict", "authorization-paths"),
        "steps": (
            "Explain the cause: the instance is inside the authorized group but the "
            "Marketplace image has no group membership, so the group-scope check fails.",
            "Path 1: build a custom image from the Marketplace image on another server, "
            "move it into the authorized resource group, then use it.",
            "Path 2: have an administrator attach the Marketplace policy to the RAM user.",
            "Both paths are performed by an administrator in the console; the paid-image "
            "caveat applies to path 1.",
        ),
        "risk": (),
        "recheck": (
            "Retry the operation as the RAM user; this assistant cannot read another "
            "account's or another identity's permission setup."
        ),
        "escalation": (
            "Designing the resource-group and RAM model is a separate permissions topic; "
            "hand over if the customer wants a review rather than this fix."
        ),
    },
    "docker-pull-failure": {
        "title": "Container image pull failure (not this tier)",
        "first-question": (
            "Confirm whether the word image refers to a Docker container image rather "
            "than an ECS Marketplace image."
        ),
        "rules": (),
        "steps": (),
        "risk": (),
        "recheck": (),
        "escalation": (
            "Hand over to the container and network support channel. This assistant does "
            "not edit daemon configuration and does not submit tickets."
        ),
    },
    "image-software-failure": {
        "title": "Third-party software inside the image misbehaving (not this tier)",
        "first-question": (
            "Confirm the image itself boots and the failure is inside the preinstalled "
            "software."
        ),
        "rules": (),
        "steps": (
            "Ask the customer to run the vendor's read-only checks over a remote "
            "connection and paste the output back.",
            "Direct the customer to the vendor support entry on the Marketplace product "
            "page.",
        ),
        "risk": (),
        "recheck": (),
        "escalation": (
            "Connection parameters and in-guest state are outside this read-only "
            "assistant; hand over to the remote-connection or instance-diagnostics "
            "channel."
        ),
    },
    "iso-install-request": {
        "title": "ISO installation or bring-your-own operating system (not this tier)",
        "first-question": "Confirm which operating system the customer needs and its license.",
        "rules": ("iso-not-supported",),
        "steps": (
            "State that ISO mounting is unsupported.",
            "Route to the custom-image import flow for an operating system with no "
            "listing.",
        ),
        "risk": (),
        "recheck": (),
        "escalation": (
            "Hand over to the image import channel for the operation itself; this "
            "assistant only gives the rule."
        ),
    },
    "unrelated-boot-failure": {
        "title": "Boot or network fault unrelated to the image source (not this tier)",
        "first-question": "Read the image facts to rule out a Marketplace image cause.",
        "rules": (),
        "steps": ("If the image is public, say the Marketplace tier does not apply here."),
        "risk": (),
        "recheck": (),
        "escalation": (
            "Hand over to the instance-boot or public-network troubleshooting channel."
        ),
    },
}

# ------------------------------------------------- knowledge: intent mapping
INTENT_SYMPTOMS = {
    "selection": ("image-not-compatible", "boot-stuck-old-image", "iso-install-request"),
    "billing": ("renewal-charge-question", "unexpected-image-charge",
                "duplicate-renewal-order"),
    "conversion": ("conversion-blocked",),
    "refund": ("refund-blocked", "refund-amount-missing"),
    "system-disk": ("payment-failed-on-image-change",),
    "transfer": ("transfer-not-supported",),
    "export": ("export-not-supported",),
    "authorization": ("no-permission-on-image-change",),
    "inventory": (),
    "triage": ("docker-pull-failure", "image-software-failure", "iso-install-request",
               "unrelated-boot-failure"),
}

# ------------------------------------------------------------ selection rules
SELECTION_RULES = (
    ("Public image", RULES["public-vs-marketplace"]),
    ("Paid image on renewal", RULES["renewal-license"]),
    ("Language availability", RULES["language-availability"]),
    ("ISO request", RULES["iso-not-supported"]),
    ("Supported instance families", RULES["legacy-spec-support"]),
    ("Spec list visibility", RULES["spec-list-visibility"]),
)

# Risk keys referenced by name from SYMPTOM_PLAYBOOK, resolved by the entry script.
RISK_BLOCKS = {
    "RISK_CHANGE_OS": RISK_CHANGE_OS,
    "RISK_SNAPSHOT_BILLING": RISK_SNAPSHOT_BILLING,
    "RISK_IRREVERSIBLE": RISK_IRREVERSIBLE,
    "RISK_BILLING_DIFF": RISK_BILLING_DIFF,
}

# ---------------------------------------------------- facts the APIs can't see
CUSTOMER_SELF_CHECK_ITEMS = (
    "Whether the purchase page displayed an incompatibility warning at order time.",
    "What the conversion, cancellation and refund pages actually render, including "
    "amounts.",
    "State inside the guest: preinstalled software behaviour, local client tools, "
    "container runtime configuration.",
    "Whether a stack was installed manually or shipped with the image, when the "
    "customer disputes the attribution.",
    "Current resource-group and RAM configuration seen by another identity.",
    "Order counts, invoice quota and refund arrival.",
)

DEGRADE_HINTS = (
    "Region scope: Describe APIs only see resources of the current credential account "
    "in the requested region. Ask the customer to switch region or account and check "
    "again.",
    "Empty result is reported as not visible, never as not present.",
    "No support-family hint in the queried image fields means the compatibility answer "
    "moves to the Marketplace product detail page.",
)
