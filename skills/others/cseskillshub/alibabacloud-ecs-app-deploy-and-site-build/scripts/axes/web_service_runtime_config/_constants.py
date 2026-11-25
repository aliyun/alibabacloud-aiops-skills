"""Constants and embedded knowledge tables for the ECS web service and runtime
environment configuration skill.

Every table this skill needs is embedded here as a Python constant: ``scripts/``
must contain executable code only, so no knowledge lives in a side file.

Content policy: each entry is derived either from this skill tier's ticket
evidence (the ``evidence`` field carries the ticket id) or from an Alibaba Cloud
help page that appeared in that evidence. Where the evidence says there is no
official statement, the entry says so instead of inventing a support matrix.
"""

SKILL_NAME = "alibabacloud-ecs-web-service-runtime-config"

# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

CLI_BIN = "aliyun"

PRODUCT_ECS = "ecs"
PRODUCT_CMS = "cms"
PRODUCT_STS = "sts"

# Documented API versions. ECS and STS are verified; the CloudMonitor version
# was not verified in this batch and is deliberately left empty rather than
# guessed (see references/ram-policies.md).
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
CMS_API_VERSION = ""

# Every product runs in plugin mode (lowercase-hyphenated command name). The
# constant below holds the PascalCase API action name; the CLI layer translates
# it to get-caller-identity before building the argv.
STS_PLUGIN_COMMAND = "GetCallerIdentity"

USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

CLI_TIMEOUT_SECONDS = 60
GUEST_CLI_TIMEOUT_SECONDS = 180
INVOCATION_POLL_TIMEOUT_SECONDS = 180
INVOCATION_WAIT_SECONDS = 6.0
INVOCATION_MAX_POLLS = 10
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5
RETRY_JITTER_SECONDS = 0.5

# Cloud Assistant execution timeout requested for a single observation command.
GUEST_COMMAND_TIMEOUT_SECONDS = 60

MAX_INSTANCE_IDS = 10
MAX_SECURITY_GROUPS = 10
MAX_PORTS = 20
MAX_PATH_CHARS = 256

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

SOURCE_CLOUD = "cloud-query"
SOURCE_GUEST = "guest-observation"
SOURCE_CUSTOMER = "customer-stated"
SOURCE_DOC = "help-doc"
SOURCE_MODEL = "whitelist-pending"

CONFIRMATION_PHRASES = ("confirm", "confirmed", "yes", "approve", "approved", "agreed")

# ---------------------------------------------------------------------------
# Symptom routing
# ---------------------------------------------------------------------------

# Scenario codes follow the tier's capability areas.
SCENARIOS = {
    "A": {
        "title": "Runtime or language environment install / OS compatibility",
        "keywords": (
            "java", "jdk", "jre", "php", "python", "node", "node.js", "nodejs",
            ".net", "dotnet", "tomcat", "golang", " go ", "gcc", "runtime",
            "environment", "version", "interpreter", "moby", "docker-ce",
            "sql server", "net framework", "install", "rebuild environment",
            "not supported", "ansible",
        ),
        "default_ports": (),
        "guest_checks": ("runtime-version-facts", "installed-package-facts"),
    },
    "B": {
        "title": "Web server (Nginx / Apache / IIS / FTP) configuration or startup",
        "keywords": (
            "nginx", "apache", "httpd", "iis", "ftp", ".htaccess", "rewrite",
            "virtual host", "reverse proxy", "proxy", "403", "certificate chain",
            "app pool", "application pool", "w3wp", "fastcgi", "cgi", "502",
            "503", "config", "conf", "restart", "start", "won't start",
        ),
        "default_ports": (80, 443),
        "guest_checks": ("service-listening", "web-config-test", "service-log-tail"),
    },
    "C": {
        "title": "Container (Docker / Kubernetes) deployment configuration",
        "keywords": (
            "docker", "dockerfile", "docker-compose", "compose", "k8s",
            "kubernetes", "helm", "container", "image", "pull", "registry",
            "restart policy", "volume", "mount", "orchestration", "pod",
            "dify", "1panel", "containerd", "moby", "daemon.json",
        ),
        "default_ports": (),
        "guest_checks": ("container-facts", "registry-mirror-config", "image-pull-selftest"),
    },
    "D": {
        "title": "Open-source site application environment (WordPress and similar)",
        "keywords": (
            "wordpress", "wp-admin", "wp-config", "dedecms", "thinkphp",
            "laravel", "discuz", "zblog", "joomla", "drupal", "typecho",
            "magento", "opencart", "pbootcms", "empire cms", "bt panel",
            "aaPanel", "panel", "siteurl", "redirect", "https", "ssl",
        ),
        "default_ports": (80, 443),
        "guest_checks": ("service-listening", "php-extension-facts", "site-address-config"),
    },
    "E": {
        "title": "Resource pressure that explains a service or site failure",
        "keywords": (
            "out of memory", "oom", "killed", "memory full", "memory high",
            "cpu 100", "cpu full", "bandwidth full", "hang", "frozen",
            "unresponsive", "hung", "swap", "php-fpm", "mysqld",
        ),
        "default_ports": (),
        "guest_checks": ("memory-and-oom-facts", "service-listening"),
    },
}

