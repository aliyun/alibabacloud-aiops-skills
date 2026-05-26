---
name: alibabacloud-terraform-import
description: This skill should be used when the user asks to "导入阿里云资源到 Terraform", "terraform import 阿里云", "将现有云资源纳入 Terraform 管理", "阿里云资源迁移 Terraform", "生成 terraform state", "import alicloud resources", "阿里云 IaC 迁移", "阿里云 Terraform 导入", or needs to manage existing Alibaba Cloud resources with Terraform. Guides users step-by-step through environment check, authentication, resource discovery, HCL generation, state import, validation, and dependency graph. Supports both one-time migration and incremental sync.
version: 0.1.0
---

# 阿里云资源 Terraform 导入向导

分步引导将阿里云账号下的现有资源导入到本地 Terraform 管理。自动执行环境检查、资源发现、HCL 生成、state 导入等操作，用户仅需在关键决策点确认。

支持两种模式：
- **一次性迁移**：完整走完 Phase 1-9
- **增量同步**：已有 Terraform 工作目录时，直接跳到增量同步模式

## 资源支持范围

- **理论支持范围**：alicloud provider 中有 Read 方法的资源（即能从云上读取状态的资源）。大多数资源可通过 `terraform import` 命令或 `import` 块（Terraform 1.5+）直接导入；少数未实现 Importer 的资源可通过手动构造 tfstate 导入，但需精确匹配 provider 的 state 结构，存在一定风险。可通过 `https://registry.terraform.io/providers/aliyun/alicloud/latest/docs` 查询各资源的支持情况。
- **预置资源**：约 50 种常用资源（网络、计算、存储、数据库、负载均衡、DNS、RAM、ACK、FC），有经过验证的 API 发现命令、HCL 模板和 import ID 格式，见 `references/`
- **预置范围之外**：会临时查 provider 文档给出命令和模板，准确性依赖文档内容，建议用户在执行前确认

---

## Phase 1: 环境检查

执行以下命令检测环境：

```bash
echo "=== aliyun CLI ===" && aliyun --version 2>&1 || echo "NOT_INSTALLED"
echo "=== terraform ===" && terraform --version 2>&1 || echo "NOT_INSTALLED"
echo "=== python3 ===" && python3 --version 2>&1 || echo "NOT_INSTALLED"
echo "=== OS ===" && uname -s 2>&1
```

根据输出自动处理缺失工具：
- aliyun CLI 缺失（macOS）：执行 `brew install aliyun-cli`
- aliyun CLI 缺失（Linux）：执行 `curl -sSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz && sudo mv aliyun /usr/local/bin/`
- terraform 缺失（macOS）：执行 `brew tap hashicorp/tap && brew install hashicorp/tap/terraform`
- terraform 缺失（Linux）：提示用户前往 https://developer.hashicorp.com/terraform/install 手动安装（需要 root 权限）

全部就绪后进入 Phase 2。

**配置 aliyun CLI AI-Mode：**

所有 aliyun CLI 命令必须配置 AI-Mode 标识，以便阿里云识别 AI 调用场景并提供优化支持。在执行任何 aliyun CLI 命令前，先执行：

```bash
# 启用 AI-Mode（必需）
aliyun configure ai-mode enable

# 设置 User-Agent 标识（必需，注意需要 --user-agent 参数名）
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-terraform-import"

# 更新插件到最新版本（推荐）
aliyun plugin update
```

**禁用 AI-Mode（如需）：**
```bash
aliyun configure ai-mode disable
```

后续所有 aliyun CLI 命令都会自动携带 AI-Mode 标识和 User-Agent。所有命令必须使用插件模式（小写连字符格式，如 `aliyun vpc describe-vpcs`）。

**插件模式参数格式说明：**
- 所有参数名使用小写连字符（lowercase-hyphenated）格式，不使用驼峰式
- **Region 参数有两种，含义不同**：
  - `--biz-region-id`：**业务参数**，对应 API 文档中的 `RegionId`，作为请求体参数传给 API。当 API 文档标注 `RegionId` 为 required 时必须使用此参数
  - `--region`：**框架参数**，控制 CLI 连接哪个地域的 endpoint（如 `vpc.cn-shanghai.aliyuncs.com`），不会作为业务参数传给 API
  - 规则：优先使用 `--biz-region-id`（覆盖所有场景）。`--region` 仅在 API 的 `RegionId` 为可选参数时可替代（如 `describe-vswitches`，设置了 endpoint 地域后 API 会默认在该 region 查询）
