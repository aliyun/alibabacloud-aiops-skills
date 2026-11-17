#!/usr/bin/env python3
"""
_constants.py -- embedded static data for ECS console resource lookup
=====================================================================
SECURITY: This skill is strictly READ-ONLY. Authentication is resolved by the
aliyun CLI default credential chain only. This module never reads, prints,
caches or passes any key material, and contains no credential literals.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
every static table this skill relies on (region sweep list, status semantics,
console entry map, concept glossary, button-gating rules, error cards, handoff
routes) is embedded here as Python constants. No data files exist in scripts/.

Knowledge provenance: root causes, console paths and URLs below were distilled
from real support-ticket conversations and the verified console links they
contain (requirements doc sections 2, 4 and 6). Anything without a ticket or
api-info source is deliberately absent -- never fabricated.
"""

# ---------------------------------------------------------------------------
# Skill identity and observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-console-resource-lookup"

# User-Agent attached to every CLI call of a run (observability rule SA-2.11).
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill-name}/{session-id}"

# ---------------------------------------------------------------------------
# API metadata (verified api-info surface for this tier)
# ---------------------------------------------------------------------------

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# Central, region-less STS endpoint.
STS_ENDPOINT = "sts.aliyuncs.com"

# ---------------------------------------------------------------------------
# Timeouts and limits (MUST 7.6.1: every CLI call carries a timeout)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60          # per-call timeout seconds, every subprocess run
CLI_TIMEOUT = 60              # alias used by callers building one command
STS_TIMEOUT = 30              # identity pre-flight is a single small call
PAGE_SIZE = 50                # DescribeInstances page size
MAX_PAGES = 10                # pagination guardrail per region+filter query
MAX_SWEEP_REGIONS = 40        # guardrail on --regions overrides
MAX_INSTANCE_IDS = 10         # status cross-check batch cap per API call

# ---------------------------------------------------------------------------
# Region sweep list (cross-region exhaustive lookup: core action C1)
# ---------------------------------------------------------------------------
# Embedded snapshot of commonly available public ECS region ids. The list is a
# convenience default, not an authority: `--region-hint` is queried FIRST and
# `--regions` replaces or extends the sweep, and every report states the exact
# list that was queried (no silent scope claims). Regions retired for an
# account answer with an API error that the sweep records and continues past.
DEFAULT_SWEEP_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-qingdao",
    "cn-zhangjiakou", "cn-huhehaote", "cn-wulanchabu", "cn-heyuan",
    "cn-guangzhou", "cn-shenzhen", "cn-chengdu", "cn-nanjing",
    "cn-fuzhou", "cn-wuhan-lr", "cn-hongkong", "ap-northeast-1",
    "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
    "ap-southeast-3", "ap-southeast-5", "ap-southeast-6",
    "ap-southeast-7", "us-east-1", "us-west-1", "eu-central-1",
    "eu-west-1", "me-east-1", "me-central-1",
]

# ---------------------------------------------------------------------------
# Instance status semantics (C2: control-plane reading vs console display)
# ---------------------------------------------------------------------------
# DescribeInstances / DescribeInstanceStatus return the control-plane
# (management) state. A console display is a view of that same state; the two
# agree once the right region/account view is selected. OS-level reality
# (booted, services up, disk mounted inside the OS) is a SECOND layer the
# cloud state does not prove.
INSTANCE_STATUS_MEANING = {
    "Pending": "created, waiting for the start workflow to take it over",
    "Running": "control plane reports running; it does NOT prove the OS, a "
               "service, or a mounted disk is usable inside the instance",
    "Starting": "start in progress",
    "Stopping": "stop in progress",
    "Stopped": "stopped (a stopped subscription instance still bills)",
}

# A banner or card in the console can lag the control-plane state after an
# appeal/release is processed on the security side; the queried status is the
# objective anchor, the banner is display-side residue to verify there.
STATUS_SYNC_NOTE = (
    "Console banners and security/disposal reminders can lag the control-plane "
    "state that DescribeInstanceStatus reports; treat the queried status as "
    "the objective reading and verify any lingering banner in the console "
    "module that owns it."
)

