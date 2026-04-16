# 子账号开通 SysOM 与服务关联角色（SLR）

子账号在 **Alinux 控制台** 开通 SysOM 时，若提示缺少 **`ram:CreateServiceLinkedRole`**（或同类 RAM 权限），需要由**主账号**或具备 RAM 管理权限的账号处理，或按组织规范为子账号授予相应权限。

**常见处置思路**（以控制台与租户策略为准）：

1. 使用具备权限的账号完成 SysOM 开通（SLR 通常随开通自动创建 **`AliyunServiceRoleForSysom`**）。
2. 在 **RAM 控制台** 为子账号附加允许创建**服务关联角色**的自定义策略（策略内容需符合贵组织安全要求）。
3. 由管理员预先完成开通与 SLR 创建后，子账号仅使用 SysOM 能力。

更完整的认证与 AK/RAM Role 路径见同目录 [authentication.md](./authentication.md)、[openapi-permission-guide.md](./openapi-permission-guide.md)。
