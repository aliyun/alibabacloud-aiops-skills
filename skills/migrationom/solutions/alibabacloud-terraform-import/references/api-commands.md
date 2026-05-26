# aliyun CLI 命令速查

按产品分组的资源发现命令，含分页参数和输出格式化。

**说明：**
- 标注 ✅ 的命令已通过测试账号验证，可直接使用
- 未标注的命令基于训练知识生成，执行前建议先用 `aliyun <product> help` 验证参数
- 文件中没有的资源类型，发现阶段由 Claude 现查 aliyun CLI 文档或 provider 文档给出命令
- **所有命令使用插件模式（小写连字符格式）**，参数名不使用驼峰式

---

## 通用参数说明

```bash
# 设置 Region（所有命令通用）
REGION="cn-hangzhou"

# Region 参数（两种，含义不同）：
# --biz-region-id  业务参数，对应 API 的 RegionId，传入请求体。API 要求 RegionId 时用此参数
# --region         框架参数，控制连接哪个地域的 endpoint，不传入 API 请求体
# 规则：优先使用 --biz-region-id（如 vpc describe-vpcs、ecs describe-instances）
#       仅当 API 的 RegionId 为可选时，--region 可替代（如 vpc describe-vswitches）

# 分页参数
--page-size 50       # 每页数量（最大 100）
--page-number 1      # 页码（从 1 开始）

# 输出格式化（表格形式）
--output cols=Field1,Field2 rows=Path.To.Array

# JSON 格式输出（用于解析详情）
# 默认输出即为 JSON，不需要额外参数
```

---

## 网络产品（VPC）

```bash
# ✅ VPC 列表（使用 --biz-region-id）
aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 \
  --output cols=VpcId,VpcName,CidrBlock,Status rows=Vpcs.Vpc

# ✅ VPC 详情（JSON）
aliyun vpc describe-vpcs --biz-region-id $REGION --vpc-id vpc-bp1xxx

# ✅ VSwitch 列表（使用 --region）
aliyun vpc describe-vswitches --region $REGION --page-size 50 \
  --output cols=VSwitchId,VSwitchName,CidrBlock,ZoneId,VpcId rows=VSwitches.VSwitch

# ✅ VSwitch 详情
aliyun vpc describe-vswitches --region $REGION --vswitch-id vsw-bp1xxx

# 路由表列表
aliyun vpc describe-route-tables --biz-region-id $REGION --page-size 50 \
  --output cols=RouteTableId,RouteTableName,VpcId,RouteTableType rows=RouteTables.RouteTable

# EIP 列表（使用 --biz-region-id）
aliyun vpc describe-eip-addresses --biz-region-id $REGION --page-size 50 \
  --output cols=AllocationId,IpAddress,Status,InstanceId,InstanceType rows=EipAddresses.EipAddress

# EIP 详情
aliyun vpc describe-eip-addresses --biz-region-id $REGION --allocation-id eip-bp1xxx

# ✅ NAT 网关列表（使用 --biz-region-id）
aliyun vpc describe-nat-gateways --biz-region-id $REGION --page-size 50 \
  --output cols=NatGatewayId,Name,VpcId,Status,NatType rows=NatGateways.NatGateway

# NAT 网关详情
aliyun vpc describe-nat-gateways --biz-region-id $REGION --nat-gateway-id ngw-bp1xxx

# SNAT 条目列表
aliyun vpc describe-snat-table-entries --biz-region-id $REGION \
  --snat-table-id stb-bp1xxx --page-size 50 \
  --output cols=SnatEntryId,SnatIp,SourceCidr,Status rows=SnatTableEntries.SnatTableEntry

# VPN 网关列表
aliyun vpc describe-vpn-gateways --biz-region-id $REGION --page-size 50 \
  --output cols=VpnGatewayId,Name,VpcId,Status rows=VpnGateways.VpnGateway
```

---

## 计算产品（ECS）

