"""Constants for the ECS instance logon-credential repair triage skill.

All reference data (error dictionary, decision tree, guest check catalog,
playbook lines) lives here as in-script constants: standalone data files are
not allowed under ``scripts/``.

The scripts of this skill only ever CALL the inspection actions listed in
CLOUD_INSPECTION_WHITELIST below. The console actions named in
WRITE_ACTIONS_NEVER_AUTO are documented so the report can hand them to a human
as guided steps; they are not in the callable surface and no code path here
invokes them.
"""

SKILL_NAME = "alibabacloud-ecs-login-credential-repair"

# --- Observability -----------------------------------------------------------
# Attached to every single CLI invocation so a run is traceable end to end.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0

# Every product runs in plugin mode: the lowercase-hyphenated command form
# (sts GetCallerIdentity -> get-caller-identity). Callers pass PascalCase API
# action names; the CLI layer translates them.
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
PLUGIN_MODE_COMMANDS = {
("sts", "GetCallerIdentity"): "get-caller-identity",
}

ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_INSTANCE_ATTRIBUTE = "DescribeInstanceAttribute"
ACTION_DESCRIBE_KEY_PAIRS = "DescribeKeyPairs"
ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS = "DescribeCloudAssistantStatus"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"

# The complete callable surface of this skill: cloud inspection reads only.
# Anything outside this tuple is prohibited by design and is rejected at
# runtime by _cli.run_cli().
CLOUD_INSPECTION_WHITELIST = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceAttribute",
    "ecs:DescribeKeyPairs",
    "ecs:DescribeCloudAssistantStatus",
    "ecs:DescribeInvocations",
    "sts:GetCallerIdentity",
)

# Write-side actions that appear in tickets and in this skill's guidance, but
# which NO code path may ever execute or wrap in a runnable command. They are
# surfaced only as customer-executed steps (console or the equivalent OpenAPI) behind the snapshot-first and
# tell-and-confirm gates documented in SKILL.md.
WRITE_ACTIONS_NEVER_AUTO = (
    "ModifyInstanceAttribute (Password field: instance logon password reset)",
    "RunCommand (in-guest command execution)",
    "CreateSnapshot",
    "ResetPassword branch of the console reset wizard",
    "StartInstance / StopInstance / RebootInstance",
    "security-group rule edits (3389/22 source restriction)",
    "re-initialize-a-system-disk (destructive, security handoff)",
)

# --- Paging ------------------------------------------------------------------
PAGE_SIZE = 50
MAX_PAGES = 10
INVOCATION_PAGE_SIZE = 20
INVOCATION_MAX_RECORDS = 40

# --- Input guards ------------------------------------------------------------
# Region ids look like cn-hangzhou / ap-southeast-1.
REGION_ID_RE = r"^[a-z0-9][a-z0-9-]{2,48}$"
# Instance ids look like i-2zeexamplefd9e6793b6.
INSTANCE_ID_RE = r"^i-[a-z0-9][a-z0-9-]{3,62}$"
# A key pair name: conservative ASCII, never used as shell input.
KEY_PAIR_NAME_RE = r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{1,127}$"
# The account of an ARN is a long digit string.
ACCOUNT_ARN_DIGITS = 12

# --- OS families -------------------------------------------------------------
OS_WINDOWS = "windows"
OS_LINUX = "linux"
OS_UNKNOWN = "unknown"

# --- Instance states that matter for the reset path --------------------------
STATE_RUNNING = "Running"
STATE_STOPPED = "Stopped"