# Error strings and codes this tier may quote back to the customer. The
# interpretation is deliberately narrow: each entry states what the string does
# NOT license the skill to conclude, because several tier tickets show an
# unverified summary blaming the platform.
ERROR_STRING_RULES = {
    "Connection refused": {
        "customer_wording": "connection refused",
        "means": (
            "nothing accepted the TCP connection: no listener on that port, a "
            "listener bound to a loopback address only, or an inbound rule that "
            "was never added"
        ),
        "next_branch": (
            "check inbound port rules first (cloud query), then the actual "
            "listen address (in-instance observation)"
        ),
        "must_not_conclude": (
            "the platform blocked the port - ticket evidence records the "
            "explicit statement that Alibaba Cloud does not block a customer "
            "proxy port"
        ),
        "evidence": "T-0C2557E6, T-9C6BB0CC",
    },
    "Connection reset": {
        "customer_wording": "connection reset / the remote host closed the connection",
        "means": (
            "the peer tore down an established connection: TLS or certificate "
            "mismatch, a device or proxy in the middle, a security penalty, or "
            "an ISP-side block"
        ),
        "next_branch": (
            "self-test the same URL from the instance itself, then split: local "
            "test passes but external fails goes to the outbound / compliance "
            "branch, local test also fails stays on the service branch"
        ),
        "must_not_conclude": (
            "platform interception; the closest ticket ended without a proven "
            "cause, so report candidates only"
        ),
        "evidence": "T-0C2557E6, T-E63D76D9",
    },
    "err_connection_reset": {
        "customer_wording": "browser error page ERR_CONNECTION_RESET",
        "means": "browser-visible form of a reset connection",
        "next_branch": "same split as 'Connection reset'; also ask for a different browser and a different access path before touching the server",
        "must_not_conclude": "a server-side fault; one ticket closed as local browser cache",
        "evidence": "T-04E91CE7, T-4729827E",
    },
    "timed out": {
        "customer_wording": "timed out",
        "means": (
            "three unrelated causes look identical here: Docker Hub reachability "
            "from a mainland region, cross-border latency, or a suspended "
            "pay-by-traffic bandwidth service"
        ),
        "next_branch": (
            "separate them by asking whether the failing address is an outbound "
            "public destination, which region the instance is in, and whether "
            "the account has an unpaid balance"
        ),
        "must_not_conclude": "one shared root cause; the three tickets resolved in three different directions",
        "evidence": "T-C59D3702, T-A692D630, T-7C096742",
    },
    "err_connection_timed_out": {
        "customer_wording": "browser error page ERR_CONNECTION_TIMED_OUT",
        "means": "browser-visible form of a timeout",
        "next_branch": "run the same separation as 'timed out'; a mainland region plus a Docker Hub address is the first thing to rule out",
        "must_not_conclude": "that the server is down",
        "evidence": "T-C59D3702",
    },
    "err_cert_date_invalid": {
        "customer_wording": "browser error page ERR_CERT_DATE_INVALID",
        "means": (
            "the presented certificate is outside its validity window, most often "
            "because the guest clock is wrong or the certificate was not yet "
            "valid / has expired"
        ),
        "next_branch": (
            "CANDIDATE BRANCH ONLY: suggest checking the instance clock and the "
            "certificate validity dates; do not change either automatically"
        ),
        "must_not_conclude": (
            "that this skill has a proven fix - there is no ticket in this tier "
            "whose dialogue reached a certificate-date conclusion; a WordPress "
            "'not secure' report turned out to be a site-address setting, not a "
            "certificate date"
        ),
        "evidence": "no ticket evidence (evidence gap)",
    },
}

# Verbatim error text that customers pasted in this tier's tickets. Kept as-is
# so the skill recognises it instead of paraphrasing it.
QUOTED_TICKET_ERRORS = {
    "SyntaxError: Missing parentheses in call to 'print'": {
        "means": "a script embedded in the customer's own automation used Python 2 syntax against a Python 3 interpreter",
        "next_branch": "ask for the script body; an interpreter-override attempt that fails does not disprove a syntax cause",
        "evidence": "T-8D57CDFD",
    },
    "symbol lookup error: php-fpm: undefined symbol: zip_libzip_version": {
        "means": "the system library providing the zip extension is older than the newly installed PHP build expects",
        "next_branch": "dependency library mismatch; the repair changes system libraries, so it is a manual step with a snapshot taken first",
        "evidence": "T-B0960B66",
    },
    "java.net.NoRouteToHostException: No route to host": {
        "means": "the destination was unreachable at the IP layer from the caller",
        "next_branch": "confirm the process and its listen address, then the inbound rules, then the caller's own access path",
        "evidence": "T-0C2557E6",
    },
    "dial tcp": {
        "means": "an outbound dial failed, typical of a Docker Hub pull from a mainland region",
        "next_branch": "outbound reachability branch; note that Docker Hub access from mainland regions was affected by an upstream change",
        "evidence": "T-C59D3702",
    },
    "NoPermission": {
        "means": "the caller's identity lacks the RAM action the query needs",
        "next_branch": "name the missing action and the least-privilege policy fragment from references/ram-policies.md",
        "evidence": "API contract",
    },
    "ImplicitDeny": {
        "means": "no policy allows the action, so it is denied implicitly",
        "next_branch": "same as NoPermission: report the missing action, never broaden to a wildcard",
        "evidence": "API contract",
    },
}

