#!/usr/bin/env node
/**
 * Query the list of Bailian knowledge bases.
 * Uses the Alibaba Cloud default credential chain.
 */

const bailian20231229 = require('@alicloud/bailian20231229');
const Util = require('@alicloud/tea-util');
const Credential = require('@alicloud/credentials');
const OpenApi = require('@alicloud/openapi-client');

async function main(workspaceId, pageNumber, pageSize) {
    let credential = new Credential.default();
    let config = new OpenApi.Config({
      credential: credential,
    });
    config.endpoint = `bailian.cn-beijing.aliyuncs.com`;
    let client = new bailian20231229.default(config);
    let listIndicesRequest = new bailian20231229.ListIndicesRequest({
        pageNumber: pageNumber,
        pageSize: pageSize
    });
    let runtime = new Util.RuntimeOptions({
        readTimeout: 8000,
        connectTimeout: 3000
    });
    let headers = {
        "User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase"
    };

    try {
        let resp = await client.listIndicesWithOptions(workspaceId || '', listIndicesRequest, headers, runtime);
        let status = resp.body?.status
        if (status == '200') {
            // 输出精简结果，包含知识库 ID 和名称/描述
            const indices = resp.body?.data?.indices || [];
            const result = indices.map(idx => ({
                indexId: idx.id,
                name: idx.name,
                description: idx.description || ''
            }));
            console.log(JSON.stringify(result, null, 2));
        } else {
            console.log(JSON.stringify(resp.body, null, 2))
        }
    } catch (error) {
        console.log(JSON.stringify({
            error: error.message,
            recommend: error.data?.["Recommend"] || ''
        }, null, 2));
        process.exit(1);
    }
}

// 参数校验函数
function validateWorkspaceId(arg) {
    if (!arg || arg.trim().length === 0) {
        return '';
    }
    if (typeof arg !== 'string') {
        throw new Error('workspaceId 必须是字符串类型');
    }
    if (arg.length > 64) {
        throw new Error('workspaceId 长度不能超过 64 字符');
    }
    // 只允许字母、数字、连字符、下划线
    if (!/^[a-zA-Z0-9_\-]+$/.test(arg)) {
        throw new Error('workspaceId 包含非法字符，只允许字母、数字、连字符和下划线');
    }
    return arg.trim();
}

function validatePageNumber(arg) {
    const num = parseInt(arg, 10);
    if (isNaN(num) || num < 1) {
        return 1;
    }
    if (num > 10000) {
        throw new Error('pageNumber 不能超过 10000');
    }
    return num;
}

function validatePageSize(arg) {
    const num = parseInt(arg, 10);
    if (isNaN(num) || num < 1) {
        return 10;
    }
    if (num > 100) {
        throw new Error('pageSize 不能超过 100');
    }
    return num;
}

// 从命令行参数获取 workspaceId (可选)
try {
    const workspaceIdArg = validateWorkspaceId(process.argv[2] || '');
    const pageNumber = validatePageNumber(process.argv[3] || 1);
    const pageSize = validatePageSize(process.argv[4] || 10);
    main(workspaceIdArg, pageNumber, pageSize);
} catch (error) {
    console.error(JSON.stringify({ error: error.message }, null, 2));
    process.exit(1);
}
