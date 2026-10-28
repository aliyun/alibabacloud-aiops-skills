#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the snapshot rollback guide skill
===========================================================================
SECURITY: This module holds constants only and performs no I/O. Per platform
rule MUST 1.1.2, scripts/ may contain executable code only, so every table
(frozen guest observation-command whitelist, verdict templates, risk
statement, API metadata) is embedded here as Python constants. No credential
is ever read, stored or printed by this module; authentication is resolved
exclusively by the aliyun CLI default credential chain.

This skill is a guidance skill for a state-changing operation (disk rollback)
that it NEVER performs. Its two gated operations -- the ECS snapshot-creation
operation (CreateSnapshot) and the Cloud Assistant command-dispatch operation
(RunCommand, carrying only one whitelisted non-mutating command) -- sit behind
the per-call customer confirmation gate documented in SKILL.md. The disk
rollback itself is manual-only, forever.
"""

# ---------------------------------------------------------------------------
# Skill identity & observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-snapshot-rollback-guide"

# User-Agent template: AlibabaCloud-Agent-Skills/{skill-name}/{session-id}
# session-id is a 32-character lowercase hex string (uuid4().hex), generated
# once per script run and attached to every CLI call of that run. Implemented
# in _cli.py (user_agent()).
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"

# ---------------------------------------------------------------------------
# API metadata (verified against the api-info contract of this tier; the
# aliyun CLI carries its own request metadata -- these values document the
# surface this skill is allowed to use and appear in related_apis.yaml)
# ---------------------------------------------------------------------------

API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# The ONLY OpenAPI actions this skill may invoke. Any action outside this
# whitelist is absolutely prohibited (SKILL.md Absolute Rule 5).
QUERY_ACTIONS = {
    "ecs": [
        "DescribeInstances",
        "DescribeDisks",
        "DescribeSnapshots",
        "DescribeCloudAssistantStatus",
        "DescribeInvocations",
    ],
    "sts": ["GetCallerIdentity"],
}
GATED_ACTIONS = {
    "ecs": [
        # dispatches exactly ONE whitelisted non-mutating command, gated
        "RunCommand",
        # creates one billable snapshot (snapshot-first discipline), gated
        "CreateSnapshot",
    ],
}

# ---------------------------------------------------------------------------
# Timeouts / loop guardrails (MUST 7.6.1: every subprocess call passes one)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60          # seconds, per aliyun CLI subprocess call
POLL_INTERVAL_SECONDS = 5     # wait between result / progress polls
POLL_MAX_ATTEMPTS = 24        # 24 * 5s = 2 min ceiling per poll loop
MAX_RESULTS = 100             # page size for NextToken pagination
MAX_PAGES = 20                # hard pagination guardrail

# ---------------------------------------------------------------------------
# Input validation (E20: strict regex on every identifier before use)
# ---------------------------------------------------------------------------

REGION_ID_RE = r"^[a-z][a-z0-9-]{2,29}$"
INSTANCE_ID_RE = r"^i-[a-z0-9]{6,40}$"
DISK_ID_RE = r"^d-[a-z0-9]{6,40}$"
SNAPSHOT_ID_RE = r"^s-[a-z0-9]{6,40}$"
PROFILE_NAME_RE = r"^[A-Za-z0-9._-]{1,64}$"

# ---------------------------------------------------------------------------
# Frozen guest observation-command whitelist (B-class, gated)
# ---------------------------------------------------------------------------
# Each entry is a full-command regex. The command string must match one
# pattern in full; anything else is REFUSED with the reason printed
# (SKILL.md Absolute Rules 2-3). As defense-in-depth the string is also
# rejected when it contains a shell control character (the anchored
# patterns below already exclude them; backslash stays allowed solely
# because Windows drive paths such as C:\\Windows legitimately contain it
# and carries no control meaning inside these single-statement commands).

_GUEST_SHELL_CONTROL = (";", "|", "&", "`", "$", "<", ">", "(", ")", "{", "}", "\n", "\r")

GUEST_COMMAND_WHITELIST = {
    "linux": [
        r"^df -h$",                       # per-filesystem usage snapshot
        r"^df -hT$",                      # usage snapshot with fs types
        r"^findmnt$",                     # current mount table
        r"^findmnt( /[A-Za-z0-9._/-]*)?$", # mount state of one path
        r"^ls( -l)?( /[A-Za-z0-9._/-]*)?$",   # list one directory
        r"^stat( -f)? /[A-Za-z0-9._/-]+$",   # metadata of one path
        r"^lsof \+L1$",                   # deleted-but-open files (reboot hint)
    ],
    "windows": [
        r"^Get-Volume$",                          # volume capacity snapshot
        r"^Get-Volume( -DriveLetter [A-Z])$",     # one volume
        r"^Get-PSDrive$",                         # drive usage snapshot
        r"^Get-PSDrive( [A-Z])?$",                # one drive
        r"^Get-ChildItem( -Path)? [A-Za-z]:\\[A-Za-z0-9 ._\\-]*$",  # list a dir
        r"^Get-Item [A-Za-z]:\\[A-Za-z0-9 ._\\-]*$",  # metadata of one path
    ],
}

# Script type understood by the dispatch operation per OS family.
RUN_COMMAND_TYPE = {
    "linux": "RunShellScript",
    "windows": "RunPowerShellScript",
}

# ---------------------------------------------------------------------------
# Mandatory risk statement (relay verbatim before any rollback guidance;
# distilled from the confirmed support-ticket wording of this tier -- the two
# points support engineers are required to state on every rollback)
# ---------------------------------------------------------------------------

RISK_STATEMENT = [
    (
        "Rolling back a disk is IRREVERSIBLE. From the snapshot's creation "
        "time until the rollback moment, all data written to that disk is "
        "permanently lost. Before rolling back, create a snapshot of the "
        "disk's CURRENT state as a fallback -- otherwise data written after "
        "the chosen snapshot point can never be recovered."
    ),
    (
        "The system disk and each data disk must be rolled back separately, "
        "disk by disk; rolling back one disk does not affect the others. "
        "The instance must be stopped first (stopping it is a manual action "
        "this skill never performs)."
    ),
]

BILLING_NOTICE = (
    "Snapshots are billed separately for their stored size. A short "
    "retention period or timely deletion of unneeded backup snapshots "
    "avoids unexpected post-pay charges; deletion itself is a manual "
    "console action outside this skill."
)

SNAPSHOT_PROGRESS_GATE = (
    "A snapshot may be used as a restore point only when its progress "
    "reaches 100% (status accomplished). The rollback step must not be "
    "guided against a snapshot that is still progressing or has failed."
)

SENSITIVE_INFO_FOOTNOTE = (
    "If you pasted passwords, access keys or other credentials into the "
    "conversation, rotate them promptly -- this report never echoes "
    "credential values."
)

# ---------------------------------------------------------------------------
# Verdict vocabulary produced by assess mode
# ---------------------------------------------------------------------------

VERDICT_ELIGIBLE = "ROLLBACK_ELIGIBLE"
VERDICT_NEEDS = "NEEDS_ACTION"
VERDICT_NO_SNAPSHOT = "NO_USABLE_SNAPSHOT"
VERDICT_UNKNOWN = "UNKNOWN_DEGRADED"

# The five preconditions verified by assess mode (one evidence line each):
PRECONDITIONS = [
    ("P1", "target disk exists and is visible in the queried region"),
    ("P2", "a candidate snapshot of that exact disk exists (ownership by SourceDiskId)"),
    ("P3", "candidate snapshot progress is 100% (status accomplished)"),
    ("P4", "candidate snapshot is not beyond its retention period"),
    ("P5", "instance state allows rollback (system-disk rollback requires the instance stopped)"),
]

# ---------------------------------------------------------------------------
# Console entry documents (relative citation pointers; full step text lives
# in references/rollback-entry-steps.md)
# ---------------------------------------------------------------------------

ENTRY_STEPS_DOC = "references/rollback-entry-steps.md"
BOUNDARIES_DOC = "references/recovery-boundaries.md"
