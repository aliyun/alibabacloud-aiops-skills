"""Constants for the public IP / EIP guide scripts.

Everything the entry point needs is a module constant in this file: the CLI
contract, the query surface, and the guidance tables. No data file lives under
``scripts/`` by design, so the tables below are the single source of the text
the report prints.

Wording discipline: any figure taken from a historical support case carries the
CASE-FIGURE qualifier and must be re-checked on the console before it reaches a
customer. Platform rules (the 7-day reclaim window for a released address, the
one-way fixed-public-IP-to-EIP conversion) are stated as platform rules, without
that qualifier. Prices are never computed here.
"""

SKILL_NAME = "alibabacloud-ecs-public-ip-guide"

# --------------------------------------------------------------------------- #
# CLI contract
# --------------------------------------------------------------------------- #
ALIYUN_BIN = "aliyun"
UA_PREFIX = "AlibabaCloud-Agent-Skills"

# Product codes are lowercase with hyphens, and every product here runs in
# plugin mode: the CLI command token is the lowercase-hyphenated form of the
# PascalCase API action name (sts GetCallerIdentity -> get-caller-identity).
# Verified against aliyun CLI 3.4.5, which serves these commands directly.
PRODUCT_ECS = "ecs"
PRODUCT_VPC = "vpc"
PRODUCT_STS = "sts"
ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"
ACTION_DESCRIBE_EIP_ADDRESSES = "DescribeEipAddresses"
ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"

# action -> RAM permission point, as verified for this skill
RAM_POINTS = {
    "ecs DescribeInstances": "ecs:DescribeInstances",
    "ecs DescribeInstanceStatus": "ecs:DescribeInstanceStatus",
    "vpc DescribeEipAddresses": "vpc:DescribeEipAddresses",
    "sts GetCallerIdentity": "sts:GetCallerIdentity",
}

CALL_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
PAGE_SIZE = 50
MAX_SCAN_REGIONS = 12

RETRYABLE_ERROR_CODES = frozenset(
    {
        "Throttling",
        "ThrottlingUser",
        "Throttling.Api",
        "SystemBusy",
        "ServiceUnavailable",
        "InternalError",
        "CliTimeout",
        "RequestTimeout",
    }
)

# Codes that mean "the credential is missing, wrong, or not allowed": the report
# names the missing action instead of a generic access-denied label.
CREDENTIAL_ERROR_CODES = frozenset(
    {
        "InvalidAccessKeyId",
        "InvalidAccessKeyId.NotFound",
        "InvalidSecurityToken",
        "InvalidSecurityToken.Expired",
        "MissingSecurityToken",
        "AuthFailure",
        "Unauthorised",
        "Unauthorized",
    }
)

PERMISSION_ERROR_CODES = frozenset({"NoPermission", "ImplicitDeny"})

CASE_FIGURE_QUALIFIER = (
    "case figure from a historical instance, not a quote: confirm the current value "
    "on the console conversion or buy page before passing it on"
)

# --------------------------------------------------------------------------- #
# Regions
# --------------------------------------------------------------------------- #
# Addresses in the source cases were spread over mainland and overseas regions, so
# "wrong region" is a frequent false not-found. The scan list is ordered by common
# usage and capped by MAX_SCAN_REGIONS.
COMMON_REGIONS = (
    "cn-hangzhou",
    "cn-shanghai",
    "cn-beijing",
    "cn-zhangjiakou",
    "cn-wulanchabu",
    "cn-shenzhen",
    "cn-heyuan",
    "cn-chengdu",
    "cn-hongkong",
    "us-west-1",
    "us-east-1",
    "ap-southeast-1",
)

# --------------------------------------------------------------------------- #
# Console and documentation entries
# --------------------------------------------------------------------------- #
EIP_CONSOLE_URL = "https://vpc.console.aliyun.com/eip/{region_id}/eips"
RENEW_CONSOLE_URL = "https://billing-cost.console.aliyun.com/renew/manual"
NO_URL = "(no stable link: use the console page named above)"

