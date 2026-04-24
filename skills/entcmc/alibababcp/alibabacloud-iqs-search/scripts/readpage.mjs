#!/usr/bin/env node
/**
 * IQS ReadPage Script
 * Usage: node readpage.mjs --url "https://example.com" [options]
 */

const API_ENDPOINT = 'https://cloud-iqs.aliyuncs.com/readpage/scrape';

/**
 * Parse command line arguments
 * @param {string[]} args - Process arguments
 * @returns {Object} Parsed options
 */
function parseArgs(args) {
  const options = {};
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const nextArg = args[i + 1];
      if (nextArg && !nextArg.startsWith('--')) {
        // Handle boolean values
        if (nextArg === 'true') {
          options[key] = true;
        } else if (nextArg === 'false') {
          options[key] = false;
        } else {
          options[key] = nextArg;
        }
        i++;
      } else {
        options[key] = true;
      }
    }
  }
  return options;
}

/**
 * Load API key from environment or config file
 * @returns {string|null} API key
 */
async function loadApiKey() {
  // First check environment variable
  if (process.env.ALIYUN_IQS_API_KEY) {
    return process.env.ALIYUN_IQS_API_KEY;
  }

  // Try loading from config file
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
    // Config file not found or unreadable
  }

  return null;
}

/**
 * Read and extract content from a web page
 * @param {Object} options - Read options
 * @returns {Promise<Object>} Formatted page content
 */
async function readPage(options) {
  const apiKey = await loadApiKey();
  if (!apiKey) {
    throw new Error('ALIYUN_IQS_API_KEY environment variable not set');
  }

  if (!options.url) {
    throw new Error('URL is required. Use --url "https://example.com"');
  }

  // Validate URL format
  if (!options.url.startsWith('http://') && !options.url.startsWith('https://')) {
    throw new Error('URL must start with http:// or https://');
  }

  // Validate timeout range
  if (options.timeout !== undefined) {
    const timeout = parseInt(options.timeout, 10);
    if (isNaN(timeout) || timeout < 1000 || timeout > 180000) {
      throw new Error('timeout must be a number between 1000ms (1s) and 180000ms (180s)');
    }
  }

  // Validate pageTimeout range
  if (options.pageTimeout !== undefined) {
    const pageTimeout = parseInt(options.pageTimeout, 10);
    if (isNaN(pageTimeout) || pageTimeout < 1000 || pageTimeout > 120000) {
      throw new Error('pageTimeout must be a number between 1000ms (1s) and 120000ms (120s)');
    }
  }

  const format = options.format || 'markdown';
  const body = {
    url: options.url,
    formats: [format],
    timeout: parseInt(options.timeout, 10) || 60000,
    pageTimeout: parseInt(options.pageTimeout, 10) || 15000,
    stealthMode: options.stealth ? 1 : 0,
    readability: {
      readabilityMode: options.extractArticle ? 'article' : 'none'
    }
  };

  // Create an AbortController to handle timeouts
  const controller = new AbortController();
  const timeoutDuration = Math.max(parseInt(options.timeout, 10) || 60000, 5000); // Minimum 5 seconds timeout

  // Set up timeout
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutDuration);

  try {
    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
        'User-Agent': 'AlibabaCloud-Agent-Skills/alibabacloud-iqs-search',
        'x-iqs-source': 'skill.alibabacloud-iqs-readpage',
      },
      body: JSON.stringify(body),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    const data = await response.json();

    if (data.errorCode) {
      throw new Error(`${data.errorCode}: ${data.errorMessage}`);
    }

    return formatContent(data.data, format);
  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutDuration}ms`);
    }

    throw error;
  }

  const data = await response.json();

  if (data.errorCode) {
    throw new Error(`${data.errorCode}: ${data.errorMessage}`);
  }

  return formatContent(data.data, format);
}

/**
 * Format page content
 * @param {Object} data - Raw page data
 * @param {string} format - Output format
 * @returns {Object} Formatted content
 */
function formatContent(data, format) {
  if (!data) {
    return {
      title: null,
      url: null,
      content: null,
      statusCode: null
    };
  }

  return {
    title: data.metadata?.title,
    url: data.metadata?.url,
    content: data[format] || data.markdown || data.text,
    statusCode: data.statusCode
  };
}

// Parse CLI arguments and execute
const args = parseArgs(process.argv.slice(2));
readPage(args).then(result => {
  console.log(JSON.stringify(result, null, 2));
}).catch(err => {
  console.error(JSON.stringify({ error: err.message }, null, 2));
  process.exit(1);
});
