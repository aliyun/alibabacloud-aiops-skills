#!/usr/bin/env node

/**
 * IQS Weather Query - 基于阿里云IQS的7天天气预报查询
 *
 * 流程：
 *   1. 调用 UnifiedSearch 搜索天气网页 URL（优先 weather.cma.cn）
 *   2. 调用 ReadPageBasic 读取天气网页正文
 *   3. 已知站点 → 预设解析器 → 结构化 JSON（parseMode: structured）
 *      未知站点 → 返回正文原文 + hint → 交由 agent(LLM) 理解（parseMode: raw）
 *
 * 用法：
 *   node weather.mjs <城市名称>
 */

const SEARCH_ENDPOINT = 'https://cloud-iqs.aliyuncs.com/search/unified';
const READPAGE_ENDPOINT = 'https://cloud-iqs.aliyuncs.com/readpage/scrape';

// 优先搜索的天气网站（按优先级排序）
const PREFERRED_WEATHER_SITES = [
  'weather.cma.cn',        // 中央气象台（优先）
  'weather.com.cn',        // 中国天气网（备选，匹配所有子域名）
];

/**
 * 从环境变量或配置文件加载 API Key
 * @returns {Promise<string|null>}
 */
async function loadApiKey() {
  if (process.env.ALIYUN_IQS_API_KEY) {
    return process.env.ALIYUN_IQS_API_KEY;
  }

  try {
    const fs = await import('fs');
    const path = await import('path');
    const os = await import('os');
    const configPath = path.join(os.homedir(), '.alibabacloud', 'iqs', 'env');
    if (fs.existsSync(configPath)) {
      const content = fs.readFileSync(configPath, 'utf-8');
      const match = content.match(/ALIYUN_IQS_API_KEY=(.+)/);
      if (match) {
        return match[1].trim();
      }
    }
  } catch {
    // 配置文件不存在或不可读
  }

  return null;
}

/**
 * 调用 UnifiedSearch 搜索天气信息
 * @param {string} apiKey - API Key
 * @param {string} city - 城市名称
 * @returns {Promise<Object>} 搜索结果
 */
async function searchWeather(apiKey, city) {
  const body = {
    query: `${city} 天气预报 未来7天`,
    engineType: 'Generic',
    timeRange: 'NoLimit',
    contents: {
      mainText: true,
      summary: false
    }
  };

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(SEARCH_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
        'User-Agent': 'AlibabaCloud-Agent-Skills'
      },
      body: JSON.stringify(body),
      signal: controller.signal
    });

    clearTimeout(timeoutId);
    const data = await response.json();

    if (data.errorCode) {
      throw new Error(`${data.errorCode}: ${data.errorMessage}`);
    }

    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('搜索请求超时 (15s)');
    }
    throw error;
  }
}

/**
 * 从搜索结果中筛选最优天气网页 URL
 * @param {Object} searchResult - 搜索结果
 * @returns {string|null} 最优天气网页 URL
 */
function findBestWeatherUrl(searchResult) {
  const pageItems = searchResult?.pageItems || [];

  if (pageItems.length === 0) {
    return null;
  }

  // 优先查找中央气象台等权威天气网站
  for (const site of PREFERRED_WEATHER_SITES) {
    const match = pageItems.find(item =>
      item.link && item.link.includes(site)
    );
    if (match) {
      return match.link;
    }
  }

  // 查找包含"天气"关键词的结果
  const weatherResult = pageItems.find(item =>
    item.title && (item.title.includes('天气') || item.title.includes('weather'))
  );
  if (weatherResult) {
    return weatherResult.link;
  }

  // 返回第一个结果
  return pageItems[0]?.link || null;
}

/**
 * 判断 URL 是否匹配某个已知站点解析器
 */
function isKnownSite(url) {
  return PARSER_REGISTRY.some(({ pattern }) => url.includes(pattern));
}

/**
 * 调用 ReadPage 读取网页内容
 * @param {string} apiKey - API Key
 * @param {string} url - 网页 URL
 * @returns {Promise<Object>} 网页解析结果
 */
async function readPage(apiKey, url) {
  // 已知站点用 normal 保留更多结构，未知站点用 article 精简正文
  const mode = isKnownSite(url) ? 'normal' : 'article';

  const body = {
    url: url,
    formats: ['text'],
    timeout: 60000,
    pageTimeout: 15000,
    stealthMode: 0,
    readability: {
      readabilityMode: mode
    }
  };

  const response = await fetch(READPAGE_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,
      'User-Agent': 'AlibabaCloud-Agent-Skills'
    },
    body: JSON.stringify(body)
  });

  const data = await response.json();

  if (data.errorCode) {
    throw new Error(`${data.errorCode}: ${data.errorMessage}`);
  }

  return {
    title: data.data?.metadata?.title,
    url: data.data?.metadata?.url,
    text: data.data?.text,
    statusCode: data.data?.statusCode
  };
}

