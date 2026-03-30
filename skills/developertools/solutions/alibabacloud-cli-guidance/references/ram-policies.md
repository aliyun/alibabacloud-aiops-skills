# RAM policies and the Aliyun CLI

Every successful `aliyun` API call is authorized as **your RAM user, RAM role, or STS session**. The CLI does not bypass RAM: if an action is denied in the console, it is denied on the command line with the same identity.

Use this note when choosing policies, interpreting errors, or guiding users who automate with the CLI.

## required_permissions

RAM permissions for **API operations illustrated** in `SKILL.md`. Use the table format below: **one row per operation**, **`Permission Required` is exactly one** `product:Action` — do not put multiple Actions in a single cell or on one table row.

These entries are **not** exhaustive for every CLI workflow. For commands not covered here, resolve Actions with `--log-level debug` and product OpenAPI / RAM docs, and authorize **on demand**.

| API Operation | Description | Permission Required |
| ------------- | ----------- | ------------------- |
| `DescribeRegions` | List regions; auth verification in skill (`aliyun ecs describe-regions`) | `ecs:DescribeRegions` |
| `DescribeInstances` | List/query ECS instances, `--cli-query`, pagination examples | `ecs:DescribeInstances` |
| `DescribeImages` | Validate image ID | `ecs:DescribeImages` |
| `DescribeVpcAttribute` | VPC attribute query and `--waiter` example | `vpc:DescribeVpcAttribute` |
| `DescribeScalingGroups` | Query ESS scaling groups in skill examples | `ess:DescribeScalingGroups` |
| `GetCallerIdentity` | Verify caller identity (e.g. OAuth verification flows) | `sts:GetCallerIdentity` |

Administrators typically use a RAM-managed system policy (for example `AliyunRAMFullAccess`) only for the consenting principal, then grant least privilege to CLI users who sign in via OAuth.

**`aliyun ess list-api-versions`**: implementation depend on CLI/plugin version and does not map to a single documented `ess:*` Action. 

**Local-only** behavior (`aliyun plugin list` for installed plugins, `aliyun <product> --help`) usually does **not** call your account’s RAM-protected APIs; `plugin install` / `plugin list-remote` need outbound network to Aliyun but often no RAM for **your** resources.

## Start from least privilege

1. Prefer **read-only** system policies or custom statements that only allow the `Describe*` / `List*` / `Get*` Actions you need.
2. Grant **write** Actions only for workflows that create, change, or delete resources.
3. Prefer **custom policies** scoped to specific resources or Actions when a system *FullAccess* policy is too broad.

## Relate policies to CLI operations

- **Product plugins** (for example `aliyun ecs`, `aliyun vpc`) map to that product’s APIs. The RAM **Action** must match the underlying API (see each product’s OpenAPI and RAM authorization topic).
- **Cross-product automation** may require multiple Actions — authorize each separately (**one `Permission Required` per row** in this file’s table; never combine multiple Actions in one cell).

When an error names a missing `Action`, add a policy statement that allows that `product:Action` (one Action per array element in JSON policy `Action`, matching one row here).

## Common error signals

Symptoms that usually mean a **RAM/policy** issue (not a wrong parameter):

- HTTP **403** or messages containing **Forbidden**, **NoPermission**, **not authorized**, **Action denied**
- Error codes such as `Forbidden.RAM`, `NoPermission`, or explicit `ACS:CheckSecurity` / missing action in the error body

Use `--log-level debug` on the CLI to see the API and error payload. Then fix the identity’s policies (user or role) in RAM, or ask an administrator to attach policies.

Authoritative policy syntax, condition keys, and the full API-to-Action mapping are maintained by Alibaba Cloud documentation and the RAM console.
