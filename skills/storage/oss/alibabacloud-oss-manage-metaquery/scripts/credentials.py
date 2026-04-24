import oss2
from alibabacloud_credentials.client import Client as CredentialClient


class _DefaultCredentialProvider(oss2.credentials.CredentialsProvider):
    """基于 alibabacloud_credentials 默认凭证链的 oss2 CredentialsProvider 实现。

    CredentialClient 会按以下顺序自动查找凭证：
    环境变量 → ~/.aliyun/config.json → IMDS（ECS 实例角色）等，
    无需在代码中显式处理 AK/SK。
    """

    def __init__(self):
        self._client = CredentialClient()

    def get_credentials(self):
        ak = self._client.get_access_key_id()
        sk = self._client.get_access_key_secret()
        token = self._client.get_security_token()
        return oss2.credentials.Credentials(ak, sk, token)


def create_oss_auth():
    """通过默认凭证链创建 oss2 V4 签名认证对象。

    依赖 alibabacloud_credentials 的 CredentialClient 自动发现凭证，
    支持 AK、STS、ECS 实例角色等多种认证方式，无需手动传入凭证。
    """
    credentials_provider = _DefaultCredentialProvider()
    return oss2.ProviderAuthV4(credentials_provider)


def create_oss_bucket(auth, endpoint, bucket_name, region=None):
    """创建带有 User-Agent 配置的 OSS Bucket 对象。

    Args:
        auth: 认证对象
        endpoint: OSS endpoint
        bucket_name: Bucket 名称
        region: 区域(可选)

    Returns:
        配置好 User-Agent 的 Bucket 对象
    """
    bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region, connect_timeout=60)
    bucket.user_agent = 'AlibabaCloud-Agent-Skills/alibabacloud-oss-manage-metaquery'
    return bucket
