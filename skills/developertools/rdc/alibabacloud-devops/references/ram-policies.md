# Yunxiao Permission Model vs. Standard Alibaba Cloud RAM

Yunxiao (DevOps) uses a **separate** authentication and authorization system from other Alibaba Cloud services. This document clarifies the differences.

## Key Differences

| Dimension | Standard Alibaba Cloud Services | Yunxiao DevOps |
|-----------|--------------------------------|----------------|
| Identity | RAM User / RAM Role (AK/SK, STS Token) | Yunxiao Personal Access Token (PAT) |
| Authorization model | RAM Policy (Action + Resource ARN) | Token Scope + Resource Membership |
| Credential format | AccessKeyId + AccessKeySecret | Bearer Token (`pt-xxx`) |
| Policy language | RAM JSON policy (`Allow`/`Deny` on `acs:ecs:*:*:*`) | Scope checkboxes per product (e.g., "Code Management Read/Write") |
| Granularity | Action-level (`ecs:DescribeInstances`) | Product-level scope + resource-level membership role |
| API endpoint | Regional endpoints (e.g., `ecs.cn-hangzhou.aliyuncs.com`) | Unified `openapi-rdc.aliyuncs.com` (Central) or `{org}-{region}.devops.aliyuncs.com` (Regional) |
| CLI auth mode | AK / STS / RamRoleArn | Personal Access Token via `--yunxiao-access-token` or `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` env var |

## Yunxiao Permission Layers

Yunxiao enforces permissions at **two layers**:

### Layer 1: Token Scope (Product-Level)

When creating a Personal Access Token, the user selects which product scopes to enable:

| Scope | Covers |
|-------|--------|
| Organization Management (Read/Write) | `base`, `organization-management` toolsets |
| Code Management (Read/Write) | `code-management` toolset |
| Pipeline (Read/Write) | `pipeline-management` toolset |
| Packages (Read/Write) | `packages-management` toolset |
| Project Collaboration (Read/Write) | `project-management` toolset |
| Test Management (Read/Write) | `test-management` toolset |
| Application Delivery (Read/Write) | `application-delivery` toolset |

Missing scope -> `403 Insufficient Permissions`.

### Layer 2: Resource Membership (Resource-Level)

Even with the correct token scope, the user must have appropriate **membership roles** on specific resources:

| Product | Resource | Roles |
|---------|----------|-------|
| Codeup | Repository | Reporter / Developer / Master / Owner |
| Flow | Pipeline / Pipeline Group | Read / Read-Write |
| Projex | Project | Member (Owner / Admin / Member) |
| AppStack | Application | Owner / Operator / Member |
| Testhub | Test Repository | Project member with test permissions |

Missing membership -> `403` even if token scope is sufficient.

## What Yunxiao Does NOT Use

- **RAM Policies**: Yunxiao API calls are **not** governed by RAM policy documents (`acs:devops:*` actions do not exist). Attaching RAM policies to a RAM user has no effect on Yunxiao API access.
- **AK/SK Authentication**: The `aliyun devops` CLI uses Personal Access Token (`--yunxiao-access-token` or `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` env var), not the standard AK/SK mode. Standard Alibaba Cloud credentials (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`) are not used.
- **STS Tokens**: Yunxiao does not support temporary STS credentials.
- **Resource ARNs**: Yunxiao resources are identified by product-specific IDs (e.g., `organizationId`, `repositoryId`, `pipelineId`), not by Alibaba Cloud Resource Names (ARNs).

## Troubleshooting Permission Errors

| Error | Likely cause | Resolution |
|-------|-------------|------------|
| 401 Unauthenticated | Token expired, revoked, or not configured | Re-generate PAT, update `YUNXIAO_ACCESS_TOKEN` |
| 403 on a toolset | Token scope missing for that product | Edit PAT, enable the required product scope |
| 403 on a specific resource | User lacks membership role on that resource | Ask org admin to grant appropriate role |
| "AK/SK invalid" | Used standard Alibaba Cloud credentials instead of PAT | Switch to Personal Access Token mode (see aliyun-cli-setup.md) |

## Summary

When encountering permission issues with Yunxiao APIs, **do not** attempt to resolve them via RAM policies or AK/SK credentials. Instead:
1. Check token scope (verify the token has the required product scope enabled)
2. Check resource membership role
3. Re-generate the Personal Access Token if needed
