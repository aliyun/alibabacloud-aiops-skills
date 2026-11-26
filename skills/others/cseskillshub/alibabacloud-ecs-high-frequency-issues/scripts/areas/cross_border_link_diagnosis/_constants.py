"""Constants for the cross-border link diagnosis skill.

All reference data lives here as code constants: no data files are shipped in
this directory.
"""

SKILL_NAME = "alibabacloud-ecs-cross-border-link-diagnosis"

USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

CLI_BIN = "aliyun"
CALL_TIMEOUT_SECONDS = 30
STS_TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0

RETRYABLE_ERROR_CODES = {
    "Throttling",
    "ThrottlingUser",
    "Throttling.Api",
    "InternalError",
    "ServiceUnavailable",
    "RequestTimeout",
    "SDK.ServerUnreachable",
}

RETRYABLE_MESSAGE_FRAGMENTS = (
    "timed out",
    "connection closed by peer",
    "service temporarily unavailable",
    "try again later",
)

AUTH_ERROR_CODES = {
    "NoPermission",
    "ImplicitDeny",
    "InvalidAccessKeyId",
    "SignatureDoesNotMatch",
    "AccessDenied",
}

PAGE_NUMBER = 1
PAGE_SIZE = 50

API_VERSIONS = {
    "ecs": "2014-05-26",
    "vpc": "2016-04-28",
    "sts": "2015-04-01",
}

RAM_ACTIONS = {
    ("ecs", "DescribeInstances"): "ecs:DescribeInstances",
    ("ecs", "DescribeInstanceStatus"): "ecs:DescribeInstanceStatus",
    ("ecs", "DescribeAvailableResource"): "ecs:DescribeAvailableResource",
    ("vpc", "DescribeEipAddresses"): "vpc:DescribeEipAddresses",
}

# Region ids used only for labelling. Anything starting with `cn-` other than
# China Hong Kong is treated as mainland; anything not recognised is `unknown`
# and must be confirmed by the operator instead of being assumed.
# side: mainland | overseas | overseas_direction (China Hong Kong).
REGION_LABELS = {
    "cn-hongkong": {"label": "China (Hong Kong)", "side": "overseas_direction"},
    "ap-southeast-1": {"label": "Singapore", "side": "overseas"},
    "ap-southeast-3": {"label": "Malaysia (Kuala Lumpur)", "side": "overseas"},
    "ap-southeast-5": {"label": "Indonesia (Jakarta)", "side": "overseas"},
    "ap-southeast-6": {"label": "Philippines (Manila)", "side": "overseas"},
    "ap-southeast-7": {"label": "Thailand (Bangkok)", "side": "overseas"},
    "ap-northeast-1": {"label": "Japan (Tokyo)", "side": "overseas"},
    "ap-northeast-2": {"label": "South Korea (Seoul)", "side": "overseas"},
    "us-east-1": {"label": "US (Virginia)", "side": "overseas"},
    "us-west-1": {"label": "US (Silicon Valley)", "side": "overseas"},
    "eu-central-1": {"label": "Germany (Frankfurt)", "side": "overseas"},
    "eu-west-1": {"label": "UK (London)", "side": "overseas"},
    "me-east-1": {"label": "UAE (Dubai)", "side": "overseas"},
    "me-central-1": {"label": "Saudi Arabia (Riyadh)", "side": "overseas"},
    "na-south-1": {"label": "Mexico", "side": "overseas"},
    "cn-hangzhou": {"label": "China (Hangzhou)", "side": "mainland"},
    "cn-shanghai": {"label": "China (Shanghai)", "side": "mainland"},
    "cn-beijing": {"label": "China (Beijing)", "side": "mainland"},
    "cn-shenzhen": {"label": "China (Shenzhen)", "side": "mainland"},
    "cn-guangzhou": {"label": "China (Guangzhou)", "side": "mainland"},
    "cn-chengdu": {"label": "China (Chengdu)", "side": "mainland"},
    "cn-qingdao": {"label": "China (Qingdao)", "side": "mainland"},
    "cn-zhangjiakou": {"label": "China (Zhangjiakou)", "side": "mainland"},
    "cn-huhehaote": {"label": "China (Hohhot)", "side": "mainland"},
    "cn-wulanchabu": {"label": "China (Ulanqab)", "side": "mainland"},
    "cn-heyuan": {"label": "China (Heyuan)", "side": "mainland"},
    "cn-nanjing": {"label": "China (Nanjing)", "side": "mainland"},
    "cn-fuzhou": {"label": "China (Fuzhou)", "side": "mainland"},
    "cn-wuhan-lr": {"label": "China (Wuhan)", "side": "mainland"},
}

