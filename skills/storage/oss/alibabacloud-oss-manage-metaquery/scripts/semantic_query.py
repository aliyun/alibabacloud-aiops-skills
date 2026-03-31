import argparse
import sys
from xml.sax.saxutils import escape as xml_escape

import oss2

from credentials import create_oss_auth, create_oss_bucket
from validation import validate_common_args

VALID_MEDIA_TYPES = {'image', 'video', 'audio', 'document'}

def parse_args():
    parser = argparse.ArgumentParser(description='执行OSS语义查询（向量检索）')
    parser.add_argument('--region', type=str, default='cn-beijing',
                        help='OSS region，例如：cn-beijing')
    parser.add_argument('--bucket', type=str, required=True,
                        help='OSS bucket 名称')
    parser.add_argument('--endpoint', type=str, default=None,
                        help='OSS endpoint，例如：https://oss-cn-beijing.aliyuncs.com（不指定则自动生成）')
    parser.add_argument('--query', type=str, required=True,
                        help='语义查询内容，如"人"、"风景"等自然语言描述')
    parser.add_argument('--media-types', type=str, nargs='+', default=['video'],
                        help='多媒体类型，支持: image, video, audio, document')
    parser.add_argument('--scalar-query', type=str, help='完整的标量查询JSON字符串，用于向量+标量组合查询')
    return parser.parse_args()

def main():
    args = parse_args()

    # 校验 media-types 是否在允许的枚举值范围内
    invalid_types = set(args.media_types) - VALID_MEDIA_TYPES
    if invalid_types:
        print(f'错误: 不支持的媒体类型: {", ".join(invalid_types)}')
        print(f'允许的值: {", ".join(sorted(VALID_MEDIA_TYPES))}')
        sys.exit(1)

    validate_common_args(args)

    if args.endpoint is None:
        args.endpoint = f'https://oss-{args.region}.aliyuncs.com'

    auth = create_oss_auth()
    bucket = create_oss_bucket(auth, args.endpoint, args.bucket, region=args.region)

    # 构建媒体类型 XML（对用户输入进行 XML 转义）
    media_types_xml = ''.join([f'<MediaType>{xml_escape(mt)}</MediaType>' for mt in args.media_types])

    # 构建 SimpleQuery 部分（如果提供了标量查询，对输入进行 XML 转义）
    simple_query_part = ''
    if args.scalar_query:
        simple_query_part = f'\n<SimpleQuery>{xml_escape(args.scalar_query)}</SimpleQuery>'

    # 构建查询 XML body（对 query 参数进行 XML 转义）
    # oss2 的 do_bucket_meta_query 不支持 semantic 模式，因此使用底层 _do 方法
    xml_body = f'''<MetaQuery>
<MediaTypes>
{media_types_xml}
</MediaTypes>
<Query>{xml_escape(args.query)}</Query>{simple_query_part}
</MetaQuery>'''

    try:
        resp = bucket._do(
            'POST',
            args.bucket,
            '',
            params={'comp': 'query', 'mode': 'semantic', 'metaQuery': ''},
            data=xml_body.encode('utf-8'),
        )
        content = resp.read()
        print('查询结果:')
        print(content.decode('utf-8'))
    except oss2.exceptions.OssError as e:
        print(f'查询失败: {e.message}')
        print(f'Error Code: {e.code}, EC: {e.ec}')
        return False


if __name__ == "__main__":
    main()