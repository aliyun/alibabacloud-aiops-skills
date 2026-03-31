# API and CLI Command Reference

## 1. GA APIs (Grouped by Resource)

### 1.1 Service Management

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga DescribeAcceleratorServiceStatus --user-agent AlibabaCloud-Agent-Skills` | DescribeAcceleratorServiceStatus | Query GA service activation status (`Normal` indicates activated) |
| `aliyun ga OpenAcceleratorService --user-agent AlibabaCloud-Agent-Skills` | OpenAcceleratorService | Activate the Global Accelerator service |

### 1.2 Instance Management

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga CreateAccelerator --user-agent AlibabaCloud-Agent-Skills` | CreateAccelerator | Create a GA instance |
| `aliyun ga DescribeAccelerator --user-agent AlibabaCloud-Agent-Skills` | DescribeAccelerator | Query GA instance details |
| `aliyun ga DeleteAccelerator --user-agent AlibabaCloud-Agent-Skills` | DeleteAccelerator | Delete a GA instance |

### 1.3 Cross-border Configuration

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga UpdateAcceleratorCrossBorderStatus --user-agent AlibabaCloud-Agent-Skills` | UpdateAcceleratorCrossBorderStatus | Enable/disable cross-border acceleration |
| `aliyun ga UpdateAcceleratorCrossBorderMode --user-agent AlibabaCloud-Agent-Skills` | UpdateAcceleratorCrossBorderMode | Set cross-border mode (`private`/`bgpPro`) |
| `aliyun ga QueryCrossBorderApprovalStatus --user-agent AlibabaCloud-Agent-Skills` | QueryCrossBorderApprovalStatus | Query cross-border approval status |

### 1.4 Acceleration Region

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga ListAccelerateAreas --user-agent AlibabaCloud-Agent-Skills` | ListAccelerateAreas | Query supported acceleration regions and ISP line types |
| `aliyun ga CreateIpSets --user-agent AlibabaCloud-Agent-Skills` | CreateIpSets | Batch-create acceleration regions |
| `aliyun ga ListIpSets --user-agent AlibabaCloud-Agent-Skills` | ListIpSets | Query acceleration regions and assigned accelerated IP addresses |
| `aliyun ga DeleteIpSets --user-agent AlibabaCloud-Agent-Skills` | DeleteIpSets | Delete acceleration regions |

### 1.5 Listener

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga CreateListener --user-agent AlibabaCloud-Agent-Skills` | CreateListener | Create a listener |
| `aliyun ga ListListeners --user-agent AlibabaCloud-Agent-Skills` | ListListeners | Query listeners |
| `aliyun ga DeleteListener --user-agent AlibabaCloud-Agent-Skills` | DeleteListener | Delete a listener |

### 1.6 Endpoint Group

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga CreateEndpointGroup --user-agent AlibabaCloud-Agent-Skills` | CreateEndpointGroup | Create an endpoint group |
| `aliyun ga ListEndpointGroups --user-agent AlibabaCloud-Agent-Skills` | ListEndpointGroups | Query endpoint groups |
| `aliyun ga GetHealthStatus --user-agent AlibabaCloud-Agent-Skills` | GetHealthStatus | Query endpoint health status |
| `aliyun ga DeleteEndpointGroup --user-agent AlibabaCloud-Agent-Skills` | DeleteEndpointGroup | Delete an endpoint group |

### 1.7 Forwarding Rules

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun ga CreateForwardingRules --user-agent AlibabaCloud-Agent-Skills` | CreateForwardingRules | Create forwarding rules |
| `aliyun ga ListForwardingRules --user-agent AlibabaCloud-Agent-Skills` | ListForwardingRules | Query forwarding rules |
| `aliyun ga DeleteForwardingRules --user-agent AlibabaCloud-Agent-Skills` | DeleteForwardingRules | Delete forwarding rules |

---

## 2. Related Service APIs

### 2.1 Certificate Management Service (CAS)

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun cas ListUserCertificateOrder --user-agent AlibabaCloud-Agent-Skills` | ListUserCertificateOrder | Query user SSL certificates (for HTTPS listener scenarios) |

### 2.2 CloudMonitor (CMS)

| CLI Command | API Action | Description |
|----------|------------|------|
| `aliyun cms DescribeMetricList --user-agent AlibabaCloud-Agent-Skills` | DescribeMetricList | Query monitoring metric data |

---

## 3. General Call Conventions

### 3.1 API Metadata

Before generating CLI commands, retrieve API parameter definitions via the following URL to verify accuracy:

```
https://api.aliyun.com/meta/v1/products/GA/versions/2019-11-20/apis/{api_name}/api.json
```

### 3.2 Common Parameter Description

| Parameter | Description | When to Use |
|------|------|----------|
| `--region cn-hangzhou` | GA control plane region, fixed to `cn-hangzhou` | All GA API calls |
| `--user-agent AlibabaCloud-Agent-Skills` | Required User-Agent identifier | **All** `aliyun` CLI calls (mandatory) |
| `--method POST` | Use POST method | When nested array parameters are present (e.g., `CreateIpSets`, `CreateEndpointGroup`) |
| `--force` | Skip parameter validation | Used together with `--method POST` |
| `--AutoPay true` | Automatic payment | `CreateAccelerator` (pay-as-you-go) |

### 3.3 Nested Array Parameter Format

GA APIs use RPC-style PascalCase naming. Nested array parameters use dot notation:

```bash
# Format: --ParentParam.{index}.ChildParam value (index starts from 1)
--AccelerateRegion.1.AccelerateRegionId "cn-hangzhou"
--AccelerateRegion.1.Bandwidth 10
--EndpointConfigurations.1.Type "Ip"
--EndpointConfigurations.1.Endpoint "1.2.3.4"
```