- 分页参数：使用 `--page-size`（而非 `--PageSize`）
- 其他 API 参数：API 文档中的驼峰参数名加 `biz-` 前缀 + 小写连字符化（如 `VpcId` → `--vpc-id`，`InstanceIds` → `--instance-ids`）。可通过 `aliyun <product> <command> --help` 确认实际参数名
---

## Phase 2: 认证配置

本 Skill 依赖阿里云默认凭证链进行认证，支持以下方式（按优先级）：
1. 环境变量（ALICLOUD_ACCESS_KEY / ALICLOUD_SECRET_KEY）— **最高优先级**
2. aliyun CLI 配置文件（~/.aliyun/config.json）
3. ECS RAM 角色（仅限在 ECS 上运行时）

**重要**：Terraform alicloud provider 和 aliyun CLI 各自独立读取凭证，且均优先使用环境变量。当环境变量与 CLI profile 指向不同账号时，统一以环境变量为准。

**验证认证：**

通过默认凭证链验证身份（不显式传递 AK/SK）：

```bash
aliyun sts get-caller-identity 2>&1
```

分析输出：
- 确认 AccountId 和 UserId，记录 Region
- **若凭证来源不符合预期**（如环境变量与 CLI profile 指向不同账号），告知用户存在凭证冲突，建议统一凭证配置后重试

若报错，提示用户：
- 检查是否已配置凭证（通过 `aliyun configure` 或环境变量）
- 检查权限（需要 ReadOnlyAccess 或对应资源的 Describe 权限）
- 参考 `references/ram-policies.md` 了解所需权限
---

## Phase 3: 工作目录初始化

询问用户以下信息：
- 目标工作目录路径（默认 `~/alicloud-terraform`）
- 目标 Region（若已从 Phase 2 推断出则确认，否则询问）
- 是否已有 Terraform 工作目录（若已有则跳过本 Phase）

用户确认后，自动完成以下操作：

1. 创建工作目录及 `.import/` 子目录（存放导入过程的中间产物）
2. 在目标目录生成 `provider.tf`（参考 `examples/provider.tf`），将 region 默认值替换为用户确认的 Region
3. 在目标目录执行 `terraform init`
4. 分析 init 输出，确认 provider 下载成功
5. **（可选增强）** 执行 `terraform providers schema -json`，提取所有资源中字段名以 `_id` 或 `_ids` 结尾的字段，构建**引用字段白名单**，供 Phase 6 使用。若 schema 输出过大导致解析超时，可跳过此步，Phase 6 将降级使用静态依赖规则解析引用
6. **（可选增强）** 调用 `iacservice list-resource-types`（分页获取全量），将返回的 `resourceType` 字段前缀 `ALIYUN` 替换为 `ACS`，建立 `terraformResourceType ↔ ResourceCode` 双向映射表，写入 `.import/resource-type-mapping.json`，供 Phase 4/5/6 使用。若调用失败或权限不足，降级使用 `references/resource-hub-api.md` 中的静态映射表。**跳过此步不影响核心导入流程**，仅影响 ResourceCenter 接口的资源类型转换
7. 告知用户初始化完成，进入 Phase 4

---

## Phase 4: 资源发现

**步骤 0 — 查询 ResourceCenter 支持的资源类型（优先执行）**

执行 `aliyun resourcecenter list-resource-types` 获取接口 A（search-resources）和接口 B（list-resource-relationships）各自支持的资源类型列表，缓存供本 Phase 和 Phase 5 使用。详见 `references/resource-hub-api.md`。

若调用失败或权限不足，跳过步骤 0，全程使用原生产品 API 发现资源。

**步骤 1 — 发现资源**

对每种目标资源类型，按以下优先级选择发现方式：
1. 若该资源类型在接口 A 支持列表中 → 用接口 A（search-resources）批量查询，详见 `references/resource-hub-api.md`
2. 否则 → 降级使用 `references/api-commands.md` 中的原生产品 API 命令

若用户需要发现 `references/api-commands.md` 中没有的资源类型：
- 先查 provider 文档（`https://registry.terraform.io/providers/aliyun/alicloud/latest/docs`）判断支持情况：
  - 有 `Import` 章节 → 支持 `terraform import`，按正常流程处理
  - 无 `Import` 章节但 provider 支持该资源 → 可通过手动构造 tfstate 导入，告知用户风险后按需处理
  - provider 完全不支持该资源 → 明确告知无法导入
- 确认支持后，查 aliyun CLI 文档（`https://help.aliyun.com/document_detail/110244.html`）或对应产品 API 文档给出发现命令

执行相应命令，收集输出后生成资源发现报告，汇总各类型数量和 ID 列表。

