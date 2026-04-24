---
name: alibabacloud-quickbi-smartq
description: |
  Quick BI-SmartQ skill with multiple data analysis capabilities:
  1. **File Q&A**: Upload Excel/CSV files for intelligent analysis via Quick BI API
  2. **Dataset Q&A**: Natural language queries on Quick BI platform datasets, with automatic intelligent table selection and matching
  3. **Document Parsing**: Parse PDF/Word/Excel/CSV/images, extract text, and support extracting key fields to generate structured Excel
  4. **Dashboard Skill Generation**: Auto-convert QuickBI dashboards into data query skills
  5. **Data Insight**: Deep data insight analysis on Quick BI datasets
  6. **Data Report**: Auto-generate professional data reports based on analysis results
  Use when users mention data analysis, smart Q&A, querying data, file analysis,
  document parsing, dashboard skills, data insight, or data reports.
compatibility: "tools: [python3, pip, browser], runtime: [requests, pyyaml, matplotlib, numpy]"
metadata:
  label: Quick BI-SmartQ
  version: "1.3.0"
---

# Quick BI-SmartQ — QuickBI Data Analysis Assistant

One entry point covering all QuickBI data analysis capabilities. Automatically routes to the corresponding module based on user intent — no manual selection required.

## Scope

**Does:**
- Automatically identify user intent and route to the corresponding data analysis module
- Perform natural-language analysis on user-uploaded Excel/CSV files via the Quick BI API (File Q&A)
- Perform natural-language query analysis on Quick BI platform datasets, with automatic intelligent table selection and matching (Dataset Q&A)
- Parse PDF/Word/Excel/CSV/images, extract text, and support extracting key fields to generate structured Excel (Document Parsing)
- Auto-convert QuickBI dashboards into data query skills (Dashboard Skill Generation)
- Perform deep insight analysis on datasets (Data Insight)
- Auto-generate professional data reports based on analysis results (Data Report)

**Does NOT:**
- Use pandas/openpyxl/csv or similar libraries to read files locally for analysis in Q&A scenarios
- Require users to manually choose a module or provide internal parameters such as cubeId
- Perform tasks unrelated to QuickBI data analysis

## Task Routing

Automatically determine intent based on user input and route to the corresponding module for execution.

### Routing Decision Table

| User Intent  | Routed Module | Reference Document |
|------------------------|--------------------------|------------------------------|
| Uploaded Excel/CSV file, wants to query specific metrics or answer specific data questions (e.g. TOP N, comparison, filtering) | File Q&A | [module-chat-file.md](references/chat/module-chat-file.md) |
| 上传了 Excel/CSV 文件，要查询具体指标或回答具体数据问题（如 TOP N、对比、筛选） | File Q&A | [module-chat-file.md](references/chat/module-chat-file.md) |
| No file uploaded, wants to query/analyze specific metrics in platform datasets | Dataset Q&A | [module-chat-dataset.md](references/chat/module-chat-dataset.md) |
| 未上传文件，要查询/分析平台数据集中的具体指标 | Dataset Q&A | [module-chat-dataset.md](references/chat/module-chat-dataset.md) |
| Uploaded multiple files (PDF/Word/images etc.) or selected a folder, wants to query specific data questions (e.g. TOP N, comparison, filtering) | Document Parsing → File Q&A | [module-document-parser.md](references/document/module-document-parser.md) → [module-chat-file.md](references/chat/module-chat-file.md) |
| 上传了多个文件(PDF/word/图片等)，或者选择文件夹，要查询具体数据问题（如 TOP N、对比、筛选） | Document Parsing → File Q&A | [module-document-parser.md](references/document/module-document-parser.md) → [module-chat-file.md](references/chat/module-chat-file.md) |
| Uploaded PDF/Word/images or other unstructured documents, or selected a folder, wants to parse all file contents or extract fields | Document Parsing | [module-document-parser.md](references/document/module-document-parser.md) |
| 上传了 PDF/Word/图片等非结构化文档，或者选择文件夹，要解析所有文件内容或提取字段 | Document Parsing | [module-document-parser.md](references/document/module-document-parser.md) |
| Provided a QuickBI dashboard URL, wants to generate a query skill | Dashboard Skill Generation | [module-dashboard.md](references/dashboard/module-dashboard.md) |
| 提供了 QuickBI 仪表板 URL，要生成查询技能 | Dashboard Skill Generation | [module-dashboard.md](references/dashboard/module-dashboard.md) |
| Uploaded Excel file, wants deep interpretation/insight/trend analysis of data (not generating a report document) | Data Insight | [module-data-insight.md](references/insight/module-data-insight.md) |
| 上传了 Excel 文件，要对数据进行深度解读/洞察/趋势分析（不生成报告文档） | Data Insight | [module-data-insight.md](references/insight/module-data-insight.md) |
| Uploaded multiple files (PDF/Word/images etc.) or selected a folder, wants deep interpretation/insight/trend analysis of data (not generating a report document) | Document Parsing → Data Insight | [module-document-parser.md](references/document/module-document-parser.md) → [module-data-insight.md](references/insight/module-data-insight.md) |
| 上传了多个文件(PDF/word/图片等)，或者选择文件夹，要对数据进行深度解读/洞察/趋势分析（不生成报告文档） | Document Parsing → Data Insight | [module-document-parser.md](references/document/module-document-parser.md) → [module-data-insight.md](references/insight/module-data-insight.md) |
| Wants to generate a report/analysis report/review report, regardless of whether files are uploaded | Data Report | [module-data-report.md](references/report/module-data-report.md) |
| 要生成报告/分析报告/复盘报告，无论是否上传文件 | Data Report | [module-data-report.md](references/report/module-data-report.md) |

