import argparse
import oss2
from oss2.models import MetaQuery

from credentials import create_oss_auth, create_oss_bucket
from validation import validate_common_args

def parse_args():
    parser = argparse.ArgumentParser(description='执行OSS基本查询（标量检索）')
    parser.add_argument('--region', type=str, default='cn-beijing',
                        help='OSS region，例如：cn-beijing')
    parser.add_argument('--bucket', type=str, required=True,
                        help='OSS bucket 名称')
    parser.add_argument('--endpoint', type=str, default=None,
                        help='OSS endpoint，例如：https://oss-cn-beijing.aliyuncs.com（不指定则自动生成）')
    parser.add_argument('--scalar-query', type=str, required=True,
                        help='完整的标量查询JSON字符串，例如: \'{"SubQueries":[{"Field":"Filename","Value":"test.jpg","Operation":"eq"}],"Operation":"and"}\'')
    return parser.parse_args()

def main():
    args = parse_args()

    validate_common_args(args)

    if args.endpoint is None:
        args.endpoint = f'https://oss-{args.region}.aliyuncs.com'

    auth = create_oss_auth()
    bucket = create_oss_bucket(auth, args.endpoint, args.bucket, region=args.region)

    query_request = MetaQuery(
        max_results=100,
        query=args.scalar_query,
        sort='Size',
        order='asc',
    )

    try:
        result = bucket.do_bucket_meta_query(query_request)
        print('查询结果:')
        if result.files:
            for file_info in result.files:
                print(f'  文件: {file_info.file_name}')
                print(f'    大小: {file_info.size}')
                print(f'    类型: {file_info.oss_object_type}')
                print(f'    存储类型: {file_info.oss_storage_class}')
                print(f'    ETag: {file_info.etag}')
                print('    ---')
        else:
            print('  无匹配结果')
    except oss2.exceptions.OssError as e:
        print(f'查询失败: {e.message}')
        print(f'Error Code: {e.code}, EC: {e.ec}')
        return False


if __name__ == "__main__":
    main()