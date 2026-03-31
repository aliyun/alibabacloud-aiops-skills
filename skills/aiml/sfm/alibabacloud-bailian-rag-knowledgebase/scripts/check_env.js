#!/usr/bin/env node
/**
 * Check the Bailian SDK environment and credential configuration.
 * Returns a JSON object with the check results.
 * Uses the Alibaba Cloud default credential chain; does not directly read AccessKey/SecretKey.
 */

const { execSync } = require('child_process');
const Credential = require('@alicloud/credentials');

// 必要的 npm 依赖列表
const REQUIRED_PACKAGES = [
    '@alicloud/bailian20231229',
    '@alicloud/modelstudio20260210',
    '@alicloud/openapi-client',
    '@alicloud/credentials',
    '@alicloud/tea-util'
];

async function checkEnv() {
    const result = {
        npmPackagesInstalled: {},
        allNpmPackagesInstalled: false,
        credentialsConfigured: false,
        ready: false,
        errors: []
    };

    // 检查凭证是否可通过默认凭证链获取
    try {
        const credential = new Credential.default();
        // 尝试获取凭证，验证凭证链是否可用
        await credential.getAccessKeyId();
        result.credentialsConfigured = true;
    } catch (error) {
        result.errors.push('阿里云凭证未配置，请运行 `aliyun configure` 配置凭证');
        result.credentialsConfigured = false;
    }

    // 检查所有必要的 npm 包是否安装
    let allInstalled = true;
    for (const pkg of REQUIRED_PACKAGES) {
        try {
            execSync(`npm list ${pkg}`, { stdio: 'pipe' });
            result.npmPackagesInstalled[pkg] = true;
        } catch (error) {
            result.npmPackagesInstalled[pkg] = false;
            result.errors.push(`未安装 npm 包：${pkg}`);
            allInstalled = false;
        }
    }
    result.allNpmPackagesInstalled = allInstalled;

    // 判断是否就绪
    result.ready = result.credentialsConfigured && result.allNpmPackagesInstalled;

    console.log(JSON.stringify(result, null, 2));
}

checkEnv();