# --- Root-cause taxonomy (decision tree nodes) -------------------------------
# Each entry: (code, one-line meaning) and is rendered verbatim in reports so
# a ticket reviewer can map findings back to the tree in
# references/login-credential-repair__login-credential-decision-tree.md.
ROOT_CAUSE_TAXONOMY = (
    ("LC1", "Client-side target or cached-credential error: private IP used, non-default remote port, remembered old credentials, RDP username prefixed with the local computer name"),
    ("LC2", "Wrong logon username for this image: sshd forbids direct root login, image expects cloud-user or ecs-user, no root account in the guest"),
    ("LC3", "Online reset channel not usable: cloud assistant agent offline or the invocation failed, task shows success but the password never changed"),
    ("LC4", "Key pair interference: the instance is bound to a key pair, key-only logon is enforced, or the key pair was removed"),
    ("LC5", "Account locked: Windows lockout threshold triggered by repeated failed logon attempts, often from brute-force traffic against an openly exposed 3389"),
    ("LC6", "Account disabled or nonexistent: the logon account is disabled, deleted, or never existed (Windows administrator, guest, or an assumed Linux user)"),
    ("LC7", "Reset write blocked by the guest environment: disk full, security software interception (unverified hypothesis), or an offline reset awaiting a restart"),
    ("LC8", "Credential knowledge gap: password cannot be viewed and can only be reset; customer does not know the default username or console entry"),
    ("LC9", "Out of scope for this skill: transport failure, instance state fault, resource exhaustion, suspected intrusion, application-layer credential, commercial question"),
)

# --- Failure vocabulary ------------------------------------------------------
# Permission failures are reported with these literals only (E34 rule: never a
# 403-word label).
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"
CODE_PROHIBITED_ACTION = "ProhibitedAction"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# Transient conditions worth retrying.
RETRYABLE_MARKERS = (
    "throttling",
    "throttlingexception",
    "systembusy",
    "serviceunavailable",
    "internalerror",
    "internal failure",
    "temporar",
    "connection reset",
    "timed out",
    "timeout",
    "500",
    "502",
    "503",
    "429",
)

# Conditions that must never be retried.
NON_RETRYABLE_MARKERS = (
    "missingparameter",
    "invalidparameter",
    "signaturedoesnotmatch",
    "invalidaccesskeyid",
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "notfound",
    "invalidinstancienotfound",
)

# Credential-chain failures, classified apart from a generic API error because
# the recovery is to refresh the local CLI configuration rather than to retry
# or to request a permission.
CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid",
    "signaturedoesnotmatch",
    "invalidsecuritytoken",
    "securitytokenexpired",
    "invalidcredential",
)

# Credential material that must never reach the terminal or a log line.
SENSITIVE_KEY_PATTERNS = (
    r"accesskeyid",
    r"access[-_]key[-_]id",
    r"accesskeysecret",
    r"access[-_]key[-_]secret",
    r"securitytoken",
    r"security[-_]token",
    r"bearer token",
    r"signature",
    r"password",
    r"passwd",
    r"private key",
)
MASKED_VALUE = "***"

# --- Error / phrase dictionary ----------------------------------------------
# Quoted console and client strings observed in support evidence, plus natural
# customer phrasing (English and the Chinese console wording customers paste).
# Each entry: (branch, [match phrases], meaning shown in the report).
# Matching is case-insensitive substring matching done by the entry script.
ERROR_DICTIONARY = (
    ("LC2", ["please login as the user", "rather than the user 'root'", "use the user 'ecs-user'"],
     "The image forbids the attempted user and names the expected one"),
    ("LC1", ["your credentials did not work", "authentication error", "unable to connect",
             "unable to sign in", "无法连接", "登录失败"],
     "Client-side logon refusal; not by itself proof the password is wrong"),
    ("LC5", ["为安全考虑", "已锁定", "锁定该用户", "已经被锁定", "已被锁定",
             "locked out and may not be logged on", "has been locked", "account lockout",
             "暂时锁", "被锁"],
     "Windows account lockout policy is in effect for the attempted account"),
    ("LC6", ["account is disabled", "has been disabled", "already disabled", "禁用状态",
             "已禁用", "被禁用", "does not exist", "用户不存在", "不存在"],
     "The attempted account is disabled, deleted, or never existed"),
    ("LC4", ["key pair has been removed", "密钥对已被移除", "permission denied (publickey)",
             "original key pair", "passwordless", "免密"],
     "Key-pair based logon is involved: binding, removal, or key-only enforcement"),
    ("LC3", ["instruction execution failure", "指令执行失败", "execution failed",
             "task shows success", "shows success", "reset failed", "重置失败",
             "修改密码失败", "设置密码不生效", "不生效", "still cannot log in after reset",
             "timeout", "timed out"],
     "The online reset or its delivery channel did not complete cleanly"),
    ("LC7", ["no space left on device", "disk space", "磁盘空间不足", "空间不足"],
     "A guest-environment limit (typically a full disk) blocks the password write"),
    ("LC8", ["forgot", "忘记", "忘了", "不记得", "don't remember", "do not remember",
             "lost my password", "密码在哪", "where can i see the password",
             "查看密码", "不知道密码"],
     "Credential knowledge gap: what to use, where to see it, how to reset it"),
    ("LC1", ["private ip", "私网", "内网地址", "9898", "port 9898", "记住",
             "旧密码", "old password", "cached credential", "computer name"],
     "The client is talking to the wrong endpoint or replaying stale credentials"),
    ("LC9", ["security group whitelist", "安全组白名单", "安全组", "拒绝规则", "blackhole",
             "黑洞", "勒索", "加密了我的文件", "中毒", "病毒", "instance does not start",
             "无法启动", "起不来", "bt default", "bt 5", "宝塔", "500 internal server error",
             "没有权限安装", "以管理员身份运行", "内存", "cpu 100"],
     "The wording points at a neighboring area (network, state, security, app layer)"),
)

