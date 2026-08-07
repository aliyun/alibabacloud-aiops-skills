# 验收标准（create-and-publish-api）

## 功能验收

| 步骤 | 验收标准 |
|------|---------|
| 查询项目 | 返回至少 1 个项目，含 ProjectId |
| 创建 API | 返回成功，含 ApiId |
| 发布 API | 返回成功 |
| 验证发布 | 已发布列表中包含目标 API |

## 非功能验收

- [ ] SKILL.md 行数 ≤ 500
- [ ] 所有 CLI 命令含 --user-agent
- [ ] 写操作含 HITL 确认
- [ ] 大整数 ID 用字符串格式
- [ ] session-id 继承自父层
