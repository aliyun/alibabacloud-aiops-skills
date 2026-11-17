"""Constants for the ECS Cloud Assistant command and agent diagnosis skill.

Every lookup table this skill uses is embedded here as code; no data file is
shipped alongside the scripts.

Provenance discipline: symptom patterns, root-cause candidates and manual steps
below were distilled from the support-case history of this scenario (each entry
keeps the case ids it came from) and from the API contracts confirmed for it.
Anything not listed here is never assumed.
"""

SKILL_NAME = "alibabacloud-ecs-cloud-assistant-diagnosis"

# Observability: one session id per process, attached to every CLI call.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

# aliyun CLI is invoked in argument-list mode only; never through a shell.
CLI_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 40
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

# ecs / sts RPC API versions actually called by this skill.
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"

# Pagination ceilings for the informational queries.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
INVOCATION_MAX_PAGES = 8

# RunCommand polling: the guest command is dispatched, then its status is read
# back through DescribeInvocations with IncludeOutput.
GUEST_POLL_INTERVAL_SECONDS = 5
GUEST_POLL_MAX_ATTEMPTS = 12

# Actions whose failures are worth a bounded retry.
TRANSIENT_ERROR_TOKENS = (
    "Throttling",
    "ThrottlingUser",
    "InternalError",
    "ServiceUnavailable",
    "RequestTimeout",
    "SystemBusy",
)

# Authentication failures must be reported with these literals only.
AUTH_ERROR_TOKENS = ("NoPermission", "ImplicitDeny")
CREDENTIAL_ERROR_TOKENS = ("InvalidSecurityToken", "MissingCredential", "NoCredential")

# Redaction applied to every stderr / error message before it reaches output.
SECRET_VALUE_PATTERNS = (
    r"(AccessKeyId\s*[=:]\s*)\S+",
    r"(AccessKeySecret\s*[=:]\s*)\S+",
    r"(SecurityToken\s*[=:]\s*)\S+",
    r"(Signature\s*[=:]\s*)\S+",
    r"(Password\s*[=:]\s*)\S+",
)
MASKED = "***REDACTED***"

# ---------------------------------------------------------------------------
# API surface. Params are limited to those verified for this scenario; anything not
# listed here is never sent. DescribeCloudAssistantStatus, DescribeCommands,
# InvokeCommand and CloudMonitor actions were NOT verified for this scenario and
# are therefore absent from the scripts and from related_apis.yaml; the report
# says so instead of guessing. See SKILL.md "Known gaps".
# ---------------------------------------------------------------------------
API_ECS_DESCRIBE_INSTANCES = "DescribeInstances"
API_ECS_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"
API_ECS_DESCRIBE_INVOCATIONS = "DescribeInvocations"
API_ECS_RUN_COMMAND = "RunCommand"
API_ECS_CREATE_SNAPSHOT = "CreateSnapshot"
API_STS_GET_CALLER_IDENTITY = "GetCallerIdentity"

# States a Cloud Assistant invocation record can be in when it is finished.
FINISHED_STATES = ("Success", "Finished", "Failed", "Stopped", "PartialFailed",
                   "Error", "Timeout", "Invalid", "Aborted")
FAILED_STATES = ("Failed", "Stopped", "PartialFailed", "Error", "Timeout",
                 "Invalid", "Aborted")

# Instance lifecycle states that send the customer to the instance-state area
# before any Cloud Assistant question is asked.
NON_RUNNING_STATES = ("Pending", "Starting", "Stopping", "Stopped")

# ---------------------------------------------------------------------------
# Symptom classification. Matching is ASCII-only: the console localises its
# message text per locale, so matching relies on stable product tokens plus the
# English wording a customer dictates or pastes. Unmatched text -> UNKNOWN, and
# the caller may pass --category explicitly.
# ---------------------------------------------------------------------------
CATEGORY_AGENT_NOT_READY = "AGENT_NOT_READY"
CATEGORY_VERSION_UPGRADE = "VERSION_UPGRADE_REQUIRED"
CATEGORY_COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
CATEGORY_CLIENT_RESTARTED = "CLIENT_RESTARTED"
CATEGORY_GUEST_ENV_BROKEN = "GUEST_ENV_BROKEN"
CATEGORY_SOFTWARE_INSTALL_FAILED = "SOFTWARE_INSTALL_FAILED"
CATEGORY_EXPAND_TASK_FAILED = "EXPAND_TASK_FAILED"
CATEGORY_TASK_CONFLICT = "TASK_CONFLICT"
CATEGORY_AK_ABUSE = "ACCESSKEY_ABUSE"
CATEGORY_DEPENDENCY_BLOCKED = "DEPENDENCY_FEATURE_BLOCKED"
CATEGORY_UNKNOWN = "UNKNOWN"

