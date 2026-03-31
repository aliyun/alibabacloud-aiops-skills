import argparse
import oss2

from credentials import create_oss_auth, create_oss_bucket
from validation import validate_common_args

# 用于创建 OSS 存储空间

def parse_args():
    parser = argparse.ArgumentParser(description='创建OSS存储空间')
    parser.add_argument('--region', type=str, default='cn-beijing',
                        help='OSS region，例如：cn-beijing')
    parser.add_argument('--bucket', type=str, required=True,
                        help='OSS bucket 名称')
    parser.add_argument('--endpoint', type=str, default=None,
                        help='OSS endpoint，例如：https://oss-cn-beijing.aliyuncs.com（不指定则自动生成）')
    return parser.parse_args()

def main():
    args = parse_args()

    validate_common_args(args)

    if args.endpoint is None:
        args.endpoint = f'https://oss-{args.region}.aliyuncs.com'

    auth = create_oss_auth()
    bucket = create_oss_bucket(auth, args.endpoint, args.bucket, region=args.region)

    try:
        bucket.create_bucket()
        print(f'创建存储空间 {args.bucket} 成功')
    except oss2.exceptions.OssError as e:
        print(f'创建 {args.bucket} 失败: {e.message}')
        print(f'Error Code: {e.code}')
        return False


if __name__ == "__main__":
    main()