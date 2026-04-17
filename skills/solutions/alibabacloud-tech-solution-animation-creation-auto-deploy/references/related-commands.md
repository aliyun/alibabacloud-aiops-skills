# Related Commands: Build AI Animation Story Creation App

> Full CLI command usage and parameters are built into `SKILL.md` Core Workflow and `scripts/` scripts. The following is a quick reference index.

## Command Quick Reference

| Phase | Command/Script | Location |
|-------|---------------|----------|
| Create Bailian API Key | `source scripts/create-api-key.sh` | SKILL.md Step 1 |
| RAM policy attachment | `bash scripts/attach-policies.sh` | SKILL.md RAM Policy |
| Enable OSS | `aliyun ossadmin open-oss-service` | SKILL.md Step 2 |
| Create OSS Bucket | `aliyun oss mb` | SKILL.md Step 2 |
| Create Devs project | `aliyun devs create-project` | SKILL.md Step 3 |
| Get UID + check role | `source scripts/setup-role.sh` | SKILL.md Step 4 |
| Render template + update env | `bash scripts/render-and-update.sh` | SKILL.md Step 4a |
| Trigger deployment | `bash scripts/deploy-environment.sh` | SKILL.md Step 4b |
| Poll deployment status | `bash scripts/poll-deploy-status.sh` | SKILL.md Step 5 |
| Create custom domain | `bash scripts/create-custom-domain.sh` | SKILL.md Step 6 |
| Clean up resources | `aliyun fc delete-custom-domain` / `aliyun devs delete-project` / `aliyun oss rm` | SKILL.md Cleanup |

## Template Parameters (parameters for create-project)

| Parameter Key | Description | Value |
|---------------|-------------|-------|
| `region` | Deployment region | Fixed `cn-hangzhou` |
| `bailian_api_key` | Bailian API Key | Auto-created via `aliyun modelstudio create-api-key` in Step 1 |
| `ossBucket` | OSS Bucket name | Bucket created in Step 2 |

## Template Variables (shared parameters for render-services-by-template)

| Variable Key | Description | Value |
|-------------|-------------|-------|
| `namespace` | Function name prefix | Set to `<ProjectName>` |
| `region` | Deployment region | Fixed `cn-hangzhou` |
| `ossBucket` | OSS Bucket name | Bucket created in Step 2 |
| `bailian_api_key` | Bailian API Key | Auto-created via `aliyun modelstudio create-api-key` in Step 1 |
| `fc_role_arn` | FC function execution role | `acs:ram::<UID>:role/aliyundevscustomrole` |

## Cannot-via-CLI/SDK

| Operation | Reason | Workaround |
|-----------|--------|------------|
| First-time cloud service activation (FC) | No CLI/API support | Users activate manually in FC console |

> OSS service can be auto-activated via `aliyun ossadmin open-oss-service` (already built into SKILL.md Step 2).
> Bailian workspace is auto-created via `aliyun modelstudio create-workspace` if none exists (built into SKILL.md Step 1).

## Notes

- The OSS CLI plugin does not support the `--user-agent` flag (returns `invalid flag`) — use `--ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy` instead
- All other `aliyun` commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy`