# ---------------------------------------------------------------------------
# Charge-type gating (why buttons exist or do not: A6 evidence)
# ---------------------------------------------------------------------------
CHARGE_TYPE_NOTE = {
    "PrePaid": "subscription (package). Console actions gated by it: a "
               "subscription data disk cannot be detached until its billing "
               "method is converted to pay-as-you-go first; unsubscription "
               "eligibility is a commercial rule, not an API finding.",
    "PostPaid": "pay-as-you-go. Detach and release actions exist in the "
                "console but are customer-side, destructive, and never "
                "executed by this skill.",
}

# LockReason semantics (returned by DescribeInstances when locked).
LOCK_REASON_MEANING = {
    "Financial": "locked for overdue payment; settle the balance first, "
                 "resources may enter the expiry/release timeline afterwards",
    "Security": "locked by a security disposal; the disposal itself is owned "
                "by the security module / security console, not by ECS",
}

# ---------------------------------------------------------------------------
# Intake: the minimum question card (anti-pattern: ticket T-19C9B029 closed
# unanswered because "cannot find the entry" named no function at all)
# ---------------------------------------------------------------------------
INTAKE_QUESTIONS = [
    "Which resource is missing: instance, disk, snapshot, image, or a console "
    "page/entry?",
    "The exact identifier if known (instance id i-..., disk id d-..., "
    "snapshot id s-...), or the instance name / IP address.",
    "Which region does the console currently show in its top-left region "
    "switcher, and did the resource live in another region?",
    "Are there several accounts (different login phone numbers / member "
    "accounts), and is the resource possibly under one you are not logged "
    "into right now?",
    "Is the console the ECS console at all, or could the resource be a "
    "Simple Application Server (SAS/SWAS), an order, or another product?",
    "For a missing button/entry: the exact button text or menu you expected, "
    "the device (PC browser or phone app), and any error text shown.",
]

# Asked when the sweep finds nothing anywhere (A1 residual causes).
NOT_FOUND_FOLLOWUPS = [
    "Wrong account: buy and creation actions under another account place the "
    "resource in that account's console; log out and check each account.",
    "Wrong product: Simple Application Server instances never appear in the "
    "ECS instance list -- open the SAS console instead.",
    "Already expired or released: resources past their expiry enter the "
    "release timeline and disappear from lists; this is a lifecycle question "
    "(see the handoff route), not a lookup failure.",
    "Auto snapshot policies paused by overdue payment plus short auto-snapshot "
    "retention can leave 'missing snapshots' with nothing left to find.",
    "Resource group filter: a resource-group filter stuck in the console "
    "hides resources outside it; switch the view to the account scope.",
]

