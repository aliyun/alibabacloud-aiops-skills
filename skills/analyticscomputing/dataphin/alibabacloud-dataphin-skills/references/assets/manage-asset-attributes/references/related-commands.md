# 相关命令

> 本 skill 涉及的 Dataphin OpenAPI Action 及其插件模式命令。V6.3 新增 Action，若插件未收录用 OpenAPI SDK 兜底（版本 `2023-06-30`）。

| OpenAPI Action | 插件命令（收录后） | 类型 | 用途 |
|---|---|---|---|
| `GetAssetTypeAttributeCodes` | `aliyun dataphin-public get-asset-type-attribute-codes` | 只读 | 查资产类型（TABLE/COLUMN）下可用属性定义 |
| `UpdateAssetAttributes` | `aliyun dataphin-public update-asset-attributes` | 写 | 批量覆盖写 / 清空资产自定义属性值 |
| `GetAssetAttributes` | `aliyun dataphin-public get-asset-attributes` | 只读 | 写入后回读校验（详见 query-asset-details） |

> 相邻场景：`SubmitAssetsOnShelve`（批量上架资产）— 属独立场景，不在本 skill 范围。