// ============================================================
// 解析器注册表：URL 模式 → 解析函数
// 新增站点只需：1.写解析函数  2.在此注册
// ============================================================
const PARSER_REGISTRY = [
  { pattern: 'weather.cma.cn', parser: parseCmaWeather },
  { pattern: 'baidu.weather.com.cn', parser: parseBaiduWeatherComCn },
  { pattern: 'sq.weather.com.cn', parser: parseBaiduWeatherComCn },
  { pattern: 'weather.com.cn', parser: parseWeatherComCn },
];

/**
 * 解析器路由：根据 URL 匹配对应解析函数
 * - 已知站点：使用预设解析器，返回结构化 JSON
 * - 未知站点 / 解析失败：返回 rawText + hint，交由 agent(LLM) 直接理解
 */
function parseWeatherData(content, city, url) {
  if (!content) {
    return { city, forecast: [], parseMode: 'empty' };
  }

  // 尝试匹配已知站点解析器
  for (const { pattern, parser } of PARSER_REGISTRY) {
    if (url && url.includes(pattern)) {
      const result = parser(content, city);
      if (result.forecast.length >= 3) {
        result.parseMode = 'structured';
        return result;
      }
    }
  }

  // 未知站点或解析失败 → 返回正文原文，交由 agent 理解
  // 同时输出 evolveHint，引导 agent 为该站点编写新解析器
  const urlPattern = url ? new URL(url).hostname : 'unknown';
  return {
    city,
    queryTime: new Date().toISOString(),
    parseMode: 'raw',
    hint: `以下是${city}天气网页的正文内容，请从中提取未来7天的天气预报信息，包括：日期、天气状况、温度范围、风向、风力等级。如果信息不完整，请尽量提取可用部分。`,
    rawText: content.substring(0, 4000),
    evolveHint: `[持续进化] 当前站点 "${urlPattern}" 没有匹配的解析器，走了 raw 模式。请在回答用户后，分析 rawText 的格式规律，为该站点编写一个新的解析器函数并注册到 scripts/weather.mjs 的 PARSER_REGISTRY 中。参考现有解析器 parseCmaWeather / parseWeatherComCn 的实现方式。解析器函数签名: function parseXxx(content, city) → { city, queryTime, forecastDays, forecast: [{date, weather, temperature, windDirection, windSpeed}] }`,
  };
}

// ============================================================
// 解析器1: 中央气象台 weather.cma.cn
// 格式: 每天10行 — 星期、日期、白天天气、白天风向、白天风力、
//       最高温、最低温、夜间天气、夜间风向、夜间风力
// ============================================================
function parseCmaWeather(content, city) {
  const forecast = [];

  try {
    const lines = content.split('\n').map(l => l.trim()).filter(l => l);

    let startIdx = lines.findIndex(l => l.includes('7天天气预报'));
    if (startIdx === -1) {
      return { city, forecast: [] };
    }
    startIdx += 1;

    const dayBlocks = [];
    for (let i = startIdx; i < lines.length; i++) {
      if (/^星期[一二三四五六日]/.test(lines[i])) {
        const block = [];
        for (let j = i; j < Math.min(i + 12, lines.length); j++) {
          if (j > i && (/^星期[一二三四五六日]/.test(lines[j]) || lines[j].startsWith('时间'))) break;
          block.push(lines[j]);
        }
        dayBlocks.push(block);
      }
      if (lines[i].startsWith('时间') && lines[i].includes('|')) break;
    }

    for (const block of dayBlocks) {
      if (block.length < 6) continue;

      const weekday = block[0].trim();
      const date = block[1]?.trim() || '';
      const dayWeather = block[2]?.trim() || '';
      const dayWindDir = block[3]?.trim() || '';
      const dayWindSpeed = block[4]?.trim() || '';
      const highTemp = block[5]?.replace(/[^\d.-]/g, '') || '';
      const lowTemp = block[6]?.replace(/[^\d.-]/g, '') || '';
      const nightWeather = block.length > 7 ? block[7]?.trim() : '';

      let weather = dayWeather;
      if (nightWeather && nightWeather !== dayWeather && !/风/.test(nightWeather)) {
        weather = `${dayWeather}转${nightWeather}`;
      }

      let temperature = '';
      if (highTemp && lowTemp) {
        temperature = `${lowTemp}°C ~ ${highTemp}°C`;
      } else if (highTemp) {
        temperature = `${highTemp}°C`;
      }

      forecast.push({
        date: `${date} ${weekday}`,
        weather,
        temperature,
        windDirection: dayWindDir,
        windSpeed: dayWindSpeed,
      });
    }
  } catch (e) {
    // 解析失败返回空
  }

  return {
    city,
    queryTime: new Date().toISOString(),
    forecastDays: Math.min(forecast.length, 7),
    forecast: forecast.slice(0, 7),
    raw: forecast.length === 0 ? content.substring(0, 2000) : undefined,
  };
}

