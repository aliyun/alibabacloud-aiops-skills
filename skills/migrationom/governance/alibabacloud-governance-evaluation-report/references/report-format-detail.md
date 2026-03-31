# 报告格式：单项检测详情分析报告

**适用场景**：

- 用户询问某个具体检测项的详情，如"MFA 那个检测项是什么情况""apbxftkv5c 这个检测项帮我看看"
- 用户询问某个检测项的修复方法，如"MFA 怎么修""如何修复高危端口暴露的问题"
- 用户查看某个检测项的不合规资源列表，如"哪些用户没开 MFA""哪些安全组开放了高危端口"

**数据来源**：

- 检测项详情：`detail --id <metric-id>` 或 `detail --keyword <keyword>` 模式输出的 JSON
- 不合规资源：`resources --id <metric-id>` 模式输出的 JSON（按需获取）

---

## 格式模板

### 仅查看检测项详情（不含资源列表）

```markdown
## 检测项详情：{DisplayName}

| 属性 | 值 |
| --- | --- |
| 检测项 ID | `{Id}` |
| 所属支柱 | {CategoryCN} |
| 优先级 | {RecommendationLevelCN} |
| 当前状态 | {Risk → 高风险/中风险/低风险/合规} |
| 合规率 | {Compliance*100:.0f}% |
| 不合规资源数 | {NonCompliant, if available, otherwise "N/A"} |
| 修复后预计提分 | +{PotentialScoreIncrease:.1f} 分 {if available, otherwise omit this row} |

### 检测说明

{Description — the full description of what this check item evaluates}

### 当前风险分析

{Agent analyzes:
- Why this check item is in its current risk state
- What the compliance rate means in practical terms
- Potential impact of non-compliance (security, cost, stability implications)
}

### 修复方案

{Parse Remediation array and present each remediation option.
For each remediation:}

#### 方案{N}：{RemediationType → "手动修复"/"分析修复"/"快速修复"}

{For each step in Steps:}

**{Classification, if present}**

{Description — what this step does}

{If Suggestion is present:}
> 建议：{Suggestion}

{If CostDescription is present:}
> 费用说明：{CostDescription}

{If Notice is present:}
> 注意：{Notice}

{If Guidance is present, for each guidance entry:}

**{Title}**

{Content}

{If ButtonRef is present:}
[{ButtonName}]({ButtonRef})

{End of steps}
{Repeat for each remediation option}
```

### 含不合规资源列表

当用户明确要求查看不合规资源，或 Agent 判断列出具体资源有助于用户理解问题时，在上述报告末尾追加资源列表部分。

需要额外调用 `resources --id <metric-id>` 获取资源数据。

```markdown
### 不合规资源列表

共 {TotalCount} 个不合规资源：

| 资源 ID | 资源名称 | 资源类型 | 地域 | 关键属性 |
| --- | --- | --- | --- | --- |
| {ResourceId} | {ResourceName, or "-"} | {ResourceType} | {RegionId} | {Agent: pick 1-2 most relevant properties from Properties} |
| ... | ... | ... | ... | ... |

{If TotalCount > displayed count:}
> 仅展示前 {N} 条，共 {TotalCount} 条。可通过增加 `--max-results` 查看更多。

### 处置建议

{Agent generates specific remediation advice based on the actual non-compliant resources:
- Group similar resources if applicable (e.g., "以下 5 个 RAM 用户均未启用 MFA")
- Provide concrete next steps for remediation
- Highlight any resources that need prioritized attention (e.g., root account, production resources)
}

---

### 相关检测项

{Agent looks through the pillar data (from the same overview/pillar query results already cached)
and picks 2-5 related check items that share the same Category or are topically related.
Only include items that have risk (Risk != "None"). If no related risky items, omit this section.}

该检测项所属的{CategoryCN}支柱下，还有以下相关风险项值得关注：

| 检测项 | 风险等级 | 合规率 |
| --- | --- | --- |
| {DisplayName} | {RiskCN} | {Compliance*100:.0f}% |
| ... | ... | ... |

---

如需进一步了解，可以告诉我：

- 想查看上述某个相关检测项的详情，如"**{pick a related DisplayName} 的详细情况**"
- 想查看该检测项的不合规资源，如"**{current DisplayName} 有哪些不合规资源**" {only if resource list was not already shown}
- 想查看{CategoryCN}支柱的整体情况，如"**分析下{CategoryCN}支柱的所有检测项**"
```

---

## 格式规则

- **禁止使用任何 emoji**，全文保持专业语气
- 检测项属性表使用竖排 key-value 布局，不使用横排表格
- "当前状态"字段将 Risk 枚举值翻译为中文：`Error` → 高风险，`Warning` → 中风险，`Suggestion` → 低风险，`None` → 合规
- 修复方案部分忠实呈现 API 返回的 Remediation 数据，不要编造修复步骤
- 如 Remediation 数据中包含控制台链接（ButtonRef），保留为 markdown 链接格式
- 不合规资源列表中的"关键属性"列：从 Properties 中挑选最能说明问题的 1-2 个属性（如 `MFAEnabled: false`）
- 若资源数量较多（>20），建议只展示前 20 条并提示总数
- 当 `detail --keyword` 匹配到多条结果时，先展示匹配列表让用户选择，不要自动展开所有详情

## 后续引导规则

- 报告末尾必须附带后续引导，帮助用户继续探索
- 引导内容必须**基于报告中的实际数据**，从报告中挑选具体的检测项名、支柱名填入引导模板
- 引导以列表形式呈现，提供 2-3 个方向，每个方向用加粗标出建议的提问语句
- 引导方向应根据当前上下文灵活选择：
  - 若当前报告未含资源列表，可引导查看不合规资源
  - 若已含资源列表，可引导查看所属支柱整体情况或回到概览
  - 若有相关检测项，优先引导查看某个相关检测项的详情
- "相关检测项"部分：从同支柱下挑选有风险的检测项（排除当前项），优先选择同主题或高风险的项；若同支柱下无其他风险项则省略该部分
- 禁止使用 emoji
