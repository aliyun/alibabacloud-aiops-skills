import argparse
import os
import time
import oss2

from credentials import create_oss_auth, create_oss_bucket
from validation import validate_common_args

# 用于上传文件到 OSS

def parse_args():
    parser = argparse.ArgumentParser(description='上传文件到OSS')
    parser.add_argument('--region', type=str, default='cn-beijing',
                        help='OSS region，例如：cn-beijing')
    parser.add_argument('--bucket', type=str, required=True,
                        help='OSS bucket 名称')
    parser.add_argument('--endpoint', type=str, default=None,
                        help='OSS endpoint，例如：https://oss-cn-beijing.aliyuncs.com（不指定则自动生成）')
    parser.add_argument('--local-path', type=str, required=True,
                        help='本地文件路径')
    parser.add_argument('--remote-key', type=str, required=True,
                        help='OSS上的文件名(key)')
    return parser.parse_args()

def main():
    args = parse_args()

    validate_common_args(args)

    if args.endpoint is None:
        args.endpoint = f'https://oss-{args.region}.aliyuncs.com'

    if not os.path.exists(args.local_path):
        print(f'文件不存在: {args.local_path}')
        return False

    auth = create_oss_auth()
    bucket = create_oss_bucket(auth, args.endpoint, args.bucket, region=args.region)

    # 生成 OSS tag，记录文件创建时间纳秒时间戳，后续可用于搜索
    tagging_header = f'CreatTime={time.time_ns()}'

    try:
        print(f'开始上传文件: {args.remote_key}')
        with open(args.local_path, 'rb') as file_obj:
            result = bucket.put_object(
                args.remote_key,
                file_obj,
                headers={'x-oss-tagging': tagging_header},
            )
        print(f'上传 {args.remote_key} 成功')
        print(f'status code: {result.status}, request id: {result.request_id}')
    except oss2.exceptions.OssError as e:
        print(f'上传 {args.remote_key} 失败: {e.message}')
        print(f'Error Code: {e.code}')
        return False


if __name__ == "__main__":
    main()