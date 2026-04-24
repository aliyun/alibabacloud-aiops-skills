# QuickBI 仪表板技能生成器 - 参考文档

> 本文档包含 SKILL.md 的详细参考内容，供深入了解使用。

## 分析框架匹配规则

### 框架匹配规则表

综合**指标语义 + 布局模式 + 联动关系**，匹配最适合的分析框架。

| 匹配规则（基于真实字段名称） | 分析框架 | 适用场景 | 核心公式/方法 |
|---------------------------|---------|---------|--------------|
| 包含"销售额/收入"+"成本"+"利润"+"毛利率/利润率" | **杜邦分析** | 财务指标分解，盈利能力分析 | ROE = 利润率 × 资产周转率 × 权益乘数 |
| 包含"获客/新增"+"激活"+"留存"+"转化"+"收入/付费" | **AARRR 海盗模型** | 互联网产品增长漏斗分析 | 各环节转化率优化 |
| 包含"最近购买时间"+"购买频次"+"消费金额" | **RFM 客户分析** | 客户价值分群，精准营销 | R×F×M 评分矩阵 |
| 包含"产品/商品"维度 + "市场份额/增长率" | **波士顿矩阵** | 产品组合策略分析 | 明星/现金牛/问题/瘦狗分类 |
| 包含"步骤/阶段/环节"维度 + "转化率/流失率" | **漏斗分析** | 流程优化，定位流失环节 | 各环节转化率 = 下一步/上一步 |
| 包含"目标值/计划值" + "实际值/完成值" | **目标达成分析** | KPI 完成度监控 | 达成率 = 实际值/目标值 × 100% |
| 包含"同期/去年同期" + "当期/本期" | **同环比分析** | 时间对比趋势分析 | 同比 = (本期-同期)/同期 × 100% |
| 包含"预算" + "实际/执行" | **预实对比分析** | 预算执行监控 | 预算执行率 = 实际/预算 × 100% |
| 包含"库存/存货" + "周转/动销" | **库存分析** | 库存健康度监控 | 周转率 = 销售成本/平均库存 |
| 包含"客单价" + "客户数/用户数" + "销售额" | **客户价值分析** | 客户贡献度分析 | 销售额 = 客户数 × 客单价 |
| 包含"曝光/展示" + "点击" + "转化/成交" | **营销漏斗分析** | 广告投放效果分析 | CTR/CVR 等转化指标 |
| 包含"人力/人数" + "产出/效率" | **人效分析** | 人力资源效能分析 | 人均产出 = 总产出/人数 |
| 以上都不匹配 | **L1-L4 金字塔** | 通用层级分析框架 | 概览→趋势→分解→明细 |

---

## 布局模式分析规则

### 布局模式识别

基于 `tileLayout` 位置信息推断仪表板的整体分析模式。

| 布局特征 | 布局模式 | 典型特点 | 推断的仪表板类型 |
|---------|---------|---------|----------------|
| 第一行有多个 indicator-card 类型组件 | **指标矩阵型** | 顶部密集指标卡阵列 | 监控型仪表板（强调 L1 概览） |
| 存在 line/bar 等趋势图表 | **核心图表型** | 有主次之分的焦点布局 | 分析型仪表板（强调 L2/L3） |
| 底部存在 common-table | **明细导向型** | 底部有明细表 | 运营型仪表板（强调 L4 追溯） |
| 同一行有多个相同类型组件 | **对比分析型** | 并列布局便于对比 | 多维对比分析 |
| 组件数量少（≤4） | **聚焦分析型** | 少而精的核心图表 | 专题分析仪表板 |

### 布局模式与分析框架的关联

| 布局模式 | 倾向的分析框架 | 置信度提升依据 |
|---------|--------------|---------------|
| 指标矩阵型 | 目标达成分析、同环比分析 | 多指标并列 → 关注指标对比 |
| 核心图表型 | 趋势分析、漏斗分析 | 大图表为主 → 关注过程变化 |
| 明细导向型 | L1-L4 金字塔 | 有明细表 → 需要追溯能力 |
| 对比分析型 | 杜邦分析、客户价值分析 | 并列布局 → 关注维度对比 |

---

## 层级归类规则

### L1-L4 层级判断

| 层级 | 类型特征 | 位置特征 |
|-----|---------|----------|
| **L1** | indicator-card/kpi/gauge | y ≤ 20（顶部）|
| **L2** | line/area/indicator-trend | 20 < y < 50，含 datetime 维度 |
| **L3** | bar/pie/ranking-list | 30 < y < 70，含分类维度 |
| **L4** | common-table | y > 50（底部）|

### 分析主题推断（基于图表类型）

| 图表类型 | 分析主题模式 |
|---------|-------------|
| indicator-card/kpi | "{度量}指标展示" |
| line/area | "{度量}时序趋势" |
| pie | "{维度}分布/占比" |
| bar | "{维度}对比分析" |
| ranking-list | "{维度}排行榜" |
| common-table | "{主题}明细查询" |

---

## 意图路由规则

### 用户问法模式匹配

