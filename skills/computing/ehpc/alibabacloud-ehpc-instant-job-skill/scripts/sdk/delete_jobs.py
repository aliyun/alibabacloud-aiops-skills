#!/usr/bin/env python
#coding=utf-8

import sys
import os
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

# 引入与 CLI 端 _lib_validate.sh 对齐的输入校验库
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib_validate import require_argv, validate_job_id

# 输入校验：JobId 必须符合 ^job-[a-zA-Z0-9]+$ 白名单
job_id = require_argv(
    sys.argv, 1, validate_job_id,
    "用法: python delete_jobs.py <JobId>   (JobId 形如 job-xxxxxxxx)"
)

# 使用默认凭证链：自动从环境变量、配置文件(~/.aliyun/config.json)、ECS RAM角色等来源获取凭证
client = AcsClient(region_id='cn-shanghai')

request = CommonRequest()
request.set_accept_format('json')
request.set_domain('ehpcinstant.cn-shanghai.aliyuncs.com')
request.set_method('POST')
request.set_protocol_type('https')
request.set_version('2023-07-01')
request.set_action_name('DeleteJobs')
request.set_connect_timeout(5000)   # 连接超时 5 秒
request.set_read_timeout(10000)     # 读取超时 10 秒
request.add_header('User-Agent', 'AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill')

jobSpec = [
  {
    "JobId": job_id
  }
]

jobSpecStr = json.dumps(jobSpec)
request.add_query_param('JobSpec', jobSpecStr)

response = client.do_action(request)
print(str(response, encoding='utf-8'))