# Acceptance Criteria: alibabacloud-network-eip-associate

**Scenario**: EIP Batch Associate Cloud Resources (ECS, ALB, NAT Gateway)
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — Verify Product Name Exists

| Product | Correct Command | Verification Method |
|---------|-----------------|---------------------|
| VPC | `aliyun vpc` | `aliyun vpc --help` |
| ECS | `aliyun ecs` | `aliyun ecs --help` |
| ALB | `aliyun alb` | `aliyun alb --help` |

## 2. Command — Verify Subcommand Exists

### VPC Commands

| Command | Verification Method |
|---------|---------------------|
| `describe-vpcs` | `aliyun vpc describe-vpcs --help` |
| `create-default-vpc` | `aliyun vpc create-default-vpc --help` |
| `describe-vpc-attribute` | `aliyun vpc describe-vpc-attribute --help` |
| `create-vswitch` | `aliyun vpc create-vswitch --help` |
| `describe-vswitch-attributes` | `aliyun vpc describe-vswitch-attributes --help` |
| `allocate-eip-address` | `aliyun vpc allocate-eip-address --help` |
| `describe-eip-addresses` | `aliyun vpc describe-eip-addresses --help` |
| `associate-eip-address` | `aliyun vpc associate-eip-address --help` |
| `unassociate-eip-address` | `aliyun vpc unassociate-eip-address --help` |
| `release-eip-address` | `aliyun vpc release-eip-address --help` |
| `create-nat-gateway` | `aliyun vpc create-nat-gateway --help` |
| `describe-nat-gateways` | `aliyun vpc describe-nat-gateways --help` |
| `delete-nat-gateway` | `aliyun vpc delete-nat-gateway --help` |
| `delete-vswitch` | `aliyun vpc delete-vswitch --help` |
| `delete-vpc` | `aliyun vpc delete-vpc --help` |

### ECS Commands

| Command | Verification Method |
|---------|---------------------|
| `create-security-group` | `aliyun ecs create-security-group --help` |
| `delete-security-group` | `aliyun ecs delete-security-group --help` |
| `run-instances` | `aliyun ecs run-instances --help` |
| `describe-instances` | `aliyun ecs describe-instances --help` |
| `delete-instance` | `aliyun ecs delete-instance --help` |

### ALB Commands

| Command | Verification Method |
|---------|---------------------|
| `create-load-balancer` | `aliyun alb create-load-balancer --help` |
| `get-load-balancer-attribute` | `aliyun alb get-load-balancer-attribute --help` |
| `delete-load-balancer` | `aliyun alb delete-load-balancer --help` |
| `update-load-balancer-address-type-config` | `aliyun alb update-load-balancer-address-type-config --help` |

## 3. Parameters — Verify Parameter Names Exist

### EIP Related Parameters

#### allocate-eip-address
- `--region`: Required, Region ID
- `--bandwidth`: Optional, Bandwidth value
- `--internet-charge-type`: Optional, Billing method

#### associate-eip-address
- `--region`: Required
- `--allocation-id`: Required, EIP instance ID
- `--instance-id`: Required, Target resource ID
- `--instance-type`: Required, Resource type

#### unassociate-eip-address
- `--region`: Required
- `--allocation-id`: Required
- `--instance-id`: Required
- `--instance-type`: Optional

### Resource Type Parameter Values

#### InstanceType Allowed Enum Values (for associate-eip-address)
- `EcsInstance` — ECS Instance
- `Nat` — NAT Gateway
- `HaVip` — High Availability Virtual IP
- `NetworkInterface` — Elastic Network Interface

> **Note**: ALB does not use `associate-eip-address`. Use `update-load-balancer-address-type-config` instead.

## 4. User-Agent Flag

#### CORRECT
All `aliyun` commands must include `--user-agent AlibabaCloud-Agent-Skills`

```bash
aliyun vpc describe-eip-addresses \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT
```bash
# Missing --user-agent
aliyun vpc describe-eip-addresses --region cn-hangzhou
```

## 5. Plugin Mode Format

#### CORRECT
Use plugin mode format (lowercase with hyphens)

```bash
aliyun vpc allocate-eip-address
aliyun ecs run-instances
aliyun alb create-load-balancer
```

#### INCORRECT
Using traditional API format (PascalCase)

```bash
aliyun vpc AllocateEipAddress
aliyun ecs RunInstances
aliyun alb CreateLoadBalancer
```

## 6. Region Parameter

#### CORRECT
Use `--region` for VPC/ECS plugins

```bash
aliyun vpc describe-vpcs --region cn-hangzhou
aliyun ecs describe-instances --region cn-hangzhou
```

#### INCORRECT
Using `--region-id` (deprecated in plugin mode)

```bash
aliyun vpc describe-vpcs --region-id cn-hangzhou
```

---

# Validation Checklist

## Pre-execution Checks

- [ ] `aliyun version` >= 3.3.1
- [ ] `aliyun configure list` shows valid credentials
- [ ] All parameters confirmed with user
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] Using plugin mode format (lowercase with hyphens)
- [ ] Using `--region` instead of `--region-id`

## Post-execution Checks

- [ ] 3 EIPs created successfully (Status = Available)
- [ ] ECS instance created successfully (Status = Running)
- [ ] ALB instance created successfully (LoadBalancerStatus = Active)
- [ ] NAT Gateway created successfully (Status = Available)
- [ ] ECS EIP bindng successful (InstanceType = EcsInstance)
- [ ] ALB EIP bindng successful (AddressType = Internet)
- [ ] NAT EIP bindng successful (InstanceType = Nat)

## Cleanup Checks

- [ ] All EIPs disassociated
- [ ] All EIPs released
- [ ] ALB instance deleted
- [ ] NAT Gateway deleted
- [ ] ECS instance deleted
- [ ] Security Group deleted
- [ ] VSwitch deleted
- [ ] VPC deleted (if created in this session)

---

# Common Errors and Solutions

| Error Code | Cause | Solution |
|------------|-------|----------|
| `InvalidRegionId.NotFound` | Invalid Region ID | Use `aliyun ecs describe-regions` to query valid regions |
| `InvalidInstanceId.NotFound` | Resource ID does not exist | Confirm resource ID is correct |
| `IncorrectInstanceStatus` | Resource status does not meet conditions | Wait for resource status to be ready and retry |
| `InvalidAllocationId.AlreadyAssociated` | EIP already bindngd | Unbind first then rebind |
| `DependencyViolation` | Resource has dependencies | Delete resources in correct order |
| `QuotaExceeded` | Quota exceeded | Request quota increase or cleanup resources |