ALL_CATEGORIES = (
    CATEGORY_AGENT_NOT_READY,
    CATEGORY_VERSION_UPGRADE,
    CATEGORY_COMMAND_TIMEOUT,
    CATEGORY_CLIENT_RESTARTED,
    CATEGORY_GUEST_ENV_BROKEN,
    CATEGORY_SOFTWARE_INSTALL_FAILED,
    CATEGORY_EXPAND_TASK_FAILED,
    CATEGORY_TASK_CONFLICT,
    CATEGORY_AK_ABUSE,
    CATEGORY_DEPENDENCY_BLOCKED,
    CATEGORY_UNKNOWN,
)

# Highest priority first; the first category that matches wins. Every pattern
# is a lower-case substring of the customer's own wording.
SYMPTOM_PATTERNS = (
    (
        CATEGORY_AK_ABUSE,
        (
            "i did not run",
            "did not execute",
            "not me",
            "someone executed",
            "unknown command",
            "unauthorized command",
            "accesskey leak",
            "ak leak",
            "key leaked",
            "malicious command",
            "trojan",
            "backdoor",
            "cryptominer",
            "mining program",
            "started a process i never",
        ),
    ),
    (
        CATEGORY_EXPAND_TASK_FAILED,
        (
            "expand partition",
            "expand the partition",
            "expand filesystem",
            "expand the filesystem",
            "growpart",
            "resize2fs",
            "disk expand failed",
            "expand the disk",
            "expansion failed",
            "extend the partition",
            "cloud assistant expand",
            "assistant expand",
            "expand the volume",
        ),
    ),
    (
        CATEGORY_TASK_CONFLICT,
        (
            "task conflict",
            "conflicts with another task",
            "conflict with the current task",
            "operation is invalid due to task",
        ),
    ),
    (
        CATEGORY_GUEST_ENV_BROKEN,
        (
            "not recognized as an internal or external command",
            "is not an internal or external command",
            "the system cannot find the file specified",
            "specified resource type",
            "cannot find the specified resource type",
        ),
    ),
    (
        CATEGORY_CLIENT_RESTARTED,
        (
            "client_restarted",
            "clientrestarted",
            "client restarted",
            "interrupted due to a restart",
            "without an exit code",
            "no exit code returned",
        ),
    ),
    (
        CATEGORY_COMMAND_TIMEOUT,
        (
            "the command execution has been timeout",
            "command execution has been timeout",
            "execution has been timeout",
            "execution timeout",
            "execution timed out",
            "invoke timed out",
        ),
    ),
    (
        CATEGORY_VERSION_UPGRADE,
        (
            "upgrade the cloud assistant",
            "cloud assistant needs to be upgraded",
            "you need to upgrade",
            "version is too low",
            "version too low",
            "cloud assistant version",
            "requires a newer cloud assistant",
        ),
    ),
    (
        CATEGORY_DEPENDENCY_BLOCKED,
        (
            "reset password",
            "reset the password",
            "password reset",
            "online reset",
            "file backup",
            "backup failed",
            "backup alarm",
            "backup alert",
            "password-free",
            "passwordless",
            "workbench login",
            "instance logon credential",
        ),
    ),
    (
        CATEGORY_AGENT_NOT_READY,
        (
            "cloud assistant",
            "aliyun assist",
            "assist service",
            "assistant service",
            "agent offline",
            "agent is offline",
            "agent abnormal",
            "assistant is not running",
            "assistant not started",
            "assistant status",
            "empty array",
            "returned an empty",
            "client is not installed",
            "agent is not installed",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Root-cause candidates, keyed by category. Every entry was observed in a real
# historical support case for this scenario (provenance: references/error-
# signatures.md and references/cloud-assistant-diagnosis__agent-readiness.md). Candidate text is guidance
# only - the skill never applies a fix itself, and service start/stop, agent
# installation, reboots and cleanups stay with the customer.
# ---------------------------------------------------------------------------
ROOT_CAUSE_CANDIDATES = {
    CATEGORY_AGENT_NOT_READY: (
        {
            "id": "assist-service-not-started",
            "summary": (
                "The Cloud Assistant agent is installed but its service is not running "
                "inside the instance, so nothing answers the dispatch. Features that ride "
                "on the agent - file backup, online password reset, Workbench password-free "
                "login - all report a Cloud Assistant error at the same time."
            ),
            "confidence": "high",
            "case_refs": ("T-BB00A07B",),
            "manual_checks": (
                "Linux (customer runs this; service status is outside the guest whitelist of "
                "this skill): sudo systemctl status aliyun.service",
                "Windows: open the services manager and read the status and startup type of "
                "'Aliyun Assist Service'.",
            ),
            "verified_mitigation": (
                "Customer-side manual step, verified in the source case: start the service - "
                "Linux: sudo systemctl start aliyun.service ; Windows: start 'Aliyun Assist "
                "Service' from the services manager. The skill never runs service commands; "
                "after the customer starts it, re-run triage to verify from new invocation "
                "history."
            ),
        },
        {
            "id": "agent-never-installed",
            "summary": (
                "The instance was created from an image without the agent (older or custom "
                "images can lack it), or its OS is not on the auto-install list, so the "
                "console has no agent to dispatch to."
            ),
            "confidence": "high",
            "case_refs": ("T-672E1C69",),
            "manual_checks": (
                "Compare the instance OS (read by this skill from DescribeInstances) against "
                "the supported-OS list on the agent installation page.",
            ),
            "verified_mitigation": (
                "Manual: install the agent via the console one-click path or the documented "
                "manual installer, then verify with a new command run."
            ),
        },
        {
            "id": "agent-missing-after-system-disk-reinit",
            "summary": (
                "After the system disk was re-initialised or replaced, the agent did not come "
                "back, and health checks keep returning an empty array instead of a status."
            ),
            "confidence": "low",
            "case_refs": ("T-270E4605",),
            "manual_checks": (
                "Ask whether a system-disk re-initialisation or OS reinstall happened before "
                "the failures started.",
            ),
            "verified_mitigation": (
                "Manual: reinstall or restart the agent after the disk operation. The source "
                "case was closed without a verified root cause, so treat this as a candidate "
                "to test, not a finding."
            ),
        },
        {
            "id": "resolver-or-route-blocks-endpoint",
            "summary": (
                "The agent is running but cannot reach its service endpoint: a changed DNS "
                "resolver or a third-party tunnel client that claims the internal service "
                "route range keeps the instance from reporting online."
            ),
            "confidence": "medium",
            "case_refs": ("T-521F4C4C", "T-1A68E453"),
            "manual_checks": (
                "Linux (customer-run): inspect /etc/resolv.conf for an unexpected nameserver. "
                "Windows: Get-DnsClientServerAddress.",
                "Check whether a VPN or mesh client was installed around the time the agent "
                "went offline.",
            ),
            "verified_mitigation": (
                "Manual: restore the nameserver or stop the client from claiming the route. "
                "Changing resolver or routes is a system change and is never automated here."
            ),
        },
    ),
    CATEGORY_VERSION_UPGRADE: (
        {
            "id": "agent-version-too-low-unreachable-endpoint",
            "summary": (
                "An outdated agent version cannot reach the current service endpoint, so the "
                "agent looks abnormal and dependent features refuse with a 'needs upgrade' "
                "message. The source case was settled by support reading the agent's own log "
                "inside the instance - agent log reading is outside this skill's whitelist, "
                "so the version step is offered directly."
            ),
            "confidence": "high",
            "case_refs": ("T-1A68E453", "T-A0FC6112"),
            "manual_checks": (
                "Compare the agent version shown in the console Cloud Assistant page against "
                "the latest release on the installation page.",
                "If the customer can log in: have them read the agent log under the agent "
                "install directory and paste the lines around the failure time.",
            ),
            "verified_mitigation": (
                "Manual: upgrade the agent per the installation page, then retry the blocked "
                "feature. For a password change meanwhile, use the offline reset path (needs "
                "a reboot - take a snapshot first)."
            ),
        },
    ),
    CATEGORY_COMMAND_TIMEOUT: (
        {
            "id": "resource-saturation-stalls-agent",
            "summary": (
                "Sustained CPU, memory or IO saturation (compiles, panel software, backup "
                "windows) starves the agent process: commands time out, and in the extreme "
                "the OS stops responding so fully - even memory alarms cannot fire."
            ),
            "confidence": "high",
            "case_refs": ("T-DE98E694", "T-02E6175C"),
            "manual_checks": (
                "Read the CloudMonitor console curves for the failure window (this skill has "
                "no verified CloudMonitor query for this scenario, so saturation is a hypothesis "
                "to confirm, never a measurement made here).",
                "Customer-run: install atop or keep top running during the window to catch "
                "the top consumers later.",
            ),
            "verified_mitigation": (
                "Manual: lower or reschedule the competing workload; a reboot of a hung "
                "instance is a class D action and belongs to the customer. The whitelisted "
                "df_h / df_i probes can run afterwards to exclude volume exhaustion."
            ),
        },
        {
            "id": "guest-volume-full-or-inode-exhausted",
            "summary": (
                "The volume the agent writes its working data to is full, or has free bytes "
                "but no free inodes, so new task files cannot be created - customers see "
                "'cannot create new file' or 'file count limit' wording."
            ),
            "confidence": "high",
            "case_refs": ("T-99046C78",),
            "manual_checks": (
                "Whitelisted probes exist for exactly this: guest-probe --command df_h and "
                "--command df_i (each needs its own consent).",
            ),
            "verified_mitigation": (
                "Manual: free space or remove small-file sprawl after a snapshot. Deletion is "
                "never automated here."
            ),
        },
        {
            "id": "agent-absent-while-command-dispatched",
            "summary": (
                "A timeout is also what a missing or stopped agent produces: the dispatch "
                "waits for a client that never answers. The source case ended after the "
                "ownership check found the instance was not even in the customer's account."
            ),
            "confidence": "medium",
            "case_refs": ("T-D87E8F47",),
            "manual_checks": (
                "This skill checks ownership and lifecycle state first; follow the AGENT_"
                "NOT_READY readiness steps if both pass but history stays empty.",
            ),
            "verified_mitigation": (
                "Manual: install or start the agent per the readiness page, then re-run."
            ),
        },
        {
            "id": "script-exceeds-its-own-timeout",
            "summary": (
                "Long-running scripts exceed the invocation timeout budget itself, so the "
                "platform stops the task even though the guest is healthy."
            ),
            "confidence": "low",
            "case_refs": ("T-D87E8F47",),
            "manual_checks": (
                "Compare the task duration against the timeout configured for the command.",
            ),
            "verified_mitigation": (
                "Manual: split the script, raise the command timeout, or run it from a "
                "terminal and use Cloud Assistant only for short evidence commands."
            ),
        },
    ),
    CATEGORY_CLIENT_RESTARTED: (
        {
            "id": "agent-process-restarted-under-load",
            "summary": (
                "The agent process restarted while the task ran, so the invocation was "
                "interrupted and carries no exit code. Load spikes are the usual trigger. "
                "The source case was never fully closed - the customer declined instance "
                "operation and support could only point at monitoring links - so the honest "
                "output here is a load-side evidence list, not a proven cause."
            ),
            "confidence": "medium",
            "case_refs": ("T-FA7FC9EE",),
            "manual_checks": (
                "Read the CloudMonitor curves for the task window (customer action; no "
                "verified metric query exists for this skill).",
                "Customer-run after the fact: atop history, or the system event log on "
                "Windows, around the interrupt timestamp.",
            ),
            "verified_mitigation": (
                "Manual: reduce the competing load; keep a persistent monitor (atop) so the "
                "next interrupt leaves evidence. Where the customer declines guest probes, "
                "the degraded mode asks for pasted readings instead."
            ),
        },
        {
            "id": "guest-rebooted-mid-task",
            "summary": (
                "A reboot (planned or a hung shutdown finally completing) restarts the guest "
                "under the running task and interrupts it without an exit code."
            ),
            "confidence": "medium",
            "case_refs": ("T-DE98E694",),
            "manual_checks": (
                "Compare the interrupt timestamp against the instance lifecycle events the "
                "console lists for the instance.",
            ),
            "verified_mitigation": (
                "Manual: schedule reboots outside command windows. Forcing a reboot is a "
                "class D action and belongs to the customer."
            ),
        },
    ),
    CATEGORY_GUEST_ENV_BROKEN: (
        {
            "id": "system-component-damage",
            "summary": (
                "The dispatch channel works - commands reach the guest - but every command "
                "fails with an OS-level error string ('not recognized as an internal or "
                "external command', 'the system cannot find the file specified', a Windows "
                "image/resource-type error). That is a broken guest execution environment, "
                "not a Cloud Assistant defect."
            ),
            "confidence": "high",
            "case_refs": ("T-E172703F",),
            "manual_checks": (
                "Open an interactive session (VNC or SSH) and run one trivial command to "
                "reproduce the OS-level error outside Cloud Assistant.",
            ),
            "verified_mitigation": (
                "Hand-off only: this belongs to the instance start-up and OS repair area "
                "(see references/cloud-assistant-diagnosis__handoff-matrix.md). The source case was escalated offline; "
                "advise a snapshot before any repair attempt."
            ),
        },
        {
            "id": "correlation-not-causation",
            "summary": (
                "'It broke right after I installed Cloud Assistant' is a timing claim, not a "
                "cause. In the source case support proved the boot failure came from a "
                "damaged system registry hive; several repair paths failed and the disk was "
                "eventually re-initialised from a snapshot-backed state."
            ),
            "confidence": "high",
            "case_refs": ("T-75912401",),
            "manual_checks": (
                "Establish what the boot failure evidence says (recovery environment, "
                "registry hive checks) before attributing anything to the agent install.",
            ),
            "verified_mitigation": (
                "Hand-off to the instance-state area; note the snapshot retention gotcha the "
                "source case paid for: a snapshot kept past its retention window is released "
                "and cannot come back."
            ),
        },
    ),
    CATEGORY_SOFTWARE_INSTALL_FAILED: (
        {
            "id": "channel-ok-content-incompatible",
            "summary": (
                "Cloud Assistant delivered the script and the script itself failed: the "
                "output carries package-manager or installer text. In the source case the "
                "OS release simply does not ship docker-ce (its supported engine is moby), "
                "and the other product had no published compatibility statement - so the "
                "failure is a software-selection issue inside the guest, not an agent fault."
            ),
            "confidence": "high",
            "case_refs": ("T-A9825E98",),
            "manual_checks": (
                "Read the invocation Output the report already fetched: installer errors sit "
                "there, not in the Cloud Assistant status.",
                "Check the product's supported-OS matrix before retrying; package names and "
                "repositories differ between OS releases.",
            ),
            "verified_mitigation": (
                "Manual: install or adapt the software from an interactive session. This "
                "skill neither installs nor removes third-party software."
            ),
        },
    ),
    CATEGORY_EXPAND_TASK_FAILED: (
        {
            "id": "capacity-bought-partition-unchanged",
            "summary": (
                "The cloud disk was resized and paid for, but the partition and filesystem "
                "inside the OS still carry the old size, so nothing 'grew'. The source case "
                "showed the partition table read (a 40G partition at 86 percent use) as the "
                "decisive evidence; the console one-click expansion path was in a "
                "limited preview, so the commands were run manually."
            ),
            "confidence": "high",
            "case_refs": ("T-79753A0F", "T-99046C78", "T-D6F80375"),
            "manual_checks": (
                "The whitelisted df_h probe (with consent) reads the live volume sizes; the "
                "partition-table readers the support engineer used (lsblk, fdisk -l, blkid) "
                "are outside this skill's whitelist and stay manual or console-side.",
            ),
            "verified_mitigation": (
                "Hand-off: partition and filesystem growth belongs to the disk-expand area "
                "(references/cloud-assistant-diagnosis__handoff-matrix.md). This skill answers only why the assistant "
                "task failed; snapshot before any expand step, always."
            ),
        },
        {
            "id": "load-or-missing-tool-blocks-the-task",
            "summary": (
                "The expansion command ran through Cloud Assistant and failed for reasons "
                "unrelated to resizing: a panel application saturating CPU blocked it, a "
                "missing partition tool, or a broken DNS resolver."
            ),
            "confidence": "medium",
            "case_refs": ("T-521F4C4C",),
            "manual_checks": (
                "Read the task Output from DescribeInvocations history for the concrete "
                "error; pause competing applications only as a customer decision.",
            ),
            "verified_mitigation": (
                "Manual: fix the named blocker (install the tool the expand guide needs, "
                "restore the resolver, quiet the busy application), then have the expand "
                "flow re-run it."
            ),
        },
        {
            "id": "windows-not-covered-by-auto-expand",
            "summary": (
                "The console Cloud Assistant auto-expansion does not support Windows disks; "
                "the source case paid for a system-disk resize and the automatic task could "
                "never have worked. Windows extension goes through Disk Management or "
                "diskpart, run by the customer."
            ),
            "confidence": "high",
            "case_refs": ("T-478C2A19",),
            "manual_checks": (
                "Confirm the instance OS (this skill reads it from DescribeInstances).",
            ),
            "verified_mitigation": (
                "Hand-off to the disk-expand area with the Windows page named; diskpart "
                "actions are manual by definition here."
            ),
        },
    ),
    CATEGORY_TASK_CONFLICT: (
        {
            "id": "concurrent-operation-blocks-the-action",
            "summary": (
                "A storage or lifecycle task already in flight (an expansion job, a "
                "pending reset) makes another operation - typically a forced restart - fail "
                "as a conflict. The Cloud Assistant status is not the cause."
            ),
            "confidence": "medium",
            "case_refs": ("T-D6F80375",),
            "manual_checks": (
                "List the in-flight tasks for the instance in the console and wait for the "
                "conflicting one to settle.",
            ),
            "verified_mitigation": (
                "Hand-off: lifecycle conflicts belong to the instance-state area; expansion "
                "jobs belong to the disk-expand area. Force operations are never issued here."
            ),
        },
    ),
    CATEGORY_AK_ABUSE: (
        {
            "id": "leaked-credentials-drive-runcommand",
            "summary": (
                "Commands the customer never issued appear in the invocation history: a "
                "leaked access key lets an external caller run Cloud Assistant commands "
                "inside the instance. Both source cases show this: the history lists the "
                "intrusion commands, and cleanup of processes, cron entries and files "
                "followed under a security team."
            ),
            "confidence": "high",
            "case_refs": ("T-2A028B99", "T-9BEAB951"),
            "manual_checks": (
                "Run the invocations mode for every affected region and keep the printed "
                "history as the evidence list (when, which instance, which command name, "
                "exit code).",
                "Check the RAM console for access keys that are not recognised; the access "
                "key list itself is read in the console, not by this skill.",
            ),
            "verified_mitigation": (
                "Manual incident response, in this order: disable the leaked key and rotate "
                "credentials (RAM console), snapshot the disks before touching anything "
                "(snapshot-guard, consented), remove persistence and malicious files with a "
                "security responder, restrict the surviving key with network conditions and "
                "least privilege. This skill only collects evidence; killing processes and "
                "cleaning files is never automated. No official AK-leak runbook URL was "
                "verified for this scenario, so the console paths above are the guidance."
            ),
        },
    ),
    CATEGORY_DEPENDENCY_BLOCKED: (
        {
            "id": "feature-depends-on-agent-health",
            "summary": (
                "Online password reset, ECS File Backup Essential Edition and Workbench "
                "password-free login are all carried by Cloud Assistant. When the agent is "
                "absent, stopped, offline or outdated, the feature reports a Cloud Assistant "
                "error - the dependency is the reason, not the feature's own defect."
            ),
            "confidence": "high",
            "case_refs": ("T-BB00A07B", "T-1A68E453", "T-A0FC6112"),
            "manual_checks": (
                "Follow the readiness steps in references/cloud-assistant-diagnosis__agent-readiness.md, then retry the "
                "feature.",
            ),
            "verified_mitigation": (
                "Two verified paths from the source cases: restore agent health (start or "
                "upgrade it, manual), or fall back to the offline password reset, which "
                "requires a reboot - snapshot first and expect business interruption."
            ),
        },
    ),
    CATEGORY_UNKNOWN: (
        {
            "id": "generic-failure",
            "summary": (
                "The wording carries no recognised token. Invocation history and the raw "
                "Output still narrow the space: status, exit code and error info come from "
                "the history query this skill always runs."
            ),
            "confidence": "low",
            "case_refs": ("T-270E4605",),
            "manual_checks": (
                "Collect the full console error text, the invoke id and the time window, in "
                "that order.",
            ),
            "verified_mitigation": (
                "Escalate with the collected identifiers where the history query itself shows "
                "no anomaly: in the source cases even support needed the agent-side log, "
                "which stays a customer-side read."
            ),
        },
    ),
}

# ---------------------------------------------------------------------------
# Side-effect-free guest commands. Exactly one command per key; the assembled
# string is re-checked for shell metacharacters before dispatch. In this scenario
# the probes exclude environment causes no cloud API can see: a volume full
# enough to stall task handling, inode exhaustion ('cannot create new file'),
# a missing mount. Service status and agent-log readers (systemctl, log tails,
# ps, lsblk, fdisk) are deliberately NOT whitelisted - they stay manual.
# ---------------------------------------------------------------------------
GUEST_TYPE_LINUX = "RunShellScript"
GUEST_TYPE_WINDOWS = "RunPowerShellScript"

# target_required commands validate --target before assembling the string.
GUEST_COMMANDS = {
    "df_h": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("df", "-h"),
        "target_required": False,
        "purpose": "Byte usage and free space of every mounted volume.",
        "reports": "A volume so full the agent cannot write its task files.",
    },
    "df_i": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("df", "-i"),
        "target_required": False,
        "purpose": "inode usage per volume.",
        "reports": "A byte-free but inode-exhausted volume behind 'cannot create new "
                   "file' task failures.",
    },
    "findmnt": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("findmnt",),
        "target_required": False,
        "purpose": "Mount table: device, mount point, filesystem, options.",
        "reports": "A missing or unexpected mount the failed task wrote to.",
    },
    "du_top": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("du", "-x", "--max-depth=1"),
        "target_required": True,
        "purpose": "Size of each direct child of one directory, without crossing mounts.",
        "reports": "Candidate directories for a customer-run cleanup.",
    },
    "lsof_deleted": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("lsof", "+L1"),
        "target_required": False,
        "purpose": "Files that are deleted but still held open by a process.",
        "reports": "Space logically freed but not yet returned to the volume.",
    },
    "stat": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("stat",),
        "target_required": True,
        "purpose": "Metadata, size and block count of one path.",
        "reports": "Whether a specific file is the space or activity in question.",
    },
    "ls_dir": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("ls", "-lh"),
        "target_required": True,
        "purpose": "Long listing of one directory.",
        "reports": "Unexpected entries (cron leftovers, tmp sprawl) in one directory.",
    },
    "wc_lines": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("wc", "-l"),
        "target_required": True,
        "purpose": "Line count of one text file, e.g. a log.",
        "reports": "Log volume before a customer truncation decision.",
    },
    "get_volume": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-Volume",),
        "target_required": False,
        "purpose": "Health, size and free space of every volume.",
        "reports": "Which Windows volume is full. NTFS has no inode counter: Windows "
                   "file-count conclusions carry reduced confidence.",
    },
    "get_psdrive": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-PSDrive",),
        "target_required": False,
        "purpose": "Used and free bytes per drive letter.",
        "reports": "Same reading in drive-letter terms.",
    },
    "get_childitem": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-ChildItem", "-Force"),
        "target_required": True,
        "purpose": "Listing of one directory, including hidden entries.",
        "reports": "Large or hidden consumers under one path.",
    },
    "fsutil_diskfree": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("fsutil", "volume", "diskfree"),
        "target_required": True,
        "purpose": "Reports total, free and available bytes for one volume, changing nothing.",
        "reports": "Precise free-space figures for the system volume.",
    },
}

