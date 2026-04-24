---
name: quickbi-smartq-dashboard
description: >
  根据 QuickBI 仪表板生成专用查询技能。
  当用户提供仪表板 URL 并希望创建查询技能时使用。
  触发关键词：生成技能、仪表板转 Skill。
---

# QuickBI 仪表板技能生成器

通过 OpenAPI 获取 QuickBI 仪表板数据，发现其图表组件、字段配置、查询控件、布局关系，提炼分析思路，生成一份可用于数据查询的 SKILL.md 文件。

## Scope

**Does:**
- 接收 QuickBI 仪表板 URL 或数据门户 URL，解析出 pageId
- 调用 OpenAPI 获取仪表板完整 JSON 结构
- 解析图表组件、查询控件、数据集、字段配置
- 分析布局模式，匹配适用的分析框架（L1-L4 金字塔或专业框架）
- 生成完整的查询技能 SKILL.md 文件并安装到技能中心

**Does NOT:**
- 不执行实际的数据查询（查询由生成的子 skill 负责）
- 不支持非 QuickBI 平台的仪表板
- 不处理需要特殊权限的仪表板（会在预校验阶段提示错误）
- **不在 `fetch_dashboard_data` 失败时尝试任何替代方案**（必须终止流程，禁止绕行）

## 触发场景

当用户提出以下类型的请求时使用此 Skill：
- "帮我把这个 QuickBI 仪表板转化为一个查询 Skill"
- "把这个看板变成一个可以查询数据的 Skill"
- "生成这个仪表板的查询技能"
- "提取这个仪表板的分析思路，生成 Skill"
- "为这个仪表板生成技能：{URL}"
- 用户提供了一个 类似 `https://bi.aliyun.com/dashboard/view/pc.htm?pageId=XXXXXXX` 格式的仪表板 URL，并希望创建查询能力
- 用户提供了一个数据门户页面 URL（格式如 `https://bi.aliyun.com/product/view.htm?module=dashboard&productId=xxx&menuId=yyy`），并希望创建查询能力

### 支持的 URL 格式

| URL 类型 | 路径特征 | 关键参数 | 处理方式 |
|----------|---------|---------|----------|
| **仪表板页面** | `/dashboard/view/pc.htm` | `pageId` | 直接提取 pageId |
| **数据门户页面** | `/product/view.htm` | `productId`, `menuId` | 通过 OpenAPI 获取关联的 pageId |

## 前置条件

- 需要有效的 API 凭证（用于调用 OpenAPI 获取仪表板数据）
- 配置说明请参见主文件的「配置」章节

---

## Phase 1: 输入收集与验证

### Step 1.0: 获取用户输入

从用户消息中提取：

1. **页面地址**（必需）：QuickBI 仪表板链接或数据门户链接
2. **技能名称**（可选）：生成的 skill 目录名（kebab-case 格式）
   - 如果用户指定了技能名称，直接使用（会覆盖同名技能）
   - 如果未指定，将在 Phase 2 发现仪表板标题后自动推导

---

## Phase 2: 仪表板数据获取与解析

### Step 2.1: 一站式获取仪表板数据

> **⚠️ 强制约束**：必须使用封装脚本，禁止自行拆分执行。

使用 `scripts/fetch_dashboard_data.py` 一站式完成：配置加载 → URL 解析 → 预校验 → 获取 JSON → 解析结构 → 获取数据集名称。

**[强制规则] 失败立即终止，禁止任何绕行**：

> ⛔ **绝对禁止**：当 `fetch_dashboard_data` 返回失败时，**禁止尝试任何替代方案**，包括但不限于：
> - ❌ 直接调用底层 API（如 `get_dashboard_json`）
> - ❌ 跳过预校验步骤
> - ❌ 尝试"其他方法"获取数据
> - ❌ 继续执行后续任何步骤
>
> **唯一正确的行为**：输出错误信息 → 终止流程 → 等待用户修正后重新触发

- 如果获取失败（`result["success"] == False`），**必须立即终止整个流程**
- **失败原因已在 `result["error"]` 中说明**，直接展示给用户即可
- **不要尝试"智能"地绕过错误**——预校验失败说明前置条件不满足，绕行只会导致后续步骤全部失败

