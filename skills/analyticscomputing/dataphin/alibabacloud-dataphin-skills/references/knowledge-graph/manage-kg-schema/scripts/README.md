# manage-kg-schema/scripts/

知识图谱 Schema 管理的辅助脚本。

> **定位说明**：KG OpenAPI 已正式发布（v6.1.1）并注册到 CLI 插件（>= 0.7.1），新环境一律优先 CLI 原生命令（见 SKILL.md）。`import-schema.py` 等 SDK 脚本仅用于独立部署 < v6.1.1 的旧环境兜底；`validate-schema.py` 为纯本地校验，不受影响，两种模式下均推荐先跑。

## 脚本清单

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `import-schema.py` | （旧环境兜底）Schema 导入端到端流程：本地校验 → 导出基线 → 导入 → 验证 → 发布 → 轮询 | PyYAML + Tea SDK |
| `validate-schema.py` | Schema YAML 本地预校验（编码/类型/必填字段/唯一性），纯本地 | PyYAML |

## import-schema.py

### 用法

```bash
# 设置环境变量
export ALIBABA_CLOUD_ACCESS_KEY_ID="<AK>"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="<SK>"
export DATAPHIN_ENDPOINT="<YOUR_DATAPHIN_ENDPOINT>"
export DATAPHIN_TENANT_ID="<OpTenantId>"
export DATAPHIN_WORKSPACE_ID="<WorkspaceId>"

# 执行导入（含发布）
python3 scripts/import-schema.py schema.yaml --ignore-ssl

# 仅导入不发布
python3 scripts/import-schema.py schema.yaml --ignore-ssl --skip-publish

# 使用 Merge 策略（增量合并）
python3 scripts/import-schema.py schema.yaml --ignore-ssl --merge-strategy Merge
```

### 选项

| 选项 | 说明 |
|------|------|
| `--skip-export` | 跳过导入前的 Schema 导出 |
| `--skip-publish` | 导入后不自动发布 |
| `--ignore-ssl` | 跳过 SSL 证书验证 |
| `--merge-strategy S` | 合并策略：Replace（默认）或 Merge |

## validate-schema.py

### 用法

```bash
# 仅校验
python3 scripts/validate-schema.py schema.yaml

# 自动修复 + 校验
python3 scripts/validate-schema.py schema.yaml --fix
```

可独立使用，也可被 `import-schema.py` 作为模块自动调用（Step 0）。