# Rejected outright, whatever the caller claims. A whitelist match is necessary
# but not sufficient: this list is re-applied to the assembled string. Note the
# entries the support dialogues of this scenario actually showed: systemctl (the
# agent service reader/starter), fdisk/lsblk/blkid (partition readers used for
# expansion evidence), ps and log tails (agent-side state readers) - all stay manual.
REJECTED_COMMAND_TOKENS = (
    "rm", "rmdir", "mv", "cp", "dd", "truncate", "mkfs", "format", "fdisk", "parted",
    "lsblk", "blkid", "kill", "pkill", "killall", "systemctl", "service", "reboot",
    "shutdown", "halt", "poweroff", "init", "chattr", "chmod", "chown", "setfacl",
    "mount", "umount", "echo", "printf", "tee", "sed", "awk", "perl", "python",
    "python3", "sh", "bash", "powershell", "curl", "wget", "nc", "ssh", "scp",
    "yum", "apt", "apt-get", "rpm", "dpkg", "journalctl", "dmesg", "tail", "cat",
    "head", "less", "more", "ps", "top", "grep", "reg", "sc", "net", "wmic",
    "iisreset", "taskkill", "stop-service", "restart-service", "get-service",
    "remove-item", "new-item", "set-content", "add-content", "clear-content",
    "move-item", "rename-item", "out-file", "invoke-expression", "start-process",
    "iex", "iwr", "install", "uninstall", "upgrade",
)

