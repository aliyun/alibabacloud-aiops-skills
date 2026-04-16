#!/usr/bin/env python3
"""
Query the list of Bailian workspaces.
Uses aliyun modelstudio CLI plugin.
"""

import subprocess
import json
import sys


def main():
    try:
        result = subprocess.run(
            ['aliyun', 'modelstudio', 'list-workspaces', '--user-agent', 'AlibabaCloud-Agent-Skills'],
            capture_output=True,
            text=True,
            timeout=10
        )

        parsed = json.loads(result.stdout)

        workspaces = []
        if 'workspaces' in parsed:
            workspaces = [
                {
                    'workspace_id': ws['workspaceId'],
                    'name': ws['workspaceName']
                }
                for ws in parsed['workspaces']
            ]

        print(json.dumps({'workspaces': workspaces}, indent=2))
    except Exception as error:
        print(json.dumps({
            'error': str(error),
            'recommend': '请确保已安装 aliyun CLI 和 modelstudio 插件（aliyun plugin install --names aliyun-cli-modelstudio）'
        }, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
