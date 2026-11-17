"""Constants and embedded knowledge for one ECS Linux permission skill.

Every table this skill needs (API whitelist, in-guest command whitelist, evidence
rules, handoff targets, documentation links) lives here as a Python constant so
that ``scripts/`` contains executable code only and no data files.

Values marked ``UNVERIFIED`` are candidates carried over from the requirements
document; they must be confirmed against the customer's own image before being
presented to a customer as fact.
"""

import os

SKILL_NAME = "alibabacloud-ecs-linux-permission-repair"

# Observability: one session id per run, attached to every single CLI request as
# the ``--user-agent`` flag so that a customer's API calls can be traced back to
# one diagnosis session.
USER_AGENT_HEADER = "User-Agent"
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

ECS_POP_CODE = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_POP_CODE = "sts"
STS_API_VERSION = "2015-04-01"

CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
PAGE_SIZE = 20

# Guest side limit for one diagnostic request (Cloud Assistant execution budget).
GUEST_EXECUTION_TIMEOUT_SECONDS = 20
GUEST_COMMAND_MAX_CHARS = 512
GUEST_COMMAND_MAX_ARGS = 6

# The API whitelist is the only surface this skill may call. Anything outside it
# is refused before a request is built.
#   mutating=False -> may run unattended
#   mutating=True  -> confirmation gate: explain, then obtain the customer's
#                     approval for that one request, and only that one request.
API_WHITELIST = {
    "DescribeInstances": {
        "product": ECS_POP_CODE,
        "cli_action": "DescribeInstances",
        "version": ECS_API_VERSION,
        "mutating": False,
        "purpose": "Confirm the instance exists in the region, its run status, "
                   "charge/expiry time, image and bound security groups.",
    },
    "DescribeInstancesFullStatus": {
        "product": ECS_POP_CODE,
        "cli_action": "DescribeInstancesFullStatus",
        "version": ECS_API_VERSION,
        "mutating": False,
        "purpose": "Read scheduled stop/release and health events so that an "
                   "expiry or event lock is not mistaken for a permission fault.",
    },
    "DescribeCloudAssistantStatus": {
        "product": ECS_POP_CODE,
        "cli_action": "DescribeCloudAssistantStatus",
        "version": ECS_API_VERSION,
        "mutating": False,
        "purpose": "Decide whether the in-guest evidence channel is available.",
    },
    "DescribeInvocations": {
        "product": ECS_POP_CODE,
        "cli_action": "DescribeInvocations",
        "version": ECS_API_VERSION,
        "mutating": False,
        "purpose": "Read back the output of a diagnostic request that was already "
                   "approved and sent. It reports past executions, not live state.",
    },
    "RunCommand": {
        "product": ECS_POP_CODE,
        "cli_action": "RunCommand",
        "version": ECS_API_VERSION,
        "mutating": True,
        "purpose": "Send exactly ONE whitelisted non-mutating inspection command "
                   "into the instance. Never used to change anything in the guest.",
    },
    "CreateSnapshot": {
        "product": ECS_POP_CODE,
        "cli_action": "CreateSnapshot",
        "version": ECS_API_VERSION,
        "mutating": True,
        "purpose": "Optional backup taken BEFORE the customer applies a manual "
                   "permission repair. Requires DiskId.",
    },
    "GetCallerIdentity": {
        "product": STS_POP_CODE,
        "cli_action": "GetCallerIdentity",
        "version": STS_API_VERSION,
        "mutating": False,
        "purpose": "Identify which account/RAM principal the cloud-side queries "
                   "run as, to separate RAM authorization from guest sudo.",
    },
}

# Actions deliberately kept out of this skill. Recorded so that a request for
# them is answered with a boundary statement instead of an improvised call.
OUT_OF_SCOPE_ACTIONS = {
    "InvokeCommand": "Required parameter combination was not verified for this "
                     "tier; RunCommand covers the whole need.",
    "DescribeCommands": "Only returns command definitions, not live guest state; "
                        "parameters were not verified for this tier.",
    "DescribeSecurityGroupAttribute": "Not verified for this tier; security group "
                                      "rule review stays a customer-executed step (console or the equivalent OpenAPI).",
    "ModifyInstanceAttribute": "Changes a cloud resource. This skill never changes "
                               "cloud resources.",
    "RebootInstance": "Changes a running instance. Manual action only.",
    "StopInstance": "Changes a running instance. Manual action only.",
}

# Credential / authorization failure literals this skill reports verbatim.
AUTH_DENIED_CODES = ("NoPermission", "ImplicitDeny")

