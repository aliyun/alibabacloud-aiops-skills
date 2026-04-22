# Category Examples

This reference provides common category codes and examples to help users navigate the Alibaba Cloud Agent Skills catalog.

## How to Use This Reference

1. **Find your domain** — Locate the relevant top-level category
2. **Browse subcategories** — Check if there's a specific subcategory for your need
3. **Use the category code** — Copy the code for use in search commands

## Category Code Format

- **Top-level category**: Use the category code directly (e.g., `computing`)
- **Subcategory**: Use dot notation (e.g., `computing.ecs`)
- **Multiple categories**: Separate with commas (e.g., `computing,database`)

## Common Categories

This is a reference guide. For the complete, up-to-date list, always run:
```bash
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 1. Computing (计算)

**Category Code**: `computing`

**Description**: Skills related to computing resources and instance management.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `computing.ecs` | 云服务器 ECS | Instance creation, batch operations, monitoring |
| `computing.eci` | 弹性容器实例 ECI | Container instance management |
| `computing.sae` | Serverless 应用引擎 SAE | Serverless app deployment |
| `computing.fc` | 函数计算 FC | Function as a Service, serverless functions |
| `computing.ehpc` | 弹性高性能计算 EHPC | High-performance computing clusters |

### Example Searches

```bash
# All computing skills
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Only ECS skills
aliyun agentexplorer search-skills \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# ECS batch operations
aliyun agentexplorer search-skills \
  --keyword "batch" \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 2. Database (数据库)

**Category Code**: `database`

**Description**: Skills for database management and operations.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `database.rds` | 云数据库 RDS | RDS instance management, backup, migration |
| `database.polardb` | 云原生数据库 PolarDB | PolarDB operations |
| `database.mongodb` | 云数据库 MongoDB | MongoDB management |
| `database.redis` | 云数据库 Redis | Redis cache management |
| `database.memcache` | 云数据库 Memcache | Memcache operations |
| `database.oceanbase` | OceanBase | Distributed database operations |

### Example Searches

```bash
# All database skills
aliyun agentexplorer search-skills \
  --category-code "database" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# RDS backup skills
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "database.rds" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Database and cache combined
aliyun agentexplorer search-skills \
  --category-code "database.rds,database.redis" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 3. Storage (存储)

**Category Code**: `storage`

**Description**: Skills for object storage, file systems, and backup.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `storage.oss` | 对象存储 OSS | Object storage operations, bucket management |
| `storage.nas` | 文件存储 NAS | Network attached storage |
| `storage.oss-hdfs` | OSS-HDFS | HDFS-compatible object storage |
| `storage.cpfs` | 文件存储 CPFS | Parallel file system |
| `storage.hbr` | 混合云备份 HBR | Hybrid cloud backup |

### Example Searches

```bash
# All storage skills
aliyun agentexplorer search-skills \
  --category-code "storage" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# OSS bucket management
aliyun agentexplorer search-skills \
  --keyword "bucket" \
  --category-code "storage.oss" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Backup solutions
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "storage" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 4. Networking (网络)

**Category Code**: `networking`

**Description**: Skills for VPC, load balancers, and network management.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `networking.vpc` | 专有网络 VPC | VPC creation, VSwitch management |
| `networking.slb` | 负载均衡 SLB | Load balancer configuration |
| `networking.eip` | 弹性公网 IP EIP | Elastic IP management |
| `networking.nat` | NAT 网关 | NAT gateway operations |
| `networking.cdn` | CDN | Content delivery network |
| `networking.ga` | 全球加速 GA | Global acceleration |

### Example Searches

