# Intent Keywords Mapping / 意图关键字映射

> **Extensibility / 可扩展性**: Add new intent categories below to route alerts to new skills.
> No code changes required - just add a new section following the template.
> 在下方添加新的意图类别即可路由告警到新技能，无需修改代码。

---

## Database Issue / 数据库问题

**Target Skill**: `alibabacloud-das-agent`

**Priority**: 1 (highest)

### Keywords / 关键字

| Category | Keywords (ZH) | Keywords (EN) |
|----------|---------------|---------------|
| Database Types | RDS, PolarDB, MongoDB, Redis, Tair, Lindorm, 数据库, DB | RDS, PolarDB, MongoDB, Redis, Tair, Lindorm, database, DB |
| Performance | 数据库慢, 查询慢, 慢查询, 慢SQL, SQL超时, 响应慢, 数据库性能 | database slow, slow query, query timeout, slow SQL, database performance |
| Connection | 数据库连接失败, 连不上数据库, 数据库连接超时, 连接数异常, 连接池满 | database connection failed, cannot connect to database, connection timeout, connection pool full |
| Resource | 数据库CPU高, 数据库内存高, 数据库磁盘满, 存储空间不足 | database high CPU, database memory high, database disk full, storage space low |
| Lock | 锁等待, 死锁, 锁超时, 元数据锁 | lock wait, deadlock, lock timeout, metadata lock |
| Health | 数据库健康检查, 实例状态检查, 安全基线, 健康巡检 | database health check, instance status, security baseline, health inspection |
| Instance Prefix | rm-, pc-, dds-, r-, tair-, ld- | rm-, pc-, dds-, r-, tair-, ld- |

### Keyword Patterns (Regex) / 关键字模式

```regex
# Instance ID patterns
rm-[a-z0-9]+
pc-[a-z0-9]+
dds-[a-z0-9]+
r-[a-z0-9]+
tair-[a-z0-9]+
ld-[a-z0-9]+

# Chinese patterns
(数据库|RDS|PolarDB|MongoDB|Redis).*(慢|超时|异常|连接失败|CPU高|内存高|磁盘满)
(慢查询|慢SQL|锁等待|死锁|连接池)
(数据库|DB).*(性能|健康|巡检|诊断)

# English patterns
(database|RDS|PolarDB|MongoDB|Redis).*(slow|timeout|error|connection failed|high CPU|high memory|disk full)
(slow query|slow SQL|lock wait|deadlock|connection pool)
```

### Required Parameters / 必需参数

| Parameter | Source | Fallback |
|-----------|--------|----------|
| instance_id | Extract rm-xxx/pc-xxx/dds-xxx/r-xxx from alert | Query CMDB by name |
| symptom | Extract from alert keywords | Ask user |
| db_type | Infer from instance ID prefix or keywords | Ask user |

### Example Alerts / 示例告警

```
✓ "RDS实例 rm-bp1xxx CPU使用率超过90%"
  → instance_id: rm-bp1xxx, symptom: CPU过高, db_type: RDS

✓ "数据库 rm-bp2xxx 慢查询告警，执行时间超过10秒"
  → instance_id: rm-bp2xxx, symptom: 慢查询

✓ "PolarDB集群 pc-2zeyyy 连接数异常增长"
  → instance_id: pc-2zeyyy, symptom: 连接数异常, db_type: PolarDB

✓ "Redis实例 r-bp3xxx 内存使用率95%"
  → instance_id: r-bp3xxx, symptom: 内存高, db_type: Redis

✓ "数据库响应慢，查询超时"
  → Need user to provide instance_id
```

---

## Network Connectivity Issue / 网络连通性问题

**Target Skill**: `alibabacloud-network-reachability-analysis`

**Priority**: 2

### Keywords / 关键字

| Category | Keywords (ZH) | Keywords (EN) |
|----------|---------------|---------------|
| Port Issues | 端口异常, 端口不通, 端口超时, 端口连接失败, 端口拒绝 | port unreachable, port timeout, port refused, port blocked |
| Network Issues | 网络不通, 网络异常, 网络超时, 网络连接失败, 无法访问 | network unreachable, network timeout, network error, connection failed, cannot access |
| Connectivity | 连接超时, 连接失败, 连接中断, 连接异常, 无法连接 | connection timeout, connection failed, connection refused, unable to connect |
| Reachability | 不可达, 无法到达, 路径不通, ping不通, 丢包 | unreachable, not reachable, path blocked, ping failed, packet loss |
| Service | 服务不可用, 服务超时, 服务异常, 访问超时, CLB/ALB后端服务异常 | service unavailable, service timeout, service error, access timeout |
| Analysis Keywords | 可达性分析, 网络路径分析, NIS分析, 连通性诊断, 网络排障 | reachability analysis, network path analysis, NIS analysis, connectivity diagnosis |

### Keyword Patterns (Regex) / 关键字模式

```regex
# Chinese patterns
(端口|网络|连接|服务).*(异常|不通|超时|失败|中断|不可达|拒绝)
(无法|不能).*(访问|连接|到达|ping)
(丢包|延迟高|不可达)

# English patterns
(port|network|connection|service).*(error|timeout|failed|refused|unreachable)
(cannot|unable).*(access|connect|reach)
(packet loss|high latency|unreachable)
```

### Required Parameters / 必需参数

| Parameter | Source | Fallback |
|-----------|--------|----------|
| source_resource_id | Extract from alert | Query CMDB by name |
| target_resource_id | Extract from alert | Query CMDB relationships |
| target_port | Extract from alert | Ask user |
| protocol | Extract from alert | Default: tcp |
| region_id | Query CMDB | Ask user |

### Example Alerts / 示例告警

