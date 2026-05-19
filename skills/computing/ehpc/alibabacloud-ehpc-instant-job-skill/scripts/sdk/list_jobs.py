#!/usr/bin/env python
#coding=utf-8

import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

# 使用默认凭证链：自动从环境变量、配置文件(~/.aliyun/config.json)、ECS RAM角色等来源获取凭证
client = AcsClient(region_id='cn-shanghai')

request = CommonRequest()
request.set_accept_format('json')
request.set_domain('ehpcinstant.cn-shanghai.aliyuncs.com')
request.set_method('POST')
request.set_protocol_type('https')
request.set_version('2023-07-01')
request.set_action_name('ListJobs')
request.set_connect_timeout(5000)   # 连接超时 5 秒
request.set_read_timeout(10000)     # 读取超时 10 秒
request.add_header('User-Agent', 'AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill')

filter = {
  "JobId": "test",
  "JobName": "test"
}
filterStr = json.dumps(filter)
request.add_query_param('Filter', filterStr)

response = client.do_action(request)
print(str(response, encoding='utf-8'))