DOC_CHANGE_BANDWIDTH_BILLING = (
    "https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-for-network-usage-1"
)
DOC_CONVERT_PUBLIC_IP_TO_EIP = "https://help.aliyun.com/document_detail/61290.html"
DOC_UNBIND_EIP = "https://help.aliyun.com/document_detail/65204.html"
DOC_ALLOCATE_EIP = "https://help.aliyun.com/document_detail/65203.html"
DOC_BIND_EIP = "https://help.aliyun.com/document_detail/72125.html"
DOC_ASSOCIATE_EIP = "https://help.aliyun.com/zh/ecs/user-guide/associate-or-disassociate-an-eip.md"
DOC_MODIFY_EIP_BANDWIDTH = "https://help.aliyun.com/zh/ecs/user-guide/modify-the-bandwidth-of-an-eip.md"
DOC_NETWORK_BANDWIDTH = "https://help.aliyun.com/zh/ecs/user-guide/network-bandwidth.md"
DOC_PUBLIC_BANDWIDTH = (
    "https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-configuring-public-bandwidth.md"
)
DOC_MANAGE_ENI = "https://help.aliyun.com/zh/ecs/user-guide/manage-eni.md"
DOC_RELEASE_INSTANCE = "https://help.aliyun.com/zh/ecs/user-guide/release-an-instance.md"
DOC_SPEC_CHANGE_OVERVIEW = (
    "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md"
)
DOC_CONNECT_TO_INSTANCE = "https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md"
DOC_SECURITY_GROUP_GUIDE = (
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md"
)
DOC_CROSS_ACCOUNT_TRANSFER = (
    "https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance"
)

# --------------------------------------------------------------------------- #
# The change path (core of the change-ip intent)
# --------------------------------------------------------------------------- #
FIVE_STEP_FLOW = (
    (
        "step 1/5 - switch the public bandwidth billing method",
        "Change the public bandwidth billing method from fixed bandwidth to pay-by-traffic. "
        "This is the mandatory precondition: while the instance is on fixed bandwidth the "
        "public address cannot be detached.",
        DOC_CHANGE_BANDWIDTH_BILLING,
    ),
    (
        "step 2/5 - convert the fixed public IP into an EIP",
        "Convert the fixed public IP of the VPC-type instance into an Elastic IP Address. "
        "Skip this step when the address is already an EIP.",
        DOC_CONVERT_PUBLIC_IP_TO_EIP,
    ),
    (
        "step 3/5 - unbind the EIP",
        "Disassociate the EIP from the instance. Keep the allocation id: that address is "
        "still billed until it is released.",
        DOC_UNBIND_EIP,
    ),
    (
        "step 4/5 - allocate a new EIP",
        "Allocate a new EIP in the same region, on the EIP product buy page, choosing the "
        "billing method and bandwidth there. Pick a pay-by-traffic EIP if the fixed-bandwidth "
        "cost of the previous step matters.",
        DOC_ALLOCATE_EIP,
    ),
    (
        "step 5/5 - bind the new EIP to the instance",
        "Associate the new EIP with the instance, then re-check the state with this skill.",
        DOC_BIND_EIP,
    ),
)

THREE_NOTICES = (
    "Notice 1 - the conversion does not go back: an EIP cannot be turned back into a fixed "
    "public IP of the instance, so the original address type is lost for good.",
    "Notice 2 - an EIP bills on its own: it adds a separate configuration fee on top of the "
    "bandwidth fee. One overseas case recorded a daily configuration fee of 0.72 CNY; "
    + CASE_FIGURE_QUALIFIER + ".",
    "Notice 3 - the bandwidth switch moves money: moving from fixed bandwidth to pay-by-traffic "
    "refunds the remaining bandwidth at the discounted rate, so with a promotional purchase the "
    "refund can be 0, and moving back to fixed bandwidth later can cost more than the refund.",
)

UNIQUE_ADDRESS_NOTE = (
    "Whether the new address differs from the old one is guaranteed by the sequence, not by "
    "luck: as long as the old EIP is still allocated to the account, a newly allocated EIP "
    "cannot be that same address. Release the old EIP only after the new one is bound and "
    "verified."
)

WRONG_SHORTCUTS = (
    "Lowering the bandwidth to 0 and buying it back does not rotate the address: a recorded "
    "case re-bought 3 Mbps fixed bandwidth and was handed the same public IP again.",
    "Rebooting or reinstalling does not change a fixed public IP either; the address belongs "
    "to the instance until it is converted and detached.",
    "Treating a direct 'change the public IP' entry as a general replacement for the EIP path "
    "is the shortcut that does not hold: the entry does exist - instance details > All "
    "Actions > Network and Security Group > Change Public IP - but it is narrow. The instance "
    "must be stopped in standard stop mode (an economical-stop instance gives its public IP "
    "up, so there is nothing left to change), it is offered only inside a short window after "
    "the instance was created (6 hours in the current documentation) and at most 3 times per "
    "instance, the new address is assigned by the system at random and cannot be chosen, and "
    "where the address must be kept the documentation points at an EIP instead. Re-check "
    "those limits on the documentation page; beyond them the EIP path is the route.",
)

