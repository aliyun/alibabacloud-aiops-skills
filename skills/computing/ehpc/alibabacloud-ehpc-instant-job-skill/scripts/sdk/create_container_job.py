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
request.set_action_name('CreateJob')
request.set_connect_timeout(5000)   # 连接超时 5 秒
request.set_read_timeout(10000)     # 读取超时 10 秒
request.add_header('User-Agent', 'AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill')

tasks = [
  {
    "TaskSpec": {
      "TaskExecutor": [
        {
          "Container": {
            "Image":"registry-vpc.cn-shanghai.aliyuncs.com/demo/xxx:v1.2",
            "AppId":"ci-ctn-xxx",
            "Command": [
              "sleep","180000",
            ],
            "EnvironmentVars": [
              {
                "Name": "RUN_PY_PATH",
                "Value": "/mnt/test.py"
              },
              {
                "Name": "OUTPUT_PATH",
                "Value": "/mnt/output/"
              },
              {
                "Name": "INPUT_PDB_PATH",
                "Value": "/mnt/input/test.pdb"
              },
              {
                "Name": "LOG_PATH",
                "Value": "/mnt/logs"
              }
            ]
          }
        }
      ],
      "VolumeMount": [
        {
          "MountPath": "/mnt",
          "VolumeDriver": "alicloud/nas",
          "MountOptions": "{\"server\":\"xxx.cn-shanghai.nas.aliyuncs.com\",\"vers\":\"3\",\"path\":\"/\",\"options\":\"nolock,tcp,noresvport\"}"
        }
      ],
      "Resource": {
        "Disks": [
          {
            "Type": "System",
            "Size": 40
          }
        ],
        "Cores": 8,
        "Memory": 32,
        "InstanceTypes":[
          "ecs.gn6v-c8g1.2xlarge"
        ]
      }
    },
    "ExecutorPolicy": {
      "MaxCount": 1
    },
    "TaskSustainable": False
  }
]

deploymentPolicy = {
  "Network": {
    "Vswitch": [
      "vsw-xxx"
    ],
    "EnableExternalIpAddress": False,
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

request.add_query_param('JobName', "testX")
request.add_query_param('JobDescription', "container job test")
request.add_query_param('Tasks', tasksStr)
request.add_query_param('DeploymentPolicy', deploymentPolicyStr)
request.add_query_param('SecurityPolicy', securityPolicyStr)

response = client.do_action(request)
print(str(response, encoding='utf-8'))