# --- In-guest reading catalog (customer-executed) -----------------------------
# The scripts of this skill never run these. They are printed so the customer
# can run each single line inside Workbench/VNC and paste back the output.
# Success criterion and side-effect class are part of every entry.
GUEST_READ_CHECKS = (
    (OS_LINUX, "Which logon users really exist",
     "getent passwd",
     "Names in the first column; note root, ecs-user, cloud-user, or a custom user"),
    (OS_LINUX, "Whether sshd forbids root / password / key logon",
     "grep -Ei 'PermitRootLogin|PasswordAuthentication|PubkeyAuthentication' /etc/ssh/sshd_config",
     "PermitRootLogin no and PasswordAuthentication no explain an ssh refusal even with the right password"),
    (OS_LINUX, "Account lock / password expiry state",
     "passwd -S <user> ; chage -l <user>",
     "A leading L or P status, or an expired date, on the attempted account"),
    (OS_LINUX, "Failed logon attempts and their source",
     "faillock --user <user> ; lastb",
     "Per-source failure counters; empty output means the guest logs nothing"),
    (OS_WINDOWS, "Effective lockout policy (query form only)",
     "net accounts",
     "Lockout threshold and lockout duration lines in the returned settings"),
    (OS_WINDOWS, "State of one local account (query form only)",
     "net user administrator",
     "Account active Yes/No and account expires fields"),
    (OS_WINDOWS, "Local accounts with disabled or locked flags",
     "Get-LocalUser | Format-Table Name,Enabled",
     "Enabled False marks a disabled account; a locked account fails logon while Enabled stays True"),
    (OS_WINDOWS, "Active remote desktop sessions",
     "query user",
     "Session names and states; no line means nobody is logged on remotely"),
    (OS_WINDOWS, "Actual RDP listening port",
     "netstat -ano | findstr 3389",
     "Nothing listening on 3389 means a non-default port or a stopped Remote Desktop service"),
    (OS_WINDOWS, "Failure source in the security log (query-only event read)",
     "Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625} -MaxEvents 20 | Format-Table TimeCreated,Message",
     "4625 events carry the failed account and source IP; empty means log access is restricted"),
)

# Commands that change state. The skill refuses to automate any of them and
# prints them only as human steps with the risk statement from the playbook.
WRITE_COMMANDS_HUMAN_ONLY = (
    "net accounts /lockoutthreshold:0 (resets the whole lockout policy: a write)",
    "net user <name> <newpassword> (changes a password from inside the guest)",
    "net user <name> /active:yes (enables an account)",
    "passwd <user> ; usermod -U <user> ; faillock --user <user> --reset (Linux)",
    "editing /etc/ssh/sshd_config and reloading sshd (Linux)",
    "gpedit.msc / secpol.msc policy edits and registry port edits (Windows)",
    "bt 5 (application-panel password, not an ECS logon credential)",
)

