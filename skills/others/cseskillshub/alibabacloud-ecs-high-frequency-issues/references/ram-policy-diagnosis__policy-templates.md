# Paste-Ready Policy Templates & Manual Grant Procedures

Everything here is **customer-facing guidance text**: the MAIN ACCOUNT
attaches these policies manually in the RAM console. This skill has no RAM
permissions at all and never applies, edits or removes any grant — matching
ticket staff behaviour ("platform security policy does not allow staff to
operate customer accounts", ticket T-8FA544FE).

Evidence labels used below (batch traceability rule):

- **[verified]** — action name and parameter surface verified for this
  build against the OpenAPI contract; the skill's own scripts may call it.
- **[ticket-cited]** — the name was quoted inside a real support-ticket
  conversation (customer or staff paste). NOT verified against the OpenAPI
  contract;
  the skill never invokes it; treat the console's own reaction and the next
  decoded denial as the verification loop.
- **[doc]** — console procedure distilled from the official documents listed
  in `help-docs.md`.

## Grammar gates before pasting (from ticket root causes)

1. A wildcard Action entry is legal **only** with a wildcard Resource
   entry; mixing a wildcard Action with an instance-ARN Resource silently
   matches nothing and later surfaces as a denial. [ticket T-8FE09114]
2. Actions without resource-level scoping (e.g. the Workbench chat action
   below) must keep the wildcard Resource form. [ticket T-39B65627,
   ticket-cited]
3. One console feature is often a multi-product chain — grant the whole
   chain, not the product in the page URL. [ticket T-296B2D19]
4. Any `Effect: "Deny"` attached to the identity (directly, via a group, or
   via the role it assumes) overrides every Allow. Audit before re-granting.
   [ticket T-EE03C367 staff advice]
5. API name != RAM action name for some products (Cloud Monitor's
   `DescribeMetricLast` is authorized as `cms:QueryMetricLast`; billing
   prefixes are `bss` / `bssapi`, not the CLI product name `bssopenapi`).
   Never derive a grant name from a call name. [batch rule]

## Scope model — choose before granting (cluster A)

| Scope | Grant location | Visibility rule | When to pick |
|---|---|---|---|
| Account | RAM user (or role) + account-level grant | everything in the account, every console context | shared operations staff, tooling |
| Resource group | grant pinned to a resource group | visible ONLY while the console context (web switcher; **mobile app: tap "All Resources" top-left and pick the group**) is on that group | "share only a few servers" (the exact trade-off conversation in ticket T-EE03C367) |
| Tag condition | custom policy conditioned on tags | many ECS actions support tag conditions; the exact condition grammar is **not verified for this build** (official policy-syntax doc pending) | design option — verify the grammar in the official syntax doc before pasting |

## Manual grant procedure (cluster A/C/D, [doc] + ticket evidence)

1. Main account signs in at `https://ram.console.aliyun.com/users` (the
   entry staff pasted in tickets T-169ADF41 / T-2B09C359).
2. Open the target RAM user (login shape `<name>@<account>.onaliyun.com`) →
   **Permissions** tab → **Add Permissions**.
3. When searching for a system policy such as `AliyunECSFullAccess`, switch
   to the **System Policies** tab first — "the policy cannot be found" is a
   real console-picker trap (ticket T-0217BF77).
4. Pick the Resource Scope (table above). Confirm.
5. Have the sub-account sign out and back in, then re-test; if scoped, set
   the console/mobile context to the same resource group first.
6. Still denied after an account-level grant? Audit every attached custom
   policy for `Deny` statements (gate 4), then re-check syntax gates 1–2.

## Template t1 — view ECS instances only [verified]

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstances"],
      "Resource": "*"
    }
  ]
}
```

Minimum grant for "sub-account should see/manage the instance list".

## Template t3 — ECS Workbench chat permission [ticket-cited]

Denial shape: repeated "no permission" toasts inside ECS Workbench; staff
identified the missing action as `ecs-workbench:ChatMessages` (ticket
T-39B65627). The customer also could not find the suggested system policy
`AliyunECSWorkbenchFullAccess` in the picker, so the custom policy is the
practical route:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecs-workbench:ChatMessages"],
      "Resource": "*"
    }
  ]
}
```

