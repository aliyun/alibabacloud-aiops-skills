#!/usr/bin/env python3
"""
_constants.py -- endpoints, limits, and embedded rule data for
area:spec-change-purchase
===========================================================================
SECURITY: This module contains static constants only. It never handles
credentials (authentication is resolved exclusively by the aliyun CLI default
credential chain) and performs no I/O.

Per platform rule 1.1.2, scripts/ may only contain executable code, so all
reference data used by the assessment flow (mandatory customer notices, the
error-string triage table, the change-rule guidance lines) is embedded here
as Python constants. The full readable versions live in references/*.md.
"""

import re

# ---------------------------------------------------------------------------
# Skill identity & observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-spec-change-purchase"

# ---------------------------------------------------------------------------
# Endpoints & API versions (contract: ecs 2014-05-26, bssopenapi 2017-12-14,
# sts 2015-04-01)
# ---------------------------------------------------------------------------

BSS_ENDPOINT = "business.aliyuncs.com"
STS_ENDPOINT = "sts.aliyuncs.com"
# ecs endpoints are regional and resolved by the aliyun CLI from --region.

API_VERSIONS = {
    "ecs": "2014-05-26",
    "bssopenapi": "2017-12-14",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

# Hard per-call timeout in seconds for every subprocess/CLI call (rule 7.6.1).
DEFAULT_TIMEOUT = 60
MAX_ATTEMPTS = 3
MAX_RESULTS = 100
MAX_PAGES = 20
MAX_TARGET_DISPLAY = 30
DEFAULT_REGION = "cn-hangzhou"

# Input validation helpers (parameter hygiene; no shell interpolation).
INSTANCE_ID_RE = re.compile(r"^i-[0-9a-z]{6,}$")
TYPE_ID_RE = re.compile(r"^ecs\.[A-Za-z0-9._-]+$")
REGION_ID_RE = re.compile(r"^[a-z0-9-]{4,}$")
ZONE_ID_RE = re.compile(r"^[a-z0-9-]{4,}$")

# ---------------------------------------------------------------------------
# The five questions this tier answers (report header)
# ---------------------------------------------------------------------------

FIVE_QUESTIONS = (
    "1) which target specs are selectable for this instance, 2) is there "
    "stock (zone / region), 3) what does the error or quota mean, "
    "4) what will it approximately cost or refund (estimate only), "
    "5) what makes the change take effect",
)

# ---------------------------------------------------------------------------
# Mandatory change notices (MUST be relayed with every change conclusion;
# wording distilled from support guidance in the reviewed ticket set)
# ---------------------------------------------------------------------------

CHANGE_NOTICES = [
    "Lowering a configuration requires STOPPING the instance first (business "
    "interrupts); use an off-peak window.",
    "Read Prerequisites, Limits and Billing before acting: "
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "change-the-instance-types-of-subscription-instances.md",
    "A downgrade refunds the residual-value difference; with a discount the "
    "refund can be 0.",
    "A long-term promo (e.g. the 99-plan) can lose its promo price at renewal "
    "after a config change.",
    "Instance type changes are bounded by family compatibility: a type on the "
    "BUY page may be absent on the CHANGE page.",
]

# Effectiveness statements (the three fixed sentences of the tier).
EFFECT_STATEMENTS = [
    "Instance-type (vCPU/memory) changes take effect only after a restart; a "
    "paid order alone does not change the running configuration.",
    "Internet bandwidth changes take effect immediately and need no restart.",
    "Temporary bandwidth and EIP-related orders follow the effective time "
    "printed on the order; verify per order instead of assuming.",
]

# Snapshot guidance (text advice only; this skill never calls any snapshot
# API).
SNAPSHOT_ADVICE = [
    "Have the customer snapshot the instance disks in the ECS console before "
    "any change, for rollback; storage is billable.",
    "This skill only advises the backup step; it never creates snapshots or "
    "other resources for you.",
]

# Restart risk (used together with EFFECT_STATEMENTS).
RESTART_RISK = (
    "Have the customer warn application owners and stop active writes first: "
    "a restart loses unflushed memory data."
)

# Irreversibility notices (mandatory BEFORE guiding the customer to the
# corresponding console flow).
IRREVERSIBLE_NOTICES = {
    "bandwidth_eip": [
        "Converting fixed public bandwidth to pay-by-traffic and converting "
        "a fixed public IP to an EIP CANNOT be reversed (an EIP can never "
        "become a fixed public IP again).",
        "The EIP adds a separate configuration fee (region-dependent; use "
        "the price shown on the buy page at order time).",
        "When fixed bandwidth converts to pay-by-traffic, the remaining "
        "bandwidth fee is refunded at a discounted difference that can be 0 "
        "on discounted instances; converting the EIP back to fixed-bandwidth "
        "billing later may require paying the bandwidth fee again.",
        "IP-refresh route when a new public address is required: change the "
        "bandwidth billing to pay-by-traffic, convert the fixed public IP to "
        "an EIP, unbind the EIP, apply for a new EIP, bind it to the "
        "instance. While the old EIP is not released, a newly applied EIP "
        "will not equal the old address.",
    ],
    "cross_az": [
        "Migrating an instance across availability zones CHANGES its private "
        "IP address; check every dependency on that address first.",
    ],
    "new_purchase_ip": [
        "Buying a new instance or cloning instead of changing the type "
        "assigns DIFFERENT IP addresses; a fixed public IP cannot be kept by "
        "moving to a new instance.",
    ],
}

# Temporary bandwidth rules (numeric caps deferred to the console page /
# official doc until documentation backfill completes).
TEMP_BANDWIDTH_RULES = [
    "Temporary upgrade supports RAISING the fixed public bandwidth for a "
    "window only; a temporary LOWER is not supported.",
    "The maximum fixed-bandwidth value that can be selected is capped; use "
    "the limit shown on the console page / official temporary-upgrade doc.",
    "Bandwidth changes take effect immediately; no restart is needed.",
]

# Estimate disclaimer (mandatory with every price figure).
PRICE_DISCLAIMER = [
    "Any number produced here is an ESTIMATE. Account-level discounts, "
    "promotion rules and the exact refund are not fully visible to cloud "
    "queries.",
    "Treat the value shown on the console change/conversion page as "
    "authoritative: step through the dialog and read the displayed price or "
    "expected refund WITHOUT confirming the order.",
]

# Activity/price wording is dynamic: it must carry the reference-only mark, the
# official place to re-check it, and the link-accuracy caveat. URLs verified via
# the help-center search leg (doSearch + llms.txt fusion), not guessed.
DYNAMIC_PRICE_NOTICE = (
    "Price rules are reference only and change often; re-check "
    "https://www.aliyun.com/price/product#/ecs/detail (link may drift)."
)

# Inventory caveats (S5).
INVENTORY_CAVEAT = (
    "Stock readings are INSTANTANEOUS: availability can flip within minutes "
    "and release times cannot be predicted; never promise a buyable "
    "time-window."
)

CHANGE_SET_VS_BUY_PAGE = (
    "The modifiable target set returned for THIS instance differs from the "
    "buy-page catalog: family-compatibility path rules bound the change set. "
    "A type you can buy on a new order may be absent from the change page, "
    "and vice versa."
)

# Generic degraded fallback.
DEGRADE_FALLBACK = (
    "Where a cloud reading was unavailable, fall back to customer-side "
    "self-checks: the ECS console instance list, the change-configuration "
    "page (price shown before confirmation), the quota center and the "
    "billing center; paste back the full error text when it appears."
)

# ---------------------------------------------------------------------------
# Error-string triage table (C7 / S9 / S7)
# ---------------------------------------------------------------------------
# "kind": quotable_code = customer-visible error code of this tier;
#         observed_string = verbatim wording seen in reviewed tickets (match
#         and route only; never restate as an official code).

STOCK_FAMILY_NOT_DISCONTINUED = (
    "A sold-out zone is not a discontinued family: say the family is still on "
    "sale and it is THIS zone that has no stock right now.")
STOCK_OTHER_REGION_FALLBACK = (
    "When every zone of the region has no stock for the target type, the way "
    "out is buying that type in another region.")

ERROR_RULES = [
    {
        "kind": "quotable_code",
        "patterns": [r"(?i)OperationDenied\.NoStock"],
        "category": "inventory-nostock",
        "meaning": "No stock for the requested instance type at the "
                   "requested zone right now (also blocks starting an "
                   "instance whose previous change left it stopped).",
        "handling": [
            "Report the live per-zone stock from the inventory scan; offer "
            "same-tier substitute types and other zones of the region from "
            "the same scan - verified first, never by hearsay.",
            STOCK_FAMILY_NOT_DISCONTINUED,
            STOCK_OTHER_REGION_FALLBACK,
            "State that stock is instantaneous and release times cannot be "
            "predicted; refreshing later is a legitimate option.",
            "For a stopped instance failing to START with this code, the "
            "documented way out is a spec change to a type WITH stock, then "
            "start again.",
        ],
        "next_actions": [
            "reservation / resource-coordination requests go to a human "
            "plus business manager",
            "if the instance then stays stuck between start/stop states, "
            "hand off to the instance-state diagnosis skill "
            "(area:instance-state-diagnosis)",
        ],
        "reference": "references/spec-change-purchase__inventory-fallback.md",
    },
    {
        "kind": "observed_string",
        "patterns": [r"(?i)CheckError\.Inventory", r"(?i)sold\s*out",
                     r"(?i)insufficient\s+(available\s+)?resources?",
                     r"售罄|售馨|售謦|库存不足|无库存|没有库存|资源不足"
                     r"|买不到|抢不到|没有货"],
        "category": "inventory-wording",
        "meaning": "Sold-out / insufficient-inventory console wording; it "
                   "belongs to the SAME handling line as "
                   "OperationDenied.NoStock (do not treat it as a separate "
                   "official error code).",
        "handling": [
            "Run the inventory scan for the target type and answer with the "
            "per-zone stock instead of 'try refreshing later'.",
            STOCK_FAMILY_NOT_DISCONTINUED,
            STOCK_OTHER_REGION_FALLBACK,
        ],
        "next_actions": ["follow the inventory-nostock disposition above"],
        "reference": "references/spec-change-purchase__inventory-fallback.md",
    },
    {
        "kind": "quotable_code",
        "patterns": [r"(?i)StoragePerformanceReachLimit"],
        "category": "storage-performance-limit",
        "meaning": "Registered customer-visible code of this tier; the "
                   "reviewed ticket evidence of this tier contains NO case "
                   "showing its triggering scenario. Never invent an "
                   "explanation beyond the code name.",
        "handling": [
            "Acknowledge the code verbatim; its detailed disposition is "
            "pending manual review (requirements section 8-7).",
            "If it arrives together with slow-disk symptoms, the disk IO "
            "area is NOT in this tier: hand off.",
        ],
        "next_actions": [
            "hand off disk IO performance questions to "
            "area:resource-bottleneck",
        ],
        "reference": "references/spec-change-purchase__error-codes.md",
    },
    {
        "kind": "observed_string",
        "patterns": [r"(?i)maximum number of refund vcpu is exceeded"],
        "category": "quota-refund-vcpu",
        "meaning": "The REFUND vCPU quota is exhausted: the downgrade would "
                   "return more vCPU than the remaining refund allowance. "
                   "Numbers arrive in the text as quota [..] used [..] "
                   "need [..] and must be quoted back verbatim.",
        "handling": [
            "Parse the three bracketed numbers and echo them unchanged.",
            "Ask which instances are being downgraded (count them; a single "
            "report can cover several instances).",
            "Draft the quota-increase application material per "
            "references/spec-change-purchase__quota-triage.md.",
        ],
        "next_actions": [
            "the increase itself is submitted and approved by humans only; "
            "after approval, retry the downgrade (support observed a ~5 "
            "minute propagation before the retry succeeds)",
        ],
        "reference": "references/spec-change-purchase__quota-triage.md",
    },
    {
        "kind": "observed_string",
        "patterns": [r"(?i)available quota is insufficient"],
        "category": "quota-insufficient-multi-cause",
        "meaning": "Multi-cause message: in reviewed ticket evidence this "
                   "exact wording came from an OVERDUE account, not from a "
                   "quota cap. Never conclude 'raise the quota' from the "
                   "text alone.",
        "handling": [
            "Fixed order: first have the customer check outstanding balance "
            "in the Billing Management console and settle it; only if "
            "billing is clean, guide the regional quota self-application.",
        ],
        "next_actions": [
            "if billing is clean, run the quota line from "
            "references/spec-change-purchase__quota-triage.md",
        ],
        "reference": "references/spec-change-purchase__quota-triage.md",
    },
    {
        "kind": "observed_string",
        "patterns": [r"(?i)reached the quota (limit|cap)",
                     r"(?i)quota (limit|cap).*(reached|exceeded)",
                     r"(?i)cannot create.*(quota|limit)"],
        "category": "quota-regional",
        "meaning": "Regional ECS quota cap wording: the account hit the "
                   "default quota for the region. The quota VALUE and "
                   "approval state are NOT queryable from this tier's API "
                   "contract - rely on the console prompt / screenshot.",
        "handling": [
            "Guide the self-service quota application in the console quota "
            "center with a reasonable amount and a detailed business "
            "reason (scenario, instance families, vCPU count, expected "
            "usage duration).",
            "State that an application in the under-approval state locks "
            "that quota item and cannot be re-submitted.",
        ],
        "next_actions": [
            "urgent handling, cancellation and any approval acceleration go "
            "to a human",
        ],
        "reference": "references/spec-change-purchase__quota-triage.md",
    },
    {
        "kind": "observed_string",
        "patterns": [r"(?i)home directory .*is not found",
                     r"(?i)HomeDirNotFound"],
        "category": "guest-side-after-change",
        "meaning": "An in-guest symptom (e.g. a missing home directory "
                   "breaking login) seen after a spec change: the change "
                   "action itself usually SUCCEEDED - the problem lives "
                   "inside the operating system.",
        "handling": [
            "First confirm the inventory spec with the verification line "
            "(--verify-effective) and state it.",
            "Do not attempt any in-guest fix from this skill.",
        ],
        "next_actions": [
            "hand off to human on-machine support or the matching "
            "troubleshooting skill; mention that on-machine work is "
            "normally prepared with a snapshot, a downtime window and an "
            "authorization form",
        ],
        "reference": "references/spec-change-purchase__handoff-map.md",
    },
    {
        "kind": "observed_string",
        "patterns": [r"(?i)Request DescribeImages error"],
        "category": "service-request-error",
        "meaning": "Service-side InternalError around an image query, sometimes "
                   "adjacent to quota changes; reviewed evidence never "
                   "established a causal quota link. Collect facts, do not "
                   "conclude causality.",
        "handling": [
            "Collect the RequestId, region, zone and chosen spec; hand the "
            "RequestId to a human for the service-side investigation.",
        ],
        "next_actions": ["no automated retry loops; one fact-collection pass"],
        "reference": "references/spec-change-purchase__handoff-map.md",
    },
]

# Red line enforced by the report text (reviewed ticket T-F2F8EF51 pattern).
RED_LINE_NO_STOCK_REFUND = (
    "'An auto-refunded change order means the target was out of stock' is "
    "an UNVERIFIED human guess in the reviewed evidence. Phrase it only as "
    "a hypothesis to test: check stock with the inventory scan and let a "
    "human inspect the order."
)

SELF_SERVICE_REFUND_URL = "https://usercenter2.aliyun.com/refund/refund"
ACTIVITY_REFERENCE_NOTICE = (
    "Have the customer treat this activity/price scope as REFERENCE ONLY: "
    "campaign rules change often, so verify it on the official page; this "
    "skill does not guarantee the link or the scope stays current."
)

SPEC_RULE_TOPICS = {
    "change-effect-restart": {
        "question": "Does this change need a restart to take effect?",
        "answer": (
            "An instance-type (vCPU/memory) change takes effect only after the "
            "customer restarts the instance in the console. A cloud-disk "
            "category or performance-level change takes effect WITHOUT a "
            "restart. A disk capacity increase still needs the filesystem "
            "extended inside the OS."),
    },
    "stop-mode-for-change": {
        "question": "Normal stop or savings stop before a spec change?",
        "answer": (
            "A normal stop keeps the resources and the IP address, and the new "
            "specification is billed once the change succeeds. A savings stop "
            "releases part of the resources and suspends the related fees, so "
            "the resources are not held. To keep the current resources, choose "
            "the normal stop mode."),
    },
    "downgrade-refund-formula": {
        "question": "How much is refunded when I downgrade?",
        "answer": (
            "The downgrade refund is the remaining value of the old "
            "specification minus the new specification's purchase cost, per "
            "billing item. "
            "It shows 0 when a discounted order is consumed at the official "
            "LIST price, so little or nothing is left to refund. "
            "Self-service refund is available in the billing console."),
    },
    "upgrade-price-difference": {
        "question": "How is the upgrade price difference computed?",
        "answer": (
            "The upgrade difference is the price gap between the target and "
            "the current specification for the REMAINING period at the moment "
            "of the operation. Changing back later is recomputed on that later "
            "remaining period, so it need not equal the earlier refund. "
            "The difference itself normally carries no campaign discount; the "
            "quote on the change page is what counts."),
    },
    "quota-independent-per-charge-type": {
        "question": "I raised my vCPU quota, why is it still limited?",
        "answer": (
            "Subscription, pay-as-you-go and spot vCPU quotas are INDEPENDENT: "
            "raising one never raises another. The quota must be requested for "
            "the specific region and the specific instance family in Quota "
            "Center. Submission and approval are handled by a human."),
    },
    "disk-type-change-impact": {
        "question": "What is the impact of changing a cloud disk's category?",
        "answer": (
            "Changing a cloud disk's category or performance level has a small "
            "impact: it consumes part of the disk's read/write performance "
            "while the change runs, and it needs no restart. A cloud disk "
            "cannot be shrunk - a smaller disk requires buying a new one and "
            "moving the data."),
    },
    "os-preserved-on-spec-change": {
        "question": "Will a spec change rebuild my operating system?",
        "answer": (
            "Upgrading or downgrading vCPU/memory does NOT rebuild the operating "
            "system: the OS, the data and the IP address are preserved. Device "
            "names can change on a new family (for example /dev/vdb1 becomes "
            "/dev/nvme1n1p1), so mounts must use UUID instead of a device name."),
    },
    "no-temporary-spec-burst": {
        "question": "Can I raise CPU/memory only for a few hours?",
        "answer": (
            "A time-boxed temporary CPU/memory increase is not supported: the "
            "only path is a specification upgrade, effective after the customer "
            "restarts the instance in the console, and a later downgrade. "
            "A temporary BANDWIDTH upgrade is supported and reverts on its own."),
    },
    "nostock-not-api": {
        "question": "My API call fails with OperationDenied.NoStock.",
        "answer": (
            "Sold out (OperationDenied.NoStock) means no stock for that type in "
            "THIS zone now; the family is still on sale. Change to another instance "
            "type first (stock is per type per zone), then other zones, then another "
            "region. Stock is instantaneous, so a zone can recover; buy+migrate is "
            "the last resort (public IP may change). If the order still fails "
            "pre-payment validation, escalate to a senior engineer."),
    },
    "ipv6-support-boundary": {
        "question": "Can I add an IPv6 address, and is it free?",
        "answer": (
            "Simple Application Server does not support IPv6 - that needs ECS. "
            "On ECS the instance must sit in a VPC with an IPv6-capable "
            "specification, the address is assigned to the elastic network "
            "interface, and public IPv6 traffic needs IPv6 internet bandwidth "
            "enabled, which is billed separately."),
    },
    "trial-instance-upgrade-cap": {
        "question": "Can a free-trial instance be upgraded?",
        "answer": (
            "A free-trial instance can be upgraded, but only within the trial's "
            "own specification cap, which is set by the campaign rather than by "
            "the normal change rules. Read the cap on the trial page before "
            "promising a target specification."),
    },
    "promo-price-lost-after-change": {
        "question": "Will I keep the promotional price after a spec change?",
        "answer": (
            "A promotional instance loses the campaign price on renewal once "
            "any upgrade, downgrade or specification change has been made; "
            "renewal then follows the standard price. Confirm the campaign "
            "terms before changing a promotional instance."),
    },
    "spec-change-is-instance-type": {
        "question": "Can I change only the CPU or only the memory?",
        "answer": (
            "CPU and memory are not changed separately: it means selecting a "
            "different instance TYPE. "
            "It takes effect only after a restart in the ECS console, so snapshot "
            "the disks first. The selectable targets come from the "
            "instance's own change set, which is narrower than the buy page and "
            "excludes a target that lacks a feature the instance already uses "
            "(for example ENI trunking), so a 'not supported' target means "
            "choosing another family."),
    },
    "instance-id-changed": {
        "question": "My instance ID changed, why?",
        "answer": (
            "An instance ID is immutable for the life of the instance: it only "
            "appears to change when the instance was released and rebuilt, "
            "replaced by a new purchase, or migrated to a new instance. A spec "
            "change, a restart or a stop never changes it."),
    },
    "spec-change-interruption-window": {
        "question": "How long is the interruption, and do my processes come back?",
        "answer": (
            "An instance-type change needs a stop and restart that fully "
            "interrupts the workload for about 3-5 minutes (at most 10), and "
            "processes only return if auto-start was already configured. A "
            "public bandwidth change instead takes effect immediately, with no "
            "restart and no shutdown."),
    },
    "order-payment-failure": {
        "question": "Why does the order, the payment or the price inquiry fail?",
        "answer": (
            "A failed order, payment or price inquiry is usually a blocked "
            "precondition: the specification is out of stock in that zone, the "
            "instance's image was deleted so it cannot be priced, or an account "
            "verification check failed. Ask for the exact error text and the "
            "RequestId to choose between them."),
    },
    "spec-catalog-entry": {
        "question": "Where do I see the specifications I can change to?",
        "answer": (
            "For a subscription instance the selectable specifications are on "
            "the ECS console's Change instance type page for that instance, not "
            "on the buy page. An 'insufficient instances' message means that "
            "specification is out of stock in the current zone, not that the "
            "account owns too many."),
    },
}

SPEC_RULE_INTENT_PATTERNS = [
    (r"(?i)operationdenied\.nostock|nostock|售罄|售馨|资源不足|库存不足|无库存|没有库存"
     r"|ecs[.\s-]?[a-z]\d[a-z0-9.-]{0,18}[^。；\n]{0,6}(没有|没货|没了|买不到|无货)"
     r"|(规格|实例规格|机型)[^。；\n]{0,8}(没有|没货|买不到|无货)", "nostock-not-api"),
    (r"(?i)(差价|差额|补差).{0,16}(优惠|折扣|活动|便宜)"
     r"|(优惠|折扣).{0,12}(差价|差额|补差)", "upgrade-price-difference"),
    (r"(?i)(ipv6|ipv 6)", "ipv6-support-boundary"),
    (r"(?i)实例\s*id.{0,8}(变了|变化|改了|不一样|换)", "instance-id-changed"),
    (r"(?i)(试用|免费试用|trial).{0,24}(升级|升配|改|变配|配置)",
     "trial-instance-upgrade-cap"),
    (r"(?i)(99|优惠|活动|促销|特价).{0,24}(变配|升配|降配|续费|价格|优惠)"
     r"|(变配|升级|降配).{0,20}(优惠|活动价|99)", "promo-price-lost-after-change"),
    (r"(?i)(普通停机|节省停机|经济停机|停机模式).{0,24}(区别|哪|保留|选)"
     r"|(保留|不丢).{0,12}(资源|ip).{0,16}(停机|停)", "stop-mode-for-change"),
    (r"(?i)(降配|降级|降低配置|降规格).{0,20}(退款|退钱|退多少|退费|返还)"
     r"|(退款|退钱).{0,16}(降配|降级|多少|怎么算|规则)"
     r"|(宽带|带宽).{0,20}(降低|降|升|改).{0,20}(退|差价|为何|为什么)",
     "downgrade-refund-formula"),
    (r"(?i)(升配|升级|带宽|宽带).{0,20}(差价|补差|补交|多少钱|价格|退)"
     r"|(改回|换回|恢复|改回之前).{0,16}(配置|规格).{0,20}(费用|支付|钱|为什么)"
     r"|(差价|补差).{0,16}(怎么|如何|算|多少)", "upgrade-price-difference"),
    (r"(?i)(配额|quota).{0,24}(独立|不通用|抢占|按量|包年|提升|申请|通过)"
     r"|q_resquota|vcpu.{0,12}(配额|quota)"
     r"|抢占.{0,14}(申请|配额|提升|创建|买|购买)"
     r"|(申请|提升).{0,14}抢占", "quota-independent-per-charge-type"),
    (r"(?i)(云盘|磁盘|数据盘|系统盘).{0,12}(变配|变更类型|换类型|类型|性能级别|pl\d|essd)"
     r"|(云盘|磁盘|数据盘|系统盘).{0,12}(大小|容量).{0,12}(减少|减小|缩|降)"
     r"|(io|性能).{0,12}(升级|变配).{0,12}(重启|生效)", "disk-type-change-impact"),
    (r"(?i)(降配|降级|升配|升级|变配).{0,24}(操作系统|系统|重装|重做|数据|ip)"
     r"|(升级配置|升配|变配|换规格).{0,12}(报错|失败|异常|起不来|启动不了)"
     r"|(操作系统|系统盘数据).{0,16}(变更|丢失|保留|重装)", "os-preserved-on-spec-change"),
    (r"(?i)(临时|按时间段|某个时间段|某一个时间段|时间段|短时|几小时|一天)"
     r".{0,24}(扩容|升配|升级|提升|扩大|加).{0,16}(cpu|内存|配置|核|性能)"
     r"|(时间段|临时|短时).{0,30}(性能|cpu|内存|配置|核).{0,12}(扩大|提升|扩容|升|加)"
     r"|(cpu|内存|性能).{0,20}(临时|某个时间段|某一个时间段|时间段)",
     "no-temporary-spec-burst"),
    (r"(?i)(可否|能否|可以|能不能).{0,12}(降低|降|升|改|调).{0,8}(配置|规格|cpu|内存)"
     r"|(升级|升配|降配).{0,6}(方式|方法|怎么|如何)"
     r"|(改为|变更为|调整成|换成).{0,24}ecs[.\s-]?[a-z]\d"
     r"|(升级|升配|变配).{0,8}(资源|配置).{0,8}(报错|失败|不支持)"
     r"|(只|单独|单独改).{0,8}(改|升|加).{0,6}(cpu|内存)",
     "spec-change-is-instance-type"),
    (r"(?i)(重启|生效).{0,16}(吗|么|需要|才|后)"
     r"|(变配|升配|降配|扩容|变更).{0,16}(重启|生效)", "change-effect-restart"),
    (r"(?i)(关机中|停止中|停机中|启动中).{0,12}(持续|超过|已经|都|了)"
     r"|(升级|升配|变配|降配).{0,10}(关机中|停止中|停机中)"
     r"|(闪断|中断|抖动)|(影响|会不会影响).{0,12}(业务|项目|服务器|运行|网站)"
     r"|(进程|程序|服务).{0,12}(自动|自启|开启|启动)|(会|会不会).{0,6}(关机|被关|停机)"
     r"|重启.{0,10}(多久|几分钟|多长时间|耗时)", "spec-change-interruption-window"),
    (r"(?i)(付款|支付|下单|购买|询价|订单).{0,8}(失败|报错|不了|异常)"
     r"|无法(下单|支付|付款|购买|询价)|(买|购)不了", "order-payment-failure"),
    (r"(?i)可选规格|(哪个|什么|啥)页面.{0,12}(规格|看|查)|实例不足"
     r"|(规格|实例型号).{0,10}(看不到|找不到|没有了)|(看不到|找不到).{0,10}(规格|可选)",
     "spec-catalog-entry"),
    (r"(?i)(变配|变更配置|调整配置|升级|升配|降配|降级|改配置|换配置|扩内存|加内存)"
     r".{0,24}(多花|多少钱|费用|收费|价格|省多少|贵|金额)|(多花|省).{0,10}多少钱"
     r"|怎么还需要支付", "upgrade-price-difference"),
    (r"(?i)(变更|更改|调整|修改|变换|改|换|扩|加|升|降)[^。；\n]{0,6}"
     r"(配置|规格|cpu|内存|核数|核|实例类型)"
     r"|(配置|规格|cpu|内存|核数)[^。；\n]{0,8}(变更|更改|调整|改|换|扩|加|升|降)"
     r"|(如何|怎么|怎样|在哪|哪里)[^。；\n]{0,8}(变更|更改|调整|升|降|扩)"
     r"|(内存|cpu|核数|配置)[^。；\n]{0,6}(不够|不足|太低|较低|小了|不够用)"
     r"|(升配|降配|变配|升降配)", "spec-change-is-instance-type"),
]

SPEC_CHANGE_SAFETY_PRELUDE = (
    "Snapshot the disks first, stop active writes, and work off-peak."
)
SPEC_RULE_SAFETY_TOPICS = (
    "change-effect-restart", "stop-mode-for-change",
    "upgrade-price-difference", "disk-type-change-impact",
    "os-preserved-on-spec-change", "no-temporary-spec-burst",
    "spec-change-interruption-window", "trial-instance-upgrade-cap",
    "spec-change-is-instance-type",
)
SPEC_RULE_ONLY_TOPICS = (
    "change-effect-restart", "stop-mode-for-change", "downgrade-refund-formula",
    "upgrade-price-difference", "quota-independent-per-charge-type",
    "disk-type-change-impact", "os-preserved-on-spec-change",
    "no-temporary-spec-burst", "nostock-not-api", "ipv6-support-boundary",
    "trial-instance-upgrade-cap", "promo-price-lost-after-change",
    "spec-change-is-instance-type", "instance-id-changed",
    "spec-catalog-entry",
)
SPEC_RULE_ACTIVITY_TOPICS = ("trial-instance-upgrade-cap",
                             "promo-price-lost-after-change")
SPEC_RULE_CONSOLE_PATH = {
    "downgrade-refund-formula": SELF_SERVICE_REFUND_URL,
    "quota-independent-per-charge-type": "Quota Center console (region + instance family)",
    "change-effect-restart": "ECS console > Instances > Restart",
    "disk-type-change-impact": "ECS console > Disks > Change category",
    "stop-mode-for-change": "ECS console > Instances > Stop (stop mode)",
    "spec-change-is-instance-type": "ECS console > Instances > Change instance type "
                                    "(Running or Stopped only; prerequisites, limits "
                                    "and fees: https://help.aliyun.com/zh/ecs/"
                                    "user-guide/change-the-instance-types-of-"
                                    "subscription-instances.md)",
    "spec-catalog-entry": "ECS console > Instances > Change instance type (升降配)",
    "order-payment-failure": "ECS console > Orders, then the buy page for the target zone",
}

SPEC_RULE_MONEY_TOPICS = (
    "downgrade-refund-formula", "upgrade-price-difference",
    "spec-change-is-instance-type", "promo-price-lost-after-change",
)
SPEC_RULE_MONEY_NOTICES = (
    "Have the customer expect the refund to be small or 0 when the purchase "
    "used a discount: only the residual-value difference is returned.",
    "Have the customer know a long-term low-price plan (for example the "
    "99-plan) loses its promo price at renewal after any config change.",
)
SPEC_RULE_TAILS = {
    "downgrade-refund-formula": (
        "Have the customer verify the dated rule (2026-02-09: per item, "
        "vouchers pro-rata, staged rollout) on the order page and at "
        "https://help.aliyun.com/zh/user-center/"
        "description-of-downgrade-refund-rules.md.",
        "Have the customer treat downgrade and refund as two separate "
        "operations, and note a refunded instance is kept about 15 days and "
        "then released without its data.",
        "Have the customer request a downgrade-for-renewal at least 15 days "
        "before expiry; it cannot be combined with the refund step.",
    ),
    "quota-independent-per-charge-type": (
        "Have the customer know the buy page's maximum count is per order, not "
        "the account quota; Quota Center is the authoritative number.",
        "Ask the customer for the target region and the expected instance "
        "count or vCPU total, plus a screenshot of the quota request page.",
    ),
    "nostock-not-api": (
        "Have the customer check stock per zone with the inventory scan "
        "(DescribeAvailableResource with WithStock) before retrying.",
        "Have the customer know a vSwitch cannot move zone: a new zone needs "
        "a new vSwitch, so a pinned script must change it.",
    ),
    "disk-type-change-impact": (
        "Have the customer shrink by migration: create a smaller disk, copy "
        "and verify the data, switch the mount, then release the old disk only "
        "after they confirm.",
    ),
    "ipv6-support-boundary": (
        "Have the customer know each instance holds one IPv6 address, and an "
        "instance type without IPv6 support must be changed first.",
    ),
    "no-temporary-spec-burst": (
        "Have the customer plan the revert: after the peak, downgrade again "
        "and restart, and expect the refund to follow the residual-value rule.",
    ),
}
