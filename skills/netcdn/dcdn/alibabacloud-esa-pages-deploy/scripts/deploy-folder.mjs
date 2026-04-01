#!/usr/bin/env node
/**
 * Deploy static directory to ESA (Assets mode)
 * Usage: node scripts/deploy-folder.mjs <name> <folder-path> [description]
 */
import Esa20240910 from "@alicloud/esa20240910";
import OpenApi from "@alicloud/openapi-client";
import TeaUtil from "@alicloud/tea-util";
import Credential from "@alicloud/credentials";
import JSZip from "jszip";
import * as fs from "fs";
import * as path from "path";

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

async function deployFolder(name, folderPath, description = "") {
  const client = createClient();
  const runtime = new TeaUtil.RuntimeOptions({});

  // 0. Ensure Edge Routine service is enabled
  await ensureServiceEnabled(client);

  // 1. Create routine
  console.log(`Creating routine: ${name}...`);
  try {
    await client.createRoutine(
      new Esa20240910.CreateRoutineRequest({ name, description })
    );
    console.log("Routine created.");
  } catch (e) {
    if (e.code === "RoutineNameAlreadyExist" || e.code === "RoutineAlreadyExist" || e.message?.includes("already exist")) {
      console.log("Routine already exists, updating...");
    } else {
      throw e;
    }
  }

  // 2. Create assets code version
  console.log("Creating assets code version...");
  const params = new OpenApi.Params({
    action: "CreateRoutineWithAssetsCodeVersion",
    version: "2024-09-10",
    protocol: "https",
    method: "POST",
    authType: "AK",
    bodyType: "json",
    reqBodyType: "json",
    style: "RPC",
    pathname: "/",
  });
  const body = { Name: name, CodeDescription: description };
  const request = new OpenApi.OpenApiRequest({ body });
  const result = await client.callApi(params, request, runtime);
  const ossConfig = result.body?.OssPostConfig || {};
  const codeVersion = result.body?.CodeVersion;
  console.log(`Code version: ${codeVersion}`);

  // 3. Package and upload zip
  console.log("Packaging files...");
  const zip = new JSZip();
  let fileCount = 0;

  const addFiles = (dir, zipPath = "") => {
    for (const file of fs.readdirSync(dir)) {
      const fullPath = path.join(dir, file);
      const zipFilePath = zipPath ? `${zipPath}/${file}` : file;
      if (fs.statSync(fullPath).isDirectory()) {
        addFiles(fullPath, zipFilePath);
      } else {
        zip.file(`assets/${zipFilePath}`, fs.readFileSync(fullPath));
        fileCount++;
      }
    }
  };
  addFiles(folderPath);
  console.log(`Packaged ${fileCount} files.`);

  const zipBuffer = await zip.generateAsync({ type: "nodebuffer" });
  console.log(`Zip size: ${(zipBuffer.length / 1024).toFixed(1)} KB`);

  console.log("Uploading to OSS...");
  const formData = new FormData();
  formData.append("OSSAccessKeyId", ossConfig.OSSAccessKeyId);
  formData.append("Signature", ossConfig.Signature);
  formData.append("policy", ossConfig.Policy);
  formData.append("key", ossConfig.Key);
  if (ossConfig.XOssSecurityToken) {
    formData.append("x-oss-security-token", ossConfig.XOssSecurityToken);
  }
  formData.append("file", new Blob([zipBuffer]));
  const controller = new AbortController();
  const uploadTimeout = setTimeout(() => controller.abort(), 120000); // 120s timeout for large files
  try {
    await fetch(ossConfig.Url, { method: "POST", body: formData, signal: controller.signal });
  } finally {
    clearTimeout(uploadTimeout);
  }

  // 4. Wait for build ready
  console.log("Waiting for build...");
  for (let i = 0; i < 300; i++) {
    const infoParams = new OpenApi.Params({
      action: "GetRoutineCodeVersionInfo",
      version: "2024-09-10",
      protocol: "https",
      method: "GET",
      authType: "AK",
      bodyType: "json",
      reqBodyType: "json",
      style: "RPC",
      pathname: "/",
    });
    const info = await client.callApi(
      infoParams,
      new OpenApi.OpenApiRequest({
        query: { Name: name, CodeVersion: codeVersion },
      }),
      runtime
    );
    const status = (info.body?.Status || "").toLowerCase();
    if (status === "available") {
      console.log("Build ready.");
      break;
    }
    if (status && status !== "init") {
      throw new Error(`Build failed: ${status}`);
    }
    process.stdout.write(".");
    await new Promise((r) => setTimeout(r, 1000));
  }

  // 5. Deploy to staging and production
  for (const env of ["staging", "production"]) {
    console.log(`Deploying to ${env}...`);
    const deployParams = new OpenApi.Params({
      action: "CreateRoutineCodeDeployment",
      version: "2024-09-10",
      protocol: "https",
      method: "POST",
      authType: "AK",
      bodyType: "json",
      reqBodyType: "json",
      style: "RPC",
      pathname: "/",
    });
    await client.callApi(
      deployParams,
      new OpenApi.OpenApiRequest({
        query: {
          Name: name,
          Env: env,
          Strategy: "percentage",
          CodeVersions: JSON.stringify([
            { Percentage: 100, CodeVersion: codeVersion },
          ]),
        },
      }),
      runtime
    );
  }

  // 6. Get access URL
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
const [, , name, folderPath, description] = process.argv;

if (!name || !folderPath) {
  console.log("Usage: node scripts/deploy-folder.mjs <name> <folder-path> [description]");
  console.log("  name: Function name (lowercase, letters/numbers/hyphens, start with letter)");
  console.log("  folder-path: Path to static directory (e.g., ./dist)");
  console.log("  description: Optional description");
  process.exit(1);
}

validateName(name);

if (!fs.existsSync(folderPath) || !fs.statSync(folderPath).isDirectory()) {
  console.error(`Error: "${folderPath}" is not a valid directory.`);
  process.exit(1);
}

deployFolder(name, folderPath, description || "")
  .then((url) => {
    console.log("\n✅ Deployment successful!");
    console.log(`Access URL: ${url}`);
  })
  .catch((err) => {
    console.error("\n❌ Deployment failed:", err.message);
    process.exit(1);
  });
