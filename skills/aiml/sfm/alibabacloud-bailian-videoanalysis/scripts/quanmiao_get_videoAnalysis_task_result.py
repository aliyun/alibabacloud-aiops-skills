#!/usr/bin/env python3
"""
Get video analysis task result from Bailian.
Uses the Alibaba Cloud default credential chain.
"""

import sys
import json
import argparse

from alibabacloud_quanmiaolightapp20240801.client import Client as QuanMiaoLightApp20240801Client
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_quanmiaolightapp20240801 import models as quan_miao_light_app_20240801_models
from alibabacloud_tea_util import models as util_models


def create_client() -> QuanMiaoLightApp20240801Client:
    """
    使用凭据初始化账号Client
    @return: Client
    @throws Exception
    """
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        user_agent='AlibabaCloud-Agent-Skills'
    )
    # Endpoint 请参考 https://api.aliyun.com/product/QuanMiaoLightApp
    config.endpoint = f'quanmiaolightapp.cn-beijing.aliyuncs.com'
    return QuanMiaoLightApp20240801Client(config)


def main(workspace_id, task_id):
    client = create_client()
    get_video_analysis_task_request = quan_miao_light_app_20240801_models.GetVideoAnalysisTaskRequest(
        task_id=task_id
    )
    runtime = util_models.RuntimeOptions(
        read_timeout=30000,
        connect_timeout=5000
    )
    headers = {}
    try:
        resp = client.get_video_analysis_task_with_options(workspace_id, get_video_analysis_task_request, headers, runtime)
        print(json.dumps(resp.body.to_map(), indent=2, ensure_ascii=False))
    except Exception as error:
        error_data = getattr(error, 'data', {})
        recommend = error_data.get('Recommend', '') if isinstance(error_data, dict) else ''
        print(json.dumps({
            'error': str(error),
            'recommend': recommend
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


# 参数校验函数
def validate_workspace_id(arg):
    if not arg or arg.strip() == '':
        raise ValueError('workspace_id 不能为空')
    if not isinstance(arg, str):
        raise ValueError('workspace_id 必须是字符串类型')
    
    # 先去除前后空格
    trimmed = arg.strip()
    
    if len(trimmed) > 64:
        raise ValueError('workspace_id 长度不能超过 64 字符')
    # 只允许字母、数字、连字符、下划线
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', trimmed):
        raise ValueError('workspace_id 包含非法字符，只允许字母、数字、连字符和下划线')
    return trimmed


def validate_task_id(arg):
    if not arg or arg.strip() == '':
        raise ValueError('task_id 不能为空')
    if not isinstance(arg, str):
        raise ValueError('task_id 必须是字符串类型')
    
    # 先去除前后空格
    trimmed = arg.strip()
    
    if len(trimmed) > 128:
        raise ValueError('task_id 长度不能超过 128 字符')
    return trimmed


# 从命令行参数获取参数
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get video analysis task result from Bailian')
    parser.add_argument('--workspace_id', required=True, help='Workspace ID')
    parser.add_argument('--task_id', required=True, help='Task ID')
    
    args = parser.parse_args()
    
    try:
        workspace_id_arg = validate_workspace_id(args.workspace_id)
        task_id_arg = validate_task_id(args.task_id)
        main(workspace_id_arg, task_id_arg)
    except Exception as error:
        print(json.dumps({'error': str(error)}, indent=2, ensure_ascii=False))
        sys.exit(1)