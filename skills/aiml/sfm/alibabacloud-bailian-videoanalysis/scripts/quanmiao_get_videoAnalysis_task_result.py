#!/usr/bin/env python3
"""
Get video analysis task result from Bailian.
Uses the Alibaba Cloud default credential chain.
Optionally save the result to a local JSON file.
"""

import sys
import json
import argparse
import os
from pathlib import Path

from alibabacloud_quanmiaolightapp20240801.client import Client as QuanMiaoLightApp20240801Client
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_quanmiaolightapp20240801 import models as quan_miao_light_app_20240801_models
from alibabacloud_tea_util import models as util_models


def create_client() -> QuanMiaoLightApp20240801Client:
    """
    Initialize client using credential chain
    @return: Client
    @throws Exception
    """
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        user_agent='AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis'
    )
    # Endpoint refer to https://api.aliyun.com/product/QuanMiaoLightApp
    config.endpoint = f'quanmiaolightapp.cn-beijing.aliyuncs.com'
    return QuanMiaoLightApp20240801Client(config)


def main(workspace_id, task_id, save_path=None):
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
        result_data = resp.body.to_map()
        
        # Save to file if save_path is provided and status is SUCCESSED
        if save_path and result_data.get('payload', {}).get('output', {}).get('taskStatus') == 'SUCCESSED':
            save_result_to_file(result_data, save_path)

        # Print result to stdout
        print("\nRaw result: \n\n" + json.dumps(result_data, indent=2, ensure_ascii=False))
    except Exception as error:
        error_data = getattr(error, 'data', {})
        recommend = error_data.get('Recommend', '') if isinstance(error_data, dict) else ''
        print(json.dumps({
            'error': str(error),
            'recommend': recommend
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


# Parameter validation functions
def validate_workspace_id(arg):
    if not arg or arg.strip() == '':
        raise ValueError('workspace_id cannot be empty')
    if not isinstance(arg, str):
        raise ValueError('workspace_id must be a string type')
    
    # Trim whitespace
    trimmed = arg.strip()
    
    if len(trimmed) > 64:
        raise ValueError('workspace_id length cannot exceed 64 characters')
    # Only allow letters, numbers, hyphens, and underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', trimmed):
        raise ValueError('workspace_id contains invalid characters, only letters, numbers, hyphens and underscores are allowed')
    return trimmed


def validate_task_id(arg):
    if not arg or arg.strip() == '':
        raise ValueError('task_id cannot be empty')
    if not isinstance(arg, str):
        raise ValueError('task_id must be a string type')
    
    # Trim whitespace
    trimmed = arg.strip()
    
    if len(trimmed) > 128:
        raise ValueError('task_id length cannot exceed 128 characters')
    return trimmed


def save_result_to_file(result_data, save_path):
    """
    Save the result data to a JSON file.
    
    Args:
        result_data: The result data to save
        save_path: Path to save the JSON file
    """
    try:
        # Create directory if it doesn't exist
        save_dir = os.path.dirname(save_path)
        if save_dir:
            Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # Write JSON file
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Raw JSON result saved to: {save_path}", file=sys.stderr)
        
    except Exception as e:
        print(f"⚠️  Warning: Failed to save raw JSON result to {save_path}: {str(e)}", file=sys.stderr)


# Get parameters from command line arguments
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get video analysis task result from Bailian')
    parser.add_argument('--workspace_id', required=True, help='Workspace ID')
    parser.add_argument('--task_id', required=True, help='Task ID')
    parser.add_argument('--save_path', required=False, default=None, 
                        help='Path to save JSON result (only saves when taskStatus=SUCCESSED)')

    args = parser.parse_args()
    
    try:
        workspace_id_arg = validate_workspace_id(args.workspace_id)
        task_id_arg = validate_task_id(args.task_id)
        main(workspace_id_arg, task_id_arg, args.save_path)
    except Exception as error:
        print(json.dumps({'error': str(error)}, indent=2, ensure_ascii=False))
        sys.exit(1)