### Routing Priority Rules

When user intent may match multiple modules, determine by the following priority:

1. **"Report" keyword takes priority** (「报告」关键词优先): When user intent contains keywords like "report", "review", "summary report", "analysis report" (报告/复盘/总结报告/分析报告), **ALWAYS route to the Data Report module**, regardless of whether files are uploaded. Data Report module has higher priority than File Q&A and Data Insight.
2. **"Interpret", "insight", "trend" keywords** (「解读」「洞察」「趋势」关键词): When user wants to understand data meaning, discover trends, or gain insights (解读/洞察/趋势), route to the Data Insight module.
3. **Specific data query** (具体数据查询): When user wants to query specific metrics (TOP N, sum, comparison, etc.), route to the Q&A module (choose Dataset Q&A or File Q&A based on whether files are present).
4. **Dashboard URL** (仪表板 URL): When user provides a dashboard link, route to Dashboard Skill Generation.

### Routing Examples

| User Input | Routing Result | Reasoning |
|-------------------------------------|--------------------------------------------------------------|-------------------|
| "Help me find the product with the highest sales in this data" + uploaded file | → File Q&A (module-chat-file) | Querying specific metric, has file |
| "帮我查一下这份数据中销售额最高的产品" + 上传文件 | → File Q&A (module-chat-file) | 查具体指标，有文件 |
| "Help me analyze this Excel data, TOP 10 headcount by department" + uploaded file | → File Q&A (module-chat-file) | Querying specific metric (TOP N), has file |
| "帮我分析这份Excel数据，各部门人数分布TOP10" + 上传文件 | → File Q&A (module-chat-file) | 查具体指标（TOP N），有文件 |
| "Top 3 regions with the highest sales" | → Dataset Q&A (module-chat-dataset) | Querying specific metric, no file |
| "销量最高的地区TOP3" | → Dataset Q&A (module-chat-dataset) | 查具体指标，无文件 |
| "Parse these contracts and summarize the information" + folder | → Document Parsing (module-document-parser) | |
| "解析这些合同并汇总信息" + 文件夹 | → Document Parsing (module-document-parser) | |
| "Convert this dashboard into a query skill" + URL | → Dashboard Skill Generation (module-dashboard) | Provided dashboard URL |
| "把这个仪表板转化为查询技能" + URL | → Dashboard Skill Generation (module-dashboard) | 提供了仪表板 URL |
| "Help me interpret the trend in sales data" + uploaded file | → Data Insight (module-data-insight) | Requests interpretation/insight, not a report |
| "帮我解读一下销售数据的趋势" + 上传文件 | → Data Insight (module-data-insight) | 要求解读/洞察，非报告 |
| "Any patterns and insights in this data" + uploaded file | → Data Insight (module-data-insight) | Requests insight analysis |
| "这份数据有什么规律和洞察" + 上传文件 | → Data Insight (module-data-insight) | 要求洞察分析 |
| "Generate a sales data report for this month" | → Data Report (module-data-report) | Contains "report" keyword |
| "生成一份本月销售数据报告" | → Data Report (module-data-report) | 含「报告」关键词 |
| "Help me generate an analysis report based on this Excel" + uploaded file | → Data Report (module-data-report) | Contains "report" keyword, file used as reference |
| "帮我基于这份Excel生成一份分析报告" + 上传文件 | → Data Report (module-data-report) | 含「报告」关键词，文件作为参考资料 |
| "Summarize these data, write a review report" + uploaded files | → Data Report (module-data-report) | Contains "review report" keyword |
| "汇总这几份数据，写一份复盘报告" + 上传文件 | → Data Report (module-data-report) | 含「复盘报告」关键词 |
| "Combine these files to generate a data analysis report" + uploaded files | → Data Report (module-data-report) | Contains "report" keyword |
| "结合这些文件生成数据分析报告" + 上传文件 | → Data Report (module-data-report) | 含「报告」关键词 |
| "Parse these 10 invoice PDFs, extract fields and generate Excel" + multiple files | → Document Parsing (module-document-parser) | Contains "extract fields" related keywords |
| "解析这10个发票PDF，提取字段生成Excel" + 多文件 | → Document Parsing (module-document-parser) | 含"提取字段"等相关关键字 |
| "Help me find the product with the highest sales in this data" + multiple files or folder | → Document Parsing → File Q&A (module-chat-file) | Querying specific metric, has multiple files |
| "帮我查一下这份数据中销售额最高的产品" + 多个文件或者文件夹 | → Document Parsing → File Q&A (module-chat-file) | 查具体指标，有多个文件 |
| "Any patterns and insights in these files" + multiple files or folder | → Document Parsing → Data Insight (module-data-insight) | Requests insight analysis |
| "这些文件中的数据有什么规律和洞察" + 多个文件或者文件夹 | → Document Parsing → Data Insight (module-data-insight) | 要求洞察分析 |
| "Summarize these data, write a review report" + ≤5 files | → Data Report (module-data-report) | Contains "review report" keyword |
| "汇总这几份数据，写一份复盘报告" + 5个以内文件 | → Data Report (module-data-report) | 含「复盘报告」关键词 |
| "Summarize these data, write a review report" + >5 files | → Document Parsing → Data Report (module-data-report) | Contains "review report" keyword |
| "汇总这几份数据，写一份复盘报告" + >5个文件 | → Document Parsing → Data Report (module-data-report) | 含「复盘报告」关键词 |