# Aliases customers type instead of a region id, used only to echo intent back.
REGION_ALIASES = {
    "hongkong": "cn-hongkong",
    "hk": "cn-hongkong",
    "singapore": "ap-southeast-1",
    "tokyo": "ap-northeast-1",
    "frankfurt": "eu-central-1",
    "virginia": "us-east-1",
    "us-east": "us-east-1",
    "siliconvalley": "us-west-1",
    "us-west": "us-west-1",
    "london": "eu-west-1",
    "jakarta": "ap-southeast-5",
}

MAINLAND_KEYWORDS = (
    "mainland", "china", "beijing", "shanghai", "guangzhou", "shenzhen",
    "hangzhou", "chengdu", "wuhan", "cn-",
)
OVERSEAS_KEYWORDS = (
    "overseas", "abroad", "foreign", "international", "hong kong", "singapore",
    "tokyo", "frankfurt", "virginia", "silicon valley", "london", "jakarta",
    "seoul", "dubai", "riyadh", "manila", "bangkok", "kuala lumpur",
)

DIRECTIONS = ("inbound", "outbound", "unknown")
SIDES = ("mainland", "overseas", "unknown")
SYMPTOMS = (
    "slow", "timeout", "packet-loss", "port-blocked", "partial-isp", "unknown",
)

# ---------------------------------------------------------------------------
# Evidence keys accepted on the command line, with the reading each one drives.
# ---------------------------------------------------------------------------
EVIDENCE_KEYS = {
    "mainland-nodes-fail-overseas-ok":
        "Multi-node dial test: mainland nodes fail, overseas nodes succeed.",
    "server-side-clean":
        "Guest-side self-check returned no anomaly (firewall, sshd, service).",
    "bandwidth-saturated":
        "Outbound bandwidth metering is pinned at the provisioned limit.",
    "request-arrives-response-lost":
        "Request reaches the instance and a response is sent, but the client "
        "receives nothing.",
    "eip-change-no-help":
        "The same fault reproduces after switching to another public IP or EIP.",
    "multi-tcp-timeout":
        "Several TCP ports time out at the same time on the same address.",
    "last-hop-drop":
        "Traceroute stops at a visible hop and the destination never appears.",
    "overseas-users-normal":
        "Users located near the instance reach it normally.",
    "partial-isp-only":
        "Only specific cities or carriers are affected, others are fine.",
    "cdn-bypass-still-slow":
        "Direct origin access, bypassing the acceleration layer, is still slow.",
    "fixed-stall-seconds":
        "Requests stall for a fixed number of seconds, independent of distance.",
    "ssh-auth-failure":
        "Failure happens at SSH authentication or configuration stage.",
    "panel-login-only":
        "The website port works; only the server management panel login fails.",
    "third-party-risk-control":
        "A third-party platform flags the IP as high risk.",
    "platform-restriction":
        "The resource is restricted by a platform policy decision.",
    "change-requested":
        "The customer is asking for a change to be made, not for a diagnosis.",
    "filing-context":
        "The conversation is about filing/registration requirements, not link quality.",
    "intranet-egress-config":
        "Failure direction is inside the VPC, NAT gateway, or route table.",
    "attack-traffic":
        "Volumetric attack traffic or a blackhole event is involved.",
    "transfer-tool-only":
        "Only a specific transfer tool or protocol misbehaves after the link is "
        "excluded.",
    "io-slow":
        "The complaint is disk read/write latency, not network latency.",
    "disk-not-expanded":
        "A disk resize has not taken effect inside the guest.",
}

# ---------------------------------------------------------------------------
# Attribution branches. Each branch carries the wording block emitted in reports.
# ---------------------------------------------------------------------------
BRANCH_CROSS_ACCOUNT = "cross-account-resource"
BRANCH_NOT_CROSS_BORDER = "not-cross-border"
BRANCH_INSTANCE_STATE = "instance-state"
BRANCH_BANDWIDTH_LIMIT = "bandwidth-saturated"
BRANCH_FORWARDING_FAULT = "platform-egress-or-return-path-fault"
BRANCH_BORDER_CONGESTION = "cross-border-congestion"
BRANCH_CARRIER_POLICY = "carrier-policy-or-local-block"
BRANCH_REGULATORY_BOUNDARY = "regulatory-boundary"
BRANCH_HANDOFF = "handoff-other-tier"
BRANCH_INSUFFICIENT = "insufficient-evidence"

THIRD_PARTY_RISK_STATEMENT = (
    "Nothing on the Alibaba Cloud side explains this result: the judgement comes from a "
    "third-party platform's own reputation model. Ask that platform to re-assess the "
    "address; a new address can be requested, but its reputation is decided by the "
    "third party, not by the cloud side."
)

