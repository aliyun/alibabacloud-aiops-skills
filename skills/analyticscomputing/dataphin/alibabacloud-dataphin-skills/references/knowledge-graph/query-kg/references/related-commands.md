# 相关命令索引（query-kg）

## 命令列表

| CLI 命令 | 用途 | 关键参数 |
|------|------|----------|
| `exec-kg-cypher` | 执行 Cypher 图查询（只读） | `--exec-command`（JSON：`{Query, Limit, Params}`） |
| `get-kg-neighbor` | 获取邻居节点遍历 | `--entity-data-id` + `--entity-type`（均必填）、`--neighbors-query`（JSON：`{Depth, DirectionType, RelationTypes}`） |

> **CLI 原生支持**：两个 API 已正式发布（Online version: v6.1.1）并注册到 `aliyun-cli-dataphin-public` 插件（>= 0.7.1），直接 `aliyun dataphin-public <cmd>` 调用。命令报 unknown command 时先 `aliyun plugin update`。

## 通用参数

所有命令均需：
- `--op-tenant-id` — 租户 ID
- `--workspace-id` — 知识图谱空间 ID
- `--user-agent AlibabaCloud-Agent-Skills/query-kg/{SESSION_ID}` — 可观测标识
- 独立部署环境加 `--endpoint dataphin-openapi.<env>.aliyun.com`（不带 `https://` 前缀）

## 兜底脚本（旧版本独立部署）

独立部署 < v6.1.1 未发布 KG OpenAPI 时，使用 `scripts/query-kg.py`（Python Tea SDK `call_api()` 泛化调用）：

```bash
pip install alibabacloud-tea-openapi alibabacloud-tea-util
# 环境变量：ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET、DATAPHIN_ENDPOINT/TENANT_ID/WORKSPACE_ID
python3 scripts/query-kg.py cypher --query "MATCH (n) RETURN count(n) AS cnt" [--limit N] [--ignore-ssl]
python3 scripts/query-kg.py neighbor --entity-data-id <DataId> --entity-type <Type> [--direction Both] [--depth 1] [--ignore-ssl]
```

- 只读，无写操作；`--ignore-ssl` 用于独立部署自签证书；凭证从环境变量读取、不打印
- 业务失败（`Success:false`）返回非零退出码，便于脚本串联
- SDK 泛化调用实测暗坑（`ExecCommand` / `EntityDataId` / POST 方法）见 [KG Query API 参数参考](./kg-query-api-params.md)

## 关联 Skill 命令

如需写入数据或管理 Schema，请参考：
- `manage-kg-schema` — Schema 导出/导入/发布
- `manage-kg-knowledge` — 实体/关系增删改查、批量导入