### Fallback Rules
- When intent is unclear, **default to Dataset Q&A** (module-chat-dataset) (当意图不明确时，默认路由到数据集问数)
- If the user involves multiple modules at the same time (e.g. "analyze data and generate a report" ("分析数据并生成报告")), execute them in sequence
- **Special scenario — multi-file preprocessing before Q&A** (特殊场景 — 多文件问数前置处理):
  - When user uploads ≥5 unstructured documents (PDF/Word/images, etc.) and requests analysis
  - **MUST execute Document Parsing first** (generate structured Excel)
  - **Then route to the corresponding functional module based on question intent** (perform intelligent analysis on the generated Excel)
  - Example: "Analyze these invoice data" + 10 PDFs → Document Parsing (generate Excel) → File Q&A (analyze Excel)
  - 示例："分析这些发票数据" + 10个PDF → 文档解析(生成Excel) → 文件问数(分析Excel)
- If routing is incorrect, allow the user to manually specify the module (路由错误时允许用户手动指定模块)

## Configuration

This skill uses a **layered configuration** architecture, separating user configuration from the skill package. **Skill package updates will NOT overwrite user configuration**.

> **`<workspace-dir>` convention**: In this document, `<workspace-dir>` refers to the absolute path of the folder the user currently has open in the IDE / file manager. The Agent MUST confirm this path before the first operation by running a Python script with `os.getenv('CODE_AGENT_CURRENT_SESSION_WORK_DIR')`. If the script returns nothing or empty, use the absolute path of the folder selected by the user. MUST NOT infer using `$PWD`, `$CWD`, or `Path.cwd()` or similar runtime variables.
>
> **`<skill-package-dir>` convention**: In this document, `<skill-package-dir>` refers to the root directory of this skill after installation (i.e. the directory containing this `SKILL.md` file). The Agent can infer it from the path of this file.

