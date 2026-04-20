#!/usr/bin/env node
/**
 * Query the list of MaaS workspaces.
 * Uses the Alibaba Cloud default credential chain.
 */

const ModelStudio20260210 = require('@alicloud/modelstudio20260210');
const Util = require('@alicloud/tea-util');
const Credential = require('@alicloud/credentials');
const OpenApi = require('@alicloud/openapi-client');

async function main() {
    let credential = new Credential.default();
    let config = new OpenApi.Config({
      credential: credential,
    });
    config.endpoint = `modelstudio.cn-beijing.aliyuncs.com`;
    let client = new ModelStudio20260210.default(config);
    let listWorkspacesRequest = new ModelStudio20260210.ListWorkspacesRequest({
        maxResults: 50
    });
    let runtime = new Util.RuntimeOptions({
        readTimeout: 8000,
        connectTimeout: 3000
    });
    let headers = {
        "User-Agent": "AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase"
    };

    try {
        let resp = await client.listWorkspacesWithOptions(listWorkspacesRequest, headers, runtime);
        let statusCode = resp.statusCode;
        if (statusCode == 200) {
            // 输出精简结果，包含工作空间 ID 和名称/描述
            const workspaces = resp.body?.workspaces || [];
            const result = workspaces.map(ws => ({
                workspaceId: ws.workspaceId,
                name: ws.workspaceName
            }));
            console.log(JSON.stringify({
                workspaces: result
            }, null, 2));
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

// 从命令行参数获取 maxResults 和 nextToken (可选)
main();