SHELL_METACHARACTERS = (";", "|", "&", "$", "`", ">", "<", "*", "?", "(", ")", "{", "}", "\n", "\r")

# ---------------------------------------------------------------------------
# Documentation links. Each URL below is an official Alibaba Cloud help-center
# page that was either retrieved for this scenario while building the skill or
# actually sent by a support engineer in one of the source cases. Tracking query
# parameters were stripped; the expansion page keeps its original .htm suffix
# because that is how the source dialogue recorded it. No other URL exists for
# this skill, and a document title with no verified address is never turned
# into one (see DOC_TITLES_WITHOUT_URL).
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "workbench_script_library":
        "https://help.aliyun.com/zh/ecs/user-guide/workbench-script-library.md",
    "assistant_command_autosave":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "enable-automatic-saving-for-cloud-assistant-commands-on-instances.md",
    "create_command": "https://help.aliyun.com/zh/ecs/user-guide/create-a-command.md",
    "run_existing_command": "https://help.aliyun.com/zh/ecs/user-guide/run-a-command.md",
    "describe_commands_api":
        "https://help.aliyun.com/zh/ecs/developer-reference/"
        "api-ecs-2014-05-26-describecommands.md",
    "install_agent":
        "https://help.aliyun.com/zh/ecs/user-guide/install-the-cloud-assistant-agent",
    "workbench_overview": "https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md",
    "workbench_passwordless_principle":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "workbench-password-free-login-principle-temporary-ssh-key-pair.md",
    "workbench_cli_manage_instances":
        "https://help.aliyun.com/zh/ecs/user-guide/use-workbench-cli-to-manage-ecs-instances.md",
    "workbench_ai_agent_mode":
        "https://help.aliyun.com/zh/ecs/user-guide/workbench-ai-agent-mode.md",
    "logon_credential_management":
        "https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management.md",
    "reset_password_offline":
        "https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance",
    "resize_windows_disks":
        "https://help.aliyun.com/zh/ecs/user-guide/resize-windows-cloud-disks.md",
    "offline_extend_linux_data_disk":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "offline-extend-partitions-and-file-systems-on-a-data-disk-of-a-linux-instance.md",
    "expand_partition_linux": "https://help.aliyun.com/document_detail/25451.htm",
    "detach_attach_system_disk":
        "https://help.aliyun.com/zh/ecs/user-guide/detach-or-attach-a-system-disk.md",
    "reinit_system_disk":
        "https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk",
    "create_snapshot": "https://help.aliyun.com/document_detail/25455.html",
    "snapshot_billing": "https://help.aliyun.com/document_detail/56159.html",
    "delete_snapshot": "https://help.aliyun.com/document_detail/128131.html",
}