```bash
# ✅ ECS 实例列表（使用 --biz-region-id）
aliyun ecs describe-instances --biz-region-id $REGION --page-size 50 \
  --output cols=InstanceId,InstanceName,Status,InstanceType,ZoneId,VpcAttributes.VpcId rows=Instances.Instance

# ✅ ECS 实例详情（JSON，包含所有属性）
aliyun ecs describe-instances --biz-region-id $REGION \
  --instance-ids '["i-bp1xxx"]'

# ✅ 安全组列表（使用 --biz-region-id）
aliyun ecs describe-security-groups --biz-region-id $REGION --page-size 50 \
  --output cols=SecurityGroupId,SecurityGroupName,VpcId,SecurityGroupType rows=SecurityGroups.SecurityGroup

# 安全组详情（含规则）
aliyun ecs describe-security-group-attribute --biz-region-id $REGION \
  --security-group-id sg-bp1xxx --direction ingress
aliyun ecs describe-security-group-attribute --biz-region-id $REGION \
  --security-group-id sg-bp1xxx --direction egress

# ✅ 云盘列表（按实例过滤）
aliyun ecs describe-disks --biz-region-id $REGION --instance-id i-bp1xxx --page-size 50 \
  --output cols=DiskId,DiskName,Status,Size,Type,Category rows=Disks.Disk

# 云盘详情
aliyun ecs describe-disks --biz-region-id $REGION --disk-ids '["d-bp1xxx"]'

# 镜像列表（自定义镜像）
aliyun ecs describe-images --biz-region-id $REGION --image-owner-alias self --page-size 50 \
  --output cols=ImageId,ImageName,Status,OSType rows=Images.Image

# 密钥对列表
aliyun ecs describe-key-pairs --biz-region-id $REGION --page-size 50 \
  --output cols=KeyPairName,KeyPairFingerPrint rows=KeyPairs.KeyPair

# 弹性伸缩组列表
aliyun ess describe-scaling-groups --biz-region-id $REGION --page-size 50 \
  --output cols=ScalingGroupId,ScalingGroupName,LifecycleState rows=ScalingGroups.ScalingGroup

# 伸缩配置列表
aliyun ess describe-scaling-configurations --biz-region-id $REGION \
  --scaling-group-id asg-bp1xxx --page-size 50 \
  --output cols=ScalingConfigurationId,ScalingConfigurationName,LifecycleState rows=ScalingConfigurations.ScalingConfiguration
```

---

## 存储产品（OSS）

```bash
# OSS Bucket 列表（全局，不需要 Region）
aliyun ossutil ls oss://

# OSS Bucket 详情
aliyun ossutil stat oss://bucket-name

# OSS Bucket ACL
aliyun ossutil bucket-acl oss://bucket-name

# OSS Bucket 版本控制
aliyun ossutil bucket-versioning oss://bucket-name

# OSS Bucket 生命周期
aliyun ossutil lifecycle --method get oss://bucket-name

# OSS Bucket CORS
aliyun ossutil cors --method get oss://bucket-name

# OSS Bucket 加密
aliyun ossutil bucket-encryption --method get oss://bucket-name

# NAS 文件系统列表
aliyun nas describe-file-systems --biz-region-id $REGION --page-size 50 \
  --output cols=FileSystemId,FileSystemType,Status,StorageType rows=FileSystems.FileSystem

# NAS 挂载点列表
aliyun nas describe-mount-targets --biz-region-id $REGION \
  --file-system-id fs-xxx --page-size 50 \
  --output cols=MountTargetDomain,Status,VpcId,VSwitchId rows=MountTargets.MountTarget
```

---

## 数据库产品（RDS）

```bash
# RDS 实例列表（使用 --biz-region-id）
aliyun rds describe-db-instances --biz-region-id $REGION --page-size 50 \
  --output cols=DBInstanceId,DBInstanceDescription,Engine,EngineVersion,DBInstanceStatus,DBInstanceClass rows=Items.DBInstance

# RDS 实例详情
aliyun rds describe-db-instance-attribute --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx

# RDS 数据库列表
aliyun rds describe-databases --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx \
  --output cols=DBName,DBStatus,CharacterSetName rows=Databases.Database

# RDS 账号列表
aliyun rds describe-accounts --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx \
  --output cols=AccountName,AccountStatus,AccountType rows=Accounts.DBInstanceAccount

# RDS 白名单
aliyun rds describe-db-instance-ip-array-list --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx

# RDS 连接地址
aliyun rds describe-db-instance-net-info --biz-region-id $REGION \
  --db-instance-id rm-bp1xxx
```

---

## 缓存产品（Redis/KVStore）

```bash
# Redis 实例列表（使用 --biz-region-id）
aliyun r-kvstore describe-instances --biz-region-id $REGION --page-size 50 \
  --output cols=InstanceId,InstanceName,InstanceStatus,InstanceType,EngineVersion rows=Instances.KVStoreInstance

# Redis 实例详情
aliyun r-kvstore describe-instance-attribute --biz-region-id $REGION \
  --instance-id r-bp1xxx

# Redis 白名单
aliyun r-kvstore describe-security-ips --biz-region-id $REGION \
  --instance-id r-bp1xxx
```

---

## 文档数据库（MongoDB/DDS）