# ---------------------------------------------------------------------------
# Port facts
# ---------------------------------------------------------------------------

PORT_CONTEXT = {
    80: {"service": "HTTP site", "evidence": "T-9C6BB0CC, T-713A543E"},
    443: {"service": "HTTPS site", "evidence": "T-9C6BB0CC, T-E63D76D9"},
    21: {"service": "FTP control channel", "evidence": "T-759C3C05"},
    22: {"service": "SSH", "evidence": "T-4729827E"},
    3389: {"service": "Windows remote desktop", "evidence": "T-CA03A3F6"},
    3128: {"service": "Squid proxy listener", "evidence": "T-0C2557E6"},
}

# IIS FTP in passive mode needs a data-port range as well as port 21; the
# ticket range is the Windows default.
FTP_PASSIVE_RANGE = (49152, 65535)
FTP_PASSIVE_NOTE = (
    "port 21 alone is not enough for IIS FTP in passive mode: the data port "
    "range (Windows default 49152-65535) must be opened in the security group "
    "AND in the Windows firewall, or transfers fail after the control "
    "connection succeeds"
)

# ---------------------------------------------------------------------------
# In-instance observation
# ---------------------------------------------------------------------------

# approval="approved": the command is inside this batch's low-risk command
#   list, so `guest-run` may issue it through Cloud Assistant after the
#   announce-and-confirm gate.
# approval="pending": the observation is needed by this tier's semantics but the
#   exact command is NOT in the approved list (the injected list is worded for
#   the disk-capacity tier). Until the batch owner signs it off, the skill must
#   print the command for the customer to run and paste back, and report the
#   item as missing. Never guess a substitute command.
GUEST_CHECKS = {
    "disk-space-facts": {
        "title": "filesystem usage, as a side witness when a service refuses to start",
        "approval": "approved",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "df -h",
        "customer_command": "df -h",
        "reversibility": "prints usage only; changes nothing",
        "evidence": "approved in this batch's low-risk command list",
    },
    "disk-inode-facts": {
        "title": "inode usage, as a side witness when writes fail during startup",
        "approval": "approved",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "df -i",
        "customer_command": "df -i",
        "reversibility": "prints counters only; changes nothing",
        "evidence": "approved in this batch's low-risk command list",
    },
    "mount-facts": {
        "title": "what is actually mounted where, when a data directory looks empty",
        "approval": "approved",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "findmnt",
        "customer_command": "findmnt",
        "reversibility": "prints the mount table only; changes nothing",
        "evidence": "approved in this batch's low-risk command list",
    },
    "deleted-open-files": {
        "title": "files still held open after deletion, when space did not come back",
        "approval": "approved",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "lsof +L1",
        "customer_command": "lsof +L1",
        "reversibility": "lists descriptors only; changes nothing",
        "evidence": "explicitly listed as low risk in this batch's decision notes",
    },
    "path-size": {
        "title": "size of one named directory, when a log or data path is suspected of filling the disk",
        "approval": "approved",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "du -sh %PATH%",
        "customer_command": "du -sh <absolute path>",
        "requires_path": True,
        "reversibility": "prints one size; changes nothing",
        "evidence": "approved in this batch's low-risk command list",
    },
    "path-facts": {
        "title": "owner, timestamps and inode of one named path, when a service refuses to read it",
        "approval": "approved",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "stat %PATH%",
        "customer_command": "stat <absolute path>",
        "requires_path": True,
        "reversibility": "prints metadata; changes nothing",
        "evidence": "approved in this batch's low-risk command list",
    },
    "service-listening": {
        "title": "which process holds which port and on which address",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "netstat -tunlp",
        "customer_command": "sudo netstat -tunlp",
        "reversibility": "prints sockets only; changes nothing",
        "evidence": "T-9C6BB0CC, T-0C2557E6 (the human agent used this exact command to decide)",
    },
    "web-config-test": {
        "title": "web server configuration syntax check without writing anything back",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "nginx -t",
        "customer_command": "sudo nginx -t",
        "reversibility": "parses the config and reports; does not reload or restart",
        "evidence": "T-E923DA06 (a version switch left nginx unhealthy and was never inspected in the guest)",
    },
    "service-log-tail": {
        "title": "tail of the service's own log around the failure time",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "journalctl -u nginx -n 50 --no-pager",
        "customer_command": "sudo journalctl -u nginx -n 50 --no-pager",
        "reversibility": "reads log records only; never rotates or vacuums",
        "evidence": "T-0C2557E6 (squid cache.log held the decisive timeline, system logs did not)",
    },
    "service-state": {
        "title": "whether a service unit is loaded and enabled, without changing it",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "systemctl status nginx --no-pager",
        "customer_command": "systemctl status nginx --no-pager",
        "reversibility": "status form only; start, stop, restart and enable stay out of scope",
        "evidence": "T-43513829, T-CA03A3F6",
    },
    "runtime-version-facts": {
        "title": "interpreter and compiler versions actually installed",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "python3 -V",
        "customer_command": "python3 -V",
        "reversibility": "prints a version string; changes nothing",
        "evidence": "T-8D57CDFD (a Python 2 vs 3 mismatch), T-F51E65E5 (Node.js)",
    },
    "php-extension-facts": {
        "title": "PHP build and the extensions it loaded",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "php -m",
        "customer_command": "php -m",
        "reversibility": "lists loaded extensions; changes nothing",
        "evidence": "T-B0960B66 (a missing zip symbol blocked every PHP version)",
    },
    "installed-package-facts": {
        "title": "installed package inventory, to spot a missing dependency library",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "rpm -qa",
        "customer_command": "rpm -qa | grep -i libzip",
        "reversibility": "lists packages; changes nothing",
        "evidence": "T-B0960B66, T-A9825E98",
    },
    "memory-and-oom-facts": {
        "title": "free memory plus the kernel's OOM record",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "free -m",
        "customer_command": "free -m && dmesg -T | grep -i oom",
        "reversibility": "prints counters and kernel messages; changes nothing",
        "evidence": "T-0868235B (17 OOM events killed mysqld, php-fpm and nginx)",
    },
    "container-facts": {
        "title": "container restart policy, mounts and restart count",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "docker ps -a",
        "customer_command": "docker ps -a && docker inspect --format '{{.HostConfig.RestartPolicy.Name}} {{.Mounts}}' <container>",
        "reversibility": "reads container metadata; never removes, stops or recreates",
        "evidence": "T-1EB845AD, T-F4F68F93",
    },
    "registry-mirror-config": {
        "title": "currently configured registry mirrors",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "cat /etc/docker/daemon.json",
        "customer_command": "cat /etc/docker/daemon.json",
        "reversibility": "prints one configuration file; changes nothing",
        "evidence": "T-C59D3702",
    },
    "image-pull-selftest": {
        "title": "outbound reachability self-test for an image pull",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "docker pull hello-world",
        "customer_command": "docker pull hello-world",
        "reversibility": "pulls into the local image cache only; writes no customer data",
        "evidence": "T-C59D3702",
    },
    "site-address-config": {
        "title": "site address stored by the web application",
        "approval": "pending",
        "os_types": ("linux",),
        "command_type": "RunShellScript",
        "command": "grep -R -E \"siteurl|home\" wp-config.php",
        "customer_command": "grep -R -E \"siteurl|home\" wp-config.php",
        "reversibility": "reads configuration values; changes nothing",
        "evidence": "T-F701AEBC (a site address written as an IP caused the redirect)",
    },
}

