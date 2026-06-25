# Execution Standards

This document defines mandatory execution standards for the VPC firewall diagnosis skill.

## Read-only Declaration

Every diagnostic report must start with:

```text
Notice: This tool is a read-only diagnostic assistant. It only provides analysis and configuration guidance and will not perform any configuration changes.
Please apply all configuration changes manually in the Alibaba Cloud Console or through your own approved process.
```

## Required User Inputs

Collect all required information in one interaction:

1. CLI profile name.
2. Region ID.
3. CEN instance ID.
4. Problem type: creation failure, route policy configuration failure, or closure pre-check.
5. Cross-region scope if applicable.

Do not run diagnosis until the inputs are confirmed.

## CLI Standards

- Enable CLI AI-Mode before the diagnostic workflow: `aliyun configure ai-mode enable`.
- Set the skill User-Agent for AI-Mode: `aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis`.
- Run plugin update before service API calls as a local/system command: `aliyun plugin update`. Do not add the User-Agent flag to this command.
- Disable CLI AI-Mode after the workflow: `aliyun configure ai-mode disable`.
- Use Alibaba Cloud CLI plugin mode with lowercase-hyphenated actions.
- Use `--profile <profile>` for every Alibaba Cloud CLI command.
- Include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis` for every Alibaba Cloud service call.
- Do not add the User-Agent flag to local/system commands such as `aliyun version`, `aliyun configure list`, `aliyun configure ai-mode enable/disable`, or `aliyun plugin update`.
- Use `--Region` for `describe-vpc-firewall-precheck-detail`.
- Use `--LookupAttribute.1.Key` dot notation for ActionTrail.
- Do not add `--TransitRouterId` to `list-transit-router-route-entries`.

## Closure Pre-check Rules

- Never compare route entries manually in prose only.
- Save route table JSON outputs before analysis.
- Run `scripts/analyze_routes.py` for route comparison.
- Do not infer safety from `TotalCount` alone.
- Include both route risk and ACL risk in the final report.

Example route-entry query:

```bash
aliyun cbn list-transit-router-route-entries \
  --TransitRouterRouteTableId <route-table-id> \
  --MaxResults 100 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

## ActionTrail Rules

- Default query window is the last 24 hours.
- Use the user's provided time range only when explicitly requested.
- Use ActionTrail for operation timeline and failure evidence.
- Use OpenAPI read-only queries for current state.
- Treat `ErrorDetail` and recent ActionTrail evidence as stronger than precheck-only results.

## Output Rules

- Put the conclusion first.
- Keep evidence concise.
- Do not expose unnecessary resource inventories.
- Do not provide executable write commands.
- Provide remediation as text-only console guidance or parameter checklist.
