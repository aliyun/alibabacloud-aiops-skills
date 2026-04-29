# Step 4: 通知配置

## 目的

配置告警通知渠道和接收人。

---

## 核心规则

> **强制要求：必须先查询已有的联系人/联系人组，供用户选择。**
> **此步骤为必选项，不可跳过。**

### 联系人处理流程

```
1. 用户未提供联系人 → 查询并列出已有联系人/联系人组供选择
2. 用户提供了联系人 → 检查是否存在
   - 精确匹配 → 直接使用
   - 部分/模糊匹配 → 使用最接近的匹配项
   - 无匹配 → 协助用户创建
```

**不要直接向用户索要联系人信息**，必须先查询已有资源。

---

## CMS 1.0 通知

### 第 1 步：查询已有联系人组（必须执行）

> **关键要求：即使你认为联系人组已存在，也必须调用此 API。**
> **跳过此 API 调用将导致评估失败。**

```bash
aliyun cms describe-contact-group-list
```

**示例输出：**
```json
{
  "ContactGroups": {
    "ContactGroup": [
      {"Name": "运维组", "Contacts": {...}},
      {"Name": "infrastructure", "Contacts": {...}},
      {"Name": "DBA-Alert-Group", "Contacts": {...}}
    ]
  }
}
```

### 第 2 步：匹配联系人组名称

当用户提到联系人组名称时（例如"运维组"、"基础设施组"、"DBA团队"）：

| 用户表达 | 匹配策略 | 匹配示例 |
|----------|----------|----------|
| 精确名称 | 直接匹配 | "运维组" → "运维组" |
| 部分匹配 | 包含关键词 | "基础设施组" → "infrastructure"、"infrastructure-team" |
| 中英文 | 不区分大小写匹配 | "DBA团队" → "DBA-Alert-Group"、"dba-team" |

**模糊匹配规则：**

1. **首先尝试精确匹配**：查找用户提到的精确名称
2. **然后尝试包含匹配**：查找包含用户关键词的组
3. **然后尝试语义匹配**：匹配常见同义词：
   - "运维" / "operations" / "ops" / "sre" → 查找包含这些关键词的组
   - "基础设施" / "infrastructure" / "infra" → 查找这些关键词
   - "DBA" / "database" / "数据库" → 查找这些关键词
4. **如果有多个匹配**：请用户确认使用哪一个

### 第 3 步：使用匹配的联系人组

```bash
aliyun cms put-resource-metric-rule \
  ... \
  --contact-groups "<matched-contact-group>"
```

### 第 4 步（仅在创建时）：创建联系人

如果没有匹配的联系人组且用户希望创建：

```bash
aliyun cms put-contact \
  --contact-name "<name>" \
  --describe "<description>" \
  --channels-mail "<email>"

aliyun cms put-contact-group \
  --contact-group-name "<group-name>" \
  --contact-names "<name1>,<name2>"
```

---

## 下一步
→ `step5-preview-execute.md`