# Exact commands a gated in-instance call may run verbatim. Entries that need a
# path are handled through APPROVED_EXECUTABLES plus the path validator below.
APPROVED_EXACT_COMMANDS = tuple(
    entry["command"] for entry in GUEST_CHECKS.values()
    if entry["approval"] == "approved" and not entry.get("requires_path")
)

# Only these binaries may start a gated in-instance command. Everything else in
# GUEST_CHECKS is approval="pending" and is printed for the customer to run,
# never executed by this skill.
APPROVED_EXECUTABLES = ("df", "findmnt", "lsof", "du", "stat")

# Only these two approved entries accept a path argument.
PATH_COMMANDS = ("du", "stat")

# A command is rejected outright if any of these appear, even inside a command
# that otherwise looks like a query. The list is deliberately conservative:
# a single false rejection costs one extra manual step, a false acceptance
# changes a customer's system.
SIDE_EFFECT_COMMAND_PATTERNS = (
    r"\brm\b", r"\brmdir\b", r"\bmv\b", r"\bcp\b", r"\bdd\b", r"\bkill\b",
    r"\bpkill\b", r"\bkillall\b", r"\breboot\b", r"\bshutdown\b", r"\bhalt\b",
    r"\btruncate\b", r"\bmkfs\b", r"\bfsck\b", r"\btune2fs\b", r"\bresize2fs\b",
    r"\bchmod\b", r"\bchown\b", r"\bsetfacl\b", r"\bmount\b", r"\bumount\b",
    r"\bparted\b", r"\bgdisk\b", r"\bfdisk\b", r"\bwipefs\b",
    r"\btee\b", r">", r">>", r"\bsed\b\s*-i", r"\bawk\b.*\bsystem\b",
    r"\bapt\b", r"\byum\b", r"\bdnf\b", r"\brpm\b\s*-", r"\bpip\b", r"\bnpm\b",
    r"\bsystemctl\b\s*(start|stop|restart|reload|enable|disable|mask|unmask|daemon-reload|reset-failed|edit)",
    r"\bservice\b\s*\S+\s*(start|stop|restart|reload)",
    r"\bjournalctl\b.*(--rotate|--vacuum|--flush|--flush-wait|-q\s*--)",
    r"\bdocker\b\s*(rm|rmi|stop|start|restart|kill|prune|run|exec|update|create|build|volume\s*rm)",
    r"\bkubectl\b\s*(delete|apply|scale|cordon|drain|taint|edit|patch|rollout|annotate|label)",
    r"\biisreset\b", r"\breg\b", r"\bnetsh\b", r"\bnet\s+(start|stop|localgroup|user)",
    r"\bNew-", r"\bSet-", r"\bRemove-", r"\bClear-", r"\bStop-", r"\bStart-",
    r"\bRestart-", r"\bInstall-", r"\bUninstall-", r"\bdel\b", r"\brd\b",
    r"\bsc\s+(start|stop|config|delete|create)", r"\btaskkill\b",
    r"\bupdate-ca-certificates\b", r"\bdate\s+-s\b", r"\btimedatectl\b\s*(set|sync)",
)