**以下为降级路径的原生 API 命令（接口 A 不支持时使用）：**

> **参数格式说明**：插件模式使用小写连字符格式。Region 参数因产品而异：部分使用 `--biz-region-id`，部分使用 `--region`。若一种报错请尝试另一种。

**网络资源（先执行）：**
```bash
REGION="cn-hangzhou"  # 替换为实际 Region

# VPC（使用 --biz-region-id）
aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 \
  --output cols=VpcId,VpcName,CidrBlock,Status rows=Vpcs.Vpc 2>&1

# VSwitch（使用 --region）
aliyun vpc describe-vswitches --region $REGION --page-size 50 \
  --output cols=VSwitchId,VSwitchName,CidrBlock,ZoneId,VpcId rows=VSwitches.VSwitch 2>&1

# 安全组（使用 --biz-region-id）
aliyun ecs describe-security-groups --biz-region-id $REGION --page-size 50 \
  --output cols=SecurityGroupId,SecurityGroupName,VpcId rows=SecurityGroups.SecurityGroup 2>&1

# EIP（使用 --biz-region-id）
aliyun vpc describe-eip-addresses --biz-region-id $REGION --page-size 50 \
  --output cols=AllocationId,IpAddress,Status,InstanceId rows=EipAddresses.EipAddress 2>&1

# NAT 网关（使用 --biz-region-id）
aliyun vpc describe-nat-gateways --biz-region-id $REGION --page-size 50 \
  --output cols=NatGatewayId,Name,VpcId,Status rows=NatGateways.NatGateway 2>&1
```

**计算资源：**
```bash
# ECS 实例（使用 --biz-region-id）
aliyun ecs describe-instances --biz-region-id $REGION --page-size 50 \
  --output cols=InstanceId,InstanceName,Status,InstanceType,ZoneId rows=Instances.Instance 2>&1

# 云盘（使用 --biz-region-id）
aliyun ecs describe-disks --biz-region-id $REGION --page-size 50 \
  --output cols=DiskId,DiskName,Status,Size,Type,InstanceId rows=Disks.Disk 2>&1
```

**存储资源：**
```bash
# OSS Bucket（全局，不需要 Region）
aliyun ossutil ls oss:// 2>&1
```

**数据库资源：**
```bash
# RDS（使用 --biz-region-id）
aliyun rds describe-db-instances --biz-region-id $REGION --page-size 50 \
  --output cols=DBInstanceId,DBInstanceDescription,Engine,EngineVersion,DBInstanceStatus rows=Items.DBInstance 2>&1

# Redis（KVStore，使用 --biz-region-id）
aliyun r-kvstore describe-instances --biz-region-id $REGION --page-size 50 \
  --output cols=InstanceId,InstanceName,InstanceStatus,InstanceType rows=Instances.KVStoreInstance 2>&1

# MongoDB（DDS，使用 --biz-region-id）
aliyun dds describe-db-instances --biz-region-id $REGION --page-size 50 \
  --output cols=DBInstanceId,DBInstanceDescription,DBInstanceStatus rows=DBInstances.DBInstance 2>&1
```

**负载均衡：**
```bash
# SLB（传统负载均衡，使用 --biz-region-id）
aliyun slb describe-load-balancers --biz-region-id $REGION --page-size 50 \
  --output cols=LoadBalancerId,LoadBalancerName,LoadBalancerStatus,VpcId rows=LoadBalancers.LoadBalancer 2>&1

# ALB（应用型负载均衡，使用 --region）
aliyun alb list-load-balancers --region $REGION --max-results 50 2>&1
```

**DNS：**
```bash
# 云解析域名（全局，不需要 Region）
aliyun alidns describe-domains --page-size 50 \
  --output cols=DomainId,DomainName,RecordCount rows=Domains.Domain 2>&1
```

**资源发现结果为空时的处理：**

若某类资源（如 NAT 网关）发现结果为空但用户预期存在，主动排查：
- 确认资源是否在其他 Region
- 确认当前凭证是否有该资源的 Describe 权限
- 确认资源是否已被释放（可查询操作审计日志）
- 告知用户发现结果与预期不符，请用户确认后再继续

---

## Phase 5: 选择导入范围和深度

展示资源发现报告，询问用户：
- 全部导入还是选择特定资源类型？
- 是否按 VPC 范围过滤？
- 是否按 Tag 过滤？
- **导入深度策略**：
  1. 仅导入已发现的资源（不查询关联资源，深度=0）
  2. 导入一层关联资源（深度=1）
  3. 导入完整依赖树（深度=无限，推荐）