// ============================================================
// 解析器2: 中国天气网 weather.com.cn (所有子域名)
// 支持两种格式:
//   A) 15天预报页: 列表标记 "* 日期\n周X" + Raphaël 图表温度
//   B) 7天预报页:  "# 7日（今天）\n多云\n22/15℃\n<3级"
// ============================================================
function parseWeatherComCn(content, city) {
  const forecast = [];

  try {
    const lines = content.split('\n').map(l => l.trim().replace(/^\*\s*/, '').trim());

    // ---- 格式B: www 桌面版 7天预报 ----
    // 特征: "# 7日（今天）" / "# 8日（明天）" / "# 9日（后天）" / "# 10日（周五）"
    const format7day = [];
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(/^#\s*(\d{1,2})日（(.+?)）$/);
      if (m) {
        const date = `${m[1]}日`;
        const label = m[2]; // 今天/明天/后天/周X
        const weather = (i + 1 < lines.length) ? lines[i + 1] : '';
        const tempLine = (i + 2 < lines.length) ? lines[i + 2] : '';
        const windLine = (i + 3 < lines.length) ? lines[i + 3] : '';

        const tempMatch = tempLine.match(/(-?\d+)\s*\/\s*(-?\d+)℃/);
        let temperature = '';
        if (tempMatch) {
          temperature = `${tempMatch[2]}°C ~ ${tempMatch[1]}°C`;
        }

        format7day.push({
          date: `${date} ${label}`,
          weather,
          temperature,
          windSpeed: windLine.includes('级') ? windLine : '',
          windDirection: ''
        });
      }
    }

    if (format7day.length >= 3) {
      forecast.push(...format7day.slice(0, 7));
    } else {
      // ---- 格式A: 15天预报页 ----
      const dates = [];
      const weekdays = [];
      for (let i = 0; i < lines.length; i++) {
        const dateMatch = lines[i].match(/^(\d{1,2}日)$/);
        if (dateMatch) {
          dates.push(dateMatch[1]);
          if (i + 1 < lines.length && /^周[一二三四五六日]$/.test(lines[i + 1])) {
            weekdays.push(lines[i + 1]);
          } else {
            weekdays.push('');
          }
        }
      }

      const weatherWords = '晴|多云|阴|小雨|中雨|大雨|暴雨|雷阵雨|小雪|中雪|大雪|雨夹雪|雾|霾|阵雨|雷雨|雨|雪';
      const weatherPattern = new RegExp(`^(${weatherWords})(转(${weatherWords}))?$`);

      const weathers = [];
      const winds = [];
      for (let i = 0; i < lines.length; i++) {
        if (weatherPattern.test(lines[i])) {
          weathers.push(lines[i]);
          if (i + 1 < lines.length && lines[i + 1].includes('级')) {
            winds.push(lines[i + 1]);
          } else {
            winds.push('');
          }
        }
      }

      const tempLines = content.match(/Created with Raphaël[\s\S]*?(\d+°C[\d°C]*)/g) || [];
      let highTemps = [];
      let lowTemps = [];

      for (let idx = 0; idx < tempLines.length; idx++) {
        const cleaned = tempLines[idx].replace(/Created with Raphaël\s*[\d.]+/, '');
        const temps = cleaned.match(/(\d+)°C/g)?.map(t => parseInt(t.replace('°C', ''))) || [];
        if (idx === 0) highTemps = temps;
        else if (idx === 1) lowTemps = temps;
      }

      const count = Math.min(dates.length, 7);
      if (count > 0 && (weathers.length > 0 || highTemps.length > 0)) {
        for (let i = 0; i < count; i++) {
          const high = highTemps[i] !== undefined ? highTemps[i] : '';
          const low = lowTemps[i] !== undefined ? lowTemps[i] : '';
          let temperature = '';
          if (high !== '' && low !== '') {
            temperature = `${low}°C ~ ${high}°C`;
          } else if (high !== '') {
            temperature = `${high}°C`;
          }

          forecast.push({
            date: dates[i] + (weekdays[i] ? ` ${weekdays[i]}` : ''),
            weather: weathers[i] || '',
            temperature,
            windSpeed: winds[i] || '',
            windDirection: ''
          });
        }
      }
    }
  } catch (e) {
    // 解析失败返回空
  }

  return {
    city,
    queryTime: new Date().toISOString(),
    forecastDays: Math.min(forecast.length, 7),
    forecast: forecast.slice(0, 7),
    raw: forecast.length === 0 ? content.substring(0, 2000) : undefined,
  };
}

