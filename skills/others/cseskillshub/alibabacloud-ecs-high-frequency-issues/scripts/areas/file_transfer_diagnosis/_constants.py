"""Constants for the area:file-transfer-diagnosis skill scripts.

Everything the scripts need is declared here as code constants. No data files
are shipped under ``scripts/`` (see the deliverable whitelist).
"""

SKILL_NAME = "alibabacloud-ecs-file-transfer-diagnosis"

# User-agent template. ``{session_id}`` is a 32-char hex value generated once
# per script run and attached to every single CLI invocation.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

# ---------------------------------------------------------------------------
# CLI execution limits (every call is bounded; no unbounded subprocess waits)
# ---------------------------------------------------------------------------
CLI_TIMEOUT_SECONDS = 30
CLI_TIMEOUT_WRITE_SECONDS = 60
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRY_BACKOFF_FACTOR = 2.0

# Transient failure markers: only these are retried, everything else surfaces.
TRANSIENT_MARKERS = (
    "Throttling",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
    "SDK.ServerUnreachable",
    "timed out",
    "connection reset by peer",
)

# Authorization denials are reported with the literals the platform expects.
PERMISSION_MARKERS = (
    "NoPermission",
    "ImplicitDeny",
    "Unauthorized",
)

# Balance-driven stoppages: not an authorization problem, so they route to the
# account and billing handoff instead of the policy advice.
ARREARS_MARKERS = (
    "InvalidAccountStatus.NotEnoughBalance",
)

# ---------------------------------------------------------------------------
# API surface actually called by the scripts. Each entry was verified with
# ``aliyun <product> <action> --help`` metadata before being listed here, and
# each one is declared in related_apis.yaml and references/ram-policies.md.
# ---------------------------------------------------------------------------
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

API_QUERIES = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstancesFullStatus",
    "ecs:DescribeCloudAssistantStatus",
    "ecs:DescribeInvocations",
    "ecs:run-command",
    "sts:GetCallerIdentity",
)

PAGE_SIZE = 50
MAX_PAGE_ITEMS = 4  # hard stop so a bad filter can never loop unbounded

# ---------------------------------------------------------------------------
# In-guest inspection commands that may be sent after an explicit confirmation.
# Anything outside this map is refused by the scripts and printed as manual
# guidance for the customer to run and paste back instead.
# ---------------------------------------------------------------------------
GUEST_COMMAND_WHITELIST = {
    "df": {"-h", "-i", "--output", "--print-free", "--total", "-k", "-m", "-T"},
    "du": {"-x", "-s", "-h", "--max-depth", "--inodes", "--apparent-size", "--block-size"},
    "ls": {"-l", "-a", "-h", "-t", "-r", "-i", "-d", "-1", "-la", "-lh", "-lt"},
    "stat": set(),
    "findmnt": {"-l", "-t", "-o", "--submounts", "-r", "-n", "-R", "--TARGET"},
    "lsof": {"+L1", "-p", "-u", "-n", "-P"},
    "wc": {"-l", "-c", "-w"},
}

# Value-taking flags must be joined with '=' so they cannot be spoofed by an
# argument that is actually a following path.
GUEST_VALUE_FLAGS = {"--output", "--max-depth", "--block-size", "-o", "-p", "-u", "-t"}

# Reject shell composition and any redirect: the whitelist is inspection only.
DISALLOWED_COMMAND_CHARS = set(";&|<>$\n\r\\'`*?!(){}\"")
MAX_COMMAND_LENGTH = 400
MAX_PATH_LENGTH = 200

GUEST_COMMAND_PREAMBLE = (
    "The commands below only inspect state. They do not modify files, "
    "permissions, services or configuration."
)

# ---------------------------------------------------------------------------
# Branches of the decision tree (B0..B6) -- mirrored in
# references/file-transfer-diagnosis__symptom-taxonomy.md
# ---------------------------------------------------------------------------
BRANCHES = {
    "B0": "Product ownership gate: the transfer belongs to another product",
    "B1": "Channel misconception: which transfer path actually exists",
    "B2": "Cannot connect: port, protocol or security group reachability",
    "B3": "Connects but slow or stalled: bandwidth and link quality",
    "B4": "Transferred but rejected or invisible: path, permission, space",
    "B5": "Protocol mode details: active vs passive, concurrency, client fit",
    "B6": "Special paths: console one-time downloads, cross-account or "
          "cross-region bulk transfer, product capability limits",
}

