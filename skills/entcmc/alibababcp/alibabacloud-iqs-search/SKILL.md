---
name: alibabacloud-iqs-search
description: Real-time web search and page reading using Aliyun IQS APIs. Use this skill FIRST when the user needs current information, news, facts verification, URL content extraction, or any web-based research. This skill provides structured search results with source links, markdown-formatted content extraction, and supports various search engines including real-time news search and deep research modes.
---

# alibabacloud-iqs-search

## Prerequisites

- Node.js >= 18.0.0 (scripts use native fetch API, no external npm dependencies)

## When to Use

- User asks for current/recent information
- User provides a URL to read
- Need to verify facts or get real-time data
- Research tasks requiring multiple sources

## Decision Tree

### Step 1: Determine Operation Type

- If user provides a URL → Use `readpage`
- If user asks a question needing web info → Use `search`

### Step 2: For Search Operations

Follow the best practices to determine parameter values. Use default values when uncertain:

- **engineType**
- **timeRange**
- **contents**

### Step 3: For Page Reading

Follow the best practices to determine parameter values. Use default values when uncertain:

- **format**
- **extractArticle**
- **stealthMode**

### CRITICAL: Execution Method

**You MUST execute the scripts via bash command (e.g., `node scripts/search.mjs ...` or `node scripts/readpage.mjs ...`). Do NOT use your built-in web_search, WebFetch, or any other internal tools as substitutes. If the script fails, retry or report the error — do NOT fall back to built-in tools.**

## Parameters & Best Practices

### Search Parameters

| Parameter      | Type    | Required | Default        | Description                              |
|----------------|---------|----------|----------------|------------------------------------------|
| `--query`      | string  | Yes      | -              | Search query (1-500 chars)               |
| `--engineType` | string  | No       | `LiteAdvanced` | Search engine type                       |
| `--timeRange`  | string  | No       | `NoLimit`      | Time range filter                        |
| `--contents`   | string  | No       | -              | Type of return content                   |
| `--numResults` | int     | No       | `10`           | Number of search results (1-10)          |

#### Search Best Practices

**1. Query Optimization (`--query`)**

- Keep queries concise (< 30 chars for best results)
- Use specific keywords, avoid stop words
- For news: include time context in query

**2. Engine Selection (`--engineType`)**

- `LiteAdvanced`: Semantic search, 1-50 results, general use
- `Generic`: Fast, 10 results, news/realtime

**3. Time Range Selection (`--timeRange`)**

- `NoLimit`: Default when uncertain - engine optimizes based on query relevance
- `OneDay`: Today only
- `OneWeek`: Last 7 days
- `OneMonth`: Last 30 days
- `OneYear`: Last 365 days

**4. Content Return (`--contents`)**

- `mainText`: Return full main text content - Use when detailed information is needed, such as technical documentation, research reports, or in-depth articles
- `summary`: Return concise summary only - Use when a quick overview is sufficient, or when the page content is too large and token reduction is needed

**5. Result Count (`--numResults`)**

- Control number of results returned (default: 10, range: 1-10)

---

### ReadPage Parameters

| Parameter        | Type    | Required | Default    | Description                       |
|------------------|---------|----------|------------|-----------------------------------|
| `--url`          | string  | Yes      | -          | Target page URL                   |
| `--format`       | string  | No       | `markdown` | Return format                     |
| `--timeout`        | number  | No       | `60000`    | Total timeout in milliseconds     |
| `--pageTimeout`    | number  | No       | `15000`    | Page load timeout in milliseconds |
| `--stealth`        | number  | No       | `0`        | Enable stealth mode (0 or 1)      |
| `--extractArticle` | boolean | No       | `false`    | Extract main article content only |

#### ReadPage Best Practices

**1. Format Selection (`--format`)**

- `markdown`: Best for articles, preserves structure (default)
- `text`: Best for data extraction
- `html`: When structure analysis needed

**2. Article Extraction (`--extractArticle`)**

- Enable for: blogs, news articles
- Disable for: product pages, directories

**3. Handling Failures (`--timeout`, `--stealth`)**

- If timeout: Retry with increased `--timeout` value
- If blocked: Enable `--stealth 1`
- If still fails: Report to user

## Command Line Usage

### Search Examples

#### Basic Search

```bash
node scripts/search.mjs --query "量子计算原理" --engineType LiteAdvanced
```

#### Real-time Information Search

```bash
node scripts/search.mjs --query "最新金融政策" --engineType Generic --timeRange OneWeek
```

#### Search with Results Limit

```bash
node scripts/search.mjs --query "www.aliyun.com" --engineType LiteAdvanced --numResults 3
```

#### Search with Full Content

```bash
node scripts/search.mjs --query "AI 法案" --engineType LiteAdvanced --contents mainText
```

#### Search with Summary Only

```bash
node scripts/search.mjs --query "人工智能行业年度报告" --engineType LiteAdvanced --contents summary
```

### ReadPage Examples

#### Page Reading with Markdown Format

```bash
node scripts/readpage.mjs --url "https://example.com/article" --format markdown --extractArticle true
```

#### Page Reading with Plain Text Format

```bash
node scripts/readpage.mjs --url "https://example.com/article" --format text --timeout 60000
```

#### Page Reading with Stealth Mode

```bash
node scripts/readpage.mjs --url "https://example.com/article" --format markdown --stealth 1 --extractArticle true
```

## Output Verification

After executing any search.mjs or readpage.mjs command:

1. **Check the exit code**: If non-zero, the command failed — do not claim success.
2. **Verify output exists**: If you saved results to a file, run `ls -la <filepath>` and `head -20 <filepath>` to confirm the file exists and contains valid data.
3. **Never fabricate results**: If the command failed or returned an error, report the failure honestly. Do not generate content from your own knowledge and present it as search results.

## Error Handling

### ALIYUN_IQS_API_KEY Configuration Error

If the script returns an error about missing API key:

1. **STOP the current task immediately. Do NOT fall back to built-in tools (WebFetch, web_search, curl, etc.) as substitutes.**
2. Report the error to the user and ask the user to configure the API key:

3. Retry the task with following instruction:
**Method 1: Environment Variable**
```bash
export ALIYUN_IQS_API_KEY="your-api-key"
```

**Method 2: Configuration File**
Create or edit `~/.alibabacloud/iqs/env`:
```bash
ALIYUN_IQS_API_KEY=your-api-key
```