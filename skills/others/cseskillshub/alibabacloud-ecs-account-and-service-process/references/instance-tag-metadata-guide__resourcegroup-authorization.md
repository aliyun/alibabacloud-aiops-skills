# Resource-group ownership and authorization rules

Scope: why an authorized resource group does not automatically show its
resources, and how to read the denial wording that comes back when scope and
identity do not line up. Everything here is read-only guidance: this module
explains what to check and what the customer has to do; it never performs the
change.

Evidence labels: `api:` = verified against the live read API; `ticket:` = taken
from a support conversation that was read in full; `summary:` = taken from a
ticket summary whose conversation was NOT re-pulled, so treat it as reported,
not verified. Rule wording cross-checked **2026-08**; response shapes
live-verified **2026-09-18**. Documentation statements change with product
versions -- re-check the linked page before quoting a rule.

## 1. Three different questions that look like one

| Customer says | Actually being asked | Answerable read-only? |
|---|---|---|
| "I authorized the resource group to the RAM user but the user still cannot see the instance" | is the instance really in that group | yes -- `DescribeInstances` returns the group id |
| "...the user still cannot see it, and the group id is correct" | is the console sitting on another group / region / URL filter | no -- console and browser session state is invisible to every API; it is a customer-side check |
| "the call is denied with `ImplicitDeny`" | which scope the failing call was issued against | partly -- the code says a resource-group identity policy denied it; the policy document itself must come from the customer |

## 2. Ownership facts: what the API returns

- Each instance record carries a resource group id. **An instance that lives in
  the account's default group returns an EMPTY group id, not a placeholder id**
  (`api:DescribeInstances`, live-verified). Reading that empty value as "no
  group was set" is correct; reading it as "the query failed" is not.
- Filters are conjunctive and silent: a request filtered by a group id that no
  instance in that region carries returns an empty list with no error
  (`api:DescribeInstances`). So "empty" never proves "does not exist" -- it only
  proves "nothing matched in this region under these filters".
- Because of that, when instance ids are supplied this skill sends the id
  filter only and compares the group locally. Filtering by both id and group
  server-side would collapse "exists elsewhere" and "does not exist" into the
  same empty answer.
- Cross-region is a real failure mode: an instance created in another region
  never appears in the region being listed (`summary:0001FS10GN`). Query the
  candidate regions with repeated `--region`.

## 3. Decision tree: "instance not visible in the group I authorized"

1. Read the instance by id across the regions the customer might have used:
   `--region <a> --region <b> --instance-id <id>`.
2. If a record comes back:
   - group id equals the authorized group -> the grant matches the object. The
     remaining cause is console-side: the resource-group selector in the top-left
     of the console must be switched to the authorized group, and a
     `ResourceGroupId` parameter left in the address bar keeps re-applying an old
     filter (`ticket:000DGRKP59` closed exactly here; `summary:000ACRDL92`
     reports the URL-parameter variant).
   - group id differs -> the instance was never moved; state the actual group and
     let the customer regroup it themselves.
   - group id is empty -> the instance is in the default group; a group-scoped
     grant will never make it appear in another group's list.
3. If nothing comes back in any queried region: say what cannot be distinguished
   (other region, other account, or not visible to this credential) and ask for
   the missing fact. Do not conclude the instance is gone.

## 4. Authorization wording: how to read a denial

| Reported wording | Reading | Next step for the customer |
|---|---|---|
| `NoPermissionType: ImplicitDeny` + `PolicyType: ResourceGroupLevelIdentityBasedPolicy` | the identity has no allow for that action **inside that resource group**; an account-level Allow on the same identity does not rescue a group-scoped call (`ticket:000FLRZSHR`, agent's written conclusion) | attach the action at that group's scope; for instance creation, keep the VPC, vSwitch and security group in the same group; cost-related actions are account-scope only |
| A named missing permission point for a console listing call, e.g. `ecs:ListTagResources` | some console calls are issued WITHOUT a group, so a group-scoped grant cannot satisfy them; the error does not mean the intended operation is blocked. Security Center and CloudMonitor console calls behave the same way (`ticket:000CTRT3JT`) | two documented options: ignore the message and verify the operation itself, or grant exactly that action at account scope in its own policy |
| Denial while the policy contains a Condition such as `ecs:NotSpecifySecurityGroupId` | a Condition the request does not satisfy produces an implicit deny even when the action is allowed (`summary:000BSRMYZW`) | review or remove the Condition block; this skill does not edit policies |
| A create that references another resource (a security group inside a VPC) fails, and the referenced resource is not in the selected group | cross-resource association is bounded by the group; the reported case was NOT closed online, so this is a hand-off candidate rather than a rule (`ticket:0001ZS57G6`) | confirm which group holds the referenced resource; escalate if the group is correct and the call still fails |

Never diagnose from a screenshot alone: ask for the action name, the request id
and the policy attachment scope (account or which group). Those three facts are
what made the conversation-backed cases resolvable.

## 5. What this skill will not do

- It does not read RAM policy documents, group membership or where a grant is
  attached, and it cannot reverse a request id into a decision trace. Those need
  the customer's paste or a human-side lookup through a support ticket.
- It does not move instances between groups, tag them, or attach a policy -- not
  even "one command for the customer to run". It states the console path, then
  re-reads the facts to confirm the customer's change landed.
- It does not treat "the account has an Allow" as "every scope can act" (the
  single most common misconception in this tier), and it does not treat "this
  console call errored" as "the operation is impossible".

## 6. Verified documentation

- Grant a RAM identity permissions at resource-group scope:
  <https://help.aliyun.com/zh/resource-management/resource-group/user-guide/add-ram-authorization>
- Use a resource group to let a RAM user manage only certain ECS instances:
  <https://help.aliyun.com/zh/ram/use-cases/use-a-resource-group-to-manage-an-ecs-instance>
- Separate ECS RAM permissions by responsibility:
  <https://help.aliyun.com/zh/ecs/user-guide/avoid-using-the-main-account-to-grant-different-permissions-to-members-of-the-sub-account-with-different-responsibilities.md>
- ECS feature catalogue (whether a feature exists at group scope at all):
  <https://help.aliyun.com/zh/ecs/user-guide/product-function-custom-node-ecs-normal.md>

No verified URL exists in this skill's evidence set for the action-by-action
list of which ECS actions support resource-group-level authorization. Where a
per-action answer matters, quote the two documents above plus the current
official authorization table for the action in question, and record the date it
was checked: in the source conversation the customer cited a document saying one
thing and the agent's conclusion said another, so do not present such a list as
settled fact from this module alone.