# ---------------------------------------------------------------------------
# Error signatures collected verbatim from customer reports. Matching is
# case-insensitive substring matching on the customer's own error text.
# ---------------------------------------------------------------------------
ERROR_SIGNATURES = (
    {
        "pattern": "permission denied",
        "branch": "B4",
        "root_cause": "Upload landed on a path the login user cannot write",
        "confidence": "high",
        "next_action": "Re-upload into the site root (for example "
                       "/www/wwwroot/<site>) or switch the client to SFTP on "
                       "port 22 with the instance account.",
    },
    {
        "pattern": "econnrefused",
        "branch": "B5",
        "root_cause": "Server side refused the data connection: passive mode "
                      "port range not opened, or connection count limit hit",
        "confidence": "medium",
        "next_action": "Prefer SFTP, or configure the FTP server passive range "
                       "and open that range in the security group; limit "
                       "parallel connections from one client IP.",
    },
    {
        "pattern": "eai_noname",
        "branch": "B2",
        "root_cause": "Host name entered in the client is incomplete or not "
                      "resolvable",
        "confidence": "high",
        "next_action": "Re-enter the full public IP or resolved domain, and "
                       "verify the account name and password fields separately.",
    },
    {
        "pattern": "errno 110",
        "branch": "B2",
        "root_cause": "Outbound connection timed out (ETIMEDOUT) while "
                      "downloading from the instance",
        "confidence": "medium",
        "next_action": "Test the same download from the instance and from the "
                       "customer workstation, then compare; if only one side "
                       "fails, the local egress path is the suspect.",
    },
    {
        "pattern": "connection lost before handshake",
        "branch": "B2",
        "root_cause": "SSH session torn down before authentication completed",
        "confidence": "medium",
        "next_action": "Confirm which account is locked out or rate limited; "
                       "hand the credential part to the login credential "
                       "skill and keep only the transfer path here.",
    },
    {
        "pattern": "control connection",
        "branch": "B5",
        "root_cause": "FTP control channel times out after login, typical of a "
                      "passive data port range that is not opened",
        "confidence": "high",
        "next_action": "Switch to SFTP on port 22, or open the FTP server "
                       "passive range in the security group and set the same "
                       "range in the server configuration.",
    },
    {
        "pattern": "no folders available",
        "branch": "B1",
        "root_cause": "FTP account root is not a browsable directory the "
                      "customer can switch to",
        "confidence": "medium",
        "next_action": "Use SFTP with the instance account instead of FTP, or "
                       "set the FTP user home to the site directory.",
    },
    {
        "pattern": "can't connect to the remote computer",
        "branch": "B2",
        "root_cause": "Remote desktop unreachable: out of scope for this skill "
                      "unless a file transfer is blocked by it",
        "confidence": "low",
        "next_action": "Hand the connection fault to the remote connection "
                       "skill; keep only the upload path guidance here.",
    },
    {
        "pattern": "forcibly closed",
        "branch": "B5",
        "root_cause": "Connection reset during transfer, commonly an idle or "
                      "concurrency limit on the FTP service",
        "confidence": "low",
        "next_action": "Retry with one connection at a time, or compress the "
                       "files and transfer a single archive over SFTP.",
    },
)

