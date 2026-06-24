# Category Examples

This reference provides common category codes and examples for navigating the Alibaba Cloud Agent Skills catalog.

For the complete, current category list, call:

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

## Category Code Format

- Top-level category: use the category code directly, e.g. `computing`
- Child category: when supported, use dot notation, e.g. `computing.ecs`
- Multiple categories: comma-separate codes, e.g. `computing,database`
- If child code filtering is uncertain, confirm with `/openapi/for-agent/categories`, then use either dot notation or a semantic `keyword`

## Common Categories

| Code | Name | Typical Domains |
| --- | --- | --- |
| `computing` | 计算 | ECS, ECI, EHPC, ComputeNest, Alibaba Cloud Linux |
| `aiml` | 人工智能与机器学习 | PAI, Bailian, OpenSearch, AgentBay |
| `developertools` | 开发工具 | CLI guidance, developer workflows |
| `storage` | 存储 | OSS, SLS, Tablestore, PDS, HBR |
| `migrationom` | 迁移与运维管理 | OOS, Terraform import, resource management |
| `netcdn` | 网络与CDN | NIS, SAG, DCDN |
| `middleware` | 中间件 | CMS, API Gateway, PTS, STAROps |
| `doweb` | 域名与网站 | Domain, ICP filing, website building |
| `security` | 安全 | SAS, WAF, KMS, CFW, DDoS |
| `database` | 数据库 | RDS, PolarDB, Tair, MongoDB, DTS, DMS |
| `analyticscomputing` | 大数据计算 | DataWorks, MaxCompute, Flink, Hologres, Elasticsearch, Milvus |
| `entcmc` | 企业服务与云通信 | SMS, voice, Chat App |
| `mediaservices` | 媒体服务 | Live, MTS, ICE |
| `others` | 其他 | General solutions |
| `playbooks` | 场景化实战 | Troubleshooting and optimization playbooks |
| `solutions` | 阿里云级跨产品类目解决方案 | Cross-product solutions |

## Example Searches

### Browse A Top-Level Category

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Search Within A Category

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=RDS backup automation' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Try A Child Category Or Product Keyword

```bash
# Child category form, when supported
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=computing.ecs' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Product keyword fallback
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS instance management' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

## Domain Mapping Hints

| User Domain | Start With | Refinement Keywords |
| --- | --- | --- |
| ECS / servers | `computing` | ECS, instance, diagnosis, command, patch |
| RDS / PolarDB / Redis | `database` | RDS, PolarDB, Tair, SQL, backup, performance |
| OSS / files / logs | `storage` | OSS, SLS, upload, sync, index, media |
| Data projects | `analyticscomputing` | DataWorks, MaxCompute, Flink, Hologres |
| AI / RAG / knowledge base | `aiml` | Bailian, knowledge base, RAG, PAI |
| Security | `security` | SAS, WAF, KMS, vulnerability, bot |
| Network troubleshooting | `netcdn` | NIS, reachability, SAG, DCDN |
| Deployment / operations | `migrationom` | OOS, Terraform, patch, import, resource |
