"""Static constants for alibabacloud-ecs-server-migration-on-cloud: site-migration-guide.

All reference data used by the entry point lives here as code constants; no data files are
shipped inside scripts/.
"""

SKILL_NAME = "alibabacloud-ecs-server-migration-on-cloud: site-migration-guide"
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 60
CLI_MAX_RETRIES = 3
RETRY_BASE_SECONDS = 1.0
RETRY_MAX_SECONDS = 8.0
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
MAX_PAGES = 20

# Enforcement allow-list: anything outside this table is refused before the CLI is called.
ALLOWED_ACTIONS = {
    ECS_PRODUCT: frozenset([
        "DescribeInstances",
        "DescribeInstanceStatus",
        "DescribeAvailableResource",
        "DescribeInvocations",
    ]),
    STS_PRODUCT: frozenset(["GetCallerIdentity"]),
}

# Plugin-mode verbs (lowercase-hyphen) mapped to the API they call.
PLUGIN_VERBS = {
    STS_PRODUCT: {"GetCallerIdentity": "GetCallerIdentity"},
}

API_VERSION_BY_PRODUCT = {
    ECS_PRODUCT: ECS_API_VERSION,
    STS_PRODUCT: STS_API_VERSION,
}

TRANSIENT_ERROR_CODES = [
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "ServiceUnavailable",
    "InternalError",
    "SDK.ServerUnreachable",
    "SDK.HttpError",
    "RequestTimeout",
    "ConnectTimeout",
]

ERROR_CODE_MISSING_ACTION = "InvalidApi.NotFound"

# In-guest inspection commands the customer or their technician may run, one at a time, after an
# explicit announce-and-confirm. This skill does not execute them.
GUEST_COMMAND_ALLOWLIST = [
    {
        "os": "linux",
        "command": "df -h",
        "reads": "File systems, sizes and usage as the guest sees them, including the real "
                 "recognised system-disk size and which disks are mounted.",
    },
    {
        "os": "linux",
        "command": "df -i",
        "reads": "inode totals and free inodes per file system.",
    },
    {
        "os": "linux",
        "command": "du -x --max-depth=1 <path>",
        "reads": "Size of each first-level entry under one path, staying inside one file system.",
    },
    {
        "os": "linux",
        "command": "du -sh --inodes <path>/*",
        "reads": "Size and inode count per entry directly under one path.",
    },
    {
        "os": "linux",
        "command": "findmnt",
        "reads": "Current mount table: device, mount point and file system type.",
    },
    {
        "os": "linux",
        "command": "stat <path>",
        "reads": "Metadata of one file or directory: size, timestamps, link count.",
    },
    {
        "os": "linux",
        "command": "ls -l <path>",
        "reads": "Directory listing with sizes and timestamps; no writes.",
    },
    {
        "os": "linux",
        "command": "wc -l <file>",
        "reads": "Line count of one text file, for a quick completeness check.",
    },
    {
        "os": "linux",
        "command": "lsof +L1",
        "reads": "Open files with no directory link: space held by deleted-but-open files.",
    },
    {
        "os": "windows",
        "command": "Get-Volume",
        "reads": "Per-volume size and free space as Windows sees it.",
    },
    {
        "os": "windows",
        "command": "Get-PSDrive",
        "reads": "Used and free space per drive letter.",
    },
    {
        "os": "windows",
        "command": "Get-ChildItem <path> -File",
        "reads": "File listing of one directory with sizes; the command changes nothing.",
    },
    {
        "os": "windows",
        "command": "fsutil volume diskfree <driveLetter>:",
        "reads": "Total, free, and available bytes of one volume; a query subcommand with no change.",
    },
]

# Command words and operators that disqualify a command on a token match.
GUEST_COMMAND_DENY_MARKERS = [
    "rm ", "rmdir", "del ", "erase", "remove-item", "clear-content",
    "mv ", "move-item", "cp ", "copy-item", ">", ">>", "out-file", "set-content", "add-content",
    "truncate", "dd ", "kill", "stop-process", "taskkill",
    "systemctl", "service", "net start", "net stop", "iisreset", "restart-computer", "shutdown",
    "reboot", "mkfs", "fdisk", "parted", "diskpart", "format", "fsck", "tune2fs",
    "mount", "umount", "new-item", "install-module", "reg add", "reg delete", "set-member",
]

# Status and port inspection inside the guest is not automated by this build: ask the customer to
# run it and paste the output.
GUEST_COMMAND_MANUAL_ONLY = [
    "systemctl status <service>",
    "ss -lnt",
    "netstat -ano",
    "Get-Service",
    "Get-Process",
    "ipconfig /all",
]

