# VPC Firewall Complete API Reference

## CloudFirewall Service (cloudfw)

### Precheck APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `CreateVpcFirewallPrecheck` | `--VpcId`, `--RegionId` | - | RegionId is the VPC's region |
| `DescribeVpcFirewallPrecheckDetail` | `--VpcId`, `--Region` | - | **Note: --Region, NOT --RegionId or --RegionNo** |

### Firewall Management APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `DescribeTrFirewallsV2List` | `--RegionId` | - | Get VPC firewall list and precheck status |
| `DescribeTrFirewallsV2Detail` | `--FirewallId` | `--Lang` | Get VPC firewall details |
| `DescribeFirewallTask` | - | `--TaskType`, `--TaskId`, `--ChildInstanceId` | **First choice for drainage failure diagnosis**. TaskType=VPC for VPC firewall tasks. Can pass ChildInstanceId (VPC instance ID) to query drainage task status and failure reason |
| `ModifyVpcFirewallDefaultIPSConfig` | `--FirewallId`, `--RegionId` | - | - |
| `ModifyVpcFirewallAclEngineMode` | `--FirewallId`, `--RegionId` | - | - |

### Route Policy APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `CreateTrFirewallV2RoutePolicy` | `--FirewallId`, `--RegionId`, `--PolicyType`, `--SrcCandidateList` | `--PolicyName`, `--PolicyDescription` | Create new drainage strategy |
| `ModifyTrFirewallV2RoutePolicyScope` | `--FirewallId`, `--RegionId`, `--TrFirewallRoutePolicyId`, `--SrcCandidateList` | `--PolicyName`, `--PolicyDescription`, `--delCandidateList` | Add/modify network elements in existing drainage strategy |
| `DescribeTrFirewallV2RoutePolicyList` | `--FirewallId`, `--RegionId` | - | Get TR firewall route policy list |

### Other Query APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `DescribeVpcFirewallList` | `--RegionId` | - | Query VPC boundary firewall list |
| `DescribeVpcFirewallAccessDetail` | `--VpcId`, `--StartTime`, `--EndTime` | - | Get VPC firewall access details (timestamps in seconds) |
| `DescribeVpcFirewallCenDetail` | `--VpcFirewallId` | - | Query VPC boundary firewall CEN details |
| `DescribeVpcFirewallSummaryInfo` | - | - | Get VPC firewall summary info (no region parameter needed) |

---

## CBN Transit Router Service (cbn)

### CEN APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `DescribeCens` | - | - | **Does NOT support --CenId parameter** |
| `DescribeCenAttachedChildInstances` | `--CenId` | - | Get CEN attached child instances |
| `DescribeCenRouteMaps` | `--CenId`, `--CenRegionId` | `--PageNumber`, `--PageSize` | Query CEN route maps (Route Map), for consistency check diagnosis |

### Transit Router Route Table Management APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `ListTransitRouterRouteTablePropagations` | `--TransitRouterRouteTableId` | `--RegionId`, `--TransitRouterId`, `--MaxResults` | Query route propagation relationships (which network instances' routes are learned into this route table). Used for closure pre-check to compare route learning differences |
| `ListTransitRouterRouteTableAssociations` | `--TransitRouterRouteTableId` | `--RegionId`, `--TransitRouterId`, `--MaxResults` | Query route table association relationships (which network instances are associated to this route table). Used for closure pre-check to compare association differences |

### Transit Router APIs

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `ListTransitRouters` | - | `--RegionId` | Can query globally or specify Region |
| `ListTransitRouterRouteTables` | `--RegionId`, `--TransitRouterId` | - | **Both parameters required** |
| `ListTransitRouterRouteEntries` | `--TransitRouterRouteTableId` | `--TransitRouterRouteEntryStatus`, `--MaxResults` | **Only needs route table ID, NOT TransitRouterId**. **Default only returns Active routes**, must explicitly specify `--TransitRouterRouteEntryStatus Rejected` to find Rejected routes |
| `ListTransitRouterVpcAttachments` | `--RegionId`, `--TransitRouterId` | - | **Both parameters required** |
| `ListTransitRouterVpnAttachments` | `--RegionId`, `--TransitRouterId` | - | **Both parameters required** |

---

## VPC Service (vpc)

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `DescribeVpcs` | `--RegionId` | `--VpcId` | VpcId is optional, used for filtering |

---

## ActionTrail Service (actiontrail)

| API | Required Parameters | Optional Parameters | Description |
|-----|-------------------|-------------------|-------------|
| `LookupEvents` | `--StartTime`, `--EndTime`, `--LookupAttribute.1.Key`, `--LookupAttribute.1.Value` | `--MaxResults`, `--NextToken` | LookupAttribute uses dot notation: `LookupAttribute.1.Key` |

---

## ⚠️ Critical Parameter Notes

### Common Mistakes to Avoid

1. ❌ `DescribeVpcFirewallPrecheckDetail` uses `--RegionId` or `--RegionNo`
   - ✅ Correct: `--Region`

2. ❌ `DescribeCens` passes `--CenId`
   - ✅ This API does NOT support this parameter

3. ❌ `ListTransitRouterRouteEntries` passes `--TransitRouterId`
   - ✅ This API does NOT need this parameter

4. ❌ `LookupEvents` LookupAttribute uses underscore separator
   - ✅ Correct: Dot notation `LookupAttribute.1.Key`

5. ❌ CLI parameter uses `--Profile` (uppercase P)
   - ✅ Correct: `--profile` (lowercase p)

6. ❌ `ListTransitRouterRouteEntries` queries without status filter
   - ✅ **Default only returns Active routes, will miss Rejected conflict routes**

### CLI Command Execution Failure Handling

If command returns `ExitCode: 2` with parameter error:
1. Check parameter name correctness (case-sensitive)
2. Check parameter format correctness (dot notation vs underscore)
3. Check if unsupported parameters are used

Common fixes:
- `--Profile` → `--profile`
- `LookupAttribute_1_Key` → `LookupAttribute.1.Key`

---

## Region Parameter Acquisition Priority

1. ActionTrail acsRegion
2. VPC RegionId
3. User provided directly

---

## API Call Chain (3-Stage Firewall Enablement)

Refer to [firewall_lifecycle.md](firewall_lifecycle.md) for complete API call chain including:
- Stage 1: Precheck
- Stage 2: Firewall Configuration
- Stage 3: Create Drainage Objects
