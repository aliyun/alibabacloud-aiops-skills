# RAM 策略

本 skill 涉及的最小 Dataphin OpenAPI 权限列表。**板块 ①③④ 只读；板块 ② 数据预览会起即席查询任务，需要开发态执行权限。**

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 最小权限（全四板块）

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:GetCatalogAssetDetails",
        "dataphin:GetAssetAttributes",
        "dataphin:ListCatalogAssets",
        "dataphin:GetTableLineages",
        "dataphin:GetTableColumnLineages",
        "dataphin:GetQualityWatchByObjectId",
        "dataphin:ListQualityWatches",
        "dataphin:ListQualityRules",
        "dataphin:ListQualityRuleTasks",
        "dataphin:ListQualityWatchTasks",
        "dataphin:ExecuteAdHocTask",
        "dataphin:GetAdHocTaskResult",
        "dataphin:GetAdHocTaskLog",
        "dataphin:ListDataSourceWithConfig",
        "dataphin:GetBizMetricByName",
        "dataphin:GetDataServiceApiDocument"
      ],
      "Resource": "*"
    }
  ]
}
```

## 按板块裁剪

只用其中某几个板块时，可只授对应 Action：

| 板块 | Action |
|---|---|
| ① 属性 / 字段 / 使用说明（全 5 类资产必需） | `GetCatalogAssetDetails`、`GetAssetAttributes`、`ListCatalogAssets` |
| ② 数据预览（仅表 / 技术指标） | `ExecuteAdHocTask`、`GetAdHocTaskResult`、`GetAdHocTaskLog`、`ListDataSourceWithConfig` |
| ③ 血缘（仅表 / 技术指标） | `GetTableLineages`、`GetTableColumnLineages` |
| ④ 质量概况（仅表 / 技术指标） | `GetQualityWatchByObjectId`、`ListQualityWatches`、`ListQualityRules`、`ListQualityRuleTasks`、`ListQualityWatchTasks`、`GetQualityWatchTask` |
| ⑤ 业务指标（相关指标 / 使用说明） | `GetBizMetricByName` |
| ⑥ 数据服务 API（API 文档） | `GetDataServiceApiDocument` |
| ⑦ 仪表板（图表信息） | 无额外 Action，复用 `GetCatalogAssetDetails` |

## 注意

- 除板块 ② 外均为只读 Action，不涉及任何写权限。
- **板块 ② 是唯一的非只读动作**：`ExecuteAdHocTask` 会真实读取表数据并消耗计算资源。授权前请确认该 AK 的数据可见范围符合预期——预览等同于把表数据取出来。
- 独立部署环境的模块级授权与公共云 RAM 是两套：POC/独立部署上还需该租户为此 AK 显式开通对应模块的 OpenAPI 访问，否则会出现 `Code=OK` 但 `Data=null` 的静默空结果（不是权限报错，容易误判成"没有数据"）。
