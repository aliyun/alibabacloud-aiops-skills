---
name: alibabacloud-safety-checker
description: Alibaba Cloud content moderation and AI guardrails automated testing. Tests sample content against moderation APIs, compares multiple services, tracks requestId/traceId, supports manual annotation, deep false-negative analysis, cross-batch comparison, AI guardrails testing (prompt injection, sensitive data, jailbreak), and generates alignment reports. Use when user asks about content safety, moderation testing, moderation strategy, label configuration, content review, batch safety checks, miss analysis, AI guardrails, prompt injection detection, or safety guardrails testing.
allowed-tools:
  - Bash(python3:*)
  - Bash(agent-browser:*)
  - Bash(pip:*)
  - Bash(cd:*)
  - Bash(export:*)
---

# Content Security & AI Guardrails Tester

阿里云内容安全 + AI安全护栏自动化测试 Skill。覆盖从场景选择、控制台配置、批量测试到标注分析的全流程，同时支持AI安全护栏效果测试。

## 重要：执行规则

1. **工作目录**：所有 python3 命令必须使用绝对路径执行。脚本位于两个位置：
   - Skill目录: `~/.qoderwork/skills/safety-checker/`（默认）
   - 用户项目目录: 如果用户有selected folder，优先使用该目录
2. **命令格式**：始终使用 `python3 <绝对路径>/script.py` 格式，例如：
   `python3 ~/.qoderwork/skills/safety-checker/scenario_manager.py list`
3. **禁止循环执行同一命令**：如果一条命令已成功执行并返回输出，直接将结果呈现给用户，不要重复执行
4. **单次执行即响应**：每个步骤只需执行一次命令，获取输出后立即向用户汇报结果或进入下一步

## 快速开始

```bash
# 设置工作目录变量
SAFETY_DIR=~/.qoderwork/skills/safety-checker

# 安装依赖
pip install -r $SAFETY_DIR/scripts/requirements.txt

# 验证连通性（依赖默认凭证链，无需手动设置凭证）
python3 $SAFETY_DIR/verify_auth.py
```

## 工作流

### Step 1: 确认业务场景

通过对话了解用户业务类型，从预定义场景中选择最匹配的：

| 场景ID | 名称 | 适用场景 |
|--------|------|---------|
| `ai_companion_chat` | AI陪聊/虚拟伴侣 | AI角色扮演、情感陪伴 |
| `game_chat` | 游戏聊天室 | 游戏内公聊、组队频道 |
| `general_chat` | 通用Chat/社交 | IM私聊群聊、论坛 |
| `ecommerce` | 零售电商 | 商品评价、描述、客服 |
| `news_content` | 资讯/新闻 | 新闻平台、自媒体 |

```bash
# 查看所有场景（使用绝对路径）
python3 ~/.qoderwork/skills/safety-checker/scenario_manager.py list

# 查看某个场景的配置详情（执行一次后直接将输出呈现给用户）
python3 ~/.qoderwork/skills/safety-checker/scenario_manager.py show <场景ID>
```

**完成条件**：命令输出场景信息后，直接将结果展示给用户并询问是否需要调整。不要重复执行同一命令。

### Step 2: 配置控制台标签开关

**方式A: 浏览器自动化（推荐）**

```bash
python3 ~/.qoderwork/skills/safety-checker/console_automator.py --scenario <场景ID>
```

脚本自动完成：打开控制台 → 引导用户登录 → 复制Service → 逐个配置标签开关 → 保存。

**方式B: 生成操作指南，用户手动配置**

```bash
python3 ~/.qoderwork/skills/safety-checker/scenario_manager.py guide <场景ID>
```

生成详细的 Markdown 操作指南。配置保存后等待 2-5 分钟生效。

### Step 3: 准备测试样本

样本支持 JSON / CSV / Excel 格式。如果是小说/长文本，自动切分：

```bash
python3 ~/.qoderwork/skills/safety-checker/prepare_novel.py /path/to/novel.txt --max-samples 100
```

样本 JSON 格式：
```json
{
  "samples": [{
    "sample_id": "text_001",
    "modality": "text",
    "content": "待审核文本",
    "data_id": "自定义ID",
    "category": "分类标签",
    "expected_risk_level": "期望风险等级(可选)",
    "expected_labels": ["期望标签(可选)"]
  }]
}
```

### Step 4: 运行审核测试