BILLING_TAIL_WARNING = (
    "Billing tail: an EIP that was unbound but never released keeps being billed. After the "
    "customer acts, list the region's EIPs and confirm the old allocation id is gone from the "
    "account. This exact gap produced an unexpected charge in a recorded case."
)

# --------------------------------------------------------------------------- #
# Billing and renewal caliber
# --------------------------------------------------------------------------- #
BILLING_MODEL = (
    "A fixed public IP is not a separate asset: it is billed with the instance and with the "
    "instance bandwidth, and it cannot be kept when the instance is released.",
    "An EIP is an independent resource: it has its own billing method and its own renewal, so "
    "it does not renew together with the instance; renew it on the EIP page.",
    "There is no reverse conversion: the switch is one way, fixed public IP to EIP "
    "(ConvertNatPublicIpToEip). Once converted, the fixed public IP address type cannot be "
    "restored - there is no API and no console entry that turns an EIP back. Getting a fixed "
    "public IP again means releasing the public address and allocating a new one, and the "
    "address will differ, so DNS records must be updated afterwards.",
    "The exact refund, price difference, and promotional renewal price of any of these steps "
    "are account specific and are shown on the console conversion and buy pages. This skill "
    "does not compute them; a support engineer could not compute them either in the recorded "
    "cases.",
)

EIP_BANDWIDTH_OPTIONS = (
    "A newly allocated EIP can be set to a fixed bandwidth value, or to pay-by-traffic with a "
    "bandwidth ceiling; see the EIP bandwidth and billing method page for what the region "
    "supports.",
    "Short-lived upgrades and renewal-time changes for an EIP follow the EIP page, not the "
    "instance page.",
)

# --------------------------------------------------------------------------- #
# Multiple addresses
# --------------------------------------------------------------------------- #
MULTI_IP_RULES = (
    "By default one instance carries one public address: one fixed public IP, or one EIP "
    "associated with it. Extra public addresses mean extra EIPs.",
    "To put more than one EIP on one instance, attach secondary elastic network interfaces "
    "and associate one EIP with each interface; the primary interface keeps its own mapping.",
    "An EIP is a one-to-one NAT mapping of a private address. Inside the operating system the "
    "instance only ever sees its private address, so the EIP will not appear in the interface "
    "configuration and that is expected, not a failure.",
    "Remote services are reached through the private address mapped by the EIP, so the "
    "security group must allow the port being used, on the interface that carries it.",
    "Public IPv6 addressing follows a separate allocation path from EIPs; confirm the region "
    "and the instance IPv6 support in the ENI documentation before promising an address.",
)

GUEST_SIDE_NOTE = (
    "Cloud queries cannot see the address configuration actually applied inside the operating "
    "system. When several secondary private addresses are configured on one interface but the "
    "instance is unreachable, the common root cause is a missing static configuration or an "
    "extra route inside the guest. Ask the customer for the interface and route table output, "
    "and point at the secondary private IP documentation; this skill does not change guest "
    "settings."
)

# --------------------------------------------------------------------------- #
# Transfer, migration, and released addresses
# --------------------------------------------------------------------------- #
TRANSFER_RULES = (
    "An ECS instance can be transferred to another account, but between enterprise accounts "
    "only when both accounts share the same enterprise verification subject. Whether that "
    "holds is account registration data, which no ECS query exposes: the customer confirms it "
    "on the verification pages.",
    "A VPC-type instance does not carry its EIP across a transfer: disassociate the EIP before "
    "the instance is transferred, then bind it again on the receiving side.",
    "A pay-as-you-go EIP can be transferred on its own, separately from any instance, so an "
    "address that must outlive the machine is not lost by the transfer itself.",
    "The fixed public IP that the system assigned travels with the instance: it is transferred "
    "together with the instance and keeps the same address.",
    "Transfer constraints recorded in the cases, to re-check on the current documentation: the "
    "vSwitch and security group must be in the same VPC, the destination vSwitch must be in the "
    "instance's zone, cross-region transfer is not supported, and a destination account holding "
    "pay-as-you-go resources needs an available balance above 100 CNY ("
    + CASE_FIGURE_QUALIFIER + ").",
    "Across different verification subjects there is no transfer, only rebuild: share a custom "
    "image or migrate with the Server Migration path. Either way the public address changes, so "
    "DNS and any IP allowlists must be republished.",
    "If the goal is to keep the address rather than the instance, an EIP is the portable "
    "answer: it can be unbound from one instance and bound to another inside the same account "
    "and region, and a pay-as-you-go EIP can be transferred on its own. A fixed public IP is "
    "not lost on transfer - it moves with its instance and keeps the same address - but it "
    "cannot be detached and moved to a different instance.",
)

