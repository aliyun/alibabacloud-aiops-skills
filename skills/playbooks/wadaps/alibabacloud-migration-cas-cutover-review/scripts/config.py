#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cutover Manual Review Tool - Configuration File (v3.3)

Contains all customizable review standards, checklist items, synonym mappings, and other configurations.
Modify this file to customize review rules without changing the core code.

Configuration structure:
  1. Review Standards - ATA standard checklist items, critical nodes, critical elements
  2. Matching Rules - Synonym mappings, Sheet name matching, step ordering
  3. Scenario Checks - Batch/full/other scenario-specific check configurations
  4. Scoring Rules - Weights, risk level determination
  5. System Configuration - Input validation, file limits
"""

# =============================================================================
# 1. Review Standards
# =============================================================================

# ATA standard 6 major category checklist items
ATA_STANDARD_CATEGORIES = [
    "Business Investigation & Assessment",
    "Cutover Plan Design & Verification",
    "Environment & Resource Preparation",
    "Data Migration & Synchronization",
    "Monitoring & Emergency Preparation",
    "Organization & Communication Mechanism",
]

# Critical checklist items (missing any of these constitutes a fatal defect)
CRITICAL_CHECKLIST_ITEMS = [
    "Database Read-Only Setting",
    "Full Data Migration Completed",
    "Incremental Sync Pipeline",
    "Data Consistency Verification",
    "Reverse Sync Pipeline",
    "Kafka/MQ Consumption Confirmation",
    "Target Initial State Pre-description",
    "Service Restart Strategy",
    "Process Consistency Check (Stop/Resume Correspondence)",
]

# Critical cutover process nodes
CRITICAL_PROCESS_NODES = [
    "Database Read-Only Setting",
    "Incremental Data Catch-up",
    "Application Service Stop",
    "Final Data Consistency Verification",
    "Canary Strategy",
    "Rollback Decision Conditions",
    "Kafka Consumption Confirm/Stop",
    "Scheduled Task Stop",
    "Nginx Configuration Change",
    "Service Restart",
]

# Critical rollback plan elements
CRITICAL_ROLLBACK_ELEMENTS = [
    "Reverse Sync Pipeline",
    "Rollback Trigger Conditions",
    "Rollback Decision Process",
    "Data Consistency Guarantee",
    "Rollback Verification Steps",
    "Rollback Time Window",
]

# Data migration 8 key elements
DATA_MIGRATION_ELEMENTS = [
    "Full Migration",
    "Incremental Sync",
    "Consistency Verification",
    "Read-Only Setting",
    "DTS Configuration",
    "Bandwidth Throttling",
    "Time Estimation",
    "Pre-check",
]

# =============================================================================
# 2. Matching Rules
# =============================================================================

# Reasonable order of cutover steps (prerequisite step -> subsequent step)
REASONABLE_STEP_ORDER = [
    ("Environment Preparation", "Data Migration"),
    ("Full Data Migration", "Incremental Data Catch-up"),
    ("Incremental Data Catch-up", "Database Read-Only"),
    ("Database Read-Only", "Application Service Stop"),
    ("Application Service Stop", "Final Data Consistency Verification"),
    ("Final Data Consistency Verification", "Traffic Switch"),
    ("Traffic Switch", "Business Verification"),
    ("Business Verification", "Cutover Complete"),
]

# Synonym/expansion word mapping for enhanced fuzzy matching
SYNONYM_MAP = {
    "数据库只读设置": [
        "数据库只读", "DB只读", "设为只读", "ReadOnly", "只读模式",
    ],
    "全量数据迁移完成": [
        "全量迁移", "全量同步", "全量数据", "initial sync", "full migration",
    ],
    "增量同步链路": [
        "增量同步", "实时同步", "增量链路", "CDC", "binlog", "DTS增量",
    ],
    "数据一致性校验": [
        "一致性校验", "数据比对", "校验", "compare", "consistency check", "数据对比",
    ],
    "反向同步链路": [
        "反向同步", "回环同步", "反向链路", "reverse sync", "回滚同步", "阿里云到源端",
    ],
    "应用停服": [
        "停服", "停止服务", "停写", "stop service", "应用下线", "服务停止",
    ],
    "最终数据一致性校验": [
        "最终一致性", "割接后校验", "切换后校验", "final check",
    ],
    "灰度策略": [
        "灰度", "渐进式", "分批", "canary", "百分比切流", "灰度发布",
    ],
    "回滚决策条件": [
        "回滚条件", "回滚决策", "rollback trigger", "回滚阈值", "触发回滚",
        "回滚决策点", "流量转发前", "流量转发后", "回滚复杂度",
    ],
    "回滚触发条件": [
        "回滚触发", "触发条件", "rollback condition", "回滚指标",
    ],
    "回滚决策流程": [
        "决策流程", "决策链", "谁来决定", "decision process",
    ],
    "数据一致性保障": [
        "一致性保障", "数据不丢失", "不丢数据", "data integrity",
    ],
    "回滚验证步骤": [
        "回滚验证", "验证回滚", "rollback verify", "回滚后检查",
    ],
    "回滚时间窗口": [
        "回滚时间", "回滚时限", "rollback window", "回滚耗时",
    ],
    "Kafka消费确认": [
        "Kafka", "kafka", "卡夫卡", "消息队列", "消费确认", "MQ", "RocketMQ", "消息消费",
    ],
    "定时任务停止": [
        "定时任务", "XXL-Job", "xxl-job", "SchedulerX", "Cron", "cron", "任务调度", "定时停止",
    ],
    "目标端初始状态": [
        "初始状态", "目标端状态", "只读状态", "白名单", "初始只读", "阿里云状态",
    ],
    "服务重启策略": [
        "服务重启", "滚动重启", "两阶段启动", "服务启动顺序", "基础服务优先", "Pod启动",
    ],
    "预计耗时": [
        "预计耗时", "预估时间", "操作耗时", "预计时长", "耗时评估",
    ],
    "Nginx配置变更": [
        "Nginx", "nginx", "NGX", "ngx", "代理配置", "配置备份", "配置覆盖", "reload", "location", "proxy",
    ],
}

# Sheet name matching patterns
# v4.3.1: Added common naming conventions found in real manuals (cutover plan / operation manual / implementation steps / switchover process, etc.),
# reducing scenarios where --process-sheet / --rollback-sheet must be explicitly specified.
# Matching uses "longest match first" (see cutover_reviewer._map_sheets), so both
# broad terms (e.g., "流程") and precise terms (e.g., "生产环境割接流程") can coexist without interference.
SHEET_NAME_PATTERNS = {
    "checklist": [
        "checklist", "割接 checklist", "生产割接 checklist",
        "检查清单", "割接检查", "check list", "准备清单", "前置检查",
    ],
    "process": [
        # Cutover category
        "生产环境割接流程", "割接执行步骤", "割接操作步骤", "割接实施步骤",
        "割接流程", "割接步骤", "割接方案", "割接操作", "割接执行", "割接计划",
        # Switchover / go-live category
        "切换步骤", "切换流程", "切换方案", "上线步骤", "上线流程",
        # General implementation category
        "实施步骤", "实施方案", "操作手册", "操作步骤", "执行步骤", "变更步骤",
        # English
        "cutover process", "cutover steps", "cutover", "switchover",
        # Broad fallback (only effective when no more precise match exists)
        "流程", "步骤",
    ],
    "rollback": [
        "回滚执行步骤", "回滚操作步骤", "回滚实施步骤",
        "回滚步骤", "回滚方案", "回滚流程", "回滚操作", "回滚策略", "回滚计划",
        "回退步骤", "回退方案", "回退流程", "回切步骤", "回切方案",
        "rollback", "roll back", "fallback",
        "回滚", "回退",
    ],
    "domains": [
        "域名清单", "割接域名清单", "域名列表",
        "dns", "domain", "域名切换", "解析清单",
    ],
    "data_migration": [
        "数据迁移方案", "数据迁移", "数据同步", "迁移步骤",
        "data migration", "dts", "migration",
    ],
}

# Sheet type exclusion words (v4.3.1)
# If a Sheet name matches exclusion words here, it will not be mapped to the corresponding type.
# Typical issue: broad terms like "流程"/"步骤" in process would incorrectly absorb "回滚流程"/"回滚步骤" as cutover process,
# causing the rollback dimension to parse as 0 items (while cutover step count is inflated).
SHEET_NAME_EXCLUSIONS = {
    "process": ["回滚", "回退", "回切", "rollback", "roll back", "fallback", "checklist", "check list"],
    "rollback": [],
    "checklist": ["回滚", "回退", "rollback"],
    "domains": [],
    "data_migration": [],
}

# =============================================================================
# 2.4.1 Header Recognition Keywords (v4.2)
# =============================================================================
# Used to locate the actual header row within the first few rows of a Sheet.
# Some manuals have a title row as the first row (e.g., "CheckList", "割接步骤").
# If "first non-empty row = header" is assumed, it will be misidentified, causing the entire block to parse as 0 items.
# Instead: among the first N rows, select the row that matches the most HEADER_KEYWORDS as the header.
HEADER_KEYWORDS = [
    "工作阶段", "阶段", "事项", "操作事项", "具体实施步骤", "实施步骤", "步骤",
    "准备事项", "操作", "当前状态", "状态", "完成状态", "开始时间", "完成时间",
    "结束时间", "变更耗时", "耗时", "负责人", "操作人", "执行人", "检查人",
    "配合方", "责任人", "备注", "任务",
]

# Header detection range: only search for the actual header row within the first N rows of a Sheet (title rows are usually in the first 1-2 rows)
HEADER_SCAN_ROWS = 6

# =============================================================================
# 2.4.2 Content Focus Toggle (v4.2)
# =============================================================================
# True  = Risk identification focuses only on "operation items / implementation steps" content columns,
#         ignoring completeness deductions for management fields like executor / time / status / duration.
# False = Retains old behavior, also deducting for missing responsible person / completion time / operator / duration.
FOCUS_ON_STEP_CONTENT = True

# =============================================================================
# 2.5 Core Review Dimensions Configuration (v4.0)
# =============================================================================
# The following 5 dimensions apply to all cutover scenarios; each review must check and output conclusions for each one.
# Reference: "Dissecting Cloud Migration - Cutover Plan Review Guide"

CORE_REVIEW_DIMENSIONS = [
    {
        "id": "core_dim_1",
        "name": "Maintenance Notice",
        "description": "Check whether maintenance notice content is configured",
        "keywords": [
            "停机公告", "维护公告", "割接公告", "维护通知", "停机通知",
            "小程序公告", "Nginx公告", "公告挂载", "停机页面", "维护页面",
        ],
        "check_logic": (
            "If no maintenance notice is configured, remind the user to configure one to inform users of the maintenance time window. "
            "If a maintenance notice is configured, further confirm the mounting method: "
            "WeChat Mini Program (automatic interception) / Alipay Mini Program (does not intercept traffic) / Nginx mounting, "
            "and clarify the deployment location (source or target)."
        ),
        "severity": "HIGH",
        "category": "Core Dimension-Maintenance Notice",
        "sub_checks": [
            {
                "id": "core_dim_1_mount",
                "name": "Maintenance notice mounting method is clear",
                "keywords": ["微信小程序", "支付宝小程序", "Nginx挂载", "公告挂载方式", "公告部署"],
                "check_logic": "Confirm whether the mounting method and deployment location of the maintenance notice are clearly specified",
                "severity": "MEDIUM",
            },
        ],
    },
    {
        "id": "core_dim_2",
        "name": "Traffic Switch (Blocking Layer)",
        "description": "Check whether a blocking layer is configured, assess traffic switch risks",
        "keywords": [
            "阻流层", "阻流", "流量转发", "流量拦截", "流量转发层",
            "iptables", "NAT转发", "DNAT", "流量快速转发",
        ],
        "check_logic": (
            "If there is no blocking layer and only DNS resolution switching is used, warn: DNS resolution is affected by ISP caching, "
            "effective time is uncontrollable, subject to Local DNS hijacking and cannot be 100% effective, "
            "and sporadic traffic will continue hitting the source causing access anomalies. "
            "If there is a blocking layer, check whether there is a corresponding blocking function verification item, "
            "and remind that blocking function verification must be performed in advance."
        ),
        "severity": "CRITICAL",
        "category": "Core Dimension-Traffic Switch",
        "sub_checks": [
            {
                "id": "core_dim_2_dns_risk",
                "name": "DNS switch risk warning",
                "keywords": ["DNS", "dns", "域名解析", "DNS切换", "DNS生效", "Local DNS", "运营商缓存", "TTL"],
                "check_logic": "If only DNS switching without a blocking layer is used, must warn about uncontrollable DNS effective time risk",
                "severity": "CRITICAL",
            },
            {
                "id": "core_dim_2_verify",
                "name": "Blocking layer function verification",
                "keywords": ["阻流功能验证", "阻流层验证", "阻流测试", "阻流验证项", "转发验证"],
                "check_logic": "If there is a blocking layer but no verification item, remind that blocking function verification must be performed in advance",
                "severity": "CRITICAL",
            },
        ],
    },
    {
        "id": "core_dim_3",
        "name": "Source Database Read-Only",
        "description": "Check source database read-only settings and session management",
        "keywords": [
            "数据库只读", "ReadOnly", "read-only", "只读模式", "设为只读",
            "禁写", "禁止写入", "停写", "数据库禁写",
        ],
        "check_logic": (
            "If only the application is stopped without setting the database to read-only, warn: even if the application is stopped, "
            "other requests (scheduled tasks, background services, direct-connect scripts, etc.) may write to the database, "
            "causing incremental data to never catch up. "
            "If database read-only is set but without kill session, warn: kill session is needed to ensure "
            "existing long connections are cleaned up, otherwise existing connections may still write data. "
            "Note: Read-only should be set at the account level, not instance level, and must not affect DTS incremental sync."
        ),
        "severity": "CRITICAL",
        "category": "Core Dimension-Database Read-Only",
        "sub_checks": [
            {
                "id": "core_dim_3_kill_session",
                "name": "Kill session after read-only setting",
                "keywords": ["kill session", "杀会话", "终止会话", "kill 会话", "断开连接", "清理长连接"],
                "check_logic": "If read-only is set but no kill session, remind that kill session is needed to clean up existing long connections",
                "severity": "HIGH",
            },
            {
                "id": "core_dim_3_account_level",
                "name": "Read-only at account level not instance level",
                "keywords": ["账号维度", "账号级别", "不影响DTS", "DTS增量", "非实例级"],
                "check_logic": "Read-only should be set at account level, not instance level, and must not affect DTS incremental sync",
                "severity": "CRITICAL",
            },
        ],
    },
    {
        "id": "core_dim_4",
        "name": "Alibaba Cloud App Restart",
        "description": "Check Alibaba Cloud application restart strategy",
        "keywords": [
            "应用重启", "服务重启", "重启应用", "重启服务", "滚动重启",
            "Pod重启", "容器重启", "服务启动", "应用启动",
        ],
        "check_logic": (
            "If Alibaba Cloud applications have no restart action, warn: after Alibaba Cloud database restores read-write, "
            "check whether the application auto-reconnects; recommend verifying connection pool status. "
            "If Alibaba Cloud applications have a restart action, warn: pay attention to application startup duration "
            "and inter-dependencies between different applications; recommend two-phase startup "
            "(single Pod verification first, then batch scaling), with base services starting first."
        ),
        "severity": "HIGH",
        "category": "Core Dimension-App Restart",
        "sub_checks": [
            {
                "id": "core_dim_4_no_restart",
                "name": "Auto-reconnect check when no restart",
                "keywords": ["自动重连", "重连", "reconnect", "连接池", "连接恢复"],
                "check_logic": "When no restart action exists, remind to check whether the application auto-reconnects after database read-write restore",
                "severity": "HIGH",
            },
            {
                "id": "core_dim_4_has_restart",
                "name": "Startup dependencies and duration when restart exists",
                "keywords": ["启动时长", "服务依赖", "两阶段启动", "基础服务优先", "启动顺序", "Pod", "扩容"],
                "check_logic": "When restart action exists, remind to pay attention to startup duration and inter-application dependencies",
                "severity": "HIGH",
            },
        ],
    },
    {
        "id": "core_dim_5",
        "name": "Rollback Decision Conditions",
        "description": "Check whether rollback decision conditions are clearly defined",
        "keywords": [
            "回滚决策", "回滚条件", "回滚预案", "回滚方案", "触发条件",
            "回滚触发", "决策点", "回滚阈值", "回滚指标",
        ],
        "check_logic": (
            "If there are no rollback decision conditions, remind: whether rollback plan design and contingency preparation exist. "
            "Rollback decision conditions should be independent of operation steps; recommend setting two key decision points: "
            "1) Before traffic forwarding (quick rollback possible); 2) After traffic forwarding (rollback complexity significantly increases). "
            "After DNS switching, rollback is generally not performed; recommend delaying DNS switching to the next day."
        ),
        "severity": "CRITICAL",
        "category": "Core Dimension-Rollback Decision",
        "sub_checks": [
            {
                "id": "core_dim_5_decision_points",
                "name": "Structured rollback decision points",
                "keywords": ["流量转发前", "流量转发后", "决策点", "DNS切换后", "回滚复杂度"],
                "check_logic": "Rollback decision conditions should set two key decision points: before/after traffic forwarding",
                "severity": "HIGH",
            },
            {
                "id": "core_dim_5_plan",
                "name": "Rollback contingency preparation",
                "keywords": ["回滚预案", "回滚步骤", "回滚操作", "回滚验证", "反向同步"],
                "check_logic": "Confirm whether complete rollback contingency preparation exists",
                "severity": "CRITICAL",
            },
        ],
    },
]

# =============================================================================
# 3. Scenario Check Configuration
# =============================================================================

# Cutover scenario classification
CUTOVER_SCENARIOS = {
    "batch": {
        "name": "Application Database Batch Cutover",
        "description": "Applications are cut over in batches, with different batches executed in different time windows",
        "review_focus": "database_batch_focus",
    },
    "full": {
        "name": "Application Database Full Cutover",
        "description": "Application is cut over all at once, with all traffic switched simultaneously",
        "review_focus": "database_full_focus",
    },
    "other": {
        "name": "Other Scenario",
        "description": "Non-database cutover or other special scenarios",
        "review_focus": "other_focus",
    },
}

# Batch cutover review focus items (18 items)
DATABASE_BATCH_FOCUS = [
    {
        "id": "batch_1_1",
        "name": "Kill session required when restoring source database read-write",
        "keywords": ["kill session", "杀会话", "杀数据库会话", "终止会话", "kill 会话"],
        "check_logic": "If the cutover process has 'source database set to read-only' but no 'kill session' related action, remind the user that kill session is required when restoring read-write",
        "severity": "HIGH",
        "category": "Batch Cutover-Database Read-Only",
    },
    {
        "id": "batch_1_2",
        "name": "Database read-only must not be instance-level",
        "keywords": ["账号维度只读", "数据库账号维度", "不能实例级别只读", "不影响DTS", "DTS增量同步", "DTS反向同步"],
        "check_logic": "When setting source database to read-only, it must not be instance-level; only account-level operation is allowed, and it must not affect DTS incremental sync tasks or subsequent DTS reverse sync task startup",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Database Read-Only",
    },
    {
        "id": "batch_1_3",
        "name": "Redis read-only limitation (version 6.0+)",
        "keywords": ["Redis", "redis", "Redis只读", "Redis 6.0", "免密", "免用户名密码"],
        "check_logic": "Redis generally only supports account-level read-only from version 6.0+; if password-free access prevents setting read-only, alternative solutions need to be considered",
        "severity": "HIGH",
        "category": "Batch Cutover-Redis Scenario",
        "condition": "Triggered when Redis database is involved",
    },
    {
        "id": "batch_1_4",
        "name": "ElasticSearch cannot be set to read-only",
        "keywords": ["ElasticSearch", "ES", "elasticsearch", "白名单", "ES只读", "ES白名单"],
        "check_logic": "ElasticSearch cannot be set to read-only; only whitelist operations are possible, but restricting the whitelist will cause application connection failures and data consistency issues; confirm whether the business can accept this",
        "severity": "CRITICAL",
        "category": "Batch Cutover-ElasticSearch Scenario",
        "condition": "Triggered when ElasticSearch is involved",
    },
    {
        "id": "batch_1_5",
        "name": "Risk of dirty writes to Alibaba Cloud database",
        "keywords": ["阿里云数据库只读", "提前设置只读", "写脏", "被写入", "割接前只读"],
        "check_logic": "If Alibaba Cloud database is not set to read-only or whitelist adjusted in advance, there is a risk of dirty writes; recommend setting to read-only in advance, then restoring read-write during cutover and kill session to trigger reconnection",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Alibaba Cloud Database",
    },
    {
        "id": "batch_1_6",
        "name": "Kill session required when restoring Alibaba Cloud database read-write",
        "keywords": ["阿里云数据库恢复读写", "阿里云kill session", "阿里云杀会话", "阿里云恢复读写"],
        "check_logic": "If Alibaba Cloud database is set to read-only in advance but has no kill session action when restoring read-write, remind the user that kill session is required when restoring read-write",
        "severity": "HIGH",
        "category": "Batch Cutover-Alibaba Cloud Database",
    },
    {
        "id": "batch_1_7",
        "name": "App status check after Alibaba Cloud database read-write restore",
        "keywords": ["应用状态", "自动重连", "应用重连", "数据库恢复后检查", "应用是否正常"],
        "check_logic": "If Alibaba Cloud database is set to read-only in advance, monitor whether the application status is normal and whether the application auto-reconnects after database read-write restore",
        "severity": "HIGH",
        "category": "Batch Cutover-App Status",
    },
    {
        "id": "batch_1_8",
        "name": "Pre-check: cross-cloud access latency and bandwidth check",
        "keywords": ["跨云访问延时", "跨云网络带宽", "跨云延时", "网络带宽检查", "阿里云数据库只读状态", "阿里云应用状态"],
        "check_logic": "Pre-check items should include: application cross-cloud access latency check, cross-cloud network bandwidth check, whether Alibaba Cloud database is in read-only state, whether Alibaba Cloud application status is normal",
        "severity": "HIGH",
        "category": "Batch Cutover-Pre-check",
    },
    {
        "id": "batch_1_9",
        "name": "Highlight warning when no reverse sync exists",
        "keywords": ["反向同步", "无反向同步", "反向链路", "回滚数据丢失", "会议纪要", "客户确认"],
        "check_logic": "If there is no database reverse sync, highlight with red warning: without reverse sync, data generated during cutover will be lost upon rollback; this must be confirmed with the customer and documented in meeting minutes",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Reverse Sync",
    },
    {
        "id": "batch_1_10",
        "name": "Reverse sync pipeline pre-check",
        "keywords": ["反向同步链路创建", "反向同步预检查", "反向同步未启动", "源端迁移账号写入权限", "预检查通过但未启动"],
        "check_logic": "If database reverse sync exists, confirm that the reverse sync pipeline is created in advance and pre-check passes but is not started, and that the pre-check includes source migration account write permissions",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Reverse Sync",
    },
    {
        "id": "batch_1_11",
        "name": "Kafka/message middleware consumption confirmation",
        "keywords": ["Kafka", "kafka", "卡夫卡", "消息队列", "消费确认", "消费完成", "消息堆积", "MQ", "RocketMQ", "RabbitMQ"],
        "check_logic": "Kafka consumption may not stop immediately after traffic stops; confirm: 1) Whether passive message sources like scheduled tasks still produce messages when no external traffic; 2) Whether Kafka consumption has completely stopped or finished; 3) Different message types need separate handling. In drills, residual Kafka messages have been observed; production message volumes are larger with higher risk",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Message Middleware",
    },
    {
        "id": "batch_1_12",
        "name": "Scheduled task stop method and duration",
        "keywords": ["定时任务", "定时任务停止", "XXL-Job", "xxl-job", "SchedulerX", "schedulerx", "Cron", "cron", "定时停止", "任务调度", "批量停止"],
        "check_logic": "Confirm the specific method for stopping scheduled tasks (console one-by-one / batch operation / API call), and estimate duration accordingly. Experience case: hundreds of scheduled tasks clicked one by one may take about 30 minutes. The stop method directly impacts estimated duration",
        "severity": "HIGH",
        "category": "Batch Cutover-Scheduled Tasks",
    },
    {
        "id": "batch_1_13",
        "name": "Target initial state pre-description",
        "keywords": ["阿里云初始状态", "目标端状态", "只读状态", "初始只读", "白名单", "Redis白名单", "MySQL只读", "初始状态说明"],
        "check_logic": "The cutover manual should pre-describe the initial state of each Alibaba Cloud component: MySQL/Redis initially in read-only state, Redis whitelist settings may cause massive errors on app startup, whether applications are initially starting or already started, whether scheduled tasks are pre-closed. Missing initial state description may cause on-site operators to misjudge",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Target Status",
    },
    {
        "id": "batch_1_14",
        "name": "Service restart strategy",
        "keywords": ["服务重启", "滚动重启", "滚动启动", "服务启动顺序", "基础服务", "两阶段启动", "Pod", "pod", "扩容", "服务依赖", "启动耗时"],
        "check_logic": "Confirm: 1) Total number of Alibaba Cloud services and time required for rolling restart (experience: at least 20 minutes in test environment); 2) Service dependency classification, base services should start first; 3) Recommend two-phase startup strategy - start one Pod per service to verify normal operation before batch scaling. Lesson learned: without phased startup, inter-dependent services may fail to start, total duration exceeding 1 hour",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Service Restart",
    },
    {
        "id": "batch_1_15",
        "name": "Estimated duration for cutover steps",
        "keywords": ["预计耗时", "预估时间", "操作耗时", "预计时长", "耗时评估", "时间估算"],
        "check_logic": "Each operation step in the cutover manual should include an estimated duration field for deviation analysis on cutover day. If actual duration significantly deviates from estimate, early warning can be issued. Missing estimated duration makes the cutover time window uncontrollable",
        "severity": "HIGH",
        "category": "Batch Cutover-Doc Standards",
    },
    {
        "id": "batch_1_16",
        "name": "Nginx/proxy layer configuration change standards",
        "keywords": ["Nginx", "nginx", "NGX", "ngx", "代理配置", "配置备份", "配置覆盖", "reload", "location", "proxy", "代理层"],
        "check_logic": "Nginx configuration changes must include the complete process: 1) Prepare new location and proxy configuration in advance; 2) Backup current configuration file; 3) Overwrite with new configuration; 4) Reload. Backup action must be explicitly documented (actual backup may exist but not documented). Nginx stop/reload strategy must be confirmed - whether to stop directly or forward to Alibaba Cloud first then stop",
        "severity": "HIGH",
        "category": "Batch Cutover-Proxy Config",
    },
    {
        "id": "batch_1_17",
        "name": "Big data consumption pipeline cutover",
        "keywords": ["大数据Kafka", "Flink", "flink", "实时作业", "Flink作业", "大数据消费", "消息同步", "消费者切换", "车辆上报"],
        "check_logic": "If the project involves independent big data system Kafka consumption (e.g., vehicle reporting data push), confirm: 1) Big data Kafka consumption stop method (shut down application services/Flink jobs), whether job count is inventoried; 2) During recovery phase, check whether Alibaba Cloud Kafka has message backlog, confirm message sync completion before switching consumers; 3) A better approach is to sync messages in advance (on-premises Kafka to Alibaba Cloud Kafka) and switch consumers to Alibaba Cloud side early, reducing cutover-day operation steps",
        "severity": "HIGH",
        "category": "Batch Cutover-Big Data Pipeline",
    },
    {
        "id": "batch_1_18",
        "name": "Process consistency check (stop/resume correspondence)",
        "keywords": ["停止服务", "启动服务", "停止不迁移", "启动不迁移", "流程对应", "恢复阶段", "上下文一致", "逻辑矛盾"],
        "check_logic": "Stop and resume steps in the cutover process must correspond one-to-one: 1) After stopping non-migrating services, the resume phase must have corresponding startup steps; 2) The restart position of non-migrating services should be reasonable (e.g., before restoring external traffic); 3) Non-migrating services sharing configuration/database/instances should point configuration to Alibaba Cloud resources before restart; 4) DNS switch timing should be before restoring external traffic, not after traffic restoration",
        "severity": "CRITICAL",
        "category": "Batch Cutover-Process Consistency",
    },
]

# Full cutover review focus items (6 items)
DATABASE_FULL_FOCUS = [
    {
        "id": "full_2_1",
        "name": "Maintenance notice check",
        "keywords": ["维护公告", "停机公告", "割接公告", "公告挂出", "维护通知"],
        "check_logic": "Check whether a maintenance notice is posted; if not, remind whether one is needed; if yes, confirm whether it is posted on the source or target side, or provided by the mini program itself, with details clarified",
        "severity": "HIGH",
        "category": "Full Cutover-Maintenance Notice",
    },
    {
        "id": "full_2_2",
        "name": "Refer to batch cutover review key points",
        "keywords": [],
        "check_logic": "Full cutover also needs to refer to batch cutover review key points (1.1-1.18) for inspection",
        "severity": "INFO",
        "category": "Full Cutover-Reference Check",
        "reference": "DATABASE_BATCH_FOCUS",
    },
    {
        "id": "full_2_3",
        "name": "Blocking layer check",
        "keywords": ["阻流层", "阻流", "流量转发", "DNS劫持", "Local DNS", "流量快速转发", "零星流量"],
        "check_logic": "Check whether a blocking layer exists; if not, remind whether to add one to quickly forward source traffic to Alibaba Cloud, otherwise DNS effective time is uncontrollable, subject to Local DNS hijacking and cannot be 100% effective, with sporadic traffic continuing to hit the source causing access anomalies",
        "severity": "CRITICAL",
        "category": "Full Cutover-Blocking Layer",
    },
    {
        "id": "full_2_4",
        "name": "Blocking layer verification check",
        "keywords": ["阻流功能验证", "阻流层验证", "阻流测试", "阻流验证项"],
        "check_logic": "If a blocking layer exists, check whether there is a corresponding blocking layer verification item; if not, must remind that blocking function verification needs to be performed in advance",
        "severity": "CRITICAL",
        "category": "Full Cutover-Blocking Layer Verification",
    },
    {
        "id": "full_2_5",
        "name": "Maintenance notice mounting method and traffic interception",
        "keywords": ["停机公告", "微信小程序", "支付宝小程序", "小程序停机公告", "流量拦截", "Nginx停机公告", "停机公告挂载", "公告挂载方式"],
        "check_logic": "Maintenance notices have multiple mounting modes that must be clearly specified in the manual: 1) WeChat Mini Program maintenance notice - auto-mounts and intercepts traffic; 2) Alipay Mini Program maintenance notice - does not intercept traffic, traffic flows naturally; 3) Nginx-mounted maintenance notice - must confirm deployment on source or target side. Different methods have completely different traffic control effects and must be selected based on actual architecture and clearly documented",
        "severity": "HIGH",
        "category": "Full Cutover-Notice Method",
    },
    {
        "id": "full_2_6",
        "name": "Structured rollback decision conditions",
        "keywords": ["回滚决策点", "回滚条件", "流量转发前", "流量转发后", "DNS切换后", "回滚复杂度", "决策条件"],
        "check_logic": "Rollback decision conditions should not be mixed into the operation steps table; they should be listed separately. Recommend setting two key decision points: 1) Before official traffic forwarding - if verification fails, quick rollback to original system is possible; 2) After traffic forwarding completion - rollback complexity significantly increases. Note that after DNS switching, rollback is generally not performed; recommend delaying DNS switching to the next day. Rollback steps need not list all operations in detail; only decision conditions need to be clarified",
        "severity": "CRITICAL",
        "category": "Full Cutover-Rollback Decision",
    },
    {
        "id": "full_2_7",
        "name": "Maintenance notice removal action",
        "keywords": ["摘除公告", "撤下公告", "移除公告", "下掉公告", "删除公告", "恢复生产后端", "切回生产后端", "切换到生产应用", "恢复正式业务", "摘除维护公告", "解除维护页"],
        "check_logic": "If a maintenance notice is configured, the cutover steps must have a corresponding 'remove notice' action. Normally after the blocking layer forwards traffic to Alibaba Cloud, the maintenance notice should be mounted on the Alibaba Cloud load balancer; when restoring traffic, there must be an action to 'switch traffic from maintenance notice backend server back to production application'. Only posting without removing the notice will cause users to still see the maintenance page after cutover completion",
        "severity": "CRITICAL",
        "category": "Full Cutover-Notice Removal",
    },
    {
        "id": "full_2_8",
        "name": "Source database read-only (stopping traffic does not mean no writes)",
        "keywords": ["源端数据库只读", "源端只读", "源库只读", "源端设置只读", "源端数据库设置只读", "关闭流量入口"],
        "check_logic": "Simply closing traffic entrance / blocking cannot guarantee no write requests to source database - scheduled tasks, background services, direct-connect scripts, and internal calls may still write to the database, causing incremental data to never catch up. Source database must be set to read-only (account level, not affecting DTS incremental sync) and kill session to clean up existing long connections, providing double insurance to ensure source stops writes",
        "severity": "CRITICAL",
        "category": "Full Cutover-Source Read-Only",
    },
    {
        "id": "full_2_9",
        "name": "OSS mirror back-to-origin plan",
        "keywords": ["镜像回源", "OSS回源", "回源规则", "回源配置", "镜像源站", "OSS源站", "回源地址"],
        "check_logic": "When OSS incremental migration is only started during cutover, the incremental catch-up duration must be assessed; uncontrollable duration will extend the service window. A safer approach is to configure OSS mirror back-to-origin in advance (back-to-origin to source object storage); objects not found on Alibaba Cloud side will be automatically pulled from origin, allowing external service on cutover day without waiting for incremental catch-up, with incremental data supplemented afterwards. If the manual only states 'start OSS incremental' without a back-to-origin plan or duration assessment, a key reminder is needed",
        "severity": "HIGH",
        "category": "Full Cutover-OSS Back-to-Origin",
    },
    {
        "id": "full_2_10",
        "name": "Leased line/network switch timing risk",
        "keywords": ["专线预切换", "提前切换专线", "专线已切换", "路由预切换", "网络预切换", "专线切换完成", "提前打通专线"],
        "check_logic": "Performing leased line/routing network changes within the cutover window is a high-risk action, easily extending cutover downtime due to network jitter and route convergence issues. Recommend completing leased line switching before the cutover window and verifying (pre-switch); on cutover day, only perform traffic switching. If leased line switching must be done within the window, clearly specify duration, verification method, and network rollback action",
        "severity": "HIGH",
        "category": "Full Cutover-Leased Line Switch",
    },
    {
        "id": "full_2_11",
        "name": "Database read-write restore method",
        "keywords": ["恢复读写方式", "白名单恢复", "账号只读恢复", "账号维度恢复", "解除只读方式", "恢复读写方法"],
        "check_logic": "When restoring database from read-only to read-write, the restore method must be clarified: whether through 'adjusting whitelist' or 'account-level read-only removal'. If whitelist was used to restrict writes before cutover, whitelist must be restored during recovery; if account-level read-only was used, remove that account's read-only setting and kill session to trigger reconnection. The two methods have different impact scopes and rollback paths; the manual must specify clearly to avoid on-site misoperation",
        "severity": "HIGH",
        "category": "Full Cutover-Read-Write Restore",
    },
    {
        "id": "full_2_12",
        "name": "Traffic restore plan",
        "keywords": ["恢复流量", "流量恢复方案", "恢复流量方案", "切回流量", "流量切回", "DNS恢复", "解除阻流", "关闭阻流层"],
        "check_logic": "The cutover manual must clarify the specific 'traffic restore' plan: is it direct DNS switch to restore? Or remove blocking layer/maintenance notice backend? Or switch load balancer backend back to production application? Different methods have different effective times and reversibility. Only writing 'cutover complete' without specifying the traffic restore path will cause missing closing actions and persistent sporadic traffic anomalies",
        "severity": "CRITICAL",
        "category": "Full Cutover-Traffic Restore",
    },
]

# Other scenario review focus items (basic checks)
OTHER_FOCUS = [
    {
        "id": "other_basic_1",
        "name": "Basic cutover process check",
        "keywords": [],
        "check_logic": "Perform basic cutover process standardization check (CheckList, cutover process, rollback plan)",
        "severity": "INFO",
        "category": "Other Scenario-Basic Check",
    },
]

# =============================================================================
# 3.5 Issue Aggregation and Convergence (v4.4)
# =============================================================================
# Background: Full cutover (full) scenario applies both "full cutover specific focus items + batch cutover focus items",
# combined with core dimension checks, critical process node checks, and rollback element checks. The same risk point
# can be matched from multiple sources (typically "database read-only" can produce 5-6 items). v4.4 introduces a topic aggregation layer:
#   1) Rewrite category prefixes by scenario, avoiding misleading "分批次割接-" prefix in full scenario;
#   2) Merge issues pointing to the same risk into a single topic;
#   3) Support conditional suppression (when the manual already has a certain action, derived reminders are not output);
#   4) Only "core risk topics" enter the must-confirm items, with a quantity cap.
# =============================================================================

# Category prefix rewrite: key is original prefix, value is the replacement prefix
# In full scenario, batch cutover focus items also apply, uniformly called "割接通用"
CATEGORY_PREFIX_REWRITE = {
    "full": {"Batch Cutover-": "General Cutover-", "Full Cutover-": "General Cutover-", "Core Dimension-": "General Cutover-"},
    "batch": {"Core Dimension-": "Batch Cutover-"},
    "other": {"Batch Cutover-": "General Cutover-", "Core Dimension-": "General Cutover-"},
}

# Maximum number of must-confirm items (excess items are downgraded to "items requiring attention")
MAX_MUST_CONFIRM_ITEMS = 10

# Issue topic normalization table
# Match target: concatenated string of `category + ' ' + message` (case insensitive)
# Order sensitive: more specific topics must be placed before more general topics
#   (e.g., topic_aliyun_db / topic_redis must precede topic_src_readonly,
#    otherwise items containing "只读" will all be absorbed by the latter)
# Field descriptions:
#   core     - True means core risk, eligible for "must-confirm items"
#   category - Classification suffix displayed in report (scenario prefix is automatically added during rendering)
#   risk     - Risk essence description (output as "specific issue")
#   advice   - Remediation advice (output as "remediation suggestion")
#   drop     - True means directly discard, not included in report (noise from time/personnel/document format issues)
ISSUE_TOPICS = [
    {
        "id": "topic_notice",
        "title": "Posting and removal of maintenance notice",
        "category": "Maintenance Notice",
        "core": True,
        "match_any": [
            "停机公告", "维护公告", "割接公告", "停机通知", "维护通知",
            "摘除公告", "公告挂", "停机页面", "维护页面",
        ],
        "risk": (
            "The maintenance notice must clearly specify both 'where it is mounted' and 'when it is removed'. "
            "The mounting location determines interception effectiveness "
            "(WeChat Mini Program auto-intercepts, Alipay Mini Program does not intercept, Nginx/load balancer requires manual configuration); "
            "if only posting without removal is specified, the notice will continue intercepting real user traffic after cutover completion."
        ),
        "advice": (
            "Specify in the manual the notice mounting location (source side or Alibaba Cloud load balancer/gateway), both posting and removal actions, "
            "and access verification steps after removal. If traffic is forwarded to Alibaba Cloud via the blocking layer, "
            "the notice is usually mounted on the Alibaba Cloud side, and the removal action must be bound to the 'traffic restore' step."
        ),
    },
    {
        "id": "topic_traffic_switch",
        "title": "Traffic switch: missing blocking layer, DNS-only switching is uncontrollable",
        "category": "Traffic Switch",
        "core": True,
        "match_any": [
            "阻流", "切流方式", "流量转发", "流量拦截", "dns切换", "dns 切换",
            "local dns", "域名解析", "iptables", "dnat",
        ],
        "risk": (
            "Relying solely on DNS switching, effective time is affected by ISP caching and Local DNS hijacking, "
            "cannot converge 100%, and sporadic traffic will continue hitting the source after cutover, "
            "causing access anomalies and dirty writes on the source."
        ),
        "advice": (
            "Add a blocking layer (source-side iptables DNAT / Nginx reverse proxy) to forcibly forward residual traffic to Alibaba Cloud; "
            "and add a pre-cutover blocking function verification step to confirm the forwarding path and rollback method are available."
        ),
    },
    {
        "id": "topic_redis",
        "title": "Read-only limitations of Redis and other cache instances",
        "category": "Cache Read-Only",
        "core": False,
        "match_any": ["redis", "tair", "缓存只读", "memcache"],
        "risk": "Redis generally only supports account-level read-only from version 6.0+; lower versions cannot restrict writes at the account level.",
        "advice": "Confirm source Redis version and read-only implementation method (account read-only / whitelist tightening / application-side write stop); lower versions need to use whitelist or stop application as fallback.",
    },
    {
        "id": "topic_aliyun_db",
        "title": "Alibaba Cloud database early read-only and read-write restore",
        "category": "Alibaba Cloud DB",
        "core": False,
        "match_any": ["阿里云数据库", "目标端数据库只读", "目的端数据库只读"],
        "risk": "If Alibaba Cloud applications are already running before cutover, the target database has a risk of early dirty writes and needs to be set to read-only in advance, then restored to read-write during cutover.",
        "advice": "Set Alibaba Cloud database to read-only in advance (or tighten whitelist); restore read-write during cutover and kill session to trigger application reconnection; check application status after restoration.",
    },
    {
        "id": "topic_src_readonly",
        "title": "Source write stop: app shutdown + database read-only + kill session",
        "category": "Source Read-Only",
        "core": True,
        "match_any": [
            "源端只读", "数据库只读", "只读设置", "只读", "禁写", "禁止写入",
            "kill session", "杀会话", "终止会话", "长连接", "应用停服",
            "停止应用", "恢复读写", "readonly",
        ],
        "risk": (
            "Closing traffic entrance or stopping applications does not mean no writes to the source: scheduled tasks, "
            "background resident services, direct-connect scripts, and existing long connections may still write to the database, "
            "causing incremental data to never catch up and data inconsistency after cutover."
        ),
        "advice": (
            "Set source database to read-only at account level (do not use instance-level read-only, as it affects DTS incremental and subsequent reverse sync), "
            "then kill session to clean up existing long connections, and use 'incremental delay equals 0' as the criterion to proceed to the next step; "
            "the manual must specify whether the read-write restore method is removing account read-only or restoring whitelist."
        ),
    },
    {
        "id": "topic_aliyun_app",
        "title": "Alibaba Cloud app startup and restart strategy",
        "category": "App Startup",
        "core": True,
        "match_any": [
            "应用重启", "服务重启", "重启应用", "重启服务", "滚动重启",
            "pod", "容器重启", "服务启动", "应用启动", "扩容",
        ],
        "risk": (
            "If startup order, startup duration, and dependencies of Alibaba Cloud applications are not clarified, "
            "inter-dependent services may easily fail to start, with total duration far exceeding estimates "
            "(measured to exceed 1 hour in practice), directly blowing through the downtime window."
        ),
        "advice": (
            "List the service startup inventory and dependency layers, with base services first; adopt two-phase startup "
            "(start single Pod to verify first, then batch scale); provide estimated duration and verification method for each batch."
        ),
    },
    {
        "id": "topic_reverse_sync",
        "title": "Missing reverse sync pipeline, rollback will lose data",
        "category": "Reverse Sync",
        "core": True,
        "match_any": ["反向同步", "反向回流", "反向链路", "回流链路"],
        "risk": (
            "Without reverse sync, business data generated on Alibaba Cloud after cutover cannot flow back to the source; "
            "if rollback is decided, data from this period will be directly lost."
        ),
        "advice": (
            "Create reverse sync pipeline (DTS reverse task) in advance and complete pre-check without starting; "
            "pre-check must cover source migration account write permissions; "
            "if the customer confirms no reverse sync, the conclusion that rollback means data loss must be documented in writing."
        ),
    },
    {
        "id": "topic_rollback_decision",
        "title": "Missing rollback decision criteria",
        "category": "Rollback Decision",
        "core": True,
        "match_any": [
            "回滚决策", "回滚条件", "回滚触发", "触发条件", "决策点",
            "回滚阈值", "回滚指标",
        ],
        "risk": "The manual does not provide rollback determination criteria and decision makers; on-site decisions can only rely on ad-hoc discussion, missing the rollback time window.",
        "advice": (
            "List a separate rollback decision criteria section in the manual (do not mix into operation steps table): "
            "specify rollback trigger conditions (data verification failure / critical business verification failure / incremental timeout not caught up), "
            "decision maker and decision time limit; recommend setting two decision points - before official traffic forwarding and before DNS switching, "
            "noting that after DNS switching, rollback is generally not performed."
        ),
    },
    {
        "id": "topic_traffic_restore",
        "title": "Missing traffic restore plan",
        "category": "Traffic Restore",
        "core": True,
        "match_any": ["恢复流量", "流量恢复", "放量", "开放流量", "恢复访问"],
        "risk": "The traffic restore method determines effective speed and reversibility; an unclear method will lead to ad-hoc decisions on-site with unclear rollback paths.",
        "advice": (
            "Specify the exact traffic restore action: direct DNS switch, remove blocking layer, "
            "or switch load balancer backend from maintenance notice back to production application; "
            "and supplement verification steps and rollback method for each approach."
        ),
    },
    {
        "id": "topic_data_consistency",
        "title": "Incremental catch-up and data consistency verification",
        "category": "Data Consistency",
        "core": True,
        "match_any": [
            "增量追平", "增量数据追平", "增量同步", "一致性校验", "数据一致性",
            "数据校验", "全量数据迁移",
        ],
        "risk": "Missing 'incremental catch-up criteria + final consistency verification before cutover' makes it impossible to prove data equivalence between both sides at traffic switch time; post-hoc investigation is extremely costly.",
        "advice": (
            "Supplement incremental delay zero observation method (DTS delay metric / business table watermark), "
            "and final consistency verification steps within the cutover window (row count comparison + key table sampling), "
            "with clear handling action when verification fails."
        ),
    },
    {
        "id": "topic_passive_write",
        "title": "Passive write sources (scheduled tasks / message consumption) not addressed",
        "category": "Passive Write Source",
        "core": True,
        "match_any": [
            "定时任务", "kafka", "消息中间件", "消费确认", "大数据", "rocketmq",
            "mq消费", "job", "调度任务",
        ],
        "risk": (
            "Scheduled tasks and message consumption may not stop after traffic is stopped; passive message sources "
            "will continue writing to the database; stopping a large number of scheduled tasks one by one may also "
            "consume a significant portion of the downtime window."
        ),
        "advice": (
            "Specify the stop method for scheduled tasks and message consumption (console batch / API / stop application) "
            "and estimated duration, completing before source read-only; confirm how consumption offsets will be resumed after cutover."
        ),
    },
    {
        "id": "topic_oss_backsource",
        "title": "OSS mirror back-to-origin and incremental catch-up",
        "category": "Object Storage",
        "core": False,
        "match_any": ["oss", "镜像回源", "对象存储", "回源"],
        "risk": "Starting object storage incremental migration within the cutover window without mirror back-to-origin will result in un-synced objects returning 404.",
        "advice": "Configure OSS mirror back-to-origin to source object storage in advance, and assess incremental catch-up duration to avoid compressing large-volume object sync into the downtime window.",
    },
    {
        "id": "topic_network_switch",
        "title": "Leased line / network switch timing",
        "category": "Network Switch",
        "core": False,
        "match_any": ["专线", "路由切换", "网络切换", "vpn", "cen", "带宽"],
        "risk": "Performing network changes within the cutover window easily extends downtime, with long rollback paths on failure.",
        "advice": "Move leased line/routing changes before the cutover window, complete and verify in advance; on cutover day only perform traffic direction switching. If it must be done within the window, provide duration assessment and rollback plan.",
    },
    {
        "id": "topic_nginx",
        "title": "Nginx / proxy layer configuration change standards",
        "category": "Proxy Layer",
        "core": False,
        "match_any": ["nginx", "代理层", "反向代理", "location", "proxy"],
        "risk": "Proxy layer configuration changes without backup and rollback make quick recovery impossible when changes go wrong.",
        "advice": "Write the complete change process: prepare new configuration in advance -> backup current configuration file -> overwrite -> reload -> verify, and clarify the basis for choosing stop/reload.",
    },
    {
        "id": "topic_precheck",
        "title": "Incomplete cutover pre-check items",
        "category": "Pre-check",
        "core": False,
        "match_any": ["前置检查", "跨云访问延时", "跨云网络", "延时检查", "预检查"],
        "risk": "Missing pre-check items will leave problems that could have been found early to surface within the cutover window.",
        "advice": "Pre-checks should at minimum cover: application cross-cloud access latency, cross-cloud network bandwidth, target database status, and target application status.",
    },
    {
        "id": "topic_rollback_completeness",
        "title": "Incomplete rollback plan elements",
        "category": "Rollback Plan",
        "core": False,
        "match_any": ["回滚验证", "回滚时间窗口", "回滚要素", "回滚步骤", "回滚方案", "回滚预案"],
        "risk": "Rollback plan missing verification steps and time window makes it impossible to confirm actual recovery after rollback execution.",
        "advice": "Supplement for rollback: execution steps, verification method, estimated duration and time window, and data handling instructions after rollback.",
    },
    {
        "id": "topic_process_consistency",
        "title": "Stop and resume step correspondence",
        "category": "Process Consistency",
        "core": True,
        "match_any": ["流程一致性", "停止/恢复", "对应性", "一一对应"],
        "risk": "Stop actions without corresponding resume actions leave services in a stopped state after cutover.",
        "advice": "Verify item by item: every stop/disable action has a corresponding start/release action in the resume phase.",
    },
    {
        "id": "topic_gray",
        "title": "Canary and batch verification strategy",
        "category": "Canary Strategy",
        "core": False,
        "match_any": ["灰度", "分批验证", "小流量"],
        "risk": "Without canary methods, traffic switch can only go full volume, maximizing impact when problems are exposed.",
        "advice": "Assess whether small traffic verification is possible first (by user/region/API dimension), and specify fallback verification method when canary is not feasible.",
    },
    # ---- The following topics are noise, directly discarded, not included in report ----
    {
        "id": "topic_doc_norm",
        "title": "Document standards reminders",
        "category": "Doc Standards",
        "core": False,
        "drop": True,
        "match_any": ["预计耗时", "文档规范", "填写率", "未填写负责人", "未填写完成时间", "责任人"],
    },
    {
        "id": "topic_monitoring",
        "title": "Monitoring and personnel reminders",
        "category": "Monitoring & Personnel",
        "core": False,
        "drop": True,
        "match_any": ["监控告警", "值守", "人员安排", "联系方式", "组织保障"],
    },
]

# Conditional suppression rules
# when_any matches against "full text of all Sheets under review"; rule takes effect when matched
# only_messages_any being empty means suppress the entire topic; non-empty means only suppress original entries within that topic that match these words
SUPPRESSION_RULES = [
    {
        "id": "suppress_aliyun_db_readonly",
        "topics": ["topic_aliyun_db"],
        "when_any": [
            "应用启动", "服务启动", "启动应用", "启动服务", "启动阿里云",
            "滚动重启", "拉起应用", "扩容 pod", "扩容pod",
        ],
        "only_messages_any": [],
        "reason": (
            "The cutover process already includes an Alibaba Cloud application startup action, indicating the target application "
            "is in a shut-down state before cutover, so there is no risk of early dirty writes; "
            "no need to require Alibaba Cloud database early read-only and read-write restore during cutover"
        ),
    },
    {
        "id": "suppress_app_restart_node_false_positive",
        "topics": ["topic_aliyun_app"],
        "when_any": [
            "应用启动", "服务启动", "启动应用", "启动服务", "滚动重启", "拉起应用",
        ],
        "only_messages_any": ["缺失关键流程节点"],
        "reason": "The manual already contains application/service startup actions; 'missing service restart node' is a false positive caused by keyword matching scope differences",
    },
]

# =============================================================================
# 4. Scoring Rules
# =============================================================================

# Cutover readiness scorecard weights
SCORING_WEIGHTS = {
    "checklist": 0.20,      # CheckList completeness
    "process": 0.25,        # Cutover process standardization
    "rollback": 0.25,       # Rollback plan feasibility
    "resource": 0.15,       # Resource allocation adequacy
    "monitoring": 0.10,     # Monitoring and emergency preparedness
    "organization": 0.05,   # Organizational assurance effectiveness
}

# Risk level determination criteria
RISK_LEVELS = {
    "low": {"min_score": 90, "max_score": 100, "label": "LOW", "recommendation": "Ready to proceed with cutover"},
    "medium": {"min_score": 70, "max_score": 89, "label": "MEDIUM", "recommendation": "Recommended to supplement and improve before proceeding"},
    "high": {"min_score": 50, "max_score": 69, "label": "HIGH", "recommendation": "Must be rectified and re-reviewed"},
    "critical": {"min_score": 0, "max_score": 49, "label": "CRITICAL", "recommendation": "Not recommended to proceed with cutover using this plan"},
}

# =============================================================================
# 5. System Configuration
# =============================================================================

# Input validation configuration
INPUT_VALIDATION = {
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "allowed_extensions": [".xlsx"],
    "min_sheet_count": 1,
    "max_sheet_count": 50,
}
