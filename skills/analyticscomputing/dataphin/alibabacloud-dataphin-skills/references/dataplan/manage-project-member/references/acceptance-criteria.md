# 验收标准

## 功能验收

| # | 验收项 | 验证方法 |
|---|---|---|
| 1 | 添加单个成员到 DEV 环境 | `add-project-member` + `list-project-members` 反查 |
| 2 | 添加单个成员到 PROD 环境 | `add-project-member` (Env=PROD) + `list-project-members` 反查 |
| 3 | 批量添加多个成员 | `add-project-member` (UserList 含多个) + `list-project-members` |
| 4 | 更新成员角色 | `update-project-member` + `list-project-members` 反查角色变更 |
| 5 | 移除单个成员 | `remove-project-member` + `list-project-members` 确认不在列表 |
| 6 | 批量移除成员 | `remove-project-member` (UserIdList 含多个) + `list-project-members` |
| 7 | 分页查询成员列表 | `list-project-members` 指定 PageSize/PageNo |

## 合规验收

- [ ] SKILL.md 正文 ≤ 500 行
- [ ] 所有 `aliyun` API 命令包含 `--user-agent` 标记
- [ ] 写操作（add/remove/update）包含 HITL 执行前确认
- [ ] 19 位 snowflake ID 示例中用引号包住
- [ ] 必备 references 文件齐备