SAFE_PATH_PATTERN = r"^/[A-Za-z0-9._/-]{0,254}$"

# ---------------------------------------------------------------------------
# Non-fault mechanisms (Cap-8)
# ---------------------------------------------------------------------------

# Several tickets in this tier are "the platform is broken" reports where the
# behaviour is documented and expected. Ruling these out comes before digging
# into a customer's configuration, because the opposite order produces long
# dead-end threads.
NON_FAULT_MECHANISMS = (
    {
        "trigger": ("stopping", "stopped", "restarting", "shutdown", "power off", "turned off", "auto stop"),
        "mechanism": (
            "a console restart without the forced option releases processes and "
            "flushes memory to the disk before the guest kernel stops: normally "
            "5-10 minutes, up to 15, and nothing can be done meanwhile"
        ),
        "action": "wait out the window, then re-test; a genuinely stuck instance belongs to the instance-state area",
        "evidence": "T-E923DA06",
    },
    {
        "trigger": ("everything stopped at the same time", "services disappeared", "auto closed", "scheduled shutdown", "turned off at night"),
        "mechanism": (
            "an OOS scheduled start/stop task, left behind by a previous "
            "administrator, shuts the whole instance down at a fixed time"
        ),
        "action": "hand off to the instance-state area plus the OOS task list; deleting the task is a manual step",
        "evidence": "T-43513829",
    },
    {
        "trigger": ("cannot create image", "pull timeout", "dockerhub", "docker hub", "registry timeout"),
        "mechanism": (
            "Docker Hub reachability from mainland regions was affected by an "
            "upstream change on Docker's side"
        ),
        "action": (
            "state the reachability fact; do not recommend third-party mirror "
            "addresses as if they were official - the ones an agent pasted in "
            "the ticket were third party"
        ),
        "evidence": "T-C59D3702",
    },
    {
        "trigger": ("port works but http does not", "ping ok", "telnet ok", "domain not working"),
        "mechanism": (
            "a domain pointing at a mainland-region server must have completed "
            "ICP filing before it can serve a site"
        ),
        "action": "raise filing as the first candidate when the network layer tests pass and HTTP still fails; hand off to the filing process",
        "evidence": "T-713A543E",
    },
    {
        "trigger": ("tcp handshake fine", "response not received", "retransmit", "cannot reach internet"),
        "mechanism": (
            "a pay-by-traffic bandwidth service with an unpaid balance is "
            "suspended, so outbound response packets are stopped even though the "
            "guest sent them"
        ),
        "action": "check billing state (handoff) before assuming a service fault",
        "evidence": "T-7C096742",
    },
    {
        "trigger": ("overseas users cannot open", "other country slow", "international access"),
        "mechanism": "cross-border latency, not a platform restriction",
        "action": "state that no restriction was found and hand off the network path question",
        "evidence": "T-A692D630",
    },
    {
        "trigger": ("security group cannot be deleted", "ip still occupied", "eci"),
        "mechanism": "after an ECI instance is deleted its elastic network interface can persist for up to 30 minutes",
        "action": "wait, then retry; this is another product's lifecycle, not this skill's",
        "evidence": "T-35437580",
    },
    {
        "trigger": ("bill has no tag", "cost split missing", "label not shown"),
        "mechanism": "billing detail is produced on a T+1 cycle, and pod tags must be written as annotations, not labels",
        "action": "hand off to the cost-tagging area",
        "evidence": "T-BBB17081",
    },
    {
        "trigger": ("cdn internal address", "internal network cdn"),
        "mechanism": "CDN is served over the public network; there is no internal-network form of it",
        "action": "correct the premise before continuing any diagnosis",
        "evidence": "T-48D25F5F",
    },
)