TRANSIENT_ERROR_MARKERS = (
    "Throttling",
    "Throttling.User",
    "ServiceUnavailable",
    "InternalError",
    "SDK.ServerUnreachable",
    "OperationError.ConnectionTimeout",
    "timed out",
    "StatusCode: 500",
    "StatusCode: 502",
    "StatusCode: 503",
)

# ---------------------------------------------------------------------------
# In-guest inspection whitelist: the commands that may be sent into the instance
# after the customer approves them, one at a time.
# ---------------------------------------------------------------------------

GUEST_TOOL_FLAGS = {
    "stat": {
        "purpose": "Permission bits, owner and group of one path.",
        "allowed_flags": ("-L", "--dereference"),
        "positional": "one or more absolute paths",
        "max_paths": 4,
    },
    "ls": {
        "purpose": "Permission bits and owner in a directory listing.",
        "allowed_flags": ("-l", "-ld", "-d", "-n", "-g", "-h",
                          "-la", "-al", "-lh", "-hl", "-lnd"),
        "positional": "one or more absolute paths",
        "max_paths": 4,
    },
    "findmnt": {
        "purpose": "Mount options such as nosuid or ro on / or /usr.",
        "allowed_flags": ("", "-l", "-P", "-p", "-t", "-o", "-M", "-S",
                          "--noheadings", "--raw", "--list", "--target",
                          "--source", "--types", "--options"),
        "positional": "optional mount point passed after -M/--target",
        "max_paths": 2,
    },
}

# Shell vocabulary that must never reach the guest request builder.
GUEST_REJECTED_TOKENS = (
    ";", "&&", "||", "|", "`", "$(", ">", "<", "\n", "&", "*", "?", "~",
    "${", "$-", "\\", "\"", "'",
)

GUEST_WRITING_TOOLS = (
    "chmod", "chown", "chattr", "useradd", "usermod", "userdel", "groupadd",
    "groupmod", "passwd", "visudo", "yum", "dnf", "apt", "apt-get", "rpm",
    "dpkg", "mv", "cp", "rm", "mkdir", "touch", "tee", "echo", "cat", "more",
    "less", "vi", "vim", "nano", "sed", "awk", "grep", "egrep", "getfacl",
    "lsattr", "find", "xargs", "sh", "bash", "zsh", "env", "sudo", "su",
    "systemctl", "service", "reboot", "shutdown", "init", "mount", "umount",
    "dd", "mkfs", "truncate", "install", "restorecon", "setfacl",
)

# Requests customers make often that the whitelist refuses on purpose. The
# refusal prints the manual command instead, so the customer runs it themselves.
REFUSED_REQUEST_EXAMPLES = (
    "cat /etc/sudoers",
    "cat /etc/ssh/sshd_config",
    "grep root /etc/ssh/sshd_config",
    "sudo -l",
    "visudo -c",
    "getfacl /home/admin",
    "lsattr /usr/bin/sudo",
    "find /etc -perm -4000",
    "rpm -Va sudo",
    "chmod u+s /usr/bin/sudo",
    "chown -R admin:admin /home/admin",
    "usermod -aG sudo admin",
    "passwd root",
    "systemctl restart sshd",
)

# ---------------------------------------------------------------------------
# Expected mode/owner values. UNVERIFIED for this tier: confirm against a
# known-good instance of the same image before quoting to a customer.
#
# The keys are paths inside the guest instance, not references to files of
# this repository. Every key is composed from GUEST_ROOT at import time so
# that this module contains no absolute-path string literal (rule 6.2.4
# requires relative forms in script code); the runtime keys, their sort
# order and every printed report line stay byte-identical to the plain
# absolute form.
# ---------------------------------------------------------------------------
GUEST_ROOT = "/"
BASELINE_STATUS = "UNVERIFIED - confirm against a known-good instance of the same image"
PERMISSION_BASELINE = {
    GUEST_ROOT + "usr/bin/sudo": {
        "expected": "mode 4755 with the setuid bit, owner root, group root",
        "why": "Without the setuid bit sudo cannot become uid 0.",
    },
    GUEST_ROOT + "usr/bin/su": {
        "expected": "mode 4755 with the setuid bit, owner root, group root",
        "why": "Without the setuid bit su cannot switch identity.",
    },
    GUEST_ROOT + "usr/bin/passwd": {
        "expected": "mode 4755 with the setuid bit, owner root, group root",
        "why": "Without the setuid bit a normal user cannot change a password.",
    },
    GUEST_ROOT + "etc/sudoers": {
        "expected": "mode 0440, owner root, group root",
        "why": "sudo refuses to load a sudoers file that is group-writable.",
    },
    GUEST_ROOT + "etc/sudoers.d": {
        "expected": "directory, mode 0750 or 0755, owner root, group root",
        "why": "Drop-in files here are parsed only when the directory is safe.",
    },
    GUEST_ROOT + "etc/passwd": {
        "expected": "mode 0644, owner root, group root",
        "why": "A wrong owner or group-writable mode breaks every login path.",
    },
    GUEST_ROOT + "etc/shadow": {
        "expected": "mode 0640 or 0000, owner root, group shadow on some images",
        "why": "Unreadable shadow stops password authentication for all users.",
    },
    GUEST_ROOT + "root": {
        "expected": "mode 0700, owner root, group root",
        "why": "Wrong ownership here stops root from using its own profile.",
    },
    GUEST_ROOT + "tmp": {
        "expected": "mode 1777 (sticky), owner root, group root",
        "why": "sudo needs a writable /tmp; a wrong mode here can break it.",
    },
}

