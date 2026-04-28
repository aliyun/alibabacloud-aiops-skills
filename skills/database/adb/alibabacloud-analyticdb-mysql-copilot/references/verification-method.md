# Verification Methods

This document describes the success indicators for each API call and common error handling.

## Success Indicators

### Cluster Management
- `describe-db-clusters`: Returns `TotalCount` field, `Items` array contains cluster list
- `describe-db-cluster-attribute`: Returns `Items` array, `Items[0].DBClusterId` matches the input
- `describe-db-cluster-space-summary`: Returns `TotalSize`, `HotData`, `ColdData` and other fields

### Intelligent Diagnosis
- `describe-chat-message`: SSE streaming interface; returns HTTP 200 with valid SSE event stream indicates success

## Common Error Codes

| Error Code | Meaning | Solution |
|--------|------|----------|
| `InvalidDBClusterId.NotFound` | Cluster ID does not exist | Call `describe-db-clusters` to get the correct cluster ID |
| `InvalidParameter.Query` | Query parameter format error | Ensure Query contains a valid cluster ID and diagnosis question |
| `Forbidden.RAM` | Insufficient permissions | Use `ram-permission-diagnose` skill to guide user to apply for permissions |
| `InvalidAccessKeyId.NotFound` | AK does not exist | Run `aliyun configure list` to check credential status |
| `SignatureDoesNotMatch` | AK Secret error | Reconfigure credentials outside this session |
| `InvalidSecurityToken.Expired` | STS Token expired | Obtain new temporary credentials |

## Cluster ID Validation Rules

If the user-provided cluster ID does not exist in the API response (error code `InvalidDBClusterId.NotFound`), do not abort the task. Instead:
1. Call `describe-db-clusters` to list the actual clusters in that region
2. Guide the user to confirm the correct cluster ID and continue execution