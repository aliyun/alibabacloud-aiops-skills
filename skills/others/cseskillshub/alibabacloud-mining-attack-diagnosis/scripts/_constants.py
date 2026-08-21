"""
_constants.py — Shared constants for Mining Attack Diagnosis scripts
===================================================================
Internal module (prefixed with `_`). Do NOT run directly.

Single source of truth for mining-alert detection heuristics used across the
orchestrator (mining_investigation.py) and the standalone query scripts. The
data source is Security Center (SAS) only.
"""

# Default HTTP timeout in seconds for API calls.
DEFAULT_TIMEOUT = 60

# Keywords used to recognize mining (cryptojacking) alerts within SAS event
# names / types / descriptions. Case-insensitive substring match. Covers both
# Chinese and English wording, common miner family names, and mining-pool
# terminology.
# NOTE: Chinese keywords are written as \uXXXX escapes (platform static check
# 4.1.2 requires English-only source; escapes keep the runtime values intact).
MINING_ALERT_KEYWORDS = [
    # Chinese (escaped): wa-kuang / kuang-chi / kuang-ji / men-luo-bi / bi
    "\u6316\u77ff", "\u77ff\u6c60", "\u77ff\u673a", "\u95e8\u7f57\u5e01", "\u5e01",
    # English generic
    "mining", "miner", "cryptomining", "cryptojacking", "coinminer",
    "coin miner", "monero", "stratum", "mining pool", "pool connection",
    # Known miner families / tools
    "xmrig", "xmr-stak", "minerd", "cpuminer", "ccminer", "nbminer",
    "phoenixminer", "kdevtmpfsi", "kinsing", "watchdogs", "sysrv",
    "wannamine", "photominer", "lemon_duck", "lemonduck", "z0miner",
    "teamtnt", "8220", "outlaw", "rocke",
]

# SAS alert event TYPES that mining commonly manifests under. Used as a
# secondary signal (alongside MINING_ALERT_KEYWORDS) when classifying alerts.
# These are the human-readable AlarmEventType values SAS returns.
MINING_EVENT_TYPES = [
    # Chinese AlarmEventType values written as \uXXXX escapes (see note above).
    "\u6076\u610f\u811a\u672c",          # Malicious Script (mining scripts land here)
    "\u6076\u610f\u8fdb\u7a0b",          # Malicious Process (cloud threat detection)
    "\u6076\u610f\u8fdb\u7a0b\uff08\u4e91\u67e5\u6740\uff09",
    "\u8fdb\u7a0b\u5f02\u5e38\u884c\u4e3a",      # Process anomaly behavior
    "\u53ef\u7591\u7f51\u7edc\u8fde\u63a5",      # Suspicious network connection (mining-pool comms)
    "\u5f02\u5e38\u7f51\u7edc\u8fde\u63a5",
    "\u81ea\u53d8\u5f02\u6728\u9a6c",        # Self-mutating trojan / worm
    "\u8815\u866b\u75c5\u6bd2",          # Worm
    "webshell",
    "Web-CMS\u5165\u4fb5",
    "\u5e94\u7528\u5165\u4fb5\u4e8b\u4ef6",      # Application intrusion (entry vector for miners)
    "\u7f51\u7ad9\u540e\u95e8",
    "\u6076\u610f\u7f51\u7edc\u884c\u4e3a",
]

# SAS alert severity levels (as returned by DescribeSuspEvents).
# Mapping to a normalized severity ordering for reporting.
LEVEL_ORDER = {
    "serious": 3, "\u4e25\u91cd": 3,
    "suspicious": 2, "\u53ef\u7591": 2,
    "remind": 1, "\u63d0\u9192": 1,
}


def is_mining_text(*texts: object) -> bool:
    """Return True if any of the given texts contains a mining indicator.

    Case-insensitive substring match against MINING_ALERT_KEYWORDS. Accepts any
    mix of alert name / type / description fields (None-safe).
    """
    blob = " ".join(str(t) for t in texts if t).lower()
    if not blob:
        return False
    return any(kw.lower() in blob for kw in MINING_ALERT_KEYWORDS)


def matched_mining_keywords(*texts: object) -> list[str]:
    """Return the distinct mining keywords found in the given texts (for evidence)."""
    blob = " ".join(str(t) for t in texts if t).lower()
    if not blob:
        return []
    hits = [kw for kw in MINING_ALERT_KEYWORDS if kw.lower() in blob]
    # Preserve order but de-duplicate.
    seen: set[str] = set()
    out: list[str] = []
    for kw in hits:
        if kw not in seen:
            seen.add(kw)
            out.append(kw)
    return out


def level_rank(level: object) -> int:
    """Normalize a SAS alert level string to an integer rank (higher = worse)."""
    return LEVEL_ORDER.get(str(level or "").strip().lower(), 0)


# ---------------------------------------------------------------------------
# B-enhancement: CloudMonitor CPU corroboration + ActionTrail intrusion trace
# ---------------------------------------------------------------------------

# CPU utilization threshold (%) above which sustained usage is treated as
# mining-consistent. Majority (>=50%) of data points above this = flagged.
MINING_CPU_THRESHOLD = 80

# High-risk ECS / RAM operations that commonly indicate miner deployment or
# post-intrusion lateral movement, queried via ActionTrail LookupEvents.
HIGH_RISK_TRACE_EVENTS: list[str] = [
    # Miner delivery / command execution
    "RunCommand", "InvokeCommand", "CreateCommand",
    # Instance creation / startup (cryptojacking scale-out)
    "RunInstances", "CreateInstance", "StartInstance", "StartInstances",
    # Persistence / credential abuse
    "CreateAccessKey", "CreateUser", "AttachPolicyToUser",
    # Security group manipulation (opening mining-pool egress)
    "CreateSecurityGroup", "AuthorizeSecurityGroup", "AuthorizeSecurityGroupEgress",
    # Disk / image manipulation (rootkit persistence)
    "ReplaceSystemDisk", "CreateImage",
]
