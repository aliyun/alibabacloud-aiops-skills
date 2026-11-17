#!/usr/bin/env python3
"""
_constants.py -- Embedded constants for the ECS billing-mode advisory skill
===========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI
default credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (API metadata, pagination limits, validation
patterns, and the guidance/FAQ knowledge base distilled from real support
tickets) is embedded as Python constants -- see `_knowledge.py` for the
guidance data. There are NO data files in this directory.
"""

# ---------------------------------------------------------------------------
# Skill identity (used for the observability User-Agent)
# ---------------------------------------------------------------------------
SKILL_NAME = "alibabacloud-ecs-billing-mode-selection"

# ---------------------------------------------------------------------------
# OpenAPI metadata (verified against aliyun CLI 3.4.5)
# ---------------------------------------------------------------------------
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# Central STS endpoint (region-less identity service).
STS_ENDPOINT = "sts.aliyuncs.com"

# Default region ONLY for the region-less STS identity call. Every ECS
# query MUST carry an explicit RegionId supplied by the agent -- this
# skill never silently guesses the customer's region.
DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Timeouts / pagination limits (MUST 7.6.1: every CLI call carries a timeout)
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT = 60   # seconds, per subprocess invocation
PAGE_SIZE = 50         # DescribeInstanceStatus page size (API max 100)
MAX_RESULTS = 100      # DescribeInstances MaxResults (API max 100)
MAX_PAGES = 20         # hard guardrail on pagination loops

# ---------------------------------------------------------------------------
# Input validation patterns (strict; anything else is rejected up-front so
# unvalidated text never reaches a CLI argument list)
# ---------------------------------------------------------------------------
REGION_ID_PATTERN = r"^[a-z][a-z0-9-]{2,29}$"
INSTANCE_ID_PATTERN = r"^i-[a-z0-9]{6,40}$"
ZONE_ID_PATTERN = r"^[a-z][a-z0-9-]{2,29}$"
INSTANCE_TYPE_PATTERN = r"^ecs\.[a-z0-9][a-z0-9.-]{1,40}$"

# ECS billing enums returned by DescribeInstances.InstanceChargeType
# (values verbatim from the official API parameter documentation).
CHARGE_TYPE_LABELS = {
    "PrePaid": "subscription (monthly/yearly, pre-paid)",
    "PostPaid": "pay-as-you-go (post-paid)",
}

# Lock reasons returned by DescribeInstances OperationLocks that are
# relevant to billing-mode decisions. A "financial" lock means the account
# is in arrears -- ticket evidence shows the console "convert to
# subscription" entry disappears while an account owes money.
ARREARS_LOCK_REASONS = {"financial"}
SECURITY_LOCK_REASONS = {"security"}
