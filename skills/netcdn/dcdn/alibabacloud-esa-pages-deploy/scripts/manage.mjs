#!/usr/bin/env node
/**
 * Manage ESA Edge Routines
 * Usage: node scripts/manage.mjs <command> [options]
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

async function listRoutines() {
  const client = createClient();
  const resp = await client.getRoutineUserInfo();
  const routines = resp.body.routines || [];

  if (routines.length === 0) {
    console.log("No routines found.");
    return;
  }

  console.log(`Found ${routines.length} routine(s):\n`);
  for (const r of routines) {
    console.log(`  ${r.routineName}`);
    if (r.description) console.log(`    Description: ${r.description}`);
  }
}

async function getRoutine(name) {
  const client = createClient();
  const resp = await client.getRoutine(
    new Esa20240910.GetRoutineRequest({ name }),
  );
  const r = resp.body;

  console.log(`Routine: ${name}`);
  console.log(`  Description: ${r.description || "(none)"}`);
  console.log(`  Created: ${r.createTime}`);
  console.log(`  Updated: ${r.modifyTime}`);
  console.log(`  Code Versions:`);

  if (r.codeVersions) {
    for (const v of r.codeVersions) {
      console.log(`    - ${v.codeVersion} (${v.createTime})`);
    }
  }

  if (r.defaultRelatedRecord) {
    console.log(`  Access URL: https://${r.defaultRelatedRecord}`);
  }
}

// CLI
const [, , command, ...args] = process.argv;

const commands = {
  list: {
    usage: "node scripts/manage.mjs list",
    desc: "List all routines",
    fn: listRoutines,
  },
  get: {
    usage: "node scripts/manage.mjs get <name>",
    desc: "Get routine details",
    fn: () => getRoutine(args[0]),
    validate: () => args[0],
  },
};

function showHelp() {
  console.log("ESA Edge Routine Management\n");
  console.log("Usage: node scripts/manage.mjs <command> [options]\n");
  console.log("Commands:");
  for (const [name, cmd] of Object.entries(commands)) {
    console.log(`  ${cmd.usage.padEnd(45)} ${cmd.desc}`);
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
