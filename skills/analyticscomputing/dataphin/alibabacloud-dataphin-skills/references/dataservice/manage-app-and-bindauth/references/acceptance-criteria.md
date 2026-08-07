# 验收标准（manage-app-and-bindauth）

## 功能验收

| 步骤 | 验收标准 |
|------|---------|
| 创建应用 | 返回成功，含 AppId、AppKey、AppSecret |
| 添加成员 | 返回成功（可选步骤） |
| 授权 API | ⚠️ 当前 OpenAPI 暂不支持（实测），改走控制台；字段标识无法经 OpenAPI 获取 |
| 验证授权 | 已授权列表中包含目标 API，字段匹配（反查控制台或未来 OpenAPI 授权结果） |
| 获取凭证 | 返回有效 AppKey |

## 非功能验收

- [ ] SKILL.md 行数 ≤ 500
- [ ] 所有 CLI 命令含 --user-agent
- [ ] 写操作含 HITL 确认
- [ ] 大整数 ID 用字符串格式
- [ ] session-id 继承自父层
- [ ] 密钥重置含强 HITL 确认（不可回滚提示）
- [ ] 提示用户保存 AppKey/AppSecret