RELEASED_ADDRESS_RULES = (
    "Once an instance is released its private addresses are not retained anywhere queryable, "
    "including the audit trail; only the public address has a bounded recovery path.",
    "A released public address can be reclaimed by the customer inside 7 days, self-service: "
    "on the EIP page apply for that specific address, or allocate an EIP with "
    "AllocateEipAddressPro and pass the address in the IpAddress parameter. After 7 days, or "
    "as soon as another account holds the address, it cannot be reclaimed: those attempts fail "
    "with OperationFailed.AllocateUnfamiliarIp or OperationDenied.IpBelongToOtherUser.",
    "A fixed public IP of a classic-network instance cannot be reclaimed at all, however recent "
    "the release is; only an EIP-format address has the 7-day reclaim path above.",
    "An EIP that is still allocated is billed even when unbound; releasing it stops the charge "
    "and returns the address to the pool, where it is no longer reserved for this account, so "
    "the reclaim path above is the only way back and only while nobody else holds it.",
    "Some account types carry a shorter automatic release cycle than the standard overdue "
    "window, and release protection does not override that cycle. For an overdue or expiry "
    "question, hand the lifecycle itself to the expiry and arrears skill.",
    "Released addresses return to the shared pool and can be handed to another customer, and "
    "someone else's stale DNS record can then point at this account's address. That inheritance "
    "is not fixed by changing the address again.",
)

COUNTER_EXAMPLES = (
    "Unreachable service on a public address: filing interception, security group rules, and a "
    "service bound to the private address are all fixed without touching the address. Changing "
    "it costs an irreversible conversion.",
    "Traffic from other people's domains arriving at this address: the records are theirs, and "
    "they cannot be withdrawn from here. Serve only the intended host name in the web server "
    "configuration, and do not use the address itself as the server name.",
    "A single client tool that cannot connect while another path works: that is the client or "
    "protocol area, not the address.",
    "Attack traffic: a new address leaks again and does not stop the attack; mitigation is a "
    "separate capability.",
)

# --------------------------------------------------------------------------- #
# Handoff table
# --------------------------------------------------------------------------- #
# (area label, recognition keywords, target skill, customer-facing wording)
HANDOFF_RULES = (
    (
        "filing interception on port 443",
        ("rst", "reset", "443", "beian", "filing", "icp", "unregistered", "blocked by carrier"),
        "area:icp-filing-guide",
        "This looks like filing interception on a mainland region, not an address problem. "
        "Point the domain at the instance only after filing is complete. Do not try to fix it "
        "by changing the address: it will not take effect, and the EIP conversion cannot be "
        "undone.",
    ),
    (
        "public path quality",
        (
            "packet loss",
            "loss",
            "timeout",
            "timed out",
            "handshake",
            "no response",
            "route",
            "return path",
            "mtu",
            "jitter",
            "slow",
            "unreachable",
            "cannot access",
            "ping",
        ),
        "alibabacloud-ecs-vpc-publicnetwork-troubleshoot",
        "The address itself is correctly assigned and bound, so this is a path problem. It goes "
        "to the public network troubleshooting skill. Changing the address will not repair a "
        "path.",
    ),
    (
        "bandwidth and link quality",
        ("bandwidth", "throughput", "speed", "mbps", "upgrade bandwidth", "downgrade bandwidth"),
        "area:bandwidth-modify-guide",
        "The bandwidth change itself belongs to the bandwidth guide; this skill keeps only the "
        "billing-method switch that is a precondition of an address change.",
    ),
    (
        "port access and service reachability",
        ("port", "security group", "firewall", "connection refused", "nginx", "80", "8080"),
        "area:access-block-layered",
        "The address is correctly published; the port or the service configuration is the "
        "question, which belongs to the layered access-block skill.",
    ),
    (
        "remote login",
        ("ssh", "22", "workbench", "rdp", "3389", "remote desktop", "mstsc", "login"),
        "area:ssh-connection",
        "Login failures after an address change go to the SSH or RDP skill; the address change "
        "itself is already covered here.",
    ),
    (
        "attack and blackhole",
        ("ddos", "attack", "blackhole", "black hole", "mitigation", "scrubbing"),
        "area:attack-blackhole-diagnosis",
        "A new address does not end an attack and will leak again. Mitigation and blackhole "
        "handling belong to the attack skill; this one only answers whether a change is "
        "possible and at what cost.",
    ),
    (
        "arrears and expiry lifecycle",
        ("overdue", "arrears", "expired", "release protection", "retention", "renew failed"),
        "area:expiry-release-retention",
        "The release and retention timeline belongs to the expiry skill; this one keeps only "
        "the address consequence: a released address cannot be renewed back.",
    ),
    (
        "account transfer mechanics",
        ("transfer ownership", "move to another account", "change account", "another account", "cross account"),
        "the Alibaba Cloud account ownership transfer process (console ticket; no skill here performs it)",
        "The transfer procedure belongs to the account transfer skill; this one answers only "
        "whether the address can come along.",
    ),
    (
        "instance spec or image change",
        ("change os", "replace image", "arm", "x86", "instance type", "spec change", "renewal change"),
        "area:instance-modify-diagnosis",
        "The spec or image change belongs to the instance change skill; the address rule stays "
        "here: an EIP can be moved, a fixed public IP cannot.",
    ),
    (
        "refund and commerce",
        ("refund", "invoice", "coupon", "discount price", "unsubscribe"),
        "area:unsubscribe-refund",
        "Money movement is a commerce action: it goes to the refund skill or a support "
        "engineer, never to an automated call.",
    ),
    (
        "network quality between regions",
        ("latency", "cross region", "international link", "packet"),
        "area:network-quality-bandwidth",
        "Inter-region and international link quality belongs to the network quality skill.",
    ),
)