# ---------------------------------------------------------------------------
# Symptom phrases that route a report without an error string. Each entry is a
# tuple of (branch, keyword substrings, root cause, next action).
# ---------------------------------------------------------------------------
SYMPTOM_ROUTES = (
    (
        "B0",
        ("web hosting", "wanwang", "cloud hosting", "wuying", "cloud desktop",
         "business licence", "renewal review"),
        "The FTP or upload the customer means belongs to another product, not "
        "to an ECS instance",
        "State the product boundary and route the customer to that product's "
        "own console and support channel.",
    ),
    (
        "B1",
        ("where is the upload", "console has no upload", "no upload button",
         "ftp account and password", "default ftp", "how to upload",
         "how to transfer", "which tool", "where can i see the password"),
        "No transfer path was chosen: ECS ships no FTP service and the "
        "connection page has no file transfer function of its own",
        "Give the transfer method selection table and one documented path "
        "matched to the direction, size and operating system.",
    ),
    (
        "B3",
        ("slow", "stuck", "stalled", "stalls", "speed", "very low", "hours",
         "timeout after long", "bandwidth full", "drops to", "takes forever"),
        "Transfer path works but throughput is limited by instance bandwidth "
        "peak or by the customer-to-instance network link",
        "Compare the configured peak against observed throughput, list the "
        "region pair, then route the link-quality part to the network "
        "diagnosis skill and the peak-value part to the bandwidth skill.",
    ),
    (
        "B4",
        ("uploaded but", "not visible", "cannot see the file", "404",
         "page not show", "wrong directory", "root directory", "c:\\",
         "site directory", "disk full", "no space left", "quota"),
        "Bytes arrive at an unintended location, or the target volume cannot "
        "accept them",
        "Split into the three sub-causes: wrong path, insufficient write "
        "permission, insufficient space or inodes; confirm with an in-guest "
        "inspection command or a customer-pasted result.",
    ),
    (
        "B6",
        ("key pair", ".pem", "download the certificate", "browser download",
         "cross account", "another account", "different region",
         "openapi", "api to download", "without public ip", "internal network"),
        "The request targets a capability boundary: console artifacts are "
        "downloadable once, and Cloud Assistant can push files but has no file "
        "download interface",
        "State the capability boundary plainly and recommend the documented "
        "alternative: object storage as an intermediary for bulk transfer, or "
        "re-issuing the console artifact.",
    ),
    (
        "B2",
        ("connect", "connection", "refused", "timeout", "cannot log in",
         "port", "security group", "unreachable", "reset by peer",
         "port 22", "port 21", "port 3389"),
        "The transfer port is not reachable: protocol port or passive range "
        "not allowed, service not listening, or the customer side is blocked",
        "Check instance state and attached security group, print the minimal "
        "allow list for the chosen protocol, and ask for a customer-side port "
        "test plus an alternate-network comparison.",
    ),
)

# ---------------------------------------------------------------------------
# Ports and protocols (references/file-transfer-diagnosis__transfer-methods.md holds the full table)
# ---------------------------------------------------------------------------
PORT_MATRIX = (
    ("SFTP / SCP / rsync", "TCP 22", "single port, no dynamic data range"),
    ("FTP", "TCP 21 + a passive data port range",
     "the passive range must be set on the server and allowed in the security "
     "group with an English slash, for example 39000/40000"),
    ("Remote desktop file drag and drop", "TCP 3389",
     "requires the remote desktop session and drive redirection"),
    ("Web panel upload", "panel port, often not the documented default",
     "the port the panel actually listens on must match the allowed rule"),
    ("Workbench file management", "browser to Workbench service",
     "no inbound customer-side port required"),
    ("Object storage intermediary", "HTTPS 443 to OSS",
     "no instance inbound port involved"),
)

# ---------------------------------------------------------------------------
# Handoff targets: this skill identifies and hands off, it does not implement
# the other symptom areas.
# ---------------------------------------------------------------------------
HANDOFFS = {
    "remote-connection": "SSH or RDP connection faults where no file transfer "
                         "is involved: route to the remote connection entry "
                         "skill for the protocol.",
    "credential": "Account lockout after repeated failed logins, password "
                  "reset, key pair re-issue: route to "
                  "area:login-credential-repair.",
    "network-quality": "Packet loss, latency and cross-border link quality as "
                       "the main complaint: route to "
                       "alibabacloud-mtr-network-diagnosis-customer.",
    "bandwidth": "Bandwidth peak change, billing mode and temporary upgrade "
                 "entries: route to area:bandwidth-modify-guide.",
    "disk-capacity": "Disk space or inode exhaustion as the main complaint: "
                     "route to the disk capacity governance skill.",
    "disk-expand": "A disk that was extended but the partition or file system "
                   "did not grow: route to "
                   "area:disk-expand-diagnosis.",
    "instance-state": "Instance stuck in a start or stop state: route to the "
                      "instance state skill.",
    "io-performance": "Disk IO latency and throughput below the declared "
                      "specification: route to the disk IO performance skill.",
    "billing": "Overdue balance stopping public bandwidth or the instance: "
               "route to the account and billing support channel.",
    "other-products": "Web Hosting FTP accounts, Wuying Cloud Desktop and "
                      "order review uploads: route to that product's support.",
}