# ---------------------------------------------------------------------------
# OS and runtime support facts (Cap-1 output vocabulary)
# ---------------------------------------------------------------------------

OS_RUNTIME_SUPPORT = (
    {
        "os": "Alibaba Cloud Linux 3",
        "fact": "the console one-click deployment scripts target this release",
        "action": "one-click deployment is applicable; verify the release before telling a customer a product is unsupported",
        "evidence": "T-F51E65E5",
    },
    {
        "os": "Alibaba Cloud Linux 4 LTS 64-bit",
        "fact": "docker-ce is not supported by default on this release; the supported container runtime is moby",
        "action": "install moby for Docker capability instead of troubleshooting the docker-ce installation",
        "evidence": "T-A9825E98",
    },
    {
        "os": "Windows Server",
        "fact": "Linux-oriented one-click deployment scripts do not apply",
        "action": "guide the manual installation path from the help catalogue instead of reporting the product as unsupported",
        "evidence": "T-F51E65E5, T-10715A07",
    },
    {
        "os": "Windows Server (.NET Framework 3.5 install failure)",
        "fact":
            "a conflicting cumulative patch can block the .NET Framework 3.5 "
            "installation through Cloud Assistant",
        "action": (
            "point to the public-image known-issues page for the patch removal "
            "path; removal plus a reboot is manual, and a snapshot must exist "
            "beforehand. The exact patch number in the ticket was only visible "
            "in a screenshot, so do not quote a patch id"
        ),
        "evidence": "T-BA3E2F89",
    },
    {
        "os": "Alibaba Cloud Linux 4 LTS 64-bit (MongoDB 8.0 Community)",
        "fact": "there is no official compatibility statement for this combination",
        "action": "report 'no official statement' verbatim; never invent a support matrix",
        "evidence": "T-A9825E98",
    },
    {
        "os": "Rocky Linux 10 with a Python 3 default interpreter",
        "fact": "automation written against Python 2 syntax fails on it while succeeding on older images",
        "action": (
            "ask for the script body before naming a cause: forcing the "
            "interpreter did not help in the ticket, the Python 2 print "
            "statement did"
        ),
        "evidence": "T-8D57CDFD",
    },
    {
        "os": "any (SQL Server 2008 on a current Windows release)",
        "fact": "the operating system version no longer supports that product version",
        "action": "state the incompatibility and stop; there was no workaround in the ticket",
        "evidence": "T-BA3E2F89",
    },
)

# ---------------------------------------------------------------------------
# Handoff matrix (Cap-9)
# ---------------------------------------------------------------------------