Gate 2 applies: this action reportedly cannot be narrowed to instances —
keeping `Resource: "*"` is required for the grant to ever match.

## Template t4 — Workbench web-VSCode install chain [ticket-cited]

Denial shape: `User has no permission to do the action:
(ListExecutionRiskyTasks)` while installing web VSCode from Workbench. The
install runs through OOS package management (NOT OSS); the customer pasted
back the working policy shape in ticket T-296B2D19, which this template
reproduces (names as pasted, written in the platform-required
lowercase-hyphenated action spelling; `Resource: "*"` because the flow
spans several services):

```json
{
  "Version": "1",
  "Statement": [
    {
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
        "bss:DescribeOrderDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- The install flow may surface one further package-state action of `Update`
  form on later denials (it was in the ticket paste). This build deliberately
  does not pre-fill action names it cannot verify: when the next denial
  appears, decode it (`--error-text`) and add exactly the named action.
- Why a billing action (`bss:DescribeOrderDetail`) and an OSS read
  (`oss:GetObject`) are in the chain: the flow reads the order and fetches
  the package object. Staff had to explain this to the customer across
  three rounds; pre-empt it when relaying the template.

## Template t5 — create instances with an existing VSwitch (cluster A/B edge)

Denial shape: 403 on `RunInstances` ("not authorized on the specified
resource or the API does not support RAM", ticket T-8FE09114). Root causes
there were gate 1 (wildcard Action with narrowed Resource) and a missing
VPC-side dependency — a reused VSwitch still needs explicit VPC/VSwitch
read actions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecs:run-instances", "ecs:DescribeInstances"],
      "Resource": "*"
    }
  ]
}
```

The VPC-side action names are **not verified for this build**: decode the
concrete denial naming them (or attach a VPC read grant manually chosen in
the console) instead of guessing names.

## Template t6 — view-only AccessKey for instance inventory (cluster C)

Customer need shape (ticket T-2D30AEF6): "a sub-account AccessKey that can
list all cloud hosts, their cost and expiry" — the online session escalated
this to an offline engineer; standardized answer with verified names:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity", "ecs:DescribeInstances"],
      "Resource": "*"
    }
  ]
}
```

Declare the gap honestly: **cost / expiry columns come from billing (BSS)
APIs whose RAM names are not verified for this build** — that slice is a
documented handoff to the billing area (see `ticket-patterns.md`), not a
guessed grant. Attach the policy to the RAM user owning the AccessKey; a
key created under a role is judged by the role's grants.

## Role flow (cluster D, [doc] + ticket T-0217BF77)

For OOS-driven automation (e.g. auto-reboot on a high-CPU alert):

1. RAM console → **Roles** → create role: Trusted Entity type = **Cloud
   Service**; Trusted service = the operation-orchestration (OOS) entry.
2. Open the created role (e.g. `OOSServiceRole`) → **Add Permissions** on
   the ROLE (grant-to-role, not grant-to-user) → attach
   `AliyunECSFullAccess` (staff route) or a narrower custom policy (t6) per
   the least-privilege principle.
3. Continue the scenario's documented steps (URL in `help-docs.md`,
   `oos-alert-restart`).

Service-linked roles (`AliyunServiceRoleFor*` shape): removable only by the
customer self-service, after the linked service no longer needs them and
with account real-name verification completed; nobody — staff or this skill
— deletes them on the customer's behalf (ticket T-8FA544FE).

## AccessKey-leak identity containment (security overlay, manual-only)

When a leaked AccessKey / rogue sub-identity is suspected (ticket
T-E55C752C pattern): this skill only prints the steps — main account
**disables** (not deletes, so evidence survives review) leaked/unknown
AccessKeys, inventories RAM users and keys created in the incident window,
rotates needed keys onto least-privilege policies (t6), re-checks instance
security groups for world-open ports, and takes a snapshot before any guest
cleanup. Nothing here is executed automatically.