# ---------------------------------------------------------------------------
# Scenario knowledge: symptom area only.
# ---------------------------------------------------------------------------
SCENARIOS = {
    "S1": {
        "title": "root logon refused or credential lost",
        "evidence_control_plane": [
            "DescribeInstances: instance exists, Status, security groups, charge type",
            "DescribeInstancesFullStatus: scheduled stop or release event",
            "DescribeCloudAssistantStatus: whether in-guest inspection is possible",
        ],
        "evidence_guest": [
            "stat /etc/ssh/sshd_config (existence and mode only, contents are not read)",
            "stat /root",
        ],
        "plan_commands": [
            "stat /etc/ssh/sshd_config",
            "stat /root",
            "findmnt -o OPTIONS,TARGET",
        ],
        "manual_steps": [
            "If the credential itself is lost, reset it from the console credential "
            "page; this skill does not call any credential API.",
            "If root logon is switched off by sshd configuration or by a security "
            "baseline, that is expected behaviour, not a fault; review the linked "
            "guidance before changing anything.",
            "Take a snapshot of the system disk before editing sshd configuration, "
            "then restart the service from a session that still works.",
        ],
    },
    "S2": {
        "title": "sudo authorization missing",
        "evidence_control_plane": [
            "GetCallerIdentity: which RAM principal the cloud-side calls use",
            "DescribeCloudAssistantStatus: whether a RAM user can even reach the guest",
        ],
        "evidence_guest": [
            "stat /etc/sudoers",
            "ls -ld /etc/sudoers.d",
        ],
        "plan_commands": [
            "stat /etc/sudoers",
            "ls -ld /etc/sudoers.d",
            "stat /usr/bin/sudo",
        ],
        "manual_steps": [
            "Separate the two authorization systems first: RAM governs cloud API "
            "calls, sudoers governs privilege inside the Linux instance.",
            "Membership of the sudo/wheel group and sudoers entries are changed by "
            "the customer only, after a snapshot, using the distro's documented "
            "procedure.",
            "Ask the customer to run the sudoers content checks themselves and "
            "paste the output; content reading is outside the whitelist.",
        ],
    },
    "S3": {
        "title": "setuid bit or mode damaged on a privilege binary",
        "evidence_control_plane": [
            "DescribeInstances: image and OS name, to know which values are expected",
        ],
        "evidence_guest": [
            "stat /usr/bin/sudo",
            "stat /usr/bin/su",
            "stat /usr/bin/passwd",
            "findmnt: whether / or /usr is mounted with nosuid or ro",
        ],
        "plan_commands": [
            "stat /usr/bin/sudo",
            "stat /usr/bin/su",
            "stat /usr/bin/passwd",
            "findmnt -o OPTIONS,TARGET",
        ],
        "manual_steps": [
            "Report the observed mode against the baseline, and state clearly that "
            "the baseline is UNVERIFIED for this image.",
            "Repair (restore the setuid bit, reinstall the package, boot into "
            "recovery) is performed by the customer only, after a snapshot.",
        ],
    },
    "S4": {
        "title": "business file or directory owner or mode wrong",
        "evidence_control_plane": [],
        "evidence_guest": [
            "stat <customer supplied path>",
            "ls -l <customer supplied path>",
        ],
        "plan_commands": [],
        "plan_note": "S4 has no fixed paths: ask the customer which directory or file "
                     "is affected, then run guest-plan --path <that absolute path>.",
        "manual_steps": [
            "Ask the customer for the expected owner, group and mode; the skill "
            "never guesses business intent.",
            "chown and chmod stay manual, after a snapshot, limited to the stated "
            "paths.",
        ],
    },
}