HANDOFF_MATRIX = (
    {
        "symptom": ("extension install failed", "cloud assistant", "plugin install", "one-click deploy failed", "command extension"),
        "target": "alibabacloud-ecs-install-extension",
        "boundary": (
            "the install action itself failing (plugin missing, delivery failed, "
            "task status abnormal, extension parameters or version) belongs "
            "there; what can be installed on which image, and everything after "
            "installation, belongs here"
        ),
        "evidence": "T-A9825E98, T-F51E65E5",
    },
    {
        "symptom": ("cannot start", "stuck stopping", "stopped by itself", "won't boot", "shutdown"),
        "target": "alibabacloud-ecs-high-frequency-issues",
        "boundary": "instance lifecycle, not web service configuration",
        "evidence": "T-E923DA06, T-43513829",
    },
    {
        "symptom": ("disk full", "no space", "inode exhausted", "file count limit", "cannot create new file"),
        "target": "the disk capacity skill",
        "boundary": "capacity and inode pressure are diagnosed there; this skill only checks whether a full filesystem is blocking a service",
        "evidence": "tier keyword budget",
    },
    {
        "symptom": ("disk slow", "io latency", "bps saturated", "performance below spec"),
        "target": "alibabacloud-ecs-high-frequency-issues",
        "boundary": "IO performance; this skill only names the resource that a service is competing with",
        "evidence": "T-99F91F5E, T-9DDDFAD4",
    },
    {
        "symptom": ("expand disk", "partition not applied", "resize not effective"),
        "target": "alibabacloud-ecs-high-frequency-issues",
        "boundary": "expansion and partition work",
        "evidence": "tier list",
    },
    {
        "symptom": ("hacked", "webshell", "virus", "malware", "unknown admin account", "abnormal process"),
        "target": "Security Center plus manual security handling",
        "boundary": (
            "identify and stop the bleeding (snapshot, change passwords, remove "
            "the unexpected account, restrict inbound ports), then hand off; "
            "removing files or processes is never done here"
        ),
        "evidence": "T-040B35C3, T-D592BBF3, T-CA03A3F6",
    },
    {
        "symptom": ("cannot reach overseas", "isp blocked", "cross border", "outbound ip blocked", "latency from another country"),
        "target": "the network product and path investigation queue",
        "boundary": "path, carrier and penalty matters; this skill reports only what the guest side shows",
        "evidence": "T-48D25F5F, T-A692D630, T-D592BBF3",
    },
    {
        "symptom": ("icp filing", "beian", "domain blocked in mainland"),
        "target": "the filing process",
        "boundary": "compliance interception, not a service fault",
        "evidence": "T-713A543E",
    },
    {
        "symptom": ("unpaid", "overdue", "arrears", "recharge", "bandwidth suspended"),
        "target": "billing and account operations",
        "boundary": "billing state",
        "evidence": "T-7C096742",
    },
    {
        "symptom": ("sub-account permission", "ram policy", "grant view access"),
        "target": "RAM (custom policy or resource group)",
        "boundary": "the ECS console has no application-log-level permission; only identify and point",
        "evidence": "T-6FC28660",
    },
    {
        "symptom": ("migrate server", "move wordpress from another provider", "cross platform migration"),
        "target": "Server Migration Center",
        "boundary": (
            "collect what must be exported instead (site files, database, PHP "
            "version and enabled parameters, Nginx or Apache, database version), "
            "then hand off"
        ),
        "evidence": "T-C0934ABB",
    },
    {
        "symptom": ("restore from backup", "file level restore", "snapshot or backup scope"),
        "target": "data protection and snapshot tooling",
        "boundary": "a file-level backup does not restore a runtime environment; reconfiguring it is this skill's scope only as guidance",
        "evidence": "T-2A482800",
    },
    {
        "symptom": ("ack node", "acs cluster", "pod cannot schedule", "cluster resource"),
        "target": "the container service for Kubernetes support path",
        "boundary": "cluster node scaling and scheduling",
        "evidence": "T-ABB48381",
    },
    {
        "symptom": ("bt panel", "aaPanel", "1panel", "third party panel", "baota"),
        "target": "the panel vendor's own support",
        "boundary": "not an Alibaba Cloud product; the agent's own wording was that they were not familiar with it",
        "evidence": "T-E24E7F32, T-B0960B66",
    },
    {
        "symptom": ("configure it for me", "do it on my behalf", "price", "discount", "promotion"),
        "target": "manual handling, or the commercial channel for pricing",
        "boundary": (
            "this skill does not enter a customer's server to configure anything "
            "and does not answer sales questions; it emits the steps instead"
        ),
        "evidence": "T-C03C9EDC, T-6A5E475B",
    },
)

# ---------------------------------------------------------------------------
# Never-automate list
# ---------------------------------------------------------------------------

NEVER_AUTOMATED = (
    "delete or empty files, including any form of log truncation",
    "rm -rf, formatting, partition or filesystem rebuild, fsck, tune2fs",
    "killing a process, or stopping, restarting or enabling a service",
    "systemctl start|stop|restart|enable|disable, service restart, iisreset",
    "removing an IIS module, role or feature, or editing applicationHost.config",
    "rebooting or stopping the instance, detaching a disk, mounting a repair disk",
    "changing a container restart policy, recreating a container, or moving a data directory",
    "deleting a snapshot, resizing a disk, refund or downgrade",
    "creating or changing an inbound rule: report the missing rule and the console path, the customer adds it",
)

# ---------------------------------------------------------------------------
# Help catalogue (verified URLs from this tier's evidence only)
# ---------------------------------------------------------------------------

