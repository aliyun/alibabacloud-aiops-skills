# aliyun CLI Command Quick Reference

Resource discovery commands organized by product, including pagination parameters and output formatting.

**Notes:**
- Commands marked with a checkmark have been verified with a test account and can be used directly
- Unmarked commands are generated based on training knowledge; verify parameters with `aliyun <product> help` before executing
- For resource types not in this file, Claude will look up aliyun CLI or provider documentation on the fly during the discovery phase
- **All commands use plugin mode (lowercase-hyphenated format)**; parameter names do not use CamelCase

---

## General Parameter Notes

```bash
# Set Region (common to all commands)
REGION="cn-hangzhou"

# Region parameters (two types, different meanings):
# --biz-region-id  Business parameter, corresponds to the API's RegionId, passed in request body. Use when API requires RegionId
# --region         Framework parameter, controls which region's endpoint to connect to, not passed to API request body
# Rule: Prefer --biz-region-id (covers all scenarios).
#       --region can substitute only when the API's RegionId is optional (e.g., describe-vswitches, where setting endpoint region causes API to default query in that region)

# Pagination parameters
--page-size 50       # Items per page (max 100)
--page-number 1      # Page number (starts from 1)

# Output formatting (table format)
--output cols=Field1,Field2 rows=Path.To.Array

# JSON format output (for parsing details)
# Default output is JSON, no additional parameters needed
```

---

## Networking Products (VPC)

```bash
# Verified: VPC list (uses --biz-region-id)
aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 \
  --output cols=VpcId,VpcName,CidrBlock,Status rows=Vpcs.Vpc

# Verified: VPC details (JSON)
aliyun vpc describe-vpcs --biz-region-id $REGION --vpc-id vpc-bp1xxx

# Verified: VSwitch list (uses --region)
aliyun vpc describe-vswitches --region $REGION --page-size 50 \
  --output cols=VSwitchId,VSwitchName,CidrBlock,ZoneId,VpcId rows=VSwitches.VSwitch

# Verified: VSwitch details
aliyun vpc describe-vswitches --region $REGION --vswitch-id vsw-bp1xxx

# Route table list
aliyun vpc describe-route-tables --biz-region-id $REGION --page-size 50 \
  --output cols=RouteTableId,RouteTableName,VpcId,RouteTableType rows=RouteTables.RouteTable

# EIP list (uses --biz-region-id)
aliyun vpc describe-eip-addresses --biz-region-id $REGION --page-size 50 \
  --output cols=AllocationId,IpAddress,Status,InstanceId,InstanceType rows=EipAddresses.EipAddress

# EIP details
aliyun vpc describe-eip-addresses --biz-region-id $REGION --allocation-id eip-bp1xxx

# Verified: NAT Gateway list (uses --biz-region-id)
aliyun vpc describe-nat-gateways --biz-region-id $REGION --page-size 50 \
  --output cols=NatGatewayId,Name,VpcId,Status,NatType rows=NatGateways.NatGateway

# NAT Gateway details
aliyun vpc describe-nat-gateways --biz-region-id $REGION --nat-gateway-id ngw-bp1xxx

# SNAT entry list
aliyun vpc describe-snat-table-entries --biz-region-id $REGION \
  --snat-table-id stb-bp1xxx --page-size 50 \
  --output cols=SnatEntryId,SnatIp,SourceCidr,Status rows=SnatTableEntries.SnatTableEntry

# VPN Gateway list
aliyun vpc describe-vpn-gateways --biz-region-id $REGION --page-size 50 \
  --output cols=VpnGatewayId,Name,VpcId,Status rows=VpnGateways.VpnGateway
```

---

## Compute Products (ECS)

