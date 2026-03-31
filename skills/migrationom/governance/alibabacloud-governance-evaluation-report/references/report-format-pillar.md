# 报告格式：支柱 / 关键词聚合分析报告

**适用场景**：

- 用户按支柱维度分析，如"安全方面有哪些问题""看下成本优化的情况"
- 用户按关键词/主题分析，如"看下网络安全相关的检测项""数据库相关的风险有哪些"
- 用户指定筛选条件，如"高优先级的安全问题""中风险以上的稳定性问题"

**数据来源**：

- 按支柱分析：`pillar -c <Category>` 模式输出的 JSON
- 按关键词分析：`detail --keyword <keyword>` 返回多个匹配项时，需逐个使用 `detail --id` 获取详情，或使用 `pillar` 模式后按关键词在结果中筛选

**设计原则**：支柱报告是漏斗的第二层，用户已主动选择了方向，报告应**聚焦该领域的风险全貌**，但仍需控制信息密度，高风险详细、低风险概括。

---

## 格式模板

```markdown
## {CategoryCN}支柱 治理检测分析

> 也可根据用户意图调整标题，如"网络安全相关检测分析"、"数据库相关风险分析"

**最近一次检测时间**：{EvaluationTime, format: YYYY-MM-DD HH:MM:SS}

**整体评分**：{TotalScore*100:.1f} 分

**分析范围**：{CategoryCN}支柱，共 {MatchedCount} 项检测
{If filtered: "筛选条件：仅显示有风险项 / 仅显示高优先级 / 等"}

### 概述

{Agent summarizes:
- 该支柱/主题下的整体合规情况
- 风险分布（高 N / 中 N / 建议 N）
- 主要问题集中在哪些方面
}

### 高风险项

{If no Error items: "当前无高风险项。"}

| 检测项 | 优先级 | 合规率 | 不合规资源数 | 说明 |
| --- | --- | --- | --- | --- |
| {DisplayName} | {RecommendationLevelCN} | {Compliance*100:.0f}% | {NonCompliant} | {Agent: brief explanation of risk and impact} |
| ... | ... | ... | ... | ... |

### 中风险项

{If no Warning items: "当前无中风险项。"}

{See "数量控制规则" for display limits.}

| 检测项 | 优先级 | 合规率 | 不合规资源数 | 说明 |
| --- | --- | --- | --- | --- |
| {DisplayName} | {RecommendationLevelCN} | {Compliance*100:.0f}% | {NonCompliant} | {Agent: brief explanation} |
| ... | ... | ... | ... | ... |

{If truncated:}
> 仅展示前 {N} 项，另有 {remaining} 项中风险未列出。如需查看完整列表，请告诉我。

### 建议优化项

{Default: only show count, do not list individual items.}

共 {suggestion_count} 项建议优化项，均为低风险。如需查看详情，请告诉我。

{If user explicitly asked for all items, then list them in a table.}

### 治理建议

{Agent generates targeted recommendations specific to this pillar/topic.
Each recommendation has a title and directly references risk items from above.}

#### 1. {Recommendation title}

{Specific actionable content, referencing the relevant risk items.
Include concrete next step, e.g., "建议优先处理 {DisplayName}，可查看其修复方案".}

#### 2. {Recommendation title}

{...}

{2-3 recommendations, prioritized by risk severity.}

---

如需进一步了解，可以告诉我：

- 想查看某个风险项的详情和修复方案，如"**{pick a risky DisplayName from report} 怎么修复**"
- 想查看某个风险项的不合规资源列表，如"**{pick a risky DisplayName} 有哪些不合规资源**"
- 想查看其他支柱的情况，如"**分析下{pick another pillar}支柱**"
```

---

## 数量控制规则

- **高风险项（Error）**：全部展示（该支柱下高风险项通常不多，且是用户钻入的核心原因）
- **中风险项（Warning）**：
  - <= 5 项：全部展示
  - > 5 项：展示 Top 5（按 RecommendationLevel 排序），其余用汇总行概括
- **建议优化项（Suggestion）**：默认只展示数量，不逐条列出；用户明确要求时才展开
- 若用户指定了 `--risk` 或 `--level` 过滤条件，按过滤后的结果展示，不再额外截断

## 格式规则

- **禁止使用任何 emoji**，全文保持专业语气
- 标题根据实际分析维度灵活调整：
  - 按支柱分析时用 "{CategoryCN}支柱 治理检测分析"
  - 按关键词分析时用 "{关键词}相关检测分析"
- 风险项按风险等级分段展示（高 → 中 → 建议），每段内按优先级排序
- "合规率"列：`Compliance * 100`，取整数百分比
- "不合规资源数"列：取 `NonCompliant` 字段值，若无则显示 "-"
- "说明"列：Agent 根据检测项的 `Description` 和实际检测结果，用简练语言说明风险含义
- 若某风险等级下无检测项，保留该段标题并注明"当前无{等级}项"
- 治理建议必须带标题分段，关联具体风险项，避免空泛的通用建议

## 后续引导规则

- 报告末尾必须附带后续引导，帮助用户继续深入分析
- 引导内容必须**基于报告中的实际数据**，从报告中挑选具体的检测项名称、支柱名填入引导模板
- 引导以列表形式呈现，提供 2-3 个方向，每个方向用加粗标出建议的提问语句
- 若当前分析的是某个支柱，引导可指向：该支柱下某个具体风险项的修复、不合规资源查看、其他支柱对比
- 禁止使用 emoji
