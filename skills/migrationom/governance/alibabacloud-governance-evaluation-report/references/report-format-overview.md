# 报告格式：整体概览报告

**适用场景**：用户询问账号整体健康状况、成熟度评分、或要求生成综合报告，且未指定具体支柱或检测项。

**数据来源**：`overview` 模式输出的 JSON

**设计原则**：概览是漏斗入口，职责是**快速诊断 + 聚焦重点 + 引导深入**，而非穷举所有风险项。

---

## 格式模板

```markdown
## 治理检测报告

**最近一次检测时间**：{EvaluationTime, format: YYYY-MM-DD HH:MM:SS}

**整体情况概述**：当前治理检测综合评分为 {TotalScore*100:.1f} 分。
{Agent summarizes: 一两句话概括整体状况，点明问题集中在哪些支柱、最需要优先关注什么}

### 各支柱风险分布

| 支柱 | 高风险 | 中风险 | 建议优化 | 总结 |
| --- | --- | --- | --- | --- |
| 安全 | {Error} | {Warning} | {Suggestion} | {Agent: one sentence summary} |
| 稳定 | {Error} | {Warning} | {Suggestion} | {Agent: one sentence summary} |
| 成本 | {Error} | {Warning} | {Suggestion} | {Agent: one sentence summary} |
| 效率 | {Error} | {Warning} | {Suggestion} | {Agent: one sentence summary} |
| 性能 | {Error} | {Warning} | {Suggestion} | {Agent: one sentence summary} |

### 重点风险项

{Agent selects the most critical risk items to highlight.
Selection criteria — see "数量控制规则" section below.
Group selected items by logical topic/domain (e.g., "身份与访问安全", "网络安全", "数据保护").}

#### {Group Name}

| 风险项 | 风险等级 | 所属支柱 | 说明 |
| --- | --- | --- | --- |
| {DisplayName} | 高风险 | {CategoryCN} | {Agent: brief explanation of risk and impact} |
| ... | ... | ... | ... |

{Repeat for each group}

{After listing, add a summary of unlisted items:}
> 以上为当前最需关注的风险项。此外还有 {remaining_error} 项高风险、{warning_count} 项中风险、{suggestion_count} 项建议优化项未列出，可按支柱深入查看。

{If no high-risk items at all: "当前无高风险项。" and skip grouping.}

### 治理建议

{Agent generates 2-3 focused, actionable recommendations.
Each recommendation must have a title and directly reference the risk items shown above.}

#### 1. {Recommendation title}

{Specific actionable content, referencing the relevant risk items from the report.
Include concrete next step, e.g., "可进一步查看安全支柱的详细分析" or "建议优先处理 {DisplayName}".}

#### 2. {Recommendation title}

{...}

#### 3. {Recommendation title}

{...}

---

如需进一步了解，可以告诉我：

- 想深入了解某个支柱的详情，如"**分析下{pick the pillar with most risks}支柱的具体情况**"
- 想查看某个具体风险项的修复方案，如"**{pick a high-risk DisplayName from report} 怎么修复**"
- 想查看某类风险的不合规资源，如"**哪些资源存在 {pick a risk topic} 问题**"
```

---

## 数量控制规则

概览报告的核心是聚焦，Agent 根据以下准则灵活控制"重点风险项"展示数量：

- **高风险项 <= 5**：全部展示
- **高风险项 6-10**：全部展示，但每项的"说明"列保持简短（一句话）
- **高风险项 > 10**：展示优先级最高的 Top 10（按 RecommendationLevel: Critical > High > Medium > Suggestion 排序），其余在汇总行中用数字概括
- **中风险 / 建议优化项**：不在"重点风险项"中逐条列出，仅在支柱分布表和汇总行中以数字体现
- 若无高风险项但有中风险项，可挑选 Top 3-5 中风险项作为"重点关注项"展示

## 格式规则

- **禁止使用任何 emoji**，全文保持专业语气
- 支柱分布表中数字列直接填数字（如 `3`），不加前缀
- "总结"列：根据该支柱下检测项的实际结果，用一句话概述；全部合规时注明"全部合规"
- "重点风险项"按逻辑主题分组，跨支柱分组（如安全和效率的 RAM 相关问题可归入同一组）
- 治理建议必须带标题分段，2-3 条即可，每条关联具体风险项，不要泛泛而谈
- 汇总行用 blockquote 格式，准确填写未列出的各等级数量

## 后续引导规则

- 报告末尾必须附带后续引导，帮助用户继续深入分析
- 引导内容必须**基于报告中的实际数据**，不要给出泛泛的示例
- 从报告中挑选具体的支柱名、风险项名称、风险主题填入引导模板
- 引导以列表形式呈现，提供 2-3 个方向，每个方向用加粗标出建议的提问语句
- 优先引导用户进入风险最集中的支柱，或查看最严重的风险项
- 禁止使用 emoji