```python
from dashboard.fetch_dashboard_data import fetch_dashboard_data

# 一站式获取（自动处理：配置加载、URL解析、预校验、获取JSON、解析、数据集名称）
result = fetch_dashboard_data(user_input_url)

if not result["success"]:
    print(f"获取失败: {result['error']}")
    # ⛔ 必须立即终止！禁止尝试其他方法，禁止继续执行任何后续步骤
    return  # 流程到此结束，等待用户修正后重新触发

# 提取结果
dashboardData = result["dashboardData"]      # 解析后的仪表板结构
datasetNameMap = result["datasetNameMap"]    # cubeId -> cubeName 映射
page_id = result["pageId"]                   # 仪表板 pageId
dashboard_url = result["dashboardUrl"]       # 标准仪表板预览页地址（用于生成 skill）

print(f"获取成功: {dashboardData['basicInfo']['name']}")
```

**脚本位置**：[scripts/fetch_dashboard_data.py](scripts/fetch_dashboard_data.py)

**执行后必须输出**（确认数据已获取）：

```markdown
---
## Step 2.1 执行结果

**执行状态**：{成功/失败}
**仪表板名称**：{dashboardData.basicInfo.name}
**仪表板URL**：{dashboard_url}（用于仪表板知识库的 URL 字段）
**pageId**：{page_id}
**gmtModified**：{dashboardData.basicInfo.gmtModified}（用于 SKILL_METADATA.skill_generated_at）
**图表组件数**：{dashboardData.chartComponents.length} 个
**查询控件数**：{dashboardData.queryControls.length} 个
**Tab组件数**：{dashboardData.tabComponents.length} 个

> ⚠️ **pageId 校验**：上方 pageId 值来自脚本返回的 `result["pageId"]`。
> 如果用户传入的是数据门户 URL（含 productId），pageId 与 productId **一定不同**。
> 后续 Phase 3 生成技能文件时，所有需要 pageId 的地方**必须使用此值**，禁止使用 URL 中的 productId。

**数据集清单**（去重）：
| 数据集名称 | 数据集ID |
|-----------|----------|
| {datasetNameMap[cubeId]} | {cubeId} |

> 数据已存储到 `dashboardData`、`datasetNameMap` 和 `dashboard_url`，继续执行 Step 2.2
---
```

**失败处理**（⛔ 禁止绕行）：
- 如果 `result["success"] == False`，**立即终止整个流程**
- 输出错误信息 `result["error"]`，告知用户失败原因
- **禁止**尝试直接调用 `get_dashboard_json` 或任何其他方法
- 提示用户检查配置或仪表板权限后重新触发