```bash
# All networking skills
aliyun agentexplorer search-skills \
  --category-code "networking" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# VPC setup
aliyun agentexplorer search-skills \
  --keyword "setup" \
  --category-code "networking.vpc" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Load balancer configuration
aliyun agentexplorer search-skills \
  --category-code "networking.slb" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 5. Security (安全)

**Category Code**: `security`

**Description**: Skills for security management, access control, and compliance.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `security.ram` | 访问控制 RAM | IAM, user/role management |
| `security.kms` | 密钥管理服务 KMS | Key management, encryption |
| `security.waf` | Web 应用防火墙 WAF | Web application firewall |
| `security.ddos` | DDoS 防护 | DDoS protection |
| `security.sas` | 云安全中心 SAS | Security center operations |
| `security.saf` | 风险识别 SAF | Risk identification |

### Example Searches

```bash
# All security skills
aliyun agentexplorer search-skills \
  --category-code "security" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# RAM policy management
aliyun agentexplorer search-skills \
  --keyword "policy" \
  --category-code "security.ram" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Encryption and key management
aliyun agentexplorer search-skills \
  --category-code "security.kms" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 6. Container (容器)

**Category Code**: `container`

**Description**: Skills for Kubernetes, container registry, and container management.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `container.ack` | 容器服务 Kubernetes ACK | K8s cluster management |
| `container.acr` | 容器镜像服务 ACR | Container registry operations |
| `container.eci` | 弹性容器实例 ECI | Serverless containers |
| `container.ask` | Serverless Kubernetes ASK | Serverless K8s |

### Example Searches

```bash
# All container skills
aliyun agentexplorer search-skills \
  --category-code "container" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Kubernetes deployment
aliyun agentexplorer search-skills \
  --keyword "deployment" \
  --category-code "container.ack" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Container image management
aliyun agentexplorer search-skills \
  --category-code "container.acr" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 7. AI & Machine Learning (人工智能)

**Category Code**: `ai`

**Description**: Skills for AI services, machine learning, and model management.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `ai.pai` | 机器学习 PAI | Machine learning platform |
| `ai.nlp` | 自然语言处理 NLP | NLP services |
| `ai.vision` | 视觉智能 | Computer vision APIs |
| `ai.bailian` | 百炼 | Model service platform |

### Example Searches

```bash
# All AI skills
aliyun agentexplorer search-skills \
  --category-code "ai" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Machine learning workflows
aliyun agentexplorer search-skills \
  --keyword "training" \
  --category-code "ai.pai" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# NLP services
aliyun agentexplorer search-skills \
  --category-code "ai.nlp" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 8. Big Data (大数据)

**Category Code**: `bigdata`

**Description**: Skills for data processing, analytics, and data warehousing.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `bigdata.maxcompute` | MaxCompute | Data warehousing, big data processing |
| `bigdata.datav` | DataV | Data visualization |
| `bigdata.emr` | E-MapReduce | Hadoop/Spark cluster management |
| `bigdata.dataworks` | DataWorks | Data development and orchestration |
| `bigdata.hologres` | Hologres | Real-time data warehouse |

### Example Searches

```bash
# All big data skills
aliyun agentexplorer search-skills \
  --category-code "bigdata" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Data warehouse operations
aliyun agentexplorer search-skills \
  --category-code "bigdata.maxcompute" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Data visualization
aliyun agentexplorer search-skills \
  --category-code "bigdata.datav" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 9. Monitoring & Operations (监控运维)

**Category Code**: `monitoring`

**Description**: Skills for monitoring, logging, and operational management.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `monitoring.cms` | 云监控 CMS | Cloud monitoring, alerts |
| `monitoring.arms` | 应用实时监控 ARMS | APM, application monitoring |
| `monitoring.sls` | 日志服务 SLS | Log collection and analysis |
| `monitoring.oos` | 运维编排服务 OOS | Operation orchestration |

### Example Searches

```bash
# All monitoring skills
aliyun agentexplorer search-skills \
  --category-code "monitoring" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Alert configuration
aliyun agentexplorer search-skills \
  --keyword "alert" \
  --category-code "monitoring.cms" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Log analysis
aliyun agentexplorer search-skills \
  --category-code "monitoring.sls" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## 10. Developer Tools (开发者工具)

**Category Code**: `devtools`

