# Intent Mapping — 场景关键词映射解决方案

用户通常不会直接说解决方案名称，需要从模糊描述推断意图。以下是常见场景的关键词映射：

| 用户描述关键词 | 匹配的解决方案 |
|---|---|
| "搭个网站" / "建站" / "企业门户" | `build-a-website` |
| "AI 问答" / "智能客服" / "RAG" / "知识库" | `analyticdb-rag`, `elasticsearch-ai-assistant`, `tongyi-langchain` |
| "日志分析" / "日志平台" / "实时日志" | `real-time-log-analysis-selectdb`, `log-management-platform` |
| "监控告警" / "Prometheus" / "可观测" | `prometheus-cloud-monitoring`, `end-to-end-tracing-diagnostics` |
| "高可用" / "容灾" / "多活" | `serverless-ha`, `tltcamanidl` |
| "小程序" / "微信" | `develop-your-wechat-mini-program-in-10-minutes` |
| "AI 绘画" / "Stable Diffusion" / "图像生成" | `pai-eas` |
| "数据库迁移" / "MongoDB 迁移" | `migrate-self-managed-mongodb-to-cloud` |
| "读写分离" | `rds-read-write-splitting` 或 `redis-read-write-splitting-tair-proxy` |
| "DeepSeek" / "个人网站 + AI" | `ecs-and-deepseek-build-personal-website` |
| "消息队列" / "RocketMQ" / "RabbitMQ" | `rocketmq-*`, `rabbitmq-serverless` |
| "微服务" / "流量治理" / "限流熔断" | `mse-traffic-protection` |
| "容器" / "ACK" / "K8s" | `ack-services`, `nginx-ingress` |
| "无服务器" / "Serverless" | `serverless-ha` |
| "数据可视化" / "大屏" / "DataV" | `datav-for-atlas`, `datav-for-digitalization` |
| "大模型安全" / "LLM 安全" | `large-language-model-security-system` |
| "AI 应用" / "百炼" / "Model Studio" | `ai-applications-model-studio` |
| "WordPress" / "博客" / "MySQL 建站" | `mysql-rds` |
| "ClickHouse" / "HTAP" | `rds-clickhouse-htap` |
| "Hologres" / "OLAP" | `hologres-olap` |
| "PolarDB + AI" / "PolarDB 向量搜索" | `polardb-ai-search`, `polardb-mysql-mcp` |
| "物联网" / "时序数据" | `lindorm-data-process` |
| "CentOS 迁移" / "系统迁移" | `centos-alinux-migration` |
| "分布式任务调度" / "定时任务" | `mse-schedulerx` |
| "OLAP 数仓" | `hologres-olap`, `rds-clickhouse-htap` |

## 匹配规则

1. **Exact match first** — 用户说了解决方案名称，直接匹配
2. **Keyword match** — 用户描述包含上述关键词，映射到对应方案
3. **Partial match OK** — 描述与某个方案的领域有部分重叠，作为候选
4. **Ambiguous → list candidates** — 2-3个方案都匹配时，列出让用户选择：
   ```
   找到以下几个匹配的方案，请选择：
   1. analyticdb-rag — 基于 AnalyticDB + 通义千问的 RAG 智能问答
   2. elasticsearch-ai-assistant — Elasticsearch + Kibana 智能运维助手
   3. tongyi-langchain — 通义千问 + LangChain 对话服务
   ```