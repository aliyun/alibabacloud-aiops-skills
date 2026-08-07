# 相关命令

## 本 skill 直接使用的命令

| 命令 | 用途 | 类型 |
|------|------|------|
| `add-project-member` | 添加项目成员并分配角色 | 写 |
| `remove-project-member` | 移除项目成员 | 写 |
| `update-project-member` | 更新成员角色 | 写 |
| `list-project-members` | 查询项目成员列表 | 读 |

## 辅助/上下游命令

| 命令 | 用途 | 备注 |
|------|------|------|
| `list-projects` | 查找目标项目 ID | 不知道项目 ID 时先查 |
| `get-project` | 获取项目详情（含模式信息） | 确认项目为 DEV_PROD 还是 BASIC |
| `get-project-by-name` | 按名称查找项目 | 已知项目名时用 |