// ============================================================
// 解析器3: 中国天气网移动版 (baidu.weather.com.cn / sq.weather.com.cn)
// 格式: "* 今天/周X\n04/07\n多云转阴\n21/10℃\n[空气质量]\n风向风力 | 日出..."
// 每天以 "* " 列表标记开头，后跟周几/今天
// ============================================================
function parseBaiduWeatherComCn(content, city) {
  const forecast = [];

  try {
    // 按 "  * " 列表标记分割天数块
    const dayBlocks = content.split(/\n\s*\*\s+/).filter(b => b.trim());

    for (const block of dayBlocks) {
      const lines = block.split('\n').map(l => l.trim()).filter(l => l);
      if (lines.length < 4) continue;

      // 第1行: 今天 / 周X
      const dayLabel = lines[0];
      if (!/^(今天|周[一二三四五六日])$/.test(dayLabel)) continue;

      // 第2行: 日期 MM/DD
      const dateMatch = lines[1].match(/^(\d{2})\/(\d{2})$/);
      if (!dateMatch) continue;
      const dateStr = `${dateMatch[1]}/${dateMatch[2]}`;

      // 第3行: 天气
      const weather = lines[2];

      // 第4行: 温度 高/低℃
      const tempMatch = lines[3].match(/(-?\d+)\s*\/\s*(-?\d+)℃/);
      if (!tempMatch) continue;
      const temperature = `${tempMatch[2]}°C ~ ${tempMatch[1]}°C`;

      // 剩余行中找风力: "东南风3-4级 东南风4-5级 | 日出..."
      let windDirection = '';
      let windSpeed = '';
      for (let i = 4; i < Math.min(lines.length, 8); i++) {
        const windMatch = lines[i].match(/^(东南风|东北风|西南风|西北风|东风|南风|西风|北风|无)([\d<>-]+级)?\s+(东南风|东北风|西南风|西北风|东风|南风|西风|北风|无)([\d<>-]+级)?/);
        if (windMatch) {
          windDirection = windMatch[1];
          windSpeed = windMatch[2] || '';
          break;
        }
      }

      forecast.push({
        date: `${dateStr} ${dayLabel}`,
        weather,
        temperature,
        windDirection,
        windSpeed,
      });
    }
  } catch (e) {
    // 解析失败返回空
  }

  return {
    city,
    queryTime: new Date().toISOString(),
    forecastDays: Math.min(forecast.length, 7),
    forecast: forecast.slice(0, 7),
    raw: forecast.length === 0 ? content.substring(0, 2000) : undefined,
  };
}

/**
 * 打印使用帮助
 */
function printUsage() {
  console.log(`
IQS Weather Query - 7天天气预报查询

用法:
  node weather.mjs <城市名称>

示例:
  node weather.mjs 北京
  node weather.mjs 上海
  node weather.mjs 杭州

环境变量:
  ALIYUN_IQS_API_KEY - 阿里云 IQS API Key

获取 API Key: https://help.aliyun.com/zh/document_detail/3025781.html
`);
}

/**
 * 主函数
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.includes('-h') || args.includes('--help') || args.length === 0) {
    printUsage();
    process.exit(0);
  }

  const city = args.join(' ');

  // 加载 API Key
  const apiKey = await loadApiKey();
  if (!apiKey) {
    console.error(JSON.stringify({
      error: 'ALIYUN_IQS_API_KEY 未配置。请设置环境变量或参考 https://help.aliyun.com/zh/document_detail/3025781.html'
    }, null, 2));
    process.exit(1);
  }

  console.error(`正在查询 ${city} 未来7天天气预报...`);

  try {
    // Step 1: 搜索天气信息，筛选最优 URL
    console.error('Step 1/3: 搜索天气信息...');
    const searchResult = await searchWeather(apiKey, city);

    const weatherUrl = findBestWeatherUrl(searchResult);
    if (!weatherUrl) {
      console.error(JSON.stringify({
        error: `未找到 ${city} 的天气信息`
      }, null, 2));
      process.exit(1);
    }

    // Step 2: 读取天气网页内容
    console.error(`Step 2/3: 读取天气网页 ${weatherUrl}`);
    const pageResult = await readPage(apiKey, weatherUrl);
    const content = pageResult.text || '';

    // Step 3: 解析天气数据
    console.error('Step 3/3: 解析天气数据...');
    const weatherData = parseWeatherData(content, city, weatherUrl);
    weatherData.source = weatherUrl;

    // 输出结果到 stdout
    console.log(JSON.stringify({
      success: true,
      data: weatherData,
    }, null, 2));

  } catch (error) {
    console.error(JSON.stringify({
      error: error.message
    }, null, 2));
    process.exit(1);
  }
}

main();
