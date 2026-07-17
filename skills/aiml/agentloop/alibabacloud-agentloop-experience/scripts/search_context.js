#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");
const https = require("https");
const { createHash, createHmac, randomUUID } = require("crypto");

const CONFIG_KEYS = [
  "AGENTLOOP_ENABLE_RECALL",
  "AGENTLOOP_RECALL_ENDPOINT",
  "AGENTLOOP_CONFIRM_OUTBOUND",
];

const SECRET_KEYS = [
  "AGENTLOOP_ACCESS_KEY",
  "AGENTLOOP_ACCESS_SECRET",
  "AGENTLOOP_BEARER_API_KEY",
];

const ENV_KEYS = [...CONFIG_KEYS, ...SECRET_KEYS];

const USAGE = "usage: node scripts/search_context.js search --query <text> --context-type experience|memory --confirm-outbound [--limit 5] [--threshold 0.6] [--filter-json '{}']";
const MAX_QUERY_LENGTH = 2048;
const MAX_FILTER_JSON_LENGTH = 8192;

function requestId() {
  return typeof randomUUID === "function"
    ? randomUUID()
    : `alibabacloud-agentloop-experience-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function writeJson(payload) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function emptyResult(id, error = null) {
  return { request_id: id, error, results: [] };
}

function helpResult(id) {
  return { request_id: id, error: null, results: [], usage: USAGE };
}

function parseEnvFile(filePath, keys = ENV_KEYS) {
  const values = {};
  const allowedKeys = new Set(keys);
  if (!filePath || !fs.existsSync(filePath)) return values;
  const text = fs.readFileSync(filePath, "utf8");
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const withoutExport = line.startsWith("export ") ? line.slice("export ".length).trim() : line;
    const eq = withoutExport.indexOf("=");
    if (eq < 0) continue;
    const key = withoutExport.slice(0, eq).trim();
    if (!allowedKeys.has(key)) continue;
    let value = withoutExport.slice(eq + 1).trim();
    const quote = value[0];
    if ((quote === "'" || quote === '"') && value.endsWith(quote)) {
      value = value.slice(1, -1);
    } else {
      const comment = value.search(/\s#/);
      if (comment >= 0) value = value.slice(0, comment).trim();
    }
    values[key] = value;
  }
  return values;
}

function findProjectConfig(startDir) {
  let current = path.resolve(startDir);
  while (true) {
    const candidate = path.join(current, ".agentloop", "recall.env");
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

function loadConfig(keys = ENV_KEYS) {
  const homeConfig = path.join(os.homedir(), ".agentloop", "recall.env");
  const projectConfig = findProjectConfig(process.cwd());
  const envConfig = {};
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(process.env, key)) {
      envConfig[key] = process.env[key];
    }
  }
  return {
    ...parseEnvFile(homeConfig, keys),
    ...parseEnvFile(projectConfig, keys),
    ...envConfig,
  };
}

function parseArgs(argv) {
  const parsed = {
    command: argv[0],
    query: null,
    contextType: null,
    limit: 5,
    threshold: 0.6,
    filterJson: "{}",
    confirmOutbound: false,
  };
  if (argv[0] === "--help" || argv[0] === "-h") {
    parsed.help = true;
    return parsed;
  }
  for (let i = 1; i < argv.length; i += 1) {
    const arg = argv[i];
    const readValue = () => {
      if (i + 1 >= argv.length) throw new Error(`missing value for ${arg}`);
      i += 1;
      return argv[i];
    };
    switch (arg) {
      case "--query":
        parsed.query = readValue();
        break;
      case "--context-type":
        parsed.contextType = readValue();
        break;
      case "--limit":
        parsed.limit = Number(readValue());
        break;
      case "--threshold":
        parsed.threshold = Number(readValue());
        break;
      case "--filter-json":
        parsed.filterJson = readValue();
        break;
      case "--confirm-outbound":
        parsed.confirmOutbound = true;
        break;
      case "--help":
      case "-h":
        parsed.help = true;
        break;
      default:
        throw new Error(`unknown argument: ${arg}`);
    }
  }
  return parsed;
}

function validateInput(args) {
  if (args.help) return null;
  if (args.command !== "search") return "first argument must be: search";
  if (!args.query || !String(args.query).trim()) return "missing --query";
  if (String(args.query).length > MAX_QUERY_LENGTH) {
    return `--query must be ${MAX_QUERY_LENGTH} characters or fewer`;
  }
  if (!args.contextType || !["experience", "memory"].includes(args.contextType)) {
    return "missing or invalid --context-type";
  }
  if (!Number.isInteger(args.limit) || args.limit < 1) return "--limit must be a positive integer";
  if (!Number.isFinite(args.threshold) || args.threshold < 0 || args.threshold > 1) {
    return "--threshold must be a number between 0 and 1";
  }
  if (String(args.filterJson || "").length > MAX_FILTER_JSON_LENGTH) {
    return `--filter-json must be ${MAX_FILTER_JSON_LENGTH} characters or fewer`;
  }
  try {
    const parsed = JSON.parse(args.filterJson || "{}");
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      return "--filter-json must be a JSON object";
    }
    args.filter = parsed;
  } catch (err) {
    return `invalid --filter-json: ${err.message}`;
  }
  return null;
}

function enabled(value) {
  return String(value || "").trim().toLowerCase() === "true";
}

function isLocalHttpHost(hostname) {
  return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(hostname);
}

function validateEndpoint(endpoint) {
  let url;
  try {
    url = new URL(endpoint);
  } catch (err) {
    return `invalid AGENTLOOP_RECALL_ENDPOINT: ${err.message}`;
  }
  if (!["https:", "http:"].includes(url.protocol)) {
    return "AGENTLOOP_RECALL_ENDPOINT must use http or https";
  }
  if (url.protocol === "http:" && !isLocalHttpHost(url.hostname)) {
    return "AGENTLOOP_RECALL_ENDPOINT must use https for non-local endpoints";
  }
  return null;
}

function normalizeResult(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    return { title: "", summary: "", content: String(item ?? ""), metadata: {} };
  }
  const metadata = item.metadata && typeof item.metadata === "object" && !Array.isArray(item.metadata)
    ? { ...item.metadata }
    : {};
  if (item.contextId !== undefined && metadata.contextId === undefined) {
    metadata.contextId = item.contextId;
  }
  if (item.score !== undefined && metadata.score === undefined) {
    metadata.score = item.score;
  }
  if (item.id !== undefined && metadata.id === undefined) {
    metadata.id = item.id;
  }
  const content = String(item.content ?? item.context ?? item.memory ?? item.text ?? item.body ?? item.formatted ?? "");
  return {
    title: String(item.title ?? ""),
    summary: String(item.summary ?? ""),
    content,
    metadata,
  };
}

function normalizeResponse(payload, fallbackRequestId) {
  const data = payload && typeof payload === "object" ? payload : {};
  const request_id = String(data.request_id || data.requestId || fallbackRequestId);
  let results = Array.isArray(payload) ? payload : data.results;
  if (!Array.isArray(results) && data.data && typeof data.data === "object") {
    results = data.data.results || data.data.items;
  }
  return {
    request_id,
    error: null,
    results: Array.isArray(results) ? results.map(normalizeResult) : [],
  };
}

function readResponseBody(response) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    response.on("data", (chunk) => chunks.push(chunk));
    response.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    response.on("error", reject);
  });
}

function rfc1123Date() {
  return new Date().toUTCString();
}

function contentMd5(data) {
  return createHash("md5").update(data, "utf8").digest("base64");
}

function canonicalizedAcsHeaders(headers) {
  return Object.entries(headers)
    .map(([name, value]) => [String(name).toLowerCase(), String(value).trim()])
    .filter(([name]) => name.startsWith("x-acs-"))
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, value]) => `${name}:${value}\n`)
    .join("");
}

function canonicalizedResource(url) {
  return `${url.pathname || "/"}${url.search || ""}`;
}

function apiKeySearchEndpoint(endpoint) {
  const url = new URL(endpoint);
  if (url.pathname.includes("/contextstore/") && url.pathname.endsWith("/context/search")) {
    url.pathname = "/v2/memories/search";
    url.search = "";
  }
  return url.toString();
}

function searchRequestBody(args, authMode) {
  if (authMode === "apiKey") {
    return {
      query: String(args.query).trim(),
      top_k: args.limit,
      threshold: args.threshold,
      filters: args.filter || {},
    };
  }
  return {
    query: String(args.query).trim(),
    context_type: args.contextType,
    limit: args.limit,
    threshold: args.threshold,
    filter: args.filter || {},
    formatted: true,
  };
}

function signRoaRequest(method, url, headers, accessKey, accessSecret) {
  const accept = headers.Accept || "";
  const md5 = headers["Content-MD5"] || "";
  const contentType = headers["Content-Type"] || "";
  const date = headers.Date || "";
  const stringToSign = [
    method.toUpperCase(),
    accept,
    md5,
    contentType,
    date,
    `${canonicalizedAcsHeaders(headers)}${canonicalizedResource(url)}`,
  ].join("\n");
  const signature = createHmac("sha1", accessSecret).update(stringToSign, "utf8").digest("base64");
  return `acs ${accessKey}:${signature}`;
}

function xmlText(text, tagName) {
  const match = text.match(new RegExp(`<${tagName}>([\\s\\S]*?)<\\/${tagName}>`, "i"));
  if (!match) return "";
  return match[1]
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'");
}

function parseResponsePayload(text, contentType) {
  const trimmed = String(text || "").trim();
  if (!trimmed) return {};
  const lowerContentType = String(contentType || "").toLowerCase();
  if (lowerContentType.includes("json") || trimmed.startsWith("{") || trimmed.startsWith("[")) {
    return JSON.parse(trimmed);
  }
  if (lowerContentType.includes("xml") || trimmed.startsWith("<?xml") || trimmed.startsWith("<Error")) {
    return {
      code: xmlText(trimmed, "Code"),
      message: xmlText(trimmed, "Message"),
      requestId: xmlText(trimmed, "RequestId"),
    };
  }
  return { message: trimmed.slice(0, 500) };
}

async function postJson(endpoint, auth, body) {
  const url = new URL(endpoint);
  const transport = url.protocol === "http:" ? http : https;
  const data = JSON.stringify(body);
  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(data),
  };
  if (auth.mode === "ak") {
    headers.Date = rfc1123Date();
    headers["Content-MD5"] = contentMd5(data);
    headers["x-acs-signature-method"] = "HMAC-SHA1";
    headers["x-acs-signature-version"] = "1.0";
    headers["x-acs-signature-nonce"] = requestId();
    headers["x-acs-request-id"] = auth.requestId;
    headers.Authorization = signRoaRequest("POST", url, headers, auth.accessKey, auth.accessSecret);
  } else if (auth.mode === "apiKey") {
    headers.Authorization = `Token ${auth.apiKey}`;
  }
  const options = {
    method: "POST",
    headers,
    timeout: 20000,
  };
  return new Promise((resolve, reject) => {
    const req = transport.request(url, options, async (res) => {
      try {
        const text = await readResponseBody(res);
        const parsed = parseResponsePayload(text, res.headers["content-type"]);
        resolve({
          statusCode: res.statusCode || 0,
          contentType: res.headers["content-type"] || "",
          payload: parsed,
        });
      } catch (err) {
        reject(err);
      }
    });
    req.on("timeout", () => req.destroy(new Error("request timed out")));
    req.on("error", reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  const id = requestId();
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (err) {
    writeJson(emptyResult(id, err.message));
    return;
  }

  const validationError = validateInput(args);
  if (validationError) {
    writeJson(emptyResult(id, validationError));
    return;
  }
  if (args.help) {
    writeJson(helpResult(id));
    return;
  }

  const config = loadConfig(CONFIG_KEYS);
  if (!enabled(config.AGENTLOOP_ENABLE_RECALL)) {
    writeJson(emptyResult(id));
    return;
  }

  if (!args.confirmOutbound && !enabled(config.AGENTLOOP_CONFIRM_OUTBOUND)) {
    writeJson(emptyResult(id, "outbound recall requires explicit confirmation: pass --confirm-outbound or set AGENTLOOP_CONFIRM_OUTBOUND=true after user approval"));
    return;
  }

  const endpoint = String(config.AGENTLOOP_RECALL_ENDPOINT || "").trim();
  if (!endpoint) {
    writeJson(emptyResult(id, "missing AGENTLOOP_RECALL_ENDPOINT"));
    return;
  }
  const endpointError = validateEndpoint(endpoint);
  if (endpointError) {
    writeJson(emptyResult(id, endpointError));
    return;
  }

  const secretConfig = loadConfig(SECRET_KEYS);
  const accessKey = String(secretConfig.AGENTLOOP_ACCESS_KEY || "").trim();
  const accessSecret = String(secretConfig.AGENTLOOP_ACCESS_SECRET || "").trim();
  const bearerApiKey = String(secretConfig.AGENTLOOP_BEARER_API_KEY || "").trim();
  const hasAkPair = Boolean(accessKey && accessSecret);
  if (!hasAkPair && !bearerApiKey) {
    writeJson(emptyResult(id, "missing credentials: set AGENTLOOP_ACCESS_KEY and AGENTLOOP_ACCESS_SECRET, or AGENTLOOP_BEARER_API_KEY"));
    return;
  }

  const auth = hasAkPair
    ? { mode: "ak", accessKey, accessSecret, requestId: id }
    : { mode: "apiKey", apiKey: bearerApiKey };
  const requestEndpoint = auth.mode === "apiKey" ? apiKeySearchEndpoint(endpoint) : endpoint;
  const body = searchRequestBody(args, auth.mode);

  try {
    const response = await postJson(requestEndpoint, auth, body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      const code = response.payload && (response.payload.code || response.payload.Code);
      const message = response.payload && (response.payload.error || response.payload.message || response.payload.Message);
      const upstreamRequestId = response.payload && (response.payload.requestId || response.payload.RequestId);
      const codeAndMessage = [
        code ? String(code) : "",
        message ? String(message) : "",
      ].filter(Boolean).join(": ");
      const details = [
        codeAndMessage,
        upstreamRequestId ? `requestId=${upstreamRequestId}` : "",
      ].filter(Boolean).join(" ");
      writeJson(emptyResult(id, `SearchContext HTTP ${response.statusCode}${details ? ` ${details}` : ""}`));
      return;
    }
    writeJson(normalizeResponse(response.payload, id));
  } catch (err) {
    writeJson(emptyResult(id, `SearchContext request failed: ${err.message}`));
  }
}

main();