# Referenced by the source material without a URL. They are named as documents
# only; no address is invented. See SKILL.md "Known gaps".
DOC_TITLES_WITHOUT_URL = (
    "CloudMonitor ECS metric reference (needed before any metric query is added)",
    "atop persistent monitoring installation guidance",
    "AccessKey-leak incident response runbook",
)

# ---------------------------------------------------------------------------
# Hand-off targets for adjacent symptom areas.
# ---------------------------------------------------------------------------
HANDOFF_RULES = (
    {
        "when": "The disk was resized (paid for) but the partition or filesystem inside the "
                "OS still shows the old size, or a growpart/resize2fs/diskpart step is asked "
                "about - including an expansion task dispatched through Cloud Assistant.",
        "target": "area:disk-expand-diagnosis",
    },
    {
        "when": "The instance will not start, is stuck in an intermediate lifecycle state "
                "(Stopping/Starting), the screen is black, or the OS boots to a repair "
                "environment.",
        "target": "area:instance-state-diagnosis",
    },
    {
        "when": "The complaint is slow disk IO or throughput below the instance "
                "specification rather than a command or agent failure.",
        "target": "area:resource-bottleneck",
    },
    {
        "when": "The Workbench CLI tool itself misbehaves (non-default SSH ports, session "
                "downgrade, file transfer), with the channel otherwise healthy.",
        "target": "alibabacloud-workbench-cli",
    },
    {
        "when": "The failure is an OS-internal deep problem or a third-party software "
                "compatibility question while the command channel works.",
        "target": "alibabacloud-ecs-linux-os-troubleshooting (or manual, for software "
                  "compatibility)",
    },
    {
        "when": "Disk or inode capacity accounting itself (growth planning, cleanup "
                "execution) rather than using df readings to exclude an environment cause.",
        "target": "the disk capacity and cleanup scenario (its skill, if installed; "
                  "otherwise manual steps - the df readings transfer with the report)",
    },
    {
        "when": "A leaked access key keeps producing commands the customer never issued.",
        "target": "manual - the security incident response flow (this skill supplies only "
                  "the evidence list)",
    },
    {
        "when": "Anything destructive: deleting files or snapshots, killing processes, "
                "starting or stopping services, reboots, re-initialisation, software "
                "install or removal.",
        "target": "manual only - the skill prints the steps, never runs them",
    },
)