# ---------------------------------------------------------------------------
# Console entry map (C3 data source: ONLY links actually verified in real
# ticket conversations; requirements doc section 4.2)
# ---------------------------------------------------------------------------
ENTRY_MAP = {
    "ecs-instance-list": {
        "title": "ECS instance list (one region at a time)",
        "say": "The instance list always shows ONE region: switch the region "
               "in the top-left corner; the list is region-scoped, not "
               "account-global.",
        "url": "https://ecs.console.aliyun.com/server/region/cn-hangzhou#/",
        "tickets": ["T-69E628E3", "T-804A0640"],
    },
    "ecs-snapshot-list": {
        "title": "ECS snapshot list",
        "say": "Snapshots are also region-scoped: check each region the "
               "source disk lived in.",
        "url": "https://ecs.console.aliyun.com/snapshot",
        "tickets": ["T-D52AE555"],
    },
    "ecs-security-groups": {
        "title": "ECS security group list",
        "say": "Security groups live per region and per VPC.",
        "url": "https://ecs.console.aliyun.com/securityGroup/region/cn-hangzhou",
        "tickets": ["T-A250313A"],
    },
    "purchasable-region-spec": {
        "title": "Purchasable regions and instance types for this account",
        "say": "When a region is not selectable on the buy page, check which "
               "regions/specs the current account may buy before assuming a "
               "console bug; real-name verification status and overdue "
               "balance also gate visibility.",
        "url": "https://ecs-buy.aliyun.com/instanceTypes/#/instanceTypeByRegion",
        "tickets": ["T-8D8F2AD9"],
    },
    "ram-console": {
        "title": "RAM console overview (users, roles, policies)",
        "say": "RAM users are created in the RAM console, not in the ECS "
               "console; an ECS-side search for a RAM user always comes back "
               "empty.",
        "url": "https://ram.console.aliyun.com/overview?activeTab=overview",
        "tickets": ["T-8AA82DFC"],
    },
    "order-list": {
        "title": "Order list (billing center)",
        "say": "Purchases such as saved plans appear as orders here, not in "
               "the ECS console.",
        "url": "https://billing-cost.console.aliyun.com/order/list",
        "tickets": ["T-DF87AF28"],
    },
    "refund-page": {
        "title": "Unsubscription / refund self-service",
        "say": "Refunds and unsubscription run through the billing self-"
               "service channel and remain commercial processes; this skill "
               "only navigates, it never executes them.",
        "url": "https://billing-cost.console.aliyun.com/refund/refund",
        "tickets": ["T-B2672FDF"],
    },
    "contract-management": {
        "title": "Contract management (server access agreement for ICP "
                 "filing)",
        "say": "The ICP-filing 'server access agreement' is a service "
               "contract, generated in the billing console, not an ECS page.",
        "url": "https://billing-cost.console.aliyun.com/contract/manage",
        "tickets": ["T-2000646E"],
    },
    "eip-console": {
        "title": "EIP list (VPC console)",
        "say": "Elastic IP addresses are managed in the VPC console, not the "
               "ECS console.",
        "url": "https://vpc.console.aliyun.com/eip/cn-shenzhen/eips",
        "tickets": ["T-AB34E2B9"],
    },
    "dns-console": {
        "title": "Alibaba Cloud DNS domain list",
        "say": "A domain is never 'bound' to a server to unbind; pointing a "
               "domain at or away from an instance means editing DNS "
               "resolution records here.",
        "url": "https://dns.console.aliyun.com/#/dns/domainList",
        "tickets": ["T-F66F330B"],
    },
    "dns-probe": {
        "title": "Public DNS propagation probe",
        "say": "Check whether a resolution change is already visible "
               "publicly before suspecting the server.",
        "url": "https://boce.aliyun.com/detect/dns",
        "tickets": ["T-F66F330B"],
    },
    "wanxiaozhi-console": {
        "title": "Wanxiaozhi website builder console",
        "say": "Domain binding for Wanxiaozhi-built sites happens in the "
               "site's own console, not in ECS.",
        "url": "https://dc.console.aliyun.com/next/index#/xiaozhi",
        "tickets": ["T-AFD53C57"],
    },
}

