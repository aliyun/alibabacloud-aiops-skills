# Error Recovery Detailed Guide

When encountering ANY error, follow these steps:
1. **Read complete error message** — Extract: ErrorCode, Message, and RequestId
2. **Identify error category** — Match against patterns below
3. **Consult documentation** — Check `api-reference.md` for correct API/parameters
4. **Apply specific fix** — Based on error category
5. **Retry with correction** — Never retry blindly without fixing the root cause

**Prohibited actions**:
- Switching to alternative APIs without understanding why the original failed
- Giving up or downgrading user's goal without exhausting recovery options
- Retrying the same failed command without modification

## Category 1: Parameter Errors

**Symptoms**: `InvalidParameter`, `MissingParameter`, `Parameter not valid`

**Root causes**:
- Wrong parameter name (e.g., `--EmrVersion` instead of `--ReleaseVersion`)
- Wrong parameter format (JSON vs flat format)
- Missing required parameters
- Invalid parameter value

**Recovery steps**:
1. Read the exact error message — note the ErrorCode and the field name mentioned in Message
2. Check exact parameter name in `api-reference.md` for that specific API
3. Verify parameter format matches API requirements (RunCluster uses JSON strings, CreateCluster and others use flat `--force` dot-notation)
4. Confirm all required parameters are present
5. Validate parameter values against API constraints
6. **Do NOT vary the same wrong parameter randomly** — if 2 attempts with the same field name both fail, the name itself is wrong; go back to docs

**Common parameter name mistakes**:

| API | Wrong | Correct | Notes |
|-----|-------|---------|-------|
| RunCluster/CreateCluster | `--EmrVersion` | `--ReleaseVersion` | Version format: "EMR-X.Y.Z" |
| RunCluster/CreateCluster | `--DeploymentMode` | `--DeployMode` | Values: NORMAL or HA |
| RunCluster/CreateCluster | `--InstanceType` | `--InstanceTypes` | Array format in NodeGroups |
| All APIs | `--VpcId` (top-level) | `--NodeAttributes.VpcId` | VPC goes in NodeAttributes |

## Category 2: API Name Errors

**Symptoms**: CLI exits with code 2 or 3, "command not found", "API does not exist"

**Common API name mistakes**:

| Wrong API | Correct API | Purpose |
|-----------|-------------|---------|
| `ListClusterVersions` | `ListReleaseVersions` | Query available EMR versions |
| `GetInstanceTypes` | `ListInstanceTypes` | Query available instance types |
| `DescribeClusters` | `ListClusters` | List clusters |

**Recovery**: Verify correct API name in `api-reference.md`.

## Category 3: Missing Required Parameters

**Symptoms**: `MissingParameter`, `MissingZoneId`, `MissingSecurityGroupId`

**Common APIs with hidden required parameters**:

**ListInstanceTypes** requires:
```bash
aliyun emr ListInstanceTypes --RegionId <region> \
  --ZoneId <zone> \              # Required: Get from DescribeVSwitches
  --ClusterType <type> \         # Required: DATALAKE/OLAP/DATAFLOW/etc.
  --PaymentType <payment> \      # Required: PayAsYouGo/Subscription
  --NodeGroupType <role>         # Required: MASTER/CORE/TASK
```

**RunCluster/CreateCluster** requires in NodeAttributes:
```bash
--NodeAttributes '{"VpcId":"...","ZoneId":"...","SecurityGroupId":"..."}'
# All three are required even if marked optional in API docs
```

## Category 4: Resource Constraints

**Symptoms**: `QuotaExceeded`, `ResourceNotEnough`, `InvalidResourceType.NotSupported`

**Recovery steps**:
1. Call `ListInstanceTypes` with correct parameters to see available types
2. Try different availability zone (use different VSwitch)
3. Check account quotas in console
4. Try alternative instance type families

## Category 5: State Conflicts

**Symptoms**: `OperationDenied.ClusterStatus`, `ConcurrentModification`

**Recovery steps**:
1. Call `GetCluster` or `GetNodeGroup` to check current state
2. Wait for state to stabilize (RUNNING)
3. Poll every 30 seconds, timeout after 15 minutes
4. Retry operation after state stabilizes

## Error Recovery Decision Tree

```
Error encountered
    ├─ Parameter error?
    │   ├─ Wrong name → Check api-reference.md, use correct name
    │   ├─ Wrong format → Switch JSON ↔ flat format based on API
    │   └─ Missing → Add required parameter (check hidden requirements)
    │
    ├─ API name error?
    │   └─ Verify correct API name in api-reference.md
    │
    ├─ Resource constraint?
    │   ├─ Zone issue → Try different zone (different VSwitch)
    │   ├─ Quota issue → Check quotas, try smaller instance type
    │   └─ Type not supported → Call ListInstanceTypes for valid types
    │
    └─ State conflict?
        └─ Wait for state transition, then retry
```

**Golden rule**: When in doubt, consult `api-reference.md` for the exact API specification.