# ---------------------------------------------------------------------------
# Manual readiness steps (agent not installed / stopped / outdated). These are
# customer actions: service control sits outside the guest whitelist on purpose
# (the low-risk command list bans systemctl-class actions for automatic runs).
# ---------------------------------------------------------------------------
READINESS_STEPS_LINUX = (
    "Check (customer-run): sudo systemctl status aliyun.service",
    "Start (customer-run, this skill never runs it): sudo systemctl start aliyun.service",
    "Install or upgrade from the agent installation page: {0}".format(
        DOC_LINKS["install_agent"]),
    "After the customer acts, verify: re-run triage - new successful history lines are the "
    "proof.",
)

READINESS_STEPS_WINDOWS = (
    "Check (customer-run): open the services manager and read the status of "
    "'Aliyun Assist Service'.",
    "Start (customer-run, this skill never runs it): start 'Aliyun Assist Service' in the "
    "services manager.",
    "Install or upgrade from the agent installation page: {0}".format(
        DOC_LINKS["install_agent"]),
    "After the customer acts, verify: re-run triage - new successful history lines are the "
    "proof.",
)

DEPENDENCY_FEATURES = (
    {
        "feature": "Online password reset",
        "depends": "a running agent of sufficient version; otherwise the console offers the "
                   "offline reset, which reboots the instance",
        "case": "T-1A68E453",
        "docs": (DOC_LINKS["logon_credential_management"], DOC_LINKS["reset_password_offline"]),
    },
    {
        "feature": "ECS File Backup Essential Edition (Cloud Backup file backup)",
        "depends": "a running agent; a stopped service surfaces as a 'Cloud Assistant is not "
                   "started' backup alarm",
        "case": "T-BB00A07B",
        "docs": (DOC_LINKS["install_agent"],),
    },
    {
        "feature": "Workbench password-free (temporary key pair) login",
        "depends": "the agent to install the temporary key; falls back to password or key "
                   "login while the agent is down",
        "case": "T-1A68E453",
        "docs": (DOC_LINKS["workbench_passwordless_principle"], DOC_LINKS["workbench_overview"]),
    },
)