# ---------------------------------------------------------------------------
# Official help docs, each cited by a real ticket conversation (requirements
# doc section 4.2 groups 1-2). Never add a URL that is not in this set.
# ---------------------------------------------------------------------------
OFFICIAL_DOCS = {
    "attach-a-data-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk",
    "init-linux-data-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/initialize-a-data-disk-"
        "whose-size-does-not-exceed-2-tib-on-a-linux-instance",
    "create-a-snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "snapshot-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview/",
    "snapshot-billing":
        "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "delete-a-snapshot":
        "https://help.aliyun.com/document_detail/128131.html",
    "reinitialize-a-system-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk",
    "create-disk-from-snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot",
    "detach-a-data-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk",
    "switch-disk-billing-method":
        "https://help.aliyun.com/zh/ecs/switch-the-billing-method-of-a-disk",
    "release-an-instance":
        "https://help.aliyun.com/zh/ecs/user-guide/release-an-instance",
    "reset-instance-login-password":
        "https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-"
        "of-an-instance",
    "bill-settlement-policy":
        "https://help.aliyun.com/zh/user-center/product-overview/updates-on-"
        "the-bill-settlement-policy",
    "ecs-purchase-guide": "https://help.aliyun.com/document_detail/2361102.html",
    "regions-and-zones": "https://help.aliyun.com/document_detail/188196.html",
    "purchase-getting-started":
        "https://help.aliyun.com/document_detail/2983142.html",
    "eip-apply": "https://help.aliyun.com/zh/eip/apply-for-new-eips",
    "eip-overview": "https://help.aliyun.com/zh/eip/elastic-ip-address",
    "ipv6-vpc-step":
        "https://help.aliyun.com/zh/ecs/user-guide/step-1-create-a-vpc-that-"
        "supports-ipv6-addressing",
    "ipv6-billing":
        "https://help.aliyun.com/zh/ipv6-gateway/product-overview/billing-rules",
    "dns-modify-record": "https://help.aliyun.com/zh/dns/modify-a-dns-record",
    "dns-manage-records":
        "https://help.aliyun.com/zh/dns/pubz-manage-resolution-records",
    "wanxiaozhi-bind-domain":
        "https://help.aliyun.com/document_detail/2928165.html",
    "icp-filing-overview":
        "https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/"
        "icp-filing-application-overview",
    "unsubscription-rules":
        "https://help.aliyun.com/zh/user-center/cancel-subscription/",
    "refund-destinations":
        "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations",
    "refund-rules-detail": "https://help.aliyun.com/document_detail/116043.html",
    "das-billing-details":
        "https://help.aliyun.com/zh/das/product-overview/billing-details",
    "instance-detail-file-transfer":
        "https://help.aliyun.com/zh/ecs/user-guide/upload-and-download-files-"
        "on-the-instance-details-page",
    "console-send-remote-command":
        "https://help.aliyun.com/zh/ecs/user-guide/send-remote-commands",
    "batch-operations":
        "https://help.aliyun.com/zh/ecs/user-guide/batch-operation-of-ecs-"
        "instances-through-the-ecs-console",
}

# ---------------------------------------------------------------------------
# Concept glossary (customer word -> what the product actually calls it)
# ---------------------------------------------------------------------------
CONCEPT_MAP = [
    ("'shutdown/turn-off button' for good", "The product term is RELEASE "
     "(destroying the instance, data unrecoverable). There is no 'shutdown "
     "forever' button.", "Instance list, More menu; manual steps only"),
    ("'disk is in use but my system cannot see it'", "Console 'In Use' means "
     "the cloud-side attachment finished. Partition + file system + mount "
     "inside the OS are a second, separate layer.",
     "handoff: in-guest disk steps, snapshot-first reminder"),
    ("'unbind the domain from the server'", "Domains are not bound to "
     "servers in ECS; point the name by editing DNS resolution records.",
     "Alibaba Cloud DNS console"),
    ("'FTP management entry in the console'", "ECS ships no FTP control "
     "panel; an FTP server is software installed inside the instance. For "
     "console file transfer use the instance-detail upload/download "
     "feature.", "official doc instance-detail-file-transfer"),
    ("'logical partition is a second disk'", "One cloud disk can carry "
     "several partitions; partition count does not equal disk count.",
     "handoff: in-guest disk steps"),
    ("'lightweight server' listed in ECS", "Simple Application Server is a "
     "different product with its own console; it never appears in the ECS "
     "instance list.", "SAS/SWAS console"),
    ("'saved plan / resource package' missing in ECS", "Orders of billing "
     "products are not ECS resources; look in the billing order list.",
     "billing center order list"),
]

