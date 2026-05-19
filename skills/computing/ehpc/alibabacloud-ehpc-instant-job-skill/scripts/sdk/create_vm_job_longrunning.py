#!/usr/bin/env python
#coding=utf-8

import os
import json
import base64
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

# 使用默认凭证链：自动从环境变量、配置文件(~/.aliyun/config.json)、ECS RAM角色等来源获取凭证
client = AcsClient(region_id='cn-shanghai')

# VM 登录密码从环境变量读取，避免明文硬编码
vm_password = os.environ.get('VM_PASSWORD')
if not vm_password:
    raise EnvironmentError("环境变量 VM_PASSWORD 未设置，请先 export VM_PASSWORD=<your-password>")

request = CommonRequest()
request.set_accept_format('json')
request.set_domain('ehpcinstant.cn-shanghai.aliyuncs.com')
request.set_method('POST')
request.set_protocol_type('https')
request.set_version('2023-07-01')
request.set_action_name('CreateJob')
request.set_connect_timeout(5000)   # 连接超时 5 秒
request.set_read_timeout(10000)     # 读取超时 10 秒
request.add_header('User-Agent', 'AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill')

# Step 1: 定义 Shell 脚本字符串
shell_script = """#!/bin/bash

sleep 180
"""

# Step 2: 将字符串转换为 Base64 编码
# 注意：Base64 编码需要将字符串转换为字节格式
encoded_script = base64.b64encode(shell_script.encode('utf-8')).decode('utf-8')

tasks = [
    {
      "TaskSpec": {
        "TaskExecutor": [
          {
            "VM": {
              "Image": "m-xxx",
              #"Script": encoded_script,
              "Password": vm_password
            }
          }
        ],
        "VolumeMount": [
          {
            "MountPath": "/mnt",
            "VolumeDriver": "alicloud/nas",
            "MountOptions": "{\"server\":\"xxx.cn-hangzhou.nas.aliyuncs.com\",\"vers\":\"3\",\"path\":\"/\",\"options\":\"nolock,tcp,noresvport\"}"
          }
        ],
        "Resource": {
          "Disks": [
            {
              "Type": "System",
              "Size": 40
            }
          ],
          "Cores": 4,
          "Memory": 8
        }
      },
      "ExecutorPolicy": {
        "MaxCount": 1
      },
      "TaskSustainable": True
    }
  ],

deploymentPolicy = {
  "Network": {
    "Vswitch": [
      "vsw-xxx"
    ],
    "EnableExternalIpAddress": True,
  },
  "AllocationSpec": "Standard",
  "Level":"General"
}

securityPolicy = {
  "SecurityGroup": {
    "SecurityGroupIds": [
      "sg-xxx"
    ]
  }
}

tasksStr = json.dumps(tasks)
deploymentPolicyStr = json.dumps(deploymentPolicy)
securityPolicyStr = json.dumps(securityPolicy)

request.add_query_param('JobName', "create_vm_job")
request.add_query_param('JobDescription', "E-HPC Instant VM 后台服务作业提交")
request.add_query_param('Tasks', tasksStr)
request.add_query_param('DeploymentPolicy', deploymentPolicyStr)
request.add_query_param('SecurityPolicy', securityPolicyStr)

response = client.do_action(request)
print(str(response, encoding='utf-8'))