### Configuration Loading Priority (higher overrides lower)

1. **Environment variable** `ACCESS_TOKEN` (highest priority, suitable for container deployment)
2. **Workspace-level configuration** `<workspace-dir>/.qbi/smartq-chat/config.yaml`
3. **QBI global configuration** `~/.qbi/config.yaml` (shared by all skills)
4. **Default configuration** `default_config.yaml` inside the skill package (package defaults, updated with the package)

`server_domain`, `api_key`, `api_secret`, and `user_token` can be placed in the workspace-level configuration or the global configuration. When both exist, the workspace-level configuration takes priority.

### Configuration Item Descriptions

- **`server_domain`**: Quick BI service domain
- **`api_key`** / **`api_secret`**: OpenAPI authentication key pair (if not configured, built-in defaults are used for trial mode)
- **`user_token`**: Quick BI platform user ID; the Q&A interface requires `userId` (if not configured, it is registered automatically and written back)

If `use_env_property: true` is enabled, the configuration can be overridden through the `qbi_api_key`, `qbi_api_secret`, `qbi_server_domain`, and `qbi_user_token` fields in the `ACCESS_TOKEN` environment variable JSON.

### Automatic Trial Credential Registration

When neither `api_key` nor `api_secret` is configured (regardless of whether `user_token` exists), the script will:
1. If `user_token` is also not configured, print a friendly message informing the user that trial credentials will be registered automatically and trial mode will begin
2. Use built-in default credentials to populate `api_key` and `api_secret`
3. Automatically register a user based on the device's unique identifier and write the userId to the global configuration `~/.qbi/config.yaml` (not affected by skill package updates)

> Note: `user_token` existing alone in the global configuration (from automatic trial registration) will NOT prevent trial credential population. ONLY when `api_key` or `api_secret` exists in an external configuration will the trial flow be skipped.

Trial expiration is controlled by the server-side interface through error code `AE0579100004` — no local tracking is required.

### Custom Configuration Guidance

When users want to use their own Quick BI account credentials (rather than trial credentials), sign in to the Quick BI console, click the avatar option **"Copy skill configuration with one click"**, as shown below:

> Show the configuration screenshot to the user based on current locale:
> - zh_CN: ![Copy Skill Config](references/common/copy_skill_config_zh.png)
> - en_US: ![Copy Skill Config](references/common/copy_skill_config_en.png)

After copying, paste the configuration to the Agent. The Agent will automatically write `server_domain`, `api_key`, `api_secret`, and `user_token` into the workspace-level configuration `<workspace-dir>/.qbi/smartq-chat/config.yaml` (and decide whether to sync to the global configuration based on the `save_global_property` switch).

## Agent Configuration Update Rules (Required Reading)

**Zero-configuration initialization for new users**: If the user says "initialize configuration", "I am a new user", or similar, but **has NOT provided any specific configuration values**, there is no need to manually write anything to any configuration file. Tell the user to run Q&A directly — the system will automatically complete trial registration (see the **Automatic Trial Credential Registration** section above).

ONLY apply the following write rules when the user **explicitly provides** specific configuration values.

**Existing configuration protection rule**: Before writing, the Agent **MUST** first check whether the workspace-level configuration file `<workspace-dir>/.qbi/smartq-chat/config.yaml` already exists and contains valid configuration. If the file already exists and is non-empty, the Agent **MUST NOT** modify or overwrite any configuration items on its own, unless the user **explicitly expresses intent to update** (e.g. "update my configuration", "replace with this configuration", "change api_key to xxx", etc.). When existing configuration is found, inform the user that configuration already exists and ask whether to confirm overwriting.

