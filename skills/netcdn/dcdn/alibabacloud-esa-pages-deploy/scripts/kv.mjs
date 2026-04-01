#!/usr/bin/env node
/**
 * Manage ESA Edge KV namespaces and key-value pairs
 * Usage: node scripts/kv.mjs <command> [options]
 */
import Esa20240910 from "@alicloud/esa20240910";
import OpenApi from "@alicloud/openapi-client";
import Credential from "@alicloud/credentials";

function createClient() {
  const credential = new Credential.default();
  const config = new OpenApi.Config({
    credential,
    endpoint: "esa.cn-hangzhou.aliyuncs.com",
    userAgent: "AlibabaCloud-Agent-Skills",
  });
  return new Esa20240910.default(config);
}

// --- Namespace commands ---

async function createNamespace(namespace, description) {
  const client = createClient();
  console.log(`Creating namespace: ${namespace}...`);
  await client.createKvNamespace(
    new Esa20240910.CreateKvNamespaceRequest({
      namespace,
      description: description || "",
    }),
  );
  console.log(`✅ Namespace "${namespace}" created.`);
}

async function listNamespaces() {
  const client = createClient();
  const resp = await client.getKvAccount(
    new Esa20240910.GetKvAccountRequest({}),
  );
  const namespaces = resp.body?.namespaces || [];

  if (namespaces.length === 0) {
    console.log("No namespaces found.");
    return;
  }

  console.log(`Found ${namespaces.length} namespace(s):\n`);
  for (const ns of namespaces) {
    console.log(`  ${ns.namespace}`);
    if (ns.description) console.log(`    Description: ${ns.description}`);
    if (ns.status) console.log(`    Status: ${ns.status}`);
  }
}

async function getNamespace(namespace) {
  const client = createClient();
  const resp = await client.getKvNamespace(
    new Esa20240910.GetKvNamespaceRequest({ namespace }),
  );
  const ns = resp.body;
  console.log(`Namespace: ${ns.namespace}`);
  console.log(`  Description: ${ns.description || "(none)"}`);
  console.log(`  Status: ${ns.status || "unknown"}`);
  console.log(
    `  Capacity: ${ns.capacityUsed || 0} / ${ns.capacity || "unknown"}`,
  );
}

// --- Key-Value commands ---

async function putKv(namespace, key, value, ttl) {
  const client = createClient();
  const request = new Esa20240910.PutKvRequest({ namespace, key, value });
  if (ttl) request.expirationTtl = Number(ttl);
  await client.putKv(request);
  console.log(`✅ Put "${key}" in "${namespace}".`);
}

async function getKv(namespace, key) {
  const client = createClient();
  const resp = await client.getKv(
    new Esa20240910.GetKvRequest({ namespace, key }),
  );
  console.log(resp.body?.value ?? resp.body);
}

async function listKvs(namespace, prefix) {
  const client = createClient();
  const request = new Esa20240910.ListKvsRequest({ namespace, pageSize: 100 });
  if (prefix) request.prefix = prefix;
  const resp = await client.listKvs(request);
  const keys = resp.body?.keys || [];

  if (keys.length === 0) {
    console.log(`No keys found in namespace "${namespace}".`);
    return;
  }

  console.log(`Keys in "${namespace}":\n`);
  for (const k of keys) {
    console.log(`  ${k}`);
  }
}

// --- Batch commands ---

async function batchPutKv(namespace, kvPairsStr) {
  const client = createClient();
  // Parse "key1=val1,key2=val2" or JSON array
  let items;
  try {
    items = JSON.parse(kvPairsStr);
  } catch {
    // Parse comma-separated key=value pairs
    items = kvPairsStr.split(",").map((pair) => {
      const [Key, ...rest] = pair.trim().split("=");
      return { Key: Key.trim(), Value: rest.join("=").trim() };
    });
  }

  console.log(`Batch writing ${items.length} key(s) to "${namespace}"...`);
  const request = new Esa20240910.BatchPutKvRequest({ namespace });
  request.body = JSON.stringify(items);
  await client.batchPutKv(request);
  console.log(`✅ Batch put ${items.length} key(s) to "${namespace}".`);
}

// --- CLI ---

const [, , command, ...args] = process.argv;

const commands = {
  // Namespace
  "ns-create": {
    usage: "node scripts/kv.mjs ns-create <namespace> [description]",
    desc: "Create a KV namespace",
    fn: () => createNamespace(args[0], args[1]),
    validate: () => args[0],
  },
  "ns-list": {
    usage: "node scripts/kv.mjs ns-list",
    desc: "List all KV namespaces",
    fn: listNamespaces,
  },
  "ns-get": {
    usage: "node scripts/kv.mjs ns-get <namespace>",
    desc: "Get namespace details",
    fn: () => getNamespace(args[0]),
    validate: () => args[0],
  },
  // Key-Value
  put: {
    usage: "node scripts/kv.mjs put <namespace> <key> <value> [ttl]",
    desc: "Write a key-value pair",
    fn: () => putKv(args[0], args[1], args[2], args[3]),
    validate: () => args[0] && args[1] && args[2],
  },
  get: {
    usage: "node scripts/kv.mjs get <namespace> <key>",
    desc: "Read a key's value",
    fn: () => getKv(args[0], args[1]),
    validate: () => args[0] && args[1],
  },
  list: {
    usage: "node scripts/kv.mjs list <namespace> [prefix]",
    desc: "List keys in a namespace",
    fn: () => listKvs(args[0], args[1]),
    validate: () => args[0],
  },
  // Batch
  "batch-put": {
    usage: 'node scripts/kv.mjs batch-put <namespace> "k1=v1,k2=v2"',
    desc: "Batch write key-value pairs",
    fn: () => batchPutKv(args[0], args[1]),
    validate: () => args[0] && args[1],
  },
};

function showHelp() {
  console.log("ESA Edge KV Management\n");
  console.log("Usage: node scripts/kv.mjs <command> [options]\n");
  console.log("Namespace Commands:");
  for (const [name, cmd] of Object.entries(commands)) {
    if (name.startsWith("ns-"))
      console.log(`  ${cmd.usage.padEnd(55)} ${cmd.desc}`);
  }
  console.log("\nKey-Value Commands:");
  for (const [name, cmd] of Object.entries(commands)) {
    if (!name.startsWith("ns-") && !name.startsWith("batch")) {
      console.log(`  ${cmd.usage.padEnd(55)} ${cmd.desc}`);
    }
  }
  console.log("\nBatch Commands:");
  for (const [name, cmd] of Object.entries(commands)) {
    if (name.startsWith("batch"))
      console.log(`  ${cmd.usage.padEnd(55)} ${cmd.desc}`);
  }
}

if (!command || !commands[command]) {
  showHelp();
  process.exit(command ? 1 : 0);
}

const cmd = commands[command];
if (cmd.validate && !cmd.validate()) {
  console.error(`Usage: ${cmd.usage}`);
  process.exit(1);
}

cmd.fn().catch((err) => {
  console.error(`❌ Error: ${err.message}`);
  process.exit(1);
});
