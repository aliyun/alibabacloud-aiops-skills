import re
import sys

# OSS 支持向量检索与 AI 内容感知的地域列表
VALID_REGIONS = {
    'cn-hangzhou',      # 华东1（杭州）
    'cn-shanghai',      # 华东2（上海）
    'cn-qingdao',       # 华北1（青岛）
    'cn-beijing',       # 华北2（北京）
    'cn-zhangjiakou',   # 华北3（张家口）
    'cn-shenzhen',      # 华南1（深圳）
    'cn-guangzhou',     # 华南3（广州）
    'cn-chengdu',       # 西南1（成都）
    'cn-hongkong',      # 中国香港
    'ap-southeast-1',   # 新加坡
    'us-east-1',        # 美国（弗吉尼亚）
}

# OSS Bucket 命名规则正则：3-63 个字符，仅允许小写字母、数字和短横线，
# 不能以短横线开头或结尾
_BUCKET_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$')

# Endpoint 合法格式正则：https://oss-{region}.aliyuncs.com 或
# https://{region}.oss[-internal].aliyuncs.com 等阿里云 OSS 域名
_ENDPOINT_RE = re.compile(
    r'^https://[\w\-]+\.aliyuncs\.com$'
)


def validate_region(region):
    """校验 --region 参数是否为合法的 OSS 地域。"""
    if region not in VALID_REGIONS:
        print(f'错误: 不支持的地域: {region}')
        print(f'允许的值: {", ".join(sorted(VALID_REGIONS))}')
        sys.exit(1)


def validate_bucket_name(name):
    """校验 --bucket 参数是否符合 OSS Bucket 命名规则。

    规则: 3-63 个字符，仅允许小写字母、数字和短横线，不能以短横线开头或结尾。
    """
    if not _BUCKET_NAME_RE.match(name):
        print(f'错误: Bucket 名称不合法: {name}')
        print('Bucket 命名规则: 3-63 个字符，仅允许小写字母、数字和短横线，不能以短横线开头或结尾')
        sys.exit(1)


def validate_endpoint(endpoint):
    """校验 --endpoint 参数是否为合法的阿里云 OSS 域名。"""
    if not _ENDPOINT_RE.match(endpoint):
        print(f'错误: endpoint 格式不合法: {endpoint}')
        print('endpoint 必须为 https://<host>.aliyuncs.com 格式的阿里云 OSS 域名')
        sys.exit(1)


def validate_common_args(args):
    """统一校验 --region、--bucket、--endpoint 参数。

    应在各脚本 main() 函数开头、使用参数之前调用。
    如果 endpoint 为 None（由 region 自动生成），则跳过 endpoint 校验。
    """
    validate_region(args.region)
    validate_bucket_name(args.bucket)
    if args.endpoint is not None:
        validate_endpoint(args.endpoint)
