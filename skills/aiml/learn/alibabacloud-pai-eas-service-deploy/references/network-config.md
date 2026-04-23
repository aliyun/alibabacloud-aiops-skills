# Network Configuration Rules

**Table of Contents**
- [Network Config Requirements](#network-config-requirements)
- [Consistency Requirements](#consistency-requirements)
- [ALB Dedicated Gateway](#alb-dedicated-gateway)
- [NLB Configuration](#nlb-configuration)
- [Shared Gateway](#shared-gateway)

## Network Config Requirements

| Gateway Type | `cloud.networking` | Description |
|-------------|-------------------|-------------|
| **Shared Gateway** | ❌ Not required | For testing, not recommended for production, no VPC config needed |
| **ALB Dedicated Gateway** | ✅ **Required** | VPC/VSwitch obtained from gateway |
| **NLB** | ✅ **Required** | VPC/VSwitch must be consistent with NLB |

## Consistency Requirements

```
When deploying with ALB/NLB:
├── cloud.networking.vpc_id           ← Must match gateway/NLB VPC
├── cloud.networking.vswitch_id       ← Must match gateway/NLB VSwitch
└── cloud.networking.security_group_id ← Must be in the same VPC as VSwitch

⚠️ Important: VPC, VSwitch, and security group must all be under the same VPC!
```

## ALB Dedicated Gateway

### Config Flow

1. Select gateway (from `list-gateway`)
2. Call `DescribeGateway` to get VPC/VSwitch
3. Select security group under the gateway VPC

### Config Example

```json
{
  "networking": { "gateway": "gw-abc123" },
  "cloud": {
    "networking": {
      "vpc_id": "{from gateway}",
      "vswitch_id": "{from gateway, comma-separated if multiple}",
      "security_group_id": "{user selected}"
    }
  }
}
```

### API Calls

```bash
# List gateways
aliyun eas list-gateway --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Get gateway details (includes VPC and VSwitch info)
aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills

# Key fields in response:
# .LoadBalancerList[0].VpcId        → VPC ID
# .LoadBalancerList[0].VSwitchIds   → VSwitch list
```

**Correct jq command to get VPC and comma-separated VSwitch ID**:

```bash
aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills | \
  jq '{
    vpc_id: .LoadBalancerList[0].VpcId,
    vswitch_id: (.LoadBalancerList[0].VSwitchIds | join(","))
  }'
```

**Response example**:

```json
{
  "vpc_id": "vpc-bp13kiflgde6v9dc9smc8",
  "vswitch_id": "vsw-bp1bhmnwqdh1ta9z9klms,vsw-bp1lz95xtmjiwqcpq31ng"
}
```

**Query security groups** (after getting VPC):

```bash
aliyun ecs describe-security-groups --biz-region-id cn-hangzhou --vpc-id {gateway_vpc} --user-agent AlibabaCloud-Agent-Skills | \
  jq '.SecurityGroups[] | "\(.SecurityGroupId)\t\(.SecurityGroupName)"'
```

---

## NLB Configuration

### Two Modes

| Mode | ID | Description |
|------|-----|-------------|
| **System NLB** | `"default"` | System auto-creates, lifecycle follows service (recommended) |
| **Custom NLB** | Actual NLB ID | Associate with user's existing NLB instance |

### System NLB (Recommended)

System automatically creates an NLB instance under your account. The NLB lifecycle follows the service.

**Config example**:

```json
{
  "networking": {
    "nlb": [{
      "id": "default",
      "listener_port": 9090,
      "netType": "intranet"
    }]
  },
  "cloud": {
    "networking": {
      "vpc_id": "vpc-xxx",
      "vswitch_id": "vsw-zone-a,vsw-zone-b",
      "security_group_id": "sg-xxx"
    }
  }
}
```

**Parameter description**:

| Parameter | Description |
|-----------|-------------|
| `id` | Fixed as `"default"` |
| `listener_port` | Listener port (cannot be 8080) |
| `netType` | `intranet` or `internet` |
| `vswitch_id` | **Comma-separated, must include at least 2 VSwitches across different zones** (e.g. `"vsw-xxx-a,vsw-xxx-b"`) |

**Multi-port config supported**:

```json
{
  "networking": {
    "nlb": [
      {"id": "default", "listener_port": 9090, "netType": "intranet"},
      {"id": "default", "listener_port": 9091, "netType": "internet"}
    ]
  }
}
```

**Config flow**:

1. Select "System NLB"
2. Configure VPC info (reuse high-speed direct connect VPC/VSwitch)
3. Select network type (intranet/internet/both)
4. Configure listener port

**⚠️ Important rules**:
- `vswitch_id` must be **comma-separated with at least 2 VSwitches across different availability zones** (e.g. `"vsw-zone-a,vsw-zone-b"`)
- Port 8080 is reserved by EAS engine, cannot be used
- VPC, VSwitch, and security group must all be under the same VPC
- System NLB lifecycle follows the service

### Custom NLB

Associate with user's existing NLB instance.

**Config example**:

```json
{
  "networking": {
    "nlb": [{
      "id": "nlb-fpj3530zrbt7x5zkhk",
      "listener_port": 9090
    }]
  },
  "cloud": {
    "networking": {
      "vpc_id": "vpc-xxx",
      "vswitch_id": "vsw-zone-a,vsw-zone-b",
      "security_group_id": "sg-xxx"
    }
  }
}
```

**Requirements**:
- NLB must be in the same VPC as the service
- `vswitch_id` must be comma-separated with at least 2 VSwitches across different zones
- Port 8080 cannot be used
- Port must not conflict with existing NLB listeners
- Custom NLB and system NLB are mutually exclusive (modifying will disassociate the old one)

### NLB API Calls

```bash
# Query existing NLBs
aliyun nlb list-load-balancers --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills

# Get NLB details (includes VPC and VSwitch info)
aliyun nlb get-load-balancer-attribute --load-balancer-id nlb-xxx --user-agent AlibabaCloud-Agent-Skills | \
  jq '{vpc_id: .VpcId, vswitch_id: ([.ZoneMappings[].VswitchId] | join(","))}'
```

**Response example**:

```json
{
  "vpc_id": "vpc-xxx",
  "vswitch_id": "vsw-xxx-a,vsw-xxx-b"
}
```

**Query security groups** (after getting NLB VPC):

```bash
aliyun ecs describe-security-groups --biz-region-id cn-hangzhou --vpc-id {nlb_vpc} --user-agent AlibabaCloud-Agent-Skills | \
  jq '.SecurityGroups[] | "\(.SecurityGroupId)\t\(.SecurityGroupName)"'
```

**⚠️ Important rules**:
- VPC, VSwitch, and security group must all be under the NLB's VPC
- Security group must be in the **same VPC** as NLB
- Port 8080 is reserved by EAS engine, cannot be used

### Access URL

```
Access URL: <NLB_domain>:<listener_port>/api/predict/<service_name>
Get domain: https://nlb.console.aliyun.com/
```

## Shared Gateway

No `cloud.networking` config needed, uses default mode.

```json
{
  "metadata": { "name": "my-service" },
  "containers": [...]
  // No networking or cloud.networking fields needed
}
```
