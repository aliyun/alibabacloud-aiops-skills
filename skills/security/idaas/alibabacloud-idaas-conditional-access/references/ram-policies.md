# Required permissions

Grant only the actions needed by the flow being run. This is an operation
inventory, not a ready-to-attach administrator policy. Resolve the exact
resource ARNs against the deployed API authorization metadata and narrow the
region, account, and instance segments to the approved plan. Resource
wildcards needed by a list or create API do not justify wildcard Actions.

## EIAM: policy discovery and read-back

`eiam:ListConditionalAccessPolicies` — Discover conditional access policies
for audits, hit preview, quota/priority checks, and the pre-write re-check,
across all pages. Authorizes against
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/conditionalaccesspolicy/*`.

`eiam:GetConditionalAccessPolicy` — Read back one policy after a write and
compare it against the plan. Authorizes against the per-policy ARN
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/conditionalaccesspolicy/{#ConditionalAccessPolicyId}`.

## EIAM: entity resolution (read-only)

`eiam:ListApplications` — Resolve application names to IDs and detect
non-configurable system applications (only the portal `iap_user_portal` is a
valid conditional access target). Authorizes against
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/application/*`.

`eiam:ListGroups` — Resolve group names to IDs for include/exclude subject
conditions. Authorizes against
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/group/*`.

`eiam:ListUsers` — Resolve usernames to IDs for include/exclude subject
conditions (for example portal policy ExcludeUsers). Authorizes against
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/user/*`.

## EIAM: network zones (discovery only)

`eiam:ListNetworkZones` — Resolve network zone names to IDs and list
existing candidates when a reference is missing. Authorizes against
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/networkzone/*`.
This skill never creates, modifies, or deletes network zones; no zone write
permissions are requested.

## Policy writes

`eiam:CreateConditionalAccessPolicy` — Create a planned policy (SDK
transport, object parameters). Authorizes against the collection ARN
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/conditionalaccesspolicy/*`.

`eiam:UpdateConditionalAccessPolicy` — Apply an approved modification (SDK
transport). `eiam:EnableConditionalAccessPolicy` — Compensating enable after
creation and enable state operations. `eiam:DisableConditionalAccessPolicy`
— First stage of delete flows and disable state operations.
`eiam:DeleteConditionalAccessPolicy` — Final stage of delete flows, only on
policies bound in the approved plan. These four authorize against the
per-policy ARN
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/conditionalaccesspolicy/{#ConditionalAccessPolicyId}`.

A single collection-scoped grant on
`acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/conditionalaccesspolicy/*`
therefore covers this skill's whole policy lifecycle (create, list, get,
update, enable, disable, delete); nothing broader is needed.

## SDK transport identity check

`sts:GetCallerIdentity` — Called once through each transport (CLI and SDK)
before any policy write: writes proceed only when the SDK credential account
matches the eiam-profile account; on mismatch, zero writes. The public STS
reference exposes no authorization table for this operation, and it takes no
request parameters. If a restrictive profile policy denies it, grant
`sts:GetCallerIdentity` on `*`; never skip the check because it was denied.

## Unsupported operations

No network zone writes (create/update/delete zones), no application, group,
user, or organizational unit mutations, and no default-policy global MFA
settings — zone and entity operations are read-only discovery in this skill.
No wildcard Actions anywhere. A denied action is never evidence that the
resource does not exist: a denied List does not imply there are no policies.
When a scoped action is denied, do not fall back to an administrator
profile — report the missing permission and stop.