**构建资源依赖图（根据深度策略选择方式）**

根据用户选择的深度策略：

**深度=0（仅导入已发现资源）：**
- 跳过接口 B 调用
- 直接使用 `references/dependency-rules.md` 中的静态依赖规则对 Phase 4 发现的资源排序
- 生成导入顺序

**深度=1（导入一层关联资源）：**
- 对 Phase 4 发现的每个资源，若其类型在接口 B 支持列表中 → 调用接口 B（list-resource-relationships）获取直接关联的资源
- 对返回的关联资源不再递归调用接口 B
- 合并发现的资源和一层关联资源，对资源图做拓扑排序，生成导入顺序

**深度=无限（导入完整依赖树，推荐）：**
- 从 Phase 4 发现的资源中，识别无父依赖的根资源（VPC、OSS Bucket、DNS 域名、RAM 用户等）
- 对每个根资源，若其类型在接口 B 支持列表中 → 调用接口 B 获取其关联资源
- 对关联资源递归调用接口 B，直到没有新资源出现（新发现资源集合 == 空集）
- 对不支持接口 B 的资源类型 → 降级使用 `references/dependency-rules.md` 中的静态依赖规则推断
- 合并所有关系树，对资源图做拓扑排序，生成导入顺序

**降级路径（接口 B 不可用时）的静态导入顺序：**
```
Layer 0: VPC、OSS Bucket（无依赖）
Layer 1: VSwitch、安全组、EIP（依赖 VPC）
Layer 2: NAT 网关、SLB（依赖 VPC + VSwitch）
Layer 3: ECS 实例（依赖 VSwitch + 安全组）
Layer 4: 云盘（依赖 ECS）
Layer 5: RDS、Redis、MongoDB（依赖 VSwitch）
Layer 6: DNS 记录（依赖域名）
```

详细依赖规则参考 `references/dependency-rules.md`。

---

## Phase 6: 生成 Terraform HCL 代码

按资源类型逐批处理。对每类资源：

1. 执行获取详情的命令（JSON 格式）
2. 解析 JSON，生成对应 .tf 文件并写入工作目录

每类资源一个文件，文件名格式为 `<产品>_<资源类型>.tf`：

```
vpc_vpcs.tf
vpc_vswitches.tf
vpc_security_groups.tf
vpc_eips.tf
vpc_nat_gateways.tf
ecs_instances.tf
ecs_disks.tf
oss_buckets.tf
rds_instances.tf
kvstore_instances.tf
dds_instances.tf
slb_load_balancers.tf
alidns_domains.tf
alidns_records.tf
```

HCL 代码模板参考 `references/terraform-patterns.md`，示例参考 `examples/` 目录。

**跨资源引用解析（三层策略）**

生成每个资源的 HCL 时，对每个字段值按以下优先级判断是否替换为 terraform resource address：

1. **接口 B 关系优先**：若该资源是通过接口 B（list-resource-relationships）发现的，其父资源或关联资源已确定。结合 Phase 3 提取的引用字段白名单，找到当前资源中类型匹配的 `_id` 字段，直接替换为对应的 terraform resource address。关系是确定的，无需猜测。

2. **白名单 + 映射表双重匹配兜底**：对接口 B 未覆盖的资源，字段名在 Phase 3 提取的引用字段白名单中，且字段值在资源 ID 映射表中有对应条目，则替换为 terraform resource address。

3. **dependency-rules.md 静态规则兜底**：对以上两层均无法覆盖的边缘情况（复合 ID、非 `_id` 结尾的引用字段等），参考 `references/dependency-rules.md` 中的静态规则处理。

**资源 ID 映射表**

每生成一个资源块，立即向映射表追加一条记录：

```
<云资源 ID>  →  <terraform resource address>
# 示例：
vpc-bp1xxx   →  alicloud_vpc.vpc_prod_main
vsw-bp1aaa   →  alicloud_vswitch.vsw_prod_a
sg-bp1xxx    →  alicloud_security_group.sg_web
```

映射表写入 `.import/id-mapping.json`，后续阶段查表使用。

**其他关键原则：**
- 资源名称使用 `<type>_<name>` 格式（如 `alicloud_vpc.vpc_prod_main`）
- 密码/密钥字段使用变量（`var.db_password`）
- 保留原始 tags

---

## Phase 7: 导入 State

根据 Phase 5 生成的拓扑排序，生成完整的 `terraform import` 命令清单，展示给用户确认后按批次执行。

