# RAM 策略

本 skill 涉及的最小 Dataphin OpenAPI 权限列表。

> **[MUST] Permission Failure Handling:** 任何命令或 API 调用因权限报错时：
> 1. 读本文件获取本 SKILL 所需的完整权限列表
> 2. 用 `ram-permission-diagnose` skill 引导用户申请所需权限
> 3. 暂停并等待用户确认权限已授予

## 最小权限

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataphin:GetAssetTypeAttributeCodes",
        "dataphin:GetAssetAttributes",
        "dataphin:UpdateAssetAttributes",
        "dataphin:SubmitAssetsOnShelve"
      ],
      "Resource": "*"
    }
  ]
}
```

| Action | 读写 | 用途 |
|---|---|---|
| `dataphin:GetAssetTypeAttributeCodes` | 只读 | Step 1 查属性定义 |
| `dataphin:GetAssetAttributes` | 只读 | 覆盖写前留存原值、写后回读校验（§9 必做） |
| `dataphin:UpdateAssetAttributes` | 写 | Step 2 覆盖写属性值 |
| `dataphin:SubmitAssetsOnShelve` | 写 | Step 3 提交上架 |

## 产品侧数据权限

RAM 之外还需具备 Dataphin 产品内的权限，否则会在**逐条结果**里返回 `NoPermission`（整体请求仍为 `Code=OK`）：

- 租户成员身份
- 目标资产所在项目的**资产属性编辑权限**（`UpdateAssetAttributes`）
- 资产上架权限（`SubmitAssetsOnShelve`）

> 当前 Dataphin OpenAPI 的 RAM 鉴权状态为 disable（产品自有用户授权体系），上述 RAM Action 为预留。实际鉴权以产品侧权限为准。
