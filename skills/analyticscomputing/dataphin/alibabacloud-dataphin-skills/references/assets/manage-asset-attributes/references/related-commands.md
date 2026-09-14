# 相关命令

> 本 skill 涉及的 Dataphin OpenAPI Action。这 3 个 Action（`GetAssetTypeAttributeCodes` / `UpdateAssetAttributes` / `SubmitAssetsOnShelve`）为 V6.3 新增，**CLI 插件普遍未收录**，且实测入参形态与官方文档不一致，故统一走 [`../scripts/`](../scripts/) 手写签名直调（API 版本 `2023-06-30`）。

## 脚本子命令

| 子命令 | 对应 Action | 类型 | 用途 |
|---|---|---|---|
| `codes --asset-type <T>` | `GetAssetTypeAttributeCodes` | 只读 | 查资产类型下可用属性定义；`--writable-only` 只看可写项，`--required-only` 只看必填项 |
| `read --guid <G>` | `GetAssetAttributes` | 只读 | 回读资产当前属性值（覆盖写前留存原值 / 写后校验） |
| `update --guid <G> --set k=v` | `UpdateAssetAttributes` | **写** | 批量覆盖写 / 清空属性值，内置写后回读校验 |
| `shelve --guid <G>` | `SubmitAssetsOnShelve` | **写** | 提交上架；失败无副作用，兼作上架预检 |

```bash
# 典型闭环
python3 scripts/asset_attr_shelve.py codes  --asset-type TABLE --writable-only
python3 scripts/asset_attr_shelve.py read   --guid "$G"
python3 scripts/asset_attr_shelve.py update --asset-type TABLE --guid "$G" --set shelve_description="已治理"
python3 scripts/asset_attr_shelve.py shelve --guid "$G"
```

`--set` 取值约定：`code=value`；多值用 `||` 分隔；空串（`--set code=`）传 `values=[]`，**仅 `DROPDOWN_MULTI` 多选属性保证清空**，非多选属性请改用覆盖为新值。

## 退出码约定

| 退出码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 部分或全部失败（含写入被静默丢弃） |
| 2 | 参数或环境变量错误 |
| 3 | 上架因「资产信息未完善」被拒，需按 SKILL.md §8 Step 3 向用户索要缺失项 |

## 实测入参契约

统一：`POST` RPC 路径 `/`、业务参数**参与签名并平铺放 JSON body**、`OpTenantId` / `OpUserId` 留 query。

| Action | 包裹参数名 | 内部字段大小写 |
|---|---|---|
| `GetAssetTypeAttributeCodes` | 无包裹，平铺 `assetType` | camelCase |
| `UpdateAssetAttributes` | `UpdateCommand` | camelCase |
| `SubmitAssetsOnShelve` | `SubmitCommand`（仅收 `guidList`） | camelCase |
| `GetAssetAttributes` | `QueryCommand` | camelCase |

> 业务参数误放 query 会报网关 502「`AddFieldOperator is not applicable to JsonNull`」，这是入参位置错误的特征信号，不是权限问题。

## 相邻场景（不在本 skill 范围）

| Action | 说明 |
|---|---|
| `SubmitAssetsOffShelve` | 资产下架，需必填下架说明 |
| `ListCatalogAssets` / `GetCatalogAssetDetails` | 资产检索与详情，网关必填参数形态与本组不同，未在本 skill 打通 |