# The five failure classes the triage report distinguishes, with the first move
# for each. Kept in one place so the SKILL.md summary and the script wording
# cannot drift.
FAILURE_CLASS_GUIDE = (
    {
        "class": "no-channel (agent missing / stopped / offline)",
        "signal": "empty invocation history, or dependency features report a Cloud Assistant "
                  "error",
        "first-move": "ownership and lifecycle precheck, then the manual readiness steps",
    },
    {
        "class": "channel-stalled (timeout / CLIENT_RESTARTED)",
        "signal": "'The command execution has been timeout', CLIENT_RESTARTED, tasks ending "
                  "without an exit code",
        "first-move": "failure-window evidence: monitor curves (customer), whitelisted df_h / "
                      "df_i probes with consent",
    },
    {
        "class": "channel-ok-guest-broken",
        "signal": "every command returns an OS-level error string ('not recognized as an "
                  "internal or external command')",
        "first-move": "reproduce interactively outside the channel, then hand off to the "
                      "instance-state / OS repair area",
    },
    {
        "class": "channel-ok-content-failed",
        "signal": "the invocation Output carries installer or package errors; expansion "
                  "tasks fail for named blockers",
        "first-move": "read the Output; software compatibility and expansion execution go to "
                      "manual steps or the disk-expand area",
    },
    {
        "class": "abuse (commands nobody claims)",
        "signal": "invocation history lists commands the customer denies issuing, often after "
                  "an access-key leak alert",
        "first-move": "run the invocations evidence list, then the security response flow "
                      "(manual)",
    },
)
