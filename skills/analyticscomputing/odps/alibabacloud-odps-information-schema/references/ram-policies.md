# RAM 权限清单

> Related: [SKILL.md](../SKILL.md), [mcp-tools-reference.md](mcp-tools-reference.md)

## required_permissions

本 Skill 查询 MaxCompute Information Schema 元数据视图所需的 RAM 权限：

`odps:Describe` — 查询 IS 元数据视图内容
`odps:Select` — 读取 IS 视图数据
`odps:List` — 列举 information_schema 下的对象

> 以上权限均为只读权限，无通配符，符合最小权限原则。

## 授权说明

IS 视图包含租户级数据。**默认仅阿里云主账号可访问。** RAM 子账号需要通过租户级角色显式授权。

> 仅主账号或拥有 `Super_Administrator`/`Admin` 角色的账号可以进行授权。

### 授权步骤

1. 登录 [MaxCompute 控制台](https://maxcompute.console.aliyun.com/)，选择地域
2. 进入 **管理配置 > 租户管理**
3. 在 **角色管理** 标签页创建新角色，使用下方 Policy 模板
4. 在 **用户管理** 标签页添加成员并分配角色

### Policy 模板

```json
{
    "Statement":[
        {
            "Action":["odps:Describe", "odps:Select"],
            "Effect":"Allow",
            "Resource":["acs:odps:*:catalogs/system_catalog/schemas/information_schema/tables/*"]
        },
        {
            "Action":["odps:List"],
            "Effect":"Allow",
            "Resource":["acs:odps:*:catalogs/system_catalog/schemas/information_schema"]
        }
    ],
    "Version":"1"
}
```

### 注意事项

- Resource 目标为 `catalogs/system_catalog/schemas/information_schema/tables/*`，非 project 级资源
- 这是**租户级**角色绑定 — 在租户管理中配置，非 project 级
- `SYSTEM_CATALOG` project 为只读；查询必须从同一地域的普通 project 发起
