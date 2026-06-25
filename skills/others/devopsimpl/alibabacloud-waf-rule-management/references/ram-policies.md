# RAM Permission Statement

> Minimum RAM permission list required for this Skill to perform operations.
> 
> Follows [§1.1 Minimum Permission Definition](../specs/agent-skills-spec-main-ee9b3dbbae2ddd938e5043ae9db7c6096f3a95ca/01-security/01-least-privilege.md): Declare item by item, no wildcards, read-only operations do not declare write permissions.

---

## Required Permissions

### STS Service

`sts:GetCallerIdentity` — Obtain AccountId for deriving SLS Project name

### WAF Service (Read-Only)

`waf-openapi:DescribeInstance` — Query WAF instance information to get instance ID

`waf-openapi:DescribeDefenseResourceTemplates` — Query protection templates bound to protection objects

`waf-openapi:DescribeDefenseTemplate` — Query template details and binding count

`waf-openapi:DescribeDefenseRules` — Query existing rule configurations

### SLS Log Service (Read-Only)

`log:GetLog` — Query WAF interception logs (resource scope: `acs:log:*:*:project/wafnew-project-*/logstore/wafnew-logstore`)

---

## Recommended System Policies

For quick user configuration, the following system policies can be used:

- `AliyunLogReadOnlyAccess` — SLS read-only permissions
- Custom policy: Contains the above WAF and STS read-only permissions

---

## Permission Configuration Instructions

**This Skill is a pure read-only diagnostic tool**, does not involve any write operations:
- ❌ Does NOT create/modify/delete WAF rules
- ❌ Does NOT deploy configuration changes to WAF instances
- ✅ Only queries rule configurations, traffic logs, instance information

If users need to configure rules, please complete manually in Alibaba Cloud Console.

---

## Permission Minimization Suggestions

1. **Only grant read-only permissions**: This Skill only requires read permissions, should NOT grant any write permissions
2. **Production environment**: Recommend using custom policies, precisely restricted to specific instance IDs and Regions
3. **Regular audits**: Check RAM permission usage to ensure minimum permission principles are followed