# --- Playbook line sets -------------------------------------------------------
# Each tuple is (scenario, [lines]) and lines are rendered under
# --- Playbook (manual steps; snapshot first for every write) ---.
PLAYBOOK_LOCKOUT_WINDOWS = (
    "Explain the mechanism first: Windows locks the account after the configured "
    "number of failed logon attempts, and brute-force traffic against an "
    "openly-exposed 3389 triggers it even when the owner never typed a password.",
    "Zero-write first path: log on through the console VNC session with the same "
    "credential. A successful interactive sign-in clears the lockout counter "
    "without touching any setting.",
    "Read the policy before changing anything: have the customer run the query "
    "form `net accounts` inside VNC or Workbench (command type Bat on Windows) "
    "and report the lockout threshold and duration.",
    "If the threshold must be reset, `net accounts /lockoutthreshold:0` is a "
    "POLICY WRITE: it must be run by the customer or a human engineer after a "
    "snapshot, and it weakens brute-force protection, so the same session must "
    "end with a sane threshold restored and a complex password.",
    "Root cause fix (manual, in the console): restrict 3389 ingress to the "
    "customer's own public IP (looked up with a public what-is-my-ip page), or "
    "move RDP to a non-default port. This skill neither reads nor edits "
    "security-group rules; state the console path instead.",
    "Expect recurrence while 3389 stays open to 0.0.0.0/0; when the customer's "
    "own IP changes frequently, say so plainly and recommend a complex password "
    "plus alerting rather than pretending a one-time unlock is a fix.",
)

PLAYBOOK_RESET_PASSWORD = (
    "A password can never be viewed, only reset. Say this first for the "
    "where-do-I-see-my-password question, and point at the credentials "
    "management help page.",
    "Default logon user: Linux root or ecs-user depending on the image (some "
    "marketplace images require cloud-user); Windows administrator.",
    "Online reset runs through the cloud assistant agent: if the agent check "
    "came back offline, do not retry online - go to VNC verification, then the "
    "offline reset path.",
    "Offline reset takes effect only after a restart: schedule the window with "
    "the business, stop applications so buffers flush to disk, and create a "
    "snapshot covering the SYSTEM disk before the restart.",
    "If the customer's only available reset keeps failing while the guest has a "
    "second enabled administrator account, changing the password from inside "
    "with that account needs no restart - offer it before the offline path.",
    "After any successful reset, walk the post-reset checklist: public IP "
    "versus private IP endpoint, non-default remote port, stale credentials "
    "cached by the client or Workbench (start a new session), and the RDP "
    "username field polluted with the local computer name.",
    "Ask the customer to save the new password in their own password manager "
    "immediately; never let the password flow into this conversation.",
)

PLAYBOOK_FORGOT_GENERIC = (
    "Answer the knowledge gap in one pass: credentials cannot be viewed, the "
    "default username per OS family, and where the public IP and the reset "
    "entry sit in the console.",
    "Offer the reset path that matches the evidence: online when the agent is "
    "confirmed online, offline with a restart window otherwise.",
    "If a snapshot rollback happened recently, warn that the logon password "
    "rolled back with the system disk to the snapshot creation time (low "
    "confidence operational note, verify on the reset path).",
    "For brand-new or trial instances, keep the answer to credentials and "
    "console entry only; hand file upload, pricing and plan questions to the "
    "onboarding and sales channels.",
)

PLAYBOOK_KEYPAIR_INTERFERENCE = (
    "A bound key pair can make the guest refuse password logon even when the "
    "password is correct: confirm the binding from instance facts, then decide "
    "with the customer between using the key and re-enabling password logon.",
    "The console binds key pairs for Linux only; Windows instances cannot use "
    "console key-pair binding (operational note from support evidence, verify "
    "against the current console before asserting it).",
    "Workbench passwordless logon relies on a temporary key pair mechanism: "
    "when it reports the key pair was removed, re-point the customer to "
    "password or VNC entry instead of chasing the temporary key.",
)

PLAYBOOK_CLIENT_CHECKLIST = (
    "Endpoint: local RDP/SSH must target the public IP (or an EIP); Workbench "
    "may use the private IP. A domain that resolves to the private address "
    "reproduces the exact credentials-wrong style failure.",
    "Port: if the remote port was moved off 22/3389, the client must carry it "
    "(RDP host:port syntax, ssh -p).",
    "Stale credentials: close the failed session and start a new connection, "
    "or switch instance in Workbench; cached old credentials fail with the "
    "same generic message.",
    "Username pollution: an RDP client that prefills <localcomputer>\\administrator "
    "authenticates against the laptop, not the server; edit the username to the "
    "bare account name and untick remember-credentials.",
    "Tie-breaker: the same credential inside a console VNC session decides "
    "between client-side path and server-side credential in one minute.",
)