When the user provides any one or more of `api_key`, `api_secret`, `user_token`, or `server_domain`, and the above protection rule is satisfied, the Agent **MUST** use a file editing tool to directly modify the corresponding user configuration file and write the provided values into the matching fields.

**Write location rules**:
- `server_domain`, `api_key`, `api_secret`, `user_token` → **ALWAYS** write to the **workspace-level configuration** `<workspace-dir>/.qbi/smartq-chat/config.yaml`
- Global configuration read/write is controlled by the `save_global_property` switch (default `true`):
  - If the switch is `false` → **MUST NOT read or write global configuration under any circumstance**, skip the global-configuration-related steps below
  - If the switch is `true` and the **global configuration** `~/.qbi/config.yaml` is empty or does not exist → also write to the global configuration
  - If the switch is `true` and the global configuration already contains content → write ONLY to the workspace-level configuration, then ask the user "Global configuration already exists. Do you want to sync the update?" and decide whether to write based on the user's reply

**Procedure**:
1. Extract configuration key-value pairs from the user message (support common formats such as `key: value`, `key：value`, and `key=value`)
2. Use a file editing tool (such as search_replace) to write the configuration into the workspace-level configuration file
3. Read the `save_global_property` value in the configuration; if it is `false`, skip to step 5
4. Check whether the global configuration `~/.qbi/config.yaml` exists and is non-empty:
   - If it is empty or does not exist → also write to the global configuration
   - If it already contains content → ask the user "Global configuration already exists. Do you want to sync the update?" and decide whether to write based on the user's reply
5. After the update, confirm to the user which configuration items were written and where they were written

**Prohibited actions**:
- ❌ MUST NOT refuse to modify configuration citing reasons such as "limited permissions" or "unable to modify files inside the skill package"
- ❌ MUST NOT suggest workarounds such as using environment variables or manually copying files
- ❌ MUST NOT only output the configuration content and ask the user to modify it themselves

## Prerequisites

- Python dependencies MUST be installed: `pip install requests pyyaml matplotlib numpy`
- Browser automation capability is required (Dashboard Skill Generation module ONLY)
- Dataset Q&A: user MUST have **Q&A permission** for the target dataset
- File Q&A: file formats limited to `xls`, `xlsx`, `csv`; single file size ≤ 10MB
- **Document Parsing**:
  - System dependency: `brew install tesseract tesseract-lang` (required for local parsing ONLY)
  - Supported formats: PDF, Word (.doc/.docx), Excel (.xls/.xlsx), CSV, images (.png/.jpg/.jpeg)
  - Single file size ≤ 10MB (remote OCR limit)
  - **Error handling**:
    - Local parsing failure → automatically falls back to remote OCR
    - Remote OCR still fails → classified as "parse failure", retaining original filename and error message
    - Unknown document type → extract 5+ generic fields, MUST obtain user confirmation before generating Excel
  - Detailed documentation: [module-document-parser.md](references/document/module-document-parser.md)

## Script Calling Convention (Required Reading)

When calling any Python script:
1. The script path MUST use the **absolute path of the installed skill package directory** (i.e. `<skill-package-dir>/scripts/...`); MUST NOT use relative paths
2. **MUST** pass the absolute path of `<workspace-dir>` via the `--workspace-dir` parameter (see the conventions in the **Configuration** section above for how to obtain it)
3. Wrap path parameter values in quotes (to prevent shell tokenization issues caused by Chinese characters, spaces, or other special characters)
4. `smartq_stream_query.py`, `file_stream_query.py`, `q_insights.py`, `create_chat.py`, `generate_report.py` MUST include the `--locale` parameter — see **User Locale Determination Rules** below

