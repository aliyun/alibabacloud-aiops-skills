#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Billing Attribution & Bill Check
==============================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (endpoints, query limits, billing-item semantics,
deduction-failure rules, timing caliber, console paths, FAQ knowledge and the
handoff map) is embedded here as Python constants. There are NO data files in
this skill. The readable companion lives under references/*.md.
"""

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-billing-attribution-bill-check"

# ---------------------------------------------------------------------------
# Endpoint / API metadata
# ---------------------------------------------------------------------------

# Central (region-less) endpoints.
BSS_ENDPOINT = "business.aliyuncs.com"
STS_ENDPOINT = "sts.aliyuncs.com"
# Regionalized services: the CLI is pinned to the per-region endpoint derived
# from these standard templates (ecs.<region>.aliyuncs.com /
# metrics.<region>.aliyuncs.com).
ECS_ENDPOINT_TEMPLATE = "ecs.{region}.aliyuncs.com"
CMS_ENDPOINT_TEMPLATE = "metrics.{region}.aliyuncs.com"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "bssopenapi": "2017-12-14",
    "cms": "2019-01-01",
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Pagination / query limits
# ---------------------------------------------------------------------------

MAX_RESULTS = 300      # BSS NextToken-style page cap (MaxResults, documented maximum)
QUERY_PAGE_SIZE = 100  # BSS PageNum/PageSize-style page cap (documented maximum)
MAX_PAGES = 20         # hard guardrail on pages fetched per loop
DEFAULT_TIMEOUT = 60   # seconds, per CLI invocation (MUST 7.6.1)
MAX_DAILY_DAYS = 31    # cap for the per-day series walk-back

# ---------------------------------------------------------------------------
# CloudMonitor cross-check defaults (usage vs bill)
# ---------------------------------------------------------------------------
# These tokens configure the OPTIONAL traffic cross-check. The metric list is
# verifiable in the CloudMonitor console under the ECS host namespace; when a
# query returns no datapoints the script degrades and asks the operator to
# confirm the metric name instead of inventing numbers.
DEFAULT_METRIC_NAMESPACE = "acs_ecs_dashboard"
DEFAULT_TRAFFIC_METRIC = "InternetOutRate"   # outbound public bandwidth, bit/s
METRIC_PERIOD_SECONDS = "3600"               # hourly points

# ---------------------------------------------------------------------------
# ECS-related billing items (dictionary distilled from real support tickets;
# readable version: references/billing-attribution-bill-check__billing-items.md). Chinese tokens are kept
# because BSS bill rows carry localized BillingItem / ProductName values for
# Chinese-language accounts; they are MATCH KEYS only, never asserted prices.
# ---------------------------------------------------------------------------

BILLING_ITEMS = {
    "network_out": {
        "names": ("NetworkOut", "network_out", "\u516c\u7f51\u6d41\u91cf",
                  "\u6d41\u51fa\u6d41\u91cf"),
        "label": "Public outbound traffic (per-GB pay-as-you-go)",
        "note": ("Charged ONLY in the outbound direction on instances whose "
                 "internet bandwidth billing mode is pay-by-traffic; a "
                 "reference mainland example seen in tickets is 0.8 CNY/GB, "
                 "but the bill row's own ListPrice is always authoritative. "
                 "A Subscription (monthly) instance CAN still carry this "
                 "post-paid item."),
    },
    "snapshot_capacity": {
        "names": ("\u5feb\u7167\u94fe\u5bb9\u91cf", "SnapshotChainSize",
                  "snapshot_chain_capacity"),
        "label": "Snapshot chain capacity (size x duration)",
        "note": ("Billed hourly by total snapshot size; the first snapshot is "
                 "full, later ones incremental (blocks changed since the last "
                 "snapshot). Cross-region copies bill in the destination "
                 "region. Manual snapshots are billed; the limited-time-free "
                 "quota applies only to disks BOUND to the auto-snapshot "
                 "policy."),
        "metering": ("Billed hourly on total snapshot size times unit price, any "
                     "part hour billed as a full hour"),
    },
    "disk_capacity": {
        "names": ("\u78c1\u76d8\u5bb9\u91cf", "Disk", "disk_capacity"),
        "label": "Disk (block storage) capacity",
        "note": ("A cloud disk bills from the moment it exists, whether or "
                 "not it is attached to a running instance."),
    },
    "disk_burst": {
        "names": ("\u6027\u80fd\u7a81\u53d1", "PerformanceBurst", "BurstIOPS",
                  "disk_burst", "burst_iops"),
        "label": "ESSD AutoPL performance burst (usage above the disk baseline)",
        "note": ("An ESSD AutoPL disk with performance burst enabled bills extra "
                 "every time the workload exceeds the disk's baseline "
                 "performance. It is a block-storage item, not an instance "
                 "item, and it can be enabled from the disk's creation, so the "
                 "customer may not remember turning it on."),
    },
    "instance_config": {
        "names": ("\u4e91\u670d\u52a1\u5668\u914d\u7f6e", "InstanceType",
                  "instance_config"),
        "label": "Instance specification (compute) fee",
        "note": ("Pay-as-you-go instances bill hourly by spec, including "
                 "while merely stopped (normal stop keeps charging; savings "
                 "stop suspends only the spec / fixed-bandwidth / image-license "
                 "fees)."),
    },
    "system_disk": {
        "names": ("\u7cfb\u7edf\u76d8", "SystemDisk", "system_disk"),
        "label": "System disk fee",
        "note": "Billed with the instance; keeps running under savings stop.",
    },
    "surplus_credit": {
        "names": ("\u8d85\u989d\u79ef\u5206", "SurplusCredit", "surplus_credit"),
        "label": "Burstable-instance excess CPU credits",
        "note": ("t5/t6 burstable instances in unlimited mode can consume "
                 "credits beyond the free baseline; the overage bills as the "
                 "SurplusCredit item. The bill PRODUCT name (e.g. ECS "
                 "subscription) may differ from this BILLING ITEM - read the "
                 "item, not the product label."),
    },
    "image_license": {
        "names": ("\u955c\u50cf\u8bb8\u53ef\u8bc1", "Image", "image_license"),
        "label": "Marketplace / commercial image license fee",
        "note": "Suspended during economical (savings) stop together with the spec fee.",
    },
    "eip": {
        "names": ("\u5f39\u6027\u516c\u7f51IP", "Eip", "eip"),
        "label": "Elastic IP address fee",
        "note": "Keeps billing under savings stop and while unbound.",
    },
}

# Products OUTSIDE the ECS family: attribute them, then hand off
# (references/billing-attribution-bill-check__handoff-map.md).
NON_ECS_PRODUCT_TOKENS = {
    "oss": "Object Storage Service (OSS)",
    "yundun_aegis": "Security Center",
    "cdn": "CDN / Edge Security Acceleration",
    "cdt": "Cloud Data Transfer (CDT)",
    "hbr": "Cloud Backup",
    "eip": "Elastic IP Address",
    "acs": "Container Compute Service (ACS)",
    "eci": "Elastic Container Instance (ECI)",
    "dms": "Data Management (DMS)",
    "sas": "Security Center",
    "bailian": "Model Studio (Bailian)",
    "nat": "NAT Gateway",
    "waf": "Web Application Firewall",
    "rds": "ApsaraDB RDS",
    "nas": "Apsara File Storage NAS",
    "slb": "Server Load Balancer",
    "vod": "ApsaraVideo VOD",
    "dns": "Alibaba Cloud DNS",
    "dbs": "Database Backup (DBS)",
    "ddos": "Anti-DDoS",
    "sls": "Simple Log Service (SLS)",
    "cms": "CloudMonitor",
}
RULE_INTENT_PATTERNS = (
    (r"(?i)(充值|续费|还款|结清).{0,24}(还有|还是有|为什么还|为啥还|仍然|仍有).{0,12}"
     r"(待还|代还|待支付|未还|欠|账单)"
     r"|(待还|代还|待支付|未结|暂估).{0,10}(账单|金额|费用)"
     r"|(账单|费用|金额).{0,12}(更新|刷新).{0,8}(太慢|很慢|慢|延迟)"
     r"|月结.{0,12}(次月|下个月|出账|最终)", "postpaid-cycle-provisional"),
    (r"(?i)(提前|立刻|即刻|马上|尽快|现在).{0,16}(开票|发票|报销)"
     r"|(开票|发票|报销).{0,20}(提前|立刻|即刻|马上|能不能|可以|怎么|时间)"
     r"|(还款|结清|付清|补缴).{0,20}(开票|发票)", "postpaid-invoice-timing"),
    (r"(?i)(快照|snapshot).{0,26}(每月|每个月|一直|还是|仍|总是).{0,12}(扣|计费|收费)",
     "settlement-caliber-change"),
    (r"(?i)(学生|校园).{0,10}(优惠|券|额度|300)", "student-coupon-spec-scope"),
    (r"(?i)(不用|停机|停止|关机|停掉|不释放).{0,16}(一个月|每月|月).{0,10}(多少|钱|费用)",
     "charged-while-stopped"),
    (r"(?i)(额度|节省计划|资源包|试用).{0,24}((?:没有?|未)用完|还有|剩余|没用)"
     r".{0,20}(扣|计费|收费)", "plan-quota-remaining-but-charged"),
    (r"(?i)(节省计划|savings\s?plan).{0,20}(扣|不抵|没抵|未抵)",
     "plan-quota-remaining-but-charged"),
    (r"(?i)(优惠券|代金券|优惠卷|代金卷|券|额度).{0,24}(抵扣|没抵|未抵|不抵|优先|没用|扣)"
     r"|(是否|有没有|有无|有|申请).{0,6}(优惠券|代金券|优惠卷|代金卷)", "coupon-not-applied"),
    (r"(?i)(余额|额度).{0,16}(优先|先扣|没用完|未用完)", "coupon-not-applied"),
    (r"(?i)(节省停机|经济停机|节省关机|节省模式关机|省关机).{0,20}(扣|余额|计费|费用|钱)"
     r"|(都|已经|已)?节省关机", "savings-stop"),
    (r"(?i)(包年包月|按年).{0,20}(后付费|按量|还.{0,4}扣)", "subscription-postpaid"),
    (r"(?i)(退款|退回|可退|退钱|退费).{0,24}(到账|只到|少了|不一致|不符|为什么|为啥|差)"
     r"|(到账|实退).{0,16}(少|不一致|差|为什么)"
     r"|(降配|退订).{0,20}退款.{0,16}(少|为0|为零|没有|不一致)",
     "refund-split-channels"),
    (r"(?i)(应付|实付|多个金额|金额不一致)", "multiple-amounts"),
    (r"(?i)(明细|详情).{0,10}(空|没有|看不到)", "bill-detail-empty"),
    (r"(?i)(试用|免费).{0,16}(到期|收费|扣费|一直)", "free-trial-composition"),
    (r"(?i)(资源包|存储包|流量包|容量包).{0,24}(共用|通用|指定|所有|哪些|范围|全部)",
     "resource-package-scope"),
    (r"(?i)(以前|之前|原来|本来|一直|都).{0,16}(不扣|没扣|未扣|不收费|没收费|免费)"
     r".{0,20}(现在|最近|突然|开始|又)", "settlement-caliber-change"),
    (r"(?i)(突然|忽然|最近|昨天|今天|这两天).{0,12}(开始|才|就).{0,8}(扣费|扣钱|收费|扣)",
     "settlement-caliber-change"),
    (r"(?i)(过期|到期|释放|停用|没用|未使用|没有使用).{0,24}(一直|还是|仍|每个月|每月)"
     r".{0,10}(扣|收费|计费)", "settlement-caliber-change"),
    (r"(?i)(自动续费|自动续订|自动续費).{0,24}(提前|几天|哪天|什么时候|何时|扣款|付款|扣费)"
     r"|(提前).{0,8}(9|九|1|一).{0,4}(天).{0,10}(付款|扣款|续费)",
     "auto-renew-deduction-schedule"),
    (r"(?i)(余额|账户).{0,12}(扣完|用完|耗尽|为0|为零|不足|没钱).{0,20}(停机|停服|停止|释放|影响)"
     r"|(欠费|欠款).{0,16}(停机|停服|释放|后果|多久|几天|影响)"
     r"|(停机|停服).{0,12}(多久|几天).{0,10}(释放|删除)", "overdue-consequences"),
    (r"(?i)(月初|1号|一号|每月.{0,4}初|月初第一天).{0,16}(扣|扣费|扣款|收费)", "charge-on-1st"),
    (r"(?i)(云盘|磁盘|数据盘|块存储).{0,20}(不用|没用|未使用|没有使用|没挂|未挂载|闲置)"
     r".{0,16}(扣|计费|收费)|(云盘|数据盘).{0,12}(一直|还是|仍).{0,8}(扣|计费)",
     "disk-still-billed"),
    (r"(?i)(快照|snapshot).{0,20}(免费|赠送|额度).{0,16}(扣|收费|计费|用完|超出)"
     r"|(快照).{0,10}(免费额度|免费配额)", "snapshot-free-quota"),
    (r"(?i)(超额积分|SurplusCredit|无性能约束|突发性能实例).{0,20}(扣|收费|计费|费用|不知情)"
     r"|(积分).{0,10}(超出|超额).{0,12}(费|扣)", "burstable-surplus"),
    (r"(?i)(跨地域|异地|其他地域|别的地域|没有创建).{0,20}(快照).{0,16}(费|扣|计费)"
     r"|(快照).{0,12}(跨地域|复制).{0,12}(费|扣|计费)", "cross-region-snapshot-fee"),
    (r"(?i)(流量).{0,16}(告警|报警|封顶|上限|自动停机|阈值).{0,16}(设置|设|能不能|可以|吗)"
     r"|(设置|设).{0,10}(流量).{0,10}(告警|封顶|上限)", "traffic-alert"),
    (r"(?i)(流量包|共享流量).{0,20}(有效期|多久|过期|提前买|预购|结转|清零)"
     r"|(流量包).{0,12}(买|购).{0,10}(多久|多长)", "no-package-left-until"),
    (r"(?i)(当月|本月|这个月).{0,16}(对账|核对|账单).{0,14}(准|能|可以|吗|最终)"
     r"|(账单).{0,10}(什么时候|何时).{0,8}(出|最终|准确)", "current-month-reconcile"),
    (r"(?i)(流量).{0,16}(去哪|到哪|谁|哪些地址|访问了|去向|来源).{0,12}"
     r"|(谁|哪些IP|哪些地址).{0,12}(访问|消耗|用了).{0,8}(流量|我的)", "traffic-not-traceable"),
    (r"(?i)(释放|删除|退订|不用了|没用了|到期).{0,48}(还|仍|为什么|为啥|怎么).{0,24}"
     r"(扣|收费|计费|费用|账单)|(已经|都).{0,8}释放.{0,48}(扣|费)", "released-still-charged"),
    (r"(?i)快照", "snapshot-billing-stop"),
    (r"(?i)(如何|怎么|怎样|想|要).{0,12}(取消|停止|关闭|不让|不再).{0,10}"
     r"(扣费|收费|计费|扣款|费用)|(不想|不需要|不用).{0,10}(要了|用了).{0,16}(扣|费|释放)"
     r"|取消收费", "stop-being-charged"),
    (r"(?i)超额积分|surpluscredit|积分.{0,8}(扣|计费|是什么)", "burstable-surplus"),
    (r"(?i)流量.{0,12}(费|计费|收费|额度|明细|高|多)|(免费|流出).{0,8}流量",
     "traffic-fee-detail"),
    (r"(?i)扣费|扣款|扣钱|扣了|扣.{0,3}费|收费|费用|账单|计费|消费|后付费|块钱|按量|哪些服务",
     "charge-source-unknown"),
)
ASKED_ITEM_PATTERNS = (
    (r"(?i)(超额积分|SurplusCredit|无性能约束|超额.{0,4}积分)", "surplus_credit"),
    (r"(?i)(性能突发|突发性能|burst)", "disk_burst"),
    (r"(?i)(快照|snapshot)", "snapshot_capacity"),
    (r"(?i)(云盘|磁盘|数据盘|块存储|\bdisk\b)", "disk_capacity"),
    (r"(?i)(流量|带宽|traffic|bandwidth)", "network_out"),
    (r"(?i)(实例|服务器|instance)", "instance_config"),
)
CONTRACT_INTENT_RE = (
    r"(?i)(框架合同|框架协议|合同申请|申请.{0,6}合同|订单合同|账单合同"
    r"|对公转账|汇款账号|合作证明|盖章|合同模板)")
CONTRACT_POLICY_ANSWER = [
    "Have the customer take the contract answer first: Alibaba Cloud does not "
    "customise a framework agreement from a third-party template online - only "
    "standardised electronic contracts are issued. The standard order contract "
    "or bill contract applied for online already has legal effect and can serve "
    "as the cooperation proof for an internal approval and a corporate bank "
    "transfer.",
    "Have the customer request the dedicated remittance account on Billing "
    "console -> Fund Management -> Recharge if a corporate transfer is needed; "
    "that account is also shown in the contract.",
    "Have the customer contact their Alibaba Cloud business manager for the "
    "discounted framework agreement seen in the console contract module: that "
    "one is signed with the business manager and cannot be issued online.",
]
SPECIALTY_BILLING_ITEMS = ("disk_burst", "surplus_credit", "image_license")
STOP_BILLING_ROUTES = {
    "disk_burst": "have them open ECS console > Block Storage, find that ESSD AutoPL "
                  "disk, choose More > Edit Attributes and uncheck Performance Burst "
                  "themselves; this only removes the headroom above the disk baseline, "
                  "so confirm the workload can run on the baseline first",
    "snapshot_capacity": "after they confirm the restore points are no longer needed and "
                         "a backup is verified, have them delete the snapshots at "
                         "https://ecs.console.aliyun.com/snapshot and delete the automatic "
                         "snapshot policy separately (it keeps the snapshots it already "
                         "made); repeat per region - irreversible",
    "disk_capacity": "after they confirm the data is backed up, have them release the "
                     "unattached pay-as-you-go disk themselves in ECS console > Disks; "
                     "a disk still attached to a stopped instance keeps billing",
    "instance_config": "after they confirm the data is backed up, have them release the "
                       "pay-as-you-go instance themselves, or enable savings stop so the "
                       "spec fee is suspended while disks and addresses keep billing",
    "network_out": "have them switch the internet bandwidth to fixed bandwidth in the "
                   "instance bandwidth settings after confirming the fee change, which "
                   "removes the per-GB traffic item",
    "surplus_credit": "have them switch the instance from unlimited back to standard "
                      "(performance-constrained) mode in ECS console > Instances > More > "
                      "Change Instance Attribute; new SurplusCredit charges stop, but CPU "
                      "is capped at the baseline, so confirm the workload fits first",
}

# ---------------------------------------------------------------------------
# Amount-field caliber (bill reconciliation; see references/
# billing-timing-and-caliber.md)
# ---------------------------------------------------------------------------

AMOUNT_FIELDS = {
    "PretaxGrossAmount": "gross amount (usage x list price, before discounts)",
    "InvoiceDiscount": "commercial discount applied to the row",
    "DeductedByResourcePackage": "equivalent amount deducted by a resource package (CNY, not usage)",
    "DeductedByCoupons": "amount deducted by a coupon for this row",
    "AfterDiscountAmount": "amount after discounts",
    "PretaxAmount": "payable amount of the row (what the balance is charged)",
    "CashAmount": "paid from cash balance",
    "OutstandingAmount": "unsettled remainder of the row",
}

# ---------------------------------------------------------------------------
# Timing caliber (verbatim authoritative statements used by support staff;
# readable version: references/billing-attribution-bill-check__billing-timing-and-caliber.md)
# ---------------------------------------------------------------------------

TIMING_CALIBER = [
    "The final bill detail of a month is issued at 12:00 on the 3rd day of "
    "the following month; before that, current-month figures are "
    "provisional reference only and are NOT the basis for reconciliation.",
    "Bill detail data lags actual consumption by about 24 hours; instance-"
    "dimension fields (instance config / spec / nickname / resource group / "
    "public IP / private IP / zone) lag by about 48 hours.",
    "Pay-as-you-go charges settle monthly: the previous month's post-paid "
    "bill is deducted from the account balance at the beginning of the next "
    "month, so a deduction on the 1st usually maps to the PREVIOUS cycle.",
    "Post-paid metering itself has a delivery delay (roughly around 2 hours "
    "for hourly-billed items), so an in-progress period may not yet appear "
    "in the bill.",
]

# ---------------------------------------------------------------------------
# Resource-package / coupon deduction failure reasons
# (readable version: references/billing-attribution-bill-check__deduction-matrix.md). No read-only inventory
# API is whitelisted for this skill, so C7/C8 run in DEGRADED mode: reasons
# are classified from the bill triple (payable / deducted / paid) plus
# user-stated package facts.
# ---------------------------------------------------------------------------

DEDUCTION_FAILURE_REASONS = [
    {"id": "type_mismatch",
     "rule": "Package type does not match the charged billing item (e.g. an "
             "OSS storage package never offsets egress traffic or data "
             "retrieval; a CDN package never offsets ECS public traffic; the "
             "ECS file-backup free quota covers Cloud Backup only, not ECS "
             "snapshots)."},
    {"id": "redundancy_mismatch",
     "rule": "Storage packages strictly distinguish redundancy type and "
             "never cross-deduct (Standard-LRS package vs ZRS-billed usage, "
             "and vice versa). ECS snapshot storage is deductible by a "
             "Standard-LRS storage package."},
    {"id": "region_mismatch",
     "rule": "Region-scoped packages never deduct other regions' usage; "
             "snapshot deduction is same-region; a 'mainland common' package "
             "does not cover Hong Kong / Macau / overseas."},
    {"id": "quota_exhausted",
     "rule": "The package allowance is used up (e.g. a downlink traffic "
             "package fully consumed); everything after that bills "
             "pay-as-you-go until reset/renewal."},
    {"id": "coverage_gap",
     "rule": "Renewal gap: the old package was exhausted at hour X and the "
             "new one activates at hour X+n; usage inside the gap bills "
             "pay-as-you-go with no deduction."},
    {"id": "association_failed",
     "rule": "Compute-plan style packages only deduct instances created "
             "through the dedicated entry and stop deducting after any "
             "configuration change (upgrade/downgrade re-orders the "
             "instance)."},
    {"id": "policy_not_bound",
     "rule": "The limited-time-free auto-snapshot quota works only when the "
             "disk is BOUND to the free auto-snapshot policy; manual "
             "snapshots still bill normally."},
    {"id": "coupon_rules",
     "rule": "Coupons cannot offset already-issued bills: they apply only "
             "to bills/orders created after issuance. Pay-as-you-go bills "
             "consume eligible coupons automatically at settlement; prepaid "
             "orders filter usable coupons at the payment page. Some "
             "campaign coupons exclude pay-as-you-go specifications."},
]

# ---------------------------------------------------------------------------
# Console paths (readable version: references/billing-attribution-bill-check__bill-console-paths.md).
# Every URL below is verbatim from the evidence set - never fabricate one.
# ---------------------------------------------------------------------------

NON_ECS_BILLING_RULES = {
    "vod": {
        "rule": "ApsaraVideo VOD bills storage by the hour for the media files it "
                "holds, plus outbound traffic when they are played",
        "stop": "only after they confirm the media is unneeded and backed up, have "
                "them delete the media files themselves in the VOD console; storage "
                "keeps billing until the files are gone",
        "package": "VOD storage and traffic packages are bought per item",
        "scope": "a storage package does not offset the traffic item",
    },
    "dns": {
        "rule": "Alibaba Cloud DNS bills the paid edition as a subscription and the "
                "traffic-analysis / log-delivery features by usage",
        "stop": "have them turn off traffic analysis and log delivery in the DNS "
                "console; the paid edition itself is unsubscribed under Orders",
        "package": "the paid edition is per domain, not per account",
        "scope": "an edition bought for one domain does not cover another",
    },
    "dbs": {
        "rule": "Database Backup (DBS) bills the backup plan by storage and by the "
                "backup traffic it moves",
        "stop": "have them release the backup plan themselves in the DBS console "
                "(More > Release) and set the deleted-instance backup retention to "
                "Do not retain; deleting backups is irreversible",
        "package": "DBS storage packages are per region",
        "scope": "a plan released still leaves already-stored backups until they expire",
    },
    "ddos": {
        "rule": "Anti-DDoS bills the protected instance as a subscription, with "
                "pay-as-you-go elastic protection on top",
        "stop": "have them turn off elastic protection first, then unsubscribe the "
                "instance under Billing console > Orders; protection stops at once",
        "package": "elastic protection is billed only on the days it triggers",
        "scope": "unsubscribing removes the protection, not just the fee",
    },
    "sls": {
        "rule": "Simple Log Service bills stored log data, index traffic and read "
                "traffic separately",
        "stop": "have them shorten the Logstore retention or delete the Logstore "
                "themselves in the SLS console; data keeps billing until it expires",
        "package": "SLS resource packages are per item and per region",
        "scope": "a storage package does not offset index traffic",
    },
    "cms": {
        "rule": "CloudMonitor bills site-monitoring probes and custom metric "
                "reporting beyond the free quota",
        "stop": "have them delete the paid site-monitoring tasks and stop the custom "
                "metric reporting jobs in the CloudMonitor console",
        "package": "probe packages are bought per probe count",
        "scope": "basic host monitoring stays free; only the paid tasks bill",
    },
    "oss": {
        "rule": "OSS settles storage hourly; data left in a bucket keeps charging",
        "package_entry": "https://common-buy.aliyun.com/?commodityCode=ossbag",
        "package_choice": "the outbound-traffic package for the traffic item and the "
                          "standard locally-redundant storage package for capacity, "
                          "sized to the observed usage",
        "stop": "only after they confirm the data is unneeded and backed up, have "
                "them empty and delete the buckets themselves in the OSS console "
                "(irreversible, never done for them)",
        "package": "buy one resource package per item (storage, outbound traffic), "
                   "one year available",
        "scope": "a package cannot target one bucket - it auto-deducts buckets in "
                 "the same region matching type, region and redundancy",
    },
    "cdn": {
        "rule": "CDN bills outbound edge traffic by tier and settles hourly",
        "stop": "disable or remove the accelerated domain",
        "package": "traffic packages are region-scoped",
        "scope": "a package deducts only traffic in its matching area",
    },
    "acs": {
        "rule": "ACS bills the running container compute by the hour",
        "stop": "after they confirm no workload is left, have them delete the "
                "container instances and the cluster themselves",
        "package": "savings plans and resource packages deduct by matching spec",
        "scope": "a plan deducts only the compute family it covers",
    },
    "eci": {
        "rule": "ECI bills each container group by the hour while it exists",
        "stop": "after they confirm the workload is finished, have them delete "
                "every container group themselves",
        "package": "savings plans deduct by matching compute family",
        "scope": "a plan does not cover a family outside its scope",
    },
    "dms": {
        "rule": "DMS bills the pay-as-you-go management mode per instance",
        "stop": "have them switch the instance back to the free management mode "
                "in the DMS console after confirming the feature loss",
        "package": "management-mode packages are per-instance",
        "scope": "a package covers only the mode it was bought for",
    },
    "eip": {
        "rule": "an elastic IP holds a fee while it exists, even when it is idle",
        "stop": "have them release the address themselves in the VPC console; the release "
                "is blocked until they move it out of any shared bandwidth, unbind it from "
                "the cloud resource and remove its SNAT/DNAT entries",
        "package": "an address fee is not offset by an ECS traffic package",
        "scope": "releasing the instance does not release the address bound to it",
    },
    "sas": {
        "rule": "Security Center bills the pay-as-you-go feature set per protected asset",
        "console_entry": "https://yundun.console.aliyun.com/?p=sas#/overview/home/cn-hangzhou",
        "stop": "have them turn off the switches under Security Center console > "
                "Overview > Pay-as-you-go services after confirming the protection loss",
        "package": "resource packages deduct by matching feature and quota",
        "scope": "a package does not cover a feature outside its scope",
    },
    "bailian": {
        "rule": "Model Studio bills model calls by token and keeps no idle fee",
        "stop": "have them delete the API keys and stop the calling jobs "
                "themselves after confirming no business depends on them",
        "package": "token packages deduct by matching model family",
        "scope": "a package does not cover a model outside its family",
    },
    "nas": {
        "rule": "NAS bills the stored capacity of every file system hourly",
        "stop": "back up, then delete the file system and its mount targets",
        "package": "capacity packages are region- and type-scoped",
        "scope": "a package deducts only matching file systems in its region",
    },
}
NON_ECS_CONSOLE_FILTER = (
    "filter Bill Details by that product - the bill cannot be narrowed to one "
    "bucket or instance")
NON_ECS_FUND_FLOW_NOTE = (
    "; top-ups and refunds are under Billing console -> Fund Flow Detail")
CONSOLE_PATHS = {
    "fund-flow-detail": {
        "url": "https://billing-cost.console.aliyun.com/fortune/fund-flow/detail",
        "params": "",
        "purpose": "Fund-flow detail: every top-up, refund and settlement entry.",
    },
    "bill-detail-by-instance": {
        "url": "https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance",
        "params": "BillingCycle=YYYY-MM; StatisticItem=DEFAULT_CHARGE_ITEM|RESOURCE; StatisticCycle=MONTHLY",
        "purpose": "Per-instance / per-billing-item detail; filter day "
                   "granularity for daily traffic; CSV export here.",
    },
    "month-bill-overview": {
        "url": "https://billing-cost.console.aliyun.com/finance/month-bill/account",
        "params": "",
        "purpose": "Per-product monthly summary: payable / paid / due.",
    },
    "month-bill-by-product": {
        "url": "https://billing-cost.console.aliyun.com/finance/month-bill/product",
        "params": "",
        "purpose": "Bill overview grouped by product - which product is charging.",
    },
    "expense-detail-usercenter": {
        "url": "https://usercenter2.aliyun.com/finance/expense-report/expense-detail-by-instance",
        "params": "select statistic item and cycle (Day) in the page",
        "purpose": "Billing-item detail with unit price, usage and package deduction; "
                   "Day granularity for sizing a month; CSV export.",
    },
    "expense-report": {
        "url": "https://billing-cost.console.aliyun.com/finance/expense-report",
        "params": "",
        "purpose": "Expense report entry (after CDT upgrade filter product "
                   "= Cloud Data Transfer).",
    },
    "order-list": {
        "url": "https://billing-cost.console.aliyun.com/order/list",
        "params": "pageIndex / pageSize / timeRange",
        "purpose": "Orders incl. auto-renewal orders - distinguishes a "
                   "renewal payment from a post-paid settlement.",
    },
    "recharge": {
        "url": "https://usercenter2.aliyun.com/home",
        "params": "",
        "purpose": "Billing-center top-up entry.",
    },
    "cdt-overview": {
        "url": "https://cdt.console.aliyun.com/overview",
        "params": "select region",
        "purpose": "CDT traffic usage, updated hourly (not real time).",
    },
    "cloud-monitor-host": {
        "url": "https://cloudmonitornext.console.aliyun.com/hostMonitor/",
        "params": "AliHost=all",
        "purpose": "Host bandwidth curves for traffic-saturation windows.",
    },
    "actiontrail-events": {
        "url": "https://actiontrail.console.aliyun.com/cn-beijing/events",
        "params": "",
        "purpose": "Operation audit trail (who did what) - handoff aid.",
    },
    "ecs-console": {
        "url": "https://ecs.console.aliyun.com/home",
        "params": "servers / snapshots per region",
        "purpose": "ECS instances and snapshots inventory views; the trial free-quota "
                   "progress is on this overview page.",
    },
    "ecs-instance-list": {
        "url": "https://ecs.console.aliyun.com/server/region",
        "params": "switch the region at the top of the page one by one",
        "purpose": "Every instance that still exists in the account, per region.",
    },
}

# ---------------------------------------------------------------------------
# FAQ knowledge distilled from the real support tickets of this skill's
# scope (symptom wording kept close to what customers actually ask).
# ---------------------------------------------------------------------------

FAQ_CONSOLE_ENTRY = {
    "charged-while-stopped": "ECS console -> Instances (Stop Mode column) and "
                             "Billing console -> Bill Details filtered by instance id",
    "savings-stop": "ECS console -> Instances (Stop Mode column) and Billing console -> "
                    "Bill Details filtered by instance id",
    "disk-still-billed": "ECS console -> Storage & Snapshots -> Disks and "
                         "Billing console -> Bill Details (item: cloud disk)",
    "snapshot-free-quota": "ECS console -> Storage & Snapshots -> Snapshots and "
                           "Billing console -> Bill Details (item: snapshot capacity)",
    "snapshot-billing-stop": "ECS console -> Storage & Snapshots -> Snapshots "
                             "(https://ecs.console.aliyun.com/snapshot, switch "
                             "region) and Automatic Snapshot Policies "
                             "(https://ecs.console.aliyun.com/autoSnapshotPolicy/region)",
    "cross-region-snapshot-fee": "ECS console -> Storage & Snapshots -> "
                                 "Snapshots (switch region) and Billing console -> "
                                 "Bill Details",
    "coupon-not-applied": "Billing console -> Orders -> order detail (discounts and "
                          "coupons applied)",
    "free-trial-composition": "Billing console -> Orders -> order detail and the trial "
                              "center entry for the instance",
    "overdue-consequences": "Billing console -> Account Overview (arrears amount) and "
                            "the ECS instance list",
    "refund-split-channels": "Billing console -> Expenses and Costs -> the refund "
                             "order detail (fund components), then Fund Flow Detail",
    "traffic-not-traceable": "Billing console -> Bill Details (item: outbound traffic) "
                             "and the EIP console for the bound address",
    "traffic-alert": "Billing console -> Bill Details (item: outbound traffic) and the "
                     "EIP console for the bound address",
    "bill-detail-empty": "Billing console -> Bill Details (switch the billing cycle and "
                         "the account/region filter)",
    "subscription-postpaid": "Billing console -> Bill Details split by billing item",
    "settlement-caliber-change": "Billing console -> Bill Details (same billing item "
                                 "compared across two cycles) and Account Overview "
                                 "(frozen amount and available credit)",
    "resource-package-scope": "Billing console -> Resource Packages (coverage and "
                              "remaining quota) and Bill Details filtered by product",
    "plan-quota-remaining-but-charged": "Billing console -> Savings Plans (deduction "
                                        "detail per instance) and ECS console -> "
                                        "Instances (specification change history)",
    "postpaid-invoice-timing": "Billing console -> Invoices > Create by bill detail "
                               "(pre-paid orders) and Bill Details (issuance status "
                               "of the post-paid cycle)",
    "postpaid-cycle-provisional": "Billing console -> Bill Details (that cycle's "
                                  "payable and paid columns) and Account Overview "
                                  "(balance and outstanding amount)",
}
FAQ_CONSOLE_DEFAULT = ("Billing console -> Bill Details filtered by the instance "
                       "id and the billing cycle")
RULE_ONLY_TOPICS = ("postpaid-invoice-timing", "student-coupon-spec-scope",
                    "postpaid-cycle-provisional")
RELEASE_HOUR_INTENT_RE = (
    r"(?i)((已|都)?(释放|停用|关闭|关机|停机|删除).{0,20}(还|仍|一直|为什么|怎么).{0,8}(扣|计费|收费)"
    r"|(释放|停用|关闭|停机)了.{0,12}(扣|计费|收费)"
    r"|(没有使用|没用|未使用|没使用|没有用).{0,20}(扣|计费|收费)"
    r"|still.{0,20}(charg|bill))")
CHARGE_COMPLAINT_INTENT_RE = (
    r"(?i)(为什么|为啥|怎么会|为何|why).{0,20}(扣|计费|收费|费用)"
    r"|(还|仍|一直|每天|又|莫名|乱|多|异常|额外).{0,10}(扣|计费|收费)"
    r"|(扣费|扣款|收费).{0,8}(异常|不对|太多|很高|这么高)"
    r"|哪里.{0,6}(扣|收费|计费)"
    r"|(still|keeps?).{0,16}(charg|bill)")
RULE_FALLBACK_TOPICS = ("charge-source-unknown", "released-still-charged",
                        "snapshot-billing-stop", "stop-being-charged",
                        "traffic-fee-detail", "burstable-surplus")
RULE_TOPIC_ASKED_ITEM = {
    "snapshot-billing-stop": "snapshot_capacity",
    "traffic-fee-detail": "network_out",
}
FAQ_TOPIC_SUBJECT_RE = {
    "disk-still-billed": r"(?i)云盘|磁盘|数据盘|块存储|系统盘|disk",
    "snapshot-free-quota": r"(?i)快照|snapshot",
    "snapshot-billing-stop": r"(?i)快照|snapshot",
    "cross-region-snapshot-fee": r"(?i)快照|snapshot",
    "burstable-surplus": r"(?i)积分|surpluscredit|突发性能|无性能约束",
    "traffic-not-traceable": r"(?i)流量|带宽|traffic|bandwidth",
    "traffic-fee-detail": r"(?i)流量|带宽|traffic|bandwidth",
    "traffic-alert": r"(?i)流量|带宽|traffic|bandwidth",
    "no-package-left-until": r"(?i)流量|共享流量|traffic",
    "savings-stop": r"(?i)节省停机|经济停机|节省关机|节省模式|savings",
    "free-trial-composition": r"(?i)试用|免费|trial|free",
    "charged-while-stopped": r"(?i)停机|关机|停止|stopped|stop",
    "student-coupon-spec-scope": r"(?i)学生|校园|student",
}
COUPON_RULES_URL = "https://help.aliyun.com/zh/user-center/user-guide/faq-about-coupons"
STUDENT_COUPON_SPEC_SNAPSHOT = (
    "ecs.e-c1m1.large, ecs.u1-c1m2.large, ecs.e-c1m2.large, ecs.e-c1m4.xlarge, "
    "ecs.u1-c1m1.2xlarge, ecs.u1-c1m4.xlarge, ecs.c7.large, ecs.c7.xlarge, "
    "ecs.g9i.3xlarge, ecs.c7a.2xlarge, ecs.c7a.4xlarge, ecs.gn6i-c16g1.4xlarge")
INVOICE_CREATE_URL = (
    "https://billing-cost.console.aliyun.com/invoice/home/main/create-by-detail/aliyun")
REFUND_ENTRY_URL = "https://billing-cost.console.aliyun.com/refund/refund"
RECHARGE_URL = (
    "https://billing-cost.console.aliyun.com/fortune/fund-management/recharge")
# The customer asks WHY the money that landed is less than the refundable amount.
# That is an explanation request: appending a stop-loss remedy (release the
# instance, savings stop) answers a question they did not ask.
REFUND_EXPLAIN_INTENT_RE = (
    r"(?i)(退款|退回|可退|到账|实到|退的).{0,30}"
    r"(为什么|为何|怎么|说明|核对|明细|少|差|不一致|不对)"
    r"|(为什么|为何|怎么).{0,24}(退款|退回|到账|实到)"
    r"|(扣费|扣款|退款).{0,10}(说明|明细|核对)")
TOTALS_INTENT_RE = (
    r"(?i)(统计|汇总|总和|合计|全年|今年|一整年).{0,24}(费用|账单|消费|花了|多少钱)"
    r"|(应付|实付).{0,12}(哪|栏|列|区别|不一样)"
    r"|(多个|几个|两个|三个).{0,8}产品.{0,12}(费用|总和|汇总)")
STOP_ALL_INTENT_RE = (
    r"(?i)(关闭|关掉|停掉|停用|停止|退订|释放|清理).{0,20}"
    r"(其他|其它|别的|以外|之外|全部|所有).{0,12}(资源|产品|服务|计费|订阅)"
    r"|(ecs|服务器).{0,12}(以外|之外).{0,16}(资源|产品|服务|都|全)"
    r"|(其他|其它|别的).{0,10}(资源|产品|服务).{0,14}(关闭|关掉|停掉|停用|退订|都关)"
    r"|(账单|计费|收费).{0,6}(项目|项).{0,6}(太多|很多|多)")
NON_ECS_STOP_BRIEF = {
    "oss": "empty and delete the buckets in the OSS console",
    "rds": "release the pay-as-you-go instance in the RDS console",
    "eip": "release the address in the VPC console - an idle EIP still holds a fee, and the "
           "release is blocked until they move it out of any shared bandwidth, unbind it from "
           "the cloud resource and remove its SNAT/DNAT entries",
    "nat": "delete the gateway and its SNAT/DNAT entries in the VPC console",
    "waf": "release the instance in the WAF console; it bills per day, so billing "
           "ends T+1 after the release",
    "dms": "switch the instance back to the free management mode in the DMS console",
    "bailian": "delete every API key and stop the calling jobs - no calls, no fee",
    "nas": "delete the file system and its mount targets in the NAS console",
    "cdn": "disable or remove the accelerated domain in the CDN console",
    "hcs_sgw": "delete the file or block gateway in the Cloud Storage Gateway console",
    "csg": "delete the file or block gateway in the Cloud Storage Gateway console",
    "acs": "delete the container instances and the cluster in the ACS console",
    "eci": "delete every container group in the ECI console",
    "sas": "turn off the switches under Security Center console > Overview > "
           "Pay-as-you-go services",
    "vod": "delete the media files in the ApsaraVideo VOD console after backing them up",
    "dns": "turn off DNS traffic analysis and log delivery; unsubscribe the paid edition "
           "under Orders",
    "dbs": "release the backup plan in the DBS console and set the deleted-instance "
           "backup retention to Do not retain - deleting backups is irreversible",
    "ddos": "turn off elastic protection, then unsubscribe the Anti-DDoS instance under "
            "Orders; protection stops immediately",
    "sls": "shorten the Logstore retention or delete the Logstore in the SLS console",
    "cms": "delete the paid site-monitoring tasks and stop custom metric reporting",
}
STOP_ALL_ECS_ITEMS = ("snapshot_capacity", "disk_capacity", "disk_burst")
NON_ECS_SHORT_LABEL = {
    "oss": "OSS", "rds": "RDS", "eip": "EIP", "nat": "NAT Gateway",
    "waf": "WAF", "dms": "DMS", "bailian": "Model Studio", "nas": "NAS",
    "cdn": "CDN", "hcs_sgw": "Cloud Storage Gateway", "csg": "Cloud Storage Gateway",
    "acs": "ACS", "eci": "ECI", "sas": "Security Center",
    "vod": "ApsaraVideo VOD", "dns": "Alibaba Cloud DNS", "dbs": "DBS",
    "ddos": "Anti-DDoS", "sls": "SLS", "cms": "CloudMonitor",
}
STOP_ALL_DETAILED_PRODUCTS = 5
ASKED_PRODUCT_CUES = (
    (r"(?i)(云安全中心|安全中心|态势感知|(?<![a-z0-9])sas(?![a-z0-9]))", "sas"),
    (r"(?i)(云解析|(?<![a-z0-9])dns(?![a-z0-9]))", "dns"),
    (r"(?i)(数据库备份|(?<![a-z0-9])dbs(?![a-z0-9]))", "dbs"),
    (r"(?i)(数据管理|(?<![a-z0-9])dms(?![a-z0-9]))", "dms"),
    (r"(?i)(高防|ddos)", "ddos"),
    (r"(?i)(全站加速|加速域名|(?<![a-z0-9])cdn(?![a-z0-9])|(?<![a-z0-9])dcdn(?![a-z0-9]))", "cdn"),
    (r"(?i)(文件存储|(?<![a-z0-9])nas(?![a-z0-9]))", "nas"),
    (r"(?i)(对象存储|(?<![a-z0-9])oss(?![a-z0-9]))", "oss"),
    (r"(?i)(负载均衡|(?<![a-z0-9])slb(?![a-z0-9])|(?<![a-z0-9])clb(?![a-z0-9])|(?<![a-z0-9])alb(?![a-z0-9]))", "slb"),
    (r"(?i)(防火墙|(?<![a-z0-9])waf(?![a-z0-9]))", "waf"),
    (r"(?i)(日志服务|(?<![a-z0-9])sls(?![a-z0-9]))", "sls"),
    (r"(?i)(云监控|(?<![a-z0-9])cms(?![a-z0-9]))", "cms"),
    (r"(?i)(视频点播|(?<![a-z0-9])vod(?![a-z0-9]))", "vod"),
    (r"(?i)(弹性公网|(?<![a-z0-9])eip(?![a-z0-9]))", "eip"),
    (r"(?i)((?<![a-z0-9])rds(?![a-z0-9])|云数据库)", "rds"),
)
WHERE_CHARGE_INTENT_RE = (
    r"(?i)哪里.{0,6}(发生)?.{0,4}(扣款|扣费|收费|计费)"
    r"|具体在哪里|消费的具体时间|按小时.{0,6}(明细|查看|看)"
    r"|(哪个|哪些)(产品|服务|资源).{0,8}(扣|计费|收费)"
    r"|(where|which).{0,20}(charg|bill).{0,12}(from|coming)")
USAGE_DETAIL_INTENT_RE = (
    r"(?i)(流量|带宽|traffic|bandwidth).{0,16}(明细|详情|清单|用量|使用|为什么|这么高|很高|高)"
    r"|用量明细|(usage|traffic).{0,12}(detail|breakdown|report)")
QUERY_PATH_INTENT_RE = (
    r"(?i)(在哪里|在哪儿|哪里|哪儿|去哪|如何|怎么|怎样).{0,14}(查询|查看|查|看|找)"
    r"|(使用量|用量|明细|订购|订单|额度).{0,14}(在哪|哪里|怎么查|如何查|查询不到)"
    r"|(明细|账单).{0,8}(查询|查看)")
RESOURCE_INVENTORY_INTENT_RE = (
    r"(?i)(未释放|未删除|没有释放|没有删除|还有没有|是否还有|还剩下).{0,18}"
    r"(实例|服务器|资源|云盘|快照)"
    r"|(所有|全部|哪些).{0,10}(地域|区域).{0,12}(实例|资源)")
TRAFFIC_GENERATORS = (
    "every response the server sends out - web pages, images and file downloads, "
    "FTP transfers, API responses and backups pulled over the internet")
SNAPSHOT_PROGRESS_INTENT_RE = (
    r"(?i)(快照|snapshot).{0,24}(完成|好了|创建完|进度|成功|完了)"
    r"|(创建|做|打|建).{0,6}快照.{0,16}(完成|好了|进度|多久)")
SNAPSHOT_RECURRING_INTENT_RE = (
    r"(?i)(快照|snapshot).{0,26}(每月|每个月|一直|还是|仍|总是).{0,12}(扣|计费|收费)")
MONTHLY_ESTIMATE_INTENT_RE = (
    r"(?i)(不用|停机|停止|关机|停掉|不释放).{0,16}(一个月|每月|月).{0,10}(多少|钱|费用)"
    r"|(一个月|每月).{0,10}(多少钱|多少费用|费用是多少)")
CONVERSION_INTENT_RE = (
    r"(?i)(转|改|换|变).{0,6}(包月|包年包月|包年)"
    r"|(包月|包年包月).{0,12}(怎么|哪里|如何|设置|转)"
    r"|(按天|按量|按小时).{0,10}(扣费|计费|收费).{0,12}(不要|不想|改|转|换)"
    r"|不要按天扣费")
CONVERSION_DOC_URL = "https://help.aliyun.com/document_detail/49884.html"
DEFERRED_STOP_INTENT_RE = (
    r"(?i)延停|延期免停|欠费停机"
    r"|欠费.{0,24}(停机|关机).{0,20}(还|仍|为什么|为啥|怎么).{0,10}(扣|计费|收费)")
SETTLEMENT_INTENT_RE = (
    r"(?i)(账单|费用|扣费|扣款|金额|余额|代还|待还).{0,16}"
    r"(更新|未更新|没更新|延迟|滞后|不准|对不上|暂估|待还|代还|待支付|未出|没出)"
    r"|(更新|出账|结算|到账|出账单).{0,10}(太慢|很慢|慢|延迟|多久|什么时候|何时)"
    r"|(待还|代还|待支付|未结|暂估).{0,12}(账单|金额|费用|为什么|为啥)"
    r"|月结|次月.{0,8}(出|扣|账)|下个月.{0,8}(出|扣|账)"
    r"|(provisional|not yet issued|final bill)")
BILLING_ACCOUNT_URL = "https://billing-cost.console.aliyun.com/fortune/billing-account"
SNAPSHOT_DELETE_INTENT_RE = (
    r"(?i)(快照|snapshot).{0,30}(删|删除|删掉|清理|关闭|停止|退)"
    r"|(删|删除|清理|关闭).{0,12}(快照|snapshot)")
SPLIT_BILL_INTENT_RE = (
    r"(?i)(关联|对应|属于).{0,14}(块存储|云盘|磁盘|实例)"
    r"|(账单|明细).{0,16}(关联|对应)")
SPLIT_BILL_URL = "https://billing-cost.console.aliyun.com/finance/split-bill"

FAQ_TOPICS = {
    "postpaid-cycle-provisional": {
        "question": "I topped up and renewed, why is there still a large unpaid bill?",
        "answer": ("A post-paid cycle settles monthly, so the outstanding amount "
                   "shown now is this cycle's provisional usage total, not a slow "
                   "refresh. Topping up adds balance and renewing pays the next "
                   "pre-paid term; neither reduces usage already metered in this "
                   "cycle. The cycle's final bill is issued at 12:00 on the 3rd of "
                   "the next month and the exact amount is deducted then; bill rows "
                   "lag consumption by about 24 hours. Nothing has to be released "
                   "or stopped for this figure to settle."),
    },
    "plan-quota-remaining-but-charged": {
        "question": "My plan still has quota, why am I being charged?",
        "answer": ("A remaining plan balance does not guarantee deduction: a "
                   "compute savings plan only offsets the instance "
                   "specifications it covers, and a specification change "
                   "(upgrade/downgrade) re-orders the instance and can move it "
                   "outside that covered set. Read the plan's deduction detail "
                   "per instance: instances still being deducted need no action "
                   "and must NOT be released, while the changed instance bills "
                   "pay-as-you-go from the moment of the change. Compare the "
                   "specification before and after the change against the "
                   "plan's covered specification list (mainland plans cover a "
                   "limited list), top up the balance for the uncovered usage, "
                   "and note that an instance already released accrues no new "
                   "fee."),
    },
    "postpaid-invoice-timing": {
        "question": "Can I repay now and get the invoice immediately?",
        "answer": ("Post-paid invoice timing is fixed by the system and cannot "
                   "be advanced by repaying early - a post-paid bill becomes "
                   "invoiceable only after it is issued at 12:00 on the 3rd of "
                   "the next month. Clearing the outstanding amount now "
                   "prevents an arrears stop but does not make the amount "
                   "invoiceable any sooner, and there is no manual override. "
                   "Already-paid pre-paid (subscription) orders CAN be "
                   "invoiced now from Billing console > Invoices > Create by "
                   "bill detail; only the post-paid cycle has to wait for "
                   "issuance."),
    },
    "student-coupon-spec-scope": {
        "question": "My student coupon still has balance, why is it not used?",
        "answer": ("A student coupon only offsets the instance-specification fee "
                   "for a limited supported specification list; an instance whose "
                   "specification is outside that list bills at the normal "
                   "pay-as-you-go rate even while the coupon still has balance. "
                   "Read the instance's specification in ECS console > Instances "
                   "and compare it with the coupon's supported list before "
                   "assuming the coupon should apply; items other than the "
                   "instance specification are not covered by it."),
    },
    "resource-package-scope": {
        "question": "Is a resource package shared by all buckets or only some?",
        "answer": ("A resource package cannot be pointed at one bucket: it "
                   "auto-deducts every resource of the matching product in the "
                   "same region whose type and redundancy the package covers. "
                   "Buy one package per billing item (storage, outbound "
                   "traffic) because a package only offsets its own item. Bill "
                   "Details can be filtered by product, not narrowed to a single "
                   "bucket, so reconcile at product level and use the product's "
                   "own usage report for per-bucket detail."),
    },
    "settlement-caliber-change": {
        "question": "It never used to charge, why am I billed every month now?",
        "answer": ("Pay-as-you-go settlement changed: hourly amounts under "
                   "CNY 0.01 used to round down to nothing, but the bill is "
                   "now frozen from your available credit at issuance and "
                   "then accumulated, rounded down and deducted monthly, so "
                   "tiny charges add up and become payable. The "
                   "metering rate and the billing cycle did not change - only "
                   "when the rounding and the deduction happen. Compare the "
                   "same billing item across the two cycles to see which item "
                   "crossed the threshold, and release the resources you no "
                   "longer need to stop new metering."),
    },
    "charge-on-1st": {
        "question": "Why was I deducted money on the 1st of the month?",
        "answer": ("Pay-as-you-go bills settle monthly: the deduction at the "
                   "beginning of month N pays the month N-1 post-paid bill "
                   "(ECS usage, snapshot capacity, outbound traffic...). The "
                   "money is NOT for anything happening on the deduction day "
                   "- query billing cycle N-1 to attribute it. Separately, a "
                   "subscription instance may renew automatically the day "
                   "before expiry: check the order list for an auto-renewal "
                   "order."),
    },
    "charged-while-stopped": {
        "question": "My instance is stopped, why is it still charging?",
        "answer": ("Stopping is NOT releasing. A pay-as-you-go instance keeps "
                   "billing its specification while stopped in normal stop "
                   "mode. Economical (savings) stop suspends only the "
                   "instance spec, fixed-bandwidth and image-license fees - "
                   "cloud disks, snapshots, EIP and pay-per-traffic items "
                   "keep billing. Billing only fully ends after the resource "
                   "is released (destructive, manual, back up data first)."),
    },
    "savings-stop": {
        "question": "I enabled savings stop mode, why does the balance drop?",
        "answer": ("Under savings stop: suspended = instance specification, "
                   "fixed public bandwidth, image license. STILL BILLING = "
                   "system/data disks, snapshots, EIP holding fees and any "
                   "outbound traffic accrued before/around the stop plus the "
                   "previous cycle settling next month. Run the attribution "
                   "mode to list exactly which items are still in fee."),
    },
    "subscription-postpaid": {
        "question": ("My ECS is monthly subscription, why do post-paid bills "
                     "still appear?"),
        "answer": ("The subscription covers the instance spec (and bundled "
                   "fixed items). Anything metered separately still produces "
                   "post-paid rows: public bandwidth billed by traffic "
                   "(outbound only), snapshot chain capacity, extra disks. "
                   "That is why a Subscription instance shows up in the "
                   "post-paid bill list. Detect it: DescribeInstances "
                   "InternetChargeType=PayByTraffic on a Subscription "
                   "instance."),
    },
    "traffic-not-traceable": {
        "question": "Which addresses did my traffic go to? Who accessed me?",
        "answer": ("For data-privacy reasons the cloud side does NOT store or "
                   "provide historical per-connection traffic destinations or "
                   "source IPs for an ECS instance. The bill can only "
                   "attribute the fee to instance x day x outbound-traffic "
                   "item. For 'where did it go': check the business access "
                   "logs inside the guest, or evaluate Network Intelligence "
                   "Service flow analysis (pay-as-you-go, needs deliberate "
                   "activation), or an on-machine tool such as iftop "
                   "(live only, not retroactive). This is outside this "
                   "skill - hand off."),
    },
    "coupon-not-applied": {
        "question": "I have a coupon / voucher, why was the bill not offset?",
        "answer": ("A coupon only covers the products and instance types in its "
                   "own scope, so a specification outside that scope is never "
                   "discounted. It also never offsets an already-issued bill: it "
                   "applies only to orders or bills created after the coupon was "
                   "issued. Pay-as-you-go bills use eligible coupons "
                   "automatically at settlement time; prepaid orders show "
                   "usable coupons at the payment page. Campaign coupons "
                   "(e.g. student credits) may exclude pay-as-you-go "
                   "specifications entirely. Check the row fields "
                   "DeductedByCoupons / PretaxAmount for the truth per row."),
    },
    "free-trial-composition": {
        "question": "Is my free-trial server free forever?",
        "answer": ("'Free trial' is not a separate product: it is a "
                   "pay-as-you-go instance covered by a savings-plan style "
                   "allowance. After the allowance is used up or the plan "
                   "expires, the SAME instance bills pay-as-you-go and drains "
                   "the balance. If you no longer need it, back up data and "
                   "release it (manual, destructive)."),
    },
    "disk-still-billed": {
        "question": "I do not use this disk, why does it still bill?",
        "answer": ("A cloud disk bills from creation regardless of whether it "
                   "is attached or the instance runs. Unattached disks show "
                   "as a disk-capacity row whose resource ID maps to no "
                   "running instance. Deleting a disk is destructive and "
                   "irreversible: back up first, then delete manually."),
    },
    "snapshot-free-quota": {
        "question": ("I thought snapshots had a free quota, why is the "
                     "snapshot chain still billed?"),
        "answer": ("The limited-time-free quota applies ONLY to snapshots the "
                    "auto-snapshot policy creates for disks BOUND to that "
                    "policy. Manually created snapshots, and snapshots on "
                    "disks not bound, bill normally (first snapshot full, "
                    "then incremental). Snapshot operations (policy bind, "
                    "delete) belong to the snapshot-management skill."),
    },
    "bill-detail-empty": {
        "question": ("I clicked the 'details' link of a deduction record and "
                     "saw nothing."),
        "answer": ("Usually a wrong month or statistic dimension on the page, "
                   "not missing data: switch the bill month to the settlement "
                   "cycle (deduction on the 1st -> previous month), set the "
                   "detail page to per-billing-item (DEFAULT_CHARGE_ITEM) or "
                   "per-resource (RESOURCE) with MONTHLY cycle. The console "
                   "front-end behaviour itself is outside this skill."),
    },
    "multiple-amounts": {
        "question": ("Why do several different 'amounts due' appear for the "
                     "same period (payable / paid / due / unsettled)?"),
        "answer": ("They are different calibers: payable (PretaxAmount) is "
                   "what the cycle owes; paid is what was already settled; "
                   "due/unsettled is the remainder; the top bar of the bill "
                   "page may include other products. Reconcile field by "
                   "field with the attribution and settlement modes; if the "
                   "layers still disagree, the residual is a bill-system "
                   "question for backend review - we output the delta, we do "
                   "not guess it away."),
    },
    "current-month-reconcile": {
        "question": "Can I reconcile the bill of the current month?",
        "answer": ("No. Current-month figures are provisional until the "
                   "final bill at 12:00 on the 3rd of the next month, and "
                   "detail data itself lags ~24h (instance fields ~48h). "
                   "State this caliber before any number discussion."),
    },
    "burstable-surplus": {
        "question": "What is the 'SurplusCredit / excess credit' charge?",
        "answer": ("Burstable instances (t5/t6) have a baseline CPU "
                   "performance with credits; in unlimited mode, exceeding "
                   "the baseline consumes credits billed as the SurplusCredit "
                   "item. The bill may display the PRODUCT as 'ECS "
                   "subscription' while the actual billing ITEM is "
                   "SurplusCredit - read the item column."),
    },
    "cross-region-snapshot-fee": {
        "question": ("There is a snapshot fee in a region where I created no "
                     "instance, why?"),
        "answer": ("Snapshots copied cross-region bill in the DESTINATION "
                    "region (both same-region and cross-region copy of "
                    "snapshots create charges). Check who performed the copy "
                    "internally (ActionTrail handoff); delete unused copies "
                    "manually to stop further billing (irreversible)."),
    },
    "overdue-consequences": {
        "question": "What happens if the account goes overdue?",
        "answer": ("An overdue balance stops pay-as-you-go services at once, "
                   "and those ECS resources STOP billing while stopped; after "
                   "15 days overdue the system releases or unbinds them and "
                   "the data is unrecoverable. Top up in the billing center; "
                   "settling is a manual, customer-side action."),
    },
    "refund-split-channels": {
        "question": "The refund said one amount but less money arrived, why?",
        "answer": ("A refund goes back along the ORIGINAL payment channels: cash "
                   "to the bank card or Alipay account, and the voucher-deducted "
                   "part to the voucher balance. So the cash that lands is less "
                   "than the refund total; read the fund-component detail on the "
                   "refund order. If the refund exceeds the account's invoiceable "
                   "amount it is paid to the Alibaba Cloud account balance "
                   "instead. Whether a voucher is returned at all follows the "
                   "downgrade order confirmation page: the refund rules were "
                   "upgraded on 2026-02-09 and are rolling out in batches, so "
                   "this is reference only and the order page is authoritative "
                   "(https://help.aliyun.com/zh/user-center/"
                   "description-of-downgrade-refund-rules.md)."),
    },
    "traffic-alert": {
        "question": "Can I set an alarm that shuts the instance off when traffic exceeds a limit?",
        "answer": ("For pay-by-traffic public bandwidth there is no "
                   "customer-set traffic cap alarm that auto-stops billing; "
                   "overage drains the balance and the account simply goes "
                   "overdue. Cost options are: switch the bandwidth billing "
                   "mode to fixed bandwidth, or buy a shared traffic plan / "
                   "upgrade to CDT (see references/billing-attribution-bill-check__bill-console-paths.md for "
                   "entry points). All switches are manual console "
                   "operations outside this read-only skill."),
    },
    "no-package-left-until": {
        "question": ("How long can I pre-purchase traffic plans, and do they "
                     "cover everything?"),
        "answer": ("Shared traffic plans cover pay-by-traffic IPv4 outbound "
                   "traffic of instances with a fixed public IP only, and "
                   "the longest term sold is 1 year - a longer instance "
                   "remaining life must be covered by balance instead. CDT "
                   "upgrade brings a monthly 20 GB mainland free allowance "
                   "and tiered pricing. Buying is a manual commercial "
                   "action; this skill only attributes usage and amount."),
    },
    "auto-renew-deduction-schedule": {
        "question": ("Is automatic renewal deducted 9 days or 1 day before "
                     "expiry?"),
        "answer": ("Automatic renewal is first attempted 9 days before the "
                   "instance expires; if the deduction fails it retries once "
                   "a day until 1 day before expiry or until it succeeds. A "
                   "manual renewal placed before the automatic deduction date "
                   "resets the next renewal date to the new expiry date, so "
                   "the two dates customers see are the first attempt and the "
                   "last attempt of the same schedule."),
    },
    "charge-source-unknown": {
        "question": "I keep being charged and cannot tell what for.",
        "answer": ("The charge is located from the bill, not from the instance "
                   "list: Expenses and Costs > Bill Management > Bill Details "
                   "shows the product, the billing item and the resource ID of "
                   "every charged row, and its usage detail view carries the "
                   "metered quantity. The rows customers most often overlook "
                   "are snapshot chain capacity, outbound public traffic, a "
                   "kept cloud disk, an image licence row (ImageOS) and a "
                   "separate pay-as-you-go product such as Security Center. A "
                   "top-up settles outstanding arrears first, so the balance "
                   "can drop right after a recharge without any new usage."),
    },
    "released-still-charged": {
        "question": "I already released the instance, why am I still charged?",
        "answer": ("Releasing a pay-as-you-go instance stops new charges, but "
                   "pay-as-you-go bills are not settled in real time: the last "
                   "hourly cycle is still issued later, so one more bill after "
                   "the release is expected and is not a new charge. Compare "
                   "that bill's coverage period with the release time before "
                   "treating it as an anomaly. Anything still billing after "
                   "that period comes from a resource the release did not "
                   "remove, such as a kept snapshot or disk, or a separate "
                   "pay-as-you-go product such as Security Center, which has "
                   "to be closed on its own console."),
    },
    "snapshot-billing-stop": {
        "question": "Can snapshot billing be switched off?",
        "answer": ("There is no switch that turns snapshot billing off: "
                   "snapshots bill on snapshot-chain capacity times unit price times "
                   "duration, metered hourly with any part hour billed as a full "
                   "hour. The charge ends only after the automatic snapshot "
                   "policy is deleted AND the snapshots it already created are "
                   "deleted - deleting the policy does not remove them. Billing "
                   "is per region, so switch region and repeat. A shared "
                   "snapshot must be unshared first, one backing a custom image "
                   "needs that image deleted first, and a cloud-backup snapshot "
                   "is deleted in the whole-instance backup console. Deletion is "
                   "irreversible and removes those restore points, so verify a "
                   "backup first. Already-incurred post-paid usage is consumed "
                   "usage, not a refundable order."),
    },
    "stop-being-charged": {
        "question": "How do I stop the charges?",
        "answer": ("Only releasing a pay-as-you-go instance stops its compute "
                   "charge; stopping it does not, and savings stop mode "
                   "suspends the specification fee while disks and addresses "
                   "keep billing. Release deletes the data and cannot be "
                   "undone, so confirm a backup first. A subscription instance "
                   "cannot simply be released mid-term: it goes through the "
                   "unsubscribe and refund path instead."),
    },
    "traffic-fee-detail": {
        "question": "Why is the traffic fee high, and where is the free quota?",
        "answer": ("Only outbound public traffic is billed; inbound is free. "
                   "Under pay-by-traffic the charge follows the actual GB, so "
                   "a busy or attacked site raises it sharply, while fixed "
                   "bandwidth caps it at the bandwidth price instead. Ask "
                   "which plan the customer believes carries a free traffic "
                   "quota and read that plan's own usage page: the ECS bill "
                   "only shows the charged GB, not a plan's remaining "
                   "allowance."),
    },
}

# ---------------------------------------------------------------------------
# Handoff map: symptom -> out-of-scope owner (readable version:
# references/billing-attribution-bill-check__handoff-map.md). This skill performs the ATTRIBUTION only, then
# hands off with an evidence pack.
# ---------------------------------------------------------------------------

HANDOFF_RULES = [
    {"symptom": "where did the traffic go / who accessed me / attack forensics",
     "target": "network-traffic troubleshoot skill or manual guest analysis; "
               "NIS flow analysis (paid) / iftop (live) - cloud side keeps "
               "no per-connection history for privacy"},
    {"symptom": "fee waiver / refund / coupon issuance / price negotiation",
     "target": "human commercial handling (duty or business manager); never "
               "promise cancellation of accrued fees"},
    {"symptom": "change billing mode / renew / upgrade / buy or unsubscribe "
                "packages / release resources / delete snapshots or disks",
     "target": "manual console operation by the customer (this skill is "
               "read-only); guidance + risk notes only"},
    {"symptom": "who performed an operation (release, renewal payment) and "
                "when",
     "target": "ActionTrail + backend ticket; API-level operation "
               "attribution is out of cloud-side scope"},
    {"symptom": "another product's own billing rules (OSS redundancy "
                "packages, Security Center pay-as-you-go, CDN/ESA, backup)",
     "target": "attribute to product x item x amount here, then that "
               "product's channel"},
    {"symptom": "snapshot create/delete/policy binding operations",
     "target": "alibabacloud-ebs-disk-snapshot-management"},
    {"symptom": "bill-system data inconsistency after four-layer check",
     "target": "backend review ticket with the evidence pack"},
]

# ---------------------------------------------------------------------------
# Stop-billing manual guidance (readable version:
# references/billing-attribution-bill-check__stop-billing-guide.md). Guidance ONLY - never executed here.
# ---------------------------------------------------------------------------

STOP_BILLING_GUIDE = [
    {"item": "pay-as-you-go instance",
     "action": "back up data, then release it in the ECS console (manual)",
     "risk": "releasing is irreversible; local disks, disks set to release "
             "with the instance, and auto snapshots released with those "
             "disks all go with it"},
    {"item": "unattached cloud disk",
     "action": "confirm it is unused, snapshot or copy the data, then delete "
               "the disk (manual)",
     "risk": "data unrecoverable after deletion"},
    {"item": "snapshots",
     "action": "delete unwanted snapshots / unbind auto-snapshot policies via "
               "the snapshot-management skill guidance",
     "risk": "deleted snapshots cannot be recovered"},
    {"item": "pay-per-traffic bandwidth",
     "action": "switch to fixed bandwidth, or buy a shared traffic plan / "
               "CDT package (manual purchase actions)",
     "risk": "changing the billing mode itself triggers a fee-change order; "
             "quotes/discounts are commercial handling"},
    {"item": "other products found during attribution (Security Center etc.)",
     "action": "turn off that product's pay-as-you-go switches in its own "
               "console",
     "risk": "resource packages of that product that expire/re-exhaust after "
             "enabling a pay-as-you-go feature keep producing bills"},
]

# ---------------------------------------------------------------------------
# Inline self-checks for pure data invariants (never raise at import time
# unless the constants file itself is broken).
# ---------------------------------------------------------------------------

assert SKILL_NAME.startswith("alibabacloud-ecs-")
assert MAX_DAILY_DAYS <= 31
assert len(TIMING_CALIBER) >= 4
assert all(("names" in v and "label" in v) for v in BILLING_ITEMS.values())
