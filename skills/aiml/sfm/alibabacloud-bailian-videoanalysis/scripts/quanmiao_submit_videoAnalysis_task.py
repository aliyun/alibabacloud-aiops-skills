#!/usr/bin/env python3
"""
Submit video analysis task to Bailian.
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

def main(workspace_id, file_url):
    client = create_client()
    submit_video_analysis_task_request = quan_miao_light_app_20240801_models.SubmitVideoAnalysisTaskRequest(
        video_url=file_url
    )
    runtime = util_models.RuntimeOptions(
        read_timeout=30000,
        connect_timeout=5000
    )
    headers = {}
    try:
        resp = client.submit_video_analysis_task_with_options(workspace_id, submit_video_analysis_task_request, headers, runtime)
        status = resp.body.http_status_code

        if status == 200:
            # 输出任务ID
            result = {
                'task_id': resp.body.data.task_id if resp.body.data else None
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
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


def validate_file_url(arg):
    if not arg or arg.strip() == '':
        raise ValueError('fileUrl 不能为空')
    if not isinstance(arg, str):
        raise ValueError('fileUrl 必须是字符串类型')
    
    # 先去除前后空格
    trimmed = arg.strip()
    
    # 基本的 URL 格式校验
    if not trimmed.startswith(('http://', 'https://')):
        raise ValueError('fileUrl 必须是有效的 HTTP/HTTPS URL')
    return trimmed

# 从命令行参数获取参数
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Submit video analysis task to Bailian')
    parser.add_argument('--workspace_id', required=True, help='Workspace ID')
    parser.add_argument('--file_url', required=True, help='File URL (OSS temporary URL)')
    
    args = parser.parse_args()
    
    try:
        workspace_id_arg = validate_workspace_id(args.workspace_id)
        file_url_arg = validate_file_url(args.file_url)
        main(workspace_id_arg, file_url_arg)
    except Exception as error:
        print(json.dumps({'error': str(error)}, indent=2, ensure_ascii=False))
        sys.exit(1)
