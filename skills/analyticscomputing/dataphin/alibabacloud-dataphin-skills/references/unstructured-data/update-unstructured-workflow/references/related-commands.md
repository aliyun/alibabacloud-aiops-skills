# 相关命令索引 · update-unstructured-workflow

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-pipeline-by-id` | 回读工作流现有全量配置（基线 + 更新后验证） | 读 |
| `update-pipeline` | 提交工作流更新（PipelineType=14，全量覆盖式） | 写 |
| `get-dataset` | 切换数据集版本/表时回读环境值（成组替换来源） | 读 |

## 命令速查（插件 >= 0.7.0 展平参数格式；旧版嵌套参数在新插件下被静默忽略，以 --help 为准）

```bash
# 回读工作流（pipeline-id / file-id / node-id 三选一）
aliyun dataphin-public get-pipeline-by-id --op-tenant-id "$TENANT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" --pipeline-id "$PIPELINE_ID"

# 提交更新（先 --cli-dry-run；pipeline-config 结构见 pipeline-config-spec.md）
aliyun dataphin-public update-pipeline --op-tenant-id "$TENANT_ID" \
  --context Env=PROD ProjectId="$PROJECT_ID" \
  --node-info "{\"PipelineId\": $PIPELINE_ID}" \
  --pipeline-type 14 \
  --pipeline-config "$(jq -c '<工作流配置路径>' pipeline-updated.json)" \
  --schedule-config '<回读的调度配置原样回传>' \
  --submit false --comment "<变更摘要>"

# 切数据集版本时回读环境值
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>"
```

> 所有 API 命令实际执行时必须追加 `--profile <有效 profile 名>`（认证信息统一来自阿里云 CLI 配置）与 `--user-agent AlibabaCloud-Agent-Skills/update-unstructured-workflow/{session-id}`（session-id 继承父 skill）。