```
✓ "ECS实例 i-bp1xxx 访问 i-bp2xxx 的 3306 端口超时"
  → source: i-bp1xxx, target: i-bp2xxx, port: 3306

✓ "web-server-01 无法连接 db-server-01，端口 3306 不通"
  → CMDB lookup: web-server-01 → i-uf6example001

✓ "Network timeout when accessing 10.0.1.5:8080 from 10.0.2.10"
  → Need CMDB to resolve IPs to resource IDs

✓ "端口22连接异常，请检查安全组配置"
  → port: 22, need user to provide resource IDs

✓ "instanceId: lb-uf6q48rodt25ybse7wbb1, 监控指标: 端口后端异常ECS实例数"
  → source: lb-uf6q48rodt25ybse7wbb1 (CLB)
  → target: CMDB lookup CLB backend servers → i-uf6xxx, i-uf6yyy
  → Analysis: CLB to each backend ECS reachability
```

---

## ECS Instance Issue / ECS 实例故障

**Target Skill**: `alibabacloud-ecs-diagnose`

**Priority**: 3

### Keywords / 关键字

| Category | Keywords (ZH) | Keywords (EN) |
|----------|---------------|---------------|
| Connection Issues | 服务器连不上, SSH超时, SSH连接失败, 远程桌面连不上, 无法登录, ECS实例访问不通, 实例访问不通, ECS访问不通 | server unreachable, SSH timeout, SSH failed, RDP failed, login failed, ECS instance unreachable |
| Performance Issues | 实例卡顿, CPU告警, CPU过高, 内存告警, 内存不足, 负载过高 | instance slow, high CPU, CPU alert, memory alert, out of memory, high load |
| Disk Issues | 磁盘满, 磁盘空间不足, 磁盘IO高, 存储告警 | disk full, disk space low, high disk IO, storage alert |
| Instance Status | 实例状态异常, 实例停止, 实例无响应, 系统事件 | instance abnormal, instance stopped, instance not responding, system event |
| Network in VM | 网站打不开, 服务无响应, 应用超时 | website down, service not responding, application timeout |
| Instance Prefix | i- | i- |

### Keyword Patterns (Regex) / 关键字模式

```regex
# Chinese patterns - HIGH PRIORITY (match first)
ECS实例.*访问不通
实例.*i-[a-z0-9]+.*访问不通
i-[a-z0-9]+.*访问不通

# Chinese patterns - general
(服务器|实例|ECS).*(连不上|超时|卡顿|异常|停止|无响应|访问不通)
(SSH|远程|登录).*(超时|失败|连不上)
(CPU|内存|磁盘|负载).*(告警|过高|不足|满)
(磁盘|存储).*(空间|满|不足)

# English patterns
(server|instance|ECS).*(unreachable|timeout|slow|abnormal|stopped)
(SSH|RDP|login).*(timeout|failed|unreachable)
(CPU|memory|disk|load).*(alert|high|full|low)
```

### Required Parameters / 必需参数

| Parameter | Source | Fallback |
|-----------|--------|----------|
| instance_id | Extract from alert | Query CMDB by name |
| region_id | Query CMDB | Ask user |
| symptom | Extract from alert keywords | Infer from context |

### Example Alerts / 示例告警

```
✓ "ECS实例 i-uf6xxx 访问不通"
  → instance_id: i-uf6xxx, symptom: 访问不通
  → NOTE: Single ECS instance unreachable → ECS diagnose (NOT NIS)

✓ "ECS实例 i-bp1xxx SSH连接超时"
  → instance_id: i-bp1xxx, symptom: SSH连接超时

✓ "服务器 web-server-01 CPU使用率超过90%"
  → CMDB lookup: web-server-01 → i-uf6example001
  → symptom: CPU过高

✓ "实例 i-uf6abc123 磁盘空间不足，使用率95%"
  → instance_id: i-uf6abc123, symptom: 磁盘满

✓ "ECS系统事件通知：i-bp2def456 计划重启"
  → instance_id: i-bp2def456, symptom: 系统事件

✓ "网站打不开，服务器无响应"
  → Need user to provide instance_id or CMDB lookup
```

---

## Template: Add New Intent / 模板：添加新意图

Copy and fill this template to add a new intent category:

```markdown
## [Intent Name] / [意图名称]

**Target Skill**: `skill-name`

**Priority**: [1-10, lower = higher priority]

### Keywords / 关键字

| Category | Keywords (ZH) | Keywords (EN) |
|----------|---------------|---------------|
| Category1 | 关键字1, 关键字2 | keyword1, keyword2 |

### Required Parameters / 必需参数

| Parameter | Source | Fallback |
|-----------|--------|----------|
| param1 | Extract from alert | Ask user |

### Example Alerts / 示例告警

```
✓ "Example alert message"
  → param1: value1, param2: value2
```
```

---

## Future Intent Categories (Planned) / 未来意图类别（计划中）

These categories are planned but not yet implemented:

| Intent | Target Skill | Status |
|--------|--------------|--------|
| Security Group Issue | `alibabacloud-resource-fault-repair` | Planned |
| Database Issue | `alibabacloud-das-agent` | ✅ Implemented |
| ECS Instance Issue | `alibabacloud-ecs-diagnose` | ✅ Implemented |
| Network Connectivity | `alibabacloud-network-reachability-analysis` | ✅ Implemented |
| Load Balancer Health | `clb-health-diagnosis` | Planned |

---

## Maintenance Notes / 维护说明

1. **Keyword Ordering**: More specific keywords should come before generic ones
2. **Priority**: Lower number = higher priority. When multiple intents match, use highest priority
3. **Testing**: After adding keywords, test with sample alerts to verify matching
4. **Deduplication**: Avoid duplicate keywords across different intents