```bash
# Verified: ECS instance list (uses --biz-region-id)
aliyun ecs describe-instances --biz-region-id $REGION --page-size 50 \
  --output cols=InstanceId,InstanceName,Status,InstanceType,ZoneId,VpcAttributes.VpcId rows=Instances.Instance

# Verified: ECS instance details (JSON, includes all attributes)
aliyun ecs describe-instances --biz-region-id $REGION \
  --instance-ids '["i-bp1xxx"]'

# Verified: Security group list (uses --biz-region-id)
aliyun ecs describe-security-groups --biz-region-id $REGION --page-size 50 \
  --output cols=SecurityGroupId,SecurityGroupName,VpcId,SecurityGroupType rows=SecurityGroups.SecurityGroup

# Security group details (with rules)
aliyun ecs describe-security-group-attribute --biz-region-id $REGION \
  --security-group-id sg-bp1xxx --direction ingress
aliyun ecs describe-security-group-attribute --biz-region-id $REGION \
  --security-group-id sg-bp1xxx --direction egress

# Verified: Disk list (filter by instance)
aliyun ecs describe-disks --biz-region-id $REGION --instance-id i-bp1xxx --page-size 50 \
  --output cols=DiskId,DiskName,Status,Size,Type,Category rows=Disks.Disk

# Disk details
aliyun ecs describe-disks --biz-region-id $REGION --disk-ids '["d-bp1xxx"]'

# Image list (custom images)
aliyun ecs describe-images --biz-region-id $REGION --image-owner-alias self --page-size 50 \
  --output cols=ImageId,ImageName,Status,OSType rows=Images.Image

# Key pair list
aliyun ecs describe-key-pairs --biz-region-id $REGION --page-size 50 \
  --output cols=KeyPairName,KeyPairFingerPrint rows=KeyPairs.KeyPair

# Auto Scaling group list
aliyun ess describe-scaling-groups --biz-region-id $REGION --page-size 50 \
  --output cols=ScalingGroupId,ScalingGroupName,LifecycleState rows=ScalingGroups.ScalingGroup

# Scaling configuration list
aliyun ess describe-scaling-configurations --biz-region-id $REGION \
  --scaling-group-id asg-bp1xxx --page-size 50 \
  --output cols=ScalingConfigurationId,ScalingConfigurationName,LifecycleState rows=ScalingConfigurations.ScalingConfiguration
```

---

## Storage Products (OSS)

```bash
# OSS Bucket list (global, no Region needed)
aliyun ossutil ls oss://

# OSS Bucket details
aliyun ossutil stat oss://bucket-name

# OSS Bucket ACL
aliyun ossutil bucket-acl oss://bucket-name

# OSS Bucket versioning
aliyun ossutil bucket-versioning oss://bucket-name

# OSS Bucket lifecycle
aliyun ossutil lifecycle --method get oss://bucket-name

# OSS Bucket CORS
aliyun ossutil cors --method get oss://bucket-name

# OSS Bucket encryption
aliyun ossutil bucket-encryption --method get oss://bucket-name

# NAS file system list
aliyun nas describe-file-systems --biz-region-id $REGION --page-size 50 \
  --output cols=FileSystemId,FileSystemType,Status,StorageType rows=FileSystems.FileSystem

# NAS mount target list
aliyun nas describe-mount-targets --biz-region-id $REGION \
  --file-system-id fs-xxx --page-size 50 \
  --output cols=MountTargetDomain,Status,VpcId,VSwitchId rows=MountTargets.MountTarget
```

---

## Database Products (RDS)

```bash
# RDS instance list (uses --biz-region-id)
aliyun rds describe-db-instances --biz-region-id $REGION --page-size 50 \
  --output cols=DBInstanceId,DBInstanceDescription,Engine,EngineVersion,DBInstanceStatus,DBInstanceClass rows=Items.DBInstance

# RDS instance details
aliyun rds describe-db-instance-attribute --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx

# RDS database list
aliyun rds describe-databases --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx \
  --output cols=DBName,DBStatus,CharacterSetName rows=Databases.Database

# RDS account list
aliyun rds describe-accounts --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx \
  --output cols=AccountName,AccountStatus,AccountType rows=Accounts.DBInstanceAccount

# RDS IP whitelist
aliyun rds describe-db-instance-ip-array-list --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx

# RDS connection addresses
aliyun rds describe-db-instance-net-info --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx
```

---

## Cache Products (Redis/KVStore)

```bash
# Redis instance list (uses --biz-region-id)
aliyun r-kvstore describe-instances --biz-region-id $REGION --page-size 50 \
  --output cols=InstanceId,InstanceName,InstanceStatus,InstanceType,EngineVersion rows=Instances.KVStoreInstance

# Redis instance details
aliyun r-kvstore describe-instance-attribute --biz-region-id $REGION \
  --instance-id r-bp1xxx

# Redis IP whitelist
aliyun r-kvstore describe-security-ips --biz-region-id $REGION \
  --instance-id r-bp1xxx
```

---

## Document Database (MongoDB/DDS)

