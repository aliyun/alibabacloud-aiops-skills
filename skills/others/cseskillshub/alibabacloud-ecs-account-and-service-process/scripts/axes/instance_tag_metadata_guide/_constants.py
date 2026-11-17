#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS instance tag / metadata /
resource-group guide
============================================================================
SECURITY: this skill is strictly READ-ONLY. This module holds no credentials
and performs no I/O of any kind: authentication is resolved exclusively by the
aliyun CLI default credential chain, and no access key or secret ever reaches
this file.

Per platform rule MUST 1.1.2 the scripts/ directory may contain executable
code only, so every table this skill answers from (authorization-error
wording, metadata-service rule facts, tag naming rules, resource-group
visibility rules, documentation pointers) is embedded here as a Python
constant instead of living in a data file.

Evidence discipline
-------------------
Every statement below carries a ``source`` label. Allowed labels are:
  * ``api:<action>``   -- field behaviour verified against the live OpenAPI.
  * ``ticket:<id>``    -- taken from a real support-ticket conversation.
  * ``summary:<id>``   -- taken from a ticket summary whose conversation was
                          NOT re-pulled; the wording is therefore weaker and
                          is always reported as "reported, not verified".
  * ``doc:<url>``      -- official documentation link supplied verbatim.
Nothing here is model memory: where the evidence set is silent the constant
says so explicitly and no URL is invented.
"""

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-instance-tag-metadata-guide"

# User-Agent template attached to every OpenAPI call of one run.
USER_AGENT_TEMPLATE = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{{session-id}} skill-version/{{skill-version}}"

# ---------------------------------------------------------------------------
# API metadata (verified with `aliyun <product> <Action> --help`, CLI 3.4.5)
# ---------------------------------------------------------------------------

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"
STS_ENDPOINT = "sts.aliyuncs.com"

# The ONLY actions this skill may call. Anything outside this tuple is
# prohibited; the list is also what references/ram-policies.md declares.
READ_ACTION_WHITELIST = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus",
    "sts:GetCallerIdentity",
)

# ---------------------------------------------------------------------------
# Limits and defaults
# ---------------------------------------------------------------------------

# Region used when the caller omits --region (always declared in output).
DEFAULT_REGION = "cn-hangzhou"
# Per-call timeout handed to every subprocess invocation (rule 7.6.1).
DEFAULT_TIMEOUT = 60
# DescribeInstances page size (API maximum for MaxResults on this action).
MAX_RESULTS = 100
# Guardrail on pages fetched per region per query.
MAX_PAGES = 20
# DescribeInstanceStatus page size (API range is 1-50).
STATUS_PAGE_SIZE = 50
# DescribeInstanceStatus accepts at most 100 ids per call (InstanceId.n).
MAX_STATUS_IDS = 100
# Cap on regions walked in one run, so a wide request stays bounded.
MAX_REGIONS = 10

# Placeholder printed when an instance carries no resource group id.
# Verified live on api:DescribeInstances -- instances that live in the account
# default group return an EMPTY ResourceGroupId, not the id of a group.
DEFAULT_GROUP_LABEL = "(no resource group id returned: account default group)"

# Tag keys with this prefix are created by Alibaba Cloud services, not by the
# customer. Verified live on api:DescribeInstances -- for example
# "acs:tag:createdby" is attached automatically to console-created instances.
SYSTEM_TAG_PREFIX = "acs:"

# ---------------------------------------------------------------------------
# Instance metadata service facts
# ---------------------------------------------------------------------------

METADATA_IP = "100.100.100.200"
METADATA_URL_V1 = f"http://{METADATA_IP}/2016-01-01/meta-data/instance-id"
METADATA_SERVICE_CIDR = "100.100.0.0/16"
METADATA_DNS_SERVERS = ("100.100.2.136", "100.100.2.138")
METADATA_EXTRA_CIDRS = ("100.64.0.0/10",)

# ---------------------------------------------------------------------------
# Documentation pointers (verbatim, evidence-backed URLs only)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "ecs-overview": (
        "ECS product overview",
        "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
    ),
    "ecs-feature-list": (
        "ECS feature catalogue (which features exist, at which scope)",
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "product-function-custom-node-ecs-normal.md",
    ),
    "ram-resource-group-grant": (
        "Grant a RAM identity permissions at resource-group scope",
        "https://help.aliyun.com/zh/resource-management/resource-group/"
        "user-guide/add-ram-authorization",
    ),
    "ram-ecs-in-one-group": (
        "Use a resource group to let a RAM user manage only certain ECS "
        "instances",
        "https://help.aliyun.com/zh/ram/use-cases/"
        "use-a-resource-group-to-manage-an-ecs-instance",
    ),
    "ram-duty-separation": (
        "Separate ECS RAM permissions by responsibility",
        "https://help.aliyun.com/zh/ecs/user-guide/avoid-using-the-main-"
        "account-to-grant-different-permissions-to-members-of-the-sub-"
        "account-with-different-responsibilities.md",
    ),
    "tag-auto-snapshot": (
        "Apply an automatic snapshot policy to instances (tag based)",
        "https://help.aliyun.com/zh/ecs/user-guide/apply-an-automatic-"
        "snapshot-policy-to-the-instance.md",
    ),
    "ssh-key-pair": (
        "Connect to a Linux instance by using an SSH key pair",
        "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-"
        "instance-by-using-an-ssh-key-pair",
    ),
}

# Topics for which the evidence set contains NO verified documentation URL.
# The skill states this instead of inventing a link.
DOC_GAPS = (
    "instance metadata service (endpoint, API versions, hardening options)",
    "ECS tag design, tag-based cost allocation and the tag listing action",
    "resource-group transfer of ECS instances and cross-group limits",
)

# Which documentation gap applies to which knowledge topic (index into
# DOC_GAPS). Keeping this explicit stops the report from implying that a doc
# was consulted when the evidence set contains none.
TOPIC_DOC_GAPS = {
    "resource-group-visibility": (2,),
    "ram-resource-group-authz": (),
    "metadata-service": (0,),
    "tags-and-tagging": (1,),
    "instance-division-and-ownership": (2,),
}

# Cross-check dates carried in every report.
EVIDENCE_DATE = "2026-08"
API_SHAPE_DATE = "2026-09-18"

# ---------------------------------------------------------------------------
# Report chrome
# ---------------------------------------------------------------------------

REPORT_BANNER = (
    "READ-ONLY SKILL -- NO CHANGES WERE MADE TO ANY RESOURCE BY THIS REPORT"
)

VISIBILITY_DECLARATION = (
    "Data visibility: only resources of the account behind the current CLI "
    "credential, in the regions queried, are visible. Cross-account "
    "resources, instances you did not name, console/browser filter state and "
    "anything inside the operating system are NOT visible to this skill."
)

HARD_LIMITATION = (
    "This skill cannot read the inside of an instance (route table, "
    "iptables/nftables, cloud-init state, installed VPN or overlay software) "
    "and cannot change any configuration. Statements about those layers are "
    "checklists for you to run, never findings of this skill."
)

HANDOFF_SENTENCE = (
    "If you prefer not to run those checks yourself, open a support ticket "
    "and authorize remote diagnosis; after the check, send the output back "
    "and this skill can re-verify the cloud-side facts read-only."
)

# ---------------------------------------------------------------------------
# Authorization-error wording table
# ---------------------------------------------------------------------------
# Each entry: id, signals (substrings matched in customer error text),
# verdict, customer_steps, source.

AUTH_ERROR_RULES = (
    {
        "id": "implicit-deny-in-resource-group",
        "signals": (
            "NoPermissionType: ImplicitDeny",
            "PolicyType: ResourceGroupLevelIdentityBasedPolicy",
            "ImplicitDeny",
            "ResourceGroupLevelIdentityBasedPolicy",
        ),
        "verdict": (
            "The identity carries no allow for that action inside the target "
            "resource group. An account-level Allow on the RAM user does not "
            "cover a call that is scoped to a resource group whose own "
            "authorisation inventory is empty -- the resource-group-level "
            "identity policy denies implicitly."
        ),
        "customer_steps": (
            "Confirm which resource group the request is scoped to, then "
            "grant the needed action at that resource-group scope (RAM / "
            "Resource Management console).",
            "For instance creation, also keep the VPC, vSwitch and security "
            "group in the same resource group as the instance being created.",
            "Cost-and-billing actions are not grantable at resource-group "
            "scope; grant those at account scope.",
            "Re-run this read-only check afterwards to confirm the instance "
            "really is inside the intended resource group.",
        ),
        "source": "ticket:000FLRZSHR (agent's written conclusion)",
    },
    {
        "id": "list-tag-resources-no-group-scope",
        "signals": (
            "ecs:ListTagResources",
            "ListTagResources",
        ),
        "verdict": (
            "Some ECS console calls -- the tag listing call is the documented "
            "example -- are issued WITHOUT a resource group, so a "
            "resource-group-scoped grant cannot satisfy them and the console "
            "shows a permission error even though the intended operation is "
            "allowed. Security Center and CloudMonitor console calls behave "
            "the same way."
        ),
        "customer_steps": (
            "Option 1: ignore that message and carry on with the intended "
            "operation; verify the operation itself succeeds.",
            "Option 2: create a custom policy for exactly the reported action "
            "at account (global) scope, and keep the rest of the grants at "
            "resource-group scope.",
        ),
        "source": "ticket:000CTRT3JT (agent's conclusion, conversation pulled)",
    },
    {
        "id": "condition-key-deny",
        "signals": (
            "ecs:NotSpecifySecurityGroupId",
            "NotSpecifySecurityGroupId",
        ),
        "verdict": (
            "A Condition key in the policy that the request does not satisfy "
            "produces an implicit deny even when the action is listed in an "
            "Allow statement. Reviewing the Condition block of the policy is "
            "the next step, not adding more actions."
        ),
        "customer_steps": (
            "Paste the policy JSON and look for a Condition block referencing "
            "the resource being requested.",
            "Remove the Condition or express the intended restriction "
            "explicitly, then retry.",
        ),
        "source": "summary:000BSRMYZW (conversation not re-pulled)",
    },
    {
        "id": "cross-group-association",
        "signals": (
            "security group",
            "VPC",
        ),
        "verdict": (
            "Creating a resource that references another resource (a security "
            "group inside a VPC) can fail when the referenced resource is not "
            "visible at the resource-group scope in use. The reported case "
            "was NOT closed online, so this skill treats it as a hand-off "
            "candidate rather than a rule."
        ),
        "customer_steps": (
            "Check whether the referenced VPC is in the resource group you "
            "have selected.",
            "If the association is the blocker, the referenced resource has "
            "to be moved into the same group, or the operation run where the "
            "referenced resource is visible.",
        ),
        "source": "ticket:0001ZS57G6 (online stage unresolved)",
    },
)

# ---------------------------------------------------------------------------
# Knowledge topics (answers for --question)
# ---------------------------------------------------------------------------

KNOWLEDGE_TOPICS = (
    {
        "id": "resource-group-visibility",
        "title": "Instance not visible in the console list or in a resource group",
        "match": (
            "cannot find", "can not find", "not visible", "not showing",
            "can't see", "missing instance", "resource group", "filter",
            "group context", "switch", "归属",
        ),
        "findings": (
            "Three causes look identical from the console and are separable: "
            "(a) the instance is genuinely in another resource group, "
            "(b) the instance carries no resource group id at all and lives "
            "in the account default group, (c) the console is showing a "
            "resource-group / region context that differs from the one you "
            "expect.",
            "Causes (a) and (b) are answerable read-only by this skill's fact "
            "mode. Cause (c) is browser-side: the resource-group "
            "selector in the top-left of the console and a ResourceGroupId "
            "query parameter left in the URL both persist a filter that no "
            "API can see.",
            "Granting a resource group to a RAM user does not make the user "
            "land on it: the console has to be switched to that group before "
            "the resources appear.",
        ),
        "customer_steps": (
            "Run this skill's fact mode on the instance id and the region(s) to "
            "read the authoritative ResourceGroupId.",
            "In the console, switch the resource-group selector (top-left) to "
            "the target group or to all groups, then reload.",
            "Check the browser address bar for a ResourceGroupId parameter "
            "and open the list page without it (or in a private window).",
            "Confirm the region selector matches the region the instance is "
            "in.",
        ),
        "docs": ("ram-ecs-in-one-group", "ram-resource-group-grant"),
        "source": "ticket:000DGRKP59 (closed), summary:000ACRDL92, "
                  "summary:0001FS10GN, api:DescribeInstances",
    },
    {
        "id": "ram-resource-group-authz",
        "title": "RAM user plus resource group: which grant is missing",
        "match": (
            "ram", "policy", "permission", "auth", "denied",
            "implicitdeny", "resourcegrouplevel", "not authorized", "403",
            "授权", "权限",
        ),
        "findings": (
            "Resource-group level grants and account level grants are "
            "evaluated separately; an account-level Allow does not make a "
            "resource-group-scoped call succeed, and vice versa.",
            "Some console calls carry no resource group at all, so they can "
            "only be satisfied at account scope. A permission error on such a "
            "call is not evidence that the intended operation is blocked.",
            "Instance creation inside a resource group needs the network "
            "resources (VPC, vSwitch, security group) in the same group; "
            "billing-related actions cannot be granted at group scope.",
            "This skill reads cloud facts only. It does not see your policy "
            "JSON or where a grant is attached, so paste those when asking "
            "about a denial.",
        ),
        "customer_steps": (
            "Note the failing action name and the RequestId from the error.",
            "In the RAM console, check the identity's grants twice: once at "
            "account scope, once at the target resource group.",
            "Grant the missing action at the scope the call actually uses.",
            "Ask this skill to re-read the instance's real resource group and "
            "tags to confirm the object you authorized is the object you are "
            "trying to see.",
        ),
        "docs": ("ram-resource-group-grant", "ram-ecs-in-one-group",
                 "ram-duty-separation"),
        "source": "ticket:000FLRZSHR, ticket:000CTRT3JT, ticket:00085RWLDE",
    },
    {
        "id": "metadata-service",
        "title": "Instance metadata service (100.100.100.200) reachability and rules",
        "match": (
            "100.100.100.200", "metadata", "imds", "cloud-init", "user-data",
            "instance-id", "errno 101", "network is unreachable",
            "httptokens", "hardening", "forced", "v2", "元数据", "加固",
        ),
        "findings": (
            f"The metadata service is reached from inside the instance at "
            f"{METADATA_IP}; it lives in the {METADATA_SERVICE_CIDR} range "
            "that Alibaba Cloud reserves inside the network for platform "
            "services (the same range carries the internal DNS resolvers "
            f"{'/'.join(METADATA_DNS_SERVERS)}).",
            "cloud-init and agent software read it at boot, so a broken route "
            "or a host firewall rule that rejects that range shows up as "
            "cloud-init timeouts and 'Network is unreachable', not as an ECS "
            "API error.",
            "Hardening controls whether a metadata read needs a session token "
            "first. On the cloud side that setting is the instance metadata "
            "option; this skill can only READ it -- turning it on is a change "
            "you make yourself, and instances that never set it return an "
            "empty value.",
            "The decisive readings for this symptom are inside the operating "
            "system, which this skill does not touch. The cloud-side check it "
            "can do is an exclusion: instance status, region, VPC and security "
            "groups attached, current metadata option value.",
        ),
        "customer_steps": (
            f"From a shell inside the instance run: curl -v "
            f"{METADATA_URL_V1} (a working endpoint answers the instance id).",
            "Check the route for the reserved range: ip route get "
            f"{METADATA_IP} and ip route show | grep -E '100\\.100|100\\.64'.",
            "Check host rules for a reject on that range: iptables -S | grep "
            "100. and nft list ruleset (look for a REJECT covering "
            f"{METADATA_SERVICE_CIDR} or {METADATA_EXTRA_CIDRS[0]}).",
            "List third-party VPN or overlay network software (tailscale and "
            "similar tools) -- a route that swallows the reserved range is a "
            "reported cause.",
            "Check whether the in-guest agent reports a client-side network "
            "block as well: that is a Cloud Assistant symptom, owned by its "
            "own skill.",
            "Decide any change yourself, and take your own backup step first; "
            "this skill reports only what a check returned and never applies "
            "one.",
        ),
        "docs": (),
        "source": "ticket:0003YRXU6P, summary:000CARW2UA, summary:00047S4Z0N, "
                  "api:DescribeInstances",
    },
    {
        "id": "tags-and-tagging",
        "title": "Instance tags: naming rules, inventory, tag-driven policies",
        "match": (
            "tag", "tags", "key", "value", "label", "cost", "allocation",
            "unbind", "bind", "分类", "标签",
        ),
        "findings": (
            "Tags are read back from the instance itself in this skill: the "
            "instance listing returns a tag array whose elements carry a "
            "tag key and a tag value.",
            "Keys that start with the reserved service prefix are created by "
            "Alibaba Cloud (for example the one recording which identity "
            "created the instance) and are not customer tags -- the "
            "fact mode of this skill separates them.",
            "Console forms that show a tag field accept a name of 2 to 128 "
            "characters, starting with a letter (either case) or a Chinese "
            "character, and not starting with an http or https prefix; the "
            "field may be left empty when tagging is not needed.",
            "Tag-driven automation such as applying an automatic snapshot "
            "policy to the instances carrying a given tag is documented for "
            "the instance itself; tag-based cost allocation has no verified "
            "document in this skill's evidence set and is not promised here.",
        ),
        "customer_steps": (
            "Run this skill's fact mode (--inventory for a fleet-wide read) to list "
            "every instance with its tags and resource group.",
            "Add or remove tags in the console or with your own tooling, then "
            "re-run the same read to verify the result.",
            "Keep one key per dimension (business, environment, owner) rather "
            "than encoding several dimensions in one value.",
        ),
        "docs": ("tag-auto-snapshot", "ssh-key-pair"),
        "source": "ticket:0005PR5NGW, ticket:000CTRT3JT, api:DescribeInstances",
    },
    {
        "id": "instance-division-and-ownership",
        "title": "Splitting instances between resource groups / owners",
        "match": (
            "divide", "split", "organisation", "ownership", "belong",
            "assign", "move", "划分", "归属",
        ),
        "findings": (
            "Ownership facts are readable: every instance carries at most one "
            "resource group id plus its tag set, and both are returned by the "
            "instance listing.",
            "Moving an instance between resource groups is a change this "
            "skill will not perform or script for you; it can only state the "
            "current group and later verify the group you moved it to.",
            "Two ways to slice a fleet are independent: resource group "
            "(authorisation boundary) and tags (queryable labels). Use the "
            "group for who may act, tags for what something is.",
        ),
        "customer_steps": (
            "Decide the grouping dimension first, then inventory the current "
            "state with this skill.",
            "Perform the actual regrouping or tagging yourself in the console.",
            "Re-run this skill to verify each instance now reports the "
            "intended group and tags.",
        ),
        "docs": ("ram-ecs-in-one-group", "ecs-feature-list"),
        "source": "ticket:000DGRKP59, ticket:00094RD4DX, api:DescribeInstances",
    },
)

# ---------------------------------------------------------------------------
# Out-of-scope hand-off table
# ---------------------------------------------------------------------------
# Each entry: signal substrings, the neighbouring skill that owns it, note.

HANDOFF_RULES = (
    {
        "signals": ("security group", "rule", "port", "ssh", "rdp"),
        "skill": "alibabacloud-ecs-access-block-layered",
        "note": "layered access-block checks on security groups and rules",
    },
    {
        "signals": ("policy json", "grant permission", "write a policy",
                    "create a policy", "custom policy"),
        "skill": "alibabacloud-ecs-ram-policy-diagnosis",
        "note": "authoring and auditing RAM policy documents",
    },
    {
        "signals": ("cloud assistant", "CLIENT_RESTARTED",
                    "ClientNetworkBlocked", "command in the instance",
                    "run command"),
        "skill": "alibabacloud-ecs-cloud-assistant-diagnosis",
        "note": "the in-guest agent itself and command execution channel",
    },
    {
        "signals": ("nginx", "apache", "site download", "mime", "website"),
        "skill": "alibabacloud-ecs-web-service-runtime-config",
        "note": "web-server behaviour inside the guest",
    },
    {
        "signals": ("windows activation", "not activated", "kms"),
        "skill": "alibabacloud-ecs-windows-activation-component",
        "note": "guest OS activation components",
    },
    {
        "signals": ("snapshot policy", "auto snapshot"),
        "skill": "alibabacloud-ecs-snapshot-policy-check",
        "note": "snapshot policy coverage review",
    },
)