CONGESTION_WAIVER = (
    "Cross-border capacity traverses public carrier networks and international "
    "peering paths. Alibaba Cloud neither owns nor controls those paths, cannot "
    "guarantee their quality, and cannot forecast a recovery time. Any option "
    "below reduces exposure to that path; none of them is a promise of a fix."
)

CONGESTION_EXPLANATION = (
    "Access between Chinese mainland networks and an overseas or China Hong Kong "
    "endpoint is not a direct link: it crosses international egress points and "
    "carrier routing nodes. Those segments can be congested, drop packets, or "
    "fail on individual ports while the server itself stays healthy. Instance-side "
    "settings have no effect on this, and there is no switch on the server that "
    "turns the quality on."
)

NEW_IP_STATEMENT = (
    "Replacing the public IP or EIP does not resolve this class of issue: the path "
    "and the carrier routing stay the same. When the fault is observed to persist "
    "after an address change, that observation is itself evidence against an "
    "address-side cause."
)

IP_DIFFERENCE_STATEMENT = (
    "Two instances in the same region can behave differently: each public address "
    "is announced over a different carrier path, so the return route - and with it "
    "the latency and loss - differs. There is no per-instance acceleration setting "
    "involved."
)

RECOVERY_STATEMENT = (
    "Recovery time for carrier-side congestion cannot be estimated and is not "
    "something Alibaba Cloud can schedule."
)

NO_GUARANTEE_STATEMENT = (
    "NOT GUARANTEED BY THIS DIAGNOSIS: carrier path quality, recovery time, and "
    "any outcome that depends on a third-party network or platform."
)

# ---------------------------------------------------------------------------
# Customer-side evidence collection. nature labels are mandatory in output.
# ---------------------------------------------------------------------------
EVIDENCE_CHECKLIST = (
    {
        "id": "source-location",
        "item": "City, carrier, and last-hop address of every affected client.",
        "how": "Ask each reporter; `tracert` on Windows, `traceroute` on macOS/Linux.",
        "nature": "read-only, no cloud change",
        "who": "customer",
    },
    {
        "id": "bidirectional-mtr",
        "item": "Raw MTR from client to server and from server to client carrier network.",
        "how": "See the MTR guide in references; submit screenshots or plain text, "
               "never a rewritten summary.",
        "nature": "read-only, no cloud change",
        "who": "customer or human engineer",
    },
    {
        "id": "multi-node-dial-test",
        "item": "Public dial test from several mainland nodes and several overseas nodes "
                "against the same address and port.",
        "how": "Run it on the console dial-test page listed in references.",
        "nature": "read-only, external probe",
        "who": "customer or human engineer",
    },
    {
        "id": "port-matrix",
        "item": "Per-port reachability: which TCP ports time out and which succeed.",
        "how": "`telnet <address> <port>` or `curl -v --max-time 15 http://<address>:<port>/`.",
        "nature": "read-only, no cloud change",
        "who": "customer",
    },
    {
        "id": "icmp-switch",
        "item": "Whether the guest ignores ICMP, which invalidates ping-only evidence.",
        "how": "`cat /proc/sys/net/ipv4/icmp_echo_ignore_all`",
        "nature": "read-only inside the guest",
        "who": "customer or, after authorisation, human engineer",
    },
    {
        "id": "guest-firewall-and-service",
        "item": "Guest firewall rules and the listening service state.",
        "how": "`iptables -S`, `firewall-cmd --list-all`, `ss -lntp`.",
        "nature": "read-only inside the guest",
        "who": "customer or, after authorisation, human engineer",
    },
    {
        "id": "security-group-reference",
        "item": "Security group ids attached to the instance and whether the tested port "
                "is allowed.",
        "how": "The report lists the group ids read from the API; rule content is checked "
               "by a human in the console.",
        "nature": "read-only, console review",
        "who": "customer or human engineer",
    },
    {
        "id": "bandwidth-usage",
        "item": "Actual outbound bandwidth over the fault window versus the provisioned "
                "limit.",
        "how": "Read the instance and EIP monitoring curves in the console; stop the "
               "competing task only if the customer chooses to.",
        "nature": "read-only, console review; stopping a workload is a customer decision",
        "who": "customer",
    },
    {
        "id": "authorised-machine-check",
        "item": "If guest inspection must be done by an engineer: snapshot the system disk "
                "first, inspect, then delete the snapshot.",
        "how": "A human takes the snapshot before the inspection and removes it afterwards; "
               "snapshots are billed separately, see the snapshot documents in references.",
        "nature": "mutating and billable - human action, never automated by this skill",
        "who": "customer decision plus human engineer",
    },
)

