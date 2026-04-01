#!/usr/bin/env node
/**
 * Deploy custom Edge Routine function
 * Usage: node scripts/deploy-function.mjs <name> <code-file>
 */
import Esa20240910 from "@alicloud/esa20240910";
import OpenApi from "@alicloud/openapi-client";
import Credential from "@alicloud/credentials";
import * as fs from "fs";

function createClient() {
  const credential = new Credential.default();
  const config = new OpenApi.Config({
    credential,
    endpoint: "esa.cn-hangzhou.aliyuncs.com",
    userAgent: "AlibabaCloud-Agent-Skills",
  });
  return new Esa20240910.default(config);
}

async function ensureServiceEnabled(client) {
  try {
    const status = await client.getErService(new Esa20240910.GetErServiceRequest({}));
    if (status.body?.status === "online" || status.body?.status === "Running") return;
  } catch (e) {
    // Ignore check errors, attempt to enable
  }
  console.log("Enabling Edge Routine service...");
  try {
    await client.openErService(new Esa20240910.OpenErServiceRequest({}));
    console.log("Edge Routine service enabled.");
  } catch (e) {
    if (e.code === "ErService.HasOpened" || e.message?.includes("HasOpened")) return;
    throw e;
  }
}

async function deployFunction(name, code) {
  const client = createClient();

  // 0. Ensure Edge Routine service is enabled
  await ensureServiceEnabled(client);

  // 1. Create routine
  console.log(`Creating routine: ${name}...`);
  try {
    await client.createRoutine(new Esa20240910.CreateRoutineRequest({ name }));
    console.log("Routine created.");
  } catch (e) {
    if (e.code === "RoutineNameAlreadyExist" || e.code === "RoutineAlreadyExist" || e.message?.includes("already exist")) {
      console.log("Routine already exists, updating...");
    } else {
      throw e;
    }
  }

  // 2. Get upload signature
  console.log("Getting upload signature...");
  const uploadInfo = await client.getRoutineStagingCodeUploadInfo(
    new Esa20240910.GetRoutineStagingCodeUploadInfoRequest({ name })
  );
  const oss = uploadInfo.body.ossPostConfig || uploadInfo.body.OssPostConfig;

  // 3. Upload code
  console.log("Uploading code...");
  const formData = new FormData();
  formData.append("OSSAccessKeyId", oss.OSSAccessKeyId);
  formData.append("Signature", oss.Signature);
  formData.append("callback", oss.callback);
  formData.append("x:codedescription", oss["x:codeDescription"]);
  formData.append("policy", oss.policy);
  formData.append("key", oss.key);
  formData.append("file", new Blob([code], { type: "text/plain" }));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000); // 60s timeout
  try {
    await fetch(oss.Url, { method: "POST", body: formData, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }

  // 4. Commit and deploy
  console.log("Committing code version...");
  const commit = await client.commitRoutineStagingCode(
    new Esa20240910.CommitRoutineStagingCodeRequest({ name })
  );
  const version = commit.body.codeVersion;
  console.log(`Code version: ${version}`);

  for (const env of ["staging", "production"]) {
    console.log(`Deploying to ${env}...`);
    await client.publishRoutineCodeVersion(
      new Esa20240910.PublishRoutineCodeVersionRequest({
        name,
        env,
        codeVersion: version,
      })
    );
  }

  // 5. Get access URL
  const routine = await client.getRoutine(
    new Esa20240910.GetRoutineRequest({ name })
  );
  return routine.body.defaultRelatedRecord
    ? `https://${routine.body.defaultRelatedRecord}`
    : null;
}

// Validate name format
function validateName(name) {
  // Must be lowercase letters/numbers/hyphens, start with letter, length >= 2
  const pattern = /^[a-z][a-z0-9-]{1,}$/;
  if (!pattern.test(name)) {
    throw new Error(
      `Invalid name "${name}". Must start with lowercase letter, contain only lowercase letters/numbers/hyphens, and be at least 2 characters long.`
    );
  }
}

// CLI
const [, , name, codeFile] = process.argv;

if (!name || !codeFile) {
  console.log("Usage: node scripts/deploy-function.mjs <name> <code-file>");
  console.log("  name: Function name (lowercase, letters/numbers/hyphens, start with letter)");
  console.log("  code-file: Path to JavaScript file with Edge Routine code");
  console.log("\nCode format:");
  console.log("  export default {");
  console.log("    async fetch(request) {");
  console.log('      return new Response("Hello");');
  console.log("    },");
  console.log("  };");
  process.exit(1);
}

validateName(name);

if (!fs.existsSync(codeFile)) {
  console.error(`Error: File "${codeFile}" not found.`);
  process.exit(1);
}

const code = fs.readFileSync(codeFile, "utf-8");

deployFunction(name, code)
  .then((url) => {
    console.log("\n✅ Deployment successful!");
    console.log(`Access URL: ${url}`);
  })
  .catch((err) => {
    console.error("\n❌ Deployment failed:", err.message);
    process.exit(1);
  });