```bash
# MongoDB instance list (uses --biz-region-id)
aliyun dds describe-db-instances --biz-region-id $REGION --page-size 50 \
  --output cols=DBInstanceId,DBInstanceDescription,DBInstanceStatus,DBInstanceType rows=DBInstances.DBInstance

# MongoDB instance details
aliyun dds describe-db-instance-attribute --biz-region-id $REGION \
  --db-instance-id dds-bp1xxx

# MongoDB IP whitelist
aliyun dds describe-security-ips --biz-region-id $REGION \
  --db-instance-id dds-bp1xxx
```

---

## Load Balancing (SLB)

```bash
# SLB instance list (uses --biz-region-id)
aliyun slb describe-load-balancers --biz-region-id $REGION --page-size 50 \
  --output cols=LoadBalancerId,LoadBalancerName,LoadBalancerStatus,AddressType,VpcId rows=LoadBalancers.LoadBalancer

# SLB instance details
aliyun slb describe-load-balancer-attribute --biz-region-id $REGION \
  --load-balancer-id lb-bp1xxx

# SLB listener list
aliyun slb describe-load-balancer-listeners --biz-region-id $REGION \
  --load-balancer-id lb-bp1xxx \
  --output cols=ListenerPort,ListenerProtocol,Status rows=Listeners

# SLB backend servers
aliyun slb describe-health-status --biz-region-id $REGION \
  --load-balancer-id lb-bp1xxx

# ALB instance list (uses --region)
aliyun alb list-load-balancers --region $REGION --max-results 50

# ALB listener list
aliyun alb list-listeners --region $REGION --max-results 50

# ALB server group list
aliyun alb list-server-groups --region $REGION --max-results 50
```

---

## DNS (Alidns)

```bash
# Domain list (global, no Region needed)
aliyun alidns describe-domains --page-size 50 \
  --output cols=DomainId,DomainName,RecordCount,GroupName rows=Domains.Domain

# Domain DNS record list
aliyun alidns describe-domain-records --domain-name example.com --page-size 500 \
  --output cols=RecordId,RR,Type,Value,TTL,Status rows=DomainRecords.Record

# DNS group list
aliyun alidns describe-domain-groups --page-size 50 \
  --output cols=GroupId,GroupName rows=DomainGroups.DomainGroup
```

---

## Security and Identity (RAM)

```bash
# RAM user list
aliyun ram list-users --output cols=UserName,DisplayName,CreateDate rows=Users.User

# RAM role list
aliyun ram list-roles --output cols=RoleName,RoleId,CreateDate rows=Roles.Role

# RAM policy list (custom)
aliyun ram list-policies --policy-type Custom \
  --output cols=PolicyName,PolicyType,CreateDate rows=Policies.Policy

# RAM user attached policies
aliyun ram list-policies-for-user --user-name username \
  --output cols=PolicyName,PolicyType rows=Policies.Policy

# KMS key list
aliyun kms list-keys --page-size 100 \
  --output cols=KeyId,KeyArn rows=Keys.Key

# KMS key details
aliyun kms describe-key --key-id key-id
```

---

## Container Service (ACK)

```bash
# ACK cluster list
aliyun cs GET /clusters 2>&1

# ACK node pool list
aliyun cs GET /clusters/<cluster-id>/nodepools 2>&1
```

---

## Function Compute (FC)

```bash
# FC service list
aliyun fc GET /services 2>&1

# FC function list
aliyun fc GET /services/<service-name>/functions 2>&1
```

---

## FAQ

**Q: Command returns empty results**
- Check if Region is correct
- Check if account has Describe permission for the corresponding resource
- Some resources (e.g., OSS) are global and do not need a Region parameter

**Q: Region parameter error**
- `--biz-region-id` is a business parameter (corresponds to the API's RegionId), `--region` is a framework parameter (controls endpoint region)
- Prefer `--biz-region-id`; `--region` can substitute only when the API's RegionId is optional
- If a command reports `--biz-region-id is required`, the API's RegionId is mandatory and `--region` alone is not sufficient
- Global resources (OSS, DNS, RAM) do not need a Region parameter

**Q: Pagination issues (more than 50 resources)**
```bash
# Use page number pagination
aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 --page-number 2

# Or use --pager parameter (aliyun CLI supports automatic page merging)
aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 --pager
```

**Q: Output formatting not working**
- Confirm the `rows=` path is correct (try without `--output` first to see raw JSON structure)
- Use `.` for nested fields (e.g., `VpcAttributes.VpcId`)

**Q: Unsure about parameter names**
- Use `aliyun <product> <command> --help` to see all supported parameters
- Plugin mode parameters are always lowercase-hyphenated (e.g., `--instance-id`, `--vpc-id`)
