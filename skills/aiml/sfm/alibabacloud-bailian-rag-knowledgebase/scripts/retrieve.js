#!/usr/bin/env node
/**
 * Retrieve information from a Bailian knowledge base.
 * Uses the Alibaba Cloud default credential chain.
 * Parameters: workspaceId, indexId, query
 */

const bailian20231229 = require('@alicloud/bailian20231229');
const Util = require('@alicloud/tea-util');
const Credential = require('@alicloud/credentials');
const OpenApi = require('@alicloud/openapi-client');

async function main(workspaceId, indexId, query) {
    let credential = new Credential.default();
    let config = new OpenApi.Config({
      credential: credential,
    });
    config.endpoint = `bailian.cn-beijing.aliyuncs.com`;
    let client = new bailian20231229.default(config);
    let retrieveRequest = new bailian20231229.RetrieveRequest({
        query: query,
        indexId: indexId,
    });
    let runtime = new Util.RuntimeOptions({
        readTimeout: 8000,
        connectTimeout: 3000
    });
    let headers = {
        "User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase"
    };
    runtime.extendsParameters = new Util.ExtendsParameters();
    runtime.extendsParameters.queries = {
        "_source": "skill"
    }

    try {
        let resp = await client.retrieveWithOptions(workspaceId, retrieveRequest, headers, runtime);
        // 输出检索结果
        const status = resp.body?.status;
        if(status != 200) {
            console.log("error", JSON.stringify(resp.body))
            process.exit(1);
        }
        const data = resp.body?.data || {};
        const nodes = data.nodes || [];
        console.log(JSON.stringify({
            indexId: indexId,
            chunks: nodes.map(n => ({
                content: n.text,
                score: n.score,
                doc_name: n.metadata?.doc_name || '',
                title: n.metadata?.title || ''
            }))
        }, null, 2));
    } catch (error) {
        console.error(JSON.stringify({
            error: error.message,
            recommend: error.data?.["Recommend"] || ''
        }, null, 2));
        process.exit(1);
    }
}

// 参数校验函数
function validateArg(arg, name, maxLength) {
    if (typeof arg !== 'string') {
        throw new Error(`${name} 必须是字符串类型`);
    }
    if (!arg || arg.trim().length === 0) {
        throw new Error(`${name} 不能为空`);
    }
    if (arg.length > maxLength) {
        throw new Error(`${name} 长度不能超过 ${maxLength} 字符`);
    }
    // 只允许字母、数字、连字符、下划线
    if (!/^[a-zA-Z0-9_\-]+$/.test(arg)) {
        throw new Error(`${name} 包含非法字符，只允许字母、数字、连字符和下划线`);
    }
    return arg.trim();
}

function validateQuery(arg) {
    if (typeof arg !== 'string') {
        throw new Error('query 必须是字符串类型');
    }
    if (!arg || arg.trim().length === 0) {
        throw new Error('query 不能为空');
    }
    if (arg.length > 2000) {
        throw new Error('query 长度不能超过 2000 字符');
    }
    // 过滤危险字符，防止注入
    const dangerous = /[<>\{\}\[\]\$\|`;]/;
    if (dangerous.test(arg)) {
        throw new Error('query 包含非法字符');
    }
    return arg.trim();
}

// 从命令行参数获取参数
const args = process.argv.slice(2);
if (args.length < 3) {
    console.error('Usage: node retrieve.js <workspaceId> <indexId> <query>');
    process.exit(1);
}

try {
    const workspaceId = validateArg(args[0], 'workspaceId', 64);
    const indexId = validateArg(args[1], 'indexId', 64);
    const query = validateQuery(args[2]);
    main(workspaceId, indexId, query);
} catch (error) {
    console.error(JSON.stringify({ error: error.message }, null, 2));
    process.exit(1);
}