```bash
python3 ~/.qoderwork/skills/safety-checker/main.py run --samples <样本文件> \
  --text-services <自定义Service名> \
  --concurrent 10 --format xlsx
```

### Step 5: 人工标注

```bash
python3 ~/.qoderwork/skills/safety-checker/main.py annotate --file results/results_batch_xxx.json --annotator "姓名"
```

交互标注选项：`c`=正确、`fp`=误判、`fn`=漏判、`u`=不确定、`s`=跳过、`q`=退出保存。

### Step 6: 生成对齐分析报告

```bash
python3 ~/.qoderwork/skills/safety-checker/main.py report --file results/annotated_xxx.xlsx
```

报告包含：按服务的准确率/误判率/漏判率、按模态分析、按类别分析。

## 输入输出示例

### 文本审核 - 输入
```json
{
  "samples": [
    {"sample_id": "t001", "modality": "text", "content": "今天天气真不错，适合出去玩", "category": "normal"}
  ]
}
```

### 文本审核 - 输出
```json
{
  "sample_id": "t001",
  "risk_level": "none",
  "labels": [],
  "request_id": "A216D7F5-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "latency_ms": 120
}
```

### 异常处理

- **凭证未配置**：`verify_auth.py` 返回明确错误提示，指引用户检查默认凭证链配置
- **Region 不可用**：SDK 返回 `InvalidRegionId` 错误时，脚本提示切换至 cn-shanghai 或 cn-beijing
- **超时**：默认 read_timeout=30s，大文本/图片场景可通过 `--timeout` 参数调整
- **API 限流**：429 状态码时自动指数退避重试（最多 3 次），并在结果中标记受影响样本

## AI安全护栏测试

### 功能概述

AI安全护栏是面向大模型应用和AI Agent的安全防护方案，支持三大检测维度：

| 防护维度 | 返回字段 | 说明 | 默认状态 |
|---------|---------|------|---------|
| 内容合规 | `Result` / `RiskLevel` | 检测色情、暴力、政治等不良内容 | 默认启用 |
| 敏感内容检测 | `SensitiveResult` / `SensitiveLevel` | 检测身份证号、信用卡号、手机号等PII数据 | **需手动开启，单独计费** |
| 提示词攻击检测 | `AttackResult` / `AttackLevel` | 检测提示词注入、越狱等恶意攻击 | **需手动开启，单独计费** |

### Step G1: 开通AI安全护栏服务

