#!/usr/bin/env python3
"""
Translate Chinese content in SKILL.md to English
"""

import re

def translate_skill_md():
    """Translate all Chinese content in SKILL.md to English"""
    
    # Read the file
    with open('/Users/chenhang/.qoder/skills/alibabacloud-waf-rule-management/SKILL.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Translation mapping
    translations = {
        # Section 0 - Profile Configuration
        'Assistant: 请问您使用哪个阿里云CLI profile？（如：default、waf-diag等）': 'Assistant: Which Alibaba Cloud CLI profile do you use? (e.g., default, waf-diag, etc.)',
        'User: 我用的是 my-waf-profile': 'User: I use my-waf-profile',
        'Assistant: 好的,我将使用 --profile my-waf-profile 执行查询': 'Assistant: OK, I will use --profile my-waf-profile to execute the query',
        'Assistant: 好的，我将使用 --profile my-waf-profile 执行查询': 'Assistant: OK, I will use --profile my-waf-profile to execute the query',
        
        # Section 1 - Interception Diagnosis
        '#### 1.1 识别用户意图': '#### 1.1 Identify User Intent',
        '拦截诊断支持以下查询方式：': 'Interception diagnosis supports the following query methods:',
        '| 查询方式 | 示例 | 说明 |': '| Query Method | Example | Description |',
        '| traceid | `traceid: 0bd17c2e...` | 精确查询单条请求 |': '| traceid | `traceid: 0bd17c2e...` | Exact query for a single request |',
        '| host + url_path + status | `host:api.example.com, path:/login, status:405` | 组合条件查询 |': '| host + url_path + status | `host:api.example.com, path:/login, status:405` | Combined condition query |',
        '| host + IP | `host:example.com, ip:1.2.3.4` | 按域名和源IP查询 |': '| host + IP | `host:example.com, ip:1.2.3.4` | Query by domain and source IP |',
        '| 仅 traceid 字符串 | 用户直接粘贴符合格式的字符串 | 自动识别为 traceid |': '| Only traceid string | User directly pastes a string matching the format | Automatically recognized as traceid |',
        
        '#### 1.2 Traceid 提取规则': '#### 1.2 Traceid Extraction Rules',
        '**格式定义**：': '**Format Definition**:',
        '- 允许字符：小写字母 (a-z)、数字 (0-9)、连字符 (-)': '- Allowed characters: lowercase letters (a-z), digits (0-9), hyphens (-)',
        '- 必须同时包含至少一个字母和至少一个数字': '- Must contain at least one letter and at least one digit',
        '- 有效长度（含分隔符）：26、30、32、35、36 个字符': '- Valid length (including separators): 26, 30, 32, 35, 36 characters',
        
        '**提取优先级**（从高到低，取最新出现的一个）：': '**Extraction Priority** (from highest to lowest, take the most recent occurrence):',
        '1. 用户提供的 WAF 日志中的 `request_traceid` 字段值': '1. The `request_traceid` field value from WAF logs provided by the user',
        '2. 用户明确表述的 "traceid: xxx"、"请求ID是: xxx"、"这条流 xxx"': '2. User explicitly states "traceid: xxx", "Request ID is: xxx", "This flow xxx"',
        '3. 用户直接提供的、符合上述格式定义的裸字符串': '3. Raw string directly provided by the user that matches the format definition above',
        
        '**排除规则**（不得提取为 traceid）：': '**Exclusion Rules** (must not be extracted as traceid):',
        '- "事件id" 关键字后面的值': '- Values after the "event id" keyword',
        '- HTML meta 标签中的 content 值（如 aliyun_waf_aa 的 content）': '- Content values in HTML meta tags (e.g., content of aliyun_waf_aa)',
        '- 纯十六进制且无字母数字混合的哈希值': '- Pure hexadecimal hash values without letter-digit mixing',
        
        '#### 1.3 时间参数处理': '#### 1.3 Time Parameter Handling',
        '- 用户提供的时间需转换为 Unix 时间戳（秒）': '- User-provided time must be converted to Unix timestamp (seconds)',
        '- 时间戳（int 或 str）：`1774345200` → 直接使用': '- Timestamp (int or str): `1774345200` → use directly',
        '- 日期时间：`2026-03-24 17:50` → 转为时间戳': '- Date time: `2026-03-24 17:50` → convert to timestamp',
        '- 相对时间：`1h`（1小时前）、`30m`（30分钟前）、`1d`（1天前）→ 基于当前时间计算': '- Relative time: `1h` (1 hour ago), `30m` (30 minutes ago), `1d` (1 day ago) → calculate based on current time',
        '- **不传则默认查询最近 7 天**（覆盖 WAF 日志默认保留周期）': '- **If not provided, default to query the last 7 days** (covers WAF log default retention period)',
        
        '> **重要**：查询日志时注意核对时区和日期，避免查不到数据。': '> **Important**: When querying logs, verify timezone and date to avoid missing data.',
        
        '#### 1.4 日志查询': '#### 1.4 Log Query',
        '> **重要**：默认查询可能返回截断的字段，建议使用 `select` 显式指定关键字段以确保完整提取。': '> **Important**: Default queries may return truncated fields. It is recommended to use `select` to explicitly specify key fields to ensure complete extraction.',
        '> 完整 CLI 命令示例见 [references/cli_commands.md](references/cli_commands.md)。': '> For complete CLI command examples, see [references/cli_commands.md](references/cli_commands.md).',
        
        '**关键字段说明**：': '**Key Field Descriptions**:',
        '| 字段 | 含义 |': '| Field | Meaning |',
        '| `matched_host` | **防护对象**（WAF 匹配的防护对象名称） |': '| `matched_host` | **Protection Object** (WAF matched protection object name) |',
        '| `host` | 请求域名 |': '| `host` | Request domain |',
        '| `real_client_ip` | 客户端真实 IP |': '| `real_client_ip` | Real client IP |',
        '| `request_path` | 请求路径 |': '| `request_path` | Request path |',
        '| `request_method` | 请求方法 |': '| `request_method` | Request method |',
        '| `status` | WAF 返回状态码 |': '| `status` | WAF returned status code |',
        '| `final_plugin` | 触发模块（waf/cc/customrule 等） |': '| `final_plugin` | Triggered module (waf/cc/customrule, etc.) |',
        '| `final_rule_id` | 触发规则 ID |': '| `final_rule_id` | Triggered rule ID |',
        '| `waf_rule_type` | 触发规则类型 |': '| `waf_rule_type` | Triggered rule type |',
        '| `waf_action` | WAF 动作（block/pass） |': '| `waf_action` | WAF action (block/pass) |',
        
        '**查询示例**（完整命令见 cli_commands.md）：': '**Query Examples** (complete commands see cli_commands.md):',
        '- 按 traceid 查询：`request_traceid:<traceid>`': '- Query by traceid: `request_traceid:<traceid>`',
        '- 按 host + url_path + status：`host:<domain> and request_path:<path> and status:<status_code>`': '- Query by host + url_path + status: `host:<domain> and request_path:<path> and status:<status_code>`',
        '- 按 host + IP：`host:<domain> and real_client_ip:<ip>`': '- Query by host + IP: `host:<domain> and real_client_ip:<ip>`',
        '- 查询被阻断的请求：`request_traceid:<traceid> and final_action:block`': '- Query blocked requests: `request_traceid:<traceid> and final_action:block`',
        
        '> **注意**：`waf_hit` 字段在部分日志中不存在，查询时请勿包含，否则会报错 `Column \'waf_hit\' cannot be resolved`。': '> **Note**: The `waf_hit` field does not exist in some logs. Do not include it in queries, otherwise it will report error `Column \'waf_hit\' cannot be resolved`.',
        
        '#### 1.5 结果处理': '#### 1.5 Result Handling',
        '- **查询失败/报错**：检查 `aliyunlog` 是否已安装、AK/SK 是否正确、Region 是否匹配': '- **Query failed/error**: Check if `aliyunlog` is installed, AK/SK is correct, Region matches',
        '- **0 条结果**：提示用户"未查到日志，请确认条件是否正确，或请求是否在15天之内"': '- **0 results**: Prompt user "No logs found, please confirm if conditions are correct, or if the request was within 15 days"',
        '- **1 条结果**：直接进行分析并输出结论': '- **1 result**: Directly analyze and output conclusions',
        '- **多条结果**：逐条分析，汇总后输出': '- **Multiple results**: Analyze each one, then summarize and output',
        '- **字段缺失/截断**：如果 `matched_host`、`real_client_ip` 等关键字段为空或未返回，使用显式字段查询方式重新查询': '- **Missing/truncated fields**: If key fields like `matched_host`, `real_client_ip` are empty or not returned, re-query using explicit field query method',
        
        '#### 1.6 分析输出格式': '#### 1.6 Analysis Output Format',
        '按以下结构向用户输出：': 'Output to users in the following structure:',
        '1. **请求基本信息**：防护对象(matched_host)、域名(host)、源IP(real_client_ip)、请求路径、时间': '1. **Request Basic Information**: Protection object (matched_host), domain (host), source IP (real_client_ip), request path, time',
        '2. **阻断原因**：触发的模块(final_plugin)、规则ID(final_rule_id)、规则类型': '2. **Blocking Reason**: Triggered module (final_plugin), rule ID (final_rule_id), rule type',
        '3. **处置建议**：具体的操作步骤': '3. **Handling Suggestions**: Specific operation steps',
        '4. **上下文信息（用于后续配置）**：在最后添加一行，格式如下（仅供 AI 后续使用，用户无需关注）：': '4. **Context Information (for subsequent configuration)**: Add a line at the end in the following format (for AI subsequent use only, users don\'t need to pay attention):',
        '   > 可用配置信息：防护对象={matched_host}，源IP={real_client_ip}，规则ID={final_rule_id}': '   > Available configuration info: Protection object={matched_host}, source IP={real_client_ip}, rule ID={final_rule_id}',
        
        '#### 1.7 诊断后提供配置指导': '#### 1.7 Provide Configuration Guidance After Diagnosis',
        '**在给出拦截诊断结论和建议后，必须向用户提供配置指导：**': '**After providing interception diagnosis conclusions and suggestions, must provide configuration guidance to users:**',
        '> 诊断完成。如需解决此问题，我可以为你提供详细的配置指导方案。': '> Diagnosis complete. To resolve this issue, I can provide you with detailed configuration guidance.',
        '- 如果用户选择**不需要配置指导**，流程结束': '- If user chooses **no configuration guidance needed**, process ends',
        '- 如果用户选择**需要配置指导**，进入第 2 章「规则配置指导」': '- If user chooses **needs configuration guidance**, proceed to Chapter 2 "Rule Configuration Guidance"',
        
        # Section 2 - Rule Configuration Guidance
        '### 2. 规则配置指导（只读模式）': '### 2. Rule Configuration Guidance (Read-Only Mode)',
        '> ⚠️ **重要：本章仅提供配置指导方案，不会执行任何写操作。所有配置需用户在控制台手动完成。**': '> ⚠️ **Important: This chapter only provides configuration guidance, will not perform any write operations. All configurations must be manually completed by users in the console.**',
        
        '#### 2.1 上下文感知（重要）': '#### 2.1 Context Awareness (Important)',
        '在处理用户的配置请求时，应遵循以下优先级：': 'When handling user configuration requests, follow these priorities:',
        '1. **自动提取**：优先从当前对话上下文中提取已知参数：': '1. **Auto-extract**: Prioritize extracting known parameters from current conversation context:',
        '   - 防护对象（matched_host）': '   - Protection object (matched_host)',
        '   - 源IP（real_client_ip）': '   - Source IP (real_client_ip)',
        '   - 规则ID（final_rule_id）': '   - Rule ID (final_rule_id)',
        '   - 域名/host': '   - Domain/host',
        '2. **已有所需信息**：如果从上下文已获取到防护对象、IP 等关键信息，直接使用，**不再重复询问用户**': '2. **Already have required info**: If key information like protection object, IP has been obtained from context, use directly, **do not ask user again**',
        '3. **信息不足**：只有当关键信息（防护对象、具体需求）确实未知时，才询问用户': '3. **Insufficient info**: Only ask user when key information (protection object, specific requirements) is truly unknown',
        
        '#### 2.2 生成配置指导方案': '#### 2.2 Generate Configuration Guidance Plan',
        '根据用户需求分析并生成详细的配置指导方案。': 'Analyze and generate detailed configuration guidance plan based on user requirements.',
        '**输出格式要求**：': '**Output Format Requirements**:',
        '- 输出文字描述的配置信息（表格或列表形式）': '- Output text-described configuration information (table or list format)',
        '- ❌ **不再提供规则 JSON 示例**': '- ❌ **No longer provide rule JSON examples**',
        '- 文字描述应包含：防护对象、IP/URL 条件、处置动作、跳过/触发的规则等关键信息': '- Text description should include: protection object, IP/URL conditions, disposal action, skipped/triggered rules and other key information',
        '- **必须包含详细的控制台操作步骤**': '- **Must include detailed console operation steps**',
        
        '**重要规则构造约束**：': '**Important Rule Construction Constraints**:',
        '- **所有规则名称和防护模版名称中不能包含空格**，使用下划线（_）或短划线（-）代替': '- **All rule names and protection template names must not contain spaces**, use underscores (_) or hyphens (-) instead',
        '- **一个用户需求只生成一条规则**：不要为同一个需求创建多条规则': '- **One user requirement generates only one rule**: Do not create multiple rules for the same requirement',
        '- **白名单 IP 条件的 opValue 必须用 `contain`**：白名单（whitelist）场景下 IP 只允许 `contain` 和 `not-contain`，**禁止使用 `eq`**': '- **Whitelist IP condition opValue must use `contain`**: In whitelist scenarios, IP only allows `contain` and `not-contain`, **`eq` is prohibited**',
        '- **opValue 必须与 key 类型和 DefenseScene 兼容**：参照 api_reference.md 第 8 章"key 与 opValue 兼容性速查"选择正确的 opValue，不要使用 `inl`': '- **opValue must be compatible with key type and DefenseScene**: Refer to Chapter 8 "key and opValue Compatibility Quick Reference" in api_reference.md to select correct opValue, do not use `inl`',
        '- **WAF 3.0 没有数字优先级配置**：规则执行顺序由规则列表的上下位置决定，**不是**通过数字优先级（如100、200）配置。调整规则顺序需要通过控制台的拖拽或上下移动按钮实现': '- **WAF 3.0 has no numeric priority configuration**: Rule execution order is determined by vertical position in rule list, **not** through numeric priority (e.g., 100, 200). Adjusting rule order requires drag-and-drop or up/down buttons in console',
        
        '**IP 访问控制配置方案**：': '**IP Access Control Configuration Plan**:',
        '当用户需要实现"只允许特定 IP/IP 段访问域名"的需求时，有以下两种方案：': 'When users need to implement "only allow specific IP/IP range to access domain" requirement, there are two options:',
        
        '**方案一：自定义规则（推荐）**': '**Option 1: Custom Rule (Recommended)**',
        '- 使用 `custom_acl` DefenseScene': '- Use `custom_acl` DefenseScene',
        '- 配置条件：IP **不属于** 指定网段（使用 `ne` 或 `all-not-match` 操作符）': '- Configuration condition: IP **does not belong to** specified network segment (use `ne` or `all-not-match` operator)',
        '- 配置动作：**拦截**（`block`）': '- Configuration action: **Block** (`block`)',
        '- 优点：逻辑清晰，一条规则即可实现': '- Advantage: Clear logic, can be implemented with one rule',
        '- 示例：只允许 `123.2.0.0/24` 访问': '- Example: Only allow `123.2.0.0/24` to access',
        '  - 规则名称：`block_non_123.2.0.0_24`': '  - Rule name: `block_non_123.2.0.0_24`',
        '  - 匹配条件：IP 不属于 `123.2.0.0/24`': '  - Match condition: IP does not belong to `123.2.0.0/24`',
        '  - 处置动作：拦截': '  - Disposal action: Block',
        
        '**方案二：白名单 + 基础防护**': '**Option 2: Whitelist + Basic Protection**',
        '- 使用 `whitelist` DefenseScene 配置白名单': '- Use `whitelist` DefenseScene to configure whitelist',
        '- 配置条件：IP **包含** 指定网段（使用 `contain` 操作符）': '- Configuration condition: IP **contains** specified network segment (use `contain` operator)',
        '- 配合基础防护（`waf_group` 或 `waf_base`）默认拦截': '- Combined with basic protection (`waf_group` or `waf_base`) default blocking',
        '- 优点：符合白名单设计理念': '- Advantage: Aligns with whitelist design philosophy',
        '- 注意：必须确保基础防护已开启，否则其他 IP 不会被拦截': '- Note: Must ensure basic protection is enabled, otherwise other IPs will not be blocked',
        '- 示例：白名单 `123.2.0.0/24`': '- Example: Whitelist `123.2.0.0/24`',
        '  - 规则名称：`whitelist_123.2.0.0_24`': '  - Rule name: `whitelist_123.2.0.0_24`',
        '  - 匹配条件：IP 包含 `123.2.0.0/24`': '  - Match condition: IP contains `123.2.0.0/24`',
        '  - 跳过模块：waf, cc, customrule, blacklist, antiscan': '  - Skip modules: waf, cc, customrule, blacklist, antiscan',
        
        '> DefenseScene 完整取值参考见 [references/api_reference.md](references/api_reference.md) 第5章。': '> For complete DefenseScene values, refer to Chapter 5 of [references/api_reference.md](references/api_reference.md).',
        
        '#### 2.3 查询现有配置（可选）': '#### 2.3 Query Existing Configuration (Optional)',
        '> **执行任何 CLI 命令前，先查阅 [references/cli_traps.md](references/cli_traps.md) 中的已知陷阱清单。**': '> **Before executing any CLI commands, consult the known traps list in [references/cli_traps.md](references/cli_traps.md).**',
        '在生成配置指导方案前，可以查询现有配置以便提供更准确的建议：': 'Before generating configuration guidance plan, you can query existing configuration to provide more accurate suggestions:',
        
        '##### 2.3.1 查询 WAF 实例信息': '##### 2.3.1 Query WAF Instance Information',
        '##### 2.3.2 查询防护对象已绑定的防护模版': '##### 2.3.2 Query Protection Templates Bound to Protection Object',
        '##### 2.3.3 查询已有规则': '##### 2.3.3 Query Existing Rules',
        '> **API 陷阱**：白名单(whitelist)场景必须加 `--RuleType whitelist`，否则查询结果为 0 条。': '> **API Trap**: Whitelist scenarios must add `--RuleType whitelist`, otherwise query result will be 0.',
        
        '##### 2.3.4 IP 格式验证': '##### 2.3.4 IP Format Validation',
        '        return False, "IP格式错误"': '        return False, "Invalid IP format"',
        '            return False, f"IP段超出范围: {part}"': '            return False, f"IP segment out of range: {part}"',
        '    return True, "验证通过"': '    return True, "Validation passed"',
        
        '#### 2.4 输出配置指导方案': '#### 2.4 Output Configuration Guidance Plan',
        '在输出配置指导方案时，必须包含以下内容：': 'When outputting configuration guidance plan, must include the following content:',
        '1. **配置概述**：说明要实现的目标和整体思路': '1. **Configuration Overview**: Explain the goal to achieve and overall approach',
        '2. **规则配置详情**：': '2. **Rule Configuration Details**:',
        '   - 防护对象': '   - Protection object',
        '   - IP/URL 条件': '   - IP/URL conditions',
        '   - 处置动作': '   - Disposal action',
        '   - 规则名称建议': '   - Rule name suggestion',
        '3. **控制台操作步骤**：详细的点击路径和填写说明': '3. **Console Operation Steps**: Detailed click path and filling instructions',
        '4. **注意事项**：安全风险提示、生效时间等': '4. **Precautions**: Security risk warnings, effective time, etc.',
        
        '##### 2.4.1 WAF 3.0 控制台路径（重要）': '##### 2.4.1 WAF 3.0 Console Path (Important)',
        '> 极其重要：WAF 3.0 与 WAF 2.0 的控制台路径不同，必须使用 WAF 3.0 的正确路径。': '> Extremely important: WAF 3.0 and WAF 2.0 have different console paths, must use correct WAF 3.0 paths.',
        '**WAF 3.0 正确路径**：': '**WAF 3.0 Correct Paths**:',
        '- 白名单配置：`防护配置` → `白名单`': '- Whitelist configuration: `Protection Configuration` → `Whitelist`',
        '- 自定义规则：`防护配置` → `Web核心防护` → `自定义规则`': '- Custom rules: `Protection Configuration` → `Web Core Protection` → `Custom Rules`',
        '- CC防护：`防护配置` → `Web核心防护` → `CC防护`': '- CC protection: `Protection Configuration` → `Web Core Protection` → `CC Protection`',
        '- IP 黑名单：`防护配置` → `Web核心防护` → `IP 黑名单`': '- IP blacklist: `Protection Configuration` → `Web Core Protection` → `IP Blacklist`',
        '> WAF 3.0 API 版本为 `2021-10-01`，使用 `waf-openapi` 产品名称。如用户未明确说明版本，默认按 WAF 3.0 处理。': '> WAF 3.0 API version is `2021-10-01`, uses `waf-openapi` product name. If user does not specify version, default to WAF 3.0.',
        
        '##### 2.4.2 配置注意事项': '##### 2.4.2 Configuration Precautions',
        '- 所有规则名称和防护模版名称中不能包含空格': '- All rule names and protection template names must not contain spaces',
        '- 白名单 IP 条件的 opValue 必须用 `contain`，**禁止使用 `eq`**': '- Whitelist IP condition opValue must use `contain`, **`eq` is prohibited**',
        '- opValue 必须与 key 类型和 DefenseScene 兼容': '- opValue must be compatible with key type and DefenseScene',
        '- 一个用户需求只生成一条规则': '- One user requirement generates only one rule',
        
        '#### 2.5 配置指导输出格式': '#### 2.5 Configuration Guidance Output Format',
        '在给出配置指导方案时，按以下结构输出：': 'When providing configuration guidance plan, output in the following structure:',
        '**⚠️ 重要：输出必须简洁，只输出核心内容，不要发散：**': '**⚠️ Important: Output must be concise, only output core content, do not diverge:**',
        '- 直接给出配置步骤，避免冗长的背景说明': '- Directly provide configuration steps, avoid lengthy background explanations',
        '- 使用表格或列表形式，信息密度高': '- Use table or list format, high information density',
        '- 控制在 3-5 个核心配置项': '- Control to 3-5 core configuration items',
        '- 注意事项只列最关键的 2-3 条': '- List only the most critical 2-3 precautions',
        '- 不要展开解释技术细节，除非用户明确要求': '- Do not expand on technical details unless user explicitly requests',
        
        '1. **配置方案概述**（1-2句话）': '1. **Configuration Plan Overview** (1-2 sentences)',
        '   - 实现目标': '   - Implementation goal',
        '   - 整体思路': '   - Overall approach',
        '2. **详细配置步骤**（核心）': '2. **Detailed Configuration Steps** (Core)',
        '   - 控制台操作路径': '   - Console operation path',
        '   - 每个字段的填写说明（表格形式）': '   - Filling instructions for each field (table format)',
        '   - 规则条件配置示例': '   - Rule condition configuration example',
        '3. **注意事项**（精简）': '3. **Precautions** (Concise)',
        '   - 安全风险提示（1句话）': '   - Security risk warning (1 sentence)',
        '   - 生效时间说明（1句话）': '   - Effective time explanation (1 sentence)',
        
        '#### 2.6 安全风险提示': '#### 2.6 Security Risk Warnings',
        '##### 扫描器 IP 加白风险': '##### Scanner IP Whitelist Risk',
        '**当请求的 User-Agent 包含扫描器标识时（如 `ANCHASHI-SCAN`、`Nessus`、`AWVS`、`sqlmap` 等），加白该 IP 存在严重安全风险：**': '**When request User-Agent contains scanner identifiers (e.g., `ANCHASHI-SCAN`, `Nessus`, `AWVS`, `sqlmap`, etc.), whitelisting this IP poses serious security risks:**',
        '- 扫描器可以绕过指定检测规则继续探测漏洞': '- Scanner can bypass specified detection rules to continue probing for vulnerabilities',
        '- 如果是生产环境，可能导致真实漏洞被利用': '- If in production environment, may lead to real vulnerabilities being exploited',
        '**处置建议**：': '**Handling Suggestions**:',
        '1. **限制 URL 范围**：添加 URL 条件，只对特定路径生效': '1. **Limit URL scope**: Add URL conditions, only effective for specific paths',
        '2. **设置临时有效期**：明确告知用户这是临时加白，建议 24 小时后清理': '2. **Set temporary validity**: Clearly inform user this is temporary whitelisting, recommend cleanup after 24 hours',
        '3. **要求用户确认**：询问"确认这是内部测试 IP 吗？"': '3. **Require user confirmation**: Ask "Confirm this is an internal test IP?"',
        
        '##### 规则命名规范': '##### Rule Naming Convention',
        '规则名称建议包含以下信息以便追溯：': 'Rule names should include the following information for traceability:',
        'whitelist_<用途>_<时间>_<IP>_<规则ID>': 'whitelist_<purpose>_<date>_<IP>_<ruleID>',
        '# 示例：whitelist_scan_test_20260331_101.201.33.171_113160': '# Example: whitelist_scan_test_20260331_101.201.33.171_113160',
        
        '##### 生效延迟提示': '##### Effective Delay Notice',
        '提醒用户规则配置后通常 **10-30 秒** 生效，高峰期可能更长：': 'Remind users that rules typically take effect within **10-30 seconds** after configuration, may be longer during peak hours:',
        '> "配置完成后，预计 30 秒内生效。如需立即验证，请稍后测试。': '> "After configuration completes, expected to take effect within 30 seconds. For immediate verification, please test later.',
        
        # Section 3 - Rule Not Effective Diagnosis
        '### 3. 规则不生效诊断（扩展功能）': '### 3. Rule Not Effective Diagnosis (Extended Feature)',
        '当用户反馈已配置的规则未命中流量时，使用以下流程诊断。': 'When users report configured rules not matching traffic, use the following process to diagnose.',
        
        '#### 3.1 信息收集': '#### 3.1 Information Collection',
        '| 信息 | 必须 | 说明 |': '| Information | Required | Description |',
        '| rule_id | 是 | 不生效的规则 ID |': '| rule_id | Yes | Rule ID not taking effect |',
        '| flow_info | 是 | 流量标识（traceid / 源IP+时间 / 域名+路径+时间） |': '| flow_info | Yes | Traffic identifier (traceid / source IP+time / domain+path+time) |',
        '| issue_type | 是 | 问题类型：规则不拦截 / 白名单不放行 |': '| issue_type | Yes | Issue type: rule not blocking / whitelist not allowing |',
        '| resource | 否 | 防护对象名称 |': '| resource | No | Protection object name |',
        '**上下文感知**：如果用户之前使用过拦截诊断分析过某条流量，应自动提取 host、matched_host、real_client_ip、traceid 等已知信息。': '**Context Awareness**: If user previously used interception diagnosis to analyze a traffic flow, should automatically extract known information like host, matched_host, real_client_ip, traceid.',
        
        '#### 3.2 诊断流程': '#### 3.2 Diagnosis Process',
        '1. 获取 WAF 实例 ID（DescribeInstance）': '1. Get WAF instance ID (DescribeInstance)',
        '2. 查询规则配置（DescribeDefenseRules with ruleId query）': '2. Query rule configuration (DescribeDefenseRules with ruleId query)',
        '3. 查询流量日志（aliyunlog get_log）': '3. Query traffic logs (aliyunlog get_log)',
        '4. 前置检查：防护对象绑定、白名单冲突、XFF 配置': '4. Pre-checks: protection object binding, whitelist conflicts, XFF configuration',
        '5. 调用诊断引擎进行条件匹配分析': '5. Call diagnosis engine for condition matching analysis',
        '完整命令见 [references/cli_commands.md](references/cli_commands.md) 第 2.1、2.2 和 3.2 节。': 'Complete commands see Section 2.1, 2.2 and 3.2 of [references/cli_commands.md](references/cli_commands.md).',
        
        '#### 3.3 调用诊断引擎': '#### 3.3 Call Diagnosis Engine',
        '将规则配置和日志数据写入临时文件，然后调用诊断引擎：': 'Write rule configuration and log data to temporary files, then call diagnosis engine:',
        '完整命令见 [references/cli_commands.md](references/cli_commands.md) 第 5 节。': 'Complete commands see Section 5 of [references/cli_commands.md](references/cli_commands.md).',
        
        '#### 3.4 诊断结论解读': '#### 3.4 Diagnosis Conclusion Interpretation',
        '| conclusion | 含义 | 建议 |': '| conclusion | Meaning | Suggestion |',
        '| `template_not_bound` | 规则所在模板未绑定到防护对象 | 将模板绑定到防护对象，或在已绑定模板中创建规则 |': '| `template_not_bound` | Template containing rule not bound to protection object | Bind template to protection object, or create rule in already bound template |',
        '| `condition_mismatch` | 规则匹配条件与实际请求不匹配 | 检查请求路径、IP等条件是否与规则配置一致 |': '| `condition_mismatch` | Rule match conditions don\'t match actual request | Check if request path, IP and other conditions match rule configuration |',
        '| `whitelist_bypass` | 白名单跳过导致规则不生效 | 调整白名单规则配置 |': '| `whitelist_bypass` | Whitelist bypass causing rule not to take effect | Adjust whitelist rule configuration |',
        '| `all_match_timing` | 所有条件匹配，生效时间不足 | 等待约1分钟后重试 |': '| `all_match_timing` | All conditions match, insufficient effective time | Wait about 1 minute and retry |',
        '| `all_match_cc` | 条件匹配但频率未达阈值 | 分析频率规则 |': '| `all_match_cc` | Conditions match but frequency hasn\'t reached threshold | Analyze frequency rules |',
        '| `module_mismatch` | 白名单跳过模块不匹配 | 调整白名单的跳过模块配置 |': '| `module_mismatch` | Whitelist skip module doesn\'t match | Adjust whitelist skip module configuration |',
        '| `already_matched` | 白名单已生效 | 告知用户白名单已经在生效 |': '| `already_matched` | Whitelist already in effect | Inform user whitelist is already in effect |',
        '| `not_matched` | IP/区域不在配置中 | 检查配置和 XFF |': '| `not_matched` | IP/region not in configuration | Check configuration and XFF |',
        
        '**常见诊断场景**：': '**Common Diagnosis Scenarios**:',
        '##### 场景1：模板未绑定到防护对象': '##### Scenario 1: Template Not Bound to Protection Object',
        '**问题表现**：规则已创建且状态正常，但流量未被拦截或放行。': '**Problem Manifestation**: Rule has been created and status is normal, but traffic is not being blocked or allowed.',
        '**诊断步骤**：': '**Diagnosis Steps**:',
        '1. 查询规则所在模板：`DescribeDefenseRules` 获取规则的 `TemplateId`': '1. Query template containing rule: `DescribeDefenseRules` to get rule\'s `TemplateId`',
        '2. 查询防护对象绑定的模板：`DescribeDefenseResourceTemplates` 获取已绑定模板列表': '2. Query templates bound to protection object: `DescribeDefenseResourceTemplates` to get list of bound templates',
        '3. 对比两者，如果规则的模板不在绑定列表中，则是此问题': '3. Compare the two, if rule\'s template is not in bound list, this is the issue',
        '**解决方案**：': '**Solution**:',
        '- 方法1：将规则所在模板绑定到防护对象': '- Method 1: Bind template containing rule to protection object',
        '  - 控制台：`防护配置` → `防护对象` → 找到目标防护对象 → `绑定模板` → 选择对应模板': '  - Console: `Protection Configuration` → `Protection Objects` → Find target protection object → `Bind Template` → Select corresponding template',
        '- 方法2：在已绑定的模板中重新创建规则': '- Method 2: Recreate rule in already bound template',
        '  - 控制台：`防护配置` → `Web核心防护` → `自定义规则` → 在已绑定模板中创建': '  - Console: `Protection Configuration` → `Web Core Protection` → `Custom Rules` → Create in already bound template',
        
        '##### 场景2：规则匹配条件与实际请求不符': '##### Scenario 2: Rule Match Conditions Don\'t Match Actual Request',
        '**问题表现**：规则配置了特定URI或IP条件，但实际请求不满足这些条件。': '**Problem Manifestation**: Rule configured with specific URI or IP conditions, but actual request doesn\'t meet these conditions.',
        '**诊断步骤**：': '**Diagnosis Steps**:',
        '1. 查询规则配置：查看 `conditions` 字段中的匹配条件': '1. Query rule configuration: Check match conditions in `conditions` field',
        '2. 查询流量日志：查看 `request_path`、`real_client_ip` 等字段': '2. Query traffic logs: Check `request_path`, `real_client_ip` and other fields',
        '3. 对比规则条件与实际请求是否匹配': '3. Compare rule conditions with actual request to see if they match',
        '**示例**：': '**Example**:',
        '- 规则配置：URI **包含** `/chenhang`': '- Rule configuration: URI **Contains** `/chenhang`',
        '- 实际请求：`request_path: "/"`': '- Actual request: `request_path: "/"`',
        '- 结论：路径不匹配，规则不会生效': '- Conclusion: Path doesn\'t match, rule will not take effect',
        
        # Section 4 - Troubleshooting
        '### 4. 常见问题排查': '### 4. Troubleshooting',
        '遇到问题时，查阅 [references/troubleshooting.md](references/troubleshooting.md) 获取详细解决方案。': 'When encountering issues, consult [references/troubleshooting.md](references/troubleshooting.md) for detailed solutions.',
        
        # Appendix
        '### 附录：引用文件说明': '### Appendix: Reference File Descriptions',
        '| 文件 | 用途 |': '| File | Purpose |',
        '| [references/cli_guide.md](references/cli_guide.md) | 阿里云 CLI 通用格式、SLS 配置推导、日志字段参考 |': '| [references/cli_guide.md](references/cli_guide.md) | Alibaba Cloud CLI general format, SLS configuration derivation, log field reference |',
        '| [references/api_reference.md](references/api_reference.md) | WAF 3.0 OpenAPI 参数规范（规则 JSON 构造权威参考） |': '| [references/api_reference.md](references/api_reference.md) | WAF 3.0 OpenAPI parameter specification (authoritative reference for rule JSON construction) |',
        '| [references/cli_traps.md](references/cli_traps.md) | CLI 调用常见陷阱和错误模式 |': '| [references/cli_traps.md](references/cli_traps.md) | Common CLI invocation traps and error patterns |',
        '| [references/ram-policies.md](references/ram-policies.md) | RAM 权限声明（最小权限清单） |': '| [references/ram-policies.md](references/ram-policies.md) | RAM permission statement (minimum permission list) |',
        '| [references/troubleshooting.md](references/troubleshooting.md) | 常见问题排查指南 |': '| [references/troubleshooting.md](references/troubleshooting.md) | Troubleshooting guide |',
        '| [scripts/rule_matcher.py](scripts/rule_matcher.py) | 规则条件匹配诊断引擎（纯逻辑脚本） |': '| [scripts/rule_matcher.py](scripts/rule_matcher.py) | Rule condition matching diagnosis engine (pure logic script) |',
    }
    
    # Apply translations
    for chinese, english in translations.items():
        content = content.replace(chinese, english)
    
    # Write back
    with open('/Users/chenhang/.qoder/skills/alibabacloud-waf-rule-management/SKILL.md', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Translation completed successfully!")

if __name__ == '__main__':
    translate_skill_md()
