#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for DB Cost Diagnosis
===========================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (DB product catalog, instance-id prefix map,
billing-item catalog, cost-driver suggestions, thresholds) is embedded here
as Python constants. There are NO data files in this skill.
"""

# ---------------------------------------------------------------------------
# BSS (Billing) API metadata
# ---------------------------------------------------------------------------

# Central BSS OpenAPI endpoint (region-less billing service).
BSS_ENDPOINT = "business.aliyuncs.com"
# Central STS endpoint (region-less).
STS_ENDPOINT = "sts.aliyuncs.com"
# Central CloudMonitor (CMS) OpenAPI endpoint (verified reachable).
CMS_ENDPOINT = "metrics.aliyuncs.com"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "bssopenapi": "2017-12-14",
    "sts": "2015-04-01",
    "cms": "2019-01-01",
}

# ---------------------------------------------------------------------------
# Pagination / query limits
# ---------------------------------------------------------------------------

# Max records per BSS bill page (API maximum for MaxResults is 300).
MAX_RESULTS = 300
# Hard guardrail on the number of pages fetched per query loop.
MAX_PAGES = 20

# Page size used by PageNum-style BSS APIs (QueryOrders max is 100).
ORDER_PAGE_SIZE = 100
# Page size used by QueryAvailableInstances (server max is 300).
INSTANCE_PAGE_SIZE = 300

# Paid-feature audit: only the top N highest-billed instances of a cycle get
# a per-item DescribeSplitItemBill drill-down (API-budget guardrail).
SPLIT_ITEM_TOP_N_INSTANCES = 10

# ---------------------------------------------------------------------------
# Cost anomaly detection thresholds
# ---------------------------------------------------------------------------

# Month-over-month relative increase above this percentage flags an anomaly.
ANOMALY_THRESHOLD_PCT = 20.0
# OR absolute increase above this amount (CNY) flags an anomaly.
ANOMALY_THRESHOLD_ABS = 100.0

# ---------------------------------------------------------------------------
# Database product catalog (BSS product-code mapping)
# ---------------------------------------------------------------------------
# Canonical key -> display metadata. NOTE: DBS may surface in BSS under
# product code "cbs" OR "dbs"; both are normalized to the canonical "cbs".
DB_PRODUCTS = {
    "rds": {
        "bss_product_code": "rds",
        "name": "RDS",
        "sub_products": ["MySQL", "SQL Server", "PostgreSQL", "MariaDB"],
        "prefixes": ["rm-", "rr-", "pgm-"],
        "note": ("The rm-/rr-/pgm- prefixes cover MySQL / SQL Server / "
                 "PostgreSQL / MariaDB; use the Engine field to tell them apart."),
    },
    "dds": {
        "bss_product_code": "dds",
        "name": "MongoDB",
        "sub_products": ["Replica Set", "Sharded Cluster", "Standalone"],
        "prefixes": ["dds-"],
    },
    "kvstore": {
        "bss_product_code": "kvstore",
        "name": "Tair (Redis)",
        "sub_products": ["Standard", "Cluster", "Read/Write Splitting"],
        "prefixes": ["r-"],
    },
    "polardb": {
        "bss_product_code": "polardb",
        "name": "PolarDB",
        "sub_products": ["PolarDB MySQL", "PolarDB PostgreSQL", "PolarDB-X"],
        "prefixes": ["pc-", "pxc-"],
    },
    "dts": {
        "bss_product_code": "dts",
        "name": "DTS (Data Transmission Service)",
        "sub_products": ["Data Migration", "Data Synchronization", "Data Subscription"],
        "prefixes": ["dts-"],
    },
    "cbs": {
        "bss_product_code": "cbs",
        "name": "DBS (Database Backup)",
        "sub_products": ["Logical Backup", "Physical Backup"],
        "prefixes": [],
        "note": ("DBS may appear in BSS as product code 'cbs' or 'dbs'; "
                 "match both and normalize to 'cbs'."),
    },
    "cdt": {
        "bss_product_code": "cdt",
        "name": "CDT (Cloud Data Transfer)",
        "sub_products": ["Internet Data Transfer"],
        "prefixes": ["cdt-"],
        "note": ("CDT is an account-level transfer product aggregating "
                 "public-network traffic fees; bill rows may carry an empty "
                 "InstanceID, so trend aggregation relies on ProductCode."),
    },
}

# Simple pip-code -> display-name map (used by trend aggregation).
DB_PRODUCT_CODES = {
    "rds": "RDS",
    "dds": "MongoDB",
    "kvstore": "Tair (Redis)",
    "polardb": "PolarDB",
    "dts": "DTS",
    "cbs": "DBS",
    "dbs": "DBS",
    "cdt": "CDT",
}

# Every BSS product code that belongs to a database product (incl. the
# alternate 'dbs' alias for DBS).
ALL_DB_PRODUCT_CODES = ["rds", "dds", "kvstore", "polardb", "dts", "cbs",
                        "dbs", "cdt"]

# ---------------------------------------------------------------------------
# Instance-id prefix -> product identification
# ---------------------------------------------------------------------------
# prefix -> (canonical product code, display name).
# Order matters: longer / more specific prefixes are checked first.
INSTANCE_ID_PREFIX_MAP = {
    "rm-": ("rds", "RDS"),
    "rr-": ("rds", "RDS (Read-only)"),
    "pgm-": ("rds", "RDS PostgreSQL"),
    "dds-": ("dds", "MongoDB"),
    "pc-": ("polardb", "PolarDB"),
    "pxc-": ("polardb", "PolarDB-X"),
    "dts-": ("dts", "DTS"),
    "cdt-": ("cdt", "CDT"),
    # Checked LAST: the single-char "r-" prefix must not shadow "rm-"/"rr-".
    "r-": ("kvstore", "Tair (Redis)"),
}

# Ordered prefixes for matching (specific before generic).
INSTANCE_ID_PREFIXES_ORDERED = [
    "rm-", "rr-", "pgm-", "dds-", "pc-", "pxc-", "dts-", "cdt-", "r-",
]

# ---------------------------------------------------------------------------
# Common billing items per product (for interpretation of bill details)
# ---------------------------------------------------------------------------
BILLING_ITEMS_COMMON = {
    # Real BSS bills localize billing-item names (zh-CN account locale), so
    # the canonical English labels are paired with their verified Chinese
    # forms (embedded as \u escapes to keep this module pure ASCII).
    #   \u89c4\u683c           = instance spec
    #   \u5b58\u50a8\u7a7a\u95f4 = storage space
    #   \u5907\u4efd\u7a7a\u95f4 = backup space
    #   \u5b9e\u4f8b\u8d39       = instance fee
    #   \u5907\u4efd\u8d39       = backup fee
    "rds": [
        "Instance fee", "Storage fee", "Backup fee", "Read-only instance fee",
        "Database proxy fee", "Cross-region backup fee", "Auto scaling fee",
        "\u89c4\u683c", "\u5b58\u50a8\u7a7a\u95f4", "\u5907\u4efd\u7a7a\u95f4",
        "\u5b9e\u4f8b\u8d39", "\u5907\u4efd\u8d39",
    ],
    "dds": [
        "Instance fee", "Storage fee", "Backup fee",
        "Mongos fee", "Shard fee", "ConfigServer fee",
    ],
    "kvstore": ["Instance fee", "Bandwidth fee", "Global distributed cache fee"],
    "polardb": [
        "Compute node fee", "Storage space fee", "SQL Explorer fee",
        "Global Database Network fee", "Backup fee",
    ],
    "dts": ["Data migration fee", "Data synchronization fee", "Data subscription fee"],
    "cbs": ["Backup plan fee", "Backup storage fee", "Sandbox instance fee"],
    "cdt": ["Internet data transfer fee", "Resource plan deduction"],
}

# ---------------------------------------------------------------------------
# Cost-driver catalog: typical root causes and optimization suggestions
# ---------------------------------------------------------------------------
COST_DRIVERS = {
    "high_storage": {
        "description": "Storage fee takes an excessive share of the total cost.",
        "diagnostic_apis": ["rds:DescribeResourceUsage", "dds:DescribeBackupStorage"],
        "suggestions": [
            "Clean up unused data and historical tables.",
            "Tune log verbosity to reduce log space consumption.",
            "Consider data archiving (hot/cold tiering).",
            "Check for heavy fragmentation (e.g. OPTIMIZE TABLE).",
        ],
    },
    "high_backup": {
        "description": "Backup fee takes an excessive share of the total cost.",
        "diagnostic_apis": ["dds:DescribeBackupStorage", "rds:DescribeBackupPolicy"],
        "suggestions": [
            "Verify the backup retention period is reasonable (default 7 days; it can often be shortened).",
            "Check whether stale manual backups are left un-cleaned.",
            "Evaluate whether cross-region backup is truly necessary.",
            "Confirm backup compression is enabled.",
        ],
    },
    "high_instance": {
        "description": "Instance fee dominates (instance spec likely oversized).",
        "diagnostic_apis": ["rds:DescribeDBInstanceAttribute"],
        "suggestions": [
            "Evaluate whether the current spec exceeds actual demand.",
            "Check whether CPU/memory utilization stays below 30% long-term.",
            "Consider downscaling or switching to a Serverless mode.",
            "Look for idle instances that can be released.",
        ],
    },
    "auto_scaling": {
        "description": "Auto scaling is generating extra charges.",
        "diagnostic_apis": ["hdm:DescribeAutoScalingHistory", "hdm:DescribeAutoScalingConfig"],
        "suggestions": [
            "Check how often and how long auto-scaling is triggered.",
            "Evaluate whether the upper-bound setting is reasonable.",
            "Check whether frequent triggers cause cost fluctuation.",
        ],
    },
}

# ---------------------------------------------------------------------------
# CloudMonitor (CMS) load sampling for idle-instance auditing
# ---------------------------------------------------------------------------

# RDS metric names verified to exist in acs_rds_dashboard. NOTE: "CPUUsage"
# does NOT exist; the verified CPU metric is "CpuUsage".
CMS_METRICS_RDS = ["CpuUsage", "ConnectionUsage", "IOPSUsage", "DiskUsage"]
# CMS namespace that carries RDS instance-level metrics.
CMS_NAMESPACE = "acs_rds_dashboard"
# Sampling period in seconds (hourly points keep the payload small).
CMS_PERIOD = 3600
# Lookback window in days for the load sample.
CMS_WINDOW_DAYS = 7
# Max number of instance ids packed into one Dimensions array per call.
CMS_BATCH_SIZE = 50
# Guardrail on the number of CMS NextToken pages fetched per metric call.
CMS_MAX_PAGES = 20

# ---------------------------------------------------------------------------
# Idle-instance thresholds (all values are percentages)
# ---------------------------------------------------------------------------

# An instance is judged idle only when BOTH average utilizations stay below
# these thresholds over the sampling window.
IDLE_CPU_AVG_PCT = 5.0
IDLE_CONN_AVG_PCT = 5.0
# Share of hourly sample points that must sit below the thresholds for the
# instance to be judged idle (a brief spike must not mask a quiet baseline).
IDLE_LOW_POINT_RATIO = 0.8
# Instances that miss the idle bar but stay under this CPU average are
# reported as "low-load" (candidates for downscaling rather than release).
IDLE_LOW_LOAD_CPU_AVG_PCT = 15.0

# ---------------------------------------------------------------------------
# Renewal / order auditing
# ---------------------------------------------------------------------------

# Expiry-warning windows in days, widest first: an instance whose EndTime
# falls inside the first matching window gets that window label.
RENEW_LOCK_WINDOWS_DAYS = (90, 30, 7)
# Default lookback for the renewal order history (calendar months).
ORDER_LOOKBACK_MONTHS = 6
# Two adjacent renewals of the same commodity whose price ratio exceeds this
# multiplier are flagged as a renewal price spike.
RENEW_PRICE_SPIKE_RATIO = 3.0

# ---------------------------------------------------------------------------
# RDS engine version end-of-support (EOS) reference table
# ---------------------------------------------------------------------------
# Key = engine display version; value = {eos_date, status, source_url,
# snapshot_date}. Dates follow the official Alibaba Cloud lifecycle docs as
# read on the snapshot date below; "planned" dates may be revised upstream.
RDS_EOS_TABLE = {
    "MySQL 5.5": {
        "eos_date": "2021-12-08",
        "status": "end_of_support",
        "source_url": ("https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/"
                       "major-version-lifecycle-description"),
        "snapshot_date": "2026-08-26",
    },
    "MySQL 5.6": {
        "eos_date": "2028-02-05",
        "status": "planned_end_of_support",
        "source_url": ("https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/"
                       "support-for-apsaradb-rds-for-mysql-instances-that-run-"
                       "mysql-5-6-and-5-7-is-extended"),
        "snapshot_date": "2026-08-26",
    },
    "MySQL 5.7": {
        "eos_date": "2028-10-21",
        "status": "planned_end_of_support",
        "source_url": ("https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/"
                       "support-for-apsaradb-rds-for-mysql-instances-that-run-"
                       "mysql-5-6-and-5-7-is-extended"),
        "snapshot_date": "2026-08-26",
    },
    "MySQL 8.0": {
        "eos_date": None,
        "status": "no_end_of_support_planned",
        "source_url": ("https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/"
                       "major-version-lifecycle-description"),
        "snapshot_date": "2026-08-26",
    },
    "MySQL 8.4": {
        "eos_date": None,
        "status": "no_end_of_support_planned",
        "source_url": ("https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/"
                       "major-version-lifecycle-description"),
        "snapshot_date": "2026-08-26",
    },
    "SQL Server 2016": {
        "eos_date": "2026-07-14",
        "status": "end_of_patch_updates",
        "source_url": ("https://help.aliyun.com/zh/rds/apsaradb-rds-for-sql-server/"
                       "new-patches-are-no-longer-provided-for-apsaradb-rds-"
                       "instances-running-sql-server-2016"),
        "snapshot_date": "2026-08-26",
    },
}

# ---------------------------------------------------------------------------
# Paid-feature attribution map for billing-item keywords
# ---------------------------------------------------------------------------
# Case-insensitive keyword -> paid feature metadata; matching is a
# word-boundary substring match (no adjacent letters/digits), so short
# tokens cannot swallow unrelated items. Used by the paid-feature audit to
# attribute split-bill items to optional paid add-ons (as opposed to the
# mandatory base instance / storage / backup charges).
PAID_FEATURE_BILLING_MAP = {
    "sql audit": {"feature": "SQL Audit (SQL Explorer)",
                  "category": "observability",
                  "note": "Opt-in audit log storage; billed by retention and volume."},
    "sql explorer": {"feature": "SQL Audit (SQL Explorer)",
                    "category": "observability",
                    "note": "Same paid feature under its legacy billing name."},
    "performance insight": {"feature": "Performance Insight",
                             "category": "observability",
                             "note": "Extended performance data retention is a paid tier."},
    "cross-region backup": {"feature": "Cross-region Backup",
                             "category": "backup",
                             "note": "Charged on top of the standard local backup."},
    "database proxy": {"feature": "Database Proxy",
                       "category": "connection",
                       "note": "Dedicated proxy nodes are billed separately from the instance."},
    "db proxy": {"feature": "Database Proxy",
                 "category": "connection",
                 "note": "Compact billing label of the same Database Proxy feature."},
    "read-only instance": {"feature": "Read-only Instance",
                           "category": "compute",
                           "note": "Each read-only replica carries its own instance fee."},
    "readonly instance": {"feature": "Read-only Instance",
                          "category": "compute",
                          "note": "Hyphen-less spelling of the same read-only replica charge."},
    "auto scaling": {"feature": "Auto Scaling (storage/compute)",
                      "category": "elasticity",
                      "note": "Auto-expanded capacity is billed until shrunk back."},
    "sql collector": {"feature": "SQL Audit (SQL Explorer)",
                      "category": "observability",
                      "note": "Alternative billing label seen on some cycles."},
    "das service": {"feature": "DAS Pro (Database Autonomy Service)",
                    "category": "observability",
                    "note": "Paid autonomy/insight service tier."},
    # Localized (zh-CN) billing labels of the same optional paid features,
    # verified on real BSS split-item bills; kept as \u escapes so this
    # module stays pure ASCII.
    #   \u5f02\u5730\u5907\u4efd = cross-region backup (e.g. the
    #       "\u5f02\u5730\u5907\u4efd\u7a7a\u95f4" cross-region backup
    #       space item)
    #   \u53ea\u8bfb\u5b9e\u4f8b = read-only instance
    #   \u6570\u636e\u5e93\u4ee3\u7406 = database proxy
    #   SQL\u6d1e\u5bdf        = SQL audit / SQL explorer
    #   \u81ea\u52a8\u5f39\u6027 = auto scaling
    "\u5f02\u5730\u5907\u4efd": {
        "feature": "Cross-region Backup",
        "category": "backup",
        "note": "Localized billing label of the cross-region backup charge."},
    "\u53ea\u8bfb\u5b9e\u4f8b": {
        "feature": "Read-only Instance",
        "category": "compute",
        "note": "Localized billing label of a read-only replica charge."},
    "\u6570\u636e\u5e93\u4ee3\u7406": {
        "feature": "Database Proxy",
        "category": "connection",
        "note": "Localized billing label of the Database Proxy charge."},
    "SQL\u6d1e\u5bdf": {
        "feature": "SQL Audit (SQL Explorer)",
        "category": "observability",
        "note": "Localized billing label of the SQL audit charge."},
    "\u81ea\u52a8\u5f39\u6027": {
        "feature": "Auto Scaling (storage/compute)",
        "category": "elasticity",
        "note": "Localized billing label of the auto-scaling charge."},
}