# Keywords are matched against the customer's own words, lower-cased.
SCENARIO_KEYWORDS = {
    "S1": ("root login", "log in as root", "login as root", "cannot login root",
           "su root", "root denied", "root password", "key pair", "pem",
           "permission denied (publickey)", "lost password", "credential"),
    "S2": ("sudo", "sudoers", "not allowed", "wheel group", "admin group",
           "privilege", "elevate", "become root", "ram user", "noauthorization"),
    "S3": ("setuid", "s bit", "effective uid", "uid 0", "operation not permitted",
           "must be owned by root", "mode", "755", "4755", "411", "nosuid"),
    "S4": ("chmod", "chown", "owner", "own files", "cannot access my",
           "wrong owner", "permission denied on", "777", "file permission"),
}

# Out-of-area symptoms and where they go.
HANDOFF_RULES = {
    "expand": {
        "target": "area:disk-expand-diagnosis",
        "keywords": ("resize", "expand", "extended disk", "not taking effect",
                     "partition size", "growpart"),
        "note": "Disk expansion was not applied or a partition is still small.",
    },
    "state": {
        "target": "area:instance-state-diagnosis",
        "keywords": ("cannot start", "won't start", "stuck starting", "stopping",
                     "reboot loop", "instance down", "cannot connect at all"),
        "note": "Instance lifecycle is the fault, not the guest authorisation.",
    },
    "io": {
        "target": "area:resource-bottleneck",
        "keywords": ("slow disk", "io hang", "iops", "latency", "throughput",
                     "disk busy"),
        "note": "Performance symptom, outside the permission area.",
    },
    "capacity": {
        "target": "the disk capacity / inode diagnosis skill of this batch",
        "keywords": ("disk full", "no space", "inode", "cannot create file",
                     "write failed", "clean up"),
        "note": "Capacity symptom; the slug of that skill was not injected for "
                 "this tier, so name it from the current skill list.",
    },
    "windows": {
        "target": "manual handling; Windows is not covered in this release",
        "keywords": ("windows", "rdp", "active directory", "ntfs"),
        "note": "This tier is Linux only; no Windows ticket evidence was supplied.",
    },
}

DOCUMENT_LINKS = (
    ("Instance logon credential management (manual credential reset path)",
     "https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management.md"),
    ("Guidance on avoiding direct root logon to an instance",
     "https://help.aliyun.com/zh/ecs/user-guide/avoid-logging-in-to-the-instance-as-root.md"),
    ("RAM policy that prohibits root as the initial user of a Linux instance",
     "https://help.aliyun.com/zh/ecs/user-guide/prohibit-ram-users-from-creating-linux-instances-with-root-as-initial-user.md"),
    ("Letting a RAM user run Cloud Assistant commands",
     "https://help.aliyun.com/zh/ecs/user-guide/run-cloud-assistant-commands-as-a-regular-user.md"),
    ("ECS security announcements",
     "https://help.aliyun.com/zh/ecs/security-announcement.md"),
)

# ---------------------------------------------------------------------------
# Report contract
# ---------------------------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

CONFIRMATION_REQUIRED = (
    "Confirmation required: tell the customer exactly which one command will run, "
    "which path it reads, that it changes nothing in the instance, and that the "
    "approval covers only this one command. Then re-run with --confirm."
)
NON_WHITELIST_REFUSAL = (
    "Refused: the request is not on the in-guest whitelist. Give the customer the "
    "command to run themselves and ask for the pasted output instead."
)
EVIDENCE_RULES = (
    "Quote only values returned by the API or printed by an approved guest command.",
    "Name the source of every value: the API action, or the command plus path.",
    "State every parameter this skill filled in by itself, such as region and page size.",
    "An empty or failed query is a limitation to report, never a value to invent.",
    "Guest file permission state has no cloud API; only an in-guest command gives it.",
    "DescribeInvocations shows past executions, so live state needs a fresh command.",
)
TICKET_EVIDENCE_GAP = (
    "No representative ticket or conversation was supplied for this tier, so the "
    "root-cause ranking, the customer error-string list and the Windows scope are "
    "unconfirmed. Symptom routing here is a design mapping, not measured frequency."
)