| 用户问法模式 | 提取的意图 | 匹配目标 |
|-------------|-----------|----------|
| "XX是多少/有多少" | 查询单一指标 | L1 指标卡 |
| "XX趋势/走势/变化" | 趋势分析 | L2 折线图/趋势图 |
| "XX排行/TOP/最高/最低" | 排序分析 | L3 排行榜 |
| "XX分布/占比/构成" | 结构分析 | L3 饼图/柱图 |
| "各XX的YY" | 维度分解 | L3 分组图表 |
| "XX明细/详情/列表" | 明细查询 | L4 明细表 |
| "为什么XX下降/上升" | 归因分析 | L1→L2→L3 联合 |

---

## 业务逻辑推断规则

### 指标组合推断公式

| 指标组合 | 推断公式 |
|---------|----------|
| 销售额 + 成本 + 利润 | 利润 = 销售额 - 成本 |
| 销售额 + 销量 | 客单价 = 销售额 / 销量 |
| 目标值 + 实际值 | 达成率 = 实际 / 目标 × 100% |
| 本期 + 同期 | 同比增长率 = (本期-同期)/同期 × 100% |
| 本期 + 上期 | 环比增长率 = (本期-上期)/上期 × 100% |

---

## 工具函数说明

### quickbi_openapi.py 函数清单

| 函数名 | 用途 | 使用阶段 |
|--------|------|----------|
| `load_config(config_path=None)` | 加载配置（优先级：环境变量 > 工作目录级 > 全局 > 包内默认） | Step 1.0, Step 2.1 |
| `is_dataportal_url(url)` | 判断是否为数据门户 URL | Step 1.0 |
| `extract_dataportal_ids(url)` | 从数据门户 URL 提取 productId 和 menuId | Step 1.0 |
| `get_dataportal_page_id(...)` | 通过 OpenAPI 获取数据门户关联的仪表板 pageId | Step 1.0 |
| `extract_page_id(url)` | 从仪表板 URL 提取 pageId | Step 1.0 |
| `validate_and_prepare_dashboard(...)` | 仪表板预校验及预处理 | Step 1.0 |
| `get_dashboard_json(...)` | 获取仪表板完整 JSON 数据 | Step 2.1 |
| `query_openapi(...)` | 调用 SmartQ 查询接口 | 生成的 skill 查询阶段 |
| `get_dashboard_update_time(...)` | 查询仪表板更新时间 | 生成的 skill 启动校验 |

### get_dashboard_json.js 函数清单

| 函数名 | 用途 |
|--------|------|
| `parseDashboardJson(json)` | 解析仪表板原始 JSON，提取组件结构 |
| `analyzeLayout(charts)` | 基于 tileLayout 分析图表布局 |

### config_loader.py 函数清单

| 函数名 | 用途 |
|--------|------|
| `load_config()` | 四层配置加载（优先级：环境变量 > 工作目录级 > 全局 > 包内默认） |
| `persist_to_global_config(key, value)` | 写入全局配置 `~/.qbi/config.yaml` |

---

## 错误码参考

### 预校验接口错误码

| 错误码 | 含义 | 处理建议 |
|--------|------|----------|
| `AE0510000005` | 用户不在组织中 | 检查 user_token 是否正确 |
| `AE0510150002` | 没有仪表板访问权限 | 检查用户是否有该仪表板的访问权限 |
| `AE0510200000` | 没有数据集管理或者授权的权限 | 检查是否有数据集管理和问数配置权限 |
| `AE0581030022` | 未购买问数功能 | 确认已购买 SmartQ 问数功能 |
| `OE10010106` | API 未授权 | 检查 api_key/api_secret 配置 |
| `CONNECTION_ERROR` | 网络连接失败 | 检查网络和 server_domain 配置 |

### 数据门户接口错误码

| 错误码 | 含义 | 处理建议 |
|--------|------|----------|
| `NO_PAGE_ID` | 数据门户菜单未关联仪表板 | 检查门户菜单是否正确配置了仪表板页面 |
| `CONNECTION_ERROR` | 网络连接失败 | 检查网络和 server_domain 配置 |

---

## dashboardData 数据结构

Step 2.2 解析后返回的完整数据结构：

```typescript
{
  success: boolean;
  basicInfo: {
    name: string;           // 仪表板名称
    pageId: string;         // 页面ID
    workspaceId: string;    // 工作空间ID
    gmtModified: number;    // 最后修改时间（毫秒级时间戳），用于 skill_generated_at
  };
  queryControls: Array<{    // 查询控件列表
    componentId: string;
    internalId: string;
    needManualQuery: boolean;
    fields: Array<{
      labelName: string;
      componentType: string;  // datetime / enumSelect
      relatedGraphIds: string[];
    }>;
  }>;
  chartComponents: Array<{  // 图表组件列表
    componentId: string;
    componentName: string;
    sourceId: string;       // 数据集ID - 问数调用的关键
    dimensions: Array<{caption: string; pathId: string}>;
    measures: Array<{caption: string; aggregateType: string}>;
    drillFields: Array<{caption: string}>;
    tabInfo: object | null; // Tab 从属关系
  }>;
  tabComponents: Array<{    // Tab 组件列表
    componentId: string;
    tabs: Array<{id: string; title: string}>;
  }>;
  richTextComponents: Array<{textContent: string}>;
  layoutAnalysis: {rows: Array};  // 布局分析
}
```
