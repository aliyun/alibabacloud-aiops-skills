# RAM policies and workspace authorization

Verified against official documentation on **2026-09-18**. Read this before onboarding a RAM identity, provisioning resources, or diagnosing access failures. This skill does not attach policies or change membership automatically.

## Three authorization layers

1. **RAM identity permissions** govern the Alibaba Cloud user's or role's access to Bailian administration and documented RAM-authorized APIs.
2. **Bailian workspace membership and permissions** are separate from RAM policy attachments. A product policy does not itself add a user to a workspace. See [Bailian permission management](https://help.aliyun.com/zh/model-studio/permission-management-overview).
3. **MA runtime authentication** uses `Authorization: Bearer <API_KEY>` at `https://{workspace_id}.{region}.maas.aliyuncs.com/api/v1/agentstudio`. The [MA authentication contract](https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/introduction.md) states that a key can access all resources in its owning workspace. Use a matching key, workspace, and region. Do not substitute a RAM AccessKey ID/secret for this bearer credential.

A successful MA call proves access for that key and operation, not the minimum RAM policy of its owner. In particular, attaching a read-only RAM policy must not be presented as making an existing MA bearer key read-only. Use separate workspaces and application-side authorization when stronger isolation is required.

## Published RAM policies: select by administrative task

These are **general Bailian policies**, not a verified per-endpoint MA least-privilege matrix. Check current policy definitions before attachment.

| Task | Published policy | Scope and limits |
| --- | --- | --- |
| Bailian data administration | `AliyunBailianDataFullAccess` | Broad data permissions; no workspace/key administration. Does not replace workspace membership. |
| Inspect Bailian data | `AliyunBailianDataReadOnlyAccess` | A candidate for inspection under the published policy; not a guarantee of read-only MA bearer-key access. |
| Manage workspaces, accounts, and API keys | `AliyunBailianControlFullAccess` | Control-plane administration; does not alone grant data permissions or first-time feature activation. |
| First-time model-call activation or full Bailian administration | `AliyunBailianFullAccess` | Broad administrator scope. Use only when this administrative task requires it, not as the default runtime prerequisite. |

Policy purposes and activation requirements: [Bailian RAM permissions](https://help.aliyun.com/zh/model-studio/bailian-ram-permission). An administrator handles grants; the runtime does not need `AdministratorAccess` or `AliyunRAMFullAccess` merely to execute this skill.

The published [AliyunBailianDataFullAccess policy](https://help.aliyun.com/zh/ram/developer-reference/aliyunbailiandatafullaccess) currently allows `bailiandata:*` and `sfm:*`, plus `ram:ListUserBasicInfos` and `ram:ListRoles`, with `Resource: "*"`. This is a broad system policy, **not** a minimal custom policy or a workspace-scoped grant. Prefer referencing the managed policy by name over copying its wildcard statements into an allegedly minimal template.

The published [AliyunBailianDataReadOnlyAccess policy](https://help.aliyun.com/zh/ram/developer-reference/aliyunbailiandatareadonlyaccess) includes read prefixes and also `sfm:CreateSession` / `sfm:AbortGenerateAnswer` for model experience. Its name does not mean every permitted action is a GET, and these names do not establish an authorization mapping for MA `/sessions`.

## Permissions needed by this skill's workflows

| Workflow | Required access in the selected MA workspace |
| --- | --- |
| Inspect or troubleshoot | List/get relevant resources; read event history and streams; retrieve selected artifacts |
| Provision or update | Create/update Agent, Environment, and requested related resources; read versions and readiness |
| Execute tasks | Create Session; send/read Events; use configured tools and any selected external credentials |
| Working memory and files | Upload/read files; attach/detach supported resources; read/write the selected Memory Store according to its mount access |
| Deployment and notifications | Manage/run/pause the selected Deployment; manage the requested Webhook endpoint and delivery records |
| Cleanup | Archive/delete only the resources in the authorized cleanup scope |

These are operational access requirements, **not RAM Action identifiers**. The reviewed MA documentation does not provide a verified Action/Resource mapping for every endpoint. Do not invent `sfm:CreateAgent`, `bailiandata:CreateMemoryStore`, or resource ARNs from URL names. The separately documented `sfm:CreateMemory` family belongs to Bailian long-term memory; it is not evidence of MA Memory Store authorization.

If a customer requires a custom least-privilege RAM policy, obtain the current MA-specific action names, supported resource scopes, and conditions from the official authorization reference or product support, then validate both allowed and denied operations using a dedicated RAM identity. Do not claim such a policy has been verified by this repository's existing API-key smoke tests.

## Optional external services and failure checks

MA-hosted environments and Vaults do not by themselves justify granting ECS, OSS, KMS, or RAM administration to the caller. Add a separate service policy only when a configured tool actually calls that service, scoped to its documented actions and resources. Third-party MCP services have their own credentials and activation requirements. A tool's approval policy and a Memory Store's `read_only` mount are runtime controls, not substitutes for caller authorization.

For access failures, check the selected key/endpoint pair, account activation, target region, workspace membership, and the exact denied action if one is returned. Retain the request ID without logging credentials. Do not resolve every 401/403 by attaching FullAccess: an invalid key or mismatched workspace is not fixed by a broader policy. Verify with a read-only call first; conduct a mutation probe only within the user's authorized test scope.