**返回数据结构**：`dashboardData` 包含 `basicInfo`、`queryControls`、`chartComponents`、`tabComponents`、`richTextComponents`、`layoutAnalysis` 等字段，完整定义见 [reference.md - dashboardData 数据结构](./reference.md#dashboarddata-数据结构)。

### Step 2.2: 数据验证与补充

**目的**：验证解析结果的完整性，必要时补充信息。

#### 2.2.1 Tab 结构验证

如果 `dashboardData.tabComponents.length > 0`：

1. 列出所有 Tab 及其标题
2. 确认每个 Tab 下包含的图表组件
3. 记录 Tab 与图表的从属关系

#### 2.2.2 图表标题验证

1. 检查 `dashboardData.chartComponents[].componentName` 是否有意义
2. 如果为空或无意义，根据度量/维度字段推断主题
3. 记录调整后的图表标题

#### 2.2.3 富文本内容提取

1. 从 `dashboardData.richTextComponents[].textContent` 提取纯文本
2. 用于理解仪表板的业务背景和使用说明

### Step 2.3: 提炼分析思路与匹配分析框架

> **【必须执行步骤】** 完成 5 个子步骤 + 强制输出（2.3.2-OUTPUT）。
> 这是将仪表板数据转化为可用分析框架的核心步骤。即使时间紧迫，也必须完成此步骤的所有子步骤（2.3.1 - 2.3.5）和强制输出（2.3.2-OUTPUT）。

> **核心原则**：所有内容必须基于 `dashboardData`（Step 2.1 获取的数据）推断，不可臆造。

#### 2.3.1 数据提取

从 `dashboardData.chartComponents` 中提取：

**数据集清单**：收集所有图表的 `sourceId`，去重后建立清单：

| 数据集ID | 关联图表 | 可用维度 | 可用度量 |
|----------|---------|---------|----------|
| {sourceId} | {图表名列表} | {维度字段} | {度量字段(聚合方式)} |

**指标体系**：遍历 `chartComponents[].measures`，按 `caption` 去重。

**维度体系**：遍历 `chartComponents[].dimensions`，按 `itemType` 分类：
- `datetime` → 时间维度 | `geographic` → 地理维度 | `dimension` → 分类维度

#### 2.3.2 分析框架匹配

综合**指标语义 + 布局模式 + 联动关系**，匹配最适合的分析框架。

**框架匹配规则**：详见 [reference.md - 分析框架匹配规则](reference.md#分析框架匹配规则)

常用框架：杜邦分析、AARRR 海盗模型、RFM 客户分析、漏斗分析、目标达成分析、同环比分析等。无法匹配时使用 **L1-L4 金字塔**（概览→趋势→分解→明细）。

#### 2.3.2-OUTPUT: 【强制】输出分析框架匹配结果

> **不可跳过**：完成 2.3.1-2.3.2 后，**必须输出**以下格式：

```markdown
---
## 【分析框架匹配结果】

### 提取到的真实字段
**度量字段**：{measures 列表}
**维度字段**：时间({datetime}) | 地理({geographic}) | 分类({dimension})

### 布局模式
**布局特征**：第一行{N}个{类型}组件，总{M}行，底部{有/无}明细表
**布局模式**：{指标矩阵型/明细导向型/对比分析型/聚焦分析型}

### 框架匹配
**匹配框架**：{框架名称}
**置信度**：{high/medium/default}
**匹配依据**：{指标特征} + {布局特征} + {联动特征}

### 层级预览（仅 L1-L4 框架）
| 层级 | 图表数 | 典型图表 | 归类依据 |
|-----|-------|---------|----------|
| L1 | {N} | {示例} | {类型+位置} |
---
```

#### 2.3.3 布局模式分析与仪表板类型推断

基于 `tileLayout` 位置信息推断仪表板的整体分析模式。详见 [reference.md - 布局模式分析规则](reference.md#布局模式分析规则)

**布局模式类型**：指标矩阵型、核心图表型、明细导向型、对比分析型、聚焦分析型。

#### 2.3.4 自动匹配分析框架（多维度综合推断）

> **综合指标语义 + 布局模式 + 联动关系，匹配最适合的分析框架**
> 
> **重要**：这是一个**思考推断步骤**，综合多个维度的信息来推断分析框架。

**层级归类规则**：详见 [reference.md - 层级归类规则](reference.md#层级归类规则)

- **L1**（整体监控）：indicator-card/kpi/gauge，顶部位置
- **L2**（趋势分析）：line/area/indicator-trend，含 datetime 维度
- **L3**（维度分解）：bar/pie/ranking-list，含分类维度
- **L4**（明细追踪）：common-table，底部位置

**匹配思考流程**：

1. **列出所有真实指标**：从 `uniqueMeasures` 中列出所有指标名称
2. **列出所有真实维度**：从 `uniqueDimensions` 中列出所有维度名称
3. **识别布局模式**：根据布局特征判断仪表板类型
4. **分析联动关系**：哪些图表共享筛选器？暗示它们在同一分析路径上
5. **分析下钻方向**：`drillFields` 的维度类型暗示分析深入的方向
6. **综合语义分析**：结合以上信息，理解仪表板的整体分析意图
7. **框架匹配**：根据综合特征判断最匹配的分析框架
8. **记录匹配依据**：说明是基于哪些特征（指标+布局+联动）匹配到该框架

#### 2.3.5 业务逻辑推断

**业务逻辑推断（基于指标组合）**：

| 指标组合 | 推断公式 |
|---------|----------|
| 销售额 + 成本 + 利润 | 利润 = 销售额 - 成本 |
| 销售额 + 销量 | 客单价 = 销售额 / 销量 |
| 目标值 + 实际值 | 达成率 = 实际 / 目标 × 100% |

更多推断规则详见 [reference.md - 业务逻辑推断规则](reference.md#业务逻辑推断规则)

### Step 2.4: 推断意图路由矩阵

> **核心目标**：建立用户问题 → 目标图表 → 数据集ID 的精准映射

**意图关键词提取规则**：

| 用户问法模式 | 提取的意图 | 匹配目标 |
|-------------|-----------|----------|
| "XX是多少/有多少" | 查询单一指标 | L1 指标卡 |
| "XX趋势/走势/变化" | 趋势分析 | L2 折线图/趋势图 |
| "XX排行/TOP/最高/最低" | 排序分析 | L3 排行榜 |
| "XX分布/占比/构成" | 结构分析 | L3 饼图/柱图 |
| "各XX的YY" | 维度分解 | L3 分组图表 |
| "XX明细/详情/列表" | 明细查询 | L4 明细表 |
| "为什么XX下降/上升" | 归因分析 | L1→L2→L3 联合 |

更多规则详见 [reference.md - 意图路由规则](reference.md#意图路由规则)

### Step 2.5: 汇总探索结果

> **【前置检查】确认 Step 2.1 和 Step 2.3.2-OUTPUT 已输出分析框架匹配结果**

整理所有探查结果，按以下结构输出（详细格式见 Phase 3.2 模板），必须确保：
- 所有图表组件都被列出（包含数据集ID、字段列表、分析主题、层级归属）
- 分析框架匹配结果基于真实提取的指标和维度
- 业务背景综合仪表板标题、图表标题、字段名称、富文本内容
```
## 探索结果汇总
├── 基本信息（名称/pageId/URL）
├── 业务背景与统计口径
├── 分析框架匹配结果
├── 核心指标体系
├── 维度体系
├── 业务逻辑推断
├── 层级结构（A/B/C 形式）
├── 数据集清单
├── 查询控件
├── 图表组件完整列表（12列）
├── 意图路由矩阵
├── 联动与下钻路径
├── 下钻字段配置
└── 适用场景与查询路径
```

**关键要求**：
- 所有图表组件必须完整列出，每个都包含数据集ID、字段列表、分析主题
- 分析框架匹配结果基于真实提取的指标和维度
- 层级归属基于图表类型和布局位置

---

## Phase 3: 技能文件生成

根据探索结果，组装并写入 SKILL.md 和 config.yaml 文件。

> ⚠️ **关键变量确认**：生成技能文件前，确认以下值的来源：
> - **pageId** = `result["pageId"]`（Step 2.1 脚本返回值）—— **不是**用户输入 URL 中的 `productId`
> - **dashboard_url** = `result["dashboardUrl"]`（Step 2.1 脚本返回值，已包含正确 pageId）
> - **skill_generated_at** = `dashboardData.basicInfo.gmtModified`
>
> 数据门户 URL 中的 `productId` 是门户 ID，与仪表板 `pageId` 是完全不同的值，禁止混用。

### Step 3.1: 确定技能名称

如果用户提供了技能名称，直接使用（会覆盖同名技能）。否则：
1. 取仪表板标题
2. 转换为 kebab-case 格式（中文用拼音或有意义的英文缩写）
3. 添加 `qbi-` 前缀
4. **追加 pageId 前8位确保唯一性**
5. 例如："好美家零售数据" (pageId: `ab12cd34-xxxx`) → `qbi-retail-query-ab12cd34`

### Step 3.2: 组装 SKILL.md 内容

按以下模板生成技能文件。**{占位符}** 表示用探索结果填充的内容。

#### 3.2.1-3.2.7 内容模板

> **【必须执行】读取模板文件**
>
> 使用 `read_file` 工具读取 `./templates/output_skill_template.md` 文件，获取以下内容的完整模板：
> - **YAML Frontmatter + 技能元数据**（3.2.1）：name/description 格式、SKILL_METADATA 注释块
> - **标题和触发场景**（3.2.2-3.2.3）：5-8 个自然语言查询示例
> - **前置条件**（3.2.4）：配置引导流程（与本 skill 的前置条件逻辑一致）
> - **仪表板知识库**（3.2.5）：基本信息、业务背景、数据集清单、查询控件、图表组件完整列表、意图路由矩阵
> - **仪表板分析思路**（3.2.6）：分析框架匹配、层级结构、核心指标、维度体系、业务逻辑、联动路径
> - **工作流程**（3.2.7）：问题理解→拆解→构建查询→调用 SmartQ→汇总结果→错误处理
>
> 按模板格式生成对应内容，填充 `dashboardData` 中提取的真实数据。

**关键要求**：
- description 必须保留 `INSTEAD OF generic quickbi-smartq-chat` 优先级声明
- 所有图表组件必须完整列出，不遗漏
- 指标和维度必须来自 `dashboardData`，不可臆造

### Step 3.3: 生成 config.yaml

复制配置模板，敏感字段置空：

```yaml
# Quick BI 文件问数配置文件

# QBI 域名
server_domain: https://bi.aliyun.com

# OpenAPI 认证配置
api_key:
api_secret:

# 用户令牌
user_token:

# 是否从环境变量读取认证信息
use_env_property: false
```

### Step 3.4: 写入文件
1. **确定输出目录**：与当前技能所在目录保持一致
   - 获取当前技能的目录路径（即本 SKILL.md 文件所在的父目录的父目录）
   - 在该目录下创建 `{skill-name}/` 子目录
   - 例如：如果当前技能在 `.qoderwork/skills/quickbi-smartq-chat/`，则新技能应在 `.qoderwork/skills/{skill-name}/`
2. 创建目录（如不存在）
3. 写入 SKILL.md 文件
4. 写入 config.yaml 模板
5. **复制脚本文件到生成的 skill 的 scripts 目录**（需调整 import）：
   - 复制 `scripts/dashboard/quickbi_openapi.py` → `{skill-name}/scripts/quickbi_openapi.py`
     - **必须调整 import**：移除 `sys.path.insert(0, ...)` 行，将 `from common.config_loader import load_config as _load_config_from_loader` 改为 `from config_loader import load_config as _load_config_from_loader`（注意：不要加点号前缀，因为 scripts 目录不是 Python 包，脚本通过 `sys.path.insert` 方式加载，只能使用绝对导入）
   - 复制 `scripts/common/config_loader.py` → `{skill-name}/scripts/config_loader.py`
     - **必须调整**：将 `DEFAULT_CONFIG_PATH = BASE_DIR.parent.parent / "default_config.yaml"` 改为 `DEFAULT_CONFIG_PATH = BASE_DIR.parent / "config.yaml"`（扁平结构下 `BASE_DIR` 指向 `scripts/`，`BASE_DIR.parent` 即 skill 根目录）
6. **复制 `references/common/copy_skill_config.png`** 到生成的 skill 的 `example/` 目录，用于首次配置引导
7. 告知用户：
   - 技能文件已生成
   - 首次使用时会引导配置 API 凭证（config.yaml）
   - 生成的技能如何使用
8. **将生成的技能安装到技能中心**（必须执行）：
   执行以下命令将技能注册到技能中心：
   ```bash
   skills install local --json '{"sourcePath": "<生成的 skill 目录绝对路径>"}'
   ```

**生成的 Skill 目录结构**：
```
./skills/{skill-name}/
├── SKILL.md           # 技能文件
├── config.yaml        # API 配置（首次使用时会引导用户配置）
├── example/
│   └── copy_skill_config.png  # 首次配置引导图片（来源：common/copy_skill_config.png）
└── scripts/
    ├── quickbi_openapi.py  # OpenAPI 调用工具函数
    └── config_loader.py    # 配置加载器（全局配置存在即用）
```
---

## Examples

### Example 1: 从仪表板 URL 生成查询技能

**Input:**
```
用户：帮我把这个仪表板转成查询技能
https://bi.aliyun.com/dashboard/view/pc.htm?pageId=ab12cd34-5678-90ef-ghij-klmnopqrstuv
```

**Expected Output:**
1. 执行预校验，确认用户有访问权限
2. 获取仪表板 JSON 并解析组件结构
3. 输出分析框架匹配结果（如 L1-L4 金字塔）
4. 生成 `skills/qbi-xxx-ab12cd34/SKILL.md`
5. 自动安装到技能中心

### Example 2: 从数据门户 URL 生成查询技能

**Input:**
```
用户：这是我们的数据门户，生成一个可以查数据的 skill
https://bi.aliyun.com/product/view.htm?module=dashboard&productId=abc123&menuId=menu456
```

**Expected Output:**
1. 识别为数据门户 URL，调用 `get_dataportal_page_id` 获取关联的仪表板 pageId
2. 执行后续标准流程（同 Example 1）

---

## 重要注意事项

1. **API 凭证安全**：config.yaml 中的 AccessKey 是敏感信息，提醒用户妥善保管
2. **数据集ID是关键**：问数查询依赖正确的 `sourceId`（数据集ID），必须从 JSON 中准确提取
3. **意图路由准确性**：意图路由矩阵决定了用户问题能否正确匹配到数据集，需要仔细推断
4. **分析框架基于真实数据**：所有分析框架的指标和维度必须来自 `dashboardData`（Step 2.1 获取的数据），不可臆造
5. **分析框架必须输出**：Step 2.3.2-OUTPUT 是强制步骤，必须在汇总探索结果前输出分析框架匹配结果。如果跳过此步骤，生成的 Skill 将缺少核心分析能力

---

## 附录 C: 工具函数

### 目录结构

```
quickbi-smartq-chat/
├── SKILL.md                       # 统一入口技能
├── default_config.yaml            # 默认配置
├── references/
│   ├── dashboard/
│   │   ├── module-dashboard.md        # 本文档
│   │   ├── module-dashboard-reference.md  # 详细参考文档
│   │   └── templates/
│   │       └── output_skill_template.md  # 生成模板
│   └── common/
│       └── copy_skill_config.png      # 配置引导图片
└── scripts/
    ├── common/
    │   └── config_loader.py           # 配置加载器（四层配置优先级）
    └── dashboard/
        ├── fetch_dashboard_data.py    # 一站式仪表板数据获取
        ├── get_dashboard_json.js      # JSON 解析脚本
        └── quickbi_openapi.py         # OpenAPI 工具函数
```

### 核心函数

#### fetch_dashboard_data.py

| 函数名 | 用途 | 使用阶段 |
|--------|------|----------|
| `fetch_dashboard_data(url, config=None)` | 一站式获取仪表板数据（配置加载+URL解析+预校验+获取JSON+解析+数据集名称） | Step 2.1 |

#### quickbi_openapi.py

| 函数名 | 用途 | 使用阶段 |
|--------|------|----------|
| `load_config(config_path=None)` | 加载配置（优先级：环境变量 > 工作目录级 > 全局 > 包内默认） | Step 1.0 |
| `is_dataportal_url(url)` | 判断是否为数据门户 URL | Step 1.0 |
| `extract_dataportal_ids(url)` | 从数据门户 URL 提取 productId 和 menuId | Step 1.0 |
| `get_dataportal_page_id(...)` | 通过 OpenAPI 获取数据门户关联的仪表板 pageId | Step 1.0 |
| `extract_page_id(url)` | 从仪表板 URL 提取 pageId | Step 1.0 |
| `validate_and_prepare_dashboard(...)` | 仪表板预校验及预处理 | Step 1.0 |
| `get_dashboard_json(...)` | 获取仪表板完整 JSON 数据 | 内部调用 |
| `batch_get_dataset_schema(...)` | 批量获取数据集详情（名称等） | 内部调用 |
| `query_openapi(...)` | 调用 SmartQ 查询接口 | 生成的 skill 查询阶段 |
| `get_dashboard_update_time(...)` | 查询仪表板更新时间 | 生成的 skill 启动校验 |

#### get_dashboard_json.js

| 函数名 | 用途 |
|--------|------|
| `parseDashboardJson(json)` | 解析仪表板原始 JSON，提取组件结构 |
| `analyzeLayout(charts)` | 基于 tileLayout 分析图表布局 |

#### config_loader.py（scripts/common/）

| 函数名 | 用途 |
|--------|------|
| `load_config()` | 四层配置加载（优先级：环境变量 > 工作目录级 > 全局 > 包内默认） |
| `check_trial_expired(result)` | 检查 API 返回结果是否为试用过期错误 |
| `get_server_domain(config=None)` | 获取 server_domain（可选传入已加载的 config） |
| `persist_to_global_config(key, value)` | 写入全局配置 `~/.qbi/config.yaml` |
| `persist_to_skill_config(key, value)` | 写入工作目录级配置 `$WORKSPACE_DIR/.qbi/smartq-chat/config.yaml` |

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