# ---------------------------------------------------------------------------
# Button/entry gating rules (A6/B4/B6: the entry is really absent because a
# condition holds; every row carries its ticket source)
# ---------------------------------------------------------------------------
GATE_RULES = [
    {
        "symptom": "detach button missing for a data disk already unmounted "
                   "in the OS",
        "gate": "the disk is subscription (PrePaid); subscription data disks "
                "expose detach only after billing conversion",
        "unlock": "convert the disk billing method to pay-as-you-go, then "
                  "detach, then release; each step is customer-side",
        "docs": ["switch-disk-billing-method", "detach-a-data-disk"],
        "source": "T-5E9C11A3",
    },
    {
        "symptom": "re-initialize system disk entry not found",
        "gate": "deep menu + wording drift between console versions ('disk' "
                "vs 'system disk')",
        "unlock": "instance list, More menu, disk and image group; requires "
                  "the instance stopped; wipes the system disk irreversibly, "
                  "manual snapshot first",
        "docs": ["reinitialize-a-system-disk", "create-a-snapshot"],
        "source": "T-69E628E3",
    },
    {
        "symptom": "unsubscription blocked, message asks to switch to a "
                   "public image",
        "gate": "subscription instances on non-public (custom/marketplace) "
                "images cannot self-unsubscribe directly",
        "unlock": "image change or commercial handling; unsubscription "
                  "eligibility itself is a commercial process",
        "docs": ["unsubscription-rules"],
        "source": "T-C3D40EB0 (ticket summary; original dialog pending "
                  "re-pull -- treat wording as reported, not quoted)",
    },
    {
        "symptom": "feature present in help docs but missing in the phone "
                   "app console",
        "gate": "mobile app renders a reduced feature set",
        "unlock": "repeat the action in a PC browser on the ECS web console",
        "docs": [],
        "source": "T-8BBBBAF4 / T-75C85AC2",
    },
    {
        "symptom": "a region is not selectable on the buy page",
        "gate": "per-account purchasability; real-name status, overdue "
                "balance and account benefits change what is visible",
        "unlock": "check the purchasable region/spec page first; if the "
                  "region sells but the account cannot see it, contact sales "
                  "via the ticket channel",
        "docs": ["purchasable-region-spec", "regions-and-zones"],
        "source": "T-8D8F2AD9",
    },
    {
        "symptom": "reset-password option unavailable on a running instance",
        "gate": "password reset may require the Cloud Assistant agent or a "
                "reboot; some images lack the agent",
        "unlock": "install/verify the agent or use the reboot-confirm flow; "
                  "credential repair itself belongs to the login-credential "
                  "route",
        "docs": ["reset-instance-login-password"],
        "source": "T-04713EBF",
    },
]

# ---------------------------------------------------------------------------
# Error signal cards (ONLY strings that literally appeared in tickets;
# requirements doc section 6.3)
# ---------------------------------------------------------------------------
ERROR_CARDS = {
    "imageid-not-exist": {
        "signal": "The specified ImageId does not exist",
        "meaning": "the chosen image is not available for that region / "
                   "instance type combination at order time",
        "steps": "On the buy page switch to another image and retry; if the "
                 "page offers no image switcher, reload the custom/blank "
                 "purchase form and pick the image there.",
        "source": "T-D3CF844C (dialog)",
    },
    "nopermission-ram": {
        "signal": "NoPermission.RAM",
        "meaning": "a RAM authorization failed; the message names the "
                   "authorization action (seen with ecs:ListTagResources / "
                   "ecs:DescribeInstances)",
        "steps": "Read the principal and the account the request id belongs "
                 "to BEFORE changing any policy. Same-account RAM user: "
                 "grant a managed ECS read policy and hand the policy "
                 "question to the ram-policy route. Request id owned by a "
                 "third-party ecosystem platform (separate console and "
                 "ticket system): submit there -- the Alibaba Cloud side "
                 "cannot act for it.",
        "source": "T-1D79BB54 (dialog)",
    },
    "unsubscribe-public-image": {
        "signal": "reported text: unsubscription refused unless the instance "
                  "uses a public image",
        "meaning": "non-public-image subscription instances are excluded "
                   "from self-unsubscription",
        "steps": "explain the rule, show the image-change entry location, "
                 "route the eligibility computation to the human commercial "
                 "channel.",
        "source": "T-C3D40EB0 (summary only; wording pending dialog re-pull)",
    },
    "account-call-rejected": {
        "signal": "reported text: this account does not support the call",
        "meaning": "the request id belongs to a different account or system",
        "steps": "use the request id to attribute the call; do not change "
                 "policies on an account that never issued it.",
        "source": "T-1D79BB54 (agent's rephrasing in dialog)",
    },
}