PLAYBOOK_BY_BRANCH = {
    "LC5": PLAYBOOK_LOCKOUT_WINDOWS,
    "LC6": PLAYBOOK_LOCKOUT_WINDOWS,
    "LC3": PLAYBOOK_RESET_PASSWORD,
    "LC7": PLAYBOOK_RESET_PASSWORD,
    "LC8": PLAYBOOK_FORGOT_GENERIC,
    "LC4": PLAYBOOK_KEYPAIR_INTERFERENCE,
    "LC1": PLAYBOOK_CLIENT_CHECKLIST,
    "LC2": PLAYBOOK_CLIENT_CHECKLIST,
}

# --- Console navigation (text guidance only, never API-generated links) -------
CONSOLE_ENTRIES = {
    "instance_list": "ECS console > Instances & Images > Instances (select the exact region first)",
    "reset_password": "ECS console > instance row > All Operations > Instance Settings > Reset Instance Password (online needs a running agent; offline needs a restart)",
    "vnc": "ECS console > instance row > Remote & Connections > VNC / Workbench sign-in (needs no in-guest credential of its own to reach the logon screen)",
    "credentials_doc": "help.aliyun.com > ECS > User Guide > instance logon credential management",
    "security_group": "ECS console > Network & Security > Security Groups > Inbound Rules (manual review of 3389/22 sources; this skill never reads or edits rules)",
    "snapshot": "ECS console > Storage & Snapshots > Snapshots > Create Snapshot, covering the system disk (manual; billable)",
    "cloud_assistant": "ECS console > O&M > Cloud Assistant (region selector top-left; command type must match the OS: Bat for Windows CMD lines)",
}

# --- Handoff lines (out-of-scope areas) ----------------------------------------
HANDOFF_LINES = {
    "network": "The port never answers or the session times out before a logon "
               "prompt: that is a connectivity and security-group area; use the SSH "
               "connection or Windows RDP connection repair path (see "
               "references/login-credential-repair__handoff-scripts.md).",
    "instance_state": "The instance will not start or is stuck mid-transition: "
                      "hand off to instance-state diagnosis; do not attempt start/stop here.",
    "disk_capacity": "The guest cannot write the reset because the disk is full: "
                     "hand off to disk capacity / expand guidance; freeing space is a write.",
    "resource": "Logon succeeds but the desktop is black or lagging: resource "
                "exhaustion (memory/CPU) is a performance area, not a credential area.",
    "security": "Signs of ransomware, encrypted files, or a tampered account stop "
                "this workflow: no re-initialization, no guest changes from here; "
                "hand to the security incident process.",
    "app_credential": "Panel, site or application passwords (BaoTa example) are not "
                      "ECS logon credentials: application-level guidance only.",
    "commercial": "Plan, pricing, renewal and file-upload teaching belong to "
                  "onboarding and sales channels, not to this skill.",
}

# --- Report boilerplate --------------------------------------------------------
SENSITIVE_CREDENTIAL_NOTICE = (
    "Do not paste passwords into this conversation or a ticket. The skill "
    "never asks for, echoes, stores or transmits a password. If a password "
    "was already typed in plain text, reset it to a new value as the FIRST "
    "action after the incident closes. Use the masked/sensitive-message "
    "option of the ticket channel for anything unavoidable."
)

SNAPSHOT_FIRST_RULE = (
    "Snapshot first: before ANY state-changing step (in-guest configuration "
    "edit, password write, unlock policy change, restart for an offline reset) "
    "the customer creates a manual snapshot that covers the SYSTEM disk. "
    "Snapshots are billable; deleting them later is itself a manual step. "
    "Console navigation that changes nothing needs no snapshot."
)

TELL_AND_CONFIRM_RULE = (
    "Tell-and-confirm: before any guided action that changes state, state in "
    "one sentence what will run, its blast radius, whether it is reversible, "
    "and whether it costs money, and obtain an explicit yes that covers that "
    "single step only."
)