**Description**: Skills for CI/CD, code management, and development workflows.

### Subcategories

| Subcategory Code | Name | Example Use Cases |
|------------------|------|-------------------|
| `devtools.cr` | 容器镜像服务 CR | Container registry |
| `devtools.rdc` | 云效 DevOps | CI/CD pipelines |
| `devtools.emas` | 移动研发平台 EMAS | Mobile development |

### Example Searches

```bash
# All developer tools
aliyun agentexplorer search-skills \
  --category-code "devtools" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# CI/CD pipeline
aliyun agentexplorer search-skills \
  --keyword "pipeline" \
  --category-code "devtools.rdc" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## Search Strategy Examples

### Example 1: Find Skills for a Specific Product

```bash
# I need skills for RDS database management
aliyun agentexplorer search-skills \
  --keyword "RDS" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Or search within database category
aliyun agentexplorer search-skills \
  --keyword "RDS" \
  --category-code "database" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Or directly search RDS subcategory
aliyun agentexplorer search-skills \
  --category-code "database.rds" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 2: Find Skills for Cross-Service Scenarios

```bash
# I need skills for VPC + ECS setup
aliyun agentexplorer search-skills \
  --keyword "VPC ECS" \
  --category-code "computing,networking" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Or search separately and combine results
aliyun agentexplorer search-skills \
  --keyword "network setup" \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 3: Find Skills by Feature

```bash
# I need backup-related skills across all services
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Or narrow to database backups
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "database" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 4: Browse a Domain

```bash
# I want to see all security-related skills
aliyun agentexplorer search-skills \
  --category-code "security" \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Narrow to specific security service
aliyun agentexplorer search-skills \
  --category-code "security.ram,security.kms" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## Tips for Category Selection

### 1. Start Broad, Then Narrow

```bash
# Step 1: Browse top-level category
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Step 2: If too many results, narrow to subcategory
aliyun agentexplorer search-skills \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Step 3: Add keyword for further filtering
aliyun agentexplorer search-skills \
  --keyword "batch" \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### 2. Use Multiple Categories for Cross-Service Skills

```bash
# Find skills that work with both ECS and RDS
aliyun agentexplorer search-skills \
  --category-code "computing.ecs,database.rds" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### 3. Combine Keyword with Category

```bash
# Most effective search strategy
aliyun agentexplorer search-skills \
  --keyword "monitoring" \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## Troubleshooting

### No Results for Category Code

**Possible causes**:
1. Category code doesn't exist (check spelling)
2. No skills in that category yet
3. Wrong separator (use dot for subcategory, comma for multiple)

**Solution**:
```bash
# List all valid categories
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Verify the correct category code
```

### Too Many Results

**Solution**: Add filters
```bash
# Add keyword filter
aliyun agentexplorer search-skills \
  --keyword "specific-feature" \
  --category-code "category" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Reduce to subcategory
aliyun agentexplorer search-skills \
  --category-code "category.subcategory" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Not Sure Which Category

**Solution**: Use keyword-only search first
```bash
# Search by product name only
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Check the categoryName and subCategoryName in results
# Then refine with category filter
```

---

## Quick Reference Table

| I Want To... | Search Strategy |
|--------------|-----------------|
| Find all skills for a product | `--keyword "ProductName"` |
| Browse a service category | `--category-code "category"` |
| Find specific subcategory skills | `--category-code "category.subcategory"` |
| Search across multiple categories | `--category-code "cat1,cat2,cat3"` |
| Find cross-service solutions | `--keyword "feature" --category-code "cat1,cat2"` |
| Narrow search results | Add both `--keyword` and `--category-code` |
| See all available categories | `aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills` |

---

## Notes

- **Always use `list-categories` first**: Get the most up-to-date category structure
- **Category names may change**: Official names and codes may be updated over time
- **Chinese and English**: Many skills support both language descriptions
- **Skill count varies**: Some categories have many skills, others have few
- **New categories added regularly**: Check back for new categories and skills