**批次 1 — 网络基础：**
```bash
terraform import alicloud_vpc.vpc_<name> <vpc-id>
terraform import alicloud_vswitch.vsw_<name> <vsw-id>
terraform import alicloud_security_group.sg_<name> <sg-id>
```

**批次 2 — 网络附属：**
```bash
terraform import alicloud_nat_gateway.nat_<name> <nat-id>
terraform import alicloud_eip_address.eip_<name> <eip-id>
```

**批次 3 — 计算：**
```bash
terraform import alicloud_instance.ecs_<name> <instance-id>
terraform import alicloud_disk.disk_<name> <disk-id>
```

**批次 4 — 存储：**
```bash
terraform import alicloud_oss_bucket.bucket_<name> <bucket-name>
```

**批次 5 — 数据库：**
```bash
terraform import alicloud_db_instance.rds_<name> <db-id>
terraform import alicloud_kvstore_instance.redis_<name> <redis-id>
terraform import alicloud_mongodb_instance.mongo_<name> <mongo-id>
```

**批次 6 — 负载均衡：**
```bash
terraform import alicloud_slb_load_balancer.slb_<name> <slb-id>
```

**批次 7 — DNS：**
```bash
terraform import alicloud_dns_domain.domain_<name> <domain-name>
```

每批执行后分析输出，处理常见错误：
- `ResourceNotFound`：资源 ID 有误，重新确认
- `PermissionDenied`：需要对应资源的 Describe 权限
- `already managed`：资源已在 state 中，跳过
- ID 格式错误：参考 `references/resource-types.md` 中的 import 格式

---

## Phase 8: 验证

执行以下命令验证导入结果：

```bash
# 列出 state 中所有资源
terraform state list 2>&1

# 执行 plan，目标是 No changes
terraform plan -refresh=true 2>&1
```

分析 plan 输出：
- `No changes` → 验证通过，进入 Phase 9
- 有 diff → 分析原因，参考 `references/terraform-patterns.md` 中的常见 diff 修复模式，给出修复方案并告知用户，用户确认后执行修复

常见 diff 原因：
- 标签格式不匹配（需调整 HCL 中的 tags 写法）
- 密码字段无法从 API 读取（用 `ignore_changes` 忽略）
- 计算字段差异（添加 `lifecycle { ignore_changes = [...] }`）
- 默认值差异（显式设置与云上一致的值）

---

## Phase 9: 资源关系图

执行以下命令生成资源关系图：

```bash
# 导出 state JSON
terraform show -json > .import/tf_state.json 2>&1

# 提取依赖关系
python3 -c "
import json, sys
with open('.import/tf_state.json') as f:
    state = json.load(f)
resources = state.get('values', {}).get('root_module', {}).get('resources', [])
print(f'总资源数: {len(resources)}')
for r in resources:
    deps = r.get('depends_on', [])
    if deps:
        for d in deps:
            print(f'  {d} --> {r[\"address\"]}')
" 2>&1
```

根据输出生成文本格式资源关系图（树状结构），展示：
- 网络层 → 计算层 → 数据层的依赖链
- 安全组的横切引用
- 负载均衡的后端绑定关系

示例格式参考 `examples/dependency-graph.txt`。

---

## 增量同步模式

已有 Terraform 工作目录时使用此模式，自动检测三类变化：

**1. 检测新增资源（云上有，state 没有）：**

执行以下命令对比 state 和云上的 ID 列表：
```bash
# 以 ECS 为例
terraform state list | grep alicloud_instance
aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 \
  --output cols=InstanceId rows=Instances.Instance 2>&1
```

对比两个列表，找出差集，生成新增资源的 HCL + import 命令，告知用户确认后执行。

**2. 检测删除资源（state 有，云上没有）：**

对 state 中每个资源执行存在性检查，若 API 返回空则执行：
```bash
terraform state rm alicloud_instance.<name>
```

**3. 检测配置漂移：**

执行以下命令检测漂移：
```bash
terraform plan -refresh=true 2>&1
```

详细增量同步方案参考 `references/incremental-sync.md`。

---

## 参考资料

- `references/resource-types.md` — 资源类型完整映射表（20+ 种资源）
- `references/terraform-patterns.md` — HCL 代码模板 + 常见 diff 修复
- `references/state-management.md` — terraform state 命令参考
- `references/api-commands.md` — aliyun CLI 命令速查（原生产品 API 降级路径）
- `references/dependency-rules.md` — 资源依赖层级和 import 顺序（接口 B 降级路径）
- `references/resource-hub-api.md` — ResourceCenter 接口使用指南（list-resource-types / search-resources / list-resource-relationships）
- `references/incremental-sync.md` — 增量同步详细方案
