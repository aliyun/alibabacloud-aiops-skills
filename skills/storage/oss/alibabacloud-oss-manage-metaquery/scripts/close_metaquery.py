import argparse
import oss2

from credentials import create_oss_auth, create_oss_bucket
from validation import validate_common_args

# 用于关闭 OSS MetaQuery 功能

def parse_args():
    parser = argparse.ArgumentParser(description='关闭OSS MetaQuery功能')
    parser.add_argument('--region', type=str, default='cn-shenzhen',
                        help='OSS region，例如：cn-shenzhen')
    parser.add_argument('--bucket', type=str, required=True,
                        help='OSS bucket 名称')
    parser.add_argument('--endpoint', type=str, default=None,
                        help='OSS endpoint，例如：https://oss-cn-shenzhen.aliyuncs.com（不指定则自动生成）')
    return parser.parse_args()

def main():
    args = parse_args()

    validate_common_args(args)

    if args.endpoint is None:
        args.endpoint = f'https://oss-{args.region}.aliyuncs.com'

    auth = create_oss_auth()
    bucket = create_oss_bucket(auth, args.endpoint, args.bucket, region=args.region)

    try:
        bucket.close_bucket_meta_query()
        print(f'{args.bucket} 关闭MetaQuery成功')
    except oss2.exceptions.OssError as e:
        print(f'关闭 {args.bucket} MetaQuery 失败: {e.message}')
        print(f'Error Code: {e.code}, EC: {e.ec}')
        return False


if __name__ == "__main__":
    main()