# ---------------------------------------------------------------------------
# Navigation knowledge topics (pure-knowledge answers, each ticket-grounded)
# ---------------------------------------------------------------------------
NAV_TOPICS = {
    "region-scoped-views": {
        "question": "I cannot find my instance / disk / snapshot anywhere.",
        "answer": "Every ECS console list is scoped to one region and one "
                  "resource-group view at a time. The most common ticket "
                  "answer is simply: switch the region in the top-left "
                  "switcher to the region the resource was created in. This "
                  "skill replaces the guesswork by sweeping Describe-"
                  "Instances across regions and reporting exactly where the "
                  "resource exists.",
    },
    "account-and-product-views": {
        "question": "I swept everywhere and the instance is still not there.",
        "answer": "Two views remain: the ACCOUNT view (resources created "
                  "under a different login / member account never appear; "
                  "ticket T-CA25DD32) and the PRODUCT view (Simple "
                  "Application Server instances live in the SAS console, "
                  "ticket T-E847A8C0; saved-plan and similar purchases are "
                  "orders in the billing center, ticket T-DF87AF28). A "
                  "resource that expired and passed its retention window is "
                  "released and unrecoverable by lookup -- that is the "
                  "expiry/lifecycle conversation, not a visibility bug.",
    },
    "snapshot-region-ambiguity": {
        "question": "My snapshots are gone; is it the region?",
        "answer": "Both causes coexist in real tickets: snapshots are "
                  "region-scoped (so the wrong region looks 'empty', ticket "
                  "T-C8FA71CA customer wording), AND overdue payment pauses "
                  "auto-snapshot policies while retained auto-snapshots are "
                  "released after their short window. Run the cross-region "
                  "sweep to separate 'elsewhere' from 'gone', then check the "
                  "overdue state.",
    },
    "two-layer-disk-state": {
        "question": "The console says the disk is In Use but df cannot see "
                    "it.",
        "answer": "Cloud-side attach and OS-side availability are two "
                  "layers: the console proved only the first. The instance "
                  "still needs partition / file system / mount (a fresh "
                  "disk) or partition extension (a resized disk). This skill "
                  "is read-only and does not touch the instance OS; it "
                  "quotes the cloud reading, names the missing OS layer, "
                  "recommends a manual snapshot first, and hands the "
                  "customer the official init/expand docs.",
    },
    "grey-button-causes": {
        "question": "The button is greyed out / does not exist.",
        "answer": "Real ticket causes cluster as: billing mode gates the "
                  "action (subscription disk detach), image type gates it "
                  "(unsubscription), terminal form gates it (phone app "
                  "reduced set), instance capability or agent state gates "
                  "it (password reset), or the console-side step is already "
                  "done so nothing is pending (grey 'configure mount "
                  "point'). Read the resource's actual fields first, then "
                  "match the gate; do not conclude 'bug'.",
    },
    "punish-banner-stale": {
        "question": "The console still shows a security/violation reminder "
                    "but the disposal is over.",
        "answer": "Disposal reminders are display data owned by the security "
                  "side; the ECS control-plane status is the objective "
                  "anchor. Query the instance status, show it, and route "
                  "the banner itself to the security management console -- "
                  "ECS APIs cannot read or clear disposal records.",
    },
    "idc-address-policy": {
        "question": "Where is my server's physical machine room address?",
        "answer": "The console does not expose physical locations by policy; "
                  "the address is released through manual channels after a "
                  "purpose review, and no stamped file exists (ticket "
                  "T-3F5A3E75). The ICP-filing 'server access agreement' "
                  "need is met by the service contract in the billing "
                  "console instead (ticket T-2000646E).",
    },
    "commercial-boundary": {
        "question": "Refund me / cancel the instance / fix this bill.",
        "answer": "Refunds, unsubscription eligibility, campaign and "
                  "same-person benefit disputes, and invoice work are "
                  "commercial processes: navigate to the billing self-"
                  "service entries (verified URLs in the entry map) and "
                  "state that the execution itself is human-owned. This "
                  "skill never simulates or performs them; tickets "
                  "T-DF87AF28 / T-B2672FDF / T-557197AF / T-B1F0887B all "
                  "closed that way.",
    },
    "third-party-console-scope": {
        "question": "I cannot find the entry -- is it in the ECS console?",
        "answer": "A large share of 'missing entry' tickets are entries in "
                  "ANOTHER product's console: RAM users (ram.console), DNS "
                  "records (dns.console), EIPs (vpc.console), Wanxiaozhi "
                  "sites (dc.console), DAS bills (das docs), SAS "
                  "(SWAS). Identify the owning product, give the verified "
                  "entry link, and stop there -- inside another product's "
                  "console this skill does not diagnose (third-party "
                  "ecosystem platforms run their own ticket systems, ticket "
                  "T-1D79BB54).",
    },
}

