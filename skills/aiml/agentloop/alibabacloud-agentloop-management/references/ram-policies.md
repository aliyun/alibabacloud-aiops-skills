# RAM Policy Reference

> Skill-wide entry point for the RAM permissions of `alibabacloud-agentloop-management`
> (`domain: aiops`). This skill spans four domains and each one calls a different
> cloud surface, so the required actions are declared per domain. API granularity
> only - **no `*` wildcard in Action lists** anywhere in this skill.
>
> Replace `<accountId>` with the target Alibaba Cloud account ID.

## Domain Index

Read the row that matches the domain being executed. The onboarding domain's actions
are declared in this file (sections 1-5 below); the other three are declared in the
per-domain files.

| # | Domain | Cloud surface | Action prefixes | Declaration |
|---|--------|---------------|-----------------|-------------|
| 1 | Application onboarding (APM & AI observability) | CMS 2024-03-30, STS, Container Service | `cms:`, `sts:`, `cs:` | Sections 1-5 of this file |
| 2 | Evaluation | AgentLoop 2026-05-20, SLS | `agentloop:`, `log:` | [evaluation/ram-policies.md](evaluation/ram-policies.md) |
| 3 | Dataset | AgentLoop 2026-05-20 | `agentloop:` | [dataset/ram-policies.md](dataset/ram-policies.md) |
| 4 | Pipeline | AgentLoop 2026-05-20 | `agentloop:` | [pipeline/ram-policies.md](pipeline/ram-policies.md) |

Cross-domain notes:

- Do not merge all four domains into one policy by default. Grant only the domains
  the identity actually executes.
- Destructive actions are excluded from the default least-privilege templates.
  `agentloop:DeleteDataset` and the Pipeline delete/terminate actions must be
  granted deliberately and scoped to a named resource ARN where the target is known.
- Experience (recall and ContextStore) permissions are out of scope for this skill;
  they are declared by the separate `alibabacloud-agentloop-experience` skill.
- `kubectl` operations run against the cluster API server and do **not** consume
  Alibaba Cloud RAM Actions. The caller must hold valid cluster RBAC permissions
  separately.

---

## Onboarding Domain Scope

AgentLoop application onboarding uses the CMS OpenAPI (2024-03-30) via `aliyun cms2`.
Only `agentloop-{32-char-code}` workspaces are in scope.

| Cloud service | APIs used | Purpose |
|---------------|-----------|---------|
| CMS (2024-03-30) | `apm service`, `apm configuration`, `integration addon` | Initialize APM, register services, fetch addon templates |
| CMS (2024-03-30) | `entity query` | Verify resource IDs before onboarding |
| STS | `GetCallerIdentity` | Resolve AccountId for diagnostics |
| Container Service | `DescribeClusters`, `DescribeClusterUserKubeconfig`, `InstallClusterAddons` | ACK/ACS cluster discovery, kubeconfig, ack-onepilot install |

Sections 1-5 below and the minimal authorization examples at the end of this file
all belong to the onboarding domain.

---

## 1. `apm` Module (CMS 2024-03-30)

Source: AgentLoop onboarding skill - Application Service + Service Configuration - Application Service + Service Configuration.

### 1.1 Application Service (`apm service`)

| CLI subcommand | RAM Action |
|----------------|------------|
| `apm service create` | `cms:CreateService` |
| `apm service get` | `cms:GetService` |
| `apm service update` | `cms:UpdateService` |
| `apm service delete` | `cms:DeleteService` |
| `apm service list` | `cms:ListServices` |

### 1.2 Service Configuration (`apm configuration`)

| CLI subcommand | RAM Action |
|----------------|------------|
| `apm configuration get` | `cms:GetServiceObservability` |
| `apm configuration create` | `cms:CreateServiceObservability` |

---

## 2. `integration addon` Module (CMS 2024-03-30)

Used for ECS/host OpenTelemetry and AI framework addon template fetch.

| CLI subcommand | RAM Action |
|----------------|------------|
| `integration addon get` | `cms:GetAddon` + `cms:GetAddonSchema` + `cms:GetAddonCodeTemplate` |

---

## 3. `entity query` Module (CMS 2024-03-30)

| CLI subcommand | RAM Action |
|----------------|------------|
| `entity query --source=CloudResource` | `cms:GetCloudResource` + `cms:GetCloudResourceData` |

---

## 4. STS Module

| CLI subcommand | RAM Action |
|----------------|------------|
| `sts get-caller-identity` | `sts:GetCallerIdentity` |

---

## 5. Container Service Module (ACK / ACS)

| CLI subcommand | RAM Action |
|----------------|------------|
| `cs describe-clusters` | `cs:DescribeClusters` |
| `cs describe-cluster-user-kubeconfig` | `cs:DescribeClusterUserKubeconfig` |
| `cs install-cluster-addons` | `cs:InstallClusterAddons` |
| `cs un-install-cluster-addons` | `cs:UnInstallClusterAddons` |

---

## Minimal Authorization Examples (onboarding domain)

### Read-only (diagnostics / verification)

```json
{
 "Version": "1",
 "Statement": [
 {
 "Effect": "Allow",
 "Action": [
 "cms:GetService",
 "cms:ListServices",
 "cms:GetServiceObservability",
 "cms:GetAddon",
 "cms:GetAddonSchema",
 "cms:GetAddonCodeTemplate",
 "cms:GetCloudResource",
 "cms:GetCloudResourceData",
 "sts:GetCallerIdentity",
 "cs:DescribeClusters",
 "cs:DescribeClusterUserKubeconfig"
 ],
 "Resource": "acs:cms:*:<accountId>:*"
 },
 {
 "Effect": "Allow",
 "Action": [
 "sts:GetCallerIdentity"
 ],
 "Resource": "*"
 },
 {
 "Effect": "Allow",
 "Action": [
 "cs:DescribeClusters",
 "cs:DescribeClusterUserKubeconfig"
 ],
 "Resource": "*"
 }
 ]
}
```

### Onboarding / mutation (integration engineer)

Append to the read-only policy:

```json
{
 "Effect": "Allow",
 "Action": [
 "cms:CreateService",
 "cms:UpdateService",
 "cms:DeleteService",
 "cms:CreateServiceObservability",
 "cs:InstallClusterAddons",
 "cs:UnInstallClusterAddons"
 ],
 "Resource": "acs:cms:*:<accountId>:*"
}
```

> For `cs:InstallClusterAddons` / `cs:UnInstallClusterAddons`, bind
> `Resource` to the target cluster ARN when possible instead of `*`.
