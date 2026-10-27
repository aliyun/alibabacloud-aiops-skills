# Acceptance Criteria: alibabacloud-cen-redundancy-route-check

**Scenario**: Down-cloud redundancy route check for IDC connected to VPC through CEN dedicated lines/VPN.
**Purpose**: Skill testing acceptance criteria

## 1. CLI Product and Commands

### ✅ CORRECT

```bash
aliyun cbn list-transit-routers --cen-id "$CEN_ID"
aliyun vpc describe-route-entry-list --biz-region-id "$REGION_ID" --route-table-id "$ROUTE_TABLE_ID"
```

Uses plugin-mode product names and lowercase kebab-case commands.

### ❌ INCORRECT

```bash
aliyun Cbn ListTransitRouters --CenId "$CEN_ID"
aliyun vpc describe-routes --route-table "$ROUTE_TABLE_ID"
```

Traditional API-style commands and non-existent plugin commands do not meet the requirements.

### ✅ CORRECT

Each cloud API call is one standalone command with literal values substituted, e.g. `aliyun cbn list-transit-routers --cen-id cen-abc123 --page-size 50`.

### ❌ INCORRECT

Shell loops, variables, scripts, or chained commands that batch several cloud API calls, or skipping a mandatory checklist step (for example one Attachment type or `describe-route-conflict`).

## 2. User Parameters

### ✅ CORRECT

Confirm the CEN/VBR ID, region, IDC CIDR, expected mode, and profile before execution.

### ❌ INCORRECT

Defaulting to `cn-hangzhou`, guessing the IDC CIDR, or treating the example `cen-xxx` as a real parameter.

## 3. Credentials

### ✅ CORRECT

```bash
aliyun configure list
```

Only confirms whether a valid profile exists.

### ❌ INCORRECT

```bash
echo "$ALIBABA_CLOUD_ACCESS_KEY_SECRET"
aliyun configure set --access-key-id '<literal-ak>' --access-key-secret '<literal-secret>'
```

Reading or printing AK/SK, or asking the user to provide them in the session, is forbidden.

## 4. Observability

### ✅ CORRECT

- Read the version from this skill's version manifest as instructed in SKILL.md.
- Generate a fresh 32-character lowercase hexadecimal session ID per conversation.
- Append the correct `--user-agent` to every cloud API command.

### ❌ INCORRECT

- Sending the literal `{session-id}`.
- Reusing a session ID from another skill or a previous conversation.
- Using the deprecated global AI mode configuration or the UA environment-variable approach.

## 5. Pagination and Empty Results

### ✅ CORRECT

Traverse all PageNumber/NextToken pages and deduplicate by resource ID; before accepting an empty result, verify permissions, region, filters, and pagination.

### ❌ INCORRECT

Querying only the first page, or interpreting an empty list caused by a permission failure as "no routes, redundancy healthy".

## 6. Redundancy Verdict

### ✅ CORRECT

Inspect Active, Standby, Candidate, Rejected, and Prohibited routes together, and cross-validate on both the TR/CEN side and the VPC side.

### ❌ INCORRECT

Concluding active/standby is complete after seeing a single Active primary route, or judging a path usable merely because an Attachment exists.

## 7. PBR Boundary

### ✅ CORRECT

When query results cannot prove PBR conditions such as source address, protocol, port, and failover behavior, output "Manual confirmation required".

### ❌ INCORRECT

Reporting "No PBR found" merely because `DescribeRouteEntryList` returned no policy conditions.

## 8. Error Handling

### ✅ CORRECT

Record the product, Action, region, resource, error code, and RequestId, and mark the affected scope as "Unable to confirm".

### ❌ INCORRECT

Swallowing errors and still reporting "All healthy", or recording credential content in the report.