1. 前往 [AI安全护栏产品开通页面](https://www.aliyun.com/product/lvwang) 开通服务（按量后付费）
2. 为RAM用户授权 `AliyunYundunGreenWebFullAccess` 权限
3. 登录 [AI安全护栏控制台](https://yundunnext.console.aliyun.com/?p=cts)，在 **防护配置 → 检测项配置** 中确认三大检测维度开关状态

> **重要**：敏感内容检测和提示词攻击检测默认关闭，需在控制台手动开启，且单独计费。如未开启，对应返回字段（SensitiveResult/AttackResult）将为空。

### Step G2: 运行护栏效果测试

```bash
# 运行默认测试套件（20个样本：10个输入检测+10个生成检测）
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py

# 仅测试AI输入检测
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --service query

# 仅测试AI生成检测
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --service response

# 指定输出文件
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --output results/my_guardrail_test.json

# 输出Excel三Sheet报告（详细结果 + 服务汇总 + 三维度拆解）
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --format xlsx

# 同时输出JSON和XLSX
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --format both

# 输出暗色主题 HTML 可视化报告（三维度卡片 + 逐样本表格 + 自动洞察）
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --format html

# 通过一站式入口调用
python3 ~/.qoderwork/skills/safety-checker/cst.py guardrail
python3 ~/.qoderwork/skills/safety-checker/cst.py guardrail --service query --format xlsx
```

### Step G3: 使用自定义样本测试

```json
{
  "query": [
    {"name": "测试名称", "content": "待检测文本", "expected_risk_level": "high"}
  ],
  "response": [
    {"name": "测试名称", "content": "待检测文本", "expected_risk_level": "none"}
  ]
}
```

```bash
python3 ~/.qoderwork/skills/safety-checker/ai_guardrail.py --samples assets/my_guardrail_samples.json
```

### Step G4: 解读测试结果

AI安全护栏返回三大维度的检测结果：

**RiskLevel（内容合规风险等级）**：
- `none`：未检测到风险
- `low`：低风险（建议日常按无风险处理）
- `medium`：中风险（建议人工复查）
- `high`：高风险（建议直接处置）

**SensitiveLevel（敏感信息等级）**：
- `S0`：未检出敏感内容
- `S1`~`S4`：数字越高敏感程度越高

**AttackLevel（攻击等级）**：
- `none`：未检测到攻击
- `low`/`medium`/`high`：攻击风险等级

### Step G5: 漏判根因分析

当测试结果出现漏判时，按以下逻辑排查：

| 漏判场景 | 可能根因 | 排查方法 | 补救方案 |
|---------|---------|---------|---------|
| SensitiveResult 全部为空 | 敏感内容检测维度未开启 | 检查控制台检测项配置 | 控制台 → 防护配置 → 检测项配置 → 开启"敏感内容检测" |
| AttackResult 全部为空 | 提示词攻击检测维度未开启 | 检查控制台检测项配置 | 控制台 → 防护配置 → 检测项配置 → 开启"提示词攻击检测" |
| 色情意图被漏判 | 模型侧重内容描写而非意图 | 对比"包含色情描写"vs"索取色情资源" | 配置自定义词库加黑"色情图片"等关键词 |
| 提示词注入被归为违禁行为 | 攻击检测未开启，仅内容合规生效 | 检查AttackLevel是否为N/A | 开启提示词攻击检测 |
| 歧视/隐喻被漏判 | 对应标签未开启或模型灵敏度不足 | 检查inappropriate_discrimination标签状态 | 控制台开启标签+补充自定义词库 |

### 默认测试样本覆盖范围

**AI输入检测（query_security_check）10个样本**：正常问候、政治敏感、色情内容、辱骂攻击、赌博引流、提示词注入（忽略指令型）、提示词注入（角色扮演型）、越狱诱导、敏感信息（身份证号）、歧视偏见

**AI生成检测（response_security_check）10个样本**：正常回答、生成敏感信息（信用卡号）、生成敏感信息（手机号）、生成敏感信息（邮箱）、生成违规内容（毒品制作）、生成违规内容（暴力教学）、生成歧视内容、生成虚假信息、生成色情内容、生成暴恐内容

## AI-Mode 与 SDK 配置声明

本 Skill 使用阿里云 Python SDK 调用内容安全服务。`references/console-guide.md` 中包含 aliyun CLI 示例仅用于手动调试，不作为自动化调用链路。

### aliyun CLI AI-Mode 配置

本 Skill 主要通过 Python SDK 调用，不依赖 AI-Mode 插件。`references/console-guide.md` 中的 aliyun CLI 命令仅用于手动调试参考。AI-Mode 生命周期管理命令如下：

```bash
# 启用 AI-Mode
aliyun configure ai-mode enable

# 设置 User-Agent
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"

# 禁用 AI-Mode
aliyun configure ai-mode disable

# 更新插件
aliyun plugin update
```

当前状态：AI-Mode 默认 disabled，本 Skill 不通过 AI-Mode 插件调用 CLI。系统命令（如 `--help`、`configure`）不设置 user-agent。

### SDK 配置规范

- SDK Config 已设置 `user_agent="AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"`
- SDK Config 已设置 `read_timeout=30` 和 `connect_timeout=10`
- 所有 API 调用通过默认凭证链获取凭证（环境变量 → credentials 文件 → ECS RAM 角色），代码中不硬编码凭证

## 安全规范

- 凭证通过默认凭证链自动获取，无需显式配置
- 浏览器登录步骤引导用户手动完成，不自动输入密码
- 每次控制台配置前向用户确认

## 参考资源

完整标签体系、审核服务列表及控制台操作指南请见 `references/` 目录：

- 完整标签配置矩阵: [references/label-matrix.md](references/label-matrix.md)
- 场景详细说明: [references/scenarios.md](references/scenarios.md)
- 控制台自动化指南: [references/console-guide.md](references/console-guide.md)

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | CLI主入口（run/annotate/report） |
| `ai_guardrail.py` | AI安全护栏效果测试（输入检测+生成检测，支持JSON/XLSX输出） |
| `cst.py` | 一站式入口（init/configure/test/annotate/report/guardrail/status/full） |
| `scenarios.py` | 场景模板和标签配置矩阵 |
| `console_automator.py` | 控制台浏览器自动化 |
| `scenario_manager.py` | 场景管理工具 |
| `prepare_novel.py` | 长文本预处理 |
| `verify_auth.py` | 凭证链连通性验证 |