```bash
# MongoDB 实例列表（使用 --biz-region-id）
aliyun dds describe-db-instances --biz-region-id $REGION --page-size 50 \
  --output cols=DBInstanceId,DBInstanceDescription,DBInstanceStatus,DBInstanceType rows=DBInstances.DBInstance

# MongoDB 实例详情
aliyun dds describe-db-instance-attribute --biz-region-id $REGION \
  --db-instance-id dds-bp1xxx

# MongoDB 白名单
aliyun dds describe-security-ips --biz-region-id $REGION \
  --db-instance-id dds-bp1xxx
```

---

## 负载均衡（SLB）

```bash
# SLB 实例列表（使用 --biz-region-id）
aliyun slb describe-load-balancers --biz-region-id $REGION --page-size 50 \
  --output cols=LoadBalancerId,LoadBalancerName,LoadBalancerStatus,AddressType,VpcId rows=LoadBalancers.LoadBalancer

# SLB 实例详情
aliyun slb describe-load-balancer-attribute --biz-region-id $REGION \
  --load-balancer-id lb-bp1xxx

# SLB 监听列表
aliyun slb describe-load-balancer-listeners --biz-region-id $REGION \
  --load-balancer-id lb-bp1xxx \
  --output cols=ListenerPort,ListenerProtocol,Status rows=Listeners

# SLB 后端服务器
aliyun slb describe-health-status --biz-region-id $REGION \
  --load-balancer-id lb-bp1xxx

# ALB 实例列表（使用 --region）
aliyun alb list-load-balancers --region $REGION --max-results 50

# ALB 监听列表
aliyun alb list-listeners --region $REGION --max-results 50

# ALB 服务器组列表
aliyun alb list-server-groups --region $REGION --max-results 50
```

---

## DNS（云解析）

```bash
# 域名列表（全局，不需要 Region）
aliyun alidns describe-domains --page-size 50 \
  --output cols=DomainId,DomainName,RecordCount,GroupName rows=Domains.Domain

# 域名解析记录列表
aliyun alidns describe-domain-records --domain-name example.com --page-size 500 \
  --output cols=RecordId,RR,Type,Value,TTL,Status rows=DomainRecords.Record

# DNS 分组列表
aliyun alidns describe-domain-groups --page-size 50 \
  --output cols=GroupId,GroupName rows=DomainGroups.DomainGroup
```

---

## 安全与身份（RAM）

```bash
# RAM 用户列表
aliyun ram list-users --output cols=UserName,DisplayName,CreateDate rows=Users.User

# RAM 角色列表
aliyun ram list-roles --output cols=RoleName,RoleId,CreateDate rows=Roles.Role

# RAM 策略列表（自定义）
aliyun ram list-policies --policy-type Custom \
  --output cols=PolicyName,PolicyType,CreateDate rows=Policies.Policy

# RAM 用户绑定的策略
aliyun ram list-policies-for-user --user-name username \
  --output cols=PolicyName,PolicyType rows=Policies.Policy

# KMS 密钥列表
aliyun kms list-keys --page-size 100 \
  --output cols=KeyId,KeyArn rows=Keys.Key

# KMS 密钥详情
aliyun kms describe-key --key-id key-id
```

---

## 容器服务（ACK）

```bash
# ACK 集群列表
aliyun cs GET /clusters 2>&1

# ACK 节点池列表
aliyun cs GET /clusters/<cluster-id>/nodepools 2>&1
```

---

## 函数计算（FC）

```bash
# FC 服务列表
aliyun fc GET /services 2>&1

# FC 函数列表
aliyun fc GET /services/<service-name>/functions 2>&1
```

---

## 常见问题

**Q: 命令返回空结果**
- 检查 Region 是否正确
- 检查账号是否有对应资源的 Describe 权限
- 部分资源（如 OSS）是全局的，不需要 Region 参数

**Q: Region 参数报错**
- `--biz-region-id` 是业务参数（对应 API 的 RegionId），`--region` 是框架参数（控制 endpoint 地域）
- 优先使用 `--biz-region-id`；仅当 API 的 RegionId 为可选时 `--region` 可替代
- 若命令报 `--biz-region-id is required`，说明该 API 的 RegionId 是必填，不能仅用 `--region`
- 全局资源（OSS、DNS、RAM）不需要 Region 参数

**Q: 分页问题（资源超过 50 个）**
```bash
# 使用页码分页
aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 --page-number 2

# 或使用 --pager 参数（aliyun CLI 支持自动分页合并）
aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 --pager
```

**Q: 输出格式化不生效**
- 确认 `rows=` 路径正确（可先不加 `--output` 参数查看原始 JSON 结构）
- 嵌套字段用 `.` 分隔（如 `VpcAttributes.VpcId`）

**Q: 参数名不确定**
- 使用 `aliyun <product> <command> --help` 查看所有支持的参数
- 插件模式参数一律为小写连字符格式（如 `--instance-id`、`--vpc-id`）