# ---------------------------------------------------------------------------
# Handoff table: recognition feature -> target tier -> wording.
# Mirrors references/cross-border-link-diagnosis__handoff-map.md one to one.
# ---------------------------------------------------------------------------
HANDOFFS = (
    {
        "key": "disk-expand",
        "feature": "Disk resized in the console but the guest still shows the old size.",
        "target": "area:disk-expand-diagnosis",
        "wording": "A resize that has not taken effect is a partition and file-system "
                   "adjustment matter; use area:disk-expand-diagnosis.",
    },
    {
        "key": "instance-state",
        "feature": "Instance will not start, or is stuck between states.",
        "target": "area:instance-state-diagnosis",
        "wording": "Boot and state-transition faults are outside this tier; use "
                   "area:instance-state-diagnosis.",
    },
    {
        "key": "disk-io",
        "feature": "Slow disk read/write or throughput below the purchased specification.",
        "target": "area:resource-bottleneck",
        "wording": "Storage latency is a different measurement path; use "
                   "area:resource-bottleneck.",
    },
    {
        "key": "bandwidth",
        "feature": "Bandwidth is fully used with no cross-border segment involved.",
        "target": "the advanced-network-diagnostics extension package",
        "wording": "A local capacity ceiling with no cross-border factor belongs to "
                   "the network quality and bandwidth check in the "
                   "advanced-network-diagnostics extension package.",
    },
    {
        "key": "ssh",
        "feature": "Authentication, key, or sshd configuration failure unrelated to the path.",
        "target": "area:ssh-connection",
        "wording": "Credential and service configuration faults belong to "
                   "area:ssh-connection.",
    },
    {
        "key": "web-access",
        "feature": "Layered unreachability across DNS, acceleration layer, or origin application.",
        "target": "area:web-inaccessible-slow",
        "wording": "Site-layer diagnosis belongs to area:web-inaccessible-slow.",
    },
    {
        "key": "intranet-egress",
        "feature": "Internal reachability or outbound direction governed by VPC, NAT, or routes.",
        "target": "the advanced-network-diagnostics extension package",
        "wording": "Private-network and egress configuration belongs to the intranet "
                   "egress check in the advanced-network-diagnostics extension package.",
    },
    {
        "key": "filing",
        "feature": "The blocker is registration or filing requirements for serving mainland users.",
        "target": "area:icp-filing-guide",
        "wording": "Filing rules and service codes belong to area:icp-filing-guide.",
    },
    {
        "key": "panel",
        "feature": "Only the server management panel login or QR scan fails; ports are open.",
        "target": "the app-deploy-and-site-build extension package",
        "wording": "Panel sign-in behaviour belongs to the panel diagnosis in the "
                   "app-deploy-and-site-build extension package.",
    },
    {
        "key": "attack",
        "feature": "Attack traffic and a resulting blackhole are already visible.",
        "target": "the security-audit-and-intrusion-response extension package",
        "wording": "Attack and blackhole handling belongs to the attack and blackhole "
                   "diagnosis in the security-audit-and-intrusion-response extension "
                   "package.",
    },
    {
        "key": "file-transfer",
        "feature": "After the cross-border path is excluded, one transfer tool or protocol "
                   "misbehaves.",
        "target": "the boot-and-login-repair extension package",
        "wording": "Protocol and tool configuration belongs to the file transfer "
                   "diagnosis in the boot-and-login-repair extension package.",
    },
    {
        "key": "punishment",
        "feature": "The resource is restricted by a platform policy decision.",
        "target": "the account-and-service-process extension package",
        "wording": "Policy restriction appeals belong to the punishment appeal guide "
                   "in the account-and-service-process extension package.",
    },
    {
        "key": "manual-change",
        "feature": "The request needs a change: cleanup, reboot, firewall edit, address swap.",
        "target": "human execution",
        "wording": "This skill is read-only and will not perform or generate the change; "
                   "the human runbook and the risk statement are provided instead.",
    },
)

# ---------------------------------------------------------------------------
# Permitted external references. These are the only links this skill may quote.
# Anything else needs a human-verified source first and must not be invented.
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "mtr-guide": "https://help.aliyun.com/zh/ecs/user-guide/use-mtr-tool-for-network-analysis",
    "dial-test": "https://boce.aliyun.com/home",
    "global-accelerator-scenarios": "https://help.aliyun.com/zh/ga/product-overview/scenarios",
    "snapshot-take": "https://help.aliyun.com/document_detail/25455.html",
    "snapshot-billing": "https://help.aliyun.com/document_detail/56159.html",
    "snapshot-remove": "https://help.aliyun.com/document_detail/128131.html",
}

LINK_DISCLAIMER = (
    "The links above are reproduced from material already shared in support "
    "conversations. Re-check that a link is still live and applicable before "
    "quoting it to a customer; do not add links that are not listed here."
)

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