# ---------------------------------------------------------------------------
# Handoff routes (C4/C6). Targets are ONLY skills that verifiably exist as
# same-batch skills or were named by the dedup data; anything else goes to
# human/console channels. Route wording lives in references/console-resource-lookup__handoff-matrix.md.
# ---------------------------------------------------------------------------
HANDOFF_ROUTES = [
    {
        "pattern": "disk attached / expanded but the OS still does not see "
                   "or cannot use the capacity "
                   "磁盘挂载后系统看不到 扩容后容量没变 磁盘不可见 数据盘看不到",
        "target": "area:disk-expand-diagnosis / "
                  "area:disk-attach-os-visibility",
        "extra": "cloud evidence + snapshot-first reminder + init/expand docs",
    },
    {
        "pattern": "instance will not start / stuck in Starting or Stopping "
                   "实例无法启动 卡在启动 开机卡住 实例启动不了",
        "target": "area:instance-state-diagnosis",
        "extra": "report only the control-plane state read; the state-"
                 "machine fault is another area",
    },
    {
        "pattern": "login password / keypair repair after the instance was "
                   "found "
                   "登录密码 密钥对 重置密码 密码修复",
        "target": "area:login-credential-repair",
        "extra": "navigation to reset entry meanwhile",
    },
    {
        "pattern": "RAM policy authoring, policy gaps, NoPermission tuning "
                   "权限策略 无权限 授权策略 RAM策略",
        "target": "area:ram-policy-diagnosis",
        "extra": "this skill only names the missing read action",
    },
    {
        "pattern": "CLI / SDK command construction and usage "
                   "命令行 CLI命令 SDK用法 命令构造",
        "target": "alibabacloud-cli-guidance",
        "extra": "boundary skill from the online dedup scan",
    },
    {
        "pattern": "expiry, release timeline, data retention, 'brought back' "
                   "questions "
                   "到期 释放 数据保留 找回数据 保留期",
        "target": "human: submit a ticket to the lifecycle queue; navigate "
                  "release/billing docs",
        "extra": "this skill only answers 'does it exist right now'",
    },
    {
        "pattern": "refund / unsubscription / campaign eligibility / invoice "
                   "退款 退订 活动资格 发票",
        "target": "human: billing self-service entries + support ticket",
        "extra": "commercial actions are never executed here",
    },
    {
        "pattern": "physical machine-room address "
                   "机房地址 物理机房 机房位置",
        "target": "human: reviewed disclosure channel only",
        "extra": "console never shows it by policy",
    },
]

# ---------------------------------------------------------------------------
# DescribeAvailableResource usage note (buy-page visibility, C5)
# ---------------------------------------------------------------------------
# DestinationResource values accepted by the verified parameter surface; keep
# to the common ones the tickets actually discuss.
DESTINATION_RESOURCES = [
    "Zone", "InstanceType", "SystemDisk", "DataDisk", "Network",
    "ReservedInstance", "DDH", "ElasticStorage",
]

AVAILABILITY_NOTE = (
    "DescribeAvailableResource reports what the account may CREATE in the "
    "given region for the destination resource; it is queried here only to "
    "answer 'is this region/spec visible to me at all'. It never books, "
    "orders or changes anything, and purchasability of campaign prices is "
    "outside its scope."
)
