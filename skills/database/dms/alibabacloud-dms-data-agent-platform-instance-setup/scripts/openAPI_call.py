import hashlib
import sys
import json

from typing import List, Dict, Any

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from fill_in_param_body import fill_in_param_body


class callAliyunOpenAPI:
    def __init__(self):
        pass

    @staticmethod
    def create_client() -> OpenApiClient:
        """
        使用凭据初始化账号Client，凭据通过默认凭据链自动获取。
        凭据链配置方式请参见：https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials#3ca299f04bw3c
        @return: Client
        @throws Exception
        """
        # 使用默认凭据链，无需手动传入 AK/SK
        credentialsClient = CredentialClient()

        config = open_api_models.Config(credential=credentialsClient)
        config.user_agent = "AlibabaCloud-Agent-Skills/alibabacloud-dms-data-agent-platform-instance-setup"
        # Endpoint 请参考 https://api.aliyun.com/product/dms-enterprise
        config.endpoint = "dms-enterprise.aliyuncs.com"
        return OpenApiClient(config)

    @staticmethod
    def create_api_info() -> open_api_models.Params:
        """
        API 相关
        @param path: string Path parameters
        @return: OpenApi.Params
        """
        params = open_api_models.Params(
            # 接口名称,
            action="CreateDifyInstance",
            # 接口版本,
            version="2018-11-01",
            # 接口协议,
            protocol="HTTPS",
            # 接口 HTTP 方法,
            method="POST",
            auth_type="AK",
            style="RPC",
            # 接口 PATH,
            pathname="/",
            # 接口请求体内容格式,
            req_body_type="json",
            # 接口响应体内容格式,
            body_type="json",
        )
        return params

    @staticmethod
    def main(
        args: List[str],
    ) -> None:
        if len(args) != 1:
            print("请传入一个json格式的字符串，作为命令行参数")
            exit(1)
        json_body: Dict[str, Any] = json.loads(args[0])
        json_body = fill_in_param_body(json_body)

        # 基于请求参数生成幂等 ClientToken，确保相同参数的重试不会创建重复实例
        client_token = hashlib.sha256(
            json.dumps(json_body, sort_keys=True).encode()
        ).hexdigest()
        json_body["ClientToken"] = client_token

        client = callAliyunOpenAPI.create_client()
        params = callAliyunOpenAPI.create_api_info()

        # runtime options
        runtime = util_models.RuntimeOptions(
            connect_timeout=10000,  # 连接超时 10 秒（单位：毫秒）
            read_timeout=30000,  # 读取超时 30 秒（单位：毫秒）
        )
        request = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(json_body)
        )
        # 返回值实际为 Map 类型，可从 Map 中获得三类数据：响应体 body、响应头 headers、HTTP 返回的状态码 statusCode。
        resp: Dict[str, Any] = client.call_api(params, request, runtime)
        # 只输出 body 中对用户有用的字段，避免暴露 HTTP headers 等非必要信息
        body: Dict[str, Any] = resp.get("body", {})

        # 对 Data 中已知敏感字段进行脱敏处理
        _SENSITIVE_DATA_KEYS = {"Password", "password", "AccessKey", "SecretKey", "ConnectionString", "connectionString"}
        raw_data = body.get("Data")
        if isinstance(raw_data, dict):
            sanitized_data = {
                k: ("***" if k in _SENSITIVE_DATA_KEYS else v)
                for k, v in raw_data.items()
            }
        else:
            sanitized_data = raw_data

        output = {
            "Success": body.get("Success"),
            "HttpStatusCode": body.get("HttpStatusCode"),
            "RequestId": body.get("RequestId"),
            "Data": sanitized_data,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    callAliyunOpenAPI.main(sys.argv[1:])
    exit(0)