HELP_DOCS = (
    {"topic": "deploy a Node.js environment manually", "url": "https://help.aliyun.com/zh/ecs/user-guide/manually-deploy-a-node-js-environment", "evidence": "T-F51E65E5"},
    {"topic": "install software with Workbench", "url": "https://help.aliyun.com/zh/ecs/user-guide/workbench-software-installation.md", "evidence": "skill capability"},
    {"topic": "known issues of public images (patch conflict)", "url": "https://help.aliyun.com/zh/ecs/known-issues-of-public-images#d3109578c6jws", "evidence": "T-BA3E2F89"},
    {"topic": "instance type selection guidance", "url": "https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-instance-type-selection.md", "evidence": "T-0868235B, T-9DDDFAD4"},
    {"topic": "build an IIS service on a Windows instance", "url": "https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-a-windows-instance-and-build-an-iis-service.md", "evidence": "Windows baseline"},
    {"topic": "build an FTP site manually on a Windows instance", "url": "https://help.aliyun.com/zh/ecs/user-guide/manually-build-an-ftp-site-on-a-windows-instance", "evidence": "T-759C3C05"},
    {"topic": "deploy Apache manually on a Linux instance", "url": "https://help.aliyun.com/zh/ecs/user-guide/use-the-ecs-instance-in-the-console.md", "evidence": "Apache baseline"},
    {"topic": "build WordPress manually (Windows)", "url": "https://help.aliyun.com/document_detail/2858756.html", "evidence": "T-C03C9EDC"},
    {"topic": "build WordPress manually (Linux)", "url": "https://help.aliyun.com/document_detail/151691.html", "evidence": "T-C03C9EDC"},
    {"topic": "add a security group rule", "url": "https://help.aliyun.com/zh/ecs/user-guide/add-a-security-group-rule", "evidence": "T-9C6BB0CC, T-759C3C05"},
    {"topic": "configure the Linux swap partition", "url": "https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance", "evidence": "T-0868235B"},
    {"topic": "Linux network traffic load analysis", "url": "https://help.aliyun.com/zh/ecs/support/query-and-case-analysis-of-linux-network-traffic-load", "evidence": "T-E24E7F32"},
    {"topic": "high bandwidth usage on a Windows instance", "url": "https://help.aliyun.com/zh/ecs/support/troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances", "evidence": "T-E24E7F32"},
    {"topic": "create a snapshot", "url": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot", "evidence": "snapshot-first rule"},
    {"topic": "snapshot billing rules", "url": "https://help.aliyun.com/document_detail/56159.html", "evidence": "T-9DDDFAD4"},
    {"topic": "delete a snapshot", "url": "https://help.aliyun.com/document_detail/128131.html", "evidence": "standard closing advice"},
    {"topic": "virus scan in Security Center", "url": "https://help.aliyun.com/document_detail/164610.html", "evidence": "T-040B35C3"},
)

# The instance "stopping" explanation page was pasted in a ticket dialogue with
# its URL cut off mid-string, so it is intentionally absent until someone
# completes it. Do not paste a guessed URL for it.
PENDING_HELP_DOC_TOPICS = (
    "instance stopped-or-restarting status explanation (URL truncated in the source dialogue)",
    "Alibaba Cloud Linux 4 versus moby and Docker CE compatibility page",
    "MongoDB on ECS compatibility",
    "official container image accelerator documentation",
    "enabling the CGI and FastCGI role in IIS",
)

# ---------------------------------------------------------------------------
# Region vocabulary
# ---------------------------------------------------------------------------

MAINLAND_REGION_PREFIX = "cn-"
# cn-hongkong is not covered by the mainland filing rule in the same way, so it
# is excluded from the filing prompt instead of being lumped in with the rest.
NON_FILING_MAINLAND_REGIONS = ("cn-hongkong",)

# ---------------------------------------------------------------------------
# Candidate branches (report appendix)
# ---------------------------------------------------------------------------

# Some tickets in this tier carry a written summary whose stated cause was never
# demonstrated in the dialogue. Those branches stay candidates here, worded the
# way the handling agent kept them, each with the claim it must not turn into.
CANDIDATE_BRANCHES = (
    {
        "topic": "an inbound push from a third party never reached the site",
        "candidates": (
            "a certificate or TLS handshake problem on the listener",
            "an intermediate layer such as a self-hosted protection proxy",
            "a security penalty or carrier-side block on the return path",
        ),
        "rule": (
            "split by self-testing the same address from inside the instance and "
            "from another access path, then report which half failed; the "
            "platform-side question needs a human queue"
        ),
        "must_not_claim": (
            "that Alibaba Cloud intercepted the request - the online stage of "
            "that ticket asked two questions and reached no cause"
        ),
        "evidence": "T-E63D76D9",
    },
    {
        "topic": "databases created inside a container keep disappearing",
        "candidates": (
            "a restart policy with no persistent host volume, so the container returns to its image state",
            "an external actor once the port became publicly reachable",
        ),
        "rule": (
            "weigh both against the timeline: restoring to the initial state "
            "after a restart points at persistence, not at an attack; keep both "
            "open until the restart policy and mounts have been read"
        ),
        "must_not_claim": "an intrusion as the conclusion",
        "evidence": "T-1EB845AD",
    },
    {
        "topic": "the site is slow only inside its admin interface",
        "candidates": (
            "a plugin calling an overseas third-party endpoint",
            "the customer's own browser or local access path",
        ),
        "rule": (
            "state that host resources and reachability are normal, so this is "
            "not the resource area, then ask for a different browser and a "
            "different access path before any server-side change"
        ),
        "must_not_claim": "a plugin as the cause without a timing breakdown",
        "evidence": "T-6FDB4F07",
    },
    {
        "topic": "IIS offers no FastCGI entry when adding a handler mapping",
        "candidates": ("the CGI role or its FastCGI sub-feature is not installed",),
        "rule": (
            "report it as unread: querying Windows role state needs a cmdlet that "
            "this batch has not signed off, so ask for a screenshot of the role "
            "list instead of asserting the cause"
        ),
        "must_not_claim": "the missing role as a verified finding",
        "evidence": "T-10715A07",
    },
    {
        "topic": "services and containers appear to have vanished after a password reset",
        "candidates": (
            "a replaced system disk or a changed image",
            "data that was never persisted outside the container",
        ),
        "rule": (
            "state that an in-console password reset runs through Cloud Assistant "
            "and leaves other services alone, then require a snapshot before any "
            "hands-on inspection"
        ),
        "must_not_claim": (
            "any candidate as the cause: that ticket never reached the instance"
        ),
        "evidence": "T-F4F68F93",
    },
)
