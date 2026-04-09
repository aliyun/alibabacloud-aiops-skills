---
name: alibabacloud-iqs-weather-query
description: |
  7-day weather forecast query powered by Alibaba Cloud IQS web search and page reading.
  Triggers: "weather forecast", "7-day weather", "weekly weather", "weather in [city]", "will it rain", "temperature forecast"
---

# IQS Weather Query - 7-Day Weather Forecast

Query 7-day weather forecasts for any city using Alibaba Cloud IQS web search (UnifiedSearch) and page reading (ReadPageBasic) capabilities.

**Underlying Service:** [alibabacloud-iqs-search](https://skills.aliyun.com/skills/alibabacloud-iqs-search)

**Hybrid Parsing Strategy:**
- **Known sites** (weather.cma.cn, weather.com.cn): Dedicated parsers extract structured JSON → `parseMode: "structured"`
- **Unknown sites**: ReadPage extracts main content (readabilityMode: article), returns raw text with extraction hint → `parseMode: "raw"`, agent (LLM) interprets directly

| Output Field | Description |
|--------------|-------------|
| parseMode | `"structured"` (parsed JSON) or `"raw"` (text for agent) |
| weather | Weather condition (sunny, cloudy, rain, etc.) |
| temperature | Temperature range |
| windSpeed | Wind speed/level |
| windDirection | Wind direction |

---

## Environment Configuration

> **Pre-check: ALIYUN_IQS_API_KEY Required**
>
> ```bash
> echo $ALIYUN_IQS_API_KEY | head -c 4
> ```
> If output is empty, the API Key is not configured.
>
> **How to obtain ALIYUN_IQS_API_KEY:** Please refer to [Aliyun IQS Documentation](https://help.aliyun.com/zh/document_detail/3025781.html)
>
> **Configure environment variable (choose one):**
>
> **Option 1: Temporary (current terminal session only)**
> ```bash
> export ALIYUN_IQS_API_KEY="your-api-key-here"
> ```
>
> **Option 2: Permanent (recommended)**
>
> Add to ~/.zshrc or ~/.bashrc:
> ```bash
> export ALIYUN_IQS_API_KEY="your-api-key-here"
> ```
> Run `source ~/.zshrc` or `source ~/.bashrc` to apply.
>
> **Alternative:** Place API Key in `~/.alibabacloud/iqs/env` file:
> ```
> ALIYUN_IQS_API_KEY=your-api-key-here
> ```

---

## Workflow

```
User Input (city name)
        │
        ▼
┌─────────────────────────┐
│ Step 1: UnifiedSearch    │  Search: "{city} 天气预报 未来7天"
│ (Web Search)            │  Priority: weather.cma.cn > weather.com.cn
└──────────┬──────────────┘
           │ Best weather URL
           ▼
┌─────────────────────────┐
│ Step 2: ReadPageBasic    │  Known site → readabilityMode: normal
│ (Page Reading)          │  Unknown site → readabilityMode: article
└──────────┬──────────────┘
           │ Page content
           ▼
     Known site?
      ╱        ╲
    YES          NO
     │            │
     ▼            ▼
  Parser       Return rawText
  Router       + hint for agent
     │         (parseMode: raw)
     ▼
  Structured JSON
  (parseMode: structured)
```

---

## Usage

### Prerequisites

- Node.js >= 18 (native `fetch` support required)
- No additional npm dependencies needed

### Execute Query

```bash
node scripts/weather.mjs <city>
```

Examples:
```bash
node scripts/weather.mjs 北京
node scripts/weather.mjs 上海
node scripts/weather.mjs 杭州
node scripts/weather.mjs Tokyo
```

### Output Format

**Structured mode** (known sites — parsed successfully):
```json
{
  "success": true,
  "data": {
    "city": "北京",
    "parseMode": "structured",
    "queryTime": "2026-03-26T10:00:00.000Z",
    "forecastDays": 7,
    "forecast": [
      {
        "date": "3月26日",
        "weather": "晴",
        "temperature": "5°C ~ 18°C",
        "windDirection": "北风",
        "windSpeed": "3-4级"
      }
    ],
    "source": "https://weather.cma.cn/..."
  }
}
```

**Raw mode** (unknown sites — agent interprets the text):
```json
{
  "success": true,
  "data": {
    "city": "北京",
    "parseMode": "raw",
    "hint": "以下是北京天气网页的正文内容，请从中提取未来7天的天气预报信息...",
    "rawText": "北京天气预报\n今天 晴 18°C/5°C ...",
    "evolveHint": "[持续进化] 当前站点 \"example.com\" 没有匹配的解析器...",
    "source": "https://example.com/weather/beijing"
  }
}
```

---

## IQS APIs Used

| API | Endpoint | Purpose | Documentation |
|-----|----------|---------|---------------|
| UnifiedSearch | `cloud-iqs.aliyuncs.com/search/unified` | Web search for weather pages | [Doc](https://help.aliyun.com/zh/document_detail/2883041.html) |
| ReadPageScrape | `cloud-iqs.aliyuncs.com/readpage/scrape` | Read and parse weather webpage | [Doc](https://help.aliyun.com/zh/document_detail/2983380.html) |

**Search Priority Sites (with dedicated parsers):**
1. weather.cma.cn (China Meteorological Administration) — `parseCmaWeather` → readabilityMode: `normal`
2. baidu.weather.com.cn / sq.weather.com.cn (China Weather Network mobile) — `parseBaiduWeatherComCn` → readabilityMode: `normal`
3. weather.com.cn (China Weather Network, all other subdomains) — `parseWeatherComCn` → readabilityMode: `normal`
4. Other sites — no parser, return raw text → readabilityMode: `article` (cleaner body extraction)

---

## Error Handling

| Error Code | Description | Solution |
|------------|-------------|----------|
| CREDENTIALS_MISSING | API Key not configured | Set ALIYUN_IQS_API_KEY environment variable |
| NO_RESULTS | No weather results found | Check city name is correct |
| QUERY_FAILED | API call failed | Check network, verify credentials |
| PARSE_FAILED | Failed to parse weather data from webpage | The target site's page structure may have changed; update the corresponding parser or add a new one (see Extending section) |

---

## Best Practices

1. **Use Chinese city names** for domestic weather queries for better accuracy
2. **Node.js >= 18 required** - native `fetch` API is used, no npm install needed
3. **Cache awareness** - ReadPage uses `maxAge` not set, always fetches latest data
4. **Extensible parsers** - Each weather site has its own parser; add new sites by registering in `PARSER_REGISTRY`

---

## Continuous Evolution

This skill is designed to **self-improve over time**. When the script encounters an unknown site format (no matching parser), it returns `parseMode: "raw"` with an `evolveHint` field.

**Agent behavior when `parseMode` is `"raw"`:**

1. **First: Answer the user** — Extract weather info from `rawText` using LLM understanding and respond to the user immediately.
2. **Then: Evolve** — Read the `evolveHint` and analyze the `rawText` format pattern, then write a new parser function and register it in `PARSER_REGISTRY` (see Extending section below). This ensures that next time the same site format is hit, it goes through `structured` mode directly.

```
First query for unknown site:
  search → readpage → no parser match → raw mode → agent answers user
                                                  → agent writes new parser ← evolveHint

Subsequent queries for same site:
  search → readpage → parser match → structured mode → direct JSON output
```

> **Key:** The skill gets smarter with every new city searched. Each raw-mode encounter is an opportunity to add a new parser, progressively covering more site formats.

---

## Extending: Add a New Weather Site Parser

The script uses a **Parser Registry** pattern. Each weather site has its own dedicated parser function, and the router automatically dispatches based on URL. To add support for a new site, follow these 3 steps:

### Step 1: Write a Parser Function

Add a new parser function in `scripts/weather.mjs`. It must accept `(content, city)` and return the standard format:

```javascript
function parseMyNewSite(content, city) {
  const forecast = [];

  // Parse the text content from ReadPage for this specific site
  // Extract: date, weather, temperature, windDirection, windSpeed
  // ...your parsing logic here...

  return {
    city,
    queryTime: new Date().toISOString(),
    forecastDays: Math.min(forecast.length, 7),
    forecast: forecast.slice(0, 7),
    raw: forecast.length === 0 ? content.substring(0, 2000) : undefined,
  };
}
```

**Return format for each forecast item:**

| Field | Type | Example |
|-------|------|---------|
| date | string | `"04/07 星期二"` |
| weather | string | `"晴转多云"` |
| temperature | string | `"5°C ~ 18°C"` |
| windDirection | string | `"北风"` |
| windSpeed | string | `"3-4级"` |

### Step 2: Register in `PARSER_REGISTRY`

Add your parser to the registry array at the top of `weather.mjs`. **Order matters** — higher position = higher priority:

```javascript
const PARSER_REGISTRY = [
  { pattern: 'weather.cma.cn',          parser: parseCmaWeather },
  { pattern: 'baidu.weather.com.cn',    parser: parseBaiduWeatherComCn },
  { pattern: 'sq.weather.com.cn',       parser: parseBaiduWeatherComCn },
  { pattern: 'weather.com.cn',          parser: parseWeatherComCn },
  { pattern: 'mynewsite.com',           parser: parseMyNewSite },    // ← Add here
];
```

### Step 3: Add to Search Priority (optional)

If you want the new site to be prioritized in search results, add it to `PREFERRED_WEATHER_SITES`:

```javascript
const PREFERRED_WEATHER_SITES = [
  'weather.cma.cn',
  'weather.com.cn',
  'mynewsite.com',           // ← Add here
];
```

### How the Router Works

```
parseWeatherData(content, city, url)
  │
  ├─ URL contains "weather.cma.cn"?          → parseCmaWeather(content, city)
  ├─ URL contains "baidu.weather.com.cn"?    → parseBaiduWeatherComCn(content, city)
  ├─ URL contains "sq.weather.com.cn"?       → parseBaiduWeatherComCn(content, city)
  ├─ URL contains "weather.com.cn"?          → parseWeatherComCn(content, city)
  ├─ URL contains "mynewsite.com"?           → parseMyNewSite(content, city)
  │
  └─ No match or result < 3 days?           → return rawText + hint (agent interprets)
```

> **Tip:** Use `node -e "..."` with the ReadPage API to fetch and inspect the raw text format of a new site before writing the parser. See existing parsers (`parseCmaWeather`, `parseWeatherComCn`) as reference implementations.