**Invocation examples**:
```bash
# File upload
python '<skill-package-dir>/scripts/chat/upload_file.py' '/path/to/data.xlsx' --workspace-dir '<workspace-dir>'

# File Q&A
python '<skill-package-dir>/scripts/chat/file_stream_query.py' <fileId> "各部门人数分布" --locale zh_CN --workspace-dir '<workspace-dir>'

# Dataset Q&A
python '<skill-package-dir>/scripts/chat/smartq_stream_query.py' "TOP 3 regions by sales" --locale zh_CN --workspace-dir '<workspace-dir>'

# Dataset Q&A (with dataset name hint — enables name lookup, exact match skips intelligent table selection)
python '<skill-package-dir>/scripts/chat/smartq_stream_query.py' "Based on 'Order Sales Details', what is the sales share by platform in Q1?" --cube-name 'Order Sales Details' --locale zh_CN --workspace-dir '<workspace-dir>'

# Document Parsing - local
python '<skill-package-dir>/scripts/document/document_local_parse.py' '/path/to/folder/' --json --workspace-dir '<workspace-dir>'

# Document Parsing - remote OCR
python '<skill-package-dir>/scripts/document/document_remote_ocr.py' '/path/to/folder/' --workspace-dir '<workspace-dir>'

# Excel generation
python '<skill-package-dir>/scripts/document/generate_excel.py' '<json-path>' --workspace-dir '<workspace-dir>'

# Data Insight
python '<skill-package-dir>/scripts/insight/q_insights.py' "这个报表有什么异常？" --excel-file '/path/to/data.xlsx' --locale zh_CN --workspace-dir '<workspace-dir>'

# Report generation
python '<skill-package-dir>/scripts/report/generate_report.py' "本月销售分析" --locale zh_CN --workspace-dir '<workspace-dir>'
```

### User Locale Determination Rules

> **Core principle**: `--locale` MUST be determined **SOLELY based on the user's input text**, NOT influenced by any other source.

Valid values: `zh_CN` or `en_US` only.

**Determination method**:
- Examine the **user's original input message** (the question or instruction the user typed)
- Identify the **question/instruction language** — the language of the sentence structure, verbs, and functional words (not embedded proper nouns)
- Chinese question language → `zh_CN`; English or other question language → `en_US`

**Mixed-language handling** (critical):
- When user input contains both Chinese and English, determine locale by the **question framing language**, NOT by embedded entity names (dataset names, field names, table names, etc.)
- Entity names (dataset names, field names, etc.) embedded in the question are **proper nouns / references** — they do NOT indicate the user's language preference
- Rule of thumb: strip out quoted names or recognizable entity references, then judge the language of the remaining sentence structure

**What counts as "user input text"**:
- ✅ The text the user typed in the current conversation turn
- ✅ The user's original question when performing follow-up queries in the same session

**What MUST NOT influence locale determination**:
- ❌ The Agent's own reply language (Agent may reply in a language different from the user's input)
- ❌ API response content or error messages (these are always in a fixed language regardless of the user's language)
- ❌ Script console output text
- ❌ Dataset names, field names, or other metadata — whether returned by the platform OR embedded in the user's question as references
- ❌ System prompt language or Agent configuration language

**Example**:
- User input: "帮我分析销售数据" → `--locale zh_CN` (question language is Chinese)
- User input: "Analyze sales data" → `--locale en_US` (question language is English)
- User input: "Analyze the 销售数据集" → `--locale en_US` (question language is English; "销售数据集" is a dataset name reference, not the question language)
- User input: "Show me data from 2024年度报表" → `--locale en_US` (question language is English; "2024年度报表" is a dataset name)
- User input: "帮我查一下 Sales Dataset 的数据" → `--locale zh_CN` (question language is Chinese; "Sales Dataset" is a dataset name)
- User input: "帮我分析销售数据", but API returns English error message → `--locale zh_CN` (locale is determined by user input, NOT by API response)
- Previous Agent reply was in English, user then types "查询TOP3" → `--locale zh_CN` (locale is determined by user input, NOT by Agent's previous reply)

**Prohibited actions**:
- ❌ MUST NOT omit the `--workspace-dir` parameter when calling scripts
- ❌ MUST NOT use relative paths to call scripts (e.g. `python3 scripts/chat/...`)
- ❌ MUST NOT use hard-coded paths or guessed paths
- ❌ MUST NOT omit the `--locale` parameter when calling scripts that require it
- ❌ MUST NOT determine `--locale` based on Agent's own output language or API/script return content
