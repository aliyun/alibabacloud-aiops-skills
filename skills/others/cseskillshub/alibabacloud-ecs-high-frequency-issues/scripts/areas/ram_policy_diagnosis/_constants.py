#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_constants.py -- embedded static data for area:ram-policy-diagnosis
===============================================================================
SECURITY: This module holds no credentials and performs no calls. It embeds,
as Python constants, every reference table the skill uses (denial/exclusion
signal patterns, action-owner catalog, policy-template corpus, manual grant
steps, handoff areas, guest command whitelist) -- per platform rule MUST 1.1.2
there are NO data files inside scripts/.

Evidence discipline (batch rule: names without OpenAPI contract verification
never enter the skill's own call surface):
  * "verified"     -- api-name and parameters verified for THIS build; the
                      skill may invoke them (see VERIFIED_ACTIONS).
  * "ticket-cited" -- the name was quoted inside a real support-ticket
                      conversation. It may only appear as clearly-labelled
                      customer-facing template text; this skill NEVER invokes
                      it and it is NOT declared in related_apis.yaml or
                      references/ram-policies.md.
  * "doc"          -- console guidance distilled from the official document
                      list verified in references/ram-policy-diagnosis__help-docs.md.

Language rule: all strings are English (MUST 4.1.2). Authorization-failure
literals use the NoPermission / ImplicitDeny vocabulary only.
"""

SKILL_NAME = "alibabacloud-ecs-ram-policy-diagnosis"

# ---------------------------------------------------------------------------
# API / CLI channel constants
# ---------------------------------------------------------------------------

ECS_API_VERSION = "2014-05-26"        # verified contract version (ecs)
STS_API_VERSION = "2015-04-01"        # verified contract version (sts)
STS_ENDPOINT = "sts.aliyuncs.com"     # central, region-less identity service

DEFAULT_REGION = "cn-hangzhou"        # defensive default for the CLI profile
                                      # region flag; never used to silently
                                      # relocate the customer's query
DEFAULT_TIMEOUT = 60                  # per-call timeout seconds (MUST 7.6.1)
POLL_MAX_ATTEMPTS = 6                 # guest-command result polling cap
POLL_INTERVAL_SECONDS = 5             # seconds between polls
MAX_ERROR_TEXT_CHARS = 4000           # truncation guard for --error-text

ECS_RUN_TYPE_SHELL = "RunShellScript"  # Linux guest command interpreter type

# The ONLY cloud actions this skill's scripts invoke (triple-aligned with
# related_apis.yaml and references/ram-policies.md). ecs:run-command (the
# RAM action of OpenAPI operation RunCommand) is a
# write-attribute action: it is used EXCLUSIVELY to dispatch one
# whitelisted, observation-only diagnostic command per confirmed request.
VERIFIED_ACTIONS = {
    "sts:GetCallerIdentity": "identity type of the configured credential",
    "ecs:DescribeInstances": "instance visibility / region / resource-group binding",
    "ecs:run-command": "dispatch one whitelisted observation-only guest command (confirmation-gated)",
    "ecs:DescribeInvocations": "read back the dispatched command's status and output",
}

# ---------------------------------------------------------------------------
# Guest-side command whitelist (batch low-risk list, class B: read-class
# in-guest diagnostics only; exact strings). Anything else is refused with
# GUEST_COMMAND_REJECT_NOTE. All listed commands mutate nothing.
# ---------------------------------------------------------------------------
GUEST_COMMAND_WHITELIST = {
    "whoami": "whoami",
    "id": "id",
    "hostname": "hostname",
    "uptime": "uptime",
    "uname": "uname -a",
    "date": "date",
}

GUEST_COMMAND_REJECT_NOTE = (
    "Commands outside the embedded whitelist are NEVER dispatched by this "
    "skill. Ask the instance owner to run any other in-guest check manually "
    "and paste the output back. This skill never performs cleanup, restart, "
    "process-kill, removal of files or services, or service-control actions "
    "inside the guest or on the cloud side."
)

GUEST_CONFIRMATION_BRIEF = (
    "About to run, via the Cloud Assistant command channel (action "
    "ecs:run-command), exactly ONE command on instance {instance_id} in "
    "region {region_id}: `{command}`. Nature: observation-only, it changes "
    "no guest state and no cloud resource; nothing to revert. Cost: none. "
    "Impact: a single short-lived command execution recorded in Cloud "
    "Assistant invocation history. Repeat with --confirm only after the "
    "customer has seen this brief and agreed."
)

# ---------------------------------------------------------------------------
# K1 signal patterns: denial (permission) vs exclusion (non-permission).
# Authorization-failure vocabulary is NoPermission / ImplicitDeny only.
# ---------------------------------------------------------------------------

DENIAL_SIGNAL_PATTERNS = [
    ("http-403", r"(?i)\b403\b",
     "HTTP 403 authorization-denied status appears in the reported error"),
    ("no-permission", r"(?i)no[ _-]?permission|nopermission",
     "explicit no-permission wording (NoPermission family)"),
    ("not-authorized", r"(?i)not authorized|unauthori[sz]ed",
     "explicit not-authorized wording"),
    ("deny-rule-hit", r"(?i)implicitdeny|implicit deny|denied by.{0,20}deny",
     "the request was rejected by a deny evaluation (ImplicitDeny / explicit Deny)"),
    ("ram-tagged-denial",
     r"(?i)\bram\b.{0,30}(denial|denied|rejected|403|no permission)"
     r"|(denial|denied|rejected|403|no permission).{0,30}\bram\b",
     "the denial is explicitly attributed to RAM authorization"),
    ("ram-suffixed-code",
     r"(?i)\b[a-z][a-z0-9]{2,24}(?:\.[a-z][a-z0-9]{0,16})*\.ram\b",
     "the failure is reported as an error code whose trailing segment names the "
     "RAM authorization layer -- a code shape, so it counts as a denial even "
     "when the customer pastes no HTTP status and no prose"),
    ("access-refused", r"(?i)permission denied|cannot (?:operate|manage|view|access|see)"
     r"|can'?t (?:operate|manage|view|access|see)|you (?:are|do) not have.{0,20}permission",
     "access refused / resource invisible to the current identity"),
]

EXCLUSION_SIGNAL_PATTERNS = [
    ("operation-state-blocked",
     r"(?i)(?:operation|request).{0,30}not (?:allowed|support)|state.{0,25}not support"
     r"|invalid(?:status|state)",
     "the block comes from resource lifecycle state, not from authorization",
     "resource-lifecycle"),
    ("browser-cors", r"(?i)\bcors\b|cross-origin",
     "a browser CORS message is an application-layer problem, not a cloud permission",
     "application-layer"),
    ("security-group-semantics",
     r"(?i)security group|source ip|port ?\d{2,5}|\bssh\b.{0,30}(login|access|key|password)"
     r"|\b22\b.{0,25}(open|allow)",
     "IP/port reachability wording belongs to the security-group area, not to RAM",
     "security-group"),
    ("empty-error-state-rollback",
     r"(?i)(?:detach|unassign|unmount).{0,40}(?:fail|stuck|rollback|back to|in use)"
     r"|no error (?:message|info)",
     "an operation that rolls back with no denial message points at the guest side,"
     " not at RAM authorization",
     "guest-resource"),
    ("site-account-system",
     r"(?i)international site|alibabacloud\.com|china site|account system|wrong site",
     "China-site and International-site accounts are separate systems; invisibility"
     " there is not a RAM grant problem",
     "account-system"),
    ("platform-managed-policy", r"(?i)jushita",
     "platform-side managed policy wording; grants inside that platform are governed"
     " by the platform console, not by plain RAM",
     "platform-policy"),
    ("snapshot-dependency-billing",
     r"(?i)snapshot.{0,45}(?:delete|deleting|charge|billing|fail|fee)"
     r"|(?:image|billing).{0,30}snapshot",
     "snapshot deletion blocked by a custom-image dependency, or snapshot charges"
     " -- billing / image area",
     "billing-image"),
    ("boot-image-failure",
     r"(?i)dracut|uefi|bios|cannot boot|won'?t start|fails? to start|stuck on start",
     "boot failure / BIOS-UEFI image wording belongs to the instance-state and image area",
     "instance-state"),
    ("expired-release-data",
     r"(?i)expir\w+.{0,35}recover|recover\w+.{0,35}expir|released?.{0,30}data",
     "recovery of released/expired resources is a backup-restore question with no"
     " permission path",
     "backup-restore"),
    ("realname-blocked", r"(?i)real[- ]?name|identity verification",
     "access blocked by account real-name verification -- account area",
     "account-verification"),
    ("connection-method-limit",
     r"(?i)vnc|graphical|remote desktop|workbench.{0,35}(?:timeout|time out|cannot open|slow)",
     "client capability / connection-method wording belongs to the remote-connection area",
     "connection-method"),
]

# Action-name extraction patterns, in priority order.
ACTION_EXTRACT_PATTERNS = [
    r"(?i)action\s*:?\s*\(?\s*([a-z][a-z0-9-]*:[A-Z][A-Za-z0-9]{2,60})\s*\)?",
    r"(?i)action\s*:?\s*\(?\s*([A-Z][A-Za-z0-9]{3,60})\s*\)?",
    r"\b([a-z][a-z0-9-]*:[A-Z][A-Za-z0-9]{2,60})\b",
    r"\b(Run[A-Z][A-Za-z0-9]{3,60}|Describe[A-Z][A-Za-z0-9]{3,60}"
    r"|List[A-Z][A-Za-z0-9]{3,60}|Get[A-Z][A-Za-z0-9]{3,60})\b",
]

# RAM action-prefix -> (product, caveat). Prefix is what appears before ':'.
ACTION_OWNERS = {
    "ecs": ("Elastic Compute Service (ECS)", ""),
    "ecs-workbench": ("ECS Workbench",
                      "separate prefix from ecs; a grant written under 'ecs' never"
                      " matches an 'ecs-workbench' action"),
    "oos": ("Operation Orchestration Service (OOS)",
            "OOS is NOT OSS -- the names differ by one letter but are different"
            " products (real ticket confusion: 'is it OOS not OSS')"),
    "oss": ("Object Storage Service (OSS)", ""),
    "vpc": ("Virtual Private Cloud (VPC)",
            "instance-creation flows need VSwitch/VPC read actions even when an"
            " existing VSwitch is reused"),
    "bss": ("Billing (BSS)", "RAM prefixes for billing APIs are bss / bssapi,"
                           " not the CLI product name"),
    "ram": ("Resource Access Management (RAM)", ""),
    "sts": ("Security Token Service (STS)", ""),
    "cms": ("Cloud Monitor (CMS)",
            "API name and RAM action name can differ (API DescribeMetricLast is"
            " authorized as cms:QueryMetricLast); never derive one from the other"),
    "log": ("Simple Log Service",
            "the RAM prefix is 'log' while the product short-name is 'sls'"),
    "yundun-aegis": ("Security Center",
                     "the CLI product is 'sas' but the RAM prefix is 'yundun-aegis'"),
}

# Unprefixed action tokens commonly seen inside console error strings.
BARE_ACTION_HINTS = {
    "chatmessages": "ecs-workbench",
    "listexecutionriskytasks": "oos",
    "startexecution": "oos",
    "gettemplate": "oos",
    "getapplicationgroup": "oos",
    "listinstancepackagestates": "oos",
    "runinstances": "ecs",
    "describeinstances": "ecs",
    "runcommand": "ecs",
    "describeinvocations": "ecs",
    "describeinvocationresults": "ecs",
    "describecloudassistantstatus": "ecs",
    "listtagresources": "ecs",
    "describeorderdetail": "bss",
    "getobject": "oss",
    "getcalleridentity": "sts",
}

# ---------------------------------------------------------------------------
# K2 root-cause taxonomy: four ordered checks applied to every permission case.
# ---------------------------------------------------------------------------
VERIFICATION_CHECKLIST = [
    ("1. Policy syntax validity",
     "Does the attached custom policy use a legal Action/Resource combination? "
     "A wildcard Action entry is only legal together with a wildcard Resource "
     "entry, and actions that do not support resource-level scoping must be "
     "granted with a wildcard Resource. An illegal combination silently matches "
     "nothing and surfaces as a denial even though the grant 'looks applied'."),
    ("2. Authorization scope x console context",
     "Was the grant made at account level or resource-group level? "
     "Resource-group grants are visible ONLY when the console (or the mobile "
     "app's top-left 'All Resources' picker) is switched to that resource "
     "group. Confirm with DescribeInstances that the resource exists in the "
     "queried region and note its actual resource-group binding."),
    ("3. Fine-grained cross-product actions",
     "Does the failing operation actually call another product's API? Console "
     "features are chains: Workbench AI chat needs ecs-workbench actions; the "
     "web-VSCode install rides on OOS plus Cloud Assistant plus OSS read plus "
     "BSS order read; RunInstances needs VPC/VSwitch reads. Grant the whole "
     "chain, not the product named in the page URL."),
    ("4. Deny audit and identity placement",
     "Is an Effect=Deny statement attached to the identity (explicit Deny "
     "overrides every Allow)? Is the grant attached where the client actually "
     "presents credentials: RAM user vs RAM role (a client that assumes a role "
     "is judged by the ROLE's grants)? GetCallerIdentity reports which of the "
     "three identity types the current credential is."),
]

# ---------------------------------------------------------------------------
# Capability-chain routing: symptom signal -> template ids to emit.
# ---------------------------------------------------------------------------
CAPABILITY_CHAINS = [
    ("workbench-chat", r"(?i)workbench",
     ["t3_workbench_chat"],
     "ECS Workbench operations (AI chat panel especially) are authorized under the "
     "ecs-workbench action namespace, not plain ecs (ticket T-39B65627, ticket-cited)."),
    ("oos-package-install", r"(?i)listexecutionriskytasks|vs ?code|\boos\b",
     ["t4_oos_vscode_chain"],
     "Installing web VSCode from Workbench runs through OOS package management: the "
     "denied action belongs to OOS even though the page is the Workbench console "
     "(ticket T-296B2D19). OOS is not OSS."),
    ("instance-create-chain", r"(?i)runinstances|create.{0,25}(?:instance|ecs)",
     ["t5_runinstances_create", "t_syntax_note"],
     "RunInstances with an existing VSwitch still requires explicit VPC/VSwitch read "
     "actions, and a wildcard Action form must pair with a wildcard Resource form "
     "(ticket T-8FE09114)."),
    ("oos-role-flow", r"(?i)(?:role|authoriz|assum).{0,40}(?:oos|alert|reboot|orchestr)"
     r"|(?:oos|alert|orchestr).{0,40}(?:role|authoriz|assum)",
     ["t6_least_privilege_read", "role_flow_steps"],
     "OOS-driven operations (for example auto-reboot on a high-CPU alert) execute as "
     "a RAM role: create the role trusted to the OOS cloud service, then grant "
     "permissions TO THE ROLE, not to the RAM user (ticket T-0217BF77)."),
    ("ak-leak-incident", r"(?i)leak|expos\w*|malicious|attacked|abnormal (?:sub|user|account)",
     ["ak_leak_steps"],
     "A leaked AccessKey may have been used to create rogue sub-identities. Containment "
     "is manual-only (disable keys, inventory identities); also re-check security groups "
     "because real tickets show both risks together (ticket T-E55C752C)."),
    ("least-privilege-planning",
     r"(?i)least|minimum.{0,20}(?:privile|polic|permission)|only read|scope.{0,25}(?:access|polic)"
     r"|(?:sub|ram).{0,15}(?:user|account).{0,35}(?:plan|design|what.{0,10}(?:permission|polic))"
     r"|sub-?account.{0,45}(?:permission|access|polic)",
     ["t6_least_privilege_read", "scope_model_note"],
     "Plan the minimum action set for the exact operation, then choose account vs "
     "resource-group scope. Cost-console data needs billing (BSS) permissions that are "
     "NOT verified for this build -- that part is a documented handoff (ticket T-2D30AEF6)."),
    ("role-generic", r"(?i)\brole\b|assume|service ?linked|aliyunservicerolefor",
     ["role_flow_steps", "slr_note"],
     "Roles carry their own grants; AliyunServiceRoleFor* identities are service-linked "
     "roles with customer-self-service-only removal (ticket T-8FA544FE)."),
    ("os-user-vs-ram-user",
     r"(?i)(?:create|add).{0,30}(?:admin|user|account).{0,35}(?:login|server|remote|ssh)"
     r"|(?:server|linux|ubuntu|windows).{0,25}(?:user|account).{0,30}(?:admin|permission)",
     ["os_user_note"],
     "Operating-system login accounts and RAM users are different layers; building a "
     "second OS admin user on the instance needs the instance credential / connection "
     "path, not RAM (ticket T-71463C20)."),
]

# ---------------------------------------------------------------------------
# Syntax rules (K2-1 detail), each with its ticket evidence label.
# ---------------------------------------------------------------------------
SYNTAX_RULES = [
    ("A wildcard Action entry is legal only with a wildcard Resource entry. "
     "Mixing a wildcard Action with an instance-ARN Resource silently matches "
     "nothing. [evidence: ticket T-8FE09114, summary-derived]",
     "ticket T-8FE09114"),
    ("Actions that do not support resource-level scoping must be granted with "
     "the wildcard Resource form; an instance-scoped grant never matches them. "
     "[evidence: ticket T-39B65627 -- ecs-workbench:ChatMessages, ticket-cited]",
     "ticket T-39B65627"),
    ("One console feature can require actions from several products at once; "
     "grant the full chain. [evidence: ticket T-296B2D19 pasted policy -- "
     "Workbench / OOS / Cloud Assistant / OSS / BSS actions, ticket-cited]",
     "ticket T-296B2D19"),
    ("An Effect=Deny statement attached anywhere to the identity overrides all "
     "Allow grants. Audit attached custom policies before re-granting. "
     "[evidence: ticket T-EE03C367 staff advice]",
     "ticket T-EE03C367"),
    ("API names and RAM action names are not guaranteed identical across "
     "products (Cloud Monitor and billing prove the trap); verify each name "
     "against the product's authorization reference before writing it into a "
     "policy. [batch rule]", ""),
]

# ---------------------------------------------------------------------------
# Scope model (K2-2 detail).
# ---------------------------------------------------------------------------
SCOPE_MODEL = {
    "account": "Visible everywhere in the account; simplest; use when the sub-account "
               "may manage all resources.",
    "resource_group": "Visible only while the console context (web: resource-group "
                      "switcher; mobile app: top-left 'All Resources' picker) is on "
                      "that resource group. The most common cause of 'granted a "
                      "full-access policy yet still denied' (ticket T-EE03C367).",
    "tag_based": "Tag-condition grants exist for many ECS actions; the exact "
                 "condition grammar is NOT verified for this build (official "
                 "policy-syntax doc to be supplemented) -- treat as a design "
                 "option to verify before pasting.",
}

# ---------------------------------------------------------------------------
# K3 paste-ready policy templates (customer-facing content; this skill never
# applies them). Every Action entry is a concrete name -- no wildcard action
# forms. Evidence labels are emitted with each template.
# ---------------------------------------------------------------------------
POLICY_TEMPLATES = {
    "t1_describe_instances": {
        "title": "View ECS instances only (skill-verified action names)",
        "evidence": "verified",
        "statement": {
            "Effect": "Allow",
            "Action": ["ecs:DescribeInstances"],
            "Resource": "*",
        },
        "notes": [
            "Minimum grant for list/view scenarios.",
            "Resource stays wildcard: this build verified no narrower resource ARN form.",
        ],
    },
    "t3_workbench_chat": {
        "title": "ECS Workbench AI chat permission (ticket-cited names)",
        "evidence": "ticket-cited (not verified against the OpenAPI contract; "
                    "this skill never invokes it)",
        "statement": {
            "Effect": "Allow",
            "Action": ["ecs-workbench:ChatMessages"],
            "Resource": "*",
        },
        "notes": [
            "Reported for repeated 'no permission' toasts inside ECS Workbench "
            "(ticket T-39B65627).",
            "This action reportedly cannot be narrowed to instances, so Resource "
            "must keep the wildcard form or the grant silently never matches.",
            "The staff also suggested attaching the system policy "
            "AliyunECSWorkbenchFullAccess; that customer could not find it in the "
            "grant picker, so the custom policy above is the practical route.",
        ],
    },
    "t4_oos_vscode_chain": {
        "title": "Workbench web-VSCode install chain (ticket-cited names)",
        "evidence": "ticket-cited (not verified against the OpenAPI contract; "
                    "this skill never invokes it)",
        "statement": {
            "Effect": "Allow",
            "Action": [
                "oos:GetApplicationGroup",
                "oos:GetTemplate",
                "oos:ListExecutionRiskyTasks",
                "oos:ListInstancePackageStates",
                "oos:StartExecution",
                "ecs:DescribeCloudAssistantStatus",
                "ecs:DescribeInstances",
                "ecs:DescribeInvocationResults",
                "ecs:DescribeInvocations",
                "ecs:ListTagResources",
                "ecs:run-command",
                "oss:GetObject",
                "bss:DescribeOrderDetail",
            ],
            "Resource": "*",
        },
        "notes": [
            "Reconstructed from the policy a customer pasted back in ticket "
            "T-296B2D19 (the OOS package flow also surfaced one further "
            "Update-form package-state action; when a later denial names it, "
            "decode that denial with --error-text and add the named action "
            "instead of guessing).",
            "Why a billing action is in the chain: the install flow reads the "
            "order detail; why OSS: it fetches the install package. OOS is "
            "System Operation Orchestration, NOT OSS.",
            "Treat every name above as ticket evidence until verification "
            "against the OpenAPI contract is completed; if a name is rejected "
            "by the console, "
            "re-derive it from the next denial's action token.",
        ],
    },
    "t5_runinstances_create": {
        "title": "Create ECS instances with an existing VSwitch (mixed evidence)",
        "evidence": "partly ticket-cited; VPC-side names NOT verified",
        "statement": {
            "Effect": "Allow",
            "Action": [
                "ecs:run-instances",
                "ecs:DescribeInstances",
            ],
            "Resource": "*",
        },
        "notes": [
            "RunInstances is additionally gated by VPC/VSwitch read actions "
            "even when an existing VSwitch is reused (ticket T-8FE09114); the "
            "exact VPC-side RAM names are not verified for this build -- grant "
            "them after decoding the concrete denial, not from memory.",
            "If a broader grant is used while iterating, wildcard Action forms "
            "must pair with wildcard Resource forms (syntax rule 1), then "
            "narrow down.",
        ],
    },
    "t6_least_privilege_read": {
        "title": "Least-privilege inventory read for a scripted AccessKey "
                 "(skill-verified names only)",
        "evidence": "verified",
        "statement": {
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity",
                "ecs:DescribeInstances",
            ],
            "Resource": "*",
        },
        "notes": [
            "Covers 'list all my ECS with a sub-account AccessKey' style needs "
            "(ticket T-2D30AEF6) with verified names.",
            "Cost / expiry-date columns come from billing APIs whose RAM names "
            "are NOT verified for this build -- state the gap and hand that "
            "part to the billing area; do not guess bss names.",
            "Attach the policy to the RAM user the AccessKey belongs to; an "
            "AccessKey created under a role is judged by the role's grants.",
        ],
    },
}

TEMPLATE_GUIDANCE_IDS = [
    "role_flow_steps", "slr_note", "ak_leak_steps", "os_user_note",
    "scope_model_note", "t_syntax_note",
]

# ---------------------------------------------------------------------------
# K4 manual grant steps (RAM side). This skill has NO RAM write capability --
# exactly like ticket staff, who never operated customer accounts either
# ("platform security policy does not allow staff to act on customer
# accounts", ticket T-8FA544FE). All grants are executed by the main account.
# ---------------------------------------------------------------------------
GRANT_STEPS = [
    "1. Sign in to the RAM console user page with the MAIN account: "
    "https://ram.console.aliyun.com/users",
    "2. Open the target RAM user (login name looks like "
    "<name>@<account>.onaliyun.com) and go to its Permissions tab.",
    "3. Click 'Add Permissions' (grant entry). Switch to the System Policies "
    "tab BEFORE searching for a system policy such as AliyunECSFullAccess -- "
    "'the policy cannot be found' reports come from the Custom Policies tab "
    "staying selected (ticket T-0217BF77).",
    "4. Choose the Resource Scope deliberately: 'Account' (visible everywhere) "
    "or a specific resource group (visible only in that group's console "
    "context). Narrowing to the few servers the sub-account manages is a valid "
    "resource-group grant -- the trade-off is the console context switch (see "
    "SCOPE_MODEL in this file and ticket T-EE03C367).",
    "5. Confirm the grant, then have the sub-account sign out and sign in so "
    "the console refreshes its cached permissions.",
    "6. If the grant was resource-group scoped: in the web console switch the "
    "resource-group context, and in the mobile app tap 'All Resources' at the "
    "top-left and pick that resource group (verified staff-guided fix, ticket "
    "T-EE03C367).",
    "7. If a denial persists after an account-level grant: audit every custom "
    "policy attached to the identity (directly or via groups) for "
    "Effect=Deny statements, and re-check the Action/Resource combination "
    "against the syntax rules.",
]

ROLE_FLOW_STEPS = [
    "1. RAM console -> Roles -> create a role: Trusted Entity type = Cloud "
    "Service; Trusted service = the operation-orchestration (OOS / system "
    "operations management) service entry (exact two parameters from ticket "
    "T-0217BF77).",
    "2. In the Roles list, open the created OOS role (e.g. OOSServiceRole) and "
    "add a grant TO THE ROLE -- for the high-CPU auto-restart scenario the "
    "staff attached AliyunECSFullAccess; a narrower custom policy (see "
    "templates) follows the least-privilege principle.",
    "3. Return to the OOS alert scenario and continue its documented steps: "
    "https://help.aliyun.com/zh/oos/use-cases/trigger-restarts-of-ecs-instances-with-high-cpu-utilization-based-on-alerts",
    "4. Remember: a client that assumes a role is judged by the ROLE's "
    "grants, not the RAM user's; grant placement is part of the diagnosis.",
]

SLR_NOTE = (
    "Identities named AliyunServiceRoleFor* are service-linked roles. They can "
    "only be removed by the customer self-service in the RAM console (Roles "
    "list), and only after the linked service no longer needs them; account "
    "real-name verification and RAM console access are prerequisites. Support "
    "will not remove them on the customer's behalf and this skill never "
    "performs the removal (ticket T-8FA544FE)."
)

AK_LEAK_STEPS = [
    "1. With the MAIN account, open the AccessKey management page of the "
    "compromised RAM user and DISABLE (do not delete, so evidence stays "
    "reviewable) every leaked or unknown AccessKey -- manual action only.",
    "2. Inventory RAM users and their AccessKeys for anything created around "
    "the incident window; disable unknown identities manually.",
    "3. Rotate still-needed AccessKeys; move scripts to a least-privilege "
    "policy (see templates) instead of broad grants.",
    "4. Re-check security groups on exposed instances -- a real ticket showed "
    "an attacker path combining a leaked key with ports 22/6379 open to all "
    "IPs (ticket T-E55C752C); source-IP restriction guidance lives in the "
    "security-group quick guide (references/ram-policy-diagnosis__help-docs.md).",
    "5. Before any in-guest cleanup, create a snapshot manually first "
    "(ticket-side standard practice). This skill only prints these steps; it "
    "never disables, deletes or rotates anything itself.",
]

OS_USER_NOTE = (
    "Operating-system login users (root/ubuntu/Administrator) and AliCloud RAM "
    "users are different layers. 'Create two admin login accounts for our "
    "engineers to remote in' is an instance-credential and connection "
    "question, answered on the remote-connection area; RAM answers 'who may "
    "operate this account's cloud resources from the console/API'. (ticket "
    "T-71463C20)"
)

SITE_ACCOUNT_NOTE = (
    "The China site (aliyun.com) and the International site "
    "(alibabacloud.com) keep separate account systems; a client configured for "
    "the wrong site shows an empty instance list that is NOT a RAM grant "
    "problem. Switch the client to the account's own site first. (ticket "
    "T-D0578489)"
)

# ---------------------------------------------------------------------------
# K8 handoff areas: target skill/channel + real-ticket evidence + doc pointer.
# Keys match the area ids in EXCLUSION_SIGNAL_PATTERNS.
# ---------------------------------------------------------------------------
HANDOFF_TARGETS = {
    "resource-lifecycle": (
        "Billing / resource lifecycle area (human)",
        "Operations rejected by resource state are not denials; release/"
        "renewal constraints and console entry guidance apply."),
    "application-layer": ("Customer application development team",
                          "A CORS message is configured in the customer's own "
                          "web code; server-side resources are not involved."),
    "security-group": (
        "alibabacloud-ecs-vpc-publicnetwork-troubleshoot / security-group area",
        "IP/port reachability is security-group semantics; note that security "
        "groups cannot distinguish SSH key login from password login."),
    "guest-resource": ("Guest-side disk/agent troubleshooting area",
                       "Platform could not read the guest disk state; relink "
                       "the agent or release the holding process inside the OS."),
    "account-system": ("Account area (site selection)",
                       "Re-point the client at the site the account belongs to."),
    "platform-policy": ("Jushita platform console and its documentation",
                        "Managed security groups must be applied through the "
                        "platform console; ECS-console edits are inert there."),
    "billing-image": ("Billing / custom-image area",
                      "A snapshot referenced by a custom image cannot be deleted "
                      "until the image is removed; charges explanation belongs "
                      "to snapshot billing."),
    "instance-state": ("area:instance-state-diagnosis / image area",
                       "Boot failure under a new instance generation is usually "
                       "an image boot-mode (BIOS vs UEFI) problem."),
    "backup-restore": ("Backup and restore area (human)",
                       "After release, data is unrecoverable without a snapshot "
                       "or image -- a platform-mechanism limit, not a permission."),
    "account-verification": ("Account real-name verification area (human)",
                             "Complete verification first; RAM console access "
                             "depends on it."),
    "connection-method": ("Remote-connection area",
                          "Connection method / client capability, not identity."),
}

# ---------------------------------------------------------------------------
# Verified official documents (the exact URLs injected for this tier).
# ---------------------------------------------------------------------------
HELP_DOCS = {
    "ram-user-ecs-access":
        "https://help.aliyun.com/zh/ecs/user-guide/control-access-to-resources-by-using-ram-users.md",
    "ram-role-ecs-access":
        "https://help.aliyun.com/zh/ecs/user-guide/use-a-ram-role-to-control-access-to-ecs-instances.md",
    "cloud-assistant-as-regular-user":
        "https://help.aliyun.com/zh/ecs/user-guide/run-cloud-assistant-commands-as-a-regular-user.md",
    "workbench-cli-credentials":
        "https://help.aliyun.com/zh/ecs/user-guide/install-and-configure-workbench-cli-credentials.md",
    "limit-ram-user-to-instances":
        "https://help.aliyun.com/document_detail/2669110.html",
    "ram-user-faq":
        "https://help.aliyun.com/document_detail/39743.html",
    "security-group-guide":
        "https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md",
    "linux-password-connect":
        "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-1",
    "remote-connect-more":
        "https://help.aliyun.com/document_detail/71529.html",
    "mate-desktop-centos":
        "https://help.aliyun.com/document_detail/41227.html",
    "oos-alert-restart":
        "https://help.aliyun.com/zh/oos/use-cases/trigger-restarts-of-ecs-instances-with-high-cpu-utilization-based-on-alerts",
    "images-overview":
        "https://help.aliyun.com/zh/ecs/product-overview/images",
    "snapshot-create":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "snapshot-billing":
        "https://help.aliyun.com/document_detail/56159.html",
    "ram-console-users": "https://ram.console.aliyun.com/users",
    "cli-install": "https://help.aliyun.com/document_detail/121541.html",
}

DOC_FOR_BRANCH = {
    "grant-context-mismatch": ["limit-ram-user-to-instances", "ram-user-faq",
                               "ram-user-ecs-access"],
    "syntax-invalid": ["ram-user-faq"],
    "missing-action-chain": ["workbench-cli-credentials",
                             "cloud-assistant-as-regular-user"],
    "role-flow": ["ram-role-ecs-access", "oos-alert-restart"],
    "identity-planning": ["ram-user-ecs-access", "ram-user-faq"],
    "security-incident": ["security-group-guide", "snapshot-create"],
    "os-user-confusion": ["linux-password-connect", "remote-connect-more"],
    "unknown-denial": ["ram-user-faq"],
}

BRANCH_TITLES = {
    "not-permission": "Not a RAM authorization problem (exclusion signal matched)",
    "grant-context-mismatch": "Grant exists but scope x console context mismatch",
    "syntax-invalid": "Policy Action/Resource combination is invalid",
    "missing-action-chain": "Fine-grained action of another product is missing "
                            "(feature-chain gap)",
    "role-flow": "Role trust / role-grant placement problem",
    "identity-planning": "Sub-account and AccessKey least-privilege planning",
    "security-incident": "AccessKey-leak identity containment (manual-only path)",
    "os-user-confusion": "Operating-system user vs RAM user layer confusion",
    "unknown-denial": "A denial is present but classification is inconclusive",
}
