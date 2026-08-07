# 相关命令

> 本 skill 涉及的 Dataphin OpenAPI Action 及其插件模式命令（纯只读）。V6.3 新增/增强 Action，若插件未收录用 OpenAPI SDK 兜底（版本 `2023-06-30`）。

| OpenAPI Action | 插件命令（收录后） | 类型 | 用途 |
|---|---|---|---|
| `GetAssetAttributes` | `aliyun dataphin-public get-asset-attributes` | 只读 | 按 GUID 批量查资产自定义属性值 |
| `GetCatalogAssetDetails` | `aliyun dataphin-public get-catalog-asset-details` | 只读 | 查资产目录挂载 + 层级链 DirectoryChain（V6.3 增强） |

> 属性写入请见 `manage-asset-attributes`（`UpdateAssetAttributes`）。
