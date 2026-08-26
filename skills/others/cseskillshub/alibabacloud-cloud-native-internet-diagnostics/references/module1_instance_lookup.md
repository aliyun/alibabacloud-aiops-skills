# Module 1: Instance Lookup (Five Products)

Minimum privilege: **read-only**. Every API listed here is a Get/Describe query; no write action exists in this skill.

This module resolves the VPC and vSwitch bound to a cloud-native product instance. All calls are executed by `scripts/cloud_native_internet_diag.py` through the aliyun CLI default credential chain.

## Product Routing

| Product | CLI call shape | Style |
|---------|----------------|-------|
| mse_gateway | `aliyun mse get-gateway --gateway-unique-id <id>` | RPC (plugin mode) |
| apig_gateway / ai_gateway | `aliyun apig GET /v1/gateways/<id>` | ROA passthrough |
| sae | `aliyun sae GET /pop/v1/sam/app/describeApplicationConfig --AppId <id>` | ROA passthrough |
| fc | `aliyun fc GET /2023-03-30/functions/<name>` | ROA passthrough |

Every call also carries `--region <region>` and `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloud-native-internet-diagnostics/<session-id>`.

## 1. Cloud-native Gateway (MSE)

**API**: `mse:GetGateway` (RPC, version 2019-05-31)

| Request parameter | Type | Required | Description |
|-------------------|------|----------|-------------|
| GatewayUniqueId | string | Yes | Gateway unique id, starts with `gw-`; passed as the CLI flag `--gateway-unique-id` |

**Key response fields**:

- `Data.Vpc` → VPC id (e.g. `vpc-bp1328cm01m6uel42b5zb`)
- `Data.Vswitch` → vSwitch id (e.g. `vsw-bp18zeqxx6mpuq843z4n5`)
- `Data.Name` → gateway name
- `Data.Status` → gateway status

An empty `Data` means the gateway id or region is wrong.

## 2. Cloud-native API Gateway / AI Gateway

**API**: `apig:GetGateway` (ROA, version 2024-03-27)

**Request path**: `GET /v1/gateways/{gatewayId}` (gatewayId starts with `gw-`)

**Key response fields**:

- `data.vpc.vpcId` → VPC id
- `data.vSwitch.vSwitchId` → vSwitch id
- `data.gatewayType` → `API` (cloud-native API gateway) or `AI` (AI gateway)
- `data.name` / `data.status` → name / status

> API gateway and AI gateway share this API; `data.gatewayType` distinguishes them. The script reports the effective product key derived from this field and logs a `[WARN]` when it differs from the requested one.

## 3. Serverless App Engine (SAE)

**API**: `sae:DescribeApplicationConfig` (ROA, version 2019-05-06)

**Request path**: `GET /pop/v1/sam/app/describeApplicationConfig?AppId=<AppId>` (AppId is a UUID)

**Key response fields**:

- `Data.VpcId` → VPC id
- `Data.VSwitchId` → vSwitch id
- `Data.AppName` → application name
- `Data.NamespaceId` → namespace id

## 4. Function Compute (FC)

**API**: `fc:GetFunction` (ROA, version 2023-03-30)

**Request path**: `GET /2023-03-30/functions/{functionName}`

**Key response fields**:

- `vpcConfig.vpcId` → VPC id
- `vpcConfig.vSwitchIds` → vSwitch id **array** (in quadrant D the egress check runs against every bound vSwitch; any hit means the function has a fixed public egress)
- `internetAccess` → boolean, whether the function may access the public internet

FC has special conclusion logic (four quadrants A/B/C/D) because the egress mode depends on `internetAccess` combined with the VPC configuration. See [module2_vswitch_egress.md](module2_vswitch_egress.md).

## Error Semantics

| Situation | Behavior |
|-----------|----------|
| CLI exit != 0 with error JSON | Script reports `<Code>: <Message>` and exits 1 |
| Empty instance payload (no Data/data) | `InstanceNotFound: ... check the instance id and region` |
| Authorization error codes (HTTP `403` class: `NoPermission` / `AccessDenied` / `InvalidAccessKeyId.NotFound` / ...) | Recorded as `[WARN]` degradation trace; report points to ram-policies.md |
| CLI timeout (> 60s) | `CliError: <api> timed out after 60s` |