---

## 4. Command Examples

### 4.1 Complete Cross-border Acceleration Workflow

```bash
# 0. Check if the GA service is activated
aliyun ga DescribeAcceleratorServiceStatus --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
# If Status is not Normal, activate the service first:
# aliyun ga OpenAcceleratorService --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# 1. Create a GA instance (pay-as-you-go + CDT billing)
aliyun ga CreateAccelerator \
  --region cn-hangzhou \
  --method POST \
  --Name "GA-Acceleration-Example" \
  --InstanceChargeType "POSTPAY" \
  --BandwidthBillingType "CDT" \
  --AutoPay true \
  --user-agent AlibabaCloud-Agent-Skills

# 2. Enable cross-border acceleration
aliyun ga UpdateAcceleratorCrossBorderStatus \
  --region cn-hangzhou \
  --AcceleratorId "ga-xxx" \
  --CrossBorderStatus true \
  --user-agent AlibabaCloud-Agent-Skills

# 3. Set private cross-border mode (must be done before creating IpSets)
aliyun ga UpdateAcceleratorCrossBorderMode \
  --region cn-hangzhou \
  --AcceleratorId "ga-xxx" \
  --CrossBorderMode private \
  --user-agent AlibabaCloud-Agent-Skills

# 4. Create acceleration regions
aliyun ga CreateIpSets \
  --region cn-hangzhou \
  --method POST \
  --force \
  --AcceleratorId "ga-xxx" \
  --AccelerateRegion.1.AccelerateRegionId "cn-hangzhou" \
  --AccelerateRegion.1.Bandwidth 10 \
  --AccelerateRegion.1.IspType "BGP" \
  --user-agent AlibabaCloud-Agent-Skills

# 5. Create a listener
aliyun ga CreateListener \
  --region cn-hangzhou \
  --AcceleratorId "ga-xxx" \
  --Protocol "TCP" \
  --PortRanges.1.FromPort <port> \
  --PortRanges.1.ToPort <port> \
  --user-agent AlibabaCloud-Agent-Skills

# 6. Create an endpoint group
aliyun ga CreateEndpointGroup \
  --region cn-hangzhou \
  --method POST \
  --force \
  --AcceleratorId "ga-xxx" \
  --ListenerId "lsr-xxx" \
  --EndpointGroupRegion "<region>" \
  --EndpointConfigurations.1.Type "Ip" \
  --EndpointConfigurations.1.Endpoint "<origin-server-IP>" \
  --EndpointConfigurations.1.Port <port> \
  --EndpointConfigurations.1.Weight 100 \
  --user-agent AlibabaCloud-Agent-Skills

# 7. Verify: Query acceleration regions and assigned accelerated IP addresses
aliyun ga ListIpSets \
  --region cn-hangzhou \
  --AcceleratorId "ga-xxx" \
  --user-agent AlibabaCloud-Agent-Skills

# 8. Verify: Query endpoint group configuration
aliyun ga ListEndpointGroups \
  --region cn-hangzhou \
  --AcceleratorId "ga-xxx" \
  --ListenerId "lsr-xxx" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 4.2 Forwarding Rules (CreateForwardingRules)

#### Complete Example (Host-based Routing)

```bash
aliyun ga CreateForwardingRules \
  --region cn-hangzhou \
  --AcceleratorId "ga-xxx" \
  --ListenerId "lsr-xxx" \
  --ForwardingRules.1.Priority 1 \
  --ForwardingRules.1.RuleConditions.1.RuleConditionType Host \
  --ForwardingRules.1.RuleConditions.1.RuleConditionValue "[\"github.com\"]" \
  --ForwardingRules.1.RuleActions.1.Order 1 \
  --ForwardingRules.1.RuleActions.1.RuleActionType ForwardGroup \
  --ForwardingRules.1.RuleActions.1.RuleActionValue "[{\"type\":\"endpointgroup\",\"value\":\"epg-xxx\"}]" \
  --method POST \
  --force \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Multi-domain / Multi-path Matching

```bash
# Multi-domain matching (OR logic)
--ForwardingRules.1.RuleConditions.1.RuleConditionValue "[\"api.example.com\", \"www.example.com\"]"

# Multi-path matching (OR logic)
--ForwardingRules.1.RuleConditions.1.RuleConditionValue "[\"/api/*\", \"/v1/*\"]"
```

#### Parameter Format Quick Reference

| Parameter | Type | Format Requirement | Example |
|------|------|----------|------|
| `RuleConditionType` | string | Enum value | `Host`, `Path`, `Method`, etc. |
| `RuleConditionValue` | string | JSON array string | `"[\"*.example.com\"]"` |
| `RuleActionType` | string | Enum value | `ForwardGroup`, `Redirect`, `FixResponse`, etc. |
| `RuleActionValue` | string | JSON array string | `"[{\"type\":\"endpointgroup\",\"value\":\"epg-xxx\"}]"` |

#### Common Errors

**RuleActionValue uses a single object instead of an array:**

```bash
# Wrong -- will cause SystemBusy or parameter validation errors
--ForwardingRules.1.RuleActions.1.RuleActionValue "{\"type\":\"endpointgroup\",\"value\":\"epg-xxx\"}"

# Correct -- must be a JSON array
--ForwardingRules.1.RuleActions.1.RuleActionValue "[{\"type\":\"endpointgroup\",\"value\":\"epg-xxx\"}]"
```

**RuleConditionValue incorrect quote escaping:**

```bash
# Wrong -- single quotes will not correctly escape
--ForwardingRules.1.RuleConditions.1.RuleConditionValue '["github.com"]'

# Correct -- use double quotes and escape inner quotes
--ForwardingRules.1.RuleConditions.1.RuleConditionValue "[\"github.com\"]"
```
