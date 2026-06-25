import sys
import json
from typing import List, Dict, Any

from dify_skill_utils import mask_sensitive_DFS, callAliyunOpenAPI

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("请传入一个区域名称, 如: cn-hangzhou, cn-beijing")
        exit(1)
    result: Dict[str, Any] = callAliyunOpenAPI.launch({'DataRegion': args[0]}, 'ListDifyInstances')
    mask_sensitive_DFS(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    exit(0)