# Regions outside mainland China where remote assistance on the instance is
# restricted by policy; in-guest inspection is therefore customer-run by
# default. Observed in customer reports for United States regions.
RESTRICTED_REMOTE_ASSISTANCE_KEYWORDS = ("us-east", "us-west", "us-southeast")

# Console-side metrics this skill cannot fetch with a verified action yet.
# Reported as gaps instead of being guessed at.
KNOWN_GAPS = (
    "Public bandwidth usage series: no verified metric action parameters are "
    "available to this skill, so ask the customer for a console Monitoring "
    "screenshot of inbound and outbound bandwidth over the transfer window.",
    "Security group rule details: no verified action is available to this "
    "skill, so the security group page must be read by the customer.",
    "Third-party dial testing and MTR from an observer network: not available "
    "in this skill; request a customer-side test on an alternate network.",
    "In-guest service listeners, firewall state, panel commands and traffic "
    "tools: outside the inspection whitelist, so printed as manual steps.",
)

# Documentation links used in guidance output (relative-path rule does not
# apply to external product documentation URLs).
DOC_LINKS = {
    "choose-transfer-method":
        "https://help.aliyun.com/zh/ecs/user-guide/choose-how-to-transfer-files.md",
    "upload-on-premises-to-ecs":
        "https://help.aliyun.com/zh/ecs/user-guide/upload-a-file-from-on-premises-to-an-ecs-instance.md",
    "console-instance-detail-upload-download":
        "https://help.aliyun.com/zh/ecs/user-guide/upload-and-download-files-on-the-instance-details-page.md",
    "workbench-upload":
        "https://help.aliyun.com/zh/ecs/user-guide/use-workbench-to-upload-a-file-to-a-linux-instance.md",
    "workbench-file-management":
        "https://help.aliyun.com/zh/ecs/user-guide/manage-files.md",
    "sftp-linux":
        "https://help.aliyun.com/zh/ecs/user-guide/use-sftp-to-upload-files-to-a-linux-instance.md",
    "winscp-linux":
        "https://help.aliyun.com/zh/ecs/user-guide/use-winscp-to-upload-a-file-to-a-linux-instance.md",
    "mstsc-windows":
        "https://help.aliyun.com/zh/ecs/user-guide/use-mstsc-exe-to-upload-a-file-to-a-windows-instance",
    "workbench-cli-connect":
        "https://help.aliyun.com/zh/ecs/user-guide/connect-to-an-instance-through-workbench-cli.md",
    "workbench-cli-manage":
        "https://help.aliyun.com/zh/ecs/user-guide/use-workbench-cli-to-manage-ecs-instances.md",
    "workbench-cli-in-agent":
        "https://help.aliyun.com/zh/ecs/user-guide/use-workbench-cli-to-operate-ecs-instances-in-ai-agent.md",
    "snapshot-console":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "snapshot-billing":
        "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "account-lockout":
        "https://help.aliyun.com/zh/ecs/for-safety-consideration-have-lock-the-user-account-the-reason-is-that-login-attempt-or-password-change-try-too-much",
}

REPORT_SECTIONS = (
    "Symptom classification",
    "Evidence collected",
    "Conclusion",
    "Actions",
    "Risk and backup notes",
    "Gaps",
)

STATUS_OK = "STATUS: OK"
STATUS_DEGRADED = "STATUS: DEGRADED"
STATUS_FAIL = "STATUS: FAIL"
