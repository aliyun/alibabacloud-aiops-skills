import argparse
import oss2

from credentials import create_oss_auth, create_oss_bucket
from validation import validate_common_args

# 用于打开 MetaQuery 功能（向量模式 + 内容感知）

def parse_args():
    parser = argparse.ArgumentParser(description='打开 OSS MetaQuery 功能')
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

    # oss2 的 open_bucket_meta_query() 不支持传递 WorkflowParameters，
    # 因此使用底层 _do 方法发送自定义 XML body 以同时开启向量模式和内容感知
    xml_body = '''<MetaQuery>
  <WorkflowParameters>
   <WorkflowParameter>
      <Name>VideoInsightEnable</Name>
      <Value>True</Value>
   </WorkflowParameter>
   <WorkflowParameter>
      <Name>ImageInsightEnable</Name>
      <Value>True</Value>
   </WorkflowParameter>
  </WorkflowParameters>
</MetaQuery>'''

    try:
        resp = bucket._do(
            'POST',
            args.bucket,
            '',
            params={'comp': 'add', 'mode': 'semantic', 'metaQuery': ''},
            data=xml_body.encode('utf-8'),
        )
        print(f'{args.bucket} 开通MetaQuery成功')
        print(f'status code: {resp.status}, request id: {resp.headers.get("x-oss-request-id", "N/A")}')
    except oss2.exceptions.OssError as e:
        print(f'{args.bucket} 开通MetaQuery失败: {e.message}')
        print(f'Error Code: {e.code}, EC: {e.ec}')
        return False

if __name__ == "__main__":
    main()