# Customer-visible error strings that identify a known root cause. Keys are ASCII fragments.
KNOWN_ERROR_ANCHORS = [
    {
        "fragment": "Error establishing a database connection",
        "meaning": "The moved web application still points at the old database host, user, "
                   "password or name; the application configuration file was not updated after "
                   "the move.",
        "next_action": "Confirm the database is reachable from the new instance, then have the "
                       "customer update the application configuration file in the console or "
                       "through their own access, and reload the site.",
    },
    {
        "fragment": "OthersLinux_64",
        "meaning": "A server imported by a migration tool was not recognised as a mainstream "
                   "distribution, so the image type is OthersLinux and the console cannot reset "
                   "the root password for it.",
        "next_action": "Use an in-instance password change over the console connection, or attach "
                       "an SSH key pair, after taking a snapshot of the affected disk.",
    },
    {
        "fragment": "OthersLinux_32",
        "meaning": "Same console password-reset limitation as OthersLinux_64.",
        "next_action": "Use an in-instance password change over the console connection or an SSH "
                       "key pair; take a snapshot first.",
    },
    {
        "fragment": "pid file",
        "meaning": "A web server start attempt reported a missing PID file, which usually means "
                   "the service was not actually started, or a reload/check command was used "
                   "instead of a start command.",
        "next_action": "Have the customer start the service with the service manager themselves "
                       "and verify the listening port; service control is outside this skill.",
    },
    {
        "fragment": "NoPermission",
        "meaning": "The credential in use lacks one of the inspection actions.",
        "next_action": "Print the failing action and the matching statement from "
                       "references/ram-policies.md for an administrator to attach.",
    },
    {
        "fragment": "ImplicitDeny",
        "meaning": "The call is implicitly denied by the effective policy.",
        "next_action": "Report which action was denied and continue with the remaining evidence; "
                       "mark the report DEGRADED.",
    },
]

# Documentation entry points. Only links confirmed from customer-facing sources are listed; the
# remaining topics are explicitly marked as needing a link before publication and must not be
# filled in from memory.
HELP_LINKS = {
    "create_custom_image_from_instance":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance",
    "copy_image_cross_region":
        "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image",
    "create_instance_from_custom_image":
        "https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image",
    "reset_simple_application_server":
        "https://help.aliyun.com/zh/simple-application-server/user-guide/reset-a-simple-application-server",
    "operating_system_migration":
        "https://help.aliyun.com/zh/ecs/user-guide/migrate-the-operating-system-of-an-ecs-instance-1",
    "create_snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "create_snapshot_detail":
        "https://help.aliyun.com/document_detail/25455.html",
    "snapshot_billing":
        "https://help.aliyun.com/document_detail/56159.html",
    "unsubscription_rules":
        "https://help.aliyun.com/zh/user-center/user-guide/unsubscription-rules",
    "refund_destinations":
        "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations",
    "refund_rules":
        "https://help.aliyun.com/document_detail/116043.html",
    "self_service_refund_entry":
        "https://usercenter2.aliyun.com/refund/refund",
    "nas_pricing":
        "https://www.aliyun.com/price/product#/nas/detail/nas_bag",
    "billing_item_detail":
        "https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance",
    "initialize_linux_data_disk":
        "https://help.aliyun.com/zh/ecs/user-guide/initialize-a-data-disk-whose-size-does-not-exceed-2-tib-on-a-linux-instance",
    "instance_login_credentials":
        "https://help.aliyun.com/document_detail/2936588.html",
    "deploy_lnmp":
        "https://help.aliyun.com/zh/ecs/user-guide/deploy-lnmp.md",
    "build_a_website":
        "https://help.aliyun.com/zh/ecs/user-guide/build-a-website.md",
}

# Topics whose official link was not confirmed in this build. The skill must say "needs manual
# confirmation" instead of inventing a URL.
HELP_LINKS_PENDING = [
    "instance transfer between accounts (procedure and conditions)",
    "share a custom image with another account",
    "replace the operating system of an ECS instance",
    "Server Migration Center (SMC) agent-based migration",
    "modify a DNS record in Cloud DNS",
    "add an inbound security-group rule",
    "prefix lists and port range lists",
    "driver requirement reported for newer instance families",
]

# Cutover ports that a moved web or application server normally needs, as a manual checklist.
CUTOVER_PORTS_HINT = [
    {"port": "22", "use": "SSH login on Linux"},
    {"port": "3389", "use": "Remote Desktop login on Windows"},
    {"port": "80", "use": "HTTP site"},
    {"port": "443", "use": "HTTPS site"},
    {"port": "app", "use": "application or control-panel port, for example 8888"},
]

ADJACENT_SKILLS = {
    "disk-expand": "alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis",
    "instance-state": "alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis",
    "disk-io": "alibabacloud-ecs-disk-io-and-data-protection: disk-io-diagnosis",
    "backup-image": "alibabacloud-ecs-disaster-recovery-image",
}

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