INTENTS = ("consult", "change-ip", "add-ip", "retain-ip", "billing", "ip-missing", "verify",
           "triage")

# A how-to question ("how do I view the public IP?") is answerable from platform rules and
# needs no read. Before this intent existed the agent chained triage -> verify -> ip-missing
# for that question: 3 runs cost 159 / 444 / 118 s with the same conclusion, and the answer
# never contained a read anyway (no resource handle was given).
CONSULT_METHODS = (
    ("console instance list",
     "ECS console > Instances: the IP address column shows the address marked (public); "
     "if the column shows only the private address, no public address is assigned."),
    ("console instance details",
     "Open the instance > Configuration information: Public IP is the fixed address, "
     "Elastic IP is the bound EIP. Either field may legitimately be empty."),
    ("API read",
     "DescribeInstances returns PublicIpAddress.IpAddress[] (fixed) and "
     "EipAddress.IpAddress + AllocationId (EIP); DescribeEipAddresses lists the EIPs of a "
     "region."),
    ("EIP console",
     "VPC console > Elastic IP addresses lists the account's EIPs with their bound instance "
     "and billing status."),
)
CONSULT_FACTS = (
    "A fixed public IP and an EIP are mutually exclusive on one instance: one instance holds "
    "at most one public address of either kind. When the fixed IP has to give way to an EIP it "
    "is converted on the cloud side (ConvertNatPublicIpToEip, one way), not released: in "
    "Alibaba Cloud semantics a release is irreversible and gives the address up instead of "
    "converting it.",
    "The guest NIC (ip addr / ipconfig) shows the private address only. A public address that "
    "does not appear inside the instance is normal, not a missing address.",
    "A public address is a cloud-side field, so an empty PublicIpAddress on a running instance "
    "means no public address is assigned, not that the query failed.",
)

INTENT_NEXT_ACTION = {
    "consult": (
        "Answer with the four viewing paths and the three facts; no cloud read is required and "
        "none was made. If the customer then names a specific instance, rerun with "
        "--intent verify --instance-id <id> --region <region> to read its actual address."
    ),
    "change-ip": (
        "Give the customer the five steps with the three notices, have them act in the "
        "console, then rerun this entry point with --intent verify."
    ),
    "add-ip": (
        "Confirm the current binding, then send the secondary ENI plus one-EIP-per-interface "
        "path, and ask for the guest interface output if an address is not answering."
    ),
    "retain-ip": (
        "Answer the address question, then route the transfer or rebuild itself to the account "
        "transfer skill."
    ),
    "billing": (
        "State the two models and the irreversible points, then send the customer to the "
        "console conversion page for the estimated fee instead of quoting a number."
    ),
    "ip-missing": (
        "Report whether an address exists now, then either point at the EIP list to re-bind, "
        "or, if the address was released less than 7 days ago, send the customer to the EIP "
        "page's apply-for-a-specific-address path; once that window has passed it is gone."
    ),
    "verify": (
        "Report whether the old EIP is gone and the new address is bound; if any EIP is left "
        "Available in the region, warn about the billing tail."
    ),
    "triage": (
        "Send the handoff wording for the matched area and stop; do not open the change path "
        "for these symptoms."
    ),
}
